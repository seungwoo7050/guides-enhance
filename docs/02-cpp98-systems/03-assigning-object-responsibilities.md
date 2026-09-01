# C++98 객체에 역할 나누기

## 목표

하나의 `main()`에 입력 해석, 데이터 저장, 명령 실행, 출력 형식을 모두 넣지 않습니다. 프로그램을 나눌 때의 목표는 클래스 수를 늘리는 것이 아니라, **실제 상태를 누가 보유하는지**, **어떤 함수가 어떤 상태를 바꾸는지**, **어떤 이유로 코드가 변경되는지**를 찾기 쉽게 만드는 것입니다.

특히 줄 단위 명령 프로그램에서는 다음 경계를 분명히 하면 구조를 이해하고 테스트하기 쉬워집니다.

- 외부 문자열을 내부 요청 구조로 바꾸는 책임
- 프로그램의 실제 상태를 보유하고 변경하는 책임
- 요청을 어떤 연산으로 실행할지 결정하는 책임
- 내부 결과를 외부 출력 문자열로 바꾸는 책임
- 객체를 생성하고 수명을 연결하는 책임

이 문서에서는 각각을 `RequestParser`, `Store`, handler, `ResponseFormatter`, `main()` 같은 역할로 설명합니다. 이름은 프로젝트에 따라 달라도 되지만 책임의 경계는 명확해야 합니다.

## 먼저 동작을 분해합니다

줄 단위 명령 프로그램을 예로 들면 다음 작업이 있습니다.

```text
한 줄 읽기
→ 명령과 인자로 분리
→ 명령 이름과 인자 수 확인
→ 필요한 타입 변환
→ 저장소 조회 또는 변경
→ 결과 값 만들기
→ 문자열로 출력
```

이 목록을 그대로 클래스 목록으로 바꾸는 것이 목표는 아닙니다.

예를 들어 "명령과 인자로 분리"와 "인자 수 확인"이 항상 함께 바뀌고 같은 테스트로 검증된다면 하나의 parser가 담당해도 됩니다. 반대로 저장 규칙과 출력 형식은 서로 다른 이유로 바뀌므로 분리하는 편이 좋습니다.

역할을 나눌 때는 다음 질문을 먼저 봅니다.

- 이 작업은 어떤 상태를 알아야 합니까?
- 이 작업은 어떤 상태를 변경합니까?
- 실패했을 때 어떤 정보가 필요합니까?
- 다른 작업과 별도로 테스트할 이유가 있습니까?
- 입력 형식이 바뀌었을 때 함께 바뀌어야 합니까?
- 저장 규칙이 바뀌었을 때 함께 바뀌어야 합니까?

서로 다른 이유로 변경되는 작업을 분리하면 한 기능을 수정할 때 영향을 받는 코드 범위가 줄어듭니다.

## Request와 Response

외부에서 읽은 문자열을 저장소 함수에 그대로 전달하지 않습니다.

예를 들어 다음과 같은 내부 요청 타입을 둘 수 있습니다.

```cpp
struct Request {
    std::string command;
    std::vector<std::string> arguments;
};
```

`Request`는 "외부 문자열을 해석한 뒤 프로그램 내부에서 사용할 명령 표현"입니다.

parser가 다음 입력을 받았다고 가정합니다.

```text
PUT name alice
```

parser는 이를 다음과 같은 내부 값으로 바꿀 수 있습니다.

```text
command   = "PUT"
arguments = ["name", "alice"]
```

이렇게 하면 `Store`나 handler는 원래 입력 줄에 공백이 몇 개 있었는지, token을 어떤 규칙으로 나눴는지 알 필요가 없습니다.

즉, 외부 문자열 형식과 내부 상태 연산 사이에 `Request`라는 경계를 둡니다.

### Request는 가능한 한 검증된 상태로 넘깁니다

handler가 받을 때마다 다시 인자 수를 확인하게 만들면 각 handler가 parser 규칙을 중복해서 알아야 합니다.

