# 반복자, 생성기와 컨텍스트 관리자

## 학습 목표

파일과 데이터를 처리하는 프로그램은 값을 한 항목씩 읽고, 파일이나 프로세스 같은 자원을 필요한 동안만 유지해야 합니다. Python은 반복자 프로토콜과 컨텍스트 관리자 프로토콜을 통해 이 두 문제를 일관된 방식으로 다룹니다.

이 문서를 마치면 다음 내용을 설명할 수 있어야 합니다.

- `iterable`과 `iterator`의 차이
- `for`문이 반복자를 사용하는 방식
- 생성기를 사용한 지연 처리
- 한 번만 소비되는 데이터의 사용 규칙
- 생성기가 보유한 파일 같은 자원의 수명
- `with`를 사용한 자원 획득과 정리
- 여러 자원을 얻는 도중 실패했을 때의 정리 방법
- 입력 크기와 재사용 방식에 따라 컬렉션과 생성기를 선택하는 기준

필수 프로젝트에서는 [`data-report`](../../exercises/data-report/README.md)가 CSV 파일을 여닫고 `Record`를 순회할 때 이 원칙을 적용합니다.

## 선행 개념

- 함수와 예외의 기본 동작을 이해해야 합니다.
- `for`로 값을 순회할 수 있어야 합니다.
- 파일처럼 사용 후 닫아야 하는 자원이 있음을 알고 있어야 합니다.

## `iterable`과 `iterator`

Python의 `for`문은 인덱스를 직접 증가시키는 문법이 아니라 **반복자 프로토콜(iterator protocol)**을 사용합니다.

```python
values = [10, 20, 30]
iterator = iter(values)

print(next(iterator))  # 10
print(next(iterator))  # 20
```

두 용어를 구분해야 합니다.

- `iterable`: `iter(value)`를 호출해 `iterator`를 얻을 수 있는 객체입니다.
- `iterator`: `next(value)`를 호출해 다음 항목을 하나씩 얻을 수 있는 객체입니다.

리스트, 튜플, 문자열, 딕셔너리, 파일 객체 등은 모두 순회할 수 있으므로 `iterable`입니다.

```python
for value in [10, 20, 30]:
    print(value)
```

개념적으로 `for`문은 다음과 비슷하게 동작합니다.

```python
iterator = iter(values)

while True:
    try:
        value = next(iterator)
    except StopIteration:
        break

    print(value)
```

실제 코드에서 일반적인 순회를 직접 `next()`와 `StopIteration`으로 작성할 필요는 거의 없습니다. 중요한 점은 **반복자가 더 이상 값을 만들 수 없을 때 `StopIteration`으로 종료를 알린다**는 것입니다.

## `iterable`은 여러 번 순회할 수 있지만 `iterator`는 보통 한 번 소비됩니다

리스트 같은 컬렉션은 `iter()`를 호출할 때마다 새 반복자를 만들 수 있습니다.

```python
values = [1, 2, 3]

print(list(values))  # [1, 2, 3]
print(list(values))  # [1, 2, 3]
```

반면 하나의 반복자 객체는 순회 위치를 내부에 유지합니다.

```python
iterator = iter([1, 2, 3])

print(list(iterator))  # [1, 2, 3]
print(list(iterator))  # []
```

첫 번째 `list(iterator)`가 반복자를 끝까지 소비했기 때문에 두 번째 호출에는 남은 항목이 없습니다.

대부분의 반복자는 자기 자신을 다시 `iter()`해도 새 반복자를 만들지 않습니다.

```python
iterator = iter([1, 2, 3])

assert iter(iterator) is iterator
```

따라서 함수가 `Iterator[T]`를 받는다면 호출자는 그 값이 소비될 수 있음을 알아야 합니다.

반대로 함수가 단순히 순회만 필요하고 리스트, 튜플, 생성기 등 여러 입력을 허용하고 싶다면 `Iterable[T]`가 더 일반적인 타입입니다.

