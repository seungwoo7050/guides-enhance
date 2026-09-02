# 최단 경로

## 학습 목표

- 간선 가중치 조건과 그래프 구조에 따라 BFS, DAG relaxation, Dijkstra, Bellman–Ford를 선택합니다.
- Relaxation이 어떤 값을 갱신하는 연산인지 설명합니다.
- 각 알고리즘에서 어떤 조건 때문에 거리 값이 확정되거나 반복 갱신되는지 설명합니다.
- 도달할 수 없는 정점, 유한한 최단 거리, reachable negative cycle의 영향을 구분합니다.
- Floyd–Warshall의 상태 정의와 loop 순서를 설명합니다.
- 경로 복원과 독립 검증 방법을 설명합니다.

## 선행지식

[그래프 순회](01-traversal-and-topological-order.md), heap, dynamic programming의 상태 갱신을 알고 있어야 합니다.

이 문서에서는 다음 표기법을 사용합니다.

- `V`: 정점 수
- `E`: 간선 수
- `w(u, v)`: 간선 `u -> v`의 가중치
- `dist[v]`: 시작점에서 `v`까지 현재 알고 있는 최단 거리 후보
- `parent[v]`: 현재 최단 거리 후보에서 `v` 직전에 오는 정점

Directed graph와 undirected graph 모두 최단 경로 문제를 정의할 수 있습니다. Undirected weighted graph는 보통 각 undirected edge `{u,v}`를 두 방향 간선 `u -> v`, `v -> u`처럼 해석해 구현할 수 있습니다.

---

## 핵심 관점

최단 경로 알고리즘의 공통 연산은 **relaxation**입니다.

간선 `u -> v`를 통해 `v`로 가는 새로운 경로 후보를 계산합니다.

```text
candidate = dist[u] + weight(u, v)
```

이 후보가 현재 알고 있는 `dist[v]`보다 작다면 갱신합니다.

```text
if dist[u]가 유한하고
   dist[u] + weight(u, v) < dist[v]:

    dist[v] = dist[u] + weight(u, v)
    parent[v] = u
```

여기서 중요한 점은 relaxation이 "최단 거리를 한 번에 계산하는 연산"이 아니라는 것입니다.

Relaxation은 단지 다음 명제를 적용합니다.

```text
u까지 가는 경로를 알고 있고
u -> v 간선이 있다면

u를 거쳐 v로 가는 경로도 하나의 후보입니다.
```

알고리즘마다 차이는 다음 두 가지입니다.

```text
어떤 순서로 간선을 relaxation하는가?
몇 번 relaxation해야 값이 더 이상 줄어들지 않는가?
```

이 순서와 반복 횟수를 정당화하는 근거가 각 알고리즘의 핵심입니다.

---

## 1. 선택 기준

| 입력 조건 | 알고리즘 | 대표 시간 |
| --- | --- | ---: |
| 모든 간선 비용이 동일합니다. | BFS | `O(V+E)` |
| DAG이며 음수 간선을 허용합니다. | topological relaxation | `O(V+E)` |
| 모든 간선 가중치가 음수가 아닙니다. | Dijkstra | `O((V+E) log V)` |
| 음수 간선을 허용하고 reachable negative cycle을 찾아야 합니다. | Bellman–Ford | `O(VE)` |
| 정점 수가 작고 all-pairs shortest path가 필요합니다. | Floyd–Warshall | `O(V³)` |

### 선택할 때 먼저 확인할 조건

최단 경로 문제를 보면 먼저 다음을 확인합니다.

```text
single-source인가 all-pairs인가?
가중치가 모두 동일한가?
가중치가 0 또는 1뿐인가?
음수 가중치가 존재할 수 있는가?
그래프가 DAG인가?
음수 cycle을 탐지해야 하는가?
```

### 0-1 BFS

간선 가중치가 `0`과 `1`뿐이라면 일반 Dijkstra보다 단순한 **0-1 BFS**를 사용할 수 있습니다.

Deque를 사용해

```text
weight 0 간선 -> 앞쪽에 삽입
weight 1 간선 -> 뒤쪽에 삽입
```

하여 더 작은 거리 후보가 먼저 처리되도록 합니다.

