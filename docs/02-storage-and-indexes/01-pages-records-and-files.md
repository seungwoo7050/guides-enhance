# 페이지, 레코드와 파일 구성

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 합니다.

- DBMS가 tuple을 page 단위로 읽고 쓰는 이유
- 가변 길이 record를 slotted page에 배치하는 방법
- `(page_id, slot_id)`를 record 식별자로 사용하는 이유
- delete, update와 compaction 뒤에도 slot ID를 유지하는 방법
- heap file과 sorted file의 읽기·쓰기 비용 차이
- 손상된 page 정보가 index와 복구 과정까지 잘못된 결과를 만드는 이유

## 저장장치는 page 단위로 접근합니다

애플리케이션은 row 하나를 읽는다고 생각하지만, DBMS는 보통 고정 크기 page를 저장장치와 메모리 사이에서 옮깁니다.

```text
논리 tuple
→ record encoding
→ page 안의 slot
→ file 안의 page
→ 저장장치 I/O
```

한 column만 필요해도 그 record가 들어 있는 page를 읽어야 할 수 있습니다. 따라서 다음 항목이 실제 비용에 영향을 줍니다.

- page 하나에 record가 몇 개 들어가는지
- 함께 조회하는 record가 가까운 page에 있는지
- update 후 record가 기존 page에 남을 수 있는지
- table scan이 page를 연속해서 읽는지
- index lookup이 heap page를 얼마나 흩어져 방문하는지

Page는 단순한 구현 세부가 아니라 I/O 비용을 계산하는 기본 단위입니다.

## 고정 길이와 가변 길이 record

모든 field 길이가 고정되어 있다면 record 위치를 계산하기 쉽습니다.

```text
record 0: base + 0 * record_size
record 1: base + 1 * record_size
```

실제 row에는 text, nullable column과 가변 길이 값이 포함됩니다. Record마다 길이가 다르면 delete와 update 뒤 빈 공간이 생기며, 단순 배열처럼 다루기 어렵습니다.

일반적인 record 형식에는 다음 정보가 들어갑니다.

- null bitmap
- 고정 길이 field
- 가변 길이 field의 offset 또는 length
- record header
- transaction visibility 정보

이 저장소의 [`slotted-page`](../../exercises/slotted-page/)는 전체 SQL row 형식을 복제하지 않습니다. 가변 길이 `bytes`, 안정적인 slot ID와 직렬화 검증에 집중합니다.

## Slotted page

Slotted page는 앞쪽에 header와 slot directory를 두고, record byte는 뒤쪽부터 쌓는 방식입니다.

```text
낮은 offset
┌──────────────────────────────┐
│ page header                  │
├──────────────────────────────┤
│ slot 0: offset, length       │
│ slot 1: offset, length       │
│ ...                          │
├──────── free space ──────────┤
│ record bytes                 │
│ record bytes                 │
└──────────────────────────────┘
높은 offset
```

Header와 slot directory는 낮은 offset 방향에서 커지고, record byte는 높은 offset 쪽에서 낮은 쪽으로 쌓입니다. 두 영역 사이가 실제로 새 record를 넣을 수 있는 연속 공간입니다.

```text
free_space = free_end - directory_end
```

새 record를 넣을 때는 payload 크기뿐 아니라 새 slot entry가 차지할 공간도 계산해야 합니다.

## Offset을 외부 식별자로 쓰지 않습니다

Compaction은 record byte를 page 안에서 이동합니다. Byte offset을 외부 식별자로 사용하면 record가 이동할 때마다 모든 index entry를 수정해야 합니다.

```text
이전: slot 3 → offset 220
이후: slot 3 → offset 180
외부 RID: (page 17, slot 3) 유지
```

외부에서는 `(page_id, slot_id)`를 사용하고, slot entry만 현재 offset을 가리키게 합니다. 이 간접 참조 덕분에 compaction 뒤에도 index가 같은 record를 찾을 수 있습니다.

## Insert 전에 전체 수용 가능성을 확인합니다

안전한 insert는 다음 순서로 처리합니다.

1. payload 형식과 길이를 검증합니다.
2. 삭제된 slot을 재사용할 수 있는지 확인합니다.
3. live record 전체와 새 payload가 page에 들어가는지 계산합니다.
4. 총공간은 충분하지만 연속 공간이 부족하면 compaction합니다.
5. 모든 검사가 끝난 뒤 byte와 slot entry를 변경합니다.

공간이 부족한 사실을 record 일부를 쓴 뒤 발견하면 page가 손상될 수 있습니다. 실패할 수 있는 계산을 먼저 끝내고 실제 변경은 마지막에 수행해야 합니다.

## Delete는 slot을 남깁니다

삭제할 때 slot entry를 제거하고 뒤의 slot 번호를 당기면 기존 RID가 다른 record를 가리키게 됩니다. 따라서 삭제된 slot은 tombstone으로 남깁니다.

```text
slot 0 → live
slot 1 → deleted
slot 2 → live
```

새 insert가 tombstone slot을 재사용하면 directory 크기를 늘리지 않아도 됩니다. 다만 오래된 RID가 남아 있다면 같은 slot에 새 record가 들어간 뒤 다른 record를 가리키는 문제가 생길 수 있습니다. 실제 DBMS는 transaction visibility, generation 값이나 index 정리로 이를 처리합니다. 이 저장소의 구현은 slot ID 유지와 tombstone 재사용까지만 다룹니다.

## Update 실패는 기존 값을 보존해야 합니다

