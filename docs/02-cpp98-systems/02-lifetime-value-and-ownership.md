# C++98 수명·값·소유권

## 목표

C++98에서는 이동 의미론과 `std::unique_ptr` 같은 현대적인 소유권 타입을 사용할 수 없습니다. 따라서 heap memory, file descriptor 같은 자원을 직접 관리해야 하는 경우 **누가 소유하고, 언제 해제하며, 복사와 대입 때 자원이 어떻게 처리되는지**를 코드 구조와 API 계약으로 명확히 해야 합니다.

이 문서의 핵심 목표는 다음과 같습니다.

- 자원을 소유하는 객체의 복사와 대입을 안전하게 정의합니다.
- 복사 중 실패해도 기존 객체의 값이 사라지지 않게 합니다.
- raw pointer가 소유용인지 관찰용인지 구분합니다.
- 소유권 이전 함수의 성공·실패 계약을 고정합니다.
- 할당된 저장 공간과 실제로 생성된 객체의 수명을 구분합니다.
- 생성자나 컨테이너 연산에서 예외가 발생했을 때 어떤 자원이 자동으로 정리되고 어떤 자원은 직접 정리해야 하는지 이해합니다.

## 값, 수명, 소유권을 구분합니다

세 개념은 서로 관련 있지만 같은 뜻이 아닙니다.

**값(value)** 은 객체가 논리적으로 표현하는 내용입니다. 예를 들어 `TextBuffer("abc")`의 값은 문자열 `"abc"`라고 볼 수 있습니다.

**수명(lifetime)** 은 객체가 생성되어 정상적인 객체로 존재하는 기간입니다. 객체의 수명이 끝난 뒤 그 객체를 가리키던 pointer나 reference를 사용하면 안 됩니다.

**소유권(ownership)** 은 어떤 객체가 특정 자원의 해제 책임을 갖는지를 뜻합니다. 예를 들어 `new[]`로 얻은 memory를 어떤 `TextBuffer`가 소유한다면, 그 `TextBuffer`는 자신의 수명이 끝날 때 해당 memory를 `delete[]`해야 합니다.

이 셋을 분리해서 생각해야 다음과 같은 문제를 구분할 수 있습니다.

- 두 객체가 같은 값을 갖지만 서로 다른 memory를 소유할 수 있습니다.
- 하나의 객체가 다른 객체를 관찰하는 pointer를 가질 수 있지만 그 pointer가 가리키는 객체를 소유하지 않을 수 있습니다.
- 자원은 아직 할당되어 있어도 그 저장 공간 안에 객체가 아직 생성되지 않았을 수 있습니다.

## Rule of Three

C++98에서 클래스가 다음 셋 중 하나를 직접 정의해야 할 이유가 있다면 나머지 둘도 함께 검토합니다.

- 소멸자
- 복사 생성자
- 복사 대입 연산자

이를 흔히 **Rule of Three**라고 부릅니다.

```cpp
class TextBuffer {
public:
    TextBuffer(const char *text);
    TextBuffer(const TextBuffer &other);
    TextBuffer &operator=(const TextBuffer &other);
    ~TextBuffer();

private:
    char *data_;
    std::size_t size_;
};
```

이 규칙이 필요한 대표적인 경우는 클래스가 raw pointer를 통해 heap memory를 직접 소유할 때입니다.

compiler가 자동으로 만드는 복사 생성자와 복사 대입 연산자는 각 멤버를 그대로 복사합니다. raw pointer 멤버의 경우 pointer가 가리키는 내용을 복사하는 것이 아니라 **주소 값만 복사**합니다.

예를 들어 다음 상태를 생각해 봅니다.

```text
a.data_ ----> [ "hello" ]
```

기본 복사 후에는 다음처럼 두 객체가 같은 memory를 가리킬 수 있습니다.

```text
a.data_ ----+
            +----> [ "hello" ]
b.data_ ----+
```

