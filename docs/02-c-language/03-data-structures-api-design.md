# 자료구조와 API 작성

자료구조를 구현할 때는 구조체 필드를 정하는 것만으로 충분하지 않습니다. 다음을 함께 정의해야 자료구조와 API가 일관되게 동작합니다.

- 어떤 내부 상태를 **유효한 상태**로 볼 것인가
- 각 함수가 어떤 입력을 허용하는가
- 함수가 성공하면 상태가 어떻게 바뀌는가
- 함수가 실패하면 기존 상태를 얼마나 보존하는가
- 동적 메모리의 소유자는 누구인가
- 초기화와 정리는 어떤 순서로 수행해야 하는가

이 규칙들이 명확하면 구현, 테스트, 호출 코드가 모두 같은 계약을 기준으로 동작할 수 있습니다.

## 먼저 유효한 상태를 적기

자료구조가 항상 만족해야 하는 조건을 **불변식(invariant)** 이라고 부를 수 있습니다.

동적 배열의 예:

```c
struct int_vector {
    int *data;
    size_t size;
    size_t capacity;
};
```

이 구조체에 대해 다음과 같은 불변식을 정할 수 있습니다.

```text
size <= capacity

capacity == 0이면:
  data == NULL
  size == 0

capacity > 0이면:
  data != NULL

읽을 수 있는 원소:
  0 <= index < size
```

여기서 `capacity`는 현재 할당된 저장 공간에 넣을 수 있는 최대 원소 수이고, `size`는 실제로 값이 들어 있는 원소 수입니다.

예를 들어

```text
size = 3
capacity = 8
```

이라면 `data[0]`, `data[1]`, `data[2]`는 현재 자료구조의 원소이지만 `data[3]`부터 `data[7]`까지는 용량에 포함될 뿐 아직 논리적인 원소는 아닙니다.

문자열 자료구조라면 종료 문자 조건이 추가됩니다.

```c
struct owned_string {
    char *data;
    size_t length;
    size_t capacity;
};
```

예를 들어 다음과 같은 불변식을 정할 수 있습니다.

```text
빈 상태:
  data == NULL
  length == 0
  capacity == 0

버퍼가 존재하는 상태:
  data != NULL
  length < capacity
  data[length] == '\0'
```

`length < capacity`인 이유는 실제 문자 `length`개 외에 종료 문자 `'\0'`를 저장할 공간이 한 바이트 더 필요하기 때문입니다.

함수를 구현하기 전에 불변식을 적어 두면 다음 질문에 답하기 쉬워집니다.

- 어떤 입력 상태를 정상으로 볼 것인가
- 어떤 입력을 거부해야 하는가
- 어느 시점에 필드를 변경해도 되는가
- 함수가 반환되기 전에 어떤 상태를 복구해야 하는가

## 불변식과 입력 검사는 같은 것이 아닙니다

자료구조의 불변식을 정했다고 해서 모든 공개 함수가 내부 손상을 완전히 검사해야 하는 것은 아닙니다.

예를 들어

```text
size <= capacity
capacity > 0이면 data != NULL
```

을 불변식으로 정했더라도, 정상적인 API 사용만 허용하는 라이브러리라면 모든 함수가 매번 이 조건을 검사하지 않을 수 있습니다.

두 가지 정책을 구분해야 합니다.

```text
1. API 계약상 항상 유효한 객체만 전달되어야 함
2. 함수가 손상된 객체까지 검사해 오류로 반환함
```

둘 다 가능한 설계지만 같은 것은 아닙니다.

특히 구조체 필드를 공개하면 호출자가 직접 값을 변경할 수 있으므로 다음과 같은 잘못된 상태가 만들어질 수 있습니다.

```c
vector.size = 100;
vector.capacity = 4;
```

이런 임의 손상까지 모든 함수가 방어해야 하는지, 아니면 API 계약 위반으로 취급할지 문서에서 정해야 합니다.

## 공개 구조체와 불투명 타입

작은 C 라이브러리는 구조체 정의를 헤더에 공개할 수 있습니다.

