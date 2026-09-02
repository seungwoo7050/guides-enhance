# 그래프 표현, 순회와 위상 순서

## 학습 목표

- directed/undirected, weighted/unweighted, simple graph/multigraph를 구분합니다.
- 인접 list, 인접 matrix, edge list를 정점 수 `V`와 간선 수 `E`에 따라 선택합니다.
- BFS와 DFS의 방문 상태와 탐색 순서를 설명합니다.
- directed/undirected graph의 cycle detection 조건을 구분합니다.
- cycle detection과 topological order의 관계를 설명합니다.
- connected component와 strongly connected component(SCC)의 차이를 설명합니다.
- 탐색 결과에서 실제 경로를 복원하는 방법을 설명합니다.

## 선행지식

[선형 자료구조](../02-data-structures/01-linear-structures-ranges-and-hashing.md)의 stack, queue, set을 알고 있어야 합니다.

다음 표기법을 사용합니다.

- `V`: 정점(vertex)의 개수
- `E`: 간선(edge)의 개수
- `u -> v`: `u`에서 `v`로 향하는 directed edge
- `degree(u)`: undirected graph에서 정점 `u`에 연결된 간선 수
- `outdegree(u)`: directed graph에서 `u`에서 나가는 간선 수
- `indegree(u)`: directed graph에서 `u`로 들어오는 간선 수

## 핵심 관점

그래프 알고리즘을 고르기 전에 **간선이 무엇을 의미하며 어떤 규칙을 갖는지** 먼저 정합니다.

```text
정점 집합
간선 집합
간선의 방향
가중치의 존재 여부와 범위
중복 간선 허용 여부
자기 loop 허용 여부
연결되지 않은 정점의 처리 방법
```

그래프의 정점과 간선 데이터가 같아 보여도 위 조건이 달라지면 문제의 의미와 사용할 수 있는 알고리즘이 달라집니다.

예를 들어 다음 두 그래프는 같은 두 정점 `A`, `B`를 사용하지만 의미가 다릅니다.

```text
undirected: A -- B
directed:   A -> B
```

첫 번째에서는 `A`에서 `B`로 갈 수 있으면 `B`에서 `A`로도 같은 간선을 통해 갈 수 있습니다. 두 번째에서는 `A -> B`가 있다고 해서 `B -> A`가 존재하는 것은 아닙니다.

### 자주 사용하는 그래프 분류

**Directed graph**

간선에 방향이 있습니다. `u -> v`와 `v -> u`는 서로 다른 간선입니다.

**Undirected graph**

간선에 방향이 없습니다. `{u, v}` 하나가 두 정점을 연결합니다.

**Weighted graph**

각 간선에 비용, 거리, 시간 같은 값이 붙습니다.

```text
u --5--> v
```

가중치의 범위도 중요합니다. 예를 들어 Dijkstra는 음수 가중치가 있는 일반 그래프에는 사용할 수 없습니다.

**Unweighted graph**

간선마다 별도의 가중치가 없다고 봅니다. 최단 경로 문제에서는 보통 모든 간선의 비용을 `1`로 해석할 수 있습니다.

**Simple graph**

일반적으로 자기 자신으로 향하는 self-loop와 같은 두 정점 사이의 중복 간선을 허용하지 않는 그래프를 뜻합니다.

**Multigraph**

같은 두 정점 사이에 여러 간선이 존재할 수 있는 그래프입니다. 문제에 따라 self-loop도 허용할 수 있으므로 입력 규칙을 별도로 확인해야 합니다.

이 구분은 단순한 용어 차이가 아닙니다. 예를 들어 multigraph에서 간선을 구분해야 하는 알고리즘은 neighbor 정점만 저장해서는 충분하지 않을 수 있습니다.

---

## 1. 그래프 표현

같은 그래프도 여러 자료구조로 표현할 수 있습니다. 어떤 표현이 적합한지는 주로 `V`, `E`, 그리고 자주 수행할 연산에 따라 결정합니다.

### 인접 list

각 정점에 연결된 neighbor 목록을 저장합니다.

예를 들어 directed graph가 다음과 같다고 합시다.

```text
0 -> 1
0 -> 2
2 -> 1
```

인접 list는 다음처럼 표현할 수 있습니다.

```text
0: [1, 2]
1: []
2: [1]
```

