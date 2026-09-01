# C++98 상속과 다형성

## 목표

상속을 단순한 코드 재사용 수단으로 사용하지 않습니다. **기반 타입을 기대하는 코드가 여러 파생 구현을 같은 방식으로 다뤄야 할 때** 상속과 다형성을 사용합니다.

C++98에서 다형성을 설계할 때는 함수 호출 방식만 보는 것이 아니라 다음 문제를 함께 처리해야 합니다.

- 어떤 함수가 virtual dispatch 대상인지
- 파생 함수가 실제로 override되었는지
- 기반 pointer를 통해 삭제해도 안전한지
- 다형 객체를 값으로 복사하면서 slicing이 발생하지 않는지
- raw pointer를 누가 소유하고 언제 삭제하는지
- 다형 객체를 보유하는 클래스의 복사 의미를 어떻게 정할지
- 상속보다 composition이 더 적절한 관계인지

즉, 상속 구조를 만든다는 것은 단순히 `class Derived : public Base`를 쓰는 것이 아니라, **호출·수명·복사·소유권 규칙을 함께 정의하는 것**입니다.

## 상속을 사용할 기준

상속을 검토할 때 가장 중요한 질문은 다음입니다.

> 기반 타입이 필요한 곳에 파생 타입을 넣어도 그 코드의 의미가 유지되는가?

예를 들어 모든 handler가 같은 형태의 요청을 처리하고 결과를 반환해야 한다면 공통 기반 타입을 둘 수 있습니다.

```cpp
class Handler {
public:
    virtual ~Handler() {}

    virtual Response handle(
        const Request &request,
        Store &store) const = 0;
};
```

`PutHandler`, `GetHandler` 등이 모두 `Handler`가 필요한 위치에서 같은 방식으로 사용될 수 있다면 public inheritance가 자연스럽습니다.

반대로 단순히 구현 코드를 재사용하고 싶다는 이유만으로 상속하면 타입 관계와 실제 의미가 어긋날 수 있습니다.

## virtual dispatch

다음 함수는 virtual function입니다.

```cpp
virtual Response handle(
    const Request &request,
    Store &store) const = 0;
```

기반 타입 pointer가 실제로 파생 객체를 가리키고 있을 때 virtual function을 호출하면, **pointer의 정적 타입이 아니라 실제 객체의 동적 타입에 따라** 실행할 함수가 선택됩니다.

예를 들어:

```cpp
class PutHandler : public Handler {
public:
    Response handle(
        const Request &request,
        Store &store) const;
};
```

```cpp
Handler *handler = new PutHandler;

Response response =
    handler->handle(request, store);
```

`handler` 변수의 정적 타입은 `Handler *`이지만 실제 객체는 `PutHandler`이므로 `PutHandler::handle()`이 호출됩니다.

이 동작을 **virtual dispatch**, 또는 동적 디스패치라고 합니다.

## 정적 타입과 동적 타입

다형성을 이해하려면 두 타입을 구분해야 합니다.

```cpp
Handler *handler = new PutHandler;
```

여기서:

```text
정적 타입(static type)
Handler *

동적 타입(dynamic type)
PutHandler
```

정적 타입은 소스 코드에서 변수 선언을 보고 compiler가 알 수 있는 타입입니다.

동적 타입은 실행 중 해당 pointer나 reference가 실제로 가리키는 객체 타입입니다.

virtual 함수 호출은 동적 타입을 사용해 최종 구현을 선택합니다.

일반 non-virtual 함수 호출은 정적 타입을 기준으로 결정됩니다.

## virtual 함수와 일반 overload를 구분합니다

virtual dispatch와 overload resolution은 서로 다른 과정입니다.

예를 들어:

```cpp
class Base {
public:
    virtual void run(int);
    virtual void run(const std::string &);
};
```

여기서 어떤 `run` overload를 호출할지는 먼저 인자의 정적 타입을 기준으로 결정됩니다.

그 뒤 선택된 함수가 virtual이면 실제 객체의 동적 타입에 따라 파생 구현이 실행될 수 있습니다.