두 객체의 소멸자가 모두 같은 주소에 `delete[]`를 실행하면 같은 자원을 두 번 해제하게 됩니다. 반대로 한 객체만 자원을 해제하도록 임의로 처리하면 다른 객체는 이미 해제된 memory를 가리키게 될 수 있습니다.

따라서 자원을 직접 소유하는 타입은 다음 중 어떤 의미를 가질지 명확히 정해야 합니다.

- 복사하면 독립된 자원을 갖는 **값 타입**
- 복사를 금지하는 타입
- 여러 객체가 자원을 공유하도록 별도의 공유 소유권 규칙을 갖는 타입

단순한 값 타입이라면 보통 깊은 복사를 구현합니다.

## 깊은 복사

복사본이 원본과 독립적인 값이어야 한다면 새 memory를 할당하고 실제 내용까지 복사합니다.

```cpp
TextBuffer::TextBuffer(const TextBuffer &other)
    : data_(new char[other.size_ + 1]),
      size_(other.size_)
{
    std::memcpy(data_, other.data_, size_ + 1);
}
```

복사가 끝난 뒤 상태는 다음과 같아야 합니다.

```text
a.data_ ----> [ "hello" ]

b.data_ ----> [ "hello" ]
```

내용은 같지만 memory는 서로 다릅니다. 따라서 한 객체의 내용 변경이나 소멸이 다른 객체의 자원에 직접 영향을 주지 않습니다.

이 코드는 다음과 같은 클래스 불변조건을 전제로 합니다.

- `size_`는 실제 문자열 길이입니다.
- `data_`는 최소 `size_ + 1` byte의 유효한 배열을 가리킵니다.
- `data_[size_]`에는 종료 문자 `'\0'`이 있습니다.

클래스 내부에서 이런 관계를 항상 유지하면 복사 생성자, 대입 연산자, 접근 함수가 훨씬 단순해집니다.

### 공유는 깊은 복사와 다른 설계입니다

여러 객체가 의도적으로 같은 자원을 공유하려면 단순히 pointer 주소를 복사해서는 안 됩니다.

다음과 같은 추가 규칙이 필요합니다.

- 현재 자원을 몇 객체가 공유하는지 추적
- 마지막 소유자가 사라질 때만 자원 해제
- 복사와 대입 때 공유 수 갱신
- 예외가 발생해도 공유 수와 실제 소유자 수가 일치하도록 유지

즉, 공유 소유는 별도의 참조 카운트 설계가 필요합니다. 단순한 문자열 buffer처럼 독립된 값으로 동작하는 타입이라면 직접 공유 소유를 구현하기보다 깊은 복사가 일반적으로 더 단순합니다.

## 소멸자

소유한 자원은 객체의 수명이 끝날 때 정확히 한 번 해제해야 합니다.

```cpp
TextBuffer::~TextBuffer()
{
    delete[] data_;
}
```

`new[]`로 할당한 배열은 반드시 `delete[]`로 해제해야 합니다.

```cpp
data_ = new char[size_ + 1];

// ...

delete[] data_;
```

`new`와 `delete`, `new[]`와 `delete[]`를 서로 바꾸어 사용하면 안 됩니다.

`delete[] 0`은 아무 동작도 하지 않으므로 `data_`가 null pointer일 수 있는 설계에서도 별도의 null 검사 없이 해제할 수 있습니다.

## 복사 대입과 실패 순서

복사 대입은 이미 유효한 값을 가진 객체를 다른 값으로 바꾸는 연산입니다.

```cpp
a = b;
```

대입을 다음처럼 구현하면 위험합니다.

```cpp
delete[] data_;
data_ = new char[other.size_ + 1];
```

기존 memory를 먼저 해제한 뒤 `new`가 실패하면 `a`의 이전 값은 이미 사라졌습니다. 더 나쁘게는 나머지 멤버와 `data_`의 관계가 깨져 객체가 불완전한 상태가 될 수도 있습니다.

따라서 새 상태를 먼저 준비하고, 준비가 성공한 뒤 현재 상태와 교체하는 순서를 사용하는 것이 안전합니다.

