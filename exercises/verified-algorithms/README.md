# Verified Algorithms

## 프로젝트 소개

`verified-algorithms`는 자료구조, 최적화, 그래프, 문자열 검색에서 자주 사용하는 알고리즘을 하나의 설치 가능한 Python 패키지로 제공합니다.

이 프로젝트가 특히 강조하는 것은 **알고리즘의 이름보다 함수 계약과 검증 근거를 명확히 하는 것**입니다. 각 함수는 다음을 구분합니다.

- 어떤 입력을 정상 입력으로 허용하는가
- 어떤 입력을 잘못된 입력으로 거부하는가
- 정상 입력 안에서 "답이 없음"을 어떻게 표현하는가
- 반환값이 만족해야 하는 불변식은 무엇인가
- 테스트가 구현과 독립적으로 결과를 어떻게 다시 확인하는가

프로젝트 이름의 `verified`는 **formal verification**을 뜻하지 않습니다. 정리 증명기나 형식 명세 언어로 프로그램 전체의 정확성을 증명한다는 의미가 아니라, 다음 요소를 함께 사용해 구현 결함을 발견하기 쉽게 만든다는 의미입니다.

```text
명시적인 입력 계약
알고리즘 불변식
독립적인 기준 계산
결정적인 반환 규칙
고정된 회귀 테스트
```

즉 이 프로젝트의 목표는 "검증된 알고리즘을 선언하는 것"이 아니라, **왜 결과를 신뢰할 수 있는지 다시 검사할 수 있는 구현과 테스트를 제공하는 것**입니다.

---

## 제공 기능

- `prefix_sums`, `range_sum`
  - 첫 원소가 `0`인 누적 합 배열을 만들고 반열린 구간 `[left, right)`의 합을 계산합니다.
- `lower_bound`
  - 오름차순으로 정렬된 수열에서 처음으로 `value >= target`을 만족하는 위치를 찾습니다.
- `RedBlackNode`, `red_black_height`
  - strict BST 순서와 red-black tree 규칙을 검사하고 black-height를 확인합니다.
- `knapsack_01`
  - 각 물건을 최대 한 번만 선택하는 0/1 knapsack의 최대 가치를 1차원 DP로 계산합니다.
- `select_intervals`
  - 가장 일찍 끝나는 구간부터 선택하는 greedy 방식으로 서로 겹치지 않는 구간의 최대 개수를 구합니다.
- `lcs_length`
  - 두 문자열의 longest common subsequence 길이를 계산하며, 추가 DP 공간을 더 짧은 문자열 길이에 맞춥니다.
- `bfs_distances`
  - directed unweighted graph에서 시작점부터 각 정점까지의 최소 간선 수를 계산합니다.
- `dijkstra`
  - 음수가 아닌 가중치를 가진 directed graph에서 시작점부터의 최단 거리를 계산합니다.
- `bellman_ford`
  - 음수 간선을 허용하지만, 시작점에서 도달 가능한 음수 cycle이 존재하면 입력을 거부합니다.
- `kruskal_mst`
  - undirected weighted graph의 MST 총가중치와 실제로 선택한 간선 목록을 반환합니다.
- `max_flow`
  - directed capacity graph에서 최대 유량 값과 원본 capacity에 대응하는 flow matrix를 반환합니다.
- `kmp_find`
  - KMP의 prefix fallback을 사용해 첫 문자열 일치 위치를 찾습니다.

각 함수는 가능한 한 **값만 반환하지 않고 그 값의 의미를 다시 확인할 수 있는 계약**을 갖도록 구성합니다.

---

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
| `strings.py` | KMP prefix table과 문자열 검색을 구현합니다. |
| `__init__.py` | 패키지의 공개 API를 한곳에서 다시 내보냅니다. |
| `tests/test_algorithms.py` | 경계 입력, 전수 계산, 독립 검증 함수를 제공합니다. |