즉:

```text
overload resolution
→ 어떤 함수 signature를 호출할지 결정

virtual dispatch
→ 그 signature의 어느 클래스 구현을 실행할지 결정
```

이 두 단계를 같은 개념으로 생각하면 이름 가리기나 override 문제를 이해하기 어려워집니다.

## C++98에서는 `override`가 없습니다

C++11 이후에는 다음처럼 의도를 compiler에게 명시할 수 있습니다.

```cpp
Response handle(...) const override;
```

하지만 C++98에는 `override`가 없습니다.

따라서 파생 클래스가 기반 virtual function을 재정의한다고 생각했더라도 signature가 조금만 다르면 override가 되지 않을 수 있습니다.

기반 클래스:

```cpp
class Handler {
public:
    virtual Response handle(
        const Request &request,
        Store &store) const = 0;
};
```

잘못된 파생 클래스:

```cpp
class PutHandler : public Handler {
public:
    Response handle(
        Request &request,
        Store &store);
};
```

차이점은 두 가지입니다.

- 첫 번째 매개변수에서 `const`가 빠졌습니다.
- 멤버 함수 뒤의 `const`가 빠졌습니다.

이 함수는 기반 함수와 같은 이름을 갖지만 동일한 signature가 아니므로 기반 virtual function을 override하지 않습니다.

기반 함수가 pure virtual이라면 `PutHandler`는 여전히 abstract class일 수 있습니다.

## override signature에서 확인할 것

C++98에서는 다음 요소를 특히 확인합니다.

- 함수 이름
- 매개변수 개수
- 각 매개변수 타입
- reference 여부
- pointer 여부
- 매개변수의 `const`
- 멤버 함수 뒤의 `const`

예:

```cpp
virtual Response handle(
    const Request &request,
    Store &store) const = 0;
```

와

```cpp
Response handle(
    const Request &request,
    Store &store) const;
```

는 override 관계를 이룰 수 있습니다.

반면:

```cpp
Response handle(
    Request request,
    Store &store) const;
```

처럼 첫 번째 매개변수를 값으로 받으면 다른 함수입니다.

## 반환 타입과 override

일반적으로 override 함수는 기반 virtual function과 같은 반환 타입을 사용합니다.

다만 pointer나 reference를 반환하는 경우에는 C++이 허용하는 **공변 반환 타입(covariant return type)** 이 있습니다.

예를 들어:

```cpp
class Base {
public:
    virtual Base *clone() const = 0;
};

class Derived : public Base {
public:
    virtual Derived *clone() const;
};
```

처럼 파생 클래스 pointer/reference 반환은 특정 조건에서 허용됩니다.

하지만 단순한 C++98 인터페이스에서는 혼동을 줄이기 위해 기반 선언과 동일한 반환 타입을 유지하는 편이 이해하기 쉽습니다.

## 기반 pointer를 통한 호출로 override를 확인합니다

파생 객체 변수를 직접 호출하면 잘못된 signature를 가진 함수도 정상적으로 호출될 수 있으므로 override 여부를 놓칠 수 있습니다.

예:

```cpp
PutHandler put;

put.handle(request, store);
```

이 호출만으로는 기반 virtual function을 실제로 override했는지 확인하기 어렵습니다.

반대로 기반 reference나 pointer를 통해 호출하면 다형성 계약을 직접 검사할 수 있습니다.

```cpp
Handler &handler = put;

handler.handle(request, store);
```

기반 타입을 통한 테스트를 두면 virtual dispatch가 의도대로 작동하는지 확인하기 쉽습니다.

compiler warning도 가능한 한 활성화합니다.

```sh
-Wall -Wextra -Werror -pedantic
```

compiler가 제공하는 추가 override 관련 warning이 있다면 사용하는 것도 도움이 되지만, 표준 C++98 자체에는 `override` 검사를 강제하는 문법이 없습니다.

## virtual destructor

