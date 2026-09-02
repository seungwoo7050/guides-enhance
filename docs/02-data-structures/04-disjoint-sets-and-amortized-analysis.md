# 서로소 집합과 상각 분석

## 학습 목표

- DSU가 각 원소의 대표(representative)와 component 정보를 어떻게 저장하는지 설명합니다.
- union by size·rank와 path compression이 각각 무엇을 제한하거나 단축하는지 구분합니다.
- aggregate, accounting, potential 방법으로 여러 연산의 총비용을 분석합니다.
- 한 번의 연산에서 발생할 수 있는 최악 비용과 연산열 전체에 대한 상각 비용을 구분합니다.

## 선행지식

[Tree](03-trees-and-balanced-search-trees.md), 점근 비용, 여러 연산의 총비용을 구분할 수 있어야 합니다.

특히 다음 차이를 이해해야 합니다.

```text
최악 시간 복잡도:
한 번의 연산이 가장 나쁜 상황에서 얼마나 비쌀 수 있는가?

상각 시간 복잡도:
어떤 허용된 연산 순서에서도 여러 연산의 총비용을
연산 수에 나누었을 때 얼마로 제한되는가?
```

상각 분석은 확률적 평균과 다릅니다.

## 핵심 관점

상각 분석(amortized analysis)은 입력이 특정 확률 분포를 따른다고 가정하지 않습니다.

핵심은 다음과 같습니다.

> 비싼 연산이 가끔 발생하더라도, 그런 연산이 자주 발생할 수 없음을 이용해 연산열 전체의 비용을 제한합니다.

potential 방법에서는 보통 다음 관계를 사용합니다.

```text
상각 비용
= 실제 비용 + Φ(새 상태) - Φ(이전 상태)
```

이를 여러 연산에 대해 더하면:

```text
전체 상각 비용
= 전체 실제 비용 + Φ(최종 상태) - Φ(초기 상태)
```

따라서 `Φ(초기 상태) = 0`이고 모든 상태에서 `Φ >= 0`이라면:

```text
전체 실제 비용 <= 전체 상각 비용
```

이 됩니다.

---

## 1. DSU

DSU(disjoint-set union), 또는 union-find는 원소들을 서로 겹치지 않는 여러 집합으로 나누어 관리합니다.

대표적인 연산은 다음과 같습니다.

```text
make_set(x):
    x만 포함한 새 집합을 만듭니다.

find(x):
    x가 속한 집합의 대표를 반환합니다.

union(a, b):
    a가 속한 집합과 b가 속한 집합을 하나로 합칩니다.
```

### 대표는 무엇인가

DSU의 대표는 component를 식별하기 위해 선택된 원소입니다.

두 원소가 같은 component에 속하는지는 다음으로 판정할 수 있습니다.

```text
find(a) == find(b)
```

대표가 반드시 다음 의미를 가지는 것은 아닙니다.

```text
가장 작은 값
가장 먼저 삽입된 값
가장 중요한 값
```

union 전략에 따라 root가 바뀔 수 있으므로, 별도 규칙이 없다면 대표는 단순한 **component 식별자**로만 해석합니다.

### parent forest

보통 배열 또는 map 형태의 `parent`를 사용해 여러 rooted tree의 forest를 표현합니다.

초기 상태:

```text
parent[x] = x
```

root는 다음 조건을 만족합니다.

```text
parent[root] == root
```

예:

```text
원소:   0  1  2  3  4
parent: 0  0  0  3  3
```

이는 개념적으로 다음 두 component를 나타낼 수 있습니다.

```text
0 component: {0, 1, 2}
3 component: {3, 4}
```

`find(x)`는 parent를 따라 올라가 root를 찾습니다.

DSU가 관리하는 중요한 불변식은 다음과 같습니다.

```text
각 원소는 정확히 하나의 component에 속합니다.
같은 component의 모든 원소는 같은 root에 도달합니다.
root는 parent[root] == root를 만족합니다.
```

---

