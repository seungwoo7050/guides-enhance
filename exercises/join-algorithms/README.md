# Join Algorithms

같은 inner equi-join을 nested-loop, hash join, merge join으로 구현한 Python 라이브러리입니다. 세 함수 모두 SQL과 같이 `NULL` key끼리는 일치시키지 않으며, 같은 key가 여러 번 나오면 가능한 모든 좌우 행 조합을 반환합니다.

## 주요 기능

- 결과 기준으로 사용할 수 있는 nested-loop join
- 작은 입력을 build side로 선택하는 hash join
- 동일 key 구간 전체를 결합하는 merge join
- 어느 알고리즘을 사용해도 `(left_row, right_row)` 반환 순서 유지
- list 순서가 아니라 행 쌍의 중복 개수로 결과 비교

## 구성

세 함수는 `list[dict]` 두 개를 입력받고 `(left_row, right_row)` tuple 목록을 반환합니다. Nested-loop join은 모든 조합을 직접 비교하므로 결과의 기준으로 사용합니다. Hash join은 작은 입력을 hash table에 넣어 메모리 사용량을 줄입니다. Merge join은 `NULL`을 제외한 입력을 정렬하고 같은 key 구간끼리 곱집합을 만듭니다.

## 설치와 사용

Python 3.11 이상이 필요합니다.

```bash
python3 -m pip install -e .
```

```python
from joins import hash_join

users = [{"id": 1}, {"id": 2}]
orders = [{"id": 10, "user_id": 1}, {"id": 11, "user_id": 1}]

rows = hash_join(users, orders, "id", "user_id")
assert [(user["id"], order["id"]) for user, order in rows] == [
    (1, 10),
    (1, 11),
]
```

## 테스트

```bash
make test
```

테스트는 중복 key의 조합 수, `NULL`, 빈 입력, build side 전환과 key가 치우친 무작위 입력에서 세 알고리즘의 결과가 같은지 확인합니다.

## 설계에서 확인할 점

- 알고리즘이 반환하는 list 순서는 비교 대상이 아닙니다. Hash table 삽입 순서나 정렬 결과가 다를 수 있으므로 테스트는 행 쌍을 `Counter`로 바꿔 중복 개수를 비교합니다.
- Hash join이 어느 입력을 build side로 고르더라도 외부 반환 값은 항상 `(left, right)`입니다.
- Merge join은 같은 key의 첫 행만 결합하지 않습니다. 양쪽 run 전체를 소비해야 결과 수가 `left_count × right_count`가 됩니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | nested-loop 결과 기준 구현 | `src/joins.py` · `nested_loop_join` |
| 2 | 작은 입력을 build하는 hash join | `src/joins.py` · `hash_join` |
| 3 | 동일 key 구간을 모두 결합하는 merge join | `src/joins.py` · `merge_join` |
| 4 | 세 알고리즘의 bag 단위 결과 검증 | `tests/test_joins.py` · `JoinAlgorithmTests` |

## 범위와 제한

이 프로젝트는 메모리 안에서 처리하는 inner equi-join만 제공합니다. Outer join, 부등호 조건, disk spill, partitioned hash join, external sort와 비용에 따른 알고리즘 선택은 포함하지 않습니다.
