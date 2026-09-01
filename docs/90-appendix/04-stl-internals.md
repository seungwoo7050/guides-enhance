# STL 내부 동작

## 사용 시점

이 문서는 표준 container를 직접 다시 구현하기 위한 일반 지침이 아닙니다.

다음과 같은 주제를 이해해야 할 때 참고합니다.

- raw storage와 실제 객체 수명의 차이
- `size`와 `capacity`의 의미
- `vector` 재할당 중 예외 안전성
- iterator/reference/pointer 무효화
- self-aliasing 입력
- `map`과 같은 node 기반 container의 성질
- algorithm이 요구하는 iterator와 비교 함수 조건

일반 application에서는 직접 container를 구현하기보다 표준 container를 우선 사용합니다.

---

## 메모리와 객체는 다릅니다

다음 코드는 `T` 객체 여러 개를 담을 수 있는 **raw storage**를 확보합니다.

```cpp
std::allocator<T> allocator;
T *memory = allocator.allocate(capacity);
```

이 시점에 확보된 영역은 `T` 객체를 놓을 수 있는 크기와 정렬 조건을 만족하지만, 그 안에 `T` 객체가 자동으로 생성된 것은 아닙니다.

즉 다음 두 개념을 구분해야 합니다.

```text
storage 확보
≠
객체 생성
```

`T` 객체의 수명은 해당 위치에 객체를 실제로 생성했을 때 시작됩니다.

C++98의 `std::allocator<T>`를 사용한다면 다음과 같이 생성할 수 있습니다.

```cpp
allocator.construct(memory + size, value);
++size;
```

개념적으로 `construct()`는 이미 확보된 storage의 특정 위치에 placement construction을 수행합니다.

중요한 순서는 다음과 같습니다.

```text
1. 객체 생성 시도
2. 생성 성공
3. size 증가
```

다음처럼 `size`를 먼저 증가시키면 안 됩니다.

```cpp
++size;
allocator.construct(memory + size - 1, value);
```

생성자가 예외를 던졌을 때 `size`가 실제 생성된 객체 수와 달라질 수 있기 때문입니다.

---

## destruction과 deallocation도 다릅니다

객체의 수명을 끝내는 것과 storage 자체를 반환하는 것도 별개의 작업입니다.

```cpp
allocator.destroy(memory + i);
```

는 해당 위치의 `T` 객체 destructor를 호출합니다.

반면:

```cpp
allocator.deallocate(memory, capacity);
```

는 raw storage를 allocator에 반환합니다.

따라서 올바른 정리 순서는 다음과 같습니다.

```text
생성된 객체 destroy
→ storage deallocate
```

storage를 먼저 반환한 뒤 객체 destructor를 호출하면 이미 유효하지 않은 메모리에 접근하게 됩니다.

보통 생성된 원소를 역순으로 파괴합니다.

```cpp
while (size > 0) {
    --size;
    allocator.destroy(memory + size);
}

allocator.deallocate(memory, capacity);
```

역순 destruction은 container 원소가 서로 의존할 가능성을 줄이고, stack과 유사한 수명 순서를 유지하는 데 도움이 됩니다.

---

## `vector`의 세 핵심 값

동적 배열 형태의 container는 보통 다음 세 값을 관리합니다.

```text
data
size
capacity
```

의미는 다음과 같습니다.

```text
data
→ 확보한 storage의 시작 위치

size
→ 실제로 생성되어 살아 있는 원소 수

capacity
→ 현재 storage에 추가 allocation 없이 놓을 수 있는 최대 원소 수
```

항상 다음 invariant가 성립해야 합니다.

```text
0 <= size <= capacity
```

그리고 `data`가 실제 storage를 가리키는 경우:

```text
[data, data + size)
→ 실제 T 객체가 존재

[data + size, data + capacity)
→ T 객체는 없고 raw storage만 존재
```

예를 들어:

```text
capacity = 8
size     = 3
```

이라면 개념적으로:

```text
index:   0 1 2 3 4 5 6 7
         ├─────┤
         객체 존재

               ├─────────┤
               storage만 존재
```

`size`보다 큰 위치를 단순히 "아직 사용하지 않은 T 객체"라고 생각하면 안 됩니다.

그 위치에는 아직 `T` 객체의 수명이 시작되지 않았습니다.

---

## 빈 container와 null pointer

간단한 구현에서는 빈 container에서 다음처럼 표현할 수 있습니다.

