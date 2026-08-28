"""Stable public API for the verified-algorithms package."""

# [Implementation 13]
# Public API composition
from .graphs import bellman_ford, bfs_distances, dijkstra, kruskal_mst, max_flow
from .optimization import knapsack_01, lcs_length, select_intervals
from .ranges import lower_bound, prefix_sums, range_sum
from .strings import kmp_find
from .trees import RedBlackNode, red_black_height

__all__ = [
    "RedBlackNode",
    "bellman_ford",
    "bfs_distances",
    "dijkstra",
    "kmp_find",
    "knapsack_01",
    "kruskal_mst",
    "lcs_length",
    "lower_bound",
    "max_flow",
    "prefix_sums",
    "range_sum",
    "red_black_height",
    "select_intervals",
]
