# 가변 인자와 제한된 포맷 출력

C의 **가변 인자 함수(variadic function)** 는 호출마다 뒤에 전달하는 인자의 개수와 타입을 다르게 할 수 있는 함수입니다.

```c
int sum_ints(size_t count, ...);
```

하지만 `...` 뒤에 전달된 값에는 다음 정보가 자동으로 붙지 않습니다.

- 가변 인자가 몇 개인가
- 각 인자가 어떤 타입인가
- 어디에서 가변 인자 목록이 끝나는가

따라서 함수를 설계할 때는 가변 인자를 **어떤 규칙으로 읽을지** 별도로 정해야 합니다.

대표적인 방법은 다음과 같습니다.

- 고정 인자로 개수를 전달
- 특별한 종결값(sentinel)을 전달
- 포맷 문자열이 뒤의 인자 타입과 개수를 설명

가변 인자를 읽는 함수와 호출자는 반드시 같은 규칙을 공유해야 합니다.

## 기본 형태

C11 스타일의 가변 인자 함수는 `...` 앞에 하나 이상의 이름 있는 매개변수를 둡니다.

```c
int sum_ints(size_t count, ...);
```

여기에서

```text
count  → 고정 인자
...    → 가변 인자
```

입니다.

호출 예:

```c
int total = sum_ints(3, 10, 20, 30);
```

`count == 3`이라는 규칙 덕분에 함수는 뒤에서 정수 세 개를 읽어야 한다는 사실을 알 수 있습니다.

`...`만 보고는 인자의 개수를 알아낼 수 없습니다.

## `<stdarg.h>`

가변 인자를 읽으려면 `<stdarg.h>`의 기능을 사용합니다.

```c
#include <stdarg.h>

int sum_ints(size_t count, ...) {
    va_list arguments;
    int total = 0;

    va_start(arguments, count);

    for (size_t index = 0; index < count; ++index) {
        total += va_arg(arguments, int);
    }

    va_end(arguments);
    return total;
}
```

주요 기능은 다음과 같습니다.

| 기능 | 역할 |
| --- | --- |
| `va_list` | 가변 인자 순회 상태를 나타내는 타입 |
| `va_start` | 가변 인자를 읽기 시작할 수 있도록 `va_list` 초기화 |
| `va_arg` | 다음 인자를 지정한 타입으로 읽고 순회 위치를 이동 |
| `va_copy` | 독립적으로 순회할 수 있는 `va_list` 복사본 초기화 |
| `va_end` | `va_start` 또는 `va_copy`로 시작한 순회를 종료 |

`va_list`를 단순한 포인터라고 가정하면 안 됩니다. 구현에 따라 포인터, 배열과 비슷한 형태, 구조체 등 여러 방식으로 표현될 수 있습니다.

따라서 `va_list`는 `<stdarg.h>`가 정한 연산을 통해서만 다루는 것이 안전합니다.

## `va_start`와 `va_end`

`va_start`로 초기화한 `va_list`는 사용이 끝난 뒤 `va_end`해야 합니다.

```c
va_list arguments;

va_start(arguments, count);

/* va_arg 사용 */

va_end(arguments);
```

마찬가지로 `va_copy`로 만든 복사본도 독립적으로 `va_end`해야 합니다.

```c
va_list copy;

va_copy(copy, arguments);

/* copy 사용 */

va_end(copy);
```

즉, 다음처럼 대응한다고 생각할 수 있습니다.

```text
va_start → va_end
va_copy  → va_end
```

중간에 함수가 여러 경로로 반환한다면 모든 경로에서 필요한 `va_end`가 실행되도록 구성해야 합니다.

## `va_arg`는 타입을 검사하지 않습니다

다음 함수는 모든 가변 인자가 `int`라는 규칙을 전제로 합니다.

```c
int sum_ints(size_t count, ...);
```

정상 호출:

```c
sum_ints(2, 10, 20);
```

잘못된 호출:

```c
sum_ints(2, 10, 2.5);
```

