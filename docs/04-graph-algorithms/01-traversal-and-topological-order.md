# 그래프 표현, 순회와 위상 순서

## 학습 목표

- directed/undirected, weighted/unweighted, simple graph/multigraph를 구분합니다.
- 인접 list, 인접 matrix, edge list를 `V`와 `E`에 따라 선택합니다.
- BFS와 DFS의 방문 상태와 실패 조건을 설명합니다.
- cycle detection과 topological order를 구분합니다.
- connected component와 SCC의 차이를 설명합니다.

## 선행지식

[선형 자료구조](../02-data-structures/01-linear-structures-ranges-and-hashing.md)의 stack, queue, set을 알고 있어야 합니다.

## 핵심 관점

그래프 알고리즘을 고르기 전에 간선이 무엇을 뜻하는지 먼저 정합니다.

```text
정점 집합
간선 집합
간선의 방향
가중치의 범위
중복 간선과 자기 loop 허용 여부
연결되지 않은 정점의 처리 방법
```

같은 정점과 간선이라도 방향성과 가중치 조건이 다르면 사용할 알고리즘이 달라집니다.

## 1. 그래프 표현

### 인접 list

각 정점에 outgoing neighbor 목록을 저장합니다.

- 저장 공간: `Θ(V+E)`
- 한 정점의 이웃 순회: degree에 비례
- 희소 그래프에서 일반적으로 적합합니다.

Directed graph에서는 `u -> v`를 `u`의 목록에만 저장합니다. Undirected graph에서는 보통 양쪽 목록에 모두 저장합니다.

### 인접 matrix

`matrix[u][v]`에 간선 존재 여부나 가중치를 저장합니다.

- 저장 공간: `Θ(V²)`
- 두 정점 사이 간선 확인: `O(1)`
- 작은 밀집 그래프나 Floyd–Warshall에 적합할 수 있습니다.

간선이 없음을 나타내는 값과 가중치 `0`을 구분합니다.

### edge list

`(source, target, weight)` 목록으로 저장합니다.

- 모든 간선을 정렬하는 Kruskal에 적합합니다.
- 모든 간선을 반복해서 relaxation하는 Bellman–Ford에 적합합니다.
- 한 정점의 이웃만 빠르게 찾는 데는 별도 인접 list가 필요합니다.

입력에서 중복 간선을 합칠지 그대로 둘지도 정해야 합니다.

## 2. BFS

무가중 그래프에서 시작점으로부터 최소 간선 수를 구합니다.

```text
start의 거리를 0으로 정하고 queue에 넣습니다.
queue에서 정점을 하나 꺼냅니다.
아직 방문하지 않은 이웃의 거리를 현재 거리 + 1로 정하고 queue에 넣습니다.
```

유지하는 내용은 다음과 같습니다.

```text
queue 앞쪽 정점의 거리는 뒤쪽 정점보다 크지 않습니다.
정점에 처음 거리를 기록하는 순간 그 값이 최소 간선 거리입니다.
```

방문 표시는 queue에서 꺼낼 때가 아니라 넣을 때 합니다. 꺼낼 때 표시하면 여러 부모가 같은 정점을 중복해서 넣을 수 있습니다.

인접 list에서 시간은 `Θ(V+E)`, 추가 공간은 `Θ(V)`입니다.

## 3. DFS

DFS는 한 경로를 끝까지 진행한 뒤 돌아옵니다.

대표적인 사용은 다음과 같습니다.

- connected component 탐색
- cycle detection
- topological order
- subtree 계산
- SCC
- articulation point와 bridge 같은 심화 문제

재귀 DFS는 그래프 깊이가 `O(V)`일 수 있습니다. 입력이 크다면 명시적인 stack을 사용합니다. postorder가 필요하면 stack에 `(vertex, next_neighbor_index)`처럼 돌아온 뒤 이어서 처리할 위치를 저장해야 합니다.

## 4. cycle detection

### undirected graph

현재 정점으로 들어온 parent 간선을 제외하고 이미 방문한 이웃을 만나면 cycle이 있습니다.

Parallel edge를 허용하는 multigraph에서는 같은 두 정점 사이의 두 간선도 길이 2인 cycle로 볼 수 있으므로 edge id를 구분해야 할 수 있습니다.

### directed graph

방문 여부 하나만으로는 부족합니다. 다음 세 상태를 사용합니다.

```text
unseen: 아직 방문하지 않았습니다.
active: 현재 DFS call stack에 있습니다.
finished: 해당 정점에서 시작하는 탐색이 끝났습니다.
```

