# 파일, 구조화된 데이터와 CLI

## 학습 목표

이 문서에서는 파일과 외부 입력을 읽고 검증해 프로그램 내부에서 사용할 값으로 바꾸는 방법을 다룹니다.

- `pathlib`로 경로를 다룹니다.
- 상대 경로가 어떤 디렉터리를 기준으로 해석되는지 구분합니다.
- 텍스트와 바이트를 구분하고 인코딩을 명시합니다.
- CSV와 JSON을 표준 라이브러리로 읽습니다.
- 파싱한 값을 필드별로 검증합니다.
- 서로 다른 입력 형식을 같은 내부 타입으로 변환합니다.
- `argparse`로 CLI 인자를 받습니다.
- 정상 출력, 오류 출력, 종료 상태를 구분합니다.
- 파일을 쓰는 도중 실패했을 때 기존 결과를 보존하는 방법을 이해합니다.

필수 프로젝트인 [`data-report`](../../exercises/data-report/README.md)는 이 문서의 내용을 직접 적용합니다.

## 선행 개념

이 문서를 읽기 전에 다음 개념을 알고 있어야 합니다.

- `Path` 객체를 만들고 `/` 연산자로 하위 경로를 조합할 수 있습니다.
- `with` 문으로 파일을 열고 닫을 수 있습니다.
- 예외가 발생하면 현재 함수에서 처리하거나 상위 호출자에게 전달할 수 있음을 이해합니다.
- `str`과 `bytes`가 서로 다른 타입임을 이해합니다.
- JSON의 **문법이 올바른지 확인하는 일**과 프로그램이 요구하는 **데이터 구조와 값을 검증하는 일**이 서로 다른 단계임을 이해합니다.

예를 들어 다음 JSON은 문법적으로는 올바릅니다.

```json
{
  "category": 123,
  "amount": "not-a-number"
}
```

하지만 프로그램이 `category`에 문자열, `amount`에 숫자를 요구한다면 이 데이터는 프로그램 입장에서는 유효하지 않습니다.

---

## `pathlib`로 경로 의미 보존하기

파일 경로는 일반 문자열처럼 보이지만 파일 시스템의 위치를 나타내는 값입니다. 문자열 덧셈으로 경로를 조립하기보다 `Path`를 사용하면 코드에서 경로라는 의미를 명확하게 유지할 수 있습니다.

```python
from pathlib import Path

root = Path(__file__).resolve().parent
config = root / "examples" / "sales.csv"
```

각 표현의 의미는 다음과 같습니다.

- `Path(__file__)`: 현재 Python 파일의 경로를 `Path`로 만듭니다.
- `resolve()`: 경로를 가능한 한 절대 경로 형태로 정규화합니다.
- `.parent`: 해당 파일이 들어 있는 디렉터리를 얻습니다.
- `/`: 하위 경로를 조합합니다.

문자열로 직접 경로를 조립하는 방식은 피합니다.

```python
# 권장하지 않는 예
path = directory + "/" + filename
```

운영체제마다 경로 구분자가 다를 수 있고, 앞뒤 구분자 처리도 직접 해야 하기 때문입니다.

`Path`는 파일 전체를 간단히 읽고 쓰는 메서드도 제공합니다.

```python
path = Path("notes.txt")
path.write_text("hello\n", encoding="utf-8")
content = path.read_text(encoding="utf-8")
```

`read_text()`는 파일 전체를 메모리에 읽고, `write_text()`는 주어진 문자열 전체를 기록합니다. 작은 설정 파일이나 보고서에는 편리하지만 큰 파일에는 적합하지 않을 수 있습니다.

큰 파일은 한 번에 읽지 않고 필요한 단위로 순차 처리합니다.

```python
from collections.abc import Iterator
from pathlib import Path


def error_lines(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if "ERROR" in line:
                yield line.rstrip("\n")
```

이 코드는 파일 전체를 메모리에 올리지 않고 한 줄씩 읽습니다.

---

## 상대 경로의 기준 정하기

`Path("data/input.csv")` 같은 상대 경로는 그 자체만으로 완전한 위치를 나타내지 않습니다. **어느 디렉터리를 기준으로 해석할지**가 함께 정해져야 합니다.

일반적인 기준은 다음과 같습니다.

