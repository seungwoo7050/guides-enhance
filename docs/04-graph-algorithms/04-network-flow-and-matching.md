# 네트워크 유량과 이분 매칭

## 학습 목표

- capacity, flow, residual capacity, flow conservation을 서로 다른 상태로 구분합니다.
- residual graph가 현재 flow를 기준으로 "추가로 보낼 수 있는 양"과 "이미 보낸 양을 되돌릴 수 있는 양"을 표현한다는 점을 설명합니다.
- residual graph의 역방향 간선이 이전 선택을 취소하고 다른 경로로 재배치하는 과정을 설명합니다.
- augmenting path를 따라 flow를 갱신하면서 capacity constraint와 flow conservation을 유지합니다.
- Ford–Fulkerson과 Edmonds–Karp의 관계를 설명합니다.
- max-flow min-cut 관계를 독립 검증에 사용합니다.
- bipartite matching을 flow network로 변환하고 matching을 다시 복원합니다.
- 정점 capacity를 vertex splitting으로 간선 capacity 문제로 바꿉니다.

## 선행지식

[그래프 순회](01-traversal-and-topological-order.md), BFS, 경로를 따라 상태를 갱신하면서 불변식을 유지하는 방법을 알고 있어야 합니다.

이 문서에서는 다음 표기법을 사용합니다.

- `G = (V, E)`: directed flow network
- `s`: source
- `t`: sink
- `c(u, v)`: 원본 간선 `u -> v`의 capacity
- `f(u, v)`: 현재 원본 방향으로 보내는 flow
- `r(u, v)`: residual graph에서 `u -> v`로 추가 이동할 수 있는 양
- `|f|`: 전체 flow value

---

## 핵심 관점

Flow network는 directed graph, source `s`, sink `t`, 음수가 아닌 capacity `c(u, v)`로 구성됩니다.

Capacity는 간선이 허용하는 최대 통과량입니다.

예를 들어

```text
c(u, v) = 7
```

이라면 `u -> v`를 통해 최대 `7`만큼의 flow를 보낼 수 있다는 뜻입니다.

유효한 flow `f`는 최소한 다음 조건을 만족합니다.

### Capacity constraint

원본 간선마다

```text
0 <= f(u, v) <= c(u, v)
```

이어야 합니다.

Flow는 capacity를 초과할 수 없습니다.

### Flow conservation

Source와 sink를 제외한 모든 정점에서는 총유입량과 총유출량이 같아야 합니다.

```text
sum of incoming flow
=
sum of outgoing flow
```

중간 정점은 flow를 새로 만들거나 없앨 수 없다는 뜻입니다.

### Flow value

전체 flow 값은 source에서 빠져나가는 순유출량으로 정의할 수 있습니다.

```text
|f|
=
source의 총유출량 - source의 총유입량
```

같은 값이 sink의 순유입량과 일치해야 합니다.

```text
|f|
=
sink의 총유입량 - sink의 총유출량
```

많은 기본 network에서는 source로 들어오는 원본 간선과 sink에서 나가는 원본 간선이 없으므로 단순히 각각 총유출량과 총유입량을 사용해도 됩니다.

하지만 일반적인 directed graph를 허용하는 API라면 **순유량(net flow)** 으로 정의하는 편이 정확합니다.

최대 유량 값만 맞는다고 충분하지 않습니다. 반환한 실제 flow가 capacity constraint와 flow conservation을 만족하는지도 확인해야 합니다.

---

## 1. residual graph

Residual graph는 현재 flow를 기준으로 앞으로 **얼마나 더 보낼 수 있는지**, 그리고 이미 보낸 flow를 **얼마나 되돌릴 수 있는지**를 나타냅니다.

원본 capacity 자체와 residual capacity는 같은 값이 아닙니다.

### 정방향 residual capacity

원본 간선 `u -> v`의 capacity가 `c(u, v)`이고 현재 `f(u, v)`만큼 flow를 보냈다면 정방향으로 더 보낼 수 있는 양은

```text
c(u, v) - f(u, v)
```

입니다.

즉

```text
forward residual
=
capacity - current flow
```

입니다.

예를 들어

```text
c(u, v) = 10
f(u, v) = 6
```

이라면

```text
r(u, v) = 4
```

만큼 더 보낼 수 있습니다.

### 역방향 residual capacity

이미 `u -> v`로 `6`만큼 보냈다면 그중 일부를 취소할 수도 있어야 합니다.

