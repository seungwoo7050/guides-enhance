# Clock Buffer Pool

정해진 수의 frame에 고정 크기 page를 올려 두는 메모리 기반 buffer pool입니다. 같은 page를 다시 요청하면 resident frame을 재사용하고, Clock second-chance 방식으로 교체할 frame을 고릅니다. `pin_count`, dirty 상태, page table과 disk write 순서를 직접 확인할 수 있습니다.

## 주요 기능

- 고정 크기 page 할당과 disk read/write 횟수 기록
- cache hit 시 같은 `bytearray` 반환
- pin된 frame 교체 금지
- referenced bit를 사용하는 Clock second chance
- dirty victim을 먼저 기록한 뒤 mapping 교체
- flush 성공 전까지 유지되는 dirty 상태
- 없는 page를 읽으려 할 때 기존 resident mapping 보존

## 구성

`DiskManager`는 page_id와 고정 크기 page bytes를 보관합니다. `BufferPool`은 `Frame` 배열, `page_table`과 Clock hand를 관리합니다. `fetch()`가 반환한 page는 호출자가 `unpin()`할 때까지 교체할 수 없습니다. Page를 수정했다면 `unpin(page_id, dirty=True)`로 알려야 합니다.

## 설치와 사용

Python 3.11 이상이 필요합니다.

```bash
python3 -m pip install -e .
```

```python
from buffer_pool import BufferPool, DiskManager

disk = DiskManager(page_size=64)
page_id = disk.allocate(b"initial")
pool = BufferPool(disk, capacity=2)

page = pool.fetch(page_id)
page[:7] = b"changed"
pool.unpin(page_id, dirty=True)
pool.flush(page_id)

assert disk.pages[page_id][:7] == b"changed"
```

## 테스트

```bash
make test
```

테스트는 cache hit, Clock second chance, pinned frame 제외, dirty eviction, 이중 unpin 거부와 실패 시 기존 mapping 보존을 확인합니다.

## 설계에서 확인할 점

- 존재하지 않는 page는 victim을 고르기 전에 거부합니다. 잘못된 read 때문에 정상 resident page가 밀려나면 안 됩니다.
- Dirty victim은 disk write가 성공한 뒤에만 page table에서 제거합니다. Write가 실패하면 기존 page_id와 bytes를 그대로 다시 사용할 수 있어야 합니다.
- Dirty 상태는 한 번 설정되면 flush가 성공할 때까지 유지합니다. 여러 호출자가 같은 page를 pin했을 때 나중의 clean `unpin()`이 앞선 수정을 지우면 안 됩니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | 고정 크기 page 저장과 I/O 횟수 기록 | `src/buffer_pool.py` · `DiskManager` |
| 2 | frame과 page table의 resident mapping | `src/buffer_pool.py` · `Frame`, `BufferPool.__init__` |
| 3 | cache hit와 실패 시 기존 mapping 보존 | `src/buffer_pool.py` · `fetch` |
| 4 | Clock second-chance 교체 | `src/buffer_pool.py` · `_choose_victim` |
| 5 | pin 반환과 dirty 유지 | `src/buffer_pool.py` · `unpin` |
| 6 | dirty page의 disk flush | `src/buffer_pool.py` · `flush`, `flush_all` |
| 7 | buffer pool 상태 전이 검증 | `tests/test_buffer_pool.py` · `BufferPoolTests` |

## 범위와 제한

이 구현은 단일 thread에서 동작하는 메모리 시뮬레이터입니다. 실제 file descriptor, 비동기 I/O, latch, WAL 순서, prefetch와 background writer는 포함하지 않습니다.
