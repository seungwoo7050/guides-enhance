# data-report

`data-report`는 CSV 또는 JSON 파일을 읽고 `category`별 합계와 전체 합계를 출력하는 Python CLI 프로그램입니다.

프로젝트의 핵심 흐름은 다음과 같습니다.

```text
외부 파일
→ 입력 형식별 파싱과 검증
→ 공통 Record
→ 집계
→ 공통 Report
→ 텍스트 또는 JSON 렌더링
→ stdout 또는 파일
```

CSV와 JSON을 서로 다른 방식으로 읽더라도 검증이 끝난 뒤에는 같은 `Record` 타입을 사용합니다. 따라서 집계와 출력 코드는 원래 입력 형식이 무엇이었는지 알 필요가 없습니다.

작은 프로젝트 안에서 다음 작업을 한 번에 확인할 수 있도록 구성했습니다.

- 패키지와 모듈 실행
- 불변 `Record`와 `Report` 정의
- CSV/JSON 입력 검증
- `Decimal` 기반 합산
- 텍스트/JSON 출력
- CLI 인자와 파일 저장
- 프로젝트 내부 테스트
- 콘솔 스크립트 설치

`subprocess`, 동시성, 네트워크, 데이터베이스는 범위에서 제외합니다.

## 요구 환경

- Python 3.12 이상
- 실행 시 필요한 외부 패키지 없음

표준 라이브러리만으로 실행되므로 런타임 의존성을 별도로 설치할 필요가 없습니다.

## 프로젝트 구성

```text
data-report/
├── .gitignore
├── README.md
├── pyproject.toml
├── data_report/
│   ├── __init__.py
│   ├── __main__.py
│   ├── aggregation.py
│   ├── cli.py
│   ├── loaders.py
│   ├── model.py
│   ├── py.typed
│   └── rendering.py
├── examples/
│   └── sales.csv
└── tests/
    └── test_data_report.py
```

| 파일 | 수행하는 작업 |
|---|---|
| `model.py` | 검증된 `Record`, `category`별 합계, 전체 `Report` 정의 |
| `loaders.py` | CSV/JSON을 읽고 필드를 검사한 뒤 `Record`로 변환 |
| `aggregation.py` | `Record`를 `category`별로 합산하고 이름순으로 정렬 |
| `rendering.py` | 같은 `Report`를 텍스트 또는 JSON 문자열로 변환 |
| `cli.py` | 인자를 읽고 입력·출력 파일을 처리하며 종료 상태 반환 |
| `tests/test_data_report.py` | 입력 형식, 합산, 출력, CLI 오류 처리 검증 |

각 모듈은 서로 다른 책임을 가집니다.

```text
loaders.py
→ 외부 데이터를 신뢰 가능한 Record로 바꿈

aggregation.py
→ Record만 사용해 계산

rendering.py
→ Report만 사용해 문자열 생성

cli.py
→ 파일과 터미널을 연결
```

이 구조 덕분에 집계와 렌더링을 실제 파일 없이 단위 테스트할 수 있습니다.

## 입력 형식

### CSV

CSV 헤더는 정확히 `category,amount`여야 합니다.

```csv
category,amount
books,12.50
games,30
books,7.50
```

헤더 이름이 다르거나 필요한 필드가 빠졌거나 예상하지 않은 필드가 추가된 입력을 묵시적으로 받아들이지 않습니다.

검증이 엄격해야 잘못된 입력을 조용히 다른 의미로 해석하는 일을 피할 수 있습니다.

### JSON

최상위 값은 객체 배열이어야 하며, 각 객체는 `category`와 `amount` 필드를 가져야 합니다.

```json
[
  {"category": "books", "amount": "12.50"},
  {"category": "games", "amount": 30},
  {"category": "books", "amount": "7.50"}
]
```

각 JSON 객체를 곧바로 내부 데이터로 사용하지 않고 필드와 값을 검사한 뒤 `Record`를 만듭니다.

## 입력 검증 규칙

입력값은 다음 규칙으로 검사합니다.

