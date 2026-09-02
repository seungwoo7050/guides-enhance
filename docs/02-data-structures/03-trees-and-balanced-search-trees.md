# 트리와 균형 탐색 트리

## 학습 목표

- root, parent, child, descendant, subtree, depth, height를 서로 구분합니다.
- DFS 순회 순서에 따라 계산에 필요한 정보가 부모에서 자식으로 가는지, 자식에서 부모로 올라오는지 설명합니다.
- BST가 만족해야 하는 전체 key 범위를 추적하고, rotation이 보존해야 하는 연결과 순서를 설명합니다.
- red-black tree의 색 조건이 tree 높이를 `O(log n)`으로 제한하는 이유를 단계적으로 설명합니다.

## 선행지식

[순서와 탐색](02-order-search-heaps-and-priority.md), 재귀 호출, 부모·자식 관계를 설명할 수 있어야 합니다.

이 문서에서는 별도 언급이 없으면 **rooted tree**, 즉 특정 node를 root로 정한 tree를 다룹니다.

## 핵심 관점

Tree 문제에서는 한 node만 따로 보지 않고, **subtree가 부모에게 무엇을 반환해야 하는지** 또는 **부모가 자식에게 무엇을 전달해야 하는지**를 먼저 정합니다.

```text
자식 subtree의 결과를 부모에서 합칩니다.
부모까지의 정보를 자식에게 전달합니다.
```

예를 들면 다음과 같습니다.

```text
subtree 높이:
자식 -> 부모

root부터 현재 node까지의 경로 합:
부모 -> 자식
```

순회 방식은 이 정보의 방향과 맞아야 합니다.

## 1. 기본 용어

- `root`: 부모가 없는 시작 node
- `parent`: 현재 node 바로 위의 node
- `child`: 현재 node 바로 아래의 node
- `ancestor`: parent를 포함하여 root 방향에 있는 모든 node
- `descendant`: child를 포함하여 아래 방향에 있는 모든 node
- `subtree`: 한 node와 그 모든 descendant로 이루어진 tree
- `leaf`: child가 없는 node
- `depth`: root에서 현재 node까지의 간선 수
- `height`: 현재 node에서 가장 깊은 leaf까지의 거리

### depth

root의 depth를 `0`으로 정의하면 다음과 같습니다.

```text
root depth = 0
root의 child depth = 1
그 child의 child depth = 2
```

즉 depth는 **root를 기준으로 위에서 아래로 내려온 거리**입니다.

### height

height는 정의를 먼저 고정해야 합니다.

간선 수를 기준으로 하면:

```text
leaf height = 0
node height = 1 + max(child height)
```

node 수를 기준으로 하면:

```text
leaf height = 1
node height = 1 + max(child height)
```

두 정의 모두 사용할 수 있지만 한 구현 안에서 섞으면 안 됩니다.

특히 빈 tree의 높이도 정의가 달라질 수 있습니다.

예를 들어 간선 수 기준 구현에서는 다음처럼 둘 수 있습니다.

```text
empty subtree height = -1
leaf height = 0
```

반면 node 수 기준 구현에서는 다음처럼 둘 수 있습니다.

```text
empty subtree height = 0
leaf height = 1
```

API와 테스트에서 어떤 정의를 사용하는지 먼저 명확히 정합니다.

## 2. 순회와 계산 방향

Tree 순회에서는 **node를 언제 처리하는가**가 중요합니다.

### preorder

현재 node를 자식보다 먼저 처리합니다.

```text
현재 node
왼쪽 subtree
오른쪽 subtree
```

부모에서 계산한 정보가 자식에게 필요할 때 적합합니다.

예:

- root에서 현재 node까지의 경로 합
- 현재 depth
- 상위 node에서 물려받은 권한이나 상태
- 현재 경로에 포함된 값

예를 들어 경로 합은 다음처럼 전달할 수 있습니다.

```text
child_sum = parent_sum + child.value
```

즉 정보의 주된 방향은 다음과 같습니다.

```text
부모 -> 자식
```

### postorder

자식을 먼저 처리한 뒤 현재 node를 처리합니다.

```text
왼쪽 subtree
오른쪽 subtree
현재 node
```

자식 subtree의 결과를 부모가 합쳐야 할 때 적합합니다.

예:

- subtree 크기
- subtree 높이
- tree 균형 여부
- subtree의 최솟값·최댓값
- red-black tree의 black height

예:

```text
size(node)
= 1 + size(node.left) + size(node.right)
```

즉 정보의 주된 방향은 다음과 같습니다.

```text
자식 -> 부모
```

### inorder

이진 tree에서 다음 순서로 방문합니다.

```text
왼쪽 subtree
현재 node
오른쪽 subtree
```

특히 **BST가 올바르게 구성되어 있고 중복 key 정책도 일관된 경우** inorder 순회 결과는 key의 정렬 순서가 됩니다.

예:

```text
    4
   / \
  2   7
```

inorder:

```text
2, 4, 7
```

그러나 일반 binary tree나 일반 tree에서 inorder가 "정렬 순서"를 의미하는 것은 아닙니다.

### level order

root에서 가까운 node부터 깊이별로 방문합니다.

보통 queue를 사용합니다.

```text
depth 0
depth 1
depth 2
...
```

다음 문제에 자주 사용합니다.

- 깊이별 처리
- binary tree의 level 출력
- 간선 가중치가 모두 동일한 tree에서 최소 간선 거리
- 가장 가까운 조건 만족 node 탐색

## 3. 재귀와 반복 구현

재귀는 각 subtree가 전체 tree와 같은 형태의 문제라는 점을 직접 표현합니다.

예를 들어 subtree 크기는 다음 형태로 생각할 수 있습니다.

```text
size(node):
    왼쪽 subtree 크기
    오른쪽 subtree 크기
    둘을 합치고 현재 node 1개 추가
```

그러나 tree가 심하게 편향되면 재귀 깊이도 커집니다.

예:

```text
1
 \
  2
   \
    3
     \
      ...
```

node가 `n`개라면 높이가 `O(n)`이고, 재귀 호출 깊이도 `O(n)`이 될 수 있습니다.

언어나 실행 환경의 call stack 제한보다 깊어지면 stack overflow 또는 recursion limit 오류가 발생할 수 있습니다.

### 반복 구현

반복 구현에서는 재귀 호출이 암묵적으로 저장하던 상태를 명시적인 stack에 직접 저장해야 합니다.

필요할 수 있는 정보는 다음과 같습니다.

```text
현재 node
부모 또는 이전 node
다음에 방문할 child 위치
현재 경로에 필요한 값
자식 방문 전인지 방문 후인지 나타내는 단계
```

특히 postorder는 node를 두 번 마주치는 상황을 구분해야 합니다.

```text
1. 처음 node에 도착함
2. 자식 처리가 끝나고 node로 돌아옴
```

따라서 다음처럼 상태를 함께 저장할 수 있습니다.

```text
(node, visited_children)
```

또는:

```text
(node, ENTER)
(node, EXIT)
```

예를 들어 stack에 `(node, false)`를 넣고, 처음 꺼냈을 때 `(node, true)`와 자식을 다시 넣는 방식으로 postorder를 흉내 낼 수 있습니다.

핵심은 반복 구현이 재귀보다 본질적으로 다른 계산을 하는 것이 아니라, **call stack이 저장하던 정보를 프로그램이 직접 관리한다는 점**입니다.

## 4. BST 조건

Binary Search Tree(BST)는 각 node의 key가 subtree 전체에 대해 순서 조건을 만족하는 binary tree입니다.

중복 key를 허용하지 않는다고 하면, node의 key가 `k`일 때:

```text
left subtree의 모든 key < k
right subtree의 모든 key > k
```

이어야 합니다.

### 바로 아래 child만 비교하면 부족한 이유

다음 tree를 보겠습니다.

```text
      10
     /  \
    5    20
        /
       7
```

각 parent-child만 보면:

```text
5 < 10
20 > 10
7 < 20
```

이라서 문제가 없어 보입니다.

그러나 `7`은 root `10`의 오른쪽 subtree에 있으므로 실제로는:

```text
7 > 10
```

이어야 합니다.

따라서 BST 검증에서는 parent와의 관계만 확인하면 안 됩니다.

### 전체 허용 범위를 전달합니다

각 재귀 호출에 현재 subtree에서 허용되는 key 범위를 전달합니다.

root에서 시작:

```text
(-∞, +∞)
```

key가 `10`인 node의 왼쪽 subtree:

```text
(-∞, 10)
```

오른쪽 subtree:

