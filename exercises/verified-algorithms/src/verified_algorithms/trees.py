"""Tree models and validation algorithms."""

from __future__ import annotations

from dataclasses import dataclass


# [Implementation 3]
# Red-black tree validation contract
@dataclass
class RedBlackNode:
    """A node in an integer-keyed red-black tree."""

    key: int
    color: str
    left: RedBlackNode | None = None
    right: RedBlackNode | None = None


def red_black_height(root: RedBlackNode | None) -> int:
    """Validate red-black and strict-BST invariants, then return black height."""
    if root is not None and root.color != "black":
        raise ValueError("the root must be black")

    def visit(
        node: RedBlackNode | None,
        lower: int | None,
        upper: int | None,
    ) -> int:
        if node is None:
            return 1
        if node.color not in {"red", "black"}:
            raise ValueError("node color must be 'red' or 'black'")
        if lower is not None and node.key <= lower:
            raise ValueError("the tree violates its strict lower BST bound")
        if upper is not None and node.key >= upper:
            raise ValueError("the tree violates its strict upper BST bound")
        if node.color == "red":
            if node.left is not None and node.left.color == "red":
                raise ValueError("a red node cannot have a red left child")
            if node.right is not None and node.right.color == "red":
                raise ValueError("a red node cannot have a red right child")

        # 각 호출은 허용 가능한 key 범위를 자식에게 전달하고 black height를 반환합니다.
        # 두 값을 함께 확인해야 subtree 전체의 BST 순서와 색 규칙을 한 번에 검사할 수 있습니다.
        left_height = visit(node.left, lower, node.key)
        right_height = visit(node.right, node.key, upper)
        if left_height != right_height:
            raise ValueError("root-to-leaf black heights must match")
        return left_height + (1 if node.color == "black" else 0)

    return visit(root, None, None)