- 사용자가 CLI로 전달한 입력 파일: 보통 **현재 작업 디렉터리**
- 프로그램과 함께 배포한 기본 자료: 보통 **프로그램 파일 또는 패키지가 있는 디렉터리**
- 설정 파일 안에 기록한 상대 경로: 보통 **설정 파일이 있는 디렉터리** 또는 문서에서 명시한 별도 기준 디렉터리

현재 작업 디렉터리는 다음과 같이 얻습니다.

```python
from pathlib import Path

cwd = Path.cwd()
```

현재 Python 파일이 있는 디렉터리는 다음과 같이 얻을 수 있습니다.

```python
root = Path(__file__).resolve().parent
```

이 둘은 같은 값이라고 가정하면 안 됩니다.

예를 들어 사용자가 `/tmp`에서 다음 명령을 실행했다고 가정합니다.

```text
python /home/user/project/app.py
```

이때 보통:

```text
Path.cwd()
→ /tmp

Path(__file__).resolve().parent
→ /home/user/project
```

입니다.

따라서 다음 두 경로는 서로 다른 파일을 가리킬 수 있습니다.

```python
Path("config.json")
Path(__file__).resolve().parent / "config.json"
```

CLI에서 사용자가 전달한 상대 경로를 프로그램 파일 위치 기준으로 임의 변환하면 사용자가 기대한 파일이 아닌 다른 파일을 읽을 수 있습니다. 상대 경로의 기준은 프로그램 인터페이스의 일부로 명확히 정해야 합니다.

---

## 텍스트와 바이트 구분하기

파일이나 프로세스에서 읽는 데이터는 크게 두 종류로 나눌 수 있습니다.

- 텍스트: 문자 데이터, Python에서는 `str`
- 바이트: 가공되지 않은 이진 데이터, Python에서는 `bytes`

텍스트 파일은 바이트를 문자로 해석하기 위한 **인코딩**이 필요합니다.

```python
content = path.read_text(encoding="utf-8")
```

인코딩을 생략하면 실행 환경의 기본 인코딩에 의존할 수 있습니다. 같은 파일이 환경마다 다르게 해석되는 문제를 피하려면 입력 형식이 정해져 있는 프로그램에서는 인코딩을 명시합니다.

파일의 바이트열이 지정한 인코딩으로 해석되지 않으면 기본적으로 `UnicodeDecodeError`가 발생합니다.

```python
content = path.read_text(
    encoding="utf-8",
    errors="strict",
)
```

`errors="strict"`는 기본 동작이므로 보통 생략합니다. 잘못된 바이트를 대체 문자로 바꾸는 `errors="replace"` 같은 정책도 있지만, 입력 손상을 숨길 수 있으므로 입력 명세에 맞게 선택해야 합니다.

이진 형식은 텍스트로 디코딩하지 않고 바이트 그대로 읽습니다.

```python
payload = path.read_bytes()
```

또는 이진 모드를 사용할 수 있습니다.

```python
with path.open("rb") as stream:
    payload = stream.read()
```

텍스트 중심 프로그램에서는 `bytes`와 `str` 변환을 여러 모듈에 흩어 놓지 않는 편이 좋습니다.

```text
외부 bytes
→ 입력 경계에서 decode
→ 프로그램 내부에서는 str
```

출력도 반대로 마지막 경계에서 인코딩하면 인코딩 책임을 추적하기 쉽습니다.

---

## JSON은 파싱한 뒤 다시 검증하기

JSON 입력 처리는 최소 두 단계로 나눌 수 있습니다.

```text
JSON 텍스트
→ JSON 문법 파싱
→ 프로그램이 요구하는 구조와 값 검증
```

Python의 `json.loads()`는 첫 번째 단계만 수행합니다.

```python
import json

raw: object = json.loads(path.read_text(encoding="utf-8"))
```

`json.loads()`가 성공했다는 사실은 JSON 문법이 올바르다는 뜻입니다. 그러나 최상위 값이 객체인지, 필수 필드가 있는지, 각 필드가 올바른 타입인지까지 보장하지는 않습니다.

최상위 값이 객체여야 한다면 직접 확인합니다.

```python
def require_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DataReportError("최상위 값은 객체여야 합니다.")
    return value
```

외부 JSON에서는 보통 다음 항목을 확인합니다.

- 최상위 값이 배열인지 객체인지
- 필수 필드가 모두 존재하는지
- 허용하지 않은 필드가 추가되어 있지 않은지
- 각 필드의 실제 타입이 맞는지
- 문자열이 비어 있지 않은지
- 숫자가 허용 범위에 있는지
- 숫자가 유한한지
- 이름이나 식별자의 중복을 허용할지
- 경로가 프로그램이 허용하는 형태인지
- 운영체제 API로 전달할 문자열에 NUL 문자(`"\0"`)가 없는지

