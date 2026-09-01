# Mini Vector

## 개요

`MiniVector<T>`는 C++98의 `std::allocator`를 사용해 만든 작은 동적 배열입니다.

이 프로젝트의 핵심은 단순히 연속 배열을 만드는 것이 아니라 다음 두 개념을 직접 분리해서 다루는 것입니다.

```text
할당된 raw storage
≠
실제로 생성된 T 객체
```

`MiniVector<T>`는 다음 상태를 관리합니다.

```text
data_
size_
capacity_
```

`data_`는 `capacity_`개의 `T`를 놓을 수 있는 storage를 가리키지만, 실제 객체가 존재하는 범위는 `size_`까지만입니다.

이 프로젝트는 표준 `std::vector`를 대체하기 위한 구현이 아닙니다.

학습 목적은 다음과 같습니다.

```text
raw storage
object lifetime
copy construction failure
exception-safe reallocation
iterator invalidation
self-aliasing
```

## 제공 기능

- `size()`
- `capacity()`
- `empty()`
- `operator[]`
- 범위를 검사하는 `at()`
- mutable pointer iterator
- const pointer iterator
- `reserve()`
- `push_back()`
- `clear()`
- 깊은 복사
- copy-and-swap 대입
- 재할당 실패 시 기존 크기·용량·값 보존
- `push_back(values[0])` 같은 self-aliasing 처리

## 기본 invariant

항상 다음 관계를 유지해야 합니다.

```text
0 <= size_ <= capacity_
```

그리고 유효한 storage가 있다면:

```text
[data_, data_ + size_)
→ 실제 T 객체가 존재

[data_ + size_, data_ + capacity_)
→ T 객체는 없고 raw storage만 존재
```

예:

```text
capacity_ = 5
size_     = 2
```

개념적으로:

```text
index: 0 1 2 3 4
       [A][B][ ][ ][ ]
        객체   raw storage
```

`capacity_`까지 모든 위치를 생성된 객체라고 생각하면 안 됩니다.

## allocation과 construction

allocator로 storage를 확보합니다.

```cpp
std::allocator<T> allocator;
T *data = allocator.allocate(capacity);
```

이 시점에는 `T` 객체가 아직 없습니다.

실제 객체를 만들 때:

```cpp
allocator.construct(data + size, value);
```

를 사용합니다.

생성 성공 뒤에만 `size`를 증가시켜야 합니다.

```cpp
allocator.construct(data + size, value);
++size;
```

반대로 size를 먼저 증가시키면 constructor가 exception을 던졌을 때 size와 실제 객체 수가 달라질 수 있습니다.

## destruction과 deallocation

객체를 없애는 것과 storage를 반환하는 것은 다른 작업입니다.

```cpp
allocator.destroy(data + i);
```

는 `T` 객체의 lifetime을 끝냅니다.

```cpp
allocator.deallocate(data, capacity);
```

는 storage 자체를 allocator에 반환합니다.

따라서 cleanup 순서는:

```text
생성된 객체 destroy
→ storage deallocate
```

입니다.

storage를 먼저 반환한 뒤 destructor를 호출하면 이미 유효하지 않은 memory를 사용하게 됩니다.

## 빌드와 실행

```sh
make
./demo
```

`demo`는 원소를 추가하면서 `size`와 `capacity` 변화를 출력합니다.

중요한 점은 capacity 증가 비율 자체가 표준 `vector`와 같아야 하는 것이 아니라, 다음 조건을 유지하는 것입니다.

```text
size <= capacity
필요할 때만 더 큰 storage 확보
기존 값 보존
```

## `operator[]`와 `at()`

두 접근 함수의 계약은 다릅니다.

### `operator[]`

일반적인 vector와 마찬가지로 index가 유효하다는 전제에서 빠르게 접근합니다.

```cpp
values[i]
```

범위를 벗어난 index는 검사하지 않는 구현일 수 있습니다.

### `at()`

범위를 확인합니다.

```cpp
values.at(i)
```

`i >= size()`이면 예외를 던집니다.

즉:

```text
operator[]
→ caller가 index 유효성을 책임

at()
→ container가 범위를 검사
```

로 역할이 다릅니다.

## pointer iterator

이 구현은 단순화를 위해 pointer를 iterator로 사용할 수 있습니다.

예:

```cpp
typedef T *iterator;
typedef const T *const_iterator;
```

그러면:

```cpp
begin()
→ data_

end()
→ data_ + size_
```

형태가 됩니다.

다만 empty 상태에서 `data_ == 0`을 허용한다면 null pointer 산술을 불필요하게 수행하지 않도록 구현에 주의해야 합니다.