## copy-and-swap

C++98에서 복사 대입을 안전하게 구현하는 대표적인 방법이 **copy-and-swap**입니다.

먼저 자원만 교환하는 멤버 함수를 만듭니다.

```cpp
void TextBuffer::swap(TextBuffer &other)
{
    char *data = data_;
    data_ = other.data_;
    other.data_ = data;

    std::size_t size = size_;
    size_ = other.size_;
    other.size_ = size;
}
```

그 다음 대입 연산자를 다음처럼 구현합니다.

```cpp
TextBuffer &TextBuffer::operator=(const TextBuffer &other)
{
    TextBuffer candidate(other);
    swap(candidate);
    return *this;
}
```

실행 순서를 보면 안전성의 이유가 분명합니다.

1. `candidate`를 `other`의 복사본으로 만듭니다.
2. 복사 중 memory 할당이 실패하면 예외가 발생하고 현재 객체 `*this`는 아직 바뀌지 않았습니다.
3. 복사가 성공하면 `candidate`와 현재 객체의 내부 자원을 교환합니다.
4. 함수가 끝날 때 `candidate`가 소멸하면서 현재 객체가 이전에 소유하던 자원을 해제합니다.

즉, **실패할 수 있는 작업을 먼저 끝낸 다음 상태를 교체**합니다.

이 방식에서는 자기 대입도 별도 분기 없이 처리할 수 있습니다.

```cpp
buffer = buffer;
```

`candidate`가 먼저 정상적인 복사본을 만들고 이후 자원을 교환하므로 자기 대입 때문에 원본을 먼저 지우는 문제가 없습니다.

### `swap`은 실패하지 않도록 구성합니다

copy-and-swap의 장점은 마지막 상태 교체 단계가 실패하지 않는다는 전제에서 가장 분명해집니다.

raw pointer와 정수 크기 값처럼 단순한 멤버를 교환하는 작업은 추가 memory 할당을 하지 않으므로 보통 예외를 발생시키지 않도록 구현할 수 있습니다.

C++98에는 `noexcept` 문법이 없으므로 문법으로 표시할 수는 없지만, `swap` 구현 자체가 추가 할당이나 실패 가능한 작업을 수행하지 않게 설계합니다.

## 소유 pointer와 관찰 pointer

C++98의 raw pointer 타입 자체에는 소유 여부가 나타나지 않습니다.

다음 두 pointer는 타입만 보면 완전히 같습니다.

```cpp
Handler *owner;
Handler *observer;
```

하지만 의미는 다를 수 있습니다.

- owner pointer: 가리키는 객체를 나중에 해제해야 함
- observing pointer: 객체를 사용하기만 하며 해제하면 안 됨

따라서 소유 여부는 클래스 책임, 함수 계약, 생성·해제 위치를 통해 명시해야 합니다.

예를 들어 다음 클래스가 handler들을 직접 소유한다고 정할 수 있습니다.

```cpp
class Router {
private:
    std::map<std::string, Handler *> handlers_;
};
```

이 경우 클래스 계약에는 다음 사실이 포함되어야 합니다.

> `Router`는 `handlers_`에 저장된 각 `Handler *`를 소유하며, 제거하거나 소멸할 때 정확히 한 번 `delete`한다.

반대로 조회 함수가 반환하는 pointer는 소유하지 않는 관찰 pointer일 수 있습니다.

```cpp
const Handler *Router::find(const std::string &command) const;
```

이 반환값의 계약은 예를 들어 다음처럼 정할 수 있습니다.

> 반환 pointer는 `Router`가 살아 있고 해당 handler가 제거되지 않는 동안만 유효하며, caller는 이를 `delete`하지 않는다.

관찰 pointer가 owner보다 오래 살아 있으면 owner가 객체를 해제한 뒤 dangling pointer가 됩니다.

```text
Router owns Handler
      |
      +----> Handler

caller stores observing pointer
      |
      +----> same Handler
```

