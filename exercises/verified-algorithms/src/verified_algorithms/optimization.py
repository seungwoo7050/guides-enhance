"""Greedy and dynamic-programming algorithms."""

from __future__ import annotations

from collections.abc import Sequence


# [Implementation 4]
# 0/1 knapsack state transition
def knapsack_01(items: Sequence[tuple[int, int]], capacity: int) -> int:
    """Return the maximum value obtainable without reusing an item."""
    if capacity < 0:
        raise ValueError("capacity cannot be negative")
    for weight, _value in items:
        if weight <= 0:
            raise ValueError("item weights must be positive")

    best = [0] * (capacity + 1)
    for weight, value in items:
        # capacity를 큰 값부터 갱신해야 현재 물건의 새 값을 같은 반복에서 다시 읽지 않습니다.
        for current_capacity in range(capacity, weight - 1, -1):
            best[current_capacity] = max(
                best[current_capacity],
                best[current_capacity - weight] + value,
            )
    return best[capacity]


# [Implementation 5]
# Earliest-finish interval selection
def select_intervals(
    intervals: Sequence[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Return a maximum-cardinality set of non-overlapping half-open intervals."""
    normalized = list(intervals)
    if any(start >= stop for start, stop in normalized):
        raise ValueError("every interval must satisfy start < stop")

    selected: list[tuple[int, int]] = []
    last_stop: int | None = None
    # 같은 종료 시각에는 시작 시각으로 순서를 정해 반환 결과를 항상 같게 만듭니다.
    for interval in sorted(normalized, key=lambda item: (item[1], item[0])):
        start, stop = interval
        if last_stop is None or start >= last_stop:
            selected.append(interval)
            last_stop = stop
    return selected


# [Implementation 6]
# Space-bounded LCS recurrence
def lcs_length(left: str, right: str) -> int:
    """Return the length of the longest common subsequence."""
    if len(right) > len(left):
        left, right = right, left

    # 짧은 문자열을 열로 사용하면 recurrence를 바꾸지 않고 추가 공간을 줄일 수 있습니다.
    previous = [0] * (len(right) + 1)
    for left_character in left:
        current = [0]
        for index, right_character in enumerate(right, start=1):
            if left_character == right_character:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current
    return previous[-1]