```text
data = 0
size = 0
capacity = 0
```

이 경우 불필요하게 다음과 같은 pointer 산술을 수행하지 않는 편이 안전합니다.

```cpp
data + 0
```

null pointer는 실제 배열 storage를 가리키는 pointer가 아니기 때문입니다.

따라서 구현은 보통 다음처럼 상태를 분리해서 처리합니다.

```cpp
if (size != 0) {
    // data가 실제 storage를 가리키는 전제에서 접근
}
```

또는 처음부터 non-null empty storage를 사용하는 별도 설계를 선택할 수도 있습니다.

어느 방식을 택하든 container invariant를 일관되게 유지해야 합니다.

---

## `size`와 `capacity`를 혼동하면 생기는 문제

다음 코드는 잘못된 접근입니다.

```cpp
for (size_t i = 0; i < capacity; ++i) {
    allocator.destroy(data + i);
}
```

`capacity`까지 모든 위치에 실제 객체가 존재한다고 가정하기 때문입니다.

실제로 destroy할 수 있는 범위는 생성에 성공한 원소뿐입니다.

```cpp
for (size_t i = size; i > 0; --i) {
    allocator.destroy(data + (i - 1));
}
```

이 구분은 특히 생성 도중 예외가 발생했을 때 중요합니다.

---

## capacity 증가

`push_back()` 시 `size == capacity`이면 새로운 storage가 필요합니다.

동적 배열 구현은 보통 capacity를 일정 비율로 증가시켜 매번 한 칸씩 allocation하는 비용을 피합니다.

예를 들어 단순 학습 구현에서 다음 정책을 사용할 수 있습니다.

```text
0 → 1 → 2 → 4 → 8 → 16 ...
```

즉 대략 두 배씩 증가합니다.

이런 geometric growth를 사용하면 개별 `push_back()`은 때때로 비싼 재할당을 수행하지만, 많은 `push_back()`을 연속 실행했을 때 평균 비용을 낮출 수 있습니다.

이를 **amortized constant time**이라고 표현합니다.

중요한 점은 실제 표준 library가 반드시 두 배 성장해야 하는 것은 아니라는 것입니다.

표준은 관찰 가능한 동작과 복잡도 조건을 요구하지만, 구체적인 growth factor는 구현 세부사항입니다.

따라서 application code에서 다음과 같이 가정하면 안 됩니다.

```text
capacity는 항상 정확히 2배 증가한다
```

---

## capacity overflow 확인

capacity 증가 계산 자체가 integer overflow를 일으키면 안 됩니다.

예를 들어:

```cpp
new_capacity = capacity * 2;
```

를 수행하기 전에 현재 값이 allocator가 표현할 수 있는 최대 크기를 넘지 않는지 확인해야 합니다.

단순한 예:

```cpp
if (capacity > allocator.max_size() / 2)
    throw std::length_error("capacity overflow");
```

실제 구현에서는 현재 필요한 최소 크기도 고려해야 합니다.

예를 들어 한 원소를 추가하려는데 기존 `capacity`가 0이라면:

```text
new_capacity = 1
```

처럼 별도 초기값이 필요합니다.

핵심은 다음 순서입니다.

```text
필요한 최소 capacity 계산
→ overflow/max_size 검사
→ 새 capacity 결정
→ allocation
```

---

## 재할당이 필요한 이유

`vector` 형태의 container는 원소를 연속된 memory 영역에 배치합니다.

현재 storage가 가득 차면 뒤에 메모리를 이어 붙일 수 있다는 보장이 없습니다.

따라서 일반적으로 더 큰 새 storage를 확보한 뒤 기존 원소를 새 위치에 다시 생성합니다.

```text
기존 storage
[A][B][C]

새 storage
[ ][ ][ ][ ][ ][ ]
```

복사가 끝나면:

```text
기존 storage
[A][B][C]

새 storage
[A][B][C][ ][ ][ ]
```

그 뒤에만 기존 storage를 제거합니다.

---

## 재할당과 strong exception guarantee

`push_back()` 같은 연산에서 strong guarantee를 목표로 한다면, 예외가 발생했을 때 기존 container의 값이 그대로 유지되어야 합니다.

즉:

```text
연산 성공
→ 새 상태

연산 실패
→ 연산 전 상태 유지
```

를 목표로 합니다.

재할당이 필요한 경우 기본적인 순서는 다음과 같습니다.

