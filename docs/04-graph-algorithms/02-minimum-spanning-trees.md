# 최소 스패닝 트리

## 학습 목표

- shortest-path tree와 minimum spanning tree(MST)의 목적과 최적화 기준을 구분합니다.
- spanning tree, spanning forest, MST의 관계를 설명합니다.
- cut property와 cycle property가 어떤 조건에서 안전한 간선을 보장하는지 설명합니다.
- Kruskal과 Prim이 유지하는 상태와 불변식, 필요한 자료구조를 비교합니다.
- Kruskal에서 DSU가 cycle을 막는 과정을 설명합니다.
- 연결되지 않은 그래프, 같은 가중치, 여러 MST가 존재하는 입력의 반환 규칙을 정합니다.
- 작은 입력에서 MST 구현을 독립적인 기준 계산으로 검증하는 방법을 설명합니다.

## 선행지식

[Greedy의 교환 논리](../03-design-techniques/02-greedy-methods.md), [DSU](../02-data-structures/04-disjoint-sets-and-amortized-analysis.md), 그래프의 연결성과 cycle 개념을 이해해야 합니다.

이 문서에서는 다음 표기법을 사용합니다.

- `V`: 정점 수
- `E`: 간선 수
- `w(e)`: 간선 `e`의 가중치
- `T`: 현재 선택된 tree 또는 spanning tree
- `F`: 현재 선택된 forest

MST는 기본적으로 **connected, undirected, weighted graph**를 대상으로 합니다.

Directed graph에는 일반적인 MST 정의를 그대로 적용하지 않습니다. Directed graph에서 모든 정점을 연결하는 최소 비용 구조가 필요하다면 minimum arborescence 같은 별도 문제를 다뤄야 합니다.

---

## 핵심 관점

연결된 undirected weighted graph의 **spanning tree**는 원래 그래프의 모든 정점을 포함하는 부분 그래프 중 다음 조건을 만족하는 tree입니다.

```text
모든 정점을 포함합니다.
연결되어 있습니다.
cycle이 없습니다.
```

정점 수가 `V >= 1`인 tree는 위 조건으로부터 자동으로 간선 수가 `V-1`개입니다.

즉 다음 세 조건은 tree에서 서로 밀접하게 연결되어 있습니다.

```text
V개의 정점을 포함
연결됨
cycle 없음
```

이때 간선 수는 반드시 `V-1`입니다.

반대로 `V`개의 정점을 포함하는 undirected graph가

```text
간선 수 V-1
연결됨
```

을 만족하면 cycle이 없으므로 tree입니다.

MST(Minimum Spanning Tree)는 가능한 모든 spanning tree 중 **선택한 간선 가중치의 총합이 최소**인 tree입니다.

```text
cost(T) = Σ w(e)
          e in T
```

MST의 최적화 대상은 **전체 tree의 간선 가중치 합**입니다.

### MST와 shortest-path tree는 목적이 다릅니다

Shortest-path tree는 특정 시작점 `s`에서 각 정점까지의 경로 거리를 최소화하는 것이 목적입니다.

MST는 특정 시작점을 기준으로 하지 않습니다. 전체 tree의 가중치 합만 최소화합니다.

예를 들어 다음 그래프를 생각해 봅시다.

```text
A --2-- B
|      /
2     1
|   /
C --100-- B
```

간선을 명확히 적으면 다음과 같습니다.

```text
A-B: 2
A-C: 2
B-C: 1
```

`A`에서 시작하는 shortest-path tree에서는 다음 두 간선을 사용할 수 있습니다.

```text
A-B: 2
A-C: 2
```

그러면 `A`에서 `B`, `C`까지의 거리는 각각 `2`입니다.

하지만 MST는 다음 두 간선을 선택합니다.

```text
A-B: 2
B-C: 1
```

총가중치는 `3`입니다.

이 tree에서 `A -> C` 경로 거리는 `3`이므로 shortest-path tree의 거리 `2`보다 길지만, 전체 간선 가중치 합은 더 작습니다.

따라서 다음을 구분해야 합니다.

```text
shortest-path tree:
특정 시작점에서 각 정점까지의 경로 거리 최소화

MST:
전체 선택 간선의 총가중치 최소화
```

---

