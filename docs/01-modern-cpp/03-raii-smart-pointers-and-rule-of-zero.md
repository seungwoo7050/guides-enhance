# RAII·smart pointer·Rule of Zero

## 목표

파일, socket, mutex, 동적 메모리처럼 반드시 정리해야 하는 자원을 객체 수명에 연결합니다. 정상적인 `return`뿐 아니라 중간 실패와 예외가 발생했을 때도 같은 정리 규칙이 적용되도록 설계합니다.

이 문서에서 중요한 질문은 다음과 같습니다.

- 이 자원을 현재 누가 소유합니까?
- 소유권은 언제 다른 객체로 이동합니까?
- 자원은 정확히 언제 해제됩니까?
- 예외가 발생해도 해제가 보장됩니까?
- 복사와 이동을 허용해도 됩니까?
- 자원 정리 중 실패를 caller에게 알려야 합니까?

RAII의 목적은 단순히 `delete`를 줄이는 것이 아니라, **자원의 유효 기간을 객체 수명 규칙으로 표현해 모든 제어 흐름에서 정리를 자동화하는 것**입니다.

---

## RAII가 해결하는 문제

직접 자원을 관리하면 함수의 모든 종료 경로에서 정리 코드를 기억해야 합니다.

```cpp
FILE* file = std::fopen(path, "rb");
if (file == nullptr)
    return error;

char* buffer = new char[size];

// 이후의 모든 return과 예외 경로에서
// file과 buffer를 직접 정리해야 합니다.
```

예를 들어 중간에 다음과 같은 코드가 추가되면:

```cpp
if (!valid_header(file))
    return invalid_format;
```

여기서 `buffer`와 `file`을 모두 해제해야 합니다.

또 다른 예외가 발생하는 연산이 들어가면 정리 경로는 더 복잡해집니다.

```text
자원 A 획득
↓
자원 B 획득
↓
작업 1
↓
작업 2
↓
중간 return 또는 exception
↓
A와 B를 어떤 순서로 정리할지 직접 관리
```

이 방식은 코드가 커질수록 누락되기 쉽습니다.

---

## RAII의 기본 구조

RAII(Resource Acquisition Is Initialization)는 자원 획득과 객체 수명을 연결합니다.

일반적인 형태는 다음과 같습니다.

```text
객체 생성
↓
자원 획득
↓
객체 사용
↓
scope 종료
↓
소멸자 실행
↓
자원 해제
```

예를 들어 다음 두 타입은 내부 자원을 스스로 관리합니다.

```cpp
std::ifstream input{path, std::ios::binary};
std::vector<char> buffer(size);
```

- `std::ifstream`은 파일 handle과 관련 상태를 관리합니다.
- `std::vector<char>`는 동적 메모리를 관리합니다.

함수가 정상적으로 끝나거나 중간에 `return`하거나 예외 때문에 stack unwinding이 일어나더라도, 이미 정상적으로 생성된 지역 객체의 소멸자는 scope를 벗어날 때 호출됩니다.

```cpp
void load(const std::string& path) {
    std::ifstream input{path, std::ios::binary};
    std::vector<char> buffer(4096);

    if (!input)
        return;

    // 이후 예외가 발생하더라도
    // input과 buffer는 정상적으로 생성되었다면 정리됩니다.
}
```

핵심은 정리 코드를 모든 분기마다 반복하지 않아도 된다는 점입니다.

---

## RAII는 메모리만 위한 기법이 아닙니다

RAII는 `new`와 `delete`를 관리하는 기법으로만 이해하면 범위가 너무 좁습니다.

다음은 모두 자원입니다.

```text
동적 메모리
파일 descriptor
FILE*
socket
mutex lock
thread ownership
database transaction handle
graphics resource
OS handle
temporary state
```

공통점은 다음과 같습니다.

> 획득한 뒤 반드시 어떤 정리 또는 해제 동작이 필요합니다.

이 자원을 소유하는 객체의 소멸자가 정리 책임을 맡으면 예외와 조기 반환에도 같은 정리 규칙을 적용할 수 있습니다.

