from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from math import ceil
from typing import Generic, TypeVar

V = TypeVar("V")


# [Implementation 1] node 형태를 정의하고 빈 root leaf를 만듭니다.
# value와 next는 leaf에서만 사용하고, internal node는 child만 보관합니다.
@dataclass(eq=False)
class Node(Generic[V]):
    leaf: bool
    keys: list[int] = field(default_factory=list)
    children: list["Node[V]"] = field(default_factory=list)
    values: list[V] = field(default_factory=list)
    next: "Node[V] | None" = None


class BPlusTree(Generic[V]):
    def __init__(self, order: int = 4) -> None:
        if isinstance(order, bool) or not isinstance(order, int):
            raise TypeError("order must be int")
        if order < 3:
            raise ValueError("order must be at least 3")
        self.order = order
        self.max_keys = order - 1
        self.root: Node[V] = Node(leaf=True)

    @staticmethod
    def _validate_key(key: int) -> int:
        if isinstance(key, bool) or not isinstance(key, int):
            raise TypeError("key must be int")
        return key

    # [Implementation 2] separator를 따라 leaf까지 내려갑니다.
    # separator는 오른쪽 subtree의 최소 key이며, 분할 결과를 올리기 위해 parent path를 함께 보관합니다.
    def _find_leaf(self, key: int) -> tuple[Node[V], list[Node[V]]]:
        node = self.root
        path: list[Node[V]] = []
        while not node.leaf:
            path.append(node)
            node = node.children[bisect_right(node.keys, key)]
        return node, path

    # [Implementation 3] key 순서에 맞춰 삽입하고 기존 key의 값은 교체합니다.
    # 새 key를 넣어 max_keys를 넘은 경우에만 node를 분할합니다.
    def insert(self, key: int, value: V) -> None:
        key = self._validate_key(key)
        leaf, path = self._find_leaf(key)
        index = bisect_left(leaf.keys, key)
        if index < len(leaf.keys) and leaf.keys[index] == key:
            leaf.values[index] = value
            return
        leaf.keys.insert(index, key)
        leaf.values.insert(index, value)
        if len(leaf.keys) > self.max_keys:
            self._split_leaf(leaf, path)

    # [Implementation 4] leaf를 나누고 오른쪽 최소 key를 parent에 반영합니다.
    # range scan이 끊기지 않도록 next 연결도 함께 갱신합니다.
    def _split_leaf(self, leaf: Node[V], path: list[Node[V]]) -> None:
        split = (len(leaf.keys) + 1) // 2
        right = Node[V](leaf=True)
        right.keys = leaf.keys[split:]
        right.values = leaf.values[split:]
        leaf.keys = leaf.keys[:split]
        leaf.values = leaf.values[:split]
        right.next = leaf.next
        leaf.next = right
        self._insert_in_parent(leaf, right.keys[0], right, path)

    @staticmethod
    def _identity_index(nodes: list[Node[V]], target: Node[V]) -> int:
        for index, node in enumerate(nodes):
            if node is target:
                return index
        raise AssertionError("split child is not owned by its parent")

    def _insert_in_parent(
        self,
        left: Node[V],
        separator: int,
        right: Node[V],
        path: list[Node[V]],
    ) -> None:
        if not path:
            self.root = Node(leaf=False, keys=[separator], children=[left, right])
            return
        parent = path.pop()
        child_index = self._identity_index(parent.children, left)
        parent.keys.insert(child_index, separator)
        parent.children.insert(child_index + 1, right)
        if len(parent.keys) > self.max_keys:
            self._split_internal(parent, path)

    # [Implementation 5] internal node를 나누고 가운데 separator를 parent로 올립니다.
    # 승격한 key는 자식에 남기지 않고, 나머지 key와 child 범위를 좌우 node에 나눕니다.
    def _split_internal(self, node: Node[V], path: list[Node[V]]) -> None:
        middle = len(node.keys) // 2
        promote = node.keys[middle]
        right = Node[V](leaf=False)
        right.keys = node.keys[middle + 1 :]
        right.children = node.children[middle + 1 :]
        node.keys = node.keys[:middle]
        node.children = node.children[: middle + 1]
        self._insert_in_parent(node, promote, right, path)

    # [Implementation 6] 단일 key와 범위를 조회합니다.
    # 범위 조회는 시작 leaf를 한 번 찾은 뒤 next를 따라가며 root를 다시 탐색하지 않습니다.
    def get(self, key: int) -> V:
        key = self._validate_key(key)
        leaf, _ = self._find_leaf(key)
        index = bisect_left(leaf.keys, key)
        if index == len(leaf.keys) or leaf.keys[index] != key:
            raise KeyError(key)
        return leaf.values[index]

    def range(self, start: int, end: int) -> list[tuple[int, V]]:
        start = self._validate_key(start)
        end = self._validate_key(end)
        if start > end:
            return []
        leaf, _ = self._find_leaf(start)
        result: list[tuple[int, V]] = []
        while leaf is not None:
            for key, value in zip(leaf.keys, leaf.values, strict=True):
                if key < start:
                    continue
                if key > end:
                    return result
                result.append((key, value))
            leaf = leaf.next
        return result

    # [Implementation 7] tree의 불변식을 검사합니다.
    # key 순서와 최소 점유율, child 범위, leaf 깊이, separator, next 연결을 함께 확인합니다.
    def validate(self) -> None:
        leaf_depths: set[int] = set()
        leaves: list[Node[V]] = []
        minimum_leaf_keys = ceil(self.max_keys / 2)
        minimum_internal_children = ceil(self.order / 2)

        def strictly_increasing(keys: list[int]) -> bool:
            return all(left < right for left, right in zip(keys, keys[1:]))

        def walk(
            node: Node[V],
            depth: int,
            low: int | None,
            high: int | None,
            *,
            root: bool,
        ) -> tuple[int, int]:
            if not strictly_increasing(node.keys) or len(node.keys) > self.max_keys:
                raise AssertionError("invalid key ordering or node overflow")

            if node.leaf:
                if len(node.keys) != len(node.values) or node.children or node.next is node:
                    raise AssertionError("invalid leaf shape")
                if not root and len(node.keys) < minimum_leaf_keys:
                    raise AssertionError("underfull non-root leaf")
                if not node.keys and not root:
                    raise AssertionError("empty non-root leaf")
                for key in node.keys:
                    if low is not None and key < low:
                        raise AssertionError("leaf key below lower bound")
                    if high is not None and key >= high:
                        raise AssertionError("leaf key above upper bound")
                leaf_depths.add(depth)
                leaves.append(node)
                return (node.keys[0], node.keys[-1]) if node.keys else (0, 0)

            if node.values or node.next is not None or len(node.children) != len(node.keys) + 1:
                raise AssertionError("invalid internal shape")
            if root:
                if len(node.children) < 2:
                    raise AssertionError("internal root must have at least two children")
            elif len(node.children) < minimum_internal_children:
                raise AssertionError("underfull non-root internal node")

            ranges: list[tuple[int, int]] = []
            for index, child in enumerate(node.children):
                child_low = low if index == 0 else node.keys[index - 1]
                child_high = high if index == len(node.children) - 1 else node.keys[index]
                ranges.append(walk(child, depth + 1, child_low, child_high, root=False))
            for index, separator in enumerate(node.keys):
                if ranges[index + 1][0] != separator:
                    raise AssertionError("separator is not right subtree minimum")
            return ranges[0][0], ranges[-1][1]

        walk(self.root, 0, None, None, root=True)
        if len(leaf_depths) != 1:
            raise AssertionError("leaves are not at the same depth")
        for index, leaf in enumerate(leaves):
            expected = leaves[index + 1] if index + 1 < len(leaves) else None
            if leaf.next is not expected:
                raise AssertionError("broken leaf chain")
