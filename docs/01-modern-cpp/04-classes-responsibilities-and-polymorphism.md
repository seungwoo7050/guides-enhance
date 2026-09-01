# 클래스·역할 분리·다형성

## 목표

클래스를 단순히 관련 함수의 묶음으로 만들지 않습니다. 어떤 상태를 누가 보유하고, 어떤 입력을 누가 해석하며, 실제 상태 변경을 누가 수행하고, 결과 표현을 누가 담당하는지 코드에서 찾을 수 있게 나눕니다.

좋은 클래스 설계에서는 다음 질문에 답할 수 있어야 합니다.

- 이 상태의 실제 소유자는 누구입니까?
- 이 클래스가 반드시 지켜야 하는 불변식은 무엇입니까?
- 입력 해석과 상태 변경은 같은 책임입니까?
- 이 클래스가 다른 객체를 소유하는지, 빌려 쓰는지 알 수 있습니까?
- 상속은 "is-a" 관계를 표현합니까, 아니면 단순히 코드를 재사용하려는 것입니까?
- runtime polymorphism이 실제로 필요한가요?
- 객체의 생성 순서와 참조·callback의 수명이 안전하게 연결되어 있습니까?

좋은 분리는 클래스 수를 많이 만드는 것이 아니라, **상태와 변경 이유가 코드에서 명확하게 드러나도록 책임을 배치하는 것**입니다.

---

## 상태를 가진 타입부터 정합니다

상태를 실제로 소유하는 타입을 먼저 찾으면 역할 분리가 쉬워집니다.

```cpp
class Store {
public:
    void put(Key key, Value value);
    std::optional<Value> find(const Key& key) const;

private:
    std::map<Key, Value> data_;
};
```

`Store`는 데이터를 보유하고 저장 규칙을 지킵니다.

예를 들어 다음과 같은 책임은 `Store`가 맡기 자연스럽습니다.

- key 중복 규칙
- 저장 가능한 value 조건
- 조회 규칙
- 내부 container와 데이터 불변식

반면 다음 책임까지 반드시 `Store`가 맡을 필요는 없습니다.

- command-line argument parsing
- 사용자에게 보여 줄 출력 문자열 구성
- 파일 입출력 형식
- 프로그램 실행 순서

그 책임들은 저장 규칙과 별개의 이유로 바뀔 수 있기 때문입니다.

---

## 변경 이유로 책임을 나눕니다

좋은 분리는 "파일 수가 많은가"가 아니라 **무엇이 바뀔 때 어느 코드가 수정되는가**로 판단합니다.

예를 들어 다음처럼 나눌 수 있습니다.

```text
입력 문법 변경
    → parser 수정

저장 규칙 변경
    → store 수정

출력 형식 변경
    → formatter 수정

프로그램 조립 방식 변경
    → main 또는 adapter 수정
```

이렇게 하면 한 요구사항의 변경이 서로 관계없는 여러 영역으로 퍼지는 것을 줄일 수 있습니다.

예를 들어 사용자가 입력하는 문법이 바뀌었는데 `Store`의 내부 자료구조까지 함께 수정해야 한다면, 입력 해석과 저장 규칙이 불필요하게 결합되어 있을 가능성이 있습니다.

---

## 불변식은 실제 소유자가 지킵니다

클래스가 어떤 상태를 소유한다면 그 상태의 유효 조건도 가능한 한 그 클래스가 지키는 것이 좋습니다.

예를 들어 `Port`가 0이 아닌 포트 번호만 허용한다고 가정합니다.

```cpp
class Port {
public:
    explicit Port(unsigned short value);

    unsigned short value() const noexcept {
        return value_;
    }

private:
    unsigned short value_;
};
```

생성자에서 유효성을 확인하면 `Port` 객체가 존재하는 동안 다음 불변식을 유지할 수 있습니다.

```text
Port 객체가 존재한다
→ value_는 허용된 범위의 값이다
```

반대로 모든 호출자가 직접 유효성을 검사해야 한다면 같은 규칙이 여러 곳에 반복되고 누락될 수 있습니다.

---

## 값 타입과 작업 수행 객체

모든 클래스가 같은 성격을 갖는 것은 아닙니다.

### 값 타입

값 타입은 주로 데이터와 그 데이터의 유효 조건을 보유합니다.

