# diagnostic-formatter

`diagnostic-formatter`는 진단 메시지에 필요한 제한된 포맷 문자열을 고정 크기 버퍼에 기록하는 C 라이브러리입니다. 버퍼가 작아도 필요한 전체 길이를 계산하며, 실제로 기록한 접두사는 항상 가능한 위치에서 NUL로 끝냅니다.

## 지원 형식

```text
%s  const char *
%d  int
%%  % 문자
```

`%s`에 `NULL`이 전달되면 `(null)`을 출력합니다.

## 반환값

- 성공하면 NUL을 제외한 전체 필요 길이를 반환합니다.
- `capacity == 0`이면 `buffer == NULL`을 허용하고 길이만 계산합니다.
- 버퍼가 작으면 `capacity - 1`바이트까지만 기록하고 NUL을 씁니다.
- `capacity > 0 && buffer == NULL`, `format == NULL`, 미지원 지정자, `int`로 반환할 수 없는 길이는 `-1`입니다.
- 포맷 오류가 발생해도 오류 전까지 기록한 접두사는 NUL로 끝냅니다.
- `diagnostic_vformat`은 전달받은 원본 `va_list`를 직접 소비하지 않습니다.

## 빌드

```sh
make
```

정적 라이브러리는 `build/libdiagnostic_formatter.a`에 생성됩니다.

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

`required`는 실제 버퍼에 기록된 길이가 아니라 전체 결과에 필요한 길이입니다.

## 주요 구현 결정

`struct output`은 버퍼에 실제로 쓸 수 있는 위치와 전체 필요 길이를 따로 관리합니다. 문자열, 정수와 일반 문자는 모두 `output_char`를 거치므로 잘림과 길이 계산 방식이 달라지지 않습니다.

음수의 크기는 부호 없는 정수 연산으로 계산합니다. `INT_MIN`을 같은 부호 있는 타입에서 바로 부정하면 표현 범위를 벗어날 수 있기 때문입니다.

`diagnostic_vformat`은 `va_copy`로 독립적인 순회 상태를 만든 뒤 `va_end`로 정리합니다. 따라서 같은 원본 `va_list`를 다시 전달해도 같은 인자를 읽을 수 있습니다.

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

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Output buffer and logical length | `src/diagnostic_formatter.c` |
| 2 | String and integer emitters | `src/diagnostic_formatter.c` |
| 3 | NUL termination after truncation | `src/diagnostic_formatter.c` |
| 4 | Format parsing with a copied va_list | `src/diagnostic_formatter.c` |
| 5 | Variadic wrapper | `src/diagnostic_formatter.c` |

## 범위

필드 너비, 정밀도, 길이 수정자, 부동소수점과 16진수 출력은 지원하지 않습니다. 미지원 지정자를 자동으로 통과시키지 않고 오류로 반환합니다.
