# C 프로그램의 구성과 전처리

C 프로그램은 소스 파일에서 곧바로 실행 파일이 만들어지는 방식이 아닙니다. 각 `.c` 파일은 전처리를 거쳐 하나의 번역 단위가 되고, 번역 단위마다 따로 컴파일된 뒤 여러 오브젝트 파일이 링크되어 실행 파일이나 라이브러리가 만들어집니다.

## 빌드 단계

```text
.c 파일 + 포함한 헤더
  ↓ 전처리
번역 단위
  ↓ 컴파일·어셈블
오브젝트 파일(.o)
  ↓ 링크
실행 파일 또는 라이브러리
```

`cc`는 이 도구들을 필요한 순서로 호출하는 컴파일러 드라이버입니다.

```sh
cc -std=c11 -Wall -Wextra -Wpedantic main.c text.c -o textstat
```

문제가 생겼을 때 전처리, 컴파일, 링크, 실행 중 어디에서 실패했는지 구분해야 합니다.

## 각 단계의 결과 확인하기

```sh
cc -std=c11 -E main.c -o main.i
cc -std=c11 -S main.c -o main.s
cc -std=c11 -c main.c -o main.o
cc main.o text.o -o textstat
```

- `-E`: 전처리 결과를 만듭니다.
- `-S`: 어셈블리 소스를 만듭니다.
- `-c`: 링크하지 않고 오브젝트 파일까지만 만듭니다.
- 마지막 명령: 오브젝트 파일을 링크합니다.

## 전처리기는 토큰을 바꿉니다

전처리기는 C 타입을 검사하거나 함수를 호출하는 단계가 아닙니다. `#include`, `#define`, 조건부 컴파일 지시문을 처리해 컴파일러가 읽을 토큰을 만듭니다.

### 객체형 매크로

```c
#define BUFFER_SIZE 4096
#define DEBUG_ENABLED 1
```

매크로 이름은 전처리 중 치환 토큰로 바뀝니다. 매크로 상수는 타입이 없으므로 타입이 있는 상수가 필요한 경우 `enum`이나 `const` 객체가 더 알맞을 수 있습니다.

### 함수형 매크로

```c
#define MIN(a, b) ((a) < (b) ? (a) : (b))
```

함수 호출처럼 보이지만 인자가 한 번만 평가된다는 보장은 없습니다.

```c
MIN(index++, limit)
```

`MIN`의 본문에서 `a`를 두 번 사용하므로 `index++`도 두 번 평가될 수 있습니다. 부수 효과가 있는 표현식은 함수형 매크로 인자로 전달하지 않는 편이 안전합니다.

괄호도 중요합니다.

```c
#define SQUARE_BAD(x) x * x
#define SQUARE(x) ((x) * (x))
```

`SQUARE_BAD(1 + 2)`는 기대한 식으로 확장되지 않습니다. 인자와 전체 결과에 괄호를 둡니다. 단, 괄호를 넣어도 중복 평가는 해결되지 않습니다.

### 여러 줄 매크로