```text
새 storage allocate
→ 기존 원소를 새 storage에 복사 생성
→ 추가할 새 원소 생성
→ 모든 생성 성공 확인
→ 기존 원소 destroy
→ 기존 storage deallocate
→ data/size/capacity를 새 storage 상태로 교체
```

핵심은 **새 상태가 완성되기 전까지 기존 상태를 파괴하지 않는 것**입니다.

---

## 재할당 중 예외 처리

예를 들어 기존 원소가 세 개 있다고 가정합니다.

```text
[A][B][C]
```

새 storage로 복사하는 도중 `C`의 copy constructor가 예외를 던질 수 있습니다.

```text
새 storage

[A'][B'][생성 실패]
```

이 경우 새 storage에서 실제로 생성된 객체는 `A'`, `B'`뿐입니다.

정리 순서는 다음과 같습니다.

```text
B' destroy
→ A' destroy
→ 새 storage deallocate
→ 예외 재전파
```

기존 storage의:

```text
[A][B][C]
```

는 건드리지 않습니다.

따라서 container는 연산 전 상태를 유지할 수 있습니다.

이때 별도의 `constructed_count` 같은 값을 두면 cleanup 범위를 정확히 추적할 수 있습니다.

예:

```cpp
size_t constructed = 0;

try {
    for (; constructed < size; ++constructed)
        allocator.construct(new_data + constructed,
                            data[constructed]);
}
catch (...) {
    while (constructed > 0) {
        --constructed;
        allocator.destroy(new_data + constructed);
    }

    allocator.deallocate(new_data, new_capacity);
    throw;
}
```

---

## 왜 생성된 원소 수를 따로 추적해야 하는가

예외가 발생한 순간 새 storage 전체가 객체로 채워진 것은 아닙니다.

따라서 다음처럼 하면 안 됩니다.

```cpp
for (size_t i = 0; i < new_capacity; ++i)
    allocator.destroy(new_data + i);
```

아직 생성되지 않은 위치에 destructor를 호출하기 때문입니다.

cleanup은 반드시:

```text
실제로 생성 성공한 객체만
```

대상으로 해야 합니다.

---

## self-aliasing 입력

다음 코드는 정상적인 container 사용입니다.

```cpp
values.push_back(values[0]);
```

여기서 `push_back()`에 전달한 `value`가 container 내부 원소를 가리키고 있습니다.

이를 **self-aliasing** 상황이라고 볼 수 있습니다.

예를 들어 parameter가 다음과 같다고 가정합니다.

```cpp
void push_back(const T &value);
```

호출:

```cpp
values.push_back(values[0]);
```

에서 `value`는 `values[0]`을 참조합니다.

---

## self-aliasing이 재할당과 만나는 경우

capacity가 남아 있으면 단순히 끝 위치에 복사 생성할 수 있습니다.

문제는 재할당이 필요한 경우입니다.

잘못된 순서:

```text
기존 storage destroy
→ 기존 storage deallocate
→ value를 이용해 새 원소 생성
```

`value`가 기존 storage 내부 원소를 참조하고 있었다면, 첫 단계에서 이미 dangling reference가 됩니다.

즉:

```cpp
values.push_back(values[0]);
```

의 `values[0]` 참조가 새 원소를 생성하기 전에 무효가 됩니다.

따라서 새 원소를 만들기 위해 필요한 입력을 모두 사용하기 전까지 기존 storage를 유지해야 합니다.

기본적으로 다음 순서가 안전합니다.

```text
새 storage 확보
→ 기존 storage를 유지한 채 필요한 복사 수행
→ 새 원소까지 생성 성공
→ 이후 기존 storage 파괴
```

self-aliasing 문제는 "parameter가 외부 객체만 참조한다"고 가정했기 때문에 발생합니다.

container API는 parameter가 **자기 자신의 원소를 가리킬 수도 있다**는 가능성을 고려해야 합니다.

---

## 복사 생성

container copy constructor는 새 storage를 확보한 뒤 원소를 하나씩 복사 생성합니다.

개념적으로:

```cpp
Vector(const Vector &other)
    : data_(0),
      size_(0),
      capacity_(0)
{
    // storage 확보
    // other의 원소를 하나씩 construct
}
```

중간 원소의 copy constructor가 예외를 던질 수 있으므로, 지금까지 생성한 객체 수를 추적해야 합니다.

