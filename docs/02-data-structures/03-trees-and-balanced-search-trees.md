# 트리와 균형 탐색 트리

## 학습 목표

- root, parent, child, subtree, depth, height를 구분합니다.
- DFS 순회 순서에 따라 계산에 필요한 정보의 방향이 달라지는 이유를 설명합니다.
- BST의 전체 key 범위와 rotation이 보존해야 하는 연결을 추적합니다.
- red-black tree의 색 조건이 높이를 `O(log n)`으로 제한하는 이유를 설명합니다.

## 선행지식

[순서와 탐색](02-order-search-heaps-and-priority.md), 재귀 호출, 부모·자식 관계를 설명할 수 있어야 합니다.

## 핵심 관점

Tree 문제에서는 한 node만 보지 않고 subtree가 반환하거나 전달해야 할 정보를 정합니다.

```text
자식 subtree의 결과를 부모에서 합칩니다.
부모까지의 정보를 자식에게 전달합니다.
```

## 1. 기본 용어

- `root`: 부모가 없는 시작 node
- `parent`와 `child`: root를 기준으로 정한 인접 관계
- `depth`: root에서 현재 node까지의 간선 수
- `height`: 현재 node에서 가장 깊은 leaf까지의 간선 수 또는 node 수
- `subtree`: 한 node와 그 모든 descendant
- `leaf`: child가 없는 node

높이를 간선 수로 셀지 node 수로 셀지 API에서 정합니다. 두 정의를 섞으면 빈 tree와 leaf의 결과가 달라집니다.

## 2. 순회와 계산 방향

### preorder

부모를 먼저 처리합니다. 현재 경로의 합, 권한, 누적 상태처럼 부모 정보가 자식에게 필요할 때 적합합니다.

### postorder

자식을 먼저 처리합니다. subtree 크기, 높이, 균형 여부처럼 자식 결과를 부모에서 합칠 때 적합합니다.

### inorder

이진 탐색 tree에서 key를 정렬된 순서로 방문합니다. 일반 tree에서는 같은 의미가 없습니다.

### level order

깊이별 처리나 최소 간선 거리에는 queue를 사용합니다.

## 3. 재귀와 반복 구현

재귀는 subtree가 같은 형태의 문제라는 점을 직접 표현합니다. 그러나 편향 tree에서는 깊이가 `O(n)`이 되어 call stack을 넘을 수 있습니다.

반복 구현에서는 다음 정보를 명시적인 stack에 저장해야 할 수 있습니다.

```text
현재 node
부모 또는 이전 node
다음에 방문할 child 위치
현재 경로에 필요한 값
자식 방문 전인지 방문 후인지 나타내는 단계
```

특히 postorder를 반복으로 구현할 때는 처음 들어온 경우와 자식 처리 뒤 돌아온 경우를 구분해야 합니다.

## 4. BST 조건

node의 key가 `k`라면 다음 범위를 만족해야 합니다.

```text
left subtree의 모든 key < k
right subtree의 모든 key > k
```

현재 node와 바로 아래 child만 비교해서는 충분하지 않습니다. 재귀 호출에 허용 가능한 `(lower, upper)` 범위를 전달해야 subtree 안쪽의 잘못된 key도 찾을 수 있습니다.

중복 key를 허용한다면 왼쪽, 오른쪽, count 필드 중 어디에 둘지 정합니다.

BST의 탐색 비용은 tree 높이 `h`에 비례합니다. 균형이 없으면 정렬된 입력에서 `h=n`이 될 수 있습니다.

## 5. rotation

오른쪽 rotation 전:

```text
        y
       / \
      x   C
     / \
    A   B
```

rotation 후:

```text
      x
     / \
    A   y
       / \
      B   C
```

`A < x < B < y < C`의 inorder 순서는 그대로입니다. 실제 구현에서는 child pointer뿐 아니라 다음 항목을 모두 갱신해야 합니다.

- `x`와 `y`의 parent
- 기존 parent가 가리키는 child
- subtree가 전체 tree의 root였다면 root pointer
- 저장 중인 height나 subtree size

## 6. red-black tree의 조건

일반적으로 다음 규칙을 사용합니다.

1. 각 node는 `red` 또는 `black`입니다.
2. root는 `black`입니다.
3. 비어 있는 leaf 위치는 `black`으로 계산합니다.
4. `red` node의 child는 `black`입니다.
5. 한 node에서 모든 descendant leaf까지의 black node 수가 같습니다.

연속된 red node가 없고 모든 root-to-leaf 경로의 black height가 같으므로 가장 긴 경로는 가장 짧은 경로의 두 배를 넘지 않습니다. 따라서 높이는 `O(log n)`입니다.

## 7. red-black tree 검증

한 번의 postorder에서 다음을 확인하고 black height를 반환할 수 있습니다.

```text
현재 key가 전달받은 BST 범위 안에 있습니까?
color가 red 또는 black입니까?
red node 아래에 red child가 있습니까?
왼쪽과 오른쪽 subtree의 black height가 같습니까?
```

빈 child는 black height `1`로 계산할 수 있습니다. root 색은 최상위 호출에서 별도로 확인합니다.

위반한 tree에서 임의의 높이를 반환하기보다 `ValueError`처럼 실패를 명확히 알리는 편이 안전합니다.

## 8. subtree에서 함께 반환할 값

같은 subtree를 여러 번 순회하지 않으려면 필요한 값을 함께 반환합니다.

- subtree 크기: `1 + left_size + right_size`
- 높이: `1 + max(left_height, right_height)`
- 균형 여부: 높이와 유효 여부를 함께 반환합니다.
- LCA: 두 target을 발견했는지 부모에서 합칩니다.
- red-black 검증: 유효 여부와 black height를 함께 계산합니다.

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 3]`은 다음을 수행합니다.

- `RedBlackNode`가 `key`, `color`, `left`, `right`를 저장합니다.
- `red_black_height`가 root 색을 먼저 검사합니다.
- 재귀 호출에 전체 허용 key 범위를 전달합니다.
- 왼쪽과 오른쪽 black height가 다르면 실패합니다.
- 모든 7-node 색 조합과 잘못된 BST 입력을 독립 검사기로 확인합니다.

exercise에는 insertion과 rotation이 없으므로, rotation을 별도 코드로 작성하고 전후 inorder 결과와 parent link를 직접 검사합니다.

## 완료 기준

- depth와 height의 단위를 명확히 정합니다.
- BST 검증에서 parent와의 직접 비교가 아니라 전체 허용 범위를 전달합니다.
- rotation 전후에 보존되는 inorder 순서와 갱신해야 할 pointer를 표시합니다.
- red-black 규칙을 하나씩 깨는 작은 tree를 만들어 검증기가 거부하는지 확인합니다.
- 깊은 편향 tree에서 재귀가 실패할 수 있음을 설명합니다.

## 실패 신호

- depth와 height를 같은 값처럼 사용합니다.
- BST 검증에서 바로 위 parent와만 비교합니다.
- rotation 뒤 parent 또는 root pointer를 갱신하지 않습니다.
- 빈 leaf의 color와 black height 계산이 불명확합니다.
- 편향 tree의 call stack 깊이를 고려하지 않습니다.