## 1. cut property

### cut이란 무엇인가

그래프의 정점 집합 `V`를 서로 겹치지 않는 두 집합 `S`, `V-S`로 나누는 것을 **cut**이라고 합니다.

```text
S | V-S
```

한 끝점은 `S`에 있고 다른 끝점은 `V-S`에 있는 간선을 **cut을 가로지르는 간선(crossing edge)** 이라고 합니다.

예를 들어 다음 cut을 생각해 봅시다.

```text
S = {A, B}
V-S = {C, D}
```

간선 `A-C`, `B-D`는 cut을 가로지릅니다.

간선 `A-B`는 두 끝점이 모두 `S`에 있으므로 cut을 가로지르지 않습니다.

### 안전한 간선

Greedy MST 알고리즘에서 **안전한 간선(safe edge)** 은 현재까지 선택한 간선 집합에 추가해도 어떤 MST로 확장할 수 있는 간선을 뜻합니다.

현재 forest `F`가 어떤 MST의 부분집합이라고 가정합니다.

이때 `F`의 어떤 간선도 가로지르지 않는 cut을 생각합니다. 이런 cut을 `F`를 **respect한다**고 표현합니다.

그 cut을 가로지르는 간선 중 가중치가 최소인 간선을 `e`라고 하면, `e`는 `F`에 대해 안전하게 선택할 수 있습니다.

여기서 최소 간선이 여러 개라면 그중 하나를 고를 수 있습니다. 특정 간선 하나가 모든 MST에 반드시 포함된다는 뜻은 아닙니다.

### 교환 논리

왜 cut의 최소 간선을 안전하게 선택할 수 있는지 보겠습니다.

현재 forest `F`를 포함하는 어떤 MST `T`가 있다고 가정합니다.

그리고 `F`를 respect하는 cut을 가로지르는 최소 가중치 간선 `e`를 고릅니다.

#### 경우 1: `e`가 이미 `T`에 있음

아무 문제 없습니다. `F + e`도 `T`의 부분집합입니다.

#### 경우 2: `e`가 `T`에 없음

`e`를 `T`에 추가하면 tree에 간선 하나가 추가되므로 정확히 하나의 cycle이 생깁니다.

```text
T + e
```

간선 `e`는 cut을 한쪽에서 다른 쪽으로 건넙니다.

Cycle은 출발점으로 다시 돌아와야 하므로 그 cycle 안에는 반드시 cut을 다시 건너는 다른 간선 `f`가 있습니다.

`e`가 cut을 가로지르는 최소 가중치 간선이므로

```text
w(e) <= w(f)
```

입니다.

이제 `f`를 제거합니다.

```text
T' = T + e - f
```

그러면 cycle은 사라지고 모든 정점은 여전히 연결되어 있으므로 `T'`도 spanning tree입니다.

또한

```text
cost(T') = cost(T) + w(e) - w(f)
         <= cost(T)
```

입니다.

`T`가 이미 MST였으므로 더 작은 비용의 spanning tree가 존재할 수 없습니다. 따라서 `T'` 역시 MST입니다.

그리고 `T'`는 `e`를 포함합니다.

즉 `e`를 선택한 뒤에도 현재 선택을 포함하는 MST가 적어도 하나 존재합니다.

이것이 cut property를 이용하는 핵심 교환 논리입니다.

---

## 2. Kruskal

Kruskal 알고리즘은 가중치가 작은 간선부터 확인하면서 cycle을 만들지 않는 간선을 선택합니다.

### 절차

1. 모든 간선을 가중치 오름차순으로 정렬합니다.
2. 현재 서로 다른 connected component를 잇는 간선만 선택합니다.
3. 선택한 두 component를 합칩니다.
4. 선택한 간선이 `V-1`개가 되면 MST가 완성됩니다.
5. 모든 간선을 확인했는데 `V-1`개를 선택하지 못했다면 원래 그래프는 연결되지 않았습니다.

결정적인 결과가 필요하다면 정렬 기준을 다음처럼 정할 수 있습니다.

```text
(weight, source, target)
```

다만 undirected edge를 `(u, v)`로 저장할 때는 `(min(u,v), max(u,v))`처럼 canonical form을 정하면 입력 방향 표현의 영향을 줄일 수 있습니다.

