# C++98 오류 처리·입력 검증·캐스트

## 목표

외부 문자열을 내부 값으로 바꾸기 전에 **입력 형식, 전체 소비 여부, 값 범위, 현재 상태와의 충돌**을 확인합니다. 검증이나 자원 준비가 실패한 요청이 기존 상태를 일부만 변경한 채 끝나지 않도록 상태 변경 순서를 설계합니다.

C++98에는 `std::optional`, `std::expected` 같은 결과 표현 타입이 없으므로 상황에 따라 다음 수단을 구분해서 사용합니다.

- 예외: 정상 흐름에서 처리하기 어려운 실패를 상위 계층으로 전달
- 반환값: 단순한 성공/실패나 조회 부재 표현
- 출력 매개변수: 성공했을 때 실제 값을 전달
- enum 또는 결과 구조체: 실패 종류가 여러 개인 경우 명시적으로 표현

오류 처리의 목표는 단순히 "에러를 잡는다"가 아니라 다음 조건을 만족하는 것입니다.

- 잘못된 입력을 정상 값으로 오해하지 않습니다.
- 실패 종류를 필요한 수준까지 구분합니다.
- 실패 후에도 기존 객체의 불변조건이 유지됩니다.
- 내부 오류 표현과 외부 protocol을 분리합니다.
- cast와 정수 연산이 값의 안전성을 자동으로 보장한다고 가정하지 않습니다.

## 입력 처리 순서

외부 요청을 처리할 때는 일반적으로 다음 순서를 따릅니다.

```text
문자열 분리
→ token 수 확인
→ 숫자·enum 변환
→ 값 범위 확인
→ 현재 상태와 충돌 확인
→ 필요한 새 값 준비
→ 상태 변경
```

앞 단계가 실패하면 뒤 단계로 진행하지 않습니다.

예를 들어 다음 입력이 있다고 가정합니다.

```text
PUT key value extra
```

`PUT`이 정확히 두 인자를 요구한다면 token 수 검사에서 즉시 실패해야 합니다. 이 시점에 이미 map에 값을 넣거나 file을 열거나 process를 시작해서는 안 됩니다.

다음 원칙을 유지합니다.

> 문법과 입력 값 검증이 끝나기 전에 외부에서 관찰 가능한 상태를 변경하지 않습니다.

다만 "현재 key가 이미 존재하는가"처럼 프로그램의 현재 상태를 알아야 하는 검증은 parser보다 Store 같은 상태 소유자가 담당하는 것이 자연스럽습니다.

## 문법 오류와 상태 오류를 구분합니다

다음 두 종류의 실패는 원인이 다릅니다.

### 문법 또는 입력 값 오류

예:

```text
PUT only-one-argument
LIMIT abc
LIMIT 999999999999999999999
```

이런 오류는 입력 자체가 요청 형식에 맞지 않는 경우입니다.

### 현재 상태와의 충돌

예:

```text
이미 존재하는 key를 새로 추가
capacity가 가득 찬 Store에 추가
존재하지 않는 항목을 삭제
```

입력 문법은 올바르지만 현재 프로그램 상태 때문에 수행할 수 없는 요청입니다.

둘을 같은 오류로 처리할 수도 있지만 내부에서는 원인을 구분해 두면 테스트와 외부 응답 매핑이 명확해집니다.

## 숫자 변환에서 `atoi()`를 피합니다

다음 코드는 입력 검증용으로 충분하지 않습니다.

```cpp
int value = std::atoi(text);
```

`atoi()`에는 다음 문제가 있습니다.

- 변환 실패와 정상 값 `0`을 구분하기 어렵습니다.
- 문자열 전체가 숫자인지 확인할 수 없습니다.
- 범위를 벗어난 입력의 처리에 의존하기 어렵습니다.

예를 들어 다음 두 입력이 모두 `0`처럼 보일 수 있습니다.

```text
"0"
"abc"
```

따라서 외부 입력 검증에는 `strtol()`과 end pointer를 사용하는 편이 적합합니다.

## `strtol()`로 정수 전체를 검증합니다

```cpp
#include <cerrno>
#include <climits>
#include <cstdlib>

int parseInt(const char *text)
{
    char *end = 0;
    errno = 0;

    const long value = std::strtol(text, &end, 10);

    if (errno == ERANGE
        || end == text
        || *end != '\0'
        || value < INT_MIN
        || value > INT_MAX) {
        throw ParseError("invalid integer");
    }

    return static_cast<int>(value);
}
```

각 조건의 의미를 구분해야 합니다.

### `errno == ERANGE`

```cpp
errno == ERANGE
```