`Router`가 먼저 Handler를 삭제하면 caller가 저장한 pointer 주소 값 자체는 남아 있어도 더 이상 유효한 객체를 가리키지 않습니다.

## 소유권 이전

C++98에는 이동 의미론이 없으므로 raw pointer를 함수 인자로 전달하면서 소유권을 넘기는 API는 특히 주의해야 합니다.

예를 들어 다음 함수가 있다고 가정합니다.

```cpp
void Router::add(const std::string &name, Handler *handler);
```

이 선언만으로는 다음을 알 수 없습니다.

- 함수 호출 직후에도 caller가 `handler`를 소유하는가
- 성공하면 `Router`가 소유권을 가져가는가
- 삽입 중 예외가 발생하면 누가 `handler`를 해제하는가

반드시 하나의 계약을 정해야 합니다.

예를 들어 다음처럼 정할 수 있습니다.

> `add`가 성공하면 `Router`가 `handler`의 소유권을 갖는다. `add`가 실패해 예외를 던지면 소유권은 caller에게 남는다.

이 계약에서는 함수가 성공하기 전까지 caller가 소유자입니다.

반대로 다음 계약도 가능하지만 구현 방식은 달라져야 합니다.

> `add`가 호출되는 순간 `Router`가 소유권을 넘겨받으며, 이후 성공 여부와 관계없이 `Router` 쪽 코드가 `handler`를 정리한다.

어떤 방식을 선택하든 모든 실행 경로에서 정확히 하나의 소유자만 존재해야 합니다.

특히 다음 두 문제가 없어야 합니다.

- caller와 callee가 모두 `delete`하여 이중 해제
- 실패 경로에서 어느 쪽도 `delete`하지 않아 memory leak

### 소유권 이전 시점은 상태 변경 순서와 연결됩니다

예를 들어 `std::map`에 pointer를 삽입하는 과정에서는 node allocation 등이 실패해 예외가 발생할 수 있습니다.

따라서 "map 삽입이 성공한 순간부터 Router가 소유한다"는 계약이라면, 삽입 성공 전에는 caller가 여전히 소유자라는 사실을 코드 전체가 따라야 합니다.

소유권 계약은 단순한 주석이 아니라 예외가 발생하는 정확한 지점까지 포함한 실행 규칙입니다.

## 생성과 등록을 한 곳에서 처리하기

외부에서 raw owning pointer를 만들어 전달하는 API보다, 객체 생성과 등록을 한 함수 안에 두면 소유권 전환 지점을 줄일 수 있습니다.

개념적으로 다음처럼 구성할 수 있습니다.

```cpp
void Router::addDefaultHandler(const std::string &name)
{
    Handler *handler = new DefaultHandler;

    try {
        handlers_.insert(std::make_pair(name, handler));
    } catch (...) {
        delete handler;
        throw;
    }
}
```

위 예제에서는 다음 순서가 명확합니다.

1. `new`가 성공하면 지역 변수 `handler`가 자원을 임시로 관리합니다.
2. map 삽입이 실패하면 `catch`에서 직접 해제합니다.
3. 삽입이 성공한 뒤에는 `Router`의 container가 해당 pointer의 소유 상태를 기록합니다.

실제 구현에서는 중복 key 처리처럼 `insert`가 예외 없이 실패를 반환하는 경우도 확인해야 합니다. 즉, "예외가 없었다"와 "실제로 삽입되었다"를 같은 의미로 취급하면 안 됩니다.

예를 들어 `std::map::insert`의 반환값을 검사해야 할 수 있습니다.

```cpp
std::pair<
    std::map<std::string, Handler *>::iterator,
    bool
> result = handlers_.insert(std::make_pair(name, handler));

if (!result.second) {
    delete handler;
    throw DuplicateHandler(name);
}
```

이처럼 소유권이 실제로 container로 넘어간 시점을 하나로 고정하면 실패 경로를 추적하기 쉬워집니다.

## 배열과 객체 수명

다음 표현은 memory만 확보하는 것이 아닙니다.

```cpp
new T[n]
```