예를 들어 `PUT` 명령이 정확히 두 인자를 가져야 한다면 parser 또는 명령 검증 단계에서 이를 확인한 뒤 handler를 호출합니다.

그러면 handler는 다음 전제를 가질 수 있습니다.

```text
PutHandler::handle()가 호출되었다면
- request.command는 PUT에 해당한다.
- arguments에는 필요한 두 값이 있다.
- parser가 담당하기로 한 문법 검증은 이미 끝났다.
```

이 전제가 명확하면 handler 코드가 단순해지고 테스트 조건도 줄어듭니다.

다만 parser가 모든 의미 검증을 담당한다는 뜻은 아닙니다. 예를 들어 "이 key가 이미 Store에 존재하는가"는 입력 문법이 아니라 저장 상태에 관한 규칙이므로 `Store` 또는 상태 연산 쪽에서 확인하는 것이 자연스럽습니다.

## Response

실행 결과도 처음부터 출력 문자열로 만들지 않습니다.

```cpp
struct Response {
    enum Code {
        Ok,
        Value,
        NotFound,
        Error
    };

    Code code;
    std::string value;
};
```

handler는 내부 결과를 `Response`로 만들고 formatter가 이를 외부 문자열로 변환합니다.

예를 들어:

```text
Response::Ok
→ "OK\n"

Response::Value + "alice"
→ "VALUE alice\n"

Response::NotFound
→ "NOT_FOUND\n"
```

이렇게 분리하면 출력 protocol이 바뀌어도 저장 규칙이나 명령 실행 코드는 그대로 둘 수 있습니다.

예를 들어 출력 형식이 다음처럼 바뀌더라도:

```text
OK
```

에서

```text
200 OK
```

로 바뀌는 것은 formatter의 책임입니다.

### Response는 내부 의미를 표현합니다

`Response`의 `code`는 단순한 출력 문자열 축약이 아니라 프로그램 내부에서 결과 의미를 구분하는 값입니다.

예를 들어:

- `Ok`: 성공했지만 별도 값은 없음
- `Value`: 성공했고 반환할 값이 있음
- `NotFound`: 요청 대상이 없음
- `Error`: 일반 오류

formatter는 이 의미를 외부 표현으로 바꿉니다.

즉, handler가 `"404 NOT FOUND"` 같은 외부 문자열을 직접 만들기 시작하면 내부 의미와 외부 protocol이 다시 결합됩니다.

## 상태는 한 곳에서 보유합니다

실제 데이터 상태는 가능하면 하나의 타입이 직접 소유하도록 합니다.

```cpp
class Store {
public:
    void putNew(const std::string &key,
                const std::string &value);

    bool get(const std::string &key,
             std::string &value) const;

private:
    std::map<std::string, TextBuffer> data_;
};
```

여기서 `Store`는 단순히 `std::map`을 감싸는 이름이 아니라 **저장 규칙의 소유자**입니다.

예를 들어 다음 규칙이 있다면 `Store`가 일관되게 적용해야 합니다.

- 최대 저장 개수
- 중복 key 허용 여부
- key 검증
- 값 저장 방식
- 삭제 규칙
- 조회 규칙

handler가 `data_`를 직접 수정하게 두면 명령마다 저장 규칙 적용 순서가 달라질 수 있습니다.

예를 들어 한 handler는 capacity를 먼저 검사하고, 다른 handler는 값을 먼저 넣은 뒤 검사할 수 있습니다. 그러면 동일한 저장 규칙이 여러 곳에 흩어집니다.

따라서 다음처럼 저장 연산을 `Store` 메서드로 모읍니다.

```cpp
store.putNew(key, value);
```

handler는 "새 값을 저장한다"는 의도만 표현하고, 구체적인 저장 규칙은 `Store`가 책임집니다.

## Store의 불변조건

상태를 한 곳에 모으는 이유 중 하나는 **불변조건(invariant)** 을 한 타입이 책임지게 하기 위해서입니다.

