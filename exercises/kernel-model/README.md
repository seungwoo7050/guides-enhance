# Kernel Model

`Kernel Model`은 운영체제가 관리하는 실행 상태, 동기화, CPU scheduling, virtual memory, filesystem과 device I/O를 같은 입력으로 반복 실행하는 Python 시뮬레이터입니다.

실제 kernel을 복제하지는 않습니다. 시간과 hardware timing을 제거하고, 상태 변경과 불변식에 집중합니다. 정상 scenario뿐 아니라 queue 중복, 잘못된 COW 공유, link count 불일치처럼 불가능한 snapshot도 구체적인 이유로 거부합니다.

## 주요 기능

- `NEW`, `READY`, `RUNNING`, `BLOCKED`, `TERMINATED` 상태와 실제 queue 위치를 함께 검사합니다.
- condition generation으로 predicate 확인과 wait 등록 사이의 lost wakeup을 막습니다.
- semaphore waiter가 있으면 permit을 다음 작업에 바로 넘깁니다.
- FCFS, SJF, priority, round-robin과 MLFQ를 같은 tick 기반 workload에서 비교합니다.
- wait-for graph cycle, 여러 instance 자원의 deadlock과 safe sequence를 계산합니다.
- demand paging, protection fault, COW, frame refcount와 FIFO/LRU/Clock replacement를 실행합니다.
- 현재 namespace와 cache를 crash 뒤 남을 directory와 data에서 분리합니다.
- commit된 journal transaction만 replay하고 같은 transaction을 두 번 적용하지 않습니다.
- device request의 pending, in-flight, completion과 reap 위치 및 DMA pin 상태를 검사합니다.
- JSON CLI와 project-local `unittest`를 제공합니다.

## 요구 환경

- Python 3.10 이상
- 외부 Python package 없음
- `make`는 편의 명령에만 사용합니다.

## 실행

프로젝트 디렉터리에서 다음 명령을 실행합니다.

```sh
python3 kernel-model.py lifecycle examples/lifecycle.json
python3 kernel-model.py schedule examples/schedule.json
python3 kernel-model.py memory examples/memory-cow.json
python3 kernel-model.py filesystem examples/filesystem-crash.json
```

지원하는 model은 다음과 같습니다.

| Model | 입력 | 출력 |
| --- | --- | --- |
| `lifecycle` | 작업 생성, 준비, 실행, block, wakeup, 종료 | 작업 상태와 queue snapshot |
| `condition` | prepare, commit, notify 순서 | generation, waiter, wakeup 결과 |
| `schedule` | workload와 scheduling policy | timeline, 완료 순서, metric |
| `deadlock` | wait graph 또는 자원 vector | cycle, deadlocked set, safe sequence |
| `memory` | process mapping, access, fork, unmap | fault 결과와 memory snapshot |
| `replacement` | page reference 목록 | fault 수, eviction 순서, 최종 frame |
| `filesystem` | namespace, durability, journal operation | filesystem, journal, replay 결과 |
| `io` | submit, start, cancel, interrupt, reap | request 상태와 queue snapshot |

성공하면 정렬된 JSON을 stdout에 출력합니다. model operation이 유효하지 않거나 불변식이 깨지면 stderr에 오류를 출력하고 종료 상태 `1`을 반환합니다. 존재하지 않는 model이나 잘못된 명령 형식은 `argparse`가 종료 상태 `2`를 반환합니다.

## Scenario 형식

`examples/`의 JSON 파일에는 실행 입력과 확인할 출력 항목이 함께 있습니다.

```json
{
  "operations": [
    {"op": "add", "tid": "A"},
    {"op": "admit", "tid": "A"}
  ],
  "expected": {
    "ready": ["A"]
  }
}
```

runtime은 `expected`를 읽지 않습니다. `tests/test_scenarios.py`가 실행 결과 중 `expected`에 적힌 key만 비교합니다. 내부 object 표현을 조금 바꾸더라도 외부에서 확인해야 할 결과가 같으면 scenario는 계속 유효합니다.

## Python API

CLI를 거치지 않고 model을 직접 사용할 수도 있습니다.

```python
from kernel_model import KernelState

kernel = KernelState()
kernel.add("worker")
kernel.admit("worker")
kernel.dispatch()
kernel.block("disk:0", "read")
kernel.wake_one("disk:0")
kernel.assert_invariants()
```