일반 BFS와 달리 가중치가 모두 같은 것은 아니므로 단순한 level 순회로 설명할 수는 없습니다.

---

## 2. BFS

모든 간선의 비용이 동일하다면 그 공통 비용을 `1`로 정규화해서 생각할 수 있습니다.

이 경우 어떤 경로의 비용은 그 경로가 사용하는 간선 수와 같습니다.

```text
경로 비용 = 간선 수
```

BFS는 시작점에서 간선 수가 적은 경로부터 탐색하므로 최단 경로를 구할 수 있습니다.

### 왜 처음 발견한 거리가 최단 거리인가

BFS queue는 거리 층별로 처리됩니다.

```text
거리 0
거리 1
거리 2
...
```

정점 `v`가 처음 발견될 때 현재 정점 `u`의 거리가 `d`라면

```text
dist[v] = d + 1
```

입니다.

BFS가 더 작은 거리 층을 먼저 모두 처리하기 때문에 나중에 `v`를 더 적은 간선 수로 발견할 수 없습니다.

따라서 **처음 발견하는 순간 거리 값이 확정됩니다.**

### 가중치가 다르면 일반 BFS를 사용할 수 없습니다

다음 그래프를 생각해 봅시다.

```text
S -> A : 100
S -> B : 1
B -> A : 1
```

간선 수만 보면 `S -> A`는 간선 하나이므로 BFS가 먼저 발견할 수 있습니다.

하지만 가중치 합은 다음과 같습니다.

```text
S -> A       = 100
S -> B -> A  = 2
```

따라서 가중치가 서로 다른 graph에 일반 BFS를 사용하면 **최소 간선 수 경로**는 구할 수 있어도 **최소 가중치 합 경로**는 보장하지 않습니다.

---

## 3. DAG 최단 경로

DAG(Directed Acyclic Graph)에서는 topological order를 이용해 모든 outgoing edge를 한 번씩 relaxation하면 됩니다.

Topological order에서는 모든 간선 `u -> v`에 대해

```text
u가 v보다 먼저 나옵니다.
```

### 절차

1. Topological order를 구합니다.
2. 시작점 `s`에 대해 `dist[s] = 0`으로 초기화합니다.
3. 나머지 정점은 도달 불가능 상태로 둡니다.
4. Topological order 앞에서부터 정점을 처리합니다.
5. 현재 정점이 도달 가능한 경우 outgoing edge를 relaxation합니다.

개념적으로 다음과 같습니다.

```text
for u in topological_order:
    if dist[u]가 유한하지 않다면:
        continue

    for each edge (u, v, w):
        relax(u, v, w)
```

### 왜 한 번씩만 처리해도 되는가

Topological order에서 `u`보다 뒤에 있는 정점에서 다시 `u`로 돌아오는 directed edge는 존재할 수 없습니다.

따라서 `u`를 처리하는 시점에는 `u`로 들어오는 모든 가능한 predecessor가 이미 앞에서 처리되었습니다.

즉 `dist[u]`에 반영될 수 있는 모든 이전 경로가 이미 반영된 상태입니다.

그래서 `u`의 outgoing edge를 한 번 relaxation한 뒤 `u`를 다시 처리할 필요가 없습니다.

### 음수 간선을 허용할 수 있는 이유

DAG에는 cycle이 없습니다.

따라서 음수 간선이 있어도 한 정점을 반복해서 거쳐 비용을 계속 줄이는 문제가 생기지 않습니다.

예를 들어 다음도 허용됩니다.

```text
A -> B : -5
B -> C : 2
```

Dijkstra와 달리 가중치가 음수여도 topological order에 따라 정확하게 relaxation할 수 있습니다.

단, graph가 실제 DAG여야 합니다.

Topological order를 구하지 못했다면 directed cycle이 있다는 뜻이므로 이 알고리즘을 실행하면 안 됩니다.

---

## 4. Dijkstra

Dijkstra의 핵심 전조건은 다음과 같습니다.

```text
모든 간선 가중치 >= 0
```

"음수 cycle이 없다"보다 더 강한 조건입니다.

음수 간선이 하나라도 존재하면 일반적인 Dijkstra의 확정 논리가 깨집니다.

### 상태

