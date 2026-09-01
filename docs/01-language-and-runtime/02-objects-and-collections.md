# 객체와 컬렉션

## 학습 목표

이 문서에서는 이름과 객체의 관계, 가변성, 동등성, 주요 컬렉션의 특성을 기준으로 Python의 기본 문법을 설명합니다.

이 문서를 마치면 다음 내용을 구분할 수 있어야 합니다.

- 이름에 객체를 대입하는 것과 객체를 복사하는 것
- 가변 객체와 불변 객체
- 값 동등성(`==`)과 객체 동일성(`is`)
- 조건식의 참·거짓 평가와 `None` 검사
- `list`, `tuple`, `dict`, `set`, `deque`의 용도와 주요 연산 비용
- 해시 가능성(hashability)과 `dict` 키·`set` 원소의 조건
- 불변 데이터 모델을 구성할 때 `dataclass(frozen=True)`가 보장하는 범위

필수 프로젝트에서는 [`data-report`](../../exercises/data-report/README.md)의 `Record`, `CategoryTotal`, `Report`를 생성 후 변경하지 않는 값 객체로 정의할 때 이 내용을 적용합니다.

## 선행 개념

- Python 모듈을 실행하고 함수를 호출할 수 있어야 합니다.
- 이름, 값, 타입의 기본 관계를 이해해야 합니다.
- 함수 인자와 반환값이 객체를 전달한다는 사실을 알고 있으면 이후 예제를 이해하기 쉽습니다.

이 문서의 예제는 `list[str]`, `int | None`, `zip(..., strict=True)`, `dataclass(..., slots=True)` 문법을 사용하므로 Python 3.10 이상을 기준으로 합니다.

## 이름은 객체를 가리킵니다

Python에서 변수처럼 사용하는 이름(name)은 객체 자체를 담는 상자라기보다 객체를 참조하도록 연결된 이름이라고 이해하는 편이 정확합니다.

```python
first = [1, 2, 3]
second = first
second.append(4)

print(first)  # [1, 2, 3, 4]
```

`second = first`는 리스트를 복사하지 않습니다. 대입 후 `first`와 `second`는 같은 리스트 객체를 가리킵니다. `append()`는 그 리스트 객체 자체를 변경하므로 어느 이름으로 확인해도 변경된 내용이 보입니다.

같은 객체인지 직접 확인할 수도 있습니다.

```python
first = [1, 2, 3]
second = first

assert first is second
```

별도의 리스트 객체가 필요하면 명시적으로 복사합니다.

```python
first = [1, 2, 3]
second = first.copy()

assert first == second
assert first is not second
```

`list.copy()`는 **얕은 복사(shallow copy)**입니다. 바깥 리스트 객체만 새로 만들고, 리스트 안에 들어 있는 객체에 대한 참조는 그대로 복사합니다.

```python
left = [[1], [2]]
right = left.copy()

assert left is not right
assert left[0] is right[0]

right[0].append(9)
print(left)  # [[1, 9], [2]]
```

중첩된 객체까지 독립적으로 복사해야 할 때는 `copy.deepcopy()`가 필요할 수 있습니다. 그러나 깊은 복사는 객체 그래프 전체를 복제할 수 있어 비용이 크고, 파일·소켓 같은 외부 자원을 의미 있게 복제하지 못하는 경우도 있습니다. 따라서 무조건 깊은 복사를 적용하기보다 다음 순서로 판단합니다.

1. 두 코드 경로가 같은 객체를 공유해도 되는가?
2. 변경이 필요하다면 어느 코드가 그 변경 권한을 가져야 하는가?
3. 애초에 변경할 필요가 없는 값이라면 불변 구조로 표현할 수 있는가?

함수 호출도 같은 원칙을 따릅니다. 함수에 리스트를 전달한다고 해서 자동으로 복사되지 않습니다.

```python
def add_marker(values: list[str]) -> None:
    values.append("done")


items = ["start"]
add_marker(items)
print(items)  # ['start', 'done']
```

함수 안에서 인자를 다른 객체에 다시 대입하는 것과, 인자가 가리키는 가변 객체를 수정하는 것은 구분해야 합니다.

```python
def replace(values: list[int]) -> None:
    values = [99]  # 지역 이름 values만 다른 리스트를 가리킴


def mutate(values: list[int]) -> None:
    values.append(99)  # 호출자가 전달한 리스트 객체를 변경함
```

