# Modern C++에서 C++98로 옮기기

## 목적

Modern C++에서 익힌 **값(value), 소유권(ownership), 객체 수명(lifetime), 오류 처리(error handling)** 원칙을 C++98에서도 최대한 유지하기 위한 대응표입니다.

목표는 최신 문법을 비슷한 모양으로 흉내 내는 것이 아닙니다. 먼저 Modern C++ 기능이 어떤 문제를 해결하고 어떤 보장을 제공하는지 확인한 뒤, C++98에서 **동일하거나 가능한 한 가까운 의미적 보장**을 별도의 설계 규칙으로 다시 만들어야 합니다.

예를 들어 `std::unique_ptr`를 raw pointer로 단순 치환하면 문법은 바뀌지만, "소유자가 하나뿐이며 scope를 벗어나면 자동 해제된다"는 보장은 사라집니다. 따라서 C++98에서는 소유자를 명확히 정하고 복사를 금지하며 모든 종료 경로에서 `delete`가 실행되도록 설계해야 합니다.

## 주요 대응

| Modern C++ | C++98에서의 처리 | 주의할 점 |
| --- | --- | --- |
| move semantics | 깊은 복사, 복사 금지 또는 명시적인 소유권 이전 함수 | C++98에는 이동 생성자/이동 대입이 없으므로 값 타입과 소유 타입을 구분해야 합니다. |
| Rule of Zero | 자원을 직접 소유하면 Rule of Three | destructor, copy constructor, copy assignment의 동작을 함께 정의합니다. |
| `std::unique_ptr` | raw pointer 소유자를 한 클래스에 고정하고 복사 금지 | raw pointer 자체는 소유권을 표현하지 않으므로 문서와 타입 구조로 owner를 고정합니다. |
| `std::shared_ptr` | 가능하면 값 또는 명시적인 단일 owner로 단순화; 꼭 필요하면 참조 카운트를 별도 타입으로 캡슐화 | 직접 참조 카운트를 구현하면 순환 참조, 예외 안전성, thread safety까지 고려해야 합니다. |
| `nullptr` | `0`; overload 모호성을 줄이는 API 설계 | `0`은 정수 literal이므로 pointer overload와 정수 overload가 함께 있으면 모호하거나 의도와 다른 overload가 선택될 수 있습니다. |
| `enum class` | enum을 클래스/타입 scope 안에 두고 외부 정수 입력을 검증 | C++98 enum은 강한 타입 안전성을 제공하지 않으므로 `enum class`와 완전히 동일하지 않습니다. |
| lambda | function object 또는 함수 pointer | capture가 필요한 경우 function object에 상태를 멤버로 저장합니다. |
| range-for | 명시적인 iterator loop | iterator의 시작/종료와 container 변경 여부를 직접 관리합니다. |
| `auto` | 전체 iterator와 타입 이름 작성 | 긴 iterator 타입은 typedef로 줄일 수 있습니다. |
| `override` | signature 일치 확인, compiler warning, 기반 클래스 pointer를 통한 호출 테스트 | `const`, parameter type, reference 여부가 다르면 override가 아니라 별도 함수가 될 수 있습니다. |
| `noexcept` | 예외를 던지지 않는다는 설계 규칙을 문서화하고 구현으로 보장; 필요한 경우 `throw()` 사용 | C++98의 `throw()`는 Modern C++의 `noexcept`와 의미와 구현 특성이 완전히 같지 않습니다. |
| `optional<T>` | `bool` + output parameter, 상태 값 또는 별도 결과 클래스 | 값이 존재하는 경우와 존재하지 않는 경우를 명시적으로 구분합니다. |
| `variant` | tagged union, enum + 값 필드 또는 다형성 | 현재 어떤 타입의 값이 유효한지 나타내는 tag와 실제 저장 값이 항상 일치해야 합니다. |
| `expected<T, E>` | 성공 여부와 value/error를 함께 표현하는 별도 결과 클래스 | 성공 상태에서는 value, 실패 상태에서는 error만 유효하도록 invariant를 정합니다. |
| `std::jthread` | pthread 또는 플랫폼 thread wrapper, stop flag, 명시적인 join | C++98 표준 자체에는 thread API가 없습니다. 플랫폼 API와 종료 규칙을 직접 관리해야 합니다. |
| `std::filesystem` | POSIX API 또는 플랫폼별 wrapper | 경로 형식, 오류 코드, platform 차이를 wrapper 안으로 격리하는 편이 안전합니다. |
| concepts | template이 요구하는 연산을 문서화하고 실제 instantiation을 수행하는 compile 검사 추가 | C++98 compiler는 concept 제약을 선언적으로 검사하지 못하므로 오류가 template instantiation 단계에서 나타납니다. |