입력 값이 `long`으로 표현할 수 있는 범위를 벗어난 경우를 검사합니다.

예를 들어 매우 큰 숫자 문자열은 `int` 범위를 검사하기도 전에 `long` 변환 단계에서 overflow 또는 underflow가 발생할 수 있습니다.

`strtol()` 호출 전에 반드시:

```cpp
errno = 0;
```

으로 초기화해야 합니다. 그렇지 않으면 이전 library 호출이 남긴 `errno` 값을 이번 변환 실패로 잘못 해석할 수 있습니다.

### `end == text`

```cpp
end == text
```

숫자로 변환된 문자가 하나도 없다는 뜻입니다.

예:

```text
"abc"
""
```

### `*end != '\0'`

```cpp
*end != '\0'
```

숫자로 변환된 부분 뒤에 아직 처리되지 않은 문자가 남았다는 뜻입니다.

예:

```text
"42x"
"10abc"
```

`strtol()`은 가능한 앞부분까지 변환하므로 `"42x"`에서 값 `42`를 얻을 수 있습니다. 그러나 전체 입력이 정수여야 하는 protocol이라면 이런 부분 성공을 허용하면 안 됩니다.

### `INT_MIN`, `INT_MAX`

`strtol()`의 결과 타입은 `long`입니다.

```cpp
const long value = std::strtol(...);
```

따라서 `long` 범위 안에는 있지만 `int` 범위 밖인 값이 존재할 수 있습니다.

```cpp
value < INT_MIN || value > INT_MAX
```

를 검사한 뒤에야 안전하게:

```cpp
static_cast<int>(value)
```

를 수행합니다.

cast 자체가 범위를 검사해 주는 것은 아닙니다.

## null input 여부도 계약에 포함합니다

`strtol()`에 넘기는 `text`는 유효한 null-terminated 문자열을 가리켜야 합니다.

따라서 `parseInt()`가 null pointer를 받을 수 있는 API라면 먼저 검사해야 합니다.

```cpp
if (text == 0)
    throw ParseError("missing integer");
```

반대로 caller가 항상 유효한 문자열 pointer를 전달한다는 계약이라면 그 전제를 함수 문서에서 명확히 합니다.

외부 입력을 다루는 함수에서는 "어떤 pointer가 유효하다고 가정하는가"도 입력 계약의 일부입니다.

## 공백 허용 규칙을 먼저 정합니다

`strtol()`은 숫자 앞의 공백을 건너뜁니다.

따라서:

```text
"   42"
```

도 정상 숫자로 변환될 수 있습니다.

반면 숫자 뒤의 공백은 end pointer에 남습니다.

예:

```text
"42 "
```

전체 소비 검사:

```cpp
*end != '\0'
```

를 사용하면 실패합니다.

따라서 protocol에서 다음 중 어떤 입력을 허용할지 먼저 정해야 합니다.

```text
"42"
" 42"
"42 "
" 42 "
```

parser가 이미 token 단위로 공백을 제거했다면 `parseInt()`는 token 내부에 공백이 없다는 전제를 가질 수 있습니다.

중요한 것은 `strtol()`의 기본 동작을 곧바로 protocol 규칙으로 착각하지 않는 것입니다.

## 부호 허용 여부도 별도 규칙입니다

`strtol()`은 다음과 같은 부호를 처리합니다.

```text
"+10"
"-10"
```

따라서 protocol에서 음수나 `+` 부호를 금지해야 한다면 변환 성공 여부만으로 충분하지 않습니다.

예를 들어 capacity처럼 음수를 허용하지 않는 값이라면 다음과 같이 의미 범위를 추가로 검사합니다.

```cpp
const int value = parseInt(text);

if (value < 0)
    throw ParseError("negative capacity");
```

즉, 다음 두 범위를 구분합니다.

```text
표현 가능한 타입 범위
→ int에 들어갈 수 있는가

도메인 범위
→ 이 값이 프로그램 규칙상 허용되는가
```

## enum 변환도 검증이 필요합니다

외부 정수나 문자열을 enum으로 바꿀 때는 정의된 값인지 확인해야 합니다.

예:

```cpp
struct Status {
    enum Value {
        Queued,
        Running,
        Done
    };
};
```

외부 숫자를 단순히 cast하면:

```cpp
Status::Value status =
    static_cast<Status::Value>(input);
```

`input`이 실제로 정의된 enumerator인지 보장되지 않습니다.

따라서 먼저 검증합니다.

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

문자열 입력도 같은 원칙입니다.

```text
"queued"  → Status::Queued
"running" → Status::Running
"done"    → Status::Done
그 외      → ParseError
```

