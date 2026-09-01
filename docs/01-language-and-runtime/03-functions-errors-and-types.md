# 함수, 예외 처리와 타입 검증

## 학습 목표

함수는 코드를 줄이는 수단에 그치지 않습니다. 함수는 **어떤 입력을 받고, 어떤 값을 반환하며, 어떤 조건에서 실패하는지**를 정하는 작은 계약(contract)의 단위입니다. 함수의 경계가 분명할수록 호출자는 내부 구현을 모두 알지 않아도 안전하게 사용할 수 있고, 테스트에서는 입력과 결과를 직접 확인할 수 있습니다.

이 문서를 마치면 다음 내용을 설명할 수 있어야 합니다.

- 함수의 입력과 반환값을 이름과 타입에 드러내는 방법
- 위치 인자와 키워드 전용 인자를 구분하는 이유
- 가변 기본 인자가 여러 호출 사이에서 상태를 공유하는 이유
- 처리할 수 있는 예외만 잡아야 하는 이유
- 예외를 변환할 때 원래 실패 원인을 보존하는 방법
- 외부 입력 오류와 정상 실행 후의 불일치를 구분하는 방법
- 타입 힌트와 실행 시 검증의 차이
- 합 타입에서 `None` 같은 경우를 검사해 타입을 좁히는 방법
- 파일 입출력과 계산 코드를 분리하는 이유

필수 프로젝트에서는 [`data-report`](../../exercises/data-report/README.md)의 입력 검증, 집계, 출력, CLI를 나눌 때 이 내용을 적용합니다.

## 선행 개념

- 객체의 가변성과 값의 동등성을 구분할 수 있어야 합니다.
- 함수의 인자와 반환값이 무엇인지 확인할 수 있어야 합니다.
- 예외가 발생하면 현재 함수의 정상 실행 흐름이 중단되고 호출자 쪽으로 전파될 수 있음을 알고 있어야 합니다.

## 함수의 계약을 이름과 시그니처에 드러내기

다음 함수 이름과 타입 힌트만 보아도 문자열을 받아 양의 정수 목록을 만들려는 함수임을 알 수 있습니다.

```python
def parse_positive_integers(text: str) -> list[int]:
    ...
```

`process(data)`처럼 범위가 모호한 이름보다 실제 동작을 드러내는 이름이 낫습니다. 특히 함수 이름에는 가능한 한 **행위와 결과의 의미**가 드러나야 합니다.

함수의 계약은 보통 다음 질문으로 확인할 수 있습니다.

```text
어떤 입력을 받는가?
입력에 어떤 제약이 있는가?
정상적으로 끝나면 무엇을 반환하는가?
실패하면 어떤 예외를 발생시키는가?
파일·시간·네트워크 같은 외부 상태를 바꾸는가?
```

예를 들어 한 함수가 다음 작업을 모두 수행하면 각 단계의 실패 원인을 분리하기 어렵고 계산 부분만 따로 테스트하기도 어렵습니다.

```text
파일을 읽습니다.
→ JSON을 파싱합니다.
→ 필드를 검증합니다.
→ 값을 집계합니다.
→ 터미널에 출력합니다.
```

역할별로 함수를 나누면 경계가 명확해집니다.

```python
from collections.abc import Iterable
from pathlib import Path


def load_records(path: Path) -> tuple[Record, ...]:
    ...


def aggregate(records: Iterable[Record]) -> Report:
    ...


def render_json(report: Report) -> str:
    ...
```

이 예에서 역할은 다음처럼 구분됩니다.

- `load_records()`는 외부 파일을 읽고 입력을 검증합니다.
- `aggregate()`는 이미 검증된 `Record`를 계산합니다.
- `render_json()`은 계산 결과를 문자열 표현으로 바꿉니다.

계산 코드는 가능하면 **값을 받아 값으로 반환**하도록 작성합니다. 파일, 시간, 환경 변수, 프로세스, 네트워크처럼 실행 환경에 의존하는 작업은 별도 경계 함수에서 수행하면 테스트와 오류 처리가 단순해집니다.

## 위치 인자와 키워드 전용 인자

Python 함수에서 `*` 뒤에 선언한 매개변수는 키워드로만 전달할 수 있습니다.

```python
def read_text(path: str, *, encoding: str = "utf-8") -> str:
    ...
```

다음 호출은 유효합니다.

```python
content = read_text("README.md", encoding="utf-8")
```

반면 `encoding`을 두 번째 위치 인자로 전달할 수는 없습니다.