함수 내부가 다음처럼 읽는다고 해도

```c
int value = va_arg(arguments, int);
```

`va_arg`가 실제 다음 인자가 `int`인지 런타임에 확인해 주는 것은 아닙니다.

호출자는 두 번째 가변 인자로 `double`을 전달했지만 함수는 `int`로 읽으려고 하므로, 이런 타입 불일치는 정의되지 않은 동작으로 이어질 수 있습니다.

즉, 가변 인자 API에서는 다음 두 종류의 오류를 구분해야 합니다.

```text
함수 내부에서 검사 가능한 오류:
  NULL 고정 인자
  잘못된 buffer/capacity 조합
  지원하지 않는 포맷 지정자
  문자열이나 결과 길이 계산 overflow

호출자가 API 계약으로 지켜야 하는 규칙:
  가변 인자 개수
  각 가변 인자의 실제 타입
  포맷 지정자와 실제 인자 타입의 일치
  sentinel 방식이라면 올바른 타입의 종결값
```

호출자가 잘못된 가변 인자 타입을 넘긴 경우를 “함수가 -1을 반환하는지” 확인하는 테스트로 만들면 안 됩니다. 함수가 그 타입 오류를 안전하게 감지할 수 있다는 보장이 없기 때문입니다.

## 기본 인자 승격

가변 인자로 전달되는 일부 타입은 호출 시 **기본 인자 승격(default argument promotions)** 을 거칩니다.

대표적으로 다음과 같습니다.

- `float` → `double`
- `_Bool`, `char`, `signed char`, `unsigned char`, `short`, `unsigned short` → 정수 승격 후 `int` 또는 필요한 경우 `unsigned int`

따라서 다음과 같은 호출을 생각해 봅니다.

```c
char letter = 'A';
float ratio = 1.5f;

function(letter, ratio);
```

가변 인자 부분에서 실제로 읽을 때는 원래 선언 타입이 아니라 승격 후 타입을 사용합니다.

```c
int promoted_letter = va_arg(arguments, int);
double promoted_ratio = va_arg(arguments, double);
```

다음처럼 읽으면 안 됩니다.

```c
char letter = va_arg(arguments, char);     /* 잘못됨 */
float ratio = va_arg(arguments, float);    /* 잘못됨 */
```

특히 `float`가 `double`로 승격된다는 점은 포맷 함수를 구현할 때 자주 중요해집니다.

## 가변 인자의 끝을 정하는 방법

함수는 `...` 뒤에 실제로 몇 개의 인자가 전달되었는지 스스로 알아낼 수 없습니다.

따라서 API가 끝을 판별할 규칙을 제공해야 합니다.

### 개수 전달

```c
int sum_ints(size_t count, ...);
```

호출:

```c
sum_ints(3, 10, 20, 30);
```

함수는 `count`만큼 정확히 `va_arg`를 호출합니다.

호출자가 실제보다 큰 개수를 전달하면 존재하지 않는 인자를 읽으려 하므로 정의되지 않은 동작으로 이어질 수 있습니다.

### 종결값

특별한 값을 마지막에 전달할 수도 있습니다.

```c
first_nonempty(
    "one",
    "two",
    (const char *)NULL
);
```

함수는 `NULL` 포인터를 만날 때까지 `const char *`를 읽는다는 규칙을 가질 수 있습니다.

여기에서

```c
(const char *)NULL
```

처럼 타입을 명확히 하는 것이 중요합니다.

가변 인자 부분에서는 함수 프로토타입이 각 위치의 목표 타입을 알려 주지 않으므로, 단순한 정수 상수 `0`이 포인터 타입으로 자동 변환될 것이라고 기대해서는 안 됩니다.

따라서 포인터 sentinel을 전달할 때는 기대하는 포인터 타입으로 명시적으로 변환하는 방식이 안전합니다.

### 포맷 문자열

포맷 문자열 자체가 뒤의 인자를 어떻게 읽을지 설명할 수도 있습니다.