```python
from collections.abc import Iterable


def total(values: Iterable[int]) -> int:
    result = 0
    for value in values:
        result += value
    return result
```

다만 `Iterable`이라고 해서 여러 번 순회할 수 있다는 뜻은 아닙니다. 생성기 역시 `Iterable`이면서 동시에 한 번만 소비되는 `Iterator`입니다. 함수 내부에서 입력을 두 번 순회해야 한다면 이를 문서화하거나 필요한 경우 한 번 컬렉션으로 저장해야 합니다.

```python
def summarize(values: Iterable[int]) -> tuple[int, int]:
    cached = tuple(values)
    return len(cached), sum(cached)
```

이렇게 저장하면 여러 번 사용할 수 있지만 그만큼 메모리를 사용합니다.

## 생성기는 값을 지연해서 만듭니다

`yield`를 포함하는 함수는 일반 함수와 다르게 동작합니다.

```python
from collections.abc import Iterator
from pathlib import Path


def nonempty_lines(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            cleaned = line.rstrip("\n")
            if cleaned:
                yield cleaned
```

이 함수를 호출하는 순간 파일을 바로 여는 것이 아닙니다.

```python
lines = nonempty_lines(path)
```

위 호출은 **생성기 객체(generator object)**를 만들 뿐입니다. 함수 본문은 아직 실행되지 않습니다.

첫 번째 항목이 필요해질 때 실행이 시작됩니다.

```python
first = next(lines)
```

실행 흐름은 다음과 같습니다.

```text
nonempty_lines(path) 호출
→ 생성기 객체 생성
→ 본문은 아직 실행되지 않음

next() 또는 for로 첫 값 요청
→ 함수 본문 실행 시작
→ 파일 열기
→ 첫 번째 yield까지 실행
→ 값 반환 후 실행 상태를 보존한 채 일시 정지

다음 값 요청
→ 직전 yield 다음 줄부터 다시 실행
→ 다음 yield에서 다시 일시 정지
```

생성기 함수가 `return`하거나 함수 끝에 도달하면 반복이 끝나고 호출자에게는 `StopIteration`으로 표현됩니다.

## 생성기의 장점과 비용

생성기를 사용하면 다음과 같은 장점이 있습니다.

- 큰 파일 전체를 메모리에 올리지 않고 한 항목씩 처리할 수 있습니다.
- 필요한 값만 만들기 때문에 불필요한 중간 컬렉션을 줄일 수 있습니다.
- 데이터 생산 속도와 소비 속도를 자연스럽게 연결할 수 있습니다.
- 파일이나 네트워크 스트림처럼 원래 순차적으로 도착하는 데이터를 표현하기 쉽습니다.

예를 들어 다음 코드는 모든 줄을 리스트로 저장하지 않습니다.

```python
for line in nonempty_lines(path):
    process(line)
```

하지만 지연 실행에는 다음과 같은 특성도 있습니다.

- 오류가 함수 호출 시점이 아니라 실제 순회 중에 발생할 수 있습니다.
- 한 번 소비한 생성기는 처음부터 다시 사용할 수 없습니다.
- 길이를 바로 알 수 없습니다.
- 임의 인덱스로 접근할 수 없습니다.
- 생성기가 외부 자원을 보유한다면 생성기의 수명과 자원 수명이 연결됩니다.

따라서 "생성기가 항상 리스트보다 효율적이다"라고 볼 수는 없습니다. 데이터가 작고 여러 번 사용해야 한다면 리스트나 튜플이 더 단순할 수 있습니다.

## 지연 실행 때문에 오류 시점이 달라질 수 있습니다

다음 호출 자체는 파일 존재 여부를 확인하지 않습니다.

```python
lines = nonempty_lines(Path("missing.txt"))
```

파일을 실제로 여는 코드는 첫 순회가 시작될 때 실행됩니다.

