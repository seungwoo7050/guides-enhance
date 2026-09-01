# 오류·optional·variant·expected

## 목표

실패를 전부 `false`, `nullptr`, 빈 문자열, 예외 하나로 처리하지 않습니다. 실패가 어떤 의미인지, caller가 복구할 수 있는지, 프로그램이 계속 정상 동작할 수 있는지에 따라 표현을 고릅니다.

특히 입력을 읽은 뒤 실제 상태를 변경하기까지 다음 질문을 구분해서 생각합니다.

- 입력 형식 자체가 잘못되었습니까?
- 형식은 맞지만 값이 허용 범위를 벗어났습니까?
- 현재 프로그램 상태와 충돌합니까?
- 외부 자원이나 실행 환경 때문에 실패했습니까?
- 프로그램 내부 불변식이 깨졌습니까?
- caller가 실패 종류에 따라 다른 행동을 해야 합니까?
- 실패 이후 기존 상태를 그대로 유지할 수 있습니까?

오류 표현의 목적은 단순히 실패 사실을 전달하는 것이 아니라, **caller가 다음 행동을 결정할 수 있을 만큼 정확한 의미를 전달하는 것**입니다.

---

## 실패 종류를 먼저 나눕니다

입력을 받아 상태를 변경하는 흐름은 다음처럼 여러 단계로 나눌 수 있습니다.

```text
외부 문자열
    ↓
문법 확인
    ↓
타입 변환
    ↓
값 범위 확인
    ↓
현재 상태와 충돌 확인
    ↓
필요한 자원 확보
    ↓
상태 변경
```

각 단계는 서로 다른 이유로 실패할 수 있습니다.

예를 들어 사용자에게 port 번호를 받아 등록한다고 가정합니다.

```text
"abc"
    → 숫자가 아님
    → parse 실패

"70000"
    → 숫자 형식은 맞음
    → 허용 범위를 벗어남
    → validation 실패

"8080"
    → 값 자체는 유효
    → 이미 사용 중
    → 현재 상태와 충돌

"8081"
    → 모든 검증 성공
    → 메모리 할당 또는 파일 작업 실패 가능
    → 실행 환경의 자원 문제
```

이 실패들을 모두 `false` 하나로 반환하면 caller는 무엇을 해야 할지 알 수 없습니다.

---

## parse 실패와 validation 실패를 구분합니다

두 실패는 모두 "입력이 잘못되었다"고 볼 수 있지만 의미가 다릅니다.

### parse 실패

입력을 원하는 타입으로 해석할 수 없습니다.

```text
"abc" → int 변환 불가
"1.2.3" → 올바른 IPv4 문법이 아님
```

### validation 실패

타입으로 변환은 되었지만 프로그램 규칙을 만족하지 않습니다.

```text
70000 → 정수이지만 port 범위 초과
-1    → 정수이지만 음수 금지
""    → string이지만 비어 있으면 안 됨
```

이 구분은 사용자에게 다른 오류 메시지를 제공하거나, 잘못된 입력이 어느 단계에서 발생했는지 테스트할 때 유용합니다.

---

## 상태 충돌은 입력 오류와 다릅니다

입력 자체는 완전히 유효하지만 현재 프로그램 상태 때문에 실패할 수 있습니다.

예:

```text
id = 42
↓
형식 정상
범위 정상
↓
이미 id 42가 존재
↓
Conflict
```

이 경우 사용자 입력 형식이 틀린 것이 아닙니다.

따라서 다음 두 오류를 같은 종류로 처리하지 않는 편이 좋습니다.

```text
InvalidInput
Conflict
```

caller가 각각 다른 응답을 해야 한다면 더욱 그렇습니다.

---

## 자원 실패와 programmer error

모든 실패가 정상적인 business-level 결과인 것도 아닙니다.

### 자원 또는 환경 실패

예:

- 메모리 할당 실패
- 파일을 열 수 없음
- socket 연결 실패
- 권한 부족
- disk full
- 외부 서비스 오류

이런 실패는 실행 환경이나 외부 자원 상태 때문에 발생합니다.

### programmer error

예:

- 함수 precondition 위반
- 내부 invariant가 깨짐
- 도달하면 안 되는 분기에 도달
- 이미 파괴된 객체 사용
- 배열 범위를 벗어나는 접근