다형 기반 클래스에서 가장 중요한 수명 규칙 중 하나는 virtual destructor입니다.

```cpp
class Handler {
public:
    virtual ~Handler() {}
};
```

다음 상황을 생각해 봅니다.

```cpp
Handler *handler = new PutHandler;
delete handler;
```

실제 객체는 `PutHandler`이지만 `delete` 표현식에서 사용하는 pointer 타입은 `Handler *`입니다.

기반 클래스 소멸자가 virtual이면 파생 객체의 소멸자가 먼저 호출되고, 이어서 기반 클래스 소멸자가 호출됩니다.

개념적으로:

```text
delete Handler*
→ PutHandler::~PutHandler()
→ Handler::~Handler()
```

따라서 파생 객체가 소유한 자원도 정상적으로 정리됩니다.

## 기반 소멸자가 virtual이 아니면

다형적으로 삭제할 객체의 기반 소멸자가 virtual이 아니면 다음 코드는 안전하지 않습니다.

```cpp
Handler *handler = new PutHandler;
delete handler;
```

실제 객체 전체를 올바르게 파괴한다는 보장이 없습니다. 결과적으로 파생 클래스가 관리하던 자원이 정리되지 않거나 정의되지 않은 동작이 발생할 수 있습니다.

따라서 다음 조건이 있다면 기반 소멸자를 virtual로 둡니다.

> 이 타입의 객체를 기반 클래스 pointer를 통해 `delete`할 수 있다.

pure virtual 함수가 있다는 사실만으로 소멸자가 자동으로 virtual이 되는 것은 아닙니다. 소멸자에 직접 `virtual`을 선언해야 합니다.

## protected non-virtual destructor

모든 기반 클래스가 반드시 public virtual destructor를 가져야 하는 것은 아닙니다.

어떤 타입은 기반 pointer를 통한 삭제 자체를 허용하지 않는 설계를 택할 수 있습니다.

예:

```cpp
class NonOwningBase {
protected:
    ~NonOwningBase() {}
};
```

이 경우 외부 코드에서 다음과 같은 삭제를 막을 수 있습니다.

```cpp
NonOwningBase *base = /* ... */;

// delete base; // protected destructor라 외부에서 불가
```

이 설계는 "다형 호출은 허용하지만 기반 pointer로 소유하지 않는다"는 식의 제한된 용도에서 사용할 수 있습니다.

다만 사용자가 삭제 방법을 쉽게 오해할 수 있으므로 이런 설계는 의도가 분명해야 합니다.

## pure virtual function과 abstract class

다음처럼 `= 0`이 붙은 함수는 pure virtual function입니다.

```cpp
virtual Response handle(
    const Request &request,
    Store &store) const = 0;
```

하나 이상의 pure virtual function을 가진 클래스는 일반적으로 **abstract class**가 됩니다.

abstract class는 직접 객체를 만들 수 없습니다.

```cpp
Handler handler; // 불가
```

대신 pointer나 reference 타입으로 사용합니다.

```cpp
Handler *handler;
Handler &reference = someDerivedHandler;
```

C++98에는 별도의 `interface` 키워드가 없습니다. pure virtual function만 가진 abstract class를 interface 역할로 사용할 수 있습니다.

## interface 역할의 기반 클래스

handler 기반 타입이 오직 공통 호출 규약만 표현한다면 상태를 억지로 넣지 않는 편이 좋습니다.

```cpp
class Handler {
public:
    virtual ~Handler() {}

    virtual Response handle(
        const Request &request,
        Store &store) const = 0;
};
```

여기에는 모든 handler가 공유해야 하는 상태가 없다면 멤버 변수를 넣을 이유가 없습니다.

예를 들어 Store는 handler들이 사용하는 외부 상태이지 Handler 자체의 공통 내부 상태가 아닐 수 있습니다.

그런 경우:

```cpp
Response handle(
    const Request &request,
    Store &store) const;
```

처럼 함수 인자로 전달하면 의존성이 더 명확합니다.

## 기반 클래스에도 구현을 둘 수 있습니다

