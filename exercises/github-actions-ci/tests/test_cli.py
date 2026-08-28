from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "src" / "change_record.py"


# [Implementation 5]
# CLI exit status and error output tests
class ChangeRecordCliTests(unittest.TestCase):
    # 함수를 직접 호출하지 않고 별도 프로세스로 실행합니다.
    # 실제 CLI의 종료 상태와 표준 출력·오류 사용을 함께 검증합니다.
    def run_program(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PROGRAM), *arguments],
            text=True,
            capture_output=True,
            check=False,
        )

    def write_json(self, directory: Path, value: object) -> Path:
        path = directory / "record.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_valid_record_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            path = self.write_json(
                Path(directory_name),
                {
                    "title": "Add CI checks",
                    "summary": "Run the same verification locally and in CI.",
                    "checks": ["./scripts/check.sh"],
                },
            )
            result = self.run_program(str(path))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, "valid change record: Add CI checks\n")

    def test_invalid_record_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            path = self.write_json(Path(directory_name), {"title": "Incomplete"})
            result = self.run_program(str(path))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("missing required field", result.stderr)

    def test_malformed_json_reports_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / "record.json"
            path.write_text('{"title":', encoding="utf-8")
            result = self.run_program(str(path))

        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid JSON at line", result.stderr)

    def test_missing_file_returns_two(self) -> None:
        result = self.run_program("does-not-exist.json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot read", result.stderr)

    def test_wrong_argument_count_returns_two(self) -> None:
        result = self.run_program()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stderr,
            "usage: change_record.py RECORD.json\n",
        )
