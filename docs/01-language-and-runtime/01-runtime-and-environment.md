# 실행 환경과 모듈

## 학습 목표

이 문서를 마치면 다음 내용을 구분할 수 있어야 합니다.

- Python 인터프리터, 스크립트, 모듈
- 파일 경로를 지정한 실행과 `-m`을 사용한 모듈 실행
- `import`할 수 있는 코드와 프로그램 진입점
- 현재 작업 디렉터리와 소스 파일이 있는 디렉터리
- 시스템 Python과 프로젝트 가상 환경

필수 프로젝트에서는 [`data-report`](../../exercises/data-report/README.md)의 패키지와 모듈 진입점을 구성할 때 이 내용을 적용합니다.

## 선행 개념

- 터미널에서 명령을 실행할 수 있어야 합니다.
- `stdout`, `stderr`, 종료 상태를 확인할 수 있어야 합니다.
- 현재 작업 디렉터리와 파일이 저장된 위치가 다를 수 있음을 알고 있어야 합니다.

## Python이 적합한 작업

Python은 파일, 데이터, 운영체제 기능, 외부 프로그램을 비교적 짧은 코드로 연결하는 데 적합합니다.

- 로그와 JSON 데이터를 정규화하거나 비교합니다.
- 디렉터리를 순회하며 파일을 일괄 처리합니다.
- CSV 또는 JSON을 읽어 보고서를 만듭니다.
- 작은 기준 구현을 작성해 다른 프로그램의 결과와 비교합니다.
- 빌드·배포 결과를 점검하는 도구를 만듭니다.

매우 짧은 지연 시간, 고정된 메모리 배치, 인터프리터를 포함할 수 없는 배포 환경이 핵심 요구사항이라면 다른 언어가 더 적합할 수 있습니다. 익숙한 언어를 고집하기보다 실행 환경과 성능 요구사항을 먼저 확인해야 합니다.

## 첫 프로그램 실행

다음 파일을 만듭니다.

```python
# hello.py
print("안녕하세요, Python")
```

파일 경로를 지정해 실행합니다.

```sh
python3 hello.py
```

가장 단순한 개발 과정은 다음과 같습니다.

```text
파일을 수정합니다.
→ 인터프리터로 실행합니다.
→ stdout, stderr, 종료 상태를 확인합니다.
→ 실패한 입력과 오류 메시지를 기록합니다.
→ 수정한 뒤 다시 실행합니다.
```

Python 구현체는 실행 중에 소스 코드를 바이트코드로 변환할 수 있지만, 일반적인 개발 과정에서는 별도의 컴파일 명령이 필요하지 않습니다. 그렇더라도 문법 분석, 모듈 탐색, `import` 과정에서 오류가 발생할 수 있습니다.

## 스크립트 실행과 모듈 실행

다음 패키지를 가정합니다.

```text
project/
└── checker/
    ├── __init__.py
    ├── __main__.py
    └── cli.py
```

패키지는 다음처럼 실행할 수 있습니다.

```sh
python3 -m checker
```

`python3 -m checker`는 현재 `sys.path`에서 `checker` 패키지를 찾고 `checker/__main__.py`를 실행합니다. 패키지 내부에서 상대 `import`를 사용하는 프로그램은 파일 하나를 직접 실행하는 방식보다 `-m`으로 실행하는 편이 안전합니다.

```python
# checker/__main__.py
from .cli import main

raise SystemExit(main())
```

반면 다음 명령은 `checker/__main__.py`를 일반 파일처럼 직접 실행합니다.

```sh
python3 checker/__main__.py
```

이 방식에서는 패키지가 어떤 이름으로 불러와졌는지 알 수 없으므로 상대 `import`가 실패할 수 있습니다.

## 진입점을 함수로 분리하기

```python
# checker/cli.py
from __future__ import annotations

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    print("검사를 시작합니다.")
    return 0
```

프로세스 종료는 `__main__.py`에서 처리하고, 실제 작업은 정수 종료 상태를 반환하는 함수로 분리합니다.

```python
raise SystemExit(main())
```

이렇게 나누면 다음 작업이 쉬워집니다.

- 테스트에서 `main(["--help"])`처럼 인자를 직접 전달합니다.
- 모듈을 `import`해도 프로그램이 자동으로 실행되지 않습니다.
- 종료 상태를 명시적인 반환값으로 검사합니다.