```text
원소 0 생성 성공
원소 1 생성 성공
원소 2 생성 실패
```

cleanup:

```text
원소 1 destroy
→ 원소 0 destroy
→ 새 storage deallocate
→ 예외 재전파
```

아직 완전히 생성되지 않은 `Vector` 객체 자체의 destructor에 cleanup을 맡길 수 없다는 점도 중요합니다.

constructor가 완료되기 전에 예외가 발생하면 그 객체의 destructor는 호출되지 않습니다.

따라서 constructor 내부에서 확보한 raw resource는 constructor 자체가 정리해야 합니다.

---

## 복사 대입

copy assignment는 이미 유효한 객체에 새로운 값을 덮어씁니다.

즉 다음 두 자원을 동시에 고려해야 합니다.

```text
기존 this의 resource
other에서 복사해 올 새 resource
```

한 가지 단순한 구현 전략은 **copy-and-swap**입니다.

```cpp
Vector &operator=(Vector other)
{
    swap(other);
    return *this;
}
```

순서는 다음과 같습니다.

```text
1. parameter other를 복사 생성
2. 복사 성공
3. this와 other의 내부 상태 swap
4. 함수 종료
5. local other destructor가 이전 this 자원 정리
```

복사 생성이 실패하면 함수 본문에 들어오기 전에 예외가 발생하므로 기존 `this`는 그대로 유지됩니다.

이 때문에 strong guarantee를 구현하기 쉬워집니다.

---

## copy-and-swap과 allocator

allocator까지 저장하는 container에서는 단순히 모든 멤버를 swap해도 되는지 별도로 확인해야 합니다.

allocator는 "어떤 storage를 누가 deallocate할 수 있는가"와 연결될 수 있기 때문입니다.

잘못 설계하면:

```text
allocator A가 allocate한 storage
→ allocator B가 deallocate
```

같은 문제가 생길 수 있습니다.

단순 C++98 학습 구현이라면 범위를 명확히 제한할 수 있습니다.

예:

```text
std::allocator<T>만 사용
allocator는 별도 state를 갖지 않는다고 가정
```

이렇게 구현 범위를 먼저 정하면 allocator propagation 같은 복잡한 문제까지 불필요하게 확장하지 않아도 됩니다.

---

## iterator란 무엇인가

iterator는 container 원소 위치를 나타내는 객체입니다.

`vector<T>::iterator`는 구현에 따라 pointer와 유사할 수 있지만, application에서는 구체 구현을 가정하지 않습니다.

iterator뿐 아니라 다음도 모두 원소 위치와 수명에 영향을 받습니다.

```text
iterator
reference
pointer
```

container 변경 연산이 내부 storage나 node를 바꾸면 이들이 무효가 될 수 있습니다.

---

## `vector` 재할당과 iterator 무효화

`vector`가 재할당되면 모든 원소가 새 storage로 이동합니다.

```text
old storage:
[A][B][C]

new storage:
[A'][B'][C'][ ][ ]
```

따라서 기존 storage를 가리키던:

```text
iterator
reference
pointer
```

는 모두 무효가 됩니다.

예:

```cpp
std::vector<int>::iterator it = values.begin();

values.push_back(42);   // 재할당 발생 가능

// 재할당이 있었다면 it 사용 불가
```

`push_back()` 이후 iterator를 계속 사용해야 한다면 capacity가 충분한지에 의존하기보다, 필요한 위치를 index 등으로 보존하고 연산 뒤 iterator를 다시 얻는 방식이 더 명확할 수 있습니다.

---

## 재할당이 없는 `push_back()`

capacity가 충분하여 재할당이 발생하지 않았다면 기존 원소를 가리키는 iterator/reference/pointer는 유지됩니다.

하지만 이전의 `end()`는 더 이상 새 끝 위치를 나타내지 않습니다.

예:

```text
before:

[A][B][ ][ ]
      ^
      old end

push_back(C)

[A][B][C][ ]
         ^
         new end
```

따라서 이전 `end()` iterator는 무효가 됩니다.

정리하면 `push_back()`에서:

```text
재할당 발생
→ 모든 iterator/reference/pointer 무효

재할당 없음
→ 기존 원소 iterator/reference/pointer 유지
→ 기존 end()는 무효
```

---

## `vector`의 중간 삽입/삭제

`vector`의 중간 위치에 원소를 삽입하거나 삭제하면 뒤쪽 원소가 이동할 수 있습니다.

