"""Range preprocessing and ordered-search algorithms."""

from __future__ import annotations

from collections.abc import Sequence


# [Implementation 1]
# Prefix-sum range model
def prefix_sums(values: Sequence[int]) -> list[int]:
    """Return a prefix array whose first element is the zero sentinel."""
    prefix = [0]
    total = 0
    for value in values:
        total += value
        prefix.append(total)
    return prefix


def range_sum(prefix: Sequence[int], start: int, stop: int) -> int:
    """Return the sum represented by the half-open range ``[start, stop)``."""
    if start < 0 or stop < start or stop >= len(prefix):
        raise ValueError("expected 0 <= start <= stop < len(prefix)")

    # 첫 원소가 0이므로 빈 구간과 전체 구간을 같은 두 값의 차이로 계산합니다.
    return prefix[stop] - prefix[start]


# [Implementation 2]
# Lower-bound search invariant
def lower_bound(values: Sequence[int], target: int) -> int:
    """Return the first index whose value is greater than or equal to ``target``.

    ``values`` must already be sorted in ascending order.
    """
    low = 0
    high = len(values)

    # 첫 삽입 위치가 항상 [low, high) 안에 남도록 두 끝점을 줄입니다.
    while low < high:
        middle = low + (high - low) // 2
        if values[middle] < target:
            low = middle + 1
        else:
            high = middle
    return low