따라서 residual graph에는 반대 방향으로

```text
r(v, u) += 6
```

의 이동 가능성이 생깁니다.

이 residual edge는 반드시 원본 graph의 실제 간선을 뜻하지 않습니다.

```text
원본:
u -> v

residual:
u -> v   # 더 보낼 수 있는 양
v -> u   # 기존 flow를 되돌릴 수 있는 양
```

원본 graph에 `v -> u` 간선이 없어도 residual graph에는 `v -> u` 방향이 생길 수 있습니다.

### 역방향 residual의 의미

Residual graph의 역방향으로 `x`만큼 이동한다는 것은

```text
반대 방향으로 새 flow x를 보낸다
```

는 뜻이 아닙니다.

정확한 의미는

```text
기존에 정방향으로 보냈던 flow를 x만큼 취소한다
```

입니다.

예를 들어 현재

```text
f(u, v) = 5
```

인데 augmenting path가 residual edge `v -> u`를 `2`만큼 사용한다면

```text
f(u, v) = 3
```

으로 줄어듭니다.

이 "취소 가능성" 때문에 greedy하게 먼저 고른 경로가 나중에 잘못된 선택으로 밝혀져도 flow를 다른 경로로 재배치할 수 있습니다.

### 원본 antiparallel edge가 있는 경우

원본 graph에 다음 두 간선이 모두 있을 수 있습니다.

```text
u -> v
v -> u
```

이런 경우를 antiparallel edge라고 부를 수 있습니다.

이때 residual 방향 `v -> u`는 두 의미가 겹칠 수 있습니다.

```text
원본 v -> u 간선의 남은 capacity
+
원본 u -> v flow를 취소할 수 있는 양
```

따라서 구현에서는 "residual capacity"와 "원본 방향별 flow"를 혼동하지 않아야 합니다.

특히 실제 flow matrix를 반환한다면 각 원본 방향의 flow가 자신의 capacity를 넘지 않도록 별도로 관리해야 합니다.

---

## 2. augmenting path

**Augmenting path**는 residual graph에서 source `s`에서 sink `t`까지 가는 경로입니다.

경로에 포함된 모든 residual edge는 residual capacity가 양수여야 합니다.

예를 들어 다음 residual path가 있다고 합시다.

```text
s -> a -> b -> t
```

각 residual capacity가

```text
s -> a : 5
a -> b : 3
b -> t : 7
```

이면 이 경로를 통해 추가로 보낼 수 있는 최대 양은

```text
min(5, 3, 7) = 3
```

입니다.

이를 **bottleneck capacity**라고 볼 수 있습니다.

```text
amount
=
min(residual capacity on the path)
```

### 경로를 따라 flow 갱신

Augmenting path의 각 residual edge에 대해 `amount`만큼 갱신합니다.

#### 정방향 residual edge를 사용한 경우

원본 방향 `u -> v`의 남은 capacity를 사용한 것이므로

```text
f(u, v) += amount
```

합니다.

#### 역방향 residual edge를 사용한 경우

기존에 반대 방향으로 보내던 flow를 취소한 것이므로

```text
f(v, u) -= amount
```

처럼 해석합니다.

구현 방식에 따라 residual matrix만 직접 갱신할 수도 있고, 원본 flow matrix를 함께 갱신할 수도 있습니다. 어느 방식이든 최종적으로 capacity와 conservation을 만족해야 합니다.

### 왜 flow conservation이 유지되는가

Augmenting path의 중간 정점 `v`를 생각해 봅시다.

Path를 따라 `v`로 `amount`만큼 들어오고, 동시에 `v`에서 다음 정점으로 `amount`만큼 나갑니다.

따라서 중간 정점에서는

```text
유입 증가량 = 유출 증가량
```

이므로 flow conservation이 유지됩니다.

역방향 residual edge가 포함된 경우에도 이는 "기존 flow 취소"로 해석되며 순변화는 path의 앞뒤에서 같은 양으로 맞춰집니다.

Source에서는 순유출량이 `amount`만큼 증가하고 sink에서는 순유입량이 `amount`만큼 증가합니다.

따라서 전체 flow value는

```text
|f| += amount
```

만큼 증가합니다.

---

## 3. 역방향 residual이 왜 필요한가

작은 예로 이전 선택을 취소하는 과정을 보겠습니다.

다음 network를 생각해 봅시다.

