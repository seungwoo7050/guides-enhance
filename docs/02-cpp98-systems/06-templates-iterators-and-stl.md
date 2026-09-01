# C++98 template·iterator·STL

## 목표

C++98 문법으로 함수와 클래스 template을 작성하고, template이 실제 타입으로 인스턴스화될 때 필요한 조건을 이해합니다. iterator는 `[begin, end)` 범위와 const 여부를 지키고, container 변경 뒤에도 기존 iterator·pointer·reference가 유효한지 확인합니다.

또한 C++98 표준 container가 원소를 값으로 저장할 때 복사 생성자, 복사 대입 연산자, 소멸자가 어떤 의미를 가져야 하는지 이해합니다.

이 문서의 핵심은 다음과 같습니다.

- template이 요구하는 연산을 명시합니다.
- template 정의가 사용하는 번역 단위에서 보여야 하는 이유를 이해합니다.
- dependent type 앞에 `typename`이 필요한 이유를 설명합니다.
- iterator 범위와 iterator category가 허용하는 연산을 구분합니다.
- const container에서 mutable 접근을 허용하지 않습니다.
- container별 iterator 무효화 규칙을 확인합니다.
- container가 값과 pointer를 저장할 때 소유권 의미가 어떻게 다른지 구분합니다.
- STL algorithm의 전제 조건을 지킵니다.

## 함수 template

함수 template은 타입을 매개변수로 받아 여러 타입에 같은 형태의 코드를 생성할 수 있게 합니다.

```cpp
template <class T>
const T &maximum(const T &left, const T &right)
{
    return left < right ? right : left;
}
```

이 함수가 모든 타입에 동작하는 것은 아닙니다. 함수 본문에서 다음 표현을 사용하기 때문에 `T`는 최소한 이 비교를 지원해야 합니다.

```cpp
left < right
```

즉, `T`에 요구되는 조건은 단순히 "어떤 타입이든 가능"이 아니라 다음과 같습니다.

```text
- const T 객체끼리 operator<로 비교할 수 있어야 한다.
- 비교 결과를 조건식에서 bool처럼 사용할 수 있어야 한다.
- 반환된 reference가 호출 뒤에도 유효해야 한다.
```

마지막 조건도 중요합니다. 이 함수는 값을 새로 만드는 것이 아니라 입력 인자 중 하나를 reference로 반환합니다.

예:

```cpp
int a = 3;
int b = 5;

const int &result = maximum(a, b);
```

`result`는 `a` 또는 `b`를 가리키므로 해당 객체보다 오래 사용할 수 없습니다.

## template이 요구하는 연산을 문서화합니다

C++98에는 concept이나 `requires`가 없습니다.

따라서 다음과 같이 template 매개변수에 필요한 조건을 언어 문법으로 직접 선언할 수 없습니다.

```text
T는 operator<를 지원해야 한다.
T는 복사 가능해야 한다.
Iterator는 ++와 *를 지원해야 한다.
```

잘못된 타입을 사용하면 template을 실제 타입으로 인스턴스화하는 과정에서 긴 compiler 오류가 발생할 수 있습니다.

예:

```cpp
struct Item {
};

Item a;
Item b;

maximum(a, b);
```

`Item`에 `operator<`가 없으면 `maximum<Item>`의 본문을 생성하는 시점에 오류가 발생합니다.

따라서 public template은 가능한 한 작게 유지하고, 필요한 연산과 의미를 README나 주석에 명시합니다.

예:

```text
maximum<T> 요구 조건:
- const T와 const T 사이의 operator<가 유효해야 한다.
- 반환 reference는 전달한 두 객체 중 하나를 가리킨다.
```

## 함수 template의 타입 추론

함수 template은 인자에서 template 인자를 추론할 수 있습니다.

```cpp
int a = 1;
int b = 2;

maximum(a, b);
```

compiler는 두 인자를 보고 `T == int`로 추론할 수 있습니다.

필요하면 직접 타입을 지정할 수도 있습니다.

```cpp
maximum<int>(a, b);
```

하지만 서로 다른 타입을 그대로 넘기면 하나의 `T`를 결정할 수 없는 경우가 있습니다.

```cpp
int a = 1;
long b = 2;

// maximum(a, b); // 하나의 T로 추론되지 않을 수 있음
```

이런 경우 template signature 자체가 두 타입을 받을 수 있도록 설계할지, 호출 전에 같은 타입으로 명시적으로 변환할지 결정해야 합니다.

## 클래스 template

클래스 template은 타입에 따라 클래스 정의를 생성합니다.