## 가변 객체와 불변 객체

**가변(mutable)** 객체는 생성된 뒤 같은 객체의 상태를 바꿀 수 있습니다. **불변(immutable)** 객체는 생성된 뒤 그 객체의 값을 바꿀 수 없습니다.

대표적인 가변 객체는 다음과 같습니다.

- `list`
- `dict`
- `set`
- 대부분의 사용자 정의 인스턴스

대표적인 불변 객체는 다음과 같습니다.

- `int`, `float`, `bool`
- `str`, `bytes`
- `tuple`, `frozenset`

불변 객체에 연산이나 메서드를 적용해 다른 값이 필요하면 기존 객체를 변경하는 대신 결과 객체를 얻습니다.

```python
text = "hello"
upper = text.upper()

print(text)   # hello
print(upper)  # HELLO
```

다만 **불변이라는 말이 항상 새 객체가 만들어진다는 뜻은 아닙니다.** 구현은 안전한 경우 기존 객체를 그대로 반환할 수도 있습니다. 중요한 보장은 객체의 값이 제자리에서 변경되지 않는다는 점입니다. 따라서 불변성을 판단할 때 객체의 `id()`가 달라지는지에 의존하지 않습니다.

### 불변 컨테이너 안의 가변 객체

`tuple` 자체는 불변이지만, 튜플이 가리키는 내부 객체까지 자동으로 불변이 되는 것은 아닙니다.

```python
items = ([1, 2], "fixed")
items[0].append(3)

print(items)  # ([1, 2, 3], 'fixed')
```

튜플의 첫 번째 원소를 다른 객체로 교체할 수는 없지만, 첫 번째 원소인 리스트 자체는 가변이므로 그 내부 상태는 바뀔 수 있습니다. 따라서 "튜플을 사용했다"는 사실만으로 전체 데이터 구조가 깊은 의미에서 불변이라고 볼 수는 없습니다.

설정값이나 이미 검증한 입력처럼 생성 후 바뀌어서는 안 되는 데이터는 가능한 한 불변 값으로 표현하는 편이 안전합니다. 여러 함수나 스레드가 같은 값을 읽더라도 변경 시점을 추적해야 할 일이 줄어듭니다. 다만 불변 객체를 사용한다고 해서 스레드 안전성 문제가 모두 해결되는 것은 아닙니다. 공유하는 다른 가변 상태나 외부 자원에는 여전히 동기화가 필요할 수 있습니다.

## `==`와 `is`

두 연산자는 질문 자체가 다릅니다.

- `==`: 두 객체의 **값이 동등한지** 비교합니다. 실제 비교 방법은 타입의 `__eq__` 구현에 따라 달라질 수 있습니다.
- `is`: 두 표현식이 **정확히 같은 객체**를 가리키는지 비교합니다. 사용자 정의 값 비교 규칙의 영향을 받지 않습니다.

```python
left = [1, 2]
right = [1, 2]

assert left == right
assert left is not right
```

`None`은 값 객체가 하나뿐인 싱글턴이므로 보통 `is` 또는 `is not`으로 검사합니다.

```python
if result is None:
    ...

if result is not None:
    ...
```

문자열이나 정수의 값 비교에는 `is`를 사용하지 않습니다.

```python
name = "admin"

if name == "admin":
    print("관리자")
```

일부 문자열이나 정수 객체는 구현 최적화 때문에 우연히 재사용될 수 있습니다. 그러나 그러한 객체 재사용은 값 비교 규칙이 아니므로 프로그램 논리에 의존해서는 안 됩니다.

## 조건문과 반복문

조건문은 조건에 따라 실행할 블록을 선택합니다.

```python
def classify(value: int) -> str:
    if value < 0:
        return "negative"
    if value == 0:
        return "zero"
    return "positive"
```

`for`는 이터러블(iterable)에서 값을 하나씩 꺼내 반복합니다.

```python
for number in range(5):
    print(number)
```

위 코드는 `0`부터 `4`까지 출력합니다. `range(5)`의 끝값 `5`는 포함되지 않습니다.

`while`은 조건이 참인 동안 반복합니다.

```python
remaining = 3
while remaining > 0:
    remaining -= 1
```