```c
int diagnostic_format(
    char *buffer,
    size_t capacity,
    const char *format,
    ...
);
```

예를 들어 이 함수가 다음 문법만 지원한다고 정할 수 있습니다.

```text
%s  → 다음 인자를 const char *로 읽음
%d  → 다음 인자를 int로 읽음
%%  → 인자를 읽지 않고 '%' 출력
```

호출:

```c
diagnostic_format(
    buffer,
    sizeof buffer,
    "name=%s count=%d%%",
    name,
    count
);
```

포맷 문자열은 단순히 출력할 문자를 나타내는 것이 아니라 **가변 인자의 타입과 소비 순서를 설명하는 데이터**입니다.

## 포맷 문자열과 실제 타입의 계약

다음 호출은 `%d`와 `int`가 일치합니다.

```c
diagnostic_format(
    buffer,
    sizeof buffer,
    "%d",
    42
);
```

다음 호출은 계약을 위반합니다.

```c
diagnostic_format(
    buffer,
    sizeof buffer,
    "%d",
    "42"
);
```

구현이 `%d`를 보고 다음을 실행하면

```c
int value = va_arg(arguments, int);
```

실제 전달된 값은 문자열 포인터이므로 타입이 맞지 않습니다.

반대로

```c
diagnostic_format(
    buffer,
    sizeof buffer,
    "%s",
    42
);
```

도 같은 이유로 잘못된 호출입니다.

포맷 함수는 포맷 문자열 자체가 올바른지는 검사할 수 있지만, 그 지정자에 대응하는 실제 가변 인자가 올바른 타입인지를 일반적으로 런타임에 검증할 수는 없습니다.

## `v` 함수로 핵심 로직 분리하기

가변 인자를 받는 함수는 보통 실제 구현을 `va_list` 기반 함수로 분리하면 재사용하기 쉽습니다.

```c
int diagnostic_vformat(
    char *buffer,
    size_t capacity,
    const char *format,
    va_list arguments
);
```

그 위에 `...` 래퍼를 둡니다.

```c
int diagnostic_format(
    char *buffer,
    size_t capacity,
    const char *format,
    ...
) {
    va_list arguments;
    int result;

    va_start(arguments, format);

    result = diagnostic_vformat(
        buffer,
        capacity,
        format,
        arguments
    );

    va_end(arguments);
    return result;
}
```

`...`로 받은 가변 인자 목록을 다른 함수의 `...` 위치에 그대로 전달하는 표준적인 문법은 없습니다.

따라서 `printf`와 `vprintf`, `snprintf`와 `vsnprintf`처럼 `va_list`를 받는 `v` 계열 함수를 따로 두는 패턴이 유용합니다.

## `va_list`는 소비됩니다

`va_arg`를 호출하면 해당 `va_list`의 현재 읽기 위치가 다음 인자로 이동합니다.

```c
int first = va_arg(arguments, int);
int second = va_arg(arguments, int);
```

따라서 같은 순회 상태에서 다시 처음부터 읽고 싶다고 해서 단순히 같은 `va_list`를 재사용할 수는 없습니다.

다음과 같은 동작을 원한다고 가정합니다.

```text
1차 순회: 전체 출력 길이 계산
2차 순회: 실제 출력
```

이 경우 각 순회에 독립적인 `va_list`가 필요합니다.

```c
va_list first_pass;
va_list second_pass;

va_copy(first_pass, arguments);
va_copy(second_pass, arguments);

/* first_pass 순회 */
/* second_pass 순회 */

va_end(first_pass);
va_end(second_pass);
```

## 전달받은 `va_list`를 보존하려면 `va_copy`

`diagnostic_vformat`이 호출자의 `va_list` 순회 상태를 변경하지 않는다는 계약을 제공하려면 함수 내부에서 복사본을 만들어 사용합니다.

```c
int diagnostic_vformat(
    char *buffer,
    size_t capacity,
    const char *format,
    va_list arguments
) {
    va_list copy;

    va_copy(copy, arguments);

    /* copy만 va_arg로 순회 */

    va_end(copy);
    return 0;
}
```