```python
# TypeError
content = read_text("README.md", "utf-8")
```

키워드 전용 인자는 단순히 문법을 제한하는 기능이 아니라 호출부에서 설정의 의미를 드러내는 수단입니다.

특히 여러 `bool` 값을 위치 인자로 전달하면 각 값의 의미를 알기 어렵습니다.

```python
# True와 False가 각각 무엇을 뜻하는지 호출부만 보고 알기 어렵습니다.
run_case(case, True, False)
```

최소한 키워드로 의미를 드러내는 편이 낫습니다.

```python
run_case(case, capture_stderr=True, stop_on_error=False)
```

그러나 서로 배타적인 여러 상태를 `bool` 여러 개로 표현하면 조합 자체가 모호해질 수 있습니다. 이런 경우에는 `Enum`이나 이름이 있는 설정 객체가 더 적합합니다.

```python
from enum import Enum


class ErrorMode(Enum):
    CONTINUE = "continue"
    STOP = "stop"
```

호출부가 읽기 쉬운지뿐 아니라 **유효하지 않은 인자 조합을 만들기 쉬운 구조인지**도 함께 확인합니다.

## 기본 인자는 함수 정의 시 평가됩니다

Python의 기본 인자 표현식은 함수를 호출할 때마다 다시 평가되지 않습니다. `def` 문이 실행되어 함수 객체가 만들어질 때 한 번 평가되고, 그 결과 객체가 이후 호출에서 재사용됩니다.

```python
def append_value(value: int, values: list[int] = []) -> list[int]:
    values.append(value)
    return values
```

예상과 달리 다음 두 호출은 같은 기본 리스트를 사용합니다.

```python
print(append_value(1))  # [1]
print(append_value(2))  # [1, 2]
```

호출마다 새 리스트가 필요하다면 `None` 같은 불변 센티널 값을 기본값으로 사용하고 함수 안에서 새 객체를 만듭니다.

```python
def append_value(
    value: int,
    values: list[int] | None = None,
) -> list[int]:
    if values is None:
        values = []

    values.append(value)
    return values
```

여기서 중요한 기준은 **기본값 객체의 내부 상태가 호출 중 바뀔 수 있는가**입니다.

문자열이나 숫자처럼 불변 객체는 일반적으로 이 문제가 없습니다.

```python
def greet(name: str, prefix: str = "Hello") -> str:
    return f"{prefix}, {name}"
```

다만 겉이 `tuple`처럼 불변 객체라도 내부에 가변 객체를 포함할 수 있습니다.

```python
shared = ([],)

shared[0].append(1)
```

따라서 "`tuple`이면 항상 안전하다"가 아니라 **기본값으로 공유되는 객체 그래프가 변경되지 않는지**를 확인해야 합니다.

기본 객체를 여러 호출에서 의도적으로 공유하려는 경우도 있을 수 있지만, 그때는 함수 내부의 숨은 상태가 되므로 의도를 명확히 문서화하는 편이 좋습니다.

## 예외는 실패를 호출자에게 전달합니다

예외는 함수가 정상적인 반환값을 만들 수 없을 때 실패를 호출자에게 전달하는 방법입니다.

다음 함수는 문자열을 포트 번호로 변환하고 두 종류의 입력 오류를 검사합니다.

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

여기에는 서로 다른 두 검증 단계가 있습니다.

```text
"abc"
→ int("abc") 자체가 실패
→ "포트는 정수여야 합니다."

"70000"
→ 정수 변환은 성공
→ 허용 범위 검사 실패
→ "포트 범위는 1..65535입니다."
```

이처럼 **파싱 실패**와 **파싱된 값의 규칙 위반**은 같은 입력 오류 계층에 속할 수 있지만 원인은 다릅니다. 오류 메시지는 사용자가 무엇을 고쳐야 하는지 알 수 있도록 실패한 규칙을 구체적으로 설명해야 합니다.

## 예외를 변환할 때 원인을 보존하기

```python
try:
    port = int(text)
except ValueError as error:
    raise ValueError("포트는 정수여야 합니다.") from error
```

`raise 새로운_예외 from 원래_예외`는 예외 체인(exception chain)을 명시적으로 만듭니다.

호출자는 상위 수준의 의미 있는 오류를 볼 수 있고, traceback을 조사할 때는 실제로 어떤 하위 연산이 실패했는지도 확인할 수 있습니다.