```text
s -> a : 1
s -> b : 1
a -> x : 1
a -> y : 1
b -> x : 1
x -> t : 1
y -> t : 1
```

처음에 다음 augmenting path를 골랐다고 합시다.

```text
s -> a -> x -> t
```

1만큼 보내면

```text
a -> x
```

가 사용됩니다.

이 상태에서는 `b`가 `x`를 통해 `t`로 가고 싶어도 `x -> t`가 이미 가득 찼습니다.

하지만 residual graph에는 기존 `a -> x` flow를 취소할 수 있는

```text
x -> a
```

역방향 residual edge가 생깁니다.

그래서 다음 residual path를 찾을 수 있습니다.

```text
s -> b -> x -> a -> y -> t
```

이 path를 따라 1만큼 augment하면 의미는 다음과 같습니다.

```text
s -> b : 새 flow 추가
b -> x : 새 flow 추가
x -> a : 기존 a -> x flow 취소
a -> y : 새 flow 추가
y -> t : 새 flow 추가
```

결과적으로 flow는 다음처럼 재배치됩니다.

```text
s -> a -> y -> t
s -> b -> x -> t
```

총 flow value는 `2`가 됩니다.

역방향 residual edge가 없다면 처음 선택한 `a -> x`를 되돌릴 수 없어서 최댓값 `2`에 도달하지 못할 수 있습니다.

따라서 residual graph의 역방향 edge는 선택적 최적화가 아니라 **최대 유량 알고리즘의 핵심 상태**입니다.

---

## 4. Ford–Fulkerson과 Edmonds–Karp

### Ford–Fulkerson

Ford–Fulkerson은 특정 하나의 path-search 알고리즘 이름이라기보다 다음 반복 구조 전체를 가리킵니다.

```text
while residual graph에 s -> t augmenting path가 존재:
    path의 bottleneck capacity를 구합니다.
    그만큼 flow를 augment합니다.
```

어떤 방식으로 augmenting path를 고르는지는 별도로 정할 수 있습니다.

DFS를 사용할 수도 있고, 다른 탐색 전략을 사용할 수도 있습니다.

### 정수 capacity에서 종료

모든 capacity가 정수이고 augmenting path가 존재한다면 bottleneck capacity도 양의 정수입니다.

따라서 매 augmentation마다 flow value가 최소 `1` 이상 증가합니다.

최대 flow value에는 유한한 상한이 있으므로 결국 종료합니다.

### 일반 실수 capacity에서는 주의

Ford–Fulkerson의 단순한 경로 선택 방식은 arbitrary real capacity에서 특정 path 선택에 따라 이론적으로 종료 보장을 잃을 수 있습니다.

따라서 "Ford–Fulkerson은 항상 종료한다"라고 일반화하면 안 됩니다.

정수 capacity라는 전제가 중요합니다.

### Edmonds–Karp

Edmonds–Karp는 Ford–Fulkerson에서 augmenting path를 **BFS**로 선택합니다.

즉 residual graph에서 간선 수가 가장 적은 `s -> t` augmenting path를 사용합니다.

대표 시간 상한은

```text
O(VE²)
```

입니다.

### 왜 BFS 선택이 의미가 있는가

Edmonds–Karp의 핵심은 단순히 "짧은 path라서 빨라 보인다"가 아닙니다.

BFS residual distance를 기준으로 특정 간선이 critical edge가 되는 횟수를 제한할 수 있고, 그 결과 augmentation 횟수에 다항식 상한을 얻습니다.

학습 단계에서는 다음 정도를 기억하면 충분합니다.

```text
Ford–Fulkerson:
augmenting path 선택 방식이 자유로운 기본 틀

Edmonds–Karp:
BFS로 최소 간선 수 augmenting path를 선택하는 구체적 구현
O(VE²) 시간 상한을 가짐
```

더 큰 입력에서는 Dinic 같은 알고리즘을 검토할 수 있지만, 먼저 다음 불변식을 정확히 구현하는 것이 중요합니다.

```text
residual capacity
역방향 residual
capacity constraint
flow conservation
```

---

## 5. max-flow min-cut

### Cut 정의

Flow network의 cut `(S, T)`는 모든 정점을 두 집합으로 나눈 partition이며 다음을 만족합니다.

```text
s ∈ S
t ∈ T
S ∪ T = V
S ∩ T = ∅
```

### Cut capacity

