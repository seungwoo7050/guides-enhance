# 프로젝트 구조, 패키징과 타입 검사

## 학습 목표

프로젝트 구조는 파일 수를 늘리기 위한 규칙이 아닙니다. 서로 다른 이유로 바뀌는 코드를 나누고, 어떤 모듈이 어떤 모듈을 사용하는지 드러내기 위한 수단입니다.

이 문서에서는 다음 내용을 다룹니다.

- 단일 파일을 여러 모듈로 나눌 시점
- 순환 `import`를 피하는 의존 방향
- `pyproject.toml`과 콘솔 스크립트
- 타입 힌트와 실행 시 입력 검증의 차이
- 소스 트리가 아니라 설치된 패키지를 확인하는 방법
- 과도한 추상화를 피하는 기준

필수 프로젝트인 [`data-report`](../../exercises/data-report/README.md)를 설치 가능한 패키지로 완성할 때 이 내용을 적용합니다.

## 선행 개념

- 모듈 간 `import`를 따라갈 수 있어야 합니다.
- 공개 함수와 내부 보조 함수를 구분할 수 있어야 합니다.
- 타입 힌트와 실행 시 검증의 차이를 이해해야 합니다.

## 프로그램 크기에 맞는 구성 선택하기

한 번만 사용하는 30줄짜리 변환 도구라면 단일 파일로 충분할 수 있습니다.

```text
normalize_log.py
```

다음 작업이 서로 독립적으로 바뀌기 시작하면 모듈 분리를 검토합니다.

```text
CLI 인자 파싱
외부 입력 검증
핵심 계산
파일·프로세스 입출력
보고서 직렬화
```

작은 패키지는 다음처럼 구성할 수 있습니다.

```text
project/
├── pyproject.toml
├── app/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   └── core.py
└── tests/
    └── test_core.py
```

`src/` 배치를 사용하면 설치하지 않은 저장소 루트가 우연히 `sys.path`에 포함되어 잘못된 `import`가 성공하는 일을 줄일 수 있습니다.

```text
project/
├── pyproject.toml
├── src/
│   └── app/
└── tests/
```

그러나 모든 작은 프로젝트에 `src/` 배치를 강제할 필요는 없습니다. 중요한 것은 설치된 상태에서도 같은 `import`와 진입점이 동작하는지 확인하는 것입니다.

## 모듈 의존 방향 정하기

공통 데이터 타입을 정의한 모듈이 파일 입출력이나 CLI 모듈을 `import`하면 순환 의존이 생기기 쉽습니다.

`data-report`의 의존 방향은 다음과 같습니다.

```text
model ← loaders
model ← aggregation
model ← rendering
cli → loaders, aggregation, rendering
```

`model.py`는 `argparse`, 파일 경로, 출력 문구를 알지 않습니다. `aggregation.py`는 CSV와 JSON 중 어떤 형식에서 `Record`가 왔는지 알지 않습니다. `rendering.py`는 파일을 직접 쓰지 않습니다.

다음 질문으로 모듈을 나눌 수 있습니다.

- 이 코드는 무엇을 입력으로 받습니까?
- 파일이나 터미널에 접근합니까?
- 다른 출력 형식을 추가할 때 함께 바뀝니까?
- 테스트에서 실제 파일 없이 실행할 수 있습니까?

## `pyproject.toml`

`pyproject.toml`에는 프로젝트 메타데이터, 지원 Python 버전, 빌드 백엔드, 콘솔 스크립트를 기록할 수 있습니다.

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "data-report"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
data-report = "data_report.cli:main"
```

`[project.scripts]`는 설치 후 생성할 명령과 호출할 함수를 연결합니다.

```text
data-report
→ data_report.cli:main
→ 정수 종료 상태 반환
```

제3자 패키지를 사용한다면 다음 항목을 구분해야 합니다.

- 프로그램 실행에 필요한 직접 의존성
- 개발과 테스트에만 필요한 의존성
- 직접 선택한 의존성과 전이 의존성
- 허용할 버전 범위
- 재현 가능한 설치를 위한 잠금 파일

필수 프로젝트는 Python 표준 라이브러리와 빌드 백엔드 외에 런타임 의존성을 요구하지 않습니다.

## 모듈 진입점과 콘솔 스크립트

`__main__.py`는 모듈 실행을 CLI 함수에 연결합니다.

```python
from .cli import main