Directed graph에서는 `u -> v`를 보통 `u`의 outgoing neighbor 목록에만 저장합니다.

Undirected graph의 간선 `{u, v}`는 보통 양쪽 목록에 모두 저장합니다.

```text
u: [..., v]
v: [..., u]
```

따라서 undirected graph에서 논리적 간선 수가 `E`라면 인접 list 내부에는 보통 총 `2E`개의 neighbor 항목이 저장됩니다. 점근적 공간 복잡도는 그대로 `Θ(V+E)`입니다.

특성은 다음과 같습니다.

- 저장 공간: `Θ(V+E)`
- 정점 `u`의 모든 outgoing neighbor 순회: `Θ(outdegree(u))`
- undirected graph에서 정점 `u`의 이웃 순회: `Θ(degree(u))`
- 특정 간선 `u -> v` 존재 여부 확인: 단순 list라면 최악의 경우 `O(outdegree(u))`
- 희소 그래프에서 일반적으로 적합

여기서 **희소 그래프(sparse graph)** 는 가능한 모든 정점 쌍에 비해 실제 간선 수 `E`가 작은 그래프를 뜻합니다.

### 인접 matrix

`matrix[u][v]`에 간선 존재 여부나 가중치를 저장합니다.

예를 들어 다음 directed graph가 있다면,

```text
0 -> 1
2 -> 0
```

간선 존재 여부를 저장하는 matrix는 다음과 같이 만들 수 있습니다.

```text
    0 1 2
0 [ 0 1 0 ]
1 [ 0 0 0 ]
2 [ 1 0 0 ]
```

특성은 다음과 같습니다.

- 저장 공간: `Θ(V²)`
- 두 정점 사이 간선 확인: `O(1)`
- 한 정점의 모든 이웃 찾기: 한 행 전체를 검사하므로 `Θ(V)`
- 작은 밀집 그래프나 Floyd–Warshall처럼 matrix 기반 연산을 하는 알고리즘에 적합할 수 있음

Weighted graph에서는 **간선이 없음**과 **가중치가 `0`인 간선**을 반드시 구분해야 합니다.

예를 들어 다음 표현은 모호합니다.

```text
matrix[u][v] = 0
```

이 값이 "간선이 없음"인지 "가중치 0인 간선이 있음"인지 알 수 없기 때문입니다.

따라서 별도의 sentinel이나 존재 여부 matrix를 사용합니다.

```text
None       # 간선 없음
0          # 가중치 0인 실제 간선
```

### edge list

모든 간선을 하나의 목록으로 저장합니다.

```text
(source, target)
(source, target, weight)
```

예:

```text
[(0, 1, 5), (0, 2, 3), (2, 1, 4)]
```

특성은 다음과 같습니다.

- 저장 공간: `Θ(E)`
- 모든 간선을 순회: `Θ(E)`
- 특정 정점의 모든 이웃 찾기: 별도 index가 없다면 최악의 경우 `Θ(E)`
- 간선 전체를 정렬하는 Kruskal에 적합
- 모든 간선을 반복해서 relaxation하는 Bellman–Ford에 적합

**Relaxation**은 현재 알고 있는 거리보다 더 짧은 경로를 발견했을 때 거리 값을 갱신하는 연산을 뜻합니다.

입력에 중복 간선이 있을 수 있다면 다음 정책도 명확히 해야 합니다.

```text
중복 간선을 그대로 유지할 것인가?
같은 두 정점 사이에서 최소 가중치 하나만 남길 것인가?
동일한 간선을 입력 오류로 거부할 것인가?
```

이 선택은 문제 정의에 따라 달라집니다.

### 표현 선택 기준

| 필요한 연산 | 자주 적합한 표현 |
|---|---|
| 각 정점의 이웃을 자주 순회 | 인접 list |
| `u`와 `v` 사이 간선 존재 여부를 매우 자주 확인 | 인접 matrix |
| 모든 간선을 정렬하거나 반복 순회 | edge list |
| `V`가 크고 `E`가 상대적으로 작음 | 인접 list |
| `V`가 작고 간선이 매우 많음 | 인접 matrix를 고려 |

하나만 사용해야 하는 것은 아닙니다. 필요한 연산이 다르면 edge list와 인접 list를 함께 유지할 수도 있습니다.

---

## 2. BFS