```text
int(text)의 ValueError
        ↓ 원인으로 보존
parse_port()가 설명을 붙인 ValueError
```

하위 라이브러리의 예외를 그대로 노출하면 호출자가 구현 세부사항에 의존하게 될 수 있습니다. 반대로 원래 예외를 잃어버리면 디버깅 정보가 부족해질 수 있습니다. 예외 변환은 **추상화 경계에서는 의미를 바꾸고, 원인은 보존하는 것**이 핵심입니다.

## 처리할 수 있는 예외만 잡기

예외를 잡는 목적은 그 실패에 대해 현재 코드가 의미 있는 처리를 하기 위해서입니다.

```python
try:
    configuration = load_configuration(path)
except OSError as error:
    ...
except ValueError as error:
    ...
```

예를 들어 다음처럼 구분할 수 있습니다.

- `OSError`: 파일을 열거나 읽는 운영체제 작업이 실패했습니다.
- `ValueError`: 파일은 읽었지만 내용이 기대한 형식이나 값 규칙을 만족하지 않았습니다.

잡은 예외가 무엇을 뜻하는지 알아야 적절한 사용자 메시지, 복구 동작, 종료 상태를 선택할 수 있습니다.

다음 코드는 예상하지 못한 구현 오류까지 모두 숨깁니다.

```python
try:
    work()
except Exception:
    pass
```

예를 들어 `work()` 내부의 `NameError`, `TypeError`, 잘못된 인덱스 접근 같은 프로그래밍 오류도 조용히 사라질 수 있습니다. 그러면 프로그램이 계속 실행되면서 더 이해하기 어려운 상태를 만들 수 있습니다.

예외를 잡았다면 보통 다음 중 하나를 수행합니다.

- 현재 위치에서 실제로 복구합니다.
- 로그나 문맥 정보를 추가한 뒤 다시 발생시킵니다.
- 호출자에게 더 적절한 예외 타입으로 변환합니다.
- 애플리케이션 최상위 경계에서 사용자용 오류 메시지와 종료 상태로 바꿉니다.

넓은 `except Exception` 자체가 항상 잘못된 것은 아닙니다. 예를 들어 애플리케이션의 최상위 경계에서 예상하지 못한 실패를 기록한 뒤 비정상 종료하는 용도로 사용할 수 있습니다. 그러나 이 경우에도 오류를 **조용히 무시해서는 안 됩니다.**

```python
try:
    run_application()
except Exception:
    logger.exception("예상하지 못한 오류")
    raise
```

핵심 원칙은 다음과 같습니다.

> 현재 위치에서 의미 있게 처리할 수 없는 실패라면 숨기지 않습니다.

## 사용자 정의 예외로 도메인 오류 구분하기

외부 데이터가 프로젝트의 규칙을 만족하지 않는 경우에는 프로젝트 의미를 담은 사용자 정의 예외를 사용할 수 있습니다.

```python
class DataReportError(ValueError):
    """입력 파일이 data-report 규칙을 만족하지 않을 때 발생합니다."""
```

`ValueError`를 상속했으므로 "값이 프로젝트가 요구하는 규칙에 맞지 않는다"는 일반적인 의미도 유지하면서 `DataReportError`만 별도로 처리할 수 있습니다.

예를 들어 `data-report`에서는 다음 실패를 같은 도메인 오류 계층으로 묶을 수 있습니다.

- 잘못된 CSV 헤더
- 필요한 JSON 필드 누락
- 허용되지 않는 `amount` 표현
- 필드 값이 프로젝트의 제약을 만족하지 않음

```python
def require_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise DataReportError(f"{field}는 문자열이어야 합니다.")

    return value
```

CLI에서는 이 예외를 잡아 사용자에게 입력 수정이 필요하다는 사실을 알리고 프로젝트가 정한 종료 상태로 변환할 수 있습니다.

```python
try:
    ...
except DataReportError as error:
    print(f"error: {error}", file=sys.stderr)
    return 2
```

여기서 종료 상태 `2`는 Python 전체에 강제되는 규칙이 아니라 **이 프로젝트에서 정한 CLI 계약**입니다. 다른 프로그램에서는 다른 종료 상태 정책을 사용할 수 있습니다.

## 예외와 정상적인 불일치를 구분하기

모든 "원하는 결과가 나오지 않은 상황"을 예외로 표현할 필요는 없습니다.

먼저 작업 자체를 수행할 수 없는 상황과, 작업은 정상적으로 수행했지만 결과가 조건을 만족하지 않은 상황을 구분합니다.