새 payload가 기존 공간보다 작으면 같은 위치에 쓰고 길이만 줄일 수 있습니다. 더 큰 payload는 다른 위치로 옮겨야 할 수 있습니다.

가능한 방법은 다음과 같습니다.

- page 안의 다른 위치로 옮기고 slot offset을 바꿉니다.
- compaction 후 다시 배치합니다.
- 다른 page로 옮기고 forwarding pointer를 남깁니다.
- delete와 insert를 하나의 원자적 변경으로 묶습니다.

어떤 방법을 선택하든 공간 부족이 확인되기 전에 기존 record를 지우면 안 됩니다.

```text
필요 공간 계산
→ 전체 배치 가능 여부 확인
→ 새 배열 준비
→ byte와 slot 정보를 한 번에 교체
```

[`slotted-page`](../../exercises/slotted-page/)는 실패한 update와 insert 뒤 `serialize()` 결과가 이전과 같은지 검사합니다. 이 검사는 예외가 발생했다는 사실보다, 실패 후 page가 바뀌지 않았는지를 확인합니다.

## Compaction이 보존해야 할 값

Delete와 축소 update가 반복되면 빈 공간이 여러 위치에 흩어집니다. Compaction은 live record를 한쪽으로 다시 모으고 각 slot의 offset을 갱신합니다.

다음 값은 바뀌면 안 됩니다.

- live slot ID
- 각 slot이 가리키는 payload
- tombstone 여부
- slot directory 순서

다음 값은 새 배치에 맞게 갱신해야 합니다.

- 각 live slot의 byte offset
- record 영역의 시작 위치
- free-space 크기

실제 DBMS에서는 `page_lsn`, checksum과 transaction 정보도 함께 보존해야 합니다.

## 직렬화된 page는 신뢰하지 않고 읽습니다

메모리 객체를 그대로 기록하지 말고, byte 순서와 field 크기가 정해진 형식을 사용합니다.

```text
magic / version
slot count
free-space boundary
slot entries
record bytes
```

외부에서 읽은 byte를 page로 만들기 전에 최소한 다음을 확인해야 합니다.

- magic과 version이 맞는지
- header와 slot directory가 page 크기를 넘지 않는지
- directory 끝이 free-space boundary보다 뒤에 있지 않은지
- live slot의 `offset + length`가 page 범위를 넘지 않는지
- record 영역과 directory가 겹치지 않는지

손상된 offset을 그대로 사용하면 다른 record를 읽거나 page 범위 밖 byte를 참조하게 됩니다. [`slotted-page`](../../exercises/slotted-page/)의 `from_bytes()`는 이러한 값을 검증한 뒤에만 객체를 반환합니다.

## Heap file과 sorted file

### Heap file

빈 공간이 있는 page에 record를 넣습니다.

- 일반적인 insert가 단순합니다.
- 전체 scan은 page 순서로 수행할 수 있습니다.
- 특정 key를 찾으려면 index가 없을 때 많은 page를 읽습니다.
- update와 delete가 잦은 table에 쓰기 쉽습니다.

Free-space map을 사용하면 모든 page를 열어 보지 않고 insert 후보를 고를 수 있습니다.

### Sorted file

특정 key 순서를 유지하며 record를 저장합니다.

- 범위 scan과 연속 읽기에 유리합니다.
- 중간 insert 시 page split이나 record 이동이 필요합니다.
- 정렬 key가 바뀌는 update는 record를 다시 배치해야 합니다.

실제 관계형 DBMS는 table heap과 별도의 B+ tree index를 조합하는 경우가 많습니다. Heap은 record 저장을 맡고 index는 key 순서와 탐색 위치를 제공합니다.

## RID가 다른 구성 요소와 연결되는 지점

```text
B+ tree leaf: key → RID
RID: page_id + slot_id
buffer pool: page_id → frame
slotted page: slot_id → record bytes
transaction: 어느 record version을 볼 수 있는지 판단
```

Slot ID가 바뀌면 index가 다른 record를 가리킵니다. Dirty page를 기록하지 않고 frame을 재사용하면 RID는 남아 있는데 record가 사라질 수 있습니다. Recovery가 `page_lsn`을 잘못 다루면 오래된 record를 다시 적용할 수 있습니다.

따라서 page layout은 byte 배열 하나의 문제가 아니라 index, buffer pool과 복구가 모두 의존하는 저장 형식입니다.

## 연결 exercise

이 문서를 읽은 뒤 [`slotted-page`](../../exercises/slotted-page/)를 수행합니다.

Exercise에서는 다음을 구현하고 검사합니다.

- 가변 길이 record insert와 read
- tombstone을 남기는 delete
- slot ID를 유지하는 update와 compaction
- 공간 부족 시 기존 page 보존
- 직렬화 왕복
- 손상된 page 정보 거부

## 완료 기준

다음 질문에 그림과 코드로 답할 수 있어야 합니다.

1. Slot directory와 record byte가 반대 방향으로 자라는 이유는 무엇입니까?
2. Byte offset 대신 `(page_id, slot_id)`를 사용하는 이유는 무엇입니까?
3. Delete할 때 뒤 slot 번호를 당기면 어떤 참조가 깨집니까?
4. 공간이 부족한 update가 기존 record를 보존하려면 어떤 순서로 처리해야 합니까?
5. Compaction 전후에 반드시 같은 값은 무엇입니까?
6. Heap file과 sorted file은 읽기와 쓰기에서 어떤 비용 차이가 있습니까?