Dijkstra는 각 정점에 대한 tentative distance, 즉 아직 최종 확정되지 않은 거리 후보를 유지합니다.

Priority queue에는 보통 다음을 넣습니다.

```text
(distance, vertex)
```

가장 작은 tentative distance를 가진 정점을 먼저 꺼냅니다.

### 기본 절차

```text
dist[start] = 0
heap에 (0, start)를 넣습니다.

heap이 빌 때까지:
    (d, u)를 꺼냅니다.

    if d != dist[u]:
        stale entry이므로 버립니다.

    for each outgoing edge (u, v, w):
        if dist[u] + w < dist[v]:
            dist[v] = dist[u] + w
            parent[v] = u
            heap에 (dist[v], v)를 넣습니다.
```

### stale heap entry

일반적인 binary heap은 이미 들어간 항목의 key를 직접 감소시키는 decrease-key 연산을 제공하지 않는 경우가 많습니다.

그래서 더 좋은 거리 후보를 발견하면 새 항목을 다시 삽입합니다.

예:

```text
(10, v) 삽입
나중에 더 짧은 경로 발견
(3, v) 삽입
```

가중치 `3`인 항목이 먼저 처리된 뒤에도 `(10, v)`는 heap 안에 남아 있을 수 있습니다.

나중에 `(10, v)`를 꺼냈을 때

```text
10 != dist[v]
```

라면 이미 더 좋은 거리 `3`이 알려졌으므로 오래된 항목입니다.

이런 항목을 **stale entry**라고 하며 버립니다.

### 왜 heap에서 최소 거리로 꺼낸 값이 확정되는가

현재 heap에서 가장 작은 tentative distance를 가진 정점 `u`를 꺼냈다고 합시다.

```text
dist[u] = d
```

아직 처리하지 않은 다른 정점을 거쳐 `u`로 더 짧게 오는 경로가 있다고 가정해 봅시다.

그 경로에서 아직 확정되지 않은 첫 번째 정점을 `x`라고 하면 `x`까지의 경로 길이는 `d`보다 작아야 합니다.

그런데 모든 간선 가중치가 음수가 아니므로 경로를 더 따라갈수록 비용이 줄어들 수 없습니다.

따라서 `x`의 tentative distance가 `d`보다 작아야 하고, 그렇다면 heap에서 `u`보다 `x`가 먼저 나왔어야 합니다.

이는 `u`가 현재 최소 항목이었다는 사실과 모순됩니다.

따라서 `u`의 거리는 더 이상 줄어들 수 없습니다.

### 음수 간선이 있으면 왜 실패하는가

음수 간선이 있으면 나중에 발견한 경로가 이미 꺼낸 정점의 거리를 줄일 수 있습니다.

예를 들어

```text
S -> A : 2
S -> B : 5
B -> A : -10
```

초기에는

```text
dist[A] = 2
dist[B] = 5
```

이므로 Dijkstra는 `A`를 먼저 확정할 수 있습니다.

하지만 실제로는

```text
S -> B -> A = -5
```

가 더 짧습니다.

즉 음수 간선이 있으면 "한번 최소 거리로 꺼낸 정점의 거리는 더 줄어들지 않는다"는 근거가 사라집니다.

따라서

```text
negative cycle 없음
```

만으로는 Dijkstra를 사용할 수 없습니다.

---

## 5. Bellman–Ford

Bellman–Ford는 음수 가중치를 허용하는 single-source shortest path 알고리즘입니다.

핵심 아이디어는 모든 간선을 여러 번 반복해서 relaxation하는 것입니다.

### 왜 `V-1`번인가

음수 cycle의 영향을 받지 않는 최단 경로는 같은 정점을 반복해서 방문할 필요가 없습니다.

정점을 반복하면 cycle이 생깁니다.

Cycle의 총가중치가

```text
양수 또는 0
```

이라면 제거해도 경로가 더 나빠지지 않습니다.

음수 cycle이라면 최단 거리가 유한하게 정의되지 않습니다.

따라서 유한한 최단 경로가 존재하는 경우 simple path로 생각할 수 있고, `V`개의 정점을 사용하는 simple path는 최대 `V-1`개의 간선을 가집니다.

### 반복의 의미

