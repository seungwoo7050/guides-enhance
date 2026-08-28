# 운영체제 원리 학습 경로

이 문서는 운영체제 기초 과정을 어떤 순서로 진행할지 정리합니다. 목표는 문서를 많이 읽는 것이 아니라, 운영체제가 관리하는 상태와 자원 수명을 이해하고 `kernel-model`의 실행 결과와 테스트로 확인하는 것입니다.

## 선행지식

다음 내용을 알고 있으면 바로 시작할 수 있습니다.

- 변수, 조건문, 반복문과 함수
- 배열, queue, set과 graph의 기본 사용법
- 프로그램 실행과 종료 상태 확인
- Python class, `dict`, `list`, module을 읽는 능력

C 관찰 예제를 실행하려면 C11과 POSIX 환경이 추가로 필요합니다. POSIX API의 사용법 자체는 C 또는 Unix 프로그래밍 가이드에서 다룹니다.

## 최종 역량

과정을 마치면 다음을 설명하고 검증할 수 있어야 합니다.

1. system call, exception, fault와 interrupt를 원인과 재개 방식으로 구분합니다.
2. process와 thread의 실행 상태 및 queue 위치를 추적합니다.
3. scheduling 정책을 동일한 workload와 metric으로 비교합니다.
4. race, atomicity, visibility와 ordering을 구분합니다.
5. condition wait, semaphore, cancellation과 wakeup에서 누가 어떤 상태를 바꾸는지 설명합니다.
6. deadlock, starvation, livelock과 priority inversion을 구분합니다.
7. mapping, page fault, COW와 frame refcount를 추적합니다.
8. cache에 보이는 값과 crash 뒤 복구되는 값을 구분합니다.
9. DMA request의 제출부터 결과 회수까지 buffer 수명을 추적합니다.
10. 모순된 snapshot을 거부하는 불변식을 작성할 수 있습니다.

## 필수 자료

### 문서

- `docs/01-boundary-and-execution/01-kernel-boundary-and-events.md`
- `docs/01-boundary-and-execution/02-processes-threads-and-context-switches.md`
- `docs/01-boundary-and-execution/03-cpu-scheduling.md`
- `docs/01-boundary-and-execution/04-blocking-wakeup-and-ipc.md`
- `docs/02-concurrency/01-races-atomicity-and-ordering.md`
- `docs/02-concurrency/02-synchronization-primitives.md`
- `docs/02-concurrency/03-deadlock-and-progress.md`
- `docs/03-virtual-memory/01-address-spaces-and-faults.md`
- `docs/03-virtual-memory/02-demand-paging-cow-and-replacement.md`
- `docs/04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md`
- `docs/04-storage-and-io/02-device-io-interrupts-and-dma.md`

### 실습

- `exercises/kernel-model/`

필수 실습은 하나지만, 내부에서는 실행 상태, 동기화, scheduling, deadlock, memory, filesystem과 device I/O를 순서대로 확인합니다.

## 단계별 진행 순서

### 1단계: 커널 진입과 실행 주체

먼저 다음 문서를 읽습니다.

1. [커널 경계와 사건](01-boundary-and-execution/01-kernel-boundary-and-events.md)
2. [프로세스, 스레드와 문맥 전환](01-boundary-and-execution/02-processes-threads-and-context-switches.md)
3. [블록, 깨우기와 IPC](01-boundary-and-execution/04-blocking-wakeup-and-ipc.md)

확인할 내용은 다음과 같습니다.

- user mode에서 kernel mode로 들어가는 이유
- mode switch와 context switch의 차이
- `READY`, `RUNNING`, `BLOCKED`, `TERMINATED`의 배타적 위치
- block된 작업을 어떤 사건이 다시 `READY`로 만드는지

그다음 `kernel_model/lifecycle.py`와 lifecycle 테스트를 확인합니다.

```sh
cd exercises/kernel-model
python3 -m unittest tests.test_models.LifecycleTests -v
python3 kernel-model.py lifecycle examples/lifecycle.json
```

작업 객체의 `state`와 실제 queue 위치가 항상 일치해야 하는 이유를 설명할 수 있으면 다음 단계로 넘어갑니다.

### 2단계: 경쟁과 조건 대기

다음 문서를 읽습니다.

1. [경쟁, 원자성과 순서](02-concurrency/01-races-atomicity-and-ordering.md)
2. [동기화 도구와 조건 대기](02-concurrency/02-synchronization-primitives.md)

확인할 내용은 다음과 같습니다.

- atomic load와 atomic store를 따로 사용해도 복합 갱신이 깨질 수 있는 이유
- condition variable이 predicate 자체를 저장하지 않는 이유
- 조건 확인과 wait 등록 사이에서 wakeup을 잃는 경우
- semaphore permit 수와 실제 소유자를 따로 기록해야 하는 이유

그다음 `kernel_model/synchronization.py`를 확인합니다.

```sh
python3 -m unittest tests.test_models.SynchronizationTests -v
python3 kernel-model.py condition examples/condition.json
```

첫 번째 `commit_wait`가 sleep하지 않는 이유를 generation 변화로 설명할 수 있어야 합니다.

### 3단계: CPU scheduling

[CPU 스케줄링](01-boundary-and-execution/03-cpu-scheduling.md)을 읽습니다.

다음 항목을 같은 workload에서 비교합니다.

- FCFS
- SJF
- priority
- round-robin
- MLFQ

그다음 `kernel_model/scheduler.py`를 확인합니다.

```sh
python3 -m unittest tests.test_models.SchedulerTests -v
python3 kernel-model.py schedule examples/schedule.json
```

