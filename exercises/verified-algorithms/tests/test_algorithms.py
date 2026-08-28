from __future__ import annotations

from itertools import product
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from verified_algorithms.ranges import prefix_sums, range_sum, lower_bound
from verified_algorithms.trees import RedBlackNode, red_black_height
def valid_red_black_tree(root: object) -> tuple[bool, int | None]:
    if root is not None and root.color != "black":
        return False, None

    def visit(node: object, lower: int | None, upper: int | None) -> int | None:
        if node is None:
            return 1
        if node.color not in {"red", "black"}:
            return None
        if lower is not None and node.key <= lower:
            return None
        if upper is not None and node.key >= upper:
            return None
        if node.color == "red" and (
            (node.left is not None and node.left.color == "red")
            or (node.right is not None and node.right.color == "red")
        ):
            return None
        left_height = visit(node.left, lower, node.key)
        right_height = visit(node.right, node.key, upper)
        if (
            left_height is None
            or right_height is None
            or left_height != right_height
        ):
            return None
        return left_height + (1 if node.color == "black" else 0)

    height = visit(root, None, None)
    return height is not None, height


def complete_tree(colors: tuple[str, ...]) -> object:
    nodes = {
        key: RedBlackNode(key, color)
        for key, color in zip((4, 2, 6, 1, 3, 5, 7), colors)
    }
    nodes[4].left, nodes[4].right = nodes[2], nodes[6]
    nodes[2].left, nodes[2].right = nodes[1], nodes[3]
    nodes[6].left, nodes[6].right = nodes[5], nodes[7]
    return nodes[4]


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

    def test_red_black_all_complete_tree_colorings(self) -> None:
        self.assertEqual(red_black_height(None), 1)
        for colors in product(("red", "black"), repeat=7):
            tree = complete_tree(colors)
            expected_valid, expected_height = valid_red_black_tree(tree)
            if expected_valid:
                self.assertEqual(
                    red_black_height(tree),
                    expected_height,
                )
            else:
                with self.assertRaises(ValueError):
                    red_black_height(tree)

    def test_red_black_rejects_bst_and_color_errors(self) -> None:
        with self.assertRaises(ValueError):
            red_black_height(RedBlackNode(2, "blue"))

        bad_order = RedBlackNode(
            4,
            "black",
            left=RedBlackNode(5, "black"),
            right=RedBlackNode(6, "black"),
        )
        with self.assertRaises(ValueError):
            red_black_height(bad_order)


if __name__ == "__main__":
    unittest.main()
