# C++98 프로그램과 타입 모델

## 목표

C++98 모드에서 compiler가 실제로 허용하는 문법과 표준 라이브러리 범위 안에서 여러 파일 프로그램을 구성합니다. Modern C++ 코드를 문법만 비슷하게 바꾸는 데 그치지 않고, C++98에서 사용할 수 없는 기능이 담당하던 역할을 확인한 뒤 타입, 객체 수명, 소유 방식, 오류 표현을 다시 설계합니다.

이 문서에서 말하는 C++98은 compiler를 C++98 언어 모드로 실행한다는 뜻입니다. compiler의 기본 언어 모드는 설치된 compiler와 버전에 따라 달라질 수 있으므로, 소스 코드가 우연히 더 최신 표준에 의존하지 않도록 build 단계에서 표준을 명시해야 합니다.

## 표준 모드를 먼저 고정합니다

단일 소스 파일은 다음처럼 검사할 수 있습니다.

```sh
c++ -std=c++98 -Wall -Wextra -Werror -pedantic main.cpp
```

여러 `.cpp`로 구성된 프로그램도 모든 번역 단위를 같은 표준 모드와 warning 정책으로 컴파일해야 합니다.

```sh
c++ -std=c++98 -Wall -Wextra -Werror -pedantic -c main.cpp
c++ -std=c++98 -Wall -Wextra -Werror -pedantic -c Counter.cpp
c++ main.o Counter.o -o app
```

compiler 기본 모드에 맡기면 소스 일부에서 실수로 C++11 이후 문법이나 라이브러리를 사용해도 개발 환경에서는 통과할 수 있습니다. 따라서 로컬 build, test build, CI가 모두 같은 `-std=c++98` 기준을 사용하도록 고정합니다.

C++98에는 다음과 같은 Modern C++ 기능이 없습니다.

- `auto`를 이용한 타입 추론
- range-based `for`
- lambda
- `nullptr`
- scoped enum인 `enum class`
- 이동 생성자와 rvalue reference
- `std::unique_ptr`, `std::optional`, `std::variant`
- `override`, `final`, `noexcept`

예를 들어 lambda가 필요하던 자리는 일반 함수나 함수 객체로, `nullptr`는 null pointer constant인 `0`으로, `std::optional`이 표현하던 "값이 있을 수도 없을 수도 있음"은 별도 상태 값이나 결과 객체로 표현할 수 있습니다.

중요한 점은 Modern C++ 기능을 무조건 일대일로 흉내 내는 것이 아니라, 그 기능이 원래 해결하던 문제를 C++98에서 명시적으로 표현하는 것입니다.

## 번역 단위와 헤더

C++ 프로그램은 보통 여러 `.cpp`와 헤더로 나뉩니다. 각 `.cpp`는 전처리 과정에서 자신이 `#include`한 헤더의 내용을 포함한 뒤 하나의 **번역 단위(translation unit)** 로 컴파일됩니다. 서로 다른 `.cpp`는 별도로 컴파일되므로, 한 `.cpp`에서 정의한 이름이 다른 `.cpp`에 자동으로 알려지지는 않습니다.

일반적인 구성은 다음과 같습니다.

- 헤더: 여러 번역 단위가 공유해야 하는 선언
- `.cpp`: 일반 함수와 비-template 멤버 함수의 정의
- template: 사용하는 번역 단위에서 정의를 볼 수 있도록 보통 헤더에 정의

```cpp
#ifndef STORE_HPP
#define STORE_HPP

#include <string>

class Store {
public:
    bool get(const std::string &key, std::string &value) const;
};

#endif
```

include guard는 같은 헤더가 하나의 번역 단위에 여러 경로로 포함되더라도 선언이 중복 처리되는 것을 막습니다.

```cpp
#ifndef STORE_HPP
#define STORE_HPP

// 헤더 내용

#endif
```

C++98에서도 `#pragma once`를 지원하는 compiler가 많지만 C++98 표준 기능은 아닙니다. compiler 간 이식성을 우선한다면 include guard를 사용합니다.

헤더는 자신이 사용하는 타입이나 선언에 필요한 헤더를 직접 포함해야 합니다. 예를 들어 헤더가 `std::string`을 사용한다면 `<string>`을 직접 포함합니다.

다른 헤더가 우연히 `<string>`을 포함해 줄 것이라고 기대하면 안 됩니다. 그 헤더의 내부 구현이 바뀌는 순간 현재 헤더가 컴파일되지 않을 수 있습니다.

