"""Graph vertex validation and breadth-first traversal."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence


# [Implementation 7]
# Graph vertex contract and BFS state
def _validate_vertex(vertex_count: int, vertex: int) -> None:
    if not 0 <= vertex < vertex_count:
        raise ValueError(
            f"vertex {vertex} is outside the valid range 0..{vertex_count - 1}"
        )


def bfs_distances(
    graph: Sequence[Sequence[int]],
    start: int,
) -> list[int | None]:
    """Return minimum edge counts from ``start`` in a directed graph."""
    vertex_count = len(graph)
    _validate_vertex(vertex_count, start)
    for neighbors in graph:
        for target in neighbors:
            _validate_vertex(vertex_count, target)

    distances: list[int | None] = [None] * vertex_count
    distances[start] = 0
    queue: deque[int] = deque([start])
    while queue:
        vertex = queue.popleft()
        assert distances[vertex] is not None
        for target in graph[vertex]:
            if distances[target] is None:
                # 방문하지 않은 정점을 queue에 넣는 순간 최소 간선 수가 확정됩니다.
                distances[target] = distances[vertex] + 1
                queue.append(target)
    return distances
