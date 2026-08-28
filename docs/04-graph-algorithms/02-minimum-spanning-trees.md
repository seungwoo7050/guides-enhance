# 최소 스패닝 트리

## 학습 목표

- shortest-path tree와 minimum spanning tree(MST)를 구분합니다.
- cut property와 cycle property로 안전한 간선을 설명합니다.
- Kruskal과 Prim의 상태, 자료구조, 비용을 비교합니다.
- 연결되지 않은 그래프와 같은 가중치가 있는 입력의 반환값을 정합니다.

## 선행지식

[Greedy의 교환 논리](../03-design-techniques/02-greedy-methods.md), [DSU](../02-data-structures/04-disjoint-sets-and-amortized-analysis.md), 그래프 연결성을 이해해야 합니다.

## 핵심 관점

연결된 undirected weighted graph의 spanning tree는 다음 조건을 만족합니다.

```text
모든 정점을 포함합니다.
간선 수가 V-1개입니다.
연결되어 있습니다.
cycle이 없습니다.
```

MST는 가능한 spanning tree 중 간선 가중치 합이 가장 작은 tree입니다.

MST는 특정 시작점에서 각 정점까지의 경로를 최소화하지 않습니다. Shortest-path tree와 목적이 다릅니다.

## 1. cut property

정점 집합을 두 부분으로 나눈 cut을 생각합니다. 현재까지 선택한 forest와 충돌하지 않는 cut을 가로지르는 간선 중 최소 가중치 간선은 안전하게 선택할 수 있습니다.

직관은 다음과 같습니다.

1. 어떤 MST가 최소 간선 `e`를 포함하지 않는다고 가정합니다.
2. `e`를 MST에 추가하면 cycle이 생깁니다.
3. 그 cycle에는 같은 cut을 반대 방향으로 가로지르는 간선 `f`가 있습니다.
4. `w(e) <= w(f)`이므로 `f`를 빼고 `e`를 넣어도 총가중치는 커지지 않습니다.
5. 따라서 `e`를 포함하는 MST가 하나 이상 존재합니다.

## 2. Kruskal

1. 모든 간선을 `(weight, tie-break)` 순서로 정렬합니다.
2. 현재 서로 다른 component를 잇는 간선만 선택합니다.
3. 선택한 간선이 `V-1`개가 되면 끝냅니다.

DSU가 각 정점의 component를 관리합니다.

```text
선택한 간선은 항상 forest입니다.
현재 forest를 포함하는 MST가 하나 이상 존재합니다.
```

시간은 간선 정렬 `O(E log E)`가 대부분을 차지합니다. DSU 연산은 union by size·rank와 path compression을 사용할 때 거의 선형에 가깝습니다.

## 3. Prim

하나의 tree를 확장합니다.

```text
inside 집합에 시작 정점을 넣습니다.
inside와 outside를 잇는 간선 중 최소를 선택합니다.
새 정점을 inside에 넣고 그 정점의 간선을 heap에 추가합니다.
```

Lazy heap을 사용하면 이미 inside에 들어간 정점으로 향하는 오래된 간선을 `pop`할 때 버립니다.

인접 list와 binary heap을 사용하면 보통 `O(E log V)`입니다. 매우 밀집된 그래프에서는 배열 기반 `O(V²)` Prim이 더 단순하고 실용적일 수 있습니다.

## 4. 알고리즘 선택

- edge list가 이미 있고 희소 그래프라면 Kruskal이 단순합니다.
- 한 정점의 인접 간선을 빠르게 얻을 수 있다면 Prim이 자연스럽습니다.
- 매우 밀집된 그래프라면 matrix와 `O(V²)` Prim을 검토합니다.
- 여러 기존 연결을 먼저 합쳐야 하는 offline 문제라면 Kruskal 전에 DSU `union`을 수행할 수 있습니다.

## 5. 같은 가중치와 결과의 유일성

모든 간선 가중치가 서로 다르면 MST는 유일합니다. 같은 가중치가 있으면 여러 MST가 존재할 수 있습니다.

반환 조건이 총가중치만 요구하는지, 특정 간선 목록까지 요구하는지 구분합니다. 특정 목록을 반환한다면 정렬의 tie-break를 정합니다.

테스트는 한 가지 간선 목록만 정답으로 가정하기보다 다음을 검사해야 합니다.

- 간선 수가 `V-1`개입니다.
- 반환한 간선이 원본에 존재합니다.
- 연결되어 있고 cycle이 없습니다.
- 반환한 총가중치가 간선 목록의 합과 같습니다.
- 총가중치가 최적값과 같습니다.

## 6. 연결되지 않은 그래프

함수의 반환 방식을 미리 정합니다.

- `ValueError`로 거부합니다.
- 각 component의 minimum spanning forest를 반환합니다.
- 연결 여부와 forest를 함께 반환합니다.

연결 그래프라는 전조건을 문서에 쓰지 않고 숨기지 않습니다.

## 7. cycle property

어떤 cycle에서 유일하게 가장 무거운 간선은 MST에 포함될 수 없습니다. 해당 간선을 제거해도 cycle의 나머지 간선으로 두 끝점이 연결되며 총가중치가 더 작아지기 때문입니다.

같은 최대 가중치 간선이 여러 개라면 특정 간선 하나가 반드시 제외된다고 단정할 수 없습니다.

## 8. 독립적인 기준 계산

작은 그래프에서는 `V-1`개 간선 조합을 모두 검사합니다.

1. 모든 정점을 연결하는지 확인합니다.
2. cycle이 없는지 확인합니다.
3. 간선 가중치 합을 계산합니다.
4. 가능한 조합 중 최솟값을 구합니다.

Kruskal을 검증하면서 기준 계산도 같은 DSU 구현을 사용하면 공통 결함을 놓칠 수 있습니다. 작은 기준 계산에서는 단순 parent 배열이나 BFS로 연결성을 따로 확인합니다.

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 9]`를 확인합니다.

- `_DisjointSet`이 component 대표와 size를 관리합니다.
- `kruskal_mst`가 `union`에 성공한 간선만 선택합니다.
- 간선을 `(weight, source, target)` 순서로 정렬해 결과를 결정적으로 만듭니다.
- 연결되지 않은 입력은 `ValueError`로 거부합니다.
- 테스트가 모든 spanning tree 조합의 최소 가중치와 비교하고 반환 간선 목록을 따로 검사합니다.

## 완료 기준

- shortest-path tree와 MST가 다른 예를 설명합니다.
- cut을 가로지르는 최소 간선이 안전한 이유를 교환 과정으로 적습니다.
- DSU가 선택 간선의 cycle을 막는 과정을 추적합니다.
- 같은 가중치가 있을 때 특정 edge set 대신 tree 조건과 총가중치를 검사합니다.
- 연결되지 않은 입력의 반환 방식을 명확히 정합니다.

## 실패 신호

- Directed graph에 MST를 그대로 적용합니다.
- 가장 가벼운 간선을 cycle 여부와 상관없이 선택합니다.
- shortest-path tree와 MST를 같은 결과로 생각합니다.
- 연결되지 않은 그래프의 처리 방법이 없습니다.
- 같은 가중치가 있을 때 한 가지 간선 목록만 정답이라고 가정합니다.
- 기준 계산도 Kruskal과 같은 구현을 사용합니다.
