# account-simulator

`account-simulator`는 여러 스레드가 두 계좌 사이에서 동시에 이체하고 잔액을 읽어도 음수 잔액이 생기지 않고 전체 합이 유지되도록 구현한 C 라이브러리입니다. 서로 반대 방향의 이체도 같은 ID 순서로 mutex를 잠가 교착 상태를 막습니다.

## 제공 기능

- 각 계좌 객체가 자신의 `pthread_mutex_t`를 소유
- 음수 초기 잔액과 음수 이체 금액 거부
- 잔액 부족과 목적지 `LONG_MAX` overflow 검사
- 두 잔액을 모두 잠근 상태에서 이체
- 같은 account로 보내는 이체와 0원 이체 처리
- 작은 account ID부터 잠그는 고정 순서
- 한 account의 잔액 조회와 두 account의 합계 조회
- 이체 스레드와 조회 스레드를 동시에 실행하는 부하 테스트

## 사용 순서

```text
account_init
→ 여러 스레드에서 조회·이체
→ 모든 스레드 join
→ account_destroy
```

초기화된 계좌 객체의 `id`, `balance`, `initialized`를 호출자가 직접 변경하면 mutex로 보호한 규칙이 깨집니다.

## 빌드

```sh
make
```

정적 라이브러리는 `build/libaccount.a`에 생성됩니다.

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

## 주요 구현 결정

두 계좌를 사용하는 함수는 항상 작은 ID의 mutex부터 잠급니다. 반대 방향 이체도 같은 순서를 사용하므로 각 스레드가 서로 다른 첫 mutex를 잡고 상대 mutex를 기다리는 순환 대기가 생기지 않습니다.

서로 다른 두 계좌가 같은 ID를 가지면 먼저 잠글 객체를 정할 수 없으므로 거부합니다. 같은 객체를 두 인자로 전달한 경우에는 mutex를 한 번만 잠급니다.

잔액 부족과 overflow 검사는 두 mutex를 모두 잠근 뒤 수행합니다. 성공할 때만 두 잔액을 함께 바꾸므로 한쪽만 바뀐 상태를 다른 스레드가 볼 수 없습니다.

`account_total`은 `account_get_balance`를 두 번 호출해 더하지 않습니다. 두 호출 사이에 이체가 들어오면 실제로 한 시점에 존재하지 않았던 합을 만들 수 있기 때문입니다.

## 테스트

```sh
make test
make sanitize
make thread-sanitize
```

기본 테스트는 이체 스레드 8개와 조회 스레드 2개를 동시에 시작합니다. 다음을 확인합니다.

- 모든 잠긴 합계 조회가 `400000`인지
- 개별 잔액이 음수가 되지 않는지
- 반대 방향 이체가 교착되지 않는지
- 잔액 부족, overflow와 같은 ID가 상태를 바꾸지 않는지
- 실패한 조회가 출력 매개변수를 덮지 않는지
- 자기 이체와 0원 이체
- 모든 스레드가 끝난 뒤 반복 정리

ThreadSanitizer는 컴파일러와 실행 환경이 지원하는 경우 데이터 경합을 추가로 검사합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Account and mutex initialization | `src/account.c` |
| 2 | Stable ID-based lock order | `src/account.c` |
| 3 | Transfer checks and two-balance update | `src/account.c` |
| 4 | Locked balance and total reads | `src/account.c` |
| 5 | Cleanup after all threads join | `src/account.c` |

## 범위

메모리 안에 있는 두 계좌에 대한 연산만 제공합니다. 영구 저장, 변경 로그, 계좌 등록부, 조건 변수와 스레드 취소는 포함하지 않습니다.
