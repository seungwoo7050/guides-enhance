# 값·수명·복사·이동

## 목표

코드를 읽을 때 단순히 "pointer인가 값인가"만 확인하지 않습니다. 다음을 함께 추적해야 합니다.

- 객체가 언제 만들어집니까?
- 객체의 수명은 언제 끝납니까?
- 누가 그 객체를 소유합니까?
- 함수는 값을 소유하는지, 잠시 빌려 쓰는지, 소유권을 넘겨받는지 어떻게 표현합니까?
- 복사와 이동 뒤 원본과 새 객체는 각각 무엇을 보유합니까?
- 참조, pointer, view가 가리키는 원본은 그 사용 시점까지 살아 있습니까?

C++에서 많은 오류는 "주소가 유효해 보인다"거나 "변수가 아직 존재한다"는 이유로 실제 객체의 수명까지 살아 있다고 잘못 가정할 때 발생합니다.

---

## 객체 수명과 저장 위치

`stack`과 `heap`은 흔히 저장 위치를 설명할 때 쓰는 표현이지만, 그것만으로 객체의 수명을 정확히 설명할 수는 없습니다.

예를 들어 지역 객체는 보통 함수 블록을 벗어날 때 수명이 끝납니다.

```cpp
std::string make_name() {
    std::string name{"worker"};
    return name;
}
```

여기서 지역 변수 `name`의 수명은 `make_name()`이 끝날 때 종료됩니다.

그러나 반환값 자체가 사라지는 것은 아닙니다. 반환 과정에서 호출자 쪽 결과 객체가 만들어지며, compiler는 copy elision을 적용해 불필요한 복사나 이동 자체를 생략할 수 있습니다.

개념적으로는 다음처럼 생각할 수 있습니다.

```text
지역 객체 name
    ↓ return
호출자가 받는 결과 객체
```

실제 구현에서는 compiler가 두 객체를 따로 만들지 않고 처음부터 결과가 놓일 위치에 직접 생성할 수도 있습니다.

반대로 동적 할당된 객체라고 해서 오래 사는 것도 아닙니다.

```cpp
auto owner = std::make_unique<std::string>("worker");
std::string* observer = owner.get();

owner.reset();

// observer에는 이전 주소 값이 남아 있을 수 있지만,
// 그 주소의 std::string 객체 수명은 이미 끝났습니다.
```

`observer` 변수 자체는 여전히 존재하지만, 그것이 가리키던 `std::string` 객체는 `owner.reset()`에서 파괴되었습니다.

따라서 다음 두 사실은 서로 다릅니다.

```text
pointer 변수에 주소 값이 남아 있다
≠
그 주소에 살아 있는 객체가 있다
```

수명이 끝난 객체를 가리키는 pointer나 reference를 **dangling pointer**, **dangling reference**라고 합니다. 이를 통해 객체를 읽거나 수정하면 정의되지 않은 동작(undefined behavior)이 발생할 수 있습니다.

---

## 저장 기간과 객체 수명은 같은 말이 아닙니다

C++에서는 객체가 얼마나 오래 저장 공간을 가지는지를 **storage duration**으로 설명합니다.

학습 단계에서는 다음 정도를 구분해 두면 충분합니다.

- 함수 내부 지역 객체는 보통 block을 벗어날 때 수명이 끝납니다.
- `static` 객체는 프로그램 종료까지 살아 있을 수 있습니다.
- 동적 할당 객체는 소유자가 해제할 때 수명이 끝납니다.
- 임시 객체는 표현식 규칙에 따라 비교적 짧은 수명을 가집니다.

중요한 점은 "어디에 저장되었는가"보다 **그 객체의 수명이 현재 사용 시점까지 이어지는가**입니다.

---

## 초기화와 대입

다음 세 줄은 비슷해 보이지만 서로 다른 연산입니다.

```cpp
Task first{"compile"};   // 새 객체를 초기화합니다.
Task second = first;     // 새 객체를 복사 생성합니다.
second = first;          // 이미 존재하는 객체에 복사 대입합니다.
```

첫 번째 줄에서는 `first`라는 새 객체가 만들어집니다.

두 번째 줄에서도 `second`라는 새 객체가 만들어지며, `first`의 값을 이용해 초기화됩니다. 이때 사용하는 것이 **복사 생성자(copy constructor)** 입니다.

