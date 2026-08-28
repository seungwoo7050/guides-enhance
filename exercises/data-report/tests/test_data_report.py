from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from data_report.aggregation import aggregate
from data_report.cli import main
from data_report.loaders import load_records
from data_report.model import DataReportError
from data_report.rendering import render_json, render_text


# [Implementation 7] Verify loading, aggregation, rendering, and CLI behavior.
class DataReportTests(unittest.TestCase):
    def test_csv_and_json_produce_same_report(self) -> None:
        # CSV와 JSON을 서로 다르게 정규화하는 구현을 검출합니다.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv_path = root / "data.csv"
            json_path = root / "data.json"
            csv_path.write_text(
                "category,amount\nbooks,12.50\ngames,30\nbooks,7.50\n",
                encoding="utf-8",
            )
            json_path.write_text(
                json.dumps(
                    [
                        {"category": "books", "amount": "12.50"},
                        {"category": "games", "amount": 30},
                        {"category": "books", "amount": "7.50"},
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                aggregate(load_records(csv_path)),
                aggregate(load_records(json_path)),
            )

    def test_validation_rejects_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            path.write_text(
                '[{"category":"books","amount":"1.00","extra":true}]',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DataReportError, "unknown fields"):
                load_records(path)

    def test_validation_rejects_non_finite_amount(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.csv"
            path.write_text("category,amount\nbooks,NaN\n", encoding="utf-8")
            with self.assertRaisesRegex(DataReportError, "must be finite"):
                load_records(path)

    def test_aggregation_sorts_categories_and_uses_decimal(self) -> None:
        # `float` 합산 오차와 입력 순서에 의존하는 출력을 함께 검출합니다.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.csv"
            path.write_text(
                "category,amount\nzeta,0.1\nalpha,0.2\nzeta,0.2\n",
                encoding="utf-8",
            )
            report = aggregate(load_records(path))

        self.assertEqual([row.category for row in report.rows], ["alpha", "zeta"])
        self.assertEqual(report.count, 3)
        self.assertEqual(report.total, Decimal("0.5"))
        self.assertEqual(report.rows[1].total, Decimal("0.3"))

    def test_renderers_use_same_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.csv"
            path.write_text("category,amount\nbooks,2.50\n", encoding="utf-8")
            report = aggregate(load_records(path))

        text = render_text(report)
        payload = json.loads(render_json(report))
        self.assertIn("books", text)
        self.assertIn("TOTAL", text)
        self.assertEqual(payload["total"], "2.50")
        self.assertEqual(payload["categories"][0]["category"], "books")

    def test_cli_writes_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "data.csv"
            output_path = root / "report.json"
            input_path.write_text("category,amount\nbooks,1.25\n", encoding="utf-8")

            status = main(
                [str(input_path), "--format", "json", "--output", str(output_path)]
            )

            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output_path.read_text())["total"], "1.25")

    def test_cli_reports_invalid_input(self) -> None:
        # 지원하지 않는 확장자를 성공으로 처리하거나
        # 오류를 `stdout`에 쓰는 구현을 검출합니다.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.txt"
            path.write_text("unsupported", encoding="utf-8")
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                status = main([str(path)])

            self.assertEqual(status, 2)
            self.assertIn("input file must use .csv or .json", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
