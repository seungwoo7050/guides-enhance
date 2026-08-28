# 학습 로드맵

## 목표

이 과정의 목표는 특정 문제의 풀이를 기억하는 것이 아니라, 낯선 문제에서도 다음 판단을 반복할 수 있게 만드는 것입니다.

```text
입력과 출력 조건을 정합니다.
→ 입력 크기에서 목표 복잡도를 계산합니다.
→ 필요한 연산과 상태를 고릅니다.
→ 정확성 근거를 적고 구현합니다.
→ 다른 계산 방법과 경계 입력으로 검증합니다.
```

최종 확인 대상은 [`verified-algorithms`](../exercises/verified-algorithms/)입니다. 문서를 모두 읽은 뒤 한꺼번에 구현하지 않고, 각 함수군에 필요한 개념을 익힌 즉시 구현합니다.

## 선행지식

- 하나 이상의 언어로 함수, 조건문, 반복문, 배열 또는 list를 작성할 수 있어야 합니다.
- 작은 입력에서 변수 값과 자료구조의 변화를 손으로 추적할 수 있어야 합니다.
- exercise를 실행하려면 Python 3.12 이상이 필요합니다.

Python과 C++ 문법 입문은 이 저장소의 범위가 아닙니다. 언어별 주의 사항은 `docs/90-implementation-profiles/`에서 확인합니다.

## 종료 능력

필수 과정을 마치면 다음을 자료 없이 수행할 수 있어야 합니다.

- 답 없음과 잘못된 입력을 구분한 함수 조건을 작성합니다.
- 입력 변수의 의미를 먼저 정한 뒤 시간과 추가 공간을 계산합니다.
- lower bound, tree 검증, greedy, DP, graph relaxation, max flow, KMP의 핵심 불변식을 설명합니다.
- 작은 입력의 전수 계산 또는 다른 알고리즘으로 기준 결과를 만듭니다.
- 실패 입력을 줄여 원인이 드러나는 회귀 테스트로 남깁니다.
- 구현을 보지 않고 핵심 함수군을 다시 작성해 전체 테스트를 통과합니다.

## 진행 순서

### 0단계. 저장소와 프로젝트 확인

1. 이 문서를 읽습니다.
2. [`verified-algorithms/README.md`](../exercises/verified-algorithms/README.md)의 공개 API와 `Implementation Order`를 확인합니다.
3. package 설치와 테스트 명령이 현재 환경에서 실행되는지 확인합니다.

아직 기준 구현을 외우려 하지 않습니다. 먼저 각 함수가 어떤 입력을 받고 무엇을 반환하는지만 확인합니다.

### 1단계. 문제 분석과 비용 계산

필수 문서:

- [`01-problem-contracts-and-counterexamples.md`](01-foundations/01-problem-contracts-and-counterexamples.md)
- [`02-asymptotic-analysis.md`](01-foundations/02-asymptotic-analysis.md)
- [`04-correctness-and-invariants.md`](01-foundations/04-correctness-and-invariants.md)

확인할 내용:

- 입력, 출력, 답 없음, 잘못된 입력, 동점 규칙을 구분합니다.
- 단순 기준 계산과 목표 구현이 같은 핵심 로직을 공유하지 않게 합니다.
- 반복 불변식과 종료 조건을 별도로 작성합니다.

이 단계가 끝나면 `pyproject.toml`의 `[Implementation 0]`을 확인하고 패키지 구성을 이해합니다.

### 2단계. 누적 합, 정렬과 탐색

필수 문서:

- [`01-linear-structures-ranges-and-hashing.md`](02-data-structures/01-linear-structures-ranges-and-hashing.md)
- [`01-sorting-stability-and-lower-bounds.md`](06-complexity/01-sorting-stability-and-lower-bounds.md)
- [`02-order-search-heaps-and-priority.md`](02-data-structures/02-order-search-heaps-and-priority.md)

구현:

- `[Implementation 1]` `prefix_sums`, `range_sum`
- `[Implementation 2]` `lower_bound`