이런 문제를 정상적인 사용자 오류와 같은 결과 타입으로 숨기면 버그를 발견하기 어려울 수 있습니다.

즉 다음 둘은 의미가 다릅니다.

```text
사용자가 잘못된 값을 입력함
≠
프로그램이 내부 규칙을 깨뜨림
```

---

## caller가 무엇을 해야 하는지 기준으로 표현을 고릅니다

실패 표현을 선택할 때는 "이 함수에서 어떤 일이 일어났는가"뿐 아니라 **caller가 무엇을 해야 하는가**도 중요합니다.

예를 들어 다음 세 함수는 서로 다른 의미를 가질 수 있습니다.

```cpp
std::optional<Task> find(TaskId id);
std::expected<Task, LoadError> load(TaskId id);
Task require(TaskId id);
```

가능한 의미는 다음과 같습니다.

```text
find()
    → 없음도 정상적인 조회 결과

load()
    → 성공 또는 구분 가능한 오류

require()
    → 실패하면 현재 작업을 정상적으로 계속할 수 없음
```

함수 이름만으로 모든 의미가 자동으로 결정되는 것은 아니지만, API 전체에서 일관된 규칙을 유지하는 것이 중요합니다.

---

## 예외와 결과 값

오류 처리에서 가장 중요한 선택 중 하나는 **결과 값으로 반환할 것인지, 예외를 사용할 것인지**입니다.

두 방식 중 하나가 항상 더 좋은 것은 아닙니다.

---

## 예상 가능한 분기는 값으로 반환하기 쉽습니다

caller가 흔히 예상하고 분기해야 하는 결과라면 값으로 표현하면 호출 지점에서 확인하기 쉽습니다.

```cpp
enum class SubmitError {
    stopped,
    queue_full,
    empty_name
};

Result<JobId, SubmitError> submit(Job job);
```

caller는 실패를 정상적인 제어 흐름으로 다룰 수 있습니다.

```cpp
auto result = submit(std::move(job));

if (!result) {
    switch (result.error()) {
    case SubmitError::stopped:
        // 서비스 종료 중
        break;

    case SubmitError::queue_full:
        // 나중에 재시도 가능
        break;

    case SubmitError::empty_name:
        // 입력 수정 필요
        break;
    }
}
```

이런 실패들은 모두 caller가 실제로 분기해서 처리할 수 있는 정상적인 결과입니다.

---

## 예외가 적합할 수 있는 경우

현재 함수가 정상적으로 결과를 만들 수 없고 실패를 여러 호출 단계를 거슬러 전달해야 한다면 예외가 자연스러울 수 있습니다.

예:

```cpp
Config load_config(const std::filesystem::path& path);
```

초기화 과정에서 다음과 같은 문제가 발생할 수 있습니다.

```text
파일 없음
읽기 실패
설정 문법 오류
필수 항목 누락
```

caller가 이런 실패를 하나의 초기화 실패 경계에서 처리한다면:

```cpp
try {
    Config config = load_config(path);
    run(config);
} catch (const ConfigError& e) {
    report(e);
    return EXIT_FAILURE;
}
```

예외가 여러 중간 함수를 따라 전달되는 코드를 단순하게 만들 수 있습니다.

---

## 예외는 "예상하지 못한 오류"와 같은 말이 아닙니다

"예상 가능한 실패는 결과 값, 예상하지 못한 실패는 예외"라고 단순하게 외우면 정확하지 않습니다.

예외를 사용할지 결과 값을 사용할지는 다음을 함께 봅니다.

```text
caller가 이 실패를 얼마나 자주 분기하는가?
실패가 정상적인 API 결과인가?
여러 호출 계층을 건너뛰어 전달해야 하는가?
해당 코드베이스의 오류 처리 정책은 무엇인가?
exception 사용이 허용되는 환경인가?
```

예를 들어 파일 없음은 충분히 예상 가능한 상황이지만, application 초기화 단계에서는 예외로 전달하는 설계가 자연스러울 수 있습니다.

반대로 queue full도 충분히 "오류"지만 caller가 자주 재시도해야 한다면 결과 값이 더 자연스럽습니다.

---

## `std::optional`

