from __future__ import annotations
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from processor_model import bits

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
if __name__ == '__main__':
    unittest.main()