`new T[n]`은 다음 두 작업을 함께 수행합니다.

1. `n`개의 `T` 객체를 둘 저장 공간을 확보
2. 그 공간에 `n`개의 `T` 객체를 생성

따라서 정상적으로 반환되었다면 해당 배열 범위에는 실제 `T` 객체들이 존재합니다.

반면 `std::allocator<T>`를 사용하면 **raw storage 확보**와 **객체 생성**을 분리할 수 있습니다.

```cpp
std::allocator<T> allocator;

T *memory = allocator.allocate(capacity);
allocator.construct(memory + index, value);
```

`allocate(capacity)` 직후에는 `capacity`개의 `T`를 둘 수 있는 저장 공간은 있지만, 그 공간 전체에 `T` 객체가 이미 생성된 것은 아닙니다.

예를 들어 `capacity == 10`, `size == 3`이라면 다음처럼 생각할 수 있습니다.

```text
memory
  |
  v
+----+----+----+----+----+----+----+----+----+----+
| T  | T  | T  |raw |raw |raw |raw |raw |raw |raw |
+----+----+----+----+----+----+----+----+----+----+
  0    1    2    3    4    5    6    7    8    9
```

앞의 세 위치에만 `construct`를 호출했다면 객체 수명도 세 개만 시작된 상태입니다.

따라서 해제할 때도 실제로 생성한 객체만 `destroy()`해야 합니다.

```cpp
for (std::size_t i = 0; i < size; ++i)
    allocator.destroy(memory + i);

allocator.deallocate(memory, capacity);
```

아직 객체가 생성되지 않은 위치에 `destroy()`를 호출하면 존재하지 않는 객체의 소멸자를 호출하려는 잘못된 동작이 됩니다.

## `allocate`, `construct`, `destroy`, `deallocate`

allocator를 사용할 때 네 작업을 구분합니다.

```text
allocate   : 객체를 둘 raw storage 확보
construct  : 특정 위치에서 객체의 수명 시작
destroy    : 특정 객체의 수명 종료
deallocate : raw storage 반환
```

대응 관계는 다음과 같습니다.

```text
allocate(capacity)
    |
    +-- construct(0)
    +-- construct(1)
    +-- construct(2)
    |
    +-- destroy(2)
    +-- destroy(1)
    +-- destroy(0)
    |
deallocate(capacity)
```

객체를 먼저 파괴한 뒤 storage를 반환해야 합니다.

`deallocate`만 호출해서는 생성된 객체의 소멸자가 자동으로 호출되지 않습니다.

## 부분 생성과 예외

여러 객체를 순서대로 `construct`하는 동안 중간 객체의 생성자가 예외를 던질 수 있습니다.

예를 들어 다섯 개를 만들려 했지만 세 번째 생성에서 실패했다면 앞에서 성공한 객체들만 실제로 존재합니다.

```text
0: 생성 성공
1: 생성 성공
2: 생성 중 실패
3: 생성 안 됨
4: 생성 안 됨
```

이 경우 정리 대상은 이미 생성이 끝난 `0`, `1`뿐입니다.

개념적으로 다음과 같이 작성할 수 있습니다.

```cpp
std::size_t constructed = 0;

try {
    for (; constructed < count; ++constructed)
        allocator.construct(memory + constructed, value);
} catch (...) {
    while (constructed > 0) {
        --constructed;
        allocator.destroy(memory + constructed);
    }

    allocator.deallocate(memory, capacity);
    throw;
}
```

핵심은 **할당된 capacity**와 **실제로 생성 완료된 객체 수**를 별도로 추적하는 것입니다.

## 생성자 실패

객체 생성 과정에서 예외가 발생하면 "완성된 객체가 존재한 적이 있는가"를 구분해야 합니다.

다음 생성자를 봅니다.

```cpp
TextBuffer::TextBuffer(const char *text)
    : data_(0),
      size_(length(text))
{
    data_ = new char[size_ + 1];
    copy_text(data_, text, size_);
}
```

