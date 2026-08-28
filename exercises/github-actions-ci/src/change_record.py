#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {"title", "summary", "checks"}
MAX_TITLE_LENGTH = 72


class RecordValidationError(ValueError):
    pass


# [Implementation 1]
# Change record validation and CLI result

def validate_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RecordValidationError("record must be a JSON object")

    fields = set(value)
    missing = sorted(REQUIRED_FIELDS - fields)
    if missing:
        raise RecordValidationError(
            f"missing required field(s): {', '.join(missing)}"
        )

    unknown = sorted(fields - REQUIRED_FIELDS)
    if unknown:
        raise RecordValidationError(f"unknown field(s): {', '.join(unknown)}")

    title = value["title"]
    if not isinstance(title, str) or not title.strip():
        raise RecordValidationError("title must be a non-empty string")
    if len(title) > MAX_TITLE_LENGTH:
        raise RecordValidationError(
            f"title must be at most {MAX_TITLE_LENGTH} characters"
        )

    summary = value["summary"]
    if not isinstance(summary, str) or not summary.strip():
        raise RecordValidationError("summary must be a non-empty string")

    checks = value["checks"]
    if not isinstance(checks, list) or not checks:
        raise RecordValidationError("checks must be a non-empty array")
    if any(not isinstance(check, str) or not check.strip() for check in checks):
        raise RecordValidationError("every check must be a non-empty string")

    return {
        "title": title.strip(),
        "summary": summary.strip(),
        "checks": [check.strip() for check in checks],
    }


def load_record(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as file:
            value = json.load(file)
    except OSError as error:
        raise RecordValidationError(f"cannot read {path}: {error.strerror}") from error
    except json.JSONDecodeError as error:
        raise RecordValidationError(
            f"invalid JSON at line {error.lineno}, column {error.colno}"
        ) from error

    return validate_record(value)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: change_record.py RECORD.json", file=sys.stderr)
        return 2

    try:
        record = load_record(Path(args[0]))
    except RecordValidationError as error:
        print(f"invalid change record: {error}", file=sys.stderr)
        return 2

    print(f"valid change record: {record['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
