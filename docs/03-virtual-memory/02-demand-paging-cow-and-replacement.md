# 요구 페이징, COW와 page replacement

## 학습 목표

- mapping 생성과 실제 frame 할당 시점을 구분합니다.
- COW 공유, write fault, private copy와 refcount 변화를 추적합니다.
- FIFO, LRU와 Clock을 같은 reference string으로 비교합니다.

## demand paging

실행 파일과 mapping의 모든 page를 process 시작 시점에 읽지 않고, 실제 접근할 때 준비할 수 있습니다.

```text
mapping 존재, PTE not-present
→ 첫 접근 fault
→ 빈 frame 확보
→ anonymous면 zero-fill
→ file-backed면 해당 offset 읽기
→ PTE 갱신
→ faulting instruction 재시도
```

장점은 다음과 같습니다.

- 사용하지 않는 code와 data를 읽지 않습니다.
- process 시작 시간과 physical memory 사용량을 줄일 수 있습니다.
- 같은 read-only file page를 여러 process가 공유할 수 있습니다.

비용도 있습니다.

- 첫 접근이 느려집니다.
- storage I/O가 필요하면 thread가 block됩니다.
- memory pressure에서 frame 확보가 실패할 수 있습니다.
- working set이 memory보다 크면 반복 fault가 생길 수 있습니다.

## frame에 연결되는 상태

frame 하나에는 다음 정보가 필요할 수 있습니다.

```text
어떤 mapping이 참조하는가
anonymous 또는 file-backed인가
clean 또는 dirty인가
최근 접근됐는가
writeback 중인가
DMA 등으로 pinned됐는가
COW 공유 중인가
reference count가 얼마인가
```

frame을 다른 용도로 재사용하려면 이전 mapping이 더 이상 접근할 수 없어야 합니다.

```text
참조 중인 frame을 free list에 두지 않습니다.
pinned 또는 I/O 중인 frame은 교체하지 않습니다.
dirty data를 backing에 보존하기 전에 재사용하지 않습니다.
PTE 변경과 stale translation 정리 뒤에만 frame을 재사용합니다.
```

## COW 상태 변화

### fork 직후

```text
부모 PTE ─┐
          ├→ frame F, refcount=2
자식 PTE ─┘

두 PTE는 COW이며 일반 write를 허용하지 않습니다.
```

### 자식의 첫 write

```text
1. mapping과 COW 표시를 확인합니다.
2. 새 frame N을 확보합니다.
3. F의 내용을 N으로 복사합니다.
4. 자식 PTE를 N의 writable mapping으로 바꿉니다.
5. F의 refcount를 줄입니다.
6. stale translation을 없앱니다.
7. write 명령을 다시 실행합니다.
```

기존 frame의 refcount가 이미 1이면 복사하지 않고 같은 frame을 writable로 바꿀 수 있습니다. 다른 snapshot 또는 참조가 없는지 먼저 확인해야 합니다.

### 동시에 발생한 COW fault

같은 mapping에 여러 thread가 동시에 write하면 다음 문제가 생길 수 있습니다.

- private frame을 두 번 할당합니다.
- refcount를 두 번 줄입니다.
- 복사 중인 frame을 다른 경로가 재사용합니다.
- stale writable translation이 shared frame을 바꿉니다.

실제 구현에서는 mapping lock, page lock과 재시도 규칙이 필요합니다. `kernel-model`은 단일 thread로 실행하지만 최종 PTE와 refcount 불변식은 검사합니다.

## mapping 유형별 공유 방식

| mapping | 일반적인 처리 |
| --- | --- |
| read-only file-backed | 같은 page cache frame 공유 가능 |
| private file-backed | read는 공유하고 write 시 private COW 가능 |
| shared file-backed | write가 공유 page cache를 변경 |
| anonymous private | fork 뒤 COW 공유 가능 |
| explicit shared memory | 같은 frame 변경을 보며 별도 동기화 필요 |

frame을 공유한다는 사실만으로 atomicity와 visibility가 보장되지는 않습니다. 공유 memory를 바꾸는 규칙은 동시성 문서의 원칙을 따릅니다.

## memory pressure와 reclaim

빈 frame이 부족하면 다음 후보를 검토합니다.

```text
clean file-backed page
→ backing file에서 다시 읽을 수 있으므로 제거하기 쉽습니다.

dirty file-backed page
→ writeback이 끝난 뒤 제거합니다.

anonymous page
→ swap 또는 compressed backing에 저장하거나 유지합니다.

page cache
→ 최근 사용 여부, dirty와 writeback 상태를 확인합니다.

pinned page
→ DMA 또는 kernel 작업이 끝날 때까지 제거하지 않습니다.
```

