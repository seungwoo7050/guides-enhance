# 메모리·포인터·문자열

포인터는 단순한 숫자 주소가 아닙니다. 어떤 객체를 가리키는지, 그 객체가 아직 살아 있는지, 몇 바이트까지 읽거나 쓸 수 있는지 함께 확인해야 합니다.

## 객체와 주소

```c
int value = 42;
int *pointer = &value;
*pointer = 7;
```

`pointer`는 `value`를 가리키며, `*pointer = 7`은 `value`를 바꿉니다.

## NULL 포인터

```c
int read_value(const int *pointer, int *out_value) {
    if (pointer == NULL || out_value == NULL) {
        return -1;
    }
    *out_value = *pointer;
    return 0;
}
```

`NULL`인지 검사하는 것만으로 충분하지 않습니다. `NULL`이 아니어도 이미 수명이 끝난 객체나 배열 범위 밖을 가리킬 수 있습니다.

## 저장 기간과 수명

### 자동 저장 기간

```c
int *wrong(void) {
    int value = 42;
    return &value;
}
```

`value`는 함수가 끝날 때 수명이 끝납니다. 반환한 포인터는 더 이상 유효하지 않습니다.

### 정적 저장 기간

파일 범위 객체와 `static` 지역 객체는 프로그램 실행 동안 존재합니다. 오래 존재한다고 해서 여러 함수나 스레드에서 자유롭게 변경해도 되는 것은 아닙니다.

### 동적 저장 기간

```c
int *values = malloc(count * sizeof *values);
```

할당이 성공하면 `free(values)`를 호출할 때까지 객체가 존재합니다. 누가 해제할지 정해야 합니다.

## 할당 크기 계산

```c
if (count > SIZE_MAX / sizeof *values) {
    return -1;
}
values = malloc(count * sizeof *values);
```

곱셈이 overflow한 뒤 작은 크기가 `malloc`에 전달되지 않도록 먼저 검사합니다.

`malloc(0)`은 `NULL` 또는 해제 가능한 고유 포인터를 반환할 수 있습니다. 빈 상태를 명확히 정하는 편이 좋습니다.

```text
빈 상태:
  data == NULL
  size == 0
  capacity == 0
```

## `realloc` 실패

```c
void *resized = realloc(data, new_size);
if (resized == NULL) {
    return -1;
}
data = resized;
```

`realloc` 결과를 원래 포인터에 바로 대입하면 실패 시 기존 포인터를 잃습니다. 임시 포인터로 결과를 받은 뒤 성공했을 때만 공개 상태를 바꿉니다.

## 소유권

함수 인자로 받은 포인터가 다음 중 무엇인지 정해야 합니다.

- 호출자가 계속 소유하며 함수는 읽기만 합니다.
- 호출자가 계속 소유하며 함수는 내용을 수정합니다.
- 함수가 새 메모리를 할당해 호출자에게 넘깁니다.
- 함수가 포인터의 소유권을 넘겨받아 나중에 해제합니다.

이 규칙은 타입만으로 모두 표현되지 않습니다. 헤더와 README에 분명히 적습니다.

## 얕은 복사와 이중 해제

```c
struct string {
    char *data;
    size_t length;
};

struct string left = right;
```

구조체 대입은 포인터가 가리키는 메모리를 복사하지 않습니다. `left.data`와 `right.data`가 같은 allocation을 가리키게 됩니다. 두 객체가 모두 `free`하면 이중 해제가 발생합니다.

## 배열 범위와 포인터 연산

```c
for (int *cursor = values; cursor != values + count; cursor++) {
    process(*cursor);
}
```

`values + count`는 비교용으로 계산할 수 있지만 역참조하면 안 됩니다.

## 문자열과 버퍼 크기

문자열은 마지막 NUL 바이트까지 저장할 공간이 필요합니다.

```c
size_t length = strlen(source);
if (length == SIZE_MAX) {
    return -1;
}
char *copy = malloc(length + 1);
```

여러 길이를 더할 때도 각 덧셈 전에 overflow를 검사합니다.

```c
if (right_length > SIZE_MAX - left_length - 1) {
    return -1;
}
```

## `memcpy`와 `memmove`

- `memcpy`: 원본과 대상 영역이 겹치지 않을 때 사용합니다.
- `memmove`: 영역이 겹칠 수 있을 때 사용합니다.

같은 버퍼 안에서 데이터를 이동할 때 `memcpy`를 사용하면 동작이 정의되지 않습니다.

## 별칭 입력과 `realloc`

현재 문자열의 일부를 다시 덧붙이면 입력 포인터가 대상 버퍼 안을 가리킬 수 있습니다.

```c
append(&string, string.data + 2);
```

덧붙이는 중 `realloc`이 메모리를 옮기면 기존 입력 포인터는 무효가 됩니다. 기존 포인터 대신 버퍼 시작 위치에서의 오프셋을 기억한 뒤 새 버퍼에서 다시 계산합니다.

```text
source_offset = source - old_data
realloc 성공
source = new_data + source_offset
```

이 계산은 입력 포인터가 실제로 현재 버퍼 안에 있다는 사실을 먼저 확인한 경우에만 사용합니다.

## `const`

```c
size_t text_length(const char *text);
```

`const char *`는 함수가 `text`가 가리키는 문자를 이 포인터를 통해 수정하지 않겠다는 뜻입니다. 포인터 자체의 수명이나 메모리 소유권을 자동으로 보장하지는 않습니다.

## 정리 함수

```c
void buffer_destroy(struct buffer *buffer) {
    if (buffer == NULL) {
        return;
    }
    free(buffer->data);
    buffer->data = NULL;
    buffer->length = 0;
    buffer->capacity = 0;
}
```

정리 뒤 빈 상태로 만들면 같은 객체에 `destroy`를 다시 호출하기 쉽습니다. 단, 다른 코드가 여전히 객체를 사용 중이면 안전하지 않습니다.

## 완료 기준

1. 포인터가 `NULL`이 아닌 것과 유효한 객체를 가리키는 것이 다른 이유를 설명합니다.
2. 지역 객체의 주소를 함수 밖으로 반환하지 않습니다.
3. 할당한 메모리마다 해제할 소유자를 정합니다.
4. `realloc` 실패 시 기존 포인터를 보존합니다.
5. 배열 원소 수와 바이트 수 계산의 overflow를 검사합니다.
6. 겹치는 영역에는 `memmove`를 사용합니다.
7. `realloc` 중 별칭 입력을 오프셋으로 보존하는 이유를 설명합니다.
