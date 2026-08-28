# Verified Algorithms

## 프로젝트 소개

`verified-algorithms`는 자료구조, 최적화, 그래프, 문자열 검색에서 자주 사용하는 알고리즘을 하나의 설치 가능한 Python 패키지로 제공합니다. 각 함수는 허용하는 입력과 실패 조건을 명확히 구분하며, 테스트는 작은 입력을 다른 방법으로 계산해 구현 결과를 확인합니다.

프로젝트 이름의 `verified`는 formal verification을 뜻하지 않습니다. 입력 조건, 알고리즘 불변식, 독립적인 기준 계산, 고정된 회귀 테스트를 함께 사용한다는 의미입니다.

## 제공 기능

- `prefix_sums`, `range_sum`: 첫 원소가 `0`인 누적 합으로 반열린 구간의 합을 계산합니다.
- `lower_bound`: 정렬된 수열에서 첫 `value >= target` 위치를 찾습니다.
- `RedBlackNode`, `red_black_height`: strict BST 순서와 red-black tree 규칙을 검사합니다.
- `knapsack_01`: 1차원 DP로 0/1 knapsack의 최대 가치를 계산합니다.
- `select_intervals`: 가장 일찍 끝나는 구간부터 선택해 서로 겹치지 않는 구간의 최대 개수를 구합니다.
- `lcs_length`: 두 문자열의 LCS 길이를 계산하며 추가 공간을 짧은 문자열 길이에 맞춥니다.
- `bfs_distances`: directed unweighted graph에서 시작점부터의 최소 간선 수를 계산합니다.
- `dijkstra`: 음수가 아닌 가중치를 가진 directed graph의 최단 거리를 계산합니다.
- `bellman_ford`: 음수 간선을 허용하며 시작점에서 도달 가능한 음수 cycle을 거부합니다.
- `kruskal_mst`: MST의 총가중치와 선택한 간선 목록을 반환합니다.
- `max_flow`: 최대 유량 값과 원본 directed capacity에 대응하는 flow matrix를 반환합니다.
- `kmp_find`: KMP prefix fallback으로 첫 문자열 일치 위치를 찾습니다.

## 디렉터리 구성

```text
verified-algorithms/
├── pyproject.toml
├── README.md
├── src/verified_algorithms/
│   ├── __init__.py
│   ├── graphs.py
│   ├── optimization.py
│   ├── ranges.py
│   ├── strings.py
│   └── trees.py
└── tests/
    └── test_algorithms.py
```

| 파일 | 역할 |
| --- | --- |
| `ranges.py` | 누적 합과 lower-bound 탐색을 구현합니다. |
| `trees.py` | Red-black node와 검증 함수를 제공합니다. |
| `optimization.py` | Knapsack, interval selection, LCS를 구현합니다. |
| `graphs.py` | 정점 검증, BFS, 최단 경로, MST, 최대 유량을 구현합니다. |
| `strings.py` | KMP 전처리와 검색을 구현합니다. |
| `__init__.py` | 공개 API를 한곳에서 내보냅니다. |
| `tests/test_algorithms.py` | 경계 입력, 전수 계산, 독립 검증 함수를 제공합니다. |

## 요구 사항

- Python 3.12 이상
- 패키지 빌드 시 `setuptools>=68`
- 실행 시 외부 의존성 없음

## 설치

프로젝트 root에서 실행합니다.

```sh
python -m pip install --no-build-isolation .
```

`--no-build-isolation`은 현재 Python 환경의 `setuptools`를 사용합니다. 소스 디렉터리에서 테스트만 실행할 때는 package를 먼저 설치하지 않아도 됩니다.

## 사용 예시

```python
from verified_algorithms import (
    bellman_ford,
    kmp_find,
    lower_bound,
    prefix_sums,
    range_sum,
)

values = [3, -2, 5, 7]
prefix = prefix_sums(values)
assert range_sum(prefix, 1, 4) == 10

assert lower_bound([1, 2, 2, 7], 2) == 1
assert kmp_find("abababac", "ababac") == 2

assert bellman_ford(
    4,
    [(0, 1, 4), (0, 2, 5), (1, 2, -2), (2, 3, 3)],
    0,
) == [0, 4, 2, 5]
```

`max_flow`는 최대 유량 값만 반환하지 않습니다. 함께 반환하는 `flow[u][v]`를 사용하면 각 원본 간선의 capacity 제한과 중간 정점의 유입·유출 일치를 다시 검사할 수 있습니다.

## 테스트

```sh
python -m unittest discover -s tests -v
```

테스트는 후보 구현과 다른 계산 방법을 사용합니다.