```cpp
class Port {
public:
    explicit Port(unsigned short value);

    unsigned short value() const noexcept;

private:
    unsigned short value_;
};
```

값 타입은 보통 다음 특성이 자연스럽습니다.

- 복사할 수 있습니다.
- 복사본은 독립된 값으로 이해할 수 있습니다.
- equality 같은 값 비교가 의미가 있을 수 있습니다.
- 외부 자원의 수명에 크게 의존하지 않습니다.

예:

```cpp
Port a{8080};
Port b = a;
```

`a`와 `b`는 같은 값을 가진 두 독립적인 객체로 이해할 수 있습니다.

### 작업 수행 객체

작업 수행 객체는 다른 상태나 외부 자원을 이용해 동작합니다.

```cpp
class Server {
public:
    explicit Server(Poller& poller);

    void run();

private:
    Poller& poller_;
};
```

이 객체는 `Poller`의 수명이나 외부 I/O 상태에 의존할 수 있습니다.

이런 타입은 값 타입처럼 자유롭게 복사하는 의미가 자연스럽지 않을 수 있습니다.

---

## 값과 서비스 역할을 억지로 합치지 않습니다

다음과 같은 클래스는 여러 성격을 동시에 가질 수 있습니다.

```text
Job
├─ job id
├─ job name
├─ socket
├─ thread
├─ parser state
└─ output formatting
```

이 경우 "Job의 값 자체"와 "Job을 실행하고 입출력하는 객체"의 책임이 섞여 있을 수 있습니다.

예를 들어 다음처럼 나누는 편이 더 명확할 수 있습니다.

```text
Job
    → 값과 유효 조건

JobRunner
    → Job 실행

JobParser
    → 입력을 Job으로 변환

JobFormatter
    → Job을 출력 형식으로 변환
```

이 분리는 복사 의미와 수명 관리도 더 명확하게 합니다.

---

## 생성자에서 유효 상태를 만듭니다

객체가 만들어진 뒤 반드시 별도의 `init()`을 호출해야 한다면 그 사이에 불완전한 상태가 존재합니다.

```cpp
class WorkerPool {
public:
    WorkerPool(std::size_t threads,
               std::size_t queue_capacity);
};
```

필수 값은 가능한 한 생성자에서 받습니다.

```cpp
WorkerPool pool{4, 1024};
```

이렇게 하면 생성이 성공한 `WorkerPool`은 곧바로 사용할 수 있는 상태라고 기대할 수 있습니다.

---

## two-phase initialization의 문제

다음 설계를 생각합니다.

```cpp
WorkerPool pool;
pool.init(4, 1024);
```

`init()` 호출 전의 `pool`은 어떤 상태인지 정해야 합니다.

```text
생성됨
↓
아직 init 안 됨
↓
일부 함수 호출 가능?
↓
init 실패 가능?
↓
다시 init 가능?
```

이런 중간 상태를 모든 member function이 고려해야 할 수 있습니다.

필수 구성 요소라면 생성자에서 확보하는 편이 불변식을 단순화합니다.

---

## 생성 실패가 자연스러운 경우

생성에 필요한 조건을 만족할 수 없다면 객체를 불완전한 상태로 남기는 대신 생성 자체가 실패하게 만들 수 있습니다.

예:

```cpp
class WorkerPool {
public:
    WorkerPool(std::size_t threads,
               std::size_t queue_capacity)
    {
        if (threads == 0)
            throw std::invalid_argument{"threads must be > 0"};
    }
};
```

다만 모든 실패를 반드시 생성자 예외로 처리해야 한다는 뜻은 아닙니다.

예를 들어 다음과 같은 작업은 별도 연산이 더 자연스러울 수 있습니다.

- 다시 시도할 수 있는 network 연결
- 사용자가 나중에 켜고 끄는 optional feature
- 실행 중 반복적으로 수행되는 start/stop 작업

핵심은 **객체가 존재하는 데 반드시 필요한 상태인지**, 아니면 **나중에 변할 수 있는 동작 상태인지**를 구분하는 것입니다.

---

## composition을 먼저 고려합니다

한 객체가 다른 객체의 기능을 **사용하는 관계**라면 composition이 자연스럽습니다.