헤더 하나만 독립적으로 포함해도 그 헤더의 선언을 해석할 수 있도록 만드는 것이 안전합니다.

## 선언과 정의

**선언(declaration)** 은 함수나 타입의 이름과 형태를 compiler에게 알립니다. **정의(definition)** 는 실제 함수 본문이나 객체의 저장 공간처럼 프로그램이 사용할 실체를 제공합니다.

```cpp
// Counter.hpp
#ifndef COUNTER_HPP
#define COUNTER_HPP

class Counter {
public:
    Counter();
    void increment();
    int value() const;

private:
    int value_;
};

#endif
```

```cpp
// Counter.cpp
#include "Counter.hpp"

Counter::Counter() : value_(0) {}

void Counter::increment()
{
    ++value_;
}

int Counter::value() const
{
    return value_;
}
```

멤버 함수 정의는 헤더의 선언과 정확히 일치해야 합니다. 함수 이름과 매개변수 타입뿐 아니라 멤버 함수 뒤의 `const`도 함수 타입을 구분하는 일부입니다.

```cpp
int value() const;
```

와

```cpp
int value();
```

는 서로 다른 멤버 함수입니다.

항상 구현 `.cpp`에서 대응하는 헤더를 직접 포함하면 선언과 정의가 어긋난 문제를 compiler가 더 일찍 발견할 수 있습니다.

## 기본 타입과 정수 변환

C++의 정수 타입 크기를 임의로 가정하면 안 됩니다. 표준은 타입 사이의 최소 관계와 범위를 규정하지만, 예를 들어 `int`가 모든 환경에서 정확히 32비트라고 보장하지는 않습니다.

문자열 입력을 `int`로 바꾸어야 한다면 다음 단계를 분리해서 생각합니다.

1. 문자열이 유효한 정수 표현인지 확인합니다.
2. 변환 과정 자체에서 범위 초과가 발생했는지 확인합니다.
3. 얻은 `long` 값이 현재 환경의 `int` 범위 안인지 확인합니다.
4. 모든 검사를 통과한 뒤 `int`로 변환합니다.

```cpp
#include <cerrno>
#include <climits>
#include <cstdlib>

char *end = 0;
errno = 0;

const long parsed = std::strtol(text, &end, 10);

if (errno == ERANGE
    || end == text
    || *end != '\0'
    || parsed < INT_MIN
    || parsed > INT_MAX) {
    throw ParseError("invalid integer");
}

const int value = static_cast<int>(parsed);
```

각 검사의 의미는 다음과 같습니다.

- `errno == ERANGE`: 결과가 `long`이 표현할 수 있는 범위를 벗어났습니다.
- `end == text`: 숫자로 변환된 문자가 하나도 없습니다.
- `*end != '\0'`: 숫자 뒤에 변환되지 않은 문자가 남아 있습니다.
- `parsed < INT_MIN || parsed > INT_MAX`: `long`으로는 표현 가능하지만 `int`로는 표현할 수 없습니다.

예를 들어 `"42"`는 성공하지만 `"42x"`는 `x`가 남으므로 실패합니다. 빈 문자열이나 `"hello"`는 숫자로 변환된 문자가 없으므로 실패합니다.

`std::strtol`은 선행 공백과 부호를 허용합니다. 프로그램의 입력 형식에서 선행 공백까지 금지해야 한다면 `strtol` 호출만으로 충분하지 않으며, 그 형식 규칙을 별도로 검사해야 합니다.

cast 자체는 값의 안전성을 검사하지 않습니다. 범위를 확인한 뒤에만 목표 타입으로 변환합니다.

## C++ cast

C 스타일 cast는 여러 종류의 변환을 같은 문법으로 표현하므로 코드만 보고 변환 의도를 구분하기 어렵습니다.

```cpp
int value = (int)parsed;
```

가능하면 목적에 맞는 C++ cast를 사용합니다.

- `static_cast`: 수치 타입 변환, 상속 관계에서 정적으로 허용되는 변환 등 일반적인 명시적 변환
- `dynamic_cast`: 다형 클래스 계층에서 실행 중 실제 객체 타입을 확인하는 변환
- `const_cast`: `const` 또는 `volatile` 한정자를 추가하거나 제거하는 변환
- `reinterpret_cast`: 관련 없는 pointer 타입 사이 변환처럼 저수준 표현을 재해석하는 변환