이렇게 하면 구현 의도가 명확해집니다.

중요한 안전 규칙은 다음과 같습니다.

```text
va_list를 독립적으로 순회해야 한다면 va_copy를 사용한다.
```

다음처럼 단순 대입을 이식 가능한 복사 방법이라고 가정하면 안 됩니다.

```c
va_list copy = arguments;   /* 이식 가능한 일반 해법이 아님 */
```

`memcpy`로 복사하는 것도 사용하지 않습니다.

```c
memcpy(&copy, &arguments, sizeof copy);   /* 사용하지 않음 */
```

`va_list`의 표현은 구현에 맡겨져 있으므로 `<stdarg.h>`가 제공하는 `va_copy`를 사용해야 합니다.

## 제한된 포맷 문법을 먼저 정의하기

직접 포맷 함수를 구현할 때 표준 `printf` 전체를 흉내 내려고 시작하면 범위가 급격히 커집니다.

먼저 지원 문법을 제한하는 것이 좋습니다.

예:

```text
일반 문자  → 그대로 출력
%%         → '%' 출력
%s         → const char * 문자열 출력
%d         → int를 10진수로 출력
```

그 다음 모호한 동작을 모두 API 계약으로 정합니다.

예를 들어 이 문서에서는 다음 계약을 사용한다고 가정합니다.

```text
format == NULL:
  오류

capacity > 0 && buffer == NULL:
  오류

capacity == 0:
  buffer에 접근하지 않고 필요한 전체 길이만 계산 가능

%s의 인자가 NULL:
  "(null)" 출력

문자열 끝에 '%'만 남음:
  포맷 오류

%x 등 지원하지 않는 지정자:
  포맷 오류

버퍼가 작음:
  오류가 아니라 정상적인 잘림(truncation)

성공 반환값:
  종료 NUL을 제외한 전체 필요 문자 수

길이를 int로 표현할 수 없음:
  오류
```

이 규칙은 하나의 가능한 API 설계입니다. 표준 `printf`의 모든 동작을 그대로 의미하는 것은 아닙니다.

특히 표준 `printf`의 `%s`에 `NULL`을 전달해도 항상 `"(null)"`이 출력된다고 가정하면 안 됩니다. 직접 만든 함수에서 그렇게 동작시키려면 별도의 계약으로 정의해야 합니다.

## 반환 길이의 의미

버퍼가 작더라도 필요한 전체 길이를 알고 싶다면 **실제로 기록한 길이**와 **논리적으로 생성하려 한 전체 길이**를 분리해야 합니다.

예:

```text
출력하려는 문자열:
  "abcdef"

capacity:
  4

실제 버퍼:
  "abc\0"

실제로 저장한 문자 수:
  3

전체 필요 문자 수:
  6
```

반환값을 전체 필요 길이로 정의하면 호출자는 필요한 크기를 계산할 수 있습니다.

```text
필요 buffer 크기 = 반환 길이 + 1
```

마지막 `1`은 종료 NUL 바이트입니다.

## 출력 상태 구조체

출력 로직을 한곳에 모으기 위해 다음과 같은 내부 구조체를 사용할 수 있습니다.

```c
struct output {
    char *buffer;
    size_t capacity;

    /*
     * 종료 NUL을 제외하고 논리적으로 출력하려 한
     * 전체 문자 수
     */
    size_t length;

    int failed;
};
```

여기서 `length`는 실제 버퍼에 기록된 문자 수가 아니라 **잘림이 없었다면 생성되었을 전체 길이**입니다.

이 구분이 중요합니다.

## 모든 출력을 하나의 함수로 보내기

일반 문자, 문자열, 정수 출력이 각각 다른 방식으로 버퍼 경계를 계산하면 실수가 생기기 쉽습니다.

모든 문자 기록을 하나의 함수로 보내는 방식이 단순합니다.

