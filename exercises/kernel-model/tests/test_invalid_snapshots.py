"""외부 JSON으로 만든 잘못된 snapshot이 거부되는지 검증합니다."""

from __future__ import annotations

import json
from pathlib import Path
import unittest
from typing import Any, Callable

from kernel_model.device_io import DeviceQueue
from kernel_model.filesystem import FileSystemModel
from kernel_model.journal import Journal
from kernel_model.lifecycle import KernelState
from kernel_model.paging import MemoryManager

ROOT = Path(__file__).resolve().parents[1]
INVALID_FIXTURES = ROOT / "tests" / "fixtures" / "invalid"
Validator = Callable[[Any], Any]


# [Implementation 10-2] 잘못된 snapshot 거부 검증
# 각 fixture가 다른 이유가 아니라
# 지정한 불변식 위반으로 거부되는지 확인합니다.
class InvalidSnapshotTests(unittest.TestCase):
    def test_invalid_snapshots_fail_for_declared_reason(self) -> None:
        validators: dict[str, Validator] = {
            "lifecycle": KernelState.validate_snapshot,
            "memory": MemoryManager.validate_snapshot,
            "device": DeviceQueue.validate_snapshot,
            "filesystem": FileSystemModel.validate_snapshot,
            "journal": Journal.from_snapshot,
        }
        paths = sorted(INVALID_FIXTURES.glob("*.json"))
        self.assertEqual(len(paths), 8)

        for path in paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            validator = validators[data["validator"]]
            with self.subTest(fixture=path.name):
                with self.assertRaises(
                    (KeyError, TypeError, ValueError, RuntimeError)
                ) as context:
                    validator(data["snapshot"])
                self.assertIn(data["expected_error"], str(context.exception))


if __name__ == "__main__":
    unittest.main()