```cpp
template <class T>
class Array {
public:
    explicit Array(std::size_t size);
    ~Array();

private:
    T *data_;
    std::size_t size_;
};
```

사용할 때는 실제 타입을 지정합니다.

```cpp
Array<int> numbers(10);
Array<std::string> names(5);
```

`Array<int>`와 `Array<std::string>`은 같은 template에서 만들어지지만 서로 다른 실제 타입입니다.

## 클래스 template 정의 위치

일반 함수는 선언을 헤더에 두고 정의를 `.cpp`에 둘 수 있습니다.

하지만 template은 compiler가 실제 타입에 맞는 코드를 생성하는 시점에 정의를 볼 수 있어야 합니다.

따라서 일반적으로 template 선언과 정의를 모두 헤더에 둡니다.

```cpp
template <class T>
class Array {
public:
    explicit Array(std::size_t size);

private:
    T *data_;
    std::size_t size_;
};

template <class T>
Array<T>::Array(std::size_t size)
    : data_(size ? new T[size] : 0),
      size_(size)
{
}
```

다른 `.cpp`에서 다음을 사용한다고 가정합니다.

```cpp
Array<int> values(10);
```

이 번역 단위를 compile할 때 compiler는 `Array<int>::Array`의 실제 코드를 만들어야 합니다. 따라서 constructor의 template 정의를 볼 수 있어야 합니다.

## template 정의를 `.cpp`에 둘 때 생기는 문제

다음처럼 선언만 헤더에 두고:

```cpp
// Array.hpp

template <class T>
class Array {
public:
    explicit Array(std::size_t size);
};
```

정의를 `.cpp`에 두었다고 가정합니다.

```cpp
// Array.cpp

template <class T>
Array<T>::Array(std::size_t size)
{
    // ...
}
```

다른 번역 단위에서 `Array<int>`를 사용해도 그 번역 단위는 constructor 정의를 볼 수 없습니다.

그 결과 필요한 인스턴스가 생성되지 않아 link 오류로 나타날 수 있습니다.

단순한 C++98 프로젝트에서는 다음 규칙이 가장 안전합니다.

> template 선언과 정의를 사용하는 코드가 볼 수 있는 헤더에 함께 둡니다.

## 명시적 instantiation

지원할 타입 목록이 고정되어 있다면 template 정의를 `.cpp`에 두고 특정 타입만 명시적으로 인스턴스화할 수 있습니다.

개념적인 예:

```cpp
// Array.cpp

template <class T>
Array<T>::Array(std::size_t size)
    : data_(size ? new T[size] : 0),
      size_(size)
{
}

template class Array<int>;
template class Array<std::string>;
```

이 방식은 `Array<int>`, `Array<std::string>`처럼 미리 지정한 타입만 지원할 때 사용할 수 있습니다.

하지만 나중에 다른 번역 단위에서:

```cpp
Array<double> values(10);
```

를 사용하려면 `Array<double>`에 필요한 정의와 명시적 instantiation도 추가해야 합니다.

즉, template의 일반성을 일부 포기하고 지원 타입 목록을 고정하는 방식입니다.

## dependent name

template 안에서는 어떤 이름의 의미가 template 매개변수에 의존할 수 있습니다.

예:

```cpp
template <class Container>
void print(const Container &items)
{
    typename Container::const_iterator it = items.begin();

    for (; it != items.end(); ++it)
        std::cout << *it << '\n';
}
```

여기서:

```cpp
Container::const_iterator
```

는 `Container`가 실제 어떤 타입인지 정해져야 정확한 의미를 알 수 있습니다.

이런 이름을 **dependent name**이라고 합니다.

## `typename`이 필요한 이유

다음 코드만 보면:

```cpp
Container::const_iterator
```

compiler는 template 정의를 처음 읽는 시점에 `const_iterator`가 타입 이름인지 다른 종류의 이름인지 확정할 수 없습니다.

따라서 타입이라는 사실을 명시합니다.

```cpp
typename Container::const_iterator
```

전체 코드는 다음과 같습니다.

```cpp
template <class Container>
void print(const Container &items)
{
    typename Container::const_iterator it = items.begin();

    for (; it != items.end(); ++it)
        std::cout << *it << '\n';
}
```

`typename`은 단순히 "이 이름이 길어서 붙이는 키워드"가 아닙니다.

> template 매개변수에 의존하는 qualified name이 타입임을 compiler에게 알려 주는 역할을 합니다.

## dependent type이 아닌 경우

일반 코드에서 이미 타입이라는 사실이 확정된 이름에는 이런 `typename`이 필요하지 않습니다.