치환 토큰를 여러 줄로 쓸 때는 각 줄 끝에 `\`를 둡니다.

```c
#define CHECK(expression)                                      \
    do {                                                       \
        if (!(expression)) {                                   \
            fprintf(stderr, "%s:%d: 실패: %s\n",             \
                    __FILE__, __LINE__, #expression);          \
            return 1;                                          \
        }                                                      \
    } while (0)
```

`do { ... } while (0)`은 여러 문장을 가진 매크로를 호출 위치에서 하나의 문장처럼 쓰기 위한 관용구입니다. 단순히 `{ ... }`만 확장하면 호출부의 세미콜론과 `if`/`else`가 예상과 다르게 결합할 수 있습니다.

### 문자열화 연산자 `#`

함수형 매크로의 치환 토큰에서 `#parameter`는 전달된 토큰을 문자열 literal로 만듭니다.

```c
#define STRINGIFY(value) #value

STRINGIFY(buffer_size)
/* "buffer_size" */
```

테스트 매크로에서 실패한 표현식을 출력할 때 유용합니다.

### 미리 정의된 매크로

```c
__FILE__
__LINE__
```

`__FILE__`은 현재 소스 파일 이름을 나타내는 문자열 literal, `__LINE__`은 현재 줄 번호를 나타내는 정수 상수로 확장됩니다.

```c
fprintf(stderr, "%s:%d: 잘못된 상태\n", __FILE__, __LINE__);
```

### 가변 인자 매크로

C99부터 함수형 매크로도 가변 인자를 받을 수 있습니다.

```c
#define LOG(format, ...) \
    fprintf(stderr, format, __VA_ARGS__)
```

매크로의 `...`와 `<stdarg.h>`의 가변 인자 함수는 다른 기능입니다. 매크로는 토큰을 확장하고, `va_list`는 실제 함수 호출로 전달된 값을 읽습니다.

호출 시 가변 인자가 비어 있는 경우까지 지원하려면 사용하는 C 표준과 컴파일러 기능을 확인해야 합니다. 이식성이 중요한 코드에서는 비어 있지 않은 인자를 요구하거나 별도 매크로를 두는 방법이 단순합니다.

### 조건부 컴파일

```c
#ifdef DEBUG
fprintf(stderr, "debug mode\n");
#endif
```

`#ifdef NAME`은 `NAME`이 정의되어 있는지 확인합니다. 같은 조건을 `defined`로 쓸 수도 있습니다.

```c
#if defined(DEBUG)
fprintf(stderr, "debug mode\n");
#endif
```

플랫폼이나 선택 기능에 따라 다른 코드를 포함할 수도 있습니다.

```c
#if defined(__linux__)
    /* Linux에서 사용할 코드 */
#elif defined(__APPLE__)
    /* macOS에서 사용할 코드 */
#else
    /* 공통 구현 */
#endif
```

컴파일 명령의 `-D` 옵션으로 매크로를 정의할 수 있습니다.

```sh
cc -DDEBUG source.c -o program
```

Makefile에서는 보통 `CPPFLAGS`에 둡니다.

```make
CPPFLAGS += -DDEBUG
```

### Include guard

헤더가 같은 번역 단위에 여러 경로로 포함되어도 선언을 한 번만 처리하도록 막습니다.

```c
#ifndef OWNED_STRING_H
#define OWNED_STRING_H

/* declarations */

#endif
```

### 토큰 결합 연산자 `##`

`##`는 두 preprocessing token을 하나로 붙입니다.

```c
#define MAKE_NAME(prefix, name) prefix##name

MAKE_NAME(test_, append)
/* test_append */
```

일반 프로그램에서 자주 필요하지는 않지만 테스트 도구나 반복 선언을 만드는 매크로를 읽을 때 의미를 알아둘 필요가 있습니다.

## 번역 단위

전처리를 마친 `.c` 파일 하나가 독립적으로 컴파일되는 번역 단위입니다.

```text
main.c + 포함한 헤더 → 번역 단위 A
text.c + 포함한 헤더 → 번역 단위 B
```

A를 컴파일할 때 B의 함수 본문은 보이지 않습니다. A가 B의 함수를 호출하려면 컴파일 시점에는 선언이 필요하고, 링크 시점에는 정의가 포함되어야 합니다.

## 선언과 정의

선언은 이름과 타입을 알려 줍니다.

```c
size_t text_length(const char *text);
extern unsigned long processed_count;
```

정의는 함수 본문이나 객체의 저장 공간을 만듭니다.

```c
size_t text_length(const char *text) {
    /* ... */
}

unsigned long processed_count = 0;
```

선언만 있고 최종 링크에 정의가 없으면 `undefined reference` 같은 오류가 발생합니다. 외부 정의가 여러 곳에 있으면 `multiple definition` 오류가 발생할 수 있습니다.

## 헤더 작성

```c
#ifndef TEXT_H
#define TEXT_H

#include <stddef.h>

size_t text_length(const char *text);
size_t text_word_count(const char *text);

#endif
```

헤더 작성 시 다음을 지킵니다.

- 헤더에서 사용하는 타입에 필요한 표준 헤더를 직접 포함합니다.
- include guard를 둡니다.
- 호출자가 알아야 하는 선언만 공개합니다.
- 일반 함수 본문과 변경 가능한 전역 객체의 정의를 넣지 않습니다.
- 구현 파일도 자신의 공개 헤더를 가장 먼저 포함해 선언과 정의의 차이를 컴파일러가 찾게 합니다.

## 내부 링키지

파일 범위 함수에 `static`을 붙이면 현재 번역 단위에서만 이름을 사용할 수 있습니다.

```c
static int is_separator(char value) {
    return value == ' ' || value == '\t' || value == '\n';
}
```

블록 내부의 `static` 객체는 이름의 사용 범위는 블록에 있지만 객체는 프로그램이 끝날 때까지 존재합니다. 이름을 사용할 수 있는 범위와 객체의 수명을 구분해야 합니다.

## 스코프·링키지·저장 기간

| 개념 | 확인할 질문 |
| --- | --- |
| 스코프 | 이 이름을 소스의 어디에서 사용할 수 있습니까? |
| 링키지 | 서로 다른 선언이 같은 함수나 객체를 뜻합니까? |
| 저장 기간 | 객체는 언제 만들어지고 언제까지 존재합니까? |

## 오브젝트 파일과 심볼 확인

```sh
nm main.o
nm text.o
ar t libtext.a
nm libtext.a
```

다음을 확인할 수 있습니다.

- 현재 오브젝트 파일이 정의한 심볼
- 다른 오브젝트가 제공해야 할 심볼
- 정적 라이브러리에 실제로 들어 있는 멤버

헤더에 선언이 있다는 사실만으로 정의가 링크에 포함되었다고 볼 수 없습니다.

## 매크로를 읽을 때 확인할 사항

- 확장된 식의 연산자 우선순위가 맞습니까?
- 같은 인자가 여러 번 평가됩니까?
- 부수 효과가 있는 표현식을 전달해도 됩니까?
- 여러 문장이 하나의 문장처럼 동작합니까?
- 어떤 `-D` 옵션과 조건부 컴파일이 연결됩니까?
- 실제 함수나 타입이 있는 상수보다 매크로가 적합한 이유가 있습니까?

## 완료 기준

1. 전처리, 컴파일과 링크를 구분합니다.
2. 번역 단위마다 따로 컴파일되는 이유를 설명합니다.
3. 선언과 정의를 헤더와 `.c` 파일에 나눕니다.
4. 함수형 매크로의 중복 평가 위험을 설명합니다.
5. `#`, `##`, `__FILE__`, `__LINE__`, `__VA_ARGS__`의 용도를 구분합니다.
6. `#if`, `defined`, `-D`와 include guard의 관계를 설명합니다.