Python은 중괄호 대신 들여쓰기로 블록을 구분합니다. 일반적인 Python 스타일에서는 들여쓰기에 공백 4칸을 사용하고 탭과 공백을 섞지 않습니다.

### 참과 거짓으로 평가되는 값

조건식은 반드시 `bool` 객체만 받을 필요가 없습니다. 객체는 참 또는 거짓으로 평가될 수 있습니다. 대표적으로 다음 값은 거짓(falsy)으로 평가됩니다.

```text
False
None
숫자 0에 해당하는 값: 0, 0.0 등
빈 문자열: ""
빈 컬렉션: [], (), {}, set()
```

그 밖의 대부분의 객체는 참(truthy)으로 평가됩니다. 사용자 정의 타입은 `__bool__()` 또는 `__len__()`을 구현해 이 동작을 정의할 수도 있습니다.

거짓으로 평가된다는 사실과 "값이 없다"는 의미는 같지 않습니다. 예를 들어 `0`, 빈 문자열, 빈 리스트가 정상적인 결과일 수 있다면 단순한 truthiness 검사로 `None`과 합쳐 처리하면 안 됩니다.

```python
result: int | None = 0

if result is None:
    print("결과 없음")
else:
    print(result)  # 0
```

따라서 API에서 `None`을 "결과 없음"의 표지로 사용한다면 `is None`으로 명시적으로 검사하는 것이 의도를 분명하게 만듭니다.

## 주요 컬렉션과 연산 비용

컬렉션은 같은 문제를 서로 다른 방식으로 해결합니다. 자료형을 고를 때는 "어떤 값을 저장하는가"뿐 아니라 "어떤 연산을 자주 하는가"를 먼저 생각합니다.

| 자료형 | 주요 용도 | 비용과 주의점 |
|---|---|---|
| `list` | 순서가 있는 가변 시퀀스 | 끝에 `append()`는 상각 `O(1)`, 끝의 `pop()`은 `O(1)`, 앞이나 중간 삽입·삭제는 보통 `O(n)` |
| `tuple` | 순서가 있는 불변 시퀀스 | 원소 교체 불가, 모든 원소가 해시 가능하면 튜플도 해시 가능 |
| `dict` | 키에서 값으로 매핑 | 평균 조회·삽입·삭제 `O(1)`, 키는 해시 가능해야 함, 삽입 순서를 유지함 |
| `set` | 포함 여부 검사와 중복 제거 | 평균 조회·삽입·삭제 `O(1)`, 원소는 해시 가능해야 함, 의미 있는 순회 순서를 보장하지 않음 |
| `deque` | 양쪽 끝에서 처리하는 큐 | 양끝 `append`, `appendleft`, `pop`, `popleft`가 `O(1)`, 중간 임의 접근에는 `list`보다 적합하지 않음 |

표의 복잡도는 CPython에서 일반적으로 기대하는 평균 또는 상각 기준의 특성을 요약한 것입니다. 최악의 경우와 실제 실행 시간은 객체 크기, 해시 충돌, 입력 분포, 메모리 배치, Python 구현에 따라 달라질 수 있습니다.

### 해시 가능성이란 무엇인가

`dict`의 키와 `set`의 원소는 **해시 가능(hashable)**해야 합니다. 해시 가능한 객체는 사용하는 동안 해시 값이 변하지 않고, 동등한 두 객체라면 같은 해시 값을 제공해야 합니다.

일반적으로 다음과 같이 구분할 수 있습니다.

- `str`, `int`, `bytes`, `frozenset`: 보통 해시 가능
- 모든 원소가 해시 가능한 `tuple`: 해시 가능
- `list`, `dict`, `set`: 가변이므로 해시 불가능

```python
locations: dict[tuple[int, int], str] = {}
locations[(10, 20)] = "origin-nearby"
```

반면 리스트는 키로 사용할 수 없습니다.

```python
# TypeError: unhashable type: 'list'
# mapping = {[10, 20]: "value"}
```

`tuple`이라는 이유만으로 항상 해시 가능한 것은 아닙니다.

```python
key = ([1, 2], "x")

# 내부 list가 해시 불가능하므로 key 역시 dict 키로 사용할 수 없습니다.
# mapping = {key: "value"}
```

### 리스트

```python
values = [3, 1, 4]
values.append(2)
ordered = sorted(values)
```

