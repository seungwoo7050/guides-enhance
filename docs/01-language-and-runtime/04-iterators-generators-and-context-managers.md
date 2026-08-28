# 반복자, 생성기와 컨텍스트 관리자

## 학습 목표

파일과 데이터를 처리하는 프로그램은 값을 한 항목씩 읽고, 파일이나 프로세스 같은 자원을 필요한 동안만 유지해야 합니다. 이 문서에서는 다음 내용을 다룹니다.

- `iterable`과 `iterator`의 차이
- 생성기를 사용한 지연 처리
- 한 번만 소비되는 데이터의 사용 규칙
- `with`를 사용한 자원 정리
- 여러 자원을 얻는 도중 실패했을 때의 정리 방법

필수 프로젝트에서는 [`data-report`](../../exercises/data-report/README.md)가 CSV 파일을 여닫고 `Record`를 순회할 때 이 원칙을 적용합니다.

## 선행 개념

- 함수와 예외의 기본 동작을 이해해야 합니다.
- `for`로 `iterable`을 순회할 수 있어야 합니다.
- 파일처럼 사용 후 닫아야 하는 자원이 있음을 알고 있어야 합니다.

## `iterable`과 `iterator`

`for`문은 인덱스를 직접 증가시키는 문법이 아니라 반복자 프로토콜을 사용합니다.

```python
values = [10, 20, 30]
iterator = iter(values)

print(next(iterator))
print(next(iterator))
```

- `iterable`: `iter(value)`를 호출해 `iterator`를 만들 수 있는 객체입니다.
- `iterator`: `next(value)`를 호출해 다음 값을 얻을 수 있는 객체입니다.

리스트는 여러 번 순회할 수 있지만 `iterator`는 일반적으로 한 번 소비됩니다.

```python
iterator = iter([1, 2, 3])
print(list(iterator))  # [1, 2, 3]
print(list(iterator))  # []
```

함수가 `iterator`를 받는다면 한 번만 순회하는지, 여러 번 필요해서 내부에 저장하는지 명확히 해야 합니다.

## 생성기로 값을 지연해서 만들기

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

`yield`가 들어 있는 함수는 호출하는 순간 본문 전체를 실행하지 않습니다. 다음 값을 요청할 때마다 다음 `yield`까지 실행한 뒤 멈춥니다.

생성기를 사용하면 다음과 같은 장점이 있습니다.

- 큰 파일 전체를 메모리에 올리지 않고 처리합니다.
- 데이터 생산 속도와 소비 속도를 자연스럽게 맞춥니다.
- 불필요한 중간 리스트를 만들지 않습니다.

다음 사항도 함께 고려해야 합니다.

- 오류가 함수 호출 시점이 아니라 실제 순회 중에 발생할 수 있습니다.
- 한 번 소비한 생성기는 처음부터 다시 사용할 수 없습니다.
- 생성기가 파일을 열고 있다면 순회를 중간에 멈췄을 때 파일이 언제 닫히는지 확인해야 합니다.

위 예제의 파일은 생성기가 끝까지 소비되거나 생성기가 명시적으로 닫힐 때 닫힙니다. 반복을 중단한 뒤 생성기 참조를 계속 보관하면 파일도 열린 채로 남을 수 있습니다.

## 생성기 표현식

```python
squares = (number * number for number in range(1_000_000))
```

리스트 내포와 달리 모든 값을 즉시 만들지 않습니다.

```python
total = sum(number * number for number in range(1_000_000))
```

지연 처리가 항상 더 좋은 선택은 아닙니다. 결과가 작고 여러 번 사용하거나 인덱스로 접근해야 한다면 리스트가 더 단순합니다.

## `yield from`

여러 `iterable`을 하나로 이어서 반환할 수 있습니다.

```python
from collections.abc import Iterable, Iterator
from pathlib import Path


def all_lines(paths: Iterable[Path]) -> Iterator[str]:
    for path in paths:
        yield from nonempty_lines(path)
```

파일 하나를 읽지 못했을 때 나머지 파일을 계속 처리할지 전체 작업을 중단할지는 별도의 오류 처리 규칙으로 정해야 합니다.

## 컨텍스트 관리자로 자원 수명 관리하기

```python
with path.open("r", encoding="utf-8") as stream:
    content = stream.read()
```

`with` 블록을 벗어나면 정상 종료와 예외 발생 여부에 관계없이 파일이 닫힙니다. `with`는 단순한 축약 문법이 아니라 자원을 얻고 정리하는 시점을 같은 범위에 두는 문법입니다.