`std::optional<T>`는 **값이 있거나 없거나** 두 상태만 표현합니다.

```cpp
std::optional<Task> find(TaskId id) const;
```

사용:

```cpp
if (auto task = store.find(id)) {
    use(*task);
} else {
    // 없음
}
```

여기서 `nullopt`의 의미가 하나로 명확해야 합니다.

예:

```text
값 있음
값 없음
```

만 필요하다면 `optional`이 간결합니다.

---

## `optional`이 적합한 경우

대표적인 예는 검색입니다.

```cpp
std::optional<User> find_user(UserId id);
```

"그 사용자가 없다"는 것이 함수 실행 실패라기보다 정상적인 조회 결과일 수 있습니다.

또 다른 예:

```cpp
std::optional<int> parse_simple_integer(std::string_view text);
```

caller가 "변환 성공/실패"만 알고 싶고 실패 이유를 구분할 필요가 없다면 사용할 수 있습니다.

---

## `optional`이 부족한 경우

다음 실패가 모두 가능하다고 가정합니다.

```text
값 없음
권한 없음
연결 실패
데이터 손상
```

이를 모두:

```cpp
return std::nullopt;
```

로 처리하면 caller는 원인을 구분할 수 없습니다.

```cpp
auto result = load_user(id);

if (!result) {
    // 사용자가 없는 것인지
    // database 연결 실패인지
    // 권한 문제인지 알 수 없음
}
```

이 경우 `expected` 같은 value/error 타입이 더 적합할 수 있습니다.

---

## `optional<bool>`처럼 의미가 겹치는 타입은 주의합니다

다음 타입은 세 상태를 갖습니다.

```cpp
std::optional<bool>
```

```text
nullopt
false
true
```

세 상태 모두 실제 의미가 있다면 사용할 수 있습니다.

하지만 caller가 각각의 의미를 매번 기억해야 한다면 enum이 더 명확할 수 있습니다.

예:

```cpp
enum class Permission {
    unknown,
    denied,
    allowed
};
```

타입은 가능한 상태의 **의미를 이름으로 표현할 수 있는가**도 중요합니다.

---

## `std::variant`

`std::variant`는 가능한 여러 타입 중 정확히 하나를 보관합니다.

```cpp
using Message =
    std::variant<TextMessage, Ping, Disconnect>;
```

여기서는 세 타입이 모두 정상적인 message 종류입니다.

```text
TextMessage
Ping
Disconnect
```

즉 `variant`의 기본 목적은 성공/실패보다는 **여러 가능한 값 형태를 하나의 타입으로 표현하는 것**입니다.

---

## `std::visit`

`std::visit`을 사용하면 variant에 들어 있는 실제 타입에 따라 처리할 수 있습니다.

```cpp
std::visit(
    [](const auto& message) {
        handle(message);
    },
    msg
);
```

각 타입별로 다른 처리가 필요하면 overload helper 등을 사용할 수도 있습니다.

핵심은 `variant`가 가능한 타입 집합을 코드에 명시한다는 점입니다.

---

## 닫힌 종류의 값에 `variant`가 잘 맞습니다

가능한 경우의 수가 코드에서 정해져 있다면 `variant`가 자연스럽습니다.

예:

```cpp
using Command =
    std::variant<AddCommand, RemoveCommand, ListCommand>;
```

가능한 command 종류가 이 세 개로 닫혀 있습니다.

새 타입을 추가하면 `visit` 처리 부분에서 빠진 case를 compiler 도움으로 찾기 쉬워질 수 있습니다.

---

## 오류를 `variant`에 넣을 수도 있습니다

다음처럼 쓸 수 있습니다.

```cpp
using ParseResult =
    std::variant<Port, ParseError>;
```

기술적으로 문제는 없습니다.

하지만 코드 전체에서 계속 다음 패턴을 사용한다면:

```text
success value
or
error value
```

`expected<T, E>` 또는 별도 `Result<T, E>` 타입이 의미를 더 직접적으로 표현합니다.

즉:

```cpp
std::variant<Port, ParseError>
```

보다:

```cpp
std::expected<Port, ParseError>
```

가 "성공 또는 오류"라는 의도를 읽기 쉽습니다.

---

## `std::expected`

C++23의 `std::expected<T, E>`는 다음 두 상태 중 하나를 보관합니다.