예를 들어 범위를 검사한 `long`을 `int`로 변환할 때는 `static_cast`를 사용할 수 있습니다.

```cpp
const int value = static_cast<int>(parsed);
```

`dynamic_cast`를 이용해 base pointer에서 derived pointer로 내려가며 실제 타입을 검사하려면 source가 **다형 타입(polymorphic type)** 이어야 합니다. 즉, 해당 클래스에 적어도 하나의 virtual 함수가 있어야 합니다.

```cpp
class Base {
public:
    virtual ~Base() {}
};

class Derived : public Base {
};

Base *base = new Derived;
Derived *derived = dynamic_cast<Derived *>(base);

if (derived != 0) {
    // 실제 객체가 Derived이거나 Derived에서 파생된 타입
}
```

pointer에 대한 `dynamic_cast`가 실패하면 결과는 null pointer입니다. reference에 대한 실패는 `std::bad_cast` 예외를 발생시킵니다.

`const_cast`로 `const`를 제거할 수 있다는 사실이 원래 const 객체를 안전하게 수정할 수 있다는 뜻은 아닙니다. 실제로 const로 정의된 객체를 강제로 수정하려 하면 정의되지 않은 동작이 될 수 있습니다.

`reinterpret_cast`는 타입 안전성을 제공하지 않으며 주소의 유효성, 정렬, 객체 수명 같은 조건도 검사하지 않습니다.

즉, 어떤 C++ cast도 값의 범위나 pointer가 가리키는 객체의 수명을 자동으로 보장해 주지 않습니다.

## `const`

다음 선언에는 두 위치의 `const`가 서로 다른 의미를 가집니다.

```cpp
const std::string &name() const;
```

반환 타입의 `const`:

```cpp
const std::string &
```

호출자가 **반환된 참조를 통해** 문자열을 수정할 수 없다는 뜻입니다. 문자열 객체 자체가 프로그램 전체에서 절대 변경되지 않는다는 뜻은 아닙니다.

멤버 함수 뒤의 `const`:

```cpp
name() const
```

이 멤버 함수가 const 객체에서도 호출될 수 있음을 뜻합니다. 함수 안에서는 `this`가 const 객체를 가리키는 것처럼 취급되므로 일반적인 non-`mutable` 멤버를 수정할 수 없고, 같은 객체의 non-const 멤버 함수도 직접 호출할 수 없습니다.

```cpp
class Person {
public:
    const std::string &name() const;

private:
    std::string name_;
};
```

이 방식은 내부 문자열을 불필요하게 복사하지 않고 읽기 전용 참조를 제공할 수 있습니다. 다만 반환한 참조는 원래 `Person` 객체의 멤버를 가리키므로, 그 `Person` 객체가 소멸한 뒤에는 참조도 더 이상 유효하지 않습니다.

### `iterator`와 `const_iterator`

const container를 순회하거나 container의 원소를 수정하지 않는다는 의도를 타입으로 표현하려면 `const_iterator`를 사용합니다.

```cpp
std::map<std::string, int>::const_iterator found = values.find(key);
```

C++11 이후처럼 `auto` 타입 추론을 사용할 수 없으므로 C++98에서는 긴 iterator 타입을 직접 적는 경우가 많습니다.

`iterator`와 `const_iterator`의 중요한 차이는 원소를 수정할 수 있는지입니다. `const_iterator`를 통해서는 container 원소를 수정할 수 없습니다.

## enum과 이름 범위

C++98의 enum은 Modern C++의 `enum class`처럼 자체적인 강한 이름 범위를 만들지 않습니다. 일반 enum의 enumerator 이름은 enum이 선언된 바깥 scope에 들어갑니다.

```cpp
enum Status {
    Queued,
    Running,
    Done
};
```

따라서 같은 scope에 `Queued` 같은 이름을 또 선언하면 충돌할 수 있습니다.

이름 충돌을 줄이기 위해 enum을 class나 struct 안에 둘 수 있습니다.

```cpp
struct Status {
    enum Value {
        Queued,
        Running,
        Done
    };
};
```

이 경우 타입과 값은 다음처럼 사용합니다.

```cpp
Status::Value status = Status::Queued;
```

C++98의 일반 enum 값은 정수 타입으로 암묵 변환될 수 있습니다.

```cpp
int code = Status::Queued;
```

