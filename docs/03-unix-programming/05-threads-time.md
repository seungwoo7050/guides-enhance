# 스레드·동기화·시간

여러 스레드가 같은 객체를 읽고 쓸 때는 **어떤 값과 검사를 하나의 논리적 작업으로 보아야 하는지** 먼저 정해야 합니다. 각 필드 접근마다 mutex를 붙이는 것만으로는 여러 값 사이의 관계나 전체 합 같은 불변식(invariant)을 유지할 수 없습니다.

예를 들어 두 계좌 사이의 이체라면 다음을 하나의 논리적 작업으로 봅니다.

```text
출발 계좌 잔액 확인
→ 도착 계좌에서 overflow가 발생하지 않는지 확인
→ 출발 계좌 차감
→ 도착 계좌 증가
```

다른 스레드가 이 과정의 중간 상태를 관찰할 수 없도록 필요한 mutex를 모두 보유한 상태에서 검사와 변경을 끝내야 합니다.

## 스레드 수명

```c
pthread_t thread;

int error = pthread_create(&thread, NULL, worker_main, argument);
if (error != 0) {
    /* error 자체가 오류 번호 */
    return -1;
}

error = pthread_join(thread, NULL);
if (error != 0) {
    return -1;
}
```

- `pthread_create`: 새 스레드를 시작합니다.
- `pthread_join`: 대상 스레드가 끝날 때까지 기다리고 join 가능한 스레드의 자원을 회수합니다.

많은 `pthread_*` 함수는 일반적인 POSIX 시스템 호출처럼 `-1`을 반환하고 `errno`를 설정하는 대신 **오류 번호 자체를 반환**합니다. 따라서 반환값을 직접 검사합니다.

스레드에 넘긴 인자와 스레드가 접근하는 공유 객체는 해당 스레드가 더 이상 접근하지 않을 때까지 살아 있어야 합니다. 가장 단순한 규칙은 모든 작업 스레드를 `pthread_join`한 뒤 공유 객체를 정리하는 것입니다.

```text
공유 객체 초기화
→ 스레드 생성
→ 작업 수행
→ 모든 스레드 join
→ 공유 객체 정리
```

지역 변수의 주소를 스레드에 넘긴 뒤 그 지역 변수의 수명이 먼저 끝나면 안 됩니다.

```c
void start_worker(void) {
    struct context context;

    pthread_create(&thread, NULL, worker_main, &context);

    /* join하지 않고 반환하면 context 수명이 끝날 수 있음 */
}
```

## join과 detach

기본적으로 생성된 스레드는 join 가능한 상태입니다. 스레드 함수가 반환해도 `pthread_join`으로 회수하기 전까지 일부 자원이 남습니다.

`pthread_detach`를 사용한 스레드는 종료 시 자원이 자동 회수되며 나중에 `pthread_join`할 수 없습니다.

```text
join 가능한 스레드
    → pthread_join으로 회수

detach된 스레드
    → pthread_join하지 않음
```

이 문서는 수명 관리가 명확한 join 가능한 작업 스레드를 기준으로 설명합니다.

## mutex 수명

동적으로 초기화하는 mutex의 기본 수명은 다음과 같습니다.

```c
pthread_mutex_t mutex;

int error = pthread_mutex_init(&mutex, NULL);
if (error != 0) {
    /* 초기화 실패 */
}

/* lock / unlock 사용 */

error = pthread_mutex_destroy(&mutex);
if (error != 0) {
    /* 정리 오류 */
}
```

정적으로 초기화할 수도 있습니다.

```c
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
```

mutex를 파괴할 때는 어떤 스레드도 그 mutex를 잠그고 있거나 다시 사용할 가능성이 없어야 합니다.

```text
mutex 초기화
→ 작업 스레드에서 사용
→ 모든 작업 스레드 join
→ mutex destroy
```

초기화된 `pthread_mutex_t` 객체를 `memcpy`나 단순 구조체 복사로 복제해 별개의 mutex처럼 사용하는 것도 피합니다. mutex는 자체 수명과 동기화 상태를 가진 객체로 취급합니다.

