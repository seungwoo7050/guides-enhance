from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tick_command_model.engine import run_scenario  # noqa: E402


# [Implementation 9]
# Command ordering and limit regression tests
# 조기 sequence 갱신, 입력 순서 의존, 무제한 catch-up 구현을 검출합니다.
class TickCommandModelTests(unittest.TestCase):
    def base_scenario(self) -> dict:
        return {
            "config": {
                "match_id": "match-1",
                "tick_rate_hz": 20,
                "start_tick": 0,
                "advance_to_tick": 2,
                "max_commands_per_tick": 4,
                "max_catch_up_ticks": 2,
                "max_future_tick_distance": 4,
                "coordinate_limit": 10,
                "score_limit": 100,
            },
            "players": [
                {
                    "player_id": "p1",
                    "session_epoch": 2,
                    "last_sequence": 0,
                    "x": 0,
                    "y": 0,
                    "score": 0,
                },
                {
                    "player_id": "p2",
                    "session_epoch": 1,
                    "last_sequence": 0,
                    "x": 0,
                    "y": 0,
                    "score": 0,
                },
            ],
            "commands": [],
        }

    @staticmethod
    def command(
        command_id: str,
        player_id: str,
        sequence: int,
        received_order: int,
        *,
        epoch: int = 2,
        tick: int = 1,
        kind: str = "MOVE",
        payload: dict | None = None,
    ) -> dict:
        return {
            "command_id": command_id,
            "match_id": "match-1",
            "player_id": player_id,
            "session_epoch": epoch,
            "sequence": sequence,
            "target_tick": tick,
            "kind": kind,
            "payload": payload if payload is not None else {"dx": 1, "dy": 0},
            "received_order": received_order,
        }

    def test_normal_moves_for_two_players(self) -> None:
        scenario = self.base_scenario()
        scenario["commands"] = [
            self.command("c1", "p1", 1, 2),
            self.command("c2", "p2", 1, 1, epoch=1, payload={"dx": 0, "dy": 2}),
        ]
        result = run_scenario(scenario)
        self.assertEqual([1, 1], [player["last_sequence"] for player in result["players"]])
        self.assertEqual("APPLIED", result["decisions"][0]["status"])
        self.assertEqual("APPLIED", result["decisions"][1]["status"])

    def test_duplicate_and_stale_sequence_do_not_change_state(self) -> None:
        scenario = self.base_scenario()
        scenario["commands"] = [
            self.command("first", "p1", 1, 1),
            self.command("duplicate", "p1", 1, 2, payload={"dx": 9, "dy": 0}),
        ]
        result = run_scenario(scenario)
        p1 = next(player for player in result["players"] if player["player_id"] == "p1")
        self.assertEqual(1, p1["x"])
        decisions = {item["command_id"]: item for item in result["decisions"]}
        self.assertEqual("STALE_SEQUENCE", decisions["duplicate"]["reason_code"])

    def test_invalid_payload_does_not_consume_sequence(self) -> None:
        scenario = self.base_scenario()
        scenario["commands"] = [
            self.command("bad", "p1", 1, 1, payload={"dx": 1000, "dy": 0}),
            self.command("good", "p1", 1, 2, payload={"dx": 2, "dy": 0}),
        ]
        result = run_scenario(scenario)
        decisions = {item["command_id"]: item for item in result["decisions"]}
        self.assertEqual("RANGE_VIOLATION", decisions["bad"]["reason_code"])
        self.assertEqual("APPLIED", decisions["good"]["status"])
        p1 = next(player for player in result["players"] if player["player_id"] == "p1")
        self.assertEqual((2, 1), (p1["x"], p1["last_sequence"]))

    def test_sequence_gap_and_old_epoch_are_rejected(self) -> None:
        scenario = self.base_scenario()
        scenario["commands"] = [
            self.command("gap", "p1", 2, 1),
            self.command("old", "p1", 1, 2, epoch=1),
        ]
        result = run_scenario(scenario)
        decisions = {item["command_id"]: item for item in result["decisions"]}
        self.assertEqual("SEQUENCE_GAP", decisions["gap"]["reason_code"])
        self.assertEqual("SESSION_EPOCH_MISMATCH", decisions["old"]["reason_code"])

    def test_future_tick_and_per_tick_limit_are_bounded(self) -> None:
        scenario = self.base_scenario()
        scenario["config"]["max_commands_per_tick"] = 1
        scenario["commands"] = [
            self.command("a", "p1", 1, 1),
            self.command("b", "p2", 1, 2, epoch=1),
            self.command("far", "p1", 1, 3, tick=10),
        ]
        result = run_scenario(scenario)
        reasons = {item["command_id"]: item["reason_code"] for item in result["decisions"]}
        self.assertEqual("TICK_COMMAND_LIMIT", reasons["b"])
        self.assertEqual("FUTURE_TICK_LIMIT", reasons["far"])
        self.assertTrue(result["overloaded"])
        self.assertEqual(["TICK_COMMAND_LIMIT"], result["overload_reasons"])

    def test_catch_up_limit_leaves_pending_work(self) -> None:
        scenario = self.base_scenario()
        scenario["config"].update(
            {"advance_to_tick": 5, "max_catch_up_ticks": 2, "max_future_tick_distance": 8}
        )
        scenario["commands"] = [self.command("later", "p1", 1, 1, tick=4)]
        result = run_scenario(scenario)
        self.assertTrue(result["overloaded"])
        self.assertEqual(2, result["final_tick"])
        self.assertEqual([{"command_id": "later", "target_tick": 4}], result["pending_commands"])

    def test_rejected_command_order_is_also_deterministic(self) -> None:
        scenario = self.base_scenario()
        scenario["commands"] = [
            self.command("future", "p1", 1, 2, tick=10),
            self.command("stale", "p2", 1, 1, epoch=1, tick=0),
        ]
        reordered = copy.deepcopy(scenario)
        reordered["commands"].reverse()
        self.assertEqual(run_scenario(scenario), run_scenario(reordered))

    def test_input_list_order_does_not_change_result(self) -> None:
        scenario = self.base_scenario()
        scenario["commands"] = [
            self.command("p1", "p1", 1, 2),
            self.command("p2", "p2", 1, 1, epoch=1),
        ]
        reversed_scenario = copy.deepcopy(scenario)
        reversed_scenario["commands"].reverse()
        self.assertEqual(run_scenario(scenario), run_scenario(reversed_scenario))


if __name__ == "__main__":
    unittest.main()