```text
성공: T
실패: E
```

예:

```cpp
std::expected<Port, ParseError>
parse_port(std::string_view text);
```

사용:

```cpp
auto result = parse_port(text);

if (!result) {
    return report(result.error());
}

Port port = *result;
```

또는 성공 값을 명시적으로 얻을 수도 있습니다.

```cpp
Port port = result.value();
```

---

## `optional`과 `expected`의 차이

두 타입 모두 "항상 값이 있는 것은 아니다"라는 점은 비슷하지만 오류 정보의 유무가 다릅니다.

```text
optional<T>
    → T 또는 없음

expected<T, E>
    → T 또는 오류 E
```

예:

```cpp
std::optional<User> find_user(UserId id);
```

`nullopt`가 단순히 "없음"을 뜻하면 충분합니다.

반면:

```cpp
std::expected<User, LoadError>
load_user(UserId id);
```

에서는 실패 원인을 caller에게 전달할 수 있습니다.

---

## 성공 값이 필요 없는 `expected`

성공 시 별도의 값을 반환할 필요가 없고 오류만 구분하고 싶다면 C++23에서는 다음처럼 표현할 수 있습니다.

```cpp
std::expected<void, SaveError>
save(const Document& document);
```

사용:

```cpp
auto result = save(document);

if (!result) {
    handle(result.error());
}
```

이 방식은 `bool`보다 실패 원인을 명확하게 표현할 수 있습니다.

---

## C++20에서는 별도 `Result` 타입을 사용할 수 있습니다

`std::expected`는 C++23 표준 library 기능입니다.

C++20을 사용하는 프로젝트에서는 다음 선택이 가능합니다.

- 작은 프로젝트 전용 `Result<T, E>` 구현
- 검증된 third-party expected/result library
- 프로젝트의 기존 오류 타입 사용
- 상황에 따라 `variant<T, E>` 사용

중요한 것은 이름만 `Result`라고 만드는 것이 아니라 다음 의미를 명확히 유지하는 것입니다.

```text
성공 값 T
또는
오류 값 E
```

---

## 오류 타입은 caller의 결정을 지원해야 합니다

오류 타입에는 caller가 다음 행동을 결정하는 데 필요한 정보가 있어야 합니다.

예:

```cpp
enum class ParseError {
    empty,
    invalid_character,
    out_of_range
};
```

caller가 각각 다른 메시지를 제공할 수 있습니다.

```cpp
switch (error) {
case ParseError::empty:
    // 값 입력 요청
    break;

case ParseError::invalid_character:
    // 형식 오류 표시
    break;

case ParseError::out_of_range:
    // 허용 범위 표시
    break;
}
```

반대로 caller가 아무 행동도 달리 하지 않는 세부사항까지 error enum에 모두 노출하면 API가 불필요하게 복잡해질 수 있습니다.

---

## 오류 메시지와 오류 종류를 분리합니다

오류를 문자열만으로 표현하면 caller가 문자열 내용을 해석해야 하는 문제가 생길 수 있습니다.

나쁜 예:

```cpp
std::string error = "queue full";

if (error == "queue full") {
    // ...
}
```

문구가 바뀌면 제어 흐름까지 깨질 수 있습니다.

대신 제어 흐름은 안정된 오류 종류로 판단하고:

```cpp
enum class SubmitError {
    stopped,
    queue_full,
    empty_name
};
```

문자열은 사용자에게 보여 주거나 로그에 남기는 표현 계층에서 생성하는 편이 좋습니다.

---

## 내부 오류 정보와 외부 응답을 분리합니다

내부 오류 객체에는 디버깅에 필요한 상세 정보가 있을 수 있습니다.

예:

```text
filesystem path
system error code
internal component name
database detail
exception message
```

하지만 이를 protocol 응답이나 사용자 메시지에 그대로 노출하면 다음 문제가 생길 수 있습니다.

- 외부 API 형식이 내부 구현에 종속됩니다.
- 내부 경로나 민감 정보가 노출될 수 있습니다.
- compiler/library/platform에 따라 메시지가 달라질 수 있습니다.
- 테스트가 불안정한 문자열에 의존합니다.

따라서 내부 오류와 외부 표현을 경계에서 변환합니다.