```python
next(lines)  # 이 시점에 FileNotFoundError가 발생할 수 있음
```

따라서 생성기 함수의 오류를 처리할 때는 생성기 객체를 만드는 부분만 `try`로 감싸서는 충분하지 않을 수 있습니다.

```python
try:
    lines = nonempty_lines(path)
except OSError:
    ...
```

위 코드는 파일을 아직 열지 않았다면 오류를 잡지 못합니다.

실제 소비까지 오류 처리 범위에 포함해야 합니다.

```python
try:
    for line in nonempty_lines(path):
        process(line)
except OSError as error:
    ...
```

## 생성기가 파일을 보유할 때 자원 수명 확인하기

다음 생성기는 순회하는 동안 파일을 열어 둡니다.

```python
def nonempty_lines(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            cleaned = line.rstrip("\n")
            if cleaned:
                yield cleaned
```

파일은 다음 경우에 `with` 블록을 빠져나가면서 닫힙니다.

- 생성기가 끝까지 소비되어 함수가 종료됨
- 생성기가 명시적으로 `close()`됨
- 생성기 내부에서 예외가 발생해 블록을 벗어남

예를 들어 다음 코드는 생성기를 끝까지 소비합니다.

```python
for line in nonempty_lines(path):
    print(line)
```

반면 일부만 읽고 생성기 참조를 계속 보관하면 파일도 계속 열려 있을 수 있습니다.

```python
lines = nonempty_lines(path)

print(next(lines))
# lines가 아직 살아 있고 생성기가 끝나지 않았으므로
# 내부 파일도 아직 열려 있을 수 있습니다.
```

필요한 만큼만 읽고 즉시 자원을 해제해야 한다면 생성기를 명시적으로 닫을 수 있습니다.

```python
lines = nonempty_lines(path)

try:
    print(next(lines))
finally:
    lines.close()
```

단순한 순회에서는 보통 끝까지 소비하도록 구조를 잡는 편이 더 명확합니다. 중간 종료가 빈번하고 자원 해제 시점이 중요하다면 **파일 수명을 생성기 내부에 숨길지, 호출자가 파일을 열어 전달할지**도 함께 설계해야 합니다.

## 생성기 표현식

생성기 표현식은 리스트 내포와 비슷하지만 값을 즉시 모두 만들지 않습니다.

```python
squares = (number * number for number in range(1_000_000))
```

`squares`는 리스트가 아니라 생성기입니다.

```python
print(next(squares))  # 0
print(next(squares))  # 1
```

모든 값을 저장할 필요가 없다면 함수 인자로 바로 전달할 수 있습니다.

```python
total = sum(number * number for number in range(1_000_000))
```

반면 다음과 같은 요구가 있다면 리스트가 더 적합할 수 있습니다.

- 결과를 여러 번 순회해야 함
- 길이를 자주 확인해야 함
- 인덱스로 접근해야 함
- 데이터가 충분히 작음

```python
squares = [number * number for number in range(100)]

print(squares[20])
print(len(squares))
```

## `yield from`

다른 `iterable`의 항목을 그대로 이어서 내보내려면 `yield from`을 사용할 수 있습니다.

```python
from collections.abc import Iterable, Iterator
from pathlib import Path


def all_lines(paths: Iterable[Path]) -> Iterator[str]:
    for path in paths:
        yield from nonempty_lines(path)
```

다음 코드와 기본적인 의미는 같습니다.

```python
def all_lines(paths: Iterable[Path]) -> Iterator[str]:
    for path in paths:
        for line in nonempty_lines(path):
            yield line
```

이 예제에서 한 파일을 읽는 도중 오류가 발생하면 예외는 바깥 호출자에게 전파되고 기본적으로 전체 순회가 중단됩니다.

```text
file-a 읽기 성공
→ file-b 읽기 중 OSError
→ all_lines()도 실패
→ file-c는 처리하지 않음
```

