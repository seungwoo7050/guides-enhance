# diagnostic-formatter

`diagnostic-formatter`는 진단 메시지에 필요한 제한된 포맷 문자열을 호출자가 제공한 고정 크기 버퍼에 기록하는 C 라이브러리입니다.

버퍼가 결과 전체를 담기에 작더라도 다음 두 정보를 서로 구분합니다.

```text
실제로 버퍼에 기록할 수 있는 접두사
전체 결과를 만들기 위해 필요했던 논리적 길이
```

따라서 잘린 출력에서도 필요한 전체 길이를 알 수 있으며, `capacity > 0`인 유효한 출력 버퍼는 가능한 범위에서 항상 NUL로 끝납니다.

## 지원 형식

```text
%s  const char *
%d  int
%%  % 문자
```

`%s`에 `NULL`이 전달되면 이 라이브러리의 정의된 동작으로 다음 문자열을 출력합니다.

```text
(null)
```

이는 일반 `printf` 구현의 비표준 동작에 의존하는 것이 아니라 이 라이브러리가 명시적으로 제공하는 규칙입니다.

## 반환값

성공하면 **NUL 문자를 제외한 전체 필요 길이**를 `int`로 반환합니다.

예를 들어 결과 전체가:

```text
hello
```

라면 필요한 문자열 길이는 `5`이고, 실제로 완전한 C 문자열을 저장하려면 NUL까지 포함해 최소 6바이트의 버퍼가 필요합니다.

세부 규칙은 다음과 같습니다.

- 성공하면 NUL을 제외한 전체 필요 길이를 반환
- `capacity == 0`이면 `buffer == NULL`을 허용하고 길이만 계산
- 버퍼가 작으면 최대 `capacity - 1`바이트까지 기록하고 마지막에 NUL을 기록
- `capacity > 0 && buffer == NULL`이면 `-1`
- `format == NULL`이면 `-1`
- 미지원 지정자를 만나면 `-1`
- 전체 필요 길이가 `int`로 표현할 수 없으면 `-1`
- 포맷 오류가 발생해도 오류 전까지 기록한 접두사는 가능한 경우 NUL 종료
- `diagnostic_vformat`은 호출자가 전달한 원본 `va_list`를 직접 순회해 소모하지 않음

### `capacity == 0`

버퍼에 아무것도 기록하지 않고 전체 필요 길이만 계산합니다.

```c
int required =
    diagnostic_format(NULL, 0, "value=%d", 42);
```

이 방식은 필요한 버퍼 크기를 먼저 계산하는 데 사용할 수 있습니다.

### `capacity == 1`

문자 데이터를 저장할 공간은 없고 NUL 하나만 저장할 수 있습니다.

성공한 출력이 비어 있지 않더라도 실제 버퍼는:

```text
"\0"
```

만 담고 반환값은 전체 필요 길이를 나타냅니다.

### 잘림 예시

전체 결과가:

```text
abcdef
```

이고 `capacity == 4`라면 버퍼에는 최대 3문자와 NUL을 기록할 수 있습니다.

```text
buffer:
a b c \0
```

하지만 반환값은 실제 기록 길이 `3`이 아니라 전체 필요 길이 `6`입니다.

## 빌드

```sh
make
```

정적 라이브러리는 다음 위치에 생성됩니다.

```text
build/libdiagnostic_formatter.a
```

## 사용 예시

```c
#include "diagnostic_formatter.h"

char message[64];

int required = diagnostic_format(
    message,
    sizeof message,
    "file=%s line=%d",
    "main.c",
    42
);
```

`required`는 실제 버퍼에 기록된 길이가 아니라 **잘리지 않았다고 가정했을 때 전체 결과에 필요한 길이**입니다.

따라서:

```c
if (required < 0) {
    /* 잘못된 인자 또는 포맷 오류 */
} else if ((size_t)required >= sizeof message) {
    /* 출력이 잘림 */
} else {
    /* 전체 출력이 message에 들어감 */
}
```

처럼 구분할 수 있습니다.

## 주요 구현 결정

### 실제 기록 위치와 논리 길이를 분리

`struct output`은 다음 두 상태를 따로 관리합니다.

```text
write position:
    실제 버퍼에 몇 바이트를 쓸 수 있는가

logical length:
    버퍼 크기와 관계없이 전체 결과가 몇 바이트인가
```

예를 들어 버퍼가 이미 가득 찼더라도 이후 포맷 문자의 길이는 계속 논리 길이에 더해야 합니다.

