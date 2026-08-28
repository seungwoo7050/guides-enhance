# 동기화 도구와 조건 대기

## 학습 목표

- mutex, spinlock, semaphore, condition variable과 barrier를 저장하는 상태와 사용 가능한 문맥으로 구분합니다.
- 도구 이름보다 보호할 predicate와 자원 수명을 먼저 정합니다.
- cancellation, shutdown과 priority inversion을 정상 실행과 함께 고려합니다.

## 먼저 predicate를 적습니다

bounded queue를 예로 들면 다음 조건을 항상 지켜야 합니다.

```text
0 <= count <= capacity
head와 tail은 유효한 slot을 가리킵니다.
count == 0이면 consumer는 pop할 수 없습니다.
count == capacity이면 producer는 push할 수 없습니다.
producer_done && count == 0이면 consumer가 종료할 수 있습니다.
```

이 조건을 적지 않고 mutex와 condition부터 고르면 다음 오류를 놓치기 쉽습니다.

- `count`만 잠그고 종료 flag는 잠그지 않습니다.
- wait할 때 predicate를 보호하던 mutex와 다른 mutex를 사용합니다.
- predicate를 바꾸기 전에 signal합니다.
- 오류 경로에서 lock을 반납하지 않습니다.
- 마지막 producer의 종료를 waiter에게 알리지 않습니다.

## mutex

mutex는 일반적으로 한 thread가 획득하고 같은 thread가 해제합니다.

```text
lock 성공
→ 보호하는 값을 읽고 바꿀 독점 권한을 얻습니다.

unlock
→ 갱신한 값을 다른 thread가 볼 수 있게 하고 lock을 반납합니다.
```

선택할 때 다음을 확인합니다.

- 현재 문맥에서 sleep해도 됩니까?
- 임계 구역이 얼마나 오래 실행됩니까?
- lock을 가진 채 I/O나 다른 thread의 completion을 기다립니까?
- 여러 lock을 항상 같은 순서로 획득합니까?
- 조기 반환과 오류에서도 반드시 해제합니까?

lock 수를 늘리면 동시에 실행할 수 있는 범위가 넓어질 수 있지만, 하나의 불변식이 여러 lock에 걸리면 일관된 snapshot을 만들기 어려워집니다.

## spinlock

spinlock은 획득할 때까지 CPU에서 반복합니다. 다음 조건에서만 검토합니다.

```text
임계 구역이 매우 짧습니다.
현재 문맥에서 sleep할 수 없습니다.
소유자가 다른 CPU에서 곧 실행될 가능성이 큽니다.
preemption과 interrupt 규칙이 정해져 있습니다.
```

single-core에서 lock 소유자가 preempt된 채 다른 thread가 계속 spin하면 진행하지 못할 수 있습니다. kernel spinlock은 preemption, interrupt mask와 memory barrier를 함께 처리할 수 있으므로 사용자 공간의 단순 busy loop와 같지 않습니다.

## semaphore

counting semaphore는 동시에 사용할 수 있는 permit 수를 나타냅니다.

```text
초기 permit = N
acquire 성공 → permit 하나 사용
permit 없음 → waiter 등록 또는 즉시 실패
release → 다음 waiter에게 넘기거나 permit 증가
```

semaphore는 mutex와 소유 규칙이 다를 수 있습니다. resource pool, producer-consumer의 item 수 또는 동시 작업 제한에 사용할 수 있습니다.

permit 수만으로 실제 queue 내용과 object lifetime이 맞는지는 알 수 없습니다. 필요하면 mutex나 별도 상태 검사로 permit과 실제 resource 수가 일치하는지 확인합니다.

`kernel-model`의 `CountingSemaphore`는 waiter가 있으면 permit을 숫자로 되돌리지 않고 다음 waiter에게 바로 넘깁니다. 이렇게 해야 “사용 가능한 permit”과 “이미 permit을 받은 owner”를 구분할 수 있습니다.

## condition variable

condition variable은 item이나 permit을 저장하지 않습니다. predicate가 바뀌었을 가능성을 waiter에게 알립니다.

```text
mutex lock
while predicate가 거짓:
    condition wait
공유 상태 변경
mutex unlock
```

wait operation은 다음 세 동작을 끊기지 않게 연결해야 합니다.

```text
wait queue 등록
mutex 해제
현재 thread block
```

깨어난 뒤에는 mutex를 다시 획득하고 predicate를 재확인합니다.

### signal과 broadcast

- `signal`: 진행할 수 있는 waiter가 하나일 때 사용합니다.
- `broadcast`: shutdown처럼 모든 waiter가 새 조건을 확인해야 할 때 사용합니다.

item 하나가 추가됐는데 모든 consumer를 깨우면 대부분 다시 sleep하며 lock 경쟁만 늘어납니다. 반대로 여러 slot이 생겼는데 한 명만 깨우면 처리량을 놓칠 수 있습니다.

