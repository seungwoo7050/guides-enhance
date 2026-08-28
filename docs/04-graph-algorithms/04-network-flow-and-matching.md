# 네트워크 유량과 이분 매칭

## 학습 목표

- capacity, flow, residual capacity, flow conservation을 구분합니다.
- residual graph의 역방향 간선이 이전 선택을 취소하는 방법을 설명합니다.
- max-flow min-cut 관계를 독립 검증에 사용합니다.
- bipartite matching을 flow network로 바꿉니다.

## 선행지식

[그래프 순회](01-traversal-and-topological-order.md), BFS, 경로를 따라 상태를 갱신하면서 불변식을 유지하는 방법을 알고 있어야 합니다.

## 핵심 관점

Flow network는 directed graph, source `s`, sink `t`, 음수가 아닌 capacity `c(u, v)`로 구성됩니다.

유효한 flow `f`는 다음 조건을 만족합니다.

```text
0 <= f(u, v) <= c(u, v)
source와 sink를 제외한 모든 정점에서 유입량 == 유출량
```

최대 유량 값만 맞는다고 충분하지 않습니다. 반환한 실제 flow가 이 조건을 만족하는지도 확인해야 합니다.

## 1. residual graph

원본 간선 `u -> v`에 현재 `f(u, v)`만큼 보냈다면 정방향으로 더 보낼 수 있는 양은 다음과 같습니다.

```text
forward residual = c(u, v) - f(u, v)
```

이미 보낸 양을 취소할 수 있도록 역방향 residual capacity도 생깁니다.

```text
reverse residual += f(u, v)
```

원본 graph에 `v -> u` 간선이 없어도 residual graph에는 역방향 이동이 존재할 수 있습니다. 이는 이전에 `u -> v`로 보낸 flow 일부를 취소한다는 뜻입니다.

## 2. augmenting path

Residual graph에서 `s`에서 `t`로 가는 경로를 찾습니다. 경로에서 보낼 수 있는 양은 각 residual capacity의 최솟값입니다.

```text
amount = min(residual capacity on the path)
```

경로를 따라 다음을 수행합니다.

- 정방향 residual을 사용하면 해당 원본 방향의 flow를 늘립니다.
- 역방향 residual을 사용하면 반대 방향으로 보냈던 flow를 줄입니다.

이 갱신은 각 간선의 capacity 제한과 중간 정점의 유입·유출 일치를 유지해야 합니다.

## 3. Ford–Fulkerson과 Edmonds–Karp

Ford–Fulkerson은 augmenting path를 반복해서 찾는 방식 전체를 가리킵니다. 정수 capacity에서는 한 번에 최소 1 이상 늘어나므로 종료하지만, 경로 선택에 따라 실행 시간이 크게 달라질 수 있습니다.

Edmonds–Karp는 BFS로 간선 수가 가장 적은 augmenting path를 선택합니다.

- 시간 상한: `O(VE²)`
- 경로 길이가 짧은 순서로 증가합니다.
- 구현이 단순해 residual 조건을 학습하기 좋습니다.

더 큰 입력에서는 Dinic 같은 알고리즘을 검토할 수 있지만, 먼저 역방향 residual과 flow conservation을 정확히 구현해야 합니다.

## 4. max-flow min-cut

Cut `(S, T)`는 다음 조건을 만족하는 정점 분할입니다.

```text
s ∈ S
t ∈ T
```

Cut capacity는 원본 간선 중 `S`에서 `T`로 향하는 간선의 capacity 합입니다.

어떤 flow 값도 어떤 cut capacity보다 클 수 없습니다. 더 이상 augmenting path가 없을 때 residual graph에서 source가 도달할 수 있는 정점 집합이 minimum cut을 만듭니다. 따라서 최대 유량 값과 최소 cut capacity가 같습니다.

작은 그래프에서는 source와 sink를 제외한 정점의 모든 부분집합을 열거해 최소 cut 값을 구할 수 있습니다.

## 5. 이분 매칭을 flow로 바꿉니다

왼쪽 정점 집합 `L`, 오른쪽 정점 집합 `R`이 있는 bipartite graph에서 maximum matching을 구합니다.

