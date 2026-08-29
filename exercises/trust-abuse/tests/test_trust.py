from __future__ import annotations

import copy
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trust_abuse.engine import run_scenario  # noqa: E402


# [Implementation 13]
# Trust, rate-limit, audit, and alert regression tests
# client 권위 상승, 조기 sequence 갱신, reconnect 우회, 비밀값 기록을 검출합니다.
class TrustAbuseTests(unittest.TestCase):
    def base(self, release: str = "r1") -> dict:
        return {
            "config": {
                "release_id": release,
                "max_payload_bytes": 128,
                "max_move_delta": 3,
                "coordinate_limit": 10,
                "alert_threshold": 2,
                "default_rate_limit": {"capacity": 3, "refill_per_tick": 1},
                "rate_limits": {"MOVE": {"capacity": 2, "refill_per_tick": 0}},
            },
            "initial_state": {
                "sessions": [
                    {
                        "session_id": "s1",
                        "actor_id": "a1",
                        "player_id": "p1",
                        "connection_id": "c1",
                        "session_epoch": 1,
                    },
                    {
                        "session_id": "s2",
                        "actor_id": "a2",
                        "player_id": "p2",
                        "connection_id": "c2",
                        "session_epoch": 1,
                    },
                ],
                "players": [
                    {
                        "player_id": "p1",
                        "session_id": "s1",
                        "room_id": "room-1",
                        "match_id": "match-1",
                        "x": 0,
                        "y": 0,
                        "score": 0,
                        "last_sequence": 0,
                    },
                    {
                        "player_id": "p2",
                        "session_id": "s2",
                        "room_id": "room-1",
                        "match_id": "match-1",
                        "x": 5,
                        "y": 0,
                        "score": 0,
                        "last_sequence": 0,
                    },
                ],
                "rooms": [{"room_id": "room-1", "player_ids": ["p1", "p2"]}],
                "matches": [
                    {
                        "match_id": "match-1",
                        "room_id": "room-1",
                        "state": "RUNNING",
                        "player_ids": ["p1", "p2"],
                    }
                ],
                "entities": [
                    {
                        "entity_id": "entity-p1",
                        "room_id": "room-1",
                        "match_id": "match-1",
                        "owner_player_id": "p1",
                    },
                    {
                        "entity_id": "entity-p2",
                        "room_id": "room-1",
                        "match_id": "match-1",
                        "owner_player_id": "p2",
                    },
                ],
            },
            "events": [],
        }

    @staticmethod
    def command(
        command_id: str,
        sequence: int,
        *,
        kind: str = "MOVE",
        payload: dict | None = None,
        **overrides: object,
    ) -> dict:
        command = {
            "command_id": command_id,
            "actor_id": "a1",
            "session_id": "s1",
            "connection_id": "c1",
            "session_epoch": 1,
            "player_id": "p1",
            "room_id": "room-1",
            "match_id": "match-1",
            "sequence": sequence,
            "kind": kind,
            "payload": payload if payload is not None else {"dx": 1, "dy": 0},
            "auth_token": "do-not-log-this-token",
        }
        command.update(overrides)
        return command

    @staticmethod
    def event(event_id: str, logical_time: int, command: dict) -> dict:
        return {
            "event_id": event_id,
            "kind": "COMMAND",
            "logical_time": logical_time,
            "command": command,
        }

    def test_normal_move_updates_authoritative_position(self) -> None:
        scenario = self.base()
        scenario["events"] = [self.event("e1", 0, self.command("c1", 1))]
        result = run_scenario(scenario)
        player = result["authoritative_state"]["players"][0]
        self.assertEqual((1, 0, 1), (player["x"], player["y"], player["last_sequence"]))
        self.assertEqual("ALLOW", result["trace"][0]["status"])

    def test_identity_room_and_epoch_mismatch_do_not_change_state(self) -> None:
        cases = [
            ("PLAYER_SESSION_MISMATCH", {"player_id": "p2"}),
            ("ROOM_MISMATCH", {"room_id": "other"}),
            ("SESSION_EPOCH_MISMATCH", {"session_epoch": 0}),
        ]
        for reason, override in cases:
            with self.subTest(reason=reason):
                scenario = self.base()
                scenario["events"] = [
                    self.event("e1", 0, self.command("c1", 1, **override))
                ]
                result = run_scenario(scenario)
                player = result["authoritative_state"]["players"][0]
                self.assertEqual((0, 0, 0), (player["x"], player["y"], player["last_sequence"]))
                self.assertEqual(reason, result["trace"][0]["reason_code"])

    def test_entity_existence_and_ownership_are_checked(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            self.event(
                "missing",
                0,
                self.command(
                    "missing-command",
                    1,
                    kind="USE_OWNED_ENTITY",
                    payload={"entity_id": "missing"},
                ),
            ),
            self.event(
                "other",
                1,
                self.command(
                    "other-command",
                    1,
                    kind="USE_OWNED_ENTITY",
                    payload={"entity_id": "entity-p2"},
                ),
            ),
        ]
        result = run_scenario(scenario)
        self.assertEqual("ENTITY_NOT_FOUND", result["trace"][0]["reason_code"])
        self.assertEqual("ENTITY_OWNERSHIP_MISMATCH", result["trace"][1]["reason_code"])
        entities = {item["entity_id"]: item for item in result["authoritative_state"]["entities"]}
        self.assertEqual(0, entities["entity-p2"]["use_count"])

    def test_move_limit_non_finite_and_payload_size_are_rejected(self) -> None:
        scenario = self.base()
        scenario["config"]["rate_limits"]["MOVE"]["capacity"] = 10
        scenario["events"] = [
            self.event("fast", 0, self.command("fast-command", 1, payload={"dx": 9, "dy": 0})),
            self.event("nan", 1, self.command("nan-command", 1, payload={"dx": math.nan, "dy": 0})),
            self.event(
                "large",
                2,
                self.command("large-command", 1, payload={"data": "x" * 200}),
            ),
        ]
        result = run_scenario(scenario)
        self.assertEqual("MOVE_LIMIT_EXCEEDED", result["trace"][0]["reason_code"])
        self.assertEqual("INVALID_NUMERIC_VALUE", result["trace"][1]["reason_code"])
        self.assertEqual("PAYLOAD_TOO_LARGE", result["trace"][2]["reason_code"])

    def test_invalid_payload_is_audited_and_rate_limited(self) -> None:
        scenario = self.base()
        scenario["config"]["rate_limits"]["MOVE"] = {"capacity": 1, "refill_per_tick": 0}
        scenario["events"] = [
            self.event(
                "large-1",
                0,
                self.command("large-command-1", 1, payload={"data": "x" * 200}),
            ),
            self.event(
                "large-2",
                1,
                self.command("large-command-2", 1, payload={"data": "y" * 200}),
            ),
        ]
        result = run_scenario(scenario)
        self.assertEqual("PAYLOAD_TOO_LARGE", result["trace"][0]["reason_code"])
        self.assertEqual("RATE_LIMITED", result["trace"][1]["reason_code"])
        self.assertEqual(2, len(result["audit_events"]))
        self.assertEqual(0, result["authoritative_state"]["players"][0]["last_sequence"])

    def test_client_authority_commands_are_denied(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            self.event(
                "set-position",
                0,
                self.command(
                    "set-position-command",
                    1,
                    kind="SET_POSITION",
                    payload={"x": 9, "y": 9},
                ),
            )
        ]
        result = run_scenario(scenario)
        self.assertEqual("CLIENT_AUTHORITY_VIOLATION", result["trace"][0]["reason_code"])
        player = result["authoritative_state"]["players"][0]
        self.assertEqual((0, 0), (player["x"], player["y"]))

    def test_rejected_command_does_not_consume_sequence(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            self.event("bad", 0, self.command("bad-command", 1, payload={"dx": 8, "dy": 0})),
            self.event("good", 1, self.command("good-command", 1, payload={"dx": 2, "dy": 0})),
        ]
        result = run_scenario(scenario)
        player = result["authoritative_state"]["players"][0]
        self.assertEqual((2, 1), (player["x"], player["last_sequence"]))
        self.assertEqual("ALLOW", result["trace"][1]["status"])

    def test_duplicate_command_does_not_repeat_state_audit_or_alert_input(self) -> None:
        scenario = self.base()
        command = self.command("c1", 1)
        scenario["events"] = [
            self.event("e1", 0, command),
            self.event("e2", 0, copy.deepcopy(command)),
        ]
        result = run_scenario(scenario)
        self.assertEqual("DUPLICATE_COMMAND", result["trace"][1]["reason_code"])
        self.assertEqual(1, len(result["audit_events"]))
        self.assertEqual(1, result["authoritative_state"]["players"][0]["x"])

    def test_command_id_conflict_does_not_replace_original_cache(self) -> None:
        scenario = self.base()
        original = self.command("c1", 1, payload={"dx": 1, "dy": 0})
        conflict = self.command("c1", 1, payload={"dx": 2, "dy": 0})
        scenario["events"] = [
            self.event("original", 0, original),
            self.event("conflict", 1, conflict),
            self.event("conflict-duplicate", 2, copy.deepcopy(conflict)),
            self.event("original-duplicate", 3, copy.deepcopy(original)),
        ]
        result = run_scenario(scenario)
        reasons = [item["reason_code"] for item in result["trace"]]
        self.assertEqual(
            [
                "ALLOWED",
                "COMMAND_ID_CONFLICT",
                "DUPLICATE_COMMAND_ID_CONFLICT",
                "DUPLICATE_COMMAND",
            ],
            reasons,
        )
        self.assertEqual(2, len(result["audit_events"]))
        self.assertEqual(1, result["authoritative_state"]["players"][0]["x"])

    def test_spoofed_actor_is_audited_under_authenticated_actor(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            self.event("spoof", 0, self.command("c1", 1, actor_id="a2"))
        ]
        result = run_scenario(scenario)
        audit = result["audit_events"][0]
        self.assertEqual("ACTOR_SESSION_MISMATCH", audit["reason_code"])
        self.assertEqual("a1", audit["actor_id"])
        self.assertEqual("a2", audit["claimed_actor_id"])

    def test_reconnect_cannot_claim_another_active_connection(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            {
                "event_id": "reconnect",
                "kind": "RECONNECT",
                "logical_time": 1,
                "session_id": "s1",
                "new_connection_id": "c2",
                "session_epoch": 2,
            }
        ]
        result = run_scenario(scenario)
        self.assertEqual("CONNECTION_ALREADY_BOUND", result["trace"][0]["reason_code"])
        session = result["authoritative_state"]["sessions"][0]
        self.assertEqual(("c1", 1), (session["connection_id"], session["epoch"]))

    def test_rate_limit_survives_reconnect(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            self.event("move-1", 0, self.command("c1", 1)),
            self.event("move-2", 0, self.command("c2", 2)),
            {
                "event_id": "reconnect",
                "kind": "RECONNECT",
                "logical_time": 1,
                "session_id": "s1",
                "new_connection_id": "c9",
                "session_epoch": 2,
            },
            self.event(
                "move-3",
                1,
                self.command(
                    "c3",
                    3,
                    connection_id="c9",
                    session_epoch=2,
                ),
            ),
        ]
        result = run_scenario(scenario)
        self.assertEqual("RATE_LIMITED", result["trace"][-1]["reason_code"])
        self.assertEqual(2, result["authoritative_state"]["players"][0]["x"])

    def test_alert_set_is_stable_under_order_and_duplicate_changes(self) -> None:
        commands = [
            self.event(
                "a",
                0,
                self.command("bad-a", 1, kind="SET_SCORE", payload={"score": 99}),
            ),
            self.event(
                "b",
                0,
                self.command("bad-b", 1, kind="SET_SCORE", payload={"score": 100}),
            ),
        ]
        first = self.base()
        first["events"] = commands + [copy.deepcopy(commands[0]) | {"event_id": "dup"}]
        second = self.base()
        second["events"] = list(reversed(commands))
        self.assertEqual(run_scenario(first)["alerts"], run_scenario(second)["alerts"])
        self.assertEqual(1, len(run_scenario(first)["alerts"]))

    def test_audit_redacts_token_and_payload_body(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            self.event(
                "e1",
                0,
                self.command("c1", 1, payload={"dx": 1, "dy": 0, "secret": "hidden"}),
            )
        ]
        encoded = json.dumps(run_scenario(scenario)["audit_events"], sort_keys=True)
        self.assertNotIn("do-not-log-this-token", encoded)
        self.assertNotIn("hidden", encoded)
        self.assertIn("payload_digest", encoded)

    def test_reason_codes_are_release_independent(self) -> None:
        reasons = []
        for release in ("r1", "r2"):
            scenario = self.base(release)
            scenario["events"] = [
                self.event(
                    "e1",
                    0,
                    self.command("c1", 1, kind="SET_SCORE", payload={"score": 99}),
                )
            ]
            reasons.append(run_scenario(scenario)["trace"][0]["reason_code"])
        self.assertEqual(["CLIENT_AUTHORITY_VIOLATION"] * 2, reasons)


if __name__ == "__main__":
    unittest.main()
