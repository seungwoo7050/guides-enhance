"""정상 JSON scenario의 공개 출력값과 종료 상태를 검증합니다."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "kernel-model.py"
EXAMPLES = ROOT / "examples"
SCENARIOS = (
    ("lifecycle", "lifecycle.json"),
    ("schedule", "schedule.json"),
    ("condition", "condition.json"),
    ("deadlock", "deadlock-cycle.json"),
    ("deadlock", "deadlock-safe.json"),
    ("memory", "memory-cow.json"),
    ("replacement", "replacement.json"),
    ("filesystem", "filesystem-crash.json"),
    ("io", "device-io.json"),
)


def assert_subset(test: unittest.TestCase, actual: Any, expected: Any) -> None:
    if isinstance(expected, Mapping):
        test.assertIsInstance(actual, Mapping)
        for key, value in expected.items():
            test.assertIn(key, actual)
            assert_subset(test, actual[key], value)
        return
    test.assertEqual(actual, expected)


# [Implementation 10-1] 정상 scenario의 관찰값 검증
# 내부 object 전체가 아니라 example이 선언한 공개 항목만 비교합니다.
class ScenarioContractTests(unittest.TestCase):
    def test_examples_match_declared_observations(self) -> None:
        for model, filename in SCENARIOS:
            fixture = EXAMPLES / filename
            data = json.loads(fixture.read_text(encoding="utf-8"))
            expected = data["expected"]
            with self.subTest(model=model, fixture=filename):
                result = subprocess.run(
                    [sys.executable, str(ENTRYPOINT), model, str(fixture)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                assert_subset(self, json.loads(result.stdout), expected)

    def test_invalid_operation_has_no_traceback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kernel-model-cli-") as temporary:
            fixture = Path(temporary) / "invalid.json"
            fixture.write_text(
                '{"operations":[{"op":"unknown"}]}\n',
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(ENTRYPOINT), "lifecycle", str(fixture)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Model execution failed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_malformed_json_has_no_traceback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kernel-model-json-") as temporary:
            fixture = Path(temporary) / "malformed.json"
            fixture.write_text("{", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ENTRYPOINT), "lifecycle", str(fixture)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Model execution failed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