```c
struct int_vector {
    int *data;
    size_t size;
    size_t capacity;
};
```

장점은 다음과 같습니다.

- 호출자가 구조체 크기를 알 수 있음
- 스택이나 다른 구조체의 멤버로 직접 배치할 수 있음
- 디버깅할 때 내부 상태를 쉽게 볼 수 있음
- 별도의 생성 함수 없이 `init` 패턴을 사용하기 쉬움

예:

```c
struct int_vector vector;

if (int_vector_init(&vector) != 0) {
    /* 실패 처리 */
}
```

반면 필드가 공개되어 있으므로 호출자가 직접 상태를 변경해 불변식을 깨뜨릴 수 있습니다.

```c
vector.size = 1000;   /* API 규칙을 깨뜨릴 수 있음 */
```

따라서 공개 구조체를 사용한다면 보통 다음 규칙을 문서화합니다.

```text
구조체 필드는 관찰할 수 있지만,
초기화 이후 상태 변경은 공개 API를 통해서만 수행한다.
```

### 불투명 타입

구조체 정의를 `.c` 파일에 숨길 수도 있습니다.

헤더:

```c
struct int_vector;

struct int_vector *int_vector_create(void);
void int_vector_destroy(struct int_vector *vector);
```

구현 파일:

```c
struct int_vector {
    int *data;
    size_t size;
    size_t capacity;
};
```

호출자는 구조체 내부 필드를 알 수 없으므로 직접 불변식을 깨뜨리기 어렵습니다.

장점:

- 내부 표현을 바꾸기 쉬움
- 호출자가 필드를 직접 수정하지 못함
- 구현 세부사항을 API에서 숨길 수 있음

단점:

- 불완전 타입이므로 호출자가 구조체 크기를 알 수 없음
- 위와 같은 포인터 기반 API에서는 생성 함수와 동적 할당이 필요해질 수 있음
- 메모리 관리 규칙이 하나 더 생김

즉, 공개 구조체와 불투명 타입의 선택은 단순한 문법 문제가 아니라 **표현의 공개 범위와 수명 관리 방식**에 대한 API 설계 결정입니다.

## 함수별 성공과 실패 정하기

공개 함수는 반환값뿐 아니라 성공과 실패 후 상태까지 정의하는 것이 좋습니다.

예:

```c
int int_vector_push(struct int_vector *vector, int value);
```

다음처럼 계약을 정할 수 있습니다.

```text
성공:
  반환값은 0
  value가 마지막 원소로 추가됨
  size가 1 증가함
  필요한 경우 capacity와 data가 변경될 수 있음

실패:
  반환값은 -1
  기존 data, size, capacity, 기존 원소를 모두 유지함
```

이처럼 실패 시 기존 상태를 그대로 유지하는 보장을 흔히 **강한 실패 보장(strong failure guarantee)** 과 비슷한 성질로 생각할 수 있습니다.

C 표준의 공식 용어는 아니지만 API 계약을 설명하는 데 유용합니다.

호출자는 실패 후에도 다음과 같이 기존 객체를 계속 사용할 수 있습니다.

```c
if (int_vector_push(&vector, value) != 0) {
    /* vector에는 이전 원소들이 그대로 남아 있음 */
}
```

반대로 실패 시 일부 상태가 변경될 수 있는 API라면 그 사실을 반드시 문서화해야 합니다.

## 사전 조건과 사후 조건

함수 계약을 더 명확히 하려면 다음 세 부분으로 생각할 수 있습니다.

```text
사전 조건(precondition):
  호출 전에 만족해야 하는 조건

성공 사후 조건(postcondition):
  성공 반환 후 보장되는 상태

실패 사후 조건:
  실패 반환 후 보장되는 상태
```

예를 들어 `int_vector_push`의 계약을 다음처럼 적을 수 있습니다.

```text
사전 조건:
  vector != NULL
  vector가 초기화된 유효한 상태임

성공:
  기존 원소의 값은 유지됨
  마지막에 value가 추가됨
  size가 이전 값 + 1이 됨

실패:
  기존 원소와 size/capacity/data가 변하지 않음
```