### 필수 필드와 추가 필드 검사

객체가 정확히 `category`, `amount` 두 필드만 가져야 한다면 다음처럼 검사할 수 있습니다.

```python
required = {"category", "amount"}
actual = set(obj)

missing = required - actual
extra = actual - required

if missing:
    raise DataReportError(
        f"필수 필드가 없습니다: {', '.join(sorted(missing))}"
    )

if extra:
    raise DataReportError(
        f"허용하지 않은 필드가 있습니다: {', '.join(sorted(extra))}"
    )
```

단순히 두 집합이 같은지만 검사할 수도 있지만, 누락 필드와 추가 필드를 구분하면 사용자가 오류 원인을 이해하기 쉽습니다.

### `bool`과 숫자 타입 주의하기

Python에서는 `bool`이 `int`의 하위 타입입니다.

```python
isinstance(True, int)
# True
```

따라서 다음 검사는 `True`를 정수로 받아들입니다.

```python
isinstance(value, int)
```

논리값을 숫자로 허용하지 않는 입력이라면 `bool`을 먼저 제외해야 합니다.

```python
if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
    raise ValueError("timeout은 숫자여야 합니다.")
```

JSON의 `true`, `false`가 Python의 `True`, `False`로 변환되므로 JSON 숫자 필드 검증에서도 같은 주의가 필요합니다.

---

## JSON 숫자와 `Decimal`

금액처럼 10진수 표현과 합계의 정확성이 중요한 값은 이진 부동소수점인 `float`보다 `Decimal`이 적합한 경우가 많습니다.

```python
from decimal import Decimal

amount = Decimal("12.50")
```

문자열 `"12.50"`을 직접 `Decimal`로 변환하면 이 값을 `float`로 먼저 근사하지 않습니다.

다음 방식은 피하는 편이 좋습니다.

```python
Decimal(0.1)
```

`0.1`이 먼저 이진 부동소수점 `float`로 만들어지므로 그 근삿값이 `Decimal`에 반영됩니다.

### JSON 숫자를 `Decimal`로 바로 읽기

기본 `json.loads()`는 JSON 정수를 `int`, 소수를 `float`로 변환합니다.

금액을 `float`로 먼저 변환하고 싶지 않다면 파서에 변환 함수를 지정할 수 있습니다.

```python
import json
from decimal import Decimal

raw = json.loads(
    text,
    parse_float=Decimal,
    parse_int=Decimal,
)
```

이렇게 하면 JSON에 숫자로 작성된 값이 `Decimal`로 변환됩니다.

```json
{
  "amount": 12.50
}
```

```python
type(raw["amount"])
# Decimal
```

반면 JSON 문자열 `"12.50"`은 여전히 `str`입니다. 따라서 JSON에서 숫자 타입만 허용해야 한다면 두 경우를 구분할 수 있습니다.

```python
if isinstance(value, bool) or not isinstance(value, Decimal):
    raise DataReportError("amount는 JSON 숫자여야 합니다.")
```

CSV의 모든 필드는 처음에는 문자열이므로 CSV에서는 별도로 `Decimal`로 변환합니다.

```text
CSV 문자열 ─┐
             ├─→ Decimal
JSON 숫자 ──┘
```

이렇게 서로 다른 입력 형식이 프로그램 내부에서는 같은 숫자 타입을 사용하게 만들 수 있습니다.

### `NaN`과 `Infinity`

합계에 사용할 금액은 유한한 값이어야 합니다.

```python
amount.is_finite()
```

를 사용해 확인합니다.

```python
if not amount.is_finite():
    raise DataReportError("amount는 유한한 숫자여야 합니다.")
```

Python의 `json` 모듈은 기본 설정에서 JSON 표준에 없는 `NaN`, `Infinity`, `-Infinity`도 받아들일 수 있습니다. 이런 값을 입력 단계에서 거부하려면 `parse_constant`를 사용할 수 있습니다.

```python
def reject_constant(value: str) -> object:
    raise DataReportError(
        f"허용하지 않는 JSON 숫자입니다: {value}"
    )


raw = json.loads(
    text,
    parse_float=Decimal,
    parse_int=Decimal,
    parse_constant=reject_constant,
)
```