생성자 본문을 끝까지 실행하기 전에 예외가 발생하면 `TextBuffer` 객체 자체의 생성은 완료되지 않은 것입니다.

이 경우 **`TextBuffer::~TextBuffer()`는 호출되지 않습니다.**

따라서 생성자 본문에서 직접 획득한 raw resource는 이후 코드가 예외를 던질 수 있다면 자동으로 정리되지 않습니다.

예를 들어 `new`가 성공한 뒤 `copy_text`가 예외를 던질 수 있다면 다음 순서에서는 memory leak 가능성이 있습니다.

```cpp
data_ = new char[size_ + 1];
copy_text(data_, text, size_); // 여기서 예외가 발생할 수 있다면?
```

`TextBuffer`의 소멸자는 호출되지 않으므로 `data_`가 자동으로 해제되지 않습니다.

### 생성자 실패 시 자동으로 정리되는 것

완성된 객체의 소멸자는 호출되지 않지만, 생성 과정에서 **이미 정상적으로 생성이 완료된 base class와 class-type member 객체**는 언어 규칙에 따라 파괴됩니다.

예를 들어 다음과 같은 경우를 생각해 봅니다.

```cpp
class Owner {
public:
    Owner();

private:
    Resource first_;
    Resource second_;
};
```

`first_` 생성은 성공했지만 `second_` 생성 중 예외가 발생하면 `first_`는 자동으로 파괴됩니다.

그러나 raw pointer는 class-type resource manager가 아닙니다.

```cpp
char *data_;
```

pointer 멤버 자체가 파괴되어도 pointer가 가리키는 heap memory에 `delete[]`가 자동으로 호출되지는 않습니다.

따라서 생성자 예외 안전성에서는 **멤버 객체가 직접 관리하는 자원**과 **생성자 본문에서 직접 획득한 raw resource**를 구분해야 합니다.

## 생성자에서 자원 획득 순서를 단순하게 합니다

생성자에서는 가능한 한 다음 원칙을 따릅니다.

- 실패 가능한 작업의 수를 줄입니다.
- 자원을 얻은 뒤 또 다른 실패 가능한 작업을 길게 이어서 수행하지 않습니다.
- 한 단계가 실패했을 때 이미 얻은 자원을 누가 정리하는지 명확하게 합니다.
- 완성되지 않은 객체의 소멸자가 호출될 것이라고 기대하지 않습니다.

예를 들어 문자열 길이 계산이 예외를 던지지 않고, `new` 뒤의 복사 함수도 예외를 던지지 않는다는 계약이 명확하다면 다음 구조는 단순합니다.

```cpp
TextBuffer::TextBuffer(const char *text)
    : data_(0),
      size_(length(text))
{
    data_ = new char[size_ + 1];
    copy_text(data_, text, size_);
}
```

하지만 `copy_text`가 예외를 던질 수 있다면 그 예외 경로의 memory 정리가 추가로 필요합니다.

## file descriptor도 소유 자원입니다

소유권 문제는 heap memory에만 적용되지 않습니다.

예를 들어 POSIX file descriptor를 직접 소유하는 클래스가 있다면 소멸 시 `close`해야 합니다.

```cpp
class File {
public:
    explicit File(int fd);
    ~File();

private:
    int fd_;
};
```

여기에서도 복사 의미를 정해야 합니다.

단순히 정수 `fd_`를 복사하면 두 객체가 같은 descriptor 번호를 소유한다고 생각하게 되어 둘 다 `close`할 수 있습니다.

따라서 다음 중 하나를 명확히 선택해야 합니다.

- 복사를 금지
- 복사 시 `dup` 같은 별도 시스템 기능으로 독립 descriptor를 생성
- 한 객체만 소유하고 다른 쪽은 관찰만 하도록 API를 설계

즉, Rule of Three의 핵심은 pointer라는 문법 자체가 아니라 **객체가 외부 자원의 수명을 책임지는가**에 있습니다.

## 복사를 금지하는 C++98 방식