이 형식은 구현 순서를 결정할 때도 도움이 됩니다.

## 실패하기 쉬운 작업을 먼저 수행하기

동적 배열에 새 원소를 추가하는 작업은 용량이 부족하면 메모리 할당에 실패할 수 있습니다.

따라서 실패 가능한 작업이 끝나기 전에 공개 상태를 먼저 변경하지 않는 것이 좋습니다.

예를 들어 다음 순서를 사용할 수 있습니다.

```text
인자 검사
→ 현재 상태 확인
→ 필요한 새 capacity 계산
→ byte 크기 overflow 검사
→ realloc 시도
→ 성공한 새 포인터 반영
→ 새 원소 기록
→ size 증가
```

잘못된 순서의 예:

```c
vector->capacity = new_capacity;

int *resized = realloc(
    vector->data,
    new_capacity * sizeof *vector->data
);

if (resized == NULL) {
    return -1;
}
```

`realloc`이 실패하면 실제 할당 크기는 예전 그대로인데 `capacity`만 커진 상태가 됩니다.

```text
capacity는 16이라고 기록됨
실제 data는 여전히 8개 원소 크기
```

이제 불변식이 깨지고 이후 코드가 존재하지 않는 공간을 사용하려 할 수 있습니다.

대신 임시 변수에서 계산하고, 실패 가능한 작업이 모두 성공한 뒤 구조체에 반영합니다.

```c
size_t new_capacity = /* 계산 */;

int *resized = realloc(
    vector->data,
    new_capacity * sizeof *vector->data
);

if (resized == NULL) {
    return -1;
}

vector->data = resized;
vector->capacity = new_capacity;
```

그 뒤 새 원소를 기록하고 마지막에 `size`를 증가시키면 상태 변경 순서가 더 분명해집니다.

## 출력 매개변수는 성공 후 변경하기

C API에서는 반환값을 성공/실패에 사용하고 실제 결과는 출력 매개변수로 전달하는 방식이 흔합니다.

```c
int int_vector_get(
    const struct int_vector *vector,
    size_t index,
    int *out_value
);
```

구현 예:

```c
int int_vector_get(
    const struct int_vector *vector,
    size_t index,
    int *out_value
) {
    if (vector == NULL || out_value == NULL) {
        return -1;
    }

    if (index >= vector->size) {
        return -1;
    }

    *out_value = vector->data[index];
    return 0;
}
```

이 함수는 실패 경로에서 `*out_value`를 변경하지 않습니다.

호출자는 다음처럼 사용할 수 있습니다.

```c
int value = 123;

if (int_vector_get(&vector, 10, &value) != 0) {
    /* value는 여전히 123 */
}
```

이 규칙은 부분 결과와 실패 결과를 구분하기 쉽게 합니다.

특히 출력 값 계산 중 실패할 수 있는 작업이 여러 개 있다면 임시 변수에 먼저 결과를 만든 뒤 마지막에 출력 매개변수에 기록하는 방식이 유용합니다.

```c
int temporary;

/* temporary 계산 */

*out_value = temporary;
return 0;
```

## 초기화와 정리

자료구조의 수명 주기는 명확하게 정의하는 것이 좋습니다.

```text
초기화되지 않은 저장 공간
  ↓ init 성공
유효한 빈 객체
  ↓ zero or more operations
유효한 사용 중 객체
  ↓ destroy
정리된 빈 상태
```

예를 들어 공개 구조체를 다음처럼 초기화할 수 있습니다.

```c
int int_vector_init(struct int_vector *vector) {
    if (vector == NULL) {
        return -1;
    }

    vector->data = NULL;
    vector->size = 0;
    vector->capacity = 0;
    return 0;
}
```

정리 함수는 다음처럼 작성할 수 있습니다.

```c
void int_vector_destroy(struct int_vector *vector) {
    if (vector == NULL) {
        return;
    }

    free(vector->data);

    vector->data = NULL;
    vector->size = 0;
    vector->capacity = 0;
}
```