`sorted(values)`는 입력을 바꾸지 않고 정렬 결과를 담은 새 `list`를 반환합니다.

```python
values = [3, 1, 4]
ordered = sorted(values)

print(values)   # [3, 1, 4]
print(ordered)  # [1, 3, 4]
```

반면 `list.sort()`는 기존 리스트를 직접 정렬하고 반환값은 `None`입니다.

```python
values = [3, 1, 4]
result = values.sort()

print(values)  # [1, 3, 4]
print(result)  # None
```

따라서 다음과 같이 작성하지 않습니다.

```python
# ordered에는 정렬된 리스트가 아니라 None이 들어갑니다.
# ordered = values.sort()
```

리스트 슬라이스도 일반적으로 새 리스트를 만들며, 원소 참조를 얕게 복사합니다.

```python
values = [1, 2, 3, 4]
first_two = values[:2]
```

큰 리스트를 반복해서 슬라이스하면 복사 시간과 메모리 사용량이 누적될 수 있습니다.

큐의 앞쪽에서 값을 반복해서 제거해야 한다면 `list.pop(0)`은 나머지 원소를 이동해야 하므로 `O(n)`입니다. 이런 작업에는 `collections.deque`의 `popleft()`가 더 적합합니다.

```python
from collections import deque

queue = deque(["a", "b", "c"])
first = queue.popleft()
```

### 딕셔너리

딕셔너리는 키와 값을 연결하는 매핑(mapping)입니다.

```python
counts: dict[str, int] = {}
for word in ["a", "b", "a"]:
    counts[word] = counts.get(word, 0) + 1

print(counts)  # {'a': 2, 'b': 1}
```

`counts.get(word, 0)`은 키가 있으면 해당 값을 반환하고, 없으면 기본값 `0`을 반환합니다. 반면 `counts[word]`는 키가 없으면 `KeyError`를 발생시킵니다.

둘 중 무엇을 사용할지는 데이터 규칙에 따라 결정합니다.

```python
config = {"host": "localhost"}

# host가 반드시 존재해야 하는 필수 키라면 누락을 오류로 드러내는 편이 낫습니다.
host = config["host"]

# timeout이 선택 항목이고 기본값이 정의되어 있다면 get()이 자연스럽습니다.
timeout = config.get("timeout", 30)
```

외부 입력에서 읽은 키가 항상 존재한다고 가정하지 않습니다. 키 누락을 오류로 처리할지 기본값으로 처리할지는 입력 형식의 계약에 따라 정해야 합니다.

Python 3.7 이상에서는 `dict`의 삽입 순서 유지가 언어 차원에서 보장됩니다. 그러나 삽입 순서와 "정렬된 순서"는 다릅니다. 키를 사전식 등 특정 기준으로 출력해야 한다면 명시적으로 정렬합니다.

```python
for key in sorted(counts):
    print(key, counts[key])
```

### 집합

집합은 중복 없는 원소 모음이며, 특정 값의 포함 여부를 빠르게 검사하는 데 적합합니다.

```python
seen: set[str] = set()
for name in names:
    if name in seen:
        raise ValueError(f"중복 이름: {name}")
    seen.add(name)
```

같은 값을 여러 번 추가해도 집합에는 하나만 남습니다.

```python
values = {"a", "a", "b"}
print(len(values))  # 2
```

집합의 순회 순서를 파일 형식이나 테스트의 기대 출력처럼 안정적인 출력 계약에 사용하지 않습니다. 같은 실행에서 특정 순서로 보일 수 있어도 그 순서를 프로그램의 의미로 간주하면 안 됩니다. 항상 같은 출력 순서가 필요하면 원래 입력 순서를 별도로 보존하거나 출력 전에 정렬합니다.

```python
for name in sorted(seen):
    print(name)
```

### 튜플과 구조 분해

튜플은 순서가 있고 원소 위치가 고정된 불변 시퀀스입니다.

```python
point = (10, 20)
x, y = point
```

`x, y = point`처럼 여러 이름에 원소를 나누어 대입하는 것을 언패킹(unpacking)이라고 합니다. 왼쪽 변수 개수와 오른쪽 원소 개수가 맞지 않으면 `ValueError`가 발생합니다.

```python
point = (10, 20)

# ValueError: not enough values to unpack
# x, y, z = point
```

