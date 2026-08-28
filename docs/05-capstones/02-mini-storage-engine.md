# 미니 저장 엔진

## 문서의 역할

이 문서는 page, buffer pool, index와 WAL을 하나의 작은 key-value 저장 엔진에서 다시 확인하는 선택 자료입니다. 필수 전용 exercise를 대체하지 않습니다.

연결하는 내용은 다음과 같습니다.

- 가변 길이 record를 slotted page에 저장합니다.
- `(page_id, slot_id)`를 index의 RID로 사용합니다.
- 고정된 수의 frame에서 page를 pin하고 dirty page를 flush합니다.
- page write 전에 해당 LSN까지 WAL이 durable한지 확인합니다.
- 정렬된 leaf index로 point lookup과 range scan을 수행합니다.
- commit된 insert만 crash 뒤 다시 적용합니다.
- recovery 뒤 heap을 읽어 index를 다시 만듭니다.

선택 exercise인 [`mini-storage-engine`](../../exercises/mini-storage-engine/)을 수행할 때 이 문서를 사용합니다.

## 구현 범위

포함하는 기능:

```text
고정 page 크기
가변 길이 value
append-only record insert
stable RID
작은 Clock buffer pool
단일 process
한 호출당 한 transaction인 auto-commit
ordered leaf index
append-only WAL
crash recovery
```

포함하지 않는 기능:

- SQL parser와 optimizer
- 여러 process의 lock manager
- 완전한 MVCC
- update와 delete
- WAL truncation
- replica와 distributed transaction
- production checksum, encryption과 compression

기능을 제한한 이유는 각 구성 요소가 바꾸는 상태와 crash 뒤 남는 값을 테스트하기 위해서입니다.

## `insert(key, value)` 처리 순서

완성된 구현은 다음 순서를 사용합니다.

```text
1. index에서 duplicate key를 확인합니다.
2. value가 들어갈 page를 찾습니다.
3. 새 transaction ID를 할당합니다.
4. INSERT WAL record를 추가합니다.
5. 대상 page를 fetch하고 pin합니다.
6. page에 record를 넣고 page_lsn을 INSERT LSN으로 갱신합니다.
7. dirty 상태로 unpin합니다.
8. COMMIT WAL record를 추가하고 flush합니다.
9. key와 RID를 index에 공개합니다.
```

각 단계 사이에서 process가 종료될 수 있습니다. Commit WAL이 durable하지 않다면 recovery 결과에 key가 나타나면 안 됩니다. Commit WAL이 durable하지만 data page가 이전 상태라면 recovery가 record를 다시 만들어야 합니다.

## `get(key)` 처리 순서

```text
index에서 RID를 찾습니다.
→ page_id를 buffer pool에서 fetch합니다.
→ slot_id로 record를 읽습니다.
→ record의 key가 요청 key와 같은지 확인합니다.
→ page를 unpin합니다.
```

Index가 다른 key의 RID를 가리키면 조용히 잘못된 value를 반환하지 않고 오류로 처리해야 합니다.

## Slotted page가 관리하는 값

Slotted page는 다음을 저장합니다.

- `page_id`
- `page_lsn`
- record byte
- slot의 offset과 length
- free-space 시작 위치

제공하는 작업:

- non-empty `bytes` record insert
- slot ID로 read
- key로 현재 slot 검색
- page byte 직렬화와 역직렬화

Page class는 다음을 결정하지 않습니다.

- 언제 disk에 기록할지
- transaction이 commit되었는지
- key가 전체 engine에서 유일한지

## Disk manager가 관리하는 값

Disk manager는 page ID별 직렬화 byte를 보관합니다.

- 새 page ID를 할당합니다.
- page byte를 읽어 `SlottedPage`로 만듭니다.
- 완성된 page byte를 기록합니다.
- write event를 관찰할 수 있게 남깁니다.

WAL의 durable 위치는 buffer pool이 확인하므로 disk manager는 전달받은 page를 그대로 기록합니다.

## Buffer pool이 관리하는 값

각 frame에는 다음 정보가 있습니다.

```text
resident page
pin_count
dirty
referenced
```

Buffer pool은 다음을 수행합니다.

- resident hit에서 같은 page를 pin합니다.
- Clock으로 unpinned victim을 고릅니다.
- dirty frame을 재사용하기 전에 flush합니다.
- `page_lsn <= log.flushed_lsn`인지 확인합니다.
- write가 성공한 뒤 dirty bit를 지웁니다.

Page table과 frame이 서로 다른 page ID를 가리키면 안 됩니다. Pinned frame도 victim으로 고르면 안 됩니다.

## WAL manager가 관리하는 값

WAL record는 다음 형태입니다.

```text
LSN
transaction ID
kind: INSERT / COMMIT
page ID
key
value
```

WAL manager는 LSN을 단조 증가시키고 flush된 마지막 LSN을 기록합니다. Durable record만 recovery 입력으로 사용합니다.

Recovery 뒤 새 transaction ID가 과거 durable WAL의 최대 ID보다 커야 합니다. 1부터 다시 시작하면 과거 `COMMIT` record가 새 미완료 `INSERT`를 commit된 transaction으로 오인하게 만들 수 있습니다.

## Ordered leaf index

Exercise의 index는 정렬된 leaf 배열입니다.

