# 함수, 예외 처리와 타입 검증

## 학습 목표

함수는 코드를 줄이는 수단에 그치지 않습니다. 어떤 입력을 받고, 무엇을 반환하며, 어떤 조건에서 실패하는지를 정하는 단위입니다.

이 문서를 마치면 다음 내용을 설명할 수 있어야 합니다.

- 함수의 입력과 반환값을 이름과 타입에 드러내는 방법
- 처리할 수 있는 예외만 잡아야 하는 이유
- 외부 입력 오류와 정상 실행 후의 불일치를 구분하는 방법
- 타입 힌트와 실행 시 검증의 차이
- 파일 입출력과 계산 코드를 분리하는 이유

필수 프로젝트에서는 [`data-report`](../../exercises/data-report/README.md)의 입력 검증, 집계, 출력, CLI를 나눌 때 이 내용을 적용합니다.

## 선행 개념

- 객체의 가변성과 값의 동등성을 구분할 수 있어야 합니다.
- 함수의 인자와 반환값을 확인할 수 있어야 합니다.

## 함수 이름으로 실제 동작을 드러내기

```python
def parse_positive_integers(text: str) -> list[int]:
    ...
```

`process(data)`처럼 범위가 모호한 이름보다 어떤 입력을 받아 무엇을 반환하는지 알 수 있는 이름이 낫습니다.

한 함수가 다음 작업을 모두 수행하면 실패 원인을 구분하기 어렵습니다.

```text
파일을 읽습니다.
→ JSON을 파싱합니다.
→ 필드를 검증합니다.
→ 값을 집계합니다.
→ 터미널에 출력합니다.
```

각 작업을 다음처럼 나눌 수 있습니다.

```python
def load_records(path: Path) -> tuple[Record, ...]:
    ...


def aggregate(records: Iterable[Record]) -> Report:
    ...


def render_json(report: Report) -> str:
    ...
```

계산 코드는 값을 받아 값으로 결과를 반환하도록 작성합니다. 파일, 시간, 프로세스처럼 외부 상태에 의존하는 작업은 별도 함수에서 수행합니다.

## 위치 인자와 키워드 전용 인자

호출 코드에서 의미가 드러나야 하는 설정은 키워드 전용 인자로 만들 수 있습니다.

```python
def read_text(path: str, *, encoding: str = "utf-8") -> str:
    ...
```

```python
content = read_text("README.md", encoding="utf-8")
```

여러 `bool` 값을 위치 인자로 전달하면 각 값의 의미를 파악하기 어렵습니다.

```python
# 각 값이 무엇을 뜻하는지 호출부에서 알기 어렵습니다.
run_case(case, True, False)
```

이런 경우에는 키워드 인자, `Enum`, 이름이 있는 설정 객체를 사용합니다.

## 가변 기본 인자를 피하기

기본 인자는 함수를 호출할 때마다 평가되지 않고 함수가 정의될 때 한 번 평가됩니다.

```python
def append_value(value: int, values: list[int] = []) -> list[int]:
    values.append(value)
    return values
```

위 함수는 여러 호출에서 같은 리스트를 공유합니다. 호출마다 새 리스트가 필요하면 `None`을 기본값으로 사용합니다.

```python
def append_value(value: int, values: list[int] | None = None) -> list[int]:
    if values is None:
        values = []
    values.append(value)
    return values
```

문자열, 숫자, 불변 `tuple`처럼 바꿀 수 없는 기본값에는 이 문제가 없습니다.

## 예외로 실패 원인 보존하기

```python
def parse_port(text: str) -> int:
    try:
        port = int(text)
    except ValueError as error:
        raise ValueError("포트는 정수여야 합니다.") from error

    if not 1 <= port <= 65535:
        raise ValueError("포트 범위는 1..65535입니다.")
    return port
```

`raise ... from error`를 사용하면 호출자에게 더 적절한 설명을 제공하면서 원래 예외도 보존할 수 있습니다.

### 처리할 수 있는 예외만 잡기

```python
try:
    configuration = load_configuration(path)
except OSError as error:
    ...
except ValueError as error:
    ...
```

다음 코드는 예상하지 못한 구현 오류까지 숨깁니다.

```python
try:
    work()
except Exception:
    pass
```

예외를 잡았다면 다음 중 하나를 수행해야 합니다.

- 현재 위치에서 복구합니다.
- 호출자에게 더 구체적인 예외로 바꿔 다시 발생시킵니다.
- 최상위 `main()`에서 사용자용 오류 메시지와 종료 상태로 바꿉니다.

아무 처리 없이 예외를 무시하는 것은 오류 처리가 아닙니다.

## 사용자 정의 예외

외부 데이터가 잘못된 경우와 정상적으로 처리한 결과가 예상과 다른 경우를 구분해야 합니다.

