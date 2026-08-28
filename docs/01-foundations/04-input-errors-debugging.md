# 입력 오류와 디버깅

문제가 발생하면 먼저 실패 종류를 구분합니다. 사용자가 잘못된 값을 입력한 경우와 프로그램이 배열 밖을 읽은 경우는 원인과 해결 방법이 다릅니다. 코드 결함을 입력 오류처럼 처리해서는 안 됩니다.

## 실패 종류

| 종류 | 예 | 처리 방법 |
| --- | --- | --- |
| 입력 형식 오류 | 인자 누락, 숫자가 아닌 문자열 | 진단 메시지와 정해진 종료 상태를 반환합니다. |
| 값 범위 오류 | 음수 금지, 허용 범위 초과 | 입력을 거부하고 기존 상태를 유지합니다. |
| 자원 확보 실패 | `malloc`, `open`, `fork` 실패 | 이미 확보한 자원을 정리하고 오류를 반환합니다. |
| 코드 결함 | 범위 밖 접근, 해제 후 사용 | 재현 조건을 만든 뒤 디버거와 sanitizer로 수정합니다. |

## `strtol`로 정수 문자열 전체 검사하기

`atoi`는 변환 실패와 정상적인 `0`을 구분하기 어렵고 범위 오류도 확인할 수 없습니다. 입력을 검증해야 한다면 `strtol`을 사용합니다.

```c
#include <ctype.h>
#include <errno.h>
#include <stdlib.h>

int parse_long(const char *text, long *out_value) {
    char *end;
    long value;

    if (text == NULL || out_value == NULL || text[0] == '\0' ||
        isspace((unsigned char)text[0])) {
        return -1;
    }

    errno = 0;
    value = strtol(text, &end, 10);
    if (errno == ERANGE || end == text || *end != '\0') {
        return -1;
    }

    *out_value = value;
    return 0;
}
```

검사 순서는 다음과 같습니다.

1. 포인터와 빈 문자열을 확인합니다.
2. 규칙에서 허용하지 않는 앞 공백을 확인합니다.
3. `errno`를 `0`으로 초기화합니다.
4. `strtol`을 호출합니다.
5. 문자를 하나도 변환하지 못했는지 확인합니다.
6. 문자열 끝까지 모두 변환했는지 확인합니다.
7. 표현 범위를 벗어났는지 확인합니다.
8. 모든 검사를 통과한 뒤 출력 값을 변경합니다.

## 오류 메시지와 종료 상태

오류 메시지는 적어도 다음을 알려야 합니다.

- 어떤 입력에서 실패했습니까?
- 어떤 값이나 형식이 필요합니까?
- 프로그램이 어떤 종료 상태를 반환합니까?

```c
fprintf(stderr, "오류: 정수가 아닙니다: %s\n", argv[index]);
return 2;
```

자동 테스트가 오류 메시지 전체 문장에 지나치게 의존하지 않도록, 프로그램이 보장할 최소 접두어나 형식만 정할 수 있습니다.

## 최소 재현 사례 만들기

오류를 고치기 전에 같은 문제를 반복해서 만들 수 있어야 합니다. 다음 정보를 기록합니다.

```text
실행 명령
입력 파일 또는 인자
컴파일 옵션
stdout
stderr
종료 상태
운영체제와 컴파일러
```

그다음 입력과 조건을 하나씩 줄입니다. 같은 문제가 유지되는 가장 작은 사례를 만들면 관련 없는 코드가 줄어들어 원인을 찾기 쉽습니다.

## 디버그 빌드

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -g -O0 source.c -o program
```

- `-g`: 디버거가 소스 위치와 변수 정보를 표시할 수 있도록 정보를 넣습니다.
- `-O0`: 처음 조사할 때 소스와 실행 순서를 대응시키기 쉽게 합니다.

문제를 수정한 뒤에는 실제로 사용할 최적화 옵션에서도 다시 빌드하고 검사합니다. `-O0`에서만 정상이라고 해서 결함이 사라진 것은 아닙니다.

## 디버거 기본 사용

GDB 예시:

```sh
gdb ./program
(gdb) break main
(gdb) run 10 bad 30
(gdb) next
(gdb) step
(gdb) print index
(gdb) backtrace
```

LLDB 예시:

```sh
lldb ./program
(lldb) breakpoint set --name main
(lldb) run 10 bad 30
(lldb) next
(lldb) step
(lldb) frame variable index
(lldb) bt
```

코드를 처음부터 무작정 한 줄씩 따라가지 않습니다. 잘못되었을 것으로 예상되는 값이나 시점을 정하고, 중단점과 변수 값으로 가설을 확인합니다.

## AddressSanitizer와 UndefinedBehaviorSanitizer

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -g \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    source.c -o program
```

AddressSanitizer는 범위를 벗어난 메모리 접근, 해제한 메모리 사용과 중복 해제를 찾는 데 도움이 됩니다. UndefinedBehaviorSanitizer는 부호 있는 정수 overflow, 잘못된 시프트, 0으로 나누기와 정렬 요구사항 위반 일부를 검사합니다.

해당 코드가 실제로 실행되어야 검사가 가능합니다. sanitizer를 켰다는 사실만으로 모든 경로가 안전하다고 볼 수 없습니다.

## 경고를 오류로 다루기

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -Werror source.c -o program
```

경고를 없애기 위해 캐스트를 추가하기 전에 원인을 확인합니다.

- 타입을 잘못 선택하지 않았습니까?
- signed와 unsigned 값을 섞지 않았습니까?
- 형식 지정자와 실제 타입이 일치합니까?
- 확인해야 할 반환값을 무시하지 않았습니까?
- 변환할 값이 대상 타입 범위 안에 있습니까?

## 테스트할 입력 나누기

- 정상 사례: 프로그램이 지원한다고 명시한 일반 입력
- 경계 사례: 빈 문자열, 한 글자, 최솟값과 최댓값, 정확히 맞는 버퍼
- 실패 사례: 잘못된 문자, 범위 초과, 할당 실패, 시스템 호출 실패

테스트는 성공 결과만 비교하지 않습니다. 실패 시 출력 매개변수와 기존 상태가 유지되는지도 확인합니다.

## 완료 기준

1. 입력 오류와 코드 결함을 구분합니다.
2. `strtol` 결과를 `errno`, 시작 포인터와 끝 포인터로 검사합니다.
3. 실패 시 출력 매개변수를 변경하지 않습니다.
4. 최소 재현 사례를 만듭니다.
5. 디버거로 중단점, 변수와 호출 스택을 확인합니다.
6. sanitizer가 확인한 범위와 확인하지 못한 범위를 구분합니다.