정리 후 다시 빈 상태로 만들면 같은 객체에 대해 `destroy`를 다시 호출하기 쉬워집니다.

### 초기화되지 않은 객체

다음 객체는 선언 직후 필드 값이 정해져 있지 않을 수 있습니다.

```c
struct int_vector vector;
```

이 상태에서 바로

```c
int_vector_destroy(&vector);
```

를 호출하면 `vector.data`가 유효한 초기값이라는 보장이 없으므로 잘못된 메모리를 `free`하려 할 수 있습니다.

따라서 API가 다음 수명 주기를 요구한다면 이를 문서화해야 합니다.

```text
반드시 init 성공 후에만
다른 연산과 destroy를 호출한다.
```

### 다시 초기화하기

이미 동적 메모리를 소유하고 있는 객체에 단순히 `init`을 다시 호출하면 기존 포인터를 잃어 메모리 누수가 발생할 수 있습니다.

```c
int_vector_init(&vector);  /* 이미 사용 중인 vector라면 위험 */
```

따라서 일반적인 규칙은 다음 중 하나입니다.

```text
destroy → init
```

또는 별도의 재설정 함수를 제공합니다.

```c
int_vector_clear(&vector);
```

`clear`는 원소만 제거하고 capacity는 유지할 수도 있고, 모든 메모리를 해제할 수도 있습니다. 어느 의미인지 함수 이름과 문서에서 명확히 해야 합니다.

## 소유권과 정리 책임

동적 자료구조는 내부 메모리의 소유권을 명시해야 합니다.

예를 들어 `int_vector`가 `data`를 직접 할당한다면 다음 계약을 가질 수 있습니다.

```text
int_vector가 data를 소유한다.
호출자는 data를 직접 free하지 않는다.
int_vector_destroy가 data를 해제한다.
```

반대로 호출자가 제공한 외부 버퍼를 잠시 사용하는 자료구조라면 정리 함수가 그 버퍼를 해제해서는 안 됩니다.

```text
data는 호출자가 소유한다.
자료구조는 빌려서 사용한다.
destroy는 data를 free하지 않는다.
```

동일한 `int *data` 필드라도 소유권 규칙은 타입만으로 알 수 없으므로 API 문서가 필요합니다.

## 할당 함수 주입

테스트에서 메모리 할당 실패를 의도적으로 발생시키려면 할당 함수를 외부에서 주입하는 방식을 사용할 수 있습니다.

예:

```c
struct allocator {
    void *context;

    void *(*resize)(
        void *context,
        void *pointer,
        size_t size
    );

    void (*release)(
        void *context,
        void *pointer
    );
};
```

`context`는 사용자 정의 allocator가 자신의 상태를 저장하는 데 사용할 수 있는 포인터입니다.

예를 들어 테스트 allocator는 다음 정보를 가질 수 있습니다.

```text
현재까지의 할당 호출 횟수
몇 번째 호출에서 실패할지
해제된 포인터 목록
```

그러면 다음 상황을 결정적으로 재현할 수 있습니다.

- 첫 할당 실패
- 두 번째 용량 증가 실패
- 특정 `push` 시점의 재할당 실패
- 실패 후 포인터와 기존 원소 보존
- 정리 함수가 올바른 `release` 콜백을 호출하는지
- 성공한 할당과 해제가 서로 짝을 이루는지

### allocator 콜백의 계약

콜백을 주입하려면 콜백 자체의 의미도 정해야 합니다.

예를 들어 `resize`가 `realloc`과 같은 의미를 가진다고 정한다면 다음을 문서화해야 합니다.

```text
pointer == NULL이면 새 할당처럼 동작
size > 0에서 실패하면 NULL 반환
실패 시 기존 pointer가 가리키는 할당은 유지
성공 시 반환된 포인터가 이후의 유효한 할당
```

크기 `0`의 의미까지 `realloc`과 완전히 동일하게 따르게 할지, 아니면 API 자체에서 `size == 0`을 `release`로 별도 처리할지도 정해야 합니다.

