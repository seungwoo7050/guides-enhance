# owned-string

`owned-string`은 NUL로 끝나는 문자열 버퍼를 직접 소유하고, 문자열 내용이 늘어날 때 필요한 만큼 내부 버퍼를 확장하는 C 라이브러리입니다.

일반적인 외부 문자열뿐 아니라 현재 문자열 전체 또는 현재 문자열 내부의 suffix를 다시 append하는 **별칭(alias) 입력**도 지원합니다.

또한 메모리 재할당에 실패하면 호출 전 문자열 상태를 그대로 유지합니다.

## 제공 기능

- 기본 `realloc`/`free`와 사용자 정의 allocator callback
- `length`, `capacity`, NUL 종료 조건 검사
- capacity를 두 배씩 늘리되 `SIZE_MAX` overflow 사전 검사
- 전체 문자열과 내부 suffix의 별칭 append 지원
- 재할당 실패 시 `data`, 내용, `length`, `capacity` 보존
- 여러 번 호출해도 안전한 `owned_string_destroy`

## 유지하는 상태

초기화된 객체는 다음 두 상태 중 하나입니다.

```text
빈 상태:
  data == NULL
  length == 0
  capacity == 0
```

또는:

```text
할당된 상태:
  data != NULL
  length < capacity
  data[length] == '\0'
```

`capacity`는 NUL 문자를 저장할 공간까지 포함한 전체 버퍼 크기입니다.

따라서:

```text
length == 5
```

인 문자열을 저장하려면 최소:

```text
capacity >= 6
```

이어야 합니다.

공개 필드는 `owned_string_init`을 호출한 뒤 라이브러리 함수로만 변경해야 합니다. 호출자가 `length`, `capacity`, `data`를 임의로 수정하면 라이브러리가 유지하는 불변식이 깨질 수 있습니다.

## 빌드

```sh
make
```

정적 라이브러리는 다음 위치에 생성됩니다.

```text
build/libowned_string.a
```

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

성공 후 문자열은 다음 상태입니다.

```text
data   → "hello world\0"
length = 11
capacity > 11
```

## 주요 구현 결정

### 문자열은 내부 버퍼를 직접 소유

`owned_string`은 `data`가 가리키는 메모리를 자신의 수명 동안 소유합니다.

따라서 destroy에서는 해당 버퍼를 해제하며, 호출자는 `data`를 별도로 `free`하지 않습니다.

반대로 append에 전달하는 `source`는 함수가 읽는 입력이며, 함수가 필요하면 그 내용을 자신의 버퍼로 복사합니다.

### 별칭 입력

`source`가 현재 `data` 내부를 가리킬 수 있습니다.

예를 들어 현재 문자열이:

```text
abcdef
```

라면 다음과 같은 입력을 지원합니다.

```text
source = data       → 전체 "abcdef"
source = data + 2   → suffix "cdef"
```

즉 self-append나 내부 suffix append가 가능합니다.

### `realloc` 뒤에는 기존 내부 포인터를 사용할 수 없음

다음 상태를 생각합니다.

```text
data ──────────────┐
                   ▼
              "abcdef\0"
                 ▲
                 │
source = data + 2 ─┘
```

append 과정에서 `realloc`이 버퍼를 다른 주소로 옮기면 기존 `data`뿐 아니라 `source`도 이전 allocation을 가리키는 무효 포인터가 됩니다.

따라서 재할당 전에 내부 별칭을 다음처럼 **offset**으로 바꿔 저장합니다.

```text
source_offset = source - data
```

재할당이 성공한 뒤:

```text
new_source = new_data + source_offset
```

으로 새 주소를 다시 계산합니다.

핵심은 재할당을 넘어서 살아남아야 하는 정보를 "이전 allocation의 포인터"가 아니라 "버퍼 시작부터의 위치"로 저장하는 것입니다.

### 별칭 범위

내부 별칭으로 취급하는 `source`는 현재 문자열 안의 NUL 종료 suffix를 가리켜야 합니다.

즉 개념적으로:

```text
data <= source <= data + length
```

범위에 있으며 `source`부터 `data[length]`의 NUL까지가 유효한 문자열이어야 합니다.

버퍼의 사용하지 않는 capacity 영역을 임의의 문자열처럼 읽는 것은 지원되는 별칭 입력으로 간주하지 않습니다.

### 겹치는 복사

self-append나 suffix append에서는 원본과 목적지 범위가 같은 allocation에 있을 수 있습니다.

따라서 구현은 겹칠 가능성이 있는 메모리를 안전하게 복사하는 방식을 사용해야 합니다. 단순히 "재할당 뒤 source 주소만 다시 구하면 끝"이 아니라, 실제 복사 연산도 별칭을 고려해야 합니다.

### 필요한 크기를 먼저 계산

append 전에 최소한 다음 크기를 계산해야 합니다.

```text
현재 length
추가할 source 길이
새 문자열의 length
마지막 NUL을 포함한 필요한 capacity
```

개념적으로:

```text
required = old_length + source_length + 1
```

입니다.

각 덧셈과 capacity 성장은 `SIZE_MAX`를 넘지 않는지 먼저 확인합니다.

### 실패 시 기존 상태 유지

새 capacity 계산과 `resize`가 모두 성공한 뒤에만 객체의 `data`와 `capacity`를 새 상태로 바꿉니다.

할당 실패 시에는 다음이 모두 유지되어야 합니다.

```text
data 주소
문자열 내용
length
capacity
마지막 NUL
```

즉 append는 실패했다고 기존 문자열까지 잃어버리지 않습니다.

## 잘못된 상태 검사

다음과 같은 객체는 유효하지 않습니다.

```text
data == NULL인데 capacity > 0
length >= capacity
data[length] != '\0'
```

라이브러리는 이런 상태를 정상 문자열로 가정하고 계속 쓰지 않습니다.

이 검사는 이미 발생한 메모리 손상을 복구하는 기능이 아니라, 불변식이 깨진 객체에 추가 연산을 수행하지 않게 하는 방어적 검사입니다.

## 정리와 재초기화

`owned_string_destroy`는 내부 allocation을 해제하고 객체를 빈 상태로 돌립니다.

```text
data = NULL
length = 0
capacity = 0
```

반복 호출해도 안전하도록 구현합니다.

이미 초기화된 객체에 다시 `owned_string_init`을 바로 호출하면 기존 allocation의 소유권을 잃을 수 있으므로, 재초기화하려면 먼저:

```text
owned_string_destroy
→ owned_string_init
```

순서를 사용합니다.

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

별칭 테스트에서는 특히 **재할당이 실제로 일어나는 경우**를 포함해야 합니다. 재할당이 없는 self-append만 검사하면 이전 주소를 저장하는 버그를 발견하지 못할 수 있습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Owned buffer and allocator callbacks | `include/owned_string.h` |
| 2 | Empty-state initialization and invariant checks | `src/owned_string.c` |
| 3 | Capacity calculation for aliased input | `src/owned_string.c` |
| 4 | Append only after successful resize | `src/owned_string.c` |
| 5 | Repeatable cleanup | `src/owned_string.c` |

## 범위

NUL로 끝나는 바이트 문자열만 저장합니다.

따라서 데이터 중간의 NUL 바이트를 포함하는 임의 바이트 배열을 길이와 함께 저장하는 컨테이너가 아닙니다.

다음 기능도 제공하지 않습니다.

- 중간 삽입
- 중간 삭제
- capacity 축소
- 여러 스레드의 동시 접근

초기화된 객체를 다시 초기화하려면 먼저 `owned_string_destroy`를 호출해야 합니다.