```cpp
class CommandService {
public:
    CommandService(Store& store, Formatter& formatter)
        : store_{store}, formatter_{formatter}
    {}

private:
    Store& store_;
    Formatter& formatter_;
};
```

`CommandService`는 `Store`의 한 종류가 아닙니다.

```text
CommandService is-a Store
```

라고 말하는 것은 자연스럽지 않습니다.

대신:

```text
CommandService uses Store
CommandService uses Formatter
```

라고 말하는 것이 자연스럽습니다.

이런 관계는 상속보다 composition으로 표현하는 것이 맞습니다.

---

## composition에는 소유와 비소유가 모두 있습니다

composition이라고 해서 항상 멤버를 값으로 소유해야 하는 것은 아닙니다.

### 값으로 소유

```cpp
class Service {
private:
    Store store_;
};
```

`Service`가 `Store`의 수명을 완전히 소유합니다.

### `unique_ptr`로 소유

```cpp
class Service {
private:
    std::unique_ptr<Store> store_;
};
```

역시 `Service`가 소유하지만 동적 수명이나 polymorphic implementation이 필요할 수 있습니다.

### 참조로 비소유

```cpp
class Service {
public:
    explicit Service(Store& store)
        : store_{store}
    {}

private:
    Store& store_;
};
```

`Service`는 `Store`를 소유하지 않습니다.

따라서 `Store`가 `Service`보다 오래 살아야 합니다.

---

## inheritance는 "is-a" 관계일 때 사용합니다

상속은 단순한 코드 재사용 기능으로만 사용하지 않습니다.

다음 관계가 자연스러운지 먼저 확인합니다.

```text
Derived는 Base의 한 종류인가?
Derived를 Base로 사용해도 의미가 자연스러운가?
```

예를 들어:

```cpp
class Handler {
public:
    virtual ~Handler() = default;

    virtual Response handle(const Request&) = 0;
};
```

그리고:

```cpp
class FileHandler : public Handler {
public:
    Response handle(const Request&) override;
};
```

`FileHandler`를 `Handler`로 다루는 것이 의미상 자연스럽다면 runtime polymorphism을 위한 상속이 적절할 수 있습니다.

---

## public inheritance의 핵심: 대체 가능성

public inheritance를 사용할 때는 파생 객체가 기반 객체가 기대되는 위치에서 의미 있게 동작해야 합니다.

예:

```cpp
void dispatch(Handler& handler,
              const Request& request)
{
    handler.handle(request);
}
```

다음 두 구현 모두 `Handler`의 계약을 만족한다면:

```cpp
FileHandler file;
NetworkHandler network;

dispatch(file, request);
dispatch(network, request);
```

상속 관계가 자연스럽습니다.

반대로 단지 member function 몇 개를 재사용하기 위해 상속했다면 기반 타입의 의미와 파생 타입의 의미가 어긋날 수 있습니다.

---

## 다형성이 필요한 경우

실행 중 여러 구현을 같은 interface로 호출해야 한다면 virtual function을 사용할 수 있습니다.

```cpp
class Handler {
public:
    virtual ~Handler() = default;

    virtual Response handle(const Request&) = 0;
};
```

사용자는 concrete type을 몰라도 `Handler&` 또는 `Handler*`를 통해 동작을 호출할 수 있습니다.

```cpp
void run(Handler& handler,
         const Request& request)
{
    Response response = handler.handle(request);
}
```

실행 중 실제 객체 타입에 따라 적절한 override가 호출됩니다.

---

## `override`를 사용합니다

파생 클래스에서 virtual function을 재정의할 때는 `override`를 사용하는 것이 좋습니다.

```cpp
class FileHandler : public Handler {
public:
    Response handle(const Request&) override;
};
```

signature를 실수로 다르게 작성하면 compiler가 알려 줄 수 있습니다.

예를 들어 기반 클래스가:

```cpp
virtual Response handle(const Request&) = 0;
```

인데 파생 클래스가 실수로:

```cpp
Response handle(Request&) override;
```

라고 작성하면 override가 아니므로 compile 오류가 납니다.

`override`가 없다면 새 overload를 만든 것처럼 보일 수 있어 실수를 찾기 어려워집니다.

---

## virtual destructor가 필요한 이유

기반 클래스 pointer로 파생 객체를 삭제할 수 있다면 기반 클래스의 destructor는 virtual이어야 합니다.

