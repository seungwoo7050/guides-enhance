# 프로젝트 구조, 패키징과 타입 검사

## 학습 목표

프로젝트 구조는 파일 수를 늘리기 위한 규칙이 아닙니다. **서로 다른 이유로 바뀌는 코드를 나누고, 의존 관계와 책임의 경계를 코드 구조로 드러내기 위한 수단**입니다.

파일을 나누는 것 자체가 목표가 아니라 다음 질문에 쉽게 답할 수 있게 만드는 것이 목표입니다.

- 이 기능은 어디에 구현되어 있습니까?
- 이 모듈은 어떤 모듈에 의존합니까?
- 입력 형식이나 출력 형식이 바뀌면 어떤 파일이 영향을 받습니까?
- 계산 로직을 파일 시스템이나 CLI 없이 테스트할 수 있습니까?
- 패키지를 실제로 설치했을 때도 같은 방식으로 실행됩니까?

이 문서에서는 다음 내용을 다룹니다.

- 단일 파일을 여러 모듈로 나눌 시점
- 순환 `import`를 피하는 의존 방향
- `pyproject.toml`과 콘솔 스크립트
- 모듈 실행 진입점과 설치된 명령의 관계
- 타입 힌트와 실행 시 입력 검증의 차이
- `Any`, `Protocol`, 불변 값 객체를 사용하는 기준
- 소스 트리가 아니라 설치된 패키지를 확인하는 방법
- 과도한 추상화를 피하는 기준

필수 프로젝트인 [`data-report`](../../exercises/data-report/README.md)를 설치 가능한 패키지로 완성할 때 이 내용을 적용합니다.

## 선행 개념

- **모듈(module)**: 일반적으로 하나의 Python 파일처럼 `import`할 수 있는 코드 단위입니다.
- **패키지(package)**: 여러 모듈을 하나의 이름 공간 아래 묶는 구조입니다. 일반적인 패키지 디렉터리에는 `__init__.py`가 있습니다.
- 모듈 간 `import`를 따라갈 수 있어야 합니다.
- 공개 함수와 내부 보조 함수를 구분할 수 있어야 합니다.
- 타입 힌트와 실행 시 검증의 차이를 이해해야 합니다.

## 프로그램 크기에 맞는 구성 선택하기

한 번만 사용하는 30줄짜리 변환 도구라면 단일 파일로 충분할 수 있습니다.

```text
normalize_log.py
```

코드가 길어졌다는 이유만으로 즉시 파일을 나눌 필요는 없습니다. 다음처럼 **서로 다른 이유로 변경되는 작업**이 한 파일 안에서 분명히 구분되기 시작하면 모듈 분리를 검토합니다.

```text
CLI 인자 파싱
외부 입력 검증
핵심 계산
파일·프로세스 입출력
보고서 직렬화
```

예를 들어 CSV 입력 형식이 바뀌어도 집계 규칙은 바뀌지 않아야 하고, 텍스트 출력 형식이 바뀌어도 CSV 파서는 바뀌지 않는 편이 좋습니다. 이런 변경 경계를 모듈 경계로 만들면 한 기능을 수정할 때 다른 기능까지 함께 건드릴 가능성이 줄어듭니다.

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

여기서 역할은 대략 다음처럼 나눌 수 있습니다.

```text
__init__.py   패키지 초기화와 필요한 공개 이름
__main__.py   python -m app 실행 진입점
cli.py        인자 파싱, 사용자 메시지, 종료 상태
core.py       파일이나 터미널에 의존하지 않는 핵심 계산
```

모듈을 나눴는데도 모든 모듈이 서로를 `import`하고 전역 상태를 공유한다면 책임 분리가 제대로 된 것은 아닙니다. 파일 개수보다 **의존 방향과 변경 이유**가 더 중요합니다.

## `src/` 배치를 사용하는 이유

패키지를 저장소 루트 바로 아래에 둘 수도 있고 `src/` 아래에 둘 수도 있습니다.

```text
project/
├── pyproject.toml
├── src/
│   └── app/
└── tests/
```

