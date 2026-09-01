# C++98 STL로 문제 풀기

## 사용 시점

이 문서는 선행 필수가 아닙니다. 실제 프로젝트에서 다음과 같은 판단이 필요할 때 참고합니다.

- 어떤 container가 문제의 연산에 가장 잘 맞는지 결정하기 어렵습니다.
- `find`, `lower_bound`, `upper_bound` 중 무엇을 써야 하는지 헷갈립니다.
- 입력 검증과 상태 변경의 순서를 안전하게 구성해야 합니다.
- 정렬 결과가 실행마다 또는 구현마다 달라지지 않게 만들고 싶습니다.
- 실패한 입력이 기존 상태를 일부만 변경하지 않게 해야 합니다.
- 이론적인 복잡도와 실제 실행 비용을 함께 판단해야 합니다.

핵심은 container 이름부터 고르는 것이 아니라 **문제에서 실제로 필요한 연산과 실패 조건을 먼저 적는 것**입니다.

## 연산을 먼저 적습니다

예를 들어 날짜별 값을 저장하고, 기준 날짜 이하에서 가장 가까운 값을 찾는 문제를 생각합니다.

필요한 연산은 다음과 같습니다.

```text
날짜 key로 정렬해 저장
중복 날짜 거부
주어진 날짜보다 큰 첫 원소 찾기
그 원소의 직전 값 사용
```

이 요구에는 정렬된 key를 유지하고 경계 검색을 제공하는 `std::map`이 잘 맞습니다.

```cpp
typedef std::map<Date, double> RateMap;

RateMap::const_iterator found =
    rates.upper_bound(date);

if (found == rates.begin())
    throw NoEarlierValue();

--found;
return found->second;
```

`upper_bound(date)`는 **`date`보다 큰 첫 key**를 가리킵니다.

따라서 그 직전 원소는 다음 조건을 만족하는 가장 큰 key입니다.

```text
key <= date
```

정확히 같은 날짜가 존재해도 올바르게 동작합니다.

예를 들어 key가 다음과 같다면:

```text
2026-01-01
2026-01-10
2026-01-20
```

기준 날짜가 `2026-01-10`일 때:

```text
upper_bound("2026-01-10")
→ "2026-01-20"
```

이므로 한 칸 뒤로 이동하면 정확히 `2026-01-10`을 얻습니다.

## `upper_bound()`의 경계를 먼저 검사합니다

다음 순서는 위험합니다.

```cpp
RateMap::const_iterator found =
    rates.upper_bound(date);

--found; // found가 begin()이면 잘못됨
```

기준 날짜 이하의 key가 하나도 없으면 `upper_bound()`가 `begin()`을 반환할 수 있으므로 감소시키기 전에 검사해야 합니다.

```cpp
if (found == rates.begin())
    throw NoEarlierValue();

--found;
```

빈 `map`에서도:

```cpp
rates.begin() == rates.end()
```

이므로 같은 검사로 처리할 수 있습니다.

반대로 `upper_bound()`가 `end()`를 반환하는 것은 오류가 아닙니다.

예를 들어 기준 날짜가 모든 key보다 크면:

```text
upper_bound(date) == rates.end()
```

이고, map이 비어 있지 않다면 `--found`로 마지막 원소에 안전하게 접근할 수 있습니다.

## `find`, `lower_bound`, `upper_bound`

세 함수는 찾는 기준이 다릅니다.

### `find(key)`

정확히 같은 key를 찾습니다.

```cpp
RateMap::const_iterator found =
    rates.find(date);

if (found != rates.end()) {
    // 정확한 date가 존재
}
```

의미:

```text
key == date
```

가 필요한 경우 사용합니다.

### `lower_bound(key)`

`key`보다 작지 않은 첫 원소를 찾습니다.

즉:

```text
first element with element_key >= key
```

예:

```text
keys: 10 20 30
lower_bound(20) → 20
lower_bound(25) → 30
lower_bound(40) → end()
```

### `upper_bound(key)`

`key`보다 큰 첫 원소를 찾습니다.

즉:

```text
first element with element_key > key
```

예:

```text
keys: 10 20 30
upper_bound(20) → 30
upper_bound(25) → 30
upper_bound(30) → end()
```

따라서 "기준값 이하에서 가장 가까운 값"을 찾는 문제에서는 `upper_bound()` 후 한 칸 감소하는 패턴이 자연스럽습니다.