세 번째 줄에서는 `second`가 이미 존재합니다. 기존 값을 버리거나 교체하고 `first`의 값을 받아야 하므로 **복사 대입 연산자(copy assignment operator)** 가 사용됩니다.

이 차이는 자원을 관리하는 타입에서 중요합니다.

예를 들어 대입은 이미 기존 상태를 가지고 있으므로 다음 질문이 생깁니다.

```text
새 값을 준비하다 실패하면
기존 값은 유지되어야 하는가?
부분적으로 바뀌어도 되는가?
```

생성자는 "아직 완성된 기존 객체가 없다"는 점에서 대입과 상황이 다릅니다.

---

## 이동 생성과 이동 대입

이동에도 생성과 대입이 따로 있습니다.

```cpp
Task a{/* ... */};

Task b = std::move(a);   // 이동 생성
Task c{/* ... */};

c = std::move(b);        // 이동 대입
```

- 이동 생성은 새 객체를 만들면서 다른 객체의 자원을 넘겨받습니다.
- 이동 대입은 이미 존재하는 객체가 자신의 기존 자원을 정리한 뒤 다른 객체의 자원을 넘겨받습니다.

따라서 "복사와 이동"뿐 아니라 "생성과 대입"도 함께 구분해야 합니다.

---

## 값, 참조, pointer, view

타입 모양은 객체를 어떻게 사용할 것인지에 대한 단서를 줍니다.

### 값 `T`

```cpp
void consume(Task task);
```

함수가 `Task`를 값으로 받으면 함수 안에 독립적인 `Task` 객체가 생깁니다.

호출자가 lvalue를 넘기면 복사될 수 있고, rvalue를 넘기면 이동될 수 있습니다.

```cpp
Task task{/* ... */};

consume(task);            // 보통 복사
consume(std::move(task)); // 이동 가능
consume(Task{/* ... */}); // 임시 객체에서 이동 또는 생략 가능
```

함수가 값을 저장하거나 소유해야 한다면 값 parameter가 자연스러운 선택이 될 수 있습니다.

### 읽기 참조 `const T&`

```cpp
void inspect(const Task& task);
```

함수는 호출 중 기존 객체를 읽기 위해 빌려 씁니다. 일반적으로 객체를 복사하지 않습니다.

함수는 이 참조가 유효한 호출 범위 안에서만 사용해야 합니다. 이를 함수 밖에 저장하면 원본 객체의 수명을 따로 보장해야 합니다.

### 변경 참조 `T&`

```cpp
void update(Task& task);
```

함수는 호출자가 가진 기존 객체를 직접 수정합니다.

호출자는 함수 호출 이후 자신의 객체가 변경될 수 있음을 알아야 합니다.

### pointer `T*`

```cpp
Task* find(TaskId id);
```

raw pointer만 보고는 다음을 모두 알 수 없습니다.

- `nullptr`이 가능한가?
- 소유권이 있는가?
- 누가 객체를 파괴하는가?
- pointer를 얼마나 오래 저장해도 되는가?

따라서 raw pointer는 문맥, 함수 이름, 문서, 주변 타입을 함께 봐야 합니다.

현대 C++에서는 소유권을 나타낼 때 raw pointer보다 `std::unique_ptr`, `std::shared_ptr` 같은 타입을 사용하는 경우가 많습니다.

### view

`std::string_view`, `std::span`, iterator 등은 원본 데이터를 **소유하지 않고 바라봅니다**.

```cpp
std::string_view title(const Task& task) {
    return task.title();
}
```

이 함수가 안전하려면 반환된 `std::string_view`가 가리키는 문자열이 view를 사용하는 동안 계속 살아 있어야 합니다.

즉 함수가 끝난 뒤에도 view를 사용할 수 있는지는 함수 자체보다 **원본 객체의 수명**에 달려 있습니다.

---

## 비소유 view의 핵심 조건

비소유 타입을 볼 때는 항상 다음 질문을 합니다.

```text
이 view가 가리키는 원본은
view의 마지막 사용 시점까지 살아 있는가?
```

예를 들어 다음 코드는 위험할 수 있습니다.

```cpp
std::string_view make_title() {
    std::string text{"compile"};
    return text;
}
```

`text`는 함수 종료 시 파괴됩니다. 반환된 `std::string_view`는 이미 수명이 끝난 문자열을 가리키므로 dangling view가 됩니다.

반면 원본이 호출자보다 오래 살아 있다면 안전할 수 있습니다.