Bellman–Ford에서 다음 불변식을 사용할 수 있습니다.

```text
k번째 전체 반복이 끝나면
시작점에서 간선을 최대 k개 사용하는 경로의 최단 비용이 반영됩니다.
```

따라서 `V-1`번 반복하면 유한한 최단 경로에 필요한 모든 간선 수가 반영됩니다.

### 기본 절차

```text
dist[start] = 0

V-1번 반복:
    changed = false

    모든 간선 (u, v, w)에 대해:
        if dist[u]가 유한하고
           dist[u] + w < dist[v]:

            dist[v] = dist[u] + w
            parent[v] = u
            changed = true

    if changed == false:
        break
```

한 반복에서 어떤 거리도 바뀌지 않았다면 이후 반복에서도 바뀔 값이 없습니다.

따라서 조기 종료할 수 있습니다.

### reachable negative cycle 탐지

`V-1`번 relaxation 이후에 한 번 더 모든 간선을 확인합니다.

어떤 간선에서 여전히

```text
dist[u] + w < dist[v]
```

가 가능하다면 시작점에서 도달 가능한 음수 cycle이 있습니다.

왜냐하면 simple path는 이미 최대 `V-1`개의 간선으로 모두 반영되었기 때문입니다.

그 이후에도 거리를 줄일 수 있다는 것은 어떤 정점을 반복해서 방문하는 cycle을 이용해 비용을 더 줄이고 있다는 뜻입니다.

### 시작점에서 도달할 수 없는 음수 cycle

Single-source shortest path에서는 시작점에서 도달할 수 없는 영역의 cycle은 결과에 영향을 주지 않습니다.

예를 들어

```text
S -> A : 3

X -> Y : -2
Y -> X : -2
```

`X`, `Y`의 음수 cycle은 `S`에서 도달할 수 없습니다.

따라서 `S`를 시작점으로 하는 shortest path 결과에는 영향을 주지 않습니다.

이 때문에 negative-cycle 검사에서도 반드시

```text
dist[u]가 유한한 경우에만
```

relaxation 가능성을 확인해야 합니다.

그렇지 않으면 도달 불가능한 cycle까지 오류로 처리할 수 있습니다.

### 음수 cycle의 영향을 받는 정점

Reachable negative cycle이 존재하면 그 cycle에서 도달 가능한 정점들은 유한한 최단 거리를 갖지 못할 수 있습니다.

Cycle을 한 번 더 돌 때마다 비용을 계속 줄일 수 있기 때문입니다.

예:

```text
A -> B : 1
B -> C : -3
C -> B : 1
C -> D : 2
```

`B -> C -> B` cycle의 가중치는

```text
-3 + 1 = -2
```

입니다.

Cycle을 반복할수록 `B`, `C`의 거리는 계속 작아지고, `C`에서 도달 가능한 `D` 역시 유한한 최단 거리가 정의되지 않습니다.

API가 단순히 "reachable negative cycle이 있으면 오류"를 반환할 수도 있고, 영향을 받는 정점을 별도로 표시할 수도 있습니다.

반환 계약을 미리 정해야 합니다.

---

## 6. Floyd–Warshall

Floyd–Warshall은 모든 정점 쌍의 최단 거리, 즉 **all-pairs shortest path**를 계산하는 dynamic programming 알고리즘입니다.

시간 복잡도는

```text
O(V³)
```

이고 거리 matrix를 사용하면 공간은 보통

```text
O(V²)
```

입니다.

### 초기화

보통 다음처럼 시작합니다.

```text
dist[i][i] = 0
```

직접 간선 `i -> j`가 있다면

```text
dist[i][j] = weight(i, j)
```

간선이 없다면

```text
dist[i][j] = infinity
```

로 둡니다.

중복 간선이 있을 수 있다면 같은 `(i, j)`에 대해 최소 가중치를 저장해야 합니다.

```text
dist[i][j] = min(existing, weight)
```

그렇지 않고 마지막 입력으로 덮어쓰면 더 좋은 직접 간선을 잃을 수 있습니다.

### 상태 정의

Floyd–Warshall의 상태를 정확히 정의하면 loop 순서를 이해하기 쉽습니다.

개념적으로