`src/` 배치의 중요한 목적은 **설치되지 않은 소스 디렉터리를 우연히 직접 import하는 상황을 줄이는 것**입니다.

Python을 저장소 루트에서 실행하면 현재 작업 디렉터리가 모듈 검색 경로에 포함될 수 있습니다. 패키지가 저장소 루트 바로 아래에 있으면 패키징 설정이 잘못되어 실제 wheel에는 패키지가 들어가지 않더라도 개발 중 `import app`이 성공할 수 있습니다.

`src/` 배치에서는 일반적으로 저장소 루트에서 바로 `import app`할 수 없으므로, 테스트와 실행이 설치된 패키지를 사용하도록 만들기 쉽습니다.

다만 `src/` 배치 자체가 패키징 오류를 자동으로 해결하는 것은 아닙니다. 빌드 백엔드가 `src/` 아래의 패키지를 올바르게 발견하도록 설정되어 있어야 합니다.

모든 작은 프로젝트에 `src/` 배치를 강제할 필요는 없습니다. 중요한 것은 **실제 설치 결과를 별도로 검사해 소스 트리 때문에 우연히 성공한 import를 구분하는 것**입니다.

## 모듈 의존 방향 정하기

모듈 분리 후에는 어떤 모듈이 어떤 모듈을 사용하는지 의존 방향을 정해야 합니다.

이 문서에서는 다음 표기를 사용합니다.

```text
A → B
```

이는 **A가 B를 import하거나 B가 제공하는 타입·함수를 사용한다**는 뜻입니다.

`data-report`를 다음처럼 구성할 수 있습니다.

```text
loaders     → model
aggregation → model
rendering   → model
cli         → loaders, aggregation, rendering, model
```

반대로 `model`은 위 모듈들을 알 필요가 없습니다.

```text
model
↑     ↑          ↑
│     │          │
loaders aggregation rendering
      \    |    /
           cli
```

핵심은 **도메인에 가까운 안정적인 모듈이 CLI나 파일 입출력처럼 바깥쪽 세부 구현에 의존하지 않게 하는 것**입니다.

예를 들어 다음 책임을 유지합니다.

- `model.py`는 `Record`, `Report` 같은 데이터 구조를 정의하며 `argparse`, 파일 경로, 출력 문구를 알지 않습니다.
- `loaders.py`는 CSV나 JSON 같은 외부 표현을 읽어 `Record`로 바꿉니다.
- `aggregation.py`는 `Record`가 CSV에서 왔는지 JSON에서 왔는지 알지 않습니다.
- `rendering.py`는 `Report`를 문자열로 바꾸지만 파일을 직접 쓰지 않습니다.
- `cli.py`는 인자 파싱, 파일 읽기·쓰기, 오류 메시지, 종료 상태처럼 애플리케이션 경계의 동작을 조정합니다.

이 방향을 지키면 `model.py`가 `cli.py`를 import하고 동시에 `cli.py`가 `model.py`를 import하는 식의 순환 의존이 생길 가능성도 줄어듭니다.

순환 `import`는 단순히 보기 나쁜 구조에 그치지 않습니다. 모듈 초기화 도중 상대 모듈의 정의가 아직 완료되지 않아 import 오류나 부분 초기화 상태가 나타날 수 있습니다.

다음 질문으로 모듈을 나눌 수 있습니다.

- 이 코드는 무엇을 입력으로 받습니까?
- 결과는 값으로 반환합니까, 아니면 파일이나 터미널에 씁니까?
- 파일이나 터미널에 접근합니까?
- 입력 형식이 바뀌면 함께 바뀝니까?
- 출력 형식이 추가되면 함께 바뀝니까?
- 테스트에서 실제 파일 없이 실행할 수 있습니까?

## `pyproject.toml`

`pyproject.toml`은 Python 프로젝트의 빌드와 배포에 필요한 정보를 선언하는 중심 설정 파일입니다. 프로젝트에 따라 여러 도구의 설정도 함께 기록할 수 있습니다.

최소한 다음 종류의 정보를 담을 수 있습니다.

- 어떤 빌드 백엔드를 사용할지
- 프로젝트 이름과 버전
- 지원 Python 버전
- 런타임 의존성
- 설치 후 생성할 콘솔 스크립트