검증:

- 빈 구간, 전체 구간, 잘못된 범위를 확인합니다.
- 중복 값과 양끝 target에서 `bisect_left`와 결과를 비교합니다.
- 정렬 여부는 `lower_bound`의 호출자 전조건이라는 점을 설명합니다.

### 3단계. 재귀, tree와 DSU

필수 문서:

- [`03-recurrences-and-divide-and-conquer.md`](01-foundations/03-recurrences-and-divide-and-conquer.md)
- [`03-trees-and-balanced-search-trees.md`](02-data-structures/03-trees-and-balanced-search-trees.md)
- [`04-disjoint-sets-and-amortized-analysis.md`](02-data-structures/04-disjoint-sets-and-amortized-analysis.md)

구현:

- `[Implementation 3]` `RedBlackNode`, `red_black_height`

검증:

- BST 허용 범위를 자식 호출에 전달합니다.
- root 색, red-red, 잘못된 색, black height 차이를 각각 거부합니다.
- DSU의 `parent`와 component size 변화는 뒤의 Kruskal 구현을 준비하며 손으로 추적합니다.

### 4단계. 완전탐색, greedy와 DP

필수 문서:

- [`01-brute-force-and-backtracking.md`](03-design-techniques/01-brute-force-and-backtracking.md)
- [`02-greedy-methods.md`](03-design-techniques/02-greedy-methods.md)
- [`03-dynamic-programming.md`](03-design-techniques/03-dynamic-programming.md)

구현:

- `[Implementation 4]` `knapsack_01`
- `[Implementation 5]` `select_intervals`
- `[Implementation 6]` `lcs_length`

검증:

- knapsack과 interval selection은 작은 부분집합을 모두 열거한 결과와 비교합니다.
- LCS는 짧은 문자열의 모든 subsequence를 검사한 결과와 비교합니다.
- 0/1 knapsack에서 capacity를 오름차순으로 갱신했을 때 같은 물건이 재사용되는 최소 입력을 찾습니다.
- 시작 시간이 빠른 구간부터 선택하는 greedy가 실패하는 입력을 찾습니다.

### 5단계. 그래프 표현과 순회

필수 문서:

- [`01-traversal-and-topological-order.md`](04-graph-algorithms/01-traversal-and-topological-order.md)

구현:

- `[Implementation 7]` `_validate_vertex`, `bfs_distances`

검증:

- 정점 번호와 모든 인접 정점을 먼저 검사합니다.
- queue에 넣는 시점에 방문 처리를 해야 하는 이유를 설명합니다.
- 도달할 수 없는 정점은 거리 `0`이 아니라 `None`으로 남깁니다.

exercise의 공개 API에는 DFS와 topological sort가 없습니다. 따라서 directed cycle을 찾는 `unseen/active/finished` 상태와 Kahn 알고리즘의 실패 조건은 별도 작은 코드로 확인합니다.

### 6단계. MST와 최단 경로

필수 문서:

- [`02-minimum-spanning-trees.md`](04-graph-algorithms/02-minimum-spanning-trees.md)
- [`03-shortest-paths.md`](04-graph-algorithms/03-shortest-paths.md)

구현:

- `[Implementation 8]` `dijkstra`
- `[Implementation 9]` `_DisjointSet`, `kruskal_mst`
- `[Implementation 10]` `bellman_ford`

검증:

- Dijkstra는 음수 간선을 거부합니다.
- shortest path 결과는 작은 graph의 Floyd–Warshall 결과와 비교합니다.
- MST는 `V-1`개 간선 조합을 모두 검사한 최소값과 비교합니다.
- Bellman–Ford는 시작점에서 도달 가능한 음수 cycle만 오류로 처리합니다.

### 7단계. 최대 유량

필수 문서:

- [`04-network-flow-and-matching.md`](04-graph-algorithms/04-network-flow-and-matching.md)

구현:

- `[Implementation 11]` `max_flow`

검증:

- 작은 graph의 모든 source-side cut을 열거해 최대 유량 값과 비교합니다.
- 반환된 `flow`가 각 원본 capacity 안에 있는지 확인합니다.
- source와 sink를 제외한 정점에서 유입과 유출이 같은지 확인합니다.
- residual graph의 역방향 간선이 이전 선택을 취소하는 방법을 설명합니다.

### 8단계. 문자열 검색

필수 문서:

- [`01-string-matching-and-preprocessing.md`](05-string-algorithms/01-string-matching-and-preprocessing.md)

구현:

- `[Implementation 12]` `kmp_find`

검증:

- 빈 pattern, pattern이 더 긴 경우, 반복 문자, 긴 prefix 뒤 mismatch를 검사합니다.
- 고정 seed로 만든 짧은 문자열에서 Python `str.find`와 비교합니다.
- prefix table이 전체 문자열 자신이 아닌 proper prefix 길이를 저장하는 이유를 설명합니다.

### 9단계. 공개 API와 전체 검증

구현:

- `[Implementation 13]` 패키지 공개 API
- `[Implementation 14]` independent verification suite

실행:

```sh
cd exercises/verified-algorithms
python -m unittest discover -s tests -v
```

전체 테스트가 통과하면 각 기준 계산이 후보 구현과 다른 방법을 사용하는지 확인합니다. 테스트가 같은 helper나 같은 상태 전이를 공유하면 공통 결함을 놓칠 수 있습니다.

### 10단계. 자료 없이 다시 구현

별도 복사본에서 `src/verified_algorithms/`의 구현을 보지 않고 다음 순서로 다시 작성합니다.

```text
ranges
→ trees
→ optimization
→ BFS와 Dijkstra
→ Kruskal과 Bellman–Ford
→ max flow
→ KMP
→ public API
```

막힌 함수만 관련 문서로 돌아갑니다. 전체 문서를 처음부터 다시 읽지 않습니다.

## 자동 검사 밖의 필수 확인

현재 exercise가 직접 제공하지 않는 다음 주제는 작은 disposable code와 설명으로 확인합니다.

- DFS의 재귀·반복 구현과 directed cycle detection
- topological order와 SCC의 차이
- backtracking의 상태 복구와 안전한 pruning
- 답에 대한 이분 탐색의 단조 판정 함수
- heap lazy deletion
- stable sort의 동점 순서
- monotonic deque의 만료 index 처리
- 동적 배열과 DSU의 상각 비용

## 선택 자료

- [`02-complexity-classes-and-reductions.md`](06-complexity/02-complexity-classes-and-reductions.md): P, NP, NP-hard, NP-complete와 환원을 정확히 표현하려는 경우에 읽습니다.
- [`80-extended-practice.md`](80-extended-practice.md): 필수 범위를 다른 조건의 문제에 적용하려는 경우에 사용합니다.
- [`90-implementation-profiles/python.md`](90-implementation-profiles/python.md): Python으로 구현할 때 읽습니다.
- [`90-implementation-profiles/cpp20.md`](90-implementation-profiles/cpp20.md): C++20으로 옮길 때 읽습니다.

## 완료 기준

다음 조건을 모두 만족해야 합니다.

- 필수 문서를 읽고 각 주제의 전제와 실패 조건을 설명할 수 있습니다.
- `verified-algorithms`의 전체 테스트가 통과합니다.
- 구현을 보지 않고 핵심 API를 다시 작성해 같은 테스트를 통과합니다.
- 함수군마다 입력 조건, 정확성 근거, 시간·추가 공간, 독립 기준 계산을 설명합니다.
- 실패한 입력을 최소화하고 회귀 테스트로 남깁니다.
- 자동 검사 밖의 필수 주제도 작은 코드나 손 추적으로 확인합니다.

자동 테스트는 무한한 모든 입력에 대한 수학적 증명을 대신하지 않습니다. 테스트 통과는 구현이 대표 조건을 만족한다는 근거이며, 전제와 불변식을 직접 설명할 수 있어야 학습이 끝납니다.