## container를 먼저 정하지 않습니다

문제를 보자마자 다음처럼 시작하지 않습니다.

```text
map을 써야겠다.
vector를 써야겠다.
stack을 써야겠다.
```

먼저 필요한 연산을 적습니다.

예:

```text
삽입 순서를 유지
끝에 값 추가
앞에서부터 전체 순회
중간 검색은 거의 없음
```

이라면 `std::vector`가 자연스러울 수 있습니다.

반대로:

```text
key로 조회
key 중복 금지
key 순서 순회
경계 검색
```

이 필요하다면 `std::map`이 더 잘 맞습니다.

container는 문제를 표현하기 위한 수단입니다. 선택한 container에 문제를 억지로 맞추지 않습니다.

## 입력을 내부 값으로 바꿉니다

외부 문자열을 그대로 비교하거나 저장하기 전에 내부 규칙에 맞는 값인지 검증합니다.

예를 들어 날짜 입력:

```text
2026-08-29
```

를 문자열 그대로 key로 사용할 수도 있습니다.

하지만 문자열의 사전식 순서가 실제 날짜 순서와 같으려면 최소한 다음 조건이 필요합니다.

```text
형식이 항상 YYYY-MM-DD
연도는 같은 고정 폭
월과 일은 0으로 채운 두 자리
문자 위치가 항상 동일
실제 존재하는 날짜만 허용
```

이 조건이 유지되면:

```text
2026-01-09 < 2026-02-01
```

이라는 문자열 순서가 날짜 순서와 일치합니다.

반대로 다음처럼 가변 폭 형식을 허용하면:

```text
2026-2-1
2026-10-1
```

문자열 비교와 날짜 순서가 어긋날 수 있습니다.

## 날짜 형식과 실제 날짜 유효성은 다릅니다

다음 문자열은 모양만 보면 `YYYY-MM-DD` 형식처럼 보입니다.

```text
2026-02-31
```

하지만 실제 달력에는 존재하지 않는 날짜입니다.

따라서 날짜 검증은 적어도 두 단계로 나눕니다.

```text
형식 검증
→ 길이, '-' 위치, 숫자 위치

값 검증
→ 월 1~12
→ 월별 일수
→ 윤년의 2월 29일
```

문자열 정렬을 날짜 정렬로 이용한다면 **유효한 고정 형식 날짜만 container에 들어간다**는 불변조건을 먼저 만들어야 합니다.

## 숫자도 전체 입력을 검증합니다

숫자 입력은 앞부분만 숫자인 문자열을 성공으로 처리하지 않습니다.

예:

```text
"42"
→ 성공

"42abc"
→ 실패

""
→ 실패

"999999999999999999999"
→ 범위 오류
```

C++98에서는 `strtol()`과 end pointer를 사용해 다음을 확인할 수 있습니다.

```text
숫자를 하나 이상 읽었는가
문자열 전체를 소비했는가
long 범위를 넘지 않았는가
목표 타입 범위를 넘지 않았는가
```

입력의 문법적 유효성과 프로그램이 허용하는 값의 범위를 분리해서 검사합니다.

## 한 줄 오류와 전체 작업 실패를 구분합니다

여러 줄을 처리하는 입력이라면 오류 정책을 먼저 정합니다.

예를 들어 다음 입력이 있다고 가정합니다.

```text
2026-01-01,10
2026-01-02,20
BAD-LINE
2026-01-04,40
```

가능한 정책은 서로 다릅니다.

### 전체 파일 거부

```text
한 줄이라도 잘못됨
→ 파일 전체를 실패로 처리
→ 기존 상태 유지
```

설정 파일이나 하나의 일관된 dataset을 읽을 때 자연스러울 수 있습니다.

### 잘못된 줄만 거부

```text
잘못된 줄
→ 오류 기록
→ 다음 줄 계속 처리
```

독립적인 요청 로그나 batch command 처리에서는 적절할 수 있습니다.

어느 방식이 맞는지는 요구사항에 따라 다릅니다. 중요한 것은 중간 구현 우연으로 정책이 정해지지 않게 하는 것입니다.

## `std::map::operator[]`는 조회만 하지 않습니다

다음 코드는 key를 단순히 조회하는 것처럼 보일 수 있습니다.

```cpp
double value = rates[date];
```

