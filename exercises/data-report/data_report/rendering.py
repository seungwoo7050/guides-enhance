"""같은 `Report`를 텍스트 또는 JSON 문자열로 변환합니다."""

from __future__ import annotations

import json
from decimal import Decimal

from .model import Report


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


# [Implementation 5] Render text and JSON without writing files.
def render_text(report: Report) -> str:
    category_width = max(
        [len("category"), len("TOTAL"), *(len(row.category) for row in report.rows)]
    )
    count_width = max(
        [len("count"), len(str(report.count)), *(len(str(row.count)) for row in report.rows)]
    )
    total_values = [_decimal_text(row.total) for row in report.rows]
    total_width = max(
        [len("total"), len(_decimal_text(report.total)), *(len(value) for value in total_values)]
    )

    lines = [
        f"{'category':<{category_width}}  {'count':>{count_width}}  {'total':>{total_width}}"
    ]
    for row, total in zip(report.rows, total_values, strict=True):
        lines.append(
            f"{row.category:<{category_width}}  {row.count:>{count_width}}  "
            f"{total:>{total_width}}"
        )

    separator = "-" * len(lines[0])
    lines.extend(
        [
            separator,
            f"{'TOTAL':<{category_width}}  {report.count:>{count_width}}  "
            f"{_decimal_text(report.total):>{total_width}}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_json(report: Report) -> str:
    payload = {
        "count": report.count,
        "total": _decimal_text(report.total),
        "categories": [
            {
                "category": row.category,
                "count": row.count,
                "total": _decimal_text(row.total),
            }
            for row in report.rows
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