파일 하나를 읽지 못해도 다음 파일을 계속 처리해야 한다면 `yield from` 자체가 해결해 주는 것이 아니라 별도의 오류 처리 규칙을 작성해야 합니다.

```python
def all_lines(paths: Iterable[Path]) -> Iterator[str]:
    for path in paths:
        try:
            yield from nonempty_lines(path)
        except OSError as error:
            report_error(path, error)
```

계속 처리하는 것이 올바른지는 프로그램의 요구사항에 따라 결정합니다. 오류를 무조건 무시해서는 안 됩니다.

## 컨텍스트 관리자는 자원의 수명을 코드 블록에 묶습니다

파일처럼 사용 후 정리가 필요한 객체는 `with`와 함께 사용할 수 있습니다.

```python
with path.open("r", encoding="utf-8") as stream:
    content = stream.read()
```

흐름은 다음과 같습니다.

```text
컨텍스트 진입
→ 자원 획득
→ with 블록 실행
→ 정상 종료 또는 예외 발생
→ 컨텍스트 종료 처리
→ 자원 정리
```

파일 객체는 컨텍스트를 종료할 때 `close()`됩니다.

따라서 다음 두 경우 모두 파일이 닫힙니다.

```python
with path.open("r", encoding="utf-8") as stream:
    content = stream.read()
```

```python
with path.open("r", encoding="utf-8") as stream:
    raise RuntimeError("실패")
```

`with`는 단순한 축약 문법이 아니라 **자원을 얻는 시점과 정리하는 시점을 같은 구조 안에 묶는 방법**입니다.

## 컨텍스트 관리자 프로토콜

컨텍스트 관리자는 개념적으로 두 동작을 제공합니다.

- 블록에 들어갈 때 실행되는 진입 동작
- 블록을 나갈 때 실행되는 종료 동작

클래스로 직접 구현하면 `__enter__()`와 `__exit__()` 메서드를 사용합니다.

```python
class ManagedResource:
    def __enter__(self):
        print("acquire")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("release")
        return False
```

```python
with ManagedResource() as resource:
    print("use")
```

`__enter__()`가 반환한 값이 `as resource`에 들어갑니다.

`__exit__()`는 정상 종료뿐 아니라 블록 안에서 예외가 발생한 경우에도 호출됩니다. `False`를 반환하면 발생한 예외를 숨기지 않고 그대로 전파합니다.

대부분의 코드에서는 직접 클래스를 작성하기보다 이미 제공되는 컨텍스트 관리자를 사용하거나 `contextlib.contextmanager`를 이용하는 편이 간단합니다.

## `try/finally`와의 관계

파일 정리는 `try/finally`로 직접 작성할 수도 있습니다.

```python
stream = path.open("r", encoding="utf-8")

try:
    content = stream.read()
finally:
    stream.close()
```

`finally` 블록은 정상 실행이든 예외 발생이든 관계없이 실행됩니다.

`with`를 쓰면 같은 수명 규칙을 더 명확하게 표현할 수 있습니다.

```python
with path.open("r", encoding="utf-8") as stream:
    content = stream.read()
```

자원을 정리하는 방법을 객체 자체가 알고 있다면 `with`가 적합합니다. 여러 종류의 정리 동작을 직접 조합해야 한다면 `try/finally` 또는 `ExitStack`이 필요할 수 있습니다.

## 사용자 정의 컨텍스트 관리자

`contextlib.contextmanager`를 사용하면 생성기 형태로 컨텍스트 관리자를 작성할 수 있습니다.

```python
import os
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def temporary_environment(name: str, value: str) -> Iterator[None]:
    previous = os.environ.get(name)
    os.environ[name] = value

    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous
```

사용법은 일반 컨텍스트 관리자와 같습니다.

```python
with temporary_environment("MODE", "test"):
    run_test()
```