어떤 자원은 값처럼 복사하는 것이 적절하지 않을 수 있습니다.

C++11의 `= delete`를 사용할 수 없으므로 C++98에서는 복사 생성자와 복사 대입 연산자를 private으로 선언하고 정의하지 않는 방식을 사용할 수 있습니다.

```cpp
class File {
public:
    explicit File(int fd);
    ~File();

private:
    File(const File &);
    File &operator=(const File &);

private:
    int fd_;
};
```

외부 코드가 복사를 시도하면 접근할 수 없는 함수라 compile 오류가 발생합니다.

이 방식은 "복사하면 어떤 의미가 되는가"를 억지로 정하기보다 복사 자체가 타입의 의미에 맞지 않을 때 사용할 수 있습니다.

## 컨테이너와 값 타입

`std::map<Key, Value>`처럼 객체를 값으로 저장하는 container에서는 `Value`의 복사 동작이 올바르게 정의되어 있어야 합니다.

```cpp
std::map<std::string, TextBuffer> values;
```

container 구현은 삽입, 내부 node 구성, 대입 등에서 `Value`의 복사 생성자나 대입 연산자를 사용할 수 있습니다.

따라서 프로그램은 "정확히 몇 번 복사될 것"이라고 가정하면 안 됩니다.

중요한 것은 복사가 몇 번 이루어지더라도 다음 조건이 유지되는 것입니다.

- 각 복사본의 값이 올바름
- 각 owning object가 자신이 책임질 자원을 정확히 하나의 규칙으로 관리
- 하나의 객체 파괴가 다른 독립 복사본의 자원을 무효화하지 않음
- 복사 실패 시 기존 객체가 불완전한 상태가 되지 않음

## 컨테이너 삽입 실패와 상태

container 삽입에는 여러 실패 지점이 있을 수 있습니다.

예를 들어 다음 과정이 필요할 수 있습니다.

- node용 memory 할당
- key 복사
- value 복사

이 중 하나가 예외를 던질 수 있습니다.

따라서 자신의 객체 상태를 먼저 바꾼 뒤 container 삽입을 시도하면 삽입 실패 후 두 상태가 어긋날 수 있습니다.

예를 들어 다음과 같은 논리가 있다고 가정합니다.

```text
1. size_ 증가
2. map에 값 삽입
```

2번이 실패하면 실제 원소 수는 늘지 않았는데 `size_`만 증가한 상태가 됩니다.

가능하면 실패할 수 있는 연산을 먼저 성공시킨 뒤, 실패하지 않는 내부 상태 변경을 마지막에 수행합니다.

## container에 값으로 저장한 객체와 외부 주소

다음 두 경우를 구분해야 합니다.

```cpp
TextBuffer buffer("abc");
values.insert(std::make_pair("key", buffer));
```

`values`가 `TextBuffer`를 **값으로 저장**한다면 container 내부에는 `buffer`의 복사본이 들어갑니다.

따라서 다음 두 객체는 같은 값일 수 있지만 서로 다른 객체입니다.

```text
외부 buffer
container 내부 TextBuffer
```

외부 `buffer`의 주소를 저장해 두었다고 해서 그것이 container 내부 복사본의 주소가 되는 것은 아닙니다.

반면 container 내부 원소 자체에 대한 pointer나 reference의 유효성은 해당 container 종류와 어떤 연산을 수행했는지에 따라 판단해야 합니다. 모든 container가 같은 무효화 규칙을 갖는 것은 아닙니다.

즉, "container에 넣었으니 기존 pointer가 자동으로 내부 원소를 가리킨다"거나 "container 연산 뒤에도 모든 pointer가 항상 유효하다"는 식으로 일반화하면 안 됩니다.

## 소유권 불변조건

자원을 직접 관리하는 클래스는 정상 상태에서 항상 만족해야 하는 조건을 정하면 구현을 검토하기 쉬워집니다.

예를 들어 `TextBuffer`라면 다음처럼 정의할 수 있습니다.