## mutex가 보호하는 상태를 명시하기

각 mutex가 어떤 데이터를 보호하는지 문서화해야 합니다.

```c
struct account {
    long id;                /* 초기화 뒤 변경하지 않음 */
    pthread_mutex_t mutex;  /* balance를 보호 */
    long balance;
};
```

이 구조에서는 다음 규칙을 둘 수 있습니다.

```text
balance
    → account.mutex를 보유한 동안만 읽거나 변경

id
    → 초기화 뒤 변경하지 않는 불변 값
    → 잠금 순서 결정에 사용 가능
```

잠금 순서를 결정하는 값이 실행 중 바뀌면 서로 다른 스레드가 다른 순서를 선택할 수 있으므로, 순서 키는 고유하고 변경되지 않는 값이어야 합니다.

## 무엇을 하나의 임계 구역으로 묶을지

두 계좌 사이의 이체에서 다음 전체가 하나의 임계 구역입니다.

```text
출발 계좌 잔액 확인
→ 도착 계좌 overflow 확인
→ 출발 계좌 차감
→ 도착 계좌 증가
```

다음처럼 검사와 변경 사이에 잠금을 풀면 안 됩니다.

```text
출발 계좌 잠금
→ 잔액 충분함 확인
→ 잠금 해제

다른 스레드가 출발 계좌 변경

다시 잠금
→ 이전 검사 결과를 믿고 차감
```

검사 결과가 변경 시점에도 유효하려면 **검사에 필요한 상태와 변경할 상태를 같은 임계 구역에서 보호**해야 합니다.

## 잠금 순서와 교착 상태

스레드 A와 B가 서로 반대 순서로 두 mutex를 잠그면 교착 상태가 생길 수 있습니다.

```text
A: lock(left)  → wait(right)
B: lock(right) → wait(left)
```

이를 피하려면 여러 mutex를 잠그는 모든 코드가 같은 전역 순서를 사용합니다.

예를 들어 계좌 ID가 고유하고 변경되지 않는다면:

```text
ID가 작은 계좌 먼저 잠금
→ ID가 큰 계좌 잠금
```

이체 방향과 잠금 순서는 다를 수 있습니다.

```text
이체:
    source → destination

잠금:
    min(source.id, destination.id)
    → max(source.id, destination.id)
```

반대 방향 이체도 같은 ID 순서를 사용해야 합니다.

## 같은 객체를 두 번 받은 경우

다음처럼 두 인자가 같은 객체일 수 있습니다.

```c
source == destination
```

이때 일반 mutex를 두 번 잠그면 자기 자신이 이미 보유한 mutex를 다시 기다리며 교착 상태가 생길 수 있습니다.

따라서 같은 객체인지 먼저 검사하고 mutex를 한 번만 사용합니다.

자기 이체의 의미는 API에서 정합니다.

```text
성공한 no-op으로 처리
또는
잘못된 요청으로 거부
```

어느 정책이든 두 번 잠그지는 않습니다.

## 같은 ID를 가진 서로 다른 객체

ID를 잠금 순서의 기준으로 사용한다면 다음 경우도 처리해야 합니다.

```text
left != right
left->id == right->id
```

ID만으로는 순서를 정할 수 없으므로 다음 중 하나를 선택합니다.

```text
객체 생성 시 ID의 전역 고유성을 강제
또는
같은 ID를 가진 서로 다른 객체의 다중 객체 연산을 거부
```

서로 관계없는 객체 포인터를 `<`로 비교해 이식 가능한 전역 순서를 만든다고 가정하지 않습니다. 잠금 순서용 값이 필요하면 별도의 고유하고 변경되지 않는 순서 키를 두는 편이 명확합니다.

## 실패 시 잠금 해제

두 번째 mutex를 잠그는 데 실패하면 첫 번째 mutex를 풀어야 합니다.