---

## 상태를 바꾸기 전에 실패 가능한 작업을 끝냅니다

상태 변경 중 실패가 발생하면 객체가 어느 상태에 남는지가 중요합니다.

예:

```cpp
void Store::put(Key key, Value value) {
    if (contains(key))
        throw Conflict{};

    Entry candidate{std::move(key), std::move(value)};
    data_.insert(std::move(candidate));
}
```

여기서 먼저:

1. conflict를 검사하고
2. 새로운 `Entry`를 준비한 뒤
3. 실제 container에 반영합니다.

이런 구조는 실패했을 때 기존 상태를 유지하기 쉽게 만듭니다.

---

## 먼저 검증하고 나중에 상태를 바꿉니다

다음 코드는 위험할 수 있습니다.

```cpp
state.name = input.name;

if (!valid(input))
    return false;
```

검증에 실패해도 `state.name`은 이미 바뀌었습니다.

caller가 "실패했으니 기존 상태가 그대로일 것"이라고 기대한다면 문제가 됩니다.

대신 가능한 경우:

```cpp
if (!valid(input))
    return false;

state.name = input.name;
```

처럼 실패 가능한 검증을 먼저 끝냅니다.

---

## 여러 값을 바꿀 때 후보 상태를 만듭니다

여러 필드를 한꺼번에 수정해야 한다면 중간 상태가 외부에 보이지 않도록 candidate를 만들 수 있습니다.

```cpp
Config candidate = current;

apply(candidate, patch);
validate(candidate);

current.swap(candidate);
```

흐름은 다음과 같습니다.

```text
current
↓ 복사
candidate
↓ 수정
candidate
↓ 검증
candidate
↓ 성공하면 swap
current 갱신
```

`apply()`나 `validate()`에서 실패하면 원래 `current`는 그대로 남습니다.

이 방식은 strong exception guarantee를 제공하는 데 도움이 될 수 있습니다.

---

## 모든 연산을 복사 후 swap으로 만들 필요는 없습니다

candidate를 복사하는 비용이 매우 크거나 데이터 구조상 다른 방식이 더 자연스러울 수 있습니다.

중요한 것은 특정 패턴을 무조건 쓰는 것이 아니라:

```text
어느 연산이 실패할 수 있는가?
실패하면 현재 객체는 어떤 상태인가?
caller에게 어떤 보장을 제공할 것인가?
```

를 명확히 하는 것입니다.

---

## 예외 안전성 수준

예외가 발생했을 때 객체와 프로그램 상태에 대해 어떤 보장을 제공하는지 구분할 수 있습니다.

### no-throw guarantee

연산이 예외를 밖으로 내보내지 않습니다.

```text
호출
↓
예외가 caller까지 전달되지 않음
```

C++에서는 실제로 예외를 던지지 않는 함수에 `noexcept`를 사용할 수 있습니다.

```cpp
void swap(State& other) noexcept;
```

---

## strong guarantee

연산이 실패하면 호출 전 상태가 유지됩니다.

```text
호출 전 상태 A
↓
작업 시도
↓ 실패
상태 A 그대로
```

이를 transaction처럼 생각할 수 있습니다.

```text
성공 → 전체 반영
실패 → 아무 변화 없음
```

---

## basic guarantee

연산이 실패하더라도 객체는 **유효한 상태**로 남습니다.

하지만 값이 호출 전과 동일하다고 보장하지는 않습니다.

```text
호출 전 상태 A
↓
일부 변경
↓ 실패
상태 B
```

단, B도 클래스 불변식을 만족하고 안전하게 사용하거나 파괴할 수 있어야 합니다.

---

## 보장 없음

실패 이후 객체 상태에 대해 의미 있는 보장을 제공하지 못합니다.

이 수준은 가능한 한 피해야 하지만, 저수준 API나 특정 치명적 상황에서는 존재할 수 있습니다.

중요한 것은 caller가 실패 이후 객체를 계속 사용할 수 있는지 알아야 한다는 점입니다.

---

## 예외 안전성 표

| 수준 | 실패 후 상태 |
|---|---|
| no-throw | 예외가 밖으로 나오지 않음 |
| strong | 호출 전 상태 유지 |
| basic | 값은 바뀔 수 있으나 객체는 유효 |
| 보장 없음 | 객체 상태를 신뢰할 수 없음 |