- `category`는 문자열이어야 합니다.
- `category`의 앞뒤 공백을 제거한 결과는 비어 있으면 안 됩니다.
- `amount`는 `Decimal`로 변환할 수 있어야 합니다.
- `NaN`과 `Infinity`처럼 유한하지 않은 값은 거부합니다.
- 누락된 필드와 예상하지 않은 필드를 모두 거부합니다.
- 입력에는 레코드가 하나 이상 있어야 합니다.

검증은 “파싱에 성공했는가”보다 더 넓은 개념입니다.

예를 들어 다음 JSON은 문법적으로 올바르지만 프로그램 입력으로는 잘못될 수 있습니다.

```json
[
  {"category": "", "amount": "12.50"}
]
```

문법은 올바르지만 공백 제거 뒤 `category`가 비어 있으므로 거부합니다.

또한 다음 값도 JSON 숫자 또는 문자열로 표현될 수 있지만 금액으로 사용할 수 없다면 거부해야 합니다.

```text
NaN
Infinity
-Infinity
```

집계를 시작하기 전에 모든 외부 데이터를 검증된 `Record`로 바꾸는 것이 핵심입니다.

## 공통 `Record`로 변환하기

CSV와 JSON은 문법이 다르지만 같은 도메인 의미를 표현합니다.

```text
CSV row ──┐
          ├── validation → Record
JSON obj ─┘
```

따라서 집계 함수는 다음처럼 입력 형식을 구분하지 않습니다.

```text
Iterable[Record]
→ Report
```

이 구조는 “CSV에서만 합산 규칙이 다르게 동작하는 버그”처럼 입력 형식과 핵심 계산이 불필요하게 결합되는 일을 줄입니다.

## 금액과 `Decimal`

금액은 `float`가 아니라 `Decimal`로 처리합니다.

이유는 10진수 금액을 이진 부동소수점으로 표현할 때 일부 값이 정확히 표현되지 않을 수 있기 때문입니다.

예를 들어 일반적인 이진 부동소수점에서는 다음과 같은 표현 오차가 나타날 수 있습니다.

```text
0.1 + 0.2
```

`data-report`에서는 입력 금액을 `Decimal`로 변환한 뒤 합산하므로 10진수 값의 의미를 그대로 유지합니다.

JSON 숫자도 바로 `float` 연산에 사용하지 않고 **원래 숫자의 10진 표현을 보존할 수 있는 문자열 형태를 거쳐 `Decimal`로 변환하는 방식**으로 처리합니다.

중요한 것은 “JSON 숫자는 항상 문자열이다”가 아니라, `float`로 먼저 바뀐 값에서 다시 `Decimal`을 만들지 않는 것입니다.

## 실행

소스 트리에서 바로 실행할 수 있습니다.

```sh
python -m data_report examples/sales.csv
```

기본 출력 형식은 텍스트입니다.

```text
category  count  total
books         2  20.00
games         2  45.25
----------------------
TOTAL         4  65.25
```

이 출력은 구조를 이해하기 위한 예시입니다. 실제 결과는 입력 파일의 레코드와 합계에 따라 결정됩니다.

JSON으로 출력하려면 `--format json`을 사용합니다.

```sh
python -m data_report examples/sales.csv --format json
```

파일에 저장하려면 `--output`을 지정합니다.

```sh
python -m data_report \
  examples/sales.csv \
  --format json \
  --output report.json
```

`--output`이 없으면 정상 보고서를 `stdout`에 출력합니다.

`--output`이 있으면 렌더링된 보고서를 지정한 파일에 저장합니다. 정상 보고서와 오류 메시지는 서로 다른 채널을 사용합니다.

```text
정상 보고서 → stdout 또는 --output 파일
오류 메시지 → stderr
```

## 설치

프로젝트 디렉터리에서 설치합니다.

```sh
python -m pip install .
data-report examples/sales.csv
```

설치된 `data-report`와 `python -m data_report`는 모두 `data_report.cli.main()`을 호출합니다.

```text
python -m data_report
        │
        └── data_report.__main__
                └── cli.main()

data-report
        │
        └── console script
                └── cli.main()
```