Cut capacity는 **원본 간선** 중 `S`에서 `T`로 향하는 간선 capacity의 합입니다.

```text
c(S, T)
=
Σ c(u, v)
u ∈ S, v ∈ T
```

여기서 `T -> S` 방향 간선은 cut capacity에 더하지 않습니다.

Cut은 directed graph의 방향을 고려합니다.

### 어떤 flow도 cut capacity를 넘을 수 없는 이유

Source에서 sink로 가는 모든 flow는 어떤 `s-t` cut을 적어도 한 번 `S -> T` 방향으로 넘어야 합니다.

Flow conservation을 이용하면 전체 flow value는 cut을 가로지르는 순flow와 같습니다.

```text
|f|
=
flow(S -> T) - flow(T -> S)
```

그리고 각 `S -> T` 간선의 flow는 자신의 capacity보다 클 수 없으므로

```text
|f|
<=
flow(S -> T)
<=
capacity(S -> T)
```

입니다.

따라서 모든 `s-t` cut에 대해

```text
flow value <= cut capacity
```

입니다.

즉 모든 cut capacity는 최대 유량 값의 상한입니다.

### augmenting path가 없을 때 minimum cut

최대 flow를 구한 뒤 residual graph에서 source `s`로부터 residual capacity가 양수인 간선만 따라 도달 가능한 정점 집합을 `S`라고 합시다.

나머지 정점을 `T`라고 둡니다.

```text
S = residual graph에서 s가 도달 가능한 정점
T = V - S
```

더 이상 `s -> t` augmenting path가 없으므로

```text
t ∉ S
```

입니다.

이 cut에서 `S -> T` 방향의 원본 간선들은 residual capacity가 남아 있으면 `T`까지 도달할 수 있어야 하므로 모두 포화되어 있습니다.

즉

```text
f(u, v) = c(u, v)
```

입니다.

반대로 `T -> S` 방향에서 실제로 양의 flow가 흐르고 있다면 그 flow를 취소하는 reverse residual edge가 `S -> T`에 존재하게 되어 `T` 정점이 도달 가능해질 수 있으므로, 최종 cut에서는 순flow와 cut capacity가 맞아떨어집니다.

결과적으로

```text
max flow value
=
min cut capacity
```

가 됩니다.

이것이 max-flow min-cut theorem입니다.

### 독립 검증에 사용

작은 graph에서는 source와 sink를 제외한 정점들을 `S` 또는 `T` 중 어디에 넣을지 모두 열거할 수 있습니다.

정점이 `V`개라면 고정된 `s`, `t`를 제외한 `V-2`개 정점에 대해

```text
2^(V-2)
```

개의 cut 후보가 있습니다.

각 cut의 capacity를 계산해 최솟값을 구하면 작은 입력에서 최대 유량 값의 독립 oracle로 사용할 수 있습니다.

이 검증은 flow 알고리즘과 다른 원리를 사용하므로 구현 결함을 찾는 데 유용합니다.

---

## 6. 이분 매칭을 flow로 바꿉니다

Bipartite graph는 정점 집합을 왼쪽 `L`과 오른쪽 `R`로 나눌 수 있고 모든 원본 edge가 `L`과 `R` 사이에만 존재하는 graph입니다.

Matching은 어떤 정점도 두 번 사용하지 않는 edge 집합입니다.

Maximum matching은 matching edge 수가 가장 큰 matching입니다.

### Flow network 구성

새 source `s`와 sink `t`를 추가합니다.

다음 간선을 만듭니다.

```text
source -> 각 L 정점: capacity 1
L -> R의 원본 연결: capacity 1
각 R 정점 -> sink: capacity 1
```

예를 들어 원본 bipartite graph가

```text
L = {A, B}
R = {X, Y}

A-X
A-Y
B-X
```

라면 flow network는

```text
s -> A : 1
s -> B : 1

A -> X : 1
A -> Y : 1
B -> X : 1

X -> t : 1
Y -> t : 1
```

가 됩니다.

### 왜 한 정점이 두 번 선택되지 않는가

각 왼쪽 정점 `u ∈ L`에는 source에서 들어오는 capacity가 `1`뿐입니다.

```text
s -> u : 1
```

따라서 `u`에서 오른쪽으로 총 `1`을 초과해 flow를 보낼 수 없습니다.

즉 왼쪽 정점 하나는 matching edge 하나에만 사용됩니다.

