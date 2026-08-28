"""명령줄 인자를 읽고 사례 실행, 보고서 저장, 종료 상태를 처리합니다."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .model import ExecutionError, SpecificationError
from .reports import write_json_report, write_junit_report
from .runner import exit_status, print_results, run_cases, validate_executable
from .specification import load_cases


# [Implementation 10] Localize argparse help and usage errors.
class CommandCheckerArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


# [Implementation 10-1] Define public arguments and the target-command separator.
def build_parser() -> argparse.ArgumentParser:
    parser = CommandCheckerArgumentParser(
        prog="command-checker",
        description="Validate a command-line program against JSON case contracts.",
    )
    parser.add_argument("--cases", required=True, type=Path, help="JSON case file")
    parser.add_argument("--jobs", type=int, default=1, help="number of cases to run concurrently")
    parser.add_argument("--json-report", type=Path, help="write a JSON report to PATH")
    parser.add_argument("--junit-report", type=Path, help="write a JUnit XML report to PATH")
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="target command written after --",
    )
    return parser


# [Implementation 10-2] Remove the separator and reject invalid jobs or commands.
def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command and arguments.command[0] == "--":
        arguments.command = arguments.command[1:]
    if not arguments.command:
        parser.error("provide a command after --")
    if arguments.jobs < 1:
        parser.error("--jobs must be at least 1")
    return arguments


# [Implementation 10-3] Run cases, write reports, and map failures to exit status.
def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)

    try:
        cases = load_cases(arguments.cases)
        executable = validate_executable(arguments.command[0])
        command = (executable, *arguments.command[1:])
        results = run_cases(cases, command, arguments.jobs)
    except (SpecificationError, ExecutionError) as error:
        print(error, file=sys.stderr)
        return 2

    print_results(results, stdout=sys.stdout, stderr=sys.stderr)

    try:
        if arguments.json_report is not None:
            write_json_report(arguments.json_report, results)
        if arguments.junit_report is not None:
            write_junit_report(arguments.junit_report, results)
    except OSError as error:
        print(f"cannot write report: {error}", file=sys.stderr)
        return 2

    passed = sum(result.passed for result in results)
    failed = len(results) - passed
    print(f"Summary: {passed} passed, {failed} failed")
    return exit_status(results)