## 소유권

### 소유권이란 무엇인가

여기서 **소유자(owner)** 는 자원의 수명을 끝낼 책임이 있는 객체나 함수를 뜻합니다.

raw pointer가 있다고 해서 항상 그 pointer가 owner인 것은 아닙니다.

```cpp
Handler *handler;
```

이 선언만으로는 다음을 알 수 없습니다.

- `handler`를 누가 생성했는가
- 현재 누가 소유하는가
- 누가 `delete`해야 하는가
- 함수 호출 뒤 소유권이 이동하는가
- 실패했을 때 누가 정리하는가

Modern C++에서는 타입과 signature에 소유권을 어느 정도 드러낼 수 있습니다.

```cpp
void install(std::unique_ptr<Handler> handler);
```

이 signature는 호출자가 넘긴 `Handler`의 단독 소유권이 `install` 쪽으로 이동한다는 의미를 표현합니다.

C++98에서는 보통 raw pointer를 사용하므로 같은 의미를 자동으로 표현할 수 없습니다.

```cpp
void addHandler(const std::string &name, Handler *handler);
```

따라서 함수 계약에서 **소유권 이전 시점과 실패 시 해제 책임**을 반드시 정해야 합니다.

예를 들어 다음 두 정책 중 하나를 선택할 수 있습니다.

### 정책 A: 함수 진입과 동시에 소유권 이전

```text
caller가 Handler 생성
→ addHandler 호출
→ 호출이 시작되는 순간 callee가 owner
→ 성공 여부와 관계없이 callee가 최종 정리 책임
```

이 경우 등록이 실패하더라도 caller가 다시 `delete handler`를 하면 double delete가 발생할 수 있습니다.

### 정책 B: 성공한 경우에만 소유권 이전

```text
caller가 Handler 생성
→ addHandler 호출
→ 실패: caller가 계속 owner
→ 성공: callee가 새로운 owner
```

이 경우 caller는 반환값을 검사하고 실패 시 직접 해제해야 합니다.

```cpp
Handler *handler = new Handler;

if (!registry.addHandler("main", handler)) {
    delete handler;
    handler = 0;
}
```

어느 정책을 사용하든 프로젝트 전체에서 일관되게 적용해야 합니다.

가능하면 생성과 등록을 같은 객체 내부에서 수행하여 owning raw pointer가 여러 함수 사이를 이동하는 구간을 줄이는 것이 좋습니다.

## Rule of Three

Modern C++에서 자원 관리 타입을 표준 RAII 타입으로 구성하면 사용자 정의 destructor, copy constructor, copy assignment를 작성하지 않아도 되는 경우가 많습니다. 이를 흔히 Rule of Zero라고 합니다.

C++98에서 클래스가 raw pointer, file descriptor, socket, mutex 같은 자원을 직접 소유한다면 **Rule of Three**를 검토해야 합니다.

```cpp
class Buffer {
public:
    Buffer();
    ~Buffer();

    Buffer(const Buffer &other);
    Buffer &operator=(const Buffer &other);

private:
    char *data_;
};
```

세 연산은 서로 독립적인 문제가 아닙니다.

- destructor는 현재 객체가 가진 자원을 해제합니다.
- copy constructor는 새 객체가 기존 객체의 자원을 어떻게 복사할지 결정합니다.
- copy assignment는 이미 자원을 가진 객체에 다른 값을 대입할 때 기존 자원과 새 자원을 어떻게 처리할지 결정합니다.