공개 symbol은 `kernel_model/__init__.py`에서 확인할 수 있습니다.

## 디렉터리 구성

```text
kernel-model/
├── README.md
├── Makefile
├── kernel-model.py
├── kernel_model/
│   ├── cli.py
│   ├── deadlock.py
│   ├── device_io.py
│   ├── filesystem.py
│   ├── journal.py
│   ├── lifecycle.py
│   ├── paging.py
│   ├── scheduler.py
│   └── synchronization.py
├── examples/
└── tests/
    └── fixtures/invalid/
```

각 module은 자신이 저장하는 값과 검사할 불변식을 직접 구현합니다. `cli.py`는 JSON operation을 model method 호출로 바꾸며, scheduling이나 memory 규칙을 다시 구현하지 않습니다.

`tests/fixtures/invalid/`에는 일부러 잘못 만든 snapshot이 있습니다. 각 fixture는 어떤 오류 메시지로 거부돼야 하는지 함께 기록합니다.

## 검증

```sh
make test
make check
```

- `make test`: 단위 테스트, 정상 scenario와 invalid snapshot 테스트를 실행합니다.
- `make check`: Python 문법을 검사하고 전체 테스트와 CLI smoke test를 실행한 뒤 bytecode cache를 제거합니다.

`make` 없이 실행할 수도 있습니다.

