"""JSON 추적 기록을 읽어 텍스트 또는 JSON 진단 결과를 출력합니다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .diagnose import diagnose, render_text
from .model import TraceFormatError, load_trace


# [Implementation 3] CLI argument and output handling
# 명령행에서는 추적 기록 경로와 출력 형식만 받고 진단 판단은 별도 함수에 맡깁니다.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="path-diagnosis",
        description="Locate the first failed network layer and propose next checks.",
    )
    parser.add_argument("trace", type=Path, help="JSON trace to diagnose")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
        help="output format",
    )
    return parser


# [Implementation 3-1] Exit-status and input-error handling
# 정상은 0, 진단된 실패는 1, 입력 오류는 traceback을 노출하지 않고 2를 반환합니다.
def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        trace = load_trace(args.trace)
        result = diagnose(trace)
    except TraceFormatError as error:
        print(f"input error: {error}", file=sys.stderr)
        return 2

    if args.output_format == "json":
        print(json.dumps(result.to_mapping(), sort_keys=True))
    else:
        print(render_text(result))
    return 0 if result.healthy else 1
