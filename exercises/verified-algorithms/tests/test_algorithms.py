from __future__ import annotations

from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from verified_algorithms.ranges import prefix_sums, range_sum, lower_bound



class DataStructureTests(unittest.TestCase):
    def test_prefix_contract_and_random_ranges(self) -> None:
        self.assertEqual(prefix_sums([]), [0])
        self.assertEqual(prefix_sums([3, -2, 5]), [0, 3, 1, 6])

        source = random.Random(20241214)
        values = [source.randrange(-20, 21) for _ in range(80)]
        prefix = prefix_sums(values)
        self.assertEqual(len(prefix), len(values) + 1)
        for _ in range(250):
            start = source.randrange(len(values) + 1)
            stop = source.randrange(start, len(values) + 1)
            self.assertEqual(
                range_sum(prefix, start, stop),
                sum(values[start:stop]),
            )

    def test_range_sum_rejects_invalid_half_open_ranges(self) -> None:
        prefix = prefix_sums([1, 2, 3])
        for start, stop in [(-1, 1), (2, 1), (0, 4), (4, 4)]:
            with self.subTest(start=start, stop=stop):
                with self.assertRaises(ValueError):
                    range_sum(prefix, start, stop)

    def test_lower_bound_matches_bisect_with_duplicates(self) -> None:
        from bisect import bisect_left

        cases = [[], [1], [1, 1, 1], [-3, -1, 0, 0, 4, 9]]
        source = random.Random(20250102)
        cases.append(sorted(source.randrange(-30, 31) for _ in range(120)))
        for values in cases:
            for target in range(-35, 36):
                self.assertEqual(
                    lower_bound(values, target),
                    bisect_left(values, target),
                )


if __name__ == "__main__":
    unittest.main()