```cpp
std::string text{"compile"};
std::string_view view{text};

// text가 살아 있는 동안 view 사용
```

다만 원본 객체가 살아 있다고 해서 항상 view가 안전한 것은 아닙니다. 원본 container나 string의 재할당으로 내부 저장 위치가 바뀌면 기존 pointer, iterator, view가 무효화될 수 있습니다.

---

## container 재할당과 무효화

다음 코드를 생각해 봅니다.

```cpp
std::vector<int> values{1, 2, 3};

int* first = &values[0];

values.push_back(4);
```

`push_back()` 과정에서 vector가 더 큰 저장 공간을 새로 할당하고 기존 원소를 이동할 수 있습니다.

그 경우 `first`가 가리키던 기존 저장 공간은 더 이상 유효하지 않습니다.

따라서 container가 수정된 뒤에는 이전에 얻은 다음 값이 계속 유효하다고 가정하면 안 됩니다.

- pointer
- reference
- iterator
- `std::span`
- 내부 데이터를 보는 기타 view

정확한 무효화 조건은 container 종류와 연산에 따라 다르므로, 오래 저장해야 한다면 해당 container의 규칙을 확인해야 합니다.

---

## 복사 의미

값 타입은 일반적으로 복사본을 수정해도 원본이 함께 바뀌지 않는 것이 자연스럽습니다.

```cpp
Task a{1, "compile"};
Task b = a;

b.rename("test");
```

보통 기대하는 상태는 다음과 같습니다.

```text
a.title() == "compile"
b.title() == "test"
```

이런 독립성이 자연스러운 타입을 값 타입처럼 다루기 쉽습니다.

---

## raw owning pointer와 얕은 복사

다음처럼 raw pointer가 실제 자원 소유권을 가진다고 가정해 봅니다.

```cpp
class Buffer {
public:
    ~Buffer() {
        delete[] data_;
    }

private:
    int* data_{nullptr};
};
```

compiler가 자동으로 만든 복사 연산은 pointer 값 자체를 복사합니다.

개념적으로는 다음과 같은 상태가 될 수 있습니다.

```text
Buffer a ──┐
           ├──> 같은 동적 배열
Buffer b ──┘
```

그러면 `a`와 `b`가 파괴될 때 같은 주소에 `delete[]`를 두 번 수행할 수 있습니다.

이런 문제를 피하려면 다음 중 하나가 필요합니다.

- 깊은 복사를 직접 구현합니다.
- 복사를 금지합니다.
- 소유권을 나타내는 RAII 타입을 사용합니다.

직접 메모리 소유를 구현할 필요가 없다면 다음처럼 이미 수명을 관리하는 타입을 우선합니다.

```cpp
std::string
std::vector<T>
std::unique_ptr<T>
std::shared_ptr<T>
```

이런 타입을 멤버로 사용하면 resource 관리 코드를 직접 작성해야 할 필요가 크게 줄어듭니다.

---

## Rule of Zero 관점

가능하다면 destructor, copy constructor, copy assignment, move constructor, move assignment를 직접 구현하지 않아도 되는 타입을 만드는 것이 좋습니다.

예:

```cpp
class Task {
public:
    Task(int id, std::string title)
        : id_{id}, title_{std::move(title)} {}

private:
    int id_;
    std::string title_;
};
```

`std::string`이 자신의 자원을 스스로 관리하므로 `Task`는 별도의 raw resource 관리 코드를 작성하지 않아도 됩니다.

이런 설계를 흔히 **Rule of Zero** 관점이라고 부릅니다.

---

## 이동 의미

이동은 객체를 파괴하는 연산이 아닙니다.

```cpp
std::vector<int> source{1, 2, 3};
std::vector<int> target = std::move(source);
```

`std::move(source)` 자체가 데이터를 이동시키는 것도 아닙니다.

`std::move`는 `source`를 "이동 대상으로 사용할 수 있는 표현식"으로 바꾸는 cast에 가깝고, 실제 자원 이전은 `std::vector`의 이동 생성자가 수행합니다.

개념적으로는 다음처럼 이해할 수 있습니다.

```text
이동 전

source ──> [1, 2, 3]


이동 후의 한 가능한 형태

target ──> [1, 2, 3]
source ──> 유효하지만 값은 특정하지 않음
```

중요한 것은 이동 후 `source`의 정확한 내용이 아니라, **타입이 보장하는 유효한 상태인가**입니다.

---

## moved-from 객체의 상태