cast는 입력 검증을 대신하지 않습니다.

## 실패를 타입으로 구분합니다

예외를 사용할 때 모든 실패를 같은 `std::runtime_error` 하나로 던지면 상위 계층에서 원인을 구분하기 어렵습니다.

예를 들어 다음처럼 오류 종류를 타입으로 나눌 수 있습니다.

```cpp
class ParseError : public std::runtime_error {
public:
    explicit ParseError(const std::string &message)
        : std::runtime_error(message)
    {
    }
};

class ConflictError : public std::runtime_error {
public:
    explicit ConflictError(const std::string &message)
        : std::runtime_error(message)
    {
    }
};

class StoreFullError : public std::runtime_error {
public:
    explicit StoreFullError(const std::string &message)
        : std::runtime_error(message)
    {
    }
};
```

그러면 최상위 계층은 예외 종류를 안정된 외부 응답으로 바꿀 수 있습니다.

```cpp
try {
    processRequest();
}
catch (const ParseError &) {
    std::cout << "BAD_REQUEST\n";
}
catch (const ConflictError &) {
    std::cout << "CONFLICT\n";
}
catch (const StoreFullError &) {
    std::cout << "STORE_FULL\n";
}
```

## 내부 예외 메시지를 protocol로 사용하지 않습니다

다음 방식은 피합니다.

```cpp
catch (const std::exception &e) {
    std::cout << e.what() << "\n";
}
```

`what()` 메시지는 내부 진단용 문자열일 수 있습니다.

예:

```text
duplicate key: /tmp/store.db line 42
```

이를 그대로 외부 protocol로 사용하면 다음 문제가 생깁니다.

- 내부 파일 경로나 구현 정보가 노출될 수 있습니다.
- 단순한 문구 수정이 protocol 변경이 됩니다.
- 테스트가 사람이 읽는 오류 문구에 과도하게 의존합니다.
- 서로 다른 내부 오류가 우연히 같은 문구를 사용할 수 있습니다.

외부 protocol은 안정된 코드나 formatter를 통해 별도로 만듭니다.

예:

```text
ConflictError
→ Response::Conflict
→ "CONFLICT"
```

내부 진단 메시지와 외부 사용자 메시지는 역할이 다릅니다.

## 예외를 언제 사용하고 반환값을 언제 사용할지

모든 실패에 예외를 사용할 필요는 없습니다.

예를 들어 key 조회에서 "없음"이 정상적인 결과 중 하나라면 반환값이 더 단순할 수 있습니다.

```cpp
bool Store::get(
    const std::string &key,
    std::string &value) const;
```

계약:

```text
true
→ key가 존재하며 value에 결과를 기록함

false
→ key가 존재하지 않으며 value는 사용하지 않음
```

이 경우 "값 없음"은 비정상적인 실행 실패라기보다 정상적인 조회 결과입니다.

반면 다음과 같은 상황은 예외로 표현할 수 있습니다.

- parser가 유효한 Request를 만들 수 없음
- Store의 불변조건을 위반하는 삽입 요청
- memory allocation 실패처럼 현재 함수가 복구할 수 없는 문제

중요한 것은 한 API 안에서 성공/실패 의미를 일관되게 유지하는 것입니다.

## 출력 매개변수의 계약을 명확히 합니다

C++98에는 `std::optional`이 없으므로 다음 형태를 사용할 수 있습니다.

```cpp
bool Store::get(
    const std::string &key,
    std::string &value) const;
```

호출 측:

```cpp
std::string value;

if (store.get(key, value)) {
    // value 사용 가능
} else {
    // value를 결과로 사용하지 않음
}
```

여기서 `false`를 반환할 때 `value`를 변경하지 않는다고 보장할지, 임의의 값이 남을 수 있다고 할지 계약을 정해야 합니다.

가능하면 실패 시 출력 매개변수를 변경하지 않는 규칙이 호출자에게 더 단순할 수 있습니다.

예:

```cpp
bool Store::get(
    const std::string &key,
    std::string &value) const
{
    std::map<std::string, TextBuffer>::const_iterator it =
        data_.find(key);

    if (it == data_.end())
        return false;

    value = it->second.str();
    return true;
}
```

단, `value = ...` 대입 자체가 실패할 수 있는 타입이라면 그 예외 의미도 별도로 고려해야 합니다.

## 실패 종류가 둘 이상이면 `bool`만으로 부족할 수 있습니다

다음 함수가 여러 실패를 구분해야 한다고 가정합니다.

```text
성공
없음
권한 없음
형식 오류
```

단순 `bool`은 두 상태만 표현할 수 있습니다.