```c
static void output_char(
    struct output *output,
    char character
) {
    if (output->failed) {
        return;
    }

    if (output->length == SIZE_MAX) {
        output->failed = 1;
        return;
    }

    if (output->capacity > 0 &&
        output->buffer != NULL &&
        output->length < output->capacity - 1) {
        output->buffer[output->length] = character;
    }

    ++output->length;
}
```

이 함수는 두 일을 동시에 합니다.

```text
1. 공간이 있으면 실제 문자를 기록
2. 공간 여부와 관계없이 전체 필요 길이를 증가
```

따라서 버퍼가 작아져도 논리 길이는 계속 계산됩니다.

`capacity == 0`일 때는 `capacity - 1`을 계산하지 않도록 조건의 평가 순서에 주의합니다.

## NUL 종료

버퍼를 문자열로 반환한다면 성공 여부와 잘림 여부를 떠나, API가 허용하는 범위에서 NUL 종료 규칙을 일관되게 적용해야 합니다.

다음 계약을 사용할 수 있습니다.

```text
capacity > 0 && buffer != NULL이면
반환 전에 buffer 안의 가능한 마지막 출력 위치에 '\0'을 기록한다.
```

출력 종료 처리 예:

```c
static void output_terminate(
    struct output *output
) {
    if (output->buffer == NULL ||
        output->capacity == 0) {
        return;
    }

    size_t index = output->length;

    if (index >= output->capacity) {
        index = output->capacity - 1;
    }

    output->buffer[index] = '\0';
}
```

예를 들어 `capacity == 1`이면 실제 문자는 하나도 기록할 수 없지만 다음은 가능합니다.

```text
buffer[0] = '\0'
```

따라서

```text
capacity == 1
```

은 “빈 C 문자열만 저장할 수 있는 버퍼”라고 이해할 수 있습니다.

## `capacity == 0`

필요한 길이만 계산하려면 실제 버퍼 없이 호출할 수 있도록 설계할 수 있습니다.

예:

```c
int required = diagnostic_format(
    NULL,
    0,
    "name=%s count=%d",
    name,
    count
);
```

이 API가 이를 지원한다고 정했다면 `capacity == 0`에서는 `buffer`를 역참조해서는 안 됩니다.

반면

```text
capacity > 0 && buffer == NULL
```

은 실제 저장 공간이 필요한데 포인터가 없으므로 오류로 처리할 수 있습니다.

이 두 경우를 구분해야 합니다.

## `%s` 출력

`%s`를 만나면 다음 가변 인자를 `const char *`로 읽습니다.

```c
const char *text =
    va_arg(arguments, const char *);
```

이 문서의 계약에서 `NULL`은 `"(null)"`로 처리한다고 정했다면 다음처럼 바꿀 수 있습니다.

```c
if (text == NULL) {
    text = "(null)";
}
```

그 뒤 각 문자를 `output_char`로 보냅니다.

```c
while (*text != '\0') {
    output_char(output, *text);
    ++text;
}
```

여기에는 호출자가 지켜야 할 중요한 전제가 있습니다.

`text != NULL`이라면 `text`는 유효하게 NUL 종료된 C 문자열을 가리켜야 합니다.

함수는 포인터만 보고 실제 접근 가능한 버퍼 길이를 알아낼 수 없습니다.

## `%d` 출력과 `INT_MIN`

정수를 10진수로 출력할 때 음수는 부호와 크기를 나누어 처리할 수 있습니다.

단순히 다음처럼 작성하면 문제가 있습니다.

```c
int value = INT_MIN;
int magnitude = -value;
```

2의 보수 표현을 사용하는 흔한 구현에서 `INT_MIN`의 크기는 `INT_MAX`보다 1 크므로 양의 `int`로 표현되지 않습니다.

따라서 `-INT_MIN`은 `int` 범위를 벗어날 수 있습니다.

unsigned 산술을 사용하면 signed negation 없이 크기를 만들 수 있습니다.

```c
unsigned int magnitude;

if (value < 0) {
    output_char(output, '-');
    magnitude = 0u - (unsigned int)value;
} else {
    magnitude = (unsigned int)value;
}
```