pure virtual 기반 클래스라고 해서 모든 코드가 비어 있어야 하는 것은 아닙니다.

여러 파생 클래스가 정말로 공유하는 동작이 있다면 일반 protected 멤버 함수로 둘 수 있습니다.

```cpp
class Handler {
public:
    virtual ~Handler() {}

    virtual Response handle(
        const Request &request,
        Store &store) const = 0;

protected:
    bool hasArgument(
        const Request &request,
        std::size_t index) const;
};
```

다만 단순 코드 중복 제거만을 위해 상속 계층이 생기기 시작한다면 composition이나 일반 helper function이 더 단순한지 먼저 확인합니다.

## object slicing

다형 객체를 값으로 다루면 파생 부분이 잘려 나갈 수 있습니다.

예:

```cpp
class Base {
public:
    virtual ~Base() {}
};

class Derived : public Base {
private:
    int extra_;
};
```

다음 함수는 위험합니다.

```cpp
void run(Base base);
```

호출:

```cpp
Derived derived;
run(derived);
```

`Derived` 객체 전체가 `Base` 매개변수에 들어가는 것이 아니라 기반 클래스 부분만 복사되어 새로운 `Base` 객체가 만들어집니다.

개념적으로:

```text
Derived
+-------------------+
| Base 부분         |
| Derived 전용 부분 |
+-------------------+

값으로 Base에 복사
        ↓

Base
+-----------+
| Base 부분 |
+-----------+
```

파생 클래스 전용 상태는 사라집니다. 이를 **object slicing**이라고 합니다.

## slicing을 피하려면 pointer나 reference를 사용합니다

다형 객체는 보통 기반 pointer나 reference로 전달합니다.

```cpp
void run(Handler &handler);
```

또는 수정하지 않는다면:

```cpp
void run(const Handler &handler);
```

pointer 형태도 가능합니다.

```cpp
void run(Handler *handler);
```

reference는 null 상태가 필요하지 않을 때, pointer는 null을 표현해야 하거나 pointer 소유권 규칙이 필요한 경우 사용할 수 있습니다.

중요한 점은 **다형 객체를 기반 타입 값으로 복사하지 않는 것**입니다.

## 값 container와 다형 객체

다형 객체를 기반 타입 값으로 container에 넣으면 같은 slicing 문제가 발생합니다.

예를 들어:

```cpp
std::vector<Handler> handlers;
```

는 pure virtual `Handler`라면 애초에 사용할 수 없고, concrete 기반 클래스라 하더라도 파생 객체를 값으로 넣으면 파생 부분이 잘릴 수 있습니다.

C++98에서 서로 다른 파생 타입을 한 container에 보관하려면 흔히 pointer를 저장합니다.

```cpp
std::vector<Handler *> handlers;
```

하지만 이 순간부터 pointer 소유권과 삭제 책임을 직접 관리해야 합니다.

다형성을 쓰는 것과 소유권 설계는 분리할 수 없습니다.

## 복사 가능한 다형 객체와 `clone()`

다형 객체를 "실제 동적 타입을 유지한 채 복사"해야 한다면 일반 복사 생성자만으로는 기반 pointer에서 정확한 타입을 알 수 없습니다.

이 경우 virtual `clone()` 패턴을 사용할 수 있습니다.

```cpp
class Handler {
public:
    virtual ~Handler() {}

    virtual Handler *clone() const = 0;
};
```

파생 클래스:

```cpp
class PutHandler : public Handler {
public:
    virtual Handler *clone() const
    {
        return new PutHandler(*this);
    }
};
```

호출:

```cpp
Handler *copy = original->clone();
```

이렇게 하면 `original`의 실제 동적 타입에 맞는 복사본이 만들어집니다.

하지만 C++98에서는 반환값이 raw pointer이므로 소유권 계약을 반드시 정해야 합니다.

예:

> `clone()`이 반환한 pointer는 caller가 소유하며, 사용 후 `delete`해야 한다.