```text
(10, +∞)
```

오른쪽 child `20`의 왼쪽 subtree라면 두 조건을 모두 만족해야 하므로:

```text
(10, 20)
```

가 됩니다.

따라서 위 예의 `7`은:

```text
10 < 7 < 20
```

을 만족하지 못해 거부됩니다.

### 중복 key 정책

중복 key를 허용한다면 정책을 명확히 정해야 합니다.

예:

```text
중복은 항상 왼쪽에 둔다.
left <= k
right > k
```

또는:

```text
중복은 항상 오른쪽에 둔다.
left < k
right >= k
```

또는 node에 count를 둡니다.

```text
Node {
    key
    count
}
```

중요한 것은 삽입, 검색, 삭제, 검증이 모두 같은 규칙을 사용해야 한다는 점입니다.

### BST 탐색 비용

BST의 탐색·삽입·삭제 비용은 일반적으로 tree 높이 `h`에 비례합니다.

```text
O(h)
```

tree가 균형에 가깝다면:

```text
h = O(log n)
```

이지만, 정렬된 값을 단순 BST에 순서대로 삽입하면 다음처럼 편향될 수 있습니다.

```text
1
 \
  2
   \
    3
     \
      4
```

이 경우:

```text
h = O(n)
```

이므로 탐색도 최악 `O(n)`이 됩니다.

BST 자체가 자동으로 `O(log n)` 탐색을 보장하는 것은 아닙니다.

## 5. rotation

rotation은 BST의 inorder 순서를 보존하면서 일부 parent-child 관계를 바꾸는 연산입니다.

균형 탐색 tree에서는 높이를 조정할 때 사용합니다.

### 오른쪽 rotation

rotation 전:

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

BST key 관계가 다음과 같다고 하겠습니다.

```text
A < x < B < y < C
```

rotation 전 inorder:

```text
A, x, B, y, C
```

rotation 후 inorder도:

```text
A, x, B, y, C
```

로 같습니다.

즉 rotation은 subtree의 모양은 바꾸지만 BST가 표현하는 key 순서는 유지합니다.

### 실제 구현에서 갱신해야 하는 연결

child pointer 두 개만 바꾸면 충분하지 않습니다.

오른쪽 rotation에서 최소한 다음 연결을 확인해야 합니다.

- `x`의 이전 parent는 `y`
- `y.left`는 이전의 `B`
- `x.right`는 `y`
- `x.parent`는 원래 `y.parent`
- `y.parent`는 `x`
- `B`가 존재하면 `B.parent`는 `y`
- 원래 `y`의 parent가 가리키던 child를 `x`로 변경
- `y`가 전체 tree의 root였다면 root pointer를 `x`로 변경

개념적으로:

```text
old_parent
    |
    y
   /
  x
```

가:

```text
old_parent
    |
    x
     \
      y
```

로 바뀌므로, subtree 내부뿐 아니라 subtree 바깥과 연결되는 pointer도 수정해야 합니다.

### 부가 정보를 저장하는 tree

node가 다음과 같은 값을 저장한다면 rotation 뒤 다시 계산해야 할 수 있습니다.

```text
height
subtree size
subtree sum
최댓값
기타 augmentation 정보
```

예를 들어 subtree size를 저장한다면 구조가 바뀐 `y`와 `x`의 size가 모두 달라질 수 있습니다.

rotation의 정확성은 다음 두 관점에서 확인합니다.

```text
1. inorder key 순서가 보존되는가?
2. parent-child 연결과 저장된 부가 정보가 일관적인가?
```

## 6. red-black tree의 조건

Red-black tree는 BST 조건에 색 규칙을 추가하여 지나치게 긴 경로가 생기지 않도록 제한하는 균형 탐색 tree입니다.

일반적으로 다음 규칙을 사용합니다.

1. 각 실제 node는 `red` 또는 `black`입니다.
2. root는 `black`입니다.
3. 비어 있는 child 위치인 NIL leaf는 `black`으로 취급합니다.
4. `red` node의 child는 모두 `black`입니다.
5. 한 node에서 descendant NIL leaf까지 가는 모든 경로에는 같은 수의 black node가 있습니다.

5번의 black node 수를 **black height**라고 부릅니다.