예를 들어 `Store`가 다음 조건을 항상 유지해야 한다고 정할 수 있습니다.

```text
- 저장된 원소 수는 capacity를 넘지 않는다.
- 같은 key는 두 번 존재하지 않는다.
- data_ 안의 각 TextBuffer는 유효한 값 상태다.
```

이 조건이 있다면 `Store`의 public 함수는 호출 전후에 이 조건을 깨뜨리지 않아야 합니다.

예를 들어 `putNew`는 다음 순서를 가질 수 있습니다.

```text
1. capacity 확인
2. 중복 key 확인
3. 새 값 준비
4. 삽입
```

중간 단계에서 예외가 발생해도 `Store`의 기존 상태가 깨지지 않도록 설계합니다.

handler가 `std::map`을 직접 조작하면 이런 불변조건을 모든 handler가 각각 알아야 하므로 유지가 어려워집니다.

## parser가 하는 일

parser의 책임은 외부 입력 문자열을 내부 요청 표현으로 바꾸는 것입니다.

보통 다음과 같은 작업이 포함될 수 있습니다.

- 입력 줄 token 분리
- command 이름 해석
- command 지원 여부 확인
- 인자 수 확인
- 숫자 문자열을 정수로 변환
- enum 문자열을 내부 enum 값으로 변환
- 문법적으로 잘못된 입력 거부

예를 들어:

```text
LIMIT 10
```

이라는 명령이 있고 두 번째 token이 정수여야 한다면 parser는 `"10"`을 정수 타입으로 변환하는 책임을 가질 수 있습니다.

이때 단순히 문자열 `"10"`을 handler에 넘긴 뒤 handler마다 다시 `strtol`을 호출하게 만들지 않는 것이 좋습니다.

다만 실제 `Request` 구조는 프로젝트의 명령 종류에 맞게 정해야 합니다. 모든 인자를 항상 `std::string`으로만 보관한다면 타입 변환 시점을 handler로 미룬 설계가 됩니다. 반대로 parser에서 숫자와 enum을 이미 검증하려면 명령별 request 타입이나 별도 필드가 더 적절할 수 있습니다.

핵심은 **어느 계층에서 어떤 검증을 끝낸다고 정했는지 일관되게 유지하는 것**입니다.

## parser가 하지 않는 일

parser는 외부 문자열을 유효한 내부 요청으로 바꾸는 데 집중합니다.

따라서 보통 다음과 같은 상태 연산은 parser가 직접 하지 않습니다.

- 저장소 조회
- 값 삽입
- 값 삭제
- capacity 변경
- handler 실행
- stdout 출력

parser가 입력 검증 중 저장소를 수정하면 문법 오류가 난 입력도 side effect를 만들 위험이 있습니다.

예를 들어 다음 잘못된 흐름은 피합니다.

```text
첫 번째 token 해석
→ Store 일부 변경
→ 두 번째 token 검사
→ 문법 오류 발견
```

이 경우 최종적으로 요청은 실패했지만 Store는 이미 바뀌었습니다.

대신 다음 흐름을 사용합니다.

```text
전체 입력 검증
→ Request 완성
→ 실행 단계로 전달
```

즉, **문법 확인이 끝나기 전에 프로그램 상태를 변경하지 않는다**는 경계를 둡니다.

## 문법 검증과 상태 검증을 구분합니다

모든 검증을 parser에 몰아넣는 것도 좋지 않습니다.

예를 들어:

```text
PUT name alice
```

에서 다음은 parser가 확인할 수 있습니다.

- `PUT`이 알려진 명령인가
- 인자가 두 개인가
- token 형식이 올바른가

하지만 다음은 `Store`의 현재 상태를 알아야 판단할 수 있습니다.

- `name`이라는 key가 이미 존재하는가
- capacity가 남아 있는가

이런 규칙은 입력 문법이 아니라 상태 규칙입니다.

따라서 일반적으로 다음처럼 나눌 수 있습니다.