이 계약이 없으면 memory leak이나 이중 삭제가 발생하기 쉽습니다.

## 이름 가리기와 overload

파생 클래스에서 기반 클래스와 같은 이름의 함수를 하나라도 선언하면 기반 클래스의 같은 이름 overload들이 이름 검색에서 가려질 수 있습니다.

예:

```cpp
class Base {
public:
    void handle(int);
    void handle(const std::string &);
};

class Derived : public Base {
public:
    void handle(int);
};
```

이제:

```cpp
Derived derived;

derived.handle(10);
```

은 정상입니다.

하지만:

```cpp
derived.handle(std::string("abc"));
```

에서는 `Base::handle(const std::string &)`가 자동으로 overload 후보에 들어오지 않을 수 있습니다. `Derived::handle`이라는 이름이 기반의 같은 이름 집합을 가리기 때문입니다.

이 현상은 override와 별개인 **name hiding**입니다.

## `using Base::handle`

C++98에서는 기반 클래스 overload를 파생 클래스 scope로 다시 노출할 수 있습니다.

```cpp
class Derived : public Base {
public:
    using Base::handle;

    void handle(int);
};
```

그러면 기반 클래스의 다른 `handle` overload도 함께 overload resolution에 참여할 수 있습니다.

이 기능은 "기반 overload 일부를 유지하면서 특정 overload만 파생 클래스에서 새로 정의"할 때 유용합니다.

## override와 이름 가리기는 다릅니다

다음 두 문제를 구분해야 합니다.

### override 실패

```cpp
class Base {
public:
    virtual void run(int) const;
};

class Derived : public Base {
public:
    void run(int); // 뒤 const가 없어 override 아님
};
```

기반 virtual 함수와 signature가 다릅니다.

### 이름 가리기

```cpp
class Base {
public:
    void run(int);
    void run(const std::string &);
};

class Derived : public Base {
public:
    void run(int);
};
```

`Derived::run(int)` 때문에 기반의 다른 `run` overload가 이름 검색에서 가려질 수 있습니다.

둘은 원인이 다르므로 문제를 진단할 때 구분해야 합니다.

## handler 소유권

다형 객체를 raw pointer로 저장하는 Router를 생각해 봅니다.

```cpp
class Router {
private:
    std::map<std::string, Handler *> handlers_;
};
```

Router가 이 pointer들을 소유한다고 정했다면 다음 불변조건을 유지해야 합니다.

```text
- handlers_에 저장된 각 Handler*는 Router가 소유한다.
- 각 Handler 객체는 정확히 한 번 delete된다.
- 같은 Handler 객체를 여러 entry가 동시에 소유하지 않는다.
- 등록 실패 시 아직 Router가 소유하지 않는 객체는 적절히 정리된다.
```

소유권은 `std::map`이 자동으로 처리하지 않습니다. container가 삭제될 때 pointer 값만 사라질 뿐, pointer가 가리키는 객체에 `delete`를 자동으로 호출하지 않습니다.

## Router 소멸

Router가 handler를 소유한다면 소멸자에서 모두 삭제해야 합니다.

```cpp
Router::~Router()
{
    std::map<std::string, Handler *>::iterator it;

    for (it = handlers_.begin();
         it != handlers_.end();
         ++it) {
        delete it->second;
    }
}
```

`Handler`의 소멸자가 virtual이므로 실제 파생 handler 소멸자가 올바르게 호출됩니다.

이 두 조건은 함께 필요합니다.

```text
Router
→ 각 Handler*를 delete할 책임

Handler
→ 기반 pointer delete를 안전하게 하기 위해 virtual destructor 제공
```

## 등록 중 실패

다음 코드를 생각해 봅니다.

```cpp
Handler *handler = new PutHandler;
handlers_.insert(
    std::make_pair("PUT", handler));
```

이 과정에는 여러 실패 지점이 있습니다.

- `new PutHandler` 실패
- map node 할당 실패
- key 복사 실패
- 중복 key 때문에 실제 삽입이 이루어지지 않음