```text
D_k[i][j]
```

를 다음과 같이 정의합니다.

```text
중간 정점으로 {0, 1, ..., k}만 사용할 수 있을 때
i에서 j로 가는 최단 거리
```

정점 `k`를 새 중간 정점으로 허용할 때 경로는 두 경우 중 하나입니다.

```text
k를 사용하지 않음
D_(k-1)[i][j]

k를 사용함
D_(k-1)[i][k] + D_(k-1)[k][j]
```

따라서 점화식은 다음과 같습니다.

```text
D_k[i][j]
=
min(
    D_(k-1)[i][j],
    D_(k-1)[i][k] + D_(k-1)[k][j]
)
```

이를 하나의 matrix에 in-place로 구현하면 다음 형태가 됩니다.

```text
for k:
    for i:
        for j:
            dist[i][j] =
                min(dist[i][j],
                    dist[i][k] + dist[k][j])
```

### 왜 `k` loop가 가장 바깥이어야 하는가

`k`는 "이번 단계에서 새로 허용하는 중간 정점"을 뜻합니다.

따라서 `k` 하나에 대해 모든 `(i, j)`를 갱신한 뒤 다음 `k+1` 단계로 넘어가야 합니다.

즉 상태의 단계가

```text
허용 중간 정점 집합:
{}
{0}
{0,1}
{0,1,2}
...
```

순서로 확장됩니다.

`i`, `j` loop를 바깥으로 옮기면 일반적으로 이 단계별 DP 의미가 깨지고, 일부 경로가 필요한 시점에 아직 반영되지 않거나 너무 일찍 반영될 수 있습니다.

따라서 표준 Floyd–Warshall 점화식을 사용할 때는 `k`가 가장 바깥이어야 합니다.

### 음수 cycle 탐지

Floyd–Warshall이 끝난 뒤

```text
dist[v][v] < 0
```

인 정점 `v`가 있다면 `v`에서 출발해 다시 `v`로 돌아오는 음수 비용 경로가 존재합니다.

즉 `v`에서 도달 가능한 어떤 음수 cycle이 있고, 그 cycle을 이용해 다시 `v`로 돌아올 수 있습니다.

Cycle 자체가 반드시 `v`를 직접 포함해야 하는 것은 아닙니다.

예를 들어 `v`에서 음수 cycle로 갔다가 다시 `v`로 돌아오는 경로가 있을 수도 있습니다.

### 모든 pair가 음수 cycle의 영향을 받는 것은 아닙니다

어떤 음수 cycle이 존재해도 모든 `(i, j)` 최단 거리가 무조건 정의되지 않는 것은 아닙니다.

정점 `k`에 대해

```text
dist[k][k] < 0
```

이고 동시에

```text
i -> k 도달 가능
k -> j 도달 가능
```

이라면 `(i, j)`는 그 음수 cycle의 영향을 받습니다.

이 경우 cycle을 반복해 `i -> j` 경로 비용을 계속 줄일 수 있으므로 유한한 최단 거리가 존재하지 않습니다.

---

## 7. 도달 불가능과 무한대 표현

도달 불가능한 정점은 실제 거리 값과 구분되는 상태로 표현해야 합니다.

### 잘못된 예

```text
0 = 도달 불가능
```

로 사용하면 시작점의 거리 `0`과 구분할 수 없습니다.

### 가능한 표현

다음 방법을 사용할 수 있습니다.

- `None` 같은 별도 값 사용
- 언어가 제공하는 infinity 값 사용
- 충분히 큰 sentinel 사용
- 별도의 reachable 배열 사용

### 큰 정수 sentinel의 위험

예를 들어

```text
INF = 10^18
```

같은 값을 사용하더라도 다음 연산은 주의해야 합니다.

```text
INF + weight
```

고정 폭 정수에서는 overflow가 발생할 수 있습니다.

따라서 다음처럼 유한한 거리인지 먼저 확인합니다.

```text
if dist[u] != INF:
    candidate = dist[u] + weight
```

또는 입력 가중치와 최대 경로 길이 상한을 이용해 안전한 sentinel을 계산합니다.

### 서로 다른 세 상태

최소한 다음 상태는 구분해야 합니다.