```text
- data_는 TextBuffer가 단독 소유한다.
- data_는 size_ + 1 이상의 char 배열을 가리킨다.
- data_[size_] == '\0'이다.
- 소멸자는 data_를 정확히 한 번 delete[]한다.
```

`Router`라면 다음처럼 정의할 수 있습니다.

```text
- handlers_에 저장된 각 pointer는 Router가 소유한다.
- 같은 Handler 객체를 두 key가 동시에 소유하지 않는다.
- 제거된 handler는 정확히 한 번 delete된다.
- find가 반환하는 pointer는 소유권을 넘기지 않는다.
```

예외가 발생하는 모든 지점에서 이 불변조건이 유지되는지 확인하면 memory leak, 이중 해제, dangling pointer 문제를 체계적으로 찾을 수 있습니다.

## 자주 놓치는 문제

- raw owning pointer를 가진 타입에서 compiler 기본 복사를 그대로 사용합니다.
- 복사 생성자는 만들었지만 복사 대입이나 소멸자의 의미를 함께 검토하지 않습니다.
- 대입에서 현재 자원을 먼저 삭제한 뒤 새 자원을 할당합니다.
- copy-and-swap의 `swap` 안에서 다시 실패 가능한 memory 할당을 수행합니다.
- owning pointer와 observing pointer를 같은 규칙으로 다룹니다.
- 관찰 pointer가 owner보다 오래 살아도 된다고 생각합니다.
- 소유권 이전 함수가 성공했을 때와 실패했을 때 누가 자원을 해제하는지 정하지 않습니다.
- container 삽입에서 예외가 없었다는 사실만 보고 실제 삽입 성공 여부를 확인하지 않습니다.
- `new T[n]`과 `allocator.allocate(n)`이 모두 `n`개의 객체를 생성한다고 생각합니다.
- allocator로 확보한 capacity 전체에 객체가 존재한다고 가정합니다.
- 실제로 `construct`가 성공한 객체 수를 기록하지 않습니다.
- 생성자 본문에서 예외가 발생하면 완성되지 않은 객체의 소멸자가 호출될 것이라고 생각합니다.
- raw pointer 멤버가 가리키는 자원도 멤버 정리 과정에서 자동으로 해제된다고 생각합니다.
- file descriptor 같은 정수형 자원은 복사해도 소유권 문제가 없다고 생각합니다.
- container에 값을 복사해 넣은 뒤 외부 객체의 pointer가 container 내부 객체를 가리킨다고 생각합니다.
- container 종류별 pointer·reference 무효화 규칙을 확인하지 않고 주소가 계속 유효하다고 가정합니다.

## 완료 기준

다음 항목을 설명하고 코드에서 적용할 수 있으면 이 범위의 목표를 달성한 것입니다.

- 값, 객체 수명, 자원 소유권의 차이를 설명합니다.
- Rule of Three가 필요한 이유를 설명하고 소멸자·복사 생성자·복사 대입을 함께 검토합니다.
- 독립 값 타입의 깊은 복사와 공유 소유를 구분합니다.
- copy-and-swap으로 복사 실패 뒤 기존 값을 보존합니다.
- raw pointer마다 소유자인지 관찰자인지와 해제 위치를 지정합니다.
- 소유권 이전 API의 성공·실패 경로에서 누가 자원을 소유하는지 설명합니다.
- `new T[n]`으로 생성된 객체 배열과 allocator로 얻은 raw storage를 구분합니다.
- allocator에서 `capacity`와 실제로 생성된 객체 수를 따로 관리합니다.
- 부분 생성 실패 시 이미 생성 완료된 객체만 파괴합니다.
- 생성자 실패 시 완성된 객체의 소멸자는 호출되지 않지만 이미 생성된 base와 class-type member는 정리된다는 점을 설명합니다.
- heap memory뿐 아니라 file descriptor 같은 외부 자원에도 동일한 소유권 원칙을 적용합니다.
- container 연산 중 복사와 할당이 실패할 수 있음을 고려해 자신의 상태 변경 순서를 정합니다.