하지만 `date`가 존재하지 않으면 `std::map::operator[]`는 해당 key를 새로 삽입하고 mapped value를 기본 생성합니다.

즉, 조회가 상태 변경이 될 수 있습니다.

조회만 하고 싶다면:

```cpp
RateMap::const_iterator found =
    rates.find(date);

if (found == rates.end())
    throw NotFound();

return found->second;
```

처럼 `find()`를 사용합니다.

`operator[]`는 "없으면 새 항목을 만들겠다"는 동작이 의도된 경우에 사용합니다.

## stack을 사용하는 문제

후위 표기식(postfix expression)은 stack과 잘 맞습니다.

예:

```text
3 4 + 2 *
```

처리 과정:

```text
3 push        [3]
4 push        [3, 4]
+             [7]
2 push        [7, 2]
*             [14]
```

숫자는 stack에 넣고, 연산자를 만나면 필요한 operand를 꺼내 연산한 뒤 결과를 다시 넣습니다.

## operand 순서

후위 표기식에서 이항 연산자를 처리할 때 먼저 pop한 값은 **오른쪽 operand**입니다.

```cpp
const int right = values.top();
values.pop();

const int left = values.top();
values.pop();

const int result = left - right;
```

예를 들어:

```text
8 3 -
```

의 결과는:

```text
8 - 3
```

이지:

```text
3 - 8
```

이 아닙니다.

나눗셈도 동일합니다.

```text
8 2 /
→ 8 / 2
```

pop 순서를 잘못 이해하면 덧셈과 곱셈에서는 우연히 맞아 보여도 뺄셈과 나눗셈에서 오류가 드러납니다.

## 연산 전 stack 크기를 확인합니다

이항 연산자에는 operand 두 개가 필요합니다.

따라서 먼저:

```cpp
if (values.size() < 2)
    throw InvalidExpression();
```

를 확인합니다.

그 뒤 값을 꺼냅니다.

```cpp
const int right = values.top();
values.pop();

const int left = values.top();
values.pop();
```

stack에 원소가 부족한 상태에서 `top()`이나 `pop()`을 호출해서는 안 됩니다.

## 연산 실패와 stack 상태

`std::stack`에서는 두 번째 원소를 읽으려면 위 원소를 pop해야 하므로, "모든 검사를 마치기 전에는 절대로 pop하지 않는다"는 규칙을 그대로 적용하기 어렵습니다.

따라서 **stack 자체를 실패 후에도 보존해야 하는지**를 먼저 정합니다.

### 표현식 전체 실패 시 stack을 버려도 되는 경우

표현식 평가에 사용하는 stack이 함수 내부의 임시 상태라면 다음처럼 처리할 수 있습니다.

```text
operand 수 확인
→ right pop
→ left pop
→ local 변수로 0 나눗셈·overflow 검사
→ 결과 push
```

연산 검사가 실패하면 함수 전체를 중단하고 임시 stack도 함께 버립니다.

이 경우 실패 후 중간 stack 상태를 복구할 필요가 없습니다.

### 실패 후 기존 stack을 그대로 유지해야 하는 경우

외부에서 제공된 stack을 수정하거나 실패 뒤에도 같은 stack을 계속 사용해야 한다면 후보 복사본에서 작업할 수 있습니다.

```cpp
std::stack<int> candidate(values);

evaluateOneOperator(candidate, op);

values.swap(candidate);
```

모든 검사가 성공한 뒤 결과 상태를 반영합니다.

다만 container 복사는 비용이 있으므로 실제 문제의 상태 보존 요구를 확인하고 선택합니다.

핵심은 다음과 같습니다.

> 실패 후 어떤 상태를 보장해야 하는지 먼저 정하고, 그 보장에 맞는 변경 순서를 선택합니다.

## 0으로 나누기

나눗셈 전에 오른쪽 operand를 검사합니다.

```cpp
if (right == 0)
    throw DivisionByZero();
```

검사 뒤:

```cpp
const int result = left / right;
```

를 수행합니다.

signed integer에서는 다음 경계도 주의해야 합니다.

```text
INT_MIN / -1
```

수학적 결과가 `INT_MAX`보다 크므로 `int`로 표현할 수 없습니다.

따라서 단순히 `right != 0`만 확인한다고 모든 정수 나눗셈이 안전해지는 것은 아닙니다.

## 산술 overflow를 계산 전에 확인합니다

