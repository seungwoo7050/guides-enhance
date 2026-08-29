from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .engine import run_scenario


# [Implementation 9]
# Scenario file execution and exit status
# 입력 파일과 복제 규칙 오류를 stderr에 쓰고 종료 상태 2로 반환합니다.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="replication-reconnect",
        description="Run a deterministic snapshot, delta, and reconnect scenario.",
    )
    parser.add_argument("scenario", type=Path, help="JSON scenario file")
    parser.add_argument("--pretty", action="store_true", help="indent the JSON result")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with args.scenario.open("r", encoding="utf-8") as source:
            scenario = json.load(source)
        result = run_scenario(scenario)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(f"replication-reconnect: {error}", file=sys.stderr)
        return 2
    json.dump(
        result,
        sys.stdout,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2 if args.pretty else None,
        separators=None if args.pretty else (",", ":"),
    )
    sys.stdout.write("\n")
    return 0
