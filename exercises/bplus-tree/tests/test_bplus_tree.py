from __future__ import annotations

import random
import unittest

from bplus_tree import BPlusTree


# [Implementation 8] B+ tree 동작과 불변식을 검증합니다.
# 무작위 삽입, 값 교체, 범위 조회, 잘못된 타입, 손상된 separator를 확인합니다.
class BPlusTreeTests(unittest.TestCase):
    def test_insert_search_and_root_growth(self) -> None:
        tree: BPlusTree[str] = BPlusTree(order=4)
        keys = list(range(100))
        random.Random(42).shuffle(keys)
        for key in keys:
            tree.insert(key, f"value-{key}")
            tree.validate()
        for key in range(100):
            self.assertEqual(tree.get(key), f"value-{key}")
        with self.assertRaises(KeyError):
            tree.get(1000)

    def test_duplicate_key_replaces_value(self) -> None:
        tree: BPlusTree[str] = BPlusTree(order=3)
        tree.insert(7, "old")
        tree.insert(7, "new")
        tree.validate()
        self.assertEqual(tree.get(7), "new")
        self.assertEqual(tree.range(0, 10), [(7, "new")])

    def test_range_crosses_leaf_boundaries(self) -> None:
        tree: BPlusTree[int] = BPlusTree(order=4)
        for key in range(0, 50, 2):
            tree.insert(key, key * 10)
        tree.validate()
        self.assertEqual(
            tree.range(9, 21),
            [(10, 100), (12, 120), (14, 140), (16, 160), (18, 180), (20, 200)],
        )
        self.assertEqual(tree.range(30, 20), [])

    def test_multiple_orders_match_sorted_mapping(self) -> None:
        keys = list(range(-30, 31))
        for order in range(3, 9):
            with self.subTest(order=order):
                tree: BPlusTree[int] = BPlusTree(order=order)
                shuffled = keys[:]
                random.Random(order).shuffle(shuffled)
                for key in shuffled:
                    tree.insert(key, key * key)
                tree.validate()
                self.assertEqual(tree.range(-7, 7), [(key, key * key) for key in range(-7, 8)])

    def test_rejects_non_integer_key(self) -> None:
        tree: BPlusTree[str] = BPlusTree()
        for invalid in ("1", True, 1.5):
            with self.subTest(invalid=invalid), self.assertRaises(TypeError):
                tree.insert(invalid, "bad")  # type: ignore[arg-type]
            with self.subTest(invalid=invalid), self.assertRaises(TypeError):
                tree.get(invalid)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            tree.range(0, True)  # type: ignore[arg-type]

    def test_validate_detects_separator_corruption(self) -> None:
        tree: BPlusTree[int] = BPlusTree(order=3)
        for key in range(10):
            tree.insert(key, key)
        tree.validate()
        self.assertFalse(tree.root.leaf)
        tree.root.keys[0] += 1
        with self.assertRaises(AssertionError):
            tree.validate()


if __name__ == "__main__":
    unittest.main()