### Kruskal이 유지하는 상태

현재 선택된 간선 집합은 항상 **forest**입니다.

Forest는 여러 개의 tree component로 이루어진 cycle 없는 undirected graph입니다.

초기 상태는 간선이 하나도 없으므로 각 정점이 독립된 tree입니다.

```text
{0} {1} {2} {3}
```

간선 `(u, v)`를 볼 때 다음 두 경우를 구분합니다.

```text
u와 v가 서로 다른 component:
    간선을 추가해도 cycle이 생기지 않습니다.

u와 v가 같은 component:
    이미 u에서 v로 가는 경로가 있으므로
    간선을 추가하면 cycle이 생깁니다.
```

### DSU가 cycle을 막는 방법

DSU(Disjoint Set Union)는 각 정점이 현재 어느 component에 속하는지 관리합니다.

간선 `(u, v)`에 대해

```text
find(u) != find(v)
```

이면 두 정점은 서로 다른 component에 있습니다.

따라서 간선을 선택하고

```text
union(u, v)
```

를 수행합니다.

반대로

```text
find(u) == find(v)
```

이면 이미 같은 component이므로 간선을 추가했을 때 cycle이 생깁니다. 이 간선은 건너뜁니다.

예를 들어 다음 간선을 순서대로 본다고 합시다.

```text
(0,1)
(1,2)
(0,2)
```

초기:

```text
{0} {1} {2}
```

`(0,1)` 선택:

```text
{0,1} {2}
```

`(1,2)` 선택:

```text
{0,1,2}
```

이제 `(0,2)`를 보면

```text
find(0) == find(2)
```

입니다.

이미 `0 -> 1 -> 2` 경로가 있으므로 `(0,2)`를 추가하면 cycle이 생깁니다. 따라서 선택하지 않습니다.

### Kruskal의 불변식

Kruskal을 이해할 때 다음 두 내용을 유지한다고 보면 좋습니다.

```text
선택한 간선은 항상 forest입니다.
현재 forest를 포함하는 MST가 하나 이상 존재합니다.
```

두 번째 성질은 cut property로 설명할 수 있습니다.

현재 서로 다른 DSU component를 잇는 가장 가벼운 다음 간선을 `e`라고 합시다.

한 component의 정점 집합과 나머지 정점을 나누는 cut을 잡으면 현재 forest의 간선은 그 cut을 가로지르지 않습니다.

Kruskal이 정렬 순서상 선택한 `e`는 그 cut을 가로지르는 최소 가중치 간선 중 하나이므로 안전합니다.

### 복잡도

간선 정렬이 가장 큰 비용입니다.

```text
O(E log E)
```

DSU에 union by size 또는 union by rank와 path compression을 함께 사용하면 `E`번 수준의 `find/union` 연산 비용은

```text
O(E α(V))
```

정도로 볼 수 있습니다.

`α`는 inverse Ackermann function으로 실제 입력 크기에서 매우 천천히 증가합니다.

따라서 전체 시간 복잡도는 일반적으로

```text
O(E log E)
```

라고 씁니다.

Undirected simple graph에서는 `E <= V²`이므로 `log E = O(log V)`여서 흔히 `O(E log V)`와 같은 수준으로도 표현합니다.

---

## 3. Prim

Prim 알고리즘은 여러 component를 합치는 Kruskal과 달리 **하나의 tree를 계속 확장**합니다.

시작 정점 하나를 정한 뒤 현재 tree와 바깥 정점을 잇는 최소 가중치 간선을 반복해서 선택합니다.

### 기본 상태

```text
inside:
    현재 tree에 포함된 정점 집합

outside:
    아직 tree에 포함되지 않은 정점
```

초기에는 시작 정점 `s`만 포함합니다.

```text
inside = {s}
```

각 단계에서 다음 cut을 생각할 수 있습니다.

```text
inside | outside
```

이 cut을 가로지르는 최소 가중치 간선을 선택합니다.

Cut property에 의해 이 간선은 안전합니다.

간선의 outside 쪽 정점을 `inside`에 추가하면 tree가 한 정점 확장됩니다.

### heap을 사용하는 구현

인접 list와 priority queue를 사용한다면 개념적으로 다음과 같습니다.