변하지 않는 작은 값 묶음에는 `tuple`이 적합할 수 있습니다. 그러나 `point[0]`, `point[1]`처럼 각 위치의 의미를 기억해야 한다면 필드 이름이 있는 `dataclass`가 더 명확할 수 있습니다.

## 반복에 유용한 도구

### `enumerate()`

인덱스와 값을 함께 사용할 때 직접 카운터를 관리하기보다 `enumerate()`를 사용합니다.

```python
for index, name in enumerate(names):
    print(index, name)
```

기본 시작 인덱스는 `0`입니다. 필요하면 시작값을 지정할 수 있습니다.

```python
for line_number, line in enumerate(lines, start=1):
    print(line_number, line)
```

### `zip()`

여러 이터러블을 같은 위치끼리 묶어 반복할 때 `zip()`을 사용합니다.

```python
for name, score in zip(names, scores, strict=True):
    print(name, score)
```

기본 `zip(names, scores)`는 입력 길이가 다르면 가장 짧은 입력이 끝나는 순간 반복을 종료합니다. 데이터 개수가 반드시 같아야 하는 상황에서는 이 동작이 오류를 숨길 수 있습니다.

`zip(..., strict=True)`는 모든 입력의 길이가 같아야 한다는 조건을 검사합니다. 길이가 다르면 `ValueError`를 발생시킵니다.

```python
names = ["alice", "bob"]
scores = [90]

# list(zip(names, scores, strict=True))  # ValueError
```

### 내포 표현식

내포 표현식(comprehension)은 간단한 변환과 필터링을 짧게 표현합니다.

```python
normalized = [item.strip().lower() for item in raw_items if item.strip()]
```

위 코드는 각 문자열이 공백 제거 후 비어 있지 않은 경우에만 소문자로 정규화한 새 리스트를 만듭니다.

다만 같은 표현식 안에 여러 단계의 분기, 예외 처리, 상태 변경, 로깅 같은 부작용을 넣으면 실행 순서를 파악하기 어려워집니다. 이런 경우에는 일반 반복문으로 풀어 쓰는 편이 읽기 쉽습니다.

```python
normalized: list[str] = []

for item in raw_items:
    stripped = item.strip()
    if not stripped:
        continue
    normalized.append(stripped.lower())
```

## 불변 데이터 모델

검증이 끝난 입력은 이후 코드에서 함부로 바뀌지 않도록 만드는 편이 좋습니다. 값의 의미가 필드 이름으로 드러나야 한다면 `dataclass`를 사용할 수 있습니다.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Record:
    category: str
    amount: Decimal
```

### `frozen=True`가 보장하는 것

`frozen=True`는 정상적인 속성 대입과 삭제를 막습니다.

```python
record = Record(category="food", amount=Decimal("12.50"))

# dataclasses.FrozenInstanceError
# record.category = "travel"
```

하지만 `frozen=True`는 **필드가 가리키는 객체까지 재귀적으로 불변으로 만들지 않습니다.**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    values: list[int]


example = Example(values=[1, 2])
example.values.append(3)  # 내부 list는 여전히 변경 가능
```

따라서 전체 값이 논리적으로 불변이어야 한다면 필드도 가능한 한 불변 타입으로 구성합니다.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    values: tuple[int, ...]
```

`frozen=True`는 실수를 방지하는 강한 인터페이스 제약이지만, Python 객체를 절대적으로 수정 불가능한 메모리로 바꾸는 보안 기능은 아닙니다. 애플리케이션 코드에서는 필드 재대입을 금지하는 값 객체 설계 수단으로 이해하면 충분합니다.

### `slots=True`가 보장하는 것

`slots=True`는 데이터 클래스에 슬롯을 생성해 선언되지 않은 인스턴스 속성을 임의로 추가하지 못하게 하고, 일반적인 경우 인스턴스별 `__dict__`가 필요하지 않게 합니다.

```python
record = Record(category="food", amount=Decimal("12.50"))

# AttributeError
# record.note = "temporary"
```

이 옵션은 고정된 필드 집합을 가진 값 객체에서 구조를 명확하게 하고 인스턴스당 메모리 사용을 줄일 수 있습니다. 다만 상속, 약한 참조, 동적 속성 추가가 필요한 설계에는 제약이 생길 수 있으므로 모든 클래스에 기계적으로 붙일 필요는 없습니다.

### 동등성과 해시

기본 `dataclass`는 같은 타입의 인스턴스끼리 필드 값을 기준으로 `==`를 비교하도록 메서드를 생성합니다.

```python
first = Record("food", Decimal("12.50"))
second = Record("food", Decimal("12.50"))