```text
입력을 읽거나 작업을 시작할 수 없음
→ 작업 자체가 성립하지 않음
→ 예외
→ CLI에서 종료 상태 2

작업은 정상적으로 끝났지만 예상값과 다름
→ 정상적인 비교 결과 중 하나
→ 결과값
→ 종료 상태 1

모든 결과가 일치함
→ 정상적인 비교 결과
→ 결과값
→ 종료 상태 0
```

예를 들어 테스트 대상 프로그램의 출력이 예상값과 다른 것은 "비교 작업 실패"가 아니라 **비교 작업의 정상적인 결과가 불일치**인 경우가 많습니다.

```python
@dataclass(frozen=True)
class Result:
    passed: bool
    message: str
```

이 구분은 선택 프로젝트인 `command-checker`에서 직접 사용합니다.

예외를 남용하면 호출자는 정상적으로 발생할 수 있는 결과까지 `try`/`except`로 처리해야 합니다. 반대로 실제로 작업을 계속할 수 없는 오류를 일반 반환값으로 섞으면 호출자가 오류 확인을 빠뜨리기 쉬워집니다.

## 타입 힌트는 실행 시 검사가 아닙니다

다음 함수의 타입 힌트는 `values`가 정수 리스트이고 결과가 정수라는 의도를 나타냅니다.

```python
def total(values: list[int]) -> int:
    return sum(values)
```

타입 힌트는 다음 작업에 도움이 됩니다.

- 함수가 받는 값과 반환하는 값을 파악합니다.
- `None` 가능성과 컬렉션 원소 타입을 드러냅니다.
- 정적 타입 검사기와 편집기가 오류 가능성을 찾도록 합니다.
- 모듈 간 함수 사용 방식을 변경할 때 영향을 추적합니다.

그러나 기본 Python 실행기는 함수 호출 때 타입 힌트를 보고 인자를 자동으로 거부하지 않습니다.

다음 호출도 함수 진입 자체는 가능합니다.

```python
total(["1", "2"])  # 타입 힌트와 맞지 않음
```

실제 실패 여부와 실패 지점은 함수 구현에 달려 있습니다. 이 예에서는 `sum()`이 문자열을 정수 합산 방식으로 처리할 수 없기 때문에 실행 중 오류가 발생합니다.

즉 다음 두 질문은 서로 다릅니다.

```text
이 값은 코드 내부에서 어떤 타입으로 취급할 예정인가?
→ 타입 힌트와 정적 분석

실제로 들어온 외부 데이터가 요구 조건을 만족하는가?
→ 실행 시 검증
```

JSON, CSV, 환경 변수, CLI 인자는 프로그램 밖에서 들어오므로 타입 힌트만 신뢰할 수 없습니다.

## 외부 입력은 검증한 뒤 좁은 타입으로 바꾸기

JSON을 파싱한 값처럼 아직 형식을 신뢰할 수 없는 입력은 처음부터 `str`이라고 단정하지 않는 편이 좋습니다.

```python
def require_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise DataReportError(f"{field}는 문자열이어야 합니다.")

    return value
```

이 함수의 흐름은 다음과 같습니다.

```text
외부에서 들어온 알 수 없는 값
        ↓ object
isinstance(value, str) 검사
        ↓
검증 성공
        ↓ str로 취급
```

검증 함수가 성공해서 `str`을 반환한 뒤에는 이후 계산 코드가 같은 타입 검사를 반복하지 않아도 됩니다.

```python
raw_category: object = payload["category"]
category = require_string(raw_category, "category")

print(category.lower())
```

입력 경계에서 검증하고 내부에서는 검증된 타입을 사용하는 구조가 오류 처리를 한곳에 모으는 데 도움이 됩니다.

## 타입 검증과 값 검증은 다릅니다

타입이 맞는 것만으로 값이 유효하다고 할 수는 없습니다.

```python
def require_category(value: object) -> str:
    if not isinstance(value, str):
        raise DataReportError("category는 문자열이어야 합니다.")

    category = value.strip()
    if not category:
        raise DataReportError("category는 빈 문자열일 수 없습니다.")

    return category
```

여기에는 두 단계가 있습니다.

```text
타입 검증
value가 str인가?

값 검증
공백을 제거한 뒤 비어 있지 않은가?
```

외부 입력을 검증할 때는 "타입이 맞는가"와 "도메인 규칙을 만족하는가"를 구분해야 합니다.

