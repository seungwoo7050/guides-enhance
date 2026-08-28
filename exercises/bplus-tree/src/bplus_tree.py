from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
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
