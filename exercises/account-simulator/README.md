# account-simulator

`account-simulator`는 여러 스레드가 두 계좌 사이에서 동시에 이체하고 잔액을 읽어도 다음 불변식이 유지되도록 구현한 C 라이브러리입니다.

```text
각 계좌의 balance >= 0
성공한 이체는 한 계좌에서 뺀 금액만큼 다른 계좌에 더함
두 계좌 사이의 이체만으로는 두 잔액의 합이 바뀌지 않음
```

여러 스레드가 서로 반대 방향으로 동시에 이체하더라도 **항상 같은 계좌 순서로 mutex를 획득**하여 교착 상태를 막습니다.

## 제공 기능

- 각 계좌 객체가 자신의 `pthread_mutex_t`를 소유
- 음수 초기 잔액과 음수 이체 금액 거부
- 잔액 부족과 목적지 `LONG_MAX` overflow 검사
- 두 잔액을 모두 잠근 상태에서 이체
- 같은 account로 보내는 이체와 0원 이체 처리
- 작은 account ID부터 잠그는 고정 순서
- 한 account의 잔액 조회와 두 account의 합계 조회
- 이체 스레드와 조회 스레드를 동시에 실행하는 부하 테스트

## 객체 수명과 사용 순서

```text
account_init
→ 여러 스레드에서 조회·이체
→ 모든 스레드 join
→ account_destroy
```

`account_init`이 성공한 뒤부터 `account_destroy`를 호출하기 전까지 계좌 객체는 초기화된 상태입니다.

초기화된 객체의 `id`, `balance`, `initialized` 같은 내부 상태를 호출자가 직접 변경하면 안 됩니다. 이 필드들은 라이브러리의 mutex와 불변식을 전제로 관리되므로, 잠금 없이 직접 수정하면 데이터 경합이나 잘못된 상태가 생길 수 있습니다.

또한 어떤 스레드가 해당 계좌를 사용하고 있는 동안 `account_destroy`를 호출해서는 안 됩니다. `pthread_mutex_t`를 다른 스레드가 사용 중인 상태에서 파괴하는 것은 안전한 정리 절차가 아닙니다. 따라서 모든 작업 스레드를 `join`한 뒤 정리합니다.

## 빌드

```sh
make
```

정적 라이브러리는 다음 위치에 생성됩니다.

```text
build/libaccount.a
```

## 사용 예시

```c
#include "account.h"

struct account left;
struct account right;
long total;

account_init(&left, 1, 1000);
account_init(&right, 2, 500);

account_transfer(&left, &right, 200);
account_total(&left, &right, &total);

account_destroy(&right);
account_destroy(&left);
```

초기 상태가 다음과 같다면:

```text
left.balance  = 1000
right.balance = 500
합계          = 1500
```

`left`에서 `right`로 `200`을 성공적으로 이체한 뒤에는:

```text
left.balance  = 800
right.balance = 700
합계          = 1500
```

이 됩니다. 핵심은 다른 스레드가 중간 상태인 `800 + 500` 또는 `1000 + 700`을 관찰하지 못하도록 두 계좌를 함께 잠근 상태에서 갱신하는 것입니다.

## 주요 구현 결정

### 계좌마다 mutex를 둠

각 `struct account`는 자신의 `pthread_mutex_t`를 소유합니다.

한 계좌의 잔액만 읽는 연산은 해당 계좌의 mutex만 잠글 수 있고, 두 계좌를 함께 사용하는 연산은 두 mutex를 모두 잠급니다.

이렇게 해야 다음과 같은 연산이 서로 데이터 경합 없이 동작할 수 있습니다.

```text
한 계좌 잔액 조회
두 계좌 사이 이체
두 계좌의 일관된 합계 조회
```

### 두 mutex의 잠금 순서를 ID로 고정

두 계좌를 함께 잠가야 할 때는 항상 **작은 ID의 계좌부터** 잠급니다.

예를 들어:

```text
Account 1: id=10
Account 2: id=20
```

이라면 이체 방향과 관계없이 잠금 순서는 항상:

```text
id=10
→ id=20
```

입니다.

따라서 다음 두 스레드가 동시에 실행되어도:

```text
Thread A: 10 → 20 이체
Thread B: 20 → 10 이체
```

둘 다 먼저 `id=10`의 mutex를 얻으려고 합니다. 한 스레드가 첫 mutex를 잡은 상태에서 다른 스레드가 반대쪽 mutex를 먼저 잡는 상황이 생기지 않으므로, 서로 상대방의 mutex를 기다리는 **순환 대기(circular wait)** 를 피할 수 있습니다.

### 서로 다른 계좌의 ID는 잠금 순서를 결정할 수 있어야 함

서로 다른 두 계좌가 같은 ID를 가지면 다음 비교만으로는 어느 객체를 먼저 잠가야 하는지 정할 수 없습니다.

```text
left.id < right.id
right.id < left.id
```