C++98에서는 enum을 사용할 수 있습니다.

```cpp
struct LookupResult {
    enum Code {
        Found,
        NotFound,
        Invalid
    };
};
```

또는 결과 구조체를 만들 수 있습니다.

```cpp
struct LookupResult {
    enum Code {
        Found,
        NotFound,
        Invalid
    };

    Code code;
    std::string value;
};
```

이처럼 오류 종류가 많아질수록 "반환값 하나에 모든 의미를 억지로 넣지 않는가"를 확인합니다.

## 상태 변경 전 검증

다음 Store 연산을 생각해 봅니다.

```cpp
void Store::putNew(
    const std::string &key,
    const std::string &value)
{
    if (data_.find(key) != data_.end())
        throw ConflictError("key already exists");

    if (data_.size() >= capacity_)
        throw StoreFullError("store is full");

    TextBuffer owned(value.c_str());

    data_.insert(
        std::make_pair(key, owned));
}
```

중요한 점은 상태를 실제로 바꾸기 전에 실패 가능한 검증과 값 준비를 먼저 수행한다는 것입니다.

실행 순서:

```text
중복 확인
→ capacity 확인
→ 새 값 생성
→ map 삽입
```

앞 단계에서 실패하면 기존 `data_`는 변경되지 않습니다.

## "검증이 끝났다"와 "상태 변경이 실패하지 않는다"는 다릅니다

모든 논리 검증을 끝냈더라도 실제 상태 변경 연산 자체가 실패할 수 있습니다.

예를 들어:

```cpp
data_.insert(...)
```

는 내부 node memory allocation이나 key/value 복사 중 예외가 발생할 수 있습니다.

따라서 다음과 같이 생각해야 합니다.

```text
검증 완료
≠
이후 모든 작업이 반드시 성공
```

container가 제공하는 예외 보장과 저장되는 타입의 복사 동작이 함께 안전해야 합니다.

`std::map::insert`가 실패했을 때 기존 container 상태가 어떤 조건으로 유지되는지와, `TextBuffer` 복사 생성자가 실패했을 때 자원 누수가 없는지까지 함께 봅니다.

## 중복 삽입 결과도 확인합니다

`std::map::insert()`는 중복 key가 있으면 예외를 던지는 대신 삽입하지 않고 결과값으로 알려 줍니다.

따라서 중복 여부를 미리 검사했더라도 경쟁 없는 단일 스레드 코드에서는 논리적으로 충분할 수 있지만, `insert()`의 실제 성공 여부를 확인해야 하는 구조라면 반환값을 사용합니다.

```cpp
std::pair<
    std::map<std::string, TextBuffer>::iterator,
    bool
> result =
    data_.insert(std::make_pair(key, owned));

if (!result.second)
    throw ConflictError("key already exists");
```

중요한 점은 "예외가 없었다"와 "원하는 상태 변경이 실제로 일어났다"를 항상 같은 뜻으로 취급하지 않는 것입니다.

## 여러 필드를 바꿀 때 partial update를 피합니다

다음과 같은 상태가 있다고 가정합니다.

```cpp
class Record {
private:
    std::string name_;
    TextBuffer data_;
    int version_;
};
```

업데이트 중:

```text
name_ 변경 성공
data_ 변경 중 예외
version_은 아직 변경 전
```

이 되면 객체가 이전 상태도 새 상태도 아닌 중간 상태가 될 수 있습니다.

이런 경우 새 상태 전체를 별도 후보 객체에 먼저 구성한 뒤 마지막에 교체할 수 있습니다.

개념적으로:

```cpp
Record candidate(*this);

candidate.setName(newName);
candidate.setData(newData);
candidate.setVersion(newVersion);

swap(candidate);
```

또는 업데이트에 필요한 새 멤버 값들을 지역 변수로 먼저 준비하고 마지막에 실패하지 않는 연산으로 현재 객체에 반영합니다.

핵심 원칙은 다음과 같습니다.

> 실패할 수 있는 준비를 먼저 끝내고, 기존 상태 변경은 가능한 한 마지막에 수행합니다.

## 강한 예외 보장과 기본 예외 보장

예외 안전성을 이해할 때 두 수준을 구분하면 도움이 됩니다.

### 강한 보장

연산이 실패하면 객체 상태가 호출 전과 동일하게 유지됩니다.

```text
성공
→ 새 상태

실패
→ 이전 상태 그대로
```

copy-and-swap 같은 방식이 이 목표에 자주 사용됩니다.

### 기본 보장

연산이 실패해도 객체의 불변조건은 유지되지만 값이 일부 변경될 수 있습니다.

