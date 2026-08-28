# 알고리즘 설계와 검증

이 저장소는 기업형 알고리즘 테스트에서 자주 요구하는 핵심 자료구조와 알고리즘을 학습하고, 직접 구현한 결과를 독립적인 기준 계산으로 검증하기 위한 과정입니다. 특정 문제 유형의 풀이를 외우는 대신 다음 순서를 반복합니다.

```text
문제의 입력·출력과 예외 조건을 정합니다.
→ 입력 크기에서 허용되는 시간·공간 비용을 계산합니다.
→ 필요한 상태와 자료구조를 고릅니다.
→ 정확성 근거를 적고 구현합니다.
→ 다른 계산 방법과 경계 입력으로 결과를 검증합니다.
```

문서는 언어에 종속되지 않게 작성했습니다. 실행 프로젝트인 [`verified-algorithms`](exercises/verified-algorithms/)는 Python 3.12 이상을 사용하며 외부 실행 의존성이 없습니다.

## 완료 후 갖춰야 할 능력

과정을 마치면 다음 작업을 자료 없이 다시 수행할 수 있어야 합니다.

- 자연어 문제를 입력, 출력, 답 없음, 잘못된 입력, 동점 처리까지 포함한 명확한 조건으로 정리합니다.
- 최악·기대·상각 비용을 구분하고, 복사·재귀 stack·출력 크기까지 포함해 시간과 공간을 계산합니다.
- 반복 불변식, 귀납, 교환 논리, 절단 성질, relaxation 근거로 구현의 정확성을 설명합니다.
- 배열, hash, stack, queue, deque, heap, tree, DSU를 필요한 연산과 비용에 따라 선택합니다.
- 완전탐색, greedy, dynamic programming을 적용할 수 있는 조건과 실패 반례를 구분합니다.
- BFS, Dijkstra, Bellman–Ford, Kruskal, max flow의 전제와 반환값을 설명하고 구현합니다.
- KMP의 prefix table과 fallback을 구현합니다.
- 작은 입력을 모두 계산하거나 다른 알고리즘을 사용해 독립적인 기준 결과를 만듭니다.
- 실패 입력을 최소화하고 회귀 테스트로 남깁니다.

## 필수 학습 범위

### 1. 문제 분석과 정확성

- [`docs/01-foundations/01-problem-contracts-and-counterexamples.md`](docs/01-foundations/01-problem-contracts-and-counterexamples.md)
- [`docs/01-foundations/02-asymptotic-analysis.md`](docs/01-foundations/02-asymptotic-analysis.md)
- [`docs/01-foundations/04-correctness-and-invariants.md`](docs/01-foundations/04-correctness-and-invariants.md)

### 2. 선형 자료구조, 정렬과 탐색

- [`docs/02-data-structures/01-linear-structures-ranges-and-hashing.md`](docs/02-data-structures/01-linear-structures-ranges-and-hashing.md)
- [`docs/06-complexity/01-sorting-stability-and-lower-bounds.md`](docs/06-complexity/01-sorting-stability-and-lower-bounds.md)
- [`docs/02-data-structures/02-order-search-heaps-and-priority.md`](docs/02-data-structures/02-order-search-heaps-and-priority.md)

### 3. 재귀, tree와 DSU

- [`docs/01-foundations/03-recurrences-and-divide-and-conquer.md`](docs/01-foundations/03-recurrences-and-divide-and-conquer.md)
- [`docs/02-data-structures/03-trees-and-balanced-search-trees.md`](docs/02-data-structures/03-trees-and-balanced-search-trees.md)
- [`docs/02-data-structures/04-disjoint-sets-and-amortized-analysis.md`](docs/02-data-structures/04-disjoint-sets-and-amortized-analysis.md)

### 4. 설계 기법

- [`docs/03-design-techniques/01-brute-force-and-backtracking.md`](docs/03-design-techniques/01-brute-force-and-backtracking.md)
- [`docs/03-design-techniques/02-greedy-methods.md`](docs/03-design-techniques/02-greedy-methods.md)
- [`docs/03-design-techniques/03-dynamic-programming.md`](docs/03-design-techniques/03-dynamic-programming.md)

