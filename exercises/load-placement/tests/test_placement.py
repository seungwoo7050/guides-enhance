from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from load_placement.engine import run_scenario  # noqa: E402


# [Implementation 10]
# Capacity, queue, and drain regression tests
# stale 서버 선택, 중복 예약, 무제한 대기, drain 중 신규 배치를 검출합니다.
class LoadPlacementTests(unittest.TestCase):
    def base(self) -> dict:
        return {
            "policy": {
                "stale_after": 10,
                "max_queue_size": 2,
                "soft_headroom": {
                    "rooms": 0,
                    "players": 1,
                    "tick_cost": 5,
                    "outbound_bytes": 10,
                    "memory": 10,
                },
            },
            "servers": [
                self.server("s1", region="kr", players=0, tick=0),
                self.server("s2", region="jp", players=5, tick=20),
            ],
            "events": [],
        }

    @staticmethod
    def server(
        server_id: str,
        *,
        region: str,
        state: str = "ACTIVE",
        protocols: list[str] | None = None,
        players: int = 0,
        tick: int = 0,
        heartbeat: int = 0,
    ) -> dict:
        return {
            "server_id": server_id,
            "release_id": "r1",
            "protocol_versions": protocols or ["v1"],
            "region": region,
            "state": state,
            "room_count": 0,
            "player_count": players,
            "tick_cost_used": tick,
            "outbound_bytes_used": 0,
            "memory_used": 0,
            "last_heartbeat": heartbeat,
            "limits": {
                "max_rooms": 10,
                "max_players": 10,
                "max_tick_cost": 100,
                "max_outbound_bytes": 1000,
                "max_memory": 1000,
            },
        }

    @staticmethod
    def request(
        request_id: str,
        *,
        created: int = 0,
        deadline: int = 20,
        **overrides: object,
    ) -> dict:
        request = {
            "request_id": request_id,
            "required_protocol_version": "v1",
            "region_preferences": ["kr", "jp"],
            "expected_players": 2,
            "estimated_tick_cost": 10,
            "estimated_bandwidth": 100,
            "estimated_memory": 50,
            "created_at": created,
            "deadline": deadline,
        }
        request.update(overrides)
        return request

    @staticmethod
    def event(event_id: str, kind: str, logical_time: int, **values: object) -> dict:
        return {"event_id": event_id, "kind": kind, "logical_time": logical_time, **values}

    def test_normal_request_is_placed(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            self.event("e1", "REQUEST", 0, request=self.request("req-1"))
        ]
        result = run_scenario(scenario)
        self.assertEqual("PLACED", result["decisions"][0]["status"])
        self.assertEqual("s1", result["decisions"][0]["server_id"])

    def test_region_preference_precedes_headroom(self) -> None:
        scenario = self.base()
        scenario["servers"][0]["player_count"] = 7
        scenario["events"] = [
            self.event("e1", "REQUEST", 0, request=self.request("req-1"))
        ]
        result = run_scenario(scenario)
        self.assertEqual("s1", result["decisions"][0]["server_id"])

    def test_larger_headroom_breaks_same_region_tie(self) -> None:
        scenario = self.base()
        scenario["servers"][1]["region"] = "kr"
        scenario["events"] = [
            self.event("e1", "REQUEST", 0, request=self.request("req-1"))
        ]
        result = run_scenario(scenario)
        self.assertEqual("s1", result["decisions"][0]["server_id"])

    def test_protocol_mismatch_draining_and_stale_servers_are_excluded(self) -> None:
        protocol = self.base()
        protocol["servers"] = [self.server("s1", region="kr", protocols=["v2"])]
        protocol["events"] = [
            self.event("e1", "REQUEST", 0, request=self.request("req-1", deadline=0))
        ]
        self.assertEqual(
            "PROTOCOL_UNSUPPORTED",
            run_scenario(protocol)["decisions"][0]["reason_code"],
        )

        draining = self.base()
        draining["servers"] = [self.server("s1", region="kr", state="DRAINING")]
        draining["events"] = [
            self.event("e1", "REQUEST", 0, request=self.request("req-1", deadline=0))
        ]
        self.assertEqual("NO_HEALTHY_SERVER", run_scenario(draining)["decisions"][0]["reason_code"])

        stale = self.base()
        stale["servers"] = [self.server("s1", region="kr", heartbeat=0)]
        stale["events"] = [
            self.event("e1", "REQUEST", 20, request=self.request("req-1", deadline=20))
        ]
        self.assertEqual("NO_HEALTHY_SERVER", run_scenario(stale)["decisions"][0]["reason_code"])

    def test_future_heartbeat_is_not_treated_as_healthy(self) -> None:
        scenario = self.base()
        scenario["servers"] = [self.server("s1", region="kr", heartbeat=10)]
        scenario["events"] = [
            self.event("e1", "REQUEST", 0, request=self.request("req-1", deadline=0))
        ]
        result = run_scenario(scenario)
        self.assertEqual("NO_HEALTHY_SERVER", result["decisions"][0]["reason_code"])

    def test_request_before_created_at_is_rejected_without_claiming_id(self) -> None:
        scenario = self.base()
        request = self.request("req-1", created=5, deadline=20)
        scenario["events"] = [
            self.event("early", "REQUEST", 0, request=copy.deepcopy(request)),
            self.event("on-time", "REQUEST", 5, request=copy.deepcopy(request)),
        ]
        result = run_scenario(scenario)
        self.assertEqual("REQUEST_NOT_CREATED", result["trace"][0]["reason_code"])
        self.assertEqual("PLACED", result["trace"][1]["reason_code"])
        self.assertEqual(1, len(result["active_reservations"]))

    def test_tick_capacity_can_reject_when_player_capacity_remains(self) -> None:
        scenario = self.base()
        scenario["servers"] = [self.server("s1", region="kr", players=0, tick=95)]
        scenario["events"] = [
            self.event("e1", "REQUEST", 0, request=self.request("req-1", deadline=0))
        ]
        result = run_scenario(scenario)
        self.assertEqual("HARD_CAPACITY_EXCEEDED", result["decisions"][0]["reason_code"])

    def test_queue_is_bounded_and_deadline_expires(self) -> None:
        scenario = self.base()
        scenario["servers"] = [self.server("s1", region="kr", state="UNAVAILABLE")]
        scenario["events"] = [
            self.event("r1", "REQUEST", 0, request=self.request("req-1", deadline=2)),
            self.event("r2", "REQUEST", 0, request=self.request("req-2", deadline=5)),
            self.event("r3", "REQUEST", 0, request=self.request("req-3", deadline=5)),
            self.event("time", "ADVANCE_TIME", 3),
        ]
        result = run_scenario(scenario)
        decisions = {item["request_id"]: item for item in result["decisions"]}
        self.assertEqual("QUEUE_FULL", decisions["req-3"]["reason_code"])
        self.assertEqual("DEADLINE_EXPIRED", decisions["req-1"]["reason_code"])
        self.assertEqual(["req-2"], result["queue"])

    def test_duplicate_request_does_not_consume_capacity_twice(self) -> None:
        scenario = self.base()
        request = self.request("req-1")
        scenario["events"] = [
            self.event("e1", "REQUEST", 0, request=request),
            self.event("e2", "REQUEST", 1, request=copy.deepcopy(request)),
        ]
        result = run_scenario(scenario)
        server = next(item for item in result["servers"] if item["server_id"] == "s1")
        self.assertEqual(1, server["room_count"])
        self.assertEqual("DUPLICATE_REQUEST", result["trace"][-1]["reason_code"])

    def test_reservation_is_visible_to_next_request(self) -> None:
        scenario = self.base()
        scenario["servers"][0]["limits"]["max_players"] = 3
        scenario["events"] = [
            self.event("e1", "REQUEST", 0, request=self.request("req-1")),
            self.event("e2", "REQUEST", 0, request=self.request("req-2")),
        ]
        result = run_scenario(scenario)
        decisions = {item["request_id"]: item for item in result["decisions"]}
        self.assertEqual("s1", decisions["req-1"]["server_id"])
        self.assertEqual("s2", decisions["req-2"]["server_id"])

    def test_drain_keeps_existing_match_and_completes_after_release(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            self.event("request", "REQUEST", 0, request=self.request("req-1")),
            self.event("drain", "BEGIN_DRAIN", 1, server_id="s1"),
            self.event("complete", "COMPLETE_MATCH", 2, request_id="req-1"),
        ]
        result = run_scenario(scenario)
        self.assertEqual("DRAIN_COMPLETE", result["trace"][-1]["drain_result"])
        server = next(item for item in result["servers"] if item["server_id"] == "s1")
        self.assertEqual(0, server["room_count"])
        self.assertTrue(server["drain_complete"])

    def test_heartbeat_can_make_queued_request_placeable(self) -> None:
        scenario = self.base()
        scenario["servers"] = [self.server("s1", region="kr", heartbeat=0)]
        scenario["events"] = [
            self.event(
                "request",
                "REQUEST",
                20,
                request=self.request("req-1", created=20, deadline=30),
            ),
            self.event("heartbeat", "HEARTBEAT", 21, server_id="s1", state="ACTIVE"),
        ]
        result = run_scenario(scenario)
        self.assertEqual("PLACED", result["decisions"][0]["status"])
        self.assertEqual([], result["queue"])


if __name__ == "__main__":
    unittest.main()