```text
실패
→ 객체는 여전히 유효하지만 이전 값과 같다는 보장은 없음
```

모든 함수가 반드시 강한 보장을 제공해야 하는 것은 아닙니다. 하지만 함수가 어떤 보장을 제공하는지 알아야 실패 후 객체를 계속 사용할 수 있는지 판단할 수 있습니다.

## 예외가 지나가는 범위

자원을 객체 소멸자가 정리하도록 설계하면 모든 함수에서 예외를 잡을 필요가 없습니다.

예를 들어:

```text
parser
→ ParseError

Store
→ ConflictError
→ StoreFullError

상위 실행 루프
→ 외부 Response로 변환
```

중간 함수가 복구 방법도 없는데 단순히 예외를 잡았다가 다시 던지는 코드는 불필요할 수 있습니다.

예:

```cpp
try {
    store.putNew(key, value);
}
catch (...) {
    throw;
}
```

추가 정리나 의미 변환이 없다면 이 catch는 가치가 거의 없습니다.

## 예외는 복구하거나 의미를 바꿀 수 있는 위치에서 잡습니다

catch를 둘 이유는 보통 다음 중 하나입니다.

- 현재 scope에서 직접 복구할 수 있음
- 현재 scope가 소유한 raw resource를 정리해야 함
- 내부 예외를 상위 계층용 오류 타입으로 변환
- 최상위에서 외부 응답 또는 종료 코드로 변환

예:

```cpp
try {
    Request request = parser.parse(line);
    Response response = service.execute(request);
    write(formatter.format(response));
}
catch (const ParseError &) {
    write("BAD_REQUEST\n");
}
```

이 위치는 parser 내부 예외를 외부 protocol로 바꿀 책임이 있으므로 catch가 의미 있습니다.

## `catch (...)`의 한계

다음 코드는 모든 예외를 잡습니다.

```cpp
catch (...) {
    // ...
}
```

하지만 모든 오류를 같은 방식으로 처리해야 한다는 뜻은 아닙니다.

특히 다음은 위험합니다.

```cpp
catch (...) {
    std::cout << "OK\n";
}
```

실패를 성공으로 숨깁니다.

또한 예외가 발생한 뒤 객체가 어떤 상태인지 확인하지 않고 반복문을 계속 돌면 손상된 상태를 재사용할 수 있습니다.

`catch (...)`가 필요한 경우에도 다음을 분명히 해야 합니다.

- 무엇을 정리하는가
- 오류를 다시 던지는가
- 현재 객체가 계속 사용 가능한가
- 외부에는 어떤 실패로 보이는가

## 소멸자와 예외

자원을 관리하는 객체의 소멸자는 stack unwinding 중에도 호출될 수 있습니다.

예:

```cpp
void process()
{
    TextBuffer buffer("abc");
    parser.parse(...); // 예외 발생 가능
}
```

`parser.parse()`가 예외를 던져도 이미 정상 생성된 `buffer`는 scope를 빠져나가며 소멸됩니다.

이것이 자원을 객체 수명에 묶는 중요한 이유입니다.

반면 생성자가 아직 완료되지 않은 객체 자체의 소멸자는 호출되지 않습니다. 따라서 생성자 본문에서 직접 얻은 raw resource는 별도의 예외 안전성 설계가 필요합니다.

## `static_cast`

`static_cast`는 compile-time에 허용되는 명시적 변환에 사용합니다.

대표적인 사용 예:

```cpp
long value = 42;

if (value < INT_MIN || value > INT_MAX)
    throw ParseError("out of range");

int converted = static_cast<int>(value);
```

여기서 안전성을 보장하는 것은 `static_cast`가 아니라 **앞의 범위 검사**입니다.

`static_cast`는 다음을 자동으로 검사하지 않습니다.

- 정수 overflow
- 값의 도메인 유효성
- pointer가 실제로 특정 파생 객체를 가리키는지
- 객체 수명

## `static_cast`와 상속 변환

파생 pointer에서 기반 pointer로 올라가는 upcast는 보통 명시적 cast 없이도 가능합니다.

```cpp
Derived *derived = new Derived;
Base *base = derived;
```

명시적으로 쓰면:

```cpp
Base *base = static_cast<Base *>(derived);
```

도 가능합니다.

반대로 기반 pointer를 파생 pointer로 내리는 downcast에 `static_cast`를 사용하면 실제 객체 타입을 실행 중 검사하지 않습니다.

```cpp
Derived *derived =
    static_cast<Derived *>(base);
```

`base`가 실제로 `Derived` 객체를 가리키는지 확실하지 않다면 `dynamic_cast`가 적절합니다.

## `dynamic_cast`

