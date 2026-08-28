# int-vector

`int-vector`는 정수를 삽입 순서대로 저장하고 공간이 부족할 때 배열을 확장하는 C 라이브러리입니다. allocator callback으로 다음 재할당을 실패시킬 수 있으며, 실패하면 기존 배열과 원소를 그대로 유지합니다.

## 유지하는 상태

```text
size <= capacity
capacity == 0이면 data == NULL이고 size == 0
capacity > 0이면 data != NULL
유효한 index는 0 <= index < size
```

## 제공 기능

- 기본 `realloc`/`free`와 사용자 정의 allocator callback
- 초기 capacity 4, 이후 두 배씩 증가
- 원소 개수와 바이트 수의 overflow 사전 검사
- 범위를 확인한 뒤에만 `out_value` 갱신
- 재할당 실패 뒤 `data`, `size`, `capacity`와 기존 원소 보존
- 반복 호출 가능한 정리 함수

## 빌드

```sh
make
```

정적 라이브러리는 `build/libint_vector.a`에 생성됩니다.

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

## 주요 구현 결정

배열이 가득 차면 새 capacity를 먼저 계산하고, `new_capacity * sizeof *data`가 `SIZE_MAX`를 넘지 않는지 확인합니다. 재할당이 성공한 뒤에만 `data`와 `capacity`를 바꾸고, 확보한 위치에 새 값을 쓴 뒤 `size`를 증가시킵니다.

조회는 index와 객체 상태를 모두 확인한 뒤 결과를 씁니다. 실패한 조회가 호출자의 기존 값을 덮지 않습니다.

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

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Owned array and allocator callbacks | `include/int_vector.h` |
| 2 | Empty-state initialization and invariant checks | `src/int_vector.c` |
| 3 | Overflow-checked growth before insertion | `src/int_vector.c` |
| 4 | Lookup after bounds validation | `src/int_vector.c` |
| 5 | Repeatable cleanup | `src/int_vector.c` |

## 범위

정수의 뒤쪽 삽입과 index 조회만 제공합니다. 중간 삽입, 삭제, capacity 축소, iterator와 여러 스레드의 동시 접근은 포함하지 않습니다.