따라서 "예외가 발생하지 않았다"는 사실만으로 Router가 소유권을 가져갔다고 판단하면 안 됩니다.

예를 들어 성공한 삽입 시점부터 Router가 소유한다고 정했다면:

```cpp
Handler *handler = new PutHandler;

try {
    std::pair<
        std::map<std::string, Handler *>::iterator,
        bool
    > result =
        handlers_.insert(
            std::make_pair("PUT", handler));

    if (!result.second) {
        delete handler;
        throw DuplicateHandler("PUT");
    }
} catch (...) {
    /*
     * 단, 위에서 이미 delete한 경로와
     * 중복 정리되지 않도록 구조를 명확히 해야 한다.
     */
    throw;
}
```

실제 구현에서는 소유권 이전 시점을 하나로 고정하고, 모든 실패 경로에서 정확히 한 번만 정리하도록 설계합니다.

중요한 것은 다음 질문에 항상 답할 수 있어야 한다는 점입니다.

> 이 줄에서 예외가 발생하면 `handler`의 소유자는 누구인가?

## 생성자에서 여러 handler 등록 중 실패

Router 생성자에서 여러 handler를 순서대로 생성·등록한다고 가정합니다.

```text
PUT 등록 성공
GET 등록 성공
DELETE 등록 중 실패
```

Router 객체의 생성이 완료되기 전에 예외가 발생하면 `Router::~Router()` 자체는 호출되지 않습니다.

따라서 생성자 본문에서 raw pointer를 직접 획득하고 container에 넣는 구조라면 부분 생성 상태의 정리를 별도로 고려해야 합니다.

예를 들어 이미 등록된 handler들을 catch 블록에서 정리하거나, 생성과 등록을 예외 안전한 helper로 구성할 수 있습니다.

핵심은 "생성자가 실패하면 소멸자가 모두 정리해 줄 것"이라고 가정하지 않는 것입니다.

## Router 복사 문제

다음 상태를 생각해 봅니다.

```text
Router A
handlers_["PUT"] ----> PutHandler
```

compiler 기본 복사를 사용하면 pointer 주소만 복사됩니다.

```text
Router A ----+
             +----> PutHandler
Router B ----+
```

두 Router가 모두 pointer를 소유한다고 생각하고 소멸자에서 `delete`하면 같은 Handler를 두 번 삭제하게 됩니다.

따라서 raw owning pointer container를 가진 Router는 복사 의미를 반드시 정해야 합니다.

## 복사가 필요 없다면 막습니다

C++98에는 `= delete`가 없으므로 복사 생성자와 복사 대입 연산자를 private으로 선언하고 정의하지 않는 방식을 사용할 수 있습니다.

```cpp
class Router {
public:
    Router();
    ~Router();

private:
    Router(const Router &);
    Router &operator=(const Router &);

private:
    std::map<std::string, Handler *> handlers_;
};
```

외부 코드가 복사하려 하면 접근할 수 없어 compile 오류가 발생합니다.

Router가 프로그램에서 하나의 명령 registry 역할만 한다면 복사를 금지하는 것이 가장 단순한 설계일 수 있습니다.

## Router 복사가 필요하다면 깊은 복사가 필요합니다

복사 가능한 Router를 정말로 지원해야 한다면 각 handler의 동적 타입을 유지한 복사본을 새로 만들어야 합니다.

이 경우 앞에서 설명한 `clone()` 패턴을 사용할 수 있습니다.

개념적으로:

```cpp
for (each handler in other.handlers_) {
    Handler *copy = handler->clone();
    // 새 Router에 등록
}
```

하지만 복사 도중 일부 `clone()`이나 map 삽입이 실패할 수 있으므로 부분 복사 상태 정리도 필요합니다.

따라서 raw pointer 기반 다형 container의 깊은 복사는 단순하지 않습니다. 복사가 필요하지 않다면 금지하는 편이 안전합니다.

## composition이 더 나은 경우

다음 관계는 보통 상속보다 composition이 자연스럽습니다.