signed integer overflow는 정의되지 않은 동작입니다.

따라서:

```cpp
const int result = left + right;
```

를 먼저 수행한 뒤 결과를 검사하면 늦습니다.

예를 들어 덧셈은 계산 전에 경계를 확인합니다.

```cpp
if (right > 0 && left > INT_MAX - right)
    throw ArithmeticOverflow();

if (right < 0 && left < INT_MIN - right)
    throw ArithmeticOverflow();

const int result = left + right;
```

곱셈, 뺄셈, 나눗셈은 각각 경계 조건이 다르므로 연산별 검사를 분리합니다.

## 후위식의 최종 상태도 검사합니다

모든 token을 읽었다고 해서 표현식이 자동으로 유효한 것은 아닙니다.

예:

```text
1 2
```

연산자가 없으므로 마지막에 stack에 값이 두 개 남습니다.

정상적인 하나의 식이라면 모든 token 처리 후:

```cpp
if (values.size() != 1)
    throw InvalidExpression();
```

이어야 합니다.

그 뒤 최종 값을 사용합니다.

```cpp
return values.top();
```

즉, stack 문제에서는 중간 operand 수뿐 아니라 **최종 stack 크기**도 입력 검증 조건입니다.

## 안정 정렬

같은 정렬 key를 가진 원소의 입력 순서를 보존해야 한다면 `std::stable_sort`를 사용할 수 있습니다.

```cpp
struct Record {
    int value;
    std::size_t inputOrder;
};
```

예를 들어 comparator가 `value`만 비교한다고 가정합니다.

```cpp
struct RecordLess {
    bool operator()(
        const Record &left,
        const Record &right) const
    {
        return left.value < right.value;
    }
};
```

입력:

```text
value=10, A
value=5,  B
value=10, C
```

`std::stable_sort` 후에는 `value == 10`인 A와 C의 상대적 순서가 유지됩니다.

```text
5  B
10 A
10 C
```

## stable sort와 tie-breaker는 다른 선택입니다

두 방법은 결과가 비슷해 보일 수 있지만 의미가 다릅니다.

### stable sort

비교 기준은 primary key만 사용하고, 비교상 동등한 원소는 기존 상대 순서를 보존합니다.

```cpp
return left.value < right.value;
```

입력 순서 자체가 의미 있는 경우에 자연스럽습니다.

### 명시적인 tie-breaker

입력 순서를 comparator의 두 번째 기준으로 직접 사용합니다.

```cpp
struct RecordLess {
    bool operator()(
        const Record &left,
        const Record &right) const
    {
        if (left.value != right.value)
            return left.value < right.value;

        return left.inputOrder < right.inputOrder;
    }
};
```

이 경우 두 record의 `inputOrder`가 서로 다르다면 comparator 관점에서 더 이상 동등하지 않습니다.

따라서 결과 순서는 `stable_sort`의 안정성에 의존하는 것이 아니라 comparator가 직접 결정합니다.

요구사항에 맞게 둘을 구분합니다.

## 입력 순서를 record에 저장하는 이유

정렬 후에도 "원래 몇 번째 입력이었는가"라는 정보가 필요하다면 입력 시점에 보존해야 합니다.

```cpp
record.inputOrder = index;
```

`stable_sort`는 현재 범위 안에서 동등한 원소의 상대 순서를 보존하지만, 이후 다음 작업이 이루어질 수 있습니다.

- 다른 기준으로 다시 정렬
- 일부 원소만 새 container에 복사
- merge
- 별도 grouping
- file에 저장 후 다시 읽기

이런 과정 뒤에도 원래 입력 위치 자체가 필요하다면 `inputOrder` 같은 값을 명시적으로 저장해야 합니다.

## 비교 함수는 strict weak ordering을 지켜야 합니다

정렬 comparator는 strict weak ordering을 만족해야 합니다.

최소한 다음과 같은 잘못된 비교를 만들지 않습니다.

```cpp
bool operator()(
    const Record &left,
    const Record &right) const
{
    return left.value <= right.value; // 잘못된 비교
}
```

같은 값에 대해:

```text
comp(x, x) == true
```

가 될 수 있으므로 strict ordering이 아닙니다.

올바른 형태는 보통:

```cpp
return left.value < right.value;
```

입니다.

tie-breaker도 같은 원칙을 지켜야 합니다.

## 결정적인 출력