raise SystemExit(main())
```

다음 두 실행 방법이 같은 `main()`을 사용해야 합니다.

```sh
python -m data_report examples/sales.csv
data-report examples/sales.csv
```

진입점마다 인자 파싱이나 종료 상태 처리를 따로 구현하면 동작이 달라질 수 있습니다.

## 타입 힌트를 우선 적용할 곳

타입 힌트는 여러 모듈이 함께 사용하는 값과 공개 함수부터 추가합니다.

```python
from collections.abc import Iterable


def aggregate(records: Iterable[Record]) -> Report:
    ...
```

다음 상황에서 특히 가치가 큽니다.

- `None` 가능 여부가 중요한 경우
- 여러 모듈이 같은 `dataclass`를 사용하는 경우
- 콜백이나 `Protocol`을 전달하는 경우
- `dict` 필드가 많아 이름 있는 타입이 필요한 경우

외부 JSON에 곧바로 `cast(Record, raw)`를 적용해서는 안 됩니다. `cast()`는 정적 검사기에만 정보를 제공하며 실행 중인 값은 검사하지 않습니다.

```python
raw: object = json.loads(text)
record = validate_record(raw)
```

실제 값을 검사한 뒤 `Record`를 만들어야 합니다.

## `Any` 사용 범위 줄이기

JSON 파서는 실행 시 다양한 값을 반환하므로 내부 보조 함수가 `Any`를 사용할 수 있습니다. 그러나 검증을 끝낸 값까지 `Any`로 전달하면 이후 모듈이 어떤 값을 받는지 알기 어렵습니다.

```text
JSON 파서 결과: object 또는 Any
→ 필드 검사
→ Record
→ 이후 모듈은 Record만 사용
```

외부 입력을 받는 지점에서 넓은 타입을 사용하고, 검증한 뒤에는 구체적인 타입으로 바꿉니다.

## 값 객체의 가변성 제한하기

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Record:
    category: str
    amount: Decimal
```

불변 값은 입력 함수가 만든 결과를 집계 함수나 출력 함수가 실수로 바꾸는 문제를 막아 줍니다.

다만 `frozen=True`인 `dataclass` 안에 가변 `list`나 `dict`를 넣으면 내부 값은 여전히 바뀔 수 있습니다. 필드도 가능한 한 불변 타입으로 구성합니다.

## `Protocol`은 교체할 동작이 있을 때 사용하기

```python
from pathlib import Path
from typing import Protocol


class ReportWriter(Protocol):
    def write(self, path: Path, text: str) -> None:
        ...
```

테스트에서 실제 파일 시스템 대신 다른 출력 객체를 전달해야 한다면 작은 `Protocol`이 도움이 될 수 있습니다. 구체 구현이 하나뿐이고 교체할 필요도 없다면 미리 인터페이스를 만들지 않습니다.

## 품질 도구 선택하기

실제 프로젝트에서는 필요에 따라 다음 도구를 추가할 수 있습니다.

- `ruff`: 린트와 포매팅
- `mypy` 또는 `pyright`: 정적 타입 검사
- `pytest`: fixture와 매개변수화가 많은 테스트
- `coverage.py`: 테스트가 실행한 코드 경로 측정
- `tox` 또는 `nox`: 여러 Python 환경에서 반복 검증

도구를 많이 추가하기보다 모든 개발자가 같은 명령으로 검증할 수 있게 만드는 일이 먼저입니다.

작은 프로젝트는 다음 명령만으로도 시작할 수 있습니다.

```sh
python -m unittest discover -s tests -v
python -m pip wheel --no-deps . -w dist
```

## 설치된 패키지 확인하기