단순히 pointer 값만 복사하면 두 객체가 같은 주소를 owner라고 생각하게 되어 double delete가 발생할 수 있습니다.

따라서 자원 소유 클래스는 보통 다음 중 하나를 택합니다.

1. **깊은 복사**: 복사 시 별도의 자원을 새로 생성합니다.
2. **복사 금지**: 객체가 단독 소유권을 가지며 복사되지 않게 합니다.
3. **공유 소유권 타입**: 참조 카운트 등을 별도 타입 안에 구현합니다.

## 복사 금지

C++11의 `= delete`가 없으므로 C++98에서는 일반적으로 copy constructor와 copy assignment를 `private`로 선언하고 구현하지 않는 방식으로 복사를 막습니다.

```cpp
class Socket {
public:
    Socket();
    ~Socket();

private:
    Socket(const Socket &);
    Socket &operator=(const Socket &);
};
```

외부 코드가 복사를 시도하면 접근 오류가 발생합니다.

이 방식은 "복사가 금지된다"는 의도를 타입 수준에서 어느 정도 강제하지만, Modern C++의 `= delete`보다 compiler diagnostic이 덜 명확할 수 있습니다.

## 복사와 이동

Modern C++에서는 이동 생성자와 이동 대입 연산자를 통해 "복사할 수는 없지만 소유권은 이동할 수 있는 타입"을 자연스럽게 만들 수 있습니다.

C++98에는 언어 차원의 move semantics가 없습니다.

따라서 이동 전용 자원을 C++98 표준 container에 값으로 저장하는 설계를 그대로 옮기기 어렵습니다. C++98 표준 container는 일반적으로 요소 타입의 복사 가능성을 전제로 하기 때문입니다.

선택지는 다음과 같습니다.

- 객체 복사를 막고 pointer를 container에 저장한 뒤, container 또는 별도 manager를 owner로 정합니다.
- 복사 가능한 식별자나 설정 값만 container에 저장하고 실제 handle은 별도 manager가 보유합니다.
- 자원의 의미상 깊은 복사가 자연스럽다면 값 타입으로 다시 설계합니다.

예를 들어 socket 자체를 값처럼 복사하는 것은 보통 자연스럽지 않습니다. 이 경우 socket 객체는 복사 금지로 만들고, manager가 pointer를 소유하도록 할 수 있습니다.

반면 작은 설정 구조체처럼 독립적인 복사본이 자연스러운 데이터는 깊은 복사가 적합합니다.

핵심은 **Modern 설계를 문법만 바꾸어 그대로 유지하려 하지 않는 것**입니다. 이동이 사라지면 소유 모델 자체를 다시 검토해야 합니다.

## `std::auto_ptr`를 `unique_ptr`처럼 사용하지 않기

C++98에는 `std::auto_ptr`가 있지만 `std::unique_ptr`의 일반적인 대체물로 생각하면 위험합니다.

`auto_ptr`는 복사 연산처럼 보이는 동작에서 소유권이 다른 객체로 이전되는 특수한 의미를 가집니다. 이 때문에 일반적인 값 복사 규칙과 맞지 않으며 표준 container의 요소 타입으로 사용하는 것도 적절하지 않습니다.

따라서 C++98 소유권 설계에서는 `auto_ptr`에 의존하기보다 다음을 우선 고려합니다.

- owner를 하나의 클래스에 고정
- 복사 금지
- 명시적인 생성/파괴 경로
- 필요한 경우 소유권 이전 전용 함수 제공

## `nullptr`와 `0`

C++98에는 `nullptr`가 없습니다. null pointer constant로 보통 `0`을 사용합니다.

```cpp
Handler *handler = 0;
```

그러나 `0`은 정수 literal이기도 합니다.

```cpp
void open(int mode);
void open(Handler *handler);
```

다음 호출은 API 형태에 따라 overload 해석 문제를 만들 수 있습니다.

