from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from processor_model import bits, cache, control, isa, perf, pipeline, predictor, rob, vm

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

class CacheTests(unittest.TestCase):

    def test_three_c_classification_sums_to_misses(self) -> None:
        accesses = cache.parse_trace((ROOT / 'fixtures/traces/cache.trace').read_text(encoding='utf-8').splitlines())
        result = cache.CacheSimulator(16, 4, 1).run(accesses)
        classified = result['compulsory_misses'] + result['conflict_misses'] + result['capacity_misses']
        self.assertEqual(classified, result['misses'])
        self.assertGreater(result['conflict_misses'], 0)
        self.assertGreater(result['capacity_misses'], 0)

    def test_dirty_eviction_writes_back(self) -> None:
        accesses = cache.parse_trace(['W 0', 'W 16'])
        result = cache.CacheSimulator(16, 4, 1).run(accesses)
        self.assertEqual(result['writebacks'], 1)

class VirtualMemoryTests(unittest.TestCase):

    def test_tlb_fault_permission_and_invalidation(self) -> None:
        config = json.loads((ROOT / 'fixtures/vm/config.json').read_text(encoding='utf-8'))
        mappings = {int(vpn, 0): vm.Mapping(entry['pfn'], set(entry['permissions'])) for vpn, entry in config['mappings'].items()}
        operations = vm.parse_operations((ROOT / 'fixtures/vm/trace.txt').read_text(encoding='utf-8').splitlines())
        result = vm.VirtualMemorySimulator(4096, 2, mappings).run(operations)
        self.assertGreater(result['tlb_hits'], 0)
        self.assertEqual(result['page_faults'], 2)
        self.assertEqual(result['protection_faults'], 1)
        self.assertGreaterEqual(result['tlb_invalidations'], 1)

class BranchPredictorTests(unittest.TestCase):

    def test_counter_learns_repeated_taken_branch(self) -> None:
        model = predictor.TwoBitPredictor(4)
        predictions = [model.update(256, True) for _ in range(4)]
        self.assertEqual(predictions, [False, True, True, True])
        self.assertEqual(model.run([])['counters'][0], 3)

    def test_aliasing_is_deterministic(self) -> None:
        model = predictor.TwoBitPredictor(2)
        model.update(0, True)
        self.assertTrue(model.predict(8))

    def test_pc_and_table_shape_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            predictor.TwoBitPredictor(3)
        model = predictor.TwoBitPredictor(4)
        with self.assertRaises(ValueError):
            model.predict(2)

class ReorderBufferTests(unittest.TestCase):

    def test_out_of_order_completion_retires_in_program_order(self) -> None:
        model = rob.ReorderBuffer(3)
        first = model.issue('r1')
        second = model.issue('r2')
        model.complete(second, value=20)
        registers: dict[str, int] = {}
        self.assertEqual(model.retire(registers), [])
        model.complete(first, value=10)
        self.assertEqual(model.retire(registers), [first, second])
        self.assertEqual(registers, {'r1': 10, 'r2': 20})

    def test_fault_discards_itself_and_younger_entries(self) -> None:
        model = rob.ReorderBuffer(4)
        older = model.issue('r1')
        faulting = model.issue('r2')
        younger = model.issue('r3')
        model.complete(older, value=7)
        model.complete(faulting, fault='page fault')
        model.complete(younger, value=9)
        registers: dict[str, int] = {}
        with self.assertRaises(rob.PreciseException) as raised:
            model.retire(registers)
        self.assertEqual(raised.exception.tag, faulting)
        self.assertEqual(registers, {'r1': 7})
        self.assertEqual(model.pending_tags(), [])

    def test_full_buffer_and_duplicate_completion_are_rejected(self) -> None:
        model = rob.ReorderBuffer(1)
        tag = model.issue(None)
        with self.assertRaises(BufferError):
            model.issue('r1')
        model.complete(tag)
        with self.assertRaises(ValueError):
            model.complete(tag)
if __name__ == '__main__':
    unittest.main()