표준 library 타입의 moved-from 객체는 일반적으로 **유효하지만 값은 특정하지 않은(valid but unspecified)** 상태로 남습니다.

따라서 다음과 같은 연산은 보통 가능합니다.

```cpp
source.clear();
source = {4, 5, 6};
source.empty();
```

소멸시키는 것도 당연히 가능합니다.

하지만 다음과 같은 가정은 하면 안 됩니다.

```cpp
// 이동 전 원소가 그대로 남아 있을 것이라고 가정
assert(source == std::vector<int>{1, 2, 3});
```

또한 "이동 후에는 반드시 empty다"라고 일반화해서도 안 됩니다.

일부 타입은 이동 후 상태를 더 강하게 보장할 수 있지만, 그런 보장은 해당 타입의 문서에 근거해야 합니다.

학습할 때는 다음 원칙이 안전합니다.

```text
이동 후 원본은
파괴하거나,
새 값을 대입하거나,
문서가 허용하는 연산만 수행한다.
```

---

## 이동 전용 타입

복사 의미가 자연스럽지 않은 자원은 이동 전용 타입으로 표현할 수 있습니다.

예를 들어 하나의 파일 handle을 여러 객체가 독립적으로 "같은 소유권"으로 복사하는 것이 부자연스럽다면 복사를 금지할 수 있습니다.

```cpp
class UniqueFile {
public:
    UniqueFile(const UniqueFile&) = delete;
    UniqueFile& operator=(const UniqueFile&) = delete;

    UniqueFile(UniqueFile&&) noexcept;
    UniqueFile& operator=(UniqueFile&&) noexcept;
};
```

이 타입은 다음을 표현합니다.

```text
복사: 금지
이동: 허용
```

즉 자원 소유권을 하나의 객체에서 다른 객체로 넘길 수는 있지만, 두 객체가 같은 유일 자원을 복사해서 동시에 소유하는 것은 허용하지 않습니다.

`std::unique_ptr<T>`도 대표적인 이동 전용 타입입니다.

---

## `noexcept`와 이동

실제로 예외를 던지지 않는 이동 생성자와 이동 대입 연산자는 `noexcept`로 표시하는 것이 중요할 수 있습니다.

```cpp
UniqueFile(UniqueFile&&) noexcept;
UniqueFile& operator=(UniqueFile&&) noexcept;
```

예를 들어 `std::vector<T>`가 내부 저장 공간을 재할당할 때 기존 원소를 새 공간으로 옮겨야 할 수 있습니다.

이때 `T`의 이동이 예외를 던질 가능성이 있고 복사가 가능하다면, 예외 안전성을 위해 이동 대신 복사를 선택할 수 있습니다.

따라서 실제로 예외가 발생하지 않는 이동 연산이라면 `noexcept`를 명시하는 것이 container가 이동을 사용할 수 있게 하는 데 도움이 됩니다.

단, 예외가 발생할 가능성이 있는데도 단순히 성능을 위해 `noexcept`를 붙이면 안 됩니다. `noexcept` 함수 밖으로 예외가 빠져나가면 프로그램은 `std::terminate()`로 종료됩니다.

---

## 함수 signature로 소유 의도를 드러냅니다

다음 signature들은 서로 다른 의도를 표현합니다.

```cpp
void inspect(const Task& task);                  // 호출 중 읽기
void update(Task& task);                         // 호출 중 변경
void consume(Task task);                         // 독립 값 소유
void install(std::unique_ptr<Task> task);        // 유일 소유권 이전
Task* find(TaskId id);                           // nullable 비소유 결과일 수 있음
```

### `const Task&`

```cpp
void inspect(const Task& task);
```

- 복사하지 않고 읽습니다.
- 호출 중 원본이 살아 있어야 합니다.
- 함수가 참조를 저장한다면 그 사실을 별도로 고려해야 합니다.

### `Task&`

```cpp
void update(Task& task);
```

- 기존 객체를 직접 수정합니다.
- `nullptr` 개념은 없습니다.
- 호출자는 객체 변경을 예상해야 합니다.

### `Task`

```cpp
void consume(Task task);
```

- 함수 내부에 독립적인 값이 생깁니다.
- 함수가 값을 저장하기 쉽습니다.
- 호출자가 lvalue를 넘기면 복사될 수 있습니다.
- rvalue를 넘기면 이동될 수 있습니다.

### `std::unique_ptr<Task>`

