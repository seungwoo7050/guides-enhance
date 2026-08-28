from __future__ import annotations

from itertools import combinations, product
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from verified_algorithms.ranges import prefix_sums, range_sum, lower_bound
from verified_algorithms.trees import RedBlackNode, red_black_height
from verified_algorithms.optimization import knapsack_01, select_intervals, lcs_length
from verified_algorithms.graphs import bfs_distances
def all_pairs_distances(
    size: int,
    edges: list[tuple[int, int, int]],
) -> list[list[int | None]]:
    distance: list[list[int | None]] = [[None] * size for _ in range(size)]
    for vertex in range(size):
        distance[vertex][vertex] = 0
    for source, target, weight in edges:
        current = distance[source][target]
        if current is None or weight < current:
            distance[source][target] = weight
    for middle in range(size):
        for source in range(size):
            if distance[source][middle] is None:
                continue
            for target in range(size):
                if distance[middle][target] is None:
                    continue
                candidate = distance[source][middle] + distance[middle][target]
                current = distance[source][target]
                if current is None or candidate < current:
                    distance[source][target] = candidate
    return distance


def brute_interval_count(intervals: list[tuple[int, int]]) -> int:
    best = 0
    for count in range(len(intervals) + 1):
        for subset in combinations(intervals, count):
            ordered = sorted(subset)
            if all(
                left[1] <= right[0]
                for left, right in zip(ordered, ordered[1:])
            ):
                best = max(best, count)
    return best


def deterministic_interval_selection(
    intervals: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    selected: list[tuple[int, int]] = []
    last_stop: int | None = None
    for interval in sorted(intervals, key=lambda item: (item[1], item[0])):
        start, stop = interval
        if last_stop is None or start >= last_stop:
            selected.append(interval)
            last_stop = stop
    return selected


def brute_knapsack(items: list[tuple[int, int]], capacity: int) -> int:
    best = 0
    for count in range(len(items) + 1):
        for selected in combinations(range(len(items)), count):
            weight = sum(items[index][0] for index in selected)
            if weight <= capacity:
                best = max(
                    best,
                    sum(items[index][1] for index in selected),
                )
    return best


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


def brute_lcs_length(left: str, right: str) -> int:
    def is_subsequence(candidate: str, text: str) -> bool:
        position = 0
        for character in text:
            if position < len(candidate) and candidate[position] == character:
                position += 1
        return position == len(candidate)

    shorter, longer = (
        (left, right) if len(left) <= len(right) else (right, left)
    )
    best = 0
    for mask in range(1 << len(shorter)):
        candidate = "".join(
            character
            for index, character in enumerate(shorter)
            if mask & (1 << index)
        )
        if len(candidate) > best and is_subsequence(candidate, longer):
            best = len(candidate)
    return best


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


class DesignTechniqueTests(unittest.TestCase):
    def test_knapsack_matches_subset_enumeration(self) -> None:
        source = random.Random(20250130)
        self.assertEqual(knapsack_01([], 0), 0)
        for _ in range(70):
            items = [
                (source.randrange(1, 8), source.randrange(-3, 16))
                for _ in range(8)
            ]
            capacity = source.randrange(0, 20)
            self.assertEqual(
                knapsack_01(items, capacity),
                brute_knapsack(items, capacity),
            )

    def test_knapsack_rejects_invalid_contract(self) -> None:
        with self.assertRaises(ValueError):
            knapsack_01([], -1)
        with self.assertRaises(ValueError):
            knapsack_01([(0, 5)], 10)
        with self.assertRaises(ValueError):
            knapsack_01([(-2, 5)], 10)

    def test_interval_selection_matches_exhaustive_optimum(self) -> None:
        source = random.Random(20250201)
        specific = [(0, 100), (1, 2), (2, 3), (3, 4)]
        self.assertEqual(len(select_intervals(specific)), 3)
        tied = [(1, 3), (0, 3), (3, 4)]
        self.assertEqual(
            select_intervals(tied),
            [(0, 3), (3, 4)],
        )
        for _ in range(80):
            intervals: list[tuple[int, int]] = []
            for _ in range(8):
                start = source.randrange(0, 12)
                intervals.append((start, start + source.randrange(1, 5)))
            selected = select_intervals(intervals)
            self.assertEqual(len(selected), brute_interval_count(intervals))
            self.assertEqual(
                selected,
                deterministic_interval_selection(intervals),
            )
            self.assertTrue(
                all(
                    left[1] <= right[0]
                    for left, right in zip(selected, selected[1:])
                )
            )

    def test_interval_selection_rejects_invalid_ranges(self) -> None:
        for intervals in [[(1, 1)], [(3, 2)], [(0, 1), (5, 4)]]:
            with self.assertRaises(ValueError):
                select_intervals(intervals)

    def test_lcs_matches_subsequence_enumeration(self) -> None:
        source = random.Random(20250205)
        self.assertEqual(lcs_length("", ""), 0)
        self.assertEqual(lcs_length("abc", "abc"), 3)
        self.assertEqual(lcs_length("abc", "def"), 0)
        for _ in range(100):
            left = "".join(
                source.choice("abcd")
                for _ in range(source.randrange(9))
            )
            right = "".join(
                source.choice("abcd")
                for _ in range(source.randrange(9))
            )
            self.assertEqual(
                lcs_length(left, right),
                brute_lcs_length(left, right),
            )


class GraphTests(unittest.TestCase):
    def test_bfs_distances_against_unit_weight_floyd_warshall(self) -> None:
        source = random.Random(20250111)
        self.assertEqual(bfs_distances([[]], 0), [0])
        for _ in range(50):
            size = 7
            graph = [
                [
                    target
                    for target in range(size)
                    if target != vertex and source.random() < 0.25
                ]
                for vertex in range(size)
            ]
            edges = [
                (vertex, target, 1)
                for vertex, neighbors in enumerate(graph)
                for target in neighbors
            ]
            expected = all_pairs_distances(size, edges)[0]
            self.assertEqual(bfs_distances(graph, 0), expected)

    def test_bfs_rejects_invalid_vertices(self) -> None:
        with self.assertRaises(ValueError):
            bfs_distances([], 0)
        with self.assertRaises(ValueError):
            bfs_distances([[1], [2]], 0)


if __name__ == "__main__":
    unittest.main()
