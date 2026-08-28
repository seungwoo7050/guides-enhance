# 자료구조와 API 작성

자료구조를 구현할 때는 필드를 정하는 데서 끝나지 않습니다. 어떤 상태를 유효하다고 볼지, 함수가 성공하거나 실패하면 값이 어떻게 바뀌는지, 메모리를 누가 정리하는지 함께 정해야 합니다.

## 먼저 유효한 상태를 적기

동적 배열의 예:

```text
size <= capacity
capacity == 0이면 data == NULL이고 size == 0
capacity > 0이면 data != NULL
0 <= index < size인 원소만 읽을 수 있음
```

문자열이라면 NUL 종료 조건이 추가됩니다.

```text
length < capacity
data[length] == '\0'
```

함수를 구현하기 전에 이 조건을 적으면 어떤 입력을 거부해야 하고 언제 상태를 변경할 수 있는지 분명해집니다.

## 공개 구조체와 불투명 타입

작은 C 라이브러리는 구조체 필드를 헤더에 공개할 수 있습니다.

```c
struct int_vector {
    int *data;
    size_t size;
    size_t capacity;
};
```

호출자가 필드를 직접 읽을 수 있지만 잘못 변경하면 유효한 상태가 깨집니다. 공개 필드를 허용한다면 초기화 뒤에는 API를 통해서만 변경한다는 사용 규칙이 필요합니다.

구조체 정의를 `.c` 파일에 숨기고 생성·조회 함수를 제공하는 방식도 있습니다. 이 경우 구현을 바꾸기 쉽지만 동적 할당과 별도 생성 함수가 필요할 수 있습니다.

## 함수별 성공과 실패 정하기

```c
int int_vector_push(struct int_vector *vector, int value);
```

예를 들어 다음처럼 정합니다.

```text
성공: 0, value를 마지막에 추가함
실패: -1, 기존 data/size/capacity/원소를 모두 유지함
```

실패 후 상태까지 적어야 호출자가 재시도하거나 정리할 수 있습니다.

## 실패하기 쉬운 작업을 먼저 수행하기

동적 배열의 `push`는 다음 순서가 안전합니다.

```text
인자와 현재 상태 검사
→ 새 capacity 계산
→ byte 크기 overflow 검사
→ resize 시도
→ 성공한 포인터 반영
→ 새 원소 기록
→ size 증가
```

할당이 성공하기 전에 `capacity`를 먼저 바꾸면 실패 후 `data`와 `capacity`가 서로 맞지 않을 수 있습니다.

## 출력 매개변수는 성공 후 변경하기

```c
int int_vector_get(
    const struct int_vector *vector,
    size_t index,
    int *out_value
) {
    if (vector == NULL || out_value == NULL || index >= vector->size) {
        return -1;
    }
    *out_value = vector->data[index];
    return 0;
}
```

실패 시 `*out_value`를 유지하면 호출자가 이전 값과 부분 결과를 구분할 필요가 없습니다.

## 초기화와 정리

```text
init
→ zero or more operations
→ destroy
```

초기화되지 않은 객체를 정리하거나 같은 객체를 자원 해제 없이 다시 초기화하면 문제가 생깁니다. 정리 뒤 빈 상태로 만들면 반복 호출에 안전하게 만들 수 있습니다.

## 할당 함수 주입

```c
struct allocator {
    void *context;
    void *(*resize)(void *context, void *pointer, size_t size);
    void (*release)(void *context, void *pointer);
};
```

이 기능의 목적은 간접 호출 구조를 늘리는 것이 아니라 다음을 결정적으로 확인하는 데 있습니다.

- 첫 할당 실패
- 다음 크기 증가 실패
- 실패 뒤 포인터와 내용 보존
- 정리 함수가 올바른 release callback을 호출하는지

기본 구현은 `realloc`과 `free`를 사용할 수 있습니다.

## 이름은 실제 동작을 드러내기

다음 이름은 구체적인 동작을 보여 줍니다.

```text
record_reader_next
account_transfer
int_vector_push
owned_string_append
```

`process`, `handle`, `manage`처럼 대상과 결과가 드러나지 않는 이름은 의미를 파악하기 어렵습니다.

## 오류 코드

간단한 라이브러리는 `0`과 `-1`로 성공과 실패를 구분할 수 있습니다. 호출자가 실패 원인을 구분해야 한다면 열거형이나 별도의 결과 타입을 사용할 수 있습니다.

```c
enum parse_result {
    PARSE_OK,
    PARSE_INVALID,
    PARSE_RANGE_ERROR
};
```

오류 종류를 세분화할수록 호출자와 테스트가 그 차이를 실제로 사용해야 합니다.

## 정수와 크기 검사

동적 자료구조에서는 원소 개수와 바이트 수를 따로 검사합니다.

```c
if (capacity > SIZE_MAX / 2) {
    return -1;
}
new_capacity = capacity * 2;

if (new_capacity > SIZE_MAX / sizeof *vector->data) {
    return -1;
}
```

첫 검사는 원소 개수 증가, 두 번째 검사는 실제 바이트 수 계산을 보호합니다.

## 별칭과 자기 참조

```c
owned_string_append(&string, string.data);
```

지원하지 않는다면 명시적으로 금지합니다. 지원한다면 `realloc`과 겹치는 복사를 고려해 구현하고 테스트합니다.

## 테스트할 내용

- 빈 상태에서 첫 삽입
- capacity 안에서 삽입
- 여러 번 크기 증가
- 첫 원소와 마지막 원소 조회
- `NULL` 인자와 범위 밖 index
- 손상된 `size`/`capacity` 조합
- 크기 계산 overflow
- 할당 실패 뒤 포인터와 기존 원소 보존
- 실패한 조회 뒤 출력 매개변수 보존

## 완료 기준

1. 구조체의 유효한 상태를 식으로 적습니다.
2. 각 공개 함수의 성공·실패 후 상태를 설명합니다.
3. 실패 가능한 작업을 먼저 수행하고 성공 후 값을 반영합니다.
4. 동적 메모리의 소유자와 정리 함수를 정합니다.
5. 크기 증가와 바이트 계산을 각각 overflow 검사합니다.
6. 별칭 입력을 지원할지 명시하고 테스트합니다.