`active` 정점으로 가는 간선은 현재 경로로 돌아가는 back edge이며 directed cycle을 뜻합니다. `finished` 정점으로 가는 간선은 cycle의 증거가 아닙니다.

## 5. topological order

DAG의 모든 간선 `u -> v`에 대해 `u`가 `v`보다 앞에 오는 순서를 구합니다.

### Kahn 알고리즘

1. indegree가 0인 정점을 queue에 넣습니다.
2. 정점을 하나 꺼내 결과에 추가합니다.
3. outgoing edge를 제거한 것처럼 이웃의 indegree를 줄입니다.
4. indegree가 0이 된 이웃을 queue에 넣습니다.
5. 처리한 정점 수가 `V`보다 작으면 cycle이 있습니다.

동일한 시점에 indegree 0인 정점이 여러 개라면 topological order는 하나가 아닙니다. 결정적인 결과가 필요하면 min-heap이나 정렬된 container로 동점 순서를 정합니다.

### DFS postorder

Directed cycle을 함께 검사하면서 DFS 종료 순서의 역순을 사용합니다. Cycle이 발견되면 일부 정점의 결과를 성공으로 반환하지 않습니다.

## 6. connected component와 SCC

Undirected graph의 connected component는 서로 경로가 존재하는 최대 정점 집합입니다.

Directed graph의 strongly connected component(SCC)는 모든 정점 쌍이 서로 양방향으로 도달 가능한 최대 집합입니다.

SCC를 하나의 정점으로 합친 condensation graph는 DAG입니다. Directed graph의 간선을 무시하고 undirected component를 구하는 방식으로 SCC를 얻을 수는 없습니다. Kosaraju나 Tarjan 같은 별도 알고리즘이 필요합니다.

## 7. 경로 복원

거리뿐 아니라 실제 경로가 필요하다면 정점을 처음 발견할 때 predecessor를 기록합니다.

```text
parent[start] = None
parent[next] = current
```

도착점에서 parent를 따라 start까지 이동한 뒤 순서를 뒤집습니다. 도달할 수 없는 정점과 start 자체를 구분합니다.

최단 경로가 여러 개라면 어떤 경로를 반환할지 neighbor 순서와 동점 처리에 따라 달라질 수 있습니다.

## 8. 입력 검증

다음 항목을 함수 시작 부분에서 확인하거나 호출자 전조건으로 명시합니다.

- `start`가 `0..V-1`에 있습니까?
- 모든 neighbor index가 유효합니까?
- directed edge를 실수로 양방향 저장하지 않았습니까?
- 중복 간선과 자기 loop를 허용합니까?
- 빈 그래프에서 start를 받을 수 있습니까?
- 도달할 수 없는 정점을 어떤 값으로 반환합니까?

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 7]`에서 `_validate_vertex`와 `bfs_distances`를 확인합니다.

- start와 모든 neighbor index를 먼저 검사합니다.
- `None`을 아직 발견하지 않은 거리로 사용합니다.
- queue에 넣을 때 거리를 기록해 중복 삽입을 막습니다.
- 단위 가중치 Floyd–Warshall 결과와 비교합니다.

현재 package에는 DFS, topological order, SCC API가 없습니다. 다음 두 실험을 별도로 작성합니다.

1. `unseen/active/finished`를 사용하는 directed cycle detector
2. Kahn 알고리즘으로 cycle 입력을 거부하는 topological sort

## 완료 기준

- 그래프의 방향, 가중치, 중복 간선 조건을 입력 설명에 포함합니다.
- 인접 list와 matrix의 저장 공간과 순회 비용을 비교합니다.
- BFS에서 방문 표시 시점이 왜 queue 삽입 시점인지 설명합니다.
- Directed cycle detector에서 `active`와 `finished`를 구분합니다.
- Cycle이 있는 입력에서 일부 topological order를 성공 결과로 반환하지 않습니다.
- SCC가 undirected component와 다른 이유를 예제로 설명합니다.

## 실패 신호

- Directed edge를 자동으로 양방향 저장합니다.
- BFS에서 dequeue할 때 방문 처리해 같은 정점을 여러 번 넣습니다.
- 재귀 DFS의 최대 깊이를 확인하지 않습니다.
- Directed cycle을 `visited` 하나만으로 판정합니다.
- Cycle이 있는 그래프에서 처리한 일부 정점을 전체 topological order로 반환합니다.
- 도달할 수 없는 정점을 거리 `0`과 같은 값으로 표현합니다.