## 2. union by size 또는 rank

단순히 아무 root나 다른 root 아래에 붙이면 tree가 길게 늘어질 수 있습니다.

예를 들어 계속 오른쪽 root 아래에 붙이면:

```text
0 -> 1 -> 2 -> 3 -> 4
```

처럼 높이가 `O(n)`까지 커질 수 있습니다.

그러면 `find`도 root까지 `O(n)`개의 parent를 따라가야 할 수 있습니다.

이를 막기 위해 보통 다음 전략 중 하나를 사용합니다.

```text
union by size
union by rank
```

### union by size

각 root에 해당 component의 원소 수를 저장합니다.

불변식:

```text
size[root]
= root가 대표하는 component의 원소 수
```

두 component를 합칠 때:

```text
ra = find(a)
rb = find(b)

ra == rb라면 아무것도 하지 않습니다.

그렇지 않다면 작은 component의 root를
큰 component의 root 아래에 붙입니다.
```

예:

```text
size[ra] = 3
size[rb] = 7
```

이면:

```text
parent[ra] = rb
size[rb] = 10
```

으로 만들 수 있습니다.

이때 `ra`는 더 이상 root가 아니므로 이후 component 크기는 `size[rb]`를 기준으로 봅니다.

### 왜 깊이가 `O(log n)`인가

union by size만 사용하고 path compression은 사용하지 않는다고 하겠습니다.

어떤 node `x`의 깊이가 1 증가하려면, `x`가 속한 tree의 root가 다른 더 큰 tree 아래에 붙어야 합니다.

작은 tree를 큰 tree 아래에 붙이므로 합치기 전:

```text
size(x가 속한 component)
<= size(다른 component)
```

입니다.

합친 뒤 `x`가 속한 component의 크기는 최소 두 배가 됩니다.

```text
s -> 최소 2s
```

node 하나의 깊이가 `d`번 증가했다면 그 component 크기는 최소:

```text
1, 2, 4, 8, ..., 2^d
```

처럼 증가해야 합니다.

전체 원소 수가 `n`이므로:

```text
2^d <= n
```

이고 따라서:

```text
d <= log2 n
```

입니다.

즉 union by size만으로도 tree 높이를 `O(log n)`으로 제한할 수 있습니다.

### union by rank

rank는 구현에 따라 "tree 높이에 대한 상한" 또는 구조적 등급을 의미합니다.

일반적으로:

```text
rank가 작은 root를 큰 rank root 아래에 붙입니다.
rank가 같을 때만 새 root의 rank를 1 증가시킵니다.
```

중요한 점은 path compression을 사용한 뒤에는 rank가 실제 tree 높이와 정확히 같다고 생각하면 안 된다는 것입니다.

rank는 union 결정을 위한 보조 정보로 사용되며, path compression 뒤 실제 높이를 그대로 나타내는 값이 아닐 수 있습니다.

### 이미 같은 component인 경우

반드시 먼저 확인합니다.

```text
ra = find(a)
rb = find(b)

if ra == rb:
    return false
```

이미 같은 component인데도 size를 더하면:

```text
size[root] += size[root]
```

처럼 잘못된 component 크기가 만들어질 수 있습니다.

따라서 `union`의 성공 여부를 반환하는 API도 자주 사용합니다.

```text
true:
실제로 두 component가 합쳐짐

false:
이미 같은 component였음
```

---

## 3. path compression

path compression은 `find(x)` 중 root까지 방문한 node들을 root에 직접 연결하는 최적화입니다.

재귀 형태는 다음과 같습니다.

```text
find(x):
    if parent[x] != x:
        parent[x] = find(parent[x])
    return parent[x]
```

예를 들어 처음 parent 관계가 다음과 같다고 하겠습니다.

```text
x -> a -> b -> root
```

`find(x)` 후에는 다음처럼 압축될 수 있습니다.

```text
x ----a -----+-> root
b ----/
```

다음 `find(x)`는 훨씬 짧은 경로로 root에 도달합니다.

