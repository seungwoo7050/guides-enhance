"""Graph traversal and nonnegative shortest paths."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Sequence
import heapq


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


# [Implementation 8]
# Nonnegative shortest-path expansion
def dijkstra(
    vertex_count: int,
    edges: Iterable[tuple[int, int, int]],
    start: int,
) -> list[int | None]:
    """Return directed shortest-path distances for nonnegative edge weights."""
    if vertex_count < 0:
        raise ValueError("vertex_count cannot be negative")
    _validate_vertex(vertex_count, start)

    graph: list[list[tuple[int, int]]] = [[] for _ in range(vertex_count)]
    for source, target, weight in edges:
        _validate_vertex(vertex_count, source)
        _validate_vertex(vertex_count, target)
        if weight < 0:
            raise ValueError("Dijkstra's algorithm does not allow negative weights")
        graph[source].append((target, weight))

    distances: list[int | None] = [None] * vertex_count
    distances[start] = 0
    queue: list[tuple[int, int]] = [(0, start)]
    while queue:
        current_distance, vertex = heapq.heappop(queue)
        # 현재 최단 거리와 다른 heap 항목은 더 짧은 경로가 이미 발견된 값이므로 확장하지 않습니다.
        if distances[vertex] != current_distance:
            continue
        for target, weight in graph[vertex]:
            candidate = current_distance + weight
            if distances[target] is None or candidate < distances[target]:
                distances[target] = candidate
                heapq.heappush(queue, (candidate, target))
    return distances