핵심은 음수를 먼저 unsigned 타입으로 변환한 뒤 unsigned 산술로 크기를 얻는 것입니다.

## unsigned 산술로 크기가 만들어지는 이유

C에서 signed 정수를 대응하는 unsigned 타입으로 변환하면 unsigned 타입의 범위에 맞도록 값이 변환됩니다.

예를 들어 `value`가 음수일 때

```c
(unsigned int)value
```

는 대응하는 unsigned 값이 됩니다.

그 뒤

```c
0u - (unsigned int)value
```

는 unsigned 산술로 계산되므로 `INT_MIN`의 크기도 표현할 수 있습니다.

이 방법은 다음 위험한 연산을 하지 않습니다.

```c
-value   /* value == INT_MIN이면 문제 */
```

## 10진수 자릿수 출력

`magnitude`의 자릿수를 뒤에서부터 얻을 수 있습니다.

```c
char digits[sizeof(unsigned int) * CHAR_BIT];
size_t count = 0;

do {
    digits[count++] =
        (char)('0' + magnitude % 10u);

    magnitude /= 10u;
} while (magnitude != 0);
```

나머지 연산으로 얻은 숫자는 역순이므로 뒤에서 앞으로 출력합니다.

```c
while (count > 0) {
    --count;
    output_char(output, digits[count]);
}
```

`0`도 출력되어야 하므로 `while`보다 `do ... while` 형태가 편리합니다.

이 코드를 사용하려면 `<limits.h>`의 `CHAR_BIT`가 필요합니다.

## 포맷 파서

포맷 문자열을 왼쪽에서 오른쪽으로 읽습니다.

개념적인 구조:

```c
while (*format != '\0') {
    if (*format != '%') {
        output_char(output, *format);
        ++format;
        continue;
    }

    ++format;

    if (*format == '\0') {
        /* 끝에 '%'만 남음: 포맷 오류 */
        break;
    }

    switch (*format) {
    case '%':
        output_char(output, '%');
        break;

    case 's':
        /* const char * 읽기 */
        break;

    case 'd':
        /* int 읽기 */
        break;

    default:
        /* 지원하지 않는 포맷 지정자 */
        break;
    }

    ++format;
}
```

중요한 점은 **유효한 포맷 지정자를 확인한 경우에만 그 지정자에 대응하는 `va_arg`를 호출하는 것**입니다.

예를 들어 `%x`를 지원하지 않는다면 `%x`를 만난 즉시 포맷 오류로 처리하고 임의의 타입으로 가변 인자를 읽지 않는 편이 좋습니다.

## 포맷 오류와 부분 출력

미지원 지정자나 끝의 `%`를 오류로 처리한다면 오류가 발견되기 전에 일부 문자가 이미 버퍼에 기록되었을 수 있습니다.

따라서 API는 오류 발생 시 버퍼 내용의 의미도 정해야 합니다.

단순한 계약은 다음과 같습니다.

```text
포맷 오류 시:
  -1 반환
  버퍼에는 오류가 발견되기 전까지의 일부 출력이 남을 수 있음
  capacity > 0 && buffer != NULL이면 가능한 위치에서 NUL 종료
  부분 출력 내용에 의존해서는 안 됨
```

더 강한 계약이 필요하다면 먼저 포맷 전체를 검증하거나 임시 버퍼를 사용할 수 있지만 구현 복잡도가 커집니다.

이 문서의 제한된 포맷터에서는 실패 시 부분 결과를 보장하지 않는 정책이 단순합니다.

## 반환 타입이 `int`일 때 길이 검사

내부 논리 길이는 `size_t`로 계산할 수 있습니다.

```c
size_t length;
```

하지만 공개 함수가

```c
int diagnostic_format(...);
```

처럼 `int`를 반환한다면 성공 길이를 `int`로 표현할 수 있는지도 확인해야 합니다.

예:

```c
if (output.length > INT_MAX) {
    return -1;
}

return (int)output.length;
```