문법 파서의 허용 범위와 프로그램의 입력 규칙이 항상 같지는 않으므로 필요한 제약을 명시적으로 적용합니다.

---

## CSV는 `csv` 모듈로 처리하기

CSV는 단순히 쉼표로 구분된 문자열이 아닙니다. 따옴표 안의 쉼표, 줄바꿈, 이스케이프 규칙을 처리해야 합니다.

예를 들어:

```csv
category,amount
"books, used",12.50
```

를 단순히 `split(",")`하면 `"books, used"` 내부의 쉼표까지 구분자로 처리하게 됩니다.

따라서 CSV 문법 처리는 표준 라이브러리의 `csv` 모듈에 맡깁니다.

```python
import csv

with path.open(
    "r",
    encoding="utf-8",
    newline="",
) as stream:
    for row in csv.DictReader(stream):
        print(row["category"])
```

CSV 파일을 `csv` 모듈로 읽을 때는 일반적으로 `newline=""`을 사용합니다. 그러면 줄바꿈 규칙을 `csv` 모듈이 직접 처리할 수 있습니다.

### 헤더도 입력 계약의 일부입니다

CSV 헤더가 정확히 `category`, `amount` 두 열이어야 한다면 헤더를 검증합니다.

```python
reader = csv.DictReader(stream)

fieldnames = reader.fieldnames or []
required = {"category", "amount"}

if len(fieldnames) != len(set(fieldnames)):
    raise DataReportError("CSV 헤더에 중복된 열 이름이 있습니다.")

actual = set(fieldnames)

missing = required - actual
extra = actual - required

if missing:
    raise DataReportError(
        f"CSV 필수 열이 없습니다: {', '.join(sorted(missing))}"
    )

if extra:
    raise DataReportError(
        f"CSV에 허용하지 않은 열이 있습니다: {', '.join(sorted(extra))}"
    )
```

중복 헤더를 먼저 검사하는 이유는 `set()`만 사용하면 중복 정보가 사라지기 때문입니다.

예를 들어:

```text
category,amount,amount
```

를 집합으로 만들면:

```python
{"category", "amount"}
```

가 되어 중복된 `amount` 열을 놓칠 수 있습니다.

헤더의 **순서까지 입력 계약에 포함되는지**도 정해야 합니다.

열 이름만 중요하다면 집합으로 비교할 수 있습니다.

```python
set(fieldnames) == {"category", "amount"}
```

정확히 `category,amount` 순서만 허용한다면 리스트로 비교합니다.

```python
if fieldnames != ["category", "amount"]:
    raise DataReportError(
        "CSV 헤더는 category,amount 순서여야 합니다."
    )
```

어느 정책이 맞는지는 프로그램의 입력 명세가 결정합니다.

---

## 외부 값을 내부 타입으로 바꾸기

CSV와 JSON은 외부 표현 방식이 다릅니다.

CSV의 모든 필드는 처음에는 문자열입니다.

```python
{
    "category": "books",
    "amount": "12.50",
}
```

JSON에서는 같은 의미의 값이 다음처럼 파싱될 수 있습니다.

```python
{
    "category": "books",
    "amount": Decimal("12.50"),
}
```

이 차이를 계산 코드까지 그대로 전달하면 이후 함수마다 입력 형식과 타입을 반복해서 확인해야 합니다.

대신 입력 경계에서 검증과 변환을 끝냅니다.

```text
CSV 행 또는 JSON 객체를 읽습니다.
→ category와 amount를 검증합니다.
→ Record로 변환합니다.
→ 이후 함수는 Record만 받습니다.
```

내부 타입은 다음처럼 정의할 수 있습니다.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Record:
    category: str
    amount: Decimal
```

`frozen=True`는 생성 후 필드 변경을 막습니다. `slots=True`는 인스턴스가 선언된 필드만 가지도록 합니다.

입력 형식별 함수는 최종적으로 같은 `Record`를 반환하도록 만듭니다.

예를 들어 문자열 필드는 다음처럼 검증할 수 있습니다.

```python
def parse_category(value: object) -> str:
    if not isinstance(value, str):
        raise DataReportError("category는 문자열이어야 합니다.")

    category = value.strip()

    if not category:
        raise DataReportError("category는 비어 있을 수 없습니다.")

    return category
```

CSV의 금액은 문자열에서 `Decimal`로 변환합니다.

```python
from decimal import Decimal, InvalidOperation