`src/` layout을 사용하므로 source tree 자체와 설치된 package namespace를 구분합니다. 패키지를 설치하면 사용자는 `verified_algorithms`를 import하며, `src` 자체를 import하지 않습니다.

---

## 요구 사항

- Python 3.12 이상
- 패키지 빌드 시 `setuptools>=68`
- 실행 시 외부 의존성 없음

"실행 시 외부 의존성 없음"은 표준 라이브러리만으로 알고리즘 함수가 동작한다는 뜻입니다. 패키지 빌드에는 별도로 `setuptools`가 필요합니다.

---

## 설치

프로젝트 root에서 실행합니다.

```sh
python -m pip install --no-build-isolation .
```

`--no-build-isolation`은 pip가 별도의 임시 build environment를 만들지 않고 **현재 Python 환경에 설치된 build dependency**를 사용하도록 합니다.

따라서 현재 환경에 `pyproject.toml`이 요구하는 버전의 `setuptools`가 준비되어 있어야 합니다.

개발 중 source tree에서 테스트만 실행하는 경우에는 프로젝트 구성에 따라 package를 먼저 설치하지 않고도 테스트를 실행할 수 있습니다. 다만 실제 사용자와 같은 import 조건을 확인하려면 설치 후 테스트도 별도로 수행하는 편이 안전합니다.

---

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

# [1, 4) == values[1] + values[2] + values[3]
assert range_sum(prefix, 1, 4) == 10

# 첫 value >= 2의 위치
assert lower_bound([1, 2, 2, 7], 2) == 1

# 첫 문자열 일치 위치
assert kmp_find("abababac", "ababac") == 2