테스트나 사용자에게 보여 주는 결과에서 순서가 의미 있다면 구현의 우연에 맡기지 않습니다.

C++98 표준에는 `std::unordered_map`이 없습니다.

`std::map`은 comparator가 정의한 key 순서로 순회합니다.

```cpp
for (Map::const_iterator it = values.begin();
     it != values.end();
     ++it) {
    // key 순서
}
```

따라서 key 정렬 순서가 그대로 출력 요구사항과 맞는다면 `map` 순회를 사용할 수 있습니다.

반대로 다른 container에 저장했다면 출력 전에 명시적으로 정렬할 수 있습니다.

## "결정적"이라는 뜻

결정적인 출력은 같은 유효 입력과 같은 규칙에서 결과 순서가 우연한 memory layout이나 삽입 구현에 따라 달라지지 않는다는 뜻입니다.

예를 들어 다음 조건을 명시해야 할 수 있습니다.

```text
첫 번째 기준: value 오름차순
두 번째 기준: inputOrder 오름차순
```

또는:

```text
value가 같으면 원래 입력 순서 유지
```

두 요구는 비슷하지만 구현 방법이 다릅니다.

- 명시적 두 번째 기준 → comparator에 tie-breaker
- 입력 상대 순서 보존 → stable sort

## 정렬 전에 전체 입력을 검증할지 결정합니다

정렬 자체는 잘못된 입력을 올바른 데이터로 만들어 주지 않습니다.

예를 들어 다음 데이터가 있다고 가정합니다.

```text
10
abc
5
```

`abc`를 임의의 0으로 바꾸고 정렬하면 입력 오류가 숨겨집니다.

전체 batch가 하나의 작업이라면:

```text
모든 입력 parse
→ 모든 값 검증
→ 정렬
→ 출력
```

순서가 자연스럽습니다.

반면 줄별 독립 처리라면 잘못된 줄만 별도 오류로 처리하는 정책을 선택할 수 있습니다.

## 복잡도와 실제 비용

자료구조를 선택할 때 Big-O만 보는 것도 부족하고, 측정값만 보는 것도 부족합니다.

둘을 함께 사용합니다.

예를 들어:

```text
vector 선형 검색
→ O(n)

map 검색
→ O(log n)
```

하지만 실제 비용에는 다음 차이도 있습니다.

### `std::vector`

- 원소가 연속 memory에 배치됩니다.
- 순차 순회가 단순합니다.
- 작은 원소를 연속으로 읽기 좋습니다.
- 중간 삽입·삭제는 원소 이동 비용이 발생합니다.
- 검색은 기본적으로 선형입니다.

### `std::map`

- key 기반 검색·삽입·삭제가 일반적으로 로그 시간입니다.
- 원소마다 node를 별도로 관리합니다.
- 정렬된 key 순서를 항상 유지합니다.
- `lower_bound`, `upper_bound` 같은 경계 검색을 제공합니다.
- 원소 접근이 연속 memory 순회보다 실제 상수 비용이 클 수 있습니다.

따라서 데이터가 작고 검색 횟수도 적다면 단순 `vector` 선형 검색이 충분하거나 더 빠를 수도 있습니다.

## 연산 빈도까지 함께 봅니다

같은 데이터 크기라도 어떤 연산을 얼마나 자주 수행하는지가 중요합니다.

예:

```text
한 번 입력
→ 한 번 정렬
→ 수천 번 순차 조회
```

와

```text
계속 삽입
→ 매번 key 검색
→ 경계 검색 반복
```

은 적절한 container가 다를 수 있습니다.

다음처럼 문제를 적어 보는 것이 도움이 됩니다.

```text
원소 수: 약 1000
삽입: 시작 시 1000회
정확 검색: 요청마다 1회
경계 검색: 요청마다 1회
전체 순회: 종료 시 1회
```

그 뒤 복잡도와 구현 단순성을 함께 비교합니다.

## parsing과 출력 비용도 포함합니다

프로그램 전체 시간이 정렬 algorithm만으로 결정되는 것은 아닙니다.

예를 들어 전체 처리에 다음 단계가 있을 수 있습니다.

```text
파일 읽기
문자열 분리
숫자 변환
날짜 검증
container 삽입
정렬
문자열 formatting
stdout 출력
```

작은 입력에서는 sorting보다 parsing이나 I/O가 더 큰 비용일 수 있습니다.