```c
int error = pthread_mutex_lock(&first->mutex);
if (error != 0) {
    return -1;
}

error = pthread_mutex_lock(&second->mutex);
if (error != 0) {
    pthread_mutex_unlock(&first->mutex);
    return -1;
}
```

모든 반환 경로에서 이미 획득한 잠금을 추적해야 합니다.

```text
first lock 성공
→ second lock 성공
→ 검증 실패
→ second unlock
→ first unlock
→ 오류 반환
```

보통 획득 순서의 역순으로 해제하면 오류 경로를 이해하기 쉽습니다.

## 이체 예시

다음 예시는 다음 정책을 가정합니다.

```text
amount < 0은 오류
자기 이체는 성공한 no-op
서로 다른 객체의 ID는 고유
잔액은 음수가 될 수 없음
```

```c
#include <limits.h>

int transfer(struct account *source,
             struct account *destination,
             long amount)
{
    if (source == NULL || destination == NULL) {
        return -1;
    }

    if (amount < 0) {
        return -1;
    }

    if (source == destination) {
        return 0;
    }

    if (source->id == destination->id) {
        return -1;
    }

    struct account *first =
        source->id < destination->id ? source : destination;
    struct account *second =
        source->id < destination->id ? destination : source;

    int error = pthread_mutex_lock(&first->mutex);
    if (error != 0) {
        return -1;
    }

    error = pthread_mutex_lock(&second->mutex);
    if (error != 0) {
        pthread_mutex_unlock(&first->mutex);
        return -1;
    }

    int result = 0;

    if (source->balance < amount) {
        result = -1;
        goto out;
    }

    if (destination->balance > LONG_MAX - amount) {
        result = -1;
        goto out;
    }

    source->balance -= amount;
    destination->balance += amount;

out:
    pthread_mutex_unlock(&second->mutex);
    pthread_mutex_unlock(&first->mutex);
    return result;
}
```

`destination->balance + amount`를 먼저 계산한 뒤 overflow가 났는지 검사하면 이미 C의 signed integer overflow가 발생했을 수 있습니다. 따라서 **계산 전에** 안전한 범위인지 검사합니다.

## 일관된 한 시점의 값

두 계좌의 합을 읽을 때 각 계좌를 따로 잠그면 두 읽기 사이에 이체가 들어올 수 있습니다.

```text
초기:
left  = 100
right = 100

조회:
left를 잠그고 100 읽음
→ 잠금 해제

다른 스레드:
left에서 right로 50 이체
left  = 50
right = 150

조회:
right를 잠그고 150 읽음
```

조회 결과는 `250`이지만 실제 총합은 계속 `200`이었습니다. 서로 다른 시점의 값을 조합한 것입니다.

두 값을 하나의 스냅샷으로 읽어야 한다면 이체 코드와 같은 순서로 두 mutex를 모두 잠근 뒤 읽습니다.

```text
lock(first)
→ lock(second)
→ left 읽기
→ right 읽기
→ unlock(second)
→ unlock(first)
```

쓰기와 읽기 모두 같은 잠금 순서를 사용해야 교착 상태를 피할 수 있습니다.

## 출력 매개변수 갱신 시점

실패 시 출력 매개변수를 변경하지 않는 계약이라면 성공이 확정된 뒤에만 값을 씁니다.

```c
int account_get_balance(struct account *account, long *out_balance) {
    if (account == NULL || out_balance == NULL) {
        return -1;
    }

    long value;

    int error = pthread_mutex_lock(&account->mutex);
    if (error != 0) {
        return -1;
    }

    value = account->balance;

    error = pthread_mutex_unlock(&account->mutex);
    if (error != 0) {
        return -1;
    }

    *out_balance = value;
    return 0;
}
```

여러 출력값을 같은 스냅샷으로 반환할 때도 먼저 지역 변수에 저장하고 잠금 처리까지 성공한 뒤 호출자의 출력 위치에 반영하는 방식이 명확합니다.

## 조건 변수

스레드가 특정 조건이 참이 될 때까지 기다려야 한다면 busy loop보다 조건 변수를 사용합니다.