---

## 스코프와 역순 파괴

지역 객체는 일반적으로 생성의 역순으로 파괴됩니다.

```cpp
void work() {
    Resource first;
    Resource second;
    Resource third;
}
```

개념적인 파괴 순서는 다음과 같습니다.

```text
third
second
first
```

이 규칙은 여러 자원이 서로 의존할 때 중요합니다.

예를 들어 두 번째 자원이 첫 번째 자원을 기반으로 생성되었다면, 역순 파괴는 보통 자연스럽게 의존 관계를 정리합니다.

---

## 소멸자는 정리의 마지막 안전망입니다

RAII 객체의 소멸자는 객체가 scope에서 벗어날 때 자원을 정리합니다.

예를 들어:

```cpp
class FileHandle {
public:
    ~FileHandle() noexcept {
        if (file_ != nullptr)
            std::fclose(file_);
    }

private:
    std::FILE* file_{nullptr};
};
```

이 소멸자는 객체가 어떤 경로로 파괴되더라도 남아 있는 `FILE*`를 정리합니다.

그러나 여기에는 중요한 제한이 있습니다.

**소멸자는 일반적으로 실패를 caller에게 보고하기 좋은 장소가 아닙니다.**

---

## 소멸자에서 예외를 던지지 않는 것이 기본입니다

다음 상황을 생각합니다.

```text
작업 중 exception A 발생
↓
stack unwinding 시작
↓
지역 객체 소멸자 실행
↓
소멸자에서 exception B 발생
```

이미 다른 예외를 처리하기 위해 stack unwinding 중인데 소멸자에서 또 예외가 밖으로 나가면 프로그램은 `std::terminate()`로 종료될 수 있습니다.

따라서 자원 정리 함수가 실패할 수 있더라도 소멸자는 일반적으로 예외를 밖으로 던지지 않도록 설계합니다.

```cpp
class OutputFile {
public:
    ~OutputFile() noexcept {
        // 남은 자원을 최선의 방식으로 정리
        // 예외는 밖으로 내보내지 않음
    }
};
```

---

## 반드시 보고해야 하는 정리 오류는 명시적으로 처리합니다

일부 자원은 단순 해제보다 "정리 결과가 성공했는가"가 중요합니다.

예를 들어 output stream을 flush하거나 파일을 close할 때 I/O 오류가 발생할 수 있습니다.

그 오류를 caller가 반드시 알아야 한다면 소멸자에만 맡기지 않고 별도 연산을 제공합니다.

```cpp
class OutputFile {
public:
    void finish();       // flush/close 실패를 caller에게 보고
    ~OutputFile() noexcept; // 남은 자원을 최종 정리
};
```

사용 코드는 다음처럼 작성할 수 있습니다.

```cpp
OutputFile out{/* ... */};

// write...

out.finish(); // 오류를 처리할 수 있는 시점에서 명시적으로 수행
```

소멸자는 여전히 `finish()`가 호출되지 않았거나 중간 실패가 발생한 경우를 위한 마지막 정리 수단으로 남습니다.

즉 역할을 나누면 다음과 같습니다.

```text
명시적 finish()/close()
    → 오류를 caller에게 보고해야 하는 정리

소멸자
    → 남은 자원을 예외 없이 최종 정리
```

---

## `std::unique_ptr`: 유일 소유권

한 객체만 동적 객체를 소유해야 한다면 `std::unique_ptr`을 우선 고려합니다.

```cpp
auto task = std::make_unique<Task>(id, name);
```

개념적으로는 다음과 같습니다.

```text
task
  │
  └── 유일 소유 ──> Task
```

`task`가 파괴되면 소유한 `Task`도 자동으로 파괴됩니다.

---

## `unique_ptr`은 복사할 수 없습니다

유일 소유권은 두 객체가 동시에 같은 대상을 소유하면 안 된다는 의미이므로 복사는 금지됩니다.

```cpp
auto first = std::make_unique<Task>();

// auto second = first; // 오류: 복사 불가
```

