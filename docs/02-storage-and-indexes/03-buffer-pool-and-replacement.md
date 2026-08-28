# Buffer pool과 page 교체

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 합니다.

- buffer pool이 disk page와 memory frame의 대응 관계를 관리하는 이유
- page table, pin count, dirty bit와 reference bit의 역할
- fetch, unpin, flush와 eviction의 상태 변화
- Clock이 최근 사용한 frame에 두 번째 기회를 주는 방법
- dirty victim을 기록하고 frame을 재사용하는 안전한 순서
- hit ratio만으로 buffer pool 동작을 평가하면 안 되는 이유

## Buffer pool은 page 수명을 관리합니다

DBMS는 모든 page를 memory에 둘 수 없습니다. Buffer pool은 제한된 frame에 필요한 page를 올리고, 다시 사용할 page는 남기며, 재사용할 frame을 고릅니다.

```text
disk page_id
    ↓ fetch
page table: page_id → frame_id
    ↓
frame: page bytes + pin_count + dirty + referenced
```

일반적인 key-value cache와 다른 점은 다음과 같습니다.

- 실행 중인 operator가 page pointer를 사용하고 있으므로 해당 frame을 즉시 바꿀 수 없습니다.
- memory에서 수정한 dirty page는 기록하지 않고 버릴 수 없습니다.
- page를 기록하기 전에 해당 변경의 WAL이 durable한지 확인해야 합니다.
- 여러 호출자가 같은 resident page를 동시에 사용할 수 있습니다.
- flush와 eviction은 서로 다른 작업입니다.

## Frame에 필요한 정보

### `page_id`

현재 frame에 들어 있는 disk page를 나타냅니다. 빈 frame에는 page가 없습니다.

### `pin_count`

현재 page를 사용 중인 호출자 수입니다.

```text
fetch   → pin_count + 1
unpin   → pin_count - 1
```

`pin_count > 0`인 frame을 다른 page로 바꾸면 호출자가 사용하던 byte 배열의 내용이 갑자기 달라집니다. 따라서 pinned frame은 victim이 될 수 없습니다.

### `dirty`

Memory의 page byte가 disk보다 최신인지 나타냅니다. 한 호출자가 `dirty=true`로 반환한 뒤 다른 호출자가 수정 없이 반환해도 dirty 상태를 지우면 안 됩니다.

```text
frame.dirty = frame.dirty OR caller_dirty
```

Disk write가 성공한 뒤에만 false로 바꿉니다.

### `referenced`

Clock이 최근 접근한 frame에 두 번째 기회를 줄 때 사용합니다. Fetch hit와 새 page 적재 시 true로 설정합니다.

## Cache hit 처리

Page가 이미 resident라면 다음만 수행합니다.

1. page table에서 frame을 찾습니다.
2. `pin_count`를 증가시킵니다.
3. `referenced`를 true로 설정합니다.
4. 같은 page 객체를 반환합니다.

같은 page를 다시 disk에서 읽으면 안 됩니다. [`clock-buffer-pool`](../../exercises/clock-buffer-pool/)은 첫 번째와 두 번째 fetch가 같은 객체를 반환하고 disk read count가 늘지 않는지 검사합니다.

## Cache miss 처리 순서

Page가 resident가 아니라면 다음 순서가 필요합니다.

1. 빈 frame을 찾거나 victim을 고릅니다.
2. victim이 dirty이면 기존 `page_id`와 byte를 disk에 기록합니다.
3. 기록이 성공한 뒤 이전 page table entry를 제거합니다.
4. 새 page를 disk에서 읽습니다.
5. frame byte와 metadata를 새 page 값으로 설정합니다.
6. page table에 새 mapping을 등록합니다.
7. `pin_count=1`, `dirty=false`, `referenced=true`로 시작합니다.

이전 mapping을 먼저 지운 뒤 dirty write가 실패하면 최신 byte가 어느 frame에 있는지 찾기 어려워집니다. 반대로 새 mapping을 먼저 등록하고 disk read가 실패하면 page table이 실제로 적재되지 않은 page를 가리킬 수 있습니다.

실제 구현에서는 실패 시 기존 frame과 page table이 어떤 상태로 남는지 테스트해야 합니다.

## Pin은 pointer의 유효 기간을 나타냅니다

Pin은 page의 중요도를 나타내는 점수가 아닙니다. 호출자가 page byte를 사용하는 동안 frame을 재사용하지 말라는 표시입니다.

자주 발생하는 오류는 다음과 같습니다.

- fetch 뒤 예외가 발생해 unpin하지 않습니다.
- fetch 한 번에 unpin을 두 번 호출합니다.
- byte를 수정했는데 `dirty=false`로 반환합니다.
- page 객체를 보관한 채 먼저 unpin합니다.
- 중첩된 함수가 누가 unpin할지 정하지 않습니다.

언어가 지원한다면 context manager나 RAII object로 수명을 표현하는 편이 안전합니다.

```text
with buffer_pool.page(page_id, write=True) as page:
    modify(page)
# scope가 끝나면 dirty 상태와 함께 unpin
```

## Clock replacement

Clock은 frame을 원형으로 순회합니다.

```text
if pin_count > 0:
    건너뜁니다.
else if referenced:
    referenced = false
    이번 순회에서는 남깁니다.
else:
    victim으로 선택합니다.
```

최근 사용한 unpinned frame은 첫 번째 순회에서 reference bit만 지우고, 다시 만났을 때 아직 재참조되지 않았다면 victim이 됩니다. 정확한 LRU 순서를 관리하는 비용 없이 최근 사용 여부를 근사합니다.

### 모든 frame이 pin된 경우

