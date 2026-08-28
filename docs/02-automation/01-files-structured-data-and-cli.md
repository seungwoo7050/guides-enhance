# 파일, 구조화된 데이터와 CLI

## 학습 목표

이 문서에서는 파일과 외부 입력을 읽고 검증해 프로그램 내부에서 사용할 값으로 바꾸는 방법을 다룹니다.

- `pathlib`로 경로를 다룹니다.
- 텍스트와 바이트를 구분하고 인코딩을 명시합니다.
- CSV와 JSON을 표준 라이브러리로 읽습니다.
- 파싱한 값을 필드별로 검증합니다.
- `argparse`로 CLI 인자를 받습니다.
- 정상 출력, 오류 출력, 종료 상태를 구분합니다.
- 파일을 쓰는 도중 실패했을 때 기존 결과를 보존하는 방법을 이해합니다.

필수 프로젝트인 [`data-report`](../../exercises/data-report/README.md)는 이 문서의 내용을 직접 적용합니다.

## 선행 개념

- `Path` 객체를 만들 수 있어야 합니다.
- 컨텍스트 관리자로 파일을 열고 닫을 수 있어야 합니다.
- 예외 유형을 구분할 수 있어야 합니다.
- JSON 문법 검사와 프로그램이 요구하는 필드 검사가 다른 작업임을 이해해야 합니다.

## `pathlib`로 경로 의미 보존하기

```python
from pathlib import Path

root = Path(__file__).resolve().parent
config = root / "examples" / "sales.csv"
```

경로를 문자열 덧셈으로 조립하지 않습니다. `Path`를 사용하면 운영체제별 경로 구분자를 직접 처리하지 않아도 되고, 일반 문자열과 파일 경로를 구분할 수 있습니다.

```python
path = Path("notes.txt")
path.write_text("hello\n", encoding="utf-8")
content = path.read_text(encoding="utf-8")
```

`read_text()`와 `write_text()`는 작은 설정 파일이나 보고서를 처리할 때 편리합니다. 큰 파일은 한 번에 읽지 말고 필요한 단위로 처리합니다.

```python
from collections.abc import Iterator


def error_lines(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if "ERROR" in line:
                yield line.rstrip("\n")
```

## 상대 경로의 기준 정하기

상대 경로는 무엇을 기준으로 해석하는지 명확해야 합니다.

- 사용자가 CLI로 전달한 입력 파일: 보통 현재 작업 디렉터리 기준
- 패키지와 함께 배포한 기본 자료: 보통 `__file__`이 있는 디렉터리 기준
- 설정 파일 안에 기록한 상대 경로: 설정 파일이 있는 디렉터리 또는 명시한 기준 디렉터리 기준

`Path.cwd()`와 `Path(__file__).resolve().parent`는 같은 값이라고 가정하면 안 됩니다.

## 텍스트와 바이트 구분하기

파일이나 프로세스에서 데이터를 읽을 때 `bytes`와 `str` 중 어떤 형태로 처리할지 정해야 합니다.

```python
content = path.read_text(encoding="utf-8")
```

텍스트를 읽을 때 인코딩을 생략해 운영체제 기본값에 의존하지 않습니다. 잘못된 바이트를 오류로 처리할지 대체 문자로 바꿀지도 입력 규칙으로 정합니다.

이진 형식을 다룬다면 `read_bytes()` 또는 이진 모드를 사용합니다.

```python
payload = path.read_bytes()
```

텍스트를 처리하는 프로그램에서 `bytes`와 `str` 변환을 여러 모듈에 흩어 놓지 말고 파일이나 프로세스를 읽는 지점에서 한 번 수행합니다.

## JSON은 파싱한 뒤 다시 검증하기

```python
import json

raw: object = json.loads(path.read_text(encoding="utf-8"))
```

JSON 문법이 올바르다는 사실은 프로그램이 요구하는 값까지 올바르다는 뜻이 아닙니다.

```python
def require_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DataReportError("최상위 값은 객체여야 합니다.")
    return value
```

외부 JSON에서는 보통 다음 항목을 확인합니다.

- 최상위 값이 배열인지 객체인지
- 필수 필드와 허용하지 않은 필드
- 각 필드의 실제 타입
- 숫자의 범위와 유한성
- 중복 이름
- 경로가 허용된 형태인지
- 운영체제 API가 거부하는 NUL 문자

Python에서 `bool`은 `int`의 하위 타입입니다. 정수나 실수를 엄격하게 받아야 하는 필드에서는 `bool`을 따로 제외해야 합니다.

```python
if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
    raise ValueError("timeout은 숫자여야 합니다.")
```

## JSON 숫자와 `Decimal`

금액처럼 10진수 표현을 그대로 보존해야 하는 값은 이진 부동소수점으로 합산하지 않는 편이 좋습니다.

```python
from decimal import Decimal

amount = Decimal("12.50")
```

JSON 파서가 실수를 `float`로 먼저 만들지 않도록 `parse_float=str`, `parse_int=str`를 사용할 수 있습니다.

```python
raw = json.loads(text, parse_float=str, parse_int=str)
```

이후 필드 검증 함수에서 `Decimal`로 변환하면 CSV와 JSON이 같은 숫자 타입을 사용합니다.

`NaN`과 `Infinity`는 합계로 사용할 수 없으므로 `is_finite()`도 확인합니다.

## CSV는 `csv` 모듈로 처리하기

```python
import csv

with path.open("r", encoding="utf-8", newline="") as stream:
    for row in csv.DictReader(stream):
        print(row["category"])
```

