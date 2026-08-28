# owned-string

`owned-string`은 문자열 버퍼를 직접 소유하고, 내용이 늘어날 때 필요한 크기만큼 버퍼를 확장하는 C 라이브러리입니다. 현재 문자열 전체나 내부 suffix를 다시 붙이는 입력을 지원하며, 메모리 재할당에 실패하면 호출 전 상태를 그대로 유지합니다.

## 제공 기능

- 기본 `realloc`/`free`와 사용자 정의 allocator callback 지원
- `length`, `capacity`, NUL 종료 조건 검사
- capacity를 두 배씩 늘리되 `SIZE_MAX` overflow 사전 검사
- 전체 문자열과 내부 suffix의 별칭 append 지원
- 재할당 실패 시 `data`, 내용, `length`, `capacity` 보존
- 여러 번 호출해도 안전한 `owned_string_destroy`

## 유지하는 상태

```text
빈 상태:
  data == NULL
  length == 0
  capacity == 0

할당된 상태:
  data != NULL
  length < capacity
  data[length] == '\0'
```

공개 필드는 `owned_string_init`을 호출한 뒤 라이브러리 함수로만 변경해야 합니다.

## 빌드

```sh
make
```

정적 라이브러리는 `build/libowned_string.a`에 생성됩니다.

## 사용 예시

```c
#include "owned_string.h"

#include <stdio.h>

int main(void) {
    struct owned_string value;

    owned_string_init(&value, NULL);
    if (owned_string_append(&value, "hello") != 0 ||
        owned_string_append(&value, " world") != 0) {
        owned_string_destroy(&value);
        return 1;
    }
    puts(value.data);
    owned_string_destroy(&value);
    return 0;
}
```

## 주요 구현 결정

입력 `source`가 현재 버퍼 안을 가리킬 수 있습니다. append 과정에서 `realloc`이 버퍼를 옮기면 기존 `source` 포인터는 무효가 되므로, 재할당 전에는 버퍼 시작 주소에서의 offset만 저장합니다. 재할당이 성공한 뒤 새 버퍼 주소에 offset을 더해 source 위치를 다시 구합니다.

capacity와 필요한 바이트 수를 모두 계산하고 `resize`가 성공한 뒤에만 `data`와 `capacity`를 바꿉니다. 이 순서 덕분에 할당 실패 후에도 기존 문자열을 계속 사용할 수 있습니다.

## 테스트

```sh
make test
make sanitize
```

테스트는 다음을 확인합니다.

- 빈 문자열과 일반 문자열 append
- capacity 안에서의 append와 여러 번의 성장
- 전체 self-append와 내부 suffix append
- 별칭 source를 사용하면서 재할당이 발생하는 경우
- 잘못된 상태의 객체 거부
- 첫 할당과 다음 성장의 강제 실패
- 실패 후 포인터, 내용, 길이와 capacity 보존
- 반복 정리

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Owned buffer and allocator callbacks | `include/owned_string.h` |
| 2 | Empty-state initialization and invariant checks | `src/owned_string.c` |
| 3 | Capacity calculation for aliased input | `src/owned_string.c` |
| 4 | Append only after successful resize | `src/owned_string.c` |
| 5 | Repeatable cleanup | `src/owned_string.c` |

## 범위

NUL로 끝나는 바이트 문자열만 저장합니다. 임의의 임의 바이트 데이터, 중간 삽입과 삭제, capacity 축소, 여러 스레드의 동시 접근은 제공하지 않습니다. 초기화된 객체를 다시 초기화하려면 먼저 `owned_string_destroy`를 호출해야 합니다.