## 합 타입과 타입 좁히기

함수 결과가 여러 타입 중 하나일 수 있다면 합 타입(union type)으로 표현할 수 있습니다.

```python
def find_name(identifier: int) -> str | None:
    ...
```

이 함수는 문자열을 찾거나, 이름이 없다는 정상적인 경우를 `None`으로 반환합니다.

```python
name = find_name(42)
```

이 시점에서 `name`은 `str | None`입니다. 바로 문자열 메서드를 호출해서는 안 됩니다.

```python
# name이 None일 수 있으므로 안전하지 않습니다.
print(name.upper())
```

먼저 `None`인 경우를 분리합니다.

```python
name = find_name(42)

if name is None:
    raise LookupError("이름을 찾지 못했습니다.")

print(name.upper())
```

`if name is None` 분기 이후에는 남은 경로에서 `name`이 `str`이라는 사실을 정적 타입 검사기도 추론할 수 있습니다. 이를 **타입 좁히기(type narrowing)**라고 합니다.

`None`을 반환할지 예외를 발생시킬지는 상황의 의미에 따라 정합니다.

- 결과가 없는 것이 정상적으로 예상되는 경우: `None`이 적합할 수 있습니다.
- 결과가 반드시 있어야 하며 없으면 작업을 계속할 수 없는 경우: 예외가 더 적합할 수 있습니다.

예를 들어 사전 조회처럼 "없을 수도 있음"이 자연스러운 연산과, 필수 설정 조회처럼 "없으면 프로그램을 시작할 수 없음"은 같은 방식으로 표현할 필요가 없습니다.

## 구조적 인터페이스와 `Protocol`

함수가 구체 클래스 전체가 아니라 특정 동작 몇 개만 필요로 한다면 `Protocol`로 필요한 인터페이스를 표현할 수 있습니다.

```python
from typing import Protocol


class Clock(Protocol):
    def monotonic(self) -> float:
        ...
```

다음 함수는 특정 시계 구현 클래스가 아니라 `monotonic()` 메서드를 제공하는 객체를 요구합니다.

```python
def elapsed(clock: Clock, started_at: float) -> float:
    return clock.monotonic() - started_at
```

실제 코드에서는 시스템 시계를 제공하고, 테스트에서는 값이 고정된 가짜 시계를 전달할 수 있습니다.

```python
class FakeClock:
    def __init__(self, now: float) -> None:
        self.now = now

    def monotonic(self) -> float:
        return self.now
```

`FakeClock`이 `Clock`을 명시적으로 상속하지 않아도 필요한 메서드의 구조가 맞으면 정적 타입 검사에서 `Clock`으로 사용할 수 있습니다. 이것이 `Protocol`의 **구조적 타이핑(structural typing)** 성격입니다.

`Protocol`은 주로 정적 타입 분석을 위한 도구입니다. 선언했다고 해서 Python이 모든 함수 호출에서 자동으로 런타임 인터페이스 검사를 수행하는 것은 아닙니다.

모든 클래스마다 `Protocol`을 만들 필요는 없습니다. 다음처럼 외부 기능을 테스트에서 쉽게 교체해야 하는 경계에 특히 유용합니다.

- 시간
- 파일 저장소
- 네트워크 클라이언트
- 프로세스 실행기
- 난수 공급자

## 계산과 입출력을 분리하기

다음 함수는 파일이나 터미널에 접근하지 않습니다.

```python
def aggregate(records: Iterable[Record]) -> Report:
    ...
```

입력으로 받은 `Record`만 사용해 `Report`를 만들기 때문에 테스트에서는 파일을 만들 필요가 없습니다.

```python
report = aggregate(
    [
        Record(category="food", amount=Decimal("10.00")),
        Record(category="food", amount=Decimal("5.00")),
    ]
)
```

다음 함수도 `Report`를 문자열로 바꿀 뿐 파일을 쓰지 않습니다.

```python
def render_json(report: Report) -> str:
    ...
```

실제 파일 저장은 바깥 계층에서 처리합니다.

```python
rendered = render_json(report)
output_path.write_text(rendered, encoding="utf-8")
```

전체 흐름을 다음처럼 나눌 수 있습니다.

```text
외부 입력
   ↓
읽기·파싱·검증
   ↓
검증된 Record
   ↓
순수한 집계 계산
   ↓
Report
   ↓
문자열 렌더링
   ↓
파일 또는 stdout 출력
```

