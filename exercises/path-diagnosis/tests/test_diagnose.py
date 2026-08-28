"""관찰 ``facts``가 선택하는 진단 코드를 검증합니다."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from path_diagnosis import Trace, diagnose, load_trace, render_text

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


class DiagnosisTests(unittest.TestCase):
    CASES = {
        "healthy.json": ("HEALTHY", "http", None),
        "dns-nxdomain.json": ("DNS_NAME_NOT_FOUND", None, "dns"),
        "route-missing.json": ("NO_ROUTE", "dns", "route"),
        "neighbor-unresolved.json": ("NEIGHBOR_UNRESOLVED", "route", "neighbor"),
        "mtu-black-hole.json": ("MTU_BLACK_HOLE", "neighbor", "path"),
        "transport-timeout.json": ("TRANSPORT_TIMEOUT", "path", "transport"),
        "tls-name-mismatch.json": ("TLS_NAME_MISMATCH", "transport", "tls"),
        "http-forbidden.json": ("HTTP_FORBIDDEN", "tls", "http"),
    }

    def test_all_published_diagnoses(self) -> None:
        for filename, expected in self.CASES.items():
            with self.subTest(filename=filename):
                result = diagnose(load_trace(FIXTURES / filename))
                self.assertEqual(
                    (result.code, result.last_success, result.first_failure),
                    expected,
                )
                self.assertTrue(result.summary)
                self.assertTrue(result.evidence)
                self.assertTrue(result.next_checks)
                self.assertEqual(
                    result.to_mapping()["healthy"],
                    filename == "healthy.json",
                )

    def test_fallback_codes_do_not_overclaim_specific_causes(self) -> None:
        # 큰 패킷만 실패했다는 근거가 없으면 MTU 블랙홀로 단정해서는 안 됩니다.
        value = json.loads(
            (FIXTURES / "mtu-black-hole.json").read_text(encoding="utf-8")
        )
        value = deepcopy(value)
        value["stages"][3]["facts"] = {
            "small_packet_ok": False,
            "large_packet_ok": False,
            "icmp_too_big_seen": False,
        }
        result = diagnose(Trace.from_mapping(value))
        self.assertEqual(result.code, "PATH_FAILURE")

    def test_transport_rst_is_not_reported_as_timeout(self) -> None:
        # RST 관찰을 제한 시간 초과보다 먼저 판정하지 않으면 명시적 거부를 응답 없음으로 오분류합니다.
        value = json.loads(
            (FIXTURES / "transport-timeout.json").read_text(encoding="utf-8")
        )
        value = deepcopy(value)
        value["stages"][4]["facts"] = {
            "syn_sent": 1,
            "syn_ack_received": False,
            "rst_received": True,
        }
        result = diagnose(Trace.from_mapping(value))
        self.assertEqual(result.code, "CONNECTION_REFUSED")

    def test_rendered_text_contains_boundary_and_code(self) -> None:
        result = diagnose(load_trace(FIXTURES / "tls-name-mismatch.json"))
        text = render_text(result)
        self.assertIn("code: TLS_NAME_MISMATCH", text)
        self.assertIn("last_success: transport", text)
        self.assertIn("first_failure: tls", text)
        self.assertIn("evidence:", text)
        self.assertIn("next_checks:", text)


if __name__ == "__main__":
    unittest.main()