예:

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

`[build-system]`은 wheel이나 소스 배포물을 만들 때 필요한 빌드 시스템을 지정합니다.

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

`[project]`는 설치되는 프로젝트의 메타데이터를 지정합니다.

```toml
[project]
name = "data-report"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = []
```

여기서 프로젝트 배포 이름인 `data-report`와 Python에서 import하는 패키지 이름인 `data_report`는 서로 다른 이름일 수 있습니다.

```text
pip에서 다루는 배포 이름: data-report
Python import 패키지:      data_report
```

따라서 `pip install data-report`와 `import data_report`처럼 하이픈과 밑줄이 다르게 보이는 것은 이상한 일이 아닙니다.

## 런타임 의존성과 개발 의존성 구분하기

제3자 패키지를 사용한다면 최소한 다음을 구분해야 합니다.

- **직접 런타임 의존성**: 프로그램 실행에 반드시 필요한 패키지
- **개발·테스트 의존성**: 테스트, 린트, 타입 검사, 문서 생성 등에만 필요한 패키지
- **전이 의존성**: 직접 의존성이 내부적으로 다시 의존하는 패키지
- **허용 버전 범위**: 프로젝트가 지원하는 의존성 버전 범위
- **잠금 정보**: 애플리케이션 개발 환경을 동일한 버전 조합으로 재현하기 위한 정보

중요한 점은 전이 의존성을 자신의 코드에서 직접 import해 사용한다면 더 이상 단순한 전이 의존성으로 취급해서는 안 된다는 것입니다. 프로젝트가 직접 사용하는 패키지는 직접 의존성으로 명시하는 편이 안전합니다.

필수 프로젝트는 Python 표준 라이브러리와 빌드 백엔드 외에 런타임 의존성을 요구하지 않습니다.

## 콘솔 스크립트

`[project.scripts]`는 패키지를 설치했을 때 생성할 명령 이름과 Python 호출 대상을 연결합니다.

```toml
[project.scripts]
data-report = "data_report.cli:main"
```

의미는 다음과 같습니다.

```text
설치 후 생성되는 명령: data-report
호출할 Python 대상:     data_report.cli 모듈의 main 함수
```

일반적인 콘솔 스크립트 실행기는 해당 함수를 인자 없이 호출한 뒤 반환값을 프로세스 종료 상태로 사용합니다. 따라서 다음처럼 `main()`이 필요할 때 `sys.argv`를 읽고 정수를 반환하도록 만들 수 있습니다.

```python
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    ...
```

`argv=None`일 때 실제 명령행 인자를 사용하고, 테스트에서는 직접 목록을 전달하게 만들면 CLI를 하위 프로세스 없이도 검사하기 쉽습니다.

예:

```python
status = main(["examples/sales.csv"])
```

CLI 함수가 성공 시 `0`, 사용법 오류나 입력 오류 시 비영(0이 아닌) 정수를 반환하도록 계약을 정하면 호출자와 테스트가 결과를 명확하게 확인할 수 있습니다.

## 모듈 진입점과 콘솔 스크립트

`__main__.py`는 다음 실행 형태를 지원하는 모듈 진입점입니다.

```sh
python -m data_report
```

`__main__.py`에서는 CLI 동작을 다시 구현하지 말고 공통 `main()`에 연결합니다.

```python
from .cli import main

raise SystemExit(main())
```

`SystemExit`에 정수를 전달하면 그 값이 프로세스 종료 상태가 됩니다.

이제 다음 두 실행 방법이 같은 `main()`을 사용합니다.

```sh
python -m data_report examples/sales.csv
data-report examples/sales.csv
```

구조는 다음과 같습니다.

```text
python -m data_report
        ↓
data_report.__main__
        ↓
     cli.main()

설치된 data-report 명령
        ↓
     cli.main()
```

진입점마다 인자 파싱, 오류 처리, 종료 상태 계산을 따로 구현하면 두 실행 방법의 동작이 달라질 수 있습니다. 사용자에게 제공하는 진입점이 여러 개라면 **실제 로직은 하나의 `main()`으로 모으고 진입점은 연결만 담당**하게 합니다.