```c
pthread_mutex_lock(&mutex);

while (!ready) {
    pthread_cond_wait(&condition, &mutex);
}

pthread_mutex_unlock(&mutex);
```

`pthread_cond_wait`는 개념적으로 다음 작업을 연결합니다.

```text
mutex를 놓고 대기 상태로 들어감
→ 깨워짐
→ mutex를 다시 획득
→ 호출자에게 반환
```

이 "잠금 해제와 대기 진입"이 원자적으로 연결되므로 다음 경쟁을 피할 수 있습니다.

```text
조건 확인
→ mutex를 따로 unlock
→ 실제 wait 전에 signal 발생
→ 깨우기 신호를 놓침
```

## 조건 변수와 predicate

조건 변수 자체가 "사건이 몇 번 발생했는가"를 저장하는 큐는 아닙니다. 실제 상태는 `ready` 같은 predicate가 나타냅니다.

```text
condition variable:
    상태가 바뀌었을 수 있으니 다시 확인하라는 알림

predicate:
    실제로 진행해도 되는지를 나타내는 공유 상태
```

predicate의 읽기와 쓰기는 같은 mutex로 보호합니다.

```c
pthread_mutex_lock(&mutex);

ready = 1;
pthread_cond_broadcast(&condition);

pthread_mutex_unlock(&mutex);
```

## 왜 `while`로 다시 검사하는가

다음처럼 `if`만 사용하면 부족합니다.

```c
if (!ready) {
    pthread_cond_wait(&condition, &mutex);
}
```

조건 변수는 다음 이유로 깨어날 수 있습니다.

```text
spurious wakeup
다른 스레드가 조건을 먼저 소비
broadcast로 여러 스레드가 함께 깨어났지만 일부만 진행 가능
```

따라서 깨어난 뒤 mutex를 다시 획득한 상태에서 predicate를 재검사합니다.

```c
while (!ready) {
    pthread_cond_wait(&condition, &mutex);
}
```

## `signal`과 `broadcast`

`pthread_cond_signal`은 대기 중인 스레드 중 적어도 하나를 깨우는 데 사용하고, `pthread_cond_broadcast`는 현재 대기 중인 모든 스레드를 깨웁니다.

```text
상태 변화로 한 스레드만 진행 가능
    → signal 검토

상태 변화로 여러 스레드가 모두 다시 판단해야 함
    → broadcast 검토
```

어느 함수를 사용할지는 "몇 개의 대기자가 깨워져야 하는가"라는 predicate의 의미에 따라 결정합니다.

## 조건 변수 수명

조건 변수도 사용 전에 초기화하고 더 이상 대기자가 없을 때 파괴합니다.

```c
pthread_cond_t condition;

pthread_cond_init(&condition, NULL);

/* 사용 */

pthread_cond_destroy(&condition);
```

보통 다음 순서가 단순합니다.

```text
종료 predicate 설정
→ 필요한 대기 스레드 깨우기
→ 모든 작업 스레드 join
→ condition destroy
→ mutex destroy
```

대기 중인 스레드가 있는데 조건 변수나 관련 mutex를 파괴하면 안 됩니다.

## 시작 시점 맞추기

동시성 테스트에서 작업 스레드를 생성하자마자 각각 실행시키면 먼저 생성된 스레드가 뒤의 스레드가 준비되기 전에 작업을 대부분 끝낼 수 있습니다.

mutex와 조건 변수로 시작 gate를 만들면 시작 시점의 편차를 줄일 수 있습니다.

```c
struct start_gate {
    pthread_mutex_t mutex;
    pthread_cond_t condition;
    size_t ready_count;
    size_t expected_count;
    int open;
};
```

작업 스레드:

```text
gate mutex 잠금
→ ready_count 증가
→ main에 준비 상태 알림
→ open이 참이 될 때까지 condition wait
→ gate mutex 해제
→ 실제 작업 시작
```

main:

```text
모든 작업 스레드 생성
→ ready_count == expected_count가 될 때까지 대기
→ open = 1
→ broadcast
```