이 계약이 없으면 기본 allocator와 테스트 allocator가 서로 다른 의미로 동작할 수 있습니다.

기본 구현은 보통 `realloc`과 `free`를 감싸서 만들 수 있습니다.

```c
static void *default_resize(
    void *context,
    void *pointer,
    size_t size
) {
    (void)context;
    return realloc(pointer, size);
}

static void default_release(
    void *context,
    void *pointer
) {
    (void)context;
    free(pointer);
}
```

할당 함수 주입의 목적은 간접 호출 자체가 아니라, 평소 재현하기 어려운 실패 경로를 테스트 가능하게 만드는 데 있습니다.

## 이름은 실제 동작을 드러내기

API 이름은 함수가 다루는 대상과 수행하는 작업을 함께 보여 주는 편이 좋습니다.

예:

```text
record_reader_next
account_transfer
int_vector_push
owned_string_append
```

각 이름에서 무엇을 대상으로 무엇을 하는지 비교적 분명합니다.

반면 다음과 같은 이름은 문맥 없이는 동작을 알기 어렵습니다.

```text
process
handle
manage
execute
```

예를 들어

```c
int process(struct int_vector *vector);
```

만 보면 다음을 알기 어렵습니다.

- 원소를 추가하는가
- 원소를 정렬하는가
- 파일로 저장하는가
- 내부 상태를 검증하는가

가능하면 함수 이름만 보아도 입력 대상과 상태 변화가 어느 정도 드러나게 만듭니다.

## 상태를 바꾸는 함수와 조회 함수를 구분하기

함수 이름과 타입은 상태 변경 여부도 어느 정도 드러낼 수 있습니다.

조회 함수:

```c
size_t int_vector_size(const struct int_vector *vector);

int int_vector_get(
    const struct int_vector *vector,
    size_t index,
    int *out_value
);
```

상태 변경 함수:

```c
int int_vector_push(
    struct int_vector *vector,
    int value
);

void int_vector_clear(
    struct int_vector *vector
);
```

`const struct int_vector *`는 해당 포인터를 통해 구조체를 수정하지 않는다는 의도를 보여 줍니다.

물론 `const`만으로 소유권이나 전체 프로그램의 불변성을 보장하는 것은 아니지만, API를 읽는 사람에게 중요한 정보를 제공합니다.

## 오류 코드

간단한 라이브러리는 다음처럼 성공과 실패만 구분할 수 있습니다.

```text
0  = 성공
-1 = 실패
```

예:

```c
if (int_vector_push(&vector, value) != 0) {
    /* 실패 처리 */
}
```

호출자가 실패 이유에 따라 다른 동작을 해야 한다면 오류 종류를 구분할 수 있습니다.

```c
enum parse_result {
    PARSE_OK,
    PARSE_INVALID,
    PARSE_RANGE_ERROR
};
```

예:

```c
enum parse_result result = parse_number(text, &value);

switch (result) {
case PARSE_OK:
    break;

case PARSE_INVALID:
    /* 형식 오류 */
    break;

case PARSE_RANGE_ERROR:
    /* 표현 가능한 범위를 벗어남 */
    break;
}
```

오류 종류를 많이 만들수록 항상 좋은 것은 아닙니다.

다음 질문을 기준으로 판단할 수 있습니다.

```text
호출자가 이 실패 원인을 실제로 구분해서 처리하는가?
테스트에서도 그 차이를 검증할 필요가 있는가?
```

구분할 필요가 없다면 단순한 성공/실패 코드가 더 적절할 수 있습니다.

## 정수와 크기 검사

동적 자료구조에서는 다음 두 종류의 크기를 구분해야 합니다.

```text
원소 개수
바이트 수
```

예를 들어 capacity를 두 배로 증가시킨다고 가정합니다.

```c
if (capacity > SIZE_MAX / 2) {
    return -1;
}

size_t new_capacity = capacity * 2;
```

이 검사는 **원소 개수 계산**이 `size_t` 범위를 넘는 것을 막습니다.

그 뒤 실제 할당 바이트 수를 계산할 때 다시 검사합니다.