- unique integer key를 저장합니다.
- key를 RID에 연결합니다.
- leaf가 capacity를 넘으면 배열을 둘로 나눕니다.
- point lookup과 범위 조회를 제공합니다.

Root, internal node와 separator를 구현하지 않으므로 완전한 B+ tree라고 부르지 않습니다. B+ tree 자체는 필수 exercise인 [`bplus-tree`](../../exercises/bplus-tree/)에서 다룹니다.

## Heap과 index를 함께 맞춥니다

다음 사이에서 crash가 날 수 있습니다.

```text
heap insert 완료
→ index insert 전
```

Exercise는 heap과 index 변경을 모두 WAL에 따로 기록하지 않습니다. 대신 durable WAL을 기준으로 committed record를 heap page에 다시 만들고, recovery가 끝난 뒤 모든 page를 읽어 index를 재구성합니다.

장점:

- recovery 규칙이 단순합니다.
- stale RID를 index replay로 복구할 필요가 없습니다.

비용과 제한:

- recovery 때 heap 전체를 읽어야 합니다.
- WAL을 source로 사용하므로 log truncation을 지원하지 않습니다.
- update와 delete의 version 처리가 없습니다.

## Crash 뒤 복구

Recovery는 다음 순서로 진행합니다.

```text
1. durable WAL에서 COMMIT transaction ID를 모읍니다.
2. WAL에 등장한 page ID를 기준으로 빈 heap page를 만듭니다.
3. durable하고 commit된 INSERT만 LSN 순서로 다시 적용합니다.
4. page_lsn을 적용한 record LSN 이상으로 갱신합니다.
5. dirty page를 flush합니다.
6. heap page를 읽어 index를 다시 만듭니다.
7. 다음 transaction ID를 durable 최대값 + 1로 설정합니다.
```

이 구현은 기존 disk page를 그대로 믿지 않고 committed WAL로 heap을 다시 만듭니다. 따라서 disk까지 도달한 uncommitted insert도 최종 결과에서 제거됩니다.

## 검사할 crash 위치

- INSERT WAL이 durable하지 않은 상태
- INSERT WAL만 durable한 상태
- Uncommitted page가 disk에 기록된 상태
- COMMIT WAL은 durable하지만 data page를 flush하지 않은 상태
- recovery를 한 번 완료한 상태에서 같은 WAL로 다시 recovery
- recovery 뒤 새 transaction의 INSERT만 durable하고 다시 crash한 상태

각 경우에 다음을 확인합니다.

- commit된 key는 조회됩니다.
- commit되지 않은 key는 조회되지 않습니다.
- 같은 WAL로 반복 recovery해도 page byte가 같습니다.
- index RID가 실제 record를 가리킵니다.
- 새 transaction ID가 이전 ID와 겹치지 않습니다.

## 주요 불변식

### Page

```text
header + slot directory + records <= page size
slot은 page 범위 안을 가리킵니다.
record 영역과 directory가 겹치지 않습니다.
```

### Buffer pool

```text
frame 하나에는 page 하나만 있습니다.
page table과 frame의 page ID가 같습니다.
pin_count는 음수가 아닙니다.
pinned frame은 victim이 아닙니다.
dirty page를 쓰기 전에 WAL이 page_lsn까지 flush되어 있습니다.
```

### Index

```text
key는 정렬되어 있습니다.
같은 key를 두 번 저장하지 않습니다.
모든 RID가 존재하는 record를 가리킵니다.
모든 live key가 index에 있습니다.
```

### Recovery

```text
commit된 insert를 포함합니다.
commit되지 않은 insert를 제외합니다.
반복 실행해도 결과가 같습니다.
새 transaction ID가 durable history와 겹치지 않습니다.
```

## 선택 계측

구현을 바꾸지 않고 다음 counter를 추가할 수 있습니다.

- page read와 write 수
- buffer hit와 miss 수
- eviction과 dirty flush 수
- WAL append/flush byte
- index comparison 수
- recovery가 다시 적용한 record 수

Page 크기, frame 수와 접근 순서를 바꾸어 counter 차이를 설명할 수 있습니다. 이 결과를 실제 DBMS 성능으로 일반화하면 안 됩니다.

## 권장 진행 순서

```text
slotted page와 직렬화
→ disk manager
→ WAL record와 durable 위치
→ buffer pool과 Clock
→ ordered leaf index
→ engine 조립
→ insert/get/range
→ checkpoint
→ recovery와 transaction ID 재개
→ crash 위치별 test
```

한 번에 coordinator 전체를 작성하기보다 각 구성 요소의 test를 통과한 뒤 연결하는 편이 실패 원인을 찾기 쉽습니다.

## 완료 기준

다음 요청을 코드에서 끝까지 추적할 수 있어야 합니다.

```text
insert(42, bytes)
→ 어떤 WAL record가 생깁니까?
→ 어느 page와 slot이 바뀝니까?
→ frame의 pin과 dirty 값은 어떻게 바뀝니까?
→ index에는 어떤 RID가 들어갑니까?
→ commit 성공 전에 무엇이 flush되어야 합니까?
→ data page flush 전 crash하면 어떻게 복구합니까?
```

그리고 다음을 test로 확인할 수 있어야 합니다.

- 직렬화 왕복 뒤 RID 유지
- pinned frame 교체 금지
- WAL-before-data
- duplicate key 거부
- committed insert 복구
- uncommitted insert 제거
- 반복 recovery
- heap과 index의 일치