그래야 잘린 결과에서도 반환값이 전체 필요 길이를 나타낼 수 있습니다.

### 모든 출력 경로를 공통 함수로 통과

문자열, 정수와 일반 문자는 모두 `output_char` 같은 공통 출력 경로를 사용합니다.

이렇게 하면:

```text
%s
%d
일반 문자
%%
```

가 서로 다른 잘림 규칙을 가지지 않고 동일한 방식으로:

```text
실제 기록 가능 여부 확인
→ 가능하면 한 바이트 기록
→ 논리 길이는 항상 증가
```

하도록 만들 수 있습니다.

### NUL 종료

`capacity > 0`이고 `buffer`가 유효하다면 함수가 기록 가능한 접두사 뒤에 NUL을 둡니다.

즉 잘림이 발생해도 호출자는 버퍼를 C 문자열로 읽을 수 있습니다.

포맷 오류가 중간에 발견되어 `-1`을 반환하는 경우에도 오류 전에 이미 쓴 접두사는 가능한 위치에서 NUL로 끝냅니다.

단, `-1`은 성공적인 포맷 결과가 아니라 오류이므로 호출자는 버퍼 내용 전체를 정상 결과라고 해석해서는 안 됩니다.

### `INT_MIN` 처리

음수 정수를 문자열로 바꿀 때 단순히 다음처럼 작성하면 위험할 수 있습니다.

```c
magnitude = -value;
```

`value == INT_MIN`이면 같은 `int` 타입에서 양수 크기를 표현할 수 없기 때문입니다.

따라서 음수의 절댓값 크기는 부호 없는 정수 연산으로 안전하게 계산한 뒤 숫자 문자를 출력합니다.

### `va_list`를 복사해서 순회

`diagnostic_vformat`은 전달받은 `va_list`를 직접 `va_arg`로 소비하지 않고 `va_copy`로 별도의 순회 상태를 만듭니다.

개념적으로:

```text
caller의 va_list
      │
      └─ va_copy
            ↓
       formatter 전용 복사본
            ↓
          va_arg
            ↓
          va_end
```

따라서 이 함수가 반환된 뒤에도 호출자가 전달한 원본 `va_list`의 위치를 이 함수 자체가 전진시키지 않는다는 계약을 유지할 수 있습니다.

복사한 `va_list`는 반드시 `va_end`로 정리합니다.

## 잘못된 포맷

지원 형식은 `%s`, `%d`, `%%`뿐입니다.

따라서 다음은 오류입니다.

```text
%x
%ld
%zu
%.3s
%5d
%
```

특히 문자열 마지막의 단독 `%`는 다음 지정자를 읽을 수 없으므로 포맷 오류입니다.

미지원 형식을 일반 문자처럼 그대로 통과시키지 않고 `-1`을 반환하므로, 호출자는 잘못된 진단 포맷을 조기에 발견할 수 있습니다.

## 테스트

```sh
make test
make sanitize
```

테스트는 다음을 확인합니다.

- `%s`, `%d`, `%%` 혼합
- `0`, `INT_MIN`, `INT_MAX`
- `NULL` 문자열
- 정확히 맞는 버퍼와 잘리는 버퍼
- `capacity`가 0 또는 1인 경우
- 미지원 지정자와 끝의 단독 `%`
- 같은 원본 `va_list`의 반복 사용

버퍼 테스트에서는 단순히 반환값만 확인하지 않고 다음을 함께 확인해야 합니다.

```text
실제 기록된 접두사
NUL 종료 위치
전체 필요 길이
오류 시 반환값
```

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Output buffer and logical length | `src/diagnostic_formatter.c` |
| 2 | String and integer emitters | `src/diagnostic_formatter.c` |
| 3 | NUL termination after truncation | `src/diagnostic_formatter.c` |
| 4 | Format parsing with a copied va_list | `src/diagnostic_formatter.c` |
| 5 | Variadic wrapper | `src/diagnostic_formatter.c` |

## 범위

다음 `printf` 계열 기능은 지원하지 않습니다.

- 필드 너비
- 정밀도
- 길이 수정자
- 부동소수점
- 16진수 출력
- 동적 형식 확장

미지원 지정자를 자동으로 통과시키지 않고 오류로 반환합니다.

이 라이브러리의 목적은 전체 `printf`를 재구현하는 것이 아니라 **진단 메시지에 필요한 작은 포맷 집합을 예측 가능한 버퍼 규칙으로 제공하는 것**입니다.