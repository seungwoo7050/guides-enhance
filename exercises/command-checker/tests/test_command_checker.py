"""command-checker의 입력 검증, 프로세스 수명, 보고서, CLI를 검사합니다."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from command_checker.model import Case, Result, SpecificationError
from command_checker.process import run_case
from command_checker.reports import render_json, render_junit
from command_checker.runner import run_cases
from command_checker.specification import load_cases

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).with_name("fixture_program.py")


# [Implementation 11] Verify specification, process, ordering, reports, and CLI behavior.
class CommandCheckerTests(unittest.TestCase):
    def write_cases(self, directory: Path, payload: object) -> Path:
        path = directory / "cases.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_load_cases_validates_and_resolves_relative_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = root / "work"
            work.mkdir()
            path = self.write_cases(
                root,
                [
                    {
                        "name": "contract",
                        "args": ["a", "b"],
                        "timeout": 0.5,
                        "cwd": "work",
                        "env": {"B": "2", "A": "1"},
                        "output_limit": 100,
                    }
                ],
            )
            cases = load_cases(path)
            self.assertEqual(cases[0].cwd, work.resolve())
            self.assertEqual(cases[0].env, (("A", "1"), ("B", "2")))

            self.write_cases(root, [{"name": "x", "unknown": True}])
            with self.assertRaises(SpecificationError):
                load_cases(path)

    def test_run_case_preserves_arguments_streams_environment_and_status(self) -> None:
        case = Case(
            name="channels",
            args=("channels",),
            stdout="out",
            stderr="err",
            returncode=7,
            env=(("OUT", "out"), ("ERR", "err"), ("CODE", "7")),
        )
        result = run_case(case, (sys.executable, str(FIXTURE)))
        self.assertTrue(result.passed)
        self.assertEqual(result.returncode, 7)

    def test_timeout_and_output_limit_are_distinct_lifecycle_failures(self) -> None:
        # 타임아웃과 출력 상한을 같은 실패로 처리하는 구현을 검출합니다.
        timeout_result = run_case(
            Case(name="timeout", args=("sleep", "2"), timeout=0.1),
            (sys.executable, str(FIXTURE)),
        )
        self.assertFalse(timeout_result.passed)
        self.assertTrue(timeout_result.timed_out)
        self.assertIn("timeout:", timeout_result.failures[0])

        output_result = run_case(
            Case(name="limit", args=("flood", "stdout", "8192"), output_limit=1024),
            (sys.executable, str(FIXTURE)),
        )
        self.assertFalse(output_result.passed)
        self.assertEqual(output_result.exceeded_stream, "stdout")
        self.assertEqual(len(output_result.stdout.encode()), 1024)

    def test_parallel_execution_preserves_input_order(self) -> None:
        # 먼저 끝난 사례와 관계없이 JSON 입력 순서를 유지하는지 검증합니다.
        cases = (
            Case(name="slow", args=("delay", "0.15", "slow"), stdout="slow\n"),
            Case(name="fast", args=("delay", "0.01", "fast"), stdout="fast\n"),
        )
        results = run_cases(cases, (sys.executable, str(FIXTURE)), jobs=2)
        self.assertEqual([result.name for result in results], ["slow", "fast"])
        self.assertTrue(all(result.passed for result in results))

    def test_reports_share_results_and_sanitize_xml(self) -> None:
        # 두 보고서가 같은 결과를 사용하고
        # XML에서 허용하지 않는 문자를 제거하는지 확인합니다.
        results = (
            Result(
                name="control\x01name",
                passed=False,
                duration_ms=12,
                failures=("bad\x01value",),
                returncode=1,
                stdout="ok\x01bad\n",
                stderr="",
            ),
        )
        payload = json.loads(render_json(results))
        self.assertEqual(payload["failed"], 1)
        xml = render_junit(results)
        self.assertNotIn("\x01", xml)
        suite = ET.fromstring(xml)
        self.assertEqual(suite.attrib["failures"], "1")

    def test_cli_example_and_reports_work_end_to_end(self) -> None:
        # 모듈 진입점, 예제 실행, 두 보고서 저장이 함께 동작하는지 검증합니다.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            json_report = root / "report.json"
            junit_report = root / "report.xml"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "command_checker",
                    "--cases",
                    str(ROOT / "examples" / "sort_cases.json"),
                    "--jobs",
                    "2",
                    "--json-report",
                    str(json_report),
                    "--junit-report",
                    str(junit_report),
                    "--",
                    sys.executable,
                    str(ROOT / "examples" / "line_sort.py"),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("PASS ascending", completed.stdout)
            self.assertIn("Summary: 2 passed, 0 failed", completed.stdout)
            self.assertEqual(completed.stderr, "")
            self.assertEqual(json.loads(json_report.read_text())["passed"], 2)
            self.assertEqual(ET.parse(junit_report).getroot().attrib["failures"], "0")

    @unittest.skipUnless(os.name == "posix", "process-group lifecycle requires POSIX")
    def test_timeout_terminates_spawned_process_group(self) -> None:
        # 자식 프로세스를 만든 뒤 타임아웃 정리 경로가 그룹 전체를 종료하는지 검증합니다.
        with tempfile.TemporaryDirectory() as temporary:
            pid_file = Path(temporary) / "child.pid"
            result = run_case(
                Case(
                    name="group-timeout",
                    args=("spawn-child",),
                    timeout=2.0,
                    env=(("CHILD_PID_FILE", str(pid_file)),),
                ),
                (sys.executable, str(FIXTURE)),
            )
            self.assertTrue(result.timed_out)
            self.assertTrue(pid_file.exists())


if __name__ == "__main__":
    unittest.main()