```cpp
class Handler {
public:
    virtual ~Handler() = default;

    virtual Response handle(const Request&) = 0;
};
```

예:

```cpp
std::unique_ptr<Handler> handler =
    std::make_unique<FileHandler>();
```

`handler`가 파괴될 때 실제 객체는 `FileHandler`입니다.

기반 destructor가 virtual이면 파괴 과정이 실제 타입에 맞게 이어집니다.

```text
FileHandler destructor
↓
Handler destructor
```

---

## virtual destructor가 없으면 생기는 문제

다음처럼 기반 pointer를 통해 삭제한다고 가정합니다.

```cpp
Handler* handler = new FileHandler;
delete handler;
```

기반 destructor가 virtual이 아니면 기반 pointer를 통한 삭제는 안전한 polymorphic destruction을 보장하지 못합니다. 파생 객체가 가진 자원이 올바르게 정리되지 않을 수 있으며, 이런 삭제는 정의되지 않은 동작이 될 수 있습니다.

따라서 polymorphic base class는 보통 다음 형태를 사용합니다.

```cpp
virtual ~Handler() = default;
```

---

## 모든 base class에 virtual destructor가 필요한 것은 아닙니다

virtual destructor는 **기반 pointer/reference를 통한 polymorphic 사용과 파괴를 의도하는가**와 관련이 있습니다.

상속을 내부 구현 기법으로만 사용하고 기반 pointer로 삭제하지 못하게 설계하는 타입까지 무조건 virtual destructor를 넣어야 한다는 뜻은 아닙니다.

하지만 virtual function이 이미 존재하고 polymorphic base 역할을 한다면 virtual destructor를 두는 것이 일반적인 설계입니다.

---

## object slicing

값으로 기반 타입을 복사하면 파생 부분이 잘려 나갈 수 있습니다.

```cpp
class Handler {
public:
    virtual ~Handler() = default;
    virtual void run();
};

class FileHandler : public Handler {
private:
    FileConfig config_;
};
```

다음 코드는:

```cpp
FileHandler file;
Handler base = file;
```

새로 만들어지는 `base`는 `Handler` 객체입니다.

`FileHandler`의 추가 상태는 복사되지 않습니다.

개념적으로:

```text
FileHandler
├─ Handler 부분
└─ FileHandler 추가 부분

        ↓ 값으로 Handler에 복사

Handler
└─ Handler 부분만 존재
```

이를 **object slicing**이라고 합니다.

---

## polymorphic object는 reference나 pointer로 다룹니다

runtime polymorphism을 유지하려면 보통 기반 타입의 reference나 pointer를 사용합니다.

```cpp
void execute(Handler& handler) {
    handler.run();
}
```

또는 소유권까지 필요하면:

```cpp
std::unique_ptr<Handler>
```

같은 형태를 사용할 수 있습니다.

반면 다음 형태는 slicing을 일으킬 수 있습니다.

```cpp
void execute(Handler handler);
```

parameter를 값으로 받으면 호출 시 파생 객체의 기반 부분만 복사될 수 있습니다.

---

## polymorphic container도 pointer를 사용합니다

다음과 같은 container는 실제 파생 타입을 보존하지 못합니다.

```cpp
std::vector<Handler> handlers;
```

파생 객체를 넣으면 기반 값으로 저장되면서 slicing될 수 있습니다.

여러 파생 객체를 polymorphic하게 소유해야 한다면 다음과 같은 형태를 사용할 수 있습니다.

```cpp
std::vector<std::unique_ptr<Handler>> handlers;
```

예:

```cpp
handlers.push_back(std::make_unique<FileHandler>());
handlers.push_back(std::make_unique<NetworkHandler>());
```

각 객체의 실제 타입은 유지됩니다.

---

## 다형성을 쓰지 않아도 되는 경우

runtime virtual dispatch가 항상 최선은 아닙니다.

필요한 변화의 형태에 따라 다른 방법이 더 단순할 수 있습니다.

### 가능한 타입이 닫혀 있고 값으로 처리할 수 있음

```cpp
using Command =
    std::variant<AddCommand, RemoveCommand, ListCommand>;
```

가능한 타입 집합이 코드에서 명확하게 닫혀 있다면 `std::variant`가 적합할 수 있습니다.

### compile-time 교체

