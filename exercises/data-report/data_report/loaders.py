"""CSV와 JSON을 읽고 각 항목을 `Record`로 변환합니다."""

from __future__ import annotations

import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .model import DataReportError, Record

_FIELDS = {"category", "amount"}


def _category(value: Any, location: str) -> str:
    if not isinstance(value, str):
        raise DataReportError(f"{location}.category must be a string")
    category = value.strip()
    if not category:
        raise DataReportError(f"{location}.category must not be empty")
    return category


def _amount(value: Any, location: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise DataReportError(f"{location}.amount must be a decimal number")

    # CSV와 JSON의 숫자를 여기서 Decimal로 통일합니다.
    # 집계 코드가 입력 형식이나 `float` 표현 오차에 의존하지 않게 합니다.
    text = value if isinstance(value, str) else str(value)
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError):
        raise DataReportError(f"{location}.amount must be a decimal number") from None

    if not amount.is_finite():
        raise DataReportError(f"{location}.amount must be finite")
    return amount


def _record(raw: Any, location: str) -> Record:
    if not isinstance(raw, dict):
        raise DataReportError(f"{location} must be an object")

    unknown = sorted(set(raw) - _FIELDS)
    missing = sorted(_FIELDS - set(raw))
    if unknown:
        raise DataReportError(f"{location} has unknown fields: {', '.join(unknown)}")
    if missing:
        raise DataReportError(f"{location} is missing fields: {', '.join(missing)}")

    return Record(
        category=_category(raw["category"], location),
        amount=_amount(raw["amount"], location),
    )


# [Implementation 3] Validate CSV/JSON files and return Record values.
def load_records(path: Path) -> tuple[Record, ...]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        records = _load_csv(path)
    elif suffix == ".json":
        records = _load_json(path)
    else:
        raise DataReportError("input file must use .csv or .json")

    if not records:
        raise DataReportError("input must contain at least one record")
    return records


def _load_csv(path: Path) -> tuple[Record, ...]:
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None:
                raise DataReportError("CSV header is missing")
            if set(reader.fieldnames) != _FIELDS or len(reader.fieldnames) != len(_FIELDS):
                raise DataReportError("CSV header must contain exactly category,amount")

            records = [
                _record(dict(row), f"row {index}")
                for index, row in enumerate(reader, start=2)
            ]
    except OSError as error:
        raise DataReportError(f"cannot read input file: {error}") from error

    return tuple(records)


def _load_json(path: Path) -> tuple[Record, ...]:
    try:
        raw = json.loads(
            path.read_text(encoding="utf-8"),
            parse_float=str,
            parse_int=str,
        )
    except OSError as error:
        raise DataReportError(f"cannot read input file: {error}") from error
    except json.JSONDecodeError as error:
        raise DataReportError(
            f"invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error

    if not isinstance(raw, list):
        raise DataReportError("JSON root must be an array")

    return tuple(_record(item, f"items[{index}]") for index, item in enumerate(raw))