## 타입 힌트와 실행 시 검증은 역할이 다릅니다

타입 힌트는 코드를 읽는 사람과 정적 타입 검사기가 값의 의도를 이해하도록 돕습니다.

```python
from collections.abc import Iterable


def aggregate(records: Iterable[Record]) -> Report:
    ...
```

이 표기는 `aggregate()`가 `Record`를 순회할 수 있는 값을 입력으로 받고 `Report`를 반환한다는 계약을 표현합니다.

하지만 일반적인 Python 타입 힌트는 함수 호출 시 자동으로 실행 검증을 수행하지 않습니다.

```python
aggregate("not records")
```

정적 타입 검사기는 이런 호출을 오류로 지적할 수 있지만, Python 인터프리터가 타입 힌트만 보고 호출 자체를 자동으로 막아 주지는 않습니다.

따라서 다음 둘을 구분해야 합니다.

```text
타입 힌트
→ 개발 중 잘못된 값의 흐름을 발견하는 데 도움

실행 시 검증
→ 파일, JSON, CLI처럼 신뢰할 수 없는 실제 입력을 검사
```

외부 경계에서는 실행 시 검증이 필요하고, 검증을 통과한 이후의 내부 코드에서는 구체적인 타입 힌트를 사용해 값의 형태를 유지하는 방식이 좋습니다.

## 타입 힌트를 우선 적용할 곳

처음부터 모든 지역 변수에 타입 힌트를 붙일 필요는 없습니다. 여러 모듈 사이에서 계약 역할을 하는 부분부터 적용하는 편이 효과적입니다.

다음과 같은 곳에 우선 적용합니다.

- 공개 함수의 매개변수와 반환값
- 여러 모듈이 공유하는 `dataclass`
- `None` 가능 여부가 중요한 값
- 콜백이나 함수 객체를 전달하는 경계
- `Protocol` 같은 교체 가능한 동작의 경계
- 여러 필드를 가진 이름 있는 데이터 구조

예:

```python
from collections.abc import Iterable


def aggregate(records: Iterable[Record]) -> Report:
    ...
```

여기서 `Iterable[Record]`를 사용하면 호출자가 반드시 `list[Record]`를 만들 필요는 없습니다. `Record`를 순회할 수 있는 값이면 사용할 수 있다는 계약을 표현합니다.

## `cast()`는 실행 시 검증이 아닙니다

외부 JSON 결과에 곧바로 `cast(Record, raw)`를 적용해서는 안 됩니다.

```python
from typing import cast

raw = json.loads(text)
record = cast(Record, raw)
```

`cast()`는 실행 중인 객체를 변환하거나 검사하지 않습니다. 정적 타입 검사기에게 “이 값을 `Record`라고 간주하라”고 알려 줄 뿐입니다.

따라서 JSON에 잘못된 필드가 있어도 `cast()` 자체는 실패하지 않습니다.

외부 입력은 먼저 넓은 타입으로 받고 실제 값을 검사합니다.

```python
raw: object = json.loads(text)
record = validate_record(raw)
```

`validate_record()`는 예를 들어 다음을 확인할 수 있습니다.

- 최상위 값이 객체인지
- 필요한 필드가 모두 있는지
- 허용하지 않은 필드가 없는지
- `category`가 문자열인지
- `amount`가 허용된 숫자 표현인지

검증이 끝난 뒤 `Record`를 생성하면 이후 모듈은 다시 원시 JSON 구조를 확인할 필요가 없습니다.

```text
신뢰할 수 없는 외부 값
        ↓ 검증
      Record
        ↓
aggregation / rendering
```

## `Any` 사용 범위 줄이기

`Any`는 정적 타입 검사를 크게 우회하는 타입입니다. `Any`인 값에서는 대부분의 속성 접근과 연산이 허용되므로 잘못된 값이 내부로 퍼져도 타입 검사기가 발견하지 못할 수 있습니다.

JSON 파서처럼 다양한 형태의 값을 반환하는 경계에서 `Any`가 나타날 수 있지만, 검증을 끝낸 값까지 계속 `Any`로 전달하지 않습니다.