`dynamic_cast`는 다형 클래스 계층에서 실행 중 실제 객체 타입을 확인할 때 사용합니다.

예:

```cpp
class Base {
public:
    virtual ~Base() {}
};

class Derived : public Base {
};
```

```cpp
Derived *derived =
    dynamic_cast<Derived *>(base);

if (derived == 0)
    return false;
```

일반적인 downcast에서 source 기반 타입은 다형 타입이어야 합니다. 즉, 적어도 하나의 virtual function을 가져야 합니다.

virtual destructor 하나만 있어도 다형 타입이 됩니다.

### pointer cast 실패

```cpp
Derived *derived =
    dynamic_cast<Derived *>(base);
```

실제 객체가 호환되는 `Derived` 타입이 아니라면 결과는 `0`입니다.

따라서 pointer cast는 결과를 검사합니다.

```cpp
if (derived == 0) {
    // 타입 불일치
}
```

### reference cast 실패

```cpp
Derived &derived =
    dynamic_cast<Derived &>(base);
```

reference는 null 상태를 표현할 수 없으므로 실패하면 `std::bad_cast` 예외가 발생합니다.

필요한 헤더:

```cpp
#include <typeinfo>
```

## `dynamic_cast`는 소유권을 바꾸지 않습니다

다음 코드를 생각해 봅니다.

```cpp
Base *base = getObject();

Derived *derived =
    dynamic_cast<Derived *>(base);
```

cast에 성공해도 새 객체가 생성되는 것이 아닙니다.

```text
base
   \
    +----> 같은 객체
   /
derived
```

두 pointer는 같은 실제 객체를 가리킵니다.

따라서 `dynamic_cast` 성공 여부와 "누가 객체를 delete해야 하는가"는 별개의 문제입니다.

cast가 소유권을 이전하거나 수명을 연장해 주지 않습니다.

## `const_cast`

`const_cast`는 `const` 또는 `volatile` 한정자를 추가하거나 제거하는 데 사용합니다.

예:

```cpp
const char *text = "hello";

char *mutableText =
    const_cast<char *>(text);
```

하지만 cast가 가능하다는 사실이 실제 수정이 안전하다는 뜻은 아닙니다.

원래 객체가 실제로 const라면 이를 수정하려는 동작은 정의되지 않은 동작이 될 수 있습니다.

예:

```cpp
const int value = 10;

int *p =
    const_cast<int *>(&value);

// *p = 20; // 안전하다고 보장할 수 없음
```

## 오래된 C API와 `const_cast`

오래된 C API가 실제로 문자열을 수정하지 않지만 signature에 `const`가 빠져 있을 수 있습니다.

예:

```cpp
void legacy_api(char *text);
```

호출자가 실제로 수정되지 않는다는 API 계약을 확실히 알고 있을 때:

```cpp
legacy_api(
    const_cast<char *>(text.c_str()));
```

같은 코드가 필요할 수 있습니다.

하지만 반드시 API 문서를 확인해야 합니다.

API가 실제로 buffer를 수정한다면 `std::string::c_str()`이 제공한 읽기 전용 문자열 storage를 넘겨서는 안 됩니다.

`const_cast`는 잘못된 API 계약을 안전하게 만들어 주는 기능이 아닙니다.

## `reinterpret_cast`

`reinterpret_cast`는 타입 사이의 저수준 표현 변환에 사용됩니다.

예:

```cpp
SomeHeader *header =
    reinterpret_cast<SomeHeader *>(buffer);
```

이 코드가 compile된다고 해서 다음이 자동으로 보장되지는 않습니다.

- `buffer` 주소가 `SomeHeader`에 필요한 정렬을 만족함
- 해당 위치에 실제 `SomeHeader` 객체가 존재함
- 읽으려는 byte 수가 충분함
- 객체 수명이 유효함
- platform의 byte order나 padding이 원하는 형식과 같음

즉, `reinterpret_cast`는 주소 표현을 바꾸는 도구이지 실제 객체를 새 타입으로 생성하는 기능이 아닙니다.

## socket 주소 변환

POSIX socket API에서는 서로 다른 socket address 구조체를 `sockaddr *` 형태로 전달해야 하는 경우가 있습니다.

예:

```cpp
struct sockaddr_in address;

::bind(
    fd,
    reinterpret_cast<struct sockaddr *>(&address),
    sizeof(address));
```

이런 API는 원래 C 스타일의 generic address interface를 사용하므로 low-level cast가 필요할 수 있습니다.

하지만 이런 특정 API 요구와 일반적인 객체 타입 변환을 혼동하지 않습니다.