assert first == second
assert first is not second
```

`eq=True`와 `frozen=True`를 기본 설정대로 함께 사용하면 데이터 클래스는 일반적으로 필드 값을 기반으로 한 `__hash__`도 생성합니다. 그러나 실제로 인스턴스를 해시하려면 각 필드 값 역시 해시 가능해야 합니다. 따라서 `list` 같은 가변·비해시 가능 필드를 넣으면 `hash(instance)`가 실패할 수 있습니다.

값 객체를 `dict` 키나 `set` 원소로 사용할 계획이라면 필드까지 해시 가능한 값으로 구성하는 것이 중요합니다.

## 프로젝트에 적용하기

### 필수: `data-report`

- CSV와 JSON의 외부 입력을 읽고 검증한 뒤 내부 표현인 `Record`로 변환합니다.
- `Record`는 생성 이후 `category`나 `amount`가 바뀌지 않는 값으로 취급합니다.
- `category`별 집계 결과는 `CategoryTotal`처럼 필드 이름이 있는 불변 값 객체로 저장합니다.
- 전체 결과는 `Report` 하나로 묶어 텍스트 출력과 JSON 출력이 같은 계산 결과를 공유하게 합니다.
- 여러 레코드를 불변 구조에 넣어야 한다면 `list` 대신 `tuple[Record, ...]` 같은 형태를 고려합니다.
- 출력 순서가 입력 파일의 우연한 순서에 좌우되지 않아야 한다면 `category`를 명시적으로 정렬합니다. `dict`가 삽입 순서를 유지한다는 사실과 정렬은 별개의 개념입니다.

예를 들어 다음과 같이 값 객체를 구성할 수 있습니다.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CategoryTotal:
    category: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class Report:
    totals: tuple[CategoryTotal, ...]
```

이 구조에서는 `Report`가 가리키는 컬렉션도 `tuple`이므로, 정상적인 애플리케이션 코드에서 집계 결과가 나중에 우연히 추가·삭제되는 일을 막기 쉽습니다.

### 선택: `command-checker`

- 여러 작업자가 공유하는 `Case`와 `Result`를 불변 `dataclass`로 정의합니다.
- 환경 변수는 가변 `dict`를 장기간 공유하는 대신 정렬된 `tuple[tuple[str, str], ...]` 같은 불변 표현으로 저장할 수 있습니다.
- 실제 프로세스를 시작할 때만 새 `dict`로 변환하면, 작업 정의 자체와 실행 시 필요한 가변 입력을 분리할 수 있습니다.

```python
environment_items = (("LANG", "C"), ("MODE", "test"))
environment = dict(environment_items)
```

## 완료 기준

- `second = first`가 객체 복사가 아니라 같은 객체에 대한 또 하나의 참조를 만든다는 점을 설명할 수 있습니다.
- 얕은 복사에서 중첩된 가변 객체가 계속 공유될 수 있음을 설명할 수 있습니다.
- 가변 객체와 불변 객체의 차이를 설명하고, `tuple` 안에도 가변 객체가 들어갈 수 있음을 이해합니다.
- `==`와 `is`를 올바르게 구분하고 `None`을 `is None`으로 검사합니다.
- `None`과 `0`, 빈 문자열, 빈 컬렉션처럼 거짓으로 평가되는 정상값을 구분합니다.
- `dict` 키와 `set` 원소가 해시 가능해야 하는 이유를 설명할 수 있습니다.
- 사용하는 컬렉션의 주요 조회·삽입·삭제 비용을 대략 설명할 수 있습니다.
- 출력 순서가 필요한 코드에서 `set`의 순회 순서에 의존하지 않고 필요하면 명시적으로 정렬합니다.
- `frozen=True`가 필드 재대입을 막지만 내부 가변 객체까지 불변으로 만들지는 않는다는 점을 설명할 수 있습니다.
- 생성 후 바뀌면 안 되는 프로젝트 값을 불변 `dataclass`와 불변 필드 타입으로 표현할 수 있습니다.

다음은 [함수, 예외 처리와 타입 검증](03-functions-errors-and-types.md)입니다.