### 5. 그래프와 문자열

- [`docs/04-graph-algorithms/01-traversal-and-topological-order.md`](docs/04-graph-algorithms/01-traversal-and-topological-order.md)
- [`docs/04-graph-algorithms/02-minimum-spanning-trees.md`](docs/04-graph-algorithms/02-minimum-spanning-trees.md)
- [`docs/04-graph-algorithms/03-shortest-paths.md`](docs/04-graph-algorithms/03-shortest-paths.md)
- [`docs/04-graph-algorithms/04-network-flow-and-matching.md`](docs/04-graph-algorithms/04-network-flow-and-matching.md)
- [`docs/05-string-algorithms/01-string-matching-and-preprocessing.md`](docs/05-string-algorithms/01-string-matching-and-preprocessing.md)

정확한 진행 순서는 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 정리했습니다.

## 구현 프로젝트

필수 exercise는 하나입니다.

```text
exercises/verified-algorithms/
```

이 프로젝트는 누적 합, lower bound, red-black tree 검증, 0/1 knapsack, 구간 선택, LCS, BFS, Dijkstra, Kruskal, Bellman–Ford, max flow, KMP를 하나의 설치 가능한 패키지로 제공합니다. 테스트는 후보 구현과 다른 계산 방법을 사용하며, 최적값뿐 아니라 MST 간선 목록과 flow matrix도 함께 검사합니다.

```sh
cd exercises/verified-algorithms
python -m unittest discover -s tests -v
```

완료 여부는 제공된 구현에서 테스트가 통과하는지만 보고 판단하지 않습니다. 별도 복사본에서 소스를 보지 않고 `Implementation 1`부터 `Implementation 12`까지 다시 작성한 뒤 같은 테스트를 통과해야 합니다.

## 권장 진행 방식

```text
기초 문서
→ package와 누적 합·탐색 구현
→ 재귀·tree 문서
→ tree 검증 구현
→ 설계 기법 문서
→ greedy·DP 구현
→ 그래프 문서와 구현
→ 문자열 문서와 구현
→ 공개 API와 전체 테스트
→ 자료를 닫고 다시 구현
```

한 번에 모든 문서를 읽은 뒤 구현을 시작하지 않습니다. 다음 함수군을 구현할 수 있을 정도로 개념을 익혔다면 바로 코드를 작성하고 테스트합니다. 실패하면 관련 문서만 다시 확인합니다.

## 선택 자료

다음 문서는 필수 완료 조건에 포함하지 않습니다.

- [`docs/06-complexity/02-complexity-classes-and-reductions.md`](docs/06-complexity/02-complexity-classes-and-reductions.md): P, NP, certificate와 다항 시간 환원을 다룹니다.
- [`docs/80-extended-practice.md`](docs/80-extended-practice.md): 필수 범위를 마친 뒤 진행할 심화 문제를 제시합니다.
- [`docs/90-implementation-profiles/python.md`](docs/90-implementation-profiles/python.md): Python 구현 시 주의할 비용과 실행 방식을 정리합니다.
- [`docs/90-implementation-profiles/cpp20.md`](docs/90-implementation-profiles/cpp20.md): 같은 알고리즘을 C++20으로 옮길 때 확인할 정수 범위, comparator, 복사와 수명을 정리합니다.

## 최종 완료 기준

다음 조건을 모두 만족해야 완료로 봅니다.

- 필수 문서의 알고리즘을 입력 조건과 복잡도에 따라 선택할 수 있습니다.
- `verified-algorithms`의 전체 테스트가 통과합니다.
- 구현을 보지 않고 핵심 함수군을 다시 작성해 같은 테스트를 통과합니다.
- 각 함수의 입력 조건, 불변식 또는 정확성 근거, 시간·추가 공간, 독립 검증 방법을 설명할 수 있습니다.
- 한 번 이상 실패한 입력을 최소화해 회귀 테스트로 남깁니다.

이 저장소의 범위만으로 모든 회사의 모든 출제 유형을 보장하지는 않습니다. 다만 현재 branch가 다루는 핵심 범위에서는 문제 유형 표시 없이 접근 방법을 정하고 구현·검증하는 데 필요한 기반을 제공합니다.