def parse_csv_amount(value: object) -> Decimal:
    if not isinstance(value, str):
        raise DataReportError("amount는 문자열이어야 합니다.")

    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise DataReportError(
            "amount는 올바른 숫자여야 합니다."
        ) from error

    if not amount.is_finite():
        raise DataReportError(
            "amount는 유한한 숫자여야 합니다."
        )

    return amount
```

이후 집계 함수는 CSV인지 JSON인지 알 필요가 없습니다.

```python
from collections.abc import Iterable
from decimal import Decimal


def total(records: Iterable[Record]) -> Decimal:
    result = Decimal("0")

    for record in records:
        result += record.amount

    return result
```

이 구조의 핵심은 **외부 데이터의 불확실성을 입력 경계에서 끝내는 것**입니다.

---

## 임시 디렉터리로 테스트 격리하기

파일을 다루는 테스트가 실제 작업 디렉터리에 파일을 만들거나 기존 파일을 덮어쓰면 테스트가 사용자의 환경을 변경할 수 있습니다.

`TemporaryDirectory`를 사용하면 테스트 전용 디렉터리를 만들 수 있습니다.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory() as directory:
    root = Path(directory)
    output = root / "result.json"

    output.write_text(
        '{"ok": true}\n',
        encoding="utf-8",
    )

    assert output.exists()
```

`with` 블록이 끝나면 임시 디렉터리와 그 안의 파일이 정리됩니다.

이 방식은 다음 문제를 줄입니다.

- 사용자의 실제 파일을 변경하는 문제
- 이전 테스트 실행이 남긴 파일 때문에 결과가 달라지는 문제
- 여러 테스트가 같은 파일 이름을 사용해 서로 간섭하는 문제

---

## 결과 파일을 안전하게 교체하기

기존 결과 파일에 직접 덮어쓰면 기록 도중 프로그램이 실패했을 때 파일이 일부만 기록된 상태로 남을 수 있습니다.

예를 들어:

```python
path.write_text(new_report, encoding="utf-8")
```

는 기존 결과를 새 내용으로 바꾸는 과정에서 실패할 수 있습니다. 중요한 결과를 갱신할 때는 기존 완성본을 가능한 한 오래 유지한 뒤 완성된 새 파일로 교체하는 방식을 사용할 수 있습니다.

순서는 다음과 같습니다.

```text
최종 파일과 같은 디렉터리에 임시 파일 생성
→ 임시 파일에 전체 내용 기록
→ flush
→ fsync
→ os.replace로 최종 경로 교체
```

```python
import os
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    descriptor, name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    temporary = Path(name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, path)

    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
```

### 같은 디렉터리에 임시 파일을 만드는 이유

```python
tempfile.mkstemp(dir=path.parent)
```

최종 파일과 같은 디렉터리에 임시 파일을 만들면 일반적으로 같은 파일 시스템에 위치하게 됩니다. `os.replace()`의 원자적 교체 특성은 같은 파일 시스템 안에서 사용할 때 기대할 수 있습니다.

`mkstemp()`는 열린 파일 디스크립터와 파일 이름을 반환합니다.

```python
descriptor, name = tempfile.mkstemp(...)
```

### `flush()`와 `fsync()`의 차이

```python
stream.flush()
os.fsync(stream.fileno())
```

`flush()`는 Python의 사용자 공간 버퍼에 남아 있는 데이터를 운영체제에 전달합니다.

`fsync()`는 운영체제에 해당 파일의 변경 내용을 저장 장치 쪽으로 동기화하도록 요청합니다.

두 호출은 같은 역할이 아닙니다.

### `os.replace()`의 역할

```python
os.replace(temporary, path)
```

`os.replace()`는 대상 파일이 이미 존재해도 새 파일로 교체합니다.

같은 파일 시스템에서 운영체제가 원자적 이름 교체를 지원한다면, 최종 경로를 읽는 다른 프로세스는 보통 다음 둘 중 하나를 보게 됩니다.

```text
교체 전의 완전한 파일
또는
교체 후의 완전한 파일
```

새 파일의 일부만 기록된 중간 상태가 최종 이름으로 노출되는 위험을 줄이는 것이 목적입니다.

다만 이 방식이 모든 장애 상황의 내구성을 자동으로 보장하는 것은 아닙니다.