```text
거리 0
도달 불가능
음수 cycle 때문에 유한한 최단 거리가 정의되지 않음
```

예:

```text
0
None
NEGATIVE_CYCLE_AFFECTED
```

실제 API에서는 예외, 별도 boolean 배열, tagged union 등으로 표현할 수 있습니다.

---

## 8. 경로 복원

Single-source 알고리즘에서 실제 경로가 필요하다면 relaxation으로 `dist[v]`가 실제로 줄어들 때

```text
parent[v] = u
```

를 기록합니다.

예를 들어

```text
parent[C] = B
parent[B] = A
parent[A] = S
```

라면 도착점 `C`에서 역방향으로 따라갑니다.

```text
C -> B -> A -> S
```

그 뒤 뒤집습니다.

```text
S -> A -> B -> C
```

### parent는 거리 갱신과 함께 바꿉니다

다음처럼 거리가 줄어들지 않았는데 parent만 바꾸면 거리와 경로가 서로 다른 후보를 나타낼 수 있습니다.

따라서 일반적으로 다음 두 갱신은 함께 수행합니다.

```text
dist[v] = candidate
parent[v] = u
```

### 시작점과 도달 불가능 정점

보통

```text
parent[start] = None
```

으로 둡니다.

도달 불가능한 정점도 `parent = None`일 수 있으므로 parent 배열만으로 두 상태를 구분하지 않습니다.

거리 배열을 함께 확인합니다.

```text
dist[start] = 0
dist[unreachable] = None 또는 INF
```

### 음수 cycle이 있는 경우

음수 cycle의 영향을 받는 정점은 유한한 최단 경로가 존재하지 않을 수 있습니다.

이 경우 parent를 따라가다 cycle에 들어갈 수도 있습니다.

따라서 Bellman–Ford에서 음수 cycle이 탐지된 뒤에는 다음 중 하나를 명확히 정해야 합니다.

- 전체 결과를 오류로 반환
- 영향을 받지 않는 정점의 거리만 유지
- 영향을 받는 정점을 별도 표시
- 영향을 받는 정점의 경로 복원을 금지

---

## 9. 독립 검증

최단 경로 알고리즘은 작은 graph에서 다른 방식의 계산 결과와 비교하면 구현 오류를 찾기 좋습니다.

### single-source 결과를 Floyd–Warshall과 비교

작은 graph에서 Floyd–Warshall로 all-pairs 거리를 계산한 뒤 시작점 `s`의 행을 가져옵니다.

```text
floyd[s][v]
```

이를 BFS, Dijkstra, Bellman–Ford 결과와 비교할 수 있습니다.

단, 알고리즘의 전제가 맞는 입력만 비교해야 합니다.

예:

```text
BFS 검증:
모든 간선 가중치가 동일한 graph

Dijkstra 검증:
모든 간선 가중치가 0 이상인 graph

Bellman–Ford 검증:
reachable negative cycle이 없는 graph
```

### 두 후보 구현끼리만 비교하면 부족할 수 있습니다

Dijkstra와 Bellman–Ford만 서로 비교하면 둘이 같은 입력 처리 코드를 공유할 때 공통 결함을 놓칠 수 있습니다.

예를 들어 다음 오류가 두 구현에 동시에 존재할 수 있습니다.

- 간선 방향을 반대로 저장했습니다.
- 중복 간선을 마지막 값으로 잘못 덮어썼습니다.
- 도달 불가능을 잘못 초기화했습니다.
- 시작 정점 validation이 빠졌습니다.
- undirected edge를 한 방향만 저장했습니다.

따라서 독립 검증에서는 알고리즘뿐 아니라 입력 해석과 출력 계약도 따로 확인합니다.

### 작은 graph에서 추가로 확인할 조건

거리 값 비교 외에도 다음을 검사합니다.

- `dist[start] == 0`
- 도달 불가능한 정점이 올바른 sentinel을 가짐
- parent를 따라 복원한 경로가 실제 간선으로 구성됨
- 복원 경로의 가중치 합이 `dist[target]`과 같음
- 음수 간선 입력에서 Dijkstra가 명시적으로 거부함
- unreachable negative cycle을 Bellman–Ford가 오류로 처리하지 않음
- reachable negative cycle은 명확한 실패 또는 별도 상태로 처리함