- 누적 합은 각 구간을 직접 더합니다.
- Lower bound는 `bisect_left`와 비교합니다.
- 최단 경로는 Floyd–Warshall로 계산합니다.
- Knapsack과 interval selection은 가능한 부분집합을 모두 검사합니다.
- MST는 `V-1`개 간선 조합을 모두 검사합니다.
- 최대 유량은 가능한 source-side cut을 모두 검사합니다.
- LCS는 짧은 문자열의 모든 subsequence를 검사합니다.
- Red-black tree는 별도 재귀 validator로 규칙을 다시 확인합니다.

무작위 입력은 고정 seed를 사용하므로 같은 실패를 다시 실행할 수 있습니다.

## 주요 구현 결정

### 잘못된 입력과 답 없음의 구분

범위를 벗어난 정점, Dijkstra의 음수 간선, 연결되지 않은 MST 입력, 시작점에서 도달 가능한 음수 cycle, 잘못된 구간, 정사각형이 아니거나 음수 값을 가진 capacity matrix는 `ValueError`로 거부합니다.

반면 도달할 수 없는 정점은 정상적인 결과입니다. BFS와 최단 경로 함수는 해당 위치에 `None`을 반환합니다.

### 결정적인 반환 결과

`select_intervals`는 `(end, start)` 순서로 구간을 봅니다. `kruskal_mst`는 `(weight, source, target)` 순서로 간선을 봅니다. 따라서 같은 입력에는 같은 구간 목록과 간선 목록을 반환합니다.

### 한 번만 순회할 수 있는 입력 처리

`dijkstra`와 `kruskal_mst`는 `Iterable`로 받은 간선을 함수 안에서 필요한 형태로 저장합니다. `bellman_ford`는 같은 간선 목록을 여러 번 순회해야 하므로 처음에 `list`로 고정합니다.

### 값뿐 아니라 certificate도 검증

MST는 총가중치만 맞는지 확인하지 않습니다. 반환한 간선이 원본에 있고, `V-1`개이며, 연결된 cycle 없는 tree인지 검사합니다.

최대 유량도 값만 비교하지 않습니다. 반환한 matrix가 capacity를 넘지 않고 각 중간 정점에서 유입량과 유출량이 같은지 확인합니다.

### 독립적인 기준 계산

후보 구현과 테스트가 같은 핵심 알고리즘을 공유하면 같은 결함을 함께 가질 수 있습니다. 이 프로젝트는 작은 입력에서 전수 계산이나 다른 알고리즘을 사용해 그 가능성을 줄입니다.

## Implementation Order

아래 순서는 파일 나열 순서가 아닙니다. Package를 처음부터 만들 때 필요한 의존 관계와 검증 순서에 따라 정리했습니다. 표의 영어 이름은 source annotation과 정확히 일치합니다.

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 0 | Installable package boundary | `pyproject.toml` |
| 1 | Prefix-sum range model | `src/verified_algorithms/ranges.py` |
| 2 | Lower-bound search invariant | `src/verified_algorithms/ranges.py` |
| 3 | Red-black tree validation contract | `src/verified_algorithms/trees.py` |
| 4 | 0/1 knapsack state transition | `src/verified_algorithms/optimization.py` |
| 5 | Earliest-finish interval selection | `src/verified_algorithms/optimization.py` |
| 6 | Space-bounded LCS recurrence | `src/verified_algorithms/optimization.py` |
| 7 | Graph vertex contract and BFS state | `src/verified_algorithms/graphs.py` |
| 8 | Nonnegative shortest-path expansion | `src/verified_algorithms/graphs.py` |
| 9 | Disjoint-set MST certificate | `src/verified_algorithms/graphs.py` |
| 10 | Bellman–Ford negative-cycle boundary | `src/verified_algorithms/graphs.py` |
| 11 | Directed max-flow certificate | `src/verified_algorithms/graphs.py` |
| 12 | KMP prefix fallback | `src/verified_algorithms/strings.py` |
| 13 | Public API composition | `src/verified_algorithms/__init__.py` |
| 14 | Independent contract verification | `tests/test_algorithms.py` |

## 지원 범위와 제한

- `lower_bound`는 입력이 오름차순으로 정렬되어 있다고 가정하며 정렬 여부를 검사하지 않습니다.
- `RedBlackNode`는 정수 key와 `"red"`, `"black"` color만 사용합니다.
- BFS, Dijkstra, Bellman–Ford의 간선은 directed edge로 해석합니다.
- `kruskal_mst`의 간선은 undirected connection으로 해석하며 parallel edge를 허용합니다.
- `max_flow`는 음수가 아닌 정수 capacity matrix를 사용합니다.
- 이 패키지는 알고리즘 library입니다. CLI, 저장 기능, 시각화, benchmark runner는 제공하지 않습니다.