두 진입점이 같은 함수를 사용하므로 인자 파싱, 출력, 종료 상태를 한 곳에서 유지할 수 있습니다.

## 종료 상태

| 종료 상태 | 의미 |
|---:|---|
| `0` | 입력을 읽고 보고서를 정상적으로 출력하거나 저장함 |
| `2` | 확장자, 파일 읽기, 입력 필드, 숫자 변환 또는 파일 쓰기 오류 |

종료 상태는 CLI를 다른 프로그램이나 셸 스크립트에서 사용할 때 성공과 실패를 구분하는 외부 계약입니다.

오류는 `stderr`에 출력합니다.

정상 보고서는 `--output`을 지정하지 않았을 때 `stdout`에 출력합니다.

예를 들어 입력 파일이 잘못되었다면 정상 결과처럼 빈 보고서를 출력하고 종료 상태 0을 반환하지 않습니다.

```text
입력 오류
→ stderr에 설명
→ 종료 상태 2
```

## 테스트

표준 라이브러리 `unittest`를 사용합니다.

```sh
python -m unittest discover -s tests -v
```

테스트는 다음 동작을 확인합니다.

- CSV와 JSON이 같은 `Report`를 만듭니다.
- 예상하지 않은 필드를 거부합니다.
- 유한하지 않은 `amount`를 거부합니다.
- `Decimal` 합산 결과에 이진 부동소수점 오차가 남지 않습니다.
- `category` 출력 순서가 입력 순서에 따라 바뀌지 않습니다.
- 텍스트와 JSON이 같은 `Report`를 사용합니다.
- `--output`이 JSON 파일을 생성합니다.
- 지원하지 않는 확장자를 종료 상태 2로 처리합니다.

이 테스트들은 단순히 함수가 실행되는지만 확인하지 않습니다. 특정 잘못된 구현이 통과하지 못하도록 설계합니다.

예를 들어 `category` 정렬 테스트는 입력을 이미 정렬된 상태로만 제공해서는 부족합니다.

```text
입력 순서:
games
books

기대 출력 순서:
books
games
```

이렇게 해야 입력 순서를 그대로 유지하는 잘못된 구현을 잡을 수 있습니다.

## 주요 구현 선택

### 입력을 `Record`로 먼저 변환합니다

CSV 행과 JSON 객체를 그대로 집계 함수에 넘기지 않습니다.

입력 함수가 필드를 검사하고 `Record`로 변환한 뒤에만 집계를 시작합니다.

```text
CSV 행 또는 JSON 객체를 읽습니다.
→ 필드 집합을 검사합니다.
→ category를 검사합니다.
→ amount를 Decimal로 변환하고 유한성을 검사합니다.
→ Record로 변환합니다.
→ category별로 합산합니다.
```

이 구조에서는 집계 함수가 잘못된 외부 입력을 직접 방어할 필요가 없습니다. 집계 함수의 입력 계약은 “이미 검증된 `Record`”입니다.

### 금액은 `Decimal`로 합산합니다

`0.1 + 0.2` 같은 10진수 값을 이진 부동소수점 `float`로 합산할 때 생길 수 있는 표현 오차를 피합니다.

`Decimal`을 사용한다는 것만으로 모든 금액 규칙이 자동으로 결정되는 것은 아닙니다. 이 프로젝트에서는 입력의 10진 표현을 보존해 합산하는 것이 핵심입니다.

`NaN`이나 `Infinity`처럼 산술 타입으로 표현할 수 있어도 실제 금액 합계에 적합하지 않은 값은 별도로 거부합니다.

### 결과 순서를 명시적으로 정합니다

`category`별 합계를 만든 뒤 이름순으로 정렬합니다.

동일한 데이터셋이라면 입력 파일의 레코드 순서가 달라도 같은 결과를 만듭니다.

```text
입력 A:
books
games
books

입력 B:
games
books
books

두 입력의 category별 합계가 같다면
→ 출력 category 순서도 같음
```

이런 결정적인 출력은 테스트와 자동 비교를 단순하게 만듭니다.

### 출력 함수는 파일을 직접 쓰지 않습니다

