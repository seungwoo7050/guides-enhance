# 서로소 집합과 상각 분석

## 학습 목표

- DSU가 저장하는 대표와 component 정보를 설명합니다.
- union by size·rank와 path compression의 역할을 구분합니다.
- aggregate, accounting, potential 방법으로 연속된 연산의 총비용을 분석합니다.
- 한 번의 최악 비용과 상각 비용을 혼동하지 않습니다.

## 선행지식

[Tree](03-trees-and-balanced-search-trees.md), 점근 비용, 여러 연산의 총비용을 구분할 수 있어야 합니다.

## 핵심 관점

상각 분석은 입력 확률을 가정하지 않습니다. 어떤 허용된 연산 순서에서도 전체 비용이 제한된다는 사실을 보입니다.

```text
전체 실제 비용
<= 연산 수 × 상각 비용 + 초기·최종 potential 차이
```

## 1. DSU

DSU(disjoint-set union)는 각 원소가 어느 연결 component에 속하는지 관리합니다.

```text
make_set(x): x만 포함한 집합을 만듭니다.
find(x): x가 속한 집합의 대표를 반환합니다.
union(a, b): 두 집합을 합칩니다.
```

보통 parent 배열로 forest를 표현하며 `parent[root] == root`인 node가 대표입니다.

## 2. union by size 또는 rank

작은 tree의 root를 큰 tree의 root 아래에 붙이면 높이가 빠르게 커지는 일을 막을 수 있습니다.

size를 사용할 때는 다음 값을 유지합니다.

```text
root의 size는 해당 component의 원소 수입니다.
서로 다른 두 component를 합칠 때 작은 root를 큰 root 아래에 붙입니다.
새 root의 size는 두 size의 합입니다.
```

한 node의 깊이가 증가할 때 그 node가 속한 component 크기는 최소 두 배가 됩니다. path compression이 없어도 깊이는 `O(log n)`으로 제한됩니다.

이미 같은 component인 두 원소를 `union`할 때는 parent와 size를 바꾸지 않습니다.

## 3. path compression

`find(x)`가 root까지 올라간 뒤 방문한 node를 root에 직접 연결합니다.

```text
find(x):
    if parent[x] != x:
        parent[x] = find(parent[x])
    return parent[x]
```

union by size·rank와 함께 사용하면 `m`개 연산의 총비용은 `O(m α(n))`으로 알려져 있습니다. 실제 입력에서는 매우 느리게 증가하지만 이론적으로 항상 `O(1)`이라고 표현하지 않습니다.

path compression 뒤에는 root의 size만 component 크기로 사용합니다. 중간 node의 오래된 size에 의미를 부여하지 않습니다.

## 4. aggregate 방법

연산 전체의 실제 비용을 직접 더합니다.

동적 배열이 가득 찰 때 capacity를 두 배로 늘린다고 가정합니다. `n`번 `append`하는 동안 기존 원소를 옮기는 횟수는 대략 다음과 같습니다.

```text
1 + 2 + 4 + ... < 2n
```

새 원소를 넣는 비용과 복사 비용을 합해도 전체는 `O(n)`이므로 `append` 한 번의 상각 비용은 `O(1)`입니다.

## 5. accounting 방법

싼 연산에 실제 비용보다 큰 가상 비용을 부과하고 남은 credit을 저장합니다. 이후 비싼 연산이 발생하면 쌓아 둔 credit으로 비용을 지불합니다.

동적 배열의 각 `append`에 일정한 credit을 추가로 부과하면 다음 resize 때의 복사 비용을 충당할 수 있습니다. 어느 시점에도 credit이 음수가 되지 않는지 확인해야 합니다.

## 6. potential 방법

자료구조 상태 `D`에 `Φ(D) >= 0`인 potential을 정합니다.

```text
상각 비용
= 실제 비용 + Φ(새 상태) - Φ(이전 상태)
```

여러 연산을 합하면 중간 potential 변화가 상쇄됩니다. 초기 potential이 0이고 마지막 potential이 음수가 아니면 전체 실제 비용은 전체 상각 비용보다 크지 않습니다.

## 7. stack의 `multipop`

다음 연산을 생각합니다.

- `push(x)`
- `pop()`
- `multipop(k)`: 최대 `k`개를 제거합니다.

한 번의 `multipop`은 `O(n)`일 수 있습니다. 그러나 각 원소는 한 번 들어가고 최대 한 번 제거되므로 `m`개 연산의 전체 비용은 `O(m)`입니다.

이와 같은 계산을 monotonic stack과 deque에도 적용합니다. 안쪽 `while`이 여러 번 실행되어도 각 원소가 한 번만 제거된다면 전체는 선형입니다.

## 8. DSU가 적합하지 않은 문제

기본 DSU는 합친 component를 되돌리기 어렵습니다.

- 간선 삭제가 자주 발생합니다.
- 시간에 따라 연결 상태를 계속 물어봅니다.
- component 안의 실제 경로나 거리를 구해야 합니다.
- 대표가 단순한 component 식별자 이상의 의미를 가져야 합니다.

이 경우 offline reverse processing, rollback DSU, dynamic connectivity처럼 다른 방법을 검토합니다.

## 9. Kruskal과 DSU

Kruskal에서는 간선을 가중치 순으로 보고 서로 다른 component를 잇는 간선만 선택합니다.

```text
find(u) != find(v)이면 간선을 선택하고 union(u, v)를 수행합니다.
find(u) == find(v)이면 해당 간선은 cycle을 만들므로 건너뜁니다.
```

선택한 간선 수가 `V-1`보다 작다면 원본 그래프가 연결되지 않았습니다.

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 9]`에서 `_DisjointSet`과 `kruskal_mst`를 확인합니다.

- `parent`와 `component_size`를 별도로 저장합니다.
- `find`가 두 번의 반복으로 root를 찾고 경로를 압축합니다.
- 작은 component를 큰 component 아래에 붙입니다.
- `union`이 성공한 간선만 MST 결과에 포함합니다.
- 선택 간선 목록이 실제 spanning tree인지 테스트에서 다시 검사합니다.

## 완료 기준

- `find`와 `union` 뒤 각 원소의 대표를 손으로 추적합니다.
- 같은 component의 두 원소를 합칠 때 상태가 변하지 않는지 확인합니다.
- 단일 연산의 최악 비용과 연속된 연산의 상각 비용을 구분합니다.
- aggregate, accounting, potential 중 하나로 실제 연산열의 전체 비용을 계산합니다.
- Kruskal에서 DSU가 cycle을 막는 과정을 설명합니다.

## 실패 신호

- 상각 `O(1)`을 한 번의 최악 `O(1)`과 같은 뜻으로 사용합니다.
- path compression 뒤 모든 node의 rank나 size가 정확하다고 가정합니다.
- potential이 음수가 될 수 있는데도 상한 증명에 사용합니다.
- 이미 같은 component인지 확인하지 않고 size를 더합니다.
- 기본 DSU로 온라인 간선 삭제를 바로 처리하려 합니다.