BFS(Breadth-First Search)는 시작점에서 가까운 정점부터 층별로 탐색합니다.

Unweighted graph 또는 모든 간선 비용을 `1`로 보는 graph에서 BFS는 시작점으로부터 **최소 간선 수**를 구할 수 있습니다.

예를 들어 다음 그래프가 있다고 합시다.

```text
0 -- 1 -- 3
 \
  2 -- 4
```

`0`에서 시작하면 탐색 층은 다음과 같습니다.

```text
거리 0: 0
거리 1: 1, 2
거리 2: 3, 4
```

### 기본 절차

```text
start의 거리를 0으로 기록합니다.
start를 queue에 넣습니다.

queue가 빌 때까지:
    정점을 하나 꺼냅니다.
    아직 발견하지 않은 각 이웃에 대해:
        이웃의 거리를 현재 거리 + 1로 기록합니다.
        이웃의 parent를 현재 정점으로 기록할 수 있습니다.
        이웃을 queue에 넣습니다.
```

### BFS가 유지하는 핵심 성질

BFS에서는 queue에 있는 정점들이 거리 순서대로 처리됩니다.

정확히는 queue 앞쪽에 있는 정점의 거리가 뒤쪽 정점의 거리보다 더 클 수 없습니다.

```text
queue 앞쪽 거리 <= queue 뒤쪽 거리
```

따라서 정점 `v`가 **처음 발견되어 거리 값이 기록되는 순간**, 그 값은 시작점에서 `v`까지 가는 최소 간선 수입니다.

### 방문 표시는 enqueue 시점에 합니다

방문 여부는 queue에서 꺼낼 때가 아니라 **queue에 넣을 때** 기록해야 합니다.

다음 그래프를 생각해 봅시다.

```text
    1
   / \
  0   3
   \ /
    2
```

`0`에서 시작하면 `1`과 `2`가 모두 `3`을 발견할 수 있습니다.

`3`을 dequeue할 때까지 방문 표시를 미룬다면 다음 일이 발생할 수 있습니다.

```text
1이 3을 enqueue
2도 아직 3이 미방문이라고 판단
2도 3을 enqueue
```

따라서 같은 정점이 queue에 여러 번 들어갑니다.

반면 enqueue하는 순간 발견 상태를 기록하면 최초 한 번만 들어갑니다.

```text
if distance[next] is None:
    distance[next] = distance[current] + 1
    queue.push(next)
```

거리 배열 자체를 방문 상태로 사용할 수도 있습니다.

```text
None   -> 아직 발견하지 않음
0 이상 -> 이미 발견함
```

### 복잡도

인접 list를 사용할 때 한 번의 BFS에서 각 정점은 최대 한 번 발견되고, 각 인접 항목은 최대 한 번 검사됩니다.

따라서 전체 그래프 기준 상한은 다음과 같습니다.

- 시간: `Θ(V+E)`
- 추가 공간: `Θ(V)`

시작점에서 도달할 수 없는 정점이 있다면 실제로는 그 정점과 관련된 간선을 검사하지 않을 수도 있지만, 전체 입력 크기에 대한 표준 복잡도 표기는 `Θ(V+E)`를 사용합니다.

---

## 3. DFS

DFS(Depth-First Search)는 현재 경로를 가능한 한 깊게 따라간 뒤 더 진행할 수 없으면 이전 정점으로 돌아옵니다.

대표적인 사용은 다음과 같습니다.

- connected component 탐색
- cycle detection
- topological order
- subtree 계산
- SCC
- articulation point와 bridge 같은 심화 문제

### 재귀 DFS

개념적으로는 다음과 같습니다.

```text
dfs(u):
    u를 방문 처리합니다.

    for each neighbor v of u:
        if v가 아직 방문되지 않았다면:
            dfs(v)
```

재귀 호출이 끝나는 시점은 `u`의 모든 후속 탐색이 끝났다는 뜻입니다. 이 **종료 시점(postorder)** 이 필요한 알고리즘도 많습니다.

### 재귀 깊이

그래프가 다음처럼 긴 사슬일 수 있습니다.

```text
0 -> 1 -> 2 -> 3 -> ... -> V-1
```

이 경우 재귀 DFS의 최대 호출 깊이는 `O(V)`입니다.

언어나 실행 환경의 call stack 한도를 넘을 수 있다면 명시적인 stack을 사용해야 합니다.

