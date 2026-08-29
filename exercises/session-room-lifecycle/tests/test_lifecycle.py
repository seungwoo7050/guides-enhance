from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from session_room_lifecycle.engine import run_scenario  # noqa: E402


# [Implementation 10]
# Lifecycle ownership and cleanup regression tests
# 중복 참가, 오래된 epoch, grace 만료, drain, shutdown 누락을 검출합니다.
class SessionRoomLifecycleTests(unittest.TestCase):
    def execute(self, events: list[dict], grace: int = 5) -> dict:
        return run_scenario({"config": {"reconnect_grace": grace}, "events": events})

    @staticmethod
    def event(event_id: str, kind: str, logical_time: int, **values: object) -> dict:
        return {"event_id": event_id, "kind": kind, "logical_time": logical_time, **values}

    def authenticated_pair(self) -> list[dict]:
        return [
            self.event("connect-1", "CONNECT", 0, connection_id="c1"),
            self.event(
                "auth-1",
                "AUTHENTICATE",
                0,
                connection_id="c1",
                session_id="s1",
                player_id="p1",
                session_epoch=1,
            ),
        ]

    def test_authentication_and_room_join(self) -> None:
        events = self.authenticated_pair() + [
            self.event("room", "CREATE_ROOM", 1, connection_id="c1", room_id="r1")
        ]
        result = self.execute(events)
        room = result["final_state"]["rooms"][0]
        self.assertEqual(["p1"], room["player_ids"])
        self.assertEqual("ROOM_CREATED", result["trace"][-1]["reason_code"])

    def test_join_before_authentication_is_rejected(self) -> None:
        result = self.execute(
            [
                self.event("connect", "CONNECT", 0, connection_id="c1"),
                self.event("join", "JOIN_ROOM", 1, connection_id="c1", room_id="r1"),
            ]
        )
        self.assertEqual("CONNECTION_NOT_AUTHENTICATED", result["trace"][-1]["reason_code"])

    def test_duplicate_join_and_duplicate_event_do_not_add_members(self) -> None:
        events = self.authenticated_pair() + [
            self.event("room", "CREATE_ROOM", 1, connection_id="c1", room_id="r1"),
            self.event("join-again", "JOIN_ROOM", 2, connection_id="c1", room_id="r1"),
            self.event("join-again", "JOIN_ROOM", 2, connection_id="c1", room_id="r1"),
        ]
        result = self.execute(events)
        self.assertEqual(["p1"], result["final_state"]["rooms"][0]["player_ids"])
        self.assertEqual("DUPLICATE_EVENT", result["trace"][-1]["reason_code"])

    def test_conflicting_duplicate_event_cannot_advance_time_or_expire_session(self) -> None:
        events = self.authenticated_pair() + [
            self.event("disconnect", "DISCONNECT", 1, connection_id="c1"),
            self.event("disconnect", "DISCONNECT", 10, connection_id="c1"),
        ]
        result = self.execute(events, grace=3)
        self.assertEqual("EVENT_ID_CONFLICT", result["trace"][-1]["reason_code"])
        self.assertEqual(1, result["final_state"]["logical_time"])
        self.assertEqual("WAITING_RECONNECT", result["final_state"]["sessions"][0]["state"])
        self.assertEqual([], result["trace"][-1]["expired_sessions"])

    def test_reconnect_with_new_epoch_preserves_player_and_room(self) -> None:
        events = self.authenticated_pair() + [
            self.event("room", "CREATE_ROOM", 1, connection_id="c1", room_id="r1"),
            self.event("disconnect", "DISCONNECT", 2, connection_id="c1"),
            self.event("connect-2", "CONNECT", 3, connection_id="c2"),
            self.event(
                "reconnect",
                "RECONNECT",
                4,
                connection_id="c2",
                session_id="s1",
                player_id="p1",
                session_epoch=2,
            ),
        ]
        result = self.execute(events)
        self.assertEqual(1, len(result["final_state"]["players"]))
        self.assertEqual("r1", result["final_state"]["players"][0]["room_id"])
        self.assertEqual(2, result["final_state"]["sessions"][0]["epoch"])

    def test_old_epoch_and_late_reconnect_are_rejected(self) -> None:
        prefix = self.authenticated_pair() + [
            self.event("disconnect", "DISCONNECT", 1, connection_id="c1"),
            self.event("connect-2", "CONNECT", 2, connection_id="c2"),
        ]
        old = self.execute(
            prefix
            + [
                self.event(
                    "old",
                    "RECONNECT",
                    2,
                    connection_id="c2",
                    session_id="s1",
                    player_id="p1",
                    session_epoch=1,
                )
            ]
        )
        self.assertEqual("SESSION_EPOCH_MISMATCH", old["trace"][-1]["reason_code"])

        late = self.execute(
            prefix
            + [
                self.event("time", "ADVANCE_TIME", 7),
                self.event(
                    "late",
                    "RECONNECT",
                    7,
                    connection_id="c2",
                    session_id="s1",
                    player_id="p1",
                    session_epoch=2,
                ),
            ],
            grace=3,
        )
        self.assertEqual("RECONNECT_GRACE_EXPIRED", late["trace"][-1]["reason_code"])

    def test_grace_expiry_reports_removed_empty_room(self) -> None:
        events = self.authenticated_pair() + [
            self.event("room", "CREATE_ROOM", 1, connection_id="c1", room_id="r1"),
            self.event("disconnect", "DISCONNECT", 2, connection_id="c1"),
            self.event("time", "ADVANCE_TIME", 8),
        ]
        result = self.execute(events, grace=3)
        last = result["trace"][-1]
        self.assertEqual(["s1"], last["expired_sessions"])
        self.assertEqual(["room:r1"], last["destroyed_resources"])
        self.assertEqual([], result["final_state"]["rooms"])

    def test_expired_owner_transfers_room_ownership(self) -> None:
        events = self.authenticated_pair() + [
            self.event("room", "CREATE_ROOM", 1, connection_id="c1", room_id="r1"),
            self.event("connect-2", "CONNECT", 1, connection_id="c2"),
            self.event(
                "auth-2",
                "AUTHENTICATE",
                1,
                connection_id="c2",
                session_id="s2",
                player_id="p2",
                session_epoch=1,
            ),
            self.event("join-2", "JOIN_ROOM", 2, connection_id="c2", room_id="r1"),
            self.event("ready-1", "READY", 2, connection_id="c1", room_id="r1"),
            self.event("ready-2", "READY", 2, connection_id="c2", room_id="r1"),
            self.event(
                "start",
                "START_MATCH",
                3,
                connection_id="c1",
                room_id="r1",
                match_id="m1",
            ),
            self.event("disconnect", "DISCONNECT", 4, connection_id="c1"),
            self.event("time", "ADVANCE_TIME", 8),
            self.event("end", "END_MATCH", 9, connection_id="c2", match_id="m1"),
        ]
        result = self.execute(events, grace=3)
        self.assertEqual("MATCH_FINALIZED", result["trace"][-1]["reason_code"])
        room = result["final_state"]["rooms"][0]
        self.assertEqual("p2", room["owner_player_id"])
        self.assertEqual(["p2"], room["player_ids"])

    def test_all_forfeited_match_is_disposed(self) -> None:
        events = self.authenticated_pair() + [
            self.event("room", "CREATE_ROOM", 1, connection_id="c1", room_id="r1"),
            self.event("ready", "READY", 2, connection_id="c1", room_id="r1"),
            self.event(
                "start",
                "START_MATCH",
                3,
                connection_id="c1",
                room_id="r1",
                match_id="m1",
            ),
            self.event("disconnect", "DISCONNECT", 4, connection_id="c1"),
            self.event("time", "ADVANCE_TIME", 8),
        ]
        result = self.execute(events, grace=3)
        last = result["trace"][-1]
        self.assertEqual(["match:m1", "room:r1"], last["destroyed_resources"])
        self.assertEqual([], result["final_state"]["rooms"])
        self.assertEqual([], result["final_state"]["matches"])

    def test_match_blocks_join_and_finalizes_once(self) -> None:
        events = self.authenticated_pair() + [
            self.event("room", "CREATE_ROOM", 1, connection_id="c1", room_id="r1"),
            self.event("ready", "READY", 2, connection_id="c1", room_id="r1"),
            self.event(
                "start",
                "START_MATCH",
                3,
                connection_id="c1",
                room_id="r1",
                match_id="m1",
            ),
            self.event("connect-2", "CONNECT", 4, connection_id="c2"),
            self.event(
                "auth-2",
                "AUTHENTICATE",
                4,
                connection_id="c2",
                session_id="s2",
                player_id="p2",
                session_epoch=1,
            ),
            self.event("late-join", "JOIN_ROOM", 5, connection_id="c2", room_id="r1"),
            self.event("end", "END_MATCH", 6, connection_id="c1", match_id="m1"),
            self.event("end-again", "END_MATCH", 7, connection_id="c1", match_id="m1"),
        ]
        result = self.execute(events)
        reasons = [item["reason_code"] for item in result["trace"]]
        self.assertIn("ROOM_NOT_JOINABLE", reasons)
        self.assertEqual("MATCH_ALREADY_FINALIZED", reasons[-1])
        self.assertEqual(1, result["final_state"]["matches"][0]["result_revision"])

    def test_drain_rejects_new_room_but_existing_match_can_end(self) -> None:
        events = self.authenticated_pair() + [
            self.event("room", "CREATE_ROOM", 1, connection_id="c1", room_id="r1"),
            self.event("ready", "READY", 2, connection_id="c1", room_id="r1"),
            self.event(
                "start",
                "START_MATCH",
                3,
                connection_id="c1",
                room_id="r1",
                match_id="m1",
            ),
            self.event("drain", "BEGIN_DRAIN", 4),
            self.event("new-room", "CREATE_ROOM", 5, connection_id="c1", room_id="r2"),
            self.event("end", "END_MATCH", 6, connection_id="c1", match_id="m1"),
        ]
        result = self.execute(events)
        self.assertEqual("SERVER_DRAINING", result["trace"][-2]["reason_code"])
        self.assertEqual("MATCH_FINALIZED", result["trace"][-1]["reason_code"])

    def test_shutdown_clears_all_resources(self) -> None:
        events = self.authenticated_pair() + [
            self.event("room", "CREATE_ROOM", 1, connection_id="c1", room_id="r1"),
            self.event("shutdown", "SHUTDOWN", 2),
        ]
        result = self.execute(events)
        final = result["final_state"]
        self.assertEqual("SHUTDOWN", final["server_state"])
        for name in ("connections", "sessions", "players", "rooms", "matches"):
            self.assertEqual([], final[name])


if __name__ == "__main__":
    unittest.main()
