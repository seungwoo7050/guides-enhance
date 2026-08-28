# 블록, 깨우기와 IPC

## 학습 목표

- predicate 확인, wait 등록, block과 wakeup을 끊기지 않는 상태 변경으로 연결합니다.
- generation을 사용해 조건 확인과 wait 등록 사이의 lost wakeup을 막습니다.
- 정상 completion, timeout과 cancellation이 경쟁할 때 마지막으로 자원을 정리할 주체를 정합니다.

## block은 CPU를 반납하는 상태 전이입니다

작업이 I/O, timer, lock 또는 message를 기다리면서 계속 반복 확인하면 CPU를 낭비합니다. 운영체제는 진행 조건이 충족되지 않은 작업을 `BLOCKED`로 옮기고, 조건을 바꾼 사건이 발생했을 때 다시 `READY`로 만듭니다.

```text
1. 작업이 진행 조건을 확인합니다.
2. 조건이 거짓이면 wait queue에 등록합니다.
3. RUNNING에서 BLOCKED로 바뀝니다.
4. scheduler가 다른 READY 작업을 실행합니다.
5. device, timer 또는 다른 작업이 조건을 바꿉니다.
6. waiter를 BLOCKED에서 READY로 옮깁니다.
7. 다시 실행될 때 조건을 재확인합니다.
```

wakeup은 즉시 `RUNNING`이 된다는 뜻이 아닙니다. ready queue에 들어간 뒤 scheduler가 선택해야 합니다.

## wait queue에 필요한 정보

단순한 thread 목록만으로는 취소와 중복 wakeup을 처리하기 어렵습니다.

```text
대기 주체 식별자
기다리는 predicate 또는 사건
연결된 object나 channel
등록 generation 또는 sequence
timeout과 cancellation 상태
깨울 때 전달할 결과 또는 오류
queue에서 제거할 주체
```

한 작업이 둘 이상의 wait queue에 동시에 있거나, wakeup 뒤에도 `BLOCKED` 상태가 남아 있으면 실행 위치 불변식이 깨집니다.

## lost wakeup이 생기는 순서

```text
consumer: queue가 비었는지 확인 → 비어 있음
producer: item 추가 → notify, 아직 waiter 없음
consumer: wait queue 등록 → sleep
```

조건은 이미 참이지만 이후 notify가 없으면 consumer가 계속 잠들 수 있습니다. 문제는 조건 확인과 wait 등록이 분리되어 있다는 점입니다.

대표적인 해결 방법은 다음과 같습니다.

- predicate를 보호하는 mutex를 잡은 상태에서 wait 등록과 mutex 해제를 연결합니다.
- event generation을 기록하고 등록 직전에 값이 바뀌었는지 확인합니다.
- message queue처럼 data 자체를 보관하여 늦게 온 receiver가 읽게 합니다.

`kernel-model`의 `ConditionChannel`은 generation을 사용합니다.

```text
prepare_wait에서 generation=4 확인
그 사이 notify로 generation=5 변경
commit_wait에서 값이 다름을 확인
→ sleep하지 않고 predicate를 다시 확인
```

## condition은 while로 재확인합니다

wakeup은 predicate가 지금도 참이라는 보장이 아닙니다.

- 다른 waiter가 먼저 자원을 가져갈 수 있습니다.
- broadcast가 여러 waiter를 동시에 깨울 수 있습니다.
- 구현이 spurious wakeup을 허용할 수 있습니다.
- timeout 또는 cancellation과 정상 사건이 경쟁할 수 있습니다.

따라서 일반적인 형태는 다음과 같습니다.

```text
mutex lock
while predicate가 거짓:
    condition wait
predicate가 참인 상태에서 공유 상태 변경
mutex unlock
```

`condition_wait`는 wait queue 등록, mutex 해제와 현재 thread의 block을 연결해야 합니다.

## timeout과 cancellation도 completion입니다

대기 중인 요청을 취소할 때 원래 작업이 이미 끝났을 수 있습니다.

```text
정상 completion이 먼저 발생
→ cancel은 완료 결과를 지우지 않습니다.

cancel이 먼저 queue에서 제거
→ 늦게 도착한 completion이 같은 자원을 다시 해제하면 안 됩니다.

in-flight device request
→ 사용자 요청은 취소됐어도 DMA 종료 전까지 buffer를 유지할 수 있습니다.
```

