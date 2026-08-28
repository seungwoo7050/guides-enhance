#!/usr/bin/env python3
"""표준 입력의 정수를 오름차순으로 정렬해 한 줄에 하나씩 출력합니다."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        values = [int(token) for token in sys.stdin.read().split()]
    except ValueError as error:
        print(f"invalid integer input: {error}", file=sys.stderr)
        return 2
    if values:
        sys.stdout.write("\n".join(str(value) for value in sorted(values)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
