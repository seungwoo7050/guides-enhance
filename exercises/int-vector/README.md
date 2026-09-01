# int-vector

`int-vector`는 정수를 삽입 순서대로 저장하고 공간이 부족할 때 내부 배열을 확장하는 C 라이브러리입니다.

핵심 목표는 다음 두 가지입니다.

```text
정상 경로:
    원소를 삽입 순서대로 보존

할당 실패 경로:
    기존 배열과 기존 원소를 호출 전 상태 그대로 보존
```

allocator callback을 사용하면 테스트에서 특정 재할당을 의도적으로 실패시켜 이 실패 보장을 확인할 수 있습니다.

## 유지하는 상태

유효한 객체는 항상 다음 불변식을 만족합니다.

```text
size <= capacity

capacity == 0이면:
    data == NULL
    size == 0

capacity > 0이면:
    data != NULL

유효한 index:
    0 <= index < size
```

여기서:

```text
size
    현재 저장된 원소 개수

capacity
    현재 할당된 배열에 저장할 수 있는 원소 개수

data
    int 원소 배열의 시작 주소
```

입니다.

예를 들어:

```text
size = 3
capacity = 4
```

라면 `data[0]`, `data[1]`, `data[2]`만 유효한 원소이고 `data[3]`은 아직 vector의 원소가 아닙니다.

## 제공 기능

- 기본 `realloc`/`free`와 사용자 정의 allocator callback
- 초기 capacity 4, 이후 두 배씩 증가
- 원소 개수와 바이트 수의 overflow 사전 검사
- 범위를 확인한 뒤에만 `out_value` 갱신
- 재할당 실패 뒤 `data`, `size`, `capacity`와 기존 원소 보존
- 반복 호출 가능한 정리 함수

allocator 인자에 기본 설정을 사용하면 일반 `realloc`과 `free`를 사용하고, 사용자 정의 callback을 전달하면 테스트에서 할당 성공·실패를 제어할 수 있습니다.

## 빌드

```sh
make
```

정적 라이브러리는 다음 위치에 생성됩니다.

```text
build/libint_vector.a
```

## 사용 예시

```c
#include "int_vector.h"

#include <stdio.h>

struct int_vector values;
int item;

int_vector_init(&values, NULL);

int_vector_push(&values, 10);
int_vector_push(&values, 20);

if (int_vector_get(&values, 1, &item) == 0) {
    printf("%d\n", item);
}

int_vector_destroy(&values);
```

두 번의 삽입 뒤 상태는 개념적으로 다음과 같습니다.

```text
data[0] = 10
data[1] = 20
size    = 2
capacity >= 2
```

`int_vector_get(&values, 1, &item)`은 두 번째 원소인 `20`을 `item`에 씁니다.

## 주요 구현 결정

### 처음에는 빈 상태

초기화 직후에는 다음 상태를 사용합니다.

```text
data = NULL
size = 0
capacity = 0
```

첫 번째 `push`가 필요할 때 초기 capacity인 4를 확보합니다.

이 방식은 빈 vector를 만들 때 불필요한 allocation을 하지 않으며, 빈 상태의 표현도 하나로 고정합니다.

### capacity 성장

배열이 가득 찼을 때만 성장합니다.

```text
size < capacity
    → 현재 공간에 바로 삽입

size == capacity
    → 더 큰 배열 필요
```

성장 시 초기 capacity는 4이고 이후에는 두 배씩 늘립니다.

예:

```text
0 → 4 → 8 → 16 → 32 ...
```

단순히 `capacity * 2`를 먼저 계산하면 `size_t` 범위를 넘을 수 있으므로 곱셈 전에 overflow 가능성을 검사해야 합니다.

### 바이트 수 overflow도 별도로 검사

allocator에는 원소 개수가 아니라 바이트 수를 전달해야 합니다.

```text
bytes = new_capacity * sizeof *data
```

따라서 다음 두 계산을 모두 안전하게 해야 합니다.

```text
새 capacity 계산
새 capacity × 원소 크기 계산
```

`new_capacity` 자체는 표현 가능해도 `new_capacity * sizeof(int)`가 `SIZE_MAX`를 넘을 수 있습니다.

