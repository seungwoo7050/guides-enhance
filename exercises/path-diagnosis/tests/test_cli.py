"""CLI 출력 형식과 종료 상태를 검증합니다."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


class CliTests(unittest.TestCase):
    def test_healthy_text_returns_zero(self) -> None:
        result = self._run(FIXTURES / "healthy.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("code: HEALTHY", result.stdout)
        self.assertIn("healthy: yes", result.stdout)

    def test_failure_json_returns_one_and_machine_readable_output(self) -> None:
        result = self._run(FIXTURES / "mtu-black-hole.json", "--format", "json")
        self.assertEqual(result.returncode, 1, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["code"], "MTU_BLACK_HOLE")
        self.assertEqual(value["last_success"], "neighbor")
        self.assertEqual(value["first_failure"], "path")
        self.assertFalse(value["healthy"])

    def test_invalid_input_returns_two_without_traceback(self) -> None:
        # 잘못된 파일은 내부 traceback을 노출하지 않고 입력 오류 종료 상태로 끝나야 합니다.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("not-json", encoding="utf-8")
            result = self._run(path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("input error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    @staticmethod
    def _run(path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        command = [sys.executable, "-m", "path_diagnosis", str(path), *arguments]
        return subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )


if __name__ == "__main__":
    unittest.main()