구조는 다음과 같습니다.

```text
yield 이전
→ 컨텍스트에 들어갈 때 실행

yield
→ with 블록 실행 위치

yield 이후의 finally
→ with 블록을 나갈 때 실행
```

`with` 블록 안에서 예외가 발생해도 `finally`가 실행되므로 원래 환경 변수를 복구할 수 있습니다.

## 프로세스 전체 상태를 바꾸는 컨텍스트 관리자의 한계

위 예제는 `os.environ`을 변경합니다.

환경 변수는 함수 하나의 지역 상태가 아니라 **현재 프로세스 전체가 공유하는 상태**입니다.

따라서 컨텍스트 관리자가 원래 값을 정확히 복구하더라도 다음 문제는 별개입니다.

```text
스레드 A
→ MODE를 "test"로 변경

동시에 스레드 B
→ MODE를 읽음
→ 의도하지 않게 "test"를 관찰할 수 있음
```

또 다른 스레드가 같은 환경 변수를 동시에 바꾸면 복구 순서도 꼬일 수 있습니다.

즉 컨텍스트 관리자는 **자원 수명과 복구 동작을 구조화**해 주지만 공유 상태에 대한 동시성 제어까지 자동으로 제공하지는 않습니다.

따라서 이런 방식은 병렬 테스트나 다중 스레드 코드에서는 주의해서 사용해야 합니다.

## 여러 자원이 고정되어 있다면 여러 `with` 항목을 사용할 수 있습니다

필요한 자원 수가 코드 작성 시점에 고정되어 있다면 한 `with`문에서 여러 컨텍스트를 열 수 있습니다.

```python
with (
    input_path.open("r", encoding="utf-8") as source,
    output_path.open("w", encoding="utf-8") as destination,
):
    destination.write(source.read())
```

앞쪽 자원이 성공적으로 열렸지만 뒤쪽 자원을 얻는 과정에서 실패해도 이미 열린 자원은 정리됩니다.

정리는 획득의 반대 순서로 이루어집니다.

```text
source 획득
→ destination 획득
→ 사용
→ destination 정리
→ source 정리
```

## 자원 수가 실행 중 결정된다면 `ExitStack`

열어야 할 파일 수가 실행 중에 결정된다면 `ExitStack`이 유용합니다.

```python
from contextlib import ExitStack


with ExitStack() as stack:
    streams = [
        stack.enter_context(path.open("r", encoding="utf-8"))
        for path in paths
    ]

    ...
```

`stack.enter_context(...)`로 등록한 컨텍스트는 `ExitStack`이 종료될 때 정리됩니다.

예를 들어 다음 순서로 파일을 연다고 가정합니다.

```text
a.txt 열기 성공
b.txt 열기 성공
c.txt 열기 실패
```

`c.txt`를 여는 과정에서 예외가 발생하더라도 `ExitStack`은 이미 등록된 자원을 정리합니다.

```text
c.txt 열기 실패
→ b.txt 닫기
→ a.txt 닫기
→ 예외 전파
```

정리 순서는 일반적으로 자원을 획득한 순서의 반대입니다. 이는 한 자원이 다른 자원에 의존할 때 중요한 특성입니다.

`ExitStack`은 특히 다음 경우에 유용합니다.

- 파일 개수가 실행 중 결정됨
- 조건에 따라 일부 자원만 열림
- 여러 종류의 컨텍스트 관리자를 동적으로 조합함
- 도중 실패해도 이미 얻은 자원을 모두 정리해야 함

## 반복자를 반환할 때 파일 수명을 확인하기

다음 코드는 올바르게 동작하지 않습니다.

```python
from pathlib import Path


def lines(path: Path):
    with path.open(encoding="utf-8") as stream:
        return iter(stream)
```

흐름을 보면 이유가 분명합니다.