```cpp
void install(std::unique_ptr<Task> task);
```

호출자가 다음처럼 호출하면:

```cpp
auto task = std::make_unique<Task>(/* ... */);

install(std::move(task));
```

유일 소유권이 `install()` 쪽으로 이전된다는 의도가 타입에 명확히 드러납니다.

이후 호출자의 `task`는 일반적으로 null 상태가 됩니다.

### `Task*`

```cpp
Task* find(TaskId id);
```

이 형태는 흔히 "없으면 `nullptr`, 있으면 비소유 pointer" 형태로 쓰일 수 있지만, 타입 자체가 소유권을 완전히 설명하지는 않습니다.

따라서 API 문서에서 다음 조건을 알려 주는 것이 좋습니다.

- 반환값이 `nullptr`일 수 있는지
- 반환된 객체를 누가 소유하는지
- pointer가 언제까지 유효한지

---

## 모든 큰 객체를 `const&`로 받을 필요는 없습니다

"큰 객체는 복사가 비싸므로 항상 `const&`로 받아야 한다"라고 단순화하면 수명 설계가 오히려 복잡해질 수 있습니다.

예를 들어 함수가 결국 문자열을 멤버에 저장한다고 가정합니다.

```cpp
class Task {
public:
    void set_title(std::string title) {
        title_ = std::move(title);
    }

private:
    std::string title_;
};
```

호출자가 lvalue를 주면 한 번 복사되어 parameter가 만들어지고, 그 뒤 멤버로 이동됩니다.

```cpp
std::string name{"compile"};
task.set_title(name);
```

호출자가 임시값이나 이동 가능한 값을 주면 불필요한 추가 복사를 줄일 수 있습니다.

```cpp
task.set_title("compile");

std::string name{"compile"};
task.set_title(std::move(name));
```

값으로 받는 방식은 함수 내부에서 독립적인 값을 확보하므로, 외부 객체의 수명에 의존하지 않는다는 장점도 있습니다.

---

## copy elision

C++ compiler는 특정 상황에서 복사나 이동 자체를 생략할 수 있습니다.

```cpp
Task make_task() {
    Task task{/* ... */};
    return task;
}
```

겉으로 보면 `task`에서 반환 객체로 복사 또는 이동이 일어날 것 같지만, compiler는 결과 객체가 놓일 위치에 직접 `task`를 구성할 수 있습니다.

이런 최적화를 **copy elision**이라고 합니다.

특히 지역 변수를 그대로 반환하는 형태에서는 NRVO(Named Return Value Optimization)가 적용될 수 있습니다.

---

## 반환할 지역 변수에 무조건 `std::move`하지 않습니다

다음처럼 작성하는 것이 일반적인 기본 형태입니다.

```cpp
Task make_task() {
    Task task{/* ... */};
    return task;
}
```

반면 다음처럼 쓰는 것은 보통 필요하지 않습니다.

```cpp
Task make_task() {
    Task task{/* ... */};
    return std::move(task);
}
```

`return std::move(task);`는 이름 있는 지역 변수에서 적용될 수 있는 일부 copy elision 기회를 방해할 수 있습니다.

또한 지역 변수를 반환하는 상황에서는 언어 규칙이 이동을 고려할 수 있으므로, "복사를 피하려면 항상 `std::move`해야 한다"라고 생각할 필요가 없습니다.

일반적인 값 반환에서는 먼저 다음을 사용합니다.

```cpp
return task;
```

---

## reference 반환과 수명

reference를 반환하는 함수는 특히 수명을 확인해야 합니다.

다음 코드는 잘못되었습니다.

```cpp
const std::string& make_name() {
    std::string name{"worker"};
    return name;
}
```

`name`은 함수 종료 시 파괴되므로 반환된 reference는 즉시 dangling reference가 됩니다.

반면 이미 더 오래 살아 있는 객체의 일부를 반환하는 것은 가능할 수 있습니다.

```cpp
const std::string& title(const Task& task) {
    return task.title();
}
```

다만 이 경우에도 반환 reference의 유효 기간은 `task`와 실제 내부 문자열의 수명 및 변경 규칙에 의존합니다.

즉 reference 반환은 "복사가 없다"보다 먼저 **누가 원본의 수명을 보장하는가**를 봐야 합니다.

---

## callback과 capture의 수명

lambda가 지역 변수를 reference로 capture한 뒤 lambda 자체가 더 오래 살아남으면 dangling 문제가 생길 수 있습니다.