```cpp
std::vector<int>::const_iterator it;
```

여기서 `std::vector<int>`는 실제 타입이 이미 정해져 있으므로 `const_iterator`가 무엇인지 compiler가 알 수 있습니다.

반면:

```cpp
Container::const_iterator
```

는 `Container`가 template 매개변수이므로 타입임을 명시해야 합니다.

## iterator는 위치를 나타내는 추상화입니다

STL iterator는 container의 원소를 순회하는 공통 인터페이스 역할을 합니다.

대표적인 연산은 다음과 같습니다.

```cpp
*it     // 현재 원소 접근
++it    // 다음 위치로 이동
it != end
```

하지만 모든 iterator가 같은 연산을 지원하는 것은 아닙니다.

예를 들어 어떤 iterator에서는 다음 연산이 가능하지만:

```cpp
it + 3
it[2]
last - first
```

다른 iterator에서는 불가능할 수 있습니다.

따라서 algorithm이나 template을 작성할 때 어떤 iterator 능력을 요구하는지 알아야 합니다.

## iterator category

표준 iterator는 지원하는 이동 능력에 따라 여러 category로 나뉩니다.

학습 범위에서 주요 관계를 단순화하면 다음과 같습니다.

```text
input iterator
→ 한 방향 읽기

output iterator
→ 한 방향 쓰기

forward iterator
→ 한 방향으로 반복 순회 가능

bidirectional iterator
→ ++와 -- 가능

random access iterator
→ +, -, 차이 계산, 임의 위치 이동 가능
```

container에 따라 iterator category가 다릅니다.

대표적으로:

```text
std::vector
→ random access iterator

std::deque
→ random access iterator

std::list
→ bidirectional iterator

std::map
→ bidirectional iterator
```

따라서 `std::vector` iterator에는 가능한 연산이 `std::map` iterator에는 허용되지 않을 수 있습니다.

## algorithm이 요구하는 iterator category

algorithm마다 요구하는 iterator 능력이 다릅니다.

예를 들어:

```cpp
std::find(first, last, value);
```

는 순차적으로 이동할 수 있는 iterator에서 사용할 수 있습니다.

반면:

```cpp
std::sort(first, last);
std::stable_sort(first, last);
```

은 random access iterator를 요구합니다.

따라서 다음은 가능합니다.

```cpp
std::vector<Record> records;
std::stable_sort(
    records.begin(),
    records.end(),
    RecordLess());
```

하지만 `std::list` iterator에는 `std::sort`나 `std::stable_sort`를 직접 사용할 수 없습니다.

`std::list`는 자신의 멤버 `sort()`를 제공합니다.

즉, "iterator처럼 보인다"는 것만으로 모든 algorithm을 사용할 수 있는 것은 아닙니다.

## 표준 iterator 범위는 `[begin, end)`입니다

STL에서 일반적인 범위는 반열린 구간입니다.

```text
[begin, end)
```

뜻은 다음과 같습니다.

```text
begin은 첫 원소를 가리킴
end는 마지막 원소 다음 위치를 나타냄
```

따라서 `end()`는 실제 원소를 가리키지 않으며 역참조하면 안 됩니다.

```cpp
for (Iterator it = first;
     it != last;
     ++it) {
    function(*it);
}
```

loop 본문은 `it != last`인 경우에만 실행되므로 `last`를 역참조하지 않습니다.

## 빈 범위

빈 container에서는:

```cpp
begin() == end()
```

입니다.

따라서 다음 loop는 본문을 한 번도 실행하지 않습니다.

```cpp
for (Iterator it = items.begin();
     it != items.end();
     ++it) {
    // 빈 container라면 실행되지 않음
}
```

빈 범위는 특별한 오류 상태가 아니라 정상적인 `[begin, end)` 범위입니다.

## 직접 구현한 pointer iterator의 빈 범위

직접 만든 연속 배열 container에서 raw pointer를 iterator로 사용할 수 있습니다.

예:

```cpp
typedef T *iterator;
```

그러나 빈 container에서 내부 pointer가 `0`인데 다음처럼 `end()`를 구현하면 주의가 필요합니다.

```cpp
iterator end()
{
    return data_ + size_;
}
```

`data_ == 0`, `size_ == 0`인 경우에도 null pointer에 pointer arithmetic을 수행하는 표현을 피하는 것이 안전합니다.

다음처럼 빈 상태를 별도로 처리할 수 있습니다.

```cpp
iterator end()
{
    if (data_ == 0)
        return 0;

    return data_ + size_;
}
```

그리고 `begin()`도 빈 경우 `0`을 반환한다면:

```cpp
begin() == end()
```

가 유지됩니다.

핵심은 STL의 `[begin, end)` 규칙을 직접 구현하더라도 실제 pointer 연산의 유효 조건까지 지켜야 한다는 것입니다.

## mutable iterator와 const iterator

수정 가능한 container와 읽기 전용 container의 iterator는 구분해야 합니다.

예:

```cpp
Array<int>::iterator it = values.begin();
Array<int>::const_iterator read = view.begin();
```

일반적으로:

```text
iterator
→ 가리키는 원소를 수정할 수 있음

const_iterator
→ iterator를 통해 원소를 수정할 수 없음
```

예:

```cpp
*it = 42;
```

는 mutable iterator라면 가능할 수 있지만:

```cpp
// *read = 42;
```

는 허용되어서는 안 됩니다.

## const container의 `begin()`과 `end()`

직접 container를 구현한다면 const 여부에 맞는 overload를 제공합니다.

예:

```cpp
class Array {
public:
    typedef T *iterator;
    typedef const T *const_iterator;

    iterator begin();
    iterator end();

    const_iterator begin() const;
    const_iterator end() const;
};
```

수정 가능한 객체에서는:

```cpp
Array<int> values;
Array<int>::iterator it = values.begin();
```

const 객체에서는:

```cpp
const Array<int> &view = values;
Array<int>::const_iterator it = view.begin();
```

처럼 동작해야 합니다.

const container에서 mutable iterator를 반환하면 caller가 const 제한을 우회해 내부 값을 변경할 수 있으므로 잘못된 interface가 됩니다.

## iterator 자체의 const와 const_iterator는 다릅니다

다음 둘은 다른 의미입니다.

```cpp
const_iterator it;
```

와

```cpp
const iterator it = ...;
```

`const_iterator`는 iterator가 가리키는 원소를 수정하지 못하게 하는 iterator 종류입니다.

반면 `const iterator`는 iterator 객체 자체를 다른 위치로 이동시키지 못하게 할 수 있지만, iterator가 mutable 원소를 가리킨다면 원소 수정 가능성과는 별개입니다.

즉:

```text
const_iterator
→ 원소 접근의 const성

const iterator
→ iterator 변수 자체의 const성
```

을 구분합니다.

## iterator 무효화

container의 구조가 변경되면 기존 iterator, pointer, reference가 더 이상 같은 원소를 안전하게 가리키지 못할 수 있습니다.

이를 **iterator invalidation**이라고 합니다.

무효화 규칙은 container마다 다릅니다.

따라서 다음처럼 작성했다고 해서:

```cpp
Iterator it = container.begin();
```

이 `it`가 container의 모든 변경 뒤에도 계속 유효하다고 가정하면 안 됩니다.

## `std::vector` 무효화

`std::vector`는 원소를 연속 storage에 보관합니다.

capacity를 넘어서 원소를 추가하면 더 큰 storage를 새로 확보하고 기존 원소를 옮겨 복사할 수 있습니다.

이 **reallocation**이 발생하면 기존 storage를 가리키던 다음 항목들이 모두 무효화됩니다.

- iterator
- pointer
- reference

예:

```cpp
std::vector<int> values;
values.push_back(1);

int *p = &values[0];

values.push_back(2); // reallocation 가능

// p를 계속 사용해도 된다고 가정하면 안 됨
```

`push_back`이 항상 reallocation을 일으키는 것은 아니지만, 발생할 수 있는 상황에서는 기존 주소에 의존하지 않아야 합니다.

### reallocation이 없는 insert

`vector`에 충분한 capacity가 있어 reallocation이 발생하지 않더라도 중간 위치에 insert하면 원소들이 뒤로 이동할 수 있습니다.

일반적으로 삽입 위치 이전의 iterator/reference는 유지될 수 있지만, 삽입 위치와 그 이후를 가리키던 iterator/reference는 무효화될 수 있습니다.

따라서 insert 위치 이후의 주소를 저장해 두고 계속 사용하는 코드는 피합니다.

### erase

`vector::erase`는 원소를 지운 뒤 뒤쪽 원소를 앞으로 이동시킵니다.

따라서 지운 위치와 그 이후를 가리키던 iterator/reference는 더 이상 이전 의미를 유지한다고 가정하면 안 됩니다.

erase 중 순회할 때는 erase가 반환하는 다음 iterator를 활용하는 패턴을 사용합니다.

```cpp
std::vector<int>::iterator it = values.begin();

while (it != values.end()) {
    if (shouldErase(*it))
        it = values.erase(it);
    else
        ++it;
}
```

