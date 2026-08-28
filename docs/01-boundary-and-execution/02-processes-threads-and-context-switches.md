# 프로세스, 스레드와 문맥 전환

## 학습 목표

- program, process, address space, thread와 CPU context를 구분합니다.
- `NEW`, `READY`, `RUNNING`, `BLOCKED`, `TERMINATED` 상태와 실제 queue 위치를 함께 추적합니다.
- mode switch와 context switch의 원인, 저장 상태와 비용을 구분합니다.

## 실행 단위를 나누어 보기

```text
program
- 저장장치에 있는 code와 초기 data

process
- 하나의 address space
- credential과 resource limit
- file descriptor table 및 kernel object 참조
- 하나 이상의 thread

thread
- program counter와 register
- stack pointer와 thread stack
- scheduling state와 priority
- signal mask 등 thread별 상태
```

같은 program을 두 번 실행하면 서로 다른 process가 됩니다. 같은 process의 thread들은 보통 code, global data, heap과 열린 file을 공유하지만 register와 stack은 각각 가집니다. 같은 memory가 보인다는 사실은 동시에 접근해도 안전하다는 뜻이 아닙니다.

## 최소 실행 상태

```text
NEW --admit--> READY --dispatch--> RUNNING --exit--> TERMINATED
                    ^                 |
                    |                 | block
                    |                 v
                    +---- wake ---- BLOCKED

RUNNING --preempt 또는 yield--> READY
```

| 전이 | 발생 주체 | 대표 원인 |
| --- | --- | --- |
| `NEW → READY` | 생성 또는 admission 처리 | 초기화가 끝나 실행 후보가 됨 |
| `READY → RUNNING` | scheduler와 dispatcher | CPU 배정 |
| `RUNNING → READY` | timer, scheduler 또는 작업 자신 | 선점, quantum 만료, yield |
| `RUNNING → BLOCKED` | system call, fault 또는 동기화 처리 | I/O, timer, page-in, lock 대기 |
| `BLOCKED → READY` | interrupt, timer 또는 다른 작업 | 기다리던 사건 발생 |
| `RUNNING → TERMINATED` | 작업 또는 kernel | 정상 종료, 복구 불가능한 오류 |

핵심 불변식은 한 작업이 동시에 두 실행 위치에 있지 않는 것입니다.

```text
READY 작업은 한 ready queue에 정확히 한 번 있습니다.
RUNNING 작업은 한 CPU에서만 실행합니다.
BLOCKED 작업은 하나의 대기 이유와 wait queue에 연결됩니다.
TERMINATED 작업은 ready queue와 wait queue에 남지 않습니다.
```

작업 객체의 `state`만 확인해서는 부족합니다. `state=READY`인데 ready queue에 없거나, `state=BLOCKED`인데 wait queue에 없다면 실제 scheduler가 그 작업을 찾을 수 없습니다.

## 상태 전이와 context switch

상태 전이는 작업의 논리적 위치가 바뀌는 사건입니다. context switch는 현재 CPU register를 저장하고 다른 작업의 register를 복원하는 동작입니다.

```text
사용자 모드 → 커널 모드 → 같은 thread
- system call이 즉시 끝납니다.
- mode는 바뀌지만 실행 주체는 같습니다.

사용자 모드 → 커널 모드 → 다른 thread
- 현재 작업이 block되거나 preempt됩니다.
- mode switch와 context switch가 함께 일어납니다.

kernel thread A → kernel thread B
- 사용자 모드로 돌아가지 않고 실행 주체만 바뀝니다.
```

system call 횟수와 context switch 횟수는 같지 않습니다. 성능을 조사할 때는 어떤 작업이 `RUNNING`에서 나갔고, 원인이 I/O, lock, page fault 또는 quantum 만료 중 무엇인지 확인해야 합니다.

## 저장해야 하는 문맥

운영체제와 ISA마다 실제 필드는 다르지만 다음 상태가 필요합니다.

```text
CPU 실행 상태
- program counter
- stack pointer
- 일반 register와 상태 flag
- 필요할 때 vector 또는 FPU state

scheduling 상태
- READY, RUNNING, BLOCKED
- priority, queue level와 남은 quantum
- CPU affinity와 최근 실행 CPU
- block reason과 wait channel

process 연결
- address space 참조
- credential과 resource limit
- file table 등 process-level object

kernel 실행 상태
- kernel stack
- 중단된 system call의 진행 상태
- 사용 중인 kernel object와 정리할 자원
```