매 tick에서 arrival, wakeup, task 선택, 실행, block 또는 종료를 어떤 순서로 처리하는지 설명해야 합니다. response, waiting과 turnaround를 서로 혼동하지 않아야 합니다.

### 4단계: 진행 실패

[데드락과 진행 보장](02-concurrency/03-deadlock-and-progress.md)을 읽습니다.

다음을 구분합니다.

- 정상 block
- deadlock
- starvation
- livelock
- priority inversion

그다음 `kernel_model/deadlock.py`를 확인합니다.

```sh
python3 -m unittest tests.test_models.DeadlockTests -v
python3 kernel-model.py deadlock examples/deadlock-cycle.json
python3 kernel-model.py deadlock examples/deadlock-safe.json
```

단일 instance 자원에서는 wait-for graph cycle을 찾고, 여러 instance에서는 현재 가용량과 allocation을 사용해 완료 가능한 작업을 줄여 나가는 차이를 설명해야 합니다.

### 5단계: 가상 메모리

다음 문서를 순서대로 읽습니다.

1. [주소 공간과 page fault](03-virtual-memory/01-address-spaces-and-faults.md)
2. [요구 페이징, COW와 page replacement](03-virtual-memory/02-demand-paging-cow-and-replacement.md)

확인할 내용은 다음과 같습니다.

- mapping 존재 여부와 resident 여부의 차이
- not-present fault와 protection fault의 차이
- COW write에서 새 frame을 만드는 시점
- PTE 수와 frame refcount가 일치해야 하는 이유
- FIFO, LRU와 Clock이 저장하는 상태

그다음 `kernel_model/paging.py`를 확인합니다.

```sh
python3 -m unittest tests.test_models.PagingTests -v
python3 kernel-model.py memory examples/memory-cow.json
python3 kernel-model.py replacement examples/replacement.json
```

부모와 자식이 같은 frame을 공유하는 동안 일반 write를 허용하면 왜 안 되는지 설명해야 합니다.

### 6단계: 파일시스템과 crash recovery

[파일시스템, page cache와 장애 일관성](04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md)을 읽습니다.

다음을 구분합니다.

- 현재 directory와 durable directory
- cached data와 durable data
- file `fsync`와 directory `fsync`
- journal의 begin, operation과 commit
- replay를 두 번 실행했을 때의 결과

그다음 `kernel_model/filesystem.py`와 `kernel_model/journal.py`를 확인합니다.

```sh
python3 -m unittest tests.test_models.StorageTests -v
python3 kernel-model.py filesystem examples/filesystem-crash.json
```

file data를 flush했어도 새 이름이 crash 뒤 사라질 수 있는 이유를 설명해야 합니다.

### 7단계: 장치 I/O와 DMA

[장치 I/O, interrupt와 DMA](04-storage-and-io/02-device-io-interrupts-and-dma.md)를 읽습니다.

다음 상태를 추적합니다.

```text
QUEUED
→ IN_FLIGHT
→ COMPLETED 또는 CANCELLED
→ REAPED
```

in-flight 요청을 취소해도 interrupt completion 전까지 buffer pin을 유지해야 하는 경우를 설명합니다.

그다음 `kernel_model/device_io.py`를 확인합니다.

```sh
python3 -m unittest tests.test_models.DeviceTests -v
python3 kernel-model.py io examples/device-io.json
```

요청이 pending, in-flight와 completion queue 중 두 곳에 동시에 있으면 어떤 오류가 생기는지 설명해야 합니다.

### 8단계: 전체 연결과 검증

마지막으로 JSON CLI와 전체 테스트를 실행합니다.

```sh
make check
```

검증 항목은 다음과 같습니다.

- 각 모델의 단위 테스트
- 9개 정상 scenario의 선언된 관찰값
- 8개 invalid snapshot의 정확한 거부 이유
- CLI 성공·실패 종료 상태
- Python 문법 검사

## 관찰 예제 사용 시점

`examples/`의 C 프로그램은 대응하는 문서를 읽은 뒤 선택적으로 실행합니다.

| 예제 | 권장 시점 | 확인할 내용 |
| --- | --- | --- |
| `syscall-boundary` | 1단계 | 반환값과 `errno` |
| `lost-update` | 2단계 | 분리된 load/store의 lost update |
| `bounded-buffer` | 2단계 | condition predicate 재검사 |
| `dining-cycle` | 4단계 | 전역 lock order |
| `cow-observer` | 5단계 | fork 뒤 값 분리 |
| `page-fault-observer` | 5단계 | 첫 page 접근과 fault 통계 |

이 예제는 필수 실습을 대신하지 않습니다. 실제 환경의 관찰값과 결정론적 상태 모델을 연결하는 보조 자료입니다.

## 선택 확장

[`80-extended-labs.md`](80-extended-labs.md)는 필수 과정을 끝낸 뒤 선택합니다.

- page-table 주소 계산
- 자세한 MLFQ trace
- 학습용 binary filesystem image
- device descriptor ring

이 항목은 전문 주제로 들어가기 위한 연습이며 필수 완료 기준에는 포함하지 않습니다.

## 최종 완료 기준

다음을 모두 충족해야 합니다.

- 필수 문서 11개를 읽고 각 문서의 자기 설명 질문에 답합니다.
- `make -C exercises/kernel-model check`가 통과합니다.
- 정상 scenario 9개와 invalid snapshot 8개를 설명합니다.
- lifecycle, scheduling, paging, filesystem, device I/O 중 하나의 상태 변화를 표로 작성합니다.
- policy 선택과 불변식 검사를 구분합니다.
- 특정 커널 구현을 관찰 결과만으로 단정하지 않습니다.

설명이 막히는 주제만 다시 읽습니다. 전체 과정을 처음부터 반복할 필요는 없습니다.