# 시작점 0에서 각 정점까지의 최단 거리
assert bellman_ford(
    4,
    [(0, 1, 4), (0, 2, 5), (1, 2, -2), (2, 3, 3)],
    0,
) == [0, 4, 2, 5]
```

`range_sum`의 구간은 Python slicing과 같은 **반열린 구간** `[left, right)`입니다. 왼쪽 끝은 포함하고 오른쪽 끝은 포함하지 않습니다.

`lower_bound`는 입력이 이미 오름차순으로 정렬되어 있다는 전제에서 동작합니다. 정렬되지 않은 입력을 자동으로 정렬하거나 정렬 여부를 검사하지 않습니다.

`kmp_find`는 첫 일치만 반환하며, 일치가 없으면 `-1`을 반환합니다. 빈 pattern은 위치 `0`에서 일치한다고 정의합니다.

`bellman_ford`의 반환 목록에서 도달할 수 없는 정점은 `None`으로 표현됩니다. 단, 시작점에서 도달 가능한 음수 cycle이 존재하면 정상적인 최단 거리 결과가 정의되지 않으므로 `ValueError`로 거부합니다.

---

## `max_flow`의 반환값

`max_flow`는 최대 유량 값만 반환하지 않습니다.

개념적으로 다음 두 정보를 함께 반환합니다.

```text
최대 유량 값
원본 directed capacity에 대응하는 flow matrix
```

반환된 `flow[u][v]`를 이용하면 최대 유량 값 자체뿐 아니라 다음 조건을 다시 확인할 수 있습니다.

### capacity 제약

원본 capacity가 `capacity[u][v]`라면 각 원본 방향에 대해 flow는 그 허용량을 넘지 않아야 합니다.

```text
0 <= flow[u][v] <= capacity[u][v]
```

### flow conservation

source와 sink를 제외한 각 중간 정점에서는 총 유입량과 총 유출량이 같아야 합니다.

```text
sum(incoming flow) == sum(outgoing flow)
```

즉 flow matrix는 결과값의 근거를 다시 검사할 수 있는 **certificate** 역할을 합니다.

---

## 테스트

프로젝트 root에서 다음 명령으로 테스트를 실행합니다.

```sh
python -m unittest discover -s tests -v
```

테스트의 핵심 원칙은 **후보 구현과 가능한 한 다른 계산 방법을 사용해 결과를 다시 구하는 것**입니다.

후보 구현과 테스트가 같은 핵심 알고리즘을 복사해 사용하면, 같은 결함이 양쪽에 존재할 때 테스트가 잘못된 결과를 정답으로 받아들일 수 있습니다.

이 프로젝트에서는 작은 입력을 대상으로 다음과 같은 독립 검증을 사용합니다.

- 누적 합은 각 구간의 원소를 직접 더합니다.
- Lower bound는 표준 라이브러리의 `bisect_left`와 비교합니다.
- 최단 경로는 Floyd–Warshall 결과와 비교합니다.
- Knapsack과 interval selection은 가능한 부분집합을 모두 검사합니다.
- MST는 `V-1`개 간선 조합을 모두 검사합니다.
- 최대 유량 값은 가능한 source-side cut을 모두 검사합니다.
- LCS는 짧은 문자열의 모든 subsequence를 검사합니다.
- Red-black tree는 별도의 재귀 validator로 규칙을 다시 확인합니다.
- KMP는 Python의 문자열 검색 결과와 비교합니다.

이러한 전수 계산은 큰 입력에는 비싸지만, 테스트 입력을 작게 제한하면 독립적인 oracle로 사용할 수 있습니다.

### 고정 seed

무작위 테스트는 고정 seed를 사용합니다.

이 방식은 무작위성을 없애는 것이 아니라 **동일한 pseudo-random 입력을 다시 생성할 수 있게 하는 것**입니다.

따라서 실패한 테스트를 같은 입력으로 반복 실행할 수 있고, 회귀 테스트에서도 결과가 흔들리지 않습니다.

---

## 주요 구현 결정

### 1. 잘못된 입력과 "답 없음"을 구분합니다

모든 실패 상황을 하나의 값으로 처리하지 않습니다.

예를 들어 다음은 **함수의 입력 계약을 위반한 경우**이므로 `ValueError`로 거부합니다.

- 범위를 벗어난 정점
- Dijkstra에 전달된 음수 간선
- 연결되지 않아 MST가 존재하지 않는 입력
- 시작점에서 도달 가능한 음수 cycle
- 형식이 잘못된 구간
- 정사각형이 아닌 capacity matrix
- 음수 capacity를 가진 matrix

반면 다음은 유효한 입력에서 발생할 수 있는 정상적인 상태입니다.

```text
어떤 정점에 도달할 수 없음
```

BFS와 최단 경로 함수는 이런 정점에 대해 `None`을 반환합니다.

이 차이는 중요합니다.

```text
ValueError
= 입력 자체가 함수의 계약을 만족하지 않음