`render_text()`와 `render_json()`은 `Report`를 문자열로 바꿉니다.

```text
Report → str
```

실제 `stdout` 출력과 파일 쓰기는 `cli.main()`에서만 수행합니다.

이렇게 하면 렌더링 규칙을 실제 파일 시스템 없이 직접 테스트할 수 있습니다.

```text
render_text(report)
→ 기대 문자열과 비교
```

파일 쓰기 실패 같은 오류는 CLI 통합 테스트에서 별도로 확인합니다.

## 불변 값 객체

`Record`와 `Report`처럼 여러 모듈 사이에서 전달되는 값은 불변 데이터로 다루는 것이 좋습니다.

예를 들어 입력 로더가 만든 `Record`를 집계 함수가 실수로 수정하면 이후 다른 코드가 같은 객체를 사용할 때 예상하지 못한 상태가 생길 수 있습니다.

불변 값 객체는 다음 흐름을 명확하게 만듭니다.

```text
loader가 Record 생성
→ aggregation이 읽기만 함
→ rendering이 Report를 읽기만 함
```

값을 변경해야 할 때는 기존 객체를 수정하기보다 새 값을 만들어 반환합니다.

## 패키징과 타입 정보

패키지에는 `py.typed`가 포함되어 있습니다.

이 파일은 설치된 패키지가 타입 힌트를 제공한다는 사실을 타입 검사 도구가 인식할 수 있게 하는 표식입니다.

소스 트리에서만 `py.typed`가 존재하고 wheel에는 빠진다면 설치된 사용자에게 타입 정보가 제대로 전달되지 않을 수 있으므로 패키지 파일 목록에도 포함되어야 합니다.

소스 트리에서 실행되는 것만 확인하지 말고 wheel 또는 설치된 패키지에서도 다음을 확인해야 합니다.

```text
data_report 모듈 포함
py.typed 포함
console script 연결
저장소 밖에서 import 및 실행 가능
```

## Implementation Order

아래 순서는 파일 배치나 실행 순서가 아니라 프로젝트를 처음부터 구현할 때의 구성 순서입니다. 한 번호는 소스 코드에서 한 번만 사용합니다.

| Order | Responsibility | Primary anchor |
|---:|---|---|
| `1` | Package metadata and console script | `pyproject.toml` |
| `1-1` | Module entry-point delegation | `data_report/__main__.py` |
| `2` | Immutable record and report values | `data_report/model.py` |
| `3` | CSV/JSON loading and validation | `data_report/loaders.py` |
| `4` | Deterministic category aggregation | `data_report/aggregation.py` |
| `5` | Text and JSON rendering | `data_report/rendering.py` |
| `6` | CLI arguments, file output, and exit status | `data_report/cli.py` |
| `7` | Project behavior verification | `tests/test_data_report.py` |

이 순서는 외부 입출력과 CLI를 먼저 복잡하게 만들기보다, 내부 데이터 모델과 계산 규칙을 먼저 고정하고 그 위에 로더, 렌더링, CLI를 연결하도록 구성되어 있습니다.

## 범위와 제한

- 작은 로컬 데이터셋을 한 번에 읽어 처리합니다.
- 중첩된 JSON 스키마는 지원하지 않습니다.
- 스프레드시트 형식은 지원하지 않습니다.
- 스트리밍 입력은 구현하지 않습니다.
- 데이터베이스와 네트워크에 접근하지 않습니다.
- 출력 파일을 원자적으로 교체하지 않습니다.

마지막 제한은 `command-checker`의 보고서 저장 방식과 다릅니다.

`data-report`는 현재 최종 출력 파일에 직접 쓰는 범위까지만 구현합니다. 기존 파일을 반드시 보존해야 하거나 소비자가 부분 파일을 읽어서는 안 되는 요구가 생기면 다음 전략을 추가해야 합니다.

```text
같은 디렉터리에 임시 파일 생성
→ 전체 내용 기록
→ 파일 닫기
→ os.replace()로 최종 경로 교체
```

이 기능은 현재 프로젝트의 필수 범위에는 포함하지 않습니다.