```c
if (new_capacity > SIZE_MAX / sizeof *vector->data) {
    return -1;
}

size_t bytes =
    new_capacity * sizeof *vector->data;
```

이 검사는 **원소 개수 × 원소 크기** 계산이 넘치는 것을 막습니다.

두 검사는 서로 다른 계산을 보호합니다.

```text
capacity * 2
new_capacity * sizeof(element)
```

첫 번째가 안전하다고 해서 두 번째도 자동으로 안전한 것은 아닙니다.

## capacity 증가 정책

동적 배열의 capacity를 늘릴 때 반드시 두 배만 사용해야 하는 것은 아닙니다.

중요한 것은 다음 조건입니다.

- 필요한 최소 원소 수 이상이어야 함
- 증가 계산이 overflow하지 않아야 함
- 바이트 수 계산이 overflow하지 않아야 함

예를 들어 빈 배열의 첫 capacity를 4로 시작하고 이후 두 배로 늘릴 수 있습니다.

```text
0 → 4 → 8 → 16 → 32
```

`push` 전에 필요한 원소 수를 먼저 계산하면 조건이 더 명확해집니다.

```c
if (vector->size == SIZE_MAX) {
    return -1;
}

size_t required = vector->size + 1;
```

그 뒤

```text
capacity >= required
```

이면 재할당할 필요가 없고, 그렇지 않으면 `required` 이상이 되도록 새 capacity를 계산합니다.

## 별칭과 자기 참조

동적 문자열처럼 입력 포인터가 자신의 내부 버퍼를 가리킬 가능성이 있는 API는 **별칭(aliasing)** 정책을 정해야 합니다.

예:

```c
owned_string_append(&string, string.data);
```

또는

```c
owned_string_append(
    &string,
    string.data + 2
);
```

입력 문자열이 현재 `string.data` 내부를 가리킬 수 있습니다.

이 상황을 지원하지 않는다면 계약에 명시적으로 금지해야 합니다.

```text
source는 destination의 내부 버퍼를 가리켜서는 안 된다.
```

지원한다면 구현에서 두 가지 문제를 고려해야 합니다.

### 1. `realloc`으로 입력 포인터가 무효화될 수 있음

```text
source ──> 기존 string.data 내부
```

용량 증가 중 `realloc`이 버퍼를 이동시키면 기존 `source`를 더 이상 사용할 수 없습니다.

내부 포인터라는 사실을 이미 알고 있다면 재할당 전에 오프셋을 저장하고 새 버퍼에서 다시 계산할 수 있습니다.

```text
source_offset = source - old_data
realloc 성공
source = new_data + source_offset
```

### 2. 원본과 대상 복사 영역이 겹칠 수 있음

자기 자신의 일부를 뒤에 덧붙이면 복사 과정에서 원본과 목적 영역이 겹칠 가능성을 검토해야 합니다.

겹칠 수 있다면 `memcpy`가 아니라 `memmove`가 필요할 수 있습니다.

따라서 “자기 참조 입력 지원”은 단순히 호출을 허용한다고 적는 것으로 끝나지 않습니다.

다음을 함께 테스트해야 합니다.

- 재할당이 없는 자기 append
- 재할당이 발생하는 자기 append
- 전체 버퍼를 source로 사용
- 내부 중간 위치를 source로 사용
- 복사 영역이 겹치는 경우
- 할당 실패 시 기존 문자열 보존

## 테스트는 계약을 검증해야 합니다

테스트 항목은 단순히 코드 줄을 실행하는 데 목적이 있는 것이 아니라 불변식과 함수 계약을 검증해야 합니다.

### 정상 동작

- 빈 상태에서 첫 삽입
- capacity 안에서 삽입
- capacity가 정확히 찬 상태에서 추가 삽입
- 여러 번의 capacity 증가
- 첫 원소 조회
- 중간 원소 조회
- 마지막 원소 조회

### 잘못된 입력

- `NULL` 구조체 포인터
- `NULL` 출력 포인터
- `index == size`
- `index > size`
- API가 손상된 상태 검사를 지원한다면 `size > capacity`
- API가 손상된 상태 검사를 지원한다면 `capacity > 0 && data == NULL`

