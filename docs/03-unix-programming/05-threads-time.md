# 스레드·동기화·시간

여러 스레드가 같은 객체를 읽고 쓸 때는 어떤 값들을 하나의 작업으로 보아야 하는지 먼저 정해야 합니다. 단순히 각 필드 접근마다 mutex를 붙이는 것만으로는 두 값 사이의 관계나 전체 합이 유지되지 않을 수 있습니다.

## 스레드 수명

```c
pthread_t thread;

if (pthread_create(&thread, NULL, worker_main, argument) != 0) {
    return -1;
}
if (pthread_join(thread, NULL) != 0) {
    return -1;
}
```

- `pthread_create`: 새 스레드를 시작합니다.
- `pthread_join`: 스레드가 끝날 때까지 기다리고 자원을 회수합니다.

스레드가 사용하는 인자와 공유 객체는 `pthread_join`이 끝날 때까지 살아 있어야 합니다.

## mutex 수명

```c
pthread_mutex_t mutex;

pthread_mutex_init(&mutex, NULL);
pthread_mutex_lock(&mutex);
/* 공유 상태 읽기 또는 변경 */
pthread_mutex_unlock(&mutex);
pthread_mutex_destroy(&mutex);
```

mutex를 정리할 때 어떤 스레드도 잠그고 있거나 다시 사용할 수 없어야 합니다. 모든 작업 스레드가 `pthread_join`으로 끝난 뒤 정리하는 순서가 단순합니다.

## 무엇을 하나의 임계 구역으로 묶을지

두 계좌 사이의 이체를 예로 들면 다음 검사가 하나의 작업입니다.

```text
출발 계좌 잔액 확인
→ 도착 계좌 오버플로 확인
→ 출발 계좌 차감
→ 도착 계좌 증가
```

중간에 mutex를 풀면 다른 스레드가 일부만 반영된 상태를 볼 수 있습니다. 두 계좌의 mutex를 모두 보유한 상태에서 검사와 두 변경을 함께 수행합니다.

## 잠금 순서와 교착 상태

스레드 A가 `left`를 잠그고 `right`를 기다리며, 스레드 B가 `right`를 잠그고 `left`를 기다리면 교착 상태가 생깁니다.

```text
A: lock(left)  → wait(right)
B: lock(right) → wait(left)
```

모든 두 객체 작업이 같은 순서를 사용하도록 정합니다.

```text
ID가 작은 계좌 먼저 잠금
→ ID가 큰 계좌 잠금
```

반대 방향 이체도 실제 출발·도착 순서가 아니라 ID 순서를 사용합니다.

같은 객체를 두 번 전달한 경우 mutex를 한 번만 잠급니다. 서로 다른 객체의 ID가 같으면 순서를 정할 수 없으므로 거부하도록 정할 수 있습니다.

## 실패 시 잠금 해제

두 번째 mutex를 잠그는 데 실패하면 첫 번째 mutex를 풀어야 합니다.

```c
if (pthread_mutex_lock(&first->mutex) != 0) {
    return -1;
}
if (pthread_mutex_lock(&second->mutex) != 0) {
    pthread_mutex_unlock(&first->mutex);
    return -1;
}
```

모든 반환 경로에서 이미 얻은 잠금을 확인합니다.

## 일관된 한 시점의 값

두 계좌의 합을 읽을 때 각 계좌를 따로 잠그면 두 읽기 사이에 이체가 들어올 수 있습니다.

```text
left 읽기
→ 다른 스레드가 left에서 right로 이체
→ right 읽기
```

이 경우 실제 어느 시점에도 존재하지 않았던 합을 계산할 수 있습니다. 두 mutex를 같은 순서로 잠근 뒤 두 값을 읽습니다.

## 출력 매개변수 갱신 시점

```c
long value;

pthread_mutex_lock(&account->mutex);
value = account->balance;
pthread_mutex_unlock(&account->mutex);
*out_balance = value;
```

잠금과 읽기가 성공한 뒤에만 출력 매개변수를 바꿉니다. 실패 시 호출자가 넣어 둔 값은 유지됩니다.

## 조건 변수

스레드가 특정 조건이 참이 될 때까지 기다려야 한다면 busy loop보다 조건 변수를 사용할 수 있습니다.

```c
pthread_mutex_lock(&mutex);
while (!ready) {
    pthread_cond_wait(&condition, &mutex);
}
pthread_mutex_unlock(&mutex);
```

`pthread_cond_wait`는 mutex를 풀고 기다린 뒤 깨어날 때 다시 잠급니다. 이유 없이 깨어나는 상황이 가능하므로 조건은 `if`가 아니라 `while`로 다시 확인합니다.

## 시작 시점 맞추기

동시성 테스트에서 모든 작업 스레드를 비슷한 시점에 시작하려면 mutex와 조건 변수로 gate를 만들 수 있습니다.

```text
각 작업 스레드가 ready 수 증가
→ main이 expected 수까지 대기
→ open = 1
→ 전체 스레드를 깨움
```

이렇게 하면 우연히 순차적으로 끝나는 테스트보다 잠금 순서와 데이터 경합 문제를 드러내기 쉽습니다.

## 시간 측정

경과 시간을 재거나 timeout을 계산할 때는 시스템 시각 변경의 영향을 받지 않는 단조 시계를 사용합니다.

```c
struct timespec now;
clock_gettime(CLOCK_MONOTONIC, &now);
```

실제 달력 시각이 필요한 경우에는 실시간 시계를 사용하지만, 경과 시간 계산과 목적을 구분합니다.

## Sleep 정확도

`usleep`, `nanosleep`은 최소한 그 시간만큼 기다리는 요청에 가깝습니다. scheduler 때문에 더 늦게 깨어날 수 있습니다. 짧은 짧은 대기를 반복하며 정확한 시각을 보장한다고 가정하지 않습니다.

종료 조건과 종료 시각을 현재 단조 시각으로 다시 계산합니다.

## 데이터 경합과 논리 오류

ThreadSanitizer는 동기화 없이 동시에 접근한 메모리를 찾는 데 도움이 됩니다. 하지만 다음 문제를 모두 찾아주지는 않습니다.

- 잘못된 잠금 순서로 인한 교착 상태
- mutex로 보호했지만 잘못 계산한 값
- 대기 조건을 잘못 정의한 경우
- 관찰하지 못한 실행 순서

제한 시간, 반복 부하 테스트와 유지해야 하는 값 검사를 함께 사용합니다.

## 테스트할 내용

- `NULL`과 초기화되지 않은 객체
- 음수 금액과 잔액 부족
- 도착 계좌 오버플로
- 0원 이체와 자기 이체
- 같은 ID의 서로 다른 객체
- 반대 방향 이체 작업 스레드 여러 개
- 전체 합을 반복해서 읽는 조회 스레드
- 제한 시간으로 교착 상태 검출
- 모든 스레드를 `pthread_join`한 뒤 mutex 정리
- 지원 환경의 ThreadSanitizer

## 완료 기준

1. 작업 스레드가 사용하는 객체를 `pthread_join` 전까지 유지합니다.
2. mutex가 보호하는 값을 구체적으로 설명합니다.
3. 여러 mutex를 항상 같은 순서로 잠급니다.
4. 검사와 관련된 상태 변경을 한 임계 구역에서 수행합니다.
5. 여러 값을 같은 시점의 상태로 같은 잠금 순서로 읽습니다.
6. 조건 변수 대기를 `while`로 다시 검사합니다.
7. 경과 시간 계산에 단조 시계를 사용합니다.
8. ThreadSanitizer 통과와 논리적 정확성을 구분합니다.