```text
자원을 얻습니다.
→ 블록 안에서 사용합니다.
→ 정상 종료하거나 예외가 발생합니다.
→ 자원을 정리합니다.
```

같은 동작을 `try/finally`로 직접 작성할 수도 있습니다.

```python
stream = path.open("r", encoding="utf-8")
try:
    content = stream.read()
finally:
    stream.close()
```

## 사용자 정의 컨텍스트 관리자

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

이 예제는 프로세스 전체가 공유하는 환경 변수를 바꿉니다. 컨텍스트 관리자는 원래 값을 복구하지만, 다른 스레드가 동시에 같은 환경 변수를 읽거나 변경하는 문제까지 막아 주지는 않습니다. 따라서 병렬 테스트에는 적합하지 않을 수 있습니다.

## 여러 자원과 `ExitStack`

열어야 할 파일 수가 실행 중에 결정된다면 `ExitStack`을 사용할 수 있습니다.

```python
from contextlib import ExitStack


with ExitStack() as stack:
    streams = [
        stack.enter_context(path.open("r", encoding="utf-8"))
        for path in paths
    ]
    ...
```

세 번째 파일을 여는 과정에서 예외가 발생해도 앞서 연 파일은 모두 닫힙니다. 여러 자원을 차례로 얻는 도중 실패해도 이미 얻은 자원을 빠뜨리지 않고 정리할 수 있습니다.

## `iterator`를 반환할 때 파일 수명 확인하기

다음 코드는 올바르게 동작하지 않습니다.

```python
def lines(path: Path):
    with path.open(encoding="utf-8") as stream:
        return iter(stream)
```

함수가 반환되는 순간 `with` 블록이 끝나 파일이 닫힙니다. 반환된 `iterator`는 닫힌 파일을 읽으려 하므로 사용할 수 없습니다.

생성기 내부에서 `with` 블록을 유지하거나 파일을 여닫는 일을 호출자에게 맡겨야 합니다.

```python
from collections.abc import Iterator


def lines(path: Path) -> Iterator[str]:
    with path.open(encoding="utf-8") as stream:
        yield from stream
```

## 작은 입력과 큰 입력 구분하기

`data-report`는 전체 입력을 `tuple[Record, ...]`로 만든 뒤 집계합니다. 작은 로컬 보고서를 다루는 명시적인 제한이 있으므로 이 선택은 단순하고 검증하기 쉽습니다.

입력이 메모리에 들어오지 않을 만큼 커진다면 다음과 같이 바꿀 수 있습니다.

```text
파일에서 Record를 한 건씩 읽습니다.
→ 생성기로 aggregate()에 전달합니다.
→ aggregate()는 전체 원본을 보관하지 않고 합계만 갱신합니다.
```

현재 요구사항에 없는 스트리밍 처리를 미리 추가할 필요는 없습니다. 입력 크기와 재사용 방식에 따라 `list`, `tuple`, 생성기 중 하나를 선택합니다.

## 프로젝트에 적용하기

### 필수: `data-report`

- CSV 파일은 `with path.open(...)`으로 열어 정상·실패 경로에서 모두 닫습니다.
- `aggregate()`는 `Iterable[Record]`를 받아 `list`와 `tuple`뿐 아니라 `iterator`도 처리할 수 있습니다.
- 현재 프로젝트는 작은 입력을 대상으로 하므로 입력 함수가 검증된 `Record` 튜플을 반환합니다.

### 선택: `command-checker`

- `stdin`, `stdout`, `stderr` 파이프와 `selector`를 누가 닫는지 명확히 정합니다.
- 타임아웃, 출력 상한, 예외가 발생해도 이미 시작한 프로세스와 파이프를 정리합니다.

## 완료 기준

- `iterable`과 `iterator`를 구분합니다.
- 한 번 소비한 `iterator`를 다시 사용하지 않습니다.
- 큰 입력을 생성기로 한 항목씩 처리할 수 있습니다.
- 자원을 얻는 코드와 정리하는 코드를 같은 범위에 둡니다.
- 여러 자원을 얻는 도중 실패해도 이미 얻은 자원을 정리합니다.
- 현재 입력 규모에 생성기가 필요한지 판단할 수 있습니다.

다음은 [파일, 구조화된 데이터와 CLI](../02-automation/01-files-structured-data-and-cli.md)입니다.