```text
inside에 start를 추가합니다.
start에서 나가는 후보 간선을 heap에 넣습니다.

heap이 빌 때까지:
    최소 가중치 후보 간선을 꺼냅니다.

    새 정점이 이미 inside라면:
        오래된 후보이므로 버립니다.

    그렇지 않다면:
        간선을 MST에 추가합니다.
        새 정점을 inside에 추가합니다.
        새 정점에서 outside로 향하는 후보 간선을 heap에 추가합니다.
```

### Lazy heap

Priority queue에 들어간 항목은 나중에 더 이상 유효하지 않을 수 있습니다.

예를 들어 어떤 정점 `v`로 가는 후보가 여러 개 heap에 들어갔다고 합시다.

```text
(... -> v, weight 10)
(... -> v, weight 3)
```

가중치 `3`인 간선으로 `v`가 먼저 inside에 들어가면, 나중에 가중치 `10`인 항목은 더 이상 사용할 수 없습니다.

Lazy implementation에서는 heap 안에서 기존 항목을 즉시 삭제하려고 하지 않고, `pop`했을 때 목적 정점이 이미 inside인지 확인해 버립니다.

```text
if v in inside:
    continue
```

이 방식은 구현이 단순합니다.

### Prim의 불변식

Prim은 다음을 유지합니다.

```text
inside 정점들은 현재 하나의 tree로 연결되어 있습니다.
선택한 간선 집합을 포함하는 MST가 하나 이상 존재합니다.
```

각 단계에서 `inside | outside` cut의 최소 간선을 고르므로 cut property가 그대로 적용됩니다.

### 복잡도

인접 list와 binary heap을 사용하면 보통

```text
O(E log V)
```

로 구현할 수 있습니다.

Lazy heap에 간선을 직접 넣는 구현에서는 heap에 최대 `O(E)`개의 후보가 들어갈 수 있어 각 heap 연산을 엄밀히 `O(log E)`로 볼 수도 있습니다.

하지만 simple graph에서는 `E <= V²`이므로

```text
log E = O(log V)
```

이고 전체적으로 `O(E log V)`라고 표현하는 것이 일반적입니다.

### 배열 기반 Prim

매우 밀집된 그래프에서는 heap보다 배열을 사용하는 `O(V²)` Prim이 더 단순하고 실용적일 수 있습니다.

각 정점에 대해 현재 tree와 연결할 수 있는 최소 비용 `best[v]`를 유지합니다.

매 단계에서 아직 선택되지 않은 정점 중 `best[v]`가 가장 작은 정점을 선형 검색합니다.

```text
V번 반복
각 반복에서 O(V) 검색
```

따라서 총 시간은

```text
O(V²)
```

입니다.

인접 matrix와 함께 사용하면 구현이 자연스럽습니다.

---

## 4. Kruskal과 Prim 비교

두 알고리즘은 모두 greedy algorithm이며 cut property를 이용하지만 상태 표현이 다릅니다.

| 항목 | Kruskal | Prim |
|---|---|---|
| 성장 방식 | 여러 tree로 이루어진 forest를 합침 | 하나의 tree를 확장 |
| 핵심 후보 | 전체 간선 중 다음 최소 간선 | inside-outside cut의 최소 간선 |
| cycle 방지 | DSU | outside 정점만 추가 |
| 자연스러운 입력 표현 | edge list | adjacency list / matrix |
| 대표 자료구조 | 정렬 + DSU | priority queue 또는 배열 |
| 대표 복잡도 | `O(E log E)` | heap: `O(E log V)`, 배열: `O(V²)` |

### 어떤 알고리즘을 선택할까

다음은 구현 관점의 일반적인 선택 기준입니다.

- edge list가 이미 있고 희소 그래프라면 Kruskal이 단순합니다.
- 한 정점의 인접 간선을 빠르게 얻을 수 있다면 Prim이 자연스럽습니다.
- 매우 밀집된 그래프라면 adjacency matrix와 `O(V²)` Prim을 검토합니다.
- 여러 정점 쌍이 이미 하나의 component로 연결된 상태에서 추가 연결 비용을 최소화하는 offline 문제라면 Kruskal 전에 DSU `union`을 수행하는 방식이 자연스러울 수 있습니다.