```cpp
open(0);
```

따라서 C++98에서는 null pointer 표현 자체보다 **정수와 pointer overload가 혼동되지 않도록 API를 설계하는 것**이 중요합니다.

## `enum class` 대응

Modern C++의 `enum class`는 이름 scope와 강한 타입 구분을 제공합니다.

```cpp
enum class State {
    Ready,
    Running
};
```

C++98에서는 비슷한 이름 scope를 만들기 위해 enum을 클래스 안에 둘 수 있습니다.

```cpp
class State {
public:
    enum Type {
        Ready,
        Running
    };
};
```

사용은 다음처럼 할 수 있습니다.

```cpp
State::Type state = State::Ready;
```

하지만 이것이 `enum class`와 완전히 같은 것은 아닙니다. C++98 enum은 정수 변환과 타입 구분이 더 느슨합니다.

특히 파일, socket, 사용자 입력처럼 외부에서 정수가 들어오는 경우에는 범위를 검증해야 합니다.

```cpp
bool isValidState(int value)
{
    return value == State::Ready ||
           value == State::Running;
}
```

## 오류 표현

Modern C++에서는 값과 오류를 하나의 결과 타입으로 표현할 수 있습니다.

```cpp
Result<Value, Error> parse(std::string_view text);
```

이런 타입의 핵심은 문법이 아니라 다음 invariant입니다.

```text
성공 → Value가 유효함
실패 → Error가 유효함
두 상태를 호출자가 구분할 수 있음
```

C++98에서는 output parameter를 사용할 수 있습니다.

```cpp
bool parse(const std::string &text, Value &value, Error &error);
```

이 API를 사용한다면 각 output parameter가 언제 유효한지 계약을 명확히 해야 합니다.

예:

```text
return == true
→ value가 유효함
→ error의 값은 사용하지 않음

return == false
→ error가 유효함
→ value의 값은 사용하지 않음
```

호출자는 반드시 반환값을 먼저 확인합니다.

```cpp
Value value;
Error error;

if (!parse(text, value, error)) {
    handleError(error);
    return;
}

use(value);
```

상태가 더 복잡하거나 함수가 많다면 결과를 별도 클래스로 만드는 편이 안전할 수 있습니다.

```cpp
class ParseResult {
public:
    bool ok() const;
    const Value &value() const;
    const Error &error() const;

private:
    bool ok_;
    Value value_;
    Error error_;
};
```

이 경우 `value()`와 `error()`가 어떤 상태에서 호출 가능한지도 invariant로 정의해야 합니다.

예상하지 못한 실패를 예외로 표현할 수도 있지만, "정상적으로 발생 가능한 parse 실패"와 "프로그램이 계속 처리하기 어려운 예외적 실패"를 구분하는 것이 중요합니다.

## `optional<T>` 대응

`optional<T>`가 해결하는 문제는 "값이 없을 수 있다"는 상태를 타입에 포함하는 것입니다.

C++98에서는 다음처럼 표현할 수 있습니다.

```cpp
bool findUser(const std::string &name, User &user);
```

계약은 다음과 같습니다.

```text
true  → user가 유효함
false → user를 사용하지 않음
```

값이 없는 상태가 객체 자체의 중요한 상태라면 별도 클래스를 만들 수도 있습니다.

```cpp
class OptionalUser {
public:
    OptionalUser();

    bool hasValue() const;
    const User &value() const;

private:
    bool has_value_;
    User value_;
};
```

중요한 점은 sentinel 값 하나를 임의로 정해 "없음"을 표현하면서 실제 값과 충돌하지 않도록 하는 것입니다.

## `variant` 대응

`variant`는 여러 타입 중 정확히 하나의 값이 현재 활성 상태라는 의미를 표현합니다.

C++98에서는 tag를 별도로 저장하는 방식이 흔합니다.

```cpp
class TokenValue {
public:
    enum Type {
        TYPE_INTEGER,
        TYPE_STRING
    };

    Type type() const;

private:
    Type type_;
    int integer_;
    std::string string_;
};
```