- `Server`가 `Poller`를 사용합니다.
- `Service`가 `Store`를 사용합니다.
- `Connection`이 `Parser`를 보유합니다.

이 관계들은 "A는 B이다"보다는 "A가 B를 사용한다"에 가깝습니다.

예:

```cpp
class Service {
public:
    explicit Service(Store &store)
        : store_(store)
    {
    }

private:
    Store &store_;
};
```

이는 상속이 아니라 참조 멤버를 이용한 composition 또는 association입니다.

## 상속과 composition을 구분하는 질문

다음 질문을 사용합니다.

### 상속 후보

> `Derived`를 `Base`가 필요한 모든 위치에 넣어도 의미가 자연스러운가?

예:

```text
PutHandler is-a Handler
GetHandler is-a Handler
```

### composition 후보

> 한 객체가 다른 객체의 기능을 사용하거나 보유하는 관계인가?

예:

```text
Service has/uses Store
Connection has Parser
Server uses Poller
```

코드 재사용만 필요하다면 일반 함수, helper 객체, 멤버 객체가 더 적절할 수 있습니다.

## public inheritance의 의미

C++98에서도 public inheritance는 단순히 기반 멤버를 가져오는 문법 이상의 의미를 가집니다.

```cpp
class PutHandler : public Handler {
};
```

이 선언은 `PutHandler`를 `Handler`로 취급하는 코드가 의미적으로 타당하다는 설계 의도를 나타냅니다.

따라서 다음이 자연스러워야 합니다.

```cpp
Handler *handler = new PutHandler;
```

그리고 `Handler`의 public 계약을 사용하는 코드가 `PutHandler`에서도 올바르게 동작해야 합니다.

이 조건이 맞지 않는다면 상속 구조 자체를 다시 검토해야 합니다.

## 다중 상속

C++98에서는 다중 상속을 사용할 수 있습니다.

서로 독립적인 pure interface를 여러 개 구현하는 경우에는 비교적 이해하기 쉽습니다.

예:

```cpp
class Readable {
public:
    virtual ~Readable() {}
    virtual void read() = 0;
};

class Writable {
public:
    virtual ~Writable() {}
    virtual void write() = 0;
};

class Device :
    public Readable,
    public Writable {
public:
    virtual void read();
    virtual void write();
};
```

이 경우 `Readable`과 `Writable`이 서로 독립적인 역할을 표현한다면 의미가 비교적 명확합니다.

## 상태를 가진 다중 상속

상태를 가진 기반 클래스들이 복잡하게 겹치면 문제가 커집니다.

예를 들어:

```text
      Base
     /    \
   Left  Right
     \    /
     Derived
```

`Left`와 `Right`가 각각 `Base`를 일반 상속하면 `Derived` 안에는 `Base` 부분이 두 개 존재할 수 있습니다.

그러면 다음 문제가 생깁니다.

- 어떤 `Base` subobject를 의미하는지 모호함
- 멤버 접근 경로가 복잡함
- 생성·소멸 순서가 복잡함
- 기반 pointer 변환이 모호할 수 있음

이를 흔히 다이아몬드 상속 문제라고 부릅니다.

## virtual inheritance

virtual inheritance를 사용하면 다이아몬드 구조에서 공통 기반 subobject를 하나만 공유하도록 설계할 수 있습니다.

예:

```cpp
class Left : virtual public Base {
};

class Right : virtual public Base {
};

class Derived :
    public Left,
    public Right {
};
```

하지만 virtual inheritance는 생성 책임과 객체 구조를 더 복잡하게 만듭니다.

따라서 단순히 기능을 조합하려는 목적이라면 먼저 composition으로 바꿀 수 있는지 확인합니다.

다중 상속과 virtual inheritance는 "사용할 수 있다"와 "사용해야 한다"가 같은 뜻이 아닙니다.

## 다형 객체의 수명은 별도 문제입니다

virtual dispatch가 잘 작동한다고 해서 객체 수명이 자동으로 안전해지는 것은 아닙니다.

