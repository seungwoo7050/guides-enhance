# 경쟁, 원자성과 순서

## 학습 목표

- race condition, 언어 수준의 data race, atomicity, visibility와 ordering을 구분합니다.
- 복합 갱신이 깨지는 실행 순서를 결정론적으로 재현합니다.
- atomic operation만으로 해결되지 않는 자원 수명과 여러 값 사이의 불변식을 찾습니다.

## 동시성과 병렬성

```text
동시성
- 여러 작업의 진행 구간이 겹칩니다.
- CPU 하나에서도 선점과 block으로 실행 순서가 섞일 수 있습니다.

병렬성
- 여러 CPU 또는 실행 장치가 실제로 같은 시간에 명령을 수행합니다.
- cache coherence와 memory ordering 문제가 더 직접적으로 나타날 수 있습니다.
```

CPU가 하나여도 `read → 계산 → write` 사이에 다른 작업이 실행될 수 있습니다. 따라서 single-core라는 이유만으로 공유 상태가 안전해지지는 않습니다.

## race condition과 data race

race condition은 결과가 사건 순서에 의존하는 넓은 문제입니다.

```text
A: 잔액 확인 → 충분함
B: 잔액 확인 → 충분함
A: 인출
B: 인출
```

각 memory access를 lock으로 보호해 data race가 없어도, 확인과 변경이 한 번에 처리되지 않으면 전체 규칙은 깨질 수 있습니다.

data race는 언어 memory model이 정의하는 더 좁은 문제입니다. 같은 memory location에 대한 상충 접근 중 하나 이상이 write이고, 필요한 동기화 관계가 없을 때 발생합니다. C와 C++에서는 data race가 undefined behavior를 만들 수 있습니다.

문제를 분석할 때는 다음을 적습니다.

```text
어떤 값이 공유됩니까?
한 번에 끝나야 하는 갱신은 어디까지입니까?
어떤 write가 어떤 read보다 먼저 보여야 합니까?
중간 상태를 다른 작업이 볼 수 있습니까?
실패하거나 선점돼도 유지해야 할 관계는 무엇입니까?
```

## atomicity는 한 번에 보이는 범위를 정합니다

load와 store가 각각 atomic이어도 복합 증가가 atomic인 것은 아닙니다.

```text
초기 counter = 0

A: load → 0
B: load → 0
A: 계산 → 1
B: 계산 → 1
A: store 1
B: store 1

예상 2, 실제 1
```

`examples/lost-update.c`는 barrier로 이 순서를 고정합니다.

```sh
make -C examples build/lost-update
./examples/build/lost-update split 100
./examples/build/lost-update fetch-add 100
```

- `split`은 atomic load와 store를 따로 사용합니다.
- `fetch-add`는 read-modify-write를 하나의 atomic operation으로 처리합니다.

한 변수의 단순 증가에는 atomic RMW가 충분할 수 있습니다. 반면 queue의 `head`, `tail`, `count`와 slot 내용처럼 여러 값이 함께 바뀌면 mutex 또는 더 넓은 직렬화가 필요합니다.

## visibility와 ordering

다음 두 값을 생각해 봅니다.

```text
data = 준비한 실제 값
ready = data가 준비됐음을 알리는 값
```

producer가 `data`를 쓴 뒤 `ready`를 설정하고, consumer가 `ready`를 본 뒤 `data`를 읽고 싶다고 가정합니다. 필요한 조건은 두 가지입니다.

1. `ready`의 read와 write가 올바르게 동기화됩니다.
2. consumer가 준비 상태를 본 경우 그보다 앞선 `data` write도 볼 수 있습니다.

두 번째 조건은 ordering과 publication의 문제입니다. 흔히 producer의 release operation과 consumer의 acquire operation을 연결합니다.

```text
producer
일반 data write
release publish

consumer
acquire observe
일반 data read
```

정확한 규칙은 사용하는 언어의 memory model을 따라야 합니다. 이 문서는 공통 원리까지만 다룹니다.

## 참가자 barrier와 memory fence

`barrier`라는 말은 두 가지로 쓰일 수 있습니다.

### 참가자 barrier

여러 thread가 같은 단계에 도착할 때까지 다음 단계로 넘어가지 않게 합니다. `lost-update.c`에서는 특정 실행 순서를 반복해서 만들기 위해 사용합니다.

### memory fence

한 thread 안의 memory access 순서와 다른 thread가 관찰할 수 있는 순서를 제한합니다.

둘은 같은 기능이 아닙니다. 참가자 barrier가 내부적으로 mutex, condition 또는 atomic을 사용하더라도, 필요한 memory ordering이 무엇인지는 구현을 확인해야 합니다.