요청 상태를 `QUEUED`, `IN_FLIGHT`, `COMPLETED`, `CANCEL_PENDING`, `CANCELLED`처럼 나누면 마지막 cleanup을 누가 수행하는지 결정하기 쉽습니다.

## IPC를 data 전달 방식으로 구분하기

### pipe와 byte stream

- byte 순서를 보존합니다.
- message boundary를 보존하지 않을 수 있습니다.
- buffer가 가득 차면 writer가 block될 수 있습니다.
- 모든 write end가 닫혀야 reader가 EOF를 볼 수 있습니다.

### message queue

- message boundary와 payload를 보존합니다.
- queue depth, message size, ordering과 backpressure 규칙이 필요합니다.

### shared memory

- data copy를 줄일 수 있습니다.
- 참여자가 동기화와 수명을 직접 관리해야 합니다.
- mapping 공유가 visibility와 atomicity를 자동으로 보장하지 않습니다.

### signal 또는 event notification

- 작은 사건을 알리는 데 적합합니다.
- 같은 사건이 합쳐지는지 queue되는지 확인해야 합니다.

### local socket

- stream 또는 datagram 형태를 사용할 수 있습니다.
- credential과 namespace 관련 기능을 제공할 수 있습니다.

구체적인 POSIX API 사용법은 C 또는 Unix 프로그래밍 문서에서 다룹니다.

## backpressure는 정상적인 제어입니다

producer가 consumer보다 빠르면 queue를 무한히 늘릴 수 없습니다.

```text
producer block
새 요청 거부
낡은 항목 제거
우선순위별 제한
속도 조절 신호 전달
storage로 임시 이동
```

아무 규칙도 정하지 않으면 memory exhaustion과 긴 latency가 사실상의 backpressure가 됩니다.

## wakeup과 scheduling

waiter를 `READY`로 바꾸는 동작과 CPU를 주는 선택은 다릅니다.

```text
상태 변경
- wait queue에서 제거합니다.
- BLOCKED를 READY로 바꿉니다.
- 결과 또는 오류를 기록합니다.

선택
- 한 명 또는 여러 명을 깨웁니다.
- 어느 CPU queue에 넣을지 정합니다.
- 현재 작업을 즉시 선점할지 정합니다.
```

`notify_all`을 항상 사용하면 많은 작업이 동시에 깨어나 다시 같은 lock을 기다리는 thundering herd가 생길 수 있습니다.

## 연결 실습

```sh
cd exercises/kernel-model
python3 -m unittest tests.test_models.LifecycleTests tests.test_models.SynchronizationTests -v
python3 kernel-model.py lifecycle examples/lifecycle.json
python3 kernel-model.py condition examples/condition.json
```

`condition` scenario에서 첫 번째 `commit`은 `slept=false`가 되어야 합니다. `prepare`와 `commit` 사이에 notify가 발생했기 때문입니다.

## 완료 기준

- block과 wakeup의 상태 변화를 순서대로 설명할 수 있습니다.
- lost wakeup이 생기는 실행 순서를 작성할 수 있습니다.
- condition wakeup 뒤 predicate를 다시 확인하는 이유를 설명할 수 있습니다.
- normal completion, timeout과 cancel 중 누가 마지막 자원을 해제하는지 정할 수 있습니다.
- pipe, message queue와 shared memory의 data 보존 방식을 구분할 수 있습니다.

## 잘못된 이해

- notify가 호출되면 waiter가 즉시 실행된다고 생각합니다.
- condition variable이 item 또는 permit을 저장한다고 생각합니다.
- timeout이 발생하면 원래 작업이 실행되지 않았다고 단정합니다.
- in-flight 요청을 취소하자마자 DMA buffer를 해제합니다.

## 자기 설명

- 조건 확인과 wait 등록 사이의 사건을 잃지 않으려면 어떤 상태가 필요합니까?
- broadcast 뒤에도 predicate를 `while`로 확인해야 하는 이유는 무엇입니까?
- cancellation과 completion이 경쟁할 때 double cleanup을 막는 방법은 무엇입니까?