모든 함수가 strong guarantee를 제공해야 하는 것은 아닙니다.

다만 중요한 상태 변경 API라면 어떤 수준을 제공하는지 코드와 테스트에서 확인할 수 있어야 합니다.

---

## 예외 안전성은 예외만을 위한 개념이 아닙니다

이 원칙은 `expected`나 오류 코드로 실패를 반환하는 코드에도 적용할 수 있습니다.

예:

```cpp
auto result = update(state, request);

if (!result) {
    // 실패했을 때 state는 원래 상태인가?
    // 일부 변경된 유효 상태인가?
}
```

즉 핵심 질문은 **실패가 발생한 뒤 상태가 어떻게 되는가**입니다.

---

## 상태 변경 API의 계약을 명확히 합니다

예를 들어 다음 API가 있다고 가정합니다.

```cpp
std::expected<void, UpdateError>
apply_patch(Config& config, const Patch& patch);
```

caller에게 다음 중 어느 보장을 제공하는지 정해야 합니다.

```text
실패하면 config는 변경되지 않는다
```

또는:

```text
실패해도 config는 유효하지만 일부 필드는 변경될 수 있다
```

둘 다 설계할 수 있지만 의미는 완전히 다릅니다.

---

## 외부 응답으로 바꾸는 위치

내부 오류 타입과 외부 문자열을 여러 계층에 섞지 않는 것이 좋습니다.

예:

```cpp
try {
    Response response = service.execute(request);
    write(format(response));
} catch (const ParseError&) {
    write("BAD_REQUEST\n");
} catch (const ConflictError&) {
    write("CONFLICT\n");
} catch (const std::exception&) {
    write("INTERNAL_ERROR\n");
}
```

이 경계에서는 내부 실패를 외부 protocol의 안정된 응답으로 변환합니다.

---

## 왜 경계에서 변환하는가

내부 service가 직접 다음 문자열을 반환한다고 가정합니다.

```text
"BAD_REQUEST\n"
"CONFLICT\n"
"INTERNAL_ERROR\n"
```

그러면 domain logic이 특정 protocol 형식에 종속됩니다.

반면 내부에서는 의미 있는 타입을 유지하고:

```text
ParseError
ConflictError
StorageError
```

외부 adapter에서:

```text
ParseError    → BAD_REQUEST
ConflictError → CONFLICT
StorageError  → INTERNAL_ERROR
```

처럼 변환하면 내부 규칙과 외부 표현을 독립적으로 변경하기 쉬워집니다.

---

## catch는 실제로 처리할 수 있는 범위에서 합니다

예외가 발생했다고 무조건 바로 catch하는 것이 좋은 것은 아닙니다.

다음처럼 catch한 뒤 아무것도 하지 않으면 실패를 숨깁니다.

```cpp
try {
    do_work();
} catch (...) {
    // 무시
}

return Success{};
```

caller는 작업이 성공했다고 오해할 수 있습니다.

예외를 catch한다면 다음 중 하나를 수행할 이유가 있어야 합니다.

- 복구
- 오류 타입 변환
- 로그 기록 후 다시 throw
- 외부 응답으로 변환
- 프로그램 종료 상태 결정

---

## catch한 뒤 다시 던질 때

현재 계층에서 로그만 남기고 같은 예외를 계속 전달해야 한다면:

```cpp
try {
    do_work();
} catch (const std::exception& e) {
    log(e.what());
    throw;
}
```

처럼 `throw;`를 사용할 수 있습니다.

현재 예외를 유지하지 않고 `throw e;`처럼 던지면 slicing이나 예외 객체 복사 문제가 생길 수 있으므로 단순 재전파에는 `throw;`가 적절합니다.

---

## 예외를 다른 오류 타입으로 바꿀 수 있습니다

저수준 library 예외를 그대로 외부에 노출하고 싶지 않다면 의미 있는 상위 오류로 바꿀 수 있습니다.

```cpp
try {
    repository.save(data);
} catch (const std::filesystem::filesystem_error& e) {
    throw StorageError{/* ... */};
}
```

이렇게 하면 상위 계층은 filesystem 세부사항을 몰라도 됩니다.

