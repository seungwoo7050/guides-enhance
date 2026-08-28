# 객체와 컬렉션

## 학습 목표

이 문서에서는 이름과 객체의 관계, 가변성, 동등성, 주요 컬렉션의 특성을 기준으로 Python의 기본 문법을 설명합니다.

필수 프로젝트에서는 [`data-report`](../../exercises/data-report/README.md)의 `Record`, `CategoryTotal`, `Report`를 불변 값으로 정의할 때 이 내용을 적용합니다.

## 선행 개념

- Python 모듈을 실행하고 함수를 호출할 수 있어야 합니다.
- 이름, 값, 타입의 기본 관계를 이해해야 합니다.

## 이름은 객체를 가리킵니다

```python
first = [1, 2, 3]
second = first
second.append(4)

print(first)  # [1, 2, 3, 4]
```

대입은 리스트를 복사하지 않습니다. `first`와 `second`가 같은 리스트 객체를 가리키므로 한쪽에서 바꾼 내용이 다른 쪽에서도 보입니다.

별도 리스트가 필요하면 명시적으로 복사합니다.

```python
second = first.copy()
```

`list.copy()`는 얕은 복사입니다. 바깥 리스트만 새로 만들며 내부 객체는 계속 공유할 수 있습니다.

```python
left = [[1], [2]]
right = left.copy()
right[0].append(9)

print(left)  # [[1, 9], [2]]
```

무조건 깊은 복사를 적용하기보다 실제로 객체를 공유해야 하는지, 처음부터 불변 값으로 표현할 수 있는지 먼저 검토합니다.

## 가변 객체와 불변 객체

대표적인 가변 객체는 다음과 같습니다.

- `list`
- `dict`
- `set`
- 대부분의 사용자 정의 인스턴스

대표적인 불변 객체는 다음과 같습니다.

- `int`, `float`, `bool`
- `str`, `bytes`
- `tuple`, `frozenset`

불변 객체에 연산이나 메서드를 적용하면 일반적으로 새 객체가 만들어집니다.

```python
text = "hello"
upper = text.upper()
```

설정값이나 이미 검증한 입력처럼 생성 후 바뀌어서는 안 되는 데이터는 불변 값으로 표현하는 편이 안전합니다. 여러 함수나 스레드에서 같은 값을 사용하더라도 변경 시점을 추적할 필요가 줄어듭니다.

## `==`와 `is`

- `==`: 두 객체의 값이 같은지 비교합니다.
- `is`: 두 이름이 정확히 같은 객체를 가리키는지 비교합니다.

```python
left = [1, 2]
right = [1, 2]

assert left == right
assert left is not right
```

`None`은 `is`로 비교합니다.

```python
if result is None:
    ...
```

문자열이나 정수의 값 비교에 `is`를 사용해서는 안 됩니다. 일부 값이 우연히 같은 객체로 재사용될 수 있지만, 프로그램이 의존할 수 있는 값 비교 규칙은 아닙니다.

## 조건문과 반복문

```python
def classify(value: int) -> str:
    if value < 0:
        return "negative"
    if value == 0:
        return "zero"
    return "positive"
```

```python
for number in range(5):
    print(number)
```

```python
remaining = 3
while remaining > 0:
    remaining -= 1
```

Python은 들여쓰기로 블록을 구분합니다. 탭과 공백을 섞지 않고 공백 4칸을 기본으로 사용합니다.

다음 값은 조건식에서 거짓으로 평가됩니다.

```text
False, None, 0, 0.0, "", 빈 list·tuple·dict·set
```

그러나 `0`과 값이 없음을 구분해야 하는 경우에는 명시적으로 비교합니다.

```python
result: int | None = 0
if result is None:
    print("결과 없음")
else:
    print(result)
```

## 주요 컬렉션과 연산 비용

| 자료형 | 주요 용도 | 비용과 주의점 |
|---|---|---|
| `list` | 순서가 있는 가변 배열 | 끝에 추가·삭제하는 연산은 상각 `O(1)`, 중간 삽입·삭제는 `O(n)` |
| `tuple` | 순서가 있는 불변 묶음 | 모든 원소가 해시 가능하면 `dict`·`set`의 키로 사용할 수 있음 |
| `dict` | 키로 값 조회 | 평균 조회·삽입·삭제 `O(1)`, 삽입 순서를 유지함 |
| `set` | 포함 여부 검사와 중복 제거 | 평균 조회·삽입·삭제 `O(1)`, 순회 순서를 보장하지 않음 |
| `deque` | 양쪽 끝에서 처리하는 큐 | `append`, `appendleft`, `pop`, `popleft`가 `O(1)` |