소유권을 다른 객체로 넘기려면 이동해야 합니다.

```cpp
auto first = std::make_unique<Task>();

auto second = std::move(first);
```

이후 개념적인 상태는 다음과 같습니다.

```text
first  ──> null
second ──> Task
```

즉 `Task`의 소유권이 `first`에서 `second`로 이동합니다.

---

## container에 `unique_ptr`을 넣을 때

다음 코드는 `task`의 소유권을 container로 넘깁니다.

```cpp
auto task = std::make_unique<Task>(id, name);

queue.push_back(std::move(task));
```

이후 `task`는 더 이상 해당 객체를 소유하지 않습니다.

```cpp
if (!task) {
    // 소유권이 이동되었음을 확인할 수 있습니다.
}
```

container가 파괴되면 그 안의 `unique_ptr`들이 파괴되고, 각 `unique_ptr`이 소유한 객체도 함께 파괴됩니다.

---

## `get()`은 소유권을 넘기지 않습니다

`unique_ptr::get()`은 내부 raw pointer를 얻지만 소유권은 그대로 `unique_ptr`에 남아 있습니다.

```cpp
auto owner = std::make_unique<Task>();

Task* observer = owner.get();
```

상태는 다음과 같습니다.

```text
owner ── 소유 ──> Task
observer ─ 관찰 ─> Task
```

`observer`는 `Task`를 삭제해서는 안 됩니다.

```cpp
delete observer; // 잘못된 소유권 처리
```

그렇게 하면 `owner`는 이미 파괴된 객체를 여전히 소유한다고 생각하게 되고, 나중에 다시 삭제하려 할 수 있습니다.

---

## raw pointer API에 `get()`을 사용할 때의 조건

기존 C API나 raw pointer를 받는 함수에 잠시 pointer를 넘겨야 할 수 있습니다.

```cpp
legacy_inspect(owner.get());
```

이때 반드시 확인해야 할 것은 함수가 pointer를 어떻게 사용하는가입니다.

### 단순 관찰

```cpp
void inspect(const Task* task);
```

호출 중만 사용하고 저장하지 않는다면 `get()` 전달이 자연스러울 수 있습니다.

### pointer를 저장함

```cpp
register_task(owner.get());
```

함수가 pointer를 호출 이후에도 저장한다면, `owner`가 얼마나 오래 살아야 하는지 별도로 보장해야 합니다.

### pointer를 삭제함

함수가 전달받은 pointer를 `delete`하는 API라면 단순히 `get()`을 넘기면 안 됩니다. 이 경우 소유권 이전 규칙을 정확히 확인해야 합니다.

즉 `get()`은 다음 의미입니다.

```text
"주소를 보여 준다"
≠
"소유권을 넘긴다"
```

---

## `release()`와 `reset()`은 의미가 다릅니다

`unique_ptr`의 소유권 조작에는 서로 다른 연산이 있습니다.

### `reset()`

```cpp
owner.reset();
```

현재 소유한 객체가 있다면 그것을 파괴하고 `owner`를 빈 상태로 만듭니다.

### `release()`

```cpp
Task* raw = owner.release();
```

소유권을 포기하지만 객체를 파괴하지 않습니다.

이후 raw pointer를 직접 관리할 책임이 생깁니다.

```cpp
delete raw;
```

따라서 `release()`는 소유권을 다른 API에 넘기는 등 명확한 이유가 있을 때만 사용해야 합니다.

---

## C API 자원과 custom deleter

`std::unique_ptr`은 반드시 `new`로 만든 객체만 관리하는 타입이 아닙니다.

해제 방식이 `delete`가 아닌 자원에도 custom deleter를 지정할 수 있습니다.

예를 들어 `std::FILE*`은 `std::fclose()`로 닫아야 합니다.

```cpp
struct FileCloser {
    void operator()(std::FILE* file) const noexcept {
        if (file != nullptr)
            std::fclose(file);
    }
};

using FilePtr = std::unique_ptr<std::FILE, FileCloser>;
```

사용:

```cpp
FilePtr file{std::fopen(path, "rb")};

if (!file) {
    // fopen 실패
    return;
}
```

이제 `file` 객체가 파괴될 때 `FileCloser`가 자동으로 호출됩니다.

```text
FilePtr 파괴
↓
FileCloser 호출
↓
std::fclose()
```

C API handle에도 RAII를 적용할 수 있다는 점이 중요합니다.

---

## `shared_ptr`: 공유 수명

`std::shared_ptr`는 "편해서 쓰는 smart pointer"가 아니라 **여러 소유자가 하나의 객체 수명을 공동으로 연장한다**는 의미입니다.

```cpp
auto first = std::make_shared<Task>();

auto second = first;
```

개념적으로:

```text
first  ─┐
        ├──> Task
second ─┘
```

둘 다 객체의 소유자입니다.

마지막 `shared_ptr` 소유자가 사라질 때 객체가 파괴됩니다.

---

## `shared_ptr`의 핵심은 공유 ownership입니다

다음과 같이 함수에 pointer를 전달하려는 이유만으로 `shared_ptr`를 선택하면 의미가 왜곡될 수 있습니다.

```cpp
void inspect(std::shared_ptr<Task> task);
```

이 signature는 단순히 "Task를 읽는다"는 뜻이 아니라 함수가 **공유 소유권을 하나 더 얻는다**는 의미가 될 수 있습니다.

단순 관찰이라면 다른 형태가 더 적절할 수 있습니다.

```cpp
void inspect(const Task& task);
```

또는 nullable 관찰이 필요하다면:

```cpp
void inspect(const Task* task);
```

즉 `shared_ptr`를 쓰는 이유는 "null을 표현하기 쉬워서"나 "복사가 편해서"가 아니라 실제 소유 관계가 공유이기 때문이어야 합니다.

---

## shared ownership은 종료 시점을 어렵게 만들 수 있습니다

`shared_ptr`가 많아지면 객체가 언제 파괴되는지 한 곳에서 바로 알기 어려워집니다.

```text
owner A ─┐
owner B ─┼──> object
owner C ─┘
```

객체는 마지막 owner가 사라질 때까지 살아 있습니다.

따라서 다음 질문이 필요합니다.

- 누가 `shared_ptr` 복사본을 가지고 있습니까?
- callback이나 queue가 추가 소유권을 가지고 있습니까?
- object의 종료 시점이 프로그램 의미상 중요한가요?

종료 시점을 명확하게 추적해야 하는 타입에 `shared_ptr`를 습관적으로 사용하면 설계가 복잡해질 수 있습니다.

---

## `shared_ptr` cycle

서로를 `shared_ptr`로 보관하면 참조 cycle이 생길 수 있습니다.

```text
A ─shared_ptr─> B
↑              │
└─shared_ptr───┘
```

예를 들어 외부의 마지막 `shared_ptr<A>`와 `shared_ptr<B>`가 사라져도 A와 B가 서로를 소유하고 있으므로 reference count가 0이 되지 않을 수 있습니다.

그 결과 두 객체가 파괴되지 않습니다.

---

## `weak_ptr`: 소유하지 않는 shared object 관찰

cycle의 한쪽이 실제 소유 관계가 아니라 단순 연결이라면 `std::weak_ptr`를 사용할 수 있습니다.

```text
A ─shared_ptr─> B
↑
└── weak_ptr ──
```

`weak_ptr`은 객체 수명을 연장하지 않습니다.

객체가 아직 살아 있는지 확인하고 잠시 사용하려면 `lock()`을 호출합니다.

```cpp
std::weak_ptr<Task> observer = owner;

if (auto task = observer.lock()) {
    task->run();
}
```

`lock()` 결과는 `std::shared_ptr<Task>`입니다.

- 객체가 살아 있으면 유효한 `shared_ptr`
- 이미 파괴되었으면 빈 `shared_ptr`

이렇게 사용하면 확인한 순간부터 지역 `shared_ptr`이 존재하는 동안 객체의 수명이 유지됩니다.

---

