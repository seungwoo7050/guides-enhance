from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = [sys.executable, str(ROOT / "processor-model.py")]


def run_json(*args: str) -> dict[str, object]:
    completed = subprocess.run(
        [*COMMAND, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"명령 실패: {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return json.loads(completed.stdout)


# [Implementation 12-1] CLI 통합 검사
# 대표 하위 명령의 JSON 결과와 오류 종료 상태를 고정합니다.
# 파일 입력, 모듈 호출과 출력 연결이 깨지는 회귀를 검출합니다.
class CliIntegrationTests(unittest.TestCase):
    def test_integer_representation_contract(self) -> None:
        result = run_json("bits", "int", "-1", "--width", "8")
        self.assertEqual(
            result,
            {
                "input": -1,
                "width": 8,
                "unsigned": 255,
                "signed": -1,
                "binary": "11111111",
                "hex": "0xff",
                "big_endian_bytes": ["0xff"],
                "little_endian_bytes": ["0xff"],
                "truncated": False,
            },
        )

    def test_isa_program_contract(self) -> None:
        result = run_json("isa", "fixtures/programs/sum.asm", "--max-steps", "100")
        self.assertEqual(result["steps"], 20)
        self.assertEqual(result["pc"], 8)
        self.assertEqual(result["registers"]["r3"], 15)
        self.assertEqual(result["nonzero_memory_words"], {"0": 15})

    def test_pipeline_summary_contract(self) -> None:
        result = run_json(
            "pipeline",
            "fixtures/traces/pipeline-branch.trace",
            "--forwarding",
            "full",
            "--json",
        )
        summary = {key: value for key, value in result.items() if key != "timeline"}
        self.assertEqual(
            summary,
            {
                "cycles": 12,
                "retired": 3,
                "data_stalls": 0,
                "control_stalls": 2,
                "flushes": 2,
                "cpi": 4.0,
            },
        )

    def test_cache_summary_contract(self) -> None:
        result = run_json(
            "cache",
            "fixtures/traces/cache.trace",
            "--size",
            "16",
            "--block",
            "4",
            "--ways",
            "1",
        )
        self.assertEqual(result["hits"], 1)
        self.assertEqual(result["misses"], 9)
        self.assertEqual(result["compulsory_misses"], 5)
        self.assertEqual(result["conflict_misses"], 2)
        self.assertEqual(result["capacity_misses"], 2)
        self.assertEqual(result["writebacks"], 1)

    def test_vm_summary_contract(self) -> None:
        result = run_json("vm", "fixtures/vm/config.json", "fixtures/vm/trace.txt")
        self.assertEqual(result["translations"], 7)
        self.assertEqual(result["tlb_hits"], 1)
        self.assertEqual(result["page_faults"], 2)
        self.assertEqual(result["protection_faults"], 1)
        self.assertEqual(result["tlb_invalidations"], 2)

    def test_coherence_summary_contract(self) -> None:
        result = run_json(
            "coherence",
            "fixtures/traces/coherence-false-sharing.trace",
            "--cores",
            "2",
            "--line-size",
            "64",
        )
        self.assertEqual(result["hits"], 0)
        self.assertEqual(result["misses"], 4)
        self.assertEqual(result["bus_read_exclusive"], 3)
        self.assertEqual(result["invalidations"], 2)
        self.assertEqual(result["writebacks"], 3)
        self.assertEqual(result["final_states"], {"0": ["S", "S"]})

    def test_expected_model_error_exits_two(self) -> None:
        completed = subprocess.run(
            [*COMMAND, "bits", "int", "1", "--width", "0"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("processor-model:", completed.stderr)


if __name__ == "__main__":
    unittest.main()