예를 들어:

```cpp
Handler *handler = router.find("PUT");
```

이 pointer가 소유하지 않는 관찰 pointer라면 Router가 해당 handler를 삭제한 뒤에는 더 이상 사용할 수 없습니다.

즉:

```text
다형성
→ 어떤 구현을 호출할지 결정

소유권
→ 누가 객체를 삭제할지 결정

수명
→ pointer/reference를 언제까지 사용할 수 있는지 결정
```

서로 관련은 있지만 별개의 문제입니다.

## 자주 놓치는 문제

- 코드 재사용만을 위해 상속합니다.
- 기반 타입으로 대체 가능한 관계인지 확인하지 않습니다.
- 기반 소멸자가 virtual이 아닌데 기반 pointer로 파생 객체를 삭제합니다.
- pure virtual 함수가 있으면 소멸자도 자동으로 virtual이라고 생각합니다.
- 기반 함수와 파생 함수의 `const`, reference, 인자 타입이 달라 override되지 않습니다.
- 파생 객체에서 직접 호출만 테스트해 실제 override 실패를 놓칩니다.
- overload resolution과 virtual dispatch를 같은 개념으로 생각합니다.
- 파생 클래스의 같은 이름 함수가 기반 overload를 가리는 현상을 override 문제로 착각합니다.
- 다형 객체를 기반 타입 값으로 전달해 slicing이 발생합니다.
- 다형 객체를 값 container에 저장하려고 합니다.
- raw pointer container의 소유권을 문서화하지 않습니다.
- raw pointer container를 가진 Router의 compiler 기본 복사를 허용합니다.
- Router 등록 실패 뒤 이미 만든 handler를 정리하지 않습니다.
- 생성자 실패 시 Router 소멸자가 부분 등록 상태를 자동으로 정리할 것이라고 생각합니다.
- `clone()`이 raw pointer를 반환하면서 caller 소유 여부를 정하지 않습니다.
- 다중 상속으로 단순한 "사용한다" 관계까지 표현합니다.
- virtual dispatch가 객체 수명까지 보장한다고 생각합니다.

## 완료 기준

다음 항목을 설명하고 코드에서 적용할 수 있으면 이 범위의 목표를 달성한 것입니다.

- 상속을 코드 재사용이 아니라 기반 타입 대체 가능성을 기준으로 판단합니다.
- 정적 타입과 동적 타입의 차이를 설명합니다.
- overload resolution과 virtual dispatch를 구분합니다.
- C++98에서 `override`가 없기 때문에 signature를 직접 정확히 맞춰야 하는 이유를 설명합니다.
- 기반 pointer 또는 reference를 통한 테스트로 override와 virtual dispatch를 확인합니다.
- 기반 pointer로 파생 객체를 삭제할 때 virtual destructor가 필요한 이유를 설명합니다.
- protected non-virtual destructor를 사용할 수 있는 제한된 설계를 설명합니다.
- pure virtual function과 abstract class의 의미를 설명합니다.
- 다형 객체를 값으로 전달하거나 저장할 때 object slicing이 발생하는 이유를 설명합니다.
- 다형 객체를 pointer/reference로 다루고 그 수명을 별도로 관리합니다.
- 이름 가리기와 override 실패를 구분하고 `using Base::name;`의 역할을 설명합니다.
- raw pointer를 보유한 Router의 소유자, 삭제 위치, 등록 실패 정리를 설명합니다.
- Router 복사 시 pointer 주소만 복사하면 이중 삭제가 발생하는 이유를 설명합니다.
- C++98에서 복사를 금지하거나 `clone()`을 이용한 깊은 복사를 선택할 수 있습니다.
- `clone()` 반환 pointer의 소유권 계약을 명확히 정합니다.
- composition으로 표현할 수 있는 "사용한다" 관계와 상속 관계를 구분합니다.
- 다중 상속과 virtual inheritance가 객체 구조와 생성 규칙을 복잡하게 만들 수 있음을 설명합니다.