- 여러 파일을 하나의 트랜잭션으로 묶지 못합니다.
- 다른 프로세스가 동시에 같은 파일을 갱신하는 경쟁 상태를 해결하지 않습니다.
- 파일 시스템과 운영체제에 따라 세부 보장이 다를 수 있습니다.
- 정전과 같은 장애까지 강하게 견디려면 POSIX 환경에서는 교체 후 상위 디렉터리의 동기화까지 고려하는 경우가 있습니다.

따라서 이 패턴은 **단일 결과 파일이 부분적으로 기록되는 문제를 줄이는 방법**으로 이해하는 것이 정확합니다.

`data-report`의 출력은 작은 로컬 보고서이므로 일반 `write_text()`를 사용합니다. 기존 결과를 반드시 보존해야 하는 도구라면 위 방식을 추가할 수 있습니다. `command-checker`는 JSON/JUnit 보고서에 이 방식을 사용합니다.

---

## CLI에서 확인할 요소

명령줄 프로그램의 외부 동작은 다음 다섯 요소로 나누어 확인합니다.

```text
명령줄 인자
stdin
stdout
stderr
종료 상태
```

### 명령줄 인자

프로그램 실행 시 함께 전달하는 값입니다.

```text
data-report sales.csv --format json
```

여기서 `sales.csv`, `--format`, `json`이 명령줄 인자입니다.

### `stdin`

프로그램의 표준 입력입니다. 터미널이나 다른 프로세스의 출력에서 데이터를 받을 때 사용할 수 있습니다.

```text
producer | consumer
```

이 경우 일반적으로 `producer`의 `stdout`이 `consumer`의 `stdin`에 연결됩니다.

### `stdout`

프로그램의 정상 결과를 내보내는 표준 출력 스트림입니다.

```text
books  125.50
games   42.00
```

쉘에서는 파일로 리디렉션할 수 있습니다.

```text
data-report sales.csv > report.txt
```

### `stderr`

오류 메시지와 진단 메시지를 내보내는 표준 오류 스트림입니다.

```text
data-report: amount가 올바른 숫자가 아닙니다.
```

정상 결과와 오류를 분리하면 `stdout`만 다른 프로그램이나 파일로 전달하면서 오류는 터미널에 표시할 수 있습니다.

### 종료 상태

프로그램이 운영체제에 반환하는 정수 값입니다.

일반적으로:

```text
0       성공
0이 아님  실패 또는 특별한 상태
```

어떤 비영(非零) 값을 어떤 오류에 사용할지는 프로그램의 CLI 계약으로 정합니다.

일반적인 규칙은 다음과 같습니다.

- 정상 결과는 `stdout`에 출력합니다.
- 오류와 진단 메시지는 `stderr`에 출력합니다.
- 성공은 종료 상태 `0`으로 나타냅니다.
- 사용법 오류나 입력 오류는 `0`이 아닌 종료 상태로 나타냅니다.

---

## `argparse`로 CLI 인자 정의하기

Python 표준 라이브러리의 `argparse`를 사용하면 위치 인자, 옵션, 기본값, 선택 가능한 값을 선언할 수 있습니다.

```python
import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CSV 또는 JSON을 category별로 집계합니다."
    )

    parser.add_argument(
        "input",
        type=Path,
    )

    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    return parser
```

예를 들어:

```text
data-report sales.csv --format json --output report.json
```

을 파싱하면 다음과 같은 값을 얻을 수 있습니다.

```python
arguments.input
# Path("sales.csv")

arguments.format
# "json"

arguments.output
# Path("report.json")
```

하지만 `argparse`가 값을 변환해 준다고 해서 모든 값이 유효해지는 것은 아닙니다.

```python
parser.add_argument("input", type=Path)
```

는 문자열을 `Path` 객체로 바꿀 뿐 다음 사실까지 확인하지 않습니다.

- 경로가 실제로 존재하는지
- 일반 파일인지
- 읽을 수 있는지
- 허용된 확장자인지
- 파일 내용이 유효한 CSV 또는 JSON인지

이런 검사는 프로그램 로직에서 별도로 수행해야 합니다.

---

## `argparse` 오류와 데이터 오류 구분하기

`argparse`는 다음과 같은 **명령줄 사용법 오류**를 자체적으로 처리합니다.

- 필수 인자 누락
- 알 수 없는 옵션
- `choices`에 없는 값
- `type` 변환 실패

예를 들어:

```text
data-report sales.csv --format xml
```

에서 `xml`이 허용되지 않았다면 `argparse`가 오류 메시지와 사용법을 `stderr`에 출력하고 일반적으로 종료 상태 `2`로 종료합니다.