오른쪽 정점 `v ∈ R`도

```text
v -> t : 1
```

이므로 총유입 flow가 `1`을 넘을 수 없습니다.

따라서 오른쪽 정점도 matching edge 하나에만 사용됩니다.

### 왜 flow value가 matching 크기인가

모든 capacity가 정수이므로 정수 capacity network에서는 정수 max flow가 존재합니다.

따라서 `L -> R` 간선의 flow는 이 구성에서 `0` 또는 `1`로 볼 수 있습니다.

Flow가 `1`인 `L -> R` 간선은 matching에 포함된 pair 하나를 나타냅니다.

```text
f(u, v) = 1
-> (u, v)를 matching에 선택
```

Source에서 한 단위 flow가 나가 sink까지 도달할 때마다 matching pair 하나가 만들어지므로

```text
maximum flow value
=
maximum matching size
```

입니다.

### Matching 복원

최대 flow를 계산한 뒤 원본 bipartite edge에 대응하는 `L -> R` 간선을 검사합니다.

```text
if flow[u][v] == 1:
    (u, v)를 matching에 포함
```

Residual edge나 `source -> L`, `R -> sink` 간선을 matching pair로 해석하면 안 됩니다.

---

## 7. 정점 capacity

기본 flow network에서는 제한이 간선에 있습니다.

하지만 문제에서 다음처럼 정점 자체의 사용량을 제한할 수 있습니다.

```text
정점 v를 최대 3개 작업만 통과할 수 있음
```

이 경우 **vertex splitting**을 사용합니다.

정점 `v`를 두 정점으로 나눕니다.

```text
v_in
v_out
```

그리고

```text
v_in -> v_out : 정점 capacity
```

를 둡니다.

원래 `v`로 들어오던 간선은 `v_in`으로 연결하고, 원래 `v`에서 나가던 간선은 `v_out`에서 시작하게 합니다.

원본 간선

```text
u -> v
```

는 변환 후 보통

```text
u_out -> v_in
```

으로 연결합니다.

모든 flow가 `v`를 통과하려면 반드시

```text
v_in -> v_out
```

간선을 지나야 하므로 이 간선의 capacity가 정점 사용량을 제한합니다.

### Source와 sink 처리

Source와 sink도 나눌지는 문제 정의에 따라 다릅니다.

예를 들어 source 자체의 생성량이나 sink의 수용량에도 제한이 있다면 vertex splitting을 적용할 수 있습니다.

그렇지 않다면 source와 sink는 그대로 둘 수 있습니다.

### "무한 capacity" 표현

다른 제한에 걸리지 않도록 사실상 무한히 큰 capacity가 필요할 수 있습니다.

고정 폭 정수 구현에서는 실제 무한대를 큰 상수로 대체할 때 overflow와 상한을 주의해야 합니다.

문제 입력의 최대 가능한 total flow보다 큰 안전한 값을 계산하는 것이 좋습니다.

예를 들어 source에서 나가는 모든 유한 capacity의 합보다 큰 값은 해당 network에서 사실상 무한대로 사용할 수 있습니다.

---

## 8. 모델링 전에 확인할 질문

Flow 문제에서는 알고리즘 자체보다 모델링을 잘못하는 경우가 많습니다.

문제를 graph로 바꾸기 전에 다음을 확인합니다.

- 정점 하나를 여러 번 사용할 수 있습니까?
- 제한값은 간선에 있습니까, 정점에 있습니까?
- capacity의 단위는 사람 수, 대역폭, 작업 수 중 무엇입니까?
- source와 sink가 여러 개라면 super source·sink가 필요합니까?
- 최대량뿐 아니라 비용도 최소화해야 합니까?
- 시간에 따라 달라지는 값을 하나의 정적 network로 표현할 수 있습니까?
- 한 대상이 둘 이상의 역할을 동시에 맡을 수 있습니까?
- 원본의 선택 하나가 flow 한 단위와 정확히 대응합니까?

### Super source와 super sink

Source가 여러 개라면 새로운 super source `S`를 만들고 각 원래 source로 간선을 연결할 수 있습니다.

```text
S -> original_source_i
```

Sink가 여러 개라면 각 원래 sink에서 super sink `T`로 연결합니다.

```text
original_sink_i -> T
```

이때 새 간선의 capacity는 원래 각 source/sink의 공급·수용 제한을 반영해야 합니다.