`reinterpret_cast`는 가능한 범위를 좁혀서 사용합니다.

## 네 가지 cast의 역할 요약

```text
static_cast
→ 일반적인 명시적 타입 변환
→ 값 범위나 실제 동적 타입을 자동 검증하지 않음

dynamic_cast
→ 다형 클래스 계층의 실제 타입 검사
→ pointer 실패는 0, reference 실패는 std::bad_cast

const_cast
→ const/volatile 한정자 변경
→ 원래 const 객체 수정의 안전성을 보장하지 않음

reinterpret_cast
→ 저수준 표현/주소 재해석
→ 정렬·실제 타입·수명·크기를 보장하지 않음
```

cast를 선택할 때는 "compiler가 허용하는가"보다 "어떤 전제를 내가 직접 보장해야 하는가"를 봅니다.

## signed integer overflow

C++에서 signed integer overflow는 정의되지 않은 동작입니다.

예:

```cpp
int result = left + right;
```

`left + right`가 `int` 범위를 벗어나면 결과를 단순히 wraparound한다고 가정하면 안 됩니다.

따라서 overflow가 일어나기 **전에** 검사해야 합니다.

## 덧셈 overflow 검사

양수 방향:

```cpp
if (right > 0
    && left > INT_MAX - right) {
    throw ArithmeticError("overflow");
}
```

음수 방향도 필요합니다.

```cpp
if (right < 0
    && left < INT_MIN - right) {
    throw ArithmeticError("underflow");
}
```

그 뒤에야 계산합니다.

```cpp
const int result = left + right;
```

중요한 점은 검사 표현 자체도 overflow를 일으키지 않아야 한다는 것입니다.

위 식에서 `INT_MAX - right`는 `right > 0`일 때 안전하고, `INT_MIN - right`는 `right < 0`일 때 안전하게 범위를 검사할 수 있도록 조건을 나눕니다.

## "계산한 뒤 검사"는 늦습니다

다음 방식은 잘못된 접근입니다.

```cpp
int result = left + right;

if (result < left)
    throw ArithmeticError("overflow");
```

이미 첫 줄에서 signed overflow가 발생했다면 프로그램 동작 자체가 정의되지 않았으므로 그 뒤 결과를 검사해 복구할 수 있다고 가정하면 안 됩니다.

항상:

```text
범위 검사
→ 계산
```

순서를 사용합니다.

## 더 넓은 타입 사용의 조건

더 넓은 타입이 실제로 목표 연산 범위를 모두 표현할 수 있다면 그 타입에서 먼저 계산할 수도 있습니다.

예:

```cpp
long result =
    static_cast<long>(left)
    + static_cast<long>(right);

if (result < INT_MIN || result > INT_MAX)
    throw ArithmeticError("overflow");
```

하지만 이 방법은 현재 platform에서 `long`이 필요한 범위를 충분히 넓게 표현한다는 전제가 있어야 합니다.

`long`이 `int`보다 반드시 더 넓은 비트 수를 가진다고 임의로 가정해서는 안 됩니다. 표준이 보장하는 타입 범위 관계와 실제 목표 범위를 확인해야 합니다.

범용 코드에서는 연산별 사전 검사가 더 명확할 수 있습니다.

## 뺄셈과 곱셈은 별도 검사가 필요합니다

뺄셈은 단순히:

```cpp
left + (-right)
```

로 바꾸어 검사하려 하면 `right == INT_MIN`일 때 `-right` 자체가 overflow할 수 있습니다.

따라서 연산 자체에 맞는 범위 검사를 작성해야 합니다.

곱셈도 부호 조합과 0, `INT_MIN`, `-1` 같은 경계 때문에 더 복잡합니다.

예를 들어:

```text
INT_MIN * -1
```

은 `int`로 표현할 수 없습니다.

따라서 "덧셈 검사를 하나 만들었으니 모든 연산에 재사용할 수 있다"고 생각하면 안 됩니다.

입력 범위와 실제 수행할 연산을 분리해서 검사합니다.

## 실패 테스트를 경계값으로 작성합니다

입력 검증과 overflow 코드는 정상값만 테스트하면 실수를 찾기 어렵습니다.

정수 parser라면 최소한 다음 종류를 테스트합니다.

```text
"0"
"1"
"-1"
INT_MAX 문자열
INT_MIN 문자열
INT_MAX보다 큰 값
INT_MIN보다 작은 값
""
"abc"
"42x"
" 42"
"42 "
```

protocol이 어떤 입력을 허용하는지에 따라 예상 결과를 명확히 정합니다.

overflow 연산은 다음 경계를 직접 테스트합니다.