구현마다 현재 node 자신을 black height에 포함할지, NIL leaf를 몇으로 셀지 정의가 조금 다를 수 있습니다. 중요한 것은 모든 경로에서 같은 규칙을 일관되게 사용하는 것입니다.

### NIL leaf

다음 실제 leaf node를 생각해 보겠습니다.

```text
    10
   /  \
 NIL  NIL
```

red-black tree 정의에서는 이 비어 있는 child 위치를 단순히 "아무것도 없음"으로 무시하지 않고 black NIL leaf로 취급합니다.

실제 구현에서는:

```text
None
```

을 사용하면서 논리적으로 black NIL로 처리할 수도 있고, 별도의 sentinel node를 둘 수도 있습니다.

### 왜 연속된 red가 금지되는가

규칙 4 때문에 red node의 바로 아래에는 red node가 올 수 없습니다.

따라서 root-to-leaf 경로에서 red node가 나타날 때마다 그 사이에는 black node가 있어야 합니다.

가장 긴 경로가 red와 black을 최대한 번갈아 포함한다고 해도:

```text
black, red, black, red, black, ...
```

처럼 됩니다.

즉 red node 수는 black node 수보다 지나치게 많아질 수 없습니다.

### 높이가 `O(log n)`인 이유

black height가 `b`인 subtree는 최소한 지수적으로 많은 실제 node를 포함해야 합니다.

직관적으로 모든 root-to-NIL 경로에 black node가 `b`개 필요하므로, black height가 커질수록 tree가 충분히 많이 분기되어야 합니다.

표준적인 하한은 다음 형태입니다.

```text
black height가 b인 subtree의 내부 node 수 >= 2^b - 1
```

따라서 node 수가 `n`이면:

```text
b <= log2(n + 1)
```

입니다.

한편 red node가 연속될 수 없으므로 실제 root-to-leaf 경로의 길이는 black node 수의 두 배보다 커질 수 없습니다.

즉 높이 `h`는 상수 배 차이 안에서:

```text
h <= 2b
```

이고 따라서:

```text
h = O(log n)
```

이 됩니다.

중요한 점은 단순히 "black node 수가 같다"만으로는 충분하지 않고, **red node가 연속될 수 없다는 규칙과 함께** 경로 길이가 제한된다는 것입니다.

## 7. red-black tree 검증

red-black tree는 BST 조건과 색 조건을 동시에 검증해야 합니다.

한 번의 postorder 재귀에서 다음 작업을 함께 수행할 수 있습니다.

```text
현재 key가 전달받은 BST 허용 범위 안에 있는가?
color가 red 또는 black인가?
red node 아래에 red child가 있는가?
왼쪽과 오른쪽 subtree의 black height가 같은가?
```

자식 결과를 모두 확인해야 현재 node의 black height를 계산할 수 있으므로 postorder가 자연스럽습니다.

### black height 반환

빈 child를 black NIL leaf로 취급하고 black height를 `1`로 세는 규칙을 선택했다고 하겠습니다.

```text
black_height(None) = 1
```

실제 node에서 왼쪽과 오른쪽 결과가 같아야 합니다.

```text
left_black_height == right_black_height
```

그 뒤 현재 node가 black이면 1을 더합니다.

```text
if node.color == BLACK:
    return child_black_height + 1
else:
    return child_black_height
```

이 정의에서는 NIL을 포함하여 세고 있습니다.

다른 구현에서 NIL을 `0`으로 세어도 가능합니다. 단, 전체 검증에서 같은 규칙을 사용해야 합니다.

### root 색

재귀 helper가 모든 subtree에 공통으로 적용된다면 root만의 조건:

```text
root는 black
```

은 최상위 호출에서 별도로 확인하는 편이 자연스럽습니다.

### 위반 시 처리

잘못된 tree에서 임의의 black height를 반환하면 호출자가 정상 결과와 실패를 구분하기 어렵습니다.

따라서 다음처럼 실패를 명확히 표현하는 편이 안전합니다.

```text
ValueError
명시적인 invalid 결과
(result, valid) 형태
```

중요한 것은 잘못된 subtree가 정상적인 black height처럼 상위 계산에 섞이지 않게 하는 것입니다.

## 8. subtree에서 함께 반환할 값

같은 subtree를 여러 번 순회하면 불필요한 비용이 생길 수 있습니다.

필요한 값을 한 번의 postorder에서 함께 계산하면 효율적입니다.

### subtree 크기