iterator는 container storage의 주소에 직접 의존하므로 재할당 뒤 기존 iterator는 모두 무효가 됩니다.

## `clear()`

`clear()`는 생성된 모든 원소를 파괴하지만 일반적으로 storage 자체는 유지할 수 있습니다.

즉:

```text
before:
size_ = 4
capacity_ = 8

clear()

after:
size_ = 0
capacity_ = 8
```

와 같은 상태를 허용할 수 있습니다.

정리 순서:

```text
원소를 역순 destroy
→ size_ = 0
```

storage를 유지한다면 이후 `push_back()`은 새 allocation 없이 기존 capacity를 사용할 수 있습니다.

## 깊은 복사

복사 생성된 `MiniVector`는 원본과 독립적인 원소를 소유해야 합니다.

잘못된 얕은 복사:

```text
a.data_ ─┐
         ├→ 같은 storage
b.data_ ─┘
```

이 구조에서는 한 객체 수정이 다른 객체에 영향을 주고 destructor에서 double deallocation이 발생할 수 있습니다.

올바른 깊은 복사:

```text
a.data_ → storage A
b.data_ → storage B
```

각 원소는 새 storage에 copy construction됩니다.

## copy constructor 예외 처리

복사 중 `T`의 copy constructor가 exception을 던질 수 있습니다.

예:

```text
원소 0 copy 성공
원소 1 copy 성공
원소 2 copy 실패
```

새 storage에서 실제 객체는 0과 1만 생성되었습니다.

따라서 cleanup은:

```text
원소 1 destroy
→ 원소 0 destroy
→ 새 storage deallocate
→ exception 재전파
```

이어야 합니다.

`capacity_` 전체를 destroy하면 아직 생성되지 않은 위치까지 destructor를 호출하게 됩니다.

중요한 것은 **실제로 생성 성공한 원소 수를 별도로 추적하는 것**입니다.

## constructor 실패와 destructor

constructor가 끝나기 전에 exception이 발생하면 완성되지 않은 `MiniVector` 객체의 destructor는 호출되지 않습니다.

따라서 copy constructor 내부에서 allocate한 raw storage는 copy constructor가 직접 정리해야 합니다.

예:

```text
copy constructor
→ allocate 성공
→ 원소 일부 construct
→ exception
→ 부분 생성 원소 destroy
→ storage deallocate
→ exception 재전파
```

이 cleanup을 destructor에 맡길 수 없습니다.

## copy-and-swap 대입

copy assignment는 다음과 같이 구현할 수 있습니다.

```cpp
MiniVector &operator=(MiniVector other)
{
    swap(other);
    return *this;
}
```

의미:

```text
1. other parameter를 copy construction
2. 복사 성공
3. this와 other 내부 상태 swap
4. 함수 종료
5. other destructor가 이전 this 자원 정리
```

복사 과정에서 exception이 발생하면 함수 body에 들어오기 전에 실패하므로 기존 `this`는 그대로 남습니다.

따라서 strong exception guarantee를 구현하기 쉬운 패턴입니다.

## `reserve()`

`reserve(new_capacity)`는 현재 capacity보다 큰 storage를 미리 확보합니다.

`new_capacity <= capacity_`라면 보통 아무 작업도 하지 않습니다.

증가가 필요하면:

```text
새 storage allocate
→ 기존 원소 copy construct
→ 모든 복사 성공
→ 기존 원소 destroy
→ 기존 storage deallocate
→ data_/capacity_ 교체
```

순서를 사용합니다.

중간 copy failure가 발생하면:

```text
새 storage의 생성된 원소만 destroy
→ 새 storage deallocate
→ 기존 storage 유지
```

해야 합니다.

즉 실패 뒤:

```text
size
capacity
기존 원소 값
```

이 모두 호출 전과 같아야 합니다.

## `push_back()`

capacity가 남아 있으면:

```text
현재 end 위치에 새 원소 construct
→ 성공 후 size_ 증가
```

하면 됩니다.

capacity가 부족하면 새 storage를 확보해야 합니다.

이때는 `reserve()`와 비슷하지만 **추가할 입력 값이 기존 vector 내부 원소를 참조할 수도 있다**는 점이 중요합니다.

## self-aliasing `push_back`

다음 호출은 정상 입력입니다.

```cpp
values.push_back(values[0]);
```

`push_back` signature가:

```cpp
void push_back(const T &value);
```

라면 `value`는 현재 `values` 내부 원소를 참조합니다.

capacity 증가가 필요한 상황에서 기존 storage를 먼저 파괴하면:

```text
value
→ 이미 파괴된 values[0]을 참조
```