따라서 두 종류의 길이 경계를 구분합니다.

```text
size_t 계산 자체의 overflow
int 반환값으로 표현 가능한 범위 초과
```

`length + 1`로 필요한 버퍼 크기를 계산하는 호출자도 반환값에 1을 더할 때 자신의 타입 범위를 확인해야 합니다.

## 두 번 순회가 필요한 경우

일부 구현은 먼저 필요한 길이를 계산하고 그 뒤 실제 출력을 수행할 수 있습니다.

```text
1차 순회:
  필요한 전체 길이 계산

2차 순회:
  실제 버퍼에 출력
```

이 경우 같은 원본 `va_list`를 두 번 처음부터 순회해야 하므로 각각 복사본이 필요합니다.

```c
va_list measure_args;
va_list write_args;

va_copy(measure_args, arguments);
va_copy(write_args, arguments);

/* measure_args 소비 */
/* write_args 소비 */

va_end(measure_args);
va_end(write_args);
```

한 번 소비한 `va_list`를 자동으로 처음 위치로 되돌릴 수 있다고 가정하면 안 됩니다.

다만 앞에서 설명한 `output_char`처럼 논리 길이와 실제 쓰기를 동시에 처리하면 제한된 포맷터에서는 한 번의 순회만으로도 잘림과 전체 길이 계산을 함께 처리할 수 있습니다.

## 같은 원본 `va_list` 보존 테스트

`diagnostic_vformat`이 원본 `va_list`를 소비하지 않는다는 계약을 갖는다면 이를 테스트할 수 있습니다.

예를 들어 테스트용 래퍼에서 하나의 원본으로 두 복사본을 만들어 각각 같은 함수에 전달합니다.

```c
va_list first;
va_list second;

va_copy(first, arguments);
va_copy(second, arguments);

int left = diagnostic_vformat(
    buffer1,
    sizeof buffer1,
    format,
    first
);

int right = diagnostic_vformat(
    buffer2,
    sizeof buffer2,
    format,
    second
);

va_end(first);
va_end(second);
```

그리고 다음을 확인합니다.

```text
left == right
buffer1과 buffer2의 결과가 같음
```

중요한 것은 소비된 동일 `va_list` 객체를 아무 처리 없이 다시 호출하는 테스트가 아니라, `va_copy`로 독립 순회 상태를 만들어 사용하는 것입니다.

## 테스트할 내용

### 기본 포맷

- 빈 format
- 일반 문자만 있는 format
- `%s`
- `%d`
- `%%`
- `%s`, `%d`, `%%` 혼합
- 여러 지정자가 연속되는 경우

### 정수 경계

- `0`
- 양수
- 음수
- `INT_MIN`
- `INT_MAX`

특히 `INT_MIN` 테스트는 signed negation을 사용하는 잘못된 구현을 찾는 데 중요합니다.

### 문자열

- 빈 문자열 `""`
- 일반 문자열
- 긴 문자열
- `%s`의 `NULL` 정책
- 여러 `%s` 연속 사용

### 버퍼 용량

다음 capacity를 구분해서 테스트합니다.

```text
capacity == 0
capacity == 1
출력보다 작은 버퍼
NUL까지 정확히 맞는 버퍼
출력보다 큰 버퍼
```

예를 들어 `"abc"`를 저장하려면 다음 네 바이트가 필요합니다.

```text
'a' 'b' 'c' '\0'
```

따라서 정확히 맞는 capacity는 `4`입니다.

### 잘림

버퍼가 작아도 다음을 확인합니다.

```text
실제 기록은 buffer 범위를 넘지 않음
가능하면 NUL 종료됨
반환 길이는 잘리기 전 전체 필요 길이
```

### 포맷 오류

- 문자열 끝에 `%`
- `%x`
- `%q`
- 지원하지 않는 다른 지정자

오류 시 반환값과 NUL 종료 정책이 계약과 일치하는지 확인합니다.

### `va_list`