```text
파일 열기
→ iter(stream) 생성
→ return 실행
→ 함수가 with 블록을 벗어남
→ 파일 닫힘
→ 이미 닫힌 파일의 iterator가 호출자에게 전달됨
```

따라서 반환된 반복자를 실제로 소비하려 하면 닫힌 파일을 읽게 됩니다.

생성기 내부에서 `with` 블록을 유지하면 순회하는 동안 파일도 유지할 수 있습니다.

```python
from collections.abc import Iterator


def lines(path: Path) -> Iterator[str]:
    with path.open(encoding="utf-8") as stream:
        yield from stream
```

이 경우 파일의 수명은 생성기의 활성 수명과 연결됩니다.

또 다른 방법은 파일을 여닫는 책임을 호출자에게 맡기는 것입니다.

```python
from collections.abc import Iterable, Iterator


def stripped_lines(stream: Iterable[str]) -> Iterator[str]:
    for line in stream:
        yield line.rstrip("\n")
```

```python
with path.open(encoding="utf-8") as stream:
    for line in stripped_lines(stream):
        ...
```

이 구조에서는 파일 수명을 호출자가 명시적으로 볼 수 있습니다.

어느 방식이 더 좋은지는 "파일을 여는 책임이 누구에게 있는가"라는 API 설계 문제입니다.

## 한 번만 순회할 수 있는 입력을 두 번 소비하지 않기

다음 함수는 리스트에서는 동작하지만 생성기를 전달하면 예상과 다른 결과를 만들 수 있습니다.

```python
def average(values):
    count = sum(1 for _ in values)
    total = sum(values)
    return total / count
```

리스트를 전달하면 두 번 순회할 수 있습니다.

```python
average([10, 20, 30])
```

하지만 생성기를 전달하면 첫 번째 `sum()`이 모든 값을 소비합니다.

```python
values = (number for number in [10, 20, 30])
average(values)
```

두 번째 `sum(values)`에서는 남은 값이 없습니다.

이 문제를 해결하는 방법은 요구사항에 따라 다릅니다.

작은 입력이고 여러 번 순회해야 한다면 저장할 수 있습니다.

```python
def average(values) -> float:
    cached = tuple(values)

    if not cached:
        raise ValueError("값이 하나 이상 필요합니다.")

    return sum(cached) / len(cached)
```

한 번의 순회만으로 계산할 수도 있습니다.

```python
from collections.abc import Iterable


def average(values: Iterable[float]) -> float:
    count = 0
    total = 0.0

    for value in values:
        count += 1
        total += value

    if count == 0:
        raise ValueError("값이 하나 이상 필요합니다.")

    return total / count
```

큰 입력이나 스트리밍 데이터를 지원하려면 두 번째 방식이 더 적합합니다.

## 작은 입력과 큰 입력 구분하기

`data-report`는 전체 입력을 `tuple[Record, ...]`로 만든 뒤 집계합니다. 작은 로컬 보고서를 다루는 명시적인 제한이 있으므로 이 선택은 단순하고 검증하기 쉽습니다.

흐름은 다음과 같습니다.

```text
파일 읽기
→ 모든 행 검증
→ tuple[Record, ...] 생성
→ aggregate() 호출
```

이 방식의 장점은 다음과 같습니다.

- 입력 전체 검증이 끝난 뒤 계산을 시작할 수 있습니다.
- 같은 데이터를 여러 번 안전하게 순회할 수 있습니다.
- 테스트에서 실제 값 전체를 비교하기 쉽습니다.
- 파일 수명과 계산 수명을 분리할 수 있습니다.

반면 입력이 메모리에 들어오지 않을 만큼 커진다면 스트리밍 구조가 필요할 수 있습니다.

```text
파일에서 Record를 한 건씩 읽음
→ 생성기로 aggregate()에 전달
→ aggregate()는 전체 원본을 보관하지 않음
→ 필요한 합계와 상태만 갱신
```