## `std::map` 무효화

`std::map`은 `vector`와 다른 무효화 규칙을 가집니다.

일반적으로 새로운 원소를 insert해도 기존 원소를 가리키는 iterator/reference는 유지됩니다.

```cpp
std::map<std::string, int>::iterator it =
    values.find("a");

values.insert(
    std::make_pair(std::string("b"), 2));

// 기존 "a" 원소 iterator는 유지됨
```

반면 원소를 erase하면 **지운 원소를 가리키던** iterator/reference는 무효화됩니다.

다른 원소를 가리키던 iterator는 일반적으로 유지됩니다.

이 차이는 container 선택과 API 설계에 직접 영향을 줍니다.

## `std::deque` 무효화

`std::deque`는 연속된 하나의 배열처럼 단순하게 구현되는 container가 아니며, 삽입·삭제 위치와 연산 종류에 따라 iterator/reference 무효화 규칙이 더 복잡합니다.

따라서 `deque`의 주소 안정성에 의존해야 하는 코드는 사용하는 연산별 규칙을 표준 문서나 compiler가 따르는 표준 library 문서에서 확인합니다.

"vector와 비슷하겠지" 또는 "list처럼 안정적이겠지"라고 추측하지 않습니다.

## 무효화 규칙은 iterator만의 문제가 아닙니다

container 변경은 iterator뿐 아니라 원소를 직접 가리키는 pointer와 reference에도 영향을 줄 수 있습니다.

예:

```cpp
int &value = values[0];
int *ptr = &values[0];
std::vector<int>::iterator it = values.begin();
```

vector reallocation이 일어나면 세 가지 모두 기존 storage를 가리키게 되므로 함께 무효화됩니다.

따라서 "iterator만 다시 구하면 pointer는 괜찮다"는 식으로 생각하면 안 됩니다.

## erase하면서 순회하기

container를 순회하면서 원소를 지울 때는 현재 iterator를 erase한 뒤 그대로 증가시키면 안 됩니다.

예를 들어 `vector`에서는 다음 패턴을 사용할 수 있습니다.

```cpp
std::vector<int>::iterator it = values.begin();

while (it != values.end()) {
    if (shouldErase(*it)) {
        it = values.erase(it);
    } else {
        ++it;
    }
}
```

`erase(it)`가 지운 원소 다음 위치를 반환하므로 그 값을 다시 사용합니다.

container마다 erase의 반환값과 무효화 규칙이 다를 수 있으므로 사용하는 container의 C++98 interface를 확인합니다.

## STL container는 값을 저장합니다

다음 container를 생각해 봅니다.

```cpp
std::vector<TextBuffer> buffers;
```

container는 `TextBuffer` 객체를 값으로 저장합니다.

삽입과 내부 관리 과정에서 원소의 복사 생성자나 복사 대입 연산자가 사용될 수 있습니다.

따라서 `TextBuffer`가 heap memory를 직접 소유한다면 깊은 복사와 안전한 소멸을 제공해야 합니다.

예를 들어 compiler 기본 복사를 그대로 사용하면 pointer 주소만 복사되어 두 원소가 같은 memory를 소유하게 될 수 있습니다.

즉, container에 저장되는 값 타입은 container가 몇 번 복사할지에 의존하지 않고 복사가 올바르게 작동해야 합니다.

## C++98 container와 복사 가능성

C++98에서는 현대 C++의 이동 전용 타입을 container에 넣는 방식에 의존할 수 없습니다.

표준 container는 원소를 복사하는 연산을 사용하므로 값으로 저장하는 타입은 필요한 복사 동작을 제공해야 합니다.

예:

```cpp
std::vector<TextBuffer> buffers;
buffers.push_back(buffer);
```

`push_back`은 `buffer`를 container 내부 원소로 복사합니다.

따라서 owning resource를 가진 값 타입이라면 Rule of Three를 올바르게 구현해야 합니다.

## pointer를 저장하면 pointee는 자동 관리되지 않습니다

다음 container는 `Handler` 객체를 저장하는 것이 아니라 pointer 값을 저장합니다.

```cpp
std::map<std::string, Handler *> handlers;
```

container가 관리하는 것은 다음과 같은 주소 값입니다.

```text
Handler*
```

container가 파괴될 때 pointer 원소 자체는 사라지지만:

```cpp
delete handler;
```

가 자동으로 실행되는 것은 아닙니다.

따라서 pointee를 누가 소유하는지 별도의 규칙이 필요합니다.

예를 들어 Router가 소유한다면:

```text
- 삽입 성공 후 Router가 Handler*를 소유한다.
- Router 소멸 시 모든 Handler*를 delete한다.
- 등록 실패 시 아직 소유권이 넘어오지 않은 pointer를 정리한다.
- Router 복사 시 shallow copy가 일어나지 않게 한다.
```

같은 계약이 필요합니다.

## 값 container와 pointer container의 차이

다음을 구분합니다.

### 값 저장

```cpp
std::vector<TextBuffer> values;
```

container 내부에 실제 `TextBuffer` 객체가 존재합니다.

container가 원소의 생성·복사·소멸을 관리합니다.

### pointer 저장

```cpp
std::vector<TextBuffer *> values;
```

container 내부에는 `TextBuffer *`라는 주소 값만 존재합니다.

가리키는 실제 `TextBuffer` 객체의 수명은 별도 소유자가 관리해야 합니다.

container가 pointer를 저장한다는 사실만으로 pointee의 ownership이 정해지지 않습니다.

## STL algorithm

STL algorithm은 container 자체보다 iterator 범위를 입력으로 받는 경우가 많습니다.

예:

```cpp
std::find(
    values.begin(),
    values.end(),
    target);
```

이 구조 덕분에 같은 algorithm을 여러 container나 iterator 범위에 적용할 수 있습니다.

C++98에서 먼저 확인할 수 있는 대표 algorithm은 다음과 같습니다.

- `std::find`
- `std::find_if`
- `std::copy`
- `std::transform`
- `std::sort`
- `std::stable_sort`
- `std::accumulate`

`std::accumulate`는 `<numeric>`에 선언되어 있고, 나머지 여러 algorithm은 주로 `<algorithm>`에 선언되어 있습니다.

## algorithm을 쓰기 전에 전제 조건을 확인합니다

algorithm은 단순히 함수 이름이 맞는다고 사용할 수 있는 것이 아닙니다.

확인해야 할 내용은 다음과 같습니다.

- 필요한 iterator category
- 입력 범위가 유효한가
- 출력 범위가 충분한가
- 비교 함수가 요구 조건을 만족하는가
- 입력과 출력 범위가 겹쳐도 되는 algorithm인가

예를 들어:

```cpp
std::copy(
    source.begin(),
    source.end(),
    destination.begin());
```

를 사용하려면 `destination`에 필요한 수의 원소를 쓸 수 있는 유효한 범위가 이미 존재해야 합니다.

빈 `destination`에 단순히 `begin()`을 넘긴다고 자동으로 크기가 늘어나지는 않습니다.

필요하다면 크기를 먼저 확보하거나 적절한 inserter를 사용해야 합니다.

## `std::stable_sort`

```cpp
std::stable_sort(
    records.begin(),
    records.end(),
    RecordLess());
```

`std::stable_sort`는 정렬 결과에서 비교상 동등한 원소의 기존 상대적 순서를 보존합니다.

예를 들어 두 record가 comparator 기준으로 동등하다면 입력에서 먼저 있던 record가 정렬 뒤에도 먼저 유지됩니다.

하지만 이 algorithm은 random access iterator를 요구하므로 `std::vector`, `std::deque` 같은 container에는 적용할 수 있지만 `std::list`나 `std::map` iterator에는 직접 사용할 수 없습니다.

## 비교 함수와 strict weak ordering

정렬이나 associative container의 비교 함수는 **strict weak ordering**을 만족해야 합니다.

대표적인 성질을 이해하기 쉽게 정리하면 다음과 같습니다.

### 자기 자신보다 작다고 하면 안 됩니다

```cpp
comp(x, x) == false
```

이어야 합니다.

### 서로 동시에 작다고 하면 안 됩니다

```cpp
comp(a, b) == true
```

라면 동시에:

```cpp
comp(b, a) == true
```

가 되어서는 안 됩니다.

### 비교 관계가 순환하면 안 됩니다

다음과 같은 관계를 만들면 안 됩니다.

```text
a < b
b < c
c < a
```

비교 함수가 이런 규칙을 깨뜨리면 정렬 algorithm이나 ordered container가 올바르게 동작한다는 전제를 잃습니다.

## 동등성과 `operator==`는 같은 개념이 아닐 수 있습니다

strict weak ordering에서 두 값이 비교상 동등하다는 뜻은 보통 다음과 같습니다.

```cpp
!comp(a, b) && !comp(b, a)
```

이것이 반드시:

```cpp
a == b
```

와 같은 의미일 필요는 없습니다.

예를 들어 이름 길이만 비교하는 comparator라면 서로 다른 문자열이라도 길이가 같으면 comparator 기준으로 동등할 수 있습니다.