```text
JSON 파서 결과: object 또는 Any
→ 구조와 필드 검사
→ Record
→ 이후 모듈은 Record만 사용
```

가능하다면 검증 함수의 입력을 `object`처럼 보수적인 타입으로 두는 것도 유용합니다. `object`에서는 먼저 타입을 좁히지 않으면 임의의 속성이나 연산을 사용할 수 없기 때문에 검증 절차를 코드에 드러내기 쉽습니다.

핵심 원칙은 다음과 같습니다.

> 외부 경계에서는 넓은 타입을 받아도 되지만, 검증을 통과한 값은 가능한 한 빨리 구체적인 도메인 타입으로 바꿉니다.

## 값 객체의 가변성 제한하기

여러 모듈 사이에서 전달하는 데이터가 값 자체를 표현한다면 불변 객체로 만드는 것이 도움이 될 수 있습니다.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Record:
    category: str
    amount: Decimal
```

`frozen=True`는 일반적인 속성 대입을 막아 `Record`가 생성된 뒤 실수로 변경되는 일을 줄입니다.

```python
record.amount = Decimal("10")  # 오류
```

`slots=True`는 인스턴스가 선언되지 않은 임의 속성을 가지지 않도록 하고 일반적으로 메모리 구조도 더 고정적으로 만듭니다.

다만 `frozen=True`가 객체 내부의 모든 값을 깊게 불변으로 만드는 것은 아닙니다.

```python
@dataclass(frozen=True)
class Example:
    values: list[int]
```

이 경우 다음 속성 재대입은 막히지만

```python
example.values = []
```

리스트 자체의 변경은 여전히 가능합니다.

```python
example.values.append(1)
```

따라서 불변 값 객체를 의도한다면 필드도 가능하면 `tuple`, `frozenset`, 불변 값 타입처럼 변경되지 않는 타입으로 구성합니다.

## `Protocol`은 교체할 동작이 있을 때 사용하기

`Protocol`은 특정 클래스를 상속했는지가 아니라 **필요한 메서드와 속성을 제공하는지**를 기준으로 타입 계약을 표현할 수 있습니다.

```python
from pathlib import Path
from typing import Protocol


class ReportWriter(Protocol):
    def write(self, path: Path, text: str) -> None:
        ...
```

이 계약을 사용하는 코드는 구체적인 파일 writer 클래스 이름보다 `write()` 동작에 의존할 수 있습니다.

예를 들어 다음 상황에서는 작은 `Protocol`이 유용할 수 있습니다.

- 실제 구현과 테스트용 구현을 바꿔 끼워야 함
- 두 개 이상의 구현이 같은 동작 계약을 공유함
- 호출하는 쪽이 구체 클래스보다 필요한 동작에만 의존해야 함

반대로 구체 구현이 하나뿐이고 교체 요구도 없다면 처음부터 모든 동작에 `Protocol`, 추상 클래스, 팩터리를 추가할 필요는 없습니다.

추상화는 **현재 존재하는 변경 경계나 테스트 경계를 표현할 때** 도입합니다.

## 품질 도구 선택하기

실제 프로젝트에서는 필요에 따라 다음 도구를 추가할 수 있습니다.

- `ruff`: 린트와 포매팅
- `mypy` 또는 `pyright`: 정적 타입 검사
- `pytest`: fixture와 매개변수화가 많은 테스트
- `coverage.py`: 테스트가 실행한 코드 경로 측정
- `tox` 또는 `nox`: 여러 Python 환경에서 반복 검증

이 도구들은 서로 다른 문제를 해결합니다. 예를 들어 타입 검사기가 테스트를 대신하지 않고, 높은 코드 커버리지가 올바른 검증을 보장하지도 않습니다.

도구를 많이 추가하기보다 **프로젝트에서 반드시 실행해야 하는 검증 명령을 명확하게 정하고 모든 개발자와 CI가 같은 방식으로 실행할 수 있게 만드는 것**이 먼저입니다.

작은 프로젝트는 다음 명령만으로도 시작할 수 있습니다.

```sh
python -m unittest discover -s tests -v
python -m pip wheel --no-deps . -w dist
```

첫 번째 명령은 테스트를 실행하고, 두 번째 명령은 현재 프로젝트에서 wheel을 만들어 `dist/`에 저장합니다.

빌드에 성공했다는 사실만으로 설치된 패키지가 올바르게 동작한다고 볼 수는 없습니다. 다음 단계에서 실제 wheel을 설치해 확인해야 합니다.

## wheel을 확인해야 하는 이유

개발 중에는 소스 파일이 모두 저장소에 있으므로 필요한 파일이 패키지에 실제로 포함되지 않아도 코드가 실행될 수 있습니다.

반면 사용자는 보통 저장소 전체가 아니라 빌드된 wheel을 설치합니다.

```text
저장소의 소스
    ↓ build
   wheel
    ↓ install
