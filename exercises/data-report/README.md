# data-report

`data-report`는 CSV 또는 JSON 파일을 읽고 `category`별 합계와 전체 합계를 출력하는 Python CLI 프로그램입니다.

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

## 입력 형식

### CSV

CSV 헤더는 정확히 `category,amount`여야 합니다.

```csv
category,amount
books,12.50
games,30
books,7.50
```

### JSON

최상위 값은 객체 배열이어야 하며, 각 객체는 `category`와 `amount` 필드를 가져야 합니다.

```json
[
  {"category": "books", "amount": "12.50"},
  {"category": "games", "amount": 30},
  {"category": "books", "amount": "7.50"}
]
```

입력값은 다음 규칙으로 검사합니다.

- `category`는 문자열이어야 합니다.
- `category`의 앞뒤 공백을 제거한 결과는 비어 있으면 안 됩니다.
- `amount`는 `Decimal`로 변환할 수 있어야 합니다.
- `NaN`과 `Infinity`처럼 유한하지 않은 값은 거부합니다.
- 누락된 필드와 예상하지 않은 필드를 모두 거부합니다.
- 입력에는 레코드가 하나 이상 있어야 합니다.

CSV와 JSON은 모두 같은 `Record`로 변환됩니다. 따라서 집계 코드는 원래 입력 형식을 구분할 필요가 없습니다.

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

## 설치

프로젝트 디렉터리에서 설치합니다.

```sh
python -m pip install .
data-report examples/sales.csv
```

설치된 `data-report`와 `python -m data_report`는 모두 `data_report.cli.main()`을 호출합니다.

## 종료 상태

| 종료 상태 | 의미 |
|---:|---|
| `0` | 입력을 읽고 보고서를 정상적으로 출력하거나 저장함 |
| `2` | 확장자, 파일 읽기, 입력 필드, 숫자 변환 또는 파일 쓰기 오류 |

오류는 `stderr`에 출력합니다. 정상 보고서는 `--output`을 지정하지 않았을 때 `stdout`에 출력합니다.

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

## 주요 구현 선택

### 입력을 `Record`로 먼저 변환합니다

CSV 행과 JSON 객체를 그대로 집계 함수에 넘기지 않습니다. 입력 함수가 필드를 검사하고 `Record`로 변환한 뒤에만 집계를 시작합니다.

```text
CSV 행 또는 JSON 객체를 읽습니다.
→ category와 amount를 검사합니다.
→ Record로 변환합니다.
→ category별로 합산합니다.
```

### 금액은 `Decimal`로 합산합니다

`0.1 + 0.2` 같은 10진수 값을 이진 부동소수점 `float`로 합산할 때 생길 수 있는 표현 오차를 피합니다. JSON 숫자도 문자열 형태로 받은 뒤 `Decimal`로 변환합니다.

### 결과 순서를 명시적으로 정합니다

`category`별 합계를 만든 뒤 이름순으로 정렬합니다. 동일한 데이터셋이라면 입력 파일의 레코드 순서가 달라도 같은 결과를 만듭니다.

### 출력 함수는 파일을 직접 쓰지 않습니다

`render_text()`와 `render_json()`은 `Report`를 문자열로 바꿉니다. 실제 `stdout` 출력과 파일 쓰기는 `cli.main()`에서만 수행합니다.

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

## 범위와 제한

- 작은 로컬 데이터셋을 한 번에 읽어 처리합니다.
- 중첩된 JSON 스키마는 지원하지 않습니다.
- 스프레드시트 형식은 지원하지 않습니다.
- 스트리밍 입력은 구현하지 않습니다.
- 데이터베이스와 네트워크에 접근하지 않습니다.
- 출력 파일을 원자적으로 교체하지 않습니다. 기존 파일을 반드시 보존해야 한다면 임시 파일과 `os.replace()`를 추가해야 합니다.