### 정수 경계

- capacity 증가 overflow
- 원소 개수 × 원소 크기 overflow
- `size + 1` overflow 가능성

### 할당 실패

주입한 allocator를 사용하면 다음을 각각 재현할 수 있습니다.

```text
첫 할당 실패
첫 resize 실패
두 번째 resize 실패
```

각 실패 후 다음을 확인합니다.

```text
data가 이전 포인터인지
size가 이전 값인지
capacity가 이전 값인지
기존 원소 값이 그대로인지
```

### 출력 매개변수

조회 함수 실패 전에 특정 값을 넣어 둡니다.

```c
int output = 1234;
```

실패 호출 후에도

```c
output == 1234
```

인지 확인하면 실패 시 출력 매개변수를 보존한다는 계약을 검증할 수 있습니다.

### 정리

- 빈 객체를 `destroy`
- 사용 중인 객체를 `destroy`
- 계약에서 허용한다면 `destroy`를 두 번 호출
- allocator의 `release`가 정확한 포인터로 호출되었는지 확인

## API를 읽을 때 확인할 사항

- 이 구조체의 불변식은 무엇인가?
- 호출자는 구조체 필드를 직접 변경해도 되는가?
- 이 함수의 사전 조건은 무엇인가?
- 성공 후 어떤 상태 변화가 보장되는가?
- 실패 후 기존 상태는 얼마나 보존되는가?
- 출력 매개변수는 실패 시 유지되는가?
- 객체는 반드시 `init`을 거쳐야 하는가?
- `destroy` 후 다시 사용할 수 있는 상태인가?
- 같은 객체를 다시 `init`하려면 먼저 `destroy`해야 하는가?
- 내부 동적 메모리의 소유자는 누구인가?
- capacity 계산과 바이트 수 계산을 각각 overflow 검사하는가?
- allocator 콜백의 성공·실패 의미가 명확한가?
- 자기 참조 또는 별칭 입력을 지원하는가?
- 지원한다면 `realloc`과 겹치는 복사를 모두 고려했는가?
- 오류 종류를 호출자가 실제로 구분할 필요가 있는가?
- 테스트가 구현 세부사항이 아니라 공개 계약을 검증하고 있는가?

## 완료 기준

1. 자료구조가 항상 만족해야 하는 불변식을 식이나 조건으로 적습니다.
2. 불변식과 함수의 입력 검증 정책이 서로 다른 문제임을 설명합니다.
3. 공개 구조체와 불투명 타입의 장단점을 설명합니다.
4. 각 공개 함수의 사전 조건과 성공·실패 후 상태를 설명합니다.
5. 실패 가능한 작업을 먼저 수행하고 성공한 뒤 공개 상태를 반영합니다.
6. 실패 시 기존 상태를 보존해야 하는 API에서 필드 변경 순서를 올바르게 구성합니다.
7. 출력 매개변수는 성공이 확정된 뒤 변경합니다.
8. `init → operations → destroy`의 수명 주기를 정의합니다.
9. 초기화되지 않은 객체를 정리하면 안 되는 이유를 설명합니다.
10. 동적 메모리의 소유자와 해제 책임을 정합니다.
11. allocator를 주입할 때 `resize`와 `release` 콜백의 계약을 명시합니다.
12. capacity 증가와 실제 바이트 수 계산을 각각 overflow 검사합니다.
13. 필요한 원소 수와 capacity 증가 정책을 구분합니다.
14. 별칭·자기 참조 입력을 지원할지 API 계약에 명시합니다.
15. 자기 참조 입력을 지원한다면 `realloc`에 의한 포인터 무효화와 복사 영역 겹침을 모두 처리합니다.
16. 오류 코드는 호출자가 실제로 구분해야 하는 수준까지만 세분화합니다.
17. 테스트가 정상 경로뿐 아니라 경계값, 할당 실패, 상태 보존, 정리 계약까지 검증하도록 구성합니다.
