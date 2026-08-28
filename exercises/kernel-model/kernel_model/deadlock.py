"""단일 및 다중 instance 자원의 보유·대기 관계를 분석합니다."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


class DeadlockInputError(ValueError):
    """graph 또는 자원 vector 입력이 유효하지 않을 때 발생합니다."""


# [Implementation 4] wait-for graph 정의
def find_wait_cycle(graph: Mapping[str, Sequence[str]]) -> list[str] | None:
    """단일 instance wait-for graph에서 cycle 하나를 반환합니다."""

    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []
    positions: dict[str, int] = {}

    # [Implementation 4-1] DFS cycle 경로 복원
    def visit(node: str) -> list[str] | None:
        if node in visiting:
            start = positions[node]
            return stack[start:] + [node]
        if node in visited:
            return None
        visiting.add(node)
        positions[node] = len(stack)
        stack.append(node)
        for neighbor in graph.get(node, ()):
            cycle = visit(str(neighbor))
            if cycle is not None:
                return cycle
        stack.pop()
        positions.pop(node, None)
        visiting.remove(node)
        visited.add(node)
        return None

    nodes = set(graph)
    for neighbors in graph.values():
        nodes.update(str(item) for item in neighbors)
    for node in sorted(nodes):
        cycle = visit(node)
        if cycle is not None:
            return cycle
    return None


# [Implementation 4-2] 여러 instance deadlock 판정
def detect_deadlocked(
    available: Sequence[int],
    allocation: Mapping[str, Sequence[int]],
    outstanding: Mapping[str, Sequence[int]],
) -> set[str]:
    """현재 요청과 가용량으로 완료할 수 없는 작업을 반환합니다."""

    resource_count = _validate_vectors(available, allocation, outstanding)
    work = list(available)
    finish = {
        tid: all(value == 0 for value in allocation[tid])
        for tid in allocation
    }

    changed = True
    while changed:
        changed = False
        for tid in sorted(allocation):
            if finish[tid]:
                continue
            request = outstanding[tid]
            if all(request[index] <= work[index] for index in range(resource_count)):
                for index in range(resource_count):
                    work[index] += allocation[tid][index]
                finish[tid] = True
                changed = True

    return {tid for tid, completed in finish.items() if not completed}


# [Implementation 4-3] safe sequence 계산
def safe_sequence(
    available: Sequence[int],
    allocation: Mapping[str, Sequence[int]],
    maximum: Mapping[str, Sequence[int]],
) -> list[str] | None:
    """모든 작업의 최대 요구량을 만족할 수 있는 순서를 반환합니다."""

    if set(allocation) != set(maximum):
        raise DeadlockInputError("allocation and maximum contain different task sets")
    resource_count = _validate_vectors(available, allocation, maximum)
    need: dict[str, list[int]] = {}
    for tid in allocation:
        current = allocation[tid]
        limit = maximum[tid]
        if any(current[index] > limit[index] for index in range(resource_count)):
            raise DeadlockInputError(f"Allocation exceeds maximum need: {tid}")
        need[tid] = [
            limit[index] - current[index]
            for index in range(resource_count)
        ]

    work = list(available)
    remaining = set(allocation)
    order: list[str] = []
    while remaining:
        candidate = next(
            (
                tid
                for tid in sorted(remaining)
                if all(
                    need[tid][index] <= work[index]
                    for index in range(resource_count)
                )
            ),
            None,
        )
        if candidate is None:
            return None
        order.append(candidate)
        remaining.remove(candidate)
        for index in range(resource_count):
            work[index] += allocation[candidate][index]
    return order


def _validate_vectors(
    available: Sequence[int],
    left: Mapping[str, Sequence[int]],
    right: Mapping[str, Sequence[int]],
) -> int:
    if set(left) != set(right):
        raise DeadlockInputError("The two task sets differ")
    if not available:
        raise DeadlockInputError("At least one resource type is required")
    resource_count = len(available)
    if any(value < 0 for value in available):
        raise DeadlockInputError("Available resource counts cannot be negative")
    for name, vectors in (("left", left), ("right", right)):
        for tid, vector in vectors.items():
            if len(vector) != resource_count:
                raise DeadlockInputError(f"{name} vector has the wrong length: {tid}")
            if any(value < 0 for value in vector):
                raise DeadlockInputError(f"{name} vector contains a negative value: {tid}")
    return resource_count