```cpp
std::function<void()> make_callback() {
    std::string name{"worker"};

    return [&name] {
        std::cout << name << '\n';
    };
}
```

`make_callback()`이 끝나면 `name`은 파괴됩니다. 반환된 callback은 더 이상 유효한 `name`을 참조하지 않습니다.

값 capture를 사용하면 callback 자체가 복사본을 보유할 수 있습니다.

```cpp
std::function<void()> make_callback() {
    std::string name{"worker"};

    return [name] {
        std::cout << name << '\n';
    };
}
```

따라서 callback을 저장하거나 비동기적으로 실행할 때는 capture된 객체의 수명을 반드시 확인해야 합니다.

---

## 자주 놓치는 문제

### 지역 객체의 reference나 pointer를 반환합니다

```text
함수 내부 지역 객체 생성
↓
그 객체의 주소/reference 반환
↓
함수 종료
↓
지역 객체 파괴
↓
반환값 dangling
```

### container 재할당 뒤 기존 iterator나 pointer를 사용합니다

container가 저장 공간을 옮겼다면 이전 주소를 가리키는 값은 더 이상 유효하지 않을 수 있습니다.

### moved-from 객체의 이전 값을 검사합니다

이동 뒤 원본이 정확히 어떤 값을 가지는지는 일반적으로 보장되지 않습니다.

### observer가 owner보다 오래 삽니다

```cpp
auto owner = std::make_unique<Task>();
Task* observer = owner.get();

owner.reset();

// observer dangling
```

비소유 pointer는 소유자보다 오래 살아서는 안 됩니다.

### callback이 reference로 잡은 지역 변수가 먼저 사라집니다

callback 자체의 수명과 capture 대상의 수명을 따로 추적해야 합니다.

### view의 원본은 살아 있지만 내부 저장 공간이 바뀝니다

`std::string_view`, `std::span`, iterator는 원본 객체가 살아 있어도 재할당이나 수정으로 무효화될 수 있습니다.

---

## 코드를 읽을 때의 추적 순서

수명 문제를 찾을 때는 각 객체에 대해 다음 순서로 확인하면 도움이 됩니다.

```text
1. 어디에서 생성되는가?
2. 누가 소유하는가?
3. 누가 비소유 reference/pointer/view를 가지고 있는가?
4. 소유자는 언제 파괴하거나 재할당하는가?
5. observer는 그 이후에도 사용되는가?
6. 복사인가 이동인가?
7. 이동 후 원본에 어떤 가정을 하고 있는가?
```

예:

```cpp
auto owner = std::make_unique<std::string>("worker");
std::string_view view = *owner;

owner.reset();

std::cout << view;
```

추적하면 다음과 같습니다.

```text
owner가 string 소유
↓
view는 string을 비소유 관찰
↓
owner.reset()
↓
string 수명 종료
↓
view dangling
↓
view 사용 오류
```

---

## 완료 기준

이 문서를 학습한 뒤에는 다음을 설명하고 판단할 수 있어야 합니다.

- 객체 수명과 메모리 주소 값의 존재를 구분합니다.
- 지역 객체, 동적 객체, 임시 객체의 수명을 코드에서 추적합니다.
- 초기화, 복사 생성, 이동 생성, 복사 대입, 이동 대입의 차이를 설명합니다.
- 값, 참조, pointer, view의 소유 여부와 수명 조건을 구분합니다.
- raw owning pointer의 얕은 복사가 왜 double delete를 만들 수 있는지 설명합니다.
- 가능하면 resource-owning standard type을 사용해 Rule of Zero 형태로 설계합니다.
- 함수 signature에서 소유·변경·관찰 의도를 드러냅니다.
- 비소유 view가 유효하려면 원본 객체와 내부 저장 공간이 모두 유효해야 함을 설명합니다.
- container 변경 뒤 pointer, reference, iterator, view가 무효화될 수 있음을 확인합니다.
- `std::move` 자체가 이동을 수행하는 것이 아님을 설명합니다.
- moved-from 객체에 대해 "이전 값 유지"나 "반드시 empty"를 가정하지 않습니다.
- 실제로 예외가 발생하지 않는 이동 연산에 `noexcept`가 중요한 이유를 설명합니다.
- 지역 변수를 값으로 반환할 때 무조건 `std::move`하지 않습니다.
- callback이나 저장된 reference가 원본보다 오래 살아남지 않는지 확인합니다.