---

## `std::exception::what()`은 제어 흐름용 식별자가 아닙니다

다음과 같은 코드는 피합니다.

```cpp
catch (const std::exception& e) {
    if (std::string_view{e.what()} == "file not found") {
        // ...
    }
}
```

`what()` 문자열은 주로 사람이 읽는 진단용 정보입니다.

오류 종류에 따라 동작을 바꿔야 한다면:

- 예외 타입
- error enum
- `std::error_code`
- 별도 오류 객체

등 구조화된 정보를 사용합니다.

---

## `std::error_code`가 자연스러운 영역도 있습니다

OS나 filesystem처럼 이미 error code 체계를 사용하는 API에서는 `std::error_code`가 적절할 수 있습니다.

예를 들어 오류를 예외 대신 code로 받고 싶다면 표준 library의 일부 API는 `std::error_code&` overload를 제공합니다.

핵심은 모든 오류를 하나의 enum으로 재정의하는 것이 아니라, 현재 abstraction에 맞는 오류 표현을 선택하는 것입니다.

---

## 결과 타입과 예외를 섞을 때의 경계

하나의 프로그램 안에서 둘 다 사용할 수 있습니다.

예:

```text
parser
    → expected<Command, ParseError>

service
    → expected<Response, DomainError>

repository
    → filesystem exception 가능

application boundary
    → exception을 안정된 종료 상태/응답으로 변환
```

중요한 것은 임의로 섞는 것이 아니라 각 계층의 책임에 맞는 규칙을 갖는 것입니다.

---

## 오류를 너무 세밀하게 나누는 문제

오류 종류를 정확히 나누는 것이 중요하지만, caller가 구분할 필요가 없는 세부사항까지 모두 public API에 노출할 필요는 없습니다.

예를 들어 내부 parser에는:

```text
unexpected_token
missing_comma
invalid_escape
unterminated_string
```

같은 세부 오류가 있을 수 있습니다.

하지만 외부 protocol은 모두:

```text
BAD_REQUEST
```

로 처리할 수 있습니다.

즉 오류 타입의 세밀함은 **어느 계층에서 누가 사용하는가**에 따라 달라질 수 있습니다.

---

## 자주 놓치는 문제

### 오류 종류가 필요한데 `bool` 하나로 반환합니다

```cpp
bool submit(Job job);
```

caller가 실패 이유를 구분해야 한다면 정보가 부족합니다.

---

### 찾지 못함과 I/O 실패를 모두 `nullopt`로 반환합니다

```text
not found
permission denied
connection lost
```

가 모두 `nullopt`이면 caller가 올바르게 대응할 수 없습니다.

---

### 상태를 먼저 변경한 뒤 입력 전체를 검증합니다

실패 후 기존 상태가 보존되지 않을 수 있습니다.

가능하면 실패 가능한 검증과 candidate 생성을 먼저 수행합니다.

---

### catch-all에서 실패를 무시하고 성공을 반환합니다

실패가 사라져 상위 계층이 잘못된 상태를 정상으로 인식할 수 있습니다.

---

### 소멸자에서 예외를 던집니다

stack unwinding 중 추가 예외가 밖으로 나오면 `std::terminate()`가 호출될 수 있습니다.

정리 실패를 반드시 보고해야 한다면 별도 `close()`, `finish()`, `commit()` 같은 함수를 검토합니다.

---

### 내부 오류 문자열을 protocol 응답으로 그대로 내보냅니다

내부 구현과 외부 interface가 강하게 결합되고 민감한 정보가 노출될 수 있습니다.

---

### `variant`를 쓰면서 성공/오류 의미를 매번 수동으로 해석합니다

프로젝트 전반에서 항상 "T 또는 E" 패턴이라면 `expected`나 `Result`가 더 읽기 쉬울 수 있습니다.

---

### moved-from 값이나 부분 변경 상태를 오류 처리 중 잘못 사용합니다

오류 처리 경로에서도 객체 수명과 유효 상태 규칙은 그대로 적용됩니다.

---

## 어떤 표현을 선택할지 판단하는 방법

다음 질문을 순서대로 확인하면 도움이 됩니다.

