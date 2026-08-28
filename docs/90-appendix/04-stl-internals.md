# STL 내부 동작

## 사용 시점

표준 container를 직접 다시 구현하기 위한 일반 지침이 아닙니다. iterator 무효화, 재할당 중 예외, raw storage와 객체 수명을 이해해야 할 때 참고합니다.

## 메모리와 객체는 다릅니다

```cpp
std::allocator<T> allocator;
T *memory = allocator.allocate(capacity);
```

이 시점에는 `T` 객체가 아직 없습니다. `construct()`를 호출한 위치에만 객체 수명이 시작됩니다.

```cpp
allocator.construct(memory + size, value);
++size;
```

정리할 때는 생성한 원소만 역순으로 `destroy()`하고 마지막에 storage를 `deallocate()`합니다.

## vector의 세 값

동적 배열은 보통 다음을 보유합니다.

```text
data pointer
size: 생성된 원소 수
capacity: 확보한 storage의 원소 수
```

항상 다음 조건을 지킵니다.

```text
0 <= size <= capacity
[data, data + size)에는 실제 객체가 존재
[data + size, data + capacity)에는 storage만 존재
```

빈 container에서 `data`가 `0`일 수 있으므로 불필요한 pointer 산술을 피합니다.

## capacity 증가

일반적으로 capacity를 두 배로 늘려 `push_back()`의 평균 비용을 낮춥니다. 곱셈 전에 `max_size()`와 overflow를 확인합니다.

```cpp
if (capacity > allocator.max_size() / 2)
    throw std::length_error("capacity overflow");
```

항상 두 배가 최적이라는 뜻은 아닙니다. 실제 표준 library의 성장 비율은 구현 세부사항이며 코드에서 가정하면 안 됩니다.

## 재할당 순서

strong guarantee를 제공하려면 다음 순서를 사용합니다.

```text
새 storage allocate
→ 기존 원소를 새 storage에 복사 생성
→ 새 원소 생성
→ 모든 생성 성공
→ 기존 원소 destroy
→ 기존 storage deallocate
→ pointer·size·capacity 교체
```

중간 예외가 나면 새 storage에서 생성이 끝난 원소만 역순으로 파괴하고 기존 storage는 건드리지 않습니다.

## self-aliasing 입력

```cpp
values.push_back(values[0]);
```

용량 증가가 필요할 때 기존 storage를 먼저 파괴하면 `value` 참조가 무효가 됩니다. 새 원소 복사가 끝날 때까지 기존 storage를 유지합니다.

이 문제는 API parameter가 container 내부 원소를 가리킬 수 있다는 사실에서 생깁니다.

## 복사 생성과 대입

복사 생성은 새 storage에서 원소를 차례로 만듭니다. 일부 원소 뒤 예외가 나면 그 원소들만 정리합니다.

대입은 복사본을 먼저 만든 뒤 swap하면 기존 값을 보존하기 쉽습니다.

```cpp
Vector &operator=(Vector other) {
    swap(other);
    return *this;
}
```

allocator state까지 교환할 수 있는지는 allocator 요구사항에 따라 다릅니다. 단순 C++98 학습 구현은 stateless `std::allocator<T>`로 범위를 제한할 수 있습니다.

## iterator 무효화

vector 재할당 뒤에는 모든 iterator, reference, pointer가 무효입니다. 재할당이 없더라도 끝에 원소를 추가하면 이전 `end()`는 무효가 됩니다.

node 기반 `map`은 insert 뒤 기존 iterator가 유지되지만 지운 node를 가리키는 iterator는 무효입니다.

API가 iterator를 반환하거나 저장한다면 어떤 변경 연산이 수명을 끝내는지 적습니다.

## map 내부

`std::map`은 key 정렬 순서를 유지하는 node 기반 tree로 구현되는 것이 일반적입니다. 표준은 구체 tree 종류를 요구하지 않고 연산 복잡도와 관찰 가능한 동작을 요구합니다.

- 검색·삽입·삭제: 로그 시간
- iterator 순회: key 순서
- insert: 기존 원소 iterator 유지

node allocation이 많고 메모리 locality가 낮을 수 있습니다. 작은 데이터나 순차 처리에서는 정렬된 vector가 더 나을 수 있습니다.

## algorithm 요구사항

`std::sort`는 random-access iterator를 요구합니다. `std::list` iterator에는 사용할 수 없고 list 자체의 `sort()`를 사용합니다.

비교 함수는 strict weak ordering을 지켜야 합니다.

- `comp(x, x)`는 false
- `comp(a, b)`가 true면 `comp(b, a)`는 false
- 비교 관계가 순환하지 않음

## 표준 container를 우선합니다

직접 vector를 구현하면 allocator, 예외 안전성, iterator, overflow와 aliasing을 모두 책임져야 합니다. 일반 application에서는 검증된 표준 container를 사용합니다.

직접 구현은 다음 목적에 한정하는 편이 좋습니다.

- 객체 수명과 raw storage 학습
- allocator 동작 확인
- 특수한 메모리 layout이나 고정 capacity 요구
- 표준 container로 충족되지 않는 측정된 요구

## 완료 기준

- raw storage와 생성된 객체 범위를 구분합니다.
- size와 capacity 불변식을 적습니다.
- 재할당 중 일부 복사 실패를 역순으로 정리합니다.
- self-aliasing `push_back`이 위험한 이유를 설명합니다.
- vector와 map의 주요 iterator 무효화 규칙을 확인합니다.
- 표준 container를 직접 구현해야 하는 경우와 그렇지 않은 경우를 구분합니다.