```cpp
struct LengthLess {
    bool operator()(
        const std::string &left,
        const std::string &right) const
    {
        return left.size() < right.size();
    }
};
```

`"cat"`과 `"dog"`는 문자열 값은 다르지만 이 comparator 기준으로는 서로 어느 쪽도 작지 않습니다.

ordered container에서 key 동등성도 comparator를 기준으로 판단될 수 있으므로 이 차이를 이해해야 합니다.

## function object

C++98에는 lambda가 없습니다.

비교 함수나 algorithm에 전달할 동작을 객체로 표현하려면 function object를 사용할 수 있습니다.

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

사용:

```cpp
std::stable_sort(
    records.begin(),
    records.end(),
    RecordLess());
```

`RecordLess()`는 임시 함수 객체이고 algorithm은 이를 함수처럼 호출합니다.

```cpp
comparator(left, right);
```

실제로는:

```cpp
comparator.operator()(left, right);
```

형태의 호출입니다.

## 상태를 가진 function object

비교 기준에 설정값이 필요하다면 멤버로 저장할 수 있습니다.

```cpp
class RecordLess {
public:
    explicit RecordLess(bool descending)
        : descending_(descending)
    {
    }

    bool operator()(
        const Record &left,
        const Record &right) const
    {
        if (descending_)
            return right.value < left.value;

        return left.value < right.value;
    }

private:
    bool descending_;
};
```

사용:

```cpp
std::stable_sort(
    records.begin(),
    records.end(),
    RecordLess(true));
```

C++11 lambda capture 없이도 동작과 상태를 함께 전달할 수 있습니다.

## algorithm과 명시적인 loop 중 선택

STL algorithm을 사용할 수 있다고 해서 항상 algorithm이 더 읽기 쉬운 것은 아닙니다.

단순 검색이나 변환은 algorithm이 명확할 수 있습니다.

예:

```cpp
std::find(
    values.begin(),
    values.end(),
    target);
```

반면 다음 조건이 동시에 얽혀 있다면 명시적인 loop가 더 이해하기 쉬울 수 있습니다.

- 여러 종류의 상태 변경
- 여러 `break` 조건
- 중간 오류 처리
- 서로 다른 container를 동시에 갱신
- iteration 도중 소유권 이전

목표는 algorithm 사용 자체가 아니라 코드의 전제와 상태 변화가 명확한 것입니다.

## specialization

template의 일반 동작이 특정 타입에서 완전히 달라야 할 때 specialization을 사용할 수 있습니다.

예를 들어 class template 전체 specialization의 형태는 다음과 같습니다.

```cpp
template <class T>
class Printer {
public:
    void print(const T &value);
};

template <>
class Printer<bool> {
public:
    void print(const bool &value);
};
```

`Printer<bool>`은 일반 `Printer<T>`와 다른 구현을 사용할 수 있습니다.

## partial specialization

class template에는 partial specialization을 사용할 수 있습니다.

개념적인 예:

```cpp
template <class T>
class Traits {
};

template <class T>
class Traits<T *> {
};
```

두 번째 정의는 모든 pointer 타입에 대한 부분 특수화입니다.

반면 function template에는 같은 방식의 partial specialization을 직접 적용할 수 없습니다.

function template에서 일부 타입 집합만 다른 동작이 필요하다면 overload가 더 자연스러운 경우가 많습니다.

## function template은 overload를 먼저 검토합니다

예를 들어 일반 template과 pointer용 동작을 구분하고 싶다면 specialization을 복잡하게 사용하기보다 overload로 표현할 수 있습니다.

```cpp
template <class T>
void printValue(const T &value)
{
    std::cout << value;
}

template <class T>
void printValue(T *value)
{
    if (value != 0)
        std::cout << *value;
}
```

실제 설계에서는 overload resolution이 의도대로 되는지 확인해야 하지만, function template partial specialization을 시도하는 것보다 언어 규칙에 맞는 접근입니다.

## C++98의 `> >` 표기

C++98에서는 중첩된 template argument의 닫는 `>`를 붙여 쓰면 parser가 `>>` 연산자로 해석할 수 있습니다.

따라서 다음처럼 공백을 두는 표기가 안전합니다.

```cpp
std::vector<std::vector<int> > matrix;
```

C++11 이후에는:

```cpp
std::vector<std::vector<int>> matrix;
```

도 허용되지만 C++98 문법을 목표로 한다면 `> >` 형태를 사용합니다.

이 차이는 Modern C++ 코드를 C++98로 옮길 때 자주 발생하는 단순 문법 오류입니다.

