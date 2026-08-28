# 함수·배열·문자열

함수는 코드를 단순히 잘게 나누는 수단이 아닙니다. 입력으로 무엇을 받고, 성공하면 무엇을 반환하며, 실패하면 호출자의 값과 자원을 어떻게 처리할지 정하는 단위입니다.

## 함수 선언과 호출

```c
int parse_count(const char *text, size_t *out_count);
```

이 선언에서 확인할 내용은 다음과 같습니다.

- `text`는 읽기만 하는 문자열입니다.
- `out_count`는 성공 결과를 기록할 위치입니다.
- 반환값은 성공 여부를 알립니다.

출력 매개변수는 모든 검사가 끝난 뒤에만 변경하는 편이 안전합니다.

```c
int parse_count(const char *text, size_t *out_count) {
    size_t value;

    if (text == NULL || out_count == NULL) {
        return -1;
    }
    if (parse_size(text, &value) != 0) {
        return -1;
    }
    *out_count = value;
    return 0;
}
```

실패했을 때 `*out_count`가 유지되므로 호출자는 부분 결과를 해석할 필요가 없습니다.

## 값 전달과 포인터 전달

C 함수의 인자는 값으로 전달됩니다.

```c
void increment(int value) {
    value++;
}
```

이 함수는 호출자의 정수를 바꾸지 않습니다. 호출자의 객체를 수정하려면 주소를 전달합니다.

```c
int increment(int *value) {
    if (value == NULL) {
        return -1;
    }
    (*value)++;
    return 0;
}
```

포인터를 전달했다고 해서 함수가 객체를 소유하게 되는 것은 아닙니다. 함수가 단순히 빌려 쓰는지, 메모리를 해제할 수 있는지 별도로 정해야 합니다.

## 배열과 길이

함수 인자의 배열 표기는 실제로 포인터로 조정됩니다.

```c
long sum_values(const long values[], size_t length);
```

함수는 `values`가 가리키는 배열의 길이를 자동으로 알 수 없습니다. 길이를 별도 인자로 전달합니다.

```c
long sum_values(const long *values, size_t length) {
    long total = 0;

    for (size_t index = 0; index < length; index++) {
        total += values[index];
    }
    return total;
}
```

`values == NULL`을 허용할지, `length == 0`일 때 `NULL`을 허용할지는 함수가 정합니다. 호출자와 구현이 같은 규칙을 따라야 합니다.

## 문자열은 NUL로 끝나는 바이트 배열

```c
char text[] = {'h', 'i', '\0'};
```

`strlen`은 `\0`을 찾을 때까지 읽습니다. 배열 안에 종료 문자가 없으면 유효한 범위를 넘어 읽게 됩니다.

```c
size_t text_length(const char *text) {
    size_t length = 0;

    if (text == NULL) {
        return 0;
    }
    while (text[length] != '\0') {
        length++;
    }
    return length;
}
```

문자열 길이에는 마지막 `\0`이 포함되지 않습니다. 문자열을 복사할 공간을 계산할 때는 보통 `length + 1`이 필요합니다.

## 문자열 literal과 수정 가능 여부

```c
const char *message = "hello";
```

문자열 literal의 문자를 수정하면 정의되지 않은 동작입니다. 수정할 배열이 필요하면 별도 배열을 만듭니다.

```c
char message[] = "hello";
message[0] = 'H';
```

## `ctype` 함수와 음수 `char`

`isspace`, `isdigit` 같은 함수에는 `EOF` 또는 `unsigned char`로 표현 가능한 값을 전달해야 합니다.

```c
if (isspace((unsigned char)*cursor)) {
    /* 공백 문자입니다. */
}
```

`char`가 signed인 환경에서는 상위 비트가 설정된 바이트가 음수가 될 수 있습니다. 그대로 전달하면 정의되지 않은 동작이 생길 수 있습니다.

## `struct`로 함께 변하는 값 묶기

```c
struct buffer {
    char *data;
    size_t length;
    size_t capacity;
};
```

이 구조체는 다음 조건을 유지해야 할 수 있습니다.

```text
length <= capacity
capacity == 0이면 data == NULL
문자열을 저장한다면 data[length] == '\0'
```

구조체를 만들었다고 조건이 자동으로 지켜지는 것은 아닙니다. 초기화, 변경, 정리 함수가 같은 규칙을 따라야 합니다.

## 함수 이름은 실제 동작을 드러내기

다음과 같이 코드가 수행하는 일을 구체적으로 나누는 편이 좋습니다.

```text
문자열을 정수로 변환합니다.
통계 값에 새 정수를 추가합니다.
결과를 stdout에 출력합니다.
동적 버퍼의 크기를 늘립니다.
파일에서 남은 바이트를 읽습니다.
```

`process`, `handle`, `manage`처럼 대상과 결과가 드러나지 않는 이름은 의미를 파악하기 어렵습니다.

## 반환값과 출력 매개변수

```c
int vector_get(const struct vector *vector, size_t index, int *out_value) {
    if (vector == NULL || out_value == NULL || index >= vector->size) {
        return -1;
    }
    *out_value = vector->data[index];
    return 0;
}
```

실패 시 `*out_value`를 변경하지 않습니다. 이 규칙은 테스트하기 쉽고 호출자도 다루기 쉽습니다.

## 완료 기준

1. 함수 선언만 보고 입력, 성공 결과와 실패 반환값을 설명합니다.
2. 배열과 길이를 함께 전달합니다.
3. 문자열 공간을 계산할 때 마지막 NUL 바이트를 포함합니다.
4. 문자열 literal을 수정하지 않습니다.
5. `ctype` 함수에 `unsigned char`로 변환한 값을 전달합니다.
6. 함께 변하는 상태를 구조체로 묶고 유지해야 할 조건을 적습니다.
