# Mini Vector

## 개요

`MiniVector<T>`는 C++98의 `std::allocator`를 사용해 만든 작은 동적 배열입니다. 할당된 메모리와 실제로 생성된 원소를 따로 관리하며, 복사나 재할당 도중 예외가 발생해도 기존 값을 유지합니다.

이 프로젝트는 표준 `vector`를 대신하기 위한 구현이 아닙니다. raw storage 위에서 객체 수명을 직접 관리할 때 어떤 정리 순서가 필요한지 확인하는 용도입니다.

## 제공 기능

- `size()`, `capacity()`, `empty()`
- `operator[]`, 범위를 검사하는 `at()`
- mutable/const pointer iterator
- `reserve()`, `push_back()`, `clear()`
- 깊은 복사와 copy-and-swap 대입
- 재할당 실패 시 기존 크기·용량·값 보존
- `push_back(values[0])`처럼 입력이 현재 원소를 가리키는 경우 처리

## 빌드와 실행

```sh
make
./demo
```

`demo`는 원소를 추가하면서 `size`와 `capacity`가 어떻게 바뀌는지 출력합니다.

## 테스트

```sh
make test
```

테스트는 다음과 같은 잘못된 구현을 검출합니다.

- 얕은 복사로 인해 복사본 수정이 원본에 반영되는 경우
- `reserve()` 도중 일부 원소만 복사된 뒤 예외가 발생했는데 새 메모리를 정리하지 않는 경우
- 재할당 전에 기존 메모리를 파괴해 `push_back(values[0])`가 댕글링 참조를 읽는 경우
- 복사 실패 뒤 `size`, `capacity` 또는 살아 있는 객체 수가 달라지는 경우

## 구현에서 지키는 조건

`data_`는 `capacity_`개 원소를 담을 수 있는 메모리를 가리킵니다. 그러나 실제 객체가 존재하는 범위는 `[data_, data_ + size_)`뿐입니다. 따라서 예외가 발생했을 때는 생성이 끝난 원소만 역순으로 파괴해야 합니다.

`reserve()`와 용량 증가가 필요한 `push_back()`은 새 메모리에서 필요한 복사를 모두 끝낸 뒤 기존 메모리를 교체합니다. 이 순서를 지키면 원소 복사가 실패해도 호출 전 상태가 남습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Raw storage, constructed size, and capacity | `include/MiniVector.hpp` |
| 2 | Deep copy, destruction, and copy-and-swap | `include/MiniVector.hpp` |
| 3 | Checked element access and half-open iterators | `include/MiniVector.hpp` |
| 4 | Copy into new storage before replacing the old storage | `include/MiniVector.hpp` |
| 5 | Grow without invalidating an aliased input value too early | `include/MiniVector.hpp` |
| 6 | Print size and capacity changes | `examples/demo.cpp` |

## 범위

`erase`, `insert`, 사용자 정의 allocator 전파, 이동 의미론은 구현하지 않습니다. C++98에서 직접 메모리와 객체 수명을 다룰 때 필요한 복사·정리·실패 복구에만 범위를 둡니다.