### 명시적 stack과 postorder

단순히 정점만 stack에 넣는 구현은 preorder 방문은 쉽게 만들 수 있지만, 재귀 DFS의 "자식 탐색을 모두 끝낸 뒤 돌아오는 시점"을 그대로 재현하기 어렵습니다.

Postorder가 필요하다면 다음처럼 **현재 정점에서 다음에 검사할 neighbor 위치**까지 저장할 수 있습니다.

```text
(vertex, next_neighbor_index)
```

개념적으로 다음 상태를 stack frame에 보존하는 것입니다.

```text
현재 정점
어디까지 이웃을 검사했는가
모든 자식 탐색이 끝났는가
```

또 다른 구현에서는 `(vertex, entering/exiting)` 같은 두 종류의 frame을 사용하기도 합니다.

---

## 4. cycle detection

Cycle은 어떤 정점에서 출발해 간선을 따라 이동한 뒤 다시 출발점으로 돌아오는 닫힌 경로를 뜻합니다.

그러나 directed graph와 undirected graph에서는 cycle을 발견하는 조건이 다릅니다.

Self-loop를 허용한다면 다음 간선 하나만으로도 cycle입니다.

```text
u -> u
```

Undirected multigraph의 parallel edge를 cycle로 취급하는지는 문제의 cycle 정의를 확인해야 합니다. 두 평행 간선을 서로 다른 edge로 구분하는 정의에서는 두 간선으로 출발점에 돌아오는 길이 2의 cycle이 됩니다.

### undirected graph

Undirected DFS에서는 현재 정점으로 들어온 간선을 다시 보는 것이 정상입니다.

예:

```text
0 -- 1
```

`0`에서 `1`로 이동한 뒤 `1`의 인접 list를 보면 다시 `0`이 나타납니다. 이것만으로 cycle이라고 판단하면 안 됩니다.

따라서 simple undirected graph에서는 보통 **부모 정점(parent)** 을 제외하고 이미 방문한 이웃을 만나면 cycle이 있다고 판단합니다.

```text
dfs(u, parent):
    visited[u] = true

    for v in neighbors[u]:
        if not visited[v]:
            if dfs(v, u):
                return true
        else if v != parent:
            return true

    return false
```

### multigraph에서는 parent 정점만 비교하면 부족할 수 있습니다

다음처럼 같은 두 정점 사이에 서로 다른 두 간선 `e1`, `e2`가 있다고 합시다.

```text
u ==e1== v
u ==e2== v
```

`v`에서 `u`를 볼 때 단순히 `u == parent`라는 이유로 모든 간선을 무시하면 두 번째 간선까지 놓칠 수 있습니다.

따라서 parallel edge를 구분해야 하는 undirected multigraph에서는 보통 parent **정점**이 아니라 parent **edge id**를 기억합니다.

```text
dfs(vertex, parent_edge_id)
```

### directed graph

Directed graph에서는 방문 여부 하나만으로 cycle을 올바르게 판정할 수 없습니다.

다음 세 상태를 사용합니다.

```text
unseen:
    아직 DFS가 시작되지 않은 정점

active:
    DFS가 시작되었지만 아직 종료되지 않은 정점
    즉 현재 DFS call stack에 있는 정점

finished:
    해당 정점에서 시작한 모든 후속 탐색이 끝난 정점
```

상태 전이는 다음과 같습니다.

```text
unseen -> active -> finished
```

DFS 중 `active` 정점으로 향하는 간선을 만나면 현재 탐색 경로의 조상으로 되돌아간 것입니다.

이런 간선을 **back edge**라고 하며 directed cycle의 증거입니다.

반면 `finished` 정점으로 향하는 간선은 cycle의 증거가 아닙니다.

예:

```text
0 -> 1
 \-> 2 -> 1
```

`1` 탐색이 이미 끝난 뒤 `2 -> 1`을 본다고 해서 cycle이 생기지는 않습니다.

따라서 다음처럼 구분해야 합니다.

```text
if state[v] == unseen:
    dfs(v)
elif state[v] == active:
    cycle 발견
elif state[v] == finished:
    cycle 아님
```

---

## 5. topological order

Topological order는 directed graph에서만 정의합니다.

DAG(Directed Acyclic Graph), 즉 **directed cycle이 없는 directed graph**에서 모든 간선 `u -> v`에 대해 `u`가 `v`보다 앞에 오도록 정점을 나열한 순서입니다.