이 구조는 모든 스레드가 CPU에서 정확히 동시에 실행된다는 보장은 하지 않습니다. 다만 우연히 순차적으로 실행되는 테스트보다 경쟁 상황을 만들 가능성을 높입니다.

## 시간 측정

경과 시간이나 timeout을 계산할 때는 시스템 달력 시각 변경의 영향을 받지 않는 **단조 시계(monotonic clock)** 를 사용합니다.

```c
struct timespec now;

if (clock_gettime(CLOCK_MONOTONIC, &now) == -1) {
    /* 오류 처리 */
}
```

목적을 구분합니다.

```text
CLOCK_MONOTONIC
    → 경과 시간, timeout, deadline

CLOCK_REALTIME
    → 실제 날짜와 시각
```

시스템 관리자가 벽시계를 바꾸거나 실시간 시각 보정이 일어나도 경과 시간 계산이 갑자기 뒤로 가지 않도록 하는 것이 `CLOCK_MONOTONIC` 사용의 핵심입니다.

## `timespec` 계산

`struct timespec`은 초와 나노초를 따로 저장합니다.

```c
struct timespec {
    time_t tv_sec;
    long tv_nsec;
};
```

정규화된 `tv_nsec` 범위는 다음과 같습니다.

```text
0 <= tv_nsec < 1,000,000,000
```

두 시각의 차이를 계산할 때 나노초 부분이 음수가 되면 초에서 1을 빌려 정규화합니다.

```c
struct timespec timespec_sub(struct timespec end,
                            struct timespec start)
{
    struct timespec result;

    result.tv_sec = end.tv_sec - start.tv_sec;
    result.tv_nsec = end.tv_nsec - start.tv_nsec;

    if (result.tv_nsec < 0) {
        result.tv_sec -= 1;
        result.tv_nsec += 1000000000L;
    }

    return result;
}
```

deadline에 시간을 더할 때도 `tv_nsec >= 1000000000L`이면 초로 올려 정규화해야 합니다.

## 조건 변수 timeout과 clock

`pthread_cond_timedwait`는 상대 시간이 아니라 **절대 deadline**을 받습니다.

```c
pthread_cond_timedwait(&condition, &mutex, &deadline);
```

여기서 중요한 것은 조건 변수가 사용하는 clock과 deadline을 계산한 clock이 일치해야 한다는 점입니다.

기본 조건 변수는 일반적으로 `CLOCK_REALTIME`을 사용합니다. 지원되는 환경에서는 조건 변수 속성을 설정해 `CLOCK_MONOTONIC`을 사용할 수 있습니다.

```c
pthread_condattr_t attr;

pthread_condattr_init(&attr);
pthread_condattr_setclock(&attr, CLOCK_MONOTONIC);
pthread_cond_init(&condition, &attr);
pthread_condattr_destroy(&attr);
```

이 경우 deadline도 `CLOCK_MONOTONIC`으로 계산합니다.

```text
condition의 clock
    ==
deadline 계산에 사용한 clock
```

서로 다른 clock을 섞으면 timeout이 즉시 끝나거나 예상보다 훨씬 오래 기다리는 잘못된 동작이 생길 수 있습니다.

## Sleep 정확도

`nanosleep` 같은 함수는 "정확히 그 시간이 지난 순간 실행을 재개한다"는 예약 기능이 아닙니다.

```text
요청한 시간이 지나야 깨어날 수 있음
+ scheduler 지연
+ 시스템 부하
```

따라서 실제 재개 시점은 더 늦을 수 있습니다.

```c
struct timespec request = {
    .tv_sec = 0,
    .tv_nsec = 10 * 1000 * 1000
};

nanosleep(&request, NULL);
```

이를 "정확히 10ms마다 실행된다"는 의미로 해석하면 안 됩니다.

## `nanosleep`과 `EINTR`

`nanosleep`은 시그널에 의해 중단될 수 있습니다. 남은 시간을 계속 기다리려면 반환된 `remaining`을 사용합니다.