이 경우에는 메모리 사용량을 줄일 수 있지만 다음 제약이 생깁니다.

- 입력을 다시 읽으려면 파일을 다시 열어야 할 수 있습니다.
- 중간에 오류가 발생하면 일부 데이터는 이미 처리되었을 수 있습니다.
- 생성기와 파일의 수명 관계를 더 주의해서 설계해야 합니다.

현재 요구사항에 없는 스트리밍 처리를 미리 추가할 필요는 없습니다.

선택 기준을 정리하면 다음과 같습니다.

| 요구사항 | 적합한 선택 |
|---|---|
| 작고 여러 번 사용할 데이터 | `list` 또는 `tuple` |
| 변경되면 안 되는 작은 결과 묶음 | `tuple` |
| 매우 크거나 끝을 미리 알 수 없는 입력 | 생성기 또는 다른 `Iterator` |
| 한 번의 순회만 필요한 변환 파이프라인 | 생성기 |
| 인덱스 접근과 길이 확인이 자주 필요함 | `list` 또는 `tuple` |

## 프로젝트에 적용하기

### 필수: `data-report`

- CSV 파일은 `with path.open(...)`으로 열어 정상 경로와 실패 경로 모두에서 닫습니다.
- 파일에서 읽은 값은 검증한 뒤 `Record`로 변환합니다.
- 현재 프로젝트는 작은 입력을 대상으로 하므로 입력 함수가 검증된 `tuple[Record, ...]`를 반환합니다.
- `aggregate()`는 `Iterable[Record]`를 받아 `list`, `tuple`, 생성기, 반복자 등 여러 입력 형태를 처리할 수 있게 합니다.
- `aggregate()`가 입력을 한 번만 순회하도록 작성하면 나중에 생성기를 전달해도 동작을 유지할 수 있습니다.
- 파일을 연 상태의 반복자를 `with` 블록 밖으로 그대로 반환하지 않습니다.

### 선택: `command-checker`

- `stdin`, `stdout`, `stderr` 파이프의 소유자가 누구인지 명확히 정합니다.
- 프로세스를 누가 시작하고 누가 종료·회수하는지 정합니다.
- 타임아웃, 출력 상한 초과, 예외 발생 시에도 이미 시작한 프로세스와 열린 파이프를 정리합니다.
- 여러 동적 자원을 순서대로 얻어야 한다면 `ExitStack` 같은 구조를 고려할 수 있습니다.

## 완료 기준

- `iterable`과 `iterator`를 구분할 수 있습니다.
- `for`문이 `iter()`와 `next()`를 기반으로 동작한다는 점을 설명할 수 있습니다.
- 반복자가 끝나면 `StopIteration`으로 종료를 알린다는 점을 이해합니다.
- 한 번 소비한 `iterator`나 생성기를 다시 사용하지 않습니다.
- 함수가 입력을 두 번 순회해야 할 때 생성기 입력에서 문제가 생길 수 있음을 설명할 수 있습니다.
- 큰 입력을 생성기로 한 항목씩 처리할 수 있습니다.
- 생성기 함수의 본문이 호출 시점이 아니라 순회 시점에 실행된다는 점을 설명할 수 있습니다.
- 생성기가 파일을 보유한다면 생성기의 수명과 파일 수명이 연결될 수 있음을 설명할 수 있습니다.
- 자원을 얻는 코드와 정리하는 코드를 같은 범위에 둡니다.
- `with`가 정상 종료와 예외 발생 모두에서 정리 동작을 수행한다는 점을 설명할 수 있습니다.
- 여러 자원을 얻는 도중 실패해도 이미 얻은 자원을 정리할 수 있습니다.
- 현재 입력 규모와 재사용 방식에 따라 `list`, `tuple`, 생성기 중 하나를 선택할 수 있습니다.

다음은 [파일, 구조화된 데이터와 CLI](../02-automation/01-files-structured-data-and-cli.md)입니다.