## `weak_ptr`는 raw pointer와 역할이 다릅니다

둘 다 비소유 관찰에 사용할 수 있지만 의미가 다릅니다.

```text
raw pointer
    → 대상 수명이 끝났는지 자동으로 알 수 없음

weak_ptr
    → shared_ptr로 관리되는 대상이 살아 있는지 확인 가능
```

`weak_ptr`는 `shared_ptr` ownership graph 안에서 비소유 연결을 표현할 때 사용합니다.

모든 비소유 pointer를 `weak_ptr`로 바꿀 필요는 없습니다.

---

## lock도 자원입니다

mutex lock 역시 반드시 해제해야 하는 자원입니다.

수동으로 작성하면:

```cpp
state.mutex.lock();

state.value += 1;

state.mutex.unlock();
```

중간 코드에서 예외가 발생하면 `unlock()`에 도달하지 못할 수 있습니다.

```cpp
state.mutex.lock();

might_throw();

state.mutex.unlock();
```

`might_throw()`가 예외를 던지면 mutex가 잠긴 채 남을 수 있습니다.

---

## `std::lock_guard`

RAII lock wrapper를 사용하면 scope 종료와 unlock이 연결됩니다.

```cpp
void update(State& state) {
    std::lock_guard lock{state.mutex};
    state.value += 1;
}
```

개념적으로:

```text
lock_guard 생성
↓
mutex lock
↓
critical section
↓
scope 종료
↓
lock_guard 소멸
↓
mutex unlock
```

중간에 예외가 발생해도 `lock_guard`의 소멸자가 실행되면서 unlock됩니다.

---

## `lock_guard`와 `unique_lock`

`std::lock_guard`는 단순히 scope 전체를 lock 상태로 유지할 때 적합합니다.

```cpp
std::lock_guard lock{mutex};
```

반면 `std::unique_lock`은 더 유연한 lock 관리가 필요할 때 사용할 수 있습니다.

예를 들어:

- 나중에 lock
- 중간에 unlock
- 다시 lock
- condition variable과 함께 사용

같은 동작이 필요할 수 있습니다.

```cpp
std::unique_lock lock{mutex};

// ...

lock.unlock();

// lock이 필요 없는 작업

lock.lock();
```

둘 다 핵심은 mutex ownership을 객체 수명으로 관리한다는 점입니다.

---

## mutex를 잡은 채 외부 callback을 호출하지 않도록 주의합니다

다음 형태는 위험할 수 있습니다.

```cpp
std::lock_guard lock{mutex_};
callback();
```

`callback()`이 어떤 코드를 실행하는지 현재 타입이 통제하지 못한다면 다음 문제가 생길 수 있습니다.

- callback이 다시 같은 mutex를 잡으려 해 deadlock
- callback 실행 시간이 길어 lock을 오래 점유
- callback이 다른 lock을 획득해 lock ordering 문제 발생

가능하다면 공유 상태에서 필요한 값을 복사하거나 이동해 놓은 뒤 lock을 풀고 외부 코드를 호출하는 구조를 검토합니다.

```cpp
Data snapshot;

{
    std::lock_guard lock{mutex_};
    snapshot = data_;
}

callback(snapshot);
```

정확한 설계는 데이터 일관성과 비용에 따라 달라지지만, **lock scope를 불필요하게 넓히지 않는다**는 원칙이 중요합니다.

---

## Rule of Zero

가능하면 다음 특수 멤버 함수를 직접 작성하지 않습니다.

- destructor
- copy constructor
- copy assignment operator
- move constructor
- move assignment operator

대신 자원을 올바르게 관리하는 멤버 타입을 사용합니다.

```cpp
struct Job {
    JobId id;
    std::string name;
    std::vector<std::string> tags;
};
```

`std::string`과 `std::vector`가 이미 자신의 자원을 관리하므로 `Job`은 일반적으로 compiler가 생성하는 복사·이동·소멸 동작으로 충분합니다.

이런 설계 원칙을 **Rule of Zero**라고 부릅니다.

핵심은 다음과 같습니다.

