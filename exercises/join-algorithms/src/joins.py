from __future__ import annotations

from collections import defaultdict
from typing import Any, TypeAlias

Row: TypeAlias = dict[str, Any]
Joined: TypeAlias = tuple[Row, Row]


# [Implementation 1] nested-loop join을 결과 기준으로 구현합니다.
# 모든 행 조합을 직접 비교해 중복 개수와 SQL의 NULL 불일치 의미를 가장 단순하게 보존합니다.
def nested_loop_join(
    left: list[Row],
    right: list[Row],
    left_key: str,
    right_key: str,
) -> list[Joined]:
    result: list[Joined] = []
    for left_row in left:
        left_value = left_row.get(left_key)
        if left_value is None:
            continue
        for right_row in right:
            right_value = right_row.get(right_key)
            if right_value is not None and left_value == right_value:
                result.append((left_row, right_row))
    return result


# [Implementation 2] 작은 입력을 build side로 선택하는 hash join을 구현합니다.
# 어느 쪽을 hash table에 넣더라도 반환 tuple의 순서는 항상 (left, right)로 유지합니다.
def hash_join(
    left: list[Row],
    right: list[Row],
    left_key: str,
    right_key: str,
) -> list[Joined]:
    if len(left) <= len(right):
        buckets: dict[Any, list[Row]] = defaultdict(list)
        for row in left:
            value = row.get(left_key)
            if value is not None:
                buckets[value].append(row)
        return [
            (left_row, right_row)
            for right_row in right
            if (value := right_row.get(right_key)) is not None
            for left_row in buckets.get(value, ())
        ]

    buckets = defaultdict(list)
    for row in right:
        value = row.get(right_key)
        if value is not None:
            buckets[value].append(row)
    return [
        (left_row, right_row)
        for left_row in left
        if (value := left_row.get(left_key)) is not None
        for right_row in buckets.get(value, ())
    ]


# [Implementation 3] 같은 key 구간을 모두 결합하는 merge join을 구현합니다.
# 양쪽의 동일 key run 전체를 소비해 중복 key의 모든 조합을 반환합니다.
def merge_join(
    left: list[Row],
    right: list[Row],
    left_key: str,
    right_key: str,
) -> list[Joined]:
    left_rows = sorted(
        (row for row in left if row.get(left_key) is not None),
        key=lambda row: row[left_key],
    )
    right_rows = sorted(
        (row for row in right if row.get(right_key) is not None),
        key=lambda row: row[right_key],
    )
    result: list[Joined] = []
    left_index = right_index = 0

    while left_index < len(left_rows) and right_index < len(right_rows):
        left_value = left_rows[left_index][left_key]
        right_value = right_rows[right_index][right_key]
        if left_value < right_value:
            left_index += 1
            continue
        if left_value > right_value:
            right_index += 1
            continue

        left_end = left_index
        while left_end < len(left_rows) and left_rows[left_end][left_key] == left_value:
            left_end += 1
        right_end = right_index
        while right_end < len(right_rows) and right_rows[right_end][right_key] == right_value:
            right_end += 1

        for left_row in left_rows[left_index:left_end]:
            for right_row in right_rows[right_index:right_end]:
                result.append((left_row, right_row))
        left_index, right_index = left_end, right_end

    return result