여기서 중요한 invariant는 다음과 같습니다.

```text
type_ == TYPE_INTEGER
→ integer_만 논리적으로 유효

type_ == TYPE_STRING
→ string_만 논리적으로 유효
```

실제 `union`을 사용할 수도 있지만, `std::string`처럼 생성자와 destructor가 필요한 타입을 C++98 union에 직접 넣는 설계는 까다롭습니다. 이런 경우 단순한 값 필드, 별도 storage 클래스 또는 다형성을 사용하는 편이 더 명확할 수 있습니다.

## callback

Modern C++ lambda는 capture한 값을 lambda 객체의 상태로 저장할 수 있으며, 값 capture인지 참조 capture인지에 따라 수명 조건이 달라집니다.

C++98에서는 같은 역할을 function object로 구현할 수 있습니다.

```cpp
class Predicate {
public:
    explicit Predicate(const Config &config)
        : config_(config)
    {
    }

    bool operator()(const Item &item) const;

private:
    const Config &config_;
};
```

여기서 `Predicate`가 `Config`를 소유하는 것은 아닙니다. `config_`는 기존 객체를 참조할 뿐입니다.

따라서 반드시 다음 조건이 성립해야 합니다.

```text
Predicate의 마지막 사용 시점
<
Config의 소멸 시점
```

즉 `Predicate`가 `Config`보다 오래 남으면 dangling reference가 됩니다.

수명 관계를 보장하기 어렵다면 값을 복사해서 저장하는 방법도 고려합니다.

```cpp
class Predicate {
public:
    explicit Predicate(const Config &config)
        : config_(config)
    {
    }

private:
    Config config_;
};
```

단, `Config`가 실제 자원을 소유하거나 복사 비용이 크다면 복사 의미가 올바른지 먼저 확인해야 합니다.

상태가 필요 없는 callback은 일반 함수 pointer로 충분할 수 있습니다.

```cpp
bool isValid(const Item &item);

typedef bool (*PredicateFn)(const Item &);
```

function pointer는 일반적으로 lambda의 capture 기능을 대신할 수 없다는 점을 구분해야 합니다.

## virtual 함수와 `override`

C++98에는 `override` keyword가 없습니다.

다음 기반 클래스가 있다고 가정합니다.

```cpp
class Base {
public:
    virtual void run() const;
};
```

파생 클래스에서 `const`를 빠뜨리면:

```cpp
class Derived : public Base {
public:
    virtual void run();
};
```

이 함수는 `Base::run() const`를 override하지 않습니다. 다른 signature의 새 함수입니다.

따라서 C++98에서는 다음을 함께 사용합니다.

- compiler warning을 최대한 활성화
- 기반 클래스와 파생 클래스의 signature를 직접 비교
- 기반 클래스 pointer/reference를 통한 동적 호출 테스트

```cpp
Derived derived;
Base *base = &derived;

base->run();
```

이 테스트는 실제 virtual dispatch가 의도한 파생 함수로 연결되는지 확인하는 데 도움이 됩니다.

## `noexcept`와 `throw()`

C++98에는 `noexcept`가 없습니다.

함수가 예외를 외부로 전달하지 않아야 한다면 가장 중요한 것은 **그 계약을 문서화하고 실제 구현이 이를 지키는 것**입니다.

C++98의 빈 동적 예외 명세를 사용할 수도 있습니다.

```cpp
void cleanup() throw();
```

그러나 이를 Modern C++의 `noexcept`와 완전히 같은 기능으로 이해하면 안 됩니다.

`throw()`가 붙은 함수 밖으로 예외가 빠져나가면 정상적인 예외 전달이 계속되는 것이 아니라 예외 명세 위반 처리로 이어집니다. 또한 Modern compiler가 `noexcept`를 이용하는 방식과 최적화/타입 시스템상의 의미도 다릅니다.

특히 destructor와 정리 함수는 예외를 밖으로 내보내지 않도록 구현하는 것이 중요합니다.