다만 마지막 경우에는 기존 연결의 비용이 이미 지불된 것인지, 반드시 유지해야 하는 연결인지 등 문제 정의를 먼저 명확히 해야 합니다.

---

## 5. 같은 가중치와 결과의 유일성

### 모든 가중치가 서로 다르면 MST는 유일합니다

모든 간선 가중치가 서로 다르면 각 cut에서 최소 가중치 간선이 하나뿐이므로 MST가 유일합니다.

이는 충분조건입니다.

### 같은 가중치가 있다고 해서 반드시 여러 MST인 것은 아닙니다

같은 가중치의 간선이 존재하면 여러 MST가 **가능할 수 있지만**, 반드시 여러 개가 존재하는 것은 아닙니다.

예를 들어 같은 가중치 간선이 있어도 graph 구조상 특정 간선을 선택할 수밖에 없다면 MST는 여전히 유일할 수 있습니다.

따라서 정확한 표현은 다음과 같습니다.

```text
모든 간선 가중치가 서로 다르면 MST는 유일합니다.

같은 가중치가 있으면 MST가 여러 개일 수 있습니다.
하지만 반드시 여러 개인 것은 아닙니다.
```

### 반환 계약을 정합니다

MST API가 무엇을 반환해야 하는지 먼저 결정합니다.

예를 들어 다음 중 하나일 수 있습니다.

```text
최소 총가중치만 반환
간선 목록만 반환
(간선 목록, 총가중치) 반환
```

여러 MST가 가능할 때 특정 간선 목록이 필요하다면 tie-break 규칙을 정합니다.

예:

```text
(weight, min(u,v), max(u,v))
```

이렇게 하면 같은 입력에서 항상 같은 결과를 만들 수 있습니다.

다만 tie-break로 선택된 tree는 "유일한 MST"가 아니라 **여러 MST 중 구현이 선택한 하나**일 수 있습니다.

### 테스트에서 무엇을 검사해야 하는가

같은 가중치가 있을 수 있는 입력에서는 한 가지 간선 목록만 정답이라고 가정하면 안 됩니다.

대신 반환 결과가 다음 조건을 만족하는지 검사합니다.

- 간선 수가 `V-1`개입니다.
- 반환한 각 간선이 원본 그래프에 존재합니다.
- 모든 정점이 연결되어 있습니다.
- cycle이 없습니다.
- 반환한 총가중치가 실제 간선 목록의 합과 같습니다.
- 총가중치가 최적값과 같습니다.

연결성과 간선 수 `V-1`을 이미 확인했다면 undirected graph에서 cycle 없음은 자동으로 따라옵니다. 하지만 검증 코드를 읽기 쉽게 만들기 위해 명시적으로 cycle 여부를 검사할 수도 있습니다.

---

## 6. 연결되지 않은 그래프

연결되지 않은 undirected graph에는 모든 정점을 포함하는 spanning tree가 존재하지 않습니다.

예:

```text
0 -- 1

2 -- 3
```

두 component 사이에 간선이 없으므로 네 정점을 하나의 tree로 연결할 수 없습니다.

따라서 일반적인 MST는 존재하지 않습니다.

함수의 반환 방식을 미리 정해야 합니다.

### 선택지 1: 오류로 거부

```text
ValueError
```

같은 오류를 반환합니다.

이 방식은 함수가 "connected graph의 MST를 계산한다"는 계약을 가질 때 자연스럽습니다.

### 선택지 2: minimum spanning forest 반환

각 connected component별 MST를 반환합니다.

위 예에서는 다음 두 tree가 forest를 이룹니다.

```text
{0,1}
{2,3}
```

이를 **minimum spanning forest**라고 부릅니다.

### 선택지 3: 연결 여부를 함께 반환

예:

```text
{
    connected: false,
    edges: [...],
    total_weight: ...
}
```

어떤 방식을 택하든 연결 그래프라는 전조건이나 실패 조건을 숨기지 않고 API 계약에 명시합니다.

### Kruskal에서 연결 실패를 감지하는 방법

정점 수가 `V > 0`일 때 connected graph의 spanning tree는 반드시 `V-1`개의 간선을 가져야 합니다.

따라서 모든 간선을 검사한 뒤

