from __future__ import annotations
import unittest
from collections import Counter
from joins import hash_join, merge_join, nested_loop_join

def normalize(rows: list[tuple[dict[str, object], dict[str, object]]]) -> Counter[tuple[int, int]]:
    return Counter(((int(left['id']), int(right['id'])) for left, right in rows))

class JoinAlgorithmTests(unittest.TestCase):

    def setUp(self) -> None:
        self.left = [{'id': 1, 'join_key': 10}, {'id': 2, 'join_key': 10}, {'id': 3, 'join_key': 20}, {'id': 4, 'join_key': None}]
        self.right = [{'id': 101, 'fk': 10}, {'id': 102, 'fk': 10}, {'id': 103, 'fk': 30}, {'id': 104, 'fk': None}]

    def test_all_algorithms_preserve_bag_semantics(self) -> None:
        expected = Counter({(1, 101): 1, (1, 102): 1, (2, 101): 1, (2, 102): 1})
        for algorithm in (nested_loop_join, hash_join, merge_join):
            with self.subTest(algorithm=algorithm.__name__):
                actual = algorithm(self.left, self.right, 'join_key', 'fk')
                self.assertEqual(normalize(actual), expected)

    def test_null_never_matches_null(self) -> None:
        for algorithm in (nested_loop_join, hash_join, merge_join):
            rows = algorithm([{'id': 1, 'k': None}], [{'id': 2, 'k': None}], 'k', 'k')
            self.assertEqual(rows, [])

    def test_empty_input(self) -> None:
        for algorithm in (nested_loop_join, hash_join, merge_join):
            self.assertEqual(algorithm([], self.right, 'join_key', 'fk'), [])
            self.assertEqual(algorithm(self.left, [], 'join_key', 'fk'), [])

    def test_hash_join_keeps_orientation_when_build_side_changes(self) -> None:
        many_left = [{'id': index, 'k': 1} for index in range(20)]
        one_right = [{'id': 100, 'k': 1}]
        rows = hash_join(many_left, one_right, 'k', 'k')
        self.assertEqual({left['id'] for left, _ in rows}, set(range(20)))
        self.assertEqual({right['id'] for _, right in rows}, {100})
if __name__ == '__main__':
    unittest.main()