CSV 한 줄을 쉼표로 직접 `split()`하면 따옴표 안의 쉼표, 여러 줄 필드, 이스케이프 규칙을 올바르게 처리할 수 없습니다. CSV 문법 처리는 표준 라이브러리에 맡깁니다.

헤더도 입력 규칙의 일부입니다.

```python
required = {"category", "amount"}
if set(reader.fieldnames or ()) != required:
    raise DataReportError("CSV 헤더는 category,amount여야 합니다.")
```

필드가 누락되었는지, 예상하지 않은 필드가 있는지 각각 검사해야 오류 원인을 알기 쉽습니다.

## 외부 값을 내부 타입으로 바꾸기

CSV와 JSON 입력 함수가 서로 다른 `dict` 형식을 반환한 채 계산 코드로 넘기면 이후 함수마다 입력 형식을 다시 확인해야 합니다.

```text
CSV 행 또는 JSON 객체를 읽습니다.
→ category와 amount를 검증합니다.
→ Record로 변환합니다.
→ 이후 함수는 Record만 받습니다.
```

```python
@dataclass(frozen=True, slots=True)
class Record:
    category: str
    amount: Decimal
```

입력 형식의 차이는 입력 함수에서 끝내고 집계 코드는 `Record`만 처리하도록 만듭니다.

## 임시 디렉터리로 테스트 격리하기

```python
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory() as directory:
    root = Path(directory)
    output = root / "result.json"
    ...
```

테스트나 중간 작업은 사용자의 실제 파일을 바꾸지 않도록 임시 디렉터리에서 수행합니다. 컨텍스트가 끝나면 임시 디렉터리와 내부 파일이 정리됩니다.

## 결과 파일을 안전하게 교체하기

기존 보고서 파일에 직접 덮어쓰면 기록 도중 실패했을 때 파일이 일부만 남을 수 있습니다. 중요한 결과를 갱신할 때는 다음 순서를 사용할 수 있습니다.

```text
최종 파일과 같은 디렉터리에 임시 파일을 만듭니다.
→ 전체 내용을 기록합니다.
→ flush와 fsync를 수행합니다.
→ os.replace로 최종 경로를 교체합니다.
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

`os.replace()`는 같은 파일 시스템 안에서 완성된 임시 파일을 최종 이름으로 바꿉니다. 중간 내용이 보이는 문제를 줄이지만, 여러 파일을 하나의 트랜잭션으로 묶거나 모든 장애 상황의 내구성을 자동으로 보장하지는 않습니다.

`data-report`의 출력은 작은 로컬 보고서이므로 일반 `write_text()`를 사용합니다. 기존 결과를 반드시 보존해야 하는 도구라면 위 방식을 추가할 수 있습니다. `command-checker`는 JSON/JUnit 보고서에 이 방식을 사용합니다.

## CLI에서 확인할 요소

명령줄 프로그램의 외부 동작은 다음 다섯 요소로 나누어 확인합니다.

```text
명령줄 인자
stdin
stdout
stderr
종료 상태
```

일반적인 규칙은 다음과 같습니다.

- 정상 결과는 `stdout`에 출력합니다.
- 오류와 진단 메시지는 `stderr`에 출력합니다.
- 성공은 종료 상태 0으로 나타냅니다.
- 사용법 오류나 입력 오류는 별도의 0이 아닌 종료 상태로 나타냅니다.

```python
import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CSV 또는 JSON을 category별로 집계합니다."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path)
    return parser
```

`argparse`가 값을 변환해 준다고 해서 모든 값이 유효해지는 것은 아닙니다. 예를 들어 `Path`로 바뀐 경로가 실제 파일인지, JSON 필드가 허용된 타입인지 별도로 확인해야 합니다.

## `main()`에서 오류를 사용자 메시지로 바꾸기

```python
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        records = load_records(arguments.input)
    except DataReportError as error:
        print(f"data-report: {error}", file=sys.stderr)
        return 2
    ...
```

입력 함수와 집계 함수는 터미널 출력 형식을 알 필요가 없습니다. 하위 함수는 구체적인 예외를 발생시키고, 최상위 `main()`에서 메시지와 종료 상태로 바꿉니다.

## 프로젝트에 적용하기

### 필수: `data-report`

- `.csv`와 `.json` 확장자를 구분합니다.
- CSV 헤더와 JSON 필드를 정확히 검사합니다.
- `category`의 앞뒤 공백을 제거하고 빈 문자열을 거부합니다.
- `amount`를 유한한 `Decimal`로 변환합니다.
- `Record` 튜플을 집계 함수에 전달합니다.
- `--format`과 `--output`을 처리합니다.

### 선택: `command-checker`

- JSON 사례 파일의 필드, 상대 `cwd`, 환경 변수 문자열을 검사합니다.
- 같은 `Result` 목록으로 JSON과 JUnit을 만듭니다.
- 임시 파일을 완성한 뒤 최종 보고서를 교체합니다.

## 완료 기준

- 상대 경로를 어떤 디렉터리 기준으로 해석하는지 명시합니다.
- 외부 JSON을 필드별로 실행 시 검증합니다.
- CSV를 `csv` 모듈로 읽고 헤더를 검사합니다.
- 텍스트 파일의 인코딩을 명시합니다.
- CSV와 JSON을 같은 내부 타입으로 변환합니다.
- CLI의 인자, 표준 입력, 표준 출력, 표준 오류, 종료 상태를 구분합니다.

다음 필수 문서는 [재현 가능한 테스트](../03-quality/01-testing.md)입니다. 외부 프로세스를 다뤄야 한다면 [외부 프로세스와 수명 관리](02-subprocess-and-process-lifecycle.md)로 진행합니다.
