from __future__ import annotations
import random
import unittest
from bplus_tree import BPlusTree

class BPlusTreeTests(unittest.TestCase):
    def test_insert_and_recursive_splits(self):
        for order in range(3, 9):
            tree = BPlusTree(order)
            keys = list(range(100))
            random.Random(order).shuffle(keys)
            for key in keys:
                tree.insert(key, str(key))
            self.assertFalse(tree.root.leaf)
            def inspect(node):
                self.assertEqual(node.keys, sorted(node.keys))
                self.assertLessEqual(len(node.keys), order - 1)
                if node.leaf:
                    self.assertEqual(len(node.keys), len(node.values))
                    return list(zip(node.keys, node.values))
                self.assertEqual(len(node.children), len(node.keys) + 1)
                groups = [inspect(child) for child in node.children]
                self.assertEqual(node.keys, [group[0][0] for group in groups[1:]])
                return [item for group in groups for item in group]
            self.assertEqual(inspect(tree.root), [(key, str(key)) for key in range(100)])

    def test_duplicate_key_replaces_value(self):
        tree = BPlusTree(3)
        tree.insert(7, "old")
        tree.insert(7, "new")
        self.assertEqual(tree.root.keys, [7])
        self.assertEqual(tree.root.values, ["new"])

    def test_rejects_non_integer_key(self):
        tree = BPlusTree()
        for key in ("1", True, 1.5):
            with self.assertRaises(TypeError): tree.insert(key, "bad")

if __name__ == "__main__": unittest.main()
