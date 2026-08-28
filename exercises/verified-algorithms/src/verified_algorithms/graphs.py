"""Graph traversal, shortest paths, and minimum spanning trees."""

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


# [Implementation 9]
# Disjoint-set MST certificate
class _DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.component_size = [1] * size

    def find(self, vertex: int) -> int:
        root = vertex
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[vertex] != vertex:
            parent = self.parent[vertex]
            self.parent[vertex] = root
            vertex = parent
        return root

    def union(self, left: int, right: int) -> bool:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return False
        if self.component_size[left_root] < self.component_size[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        self.component_size[left_root] += self.component_size[right_root]
        return True


def kruskal_mst(
    vertex_count: int,
    edges: Iterable[tuple[int, int, int]],
) -> tuple[int, list[tuple[int, int, int]]]:
    """Return total weight and selected edges of an undirected MST."""
    if vertex_count < 0:
        raise ValueError("vertex_count cannot be negative")
    if vertex_count == 0:
        return 0, []

    normalized: list[tuple[int, int, int]] = []
    for source, target, weight in edges:
        _validate_vertex(vertex_count, source)
        _validate_vertex(vertex_count, target)
        normalized.append((source, target, weight))

    groups = _DisjointSet(vertex_count)
    chosen: list[tuple[int, int, int]] = []
    total_weight = 0
    for source, target, weight in sorted(
        normalized,
        key=lambda edge: (edge[2], edge[0], edge[1]),
    ):
        if groups.union(source, target):
            # 서로 다른 component를 실제로 합친 간선만 넣어야 선택 결과에 cycle이 생기지 않습니다.
            chosen.append((source, target, weight))
            total_weight += weight
            if len(chosen) == vertex_count - 1:
                break

    if len(chosen) != vertex_count - 1:
        raise ValueError("the graph is disconnected")
    return total_weight, chosen


# [Implementation 10]
# Bellman–Ford negative-cycle boundary
def bellman_ford(
    vertex_count: int,
    edges: Sequence[tuple[int, int, int]],
    start: int,
) -> list[int | None]:
    """Return shortest paths or reject a reachable negative-weight cycle."""
    if vertex_count < 0:
        raise ValueError("vertex_count cannot be negative")
    _validate_vertex(vertex_count, start)

    normalized = list(edges)
    for source, target, _weight in normalized:
        _validate_vertex(vertex_count, source)
        _validate_vertex(vertex_count, target)

    distances: list[int | None] = [None] * vertex_count
    distances[start] = 0
    for _ in range(max(0, vertex_count - 1)):
        changed = False
        for source, target, weight in normalized:
            if distances[source] is None:
                continue
            candidate = distances[source] + weight
            if distances[target] is None or candidate < distances[target]:
                distances[target] = candidate
                changed = True
        if not changed:
            break

    # 시작점에서 도달할 수 없는 음수 cycle은 이 single-source 결과에 영향을 주지 않습니다.
    for source, target, weight in normalized:
        if distances[source] is None:
            continue
        candidate = distances[source] + weight
        if distances[target] is None or candidate < distances[target]:
            raise ValueError("a negative-weight cycle is reachable from start")
    return distances