```text
parser
  → 문자열·문법 검증

handler
  → 요청을 상태 연산으로 연결

Store
  → 현재 상태에 의존하는 규칙 검증과 실제 변경
```

이 구분을 지키면 parser가 Store에 의존하지 않아도 됩니다.

## handler가 하는 일

handler는 검증된 요청을 실제 상태 연산으로 연결합니다.

```cpp
Response PutHandler::handle(const Request &request,
                            Store &store) const
{
    store.putNew(request.arguments[0],
                 request.arguments[1]);

    return Response(Response::Ok);
}
```

handler는 "이 명령이 Store에 어떤 연산을 요청하는가"를 표현합니다.

예를 들어:

```text
PUT
→ Store::putNew()

GET
→ Store::get()

DELETE
→ Store::remove()
```

handler는 보통 다음을 하지 않습니다.

- 원시 입력 줄 다시 parsing
- command 이름 재선택
- stdout 직접 출력
- Store의 private container 직접 수정

이렇게 하면 handler 테스트는 입력 문자열 처리와 출력 형식에서 독립될 수 있습니다.

## handler는 Store 규칙을 복제하지 않습니다

다음과 같은 중복은 피합니다.

```cpp
if (store.size() >= store.capacity())
    throw FullError();

store.putNew(key, value);
```

만약 `Store::putNew()`도 capacity를 확인한다면 같은 규칙이 두 곳에 존재합니다.

반대로 `Store::putNew()`는 아무 검사 없이 삽입하고 handler만 capacity를 확인한다면, 다른 호출자가 `putNew()`를 사용할 때 규칙을 우회할 수 있습니다.

저장 규칙이 `Store`의 불변조건이라면 `Store` 자체가 책임지는 것이 안전합니다.

handler는 그 규칙을 직접 구현하기보다 결과를 적절한 `Response`로 변환하는 역할에 집중합니다.

## Router의 역할

여러 명령 handler가 있다면 명령 이름에 맞는 handler를 고르는 책임을 별도 Router가 가질 수 있습니다.

개념적으로 다음과 같습니다.

```text
Request.command
    |
    v
 Router
    |
    +--> PutHandler
    +--> GetHandler
    +--> DeleteHandler
```

handler 내부에서 다시 긴 `if` 체인으로 명령을 선택하면 Router를 둔 의미가 사라집니다.

예를 들어 `PutHandler` 안에서 다음과 같은 코드는 피합니다.

```cpp
if (request.command == "PUT") {
    // ...
} else if (request.command == "GET") {
    // ...
}
```

각 handler는 자신이 맡은 명령만 처리하도록 합니다.

## Router가 상태를 소유할 필요는 없습니다

Router의 핵심 책임이 "명령 이름 → handler 선택"이라면 Store의 데이터를 직접 소유하거나 수정할 필요는 없습니다.

예를 들어:

```cpp
const Handler *Router::find(
    const std::string &command) const;
```

처럼 handler 선택만 수행할 수 있습니다.

Store 변경은 선택된 handler가 `Store &`를 받아 수행합니다.

이렇게 하면 Router가 명령 등록과 상태 저장이라는 서로 다른 책임을 동시에 갖는 것을 피할 수 있습니다.

## 조립 위치

`main()`은 프로그램의 세부 로직을 모두 구현하는 곳이 아니라, 객체를 만들고 서로 연결하는 **조립 위치(composition root)** 로 사용할 수 있습니다.

예를 들어:

```cpp
Store store(capacity);
Router router;
RequestParser parser;
ResponseFormatter formatter;
```

이 선언만 봐도 프로그램의 주요 객체와 생성 순서를 확인할 수 있습니다.

반복문은 개념적으로 다음 흐름을 연결합니다.

```text
read
→ parse
→ route
→ handle
→ format
→ write
```

각 단계의 책임이 분리되어 있다면 `main()`은 orchestration만 담당합니다.

예를 들어 의사 코드는 다음과 같습니다.