```text
INT_MAX + 0
INT_MAX + 1
INT_MIN - 0
INT_MIN - 1
큰 양수 × 큰 양수
INT_MIN × -1
```

실패 테스트가 실제 코드 경계를 재현해야 검사 코드가 올바른지 확인할 수 있습니다.

## partial update도 테스트합니다

여러 단계로 상태를 바꾸는 함수는 중간 실패를 의도적으로 발생시켜 봅니다.

예를 들어:

```text
1. 첫 필드 준비 성공
2. 두 번째 값 복사에서 예외
3. 기존 객체 상태 확인
```

테스트에서는 다음을 확인합니다.

- key 개수가 바뀌지 않았는가
- 기존 값이 그대로인가
- 새 자원이 leak되지 않았는가
- 객체 불변조건이 유지되는가

정상 경로 테스트만으로는 exception safety를 확인할 수 없습니다.

## 자주 놓치는 문제

- `atoi()` 결과 `0`을 정상 입력 `"0"`과 변환 실패 모두에 사용합니다.
- `errno`를 0으로 초기화하지 않고 `strtol()` 결과를 검사합니다.
- `strtol()`이 숫자의 앞부분만 읽었는데 전체 입력이 유효하다고 판단합니다.
- `long` 변환 성공만 확인하고 `int` 범위를 별도로 검사하지 않습니다.
- `static_cast<int>`가 범위를 자동으로 검사한다고 생각합니다.
- `strtol()`이 선행 공백이나 부호를 허용한다는 점을 protocol 규칙과 구분하지 않습니다.
- enum으로 cast하면 정의된 enumerator인지 자동으로 확인된다고 생각합니다.
- map을 먼저 수정하고 중복·용량 검사를 나중에 수행합니다.
- 논리 검증이 끝났으니 container 삽입은 실패하지 않는다고 생각합니다.
- 여러 멤버를 순서대로 변경하다 중간 예외가 나도 이전 상태로 자동 복구될 것이라고 생각합니다.
- 모든 예외를 `catch (...)`로 잡고 성공 응답이나 계속 실행으로 바꿉니다.
- 내부 `what()` 문자열을 그대로 외부 protocol로 사용합니다.
- `dynamic_cast` 성공이 객체 소유권 이전을 뜻한다고 생각합니다.
- `const_cast`로 const를 제거하면 원래 const 객체도 안전하게 수정할 수 있다고 생각합니다.
- `reinterpret_cast`가 해당 주소에 실제 새 타입 객체를 만들어 준다고 생각합니다.
- signed overflow가 항상 2의 보수 wraparound를 한다고 가정합니다.
- overflow가 발생한 뒤 결과를 검사해 복구하려고 합니다.
- 덧셈 overflow 검사 하나를 뺄셈과 곱셈에 그대로 적용합니다.

## 완료 기준

다음 항목을 설명하고 코드에서 적용할 수 있으면 이 범위의 목표를 달성한 것입니다.

- 입력을 상태 변경 전에 전체적으로 검증합니다.
- token 수, 숫자 변환, 타입 범위, 도메인 범위, 현재 상태 충돌을 구분합니다.
- `strtol()`에서 `errno`, end pointer, 전체 소비 여부와 목표 타입 범위를 확인합니다.
- 공백과 부호 허용 여부를 library 기본 동작과 별개의 protocol 규칙으로 정의합니다.
- 외부 정수나 문자열을 enum으로 바꿀 때 정의된 값인지 검증합니다.
- 문법 오류, 상태 충돌, 용량 부족과 내부 실패를 필요한 수준까지 구분합니다.
- 내부 예외 메시지와 외부 protocol 응답을 분리합니다.
- 조회 부재처럼 정상적인 대안 결과는 반환값과 출력 매개변수로 표현할 수 있습니다.
- 실패 종류가 여러 개라면 enum 또는 별도 결과 타입을 사용합니다.
- 실패 가능한 준비를 실제 상태 변경 전에 수행합니다.
- 여러 필드를 갱신할 때 partial update를 피하도록 후보 상태나 swap을 사용합니다.
- 예외를 복구하거나 의미를 바꿀 수 있는 위치에서만 catch합니다.
- `static_cast`, `dynamic_cast`, `const_cast`, `reinterpret_cast`의 목적과 각각이 보장하지 않는 것을 설명합니다.
- `dynamic_cast`의 pointer 실패와 reference 실패를 구분합니다.
- signed integer overflow가 정의되지 않은 동작임을 설명하고 계산 전에 범위를 검사합니다.
- 입력 경계값, overflow, 부분 상태 변경 실패를 실제 테스트로 재현합니다.