따라서 재할당이 없더라도 변경 위치 이후의 iterator/reference가 무효가 될 수 있습니다.

예:

```text
[A][B][C][D]

B 앞에 X 삽입

[A][X][B][C][D]
```

`B`, `C`, `D`가 이전과 같은 storage 주소에 그대로 있다는 보장이 없습니다.

따라서 `vector`에서는 단순히 "재할당 여부"만이 아니라 **변경 위치도 iterator 수명에 영향을 준다**는 점을 기억해야 합니다.

---

## `map` iterator 무효화

`std::map`은 일반적으로 각 원소가 독립된 node에 저장되는 tree 구조로 구현됩니다.

삽입할 때 다른 기존 node 자체를 이동할 필요가 없으므로, 일반적으로 insert는 기존 원소의 iterator/reference를 무효화하지 않습니다.

예:

```cpp
std::map<int, std::string>::iterator it = m.find(10);

m.insert(std::make_pair(20, "twenty"));

// it는 기존 원소가 삭제되지 않았다면 계속 유효
```

반면 원소를 erase하면 그 원소를 가리키던 iterator/reference는 더 이상 유효하지 않습니다.

```text
erase된 node를 가리키는 iterator
→ 무효

다른 node를 가리키는 iterator
→ 유지
```

이 차이는 `vector`와 node 기반 container의 중요한 성질 차이입니다.

---

## iterator를 저장하는 API

어떤 객체가 container iterator를 멤버로 오래 저장한다면, iterator를 제공한 container의 변경 연산까지 함께 고려해야 합니다.

예:

```cpp
class Cursor {
private:
    std::vector<Item>::iterator current_;
};
```

이 구조에서 외부 코드가 `vector`를 재할당시키면 `current_`가 dangling iterator가 될 수 있습니다.

따라서 iterator를 장기간 저장하는 API라면 다음을 문서화해야 합니다.

```text
어떤 container를 참조하는가
어떤 변경 연산까지 iterator가 유효한가
container가 먼저 파괴되면 어떻게 되는가
```

경우에 따라 iterator 대신 index나 key를 저장하는 편이 더 안전할 수 있습니다.

---

## `map` 내부

`std::map`은 key 정렬 순서를 유지하는 associative container입니다.

일반적인 구현은 balanced search tree를 사용하지만, C++ 표준은 특정 tree 종류를 요구하지 않습니다.

즉 다음과 같이 가정해서는 안 됩니다.

```text
std::map은 반드시 red-black tree다
```

구현자는 다른 자료구조를 사용할 수도 있습니다.

중요한 것은 표준이 요구하는 **관찰 가능한 동작과 복잡도 특성**입니다.

대표적으로:

```text
검색
삽입
삭제
→ logarithmic complexity

iterator 순회
→ key ordering에 따른 순서
```

삽입 시 기존 원소가 node 자체로 유지되므로 기존 iterator 안정성이 `vector`보다 높습니다.

---

## node 기반 container의 비용

node 기반 tree는 원소마다 별도 allocation을 수행하는 구현이 일반적입니다.

따라서 다음 비용이 생길 수 있습니다.

```text
node별 allocation overhead
pointer field
낮은 memory locality
cache miss 증가 가능성
```

반대로 정렬된 연속 memory 구조는 lookup마다 이동 비용이나 insertion 비용이 더 클 수 있지만, 순차 접근에서는 locality가 좋을 수 있습니다.

그래서 데이터가 작거나 다음 조건이라면 정렬된 `vector` 계열 구조가 더 적합할 수도 있습니다.

```text
삽입이 드묾
조회가 많음
순차 iteration이 중요함
데이터 크기가 작음
```

하지만 이는 workload에 따라 달라집니다.

실제 application에서는 추측보다 측정 결과를 기준으로 선택합니다.

---

## algorithm과 iterator category

STL algorithm은 모든 iterator에 같은 연산을 요구하지 않습니다.

대표적인 iterator category는 다음과 같습니다.

```text
input iterator
output iterator
forward iterator
bidirectional iterator
random-access iterator
```

뒤로 갈수록 더 많은 연산을 지원합니다.

예를 들어 `std::sort`는 **random-access iterator**를 요구합니다.

따라서 다음은 가능합니다.

```cpp
std::vector<int> values;
std::sort(values.begin(), values.end());
```