```text
직접 자원 관리 코드를 작성하지 않고
자원 관리 책임을 이미 올바른 RAII 타입에게 맡긴다.
```

---

## Rule of Zero의 장점

자원 관리 코드를 직접 작성하지 않으면 다음 문제가 줄어듭니다.

- double free
- leak
- self-assignment 오류
- move 후 원본 초기화 누락
- 예외 중간 경로에서 cleanup 누락
- copy/move 연산 간 불일치

즉 특수 멤버 함수를 적게 작성하는 것이 단순한 코드 스타일 문제가 아니라 정확성을 높이는 방법입니다.

---

## 직접 자원을 소유해야 하는 타입

모든 타입이 Rule of Zero만으로 끝나는 것은 아닙니다.

예를 들어 OS handle 같은 자원을 직접 감싸는 RAII wrapper를 구현한다면 소멸자와 이동 연산을 직접 작성해야 할 수 있습니다.

이때 먼저 소유 의미를 정합니다.

### 복사 가능한 값

복사 후 두 객체가 논리적으로 독립적이어야 한다면 깊은 복사를 구현할 수 있습니다.

```text
A owns resource A
B = copy(A)
↓
B owns independent resource B
```

### 유일 자원

복사가 자연스럽지 않다면 복사를 금지하고 이동만 허용합니다.

```cpp
class UniqueFile {
public:
    UniqueFile(const UniqueFile&) = delete;
    UniqueFile& operator=(const UniqueFile&) = delete;

    UniqueFile(UniqueFile&& other) noexcept;
    UniqueFile& operator=(UniqueFile&& other) noexcept;

    ~UniqueFile() noexcept;

private:
    Handle handle_{invalid_handle};
};
```

### 이동조차 부적절한 타입

일부 타입은 주소가 바뀌면 안 되거나 내부 동기화 상태 때문에 이동이 자연스럽지 않을 수 있습니다.

그런 경우 복사와 이동을 모두 금지할 수 있습니다.

```cpp
class State {
public:
    State(const State&) = delete;
    State& operator=(const State&) = delete;
    State(State&&) = delete;
    State& operator=(State&&) = delete;

private:
    std::mutex mutex_;
};
```

---

## 이동 전용 RAII 타입의 핵심 불변식

유일 자원을 가진 타입의 이동에서는 다음 조건이 중요합니다.

```text
이동 전:
source가 자원 소유

이동 후:
target이 자원 소유
source는 더 이상 그 자원을 소유하지 않음

마지막:
source와 target 모두 안전하게 소멸 가능
```

예를 들어 handle을 이동한 뒤 원본을 invalid 상태로 만들 수 있습니다.

```cpp
UniqueFile::UniqueFile(UniqueFile&& other) noexcept
    : handle_{other.handle_}
{
    other.handle_ = invalid_handle;
}
```

이렇게 해야 두 객체의 소멸자가 같은 handle을 두 번 닫지 않습니다.

---

## 이동 대입은 기존 자원도 처리해야 합니다

이동 생성은 새 객체가 아직 자원을 가지고 있지 않지만, 이동 대입의 대상 객체는 이미 자원을 소유하고 있을 수 있습니다.

예:

```text
target owns resource A
source owns resource B

target = std::move(source)
```

이동 대입 후 기대되는 상태는:

```text
resource A는 적절히 해제
target owns resource B
source는 resource B를 더 이상 소유하지 않음
```

따라서 이동 대입에서는 현재 대상이 가진 자원을 잃어버리지 않도록 먼저 정리하거나 안전하게 교환해야 합니다.

---

## 생성자 실패와 RAII

생성자에서 예외가 발생하면 **완성되지 못한 객체 자체의 소멸자는 호출되지 않습니다.**

```cpp
class ResourceOwner {
public:
    ResourceOwner() {
        // 여기서 exception 발생 가능
    }

    ~ResourceOwner();
};
```

생성자가 끝까지 완료되지 않았다면 `ResourceOwner` 객체는 완성된 객체가 아니므로 그 소멸자가 호출되지 않습니다.