```cpp
while (readLine(line)) {
    try {
        Request request = parser.parse(line);

        const Handler *handler =
            router.find(request.command);

        Response response =
            handler->handle(request, store);

        write(formatter.format(response));
    } catch (const ParseError &e) {
        write(formatter.formatParseError(e));
    }
}
```

실제 예외 구조와 반환 타입은 프로젝트 규칙에 맞게 달라질 수 있지만, 핵심은 각 단계가 서로의 내부 구현을 직접 알지 않아도 된다는 점입니다.

## 예외를 외부 응답으로 바꾸는 위치

내부 코드가 예외를 사용한다면 어느 계층에서 외부 응답으로 바꿀지 정해야 합니다.

예를 들어 `Store::putNew()`가 다음 예외를 던진다고 가정합니다.

```text
DuplicateKey
StoreFull
```

이 예외를 `Store` 내부에서 바로 문자열로 출력하면 Store가 출력 protocol까지 알아야 합니다.

대신 상위 실행 흐름에서 예외를 잡아 `Response`로 바꿀 수 있습니다.

```text
StoreFull
→ Response::Error
→ formatter
→ "STORE_FULL\n"
```

이렇게 하면 내부 오류 모델과 외부 문자열 형식을 분리할 수 있습니다.

어디에서 예외를 `Response`로 바꿀지는 프로젝트마다 다를 수 있지만, 최소한 Store나 parser가 stdout을 직접 쓰지 않게 하면 테스트가 단순해집니다.

## 출력은 formatter가 담당합니다

formatter는 내부 결과를 외부 문자열로 변환합니다.

```cpp
std::string ResponseFormatter::format(
    const Response &response) const;
```

예를 들어:

```cpp
switch (response.code) {
    case Response::Ok:
        return "OK";
    case Response::Value:
        return "VALUE " + response.value;
    case Response::NotFound:
        return "NOT_FOUND";
    case Response::Error:
        return "ERROR";
}
```

formatter는 저장소를 조회하거나 command를 실행하지 않습니다.

이렇게 하면 단위 테스트도 다음처럼 분리할 수 있습니다.

```text
Store test
→ 저장 규칙 검증

Parser test
→ 문자열 → Request 검증

Handler test
→ Request + Store → Response 검증

Formatter test
→ Response → 문자열 검증
```

stdout 캡처 없이 각 계층을 직접 검사할 수 있습니다.

## 클래스 수를 늘리는 것이 목표가 아닙니다

역할 분리의 목적은 모든 동작을 클래스로 만드는 것이 아닙니다.

분리한 타입이 실제로 하는 일이 거의 없고 별도의 변경 이유도 없다면 합치는 편이 더 이해하기 쉬울 수 있습니다.

다음 질문으로 판단합니다.

- 독립적으로 지켜야 하는 상태가 있습니까?
- 다른 부분과 별도로 테스트할 실패가 있습니까?
- 입력 형식 변경과 데이터 규칙 변경이 같은 파일을 건드립니까?
- 이 타입을 사용하는 호출자가 둘 이상입니까?
- 생성과 소멸 순서를 별도로 관리해야 합니까?
- 이 역할이 다른 역할의 private 구현을 너무 많이 알아야 합니까?
- 분리했을 때 의존성이 줄어듭니까, 아니면 전달 코드만 늘어납니까?

예를 들어 stateless formatter가 함수 하나뿐이라면 반드시 클래스로 만들 필요는 없습니다.

```cpp
std::string formatResponse(const Response &response);
```

이렇게 일반 함수로 두어도 책임 분리는 유지됩니다.

중요한 것은 "클래스인가 함수인가"보다 "변경 이유와 상태 책임이 분리되어 있는가"입니다.

## 너무 큰 Manager를 피합니다

다음과 같은 클래스는 처음에는 편해 보여도 책임이 빠르게 섞일 수 있습니다.

```text
ApplicationManager
  - parse input
  - modify store
  - open network
  - write log
  - format output
```

