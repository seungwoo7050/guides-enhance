"""입력 검증 이후 사용하는 불변 값을 정의합니다."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class DataReportError(ValueError):
    """입력 파일이 data-report의 입력 규칙을 만족하지 않을 때 발생합니다."""


# [Implementation 2] Store validated records and aggregate results as immutable values.
@dataclass(frozen=True, slots=True)
class Record:
    category: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class CategoryTotal:
    category: str
    count: int
    total: Decimal


@dataclass(frozen=True, slots=True)
class Report:
    rows: tuple[CategoryTotal, ...]
    count: int
    total: Decimal
