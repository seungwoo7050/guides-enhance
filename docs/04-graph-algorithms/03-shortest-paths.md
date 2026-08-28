# 최단 경로

## 학습 목표

- 간선 가중치 조건에 따라 BFS, DAG relaxation, Dijkstra, Bellman–Ford를 선택합니다.
- Relaxation이 어떤 값을 줄이는 연산인지 설명합니다.
- 도달할 수 없는 정점과 음수 cycle의 영향을 구분합니다.
- Floyd–Warshall의 상태와 loop 순서를 설명합니다.

## 선행지식

[그래프 순회](01-traversal-and-topological-order.md), heap, dynamic programming의 상태 갱신을 알고 있어야 합니다.

## 핵심 관점

최단 경로 알고리즘의 공통 연산은 relaxation입니다.

```text
if dist[u]가 정해져 있고 dist[u] + weight(u, v) < dist[v]:
    dist[v] = dist[u] + weight(u, v)
    parent[v] = u
```

알고리즘마다 어떤 순서로, 몇 번 relaxation하면 값이 확정되는지가 다릅니다.

## 1. 선택 기준

| 입력 조건 | 알고리즘 | 대표 시간 |
| --- | --- | ---: |
| 모든 간선 비용이 동일합니다. | BFS | `O(V+E)` |
| DAG이며 음수 간선을 허용합니다. | topological relaxation | `O(V+E)` |
| 모든 간선 가중치가 음수가 아닙니다. | Dijkstra | `O((V+E) log V)` |
| 음수 간선을 허용하고 reachable negative cycle을 찾아야 합니다. | Bellman–Ford | `O(VE)` |
| 정점 수가 작은 all-pairs 문제입니다. | Floyd–Warshall | `O(V³)` |

간선 비용이 0과 1뿐이라면 deque를 사용하는 0-1 BFS도 검토할 수 있습니다.

## 2. BFS

모든 간선의 비용이 1이면 queue의 level 순서가 거리 순서입니다. 정점을 처음 발견할 때 거리를 정하면 그 값이 최단 거리입니다.

가중치가 서로 다른 그래프에 일반 BFS를 사용하면 간선 수가 적은 경로만 찾을 뿐 가중치 합이 작은 경로를 보장하지 않습니다.

## 3. DAG 최단 경로

Topological order로 정점을 방문하며 outgoing edge를 한 번씩 relaxation합니다. 뒤쪽 정점에서 앞쪽 정점으로 돌아가는 간선이 없으므로 이미 처리한 상태를 다시 갱신할 필요가 없습니다.

Cycle이 없기 때문에 음수 간선을 허용해도 됩니다. Topological order를 구하지 못했다면 DAG 알고리즘을 실행하지 않습니다.

## 4. Dijkstra

전조건은 모든 간선 가중치가 음수가 아니라는 것입니다.

```text
heap에서 현재 tentative distance가 가장 작은 정점을 꺼냅니다.
꺼낸 거리와 현재 distance 배열이 다르면 오래된 항목이므로 버립니다.
outgoing edge를 relaxation합니다.
```

음수 간선이 없으면 heap에서 현재 최소 거리로 꺼낸 정점의 거리는 이후 더 줄어들 수 없습니다.

음수 간선이 있으면 나중에 발견한 경로가 이미 확정한 값을 줄일 수 있어 이 근거가 깨집니다. 단순히 음수 cycle이 없다는 조건만으로는 Dijkstra를 사용할 수 없습니다.

## 5. Bellman–Ford

모든 간선을 최대 `V-1`번 반복해서 relaxation합니다.

```text
k번째 반복이 끝나면 시작점에서 간선을 최대 k개 사용하는 모든 경로가 반영됩니다.
```

음수 cycle이 없을 때 단순 최단 경로는 같은 정점을 반복할 필요가 없으므로 간선을 최대 `V-1`개 사용합니다.