- `va_copy`로 만든 복사본이 동일한 결과를 생성하는지
- `diagnostic_vformat`이 원본을 보존한다고 정했다면 그 계약을 지키는지
- 모든 `va_start`와 `va_copy`에 대응하는 `va_end`가 있는지 코드 검토

잘못된 가변 인자 타입 자체를 실행해 오류 반환을 기대하는 테스트는 작성하지 않습니다.

## 가변 인자 코드를 읽을 때 확인할 사항

- 함수는 가변 인자의 개수나 끝을 어떤 규칙으로 아는가?
- 각 `va_arg` 타입이 호출자가 실제로 전달해야 하는 타입과 일치하는가?
- 기본 인자 승격을 고려했는가?
- `float`를 `double`로 읽는가?
- 작은 정수 타입을 승격 후 타입으로 읽는가?
- 포인터 sentinel의 타입이 명확한가?
- `va_start`한 모든 `va_list`에 `va_end`가 있는가?
- `va_copy`한 모든 복사본에 `va_end`가 있는가?
- 독립 순회가 필요한데 단순 대입으로 `va_list`를 복사하지 않았는가?
- 전달받은 원본 `va_list`를 보존할지 소비할지 계약이 명확한가?
- 미지원 포맷 지정자를 만나기 전에 불필요한 `va_arg`를 호출하지 않는가?
- 실제 버퍼 기록 위치와 전체 논리 길이를 구분하는가?
- `capacity == 0`에서 버퍼에 접근하지 않는가?
- `capacity == 1`에서 NUL만 기록할 수 있음을 고려하는가?
- 문자열 출력이 버퍼 범위를 넘지 않는가?
- `%d`에서 `INT_MIN`을 signed negation하지 않는가?
- 내부 `size_t` 길이가 넘치는 경우를 검사하는가?
- `int` 반환 타입으로 전체 길이를 표현할 수 있는지도 검사하는가?
- 오류가 발생했을 때 부분 출력의 의미가 문서화되어 있는가?

## 완료 기준

1. 가변 인자에는 개수와 타입 정보가 자동으로 포함되지 않는 이유를 설명합니다.
2. 개수, sentinel, 포맷 문자열 방식으로 가변 인자의 끝을 정하는 방법을 구분합니다.
3. 포맷 문자열과 실제 가변 인자 타입이 일치해야 하는 이유를 설명합니다.
4. 잘못된 가변 인자 타입을 함수가 일반적인 런타임 타입 검사로 잡을 수 없음을 설명합니다.
5. 기본 인자 승격 후 타입으로 `va_arg`를 호출합니다.
6. `float`를 `double`로, 작은 정수 타입을 승격된 정수 타입으로 읽습니다.
7. 포인터 sentinel은 기대하는 포인터 타입으로 명확히 전달합니다.
8. `va_start`와 `va_copy`로 초기화한 각 `va_list`에 `va_end`를 호출합니다.
9. 독립적인 가변 인자 순회가 필요할 때 `va_copy`를 사용합니다.
10. 전달받은 원본 `va_list`를 보존하는 API라면 복사본만 소비합니다.
11. 제한된 포맷 문법과 미지원 지정자 처리 규칙을 먼저 정의합니다.
12. `%s`의 `NULL`, 끝의 `%`, 작은 버퍼의 동작을 API 계약으로 명시합니다.
13. 실제 기록 범위와 잘리기 전 전체 필요 길이를 분리합니다.
14. `capacity == 0`에서는 버퍼에 접근하지 않고 길이만 계산할 수 있도록 구현할 수 있습니다.
15. `capacity > 0`인 유효한 출력 버퍼는 가능한 위치에서 NUL 종료합니다.
16. `%d`에서 `INT_MIN`을 signed negation하지 않고 unsigned 산술로 크기를 계산합니다.
17. 내부 `size_t` 길이 overflow와 `int` 반환 범위 초과를 각각 검사합니다.
18. 정상 출력뿐 아니라 경계 capacity, 잘림, 포맷 오류, 정수 경계, `va_list` 복사 규칙까지 테스트합니다.