`vector` iterator는 random-access iterator이기 때문입니다.

반면 다음은 사용할 수 없습니다.

```cpp
std::list<int> values;
std::sort(values.begin(), values.end()); // 불가
```

`std::list` iterator는 bidirectional iterator이지 random-access iterator가 아닙니다.

`std::list`는 자체 정렬 기능을 제공합니다.

```cpp
values.sort();
```

즉 algorithm 이름만 보고 사용할 수 있는 것이 아니라 **iterator가 algorithm의 요구사항을 만족하는지** 확인해야 합니다.

---

## 비교 함수와 strict weak ordering

정렬과 associative container는 비교 함수가 일관된 순서를 제공한다고 가정합니다.

예:

```cpp
struct Less {
    bool operator()(const Item &a,
                    const Item &b) const;
};
```

비교 함수는 **strict weak ordering**을 만족해야 합니다.

기본적으로 다음 성질을 이해하면 좋습니다.

### 자기 자신보다 작을 수 없음

```text
comp(x, x) == false
```

### 비대칭성

```text
comp(a, b) == true
→ comp(b, a) == false
```

### 추이성

```text
comp(a, b) == true
comp(b, c) == true
→ comp(a, c) == true
```

그리고 두 값이 서로보다 작지 않으면 비교 관점에서 동등한 그룹으로 취급됩니다.

```text
!comp(a, b) && !comp(b, a)
```

이 관계도 일관되게 유지되어야 합니다.

---

## 잘못된 comparator 예

다음 comparator는 문제가 있습니다.

```cpp
bool lessEqual(int a, int b)
{
    return a <= b;
}
```

자기 자신에 대해:

```cpp
lessEqual(3, 3) == true
```

가 되므로 strict ordering 조건을 위반합니다.

정렬 comparator는 일반적으로 다음처럼 "엄격히 작다" 관계여야 합니다.

```cpp
bool lessThan(int a, int b)
{
    return a < b;
}
```

또한 comparator가 호출 중 외부 상태에 따라 결과를 바꾸면 순서가 일관되지 않을 수 있습니다.

예를 들어 동일한 `a`, `b`에 대해 어떤 때는 true, 어떤 때는 false를 반환하면 algorithm이 요구하는 전제가 깨집니다.

---

## `map`에서 comparator가 중요한 이유

`std::map`은 comparator가 정의하는 순서를 이용해 key 위치를 결정합니다.

두 key `a`, `b`가 다음을 만족하면:

```text
!comp(a, b) && !comp(b, a)
```

`map`은 비교 관점에서 둘을 같은 key equivalence class로 취급합니다.

이는 반드시 `operator==`와 같은 의미일 필요는 없습니다.

따라서 custom comparator를 작성할 때:

```text
ordering
key uniqueness 판단
검색 결과
```

가 모두 comparator 정의에 영향을 받는다는 점을 알아야 합니다.

---

## exception safety의 기본 수준

container 연산의 예외 안전성을 설명할 때 다음 용어를 구분하면 유용합니다.

### no-throw guarantee

```text
연산이 예외를 던지지 않음
```

### strong guarantee

```text
실패하면 연산 전 상태 유지
```

### basic guarantee

```text
실패해도 객체 invariant는 유지되지만
값 자체는 일부 변경될 수 있음
```

### no guarantee

```text
실패 뒤 상태를 신뢰하기 어려움
```

직접 container를 구현한다면 각 연산이 어떤 수준을 제공하는지 명확히 해야 합니다.

이 문서에서 설명한 새 storage를 먼저 완성한 뒤 기존 storage를 버리는 방식은 strong guarantee를 구현할 때 자주 사용되는 기본 패턴입니다.

---

## 직접 구현할 때 필요한 책임

직접 `vector` 유사 container를 구현하면 단순히 "동적 배열"만 만드는 것이 아닙니다.

최소한 다음 문제를 직접 책임져야 합니다.

```text
allocation/deallocation
construction/destruction
size/capacity invariant
capacity overflow
copy construction failure
assignment failure
self-aliasing
iterator invalidation
exception safety
const correctness
allocator contract
```

따라서 학습 목적의 구현이라도 지원 범위를 먼저 정하는 것이 좋습니다.

예:

```text
C++98
std::allocator<T>
copy-constructible T
single-threaded container object
일부 vector 연산만 구현
```