하지만 이미 정상적으로 생성된 다음 요소는 정리됩니다.

- base class subobject
- member object

즉 생성 중 이미 만들어진 RAII 멤버는 자신의 소멸자로 정리됩니다.

---

## 생성자에서 raw 자원을 직접 잡는 문제

다음과 같은 구조는 주의가 필요합니다.

```cpp
class Example {
public:
    Example() {
        raw_ = acquire_resource();

        might_throw();
    }

    ~Example() {
        release_resource(raw_);
    }

private:
    Resource* raw_{nullptr};
};
```

`acquire_resource()` 이후 `might_throw()`에서 예외가 발생하면 `Example`의 생성자가 완료되지 않았으므로 `~Example()`은 호출되지 않습니다.

그 결과 `raw_`가 누수될 수 있습니다.

---

## 자원은 얻는 즉시 RAII 멤버에 넣습니다

더 안전한 방식은 자원을 획득하는 즉시 이미 올바른 정리 의미를 가진 멤버에게 맡기는 것입니다.

```cpp
class Example {
public:
    Example()
        : resource_{acquire_resource()}
    {
        might_throw();
    }

private:
    ResourcePtr resource_;
};
```

`resource_`가 정상적으로 생성된 뒤 생성자 본문에서 예외가 발생하면 `resource_`의 소멸자는 호출됩니다.

즉 다음 원칙이 중요합니다.

> raw 자원을 얻은 뒤 나중에 RAII 객체에 넘기는 것이 아니라, 가능한 한 획득 즉시 RAII 객체가 소유하게 합니다.

---

## member 초기화 순서도 중요합니다

class member는 initializer list에 적은 순서가 아니라 **class에 선언된 순서**로 초기화됩니다.

```cpp
class Example {
private:
    Resource first_;
    Resource second_;

public:
    Example()
        : second_{/* ... */}
        , first_{/* ... */}
    {}
};
```

실제 초기화 순서는 선언 순서에 따라:

```text
first_
second_
```

입니다.

파괴는 반대로:

```text
second_
first_
```

순서입니다.

자원 간 의존성이 있다면 멤버 선언 순서 자체가 중요합니다.

---

## RAII wrapper에서 지켜야 할 기본 조건

직접 RAII 타입을 작성한다면 다음을 확인합니다.

```text
1. 자원 획득 성공 여부를 명확히 표현하는가?
2. 소멸자는 자원을 정확히 한 번 해제하는가?
3. 소멸자는 예외를 밖으로 던지지 않는가?
4. 복사 의미가 올바른가?
5. 이동 후 원본이 안전하게 소멸 가능한가?
6. 이동 대입이 대상의 기존 자원을 잃어버리지 않는가?
7. invalid/empty 상태를 명확히 표현하는가?
```

---

## 자주 놓치는 문제

### 자원 handle을 가진 타입을 기본 복사에 맡깁니다

raw pointer나 OS handle 값만 복사되면 두 객체가 같은 자원을 소유한다고 생각할 수 있습니다.

그 결과 double close나 double delete가 발생할 수 있습니다.

---

### 이동 대입에서 대상의 기존 자원을 잃어버립니다

```text
target owns A
source owns B

target.handle = source.handle
```

처럼 단순 대입만 하면 기존 `A`를 해제할 기회를 잃을 수 있습니다.

---

### 이동 후 원본 handle을 비우지 않습니다

두 객체가 같은 자원을 가진 상태로 남으면 둘의 소멸자에서 같은 자원을 두 번 해제할 수 있습니다.

---

### 소멸자에서 I/O 실패를 예외로 던집니다

stack unwinding 중 또 예외가 밖으로 나가면 `std::terminate()`가 발생할 수 있습니다.

오류 보고가 필요하면 명시적인 `finish()`, `close()`, `commit()` 같은 연산을 검토합니다.

---

### `shared_ptr`를 단순 전달을 위해 사용합니다

함수가 객체를 잠시 읽기만 하는데 `shared_ptr`를 값으로 받으면 불필요한 shared ownership을 표현하게 됩니다.