```cpp
template <typename Formatter>
class Service {
    Formatter formatter_;
};
```

runtime polymorphism이 필요하지 않고 compile 시점에 구현을 정할 수 있다면 template을 사용할 수 있습니다.

### 단순 callback

```cpp
std::function<void(const Event&)> callback;
```

동작 하나를 전달하는 것이 목적이라면 전체 class hierarchy보다 lambda나 callback이 더 단순할 수 있습니다.

### 구현 하나만 필요

구현이 하나뿐이고 교체 요구도 없다면 concrete type을 직접 사용하는 것이 가장 단순합니다.

---

## virtual interface가 만드는 비용보다 결합도를 봅니다

virtual dispatch 자체의 작은 실행 비용만을 기준으로 polymorphism 사용 여부를 판단하는 것은 충분하지 않습니다.

더 중요한 질문은 다음과 같습니다.

```text
구현을 runtime에 교체해야 하는가?
호출자는 concrete type을 몰라도 되는가?
interface를 통해 결합도를 줄이는 것이 실제로 필요한가?
객체 ownership과 lifetime은 명확한가?
```

필요한 abstraction이 없다면 virtual hierarchy를 만드는 것이 오히려 코드를 복잡하게 만들 수 있습니다.

---

## 생성자와 소멸자에서 virtual dispatch

생성자 안에서 virtual function을 호출하면 파생 클래스 override가 완성된 객체처럼 동작할 것이라고 기대하면 안 됩니다.

예:

```cpp
class Base {
public:
    Base() {
        setup();
    }

    virtual void setup();
};

class Derived : public Base {
public:
    void setup() override;
};
```

`Base` 생성자가 실행되는 시점에는 아직 `Derived` 부분이 완전히 생성되지 않았습니다.

따라서 `Base` 생성자에서 virtual call을 해도 완성된 `Derived` 객체에 대한 일반적인 dynamic dispatch를 기대할 수 없습니다.

소멸 과정에서도 마찬가지로 이미 파생 부분이 파괴되는 중이므로 일반적인 파생 동작을 기대하면 안 됩니다.

---

## 생성 후 별도 polymorphic 초기화가 필요하다면

파생 타입의 virtual 동작이 반드시 필요한 초기화라면 생성자 내부에서 호출하는 대신 객체 생성 이후 별도 단계에서 호출하도록 설계를 바꿀 수 있습니다.

예:

```cpp
auto handler = std::make_unique<FileHandler>();
handler->start();
```

또는 factory가 완성된 객체를 생성하고 필요한 초기화를 수행한 뒤 반환하도록 만들 수 있습니다.

중요한 것은 **기반 생성자에서 아직 존재하지 않는 파생 상태에 의존하지 않는 것**입니다.

---

## 의존성의 수명

참조 멤버로 외부 객체를 받으면 현재 객체는 그 의존성을 소유하지 않습니다.

```cpp
class Service {
public:
    explicit Service(Store& store)
        : store_{store}
    {}

private:
    Store& store_;
};
```

이 경우 반드시 다음 조건이 필요합니다.

```text
Store의 수명 > Service의 마지막 store_ 사용 시점
```

간단히 말하면 `Store`가 `Service`보다 오래 살아야 합니다.

---

## 생성 순서와 역순 소멸을 이용합니다

조립 위치에서 다음처럼 만들 수 있습니다.

```cpp
int main() {
    Store store;
    Formatter formatter;
    CommandService service{store, formatter};

    // ...
}
```

생성 순서:

```text
store
formatter
service
```

지역 객체는 역순으로 파괴되므로:

```text
service
formatter
store
```

순서로 소멸합니다.

따라서 `service`가 파괴될 때까지 `store`와 `formatter`가 살아 있습니다.

이런 조립 위치를 흔히 composition root라고 생각할 수 있으며, 작은 프로그램에서는 `main()`이 그 역할을 할 수 있습니다.

---

## 선언 순서도 수명에 영향을 줍니다

다음 코드는 위험합니다.

```cpp
int main() {
    Service service{store}; // store는 아직 없음
    Store store;
}
```

당연히 compile되지 않지만, 더 복잡한 객체 그래프에서도 같은 원칙이 적용됩니다.

의존 객체가 먼저 만들어지고, 그것을 빌려 쓰는 객체가 나중에 만들어져야 역순 파괴가 안전하게 작동합니다.