```sh
PYTHONDONTWRITEBYTECODE=1 \
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## 중요한 구현 선택

### state와 실제 위치를 함께 검사합니다

작업의 enum 값만 확인하면 queue 중복, 남아 있는 wait metadata와 종료 후 stale reference를 놓칠 수 있습니다. lifecycle과 device model은 state 값뿐 아니라 ready, wait, pending, in-flight와 completion container를 함께 검사합니다.

### 같은 입력에서 같은 순서를 만듭니다

scheduler와 deadlock 분석은 후보가 여러 개일 때 정렬 기준을 명시합니다. hash iteration order나 실행 환경 때문에 timeline과 cycle 경로가 달라지지 않게 합니다.

### 현재 보이는 값과 crash 뒤 남는 값을 나눕니다

filesystem은 `directory`와 `durable_directory`, `cached_data`와 `durable_data`를 따로 저장합니다. file data를 `fsync`했어도 새 이름이 directory에 durable하지 않으면 crash 뒤 사라질 수 있습니다.

### request는 owner가 결과를 받을 때까지 유지합니다

in-flight device request는 cancel 요청을 받아도 interrupt completion 전까지 DMA pin을 유지합니다. completion은 owner queue에 한 번만 들어가며, `reap`이 성공한 뒤에 request 상태를 `REAPED`로 바꿉니다.

## Implementation Order

다음 순서는 파일 배치 순서가 아니라 프로젝트를 처음부터 구현할 때 필요한 의존 순서입니다. 표의 설명은 source annotation과 같습니다.

| Order | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | 실행 상태와 위치 정의 | `kernel_model/lifecycle.py:TaskState` |
| 1-1 | 생성·준비·실행 위치 이전 | `kernel_model/lifecycle.py:KernelState.add` |
| 1-2 | 배타적인 실행 상태 전이 | `kernel_model/lifecycle.py:KernelState.block` |
| 1-3 | 실행 상태 불변식 검사 | `kernel_model/lifecycle.py:KernelState.assert_invariants` |
| 2 | 대기 generation 정의 | `kernel_model/synchronization.py:WaitToken` |
| 2-1 | lost wakeup 방지 | `kernel_model/synchronization.py:ConditionChannel.commit_wait` |
| 2-2 | semaphore permit 직접 이전 | `kernel_model/synchronization.py:CountingSemaphore` |
| 3 | workload와 scheduling 결과 정의 | `kernel_model/scheduler.py:JobSpec` |
| 3-1 | 실행 중 scheduling 상태 | `kernel_model/scheduler.py:simulate` |
| 3-2 | 재현 가능한 작업 선택 | `kernel_model/scheduler.py:choose` |
| 3-3 | tick 사건 처리 순서 | `kernel_model/scheduler.py:simulate` |
| 4 | wait-for graph 정의 | `kernel_model/deadlock.py:find_wait_cycle` |
| 4-1 | DFS cycle 경로 복원 | `kernel_model/deadlock.py:visit` |
| 4-2 | 여러 instance deadlock 판정 | `kernel_model/deadlock.py:detect_deadlocked` |
| 4-3 | safe sequence 계산 | `kernel_model/deadlock.py:safe_sequence` |
| 5 | 가상 메모리 상태 정의 | `kernel_model/paging.py:FaultKind` |
| 5-1 | mapping과 frame 수명 관리 | `kernel_model/paging.py:MemoryManager` |
| 5-2 | memory access fault 분류 | `kernel_model/paging.py:MemoryManager.read` |
| 5-3 | COW 공유와 분리 | `kernel_model/paging.py:MemoryManager.fork` |
| 5-4 | PTE·frame 불변식 검사 | `kernel_model/paging.py:MemoryManager.assert_invariants` |
| 5-5 | page replacement 실행 | `kernel_model/paging.py:simulate_replacement` |
| 6 | 현재값과 durable filesystem 상태 분리 | `kernel_model/filesystem.py:Inode` |
| 6-1 | namespace와 link count 변경 | `kernel_model/filesystem.py:FileSystemModel.create` |
| 6-2 | fsync와 crash recovery | `kernel_model/filesystem.py:FileSystemModel.fsync_file` |
| 6-3 | journal replay용 filesystem operation | `kernel_model/filesystem.py:FileSystemModel.apply_operation` |
| 6-4 | 관찰 가능한 filesystem snapshot | `kernel_model/filesystem.py:FileSystemModel.snapshot` |
| 6-5 | namespace·inode 불변식 검사 | `kernel_model/filesystem.py:FileSystemModel.assert_invariants` |
| 7 | journal record 정의 | `kernel_model/journal.py:JournalRecord` |
| 7-1 | transaction 시작과 txid 발급 | `kernel_model/journal.py:Journal.begin` |
| 7-2 | 열린 transaction에 operation 추가 | `kernel_model/journal.py:Journal.append` |
| 7-3 | commit된 transaction만 replay | `kernel_model/journal.py:Journal.recover` |
| 7-4 | journal record 순서 검사 | `kernel_model/journal.py:Journal.validate` |
| 8 | device request 상태 정의 | `kernel_model/device_io.py:RequestState` |
| 8-1 | queue 용량 확인과 DMA 시작 | `kernel_model/device_io.py:DeviceQueue.submit` |
| 8-2 | cancel과 interrupt completion 경쟁 | `kernel_model/device_io.py:DeviceQueue.cancel` |
| 8-3 | completion 결과 한 번만 전달 | `kernel_model/device_io.py:DeviceQueue.reap` |
| 8-4 | request 위치와 DMA pin 검사 | `kernel_model/device_io.py:DeviceQueue.assert_invariants` |
| 9 | JSON 입력과 출력 | `kernel_model/cli.py:_load` |
| 9-1 | JSON operation을 model 호출로 변환 | `kernel_model/cli.py:run_lifecycle` |
| 9-2 | model 선택과 종료 상태 반환 | `kernel_model/cli.py:main` |
| 9-3 | CLI process 진입점 | `kernel-model.py` |
| 10 | model별 단위 검증 | `tests/test_models.py` |
| 10-1 | 정상 scenario의 관찰값 검증 | `tests/test_scenarios.py` |
| 10-2 | 잘못된 snapshot 거부 검증 | `tests/test_invalid_snapshots.py` |

## 범위와 제한

- 실제 kernel, CPU instruction, interrupt controller, TLB 또는 cache coherence를 구현하지 않습니다.
- scheduler는 CPU 하나와 정수 tick을 사용합니다. multi-CPU load balancing은 다루지 않습니다.
- virtual page와 physical frame은 정수 값 하나로 단순화합니다.
- filesystem은 단일 directory만 지원합니다. block allocator, B-tree와 실제 on-disk format은 구현하지 않습니다.
- journal recovery 도중 operation 하나가 실패해도 transaction 전체를 rollback하지 않습니다.
- device model은 queue 하나만 사용합니다. 실제 register, bus와 IOMMU page table은 다루지 않습니다.
- 결과는 운영체제의 상태 변화와 불변식을 설명하기 위한 것이며 특정 kernel의 성능이나 timing을 예측하지 않습니다.
