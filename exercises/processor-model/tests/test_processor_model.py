from __future__ import annotations
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from processor_model import bits, isa

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
if __name__ == '__main__':
    unittest.main()