반대로 임의의 정수가 자동으로 `Status::Value`가 되는 것은 아닙니다. 명시적인 cast를 쓰면 enum 타입으로 변환할 수 있지만, 그 cast가 값이 `Queued`, `Running`, `Done` 중 하나인지 검증해 주지는 않습니다.

따라서 파일, 네트워크, 사용자 입력처럼 외부에서 받은 정수를 enum으로 바꿀 때는 정의된 값인지 먼저 검사합니다.

```cpp
Status::Value parseStatus(int value)
{
    switch (value) {
        case Status::Queued:
            return Status::Queued;
        case Status::Running:
            return Status::Running;
        case Status::Done:
            return Status::Done;
        default:
            throw ParseError("invalid status");
    }
}
```

## `0`과 null pointer

C++98에는 `nullptr`가 없습니다. pointer가 아무 객체도 가리키지 않는 상태를 표현할 때는 null pointer constant인 `0`을 사용할 수 있습니다.

```cpp
Handler *handler = 0;
```

여기서 `0`은 pointer 전용 타입이 아닙니다. 원래 정수 literal이지만 pointer가 필요한 문맥에서는 null pointer로 변환될 수 있습니다.

이 특성은 overload와 함께 사용할 때 특히 중요합니다.

```cpp
void select(int value);
void select(Handler *handler);

select(0);
```

이 호출은 `select(int)`를 선택합니다. `0` 자체가 정수이므로 `int` overload가 정확히 일치하고, pointer overload에는 null pointer 변환이 필요하기 때문입니다. 따라서 C++11의 `nullptr`처럼 "반드시 pointer overload를 선택하는 값"이라고 생각하면 안 됩니다.

여러 pointer overload가 있는 경우에는 `0`만으로 어느 pointer 타입인지 결정할 수 없어 호출이 모호해질 수도 있습니다.

```cpp
void reset(Reader *reader);
void reset(Writer *writer);

// reset(0);  // 어느 pointer overload인지 결정할 수 없어 모호함
```

필요하다면 의도한 pointer 타입을 명시할 수 있습니다.

```cpp
reset(static_cast<Reader *>(0));
```

`NULL`도 C++98에서 pointer 전용 타입이라고 보장되지 않습니다. 구현이 정수 상수 형태의 macro로 정의할 수 있으므로 overload 해석에서는 `0`과 비슷한 문제가 생길 수 있습니다.

따라서 C++98 API에서는 정수와 여러 pointer 타입을 같은 함수 이름으로 과도하게 overload하지 않는 것이 좋습니다.

## 이름과 scope

변수의 scope는 가능한 한 실제로 필요한 범위로 좁힙니다. 이렇게 하면 같은 이름을 실수로 재사용하거나, 이미 필요하지 않은 객체가 계속 살아 있는 문제를 줄일 수 있습니다.

```cpp
{
    std::map<Key, Value>::iterator found = data.find(key);

    if (found != data.end())
        return found->second;
}
```

위의 `found`는 중괄호 블록 안에서만 존재합니다. 블록이 끝난 뒤에는 같은 함수의 다른 작업에서 별도의 iterator를 선언할 수 있습니다.

특히 iterator나 pointer는 자신이 참조하던 container나 객체가 변경된 뒤에도 같은 변수 이름이 오래 남아 있으면 유효하다고 착각하기 쉽습니다. 필요한 작업 가까이에서 선언하고 scope를 짧게 유지하면 이런 실수를 줄일 수 있습니다.

## build 문제를 구분합니다

문제가 어느 단계에서 발생했는지 먼저 구분하면 원인을 찾기 쉽습니다.

### compile 오류

각 번역 단위를 object file로 만드는 과정에서 발생합니다.

대표적인 원인:

- C++98에서 지원하지 않는 문법 사용
- 타입 불일치
- 필요한 선언이나 헤더 누락
- 클래스 선언과 멤버 함수 정의 불일치
- 잘못된 `const` 사용

예:

```sh
c++ -std=c++98 -Wall -Wextra -Werror -pedantic -c Counter.cpp
```

이 단계가 실패하면 아직 linker까지 진행되지 않은 것입니다.

### link 오류

여러 object file과 library를 연결해 최종 실행 파일을 만드는 과정에서 발생합니다.

대표적인 원인:

- 선언만 있고 실제 정의가 없음
- 필요한 `.o` 또는 library를 link 명령에서 누락
- 호출한 함수에 대응하는 symbol 정의가 없음
- template 정의가 필요한 번역 단위에서 보이지 않아 필요한 인스턴스가 생성되지 않음