`V-1`번 뒤 한 번 더 relaxation했을 때 거리가 줄어들면 시작점에서 도달 가능한 음수 cycle이 있습니다. 시작점에서 도달할 수 없는 음수 cycle은 single-source 결과에 영향을 주지 않습니다.

한 반복에서 값이 전혀 바뀌지 않으면 더 일찍 끝낼 수 있습니다.

## 6. Floyd–Warshall

상태는 다음과 같이 정의합니다.

```text
dist[i][j]
= 지금까지 허용한 중간 정점만 사용해 i에서 j로 가는 최단 거리
```

정점 `k`를 새 중간 후보로 허용합니다.

```text
dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])
```

`k` loop가 가장 바깥에 있어야 이전 단계의 의미를 유지할 수 있습니다.

`dist[v][v] < 0`이라면 `v`에서 도달하고 다시 `v`로 돌아올 수 있는 음수 cycle이 있습니다. Cycle 자체가 반드시 `v`를 직접 포함하는 것은 아닙니다.

## 7. 도달 불가능과 무한대 표현

도달 불가능을 큰 정수 하나로 표현할 때는 덧셈 overflow를 주의합니다.

가능한 방법은 다음과 같습니다.

- `None` 같은 별도 값 사용
- 명시적인 infinity 객체 사용
- `dist[u]`가 유한할 때만 덧셈
- 입력 상한으로 overflow하지 않는 sentinel 계산

거리 `0`, 도달 불가능, 음수 cycle의 영향을 받은 상태를 같은 값으로 표현하지 않습니다.

## 8. 경로 복원

Relaxation으로 값이 실제로 줄어들 때 `parent[v] = u`를 기록합니다. 도착점에서 parent를 따라가면 경로를 복원할 수 있습니다.

음수 cycle의 영향을 받는 정점에는 최단 경로가 정의되지 않을 수 있습니다. 거리 배열만 반환할지, 영향을 받는 정점을 별도 표시할지 함수 조건에서 정합니다.

## 9. 독립 검증

작은 그래프에서는 Floyd–Warshall 결과를 single-source 후보와 비교합니다.

Dijkstra와 Bellman–Ford만 서로 비교하면 다음 공통 결함을 놓칠 수 있습니다.

- 간선 방향을 반대로 저장했습니다.
- 중복 간선을 잘못 덮어썼습니다.
- 도달 불가능을 잘못 초기화했습니다.
- 시작 정점 validation이 빠졌습니다.

입력 처리와 결과 형식도 별도로 검사합니다.

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)에서 다음을 확인합니다.

- `[Implementation 7]` `bfs_distances`
- `[Implementation 8]` `dijkstra`
- `[Implementation 10]` `bellman_ford`

테스트는 작은 그래프의 Floyd–Warshall 결과를 기준으로 사용합니다. Dijkstra는 음수 간선을 거부하며, Bellman–Ford는 reachable negative cycle만 오류로 처리합니다.

DAG shortest path는 공개 API에 없으므로 topological order와 relaxation을 결합한 작은 구현을 별도로 작성합니다.

## 완료 기준

- 간선 가중치 조건에 따라 BFS, DAG, Dijkstra, Bellman–Ford를 선택합니다.
- 각 알고리즘에서 거리 값이 확정되는 이유를 설명합니다.
- 도달 불가능, 거리 0, reachable negative cycle을 서로 다른 결과로 표현합니다.
- Floyd–Warshall에서 `k` loop가 가장 바깥이어야 하는 이유를 설명합니다.
- 후보와 다른 계산 방법으로 작은 그래프 결과를 확인합니다.

## 실패 신호

- 음수 간선이 있는 그래프에 Dijkstra를 사용합니다.
- stale heap entry를 계속 확장합니다.
- 도달 불가능과 거리 0을 같은 값으로 표현합니다.
- Bellman–Ford가 도달할 수 없는 음수 cycle까지 오류로 처리합니다.
- Floyd–Warshall loop 순서를 바꿔 상태 정의를 깨뜨립니다.
- 큰 sentinel끼리 더해 overflow합니다.