둘 다 거짓이기 때문입니다.

따라서 이 라이브러리는 서로 다른 두 계좌가 같은 ID를 가지는 경우를 거부합니다. 즉 ID는 두 객체 사이의 안정적인 잠금 순서를 정하는 기준으로 사용됩니다.

같은 객체를 두 인자로 전달한 경우에는 mutex를 두 번 잠그지 않고 한 번만 잠급니다. 일반적인 비재귀 mutex를 같은 스레드가 두 번 잠그면 스스로 기다리게 될 수 있기 때문입니다.

### 검사는 두 mutex를 모두 잠근 뒤 수행

다음 검사는 두 계좌의 현재 상태에 의존합니다.

- 출발 계좌의 잔액이 충분한가
- 목적지 계좌에 금액을 더했을 때 `LONG_MAX`를 넘지 않는가

따라서 두 계좌를 모두 잠근 뒤 검사합니다.

```text
두 mutex 획득
→ 잔액 부족 검사
→ overflow 검사
→ 둘 다 성공하면 두 balance 변경
→ mutex 해제
```

검사와 갱신 사이에 mutex를 풀지 않으므로 다른 스레드가 검사 직후 잔액을 바꾸는 TOCTOU(time-of-check to time-of-use) 형태의 경쟁 조건을 만들 수 없습니다.

### 실패한 이체는 상태를 바꾸지 않음

잔액 부족이나 overflow 같은 조건을 발견하면 두 잔액을 변경하지 않고 실패합니다.

즉 이체는 다음 둘 중 하나여야 합니다.

```text
성공:
    출발 잔액 감소 + 목적지 잔액 증가

실패:
    두 잔액 모두 호출 전 상태 유지
```

한쪽 잔액만 먼저 바꾼 뒤 두 번째 변경에서 실패하는 방식은 허용하지 않습니다.

### 일관된 합계 조회

`account_total`은 다음처럼 구현하지 않습니다.

```text
left = account_get_balance(a)
right = account_get_balance(b)
return left + right
```

두 조회 사이에 이체가 발생하면 두 값이 서로 다른 시점에서 읽힐 수 있기 때문입니다.

예를 들어 실제 계좌 상태가:

```text
시점 1: A=100, B=100
시점 2: A=50,  B=150
```

로 바뀌는 동안 `A=100`과 `B=150`을 각각 읽으면 실제 어느 한 시점에도 존재하지 않았던 합 `250`을 만들 수 있습니다.

따라서 `account_total`은 두 계좌의 mutex를 같은 잠금 순서로 모두 획득한 뒤 두 잔액을 읽습니다.

## 실패한 조회와 출력 매개변수

출력 매개변수를 사용하는 조회 함수는 실패가 확인된 뒤 호출자의 기존 값을 덮지 않아야 합니다.

예를 들어:

```c
long value = 1234;
```

인 상태에서 잘못된 계좌를 조회해 함수가 실패했다면 `value`는 그대로 `1234`로 남아 있어야 합니다.

이 규칙은 호출자가 반환값을 확인한 뒤에만 출력값을 신뢰할 수 있게 해 줍니다.

## 테스트

```sh
make test
make sanitize
make thread-sanitize
```

기본 테스트는 이체 스레드 8개와 조회 스레드 2개를 동시에 시작합니다.

다음을 확인합니다.

- 모든 잠긴 합계 조회가 `400000`인지
- 개별 잔액이 음수가 되지 않는지
- 반대 방향 이체가 교착되지 않는지
- 잔액 부족, overflow와 같은 ID가 상태를 바꾸지 않는지
- 실패한 조회가 출력 매개변수를 덮지 않는지
- 자기 이체와 0원 이체
- 모든 스레드가 끝난 뒤 반복 정리

`ThreadSanitizer`는 컴파일러와 실행 환경이 지원하는 경우 mutex 바깥의 잘못된 공유 메모리 접근 같은 데이터 경합을 추가로 탐지하는 데 사용합니다.

일반 테스트가 통과한다고 데이터 경합이 없다는 뜻은 아니므로, 동시성 구현에서는 가능한 환경에서 ThreadSanitizer 결과도 함께 확인합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Account and mutex initialization | `src/account.c` |
| 2 | Stable ID-based lock order | `src/account.c` |
| 3 | Transfer checks and two-balance update | `src/account.c` |
| 4 | Locked balance and total reads | `src/account.c` |
| 5 | Cleanup after all threads join | `src/account.c` |

## 범위

메모리 안에 있는 두 계좌에 대한 연산만 제공합니다.

다음 기능은 포함하지 않습니다.

- 영구 저장
- 변경 로그
- 계좌 등록부
- 조건 변수
- 스레드 취소
- 여러 프로세스 사이의 공유 계좌
- 분산 트랜잭션

이 라이브러리의 핵심 범위는 **한 프로세스 안에서 여러 스레드가 공유하는 계좌 상태를 mutex로 일관되게 보호하는 것**입니다.