범위를 정하지 않으면 표준 container 전체 규격을 무의식적으로 재현해야 하는 상황이 생길 수 있습니다.

---

## 표준 container를 우선합니다

일반 application에서는 검증된 표준 container를 우선 사용합니다.

직접 구현은 다음 목적에 한정하는 편이 좋습니다.

- 객체 수명과 raw storage 학습
- allocator 동작 확인
- exception safety 학습
- iterator 무효화 원리 이해
- 특수한 memory layout 요구
- 고정 capacity 같은 명확한 제약
- 표준 container로 충족되지 않는 측정된 성능 요구

단순히 "직접 구현하면 더 빠를 것 같다"는 이유만으로 표준 container를 대체하지 않습니다.

성능 문제가 실제로 있다면 먼저 측정합니다.

```text
profile
→ bottleneck 확인
→ 자료구조 변경 후보 비교
→ benchmark
→ 구현 결정
```

---

## 구현 검토 순서

직접 container 구현을 읽거나 작성할 때는 다음 순서로 확인하면 이해하기 쉽습니다.

1. **누가 storage를 소유하는지 확인합니다.**

   ```text
   data
   allocator
   capacity
   ```

2. **실제 객체가 존재하는 범위를 확인합니다.**

   ```text
   [data, data + size)
   ```

3. **모든 생성 성공 뒤에만 `size`가 증가하는지 확인합니다.**

4. **예외 발생 시 지금까지 생성된 객체 수를 정확히 추적하는지 확인합니다.**

5. **기존 상태를 언제 파괴하는지 확인합니다.**

   strong guarantee라면 새 상태가 완성되기 전에 기존 상태를 버리면 안 됩니다.

6. **입력 reference가 container 내부를 가리킬 수 있는지 확인합니다.**

7. **재할당과 중간 삽입이 iterator/reference/pointer를 어떻게 무효화하는지 확인합니다.**

8. **capacity 계산에서 overflow와 `max_size()`를 확인합니다.**

9. **algorithm 사용 시 iterator category와 comparator 요구사항을 확인합니다.**

10. **직접 구현이 실제로 필요한지 다시 확인합니다.**

---

## 완료 기준

- raw storage와 생성된 객체를 같은 것으로 취급하지 않습니다.
- `allocate()`만으로 `T` 객체 수명이 시작되지 않는 이유를 설명할 수 있습니다.
- `destroy()`와 `deallocate()`의 역할 차이를 설명할 수 있습니다.
- `size`와 `capacity` invariant를 적고 실제 객체가 존재하는 범위를 구분할 수 있습니다.
- 빈 container의 null `data`에 불필요한 pointer 산술을 하지 않습니다.
- capacity 증가 전에 overflow와 `max_size()`를 확인합니다.
- 재할당 중 일부 copy construction이 실패하면 새 storage의 생성 완료 원소만 역순으로 정리합니다.
- strong exception guarantee를 위해 새 상태가 완성될 때까지 기존 storage를 유지하는 이유를 설명할 수 있습니다.
- self-aliasing `push_back()`에서 기존 storage를 너무 일찍 파괴하면 reference가 dangling이 되는 이유를 설명할 수 있습니다.
- copy constructor 도중 예외가 나면 constructor 자체가 부분 생성 자원을 정리해야 하는 이유를 설명할 수 있습니다.
- copy-and-swap이 assignment의 strong guarantee를 단순화하는 방식을 설명할 수 있습니다.
- allocator state를 무조건 swap해도 된다고 가정하지 않습니다.
- `vector` 재할당 뒤 모든 iterator/reference/pointer가 무효가 됨을 설명할 수 있습니다.
- 재할당 없는 `push_back()`에서도 이전 `end()`가 무효가 됨을 설명할 수 있습니다.
- `vector` 중간 삽입/삭제에서는 변경 위치 이후 iterator가 영향을 받을 수 있음을 설명할 수 있습니다.
- `map` insert와 erase의 주요 iterator 무효화 차이를 설명할 수 있습니다.
- `std::map`의 구체적인 tree 종류를 표준이 보장한다고 가정하지 않습니다.
- `std::sort`가 random-access iterator를 요구하는 이유를 설명할 수 있습니다.
- comparator가 strict weak ordering을 지켜야 하는 이유와 기본 조건을 설명할 수 있습니다.
- 표준 container를 직접 구현해야 하는 경우와 그렇지 않은 경우를 구분할 수 있습니다.