### path compression의 역할

union by size·rank와 path compression은 역할이 다릅니다.

```text
union by size/rank:
union 시 tree가 너무 깊어지는 것을 막습니다.

path compression:
find가 지나간 기존 경로를 짧게 만듭니다.
```

두 기법을 함께 사용하면 매우 강한 상각 시간 경계를 얻습니다.

### `O(m α(n))`

union by rank 또는 size와 path compression을 함께 사용한 DSU에서, `n`개 원소에 대해 `m`개의 `make_set`, `find`, `union` 계열 연산을 수행하면 전체 비용은 일반적으로 다음과 같이 알려져 있습니다.

```text
O(m α(n))
```

여기서 `α(n)`은 inverse Ackermann function입니다.

이 함수는 현실적인 크기의 `n`에서 매우 작게 증가합니다. 그래서 실무에서는 거의 상수처럼 보입니다.

그러나 이론적으로 다음처럼 표현하는 것이 정확합니다.

```text
상각 O(α(n))
```

다음처럼 표현하면 부정확합니다.

```text
항상 O(1)
최악 O(1)
```

특히 개별 `find` 한 번의 비용은 tree 상태에 따라 상수보다 클 수 있습니다.

### size와 rank의 의미

path compression 이후에는 중간 node들이 root에 직접 연결됩니다.

따라서 `size`를 다음처럼 관리한다면:

```text
size[root] = component의 실제 크기
```

root의 값만 의미가 있습니다.

예를 들어:

```text
size[non_root]
```

가 배열에 남아 있더라도 최신 component 크기를 나타낸다고 가정하면 안 됩니다.

rank도 마찬가지로 path compression 뒤 실제 높이와 일치한다고 가정하지 않습니다.

---

## 4. aggregate 방법

aggregate method는 연산열 전체의 실제 비용을 직접 계산한 뒤 연산 수로 나눕니다.

예를 들어 동적 배열이 가득 찰 때 capacity를 두 배로 늘린다고 하겠습니다.

초기 capacity를 `1`로 두면 resize 때 기존 원소를 복사하는 수는 대략 다음과 같습니다.

```text
1 + 2 + 4 + 8 + ...
```

`n`번 append할 때 마지막 resize 크기가 `n`보다 작거나 비슷하므로:

```text
1 + 2 + 4 + ... < 2n
```

입니다.

새 원소를 실제로 넣는 비용도 `n`번이므로 전체 비용은:

```text
O(n)
```

입니다.

따라서 `n`번 append의 평균 상각 비용은:

```text
O(n) / n = O(1)
```

입니다.

### 무엇을 증명한 것인가

여기서 증명한 것은:

```text
각 append가 최악 O(1)
```

이 아닙니다.

resize가 발생한 한 번의 append는 여전히 `O(n)`일 수 있습니다.

증명한 것은:

```text
어떤 n번의 append 연산열 전체 비용이 O(n)
```

이라는 사실입니다.

즉:

```text
append의 상각 비용 O(1)
```

입니다.

---

## 5. accounting 방법

accounting method에서는 각 연산에 실제 비용과 다른 **상각 비용(amortized charge)**을 부과합니다.

싼 연산에 실제 비용보다 더 많이 청구하여 credit을 저장하고, 이후 비싼 연산이 생기면 그 credit을 사용합니다.

개념적으로:

```text
실제 비용 1
상각 비용 3

남는 2를 credit으로 저장
```

나중에 resize에서 복사 비용이 발생하면 이전에 저장한 credit으로 지불합니다.

### 증명 조건

accounting 방법에서는 다음이 중요합니다.

```text
누적 credit이 어느 시점에도 음수가 되지 않아야 합니다.
```

왜냐하면 미래에 생길 credit을 미리 빌려 현재 실제 비용을 지불하는 방식이 되면 전체 비용의 상한 증명이 깨질 수 있기 때문입니다.

즉 모든 prefix 연산열에 대해:

```text
누적 상각 비용 >= 누적 실제 비용
```

이 유지되어야 합니다.

### 동적 배열 예

capacity가 두 배로 늘어나는 배열에서 append마다 일정한 추가 비용을 미리 청구합니다.

예를 들어 실제 삽입 비용 외에 몇 단위의 credit을 더 저장해 두고, 다음 resize가 발생했을 때 기존 원소를 옮기는 데 사용합니다.

정확한 상수는 비용 모델에 따라 달라질 수 있지만 핵심은 다음입니다.

```text
resize를 위해 필요한 전체 복사 비용을
그 전에 수행된 싼 append들이 미리 나누어 부담합니다.
```

따라서 개별 비싼 연산이 있더라도 전체 상각 비용은 일정하게 제한됩니다.

---

## 6. potential 방법

potential method는 자료구조의 현재 상태에 저장된 "미래 작업을 지불할 수 있는 에너지"를 수학적 함수로 표현합니다.

자료구조 상태를 `D`라고 할 때 potential을:

```text
Φ(D)
```

로 정의합니다.

보통 다음 조건을 사용합니다.

```text
Φ(D) >= 0
```

각 연산의 상각 비용은:

```text
상각 비용
= 실제 비용 + Φ(새 상태) - Φ(이전 상태)
```

입니다.

### 여러 연산을 더하면

상태가 다음처럼 변한다고 하겠습니다.

```text
D0 -> D1 -> D2 -> ... -> Dm
```

각 연산의 potential 변화는:

```text
Φ(D1) - Φ(D0)
Φ(D2) - Φ(D1)
...
Φ(Dm) - Φ(Dm-1)
```

입니다.

모두 더하면 중간 항이 상쇄되어:

```text
Φ(Dm) - Φ(D0)
```

만 남습니다.

따라서:

```text
전체 상각 비용
= 전체 실제 비용 + Φ(Dm) - Φ(D0)
```

입니다.

정리하면:

```text
전체 실제 비용
= 전체 상각 비용 - Φ(Dm) + Φ(D0)
```

입니다.

만약:

```text
Φ(D0) = 0
Φ(Dm) >= 0
```

이라면:

```text
전체 실제 비용 <= 전체 상각 비용
```

이 됩니다.

### potential 선택의 의미

좋은 potential은 현재 자료구조에 얼마나 많은 "미래의 비싼 작업"이 쌓여 있는지를 표현합니다.

potential이 지나치게 크거나 실제 구조와 무관하면 각 연산의 상각 비용을 유용하게 제한하기 어렵습니다.

따라서 potential 함수는 임의로 정하는 값이 아니라, 비싼 연산이 발생할 수 있는 상태를 수치화하도록 선택합니다.

---

## 7. stack의 `multipop`

다음 stack 연산을 생각합니다.

```text
push(x)
pop()
multipop(k):
    최대 k개를 제거
```

stack 크기가 `n`이면 한 번의:

```text
multipop(n)
```

은 `O(n)`일 수 있습니다.

그러나 여러 연산의 총비용은 다르게 분석할 수 있습니다.

### aggregate 분석

원소 하나를 기준으로 봅니다.

각 원소는:

```text
push로 최대 한 번 들어감
pop 또는 multipop으로 최대 한 번 제거됨
```

이미 제거된 원소가 다시 제거되는 일은 없습니다.

따라서 `m`개의 연산 동안 실제 push와 실제 제거의 총 횟수는 `O(m)`입니다.

즉 전체 비용:

```text
O(m)
```

이고 연산당 상각 비용:

```text
O(1)
```

입니다.

### 중요한 해석

이 결과는:

```text
multipop 한 번이 항상 O(1)
```

이라는 뜻이 아닙니다.

정확한 의미는:

```text
연산열 전체에서 원소 하나가 여러 번 제거될 수 없으므로
비싼 multipop이 반복해서 큰 비용을 낼 수 없다.
```

입니다.

### monotonic stack·deque와의 연결