```c
struct timespec request = desired;
struct timespec remaining;

while (nanosleep(&request, &remaining) == -1) {
    if (errno != EINTR) {
        break;
    }

    request = remaining;
}
```

그러나 주기적인 작업에서는 매번 "상대 시간만큼 다시 sleep"하면 작업 시간과 scheduler 지연이 반복마다 누적될 수 있습니다.

## 절대 deadline 사용하기

종료 시각이나 반복 주기가 중요하다면 시작 시점에서 절대 deadline을 계산하고 현재 단조 시각과 비교합니다.

```text
deadline = 시작 시각 + 1초

반복:
    now = CLOCK_MONOTONIC
    if now >= deadline:
        종료
    남은 시간만 대기
```

지원 환경에서는 다음처럼 절대 시각 기반 sleep도 사용할 수 있습니다.

```c
clock_nanosleep(CLOCK_MONOTONIC,
                TIMER_ABSTIME,
                &deadline,
                NULL);
```

절대 deadline을 기준으로 하면 이전 반복에서 생긴 지연이 다음 대기 시간에 그대로 누적되는 문제를 줄일 수 있습니다.

## timeout 테스트

교착 상태 검출용 timeout은 테스트가 영원히 멈추지 않도록 하는 안전 장치입니다.

다만 정상 실행이 20ms 정도라고 해서 timeout을 21ms로 잡으면 느린 CI 머신이나 높은 시스템 부하에서 거짓 실패가 발생할 수 있습니다.

목적을 구분합니다.

```text
성능 요구사항 검증
    → 실제 요구 시간에 맞춘 엄격한 제한

교착 상태 방지용 테스트 timeout
    → 정상 실행 시간보다 충분히 넉넉한 제한
```

## 데이터 경합과 논리 오류

데이터 경합(data race)은 동기화되지 않은 접근 중 적어도 하나가 쓰기이고 여러 스레드가 같은 메모리 위치에 동시에 접근하는 상황입니다.

ThreadSanitizer는 이런 문제를 찾는 데 도움이 됩니다.

```c
/* 여러 스레드가 동기화 없이 접근하면 데이터 경합 가능 */
shared_counter++;
```

하지만 ThreadSanitizer가 통과했다고 동시성 논리가 모두 올바른 것은 아닙니다.

다음 문제는 별도로 검사해야 합니다.

- 잘못된 잠금 순서로 인한 교착 상태
- mutex로 보호했지만 계산 자체가 잘못된 경우
- 여러 값을 서로 다른 시점에 읽는 논리 오류
- 조건 변수 predicate를 잘못 정의한 경우
- `signal`과 `broadcast` 선택이 잘못된 경우
- 특정 실행 순서를 테스트가 만들지 못한 경우
- timeout에 잘못된 clock을 사용하는 경우

도구 검출과 프로그램의 불변식 검사를 함께 사용합니다.

## 불변식 테스트

두 계좌 사이에서 돈만 이동한다면 전체 합은 변하지 않아야 합니다.

```text
left.balance + right.balance == initial_total
```

이 합을 읽을 때도 두 mutex를 같은 순서로 잠가야 실제 한 시점의 상태를 검사할 수 있습니다.

테스트 구조:

```text
여러 transfer 스레드
+
전체 합을 반복 확인하는 observer 스레드
```

observer가 항상 같은 총합을 확인하는지 검사하면 단순히 "데이터 경합이 없다"보다 강한 논리적 정확성을 검증할 수 있습니다.

## 초기화되지 않은 객체

`NULL`은 API가 명확하게 검사할 수 있습니다.

```c
if (account == NULL) {
    return -1;
}
```

하지만 실제로 초기화되지 않은 `pthread_mutex_t`를 잠가 보고 오류가 반환되기를 기대해서는 안 됩니다. 초기화되지 않은 동기화 객체를 사용하는 것은 유효한 프로그램 상태가 아니며 구현이 이를 항상 감지해 준다는 보장도 없습니다.

따라서 객체 수명 자체를 API 계약으로 정의합니다.