---

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)에서 다음을 확인합니다.

- `[Implementation 7]` `bfs_distances`
- `[Implementation 8]` `dijkstra`
- `[Implementation 10]` `bellman_ford`

구현에서 확인할 핵심은 다음과 같습니다.

### `bfs_distances`

- 모든 간선 비용이 동일한 상황을 전제로 합니다.
- 정점을 처음 발견할 때 거리를 기록합니다.
- queue에 넣는 시점에 발견 상태를 확정해 중복 삽입을 막습니다.

### `dijkstra`

- 음수 간선을 입력 오류로 거부합니다.
- heap에서 꺼낸 거리와 현재 `dist`가 다르면 stale entry로 버립니다.
- 음수 간선이 없다는 전제 아래 pop된 최소 거리의 확정성을 이용합니다.

### `bellman_ford`

- 최대 `V-1`번 전체 간선을 relaxation합니다.
- 시작점에서 도달 가능한 간선만 relaxation합니다.
- 추가 relaxation 가능 여부로 reachable negative cycle을 검사합니다.
- 시작점에서 도달할 수 없는 negative cycle은 single-source 결과의 오류로 처리하지 않습니다.

테스트는 작은 graph의 Floyd–Warshall 결과를 독립 기준으로 사용합니다.

DAG shortest path는 공개 API에 없으므로 다음 순서로 작은 구현을 별도로 작성합니다.

```text
topological order 계산
cycle이면 거부
dist[start] = 0
topological order 앞에서부터 outgoing edge relaxation
```

---

## 완료 기준

- 간선 가중치와 graph 구조 조건에 따라 BFS, DAG relaxation, Dijkstra, Bellman–Ford를 선택합니다.
- Relaxation이 현재 거리 후보를 줄이는 연산임을 설명합니다.
- BFS에서 처음 발견한 거리가 확정되는 이유를 설명합니다.
- DAG에서 topological order 때문에 각 정점을 다시 처리할 필요가 없는 이유를 설명합니다.
- Dijkstra에서 음수 간선이 없어야 pop된 최소 거리를 확정할 수 있는 이유를 설명합니다.
- Bellman–Ford의 `k`번째 반복이 최대 `k`개 간선 경로를 반영한다는 의미를 설명합니다.
- reachable negative cycle과 unreachable negative cycle을 구분합니다.
- 도달 불가능, 거리 `0`, negative cycle의 영향을 서로 다른 결과로 표현합니다.
- Floyd–Warshall에서 `k` loop가 가장 바깥이어야 하는 이유를 DP 상태 정의로 설명합니다.
- Floyd–Warshall에서 `dist[v][v] < 0`의 의미를 설명합니다.
- parent를 이용한 경로 복원과 음수 cycle이 있을 때의 제한을 설명합니다.
- 후보와 다른 계산 방법으로 작은 graph 결과를 확인합니다.

## 실패 신호

- 음수 간선이 있는 graph에 일반 Dijkstra를 사용합니다.
- "음수 cycle만 없으면 Dijkstra를 사용할 수 있다"고 생각합니다.
- stale heap entry를 계속 확장합니다.
- 가중치가 서로 다른 graph에 일반 BFS를 사용합니다.
- DAG가 아닌데 topological relaxation을 실행합니다.
- Bellman–Ford에서 `dist[u]`가 도달 불가능한데도 덧셈을 수행합니다.
- Bellman–Ford가 도달할 수 없는 음수 cycle까지 오류로 처리합니다.
- reachable negative cycle이 있어도 유한한 최단 거리가 있다고 가정합니다.
- 도달 불가능과 거리 `0`을 같은 값으로 표현합니다.
- 음수 cycle 영향 상태를 단순한 유한 거리와 같은 형식으로 해석합니다.
- Floyd–Warshall loop 순서를 바꿔 상태 정의를 깨뜨립니다.
- Floyd–Warshall 초기화에서 중복 간선의 최소 가중치를 보존하지 않습니다.
- 큰 sentinel끼리 더해 overflow합니다.
- 거리 갱신 없이 parent만 바꿔 거리와 복원 경로가 불일치합니다.