설치된 패키지
```

따라서 배포 결과를 검증하려면 최종적으로 **wheel에 무엇이 들어갔고 설치 후 무엇이 동작하는지** 확인해야 합니다.

## 설치된 패키지 확인하기

소스 트리에서 다음 명령이 동작한다고 해서

```sh
python -m data_report
```

패키지 메타데이터와 콘솔 스크립트가 올바르다고 단정할 수는 없습니다. 현재 작업 디렉터리나 `PYTHONPATH` 때문에 저장소의 소스를 직접 import했을 가능성이 있기 때문입니다.

다음 순서로 확인합니다.

```text
1. wheel을 만듭니다.
2. 새 가상 환경을 만듭니다.
3. 만든 wheel을 설치합니다.
4. 저장소 밖의 디렉터리로 이동합니다.
5. 설치된 모듈과 콘솔 스크립트를 실행합니다.
```

POSIX 환경의 예:

```sh
python -m pip wheel --no-deps . -w dist
python -m venv /tmp/data-report-venv
/tmp/data-report-venv/bin/python -m pip install dist/data_report-1.0.0-py3-none-any.whl
cd /tmp
/tmp/data-report-venv/bin/python -m data_report /path/to/sales.csv
/tmp/data-report-venv/bin/data-report /path/to/sales.csv
```

여기서 저장소 밖으로 이동하는 이유는 현재 디렉터리의 소스 패키지가 import 후보가 되는 것을 피하기 위해서입니다.

가능하면 `PYTHONPATH`에도 저장소 소스 경로가 남아 있지 않게 합니다.

이 검사는 다음과 같은 오류를 찾을 수 있습니다.

- 패키지 디렉터리가 wheel에 포함되지 않음
- 실행에 필요한 데이터 파일이 wheel에서 누락됨
- 콘솔 스크립트 대상 함수가 잘못됨
- `__main__.py`가 누락되거나 잘못 연결됨
- 버전 메타데이터가 예상과 다름
- 저장소 루트가 모듈 검색 경로에 있을 때만 `import`됨
- 프로젝트가 타입 정보 배포를 약속하는 경우 `py.typed`가 누락됨

## `py.typed`의 의미

`py.typed`는 패키지가 소스 코드 안의 타입 힌트를 외부 정적 타입 검사기에도 제공하는 **typed package**임을 표시할 때 사용하는 마커 파일입니다.

대략 다음과 같은 구조가 됩니다.

```text
data_report/
├── __init__.py
├── model.py
├── cli.py
└── py.typed
```

단순히 프로젝트 내부에서 타입 힌트를 사용한다는 이유만으로 모든 애플리케이션에 반드시 `py.typed`가 필요한 것은 아닙니다. 그러나 패키지를 다른 프로젝트가 import해 사용하고 그 타입 정보를 배포 계약의 일부로 제공하려면 `py.typed`가 wheel에 포함되어 있는지 확인해야 합니다.

선택 프로젝트 `command-checker`처럼 `py.typed` 포함을 명시적으로 요구한다면 소스 트리에 파일이 존재하는지만 확인하지 말고 **빌드된 wheel과 설치 결과에도 포함되는지** 검사합니다.

## 로그와 비밀값

라이브러리 모듈은 `import`만으로 애플리케이션 전체의 로깅 설정을 바꾸지 않는 편이 좋습니다.

예를 들어 라이브러리 내부에서 다음과 같은 전역 설정을 임의로 호출하면

```python
logging.basicConfig(...)
```

그 라이브러리를 사용하는 애플리케이션의 로그 형식이나 레벨에 영향을 줄 수 있습니다.

일반적으로 라이브러리 모듈은 자신의 로거를 얻어 메시지만 기록하고, 로그 레벨·핸들러·출력 형식 같은 최종 설정은 애플리케이션 진입점에서 결정합니다.

또한 환경 변수에 저장했다고 해서 값이 자동으로 비밀이 되는 것은 아닙니다.

다음 값은 로그, 예외 메시지, 디버그 출력, 보고서에 그대로 포함하지 않습니다.

- API 키
- 인증 토큰
- 비밀번호
- 쿠키나 세션 비밀값
- 전체 환경 변수 `dict`

필요한 진단 정보를 남길 때도 비밀값 자체가 아니라 어떤 설정이 누락되었는지처럼 최소한의 정보만 기록합니다.

## 자주 발생하는 문제

### 거대한 `utils.py`

경로 처리, 직렬화, 프로세스 실행, 출력 형식처럼 서로 다른 이유로 바뀌는 함수가 모두 `utils.py`에 들어가면 파일 이름만 보고 책임을 알 수 없고 여러 모듈이 그 파일에 의존하게 됩니다.

```text
utils.py
├── parse_csv()
├── write_json()
├── run_process()
├── format_report()
└── normalize_path()
```

이 경우 단순히 `utils1.py`, `utils2.py`로 나누는 것이 아니라 실제 책임에 따라 이름을 붙입니다.

```text
loaders.py
rendering.py
processes.py
paths.py
```

모든 짧은 보조 함수를 반드시 별도 모듈로 만들 필요는 없습니다. **함수들이 같은 변경 이유를 공유하는지**를 기준으로 판단합니다.

### `import` 시 부작용

모듈을 `import`하는 것만으로 외부 상태를 바꾸지 않는 편이 좋습니다.

피해야 할 예는 다음과 같습니다.

- 파일 생성 또는 삭제
- 네트워크 요청
- 자식 프로세스 실행
- 환경 변수 변경
- 애플리케이션 전체 로깅 설정 변경
- CLI 실행

예를 들어 다음 코드는 모듈을 import하는 순간 CLI를 실행합니다.

```python
main()
```

CLI 실행은 `__main__.py`처럼 명시적인 진입점에서 수행합니다.

```python
raise SystemExit(main())
```

이렇게 하면 테스트나 다른 모듈이 `import data_report.cli`만 했을 때 프로그램이 갑자기 실행되는 일을 막을 수 있습니다.

### 저장소 루트에서만 성공하는 `import`

테스트가 저장소 루트를 자동으로 `sys.path`에 포함하면 실제 설치에 실패하는 패키징 오류를 숨길 수 있습니다.

예를 들어 다음 상황이 가능할 수 있습니다.

```text
저장소에서 import 성공
wheel에는 data_report가 누락됨
설치 환경에서는 import 실패
```

따라서 테스트 성공과 별개로 wheel을 새 가상 환경에 설치한 뒤 저장소 밖에서 다시 실행합니다.

### 타입 오류를 `Any`와 `cast()`로 숨기기

타입 검사 오류를 해결하기 위해 모든 값을 `Any`로 바꾸거나 검증 없이 `cast()`를 추가하면 오류 메시지는 사라질 수 있지만 타입 검사의 의미도 함께 사라집니다.

다음 순서로 문제를 확인합니다.

```text
실제 입력의 타입이 무엇인가?
→ 어느 경계에서 검증해야 하는가?
→ 검증 후 어떤 구체 타입으로 바꿀 수 있는가?
```

### 과도한 추상화

인터페이스, 팩터리, 클래스 계층, 플러그인 구조를 실제 변경 요구 없이 미리 추가하면 간단한 호출 흐름도 여러 계층을 따라가야 이해할 수 있습니다.

예를 들어 구현이 하나뿐인 `JsonReportWriter`를 위해 별도 추상 클래스, 팩터리, 레지스트리를 모두 만드는 것은 필요하지 않을 수 있습니다.

추상화를 도입할 근거가 되는 질문은 다음과 같습니다.

- 실제로 두 개 이상의 구현을 교체해야 합니까?
- 테스트에서 외부 기능을 대체해야 합니까?
- 호출하는 쪽이 구체 구현을 몰라야 하는 변경 이유가 있습니까?

답이 모두 아니라면 구체 함수나 클래스로 시작한 뒤 실제 필요가 생길 때 구조를 확장해도 됩니다.

## 프로젝트에 적용하기

### 필수: `data-report`

권장 책임 분리는 다음과 같습니다.

```text
model.py
└── Record, Report 같은 도메인 값