None
= 입력은 유효하지만 해당 정점에 대한 경로가 존재하지 않음
```

호출자는 이 둘을 서로 다른 방식으로 처리할 수 있습니다.

---

### 2. 결정적인 반환 결과를 유지합니다

어떤 알고리즘은 최적해가 여러 개 존재할 수 있습니다.

예를 들어 interval scheduling에서 같은 최대 개수를 만드는 구간 집합이 여러 개 있을 수 있고, MST도 같은 총가중치를 갖는 여러 tree가 존재할 수 있습니다.

이 프로젝트는 테스트와 사용자 경험을 안정적으로 만들기 위해 tie-breaking 순서를 고정합니다.

`select_intervals`는 다음 순서로 구간을 봅니다.

```text
(end, start)
```

즉 종료 시각이 빠른 구간을 먼저 보고, 종료 시각이 같다면 시작 시각으로 순서를 고정합니다.

`kruskal_mst`는 다음 순서로 간선을 봅니다.

```text
(weight, source, target)
```

따라서 같은 입력에는 항상 같은 선택 순서가 적용되고, 동일한 간선 목록이 반환됩니다.

이 결정성은 알고리즘의 최적성 자체와는 별개의 API 특성입니다. 여러 최적해 중 **어느 하나를 항상 같은 규칙으로 선택한다**는 의미입니다.

---

### 3. 한 번만 순회할 수 있는 `Iterable`을 고려합니다

Python의 `Iterable`은 항상 여러 번 순회할 수 있는 container라는 뜻이 아닙니다.

예를 들어 generator는 보통 한 번 소비하면 같은 원소를 다시 제공하지 않습니다.

```python
edges = ((u, v, w) for u, v, w in source)
```

따라서 함수 구현이 입력을 두 번 이상 순회해야 한다면 처음에 자료를 저장해야 합니다.

`dijkstra`와 `kruskal_mst`는 `Iterable`로 받은 간선을 함수 안에서 필요한 자료구조로 저장합니다.

`bellman_ford`는 relaxation 과정에서 같은 전체 간선 목록을 반복해서 순회해야 하므로 처음에 다음과 같이 고정하는 방식이 필요합니다.

```python
edges = list(edges)
```

이 결정은 단순한 최적화가 아니라 **입력 타입의 의미를 올바르게 지키기 위한 처리**입니다.

---

### 4. 값뿐 아니라 certificate도 검증합니다

최적화 문제에서는 최종 숫자 하나만 맞다고 해서 반환 구조 전체가 올바르다고 단정할 수 없습니다.

#### MST

MST 테스트는 총가중치만 비교하지 않습니다.

반환한 간선 목록에 대해 다음을 다시 확인합니다.

```text
모든 간선이 원본 입력에 존재함
정점이 V개라면 간선이 정확히 V-1개임
cycle이 없음
모든 정점이 연결됨
총가중치가 최적값과 같음
```

즉 반환한 간선 집합 자체가 실제 spanning tree인지 검증합니다.

#### 최대 유량

최대 유량도 값만 비교하지 않습니다.

flow matrix가 다음을 만족하는지 검사합니다.

```text
capacity 제한을 넘지 않음
중간 정점의 flow conservation을 만족함
source에서 빠져나간 순유량이 반환된 최대 유량 값과 일치함
```

이처럼 결과 구조가 정답 조건을 만족한다는 증거를 함께 반환하면 테스트는 더 강한 조건을 확인할 수 있습니다.

---

### 5. 독립적인 기준 계산을 사용합니다

후보 구현과 테스트 oracle이 같은 핵심 알고리즘을 공유하면 다음과 같은 위험이 있습니다.

```text
후보 구현에 결함이 있음
테스트 구현에도 같은 결함이 있음
두 결과가 같음
테스트가 통과함
```

이를 피하기 위해 이 프로젝트는 가능한 경우 작은 입력에서 전수 계산이나 다른 알고리즘을 사용합니다.

예를 들어 Dijkstra를 테스트할 때 Dijkstra를 다시 구현하는 대신 Floyd–Warshall로 전체 쌍 최단 거리를 계산합니다.

MST를 테스트할 때 Kruskal을 다시 쓰는 대신 가능한 `V-1`개 간선 조합을 검사합니다.

이 방식의 목적은 "oracle이 절대로 틀리지 않는다"는 보장이 아니라, **같은 구현 아이디어에 의존해 같은 결함을 공유할 가능성을 줄이는 것**입니다.

---

## 알고리즘별 핵심 계약

이 절은 각 함수에서 가장 먼저 확인해야 할 입력 전제와 반환 의미를 요약합니다.

| 기능 | 핵심 입력 전제 | 정상적인 "없음" 표현 | 잘못된 입력 예 |
| --- | --- | --- | --- |
| `range_sum` | prefix와 구간 index가 유효해야 함 | 해당 없음 | 잘못된 구간 |
| `lower_bound` | 입력이 오름차순 정렬 | `len(values)`가 반환될 수 있음 | 정렬 여부는 검사하지 않음 |
| Red-black 검증 | strict BST와 허용된 color 사용 | 해당 없음 | 잘못된 tree 규칙 |
| `knapsack_01` | 0/1 선택 문제 계약을 만족 | 최대값 반환 | 잘못된 항목 입력 |
| `select_intervals` | 각 구간의 형식이 유효 | 빈 선택 가능 | 잘못된 구간 |
| `lcs_length` | 두 문자열 입력 | 길이 `0` 가능 | 별도 "없음" 없음 |
| `bfs_distances` | 유효한 directed graph 정점 | 도달 불가 정점은 `None` | 범위 밖 정점 |
| `dijkstra` | 모든 간선 가중치가 음수 아님 | 도달 불가 정점은 `None` | 음수 간선 |
| `bellman_ford` | directed weighted graph | 도달 불가 정점은 `None` | 도달 가능한 음수 cycle |
| `kruskal_mst` | 연결 가능한 undirected graph | 해당 없음 | 연결되지 않은 graph |
| `max_flow` | square, nonnegative integer capacity matrix | 최대 유량 `0` 가능 | 음수 또는 비정상 matrix |
| `kmp_find` | 문자열 입력 | 일치 없음은 `-1` | 빈 pattern은 오류가 아니라 `0` |

이 표는 전체 구현 세부사항을 대체하지 않고, 각 API를 읽을 때 먼저 확인할 경계를 정리한 것입니다.

---

## Implementation Order

아래 순서는 파일의 단순 나열 순서가 아닙니다.

패키지를 처음부터 구현할 때 필요한 **의존 관계와 검증 순서**를 기준으로 정리했습니다. 표의 영어 이름은 source annotation과 정확히 일치합니다.

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

이 순서에서 `Primary anchor`는 해당 단계의 핵심 구현 위치를 뜻합니다. 한 단계의 모든 검증 코드가 반드시 그 파일 안에만 있다는 뜻은 아닙니다.

---

## 지원 범위와 제한

현재 프로젝트는 다음 범위만 지원합니다.

- `lower_bound`는 입력이 오름차순으로 정렬되어 있다고 가정하며 정렬 여부를 검사하지 않습니다.
- `RedBlackNode`는 정수 key와 `"red"`, `"black"` color만 사용합니다.
- BFS, Dijkstra, Bellman–Ford의 간선은 directed edge로 해석합니다.
- `kruskal_mst`의 간선은 undirected connection으로 해석하며 parallel edge를 허용합니다.
- `max_flow`는 음수가 아닌 정수 capacity matrix를 사용합니다.
- `kmp_find`는 첫 일치 위치만 반환하며, 모든 일치 위치 검색이나 streaming KMP는 제공하지 않습니다.
- 이 패키지는 알고리즘 library이며 CLI, 저장 기능, 시각화, benchmark runner는 제공하지 않습니다.

이 제한은 구현이 불완전하다는 의미가 아니라 **현재 공개 API가 의도적으로 다루는 문제 범위**입니다.

범위를 넓힐 때는 단순히 기능을 추가하는 것보다 다음 계약도 함께 확장해야 합니다.

```text
새 입력을 어떤 형식으로 허용하는가
기존 반환 규칙과 충돌하지 않는가
새 실패 조건은 무엇인가
독립적으로 검증할 방법이 있는가
결과가 여전히 결정적인가
```

---

## 학습할 때 확인할 질문

이 프로젝트를 알고리즘 모음으로만 읽지 말고, 각 구현에서 다음 질문을 확인합니다.

```text
이 함수의 입력 전제는 무엇입니까?
잘못된 입력과 정상적인 "답 없음"은 어떻게 구분합니까?
반복 중 유지되는 불변식은 무엇입니까?
여러 정답이 있을 때 반환 결과를 어떻게 고정합니까?
Iterable을 한 번 이상 순회합니까?
반환값 자체를 다시 검증할 certificate가 있습니까?
테스트 oracle은 후보 구현과 충분히 독립적입니까?
작은 입력에서 전수 계산으로 확인할 수 있습니까?
```

이 질문에 답할 수 있으면 단순히 알고리즘의 결과만 아는 것이 아니라, **구현의 계약과 검증 근거까지 이해한 것**입니다.