하게 됩니다.

잘못된 순서:

```text
새 storage allocate
→ 기존 storage destroy/deallocate
→ value를 복사해 새 원소 생성
```

올바른 방향:

```text
새 storage allocate
→ 기존 storage가 살아 있는 동안 필요한 copy construction 수행
→ 새 원소 생성까지 성공
→ 그 뒤 기존 storage destroy/deallocate
```

즉 새 storage에서 필요한 모든 값이 완성될 때까지 기존 storage를 유지해야 합니다.

## capacity 증가

구현은 capacity를 일정 비율로 증가시킬 수 있습니다.

단순 예:

```text
0
1
2
4
8
16
```

그러나 실제 `std::vector`가 반드시 같은 비율을 사용한다는 뜻은 아닙니다.

중요한 것은 geometric growth를 사용해 반복 `push_back()`에서 매번 allocation하지 않도록 하는 것입니다.

새 capacity 계산 전에 overflow와 allocator의 `max_size()`를 확인해야 합니다.

예:

```cpp
if (capacity_ > allocator_.max_size() / 2)
    throw std::length_error("MiniVector capacity overflow");
```

실제 계산은 현재 필요한 최소 크기도 함께 고려해야 합니다.

## iterator 무효화

`MiniVector`가 새 storage로 이동하면 기존 원소 주소가 바뀝니다.

따라서 재할당 뒤 다음은 모두 무효입니다.

```text
iterator
pointer
reference
```

예:

```cpp
MiniVector<int>::iterator it = values.begin();

values.push_back(42); // 재할당 가능

// 재할당이 있었다면 it 사용 불가
```

capacity가 충분해 재할당이 없었다면 기존 원소 주소는 유지할 수 있지만 이전 `end()`는 새 끝을 가리키지 않으므로 다시 얻어야 합니다.

## 테스트

```sh
make test
```

테스트는 다음 잘못된 구현을 검출합니다.

- 얕은 복사 때문에 복사본 수정이 원본에 반영됨
- copy constructor 중 예외가 발생했는데 부분 생성 원소를 정리하지 않음
- `reserve()` 중 일부 원소 복사 뒤 exception이 발생했는데 새 memory를 정리하지 않음
- `reserve()` 실패 뒤 기존 size/capacity/value가 바뀜
- 재할당 전에 기존 memory를 파괴하여 `push_back(values[0])`가 dangling reference를 읽음
- copy failure 뒤 살아 있는 객체 수가 달라짐
- `clear()`가 실제 생성된 범위보다 넓게 destroy함

객체 수명 검사는 test용 타입에 static live-object counter를 두는 방식으로 확인할 수 있습니다.

예:

```text
construction
→ live_count + 1

destruction
→ live_count - 1
```

각 test 종료 뒤 count가 원래 값으로 돌아오는지 확인하면 leak이나 double destruction을 찾는 데 도움이 됩니다.

## 구현에서 지키는 조건

핵심 invariant를 다시 정리하면 다음과 같습니다.

```text
0 <= size_ <= capacity_

[data_, data_ + size_)
→ 실제 객체 존재

[data_ + size_, data_ + capacity_)
→ raw storage only
```

그리고 상태 변경 연산에서는:

```text
새 상태가 완성되기 전
→ 기존 상태를 파괴하지 않음
```

을 기본 원칙으로 둡니다.

특히 `reserve()`와 재할당이 필요한 `push_back()`은 새 memory에서 필요한 복사를 모두 끝낸 뒤 기존 memory를 교체해야 합니다.

이 순서를 지키면 원소 복사가 실패해도 호출 전 상태를 보존할 수 있습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Raw storage, constructed size, and capacity | `include/MiniVector.hpp` |
| 2 | Deep copy, destruction, and copy-and-swap | `include/MiniVector.hpp` |
| 3 | Checked element access and half-open iterators | `include/MiniVector.hpp` |
| 4 | Copy into new storage before replacing the old storage | `include/MiniVector.hpp` |
| 5 | Grow without invalidating an aliased input value too early | `include/MiniVector.hpp` |
| 6 | Print size and capacity changes | `examples/demo.cpp` |

이 순서는 storage invariant를 먼저 확립한 뒤 복사, 접근, 재할당, self-aliasing 문제를 순서대로 다루도록 구성되어 있습니다.

## 범위

이 프로젝트에서는 다음을 구현하지 않습니다.

```text
erase
insert
custom allocator propagation
move semantics
완전한 std::vector 호환 API
```

C++98에서 직접 memory와 object lifetime을 관리할 때 필요한 복사, 정리, 재할당 실패 복구에만 범위를 둡니다.