단순히 무한 capacity를 넣어도 되는지는 문제 조건에 달려 있습니다.

### 최대 유량과 최소 비용은 다른 문제입니다

문제가

```text
가능한 양을 최대화
```

만 요구한다면 max flow로 충분할 수 있습니다.

하지만

```text
최대한 많이 보내면서 총 비용도 최소화
```

해야 한다면 일반 max flow만으로는 부족하고 min-cost max-flow 같은 별도 모델이 필요합니다.

### 대응표를 먼저 적습니다

문제를 flow로 바꾸기 전에 원래 대상과 새 network의 요소를 대응시키면 모델링 오류를 줄일 수 있습니다.

예:

| 원래 문제 | Flow network |
|---|---|
| 지원자 | 왼쪽 정점 |
| 작업 | 오른쪽 정점 |
| 지원 가능 관계 | `L -> R` capacity 1 |
| 지원자 1명당 최대 1개 작업 | `source -> L` capacity 1 |
| 작업 1개당 최대 1명 | `R -> sink` capacity 1 |

---

## 9. 입력과 반환값

Flow 구현은 입력 형식과 반환 형식을 명확히 해야 합니다.

### Capacity matrix를 사용하는 경우

다음 조건을 확인합니다.

- matrix가 정사각형입니까?
- `capacity[u][v]`가 모든 정점 쌍에 대해 정의됩니까?
- 모든 capacity가 음수가 아닙니까?
- capacity가 정수여야 합니까, 실수도 허용합니까?
- source와 sink index가 유효합니까?
- source와 sink가 같아도 됩니까?
- parallel edge는 입력 단계에서 합산합니까?

### Parallel edge

Capacity matrix는 `(u, v)` 쌍마다 값 하나만 저장합니다.

따라서 원본 입력에 parallel edge가 있으면 보통

```text
capacity[u][v] += edge_capacity
```

처럼 합산해야 합니다.

마지막 간선 값으로 덮어쓰면 전체 capacity를 잃을 수 있습니다.

Edge list 기반 구현이라면 parallel edge를 별도 간선으로 유지할 수도 있습니다.

### `source == sink`

Source와 sink가 같으면 일반적인 max-flow 정의에서 특별한 경우가 됩니다.

API가 이를 허용할지, `0`을 반환할지, 오류로 거부할지 미리 정해야 합니다.

숨겨진 암묵적 동작으로 두지 않습니다.

### 반환 형식

다음 중 무엇을 반환할지 정합니다.

```text
최대 flow value만 반환
(value, flow) 반환
(value, flow, min_cut) 반환
```

실제 `flow`를 반환한다면 그 matrix가 무엇을 뜻하는지 명확히 해야 합니다.

```text
원본 directed edge별 실제 flow matrix인가?
residual capacity matrix인가?
```

이 둘은 전혀 다른 상태입니다.

Residual matrix를 실제 flow라고 반환하면 capacity와 conservation 검증을 제대로 수행할 수 없습니다.

---

## 10. flow certificate 검증

`(value, flow)`를 반환한다고 가정하면 결과를 **certificate**처럼 검증할 수 있습니다.

값만 맞는지 보지 않고 실제 flow가 유효한지 검사합니다.

### 1. 크기 검사

`flow`가 capacity와 같은 크기의 정사각 matrix인지 확인합니다.

```text
len(flow) == V
각 row 길이 == V
```

### 2. Capacity constraint

원본 directed edge 기준으로 각 값이 다음을 만족해야 합니다.

```text
0 <= flow[u][v] <= capacity[u][v]
```

Capacity가 `0`인 방향에서는 실제 flow도 `0`이어야 합니다.

Antiparallel edge가 있더라도 각 방향을 독립적으로 검사합니다.

### 3. Flow conservation

중간 정점 `v`에 대해

```text
incoming(v)
=
Σ flow[u][v]

outgoing(v)
=
Σ flow[v][w]
```

를 계산하고

```text
incoming(v) == outgoing(v)
```

인지 확인합니다.

`v != s`, `v != t`인 모든 정점에서 성립해야 합니다.

### 4. Source의 순유출량

일반적으로

```text
source_net
=
Σ flow[s][v]
-
Σ flow[v][s]
```

를 계산합니다.

그리고

```text
source_net == value
```

여야 합니다.

### 5. Sink의 순유입량

```text
sink_net
=
Σ flow[u][t]
-
Σ flow[t][u]
```