다음 network를 만듭니다.

```text
source -> 각 L 정점: capacity 1
L -> R의 원본 연결: capacity 1
각 R 정점 -> sink: capacity 1
```

정수 capacity의 최대 flow는 정수값을 가지며, flow 값이 matching 크기입니다. `L -> R` 간선 중 flow가 1인 간선이 선택한 pair입니다.

Source와 각 `L`, 각 `R`과 sink의 capacity를 1로 두기 때문에 한 정점이 두 pair에 동시에 사용되지 않습니다.

## 6. 정점 capacity

간선이 아니라 정점의 사용 횟수를 제한해야 한다면 정점을 `in`과 `out`으로 나눕니다.

```text
v_in -> v_out: 정점 capacity
원본 u -> v: u_out -> v_in
```

Source와 sink를 나눌지, 무한 capacity를 어떤 안전한 값으로 표현할지 문제 조건에 따라 정합니다.

## 7. 모델링 전에 확인할 질문

- 정점 하나를 여러 번 사용할 수 있습니까?
- 제한값은 간선에 있습니까, 정점에 있습니까?
- capacity의 단위는 사람 수, 대역폭, 작업 수 중 무엇입니까?
- source와 sink가 여러 개라면 super source·sink가 필요합니까?
- 최대량뿐 아니라 비용도 최소화해야 합니까?
- 시간에 따라 달라지는 값을 정적인 network로 표현할 수 있습니까?

문제를 flow로 바꾸기 전에 원래 대상과 새 정점·간선의 대응을 표로 적습니다.

## 8. 입력과 반환값

다음 조건을 정합니다.

- capacity matrix가 정사각형입니까?
- 모든 capacity가 음수가 아닌 정수입니까?
- source와 sink index가 유효합니까?
- parallel edge를 합산합니까?
- source와 sink가 같을 때 결과는 무엇입니까?
- 함수가 값만 반환합니까, 실제 flow도 반환합니까?

실제 flow를 반환한다면 원본 directed edge 기준의 matrix인지 residual matrix인지 혼동하지 않습니다.

## 9. flow certificate 검증

`(value, flow)`를 반환한다고 가정하면 다음을 별도로 검사합니다.

1. `flow`가 capacity와 같은 크기의 정사각 matrix입니다.
2. 각 값이 정수이며 `0 <= flow[u][v] <= capacity[u][v]`입니다.
3. 중간 정점마다 유입량과 유출량이 같습니다.
4. source의 순유출량이 `value`와 같습니다.
5. sink의 순유입량이 `value`와 같습니다.
6. `value`가 작은 그래프의 minimum cut과 같습니다.

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 11]`을 확인합니다.

- 입력 capacity matrix의 크기와 음수 값을 검사합니다.
- BFS로 augmenting path를 찾습니다.
- 역방향 기존 flow를 먼저 취소한 뒤 남은 양을 정방향 flow로 보냅니다.
- antiparallel 원본 간선이 있어도 각 방향의 capacity 안에 있는 flow matrix를 반환합니다.
- 테스트가 모든 source-side cut을 열거하고 flow certificate를 별도로 검사합니다.

## 완료 기준

- 원본 capacity, 현재 flow, residual capacity를 다른 값으로 설명합니다.
- 역방향 residual edge가 이전 flow를 취소하는 과정을 작은 network에서 추적합니다.
- 반환한 값뿐 아니라 capacity와 conservation을 검사합니다.
- maximum matching network에서 각 원본 정점과 새 간선의 역할을 설명합니다.
- 작은 그래프의 모든 cut을 열거해 최댓값을 독립적으로 확인합니다.

## 실패 신호

- 역방향 residual edge를 만들지 않습니다.
- residual capacity와 원본 capacity를 같은 의미의 배열로 사용합니다.
- 최대 유량 값만 검사하고 실제 flow는 확인하지 않습니다.
- augmenting path가 없는지 원본 graph에서 검사합니다.
- matching 변환에서 정점 사용 횟수 1을 강제하지 않습니다.
- antiparallel 간선에서 한 방향 flow가 원본 capacity를 넘습니다.
