from __future__ import annotations
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from processor_model import bits, control, isa, perf, pipeline

class BitsTests(unittest.TestCase):

    def test_two_complement_view(self) -> None:
        view = bits.represent_integer(-1, 8)
        self.assertEqual(view['unsigned'], 255)
        self.assertEqual(view['signed'], -1)
        self.assertEqual(view['hex'], '0xff')

    def test_signed_overflow_differs_from_carry(self) -> None:
        signed = bits.add_fixed(127, 1, 8)
        self.assertTrue(signed['signed_overflow'])
        self.assertFalse(signed['carry_out'])
        unsigned = bits.add_fixed(255, 1, 8)
        self.assertTrue(unsigned['carry_out'])
        self.assertFalse(unsigned['signed_overflow'])

    def test_float32_rounding_is_visible(self) -> None:
        result = bits.represent_float(0.1, 'f32')
        self.assertEqual(result['classification'], 'normal')
        self.assertEqual(result['hex'], '0x3dcccccd')
        self.assertNotEqual(result['rounded_value'], 0.1)

class PerformanceTests(unittest.TestCase):

    def test_cpu_time(self) -> None:
        result = perf.cpu_time(1000000000, 2.0, 2.0)
        self.assertAlmostEqual(result['seconds'], 1.0)

    def test_amdahl_limit(self) -> None:
        result = perf.amdahl(0.5, 10.0)
        self.assertAlmostEqual(result['overall_speedup'], 1 / 0.55)
        self.assertAlmostEqual(result['infinite_enhancement_limit'], 2.0)

    def test_fully_enhanced_amdahl_limit_is_unbounded(self) -> None:
        result = perf.amdahl(1.0, 4.0)
        self.assertIsNone(result['infinite_enhancement_limit'])

    def test_amat(self) -> None:
        self.assertAlmostEqual(perf.amat(1.0, 0.05, 80.0)['amat'], 5.0)

class IsaTests(unittest.TestCase):

    def test_sum_program(self) -> None:
        result = isa.run_file(ROOT / 'fixtures/programs/sum.asm', 4096, 100)
        self.assertTrue(result['halted'])
        self.assertEqual(result['registers']['r3'], 15)
        self.assertEqual(result['nonzero_memory_words']['0'], 15)

    def test_wraparound_and_zero_register(self) -> None:
        result = isa.run_file(ROOT / 'fixtures/programs/overflow.asm', 4096, 20)
        self.assertEqual(result['registers']['r1'], -2147483648)
        self.assertEqual(result['registers']['r0'], 0)

    def test_unaligned_access_fails(self) -> None:
        program, labels = isa.parse_program(['li r1, 1', 'lw r2, 0(r1)', 'halt'])
        with self.assertRaises(RuntimeError):
            isa.Machine().run(program, labels)

class ControlTests(unittest.TestCase):

    def test_load_uses_memory_writeback(self) -> None:
        result = control.signals('lw')
        self.assertEqual(result['mem_read'], 1)
        self.assertEqual(result['writeback'], 'memory')

class PipelineTests(unittest.TestCase):

    def _trace(self, name: str) -> list[isa.Instruction]:
        return isa.parse_pipeline_trace((ROOT / f'fixtures/traces/{name}').read_text(encoding='utf-8').splitlines())

    def test_forwarding_only_stalls_load_use(self) -> None:
        trace = self._trace('pipeline-load-use.trace')
        result = pipeline.simulate(trace, forwarding='full').as_dict()
        self.assertEqual(result['retired'], 3)
        self.assertEqual(result['data_stalls'], 1)

    def test_without_forwarding_needs_more_stalls(self) -> None:
        trace = self._trace('pipeline-load-use.trace')
        full = pipeline.simulate(trace, forwarding='full').as_dict()
        none = pipeline.simulate(trace, forwarding='none').as_dict()
        self.assertGreater(none['cycles'], full['cycles'])
        self.assertGreater(none['data_stalls'], full['data_stalls'])

    def test_taken_branch_flushes_younger_instruction(self) -> None:
        trace = self._trace('pipeline-branch.trace')
        result = pipeline.simulate(trace, branch_penalty=2).as_dict()
        self.assertEqual(result['retired'], 3)
        self.assertEqual(result['flushes'], 2)
        self.assertEqual(result['control_stalls'], 2)
        wrong_id = result['timeline'][2]
        wrong_if = result['timeline'][3]
        target = result['timeline'][4]
        self.assertIn('ID*', wrong_id.values())
        self.assertIn('IF*', wrong_if.values())
        self.assertIn('WB', target.values())

    def test_taken_annotation_requires_control_instruction(self) -> None:
        with self.assertRaises(ValueError):
            isa.parse_pipeline_trace(['add r1, r2, r3 @taken'])
if __name__ == '__main__':
    unittest.main()