표의 복잡도는 평균 또는 상각 기준입니다. 실제 성능은 객체 크기, 해시 충돌, 입력 분포, 메모리 배치에 따라 달라질 수 있습니다.

### 리스트

```python
values = [3, 1, 4]
values.append(2)
ordered = sorted(values)
```

`sorted()`는 새 리스트를 반환하고 `list.sort()`는 기존 리스트를 직접 바꿉니다. 슬라이스도 일반적으로 새 리스트를 만들므로 큰 리스트에서 반복해서 사용하면 복사 비용이 생깁니다.

### 딕셔너리

```python
counts: dict[str, int] = {}
for word in ["a", "b", "a"]:
    counts[word] = counts.get(word, 0) + 1
```

외부 입력에서 읽은 키가 항상 존재한다고 가정하지 않습니다. 키 누락을 오류로 처리할지 기본값으로 처리할지는 입력 형식의 규칙에 따라 정합니다.

### 집합

```python
seen: set[str] = set()
for name in names:
    if name in seen:
        raise ValueError(f"중복 이름: {name}")
    seen.add(name)
```

집합의 순회 순서를 출력 형식에 사용하지 않습니다. 항상 같은 출력 순서가 필요하면 원래 입력 순서를 따로 보존하거나 출력 전에 정렬합니다.

### 튜플과 구조 분해

```python
point = (10, 20)
x, y = point
```

변하지 않는 작은 값 묶음에는 `tuple`이 적합할 수 있습니다. 각 위치의 의미가 중요하다면 `dataclass`처럼 필드 이름이 있는 타입이 더 명확합니다.

## 반복에 유용한 도구

```python
for index, name in enumerate(names):
    print(index, name)
```

```python
for name, score in zip(names, scores, strict=True):
    print(name, score)
```

`zip(..., strict=True)`는 두 입력의 길이가 같아야 한다는 조건을 검사합니다. 길이가 다르면 짧은 쪽에 맞춰 조용히 끝내지 않고 `ValueError`를 발생시킵니다.

내포 표현식은 한눈에 동작을 파악할 수 있을 때만 사용합니다.

```python
normalized = [item.strip().lower() for item in raw_items if item.strip()]
```

여러 단계의 분기나 부작용이 필요하다면 일반 반복문으로 풀어 쓰는 편이 읽기 쉽습니다.

## 불변 데이터 모델

검증이 끝난 입력은 이후 코드에서 함부로 바뀌지 않도록 만드는 편이 좋습니다.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Record:
    category: str
    amount: Decimal
```

`frozen=True`는 필드에 다른 값을 다시 대입하는 일을 막습니다. 다만 필드 안에 가변 `dict`나 `list`를 넣으면 내부 값은 여전히 바뀔 수 있습니다. 불변 값이 필요하다면 필드도 가능한 한 `tuple`이나 다른 불변 타입으로 구성합니다.

`slots=True`는 인스턴스가 임의의 새 속성을 갖지 못하게 하고 인스턴스별 `__dict__`를 만들지 않습니다. 모든 클래스에 기계적으로 붙이기보다 고정된 값 객체에 사용합니다.

## 프로젝트에 적용하기

### 필수: `data-report`

- CSV와 JSON을 읽은 뒤 `Record`로 변환합니다.
- `category`별 결과는 `CategoryTotal`로 저장합니다.
- 전체 결과는 `Report` 하나로 묶어 텍스트와 JSON 출력에 함께 사용합니다.
- `category`는 정렬해서 입력 파일의 순서에 따라 출력이 바뀌지 않게 합니다.

### 선택: `command-checker`

- 여러 작업자가 공유하는 `Case`와 `Result`를 불변 `dataclass`로 정의합니다.
- 환경 변수는 가변 `dict` 대신 정렬된 `tuple` 쌍으로 저장하고, 프로세스를 시작할 때만 새 `dict`로 바꿉니다.

## 완료 기준

- 대입과 복사의 차이를 설명할 수 있습니다.
- `==`와 `is`를 올바르게 구분합니다.
- `None`과 거짓으로 평가되는 정상값을 구분합니다.
- 출력 순서가 필요한 코드에서 `set`의 순회 순서에 의존하지 않습니다.
- 생성 후 바뀌면 안 되는 값을 불변 `dataclass`로 표현합니다.
- 사용하는 컬렉션의 조회·삽입 비용을 대략 설명할 수 있습니다.

다음은 [함수, 예외 처리와 타입 검증](03-functions-errors-and-types.md)입니다.