반면 다음 명령은 CLI 문법 자체는 올바릅니다.

```text
data-report missing.csv
```

하지만 프로그램이 파일을 읽는 단계에서 다음과 같은 오류가 발생할 수 있습니다.

- 파일이 존재하지 않음
- CSV 헤더가 잘못됨
- JSON 필드 타입이 잘못됨
- `amount`가 유효하지 않음

이런 문제는 프로그램의 **입력 데이터 오류**입니다.

사용법 오류와 데이터 오류가 반드시 서로 다른 종료 상태를 가져야 하는 것은 아니지만, 어떤 오류를 어떤 상태로 나타낼지 일관된 정책을 정해야 합니다.

---

## `main()`에서 오류를 사용자 메시지로 바꾸기

입력 함수와 집계 함수가 직접 터미널 메시지를 출력하면 프로그램 로직과 CLI 표현이 섞입니다.

대신 하위 함수는 의미 있는 예외를 발생시키고, 최상위 `main()`에서 사용자 메시지와 종료 상태로 변환합니다.

```python
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)

    try:
        records = load_records(arguments.input)
    except DataReportError as error:
        print(
            f"data-report: {error}",
            file=sys.stderr,
        )
        return 2

    ...
```

구조는 다음과 같습니다.

```text
load_records()
→ 파일 읽기와 데이터 검증
→ 문제가 있으면 DataReportError 발생

main()
→ DataReportError 포착
→ stderr에 사용자 메시지 출력
→ 종료 상태 반환
```

하위 함수는 CLI 출력 형식을 알 필요가 없습니다.

```python
def parse_amount(value: object) -> Decimal:
    ...
    raise DataReportError(
        "amount는 유한한 숫자여야 합니다."
    )
```

`main()`만 사용자에게 어떻게 보여 줄지 결정합니다.

```python
except DataReportError as error:
    print(f"data-report: {error}", file=sys.stderr)
    return 2
```

이렇게 하면 같은 데이터 처리 코드를 테스트나 다른 Python 코드에서도 재사용하기 쉽습니다.

### `main()`의 반환값을 실제 종료 상태로 전달하기

`main()`이 정수를 반환하는 것만으로는 그 값이 자동으로 프로세스 종료 상태가 되지 않습니다.

엔트리 포인트에서 `SystemExit`로 전달합니다.

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

예를 들어 `main()`이 `2`를 반환하면 운영체제에서 종료 상태 `2`로 관찰됩니다.

테스트에서는 프로세스를 실제 종료하지 않고 `main()`을 직접 호출할 수 있습니다.

```python
assert main(["input.csv"]) == 0
```

---

## 파일 읽기 오류를 애플리케이션 오류로 바꾸기

파일을 읽을 때도 여러 종류의 오류가 발생할 수 있습니다.

```python
path.read_text(encoding="utf-8")
```

예를 들면:

- 파일이 없음: `FileNotFoundError`
- 권한 부족: `PermissionError`
- 디렉터리를 파일처럼 읽음: `IsADirectoryError`
- UTF-8로 해석할 수 없음: `UnicodeDecodeError`

사용자에게 일관된 오류 형식을 제공하려면 이런 예외를 애플리케이션 수준의 예외로 바꿀 수 있습니다.

```python
def read_input_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise DataReportError(
            f"입력 파일이 UTF-8 텍스트가 아닙니다: {path}"
        ) from error
    except OSError as error:
        raise DataReportError(
            f"입력 파일을 읽을 수 없습니다: {path}"
        ) from error
```

`from error`를 사용하면 사용자에게는 `DataReportError`를 전달하면서 디버깅 시 원래 원인도 보존할 수 있습니다.

모든 예외를 무조건 하나로 묶을 필요는 없습니다. 어떤 오류를 사용자 입력 오류로 간주할지는 프로그램의 오류 정책에 따라 정합니다.

---

## 프로젝트에 적용하기

### 필수: `data-report`

`data-report`에서는 다음 경계를 명확히 구현합니다.

```text
CLI 인자
→ 입력 파일 선택
→ CSV 또는 JSON 파싱
→ 필드 검증
→ Record 변환
→ 집계
→ text 또는 JSON 출력
```

구체적으로:

- `.csv`와 `.json` 확장자를 구분합니다.
- CSV 헤더와 JSON 필드를 정확히 검사합니다.
- CSV의 중복 헤더를 허용할지 명확히 정합니다.
- `category`가 문자열인지 검사합니다.
- `category`의 앞뒤 공백을 제거합니다.
- 공백 제거 후 빈 문자열이면 거부합니다.
- `amount`를 유한한 `Decimal`로 변환합니다.
- CSV와 JSON 모두 최종적으로 같은 `Record` 타입을 만듭니다.
- `Record`를 집계 함수에 전달합니다.
- `--format`으로 출력 형식을 선택합니다.
- `--output`이 있으면 파일에 기록하고, 없으면 정상 결과를 `stdout`에 출력합니다.
- 입력 오류는 `stderr`와 비영(非零) 종료 상태로 나타냅니다.

### 선택: `command-checker`

`command-checker`에서는 같은 원칙을 조금 더 넓게 적용합니다.

- JSON 사례 파일의 필드를 검사합니다.
- 사례 파일 안의 상대 `cwd`를 어떤 디렉터리 기준으로 해석할지 정합니다.
- 환경 변수의 키와 값이 문자열인지 확인합니다.
- 같은 `Result` 목록으로 JSON과 JUnit 보고서를 만듭니다.
- 중요한 보고서는 임시 파일을 완성한 뒤 최종 파일로 교체합니다.

---

## 전체 흐름 정리

외부 입력을 다루는 프로그램은 다음 구조로 생각하면 이해하기 쉽습니다.

```text
외부 세계
  │
  ├─ 경로
  ├─ 파일 bytes
  ├─ CSV/JSON
  └─ CLI 인자
  │
  ▼
입력 경계
  │
  ├─ 상대 경로 기준 결정
  ├─ 인코딩 적용
  ├─ 문법 파싱
  ├─ 필드와 값 검증
  └─ 내부 타입으로 변환
  │
  ▼
프로그램 내부
  │
  └─ Record 같은 검증된 타입만 사용
  │
  ▼
출력 경계
  │
  ├─ stdout 또는 파일
  ├─ stderr
  └─ 종료 상태
```

핵심은 **외부 데이터의 불확실성을 프로그램 내부 전체로 퍼뜨리지 않는 것**입니다.

파일 형식과 CLI에서 들어온 값은 입력 경계에서 검증하고 변환합니다. 이후 계산 코드에서는 이미 검증된 내부 타입만 사용하도록 만들면 함수의 책임이 단순해지고 오류가 발생하는 위치도 명확해집니다.

---

## 완료 기준

다음 항목을 설명하고 구현할 수 있으면 이 문서의 목표를 달성한 것입니다.

- 상대 경로를 어떤 디렉터리 기준으로 해석하는지 명시할 수 있습니다.
- `Path.cwd()`와 `Path(__file__).resolve().parent`의 차이를 설명할 수 있습니다.
- 텍스트와 바이트를 구분하고 텍스트 인코딩을 명시할 수 있습니다.
- JSON 문법 파싱과 애플리케이션 수준의 필드 검증을 구분할 수 있습니다.
- `bool`이 `int`의 하위 타입이라는 점을 고려해 숫자 필드를 검증할 수 있습니다.
- 금액을 `Decimal`로 변환하고 유한성을 검사할 수 있습니다.
- JSON의 비표준 `NaN`, `Infinity` 처리 정책을 명시할 수 있습니다.
- CSV를 `csv` 모듈로 읽고 헤더와 중복 열 이름을 검사할 수 있습니다.
- CSV와 JSON을 같은 내부 타입으로 변환할 수 있습니다.
- 임시 디렉터리를 사용해 파일 테스트를 실제 작업 파일과 격리할 수 있습니다.
- 임시 파일과 `os.replace()`를 사용한 안전한 단일 파일 교체의 목적과 한계를 설명할 수 있습니다.
- CLI의 인자, `stdin`, `stdout`, `stderr`, 종료 상태를 구분할 수 있습니다.
- `argparse`의 사용법 검증과 프로그램 데이터 검증이 다른 단계임을 설명할 수 있습니다.
- 하위 함수의 예외를 `main()`에서 사용자 메시지와 종료 상태로 변환할 수 있습니다.
- `raise SystemExit(main())`이 `main()`의 반환값을 프로세스 종료 상태로 전달한다는 점을 이해합니다.

다음 필수 문서는 [재현 가능한 테스트](../03-quality/01-testing.md)입니다. 외부 프로세스를 다뤄야 한다면 [외부 프로세스와 수명 관리](02-subprocess-and-process-lifecycle.md)로 진행합니다.