```text
1. "값이 없음"만 표현하면 충분한가?
   └─ 예 → optional<T>

2. 여러 정상 값 종류 중 하나인가?
   └─ 예 → variant<A, B, ...>

3. 성공 값과 구분 가능한 오류가 필요한가?
   └─ 예 → expected<T, E> 또는 Result<T, E>

4. 실패를 여러 호출 계층을 건너 전달해야 하는가?
   └─ 예 → exception을 검토

5. programmer error인가?
   └─ 정상적인 사용자 오류와 섞지 말 것

6. 외부 API에 노출되는 오류인가?
   └─ 경계에서 안정된 외부 표현으로 변환
```

---

## 간단한 선택표

| 상황 | 고려할 표현 |
|---|---|
| 값이 있거나 없음 | `std::optional<T>` |
| 여러 정상 타입 중 하나 | `std::variant<...>` |
| 성공 값 또는 오류 값 | `std::expected<T, E>` / `Result<T, E>` |
| 여러 호출 계층을 건너가는 실패 | 예외 |
| OS/library 오류 코드 | `std::error_code` 등 |
| 내부 불변식 위반 | assertion, contract, bug 처리 정책 |

이 표는 절대 규칙이 아니라 의미를 판단하기 위한 출발점입니다.

---

## 테스트해야 할 것은 성공뿐만이 아닙니다

오류 처리 코드는 실패 경로를 테스트해야 의미가 있습니다.

예를 들어 `submit()`이 다음 오류를 반환한다면:

```cpp
enum class SubmitError {
    stopped,
    queue_full,
    empty_name
};
```

각 오류가 실제 조건에서 발생하는지 테스트합니다.

또 상태 변경 API라면 실패 뒤 상태도 확인합니다.

예:

```text
초기 state = A
↓
실패하는 update 호출
↓
오류 종류 확인
↓
state가 A 그대로인지 확인
```

이렇게 해야 strong guarantee가 실제로 유지되는지 확인할 수 있습니다.

---

## 예외 안전성 테스트 예시

strong guarantee를 의도한다면 다음 구조의 테스트를 생각할 수 있습니다.

```cpp
Config before = config;

try {
    apply_invalid_patch(config);
} catch (const ValidationError&) {
}

assert(config == before);
```

결과 타입을 사용하는 경우에도 마찬가지입니다.

```cpp
Config before = config;

auto result = apply_invalid_patch(config);

assert(!result);
assert(config == before);
```

즉 예외 안전성은 문서에만 적는 속성이 아니라 테스트 가능한 계약입니다.

---

## 완료 기준

이 문서를 학습한 뒤에는 다음을 설명하고 판단할 수 있어야 합니다.

- parse, validation, 상태 충돌, 외부 자원 실패, programmer error를 구분합니다.
- caller가 실패 종류에 따라 다른 행동을 해야 하는지 판단합니다.
- `std::optional<T>`를 값의 부재가 유일한 의미일 때 사용합니다.
- 여러 실패 이유를 `nullopt` 하나로 숨기지 않습니다.
- `std::variant`를 닫힌 여러 정상 값 종류를 표현하는 데 사용합니다.
- 반복되는 value/error 패턴에서는 `std::expected<T, E>` 또는 `Result<T, E>`를 검토합니다.
- C++23의 `std::expected`와 C++20에서 사용할 수 있는 대안을 구분합니다.
- 오류 문자열보다 구조화된 오류 타입으로 제어 흐름을 표현합니다.
- 결과 값과 예외를 caller의 복구 방식과 호출 계층에 따라 선택합니다.
- 예외를 단순히 "예상하지 못한 오류"라고만 정의하지 않습니다.
- 실패 가능한 검증과 candidate 준비를 실제 상태 변경보다 먼저 수행하는 이유를 설명합니다.
- no-throw, strong, basic, no-guarantee의 차이를 설명합니다.
- 결과 타입을 사용하는 코드에서도 실패 후 상태 보장이 중요함을 설명합니다.
- catch한 오류를 무시하고 성공으로 바꾸지 않습니다.
- 내부 오류 정보와 외부 protocol 응답을 경계에서 분리합니다.
- `what()` 문자열을 프로그램 제어 흐름의 식별자로 사용하지 않습니다.
- 함수가 제공하는 실패 의미와 예외 안전성 수준을 테스트로 확인합니다.