따라서 전체 프로그램 성능과 특정 algorithm 성능을 구분합니다.

## 측정 범위를 명확히 합니다

성능 측정을 기록할 때 최소한 다음 조건을 함께 적습니다.

```text
입력 크기
데이터 분포
compiler와 build mode
측정한 코드 범위
반복 횟수
```

예를 들어:

```text
Release build
100,000 records
정렬 함수 호출 구간만 측정
20회 반복 평균
```

처럼 적습니다.

Debug build 한 번의 실행 시간만 보고 container나 algorithm의 일반적인 성능을 결론 내리지 않습니다.

또한 한 번의 짧은 측정은 timer 오차, OS scheduling, cache 상태의 영향을 크게 받을 수 있습니다.

## 전체 파일을 후보 상태로 읽기

설정 파일이나 CSV 전체가 하나의 일관된 상태를 나타낸다면 중간 오류 때문에 기존 상태가 일부만 바뀌어서는 안 됩니다.

다음 패턴을 사용할 수 있습니다.

```cpp
Map candidate;

read_all_rows(input, candidate);
validate(candidate);

rates_.swap(candidate);
```

흐름은 다음과 같습니다.

```text
기존 rates_ 유지
      |
      +→ candidate에 전체 파일 읽기
      |
      +→ 전체 검증
      |
      +→ 성공하면 swap
```

읽기나 검증 중 실패하면 `rates_`에는 손대지 않았으므로 기존 상태가 유지됩니다.

## 후보 상태 방식의 장점

예를 들어 기존 상태가:

```text
A
B
C
```

이고 새 파일에서:

```text
X
Y
BAD
Z
```

를 읽었다고 가정합니다.

기존 container를 직접 수정하면:

```text
X
Y
```

까지 반영된 뒤 실패할 수 있습니다.

후보 상태를 사용하면:

```text
candidate = X, Y까지 구성
→ BAD에서 실패
→ candidate 폐기
→ 기존 A, B, C 유지
```

가 됩니다.

이 방식은 파일 전체가 유효할 때만 새 상태를 적용하는 **강한 상태 교체 방식**을 만들기 쉽습니다.

## `swap()`하기 전까지 기존 상태를 건드리지 않습니다

후보 상태 방식을 사용할 때 중간에 기존 객체의 부가 상태를 먼저 수정하면 장점이 사라집니다.

예를 들어:

```cpp
ratesCount_ = newCount; // 너무 일찍 변경
read_all_rows(input, candidate);
```

읽기가 실패하면 `rates_`는 이전 값인데 `ratesCount_`만 새 값이 될 수 있습니다.

서로 함께 변해야 하는 상태라면 하나의 후보 객체로 묶거나 모든 준비를 끝낸 뒤 함께 반영합니다.

예:

```cpp
State candidate;

read_all_rows(input, candidate.rates);
candidate.count = candidate.rates.size();
validate(candidate);

state_.swap(candidate);
```

핵심은 "실패 가능한 준비"와 "현재 상태 반영" 사이에 명확한 경계를 두는 것입니다.

## `swap()`도 타입의 계약을 확인합니다

후보 상태 패턴은 마지막 상태 교체가 단순하고 안전할수록 좋습니다.

표준 container의 `swap()`은 전체 원소를 하나씩 다시 복사하는 것보다 효율적인 상태 교체에 적합합니다.

직접 만든 타입에 `swap()`을 제공한다면 가능하면 다음을 지킵니다.

```text
추가 allocation을 하지 않음
소유 resource를 단순 교환
실패 가능한 연산을 넣지 않음
```

C++98에는 `noexcept` 문법이 없지만, 상태 반영 단계가 새 실패 지점을 만들지 않도록 구현하는 것이 중요합니다.

## 문제를 STL 연산으로 번역합니다

문제를 풀 때 다음처럼 자연어 요구를 STL 연산으로 바꿔 보면 container 선택이 쉬워집니다.

```text
"정확한 key가 있는지 확인"
→ find

"처음으로 key >= x인 위치"
→ lower_bound

"처음으로 key > x인 위치"
→ upper_bound

"마지막에 넣고 마지막에서 꺼냄"
→ stack 또는 vector의 back

"같은 기준값끼리 원래 순서 유지"
→ stable_sort

"전체가 유효할 때만 교체"
→ candidate + validate + swap
```