이런 타입은 모든 기능이 한곳을 통해 연결되므로 다음 문제가 생깁니다.

- 작은 변경에도 큰 클래스가 수정됩니다.
- 단위 테스트가 많은 의존성을 필요로 합니다.
- 어떤 상태를 누가 소유하는지 불분명해집니다.
- 수명과 초기화 순서가 복잡해집니다.

"Manager"라는 이름 자체가 문제는 아니지만, 하나의 타입이 서로 다른 변경 이유를 지나치게 많이 가지는지 확인해야 합니다.

## 의존성을 숨기지 않습니다

전역 변수나 singleton으로 필요한 객체를 숨기기보다 생성자나 함수 인자로 전달합니다.

```cpp
class CommandService {
public:
    explicit CommandService(Store &store)
        : store_(store)
    {
    }

private:
    Store &store_;
};
```

이 코드는 `CommandService`가 `Store`를 필요로 한다는 사실을 타입 선언에서 바로 보여 줍니다.

반대로 전역 Store를 내부에서 임의로 참조하면 호출자는 이 의존성을 코드만 보고 알기 어렵습니다.

명시적 의존성은 테스트할 때도 유리합니다. 테스트에서 별도의 Store를 만들어 주입할 수 있기 때문입니다.

## 참조 멤버와 수명

참조 멤버는 자신이 가리키는 객체를 소유하지 않습니다.

```cpp
class CommandService {
public:
    explicit CommandService(Store &store)
        : store_(store)
    {
    }

private:
    Store &store_;
};
```

따라서 `store_`가 유효하려면 원래 `Store` 객체가 `CommandService`보다 오래 살아야 합니다.

다음 생성 순서는 자연스럽습니다.

```cpp
Store store(capacity);
CommandService service(store);
```

지역 객체는 보통 생성의 역순으로 파괴되므로:

```text
생성:
Store
→ CommandService

파괴:
CommandService
→ Store
```

가 되어 `CommandService`가 살아 있는 동안 `Store`도 살아 있습니다.

반대로 참조 대상이 먼저 사라지면 `store_`는 dangling reference가 됩니다.

이 수명 조건은 참조 타입 자체가 자동으로 보장해 주는 것이 아닙니다. 조립 위치에서 객체 생성 순서와 scope를 올바르게 구성해야 합니다.

## 생성 순서와 선언 순서를 구분합니다

한 클래스 내부의 멤버 객체 초기화 순서는 생성자 initializer list에 적은 순서가 아니라 **클래스에 멤버가 선언된 순서**를 따릅니다.

예를 들어:

```cpp
class Application {
private:
    Store store_;
    CommandService service_;

public:
    Application()
        : service_(store_),
          store_(100)
    {
    }
};
```

initializer list에는 `service_`가 먼저 보이지만 실제 초기화 순서는 선언 순서 때문에:

```text
store_
→ service_
```

입니다.

혼동을 피하려면 initializer list도 멤버 선언 순서와 맞추는 것이 좋습니다.

```cpp
Application()
    : store_(100),
      service_(store_)
{
}
```

의존 객체의 수명 관계가 중요한 C++98 코드에서는 이 규칙을 알고 있어야 합니다.

## 전역 singleton이 숨기는 것

전역 singleton을 사용하면 호출 코드에서 의존성이 짧아질 수 있지만 다음 정보가 숨겨질 수 있습니다.

- 어떤 함수가 Store에 의존하는가
- 객체 초기화 순서는 무엇인가
- 프로그램 종료 시 파괴 순서는 무엇인가
- 테스트에서 별도 상태로 교체할 수 있는가

특히 여러 번역 단위에 전역 객체가 있을 때 초기화 순서를 서로 의존하게 만들면 이해와 유지보수가 어려워집니다.

이 문서의 범위에서는 전역 상태를 기본 선택으로 두기보다 `main()` 같은 조립 위치에서 객체를 만들고 필요한 곳에 명시적으로 전달하는 방식을 우선합니다.