```text
account_init 성공
→ account API 사용 가능
→ 모든 작업 스레드 종료
→ account_destroy
→ 이후 사용 금지
```

초기화 여부를 별도 필드로 추적하는 설계를 사용할 수는 있지만, 그 필드 자체도 객체 메모리가 유효하고 정상적으로 초기화되었다는 전제 안에서만 읽어야 합니다.

## 테스트할 내용

- `NULL` 인자
- 정상 초기화 전 객체를 사용하지 않는 수명 규칙
- 음수 금액
- 잔액 부족
- 도착 계좌 overflow
- 0원 이체 정책
- 자기 이체 정책
- 같은 ID의 서로 다른 객체 처리
- 반대 방향 이체 작업 스레드 여러 개
- 모든 다중 객체 작업이 같은 잠금 순서를 사용하는지
- 전체 합을 반복해서 읽는 조회 스레드
- 조회가 항상 한 시점의 일관된 값을 읽는지
- 시작 gate를 사용한 동시성 부하 테스트
- 조건 변수 predicate를 `while`로 재검사하는지
- `signal`과 `broadcast` 정책
- 조건 변수 timeout의 clock과 deadline clock 일치 여부
- `nanosleep`이 `EINTR`로 중단되는 경우
- 절대 deadline 기반 시간 계산
- 넉넉한 제한 시간으로 교착 상태 검출
- 모든 작업 스레드를 `pthread_join`한 뒤 condition과 mutex 정리
- join 가능한 스레드를 빠뜨리지 않고 모두 회수하는지
- 반복 부하 테스트에서 유지해야 하는 불변식
- 지원 환경의 ThreadSanitizer

## 완료 기준

1. 작업 스레드가 사용하는 인자와 공유 객체를 해당 스레드가 종료하고 `pthread_join`될 때까지 유지합니다.
2. `pthread_*` 함수가 일반적으로 오류 번호 자체를 반환한다는 점을 일반 `errno` 기반 시스템 호출과 구분합니다.
3. join 가능한 스레드와 detach된 스레드의 수명 규칙을 구분합니다.
4. mutex와 조건 변수를 사용 전에 초기화하고 모든 사용자 스레드가 끝난 뒤 정리합니다.
5. 각 mutex가 보호하는 공유 상태를 구체적으로 설명합니다.
6. 검사와 관련 상태 변경을 하나의 임계 구역에서 수행합니다.
7. 여러 mutex를 사용하는 모든 코드가 같은 전역 잠금 순서를 따릅니다.
8. 같은 객체를 두 번 받은 경우 같은 mutex를 중복 잠그지 않습니다.
9. 잠금 순서 키는 고유하고 변경되지 않도록 하거나 같은 키의 서로 다른 객체를 명시적으로 처리합니다.
10. 실패 경로에서도 이미 획득한 모든 mutex를 해제합니다.
11. 여러 값을 한 시점의 스냅샷으로 읽을 때도 쓰기 코드와 같은 잠금 순서를 사용합니다.
12. 실패 시 출력 매개변수를 유지하는 계약이라면 성공이 확정된 뒤에만 출력값을 갱신합니다.
13. 조건 변수의 실제 상태는 predicate가 나타내며 대기 후에는 `while`로 다시 검사합니다.
14. predicate의 읽기와 변경은 같은 mutex로 보호합니다.
15. 필요하면 시작 gate로 동시성 테스트의 시작 편차를 줄입니다.
16. 경과 시간과 timeout 계산에 `CLOCK_MONOTONIC` 같은 단조 시계를 사용합니다.
17. `pthread_cond_timedwait`의 조건 변수 clock과 deadline 계산에 사용하는 clock을 일치시킵니다.
18. sleep 함수가 정확한 재개 시각을 보장하지 않으며 `EINTR`과 scheduler 지연을 고려합니다.
19. 반복 시간 제어에서는 필요하면 상대 sleep보다 절대 deadline을 사용해 누적 오차를 줄입니다.
20. ThreadSanitizer 통과와 교착 상태·불변식·조건 변수 논리의 정확성을 별도로 검증합니다.