### 재할당 성공 뒤에만 객체 상태 변경

실패 보장을 유지하려면 다음과 같이 기존 포인터에 `realloc` 결과를 바로 대입하면 안 됩니다.

```c
vector->data = realloc(vector->data, bytes);
```

실패 시 `realloc`이 `NULL`을 반환하면 기존 포인터를 잃을 수 있기 때문입니다.

대신 개념적으로:

```text
새 capacity와 byte 수 계산
→ 임시 포인터로 realloc 시도
→ 실패하면 기존 객체 그대로 반환
→ 성공하면 data와 capacity 갱신
→ 새 원소 기록
→ size 증가
```

순서로 처리합니다.

즉 삽입 실패 후에는 다음이 모두 호출 전과 같아야 합니다.

```text
data 주소
size
capacity
기존 원소 값
```

### 삽입 완료 순서

새 공간이 확보된 뒤:

```text
data[size] = value
size++
```

순서로 새 원소를 추가합니다.

`size`를 먼저 증가시키면 원소 기록 전에 객체가 새 원소가 존재한다고 주장하는 중간 상태가 될 수 있으므로, 상태 갱신 순서를 분명히 합니다.

### 조회는 검증 뒤 출력

`int_vector_get`은 다음 조건을 먼저 검사합니다.

```text
객체 상태가 유효한가
out_value가 유효한가
index < size 인가
```

모든 검사가 성공한 뒤에만:

```c
*out_value = vector->data[index];
```

를 수행합니다.

따라서 실패한 조회는 호출자의 기존 출력값을 바꾸지 않습니다.

예:

```c
int value = 99;

if (int_vector_get(&vector, 100, &value) != 0) {
    /* value는 여전히 99 */
}
```

## 손상된 객체 상태

예를 들어 다음 상태는 불변식을 위반합니다.

```text
size = 10
capacity = 4
```

또는:

```text
capacity = 4
data = NULL
```

라이브러리 함수는 이런 손상된 상태를 정상 vector처럼 사용하지 않습니다.

이 검사는 호출자의 메모리 오염을 복구한다는 뜻은 아닙니다. 잘못된 상태에서 배열에 접근해 더 큰 오류를 만들지 않도록 거부하는 방어적 검사입니다.

## 정리

`int_vector_destroy`는 내부 배열을 해제한 뒤 객체를 다시 빈 상태로 만듭니다.

개념적으로:

```text
free(data)
data = NULL
size = 0
capacity = 0
```

따라서 같은 객체에 `destroy`를 반복 호출해도 이미 해제된 포인터를 다시 해제하지 않도록 구현합니다.

## 테스트

```sh
make test
make sanitize
```

테스트는 다음을 확인합니다.

- 빈 배열에서 첫 삽입
- 여러 번의 capacity 증가와 삽입 순서
- 첫 원소와 마지막 원소 조회
- 범위 밖 조회에서 출력값 보존
- 손상된 `size`/`capacity` 조합 거부
- 첫 할당과 다음 성장의 강제 실패
- 실패 후 포인터, 원소, `size`, `capacity` 보존
- 반복 정리

강제 allocator 실패 테스트는 단순히 함수가 오류를 반환하는지만 보는 것이 아니라 **실패 뒤 객체 전체가 이전 상태와 같은지** 확인하는 테스트입니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Owned array and allocator callbacks | `include/int_vector.h` |
| 2 | Empty-state initialization and invariant checks | `src/int_vector.c` |
| 3 | Overflow-checked growth before insertion | `src/int_vector.c` |
| 4 | Lookup after bounds validation | `src/int_vector.c` |
| 5 | Repeatable cleanup | `src/int_vector.c` |

## 범위

다음 기능만 제공합니다.

```text
뒤쪽 삽입(push)
index 기반 조회(get)
```

다음 기능은 포함하지 않습니다.

- 중간 삽입
- 삭제
- capacity 축소
- iterator
- 여러 스레드의 동시 접근

여러 스레드가 같은 vector를 동시에 사용해야 한다면 호출자가 별도의 동기화 정책을 제공해야 합니다.