---

## 참조 멤버를 저장할 때의 의미

참조 멤버는 다음 의미를 갖습니다.

```text
이 객체는 dependency를 소유하지 않는다
dependency는 null이 아니다
dependency가 이 객체보다 오래 살아야 한다
```

이 계약이 맞지 않는다면 다른 표현을 고려해야 합니다.

### 소유해야 함

값으로 보유:

```cpp
Store store_;
```

또는 유일 소유권:

```cpp
std::unique_ptr<Store> store_;
```

### nullable 비소유 관계

raw pointer를 사용할 수 있습니다.

```cpp
Store* store_;
```

다만 pointer가 null일 수 있는지와 수명 조건을 명확히 해야 합니다.

raw pointer를 단순히 "heap 객체"라는 이유로 owning pointer처럼 사용하지 않습니다.

---

## callback도 비소유 수명 문제를 만들 수 있습니다

다음처럼 객체를 callback에서 참조로 capture할 수 있습니다.

```cpp
Store store;

register_callback([&store] {
    store.flush();
});
```

이 callback이 `store`보다 오래 살아남는다면 dangling reference가 됩니다.

따라서 callback은 등록하는 시점뿐 아니라 **실제로 호출되는 시점**까지 capture 대상이 살아 있는지 확인해야 합니다.

비동기 작업, event loop, thread, delayed callback에서는 특히 중요합니다.

---

## 큰 클래스가 보내는 신호

다음이 함께 보이면 책임을 나눌 지점을 검토합니다.

- parser 상태와 업무 데이터를 동시에 보유합니다.
- file descriptor, thread, formatting 문자열까지 한 클래스가 관리합니다.
- private 멤버 일부만 사용하는 함수 묶음이 여러 개 있습니다.
- test 하나를 만들기 위해 filesystem과 network를 모두 준비해야 합니다.
- 한 변경이 관계없는 함수까지 자주 건드립니다.
- 생성자가 수많은 서로 다른 dependency를 받습니다.
- class 이름이 `Manager`, `Processor`, `Controller`처럼 지나치게 포괄적인데 책임을 한 문장으로 설명하기 어렵습니다.

이런 신호는 클래스가 여러 변경 이유를 동시에 가지고 있을 수 있음을 나타냅니다.

---

## 큰 클래스 분리 예시

예를 들어 다음 클래스가 있다고 가정합니다.

```text
TaskManager
├─ command-line parsing
├─ task 저장
├─ file read/write
├─ terminal formatting
└─ network sync
```

한 클래스에서 모두 처리하면 task 저장 규칙을 테스트하기 위해 filesystem과 network까지 준비해야 할 수 있습니다.

다음처럼 역할을 나눌 수 있습니다.

```text
CommandParser
    → 문자열을 command로 변환

TaskStore
    → task 상태와 규칙 관리

TaskRepository
    → 파일 또는 외부 저장소 persistence

TaskFormatter
    → 출력 표현

SyncClient
    → network 동기화
```

그 뒤 상위 service가 이 객체들을 조합해 use case를 수행할 수 있습니다.

---

## 너무 잘게 나누는 것도 문제입니다

클래스를 작게 만드는 것 자체가 목표는 아닙니다.

예를 들어 하나의 불변식을 유지하려면 항상 세 필드가 함께 변경되어야 한다고 가정합니다.

```text
balance
last_update
version
```

이를 서로 다른 객체에 흩어 놓으면 한 상태 변경을 위해 여러 객체의 호출 순서를 정확히 맞춰야 할 수 있습니다.

이 경우 오히려 불변식을 한 타입 내부에 유지하는 것이 더 안전할 수 있습니다.

좋은 분리의 기준은 다음과 같습니다.

```text
함께 변해야 하는 상태는 함께 둔다.
서로 다른 이유로 변하는 정책은 분리한다.
```

---

## 모든 함수를 `Manager`에 넣지 않습니다

`Manager`라는 이름은 책임이 넓어지기 쉽습니다.

다음처럼 계속 기능이 추가될 수 있습니다.

```cpp
class TaskManager {
public:
    void parse();
    void load();
    void save();
    void validate();
    void format();
    void sync();
    void run();
};
```