loaders.py
└── CSV/JSON → Record

aggregation.py
└── Iterable[Record] → Report

rendering.py
└── Report → 출력 문자열

cli.py
└── 인자 파싱, 파일 선택, 파일 쓰기, 오류 메시지, 종료 상태

__main__.py
└── cli.main() 호출
```

다음 조건을 확인합니다.

- `model.py`는 파일이나 CLI 모듈을 `import`하지 않습니다.
- `loaders.py`가 CSV/JSON을 검증한 뒤 `Record`로 바꿉니다.
- `aggregation.py`와 `rendering.py`는 파일 시스템에 접근하지 않습니다.
- `cli.py`가 인자 파싱과 최종 파일 쓰기를 조정합니다.
- `__main__.py`와 설치된 `data-report` 명령이 같은 `main()`을 사용합니다.
- `pyproject.toml`이 지원 Python 버전과 `data-report` 콘솔 스크립트를 선언합니다.
- wheel을 새 환경에 설치했을 때 저장소 소스 경로 없이 실행됩니다.

### 선택: `command-checker`

다음 구조적 조건을 확인합니다.

- 프로세스 실행, 결과 비교, 보고서 생성, CLI를 서로 다른 책임으로 나눕니다.
- 저수준 프로세스 실행 코드가 보고서 형식까지 알지 않습니다.
- `py.typed`, 패키지 버전, wheel 메타데이터가 요구사항과 일치하는지 설치 결과에서 검사합니다.
- 자체 PEP 517 백엔드가 요구된다면 같은 소스와 같은 입력에서 재현 가능한 wheel을 만들도록 설계합니다.

## 완료 기준

- 단일 파일을 여러 모듈로 나눈 이유를 파일 크기가 아니라 실제 변경 단위와 책임으로 설명합니다.
- `A → B`가 A가 B에 의존한다는 의미임을 알고 의존 방향을 추적할 수 있습니다.
- 핵심 도메인 모듈이 CLI나 파일 입출력 같은 바깥쪽 세부 구현에 의존하지 않습니다.
- 모듈 의존 방향에 불필요한 순환이 없습니다.
- 지원 Python 버전과 콘솔 스크립트가 `pyproject.toml`에 기록되어 있습니다.
- `python -m data_report`와 설치된 `data-report`가 같은 `main()`을 사용합니다.
- 타입 힌트와 실행 시 입력 검증을 서로 다른 역할로 구분합니다.
- 외부 입력은 검증 후 구체적인 도메인 타입으로 바뀝니다.
- `Any`와 `cast()`를 실행 시 검증의 대체물로 사용하지 않습니다.
- `Protocol`과 기타 추상화는 실제 교체 요구나 테스트 경계가 있을 때 도입합니다.
- wheel을 새 가상 환경에 설치한 뒤 저장소 밖에서 import와 진입점을 검사합니다.
- 타입 정보 배포가 요구되는 패키지는 `py.typed`가 wheel에도 포함되는지 확인합니다.
- 테스트와 패키지 빌드 명령을 문서에서 바로 실행할 수 있습니다.

필수 과정은 여기까지입니다. 외부 CLI 프로그램을 검사하는 도구가 필요하다면 [CLI 검사기 설계](03-cli-test-runner.md)로 진행합니다.