process memory와 page cache는 같은 physical memory를 두고 경쟁할 수 있습니다.

## replacement 정책

### FIFO

가장 먼저 들어온 page를 먼저 내보냅니다.

```text
저장 상태: resident 순서
장점: 구현이 단순합니다.
약점: 최근 자주 쓴 page도 오래됐다는 이유로 제거합니다.
```

frame 수를 늘렸는데 fault가 증가하는 Belady anomaly가 생길 수 있습니다.

### LRU

가장 오래 사용하지 않은 page를 내보냅니다.

```text
저장 상태: 최근 접근 시점 또는 순서
장점: temporal locality를 반영합니다.
약점: 모든 접근을 정확히 기록하는 비용이 큽니다.
```

실제 kernel은 accessed bit와 여러 list를 사용해 근사할 수 있습니다.

### Clock

원형 list와 reference bit를 사용합니다.

```text
reference=1
→ bit를 0으로 바꾸고 다음 후보를 확인합니다.

reference=0
→ 해당 page를 교체합니다.
```

정확한 LRU보다 기록해야 할 상태가 적습니다.

## trace로 비교합니다

다음 access pattern은 서로 다른 결과를 만듭니다.

- 순차 scan
- 작은 hot set 반복
- 두 working set 교대
- 큰 random access
- 한 번만 읽는 streaming

같은 reference string과 frame capacity를 사용해야 정책 차이를 비교할 수 있습니다.

```sh
cd exercises/kernel-model
python3 kernel-model.py replacement examples/replacement.json
```

출력의 `faults`, `evictions`와 최종 `frames`를 비교합니다.

## thrashing

working set이 resident capacity보다 크면 계산보다 page-in과 eviction에 더 많은 시간을 쓸 수 있습니다.

```text
필요한 page fault
→ 다른 hot page 제거
→ 제거한 page를 곧 다시 접근
→ 다시 fault
```

fault 수만 많다고 바로 thrashing은 아닙니다. CPU 사용률, I/O 대기, working set과 reclaim 반복을 함께 확인합니다.

완화 방법은 다음과 같습니다.

- process별 resident set 조정
- 동시에 실행하는 process 수 감소
- page-fault frequency에 따른 frame 재배분
- workload의 locality 개선
- sequential scan을 별도로 식별하여 cache 오염 완화

## dirty page와 writeback

교체할 page가 dirty라면 backing에 값을 기록해야 합니다. writeback 중인 page를 곧바로 재사용하면 data를 잃을 수 있습니다.

```text
dirty page 선택
→ writeback 요청
→ I/O 완료 대기
→ PTE와 translation 정리
→ frame 재사용
```

writeback이 실패하면 page를 유지할지, process에 오류를 전달할지, filesystem을 read-only로 바꿀지 등 추가 처리가 필요합니다.

## 연결 실습

```sh
cd exercises/kernel-model
python3 -m unittest tests.test_models.PagingTests -v
python3 kernel-model.py memory examples/memory-cow.json
python3 kernel-model.py replacement examples/replacement.json
```

invalid snapshot 테스트는 같은 frame을 여러 process가 공유하면서 일반 writable 상태로 둔 경우를 거부합니다.

## 완료 기준

- demand paging이 frame 할당을 미루는 과정을 설명할 수 있습니다.
- COW write에서 PTE와 refcount가 어떻게 바뀌는지 추적할 수 있습니다.
- shared frame이 일반 writable 상태이면 안 되는 이유를 설명할 수 있습니다.
- FIFO, LRU와 Clock이 저장하는 상태를 구분할 수 있습니다.
- dirty, pinned와 writeback 중인 page를 즉시 교체하면 안 되는 이유를 설명할 수 있습니다.

## 잘못된 이해

- COW가 어떤 경우에도 memory copy를 하지 않는다고 생각합니다.
- frame refcount만 줄이면 stale mapping과 TLB도 자동으로 사라진다고 생각합니다.
- LRU가 모든 workload에서 가장 적은 fault를 보장한다고 생각합니다.
- fault 수가 많으면 언제나 thrashing이라고 판단합니다.

## 자기 설명

- COW frame의 refcount가 1일 때 copy를 생략할 수 있는 이유는 무엇입니까?
- pinned page가 replacement 후보가 될 수 없는 이유는 무엇입니까?
- FIFO에서 frame 수가 늘어도 fault가 증가할 수 있는 이유는 무엇입니까?