라이브러리 모듈의 최상위 코드에서 파일을 삭제하거나 네트워크 요청을 보내는 등 큰 부작용을 일으키면 안 됩니다. `import`는 모듈을 불러오는 동작이지 프로그램 실행을 요청하는 신호가 아닙니다.

## `__name__`의 의미

파일을 직접 실행하면 `__name__`에는 `"__main__"`이 들어갑니다. 다른 모듈에서 `import`하면 실제 모듈 이름이 들어갑니다.

```python
def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

작은 단일 파일 프로그램에는 이 형태로 충분합니다. 프로그램이 패키지로 커지면 `__main__.py`와 `cli.py`를 분리하는 편이 실행 코드와 실제 기능을 구분하기 쉽습니다.

## 현재 작업 디렉터리와 소스 파일 위치

다음 두 경로는 서로 다른 의미를 가집니다.

```python
from pathlib import Path

working_directory = Path.cwd()
source_directory = Path(__file__).resolve().parent
```

- 사용자가 전달한 상대 경로는 보통 현재 작업 디렉터리를 기준으로 해석합니다.
- 소스 코드와 함께 배포한 예제나 기본 설정은 보통 `__file__`이 있는 위치를 기준으로 찾습니다.

어떤 디렉터리를 기준으로 삼는지 문서와 오류 메시지에 명시해야 합니다. 테스트가 저장소 루트에서만 우연히 통과한다면 경로 기준이 코드에 드러나지 않은 상태일 수 있습니다.

## 가상 환경과 인터프리터 확인

프로젝트마다 독립된 실행 환경을 만드는 편이 안전합니다.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -c 'import sys; print(sys.executable)'
python --version
```

위 활성화 명령은 POSIX 셸용입니다. Windows에서는 사용하는 셸에 맞는 활성화 명령을 선택해야 합니다.

Python을 하위 프로세스로 다시 실행할 때는 현재 인터프리터 경로를 재사용합니다.

```python
import subprocess
import sys

subprocess.run([sys.executable, "-m", "checker"], check=False)
```

`"python3"` 문자열을 직접 적는 것보다 현재 가상 환경과 Python 버전을 그대로 유지할 수 있습니다.

## 오류 유형부터 구분하기

| 실패 | 의미 | 먼저 확인할 항목 |
|---|---|---|
| `SyntaxError` | 소스 코드를 문법에 맞게 해석할 수 없음 | 표시된 줄과 바로 앞 줄 |
| `ModuleNotFoundError` | 모듈 탐색 경로나 실행 환경에 문제가 있음 | 실행 위치, `-m` 사용 여부, `sys.executable` |
| `NameError` | 현재 범위에 해당 이름이 없음 | 철자, 분기, `import` |
| `TypeError` | 연산이나 함수 호출에 맞지 않는 타입을 사용함 | 실제 타입과 전달한 인자 |
| 0이 아닌 종료 상태 | 프로그램이 오류를 처리한 뒤 실패 상태로 종료함 | `stderr`와 입력 규칙 |

오류 메시지를 지우지 말고 재현 입력과 함께 보관합니다.

## 프로젝트에 적용하기

### 필수: `data-report`

- `pyproject.toml`에서 `data-report = "data_report.cli:main"` 콘솔 스크립트를 선언합니다.
- `data_report/__main__.py`도 같은 `cli.main`을 호출합니다.
- 소스 트리와 설치된 패키지에서 같은 종료 상태를 반환하는지 확인합니다.

### 선택: `command-checker`

- `python -m command_checker`와 설치된 `command-checker` 명령이 같은 `main()`을 호출합니다.
- Python으로 작성한 외부 테스트 프로그램을 실행할 때 `sys.executable`을 사용합니다.

## 완료 기준

- 파일 실행과 모듈 실행의 차이를 설명할 수 있습니다.
- 모듈을 불러오는 동작과 프로그램 실행을 분리했습니다.
- `main()`이 정수 종료 상태를 반환합니다.
- 테스트에서 명령줄 인자를 직접 전달할 수 있습니다.
- 현재 사용 중인 Python 인터프리터 경로를 확인할 수 있습니다.
- 상대 경로가 어떤 디렉터리를 기준으로 해석되는지 설명할 수 있습니다.

다음은 [객체와 컬렉션](02-objects-and-collections.md)입니다.