## 역할 사이 계약을 문장으로 적어 봅니다

각 타입의 책임을 짧은 문장으로 설명할 수 있으면 구조가 명확한지 확인하기 쉽습니다.

예를 들어:

```text
RequestParser:
외부 입력 문자열을 검증된 Request로 변환한다.
프로그램 상태는 변경하지 않는다.

Router:
Request의 command에 대응하는 Handler를 선택한다.

Handler:
검증된 Request를 Store 연산으로 연결하고 Response를 만든다.

Store:
실제 데이터를 소유하고 저장 규칙과 불변조건을 유지한다.

ResponseFormatter:
Response를 외부 출력 문자열로 변환한다.

main:
객체를 생성하고 수명을 보장하며 전체 실행 흐름을 연결한다.
```

한 타입의 설명에 `그리고`, `또한`, `뿐만 아니라`가 계속 붙는다면 책임이 너무 많이 섞였는지 검토할 수 있습니다.

## 자주 놓치는 문제

- parser가 입력 검증 중 Store까지 변경합니다.
- parser가 Store 상태에 의존하는 규칙까지 모두 판단하려고 합니다.
- handler가 인자 수와 원시 문자열 parsing을 다시 수행합니다.
- handler가 직접 출력해 단위 테스트가 stdout 캡처에 의존합니다.
- handler마다 capacity, 중복 key 같은 Store 규칙을 따로 검사합니다.
- 여러 클래스가 같은 `std::map`을 직접 수정합니다.
- Router가 명령 선택뿐 아니라 실제 데이터까지 직접 소유합니다.
- `Manager` 하나가 parser, store, network, logging, formatter를 모두 가집니다.
- 타입을 많이 나눴지만 모든 함수가 다른 타입의 private 상태를 알아야 합니다.
- 분리를 했지만 의존성이 줄지 않고 단순 전달 코드만 크게 늘어납니다.
- 참조 멤버가 참조 대상의 수명을 자동으로 연장한다고 생각합니다.
- 멤버 초기화 순서가 initializer list에 적은 순서라고 생각합니다.
- 전역 singleton으로 의존성과 소멸 순서를 숨깁니다.
- 내부 오류를 Store나 parser가 직접 외부 문자열로 출력합니다.
- `Response`가 내부 의미가 아니라 단순한 출력 문자열 보관소가 됩니다.

## 완료 기준

다음 항목을 설명하고 코드에서 적용할 수 있으면 이 범위의 목표를 달성한 것입니다.

- 입력 해석과 상태 변경이 다른 함수나 타입에서 일어납니다.
- 외부 문자열을 내부 `Request` 표현으로 바꾸는 경계를 설명합니다.
- parser가 담당하는 문법 검증과 Store가 담당하는 상태 검증을 구분합니다.
- 데이터를 직접 보유하는 타입이 하나로 정해져 있습니다.
- Store의 불변조건을 문장으로 설명할 수 있습니다.
- handler는 검증된 요청만 받고 저장 규칙을 중복 구현하지 않습니다.
- Router는 명령 선택 책임과 실제 상태 저장 책임을 구분합니다.
- handler가 내부 `Response`를 만들고 formatter가 외부 문자열을 만듭니다.
- 출력 형식 변경이 저장소 구현을 건드리지 않습니다.
- `main()`이 객체를 생성하고 `parse → route → handle → format → write` 흐름을 연결합니다.
- 내부 예외를 어느 계층에서 외부 응답으로 바꾸는지 정해져 있습니다.
- 전역 상태 대신 생성자나 함수 인자로 의존성을 드러냅니다.
- 참조 멤버를 사용할 때 참조 대상이 더 오래 살아야 하는 이유를 설명합니다.
- 멤버 초기화 순서가 선언 순서를 따른다는 사실을 이해합니다.
- 각 타입을 별도 테스트할 구체적인 이유가 있습니다.
- 클래스 수가 아니라 책임, 상태, 변경 이유를 기준으로 분리합니다.