이 구조에서는 각 단계의 테스트 대상이 분명해집니다.

- 입력 검증 테스트: 잘못된 필드가 올바른 예외를 만드는지 확인합니다.
- 집계 테스트: `Record`를 직접 전달하고 `Report`를 비교합니다.
- 렌더링 테스트: `Report`를 직접 전달하고 문자열을 비교합니다.
- CLI 테스트: 파일 오류, 입력 오류, 종료 상태, `stderr`를 확인합니다.

집계와 출력 형식을 검사하기 위해 매번 임시 파일이나 하위 프로세스를 만들 필요가 없으므로 테스트가 더 빠르고 실패 원인도 좁혀집니다.

## `main()`은 프로그램 경계입니다

라이브러리 함수와 CLI의 책임을 분리하면 `main()`은 내부 실패를 사용자에게 보이는 프로세스 결과로 바꾸는 경계가 됩니다.

```python
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    try:
        ...
    except DataReportError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    return 0
```

내부 함수는 가능하면 오류의 의미를 예외로 보존하고, `main()`이 다음 프로세스 수준의 정책을 결정합니다.

```text
어떤 메시지를 stderr에 출력할 것인가?
어떤 종료 상태를 반환할 것인가?
사용자에게 traceback을 노출할 것인가?
```

`main()` 아래의 모든 함수가 각자 `print()`하고 종료 상태를 결정하기 시작하면 오류 정책이 여러 위치로 흩어집니다.

프로젝트에서 `main()`이 정수 값을 반환하고 다음처럼 실행한다면,

```python
raise SystemExit(main())
```

그 정수가 프로세스 종료 상태가 됩니다. 따라서 테스트에서는 프로세스를 실제로 종료하지 않고 `main([...])`의 반환값만 검사할 수 있습니다.

## 프로젝트에 적용하기

### 필수: `data-report`

- `load_records()`는 파일을 읽고 각 행 또는 객체의 필드를 검사합니다.
- 외부 입력은 신뢰하지 않고 타입과 값 규칙을 실행 시 검증합니다.
- 검증이 끝난 데이터만 `Record`로 변환합니다.
- `aggregate()`는 검증된 `Record`를 받아 `Report`를 반환합니다.
- `render_text()`와 `render_json()`은 같은 `Report`를 문자열로 바꿉니다.
- 계산 함수는 파일과 터미널에 직접 접근하지 않습니다.
- 입력 형식 오류는 `DataReportError` 같은 도메인 예외로 표현합니다.
- `main()`은 파일 오류와 입력 오류를 사용자 메시지와 프로젝트에서 정한 종료 상태 `2`로 바꿉니다.
- 정상적으로 처리된 결과는 예외가 아니라 반환값으로 표현합니다.

### 선택: `command-checker`

- JSON 명세 오류는 `SpecificationError`로 알립니다.
- 프로세스를 시작하거나 정리할 수 없는 경우는 `ExecutionError`로 알립니다.
- 실행 후 출력이 예상과 다른 경우는 예외가 아니라 `Result(passed=False)`로 반환합니다.
- 시간이나 프로세스 실행 기능을 테스트에서 교체해야 한다면 작은 `Protocol`로 경계를 정의할 수 있습니다.

## 완료 기준

- 함수 이름과 시그니처에서 입력과 결과를 대략 파악할 수 있습니다.
- 키워드 전용 인자를 사용해야 하는 경우를 설명할 수 있습니다.
- 가변 기본 인자가 여러 호출에서 공유되는 이유를 설명할 수 있습니다.
- 외부 입력의 실행 시 검증과 내부 타입 힌트를 구분합니다.
- 타입 검증과 값 검증을 구분합니다.
- `str | None` 같은 합 타입을 분기 후 좁혀 사용할 수 있습니다.
- 입력 오류와 정상 실행 후의 불일치를 다른 방식으로 표현합니다.
- 처리할 수 없는 예외를 조용히 숨기지 않습니다.
- 예외를 변환할 때 `raise ... from ...`으로 원인을 보존할 수 있습니다.
- 계산과 파일·터미널 입출력을 별도 함수로 나눕니다.
- `main()`이 내부 오류를 `stderr` 메시지와 종료 상태로 바꿉니다.
- `Protocol`이 구체 구현이 아니라 필요한 동작의 형태를 표현한다는 점을 설명할 수 있습니다.

다음은 [반복자, 생성기와 컨텍스트 관리자](04-iterators-generators-and-context-managers.md)입니다.
