# Mini Storage Engine

가변 길이 key-value record를 slotted heap page에 저장하고 Clock buffer pool, 정렬된 leaf index와 write-ahead log를 연결한 소형 Python 저장 엔진입니다. 유일한 정수 key의 auto-commit insert, 단일 key 조회, 범위 조회, checkpoint와 crash recovery를 제공합니다.

## 주요 기능

- `(page_id, slot_id)` RID를 사용하는 append-only slotted heap
- 고정 크기 page 할당과 binary 직렬화 왕복
- pin과 dirty 상태를 관리하는 Clock buffer pool
- `page_lsn`까지 WAL이 durable해야 하는 page write
- 분할 가능한 정렬 leaf 배열 index
- WAL을 먼저 기록하는 auto-commit insert
- COMMIT record가 있는 INSERT만 다시 적용하는 crash recovery
- disk에 기록된 미완료 record 제거
- 반복 recovery 결과 유지와 다음 txid 재개

## 구성

`SlottedPage`가 page bytes와 slot 기반 RID를 관리하고, `DiskManager`가 직렬화된 page를 보관합니다. `BufferPool`은 resident page, pin, dirty 상태와 Clock 교체를 관리합니다. `LogManager`는 `INSERT`와 `COMMIT` record, LSN과 `flushed_lsn`을 보관합니다. `OrderedLeafIndex`는 key를 RID에 연결하며 복구 뒤 durable heap을 읽어 다시 만듭니다.

## 설치와 사용

Python 3.11 이상이 필요합니다.

```bash
python3 -m pip install -e .
```

```python
from mini_storage import DiskManager, MiniStorageEngine

disk = DiskManager(page_size=160)
engine = MiniStorageEngine(disk, buffer_capacity=2)

engine.insert(10, b"ten")
engine.insert(20, b"twenty")
assert engine.get(10) == b"ten"
assert engine.range(5, 20) == [(10, b"ten"), (20, b"twenty")]

engine.checkpoint()
recovered = MiniStorageEngine.recover(disk, engine.log.durable_records())
assert recovered.get(20) == b"twenty"
```

## 테스트

```bash
make test
```

테스트는 여러 page로의 증가, 중복 key 거부, 손상된 page 거부, WAL 선행 쓰기, 미완료 record 제거, 반복 recovery, txid 재개와 index RID 검증을 함께 수행합니다.

## 설계에서 확인할 점

- Insert 순서는 `INSERT WAL → page 변경과 page_lsn 갱신 → COMMIT WAL flush → index 등록`입니다. Index에 보이는 key에는 durable COMMIT record가 있어야 합니다.
- Index는 durable한 데이터가 아닙니다. 복구가 끝나면 heap page의 live RID를 순회해 다시 만듭니다.
- Recovery는 durable WAL 전체에서 heap page를 재구성합니다. 미완료 record를 제거하기는 쉽지만 WAL 일부를 버릴 수 없으므로 log truncation을 지원하지 않습니다.
- `OrderedLeafIndex`는 leaf 배열 분할과 범위 조회만 제공합니다. Root, internal node와 separator를 가진 완전한 B+ tree는 아닙니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | page, slot, record의 binary layout | `src/mini_storage.py` · `PAGE_HEADER`, `PAGE_SLOT`, `RECORD_HEADER` |
| 2 | page_id, page_lsn, bytes와 RID 관리 | `src/mini_storage.py` · `SlottedPage` |
| 2-1 | 검증 뒤 record 삽입 | `src/mini_storage.py` · `SlottedPage.insert` |
| 2-2 | page 직렬화와 외부 bytes 검증 | `src/mini_storage.py` · `SlottedPage.serialize`, `SlottedPage.from_bytes` |
| 3 | page_id 할당과 직렬화된 page I/O | `src/mini_storage.py` · `DiskManager` |
| 4 | append-only WAL과 LSN 관리 | `src/mini_storage.py` · `LogRecord`, `LogManager` |
| 5 | frame과 page table의 resident mapping | `src/mini_storage.py` · `Frame`, `BufferPool` |
| 5-1 | 실패 시 기존 mapping을 보존하는 fetch와 Clock 교체 | `src/mini_storage.py` · `BufferPool.fetch`, `BufferPool._victim` |
| 5-2 | WAL 조건을 확인하는 dirty page flush | `src/mini_storage.py` · `BufferPool._flush_frame` |
| 6 | 정렬 leaf 배열의 key와 RID 관리 | `src/mini_storage.py` · `OrderedLeafIndex` |
| 7 | 구성 요소 조합과 다음 txid 관리 | `src/mini_storage.py` · `MiniStorageEngine.__init__` |
| 7-1 | durable heap에서 index 재구성 | `src/mini_storage.py` · `_rebuild_index` |
| 7-2 | pin을 반환하며 삽입 page 선택 | `src/mini_storage.py` · `_choose_page` |
| 8 | WAL을 먼저 기록하는 auto-commit insert | `src/mini_storage.py` · `insert` |
| 9 | index 조회와 checkpoint | `src/mini_storage.py` · `get`, `range`, `checkpoint` |
| 10 | committed INSERT 재적용과 미완료 record 제거 | `src/mini_storage.py` · `recover` |
| 11 | 저장 엔진 구성 요소 통합 검증 | `tests/test_mini_storage.py` · `MiniStorageEngineTests` |

## 범위와 제한

이 구현은 단일 process와 단일 thread에서 동작하는 append-only 엔진입니다. Update와 delete, 완전한 B+ tree, latch, concurrent transaction, isolation, checkpoint metadata, log truncation, compensation log record와 운영용 ARIES는 포함하지 않습니다. Heap을 다시 만들려면 WAL 전체가 남아 있어야 합니다.