예를 들어 `Counter.cpp`를 컴파일했지만 link 명령에서 `Counter.o`를 빠뜨리면 `Counter`의 멤버 함수 정의를 찾지 못하는 link 오류가 발생할 수 있습니다.

### 실행 오류

compile과 link는 성공했지만 프로그램을 실행하는 동안 발생하는 문제입니다.

대표적인 원인:

- 이미 소멸한 객체를 가리키는 pointer 또는 reference 사용
- 잘못된 입력 처리
- 범위 검사 누락
- 시스템 호출 실패 처리 누락
- 소유권 오류로 인한 memory leak 또는 중복 해제

compile 성공은 프로그램의 수명과 입력 처리까지 안전하다는 뜻이 아닙니다.

## template 정의 위치

template는 일반 함수와 달리 compiler가 실제 타입에 맞는 코드를 만들어 내는 시점에 정의 내용을 알아야 합니다.

예를 들어 다음 선언만 헤더에 있고 정의가 `.cpp`에 있으면 다른 번역 단위에서 사용할 때 문제가 생길 수 있습니다.

```cpp
// maxValue.hpp
template <typename T>
T maxValue(const T &a, const T &b);
```

일반적인 C++98 프로젝트에서는 template 정의까지 헤더에 둡니다.

```cpp
#ifndef MAX_VALUE_HPP
#define MAX_VALUE_HPP

template <typename T>
T maxValue(const T &a, const T &b)
{
    return a < b ? b : a;
}

#endif
```

특정 타입에 대한 명시적 인스턴스화를 별도로 관리하는 방법도 있지만, 단순한 프로젝트에서는 "template 선언과 정의를 함께 헤더에 둔다"는 규칙이 가장 이해하기 쉽고 실수를 줄이기 쉽습니다.

## 자주 놓치는 문제

- 프로그램 build에는 `-std=c++98`을 쓰지만 test build는 compiler 기본 모드로 실행합니다.
- 헤더에 `using namespace std;`를 두어 그 헤더를 포함한 모든 코드의 이름 검색에 영향을 줍니다.
- 헤더가 직접 필요한 표준 헤더를 포함하지 않고 다른 헤더의 간접 include에 의존합니다.
- 문자열을 `long`으로 읽은 뒤 범위를 확인하지 않고 바로 `int`로 cast합니다.
- `strtol`이 일부 문자만 변환했는데도 성공으로 처리합니다.
- `NULL`이나 `0`을 `nullptr`와 같은 pointer 전용 값이라고 생각합니다.
- 멤버 함수 선언과 정의에서 뒤의 `const`가 다릅니다.
- const reference를 반환하면 원본 객체보다 reference가 오래 살아도 된다고 생각합니다.
- enum으로 cast하면 정의된 enumerator인지 자동으로 검증된다고 생각합니다.
- template 정의를 `.cpp`에 두고 다른 번역 단위에서 사용합니다.
- 한 `.cpp`에서 선언된 이름을 다른 `.cpp`도 자동으로 안다고 생각합니다.

## 완료 기준

다음 항목을 설명하고 코드에서 적용할 수 있으면 이 범위의 목표를 달성한 것입니다.

- 모든 build와 test에서 C++98 표준 모드와 warning 정책을 고정합니다.
- 번역 단위가 무엇인지 설명하고, 헤더와 `.cpp` 사이의 선언·정의 관계를 구분합니다.
- 헤더가 필요한 의존성을 직접 포함하도록 구성합니다.
- Modern C++ 기능이 하던 역할을 확인한 뒤 C++98에서 사용할 수 있는 타입과 구조로 다시 설계합니다.
- 문자열 정수를 변환할 때 변환 성공 여부, 남은 문자, `long` 범위, 목표 정수 타입 범위를 구분해 검사합니다.
- C++ cast 각각의 목적과 한계를 구분합니다.
- `const`가 reference와 멤버 함수에서 각각 무엇을 제한하는지 설명합니다.
- C++98 enum의 이름 범위와 정수 변환 특성을 이해하고 외부 입력을 검증합니다.
- `0`과 `NULL`이 pointer 전용 타입이 아니며 overload 선택에 영향을 줄 수 있음을 이해합니다.
- template 정의가 사용하는 번역 단위에서 보여야 하는 이유를 설명합니다.
- compile, link, 실행 단계의 오류를 구분해 진단합니다.