소스 트리에서 `python -m data_report`가 동작한다고 해서 패키지 메타데이터와 콘솔 스크립트가 올바르다는 뜻은 아닙니다.

다음 순서로 확인합니다.

```text
wheel을 만듭니다.
→ 새 가상 환경을 만듭니다.
→ wheel을 설치합니다.
→ 저장소 밖의 디렉터리로 이동합니다.
→ 콘솔 스크립트를 실행합니다.
```

예:

```sh
python -m pip wheel --no-deps . -w dist
python -m venv /tmp/data-report-venv
/tmp/data-report-venv/bin/python -m pip install dist/data_report-1.0.0-py3-none-any.whl
cd /tmp
/tmp/data-report-venv/bin/data-report /path/to/sales.csv
```

이 검사는 다음 오류를 찾습니다.

- 패키지가 wheel에 포함되지 않음
- `py.typed`가 누락됨
- 콘솔 스크립트 대상 함수가 잘못됨
- 버전 메타데이터가 소스와 다름
- 소스 루트가 `PYTHONPATH`에 있을 때만 `import`됨

## 로그와 비밀값

라이브러리 모듈이 전역 로깅 설정을 임의로 바꾸지 않도록 합니다. 로그 레벨과 핸들러는 최종 애플리케이션 진입점에서 설정합니다.

환경 변수에 저장했다고 해서 값이 자동으로 안전해지는 것은 아닙니다. API 키, 토큰, 전체 환경 변수 `dict`를 로그, 예외, 보고서에 출력하지 않습니다.

## 자주 발생하는 문제

### 거대한 `utils.py`

경로 처리, 직렬화, 프로세스 실행, 출력 형식처럼 서로 다른 이유로 바뀌는 함수가 한 파일에 모이면 사용 관계를 파악하기 어렵습니다. 실제 작업 단위에 따라 모듈을 나눕니다.

### `import` 시 부작용

모듈을 `import`하는 것만으로 파일을 만들거나 환경 변수를 바꾸지 않습니다.

### 저장소 루트에서만 성공하는 `import`

테스트가 소스 루트를 자동으로 `sys.path`에 넣어 패키지 설치 오류를 숨길 수 있습니다. 별도 가상 환경에 설치한 뒤 저장소 밖에서 실행합니다.

### 과도한 추상화

인터페이스, 팩터리, 클래스 계층을 실제 변경 요구 없이 추가하지 않습니다. 두 구현을 교체하거나 테스트에서 외부 기능을 대체해야 할 때만 도입합니다.

## 프로젝트에 적용하기

### 필수: `data-report`

- `model.py`는 파일이나 CLI 모듈을 `import`하지 않습니다.
- `loaders.py`가 CSV/JSON을 `Record`로 바꿉니다.
- `aggregation.py`와 `rendering.py`는 파일 시스템에 접근하지 않습니다.
- `cli.py`가 인자 파싱과 파일 쓰기를 수행합니다.
- `pyproject.toml`이 `data-report` 콘솔 스크립트를 선언합니다.

### 선택: `command-checker`

- 프로세스 실행, 비교, 보고서 생성, CLI를 별도 모듈로 나눕니다.
- `py.typed`, 패키지 버전, wheel 메타데이터가 서로 일치하는지 검사합니다.
- 자체 PEP 517 백엔드가 결정적인 wheel을 만듭니다.

## 완료 기준

- 단일 파일을 여러 모듈로 나눈 이유를 실제 변경 단위로 설명합니다.
- 모듈 의존 방향에 순환이 없습니다.
- 지원 Python 버전과 콘솔 스크립트가 `pyproject.toml`에 기록되어 있습니다.
- 타입 힌트와 실행 시 입력 검증을 구분합니다.
- 설치된 `data-report`가 소스 경로 없이 실행됩니다.
- 테스트와 패키지 빌드 명령을 문서에서 바로 실행할 수 있습니다.

필수 과정은 여기까지입니다. 외부 CLI 프로그램을 검사하는 도구가 필요하다면 [CLI 검사기 설계](03-cli-test-runner.md)로 진행합니다.