```python
class DataReportError(ValueError):
    """입력 파일이 data-report 규칙을 만족하지 않을 때 발생합니다."""
```

`data-report`에서는 잘못된 CSV 헤더, 누락된 JSON 필드, 유효하지 않은 `amount`를 `DataReportError`로 알립니다. CLI는 이를 `stderr` 메시지와 종료 상태 2로 바꿉니다.

반면 계산은 정상적으로 끝났지만 검증 대상의 결과가 예상과 다른 경우라면 예외보다 결과값이 적절할 수 있습니다.

```text
작업을 시작할 수 없음 → 예외 → 종료 상태 2
작업은 끝났지만 예상값과 다름 → 결과값 → 종료 상태 1
모든 결과가 일치함 → 결과값 → 종료 상태 0
```

이 구분은 선택 프로젝트인 `command-checker`에서 직접 사용합니다.

## 타입 힌트와 실행 시 검증 구분하기

```python
def total(values: list[int]) -> int:
    return sum(values)
```

타입 힌트는 다음 작업에 도움이 됩니다.

- 함수가 받는 값과 반환하는 값을 파악합니다.
- `None` 가능성과 컬렉션 원소 타입을 드러냅니다.
- 정적 타입 검사기와 편집기가 오류 가능성을 찾도록 합니다.
- 모듈 간 함수 사용 방식을 변경할 때 영향을 추적합니다.

그러나 JSON, CSV, 환경 변수, CLI 인자가 타입 힌트를 따르는지는 Python이 자동으로 검사하지 않습니다.

```python
def require_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise DataReportError(f"{field}는 문자열이어야 합니다.")
    return value
```

외부 입력은 `object` 또는 넓은 타입으로 받은 뒤 실제 값을 검사해 더 구체적인 타입으로 바꿉니다.

## 합 타입과 타입 좁히기

```python
def find_name(identifier: int) -> str | None:
    ...


name = find_name(42)
if name is None:
    raise LookupError("이름을 찾지 못했습니다.")
print(name.upper())
```

결과가 없음을 `None`으로 표현할지 예외로 표현할지는 호출자가 반드시 실패로 처리해야 하는지, 정상적인 결과 중 하나인지에 따라 정합니다.

## 구조적 인터페이스

함수가 특정 동작만 필요로 한다면 구체 클래스 대신 작은 `Protocol`을 받을 수 있습니다.

```python
from typing import Protocol


class Clock(Protocol):
    def monotonic(self) -> float:
        ...
```

테스트에서는 가짜 시계를 전달해 시간에 의존하는 동작을 반복해서 재현할 수 있습니다. 모든 코드에 `Protocol`을 추가할 필요는 없습니다. 시간·파일·네트워크처럼 테스트에서 대체해야 하는 외부 기능이 있을 때 사용합니다.

## 계산과 입출력을 분리하기

다음 함수는 파일이나 터미널에 접근하지 않습니다.

```python
def aggregate(records: Iterable[Record]) -> Report:
    ...
```

다음 함수도 `Report`를 문자열로 바꿀 뿐 파일을 쓰지 않습니다.

```python
def render_json(report: Report) -> str:
    ...
```

실제 파일 저장은 `main()`에서 처리합니다.

```python
rendered = render_json(report)
output_path.write_text(rendered, encoding="utf-8")
```

이렇게 나누면 집계와 출력 형식을 임시 파일이나 하위 프로세스 없이 빠르게 검사할 수 있습니다.

## 프로젝트에 적용하기

### 필수: `data-report`

- `load_records()`는 파일을 읽고 각 행의 필드를 검사합니다.
- `aggregate()`는 `Record`를 받아 `Report`를 반환합니다.
- `render_text()`와 `render_json()`은 같은 `Report`를 문자열로 바꿉니다.
- `main()`은 파일 오류와 입력 오류를 사용자 메시지와 종료 상태 2로 바꿉니다.

### 선택: `command-checker`

- JSON 명세 오류는 `SpecificationError`로 알립니다.
- 프로세스를 시작하거나 정리할 수 없는 경우는 `ExecutionError`로 알립니다.
- 실행 후 출력이 예상과 다른 경우는 `Result(passed=False)`로 반환합니다.

## 완료 기준

- 함수 이름에서 입력과 결과를 대략 파악할 수 있습니다.
- 외부 입력의 실행 시 검증과 내부 타입 힌트를 구분합니다.
- 입력 오류와 정상 실행 후의 불일치를 다른 방식으로 표현합니다.
- 처리할 수 없는 예외를 숨기지 않습니다.
- 계산과 파일·터미널 입출력을 별도 함수로 나눕니다.
- `main()`이 오류를 `stderr`와 종료 상태로 바꿉니다.

다음은 [반복자, 생성기와 컨텍스트 관리자](04-iterators-generators-and-context-managers.md)입니다.