## template과 STL 오류를 진단하는 순서

template 관련 compiler 오류는 실제 원인보다 훨씬 길게 출력될 수 있습니다.

다음 순서로 확인하면 도움이 됩니다.

```text
1. 내가 호출한 template 또는 algorithm 위치를 찾습니다.
2. template 인자에 실제로 어떤 타입이 들어갔는지 확인합니다.
3. 그 template이 요구하는 연산을 적습니다.
4. 해당 타입이 그 연산을 지원하는지 확인합니다.
5. iterator category와 const 여부를 확인합니다.
6. 긴 표준 library 내부 오류보다 최초 사용자 코드 오류를 우선 봅니다.
```

예를 들어 `std::sort`에 `std::list` iterator를 넘겼다면 표준 library 내부에서 복잡한 연산 오류가 이어질 수 있지만 실제 원인은 "random access iterator가 필요한 algorithm에 bidirectional iterator를 전달했다"는 것입니다.

## 자주 놓치는 문제

- template 정의를 `.cpp`에 두고 다른 번역 단위에서 사용해 link 오류가 발생합니다.
- 명시적 instantiation을 사용하면서 지원 타입 목록에 새 타입을 추가하지 않습니다.
- template이 요구하는 `operator<`, 복사, iterator 연산 등을 문서화하지 않습니다.
- dependent type 앞의 `typename`을 빠뜨립니다.
- 모든 iterator가 `+`, `-`, `[]`를 지원한다고 생각합니다.
- `std::sort`나 `std::stable_sort`를 `std::list` iterator에 사용하려고 합니다.
- `end()`를 마지막 원소라고 생각하고 역참조합니다.
- 빈 custom container에서 null pointer에 pointer arithmetic을 수행합니다.
- const container에서 mutable iterator를 반환합니다.
- `const_iterator`와 `const iterator`를 같은 의미로 생각합니다.
- `vector` reallocation 뒤 이전 iterator, pointer, reference를 사용합니다.
- `vector` 중간 insert/erase 뒤 변경 위치 이후의 iterator를 계속 사용합니다.
- container마다 iterator 무효화 규칙이 같다고 생각합니다.
- pointer container가 pointee 객체의 수명까지 자동으로 관리한다고 생각합니다.
- C++98 container에 저장되는 owning 값 타입의 복사 의미를 정의하지 않습니다.
- 빈 destination에 `std::copy`를 호출하면 container 크기가 자동으로 늘어난다고 생각합니다.
- 비교 함수가 같은 값에 `true`를 반환합니다.
- comparator 기준 동등성과 `operator==`를 항상 같은 의미로 생각합니다.
- function template에 partial specialization을 직접 적용하려고 합니다.
- C++98 코드에서 중첩 template의 `>>` 표기를 그대로 사용합니다.

## 완료 기준

다음 항목을 설명하고 코드에서 적용할 수 있으면 이 범위의 목표를 달성한 것입니다.

- 함수·클래스 template을 C++98 문법으로 작성합니다.
- template이 실제 타입에 요구하는 연산과 의미를 명시합니다.
- template 정의가 사용하는 번역 단위에서 보여야 하는 이유를 설명합니다.
- 헤더 정의와 명시적 instantiation 방식의 차이를 설명합니다.
- dependent name이 무엇인지 설명하고 dependent type 앞에 `typename`을 사용합니다.
- iterator category에 따라 가능한 연산이 다르다는 점을 설명합니다.
- STL의 `[begin, end)` 반열린 범위와 빈 범위를 안전하게 처리합니다.
- custom pointer iterator에서 빈 상태의 pointer arithmetic을 피합니다.
- mutable iterator와 const iterator를 구분하고 const overload를 제공합니다.
- `const_iterator`와 const iterator 객체 자체의 차이를 설명합니다.
- `vector`, `map` 등 주요 container의 iterator·pointer·reference 무효화 규칙을 구분합니다.
- erase하면서 순회할 때 container가 반환하는 유효 iterator를 사용합니다.
- container에 값으로 저장하는 객체의 복사·대입·소멸 의미를 올바르게 정의합니다.
- pointer container와 pointee ownership을 별도로 관리합니다.
- algorithm이 요구하는 iterator category와 출력 범위를 확인합니다.
- comparator가 strict weak ordering을 만족해야 하는 이유를 설명합니다.
- function object로 C++98에서 lambda가 담당하던 간단한 동작을 표현합니다.
- class template specialization과 function overload를 상황에 맞게 구분합니다.
- C++98 중첩 template에서 `> >` 표기를 사용합니다.
