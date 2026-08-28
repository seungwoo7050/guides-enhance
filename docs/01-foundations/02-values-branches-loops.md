# 값·분기·반복

프로그램은 입력을 값으로 바꾸고, 조건에 따라 다른 코드를 실행하며, 같은 작업을 여러 번 반복합니다. 이 과정에서 중요한 것은 문법을 외우는 것보다 **현재 값이 어떤 범위를 가지며 반복할 때 무엇이 유지되어야 하는지** 이해하는 것입니다.

## 정수 타입과 범위

```c
int count = 0;
long total = 0;
size_t length = 0;
```

- `int`: 일반적인 정수 계산과 함수 반환값에 자주 사용합니다.
- `long`: `int`보다 넓은 범위가 필요할 때 사용할 수 있습니다.
- `size_t`: 객체의 크기와 원소 개수를 나타내는 부호 없는 타입입니다.

타입의 실제 폭은 구현 환경에 따라 달라질 수 있습니다. 정확한 최댓값과 최솟값은 `<limits.h>`와 `<stdint.h>`의 매크로를 사용합니다.

## 부호 있는 값과 부호 없는 값

부호 있는 정수와 `size_t`를 비교하면 부호 있는 값이 부호 없는 값으로 변환될 수 있습니다.

```c
int index = -1;
size_t length = 10;

if (index < length) {
    /* 예상과 다른 결과가 나올 수 있습니다. */
}
```

음수 여부를 먼저 확인한 뒤 변환합니다.

```c
if (index >= 0 && (size_t)index < length) {
    /* 유효한 범위입니다. */
}
```

경고를 없애려고 무조건 캐스트하지 않습니다. 변환 전 값이 대상 타입으로 표현 가능한지 먼저 확인합니다.

## 조건문

```c
if (value < 0) {
    fprintf(stderr, "음수는 허용하지 않습니다.\n");
    return -1;
} else if (value == 0) {
    puts("zero");
} else {
    puts("positive");
}
```

포인터나 정수의 의미를 분명히 드러내기 위해 비교 대상을 적는 편이 읽기 쉽습니다.

```c
if (pointer == NULL) {
    return -1;
}
```

## 논리 연산자의 짧은 평가

`&&`와 `||`는 왼쪽부터 평가하며 결과가 이미 정해지면 오른쪽을 평가하지 않습니다.

```c
if (text != NULL && text[0] != '\0') {
    /* text가 NULL이 아닐 때만 text[0]을 읽습니다. */
}
```

이 순서는 포인터 검사와 범위 검사를 앞에 둘 때 유용합니다.

```c
if (index < length && values[index] == target) {
    /* index가 유효할 때만 배열을 읽습니다. */
}
```

## 반복문과 유지해야 할 조건

```c
size_t index = 0;

while (index < length) {
    process(values[index]);
    index++;
}
```

반복문을 읽을 때는 다음을 확인합니다.

- 반복을 시작하기 전에 어떤 값이 준비되어 있습니까?
- 본문에 들어올 때 항상 참이어야 하는 조건은 무엇입니까?
- 한 번 실행한 뒤 어떤 값이 바뀝니까?
- 언젠가 종료 조건에 도달합니까?

위 예에서는 본문에 들어올 때 `index < length`이므로 `values[index]`를 읽을 수 있습니다. 본문 끝에서 `index`를 증가시키므로 유한한 `length`에 대해 반복은 종료합니다.

초기화, 조건, 갱신이 한 변수에 모이면 `for` 문이 읽기 쉽습니다.

```c
for (size_t index = 0; index < length; index++) {
    total += values[index];
}
```

## 누적 상태

여러 입력에서 통계를 계산할 때는 필요한 값을 먼저 정합니다.

```c
struct statistics {
    size_t count;
    long minimum;
    long maximum;
    long sum;
};
```

첫 값은 최솟값과 최댓값을 초기화하는 기준으로 사용할 수 있습니다.

```c
if (stats->count == 0) {
    stats->minimum = value;
    stats->maximum = value;
} else {
    if (value < stats->minimum) {
        stats->minimum = value;
    }
    if (value > stats->maximum) {
        stats->maximum = value;
    }
}
```

`minimum = 0`으로 시작하면 모든 입력이 양수일 때 실제로 입력되지 않은 `0`이 최솟값으로 남을 수 있습니다. 초기값은 결과에 영향을 주므로 근거 없이 정하지 않습니다.

## overflow를 계산 전에 검사하기

부호 있는 정수 overflow는 정의되지 않은 동작입니다. 계산한 뒤 결과를 검사해서는 늦습니다.

```c
#include <limits.h>

int add_long(long left, long right, long *out) {
    if (out == NULL) {
        return -1;
    }
    if ((right > 0 && left > LONG_MAX - right) ||
        (right < 0 && left < LONG_MIN - right)) {
        return -1;
    }
    *out = left + right;
    return 0;
}
```

뺄셈과 곱셈도 같은 원칙을 적용합니다. 위험한 연산을 먼저 실행하지 않습니다.

## `switch`

```c
switch (command) {
case COMMAND_START:
    start();
    break;
case COMMAND_STOP:
    stop();
    break;
default:
    return -1;
}
```

`break`를 생략하면 다음 `case`로 계속 실행됩니다. 의도한 동작이 아니라면 반드시 막습니다.

## 완료 기준

1. 부호 있는 타입과 부호 없는 타입을 비교할 때 생길 수 있는 변환을 설명합니다.
2. 배열을 읽기 전에 인덱스 범위를 검사합니다.
3. 반복문 본문에 들어올 때 유지되는 조건과 종료 조건을 설명합니다.
4. 첫 입력으로 최솟값과 최댓값을 초기화합니다.
5. 부호 있는 덧셈의 overflow를 연산 전에 검사합니다.