예를 들어 다음 그래프가 있다면,

```text
0 -> 2
1 -> 2
2 -> 3
```

가능한 topological order 중 하나는 다음과 같습니다.

```text
0, 1, 2, 3
```

다음도 가능합니다.

```text
1, 0, 2, 3
```

즉 topological order는 항상 유일한 것이 아닙니다.

Directed cycle이 있으면 topological order는 존재하지 않습니다.

### Kahn 알고리즘

Kahn 알고리즘은 indegree를 사용합니다.

`indegree(v)`는 `v`로 들어오는 directed edge의 개수입니다.

절차는 다음과 같습니다.

1. 모든 정점의 indegree를 계산합니다.
2. indegree가 `0`인 정점을 queue에 넣습니다.
3. 정점을 하나 꺼내 결과에 추가합니다.
4. 그 정점의 outgoing edge를 제거한 것처럼 각 이웃의 indegree를 `1` 줄입니다.
5. indegree가 새로 `0`이 된 이웃을 queue에 넣습니다.
6. queue가 빌 때까지 반복합니다.
7. 결과에 들어간 정점 수가 `V`보다 작으면 cycle이 있습니다.

Directed cycle 안의 각 정점은 cycle 내부에서 적어도 하나의 incoming edge를 받습니다. 따라서 cycle의 간선이 남아 있는 동안 그 정점들의 indegree는 모두 `0`이 될 수 없습니다.

결국 처리 가능한 정점이 없어 queue가 비지만 아직 처리되지 않은 정점이 남습니다.

따라서 성공 조건은 반드시 다음과 같이 검사해야 합니다.

```text
len(order) == V
```

그렇지 않다면 `order`에는 cycle 바깥에서 처리할 수 있었던 일부 정점만 들어 있을 수 있습니다. 이 부분 결과를 전체 topological order처럼 반환하면 안 됩니다.

### 중복 간선이 있는 경우

Directed multigraph에서 `u -> v` 간선이 두 개라면 `v`의 indegree에도 둘 다 포함해야 합니다.

```text
u -> v
u -> v
```

초기 indegree를 `2` 증가시켰다면 `u`를 처리할 때 두 간선에 대해 각각 `1`씩 감소시켜야 합니다. 증가와 감소의 기준이 일치해야 합니다.

### 동점 처리와 결정적인 결과

동일한 시점에 indegree가 `0`인 정점이 여러 개일 수 있습니다.

```text
0 -> 2
1 -> 2
```

초기에 `0`, `1` 모두 indegree가 `0`이므로 다음 두 순서가 모두 가능합니다.

```text
0, 1, 2
1, 0, 2
```

테스트에서 항상 같은 결과가 필요하다면 동점 규칙을 정합니다.

- min-heap 사용
- 정렬된 container 사용
- 입력 순서를 보존하는 queue 사용

어떤 규칙을 선택하든 API 계약에 명시해야 합니다.

### DFS postorder

DFS로도 topological order를 만들 수 있습니다.

핵심은 정점을 **처음 방문할 때**가 아니라 그 정점에서 나가는 모든 경로를 탐색한 **종료 시점**에 결과에 추가하는 것입니다.

```text
dfs(u):
    state[u] = active

    for v in neighbors[u]:
        ...
        cycle 검사
        ...

    state[u] = finished
    order.append(u)
```

모든 DFS가 끝난 뒤 `order`를 뒤집으면 topological order가 됩니다.

```text
reverse(postorder)
```

단, directed cycle이 발견되면 topological order는 존재하지 않습니다. 따라서 일부 정점이 이미 `order`에 들어갔더라도 성공 결과로 반환해서는 안 됩니다.

---

## 6. connected component와 SCC

### connected component

Undirected graph의 connected component는 서로 경로가 존재하는 정점들의 **최대 집합**입니다.

예:

```text
0 -- 1 -- 2

3 -- 4
```

connected component는 두 개입니다.

```text
{0, 1, 2}
{3, 4}
```

모든 정점에서 아직 방문하지 않은 정점을 하나씩 골라 BFS나 DFS를 시작하면 component를 구할 수 있습니다.

### strongly connected component

Directed graph에서는 한 방향으로 도달할 수 있다는 것만으로 같은 component라고 하지 않습니다.