```text
selected_edges < V - 1
```

이면 graph가 연결되지 않은 것입니다.

`V = 0` 또는 `V = 1`을 허용하는 API라면 그 경우의 반환 규칙도 별도로 정해야 합니다.

---

## 7. cycle property

Cycle property는 cut property와 반대 방향에서 MST 간선을 판단하는 데 도움을 줍니다.

어떤 cycle에서 **유일하게 가장 무거운 간선** `e`가 있다고 합시다.

그러면 `e`는 어떤 MST에도 포함될 수 없습니다.

### 이유

`e`를 포함하는 spanning tree `T`가 있다고 가정합니다.

원래 graph의 cycle에서 `e`를 제외한 나머지 간선들은 `e`의 양 끝점을 다른 경로로 연결합니다.

따라서 `T`에서 `e`를 제거하면 tree가 두 component로 나뉘고, cycle의 나머지 간선 중 하나 `f`를 추가해 다시 연결할 수 있습니다.

`e`가 cycle에서 유일하게 가장 무거우므로

```text
w(f) < w(e)
```

입니다.

따라서

```text
T' = T - e + f
```

의 총가중치는 `T`보다 작습니다.

그러므로 `e`를 포함하는 `T`는 MST일 수 없습니다.

### 가장 무거운 간선이 여러 개라면

다음처럼 cycle의 최대 가중치가 동률일 수 있습니다.

```text
A-B: 5
B-C: 5
C-A: 3
```

가중치 `5`인 간선 하나를 반드시 제외해야 tree가 되지만, `A-B`와 `B-C` 중 특정 하나가 모든 MST에서 반드시 제외된다고 단정할 수는 없습니다.

따라서 cycle property는 다음처럼 정확히 표현해야 합니다.

```text
cycle에서 유일하게 가장 무거운 간선은
어떤 MST에도 포함될 수 없습니다.
```

"cycle의 가장 무거운 간선은 항상 제외된다"라고 단순화하면 동률 상황에서 잘못된 설명이 됩니다.

---

## 8. cut property와 cycle property의 관계

두 성질은 MST에서 간선을 선택하거나 제거할 때 서로 보완적으로 사용할 수 있습니다.

### cut property

```text
특정 cut을 가로지르는 최소 가중치 간선
-> 안전하게 포함할 수 있음
```

### cycle property

```text
특정 cycle에서 유일하게 가장 무거운 간선
-> MST에 포함될 수 없음
```

Kruskal은 주로 cut property로 "선택해도 되는 간선"을 설명할 수 있고, cycle 검사로 잘못된 추가를 막습니다.

Cycle property는 특정 간선이 MST에 들어갈 수 없는 이유를 설명하거나 문제를 역방향으로 분석할 때 유용합니다.

---

## 9. 독립적인 기준 계산

MST 구현을 테스트할 때 같은 아이디어를 다시 구현한 코드와만 비교하면 공통 결함을 놓칠 수 있습니다.

예를 들어 Kruskal 구현과 기준 구현이 모두 같은 DSU 코드를 공유한다면 DSU에 동일한 버그가 있을 때 두 결과가 똑같이 잘못될 수 있습니다.

따라서 작은 graph에서는 더 느리지만 구조적으로 다른 기준 계산을 사용할 수 있습니다.

### 모든 `V-1`개 간선 조합 검사

작은 그래프에서는 다음 방식으로 exact answer를 구할 수 있습니다.

1. 전체 `E`개 간선에서 `V-1`개를 고르는 모든 조합을 생성합니다.
2. 각 조합이 모든 정점을 연결하는지 확인합니다.
3. cycle이 없는지 확인합니다.
4. 유효한 spanning tree라면 간선 가중치 합을 계산합니다.
5. 가능한 모든 spanning tree의 가중치 중 최솟값을 구합니다.

조합 수는

```text
C(E, V-1)
```

이므로 큰 입력에는 사용할 수 없습니다.

하지만 작은 무작위 graph를 검증하는 oracle로는 유용합니다.

### 검증 구현은 다른 메커니즘을 사용합니다

Kruskal을 검증하면서 기준 계산도 같은 DSU를 사용하면 공통 결함을 놓칠 수 있습니다.

