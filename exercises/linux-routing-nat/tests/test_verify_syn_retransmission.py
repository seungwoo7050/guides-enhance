from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "verify_syn_retransmission.py"
spec = importlib.util.spec_from_file_location("verify_syn_retransmission", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class SynRetransmissionVerifierTests(unittest.TestCase):
    def test_repeated_syn_signature_is_reported(self) -> None:
        trace = "\n".join(
            [
                "1710000100.000000 IP 10.0.0.2.41000 > 10.0.1.2.9000: Flags [S], seq 12345, win 64240, length 0",
                "1710000101.025000 IP 10.0.0.2.41000 > 10.0.1.2.9000: Flags [S], seq 12345, win 64240, length 0",
            ]
        )
        report = module.analyze(trace)
        self.assertEqual(report["syn_count"], 2)
        candidates = report["retransmission_candidates"]
        self.assertEqual(len(candidates), 1)
        self.assertGreater(candidates[0]["delay_seconds"], 1.0)

    def test_different_sequence_is_not_reported(self) -> None:
        # 튜플이 같아도 순서 번호가 다르면 새 연결 시도일 수 있으므로 제외합니다.
        trace = "\n".join(
            [
                "1710000100.000000 IP 10.0.0.2.41000 > 10.0.1.2.9000: Flags [S], seq 12345, win 64240, length 0",
                "1710000101.025000 IP 10.0.0.2.41000 > 10.0.1.2.9000: Flags [S], seq 12346, win 64240, length 0",
            ]
        )
        self.assertEqual(module.analyze(trace)["retransmission_candidates"], [])

    def test_non_syn_lines_are_ignored(self) -> None:
        trace = "1710000100.0 IP 10.0.0.2.1 > 10.0.1.2.2: Flags [.], ack 1, length 0\n"
        self.assertEqual(module.parse_syn_observations(trace), [])


if __name__ == "__main__":
    unittest.main()