Strongly connected component(SCC)는 component 안의 임의의 두 정점 `u`, `v`에 대해 다음이 모두 가능한 최대 정점 집합입니다.

```text
u에서 v로 도달 가능
v에서 u로 도달 가능
```

예를 들어 다음 directed graph를 봅시다.

```text
0 -> 1
^    |
|____|

1 -> 2
```

`0`과 `1`은 서로 왕복할 수 있으므로 같은 SCC입니다.

하지만 `2`에서는 `0`이나 `1`로 돌아갈 수 없으므로 SCC는 다음과 같습니다.

```text
{0, 1}
{2}
```

### 방향을 무시한 connected component와 SCC는 다릅니다

다음 그래프를 생각해 봅시다.

```text
0 -> 1 -> 2
```

방향을 무시하면 세 정점은 하나의 undirected connected component입니다.

```text
{0, 1, 2}
```

하지만 directed path를 따라 반대 방향으로 돌아갈 수 없으므로 SCC는 각각 따로입니다.

```text
{0}
{1}
{2}
```

따라서 directed edge의 방향을 지우고 undirected component를 구하는 방법으로 SCC를 얻을 수 없습니다.

Kosaraju나 Tarjan 같은 별도 SCC 알고리즘이 필요합니다.

### condensation graph

각 SCC를 하나의 정점으로 축약하고 서로 다른 SCC 사이의 간선만 남기면 **condensation graph**를 만들 수 있습니다.

이 graph는 항상 DAG입니다.

만약 condensation graph에 directed cycle이 존재한다면 그 cycle에 포함된 SCC들은 서로 왕복 가능하므로 사실 하나의 더 큰 SCC여야 합니다. 이는 SCC가 최대 집합이라는 정의와 모순됩니다.

---

## 7. 경로 복원

거리뿐 아니라 실제 경로가 필요하다면 정점을 처음 발견할 때 predecessor, 즉 바로 이전 정점을 기록합니다.

BFS에서는 다음과 같이 사용할 수 있습니다.

```text
parent[start] = None

next를 처음 발견할 때:
    parent[next] = current
```

예를 들어 탐색 결과가 다음과 같다고 합시다.

```text
parent[0] = None
parent[2] = 0
parent[4] = 2
```

`0`에서 `4`까지 경로를 복원하려면 도착점부터 parent를 거꾸로 따라갑니다.

```text
4 -> 2 -> 0
```

그 뒤 순서를 뒤집습니다.

```text
0 -> 2 -> 4
```

### 도달 불가능 상태와 시작점은 구분합니다

다음 두 상태는 서로 다릅니다.

```text
start 자체
start에서 도달할 수 없는 정점
```

둘 다 `parent = None`만 사용하면 구분이 어려울 수 있습니다.

따라서 거리 배열과 함께 해석할 수 있습니다.

```text
distance[start] = 0
distance[unreachable] = None
```

또는 별도의 discovered 상태를 둘 수도 있습니다.

### 여러 최단 경로가 있는 경우

BFS에서 최단 경로가 여러 개라면 어떤 parent가 선택되는지는 이웃을 검사하는 순서에 따라 달라질 수 있습니다.

예:

```text
0 -> 1 -> 3
 \-> 2 -> 3
```

`0 -> 1 -> 3`과 `0 -> 2 -> 3`은 모두 길이 `2`입니다.

항상 같은 경로를 반환해야 한다면 다음과 같은 동점 규칙을 정해야 합니다.

- neighbor를 정렬된 순서로 탐색
- 입력 순서를 보존
- 별도의 우선순위 규칙 사용

---

## 8. 입력 검증

그래프 알고리즘은 자료구조가 올바르다는 전제에 크게 의존합니다.

다음 항목을 함수 시작 부분에서 확인하거나 호출자 전조건으로 명시합니다.

- `start`가 `0..V-1` 범위에 있습니까?
- 모든 neighbor index가 `0..V-1` 범위에 있습니까?
- directed edge를 실수로 양방향 저장하지 않았습니까?
- undirected edge를 표현할 때 양쪽 목록이 필요한 구현입니까?
- 중복 간선을 허용합니까?
- self-loop를 허용합니까?
- 빈 그래프에서 `start`를 받을 수 있습니까?
- 도달할 수 없는 정점을 어떤 값으로 반환합니까?
- weighted graph라면 허용하는 가중치 범위는 무엇입니까?

