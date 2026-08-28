# B+ Tree

정수 key와 임의의 값을 저장하는 메모리 기반 B+ tree 구현입니다. 실제 값은 leaf에만 저장하고, internal separator는 오른쪽 subtree의 최소 key를 나타냅니다. Leaf의 `next` 연결을 따라가므로 시작 key를 찾은 뒤 root를 다시 탐색하지 않고 범위 조회를 이어 갈 수 있습니다.

## 주요 기능

- 유일한 정수 key 삽입과 기존 값 교체
- 서로 다른 규칙을 사용하는 leaf split과 internal split
- root 증가와 여러 단계의 분할 전파
- 단일 key 조회
- 양 끝을 포함하는 leaf 연결 범위 조회
- key 순서, 최소 점유율, child 범위, separator, leaf 깊이와 next 연결 검증

## 구성

`Node`는 leaf와 internal node를 모두 표현합니다. Leaf는 `keys`, `values`, `next`를 사용하고 internal node는 `keys`, `children`을 사용합니다. `BPlusTree`는 leaf까지 내려온 parent path를 보관했다가 분할 결과를 위로 반영합니다.

## 설치와 사용

Python 3.11 이상이 필요합니다.

```bash
python3 -m pip install -e .
```

```python
from bplus_tree import BPlusTree

tree: BPlusTree[str] = BPlusTree(order=4)
tree.insert(20, "twenty")
tree.insert(10, "ten")
tree.insert(30, "thirty")

tree.validate()
assert tree.get(20) == "twenty"
assert tree.range(10, 25) == [(10, "ten"), (20, "twenty")]
```

## 테스트

```bash
make test
```

테스트는 여러 `order`, 무작위 삽입 순서, root 증가, 기존 key 교체, 여러 leaf를 지나는 범위 조회와 손상된 separator 탐지를 확인합니다.

## 설계에서 확인할 점

- Separator는 오른쪽 subtree의 최소 key입니다. 탐색에서는 `bisect_right`를 사용해 separator와 같은 key를 오른쪽 child로 보냅니다.
- Leaf split은 key, value와 `next` 연결을 함께 나눕니다. Internal split은 가운데 separator를 parent로 올리고 그 key를 어느 child에도 남기지 않습니다.
- Parent의 child 위치는 dataclass 값 비교가 아니라 객체 identity로 찾습니다. 연결된 node 전체를 값으로 비교하면 같은 내용의 sibling을 잘못 고르거나 재귀 비교가 발생할 수 있습니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | node 형태와 빈 root leaf | `src/bplus_tree.py` · `Node`, `BPlusTree.__init__` |
| 2 | separator에 따른 leaf 탐색 | `src/bplus_tree.py` · `_find_leaf` |
| 3 | 정렬 삽입과 기존 값 교체 | `src/bplus_tree.py` · `insert` |
| 4 | leaf 분할과 parent 반영 | `src/bplus_tree.py` · `_split_leaf`, `_insert_in_parent` |
| 5 | internal node 분할과 separator 승격 | `src/bplus_tree.py` · `_split_internal` |
| 6 | 단일 key 조회와 leaf 연결 범위 조회 | `src/bplus_tree.py` · `get`, `range` |
| 7 | tree 불변식 검사 | `src/bplus_tree.py` · `validate` |
| 8 | B+ tree 동작과 손상 검증 | `tests/test_bplus_tree.py` · `BPlusTreeTests` |

## 범위와 제한

이 구현은 insert, 기존 값 교체, 단일 key 조회와 범위 조회만 제공합니다. Delete, merge와 redistribution, 영속 저장, latch와 동시 접근은 포함하지 않습니다.