```cpp
Resource::~Resource()
{
    // 실패 가능성이 있는 정리 작업은
    // destructor 밖으로 예외가 전파되지 않도록 처리한다.
}
```

## thread와 종료

C++98 표준 라이브러리 자체에는 `std::thread`나 `std::jthread`가 없습니다.

POSIX 환경이라면 pthread를 직접 사용하거나, 프로젝트 내부에 작은 thread wrapper를 만들어 다음 책임을 한곳에 모을 수 있습니다.

- thread 생성
- 생성 성공 여부 기록
- stop 요청
- wait 중인 thread 깨우기
- join
- thread 관련 자원 정리

종료 순서는 보통 다음 관계를 만족해야 합니다.

```text
thread 생성 성공 수 기록
→ stop flag 설정
→ 대기 중인 thread 깨움
→ 실제로 생성된 thread만 join
→ thread가 더 이상 접근하지 않는 것이 확인된 뒤 공유 상태 소멸
```

중요한 점은 **공유 상태를 먼저 파괴한 뒤 thread를 join하면 안 된다는 것**입니다.

worker가 아직 다음 객체를 참조한다고 가정합니다.

```text
queue
mutex
condition variable
configuration
logger
```

이 객체들을 worker 종료 전에 파괴하면 use-after-free 또는 동기화 객체 접근 오류가 발생할 수 있습니다.

### thread 생성이 일부만 성공한 경우

예를 들어 4개 thread를 만들려 했지만 세 번째 생성이 실패할 수 있습니다.

```text
thread 0 생성 성공
thread 1 생성 성공
thread 2 생성 실패
```

이때 아직 생성되지 않은 thread까지 join하려 하면 안 됩니다.

따라서 생성 성공 수를 별도로 기록합니다.

```cpp
size_t created = 0;

for (size_t i = 0; i < count; ++i) {
    if (!createThread(i)) {
        break;
    }
    ++created;
}

requestStop();

for (size_t i = 0; i < created; ++i) {
    joinThread(i);
}
```

실제 코드는 thread 생성 실패 뒤 이미 생성된 worker가 대기 중이라면 stop flag 설정뿐 아니라 wake-up도 수행해야 합니다.

## filesystem

C++98에는 표준 filesystem 라이브러리가 없습니다.

POSIX 환경에서는 다음과 같은 API를 사용할 수 있습니다.

```text
open
stat
opendir / readdir
mkdir
unlink
rename
```

하지만 이 API를 애플리케이션 전체에서 직접 호출하면 platform 차이와 오류 처리가 넓게 퍼질 수 있습니다.

가능하면 다음과 같은 작은 wrapper 뒤에 숨깁니다.

```cpp
class FileSystem {
public:
    bool exists(const std::string &path) const;
    bool remove(const std::string &path);
    bool rename(const std::string &from,
                const std::string &to);
};
```

이렇게 하면 호출자는 POSIX `errno` 처리나 플랫폼별 API 차이를 직접 알 필요가 줄어듭니다.

## template 요구 사항과 concepts

Modern C++ concepts는 template parameter가 만족해야 할 조건을 interface 가까이에서 표현합니다.

C++98에는 해당 기능이 없으므로 요구 사항을 문서로 명시해야 합니다.

예:

```cpp
template <typename T>
void sortItems(T &container);
```

문서에는 최소한 다음과 같이 적습니다.

```text
T는 begin()과 end()를 제공해야 한다.
iterator는 증가와 역참조를 지원해야 한다.
element type은 비교 가능해야 한다.
```

그리고 실제 지원 타입을 template에 instantiation하는 작은 compile test를 두면 요구 연산이 깨졌는지 확인하는 데 도움이 됩니다.

C++98에서는 제약을 만족하지 않는 타입을 넣었을 때 오류가 function 선언 위치가 아니라 깊은 template instantiation 과정에서 나타날 수 있으므로, 요구 사항 문서가 더욱 중요합니다.

## 적용 순서

1. **Modern 코드가 해결하는 실제 문제를 적습니다.**  
   예: 단독 소유권, nullable 값, 여러 결과 타입, 자동 join.