STL을 외우는 것보다 문제의 요구를 연산으로 번역하는 습관이 중요합니다.

## 자주 놓치는 문제

- container 이름을 먼저 정하고 문제를 그 container에 맞춥니다.
- `map::operator[]`로 조회하다 없는 key를 의도치 않게 추가합니다.
- `find`, `lower_bound`, `upper_bound`의 경계 조건을 같은 것으로 생각합니다.
- `upper_bound()`가 `begin()`인데 직전 원소로 이동합니다.
- `upper_bound()`가 `end()`이면 항상 실패라고 생각합니다.
- 날짜가 `YYYY-MM-DD` 모양이기만 하면 실제 달력 날짜도 유효하다고 생각합니다.
- 가변 폭 날짜 문자열도 사전식 순서와 날짜 순서가 일치한다고 생각합니다.
- 숫자의 앞부분만 읽고 뒤 문자를 무시합니다.
- 후위식 operand 순서를 반대로 계산합니다.
- stack 원소 수를 확인하기 전에 `top()`이나 `pop()`을 호출합니다.
- 나눗셈에서 0만 검사하고 `INT_MIN / -1` 경계를 놓칩니다.
- 후위식 모든 token을 처리한 뒤 stack에 값이 정확히 하나 남는지 검사하지 않습니다.
- 실패 뒤에도 stack 상태를 보존해야 하는지 먼저 정하지 않습니다.
- `stable_sort`와 명시적인 tie-breaker를 같은 의미로 생각합니다.
- comparator에 `<=`를 사용해 strict weak ordering을 깨뜨립니다.
- stable sort를 사용했다는 이유만으로 이후 다른 변환에서도 원래 입력 위치 정보를 복원할 수 있다고 생각합니다.
- 정렬 전에 필요한 입력 검증을 끝내지 않습니다.
- 같은 key의 출력 순서를 구현 우연에 맡깁니다.
- Big-O만 보고 실제 데이터 크기와 연산 빈도를 무시합니다.
- Debug build 한 번의 시간을 성능 결과로 사용합니다.
- sorting만 측정했다고 생각하면서 파일 I/O나 formatting까지 측정 구간에 포함합니다.
- 새 파일을 기존 상태에 직접 덮어쓰다가 중간 실패 후 partial update를 남깁니다.
- 후보 container를 사용하면서 별도 멤버 상태는 먼저 변경합니다.

## 완료 기준

다음 항목을 설명하고 코드에서 적용할 수 있으면 이 범위의 목표를 달성한 것입니다.

- 문제에서 필요한 주요 연산과 실패 조건을 먼저 적고 그에 맞는 container를 선택합니다.
- `find`, `lower_bound`, `upper_bound`의 정확한 의미와 경계 조건을 설명합니다.
- 기준값 이하의 가장 가까운 map 원소를 `upper_bound()`로 찾고 `begin()` 경계를 안전하게 처리합니다.
- `map::operator[]`가 조회 중 새 원소를 삽입할 수 있음을 설명합니다.
- 문자열 날짜의 사전식 순서를 이용하려면 고정 폭 형식과 실제 날짜 검증이 필요함을 설명합니다.
- 숫자 입력의 전체 소비와 타입·도메인 범위를 검사합니다.
- 입력 오류가 전체 작업을 실패시킬지 한 줄만 실패시킬지 명시적으로 정합니다.
- 후위 표기식에서 오른쪽 operand와 왼쪽 operand의 pop 순서를 설명합니다.
- stack operand 수, 0 나눗셈, overflow와 최종 stack 크기를 검사합니다.
- 실패 후 stack을 유지해야 하는지에 따라 임시 상태와 후보 복사 전략을 구분합니다.
- stable sort와 명시적인 tie-breaker의 의미 차이를 설명합니다.
- comparator가 strict weak ordering을 만족하도록 작성합니다.
- 출력 순서를 container나 comparator 규칙으로 명시적으로 결정합니다.
- 이론적 복잡도와 실제 데이터 크기·연산 빈도·memory 특성을 함께 비교합니다.
- 성능 측정 시 build mode, 입력 크기와 측정 범위를 기록합니다.
- 전체 입력을 후보 상태에 읽고 검증 성공 후 현재 상태와 교체합니다.
- 후보 상태를 사용하는 동안 기존 상태의 관련 멤버를 먼저 변경하지 않습니다.
