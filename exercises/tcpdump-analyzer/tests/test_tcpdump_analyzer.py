from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tcpdump_analyzer.py"
spec = importlib.util.spec_from_file_location("tcpdump_analyzer", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class TcpdumpAnalyzerTests(unittest.TestCase):
    def test_complete_handshake_is_detected(self) -> None:
        result = module.analyze(
            (ROOT / "fixtures" / "handshake.txt").read_text(encoding="utf-8")
        )
        self.assertTrue(result["handshake_complete"])
        self.assertEqual(result["packet_count"], 5)
        self.assertEqual(result["retransmission_candidates"], [])

    def test_wrong_handshake_ack_is_rejected(self) -> None:
        # 패킷 방향만 맞추는 구현은 잘못된 ACK도 정상 핸드셰이크로 오인합니다.
        trace = (ROOT / "fixtures" / "handshake.txt").read_text(encoding="utf-8")
        trace = trace.replace("ack 1001", "ack 1002", 1)
        self.assertFalse(module.analyze(trace)["handshake_complete"])

    def test_repeated_syn_is_reported_as_candidate(self) -> None:
        # 반복 SYN은 후보로만 표시하고 손실 원인까지 확정하지 않는 출력 형식을 확인합니다.
        result = module.analyze(
            (ROOT / "fixtures" / "retransmission.txt").read_text(encoding="utf-8")
        )
        self.assertTrue(result["handshake_complete"])
        candidates = result["retransmission_candidates"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["flags"], "S")
        self.assertGreater(candidates[0]["delay_seconds"], 1.0)

    def test_unrelated_lines_are_ignored(self) -> None:
        self.assertEqual(module.parse_trace("tcpdump: listening on lo\nnoise\n"), [])


if __name__ == "__main__":
    unittest.main()
