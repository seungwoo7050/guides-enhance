from __future__ import annotations

import copy
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from replication_reconnect.engine import run_scenario  # noqa: E402


# [Implementation 10]
# Replication loss, reorder, and queue regression tests
# baseline 무시, 무제한 보류, 부분 resume, 느린 클라이언트 큐 증가를 검출합니다.
class ReplicationReconnectTests(unittest.TestCase):
    def base(self) -> dict:
        return {
            "config": {
                "match_id": "m1",
                "protocol_version": 1,
                "schema_version": 1,
                "max_pending_deltas": 3,
                "max_gap": 3,
                "max_snapshot_bytes": 4096,
                "max_send_queue_bytes": 700,
            },
            "server": {
                "current_version": 3,
                "current_state": {"score": 2, "players": {"p1": {"x": 2}}},
                "history": [
                    self.delta("h2", 1, [("INCREMENT", ["score"], 1)]),
                    self.delta("h3", 2, [("SET", ["players", "p1", "x"], 2)]),
                ],
            },
            "clients": [
                {"client_id": "c1", "state_version": 0, "state": {}, "connected": True}
            ],
            "events": [],
        }

    @staticmethod
    def snapshot(message_id: str, version: int, state: dict, **overrides: object) -> dict:
        message = {
            "message_id": message_id,
            "kind": "SNAPSHOT",
            "match_id": "m1",
            "protocol_version": 1,
            "schema_version": 1,
            "version": version,
            "state": state,
        }
        message.update(overrides)
        return message

    @staticmethod
    def delta(
        message_id: str,
        baseline: int,
        operations: list[tuple[str, list[str], object]],
        **overrides: object,
    ) -> dict:
        normalized = []
        for op, path, value in operations:
            item = {"op": op, "path": path}
            if op != "DELETE":
                item["value"] = value
            normalized.append(item)
        message = {
            "message_id": message_id,
            "kind": "DELTA",
            "match_id": "m1",
            "protocol_version": 1,
            "schema_version": 1,
            "baseline_version": baseline,
            "version": baseline + 1,
            "operations": normalized,
        }
        message.update(overrides)
        return message

    @staticmethod
    def event(event_id: str, kind: str, **values: object) -> dict:
        return {"event_id": event_id, "kind": kind, "client_id": "c1", **values}

    def test_snapshot_then_delta_converges(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            self.event("e1", "DELIVER", message=self.snapshot("s1", 1, {"score": 0})),
            self.event(
                "e2",
                "DELIVER",
                message=self.delta("d2", 1, [("INCREMENT", ["score"], 2)]),
            ),
        ]
        result = run_scenario(scenario)
        client = result["clients"][0]
        self.assertEqual((2, 2), (client["state_version"], client["state"]["score"]))

    def test_duplicate_delta_is_idempotent(self) -> None:
        scenario = self.base()
        delta = self.delta("d2", 1, [("INCREMENT", ["score"], 1)])
        scenario["clients"][0].update({"state_version": 1, "state": {"score": 0}})
        scenario["events"] = [
            self.event("e1", "DELIVER", message=delta),
            self.event("e2", "DELIVER", message=copy.deepcopy(delta)),
        ]
        result = run_scenario(scenario)
        self.assertEqual(1, result["clients"][0]["state"]["score"])
        self.assertEqual("DUPLICATE_OR_STALE_DELTA", result["trace"][-1]["reason_code"])

    def test_out_of_order_delta_is_buffered_then_replayed(self) -> None:
        scenario = self.base()
        scenario["clients"][0].update({"state_version": 1, "state": {"score": 0}})
        scenario["events"] = [
            self.event(
                "future",
                "DELIVER",
                message=self.delta("d3", 2, [("INCREMENT", ["score"], 1)]),
            ),
            self.event(
                "missing",
                "DELIVER",
                message=self.delta("d2", 1, [("INCREMENT", ["score"], 1)]),
            ),
        ]
        result = run_scenario(scenario)
        self.assertEqual("FUTURE_DELTA_BUFFERED", result["trace"][0]["reason_code"])
        self.assertEqual(["d3"], result["trace"][1]["replayed_message_ids"])
        self.assertEqual(
            (3, 2),
            (
                result["clients"][0]["state_version"],
                result["clients"][0]["state"]["score"],
            ),
        )

    def test_conflicting_pending_delta_requests_resync(self) -> None:
        scenario = self.base()
        scenario["clients"][0].update({"state_version": 1, "state": {"score": 0}})
        scenario["events"] = [
            self.event(
                "future-a",
                "DELIVER",
                message=self.delta("d3-a", 2, [("SET", ["score"], 2)]),
            ),
            self.event(
                "future-b",
                "DELIVER",
                message=self.delta("d3-b", 2, [("SET", ["score"], 3)]),
            ),
        ]
        result = run_scenario(scenario)
        self.assertEqual("CONFLICTING_PENDING_DELTA", result["trace"][-1]["reason_code"])
        self.assertTrue(result["clients"][0]["resync_requested"])
        self.assertEqual([], result["clients"][0]["pending_versions"])

    def test_gap_limit_requests_resync(self) -> None:
        scenario = self.base()
        scenario["config"]["max_gap"] = 1
        scenario["server"]["current_version"] = 4
        scenario["events"] = [
            self.event(
                "gap",
                "DELIVER",
                message=self.delta("d4", 3, [("SET", ["score"], 5)]),
            )
        ]
        result = run_scenario(scenario)
        self.assertEqual("GAP_LIMIT_EXCEEDED", result["trace"][0]["reason_code"])
        self.assertTrue(result["clients"][0]["resync_requested"])

    def test_stale_snapshot_and_wrong_identity_are_rejected(self) -> None:
        scenario = self.base()
        scenario["clients"][0].update({"state_version": 2, "state": {"score": 2}})
        scenario["events"] = [
            self.event("old", "DELIVER", message=self.snapshot("s1", 1, {"score": 0})),
            self.event(
                "wrong",
                "DELIVER",
                message=self.snapshot("s2", 3, {"score": 3}, match_id="other"),
            ),
        ]
        result = run_scenario(scenario)
        self.assertEqual("STALE_SNAPSHOT", result["trace"][0]["reason_code"])
        self.assertEqual("MATCH_MISMATCH", result["trace"][1]["reason_code"])

    def test_same_version_conflicting_snapshot_requests_resync(self) -> None:
        scenario = self.base()
        scenario["clients"][0].update({"state_version": 2, "state": {"score": 2}})
        scenario["events"] = [
            self.event(
                "conflict",
                "DELIVER",
                message=self.snapshot("s2", 2, {"score": 999}),
            )
        ]
        result = run_scenario(scenario)
        self.assertEqual("SNAPSHOT_VERSION_CONFLICT", result["trace"][0]["reason_code"])
        self.assertEqual({"score": 2}, result["clients"][0]["state"])
        self.assertTrue(result["clients"][0]["resync_requested"])

    def test_message_beyond_server_version_is_rejected(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            self.event(
                "future",
                "DELIVER",
                message=self.snapshot("s4", 4, {"score": 4}),
            )
        ]
        result = run_scenario(scenario)
        self.assertEqual("SERVER_VERSION_EXCEEDED", result["trace"][0]["reason_code"])
        self.assertEqual(0, result["clients"][0]["state_version"])

    def test_non_finite_snapshot_is_rejected_as_invalid_message(self) -> None:
        scenario = self.base()
        scenario["events"] = [
            self.event(
                "nan",
                "DELIVER",
                message=self.snapshot("nan-snapshot", 1, {"score": math.nan}),
            )
        ]
        result = run_scenario(scenario)
        self.assertEqual("INVALID_MESSAGE", result["trace"][0]["reason_code"])
        self.assertEqual(0, result["clients"][0]["state_version"])

    def test_reconnect_uses_contiguous_history(self) -> None:
        scenario = self.base()
        scenario["clients"][0].update(
            {
                "state_version": 1,
                "state": {"score": 1, "players": {"p1": {"x": 0}}},
                "connected": False,
            }
        )
        scenario["events"] = [
            self.event(
                "reconnect",
                "RECONNECT",
                token={
                    "match_id": "m1",
                    "protocol_version": 1,
                    "schema_version": 1,
                    "baseline_version": 1,
                },
            )
        ]
        result = run_scenario(scenario)
        client = result["clients"][0]
        self.assertEqual("DELTA_RESUME", client["reconnect_path"])
        self.assertEqual((3, 2), (client["state_version"], client["state"]["score"]))

    def test_reconnect_falls_back_to_full_snapshot_when_history_is_missing(self) -> None:
        scenario = self.base()
        scenario["server"]["history"] = []
        scenario["clients"][0].update(
            {"state_version": 1, "state": {"score": 0}, "connected": False}
        )
        scenario["events"] = [
            self.event(
                "reconnect",
                "RECONNECT",
                token={
                    "match_id": "m1",
                    "protocol_version": 1,
                    "schema_version": 1,
                    "baseline_version": 1,
                },
            )
        ]
        result = run_scenario(scenario)
        client = result["clients"][0]
        self.assertEqual("FULL_SNAPSHOT", client["reconnect_path"])
        self.assertEqual(scenario["server"]["current_state"], client["state"])

    def test_failed_reconnect_does_not_commit_partial_history(self) -> None:
        scenario = self.base()
        scenario["server"]["history"] = [
            self.delta("h2", 1, [("INCREMENT", ["score"], 1)])
        ]
        scenario["config"]["max_snapshot_bytes"] = 1
        scenario["clients"][0].update(
            {"state_version": 1, "state": {"score": 1}, "connected": False}
        )
        scenario["events"] = [
            self.event(
                "reconnect",
                "RECONNECT",
                token={
                    "match_id": "m1",
                    "protocol_version": 1,
                    "schema_version": 1,
                    "baseline_version": 1,
                },
            )
        ]
        result = run_scenario(scenario)
        client = result["clients"][0]
        self.assertEqual("FAILED", client["reconnect_path"])
        self.assertFalse(client["connected"])
        self.assertEqual((1, {"score": 1}), (client["state_version"], client["state"]))
        self.assertNotIn("h2", client["applied_message_ids"])

    def test_flush_preserves_fifo_order(self) -> None:
        scenario = self.base()
        scenario["config"]["max_send_queue_bytes"] = 1200
        scenario["events"] = [
            self.event(
                "q1",
                "ENQUEUE",
                message=self.snapshot("large", 1, {"payload": "x" * 240}),
            ),
            self.event(
                "q2",
                "ENQUEUE",
                message=self.snapshot("small", 1, {}),
            ),
            self.event("flush", "FLUSH", max_bytes=220),
        ]
        result = run_scenario(scenario)
        self.assertEqual([], result["trace"][-1]["sent_message_ids"])
        self.assertEqual(
            ["large", "small"],
            result["clients"][0]["outbound_message_ids"],
        )

    def test_slow_client_queue_compacts_to_snapshot(self) -> None:
        scenario = self.base()
        scenario["config"]["max_send_queue_bytes"] = 350
        large = self.snapshot("large", 1, {"payload": "x" * 180})
        scenario["events"] = [
            self.event("q1", "ENQUEUE", message=large),
            self.event("q2", "ENQUEUE", message=large | {"message_id": "large-2"}),
        ]
        result = run_scenario(scenario)
        self.assertEqual("COMPACTED_TO_SNAPSHOT", result["trace"][-1]["reason_code"])
        self.assertEqual(["queue-snapshot-c1"], result["clients"][0]["outbound_message_ids"])

    def test_uncompactable_queue_disconnects_client(self) -> None:
        scenario = self.base()
        scenario["config"].update({"max_send_queue_bytes": 120, "max_snapshot_bytes": 4096})
        scenario["events"] = [
            self.event("q1", "ENQUEUE", message=self.snapshot("large", 1, {"payload": "x" * 200}))
        ]
        result = run_scenario(scenario)
        self.assertEqual("SLOW_CLIENT_DISCONNECTED", result["trace"][-1]["reason_code"])
        self.assertFalse(result["clients"][0]["connected"])


if __name__ == "__main__":
    unittest.main()