무한히 순회하면 안 됩니다. 명시적인 오류를 반환하거나 대기해야 합니다.

```text
BufferPoolFull
```

이 오류는 capacity가 작은 경우뿐 아니라 unpin 누락을 뜻할 수도 있습니다. 진단하려면 frame별 pin count, page ID와 pin 유지 시간을 기록해야 합니다.

### 모든 unpinned frame이 referenced인 경우

첫 순회에서 bit를 지우고 두 번째 순회에서 하나를 선택할 수 있어야 합니다. 한 바퀴만 보고 곧바로 실패하면 최근 참조된 frame밖에 없는 정상 상태를 처리하지 못합니다.

## Dirty page를 기록하는 순서

Dirty page를 disk에 쓰기 전에 다음 정보를 확인합니다.

- frame이 가리키는 `page_id`
- memory의 최신 page byte
- `page_lsn`
- WAL이 어디까지 flush되었는지

WAL을 사용하는 경우 다음 순서를 지켜야 합니다.

```text
log record append
→ log flush through page_lsn
→ data page write
```

Data page가 먼저 disk에 도달하면 crash 뒤 해당 변경을 redo하거나 undo할 durable log가 없을 수 있습니다. 자세한 내용은 [`MVCC, WAL과 crash recovery`](../03-transactions-and-recovery/02-mvcc-wal-and-recovery.md)에서 다룹니다.

Disk write가 실패하면 dirty bit를 유지해야 합니다. 성공 확인 전에 false로 바꾸면 최신 변경을 잃습니다.

## Flush와 eviction은 다릅니다

- **flush**: frame은 그대로 두고 dirty byte를 disk에 기록합니다.
- **eviction**: frame을 다른 page에 사용합니다.

Flush한 page는 resident 상태로 남아 다음 fetch에서 hit할 수 있습니다. Checkpoint와 background writer는 page를 내보내지 않고 미리 기록해 eviction 지연을 줄일 수 있습니다.

## 새 page 할당은 두 작업입니다

새 page를 만드는 과정에는 서로 다른 작업이 있습니다.

```text
disk manager: 새 page_id와 빈 page를 생성합니다.
buffer pool: 그 page를 frame에 적재하고 pin합니다.
```

Disk allocation은 성공했는데 frame을 얻지 못했다면 생성한 page를 남길지 회수할지 정해야 합니다. 반대로 frame을 먼저 비웠는데 allocation이 실패하면 이전 page를 잃으면 안 됩니다.

[`clock-buffer-pool`](../../exercises/clock-buffer-pool/)은 기존 page fetch와 eviction에 집중하고, 선택 프로젝트인 [`mini-storage-engine`](../../exercises/mini-storage-engine/)이 allocation과 buffer 사용을 함께 다룹니다.

## 큰 sequential scan은 별도 처리가 필요할 수 있습니다

Table 전체를 한 번 읽는 scan은 곧 다시 쓰지 않을 page로 buffer를 채워 자주 사용하는 page를 밀어낼 수 있습니다. 실제 DBMS는 다음 방법을 사용할 수 있습니다.

- sequential scan 전용 작은 ring
- read-ahead와 prefetch
- bulk read용 접근 방식
- hot page와 streaming page의 replacement 처리 분리

모든 read를 같은 방법으로 cache하는 것이 항상 최선은 아닙니다.

## Hit ratio만으로 판단하지 않습니다

높은 hit ratio가 빠른 실행을 뜻하지는 않습니다.

- 느린 query가 같은 page를 반복해서 읽어 hit 수를 늘릴 수 있습니다.
- dirty flush가 한 시점에 몰려 write 지연이 커질 수 있습니다.
- 오래 pin된 frame 때문에 대기해도 최종 fetch는 hit로 기록될 수 있습니다.
- sequential scan은 낮은 hit ratio여도 가장 적절한 실행일 수 있습니다.

다음 항목을 함께 봅니다.

```text
page read / write 수
cache hit / miss
flush latency
dirty frame 수
pin wait 시간
eviction 수
checkpoint write 양
```

## 최소 불변식

Buffer pool 구현에서는 다음을 확인해야 합니다.

- page table entry 하나는 정확히 한 frame을 가리킵니다.
- resident frame의 `page_id`와 page table key가 같습니다.
- `pin_count`는 음수가 될 수 없습니다.
- pinned frame은 victim이 될 수 없습니다.
- dirty page는 disk write 성공 전까지 dirty입니다.
- 빈 frame은 page table에 등록되지 않습니다.
- eviction 뒤 이전 page mapping이 남지 않습니다.

이 조건이 깨지면 서로 다른 page ID가 같은 byte 배열을 가리키거나 최신 변경이 조용히 사라집니다.

## 연결 exercise

이 문서를 읽은 뒤 [`clock-buffer-pool`](../../exercises/clock-buffer-pool/)을 수행합니다.

Exercise에서는 다음을 확인합니다.

- 같은 page의 cache hit
- 여러 pin과 dirty 상태 유지
- pinned frame 교체 금지
- Clock second chance
- dirty victim의 write-before-remap
- double unpin 거부

## 완료 기준

다음 상황에서 page table, frame metadata와 disk 상태가 어떻게 바뀌는지 그릴 수 있어야 합니다.

1. Clean page cache miss
2. Dirty victim을 사용하는 cache miss
3. 같은 page를 두 호출자가 fetch한 뒤 순서대로 unpin
4. 모든 frame이 pin되어 새 page를 가져오지 못하는 경우
5. Disk write가 실패한 뒤 dirty bit를 유지하는 경우
6. WAL이 `page_lsn`까지 flush되지 않은 상태에서 flush를 시도하는 경우