대신 작은 기준 계산에서는 다음처럼 다른 방법을 사용합니다.

- BFS/DFS로 연결성 검사
- 단순 parent 배열로 cycle 검사
- 간선 수 `V-1`과 연결성만으로 tree 여부 판정

예를 들어 `V-1`개의 간선을 골랐고 모든 정점이 연결되어 있다면 undirected graph에서는 자동으로 tree입니다.

따라서 작은 oracle에서는

```text
간선 수 == V-1
AND
모든 정점이 연결됨
```

만 확인해도 충분합니다.

---

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 9]`를 확인합니다.

구현에서 확인할 핵심은 다음과 같습니다.

- `_DisjointSet`이 component 대표와 size를 관리합니다.
- `kruskal_mst`가 `union`에 성공한 간선만 선택합니다.
- 간선을 `(weight, source, target)` 순서로 정렬해 결과를 결정적으로 만듭니다.
- 연결되지 않은 입력은 `ValueError`로 거부합니다.
- 테스트가 모든 spanning tree 조합의 최소 가중치와 비교하고 반환 간선 목록을 따로 검사합니다.

`union`이 성공했다는 것은 두 끝점이 서로 다른 component에 있었다는 뜻입니다.

따라서 선택 직전에는 두 끝점 사이에 기존 경로가 없었고, 간선을 추가해도 cycle이 생기지 않습니다.

반대로 `union`이 실패했다면 두 끝점은 이미 같은 component에 있으므로 그 간선을 추가하면 cycle이 생깁니다.

테스트에서 brute-force 기준 계산과 비교할 때는 Kruskal과 동일한 DSU 구현을 재사용하지 않는 것이 중요합니다. 구현과 oracle이 같은 결함을 공유하면 테스트가 통과하면서도 둘 다 잘못될 수 있기 때문입니다.

---

## 완료 기준

- spanning tree와 MST의 정의를 구분해 설명합니다.
- shortest-path tree와 MST가 서로 다른 tree를 선택하는 예를 설명합니다.
- MST가 기본적으로 connected undirected weighted graph에 대한 문제임을 설명합니다.
- cut을 가로지르는 최소 간선이 안전한 이유를 교환 과정으로 적습니다.
- cut property에서 현재 forest를 respect하는 cut의 의미를 설명합니다.
- DSU가 Kruskal의 선택 간선에서 cycle을 막는 과정을 추적합니다.
- Kruskal과 Prim이 각각 forest를 합치는 방식과 하나의 tree를 확장하는 방식이라는 차이를 설명합니다.
- Prim의 lazy heap에서 오래된 후보 간선을 왜 버리는지 설명합니다.
- 같은 가중치가 있을 때 MST가 여러 개일 수 있지만 반드시 그런 것은 아님을 설명합니다.
- 같은 가중치가 있을 때 특정 edge set 대신 tree 조건과 총가중치를 검사합니다.
- 연결되지 않은 입력의 반환 방식을 명확히 정합니다.
- cycle property에서 "유일하게 가장 무거운 간선"이라는 조건이 필요한 이유를 설명합니다.
- 작은 graph에서 brute-force spanning tree 검사를 독립적인 oracle로 사용할 수 있음을 설명합니다.

## 실패 신호

- Directed graph에 일반 MST를 그대로 적용합니다.
- spanning tree와 shortest-path tree를 같은 개념으로 생각합니다.
- MST가 특정 시작점에서 모든 최단 경로를 보장한다고 생각합니다.
- 가장 가벼운 간선을 cycle 여부나 component 상태와 상관없이 선택합니다.
- Kruskal에서 `find(u) == find(v)`인 간선도 선택합니다.
- Prim에서 이미 inside에 들어간 정점으로 향하는 오래된 heap 항목을 다시 선택합니다.
- 같은 가중치가 있으면 반드시 MST가 여러 개라고 단정합니다.
- 같은 가중치가 있을 때 한 가지 간선 목록만 정답이라고 가정합니다.
- 연결되지 않은 그래프의 처리 방법이 없습니다.
- cycle property에서 최대 가중치가 동률인데 특정 간선이 반드시 제외된다고 단정합니다.
- 기준 계산도 Kruskal과 동일한 DSU 구현을 사용해 공통 결함을 놓칩니다.