monotonic stack이나 deque에서도 내부 `while`이 한 호출에서 여러 번 실행될 수 있습니다.

예:

```text
while stack and stack[-1] < current:
    stack.pop()
```

한 원소가 stack에:

```text
최대 한 번 들어가고
최대 한 번 제거된다면
```

전체 push·pop 횟수는 `O(n)`입니다.

따라서 내부에 반복문이 중첩되어 보인다는 이유만으로 바로 `O(n^2)`이라고 결론 내리면 안 됩니다.

---

## 8. DSU가 적합하지 않은 문제

기본 DSU는 **component를 합치는 연산에는 강하지만, 이미 합친 component를 다시 분리하는 연산에는 적합하지 않습니다.**

### 간선 삭제

DSU는 다음 정보를 주로 저장합니다.

```text
이 두 원소가 같은 component인가?
```

하지만 연결을 만든 실제 간선 구조를 충분히 저장하지 않습니다.

간선 하나를 삭제했을 때 component가 둘로 갈라지는지 확인하려면 추가적인 정보가 필요합니다.

따라서 온라인으로 간선 삽입·삭제가 반복되는 일반 dynamic connectivity 문제를 기본 DSU만으로 직접 처리하기 어렵습니다.

### 시간에 따른 연결 상태

다음 같은 문제에서는 다른 기법이 필요할 수 있습니다.

```text
시간 t에 간선 추가
시간 t에 간선 삭제
각 시점마다 u와 v가 연결되어 있는지 질의
```

상황에 따라 다음을 검토합니다.

- offline reverse processing
- rollback DSU
- segment tree over time + rollback DSU
- dynamic connectivity용 다른 자료구조

### 실제 경로나 거리

DSU가 알려주는 기본 정보는:

```text
같은 component인가?
```

입니다.

다음 질문에 직접 답하는 구조는 아닙니다.

```text
u에서 v까지 실제 경로는 무엇인가?
거리 합은 얼마인가?
경로 위 최댓값은 무엇인가?
```

이런 정보가 필요하면 graph traversal, tree 자료구조, LCA, weighted DSU 같은 별도 구조가 필요할 수 있습니다.

### 대표에 특별한 의미가 필요한 경우

기본 DSU에서는 union 전략에 따라 대표가 바뀔 수 있습니다.

따라서 대표가 반드시:

```text
최솟값
가장 오래된 원소
특정 우선순위의 원소
```

여야 한다면 그 조건을 별도 metadata로 관리하거나 union 규칙에 반영해야 합니다.

---

## 9. Kruskal과 DSU

Kruskal 알고리즘은 가중치가 작은 간선부터 검사하면서 cycle을 만들지 않는 간선을 선택합니다.

간선을:

```text
(weight, u, v)
```

순서로 정렬했다고 하겠습니다.

각 간선 `(u, v)`에 대해:

```text
find(u) != find(v)
```

이면 두 정점은 현재 선택된 간선들로 아직 연결되어 있지 않습니다.

따라서 이 간선을 추가해도 cycle이 생기지 않습니다.

```text
간선 선택
union(u, v)
```

반대로:

```text
find(u) == find(v)
```

이면 이미 선택된 간선들을 통해 `u`와 `v` 사이에 경로가 있습니다.

여기에 `(u, v)`를 추가하면 cycle이 만들어지므로 건너뜁니다.

### DSU가 유지하는 의미

Kruskal 실행 중 DSU의 component는:

```text
지금까지 선택한 간선으로 서로 연결된 정점 집합
```

을 나타냅니다.

즉 다음 불변식이 중요합니다.

```text
find(u) == find(v)
<=> 현재 선택된 간선들만 사용해 u와 v가 연결되어 있음
```

### 선택 간선 수

연결된 그래프에서 spanning tree는 정점이 `V`개일 때 정확히:

```text
V - 1
```

개의 간선을 가집니다.

따라서 Kruskal이 끝났는데 선택한 간선 수가:

```text
V - 1보다 작음
```

