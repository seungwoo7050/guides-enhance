"""`Record`를 `category`별로 합산해 `Report`를 만듭니다."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from .model import CategoryTotal, Record, Report


# [Implementation 4] Aggregate records and sort category totals deterministically.
def aggregate(records: Iterable[Record]) -> Report:
    counts: dict[str, int] = defaultdict(int)
    totals: dict[str, Decimal] = defaultdict(Decimal)
    overall_count = 0
    overall_total = Decimal(0)

    for record in records:
        counts[record.category] += 1
        totals[record.category] += record.amount
        overall_count += 1
        overall_total += record.amount

    # `category`를 정렬해 레코드 순서와 무관한 결과를 만듭니다.
    rows = tuple(
        CategoryTotal(
            category=category,
            count=counts[category],
            total=totals[category],
        )
        for category in sorted(totals)
    )
    return Report(rows=rows, count=overall_count, total=overall_total)