```text
size
= 1 + left_size + right_size
```

### 높이

node 수 기준이라면:

```text
height
= 1 + max(left_height, right_height)
```

간선 수 기준이라면 빈 subtree의 기본값을 그 정의에 맞게 정합니다.

### 균형 여부

binary tree가 높이 균형인지 확인한다고 하겠습니다.

나쁜 방식:

```text
각 node에서 왼쪽 height를 다시 계산
각 node에서 오른쪽 height를 다시 계산
```

편향 tree에서는 같은 subtree를 반복 방문하여 `O(n^2)`이 될 수 있습니다.

대신 한 번의 postorder에서 다음을 함께 반환합니다.

```text
(valid, height)
```

부모는 자식의 height와 valid 여부를 한 번에 사용합니다.

### LCA

Lowest Common Ancestor 문제에서는 subtree가 다음 정보를 부모에게 반환할 수 있습니다.

```text
target A를 발견했는가?
target B를 발견했는가?
이 subtree 안에서 이미 LCA를 찾았는가?
```

문제의 API에 따라 실제 구현 형태는 달라지지만 핵심은 **두 target에 대한 정보를 자식 subtree에서 부모가 합친다**는 점입니다.

### red-black 검증

red-black 검증도 같은 원리입니다.

```text
BST 범위 검증
색 규칙 검증
black height 계산
```

을 별도 순회로 나누지 않고 한 postorder 안에서 처리할 수 있습니다.

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 3]`은 다음을 수행합니다.

- `RedBlackNode`가 `key`, `color`, `left`, `right`를 저장합니다.
- `red_black_height`가 root 색을 먼저 검사합니다.
- 재귀 호출에 전체 허용 key 범위를 전달합니다.
- 왼쪽과 오른쪽 black height가 다르면 실패합니다.
- 모든 7-node 색 조합과 잘못된 BST 입력을 독립 검사기로 확인합니다.

exercise에는 insertion과 rotation이 없으므로, rotation을 별도 코드로 작성하고 다음 조건을 직접 검사합니다.

```text
rotation 전 inorder == rotation 후 inorder
모든 child의 parent가 실제 parent를 가리킴
원래 subtree root의 parent 연결이 새 subtree root로 바뀜
전체 tree root에서 rotation했다면 root pointer가 갱신됨
```

height나 subtree size 같은 부가 정보를 저장하는 구현이라면 rotation 뒤 그 값도 검사합니다.

## 완료 기준

- depth가 root에서 현재 node까지의 거리이고 height가 현재 node에서 leaf까지의 거리임을 구분합니다.
- height를 간선 수로 셀지 node 수로 셀지 명확히 정합니다.
- preorder가 부모 정보를 자식에게 전달할 때, postorder가 자식 결과를 부모가 합칠 때 적합한 이유를 설명합니다.
- BST 검증에서 parent와의 직접 비교가 아니라 전체 허용 key 범위를 전달합니다.
- 중복 key를 허용한다면 어느 방향에 둘지 또는 count를 사용할지 명시합니다.
- rotation 전후에 보존되는 inorder 순서와 갱신해야 할 parent·child·root pointer를 표시합니다.
- red-black 규칙을 하나씩 깨는 작은 tree를 만들어 검증기가 거부하는지 확인합니다.
- red-black tree 높이가 `O(log n)`인 이유를 black height와 연속 red 금지 규칙으로 설명합니다.
- 깊은 편향 tree에서 재귀 깊이가 `O(n)`이 되어 call stack 문제가 생길 수 있음을 설명합니다.

## 실패 신호

- depth와 height를 같은 값처럼 사용합니다.
- leaf height와 빈 tree height의 기준이 문서나 코드 안에서 바뀝니다.
- BST 검증에서 바로 위 parent와만 비교합니다.
- 중복 key 정책이 삽입과 검증에서 서로 다릅니다.
- rotation 뒤 parent 또는 root pointer를 갱신하지 않습니다.
- rotation 뒤 height나 subtree size 같은 저장된 부가 정보를 갱신하지 않습니다.
- 빈 leaf의 color와 black height 계산 규칙이 불명확합니다.
- red-black tree 높이 제한을 색의 개수만으로 설명하고 연속 red 금지 조건을 연결하지 않습니다.
- 편향 tree의 call stack 깊이를 고려하지 않습니다.