를 계산하고

```text
sink_net == value
```

인지 확인합니다.

따라서

```text
source_net == sink_net == value
```

여야 합니다.

### 6. 최적성 검사

작은 graph에서는 모든 `s-t` cut을 열거해 minimum cut capacity를 계산합니다.

```text
value == minimum_cut_capacity
```

인지 확인합니다.

이 조건까지 만족하면 max-flow min-cut theorem에 의해 반환 flow의 값이 최적임을 독립적으로 검증할 수 있습니다.

---

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 11]`을 확인합니다.

구현에서 확인할 핵심은 다음과 같습니다.

- 입력 capacity matrix의 크기와 음수 값을 검사합니다.
- BFS로 residual graph의 augmenting path를 찾습니다.
- 역방향 residual을 사용하면 기존 반대 방향 flow를 먼저 취소합니다.
- 취소하고도 augment할 양이 남으면 원본 정방향 flow를 늘립니다.
- antiparallel 원본 간선이 있어도 각 방향의 실제 flow가 자신의 원본 capacity 안에 있도록 유지합니다.
- 테스트가 모든 source-side cut을 열거해 minimum cut 값을 독립적으로 계산합니다.
- 테스트가 최대 유량 값뿐 아니라 반환된 실제 flow certificate도 별도로 검사합니다.

특히 다음 세 상태를 혼동하지 않아야 합니다.

```text
capacity[u][v]
    원본에서 허용한 최대량

flow[u][v]
    현재 실제로 원본 방향으로 보내는 양

residual[u][v]
    현재 상태에서 u -> v로 추가 이동할 수 있는 양
```

Residual graph의 역방향 edge를 따라 이동했을 때는 "반대 방향 원본 flow를 새로 만든다"가 아니라 기존 flow를 취소한다는 의미를 유지해야 합니다.

---

## 완료 기준

- 원본 capacity, 현재 flow, residual capacity를 서로 다른 값으로 설명합니다.
- capacity constraint와 flow conservation을 식으로 설명합니다.
- source의 순유출량과 sink의 순유입량이 flow value와 같음을 설명합니다.
- 역방향 residual edge가 이전 flow를 취소하는 과정을 작은 network에서 추적합니다.
- augmenting path의 bottleneck capacity를 계산하고 그만큼 flow가 증가하는 이유를 설명합니다.
- Ford–Fulkerson이 augmenting-path 반복 틀이고 Edmonds–Karp가 BFS 선택 규칙을 추가한 알고리즘임을 설명합니다.
- maximum flow가 어떤 `s-t` cut capacity도 넘을 수 없는 이유를 설명합니다.
- augmenting path가 없을 때 residual reachability가 minimum cut을 만드는 이유를 설명합니다.
- 반환한 값뿐 아니라 capacity constraint와 conservation을 검사합니다.
- maximum matching network에서 source, `L`, `R`, sink 간선의 역할을 설명합니다.
- `L -> R` flow가 matching pair로 복원되는 이유를 설명합니다.
- 정점 capacity를 `v_in -> v_out` 간선으로 변환하는 이유를 설명합니다.
- 작은 graph의 모든 cut을 열거해 최대 유량 값을 독립적으로 확인합니다.

## 실패 신호

- 역방향 residual edge를 만들지 않습니다.
- residual capacity와 원본 capacity를 같은 의미의 배열로 사용합니다.
- 역방향 residual 사용을 반대 방향의 새 원본 flow로만 해석합니다.
- augmenting path가 없는지 원본 graph에서 검사합니다.
- 최대 유량 값만 검사하고 실제 flow의 capacity constraint를 확인하지 않습니다.
- 중간 정점의 flow conservation을 검사하지 않습니다.
- source/sink에 원본 역방향 간선이 있을 수 있는데도 단순 총유출·총유입만으로 flow value를 검증합니다.
- matching 변환에서 `source -> L` 또는 `R -> sink` capacity를 1보다 크게 두어 정점 사용 횟수 1을 강제하지 못합니다.
- matching 복원에서 residual edge를 원본 matching edge로 오해합니다.
- parallel edge를 capacity matrix에 넣으면서 마지막 값으로 덮어씁니다.
- antiparallel 간선에서 한 방향의 실제 flow가 자신의 원본 capacity를 넘습니다.
- 정점 capacity 문제에서 vertex splitting 없이 간선 capacity만 임의로 조정합니다.
