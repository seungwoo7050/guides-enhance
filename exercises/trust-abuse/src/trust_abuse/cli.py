from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .engine import run_scenario


# [Implementation 12]
# Scenario file execution and exit status
# 파일, JSON, 입력 검증 오류를 stderr에 쓰고 종료 상태 2를 반환합니다.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trust-abuse",
        description=(
            "Run authoritative command validation, rate limiting, audit, "
            "and alert scenarios."
        ),
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
        print(f"trust-abuse: {error}", file=sys.stderr)
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