이런 클래스는 "task와 관련된 모든 것"을 담당하는 객체가 되기 쉽습니다.

대신 각각의 책임을 먼저 식별하고, 정말 함께 상태를 공유해야 하는 기능만 같은 타입에 두는 편이 좋습니다.

---

## 자주 놓치는 문제

### 이름이 비슷하다는 이유로 상속합니다

`FileLogger`와 `FileReader` 모두 파일을 사용한다고 해서 둘 사이에 상속 관계가 생기는 것은 아닙니다.

공통 dependency를 composition으로 공유하는 것이 더 자연스러울 수 있습니다.

---

### 코드 재사용만을 위해 상속합니다

상속의 기반 타입으로 실제 사용하지 않을 것이라면 helper object나 composition이 더 명확할 수 있습니다.

---

### 기반 destructor를 virtual로 만들지 않고 polymorphic 삭제를 합니다

```cpp
Base* p = new Derived;
delete p;
```

같은 사용을 허용한다면 기반 destructor가 virtual인지 확인합니다.

---

### 값으로 기반 타입을 복사해 slicing이 발생합니다

```cpp
Derived d;
Base b = d;
```

`Derived` 고유 상태가 사라집니다.

runtime polymorphism을 유지하려면 reference나 pointer를 사용합니다.

---

### 생성자 안에서 virtual function을 호출해 파생 동작을 기대합니다

기반 생성 중에는 파생 부분이 아직 완성되지 않았습니다.

---

### callback이나 참조가 소유 객체보다 오래 남습니다

비소유 관계는 실제 사용 시점까지 원본이 살아 있어야 합니다.

---

### 모든 함수를 하나의 `Manager`에 넣습니다

책임과 변경 이유가 뒤섞여 test와 변경 범위가 커질 수 있습니다.

---

## 설계할 때의 판단 순서

새 클래스를 만들거나 기존 클래스를 나눌 때는 다음 순서로 생각할 수 있습니다.

```text
1. 어떤 상태를 소유하는가?
2. 그 상태가 지켜야 하는 불변식은 무엇인가?
3. 어떤 이유로 이 코드가 변경되는가?
4. dependency를 소유하는가, 빌려 쓰는가?
5. 다른 타입과 관계가 uses-a인가 is-a인가?
6. runtime 교체가 정말 필요한가?
7. 값으로 복사해도 의미가 자연스러운가?
8. reference/pointer/callback의 수명은 누가 보장하는가?
```

---

## 완료 기준

이 문서를 학습한 뒤에는 다음을 설명하고 판단할 수 있어야 합니다.

- 각 상태의 실제 소유자를 말할 수 있습니다.
- 상태를 소유하는 타입이 자신의 불변식을 지키도록 설계합니다.
- 입력 해석, 상태 변경, 출력 형식을 별도 코드에서 검사할 수 있습니다.
- 값 타입과 외부 자원에 의존하는 작업 수행 객체의 차이를 설명합니다.
- 필수 상태를 생성자에서 받아 불완전한 객체 상태를 줄입니다.
- composition과 inheritance를 "uses-a"와 "is-a" 관계로 구분합니다.
- public inheritance에서 기반 타입으로 대체 가능한 의미가 필요한 이유를 설명합니다.
- runtime polymorphism이 필요한 경우와 `std::variant`, template, callback, concrete type이 더 적합한 경우를 구분합니다.
- polymorphic base class에서 virtual destructor가 필요한 이유를 설명합니다.
- `override`가 signature 실수를 잡는 데 도움이 되는 이유를 설명합니다.
- object slicing이 언제 발생하고 왜 polymorphism을 잃는지 설명합니다.
- polymorphic object를 reference나 pointer로 다루는 이유를 설명합니다.
- 생성자와 소멸자에서 virtual dispatch에 파생 동작을 기대하면 안 되는 이유를 설명합니다.
- 참조 멤버가 비소유 관계임을 설명하고 dependency의 수명 조건을 말할 수 있습니다.
- 객체 생성 순서와 역순 파괴를 이용해 참조 dependency의 수명을 안전하게 구성합니다.
- callback과 비소유 pointer/reference가 원본보다 오래 살아남지 않는지 확인합니다.
- 큰 클래스를 분리해야 하는 신호와 지나치게 작은 클래스로 쪼개는 문제를 함께 설명합니다.