모든 상태를 매번 같은 방식으로 저장하지는 않습니다. 같은 process 안의 thread를 바꾸면 address space를 유지할 수 있고, 일부 register는 필요할 때만 저장할 수 있습니다.

## process와 thread가 공유하는 항목

| 자원 | process 사이 | 같은 process의 thread 사이 |
| --- | --- | --- |
| virtual address space | 기본적으로 분리 | 공유 |
| register와 stack | 분리 | thread마다 분리 |
| heap과 global data | 별도 mapping 없이는 분리 | 공유 |
| file descriptor table | 생성·전달 방식에 따라 공유 가능 | 보통 process 단위로 공유 |
| credential과 resource limit | process 단위 | 대체로 공유 |
| scheduling state | 실행 주체마다 별도 | thread마다 별도 |

같은 file descriptor 번호를 사용하더라도 실제 file offset과 open file object를 무엇이 공유하는지는 API의 정확한 규칙을 확인해야 합니다.

## 생성과 종료에서 남는 상태

### 생성

- 새 process 또는 thread를 누가 할당합니까?
- address space와 file table을 복사합니까, 공유합니까?
- `READY`로 공개하기 전에 초기화가 끝났습니까?

### 실행 이미지 교체

- process identity와 PID는 유지됩니까?
- 기존 address space와 다른 thread는 어떻게 정리됩니까?
- 어떤 file과 signal 상태가 남습니까?

### 종료

- exit status를 누가 보관합니까?
- parent가 결과를 회수하기 전 어떤 최소 상태가 남습니까?
- 마지막 참조가 사라질 때 누가 object를 해제합니까?

실행을 끝낸 시점과 모든 관련 자원이 해제되는 시점은 다를 수 있습니다. zombie 상태는 종료 결과를 parent가 아직 회수하지 않은 대표적인 예입니다.

## context switch 비용

비용은 register 저장과 복원만이 아닙니다.

- scheduler queue를 갱신하고 다음 작업을 고릅니다.
- kernel stack과 작업별 상태를 바꿉니다.
- address space가 바뀌면 translation 상태가 달라질 수 있습니다.
- 새 작업의 code와 data가 cache에 없으면 이후 miss가 늘어납니다.
- 여러 CPU가 같은 lock과 cache line을 갱신할 수 있습니다.

quantum이 지나치게 짧으면 응답성이 좋아질 수 있지만 실제 계산보다 전환에 쓰는 시간이 커질 수 있습니다.

## 다중 CPU에서 추가되는 문제

```text
한 작업은 동시에 두 CPU에서 RUNNING이면 안 됩니다.
CPU별 ready queue의 부하를 언제 옮길지 정해야 합니다.
최근 CPU를 유지해 locality를 얻을지 빈 CPU로 옮길지 선택해야 합니다.
동일한 kernel object를 여러 CPU가 바꾸면 동기화가 필요합니다.
```

`kernel-model`은 CPU 하나만 사용합니다. 다중 CPU는 같은 위치 불변식에 CPU별 queue와 migration이 추가된 확장으로 이해합니다.

## 연결 실습

```sh
cd exercises/kernel-model
python3 -m unittest tests.test_models.LifecycleTests -v
python3 kernel-model.py lifecycle examples/lifecycle.json
```

다음 항목을 확인합니다.

- `dispatch`가 ready queue에서 작업을 제거하는지
- `block`이 running 위치를 비우고 wait queue에 한 번만 넣는지
- `wake_one`이 wait metadata를 지우는지
- 종료한 작업이 다른 queue에 남지 않는지

## 완료 기준

- program, process와 thread의 차이를 설명할 수 있습니다.
- 각 실행 상태의 실제 위치를 함께 적을 수 있습니다.
- mode switch와 context switch의 차이를 예로 설명할 수 있습니다.
- process 종료 뒤에도 잠시 남을 수 있는 상태를 설명할 수 있습니다.

## 잘못된 이해

- `RUNNING`을 “process가 존재함”과 같은 뜻으로 사용합니다.
- thread가 heap을 공유하므로 동시 접근도 안전하다고 생각합니다.
- system call마다 항상 다른 process로 switch한다고 생각합니다.
- 객체의 enum 값만 맞으면 queue 상태도 맞다고 가정합니다.

## 자기 설명

- `BLOCKED` 작업이 ready queue에도 있으면 어떤 문제가 생깁니까?
- 같은 process의 thread switch와 다른 process로의 switch가 이후 memory 접근에 다르게 영향을 줄 수 있는 이유는 무엇입니까?
- 종료와 결과 회수를 분리해야 하는 이유는 무엇입니까?