이라면 원본 그래프가 연결되어 있지 않아 하나의 spanning tree를 만들 수 없었다는 뜻입니다.

이 경우 결과는 여러 component의 minimum spanning forest로 해석할 수 있습니다.

---

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 9]`에서 `_DisjointSet`과 `kruskal_mst`를 확인합니다.

- `parent`와 `component_size`를 별도로 저장합니다.
- `find`가 두 번의 반복으로 root를 찾고 경로를 압축합니다.
- 작은 component를 큰 component 아래에 붙입니다.
- 이미 같은 component인 두 root는 다시 합치지 않습니다.
- `union`이 실제로 성공한 간선만 MST 결과에 포함합니다.
- 선택 간선 목록이 실제 spanning tree인지 테스트에서 다시 검사합니다.

구현을 손으로 추적할 때는 다음을 구분해서 기록합니다.

```text
parent 배열
각 root의 component_size
각 find 뒤 path compression으로 바뀐 parent
각 union이 실제로 component 수를 줄였는지
```

예를 들어 같은 component에 대해 `union(a, b)`를 다시 호출했을 때:

```text
대표가 바뀌지 않음
component_size가 증가하지 않음
component 수가 줄지 않음
```

을 확인합니다.

---

## 완료 기준

- `parent[root] == root`가 대표를 나타내는 이유를 설명합니다.
- `find(a) == find(b)`가 같은 component임을 뜻하는 이유를 설명합니다.
- union by size에서 node 깊이가 증가할 때 component 크기가 최소 두 배가 되는 이유를 설명합니다.
- 같은 component의 두 원소를 합칠 때 parent와 size가 변하지 않는지 확인합니다.
- union by size·rank와 path compression의 역할을 구분합니다.
- path compression 뒤 non-root의 size나 rank를 실제 component 정보로 사용하면 안 되는 이유를 설명합니다.
- 단일 연산의 최악 비용과 연속된 연산의 상각 비용을 구분합니다.
- aggregate, accounting, potential 방법 중 하나로 실제 연산열의 전체 비용을 계산합니다.
- accounting 방법에서 credit이 음수가 되면 안 되는 이유를 설명합니다.
- potential 방법에서 중간 potential 변화가 상쇄되는 식을 전개합니다.
- `multipop` 또는 monotonic stack에서 각 원소가 최대 한 번 제거된다는 사실로 전체 비용을 분석합니다.
- Kruskal에서 DSU component가 현재 선택된 간선들의 연결 component를 나타내는 이유를 설명합니다.
- Kruskal에서 `find(u) == find(v)`인 간선을 추가하면 cycle이 생기는 이유를 설명합니다.

## 실패 신호

- 상각 `O(1)`을 한 번의 최악 `O(1)`과 같은 뜻으로 사용합니다.
- 상각 분석을 "평균적인 입력에서 빠르다"는 확률적 주장으로 설명합니다.
- union by size에서 작은 tree와 큰 tree의 방향을 반대로 붙이면서도 같은 높이 증명을 사용합니다.
- 이미 같은 component인지 확인하지 않고 size를 더합니다.
- path compression 뒤 모든 node의 rank나 size가 실제 tree 높이·component 크기라고 가정합니다.
- `O(α(n))`을 엄밀한 의미의 항상 `O(1)`이라고 표현합니다.
- accounting 방법에서 누적 credit이 음수가 될 수 있습니다.
- potential이 음수가 될 수 있는데도 `전체 실제 비용 <= 전체 상각 비용`을 그대로 사용합니다.
- `multipop` 한 번의 최악 비용과 연산열 전체의 상각 비용을 혼동합니다.
- 내부 `while`이 있다는 이유만으로 monotonic stack·deque를 곧바로 `O(n^2)`이라고 판단합니다.
- 기본 DSU로 온라인 간선 삭제를 바로 처리하려 합니다.
- Kruskal에서 이미 같은 component인 정점을 잇는 간선을 선택합니다.