## event와 generation

notify를 호출할 때 waiter가 없으면 사건이 사라질 수 있습니다. 필요한 저장 방식은 사건의 의미에 따라 다릅니다.

```text
상태 기반 조건
→ 공유 상태 자체를 저장하고 mutex 아래에서 다시 확인합니다.

누적 허가
→ semaphore count에 저장합니다.

message
→ queue에 payload를 보관합니다.

변경 여부
→ generation 또는 sequence를 증가시킵니다.
```

`ConditionChannel`은 `prepare_wait`에서 확인한 generation과 `commit_wait` 시점의 generation을 비교합니다. 값이 바뀌었다면 실제로 sleep하지 않고 호출자가 predicate를 다시 확인하게 합니다.

## reader-writer lock과 seqlock

### reader-writer lock

여러 reader를 허용하고 writer는 독점합니다. 읽기가 많다는 이유만으로 선택하면 안 됩니다.

- writer starvation 또는 reader starvation 규칙
- read에서 write로 upgrade할 때의 deadlock
- 긴 read 구간으로 인한 writer latency
- 관리용 cache line contention

### seqlock

writer가 sequence를 바꾸며 갱신하고 reader는 snapshot을 읽은 뒤 sequence가 바뀌었는지 확인합니다.

- reader는 재시도할 수 있어야 합니다.
- reader가 해제된 object를 따라가면 안 됩니다.
- writer가 오래 걸리면 reader 재시도가 급증합니다.
- memory ordering이 정확해야 합니다.

기본 과정에서는 구현하지 않지만, lock-free read가 object reclamation 문제를 없애지 않는다는 점은 기억해야 합니다.

## barrier와 latch

barrier는 정해진 수의 참가자가 같은 단계에 도착할 때까지 기다립니다. 반복해서 사용하려면 generation이 필요합니다. 참가자 생성이 실패하거나 중간에 빠지면 모든 waiter를 깨울 abort 상태도 필요합니다.

latch는 보통 count가 0이 될 때 한 번 열립니다. 작업 시작 gate, 여러 worker의 완료 대기와 결정론적 test에 사용할 수 있습니다.

## priority inversion

낮은 priority 작업 `L`이 mutex를 잡고, 높은 priority 작업 `H`가 그 mutex를 기다리는 동안 중간 priority 작업 `M`이 `L`을 계속 선점할 수 있습니다.

```text
L: lock 보유
H: lock 대기
M: L을 선점
→ H가 M보다 간접적으로 늦게 실행됩니다.
```

priority inheritance는 `L`이 `H`의 priority를 잠시 상속하게 합니다. 하지만 긴 임계 구역이나 잘못된 lock order를 자동으로 고치지는 않습니다.

## shutdown과 오류 처리

동기화 코드는 정상 경로보다 종료 과정에서 자주 깨집니다.

- 일부 thread 생성 실패
- producer의 조기 종료
- waiter timeout
- shutdown 요청
- lock 획득 뒤 오류 반환
- cancellation과 정상 completion의 경쟁

다음 항목을 미리 정합니다.

```text
누가 shutdown flag를 설정합니까?
어떤 mutex가 그 flag를 보호합니까?
어떤 waiter를 깨워야 합니까?
queue에 남은 item을 처리합니까, 버립니까?
마지막 resource를 누가 해제합니까?
```

## 연결 실습

```sh
make -C examples build/bounded-buffer
./examples/build/bounded-buffer 100

cd exercises/kernel-model
python3 -m unittest tests.test_models.SynchronizationTests -v
python3 kernel-model.py condition examples/condition.json
```

## 완료 기준

- 보호할 predicate를 먼저 작성한 뒤 적절한 동기화 도구를 고를 수 있습니다.
- mutex와 semaphore의 소유 규칙 차이를 설명할 수 있습니다.
- condition wait가 mutex 해제와 wait 등록을 연결해야 하는 이유를 설명할 수 있습니다.
- signal과 broadcast를 predicate 변화량에 따라 선택할 수 있습니다.
- shutdown과 cancellation에서 깨워야 할 waiter와 정리할 자원을 정할 수 있습니다.

## 잘못된 이해

- condition variable이 조건 값을 저장한다고 생각합니다.
- 읽기가 많으면 항상 reader-writer lock이 빠르다고 생각합니다.
- spinlock이 mutex보다 항상 빠르다고 생각합니다.
- semaphore count가 실제 resource 수와 언제나 자동으로 일치한다고 생각합니다.

## 자기 설명

- bounded queue에서 `producer_done`을 `count`와 같은 mutex로 보호해야 하는 이유는 무엇입니까?
- waiter가 있는 semaphore에서 release가 permit을 바로 waiter에게 넘기는 이유는 무엇입니까?
- condition broadcast 뒤 모든 thread가 동시에 진행할 수 없는 이유는 무엇입니까?