2. **최신 기능이 제공하는 보장을 분리합니다.**  
   예: `unique_ptr`라면 단독 소유권, 자동 파괴, 복사 금지, 이동 가능성이 핵심입니다.

3. **C++98에서 같은 보장을 제공할 최소 타입과 규칙을 설계합니다.**  
   raw pointer로 바꾸는 것만으로 끝내지 말고 owner, 복사 정책, 실패 시 정리 책임까지 정합니다.

4. **정상 경로뿐 아니라 중간 실패 경로를 검사합니다.**  
   생성 실패, allocation 실패, 등록 실패, 일부 thread 생성 실패, parse 실패 등을 확인합니다.

5. **문법이 아니라 관찰 가능한 결과를 비교합니다.**  
   자원이 정확히 한 번 해제되는지, 잘못된 상태가 노출되지 않는지, 종료 후 worker가 남지 않는지를 확인합니다.

## 예시: `unique_ptr` 기반 설계를 C++98로 옮기기

Modern C++ 코드:

```cpp
class Server {
public:
    void setHandler(std::unique_ptr<Handler> handler);

private:
    std::unique_ptr<Handler> handler_;
};
```

이 코드가 제공하는 핵심 보장은 다음과 같습니다.

```text
Server가 Handler의 단독 owner
Server 소멸 → Handler 자동 파괴
Server 복사 시 ownership 문제가 타입 시스템에 의해 제한됨
```

C++98에서는 다음처럼 직접 표현할 수 있습니다.

```cpp
class Server {
public:
    Server()
        : handler_(0)
    {
    }

    ~Server()
    {
        delete handler_;
    }

    bool setHandler(Handler *handler)
    {
        if (handler == 0) {
            return false;
        }

        delete handler_;
        handler_ = handler;
        return true;
    }

private:
    Server(const Server &);
    Server &operator=(const Server &);

    Handler *handler_;
};
```

이 설계에서는 `Server`가 `handler_`의 유일한 owner라는 규칙을 유지해야 합니다.

또한 `setHandler`의 ownership 계약을 명확히 해야 합니다. 예를 들어 "성공하면 Server가 ownership을 받고, 실패하면 caller가 계속 owner"라고 정의했다면 호출 코드는 다음과 같아야 합니다.

```cpp
Handler *handler = new Handler;

if (!server.setHandler(handler)) {
    delete handler;
    handler = 0;
}
```

이처럼 C++98 porting의 핵심은 최신 문법을 제거하는 것이 아니라 **최신 기능이 자동으로 제공하던 보장을 코드 구조와 명시적인 계약으로 다시 만드는 것**입니다.

## 완료 기준

- Modern 기능을 제거했을 때 사라지는 보장을 설명할 수 있습니다.
- raw pointer가 owner인지 non-owner인지 구분하고, owner라면 최종 해제자를 정합니다.
- 함수 호출 전후의 소유권 이전 시점을 정하고 실패했을 때 누가 해제하는지 설명할 수 있습니다.
- Rule of Zero 설계를 Rule of Three, 깊은 복사 또는 복사 금지 설계로 옮길 수 있습니다.
- 이동 전용 객체를 C++98 container에 그대로 넣기 어려운 이유를 설명할 수 있습니다.
- `optional`, `variant`, 결과 타입을 C++98에서 상태와 invariant를 가진 값으로 표현할 수 있습니다.
- callback function object가 참조나 pointer를 보관할 때 대상 객체의 수명을 검사할 수 있습니다.
- `override`가 없는 환경에서 signature 불일치를 warning과 기반 pointer 호출 테스트로 확인할 수 있습니다.
- `throw()`를 `noexcept`와 동일한 기능으로 오해하지 않습니다.
- thread 생성이 일부만 성공한 경우에도 생성된 thread만 종료하고 join할 수 있습니다.
- 모든 worker가 종료된 뒤 공유 상태가 파괴되도록 종료 순서를 설명할 수 있습니다.
