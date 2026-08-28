"""추적 기록 형식과 단계 진행 규칙을 검증합니다."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from path_diagnosis import STAGE_ORDER, Trace, TraceFormatError, load_trace

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


class TraceModelTests(unittest.TestCase):
    def test_all_published_fixtures_are_valid(self) -> None:
        for path in sorted(FIXTURES.glob("*.json")):
            with self.subTest(path=path.name):
                trace = load_trace(path)
                self.assertEqual(tuple(stage.stage for stage in trace.stages), STAGE_ORDER)
                self.assertEqual(trace.request.name, "api.example.test")

    def test_healthy_trace_has_http_as_last_success(self) -> None:
        trace = load_trace(FIXTURES / "healthy.json")
        self.assertIsNone(trace.first_failure)
        self.assertIsNotNone(trace.last_success)
        assert trace.last_success is not None
        self.assertEqual(trace.last_success.stage, "http")
        self.assertEqual(Trace.from_mapping(trace.to_mapping()), trace)

    def test_failure_trace_exposes_adjacent_boundary(self) -> None:
        trace = load_trace(FIXTURES / "tls-name-mismatch.json")
        self.assertIsNotNone(trace.first_failure)
        self.assertIsNotNone(trace.last_success)
        assert trace.first_failure is not None
        assert trace.last_success is not None
        self.assertEqual(trace.first_failure.stage, "tls")
        self.assertEqual(trace.last_success.stage, "transport")

    def test_rejects_wrong_stage_order(self) -> None:
        value = self._mapping("healthy.json")
        value["stages"][0], value["stages"][1] = value["stages"][1], value["stages"][0]
        with self.assertRaisesRegex(TraceFormatError, "stage order"):
            Trace.from_mapping(value)

    def test_rejects_not_run_without_failure(self) -> None:
        value = self._mapping("healthy.json")
        value["stages"][2]["status"] = "not-run"
        with self.assertRaisesRegex(TraceFormatError, "preceding failure"):
            Trace.from_mapping(value)

    def test_rejects_success_after_failure(self) -> None:
        # 첫 실패 뒤의 성공을 허용하면 ``last_success``와 ``first_failure``가 모순됩니다.
        value = self._mapping("route-missing.json")
        value["stages"][2]["status"] = "ok"
        with self.assertRaisesRegex(TraceFormatError, "after the first failure"):
            Trace.from_mapping(value)

    def test_rejects_missing_stage(self) -> None:
        value = self._mapping("healthy.json")
        value["stages"].pop()
        with self.assertRaisesRegex(TraceFormatError, "exactly 7"):
            Trace.from_mapping(value)

    def test_rejects_invalid_port_and_facts(self) -> None:
        value = self._mapping("healthy.json")
        value["request"]["port"] = 70000
        with self.assertRaisesRegex(TraceFormatError, "65535"):
            Trace.from_mapping(value)
        value = self._mapping("healthy.json")
        value["stages"][0]["facts"] = []
        with self.assertRaisesRegex(TraceFormatError, "facts"):
            Trace.from_mapping(value)

    def test_invalid_json_is_public_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(TraceFormatError, "invalid JSON syntax"):
                load_trace(path)

    @staticmethod
    def _mapping(name: str) -> dict[str, object]:
        return deepcopy(json.loads((FIXTURES / name).read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