## 임계 구역은 줄 수가 아니라 불변식으로 정합니다

bounded queue에는 다음 관계가 있습니다.

```text
0 <= count <= capacity
head와 tail은 배열 범위 안에 있습니다.
count == 0이면 pop할 수 없습니다.
count == capacity이면 push할 수 없습니다.
실제 저장한 item 수와 count가 같습니다.
```

`head`와 `tail`을 각각 다른 lock으로 보호해도 `count`와 slot 내용이 함께 바뀌는 동안 중간 상태가 보이면 전체 관계가 깨질 수 있습니다.

임계 구역을 정할 때는 다음 순서를 사용합니다.

1. 항상 참이어야 할 관계를 적습니다.
2. 그 관계를 읽거나 바꾸는 연산을 찾습니다.
3. 중간 상태를 다른 작업이 볼 수 있는지 확인합니다.
4. 실패와 조기 반환도 같은 lock 규칙을 따르는지 확인합니다.
5. 정확성을 확보한 뒤 실제 contention을 측정합니다.

## interrupt handler도 동시에 실행될 수 있습니다

kernel에서는 일반 thread뿐 아니라 다음 실행 주체가 같은 상태를 바꿀 수 있습니다.

- process 또는 thread context
- interrupt handler
- timer callback
- deferred worker
- 다른 CPU의 kernel path

현재 CPU에서 interrupt를 잠시 막아도 다른 CPU의 접근까지 막지는 못합니다. 반대로 sleep 가능한 mutex는 interrupt context에서 사용할 수 없는 경우가 있습니다.

```text
현재 문맥은 sleep할 수 있습니까?
다른 CPU가 같은 값을 바꿀 수 있습니까?
interrupt handler가 같은 lock을 사용합니까?
lock을 잡은 채 completion을 기다리지는 않습니까?
```

## 원자적 상태 전이와 자원 수명

다음 상태 변경을 compare-and-swap으로 처리한다고 가정합니다.

```text
PENDING → COMPLETED
PENDING → CANCELLED
```

둘 중 하나만 성공하게 하면 중복 completion을 줄일 수 있습니다. 하지만 다음 문제는 별도로 해결해야 합니다.

- 결과 buffer를 언제 해제합니까?
- 경쟁에서 진 호출자가 가진 참조는 누가 반납합니까?
- completion 결과를 user가 받기 전 어디에 보관합니까?
- 늦은 interrupt가 재사용한 request id를 잘못 완료할 수 있습니까?

atomic state는 승자를 정할 뿐입니다. request object, buffer와 queue 위치의 수명은 별도 불변식으로 관리해야 합니다.

## 결정론적 재현

동시성 오류를 `sleep`과 반복 횟수에만 의존해 재현하면 machine load에 따라 결과가 달라집니다. 먼저 다음 도구로 문제가 되는 순서를 고정합니다.

- barrier
- latch
- 명시적 event
- fixture로 제공한 상태 전이
- single-thread simulator에서 여러 작업의 step을 번갈아 실행

순서를 고정한 뒤 실제 병렬 실행으로 확장합니다.

## 연결 실습

```sh
make -C examples build/lost-update
./examples/build/lost-update split 100
./examples/build/lost-update fetch-add 100

cd exercises/kernel-model
python3 -m unittest tests.test_models.SynchronizationTests -v
```

## 완료 기준

- race condition과 data race를 서로 다른 예로 설명할 수 있습니다.
- atomic load/store 두 개와 atomic RMW 하나가 다른 이유를 설명할 수 있습니다.
- visibility와 ordering이 atomicity와 별개인 이유를 설명할 수 있습니다.
- 여러 값에 걸친 불변식을 기준으로 임계 구역을 정할 수 있습니다.
- atomic state를 사용해도 자원 수명 문제가 남는 예를 들 수 있습니다.

## 잘못된 이해

- 정수 read와 write가 atomic이면 복합 연산도 안전하다고 생각합니다.
- CPU 하나에서는 race condition이 생기지 않는다고 생각합니다.
- 참가자 barrier와 memory fence를 같은 기능으로 봅니다.
- atomic flag 하나로 object lifetime과 cleanup까지 해결됐다고 생각합니다.

## 자기 설명

- data race 없이도 race condition이 남을 수 있는 이유는 무엇입니까?
- `ready`를 본 consumer가 `data`의 최신 값을 봐야 한다면 어떤 ordering이 필요합니까?
- queue의 `head`와 `count`를 따로 잠그기 전에 확인할 불변식은 무엇입니까?
