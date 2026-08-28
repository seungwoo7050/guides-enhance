# 가변 인자와 제한된 포맷 출력

가변 인자 함수는 호출할 때마다 인자의 개수와 타입을 다르게 전달할 수 있습니다. 하지만 `...` 뒤에 전달된 값에는 개수와 타입을 설명하는 정보가 자동으로 들어 있지 않습니다. 함수는 별도의 규칙으로 어디까지 읽고 각 값을 어떤 타입으로 해석할지 알아야 합니다.

## 기본 형태

```c
int sum_ints(size_t count, ...);
```

`count`는 고정 인자이고, 뒤의 `...`가 가변 인자입니다. C에서는 `...` 앞에 최소 하나의 고정 인자가 필요합니다.

## `<stdarg.h>`

```c
#include <stdarg.h>

int sum_ints(size_t count, ...) {
    va_list arguments;
    int total = 0;

    va_start(arguments, count);
    for (size_t index = 0; index < count; index++) {
        total += va_arg(arguments, int);
    }
    va_end(arguments);
    return total;
}
```

- `va_list`: 현재 읽기 위치를 포함한 가변 인자 상태
- `va_start`: 첫 가변 인자를 읽을 수 있도록 초기화
- `va_arg`: 다음 값을 지정한 타입으로 읽고 위치 이동
- `va_end`: 해당 순회 종료
- `va_copy`: 독립적으로 읽을 수 있는 복사본 초기화

`va_start`와 `va_copy`로 초기화한 각 `va_list`에는 `va_end`가 필요합니다.

## 함수는 실제 타입을 검사할 수 없습니다

```c
sum_ints(2, 10, 2.5);
```

함수 안에서 `va_arg(arguments, int)`를 호출해도 다음 인자가 실제로 `int`인지 확인해 주지 않습니다. 호출자가 전달한 타입과 읽는 타입이 맞지 않으면 정의되지 않은 동작이 생길 수 있습니다.

다음을 구분해야 합니다.

```text
함수가 확인할 수 있는 오류:
  NULL 포인터
  잘못된 capacity
  지원하지 않는 포맷 문자
  결과 길이 overflow

호출자가 지켜야 하는 규칙:
  인자 개수
  포맷 문자열과 실제 타입 일치
```

잘못된 가변 인자 타입을 테스트로 전달하면 오류 반환을 검사하는 것이 아니라 정의되지 않은 동작을 실행하게 됩니다.

## 기본 인자 승격

- `char`, `short` 등은 일반적으로 `int` 또는 `unsigned int`로 전달됩니다.
- `float`는 `double`로 전달됩니다.

받는 쪽에서는 승격된 타입으로 읽습니다.

```c
int promoted_letter = va_arg(arguments, int);
double promoted_ratio = va_arg(arguments, double);
```

## 인자의 끝을 정하는 방법

함수는 가변 인자의 개수를 스스로 알 수 없습니다.

### 개수 전달

```c
int sum_ints(size_t count, ...);
```

### 종결값

```c
first_nonempty("one", "two", (const char *)NULL);
```

### 포맷 문자열

```c
int diagnostic_format(
    char *buffer,
    size_t capacity,
    const char *format,
    ...
);
```

```text
%s  다음 인자는 const char *
%d  다음 인자는 int
%%  인자를 읽지 않고 % 출력
```

포맷 문자열은 출력할 글자뿐 아니라 뒤의 인자를 읽는 방법도 정합니다.

## `v` 함수로 핵심 로직 분리하기

```c
int diagnostic_vformat(
    char *buffer,
    size_t capacity,
    const char *format,
    va_list arguments
);
```

`...`를 받은 함수가 다른 가변 인자 함수의 `...`에 그대로 전달할 수는 없습니다. `va_list`를 받는 함수를 따로 두면 여러 래퍼가 같은 구현을 사용할 수 있습니다.

## 원본 `va_list` 보존

`va_arg`를 호출하면 읽기 위치가 바뀝니다. 전달받은 원본을 소비하지 않겠다고 정했다면 `va_copy`를 사용합니다.

```c
va_list copy;

va_copy(copy, arguments);
/* copy를 순회합니다. */
va_end(copy);
```

단순 대입이나 `memcpy`를 이식 가능한 복사 방법으로 사용하지 않습니다.

## 제한된 포맷 문법 먼저 정하기

```text
일반 문자  그대로 출력
%%         % 출력
%s         문자열 출력
%d         10진수 int 출력
```

함께 정해야 할 항목:

- `%s`에 `NULL`이 오면 무엇을 출력합니까?
- 문자열 끝에 `%`만 남으면 오류입니까?
- `%x` 같은 미지원 지정자를 만나면 어떻게 합니까?
- 버퍼가 작으면 오류입니까, 정상적인 잘림입니까?
- 반환 길이는 실제로 쓴 길이입니까, 필요한 전체 길이입니까?

## 논리 길이와 실제 쓰기 위치 분리

작은 버퍼에서도 전체 필요 길이를 반환하려면 두 값을 구분합니다.

```c
struct output {
    char *buffer;
    size_t capacity;
    size_t length;
    int failed;
};
```

`length`는 실제로 쓴 바이트 수가 아니라 출력하려 했던 전체 길이입니다. 모든 문자 출력을 한 함수로 보내면 문자열, 정수와 일반 문자가 같은 잘림 규칙을 사용합니다.

## NUL 종료

`capacity > 0`이고 `buffer != NULL`이면 가능한 위치에 NUL을 씁니다. `capacity == 0`일 때는 버퍼에 접근하지 않고 길이만 계산할 수 있습니다.

## `INT_MIN` 출력

```c
int value = INT_MIN;
int magnitude = -value; /* overflow 가능 */
```

`INT_MIN`의 절댓값은 같은 signed 타입에 들어가지 않을 수 있습니다. unsigned arithmetic으로 크기를 계산합니다.

```c
unsigned int magnitude;

if (value < 0) {
    output_char(output, '-');
    magnitude = 0u - (unsigned int)value;
} else {
    magnitude = (unsigned int)value;
}
```

## 테스트할 내용

- 빈 format
- `%s`, `%d`, `%%` 혼합
- `0`, `INT_MIN`, `INT_MAX`
- `NULL` 문자열
- 정확히 맞는 버퍼와 잘리는 버퍼
- `capacity == 0`과 `capacity == 1`
- 미지원 지정자와 끝의 `%`
- 같은 원본 `va_list`를 두 번 전달했을 때 동일 결과

## 완료 기준

1. 포맷 문자열과 실제 인자 타입이 맞아야 하는 이유를 설명합니다.
2. 기본 인자 승격 후 타입으로 `va_arg`를 호출합니다.
3. `va_start`/`va_copy`마다 `va_end`를 호출합니다.
4. 전달받은 원본 `va_list`를 보존할 때 `va_copy`를 사용합니다.
5. 실제 기록 범위와 전체 필요 길이를 분리합니다.
6. `INT_MIN`을 signed negation 없이 출력합니다.