---

### `shared_ptr` cycle을 만듭니다

서로가 서로를 소유하면 마지막 외부 owner가 없어져도 객체가 남을 수 있습니다.

비소유 연결에는 `weak_ptr`가 적합한지 확인합니다.

---

### `unique_ptr::get()`으로 얻은 pointer를 저장합니다

소유자가 먼저 파괴되면 저장된 raw pointer는 dangling이 됩니다.

---

### mutex를 잡은 채 외부 callback을 호출합니다

deadlock과 긴 lock 점유 시간이 생길 수 있습니다.

가능하면 lock scope를 필요한 범위로 제한합니다.

---

## 설계할 때의 판단 순서

새 자원을 관리해야 할 때는 다음 순서로 생각할 수 있습니다.

```text
1. 이미 이 자원을 관리하는 표준 RAII 타입이 있는가?
   └─ 있으면 그것을 우선 사용

2. 소유자는 정확히 하나인가?
   └─ std::unique_ptr 또는 전용 RAII wrapper 검토

3. 여러 객체가 실제로 수명을 공동 소유해야 하는가?
   └─ std::shared_ptr 검토

4. shared ownership graph 안의 비소유 연결인가?
   └─ std::weak_ptr 검토

5. 단순 호출 중 관찰만 필요한가?
   └─ reference 또는 raw pointer 검토

6. 자원 해제 중 오류를 caller에게 보고해야 하는가?
   └─ 명시적 close/finish/commit 연산 검토
```

---

## 소유 관계를 코드에서 읽는 방법

예를 들어 다음 코드를 봅니다.

```cpp
auto task = std::make_unique<Task>();

Task* observer = task.get();

queue.push_back(std::move(task));
```

소유권을 추적하면:

```text
1. task가 Task 소유
2. observer는 Task를 비소유 관찰
3. queue로 unique_ptr 이동
4. 이제 queue가 Task 소유
5. observer의 유효 기간은 queue 안의 객체 수명에 의존
```

이런 방식으로 pointer 값보다 소유권의 이동을 따라가면 lifetime 문제를 찾기 쉬워집니다.

---

## 완료 기준

이 문서를 학습한 뒤에는 다음을 설명하고 판단할 수 있어야 합니다.

- RAII가 예외와 조기 반환에서도 자원 정리를 보장하는 이유를 설명합니다.
- 메모리뿐 아니라 파일, socket, mutex lock 등에도 RAII를 적용합니다.
- 각 자원의 소유자와 해제 지점을 타입으로 표현합니다.
- `std::unique_ptr`의 유일 소유권과 이동 의미를 설명합니다.
- `get()`, `reset()`, `release()`의 차이를 설명합니다.
- C API handle에 custom deleter를 사용해 RAII를 적용합니다.
- `std::shared_ptr`를 공유 수명이 실제로 필요한 경우에만 사용합니다.
- `shared_ptr` cycle이 왜 객체 파괴를 막는지 설명합니다.
- `std::weak_ptr`가 shared ownership graph에서 비소유 관계를 표현하는 이유를 설명합니다.
- `std::lock_guard`와 `std::unique_lock`이 mutex unlock을 scope에 연결하는 방식을 설명합니다.
- mutex를 잡은 채 외부 callback을 호출하는 위험을 설명합니다.
- 소멸자에서 보고하기 어려운 오류와 명시적 종료 함수가 필요한 오류를 구분합니다.
- Rule of Zero를 우선하고 특수 멤버 함수를 직접 작성해야 하는 경우를 설명합니다.
- 유일 자원 RAII 타입이 이동 뒤에도 두 객체 모두 안전하게 소멸되는지 확인합니다.
- 이동 대입에서 대상의 기존 자원을 적절히 처리합니다.
- 생성자 실패 시 완성되지 않은 객체의 소멸자는 호출되지 않지만 이미 생성된 멤버는 정리된다는 점을 설명합니다.
- 자원을 얻는 즉시 RAII 객체에 맡기는 이유를 설명합니다.