### 입력 표현과 알고리즘의 전제가 일치해야 합니다

예를 들어 Kahn 알고리즘에서 directed edge 하나를 양방향으로 잘못 저장하면 실제 그래프와 다른 indegree가 계산됩니다.

```text
원래 입력:
u -> v

잘못 저장:
u -> v
v -> u
```

이렇게 되면 존재하지 않던 cycle이 생긴 것처럼 보일 수도 있습니다.

또한 simple graph를 전제로 작성한 undirected cycle detector에 multigraph 입력을 그대로 넣으면 parallel edge를 잘못 처리할 수 있습니다.

따라서 그래프 표현 규칙은 알고리즘 구현보다 먼저 정의되어야 합니다.

---

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 7]`에서 `_validate_vertex`와 `bfs_distances`를 확인합니다.

구현에서 확인할 핵심은 다음과 같습니다.

- `start`와 모든 neighbor index를 먼저 검사합니다.
- `None`을 아직 발견하지 않은 거리로 사용합니다.
- queue에 넣을 때 거리를 기록해 중복 삽입을 막습니다.
- 단위 가중치 Floyd–Warshall 결과와 비교해 BFS 거리 결과를 검증합니다.

여기서 Floyd–Warshall 비교는 작은 검증용 그래프에서 BFS 결과의 정당성을 교차 확인하는 용도로 사용할 수 있습니다. BFS 자체를 Floyd–Warshall로 대체한다는 뜻은 아닙니다.

현재 package에는 DFS, topological order, SCC API가 없습니다. 다음 두 실험을 별도로 작성합니다.

1. `unseen/active/finished` 상태를 사용하는 directed cycle detector
2. Kahn 알고리즘으로 cycle 입력을 거부하는 topological sort

Directed cycle detector는 최소한 다음 두 경우를 구분해야 합니다.

```text
active 정점으로 가는 간선   -> cycle
finished 정점으로 가는 간선 -> cycle 아님
```

Kahn 알고리즘은 결과 길이를 반드시 검사해야 합니다.

```text
if len(order) != V:
    cycle 오류
```

부분 결과를 성공한 topological order로 반환하지 않습니다.

---

## 완료 기준

- 그래프의 방향, 가중치, 중복 간선, self-loop 조건을 입력 설명에 포함합니다.
- simple graph와 multigraph의 차이를 설명합니다.
- 인접 list, matrix, edge list의 저장 공간과 주요 연산 비용을 비교합니다.
- BFS에서 방문 표시 시점이 왜 queue 삽입 시점인지 설명합니다.
- BFS가 unweighted graph에서 최소 간선 거리를 구하는 이유를 설명합니다.
- DFS에서 재귀 깊이가 `O(V)`까지 증가할 수 있음을 설명합니다.
- Directed cycle detector에서 `active`와 `finished`를 구분합니다.
- Undirected multigraph에서는 parent edge 구분이 필요할 수 있음을 설명합니다.
- Cycle이 있는 입력에서 일부 topological order를 성공 결과로 반환하지 않습니다.
- SCC가 undirected component와 다른 이유를 예제로 설명합니다.
- 실제 경로가 필요할 때 predecessor를 기록하고 역추적하는 과정을 설명합니다.

## 실패 신호

- Directed edge를 자동으로 양방향 저장합니다.
- 그래프가 simple graph인지 multigraph인지 확인하지 않습니다.
- BFS에서 dequeue할 때 처음 방문 처리해 같은 정점을 여러 번 넣습니다.
- Unweighted BFS 결과를 임의의 weighted shortest path에도 그대로 적용합니다.
- 재귀 DFS의 최대 깊이를 확인하지 않습니다.
- Directed cycle을 `visited` 하나만으로 판정합니다.
- Undirected graph에서 parent로 되돌아가는 정상 간선을 cycle로 오해합니다.
- Multigraph인데 parent 정점만 비교해 parallel edge를 놓칩니다.
- Cycle이 있는 그래프에서 처리한 일부 정점을 전체 topological order로 반환합니다.
- 도달할 수 없는 정점을 거리 `0`과 같은 값으로 표현합니다.
- 경로가 여러 개인데 결과 순서의 결정성(determinism)이 필요한지 정의하지 않습니다.
