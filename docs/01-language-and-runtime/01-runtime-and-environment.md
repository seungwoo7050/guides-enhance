# 실행 환경과 모듈

## 학습 목표

이 문서를 마치면 다음 내용을 구분하고 설명할 수 있어야 합니다.

- Python 인터프리터, 스크립트, 모듈, 패키지
- 파일 경로를 지정한 실행과 `-m`을 사용한 모듈 실행
- `import`할 수 있는 코드와 프로그램 진입점
- `__name__`과 `__package__`이 실행 방식에 따라 달라지는 이유
- 현재 작업 디렉터리와 소스 파일이 있는 디렉터리
- 시스템 Python과 프로젝트 가상 환경
- 현재 실행 중인 Python 인터프리터를 하위 프로세스에서도 그대로 사용하는 방법

필수 프로젝트에서는 [`data-report`](../../exercises/data-report/README.md)의 패키지와 모듈 진입점을 구성할 때 이 내용을 적용합니다.

## 선행 개념

- 터미널에서 명령을 실행할 수 있어야 합니다.
- `stdout`, `stderr`, 종료 상태를 확인할 수 있어야 합니다.
- 현재 작업 디렉터리와 파일이 저장된 위치가 다를 수 있음을 알고 있어야 합니다.

## 인터프리터, 스크립트, 모듈, 패키지

먼저 용어를 구분합니다.

- **Python 인터프리터**는 Python 코드를 읽고 실행하는 프로그램입니다. 터미널에서 `python3` 또는 `python`으로 실행하는 프로그램이 여기에 해당합니다.
- **스크립트(script)**는 보통 사용자가 직접 실행하는 Python 파일을 가리킵니다. 예를 들어 `python3 hello.py`에서 `hello.py`는 스크립트로 실행됩니다.
- **모듈(module)**은 `import`할 수 있는 Python 코드 단위입니다. 일반적으로 하나의 `.py` 파일이 하나의 모듈이지만, 실행 방식에 따라 같은 파일도 스크립트처럼 실행되거나 모듈로 불릴 수 있습니다.
- **패키지(package)**는 여러 모듈과 하위 패키지를 묶는 단위입니다. 이 문서의 예제처럼 `checker/__init__.py`가 있는 디렉터리는 일반적인 패키지 구조입니다.

따라서 "파일"과 "모듈"은 완전히 같은 개념이 아닙니다. 중요한 차이는 Python이 그 코드를 **어떤 이름과 패키지 문맥으로 불러왔는가**입니다. 이 차이가 상대 `import`, `__name__`, 모듈 탐색 경로에 영향을 줍니다.

## Python이 적합한 작업

Python은 파일, 데이터, 운영체제 기능, 외부 프로그램을 비교적 짧은 코드로 연결하는 데 적합합니다.

- 로그와 JSON 데이터를 정규화하거나 비교합니다.
- 디렉터리를 순회하며 파일을 일괄 처리합니다.
- CSV 또는 JSON을 읽어 보고서를 만듭니다.
- 작은 기준 구현을 작성해 다른 프로그램의 결과와 비교합니다.
- 빌드·배포 결과를 점검하는 도구를 만듭니다.

반대로 매우 짧은 지연 시간이 필수이거나, 메모리 배치를 세밀하게 제어해야 하거나, Python 인터프리터를 포함할 수 없는 배포 환경이라면 다른 언어가 더 적합할 수 있습니다. 익숙한 언어를 고집하기보다 실행 환경과 성능 요구사항을 먼저 확인해야 합니다.

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

여기서 셸은 `python3`라는 실행 파일을 찾고, Python 인터프리터는 `hello.py` 파일을 읽어 실행합니다.

가장 단순한 개발 과정은 다음과 같습니다.

```text
파일을 수정합니다.
→ 인터프리터로 실행합니다.
→ stdout, stderr, 종료 상태를 확인합니다.
→ 실패한 입력과 오류 메시지를 기록합니다.
→ 수정한 뒤 다시 실행합니다.
```

CPython 같은 Python 구현체는 실행 과정에서 소스 코드를 바이트코드로 변환할 수 있습니다. 그러나 일반적인 Python 개발에서는 C나 C++처럼 사용자가 먼저 별도의 컴파일 명령을 실행한 뒤 결과 실행 파일을 실행하는 과정이 필요하지 않습니다.

그렇다고 실행 전에 확인할 것이 없는 것은 아닙니다. 소스를 읽는 과정에서는 문법 오류가 발생할 수 있고, 프로그램을 시작한 뒤에는 모듈 탐색, `import`, 이름 조회, 타입 사용 등 여러 단계에서 오류가 발생할 수 있습니다.

## 스크립트 실행과 모듈 실행

다음 패키지 구조를 가정합니다.

```text
project/
└── checker/
    ├── __init__.py
    ├── __main__.py
    └── cli.py
```

현재 작업 디렉터리가 `project/`라면 다음처럼 패키지를 실행할 수 있습니다.

```sh
python3 -m checker
```

`-m`은 뒤의 값을 파일 경로가 아니라 **모듈 이름**으로 해석하라는 뜻입니다. Python은 현재 모듈 탐색 경로인 `sys.path`에서 `checker`를 찾고, 실행 가능한 패키지라면 `checker/__main__.py`를 실행합니다.

```python
# checker/__main__.py
from .cli import main

raise SystemExit(main())
```

여기서 `.cli`의 앞에 있는 `.`은 현재 패키지인 `checker`를 기준으로 `cli` 모듈을 찾으라는 **상대 import**입니다. `python3 -m checker`로 실행하면 Python이 `checker`를 패키지로 인식한 상태에서 `__main__.py`를 실행하므로 이 상대 import가 올바른 패키지 문맥을 가집니다.

반면 다음 명령은 `checker/__main__.py`를 패키지의 진입점이 아니라 일반 파일 경로로 직접 실행합니다.

```sh
python3 checker/__main__.py
```

이 경우 실행 중인 파일의 `__name__`은 `"__main__"`이지만, 상대 import가 기준으로 삼을 패키지 문맥인 `__package__`가 적절히 설정되지 않을 수 있습니다. 따라서 다음 코드가 실패할 수 있습니다.

```python
from .cli import main
```

대표적으로 다음과 같은 오류가 발생할 수 있습니다.

```text
ImportError: attempted relative import with no known parent package
```

패키지 내부 모듈을 실행할 때는 파일 경로를 직접 실행하기보다, 가능한 한 패키지의 부모 디렉터리에서 `-m`을 사용해 모듈 또는 패키지 이름으로 실행하는 것이 좋습니다.

예를 들어 `checker/cli.py` 자체를 모듈로 실행할 수 있게 작성했다면 다음처럼 실행합니다.

```sh
python3 -m checker.cli
```

핵심은 다음과 같습니다.

```text
python3 path/to/file.py
→ 파일 경로를 직접 실행
→ 그 파일이 프로그램의 최상위 코드가 됨

python3 -m package.module
→ sys.path에서 모듈 이름을 탐색
→ 패키지 문맥을 유지한 채 모듈을 실행
```

## 모듈 탐색 경로와 실행 위치

`import checker`나 `python3 -m checker`가 성공하려면 Python이 `checker`를 찾을 수 있어야 합니다. Python이 모듈과 패키지를 찾을 때 확인하는 경로 목록은 `sys.path`에 들어 있습니다.

확인하려면 다음 코드를 사용할 수 있습니다.

```python
import sys

for path in sys.path:
    print(path)
```

현재 작업 디렉터리에서 `python3 -m checker`를 실행하는 일반적인 경우에는 현재 작업 디렉터리가 모듈 탐색 기준에 포함됩니다. 따라서 위 예제 구조에서는 보통 `project/`에서 명령을 실행해야 `checker` 패키지를 찾을 수 있습니다.

```sh
cd project
python3 -m checker
```

반대로 파일 경로로 스크립트를 직접 실행하면 스크립트가 있는 디렉터리가 모듈 탐색의 중요한 기준이 됩니다. 이 차이 때문에 같은 소스라도 **어느 디렉터리에서 어떤 방식으로 실행했는가**에 따라 import 결과가 달라질 수 있습니다.

모듈을 찾지 못했을 때 무조건 패키지가 설치되지 않았다고 단정하지 말고 다음을 함께 확인해야 합니다.

- 모듈 또는 패키지 이름의 철자가 맞는가
- 현재 작업 디렉터리가 의도한 위치인가
- 파일 직접 실행과 `-m` 실행 중 어느 방식을 사용했는가
- 필요한 패키지가 현재 인터프리터 환경에 설치되어 있는가
- 실제로 어떤 인터프리터를 실행하고 있는가

## 진입점을 함수로 분리하기

명령줄 프로그램의 실제 동작은 함수로 분리해 두는 편이 좋습니다.

```python
# checker/cli.py
from __future__ import annotations

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    print("검사를 시작합니다.")
    return 0
```

프로세스 종료는 진입점에서 처리하고, 실제 작업 함수는 정수 종료 상태를 반환하게 만들 수 있습니다.

```python
# checker/__main__.py
from .cli import main

raise SystemExit(main())
```

`SystemExit`에 정수를 전달하면 일반적으로 그 정수가 프로세스 종료 상태가 됩니다.

```text
0          성공
0 이외 값   실패 또는 비정상적인 결과
```

구체적으로 어떤 비제로 값을 어떤 실패에 사용할지는 프로그램의 인터페이스로 정해야 합니다.

진입점과 작업 함수를 나누면 다음 작업이 쉬워집니다.

- 테스트에서 `main(["--help"])`처럼 인자를 직접 전달할 수 있습니다.
- CLI 진입점과 실제 처리 로직을 별도로 테스트할 수 있습니다.
- 종료 상태를 함수의 반환값으로 검사할 수 있습니다.
- 모듈을 import하는 코드와 프로그램 시작 코드를 분리할 수 있습니다.

`argv` 매개변수를 실제 명령줄 인자와 연결하려면 예를 들어 다음처럼 작성할 수 있습니다.

```python
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    print(list(argv))
    return 0
```

`sys.argv[0]`은 보통 실행된 스크립트나 모듈을 나타내는 값이므로, 실제 사용자 인자만 함수에 전달하려면 `sys.argv[1:]`을 사용합니다. 테스트에서는 `sys.argv`를 수정하지 않고 `main(["--help"])`처럼 원하는 인자를 직접 넘길 수 있습니다.

## `import`와 최상위 코드의 부작용

`import`는 단순히 파일 내용을 복사해 오는 동작이 아닙니다. 모듈이 처음 import될 때 Python은 그 모듈의 **최상위 문장**을 실행해 모듈 객체를 초기화합니다.

예를 들어 다음 코드는 import만 해도 출력이 발생합니다.

```python
# noisy.py
print("모듈을 불러왔습니다.")
```

```python
import noisy
```

따라서 "import는 프로그램 실행 요청이 아니다"라는 원칙은 **import할 때 아무 코드도 실행되지 않는다**는 뜻이 아닙니다. 오히려 import 과정에서도 최상위 코드가 실행되므로, 라이브러리 모듈의 최상위에서는 다음과 같은 큰 부작용을 피해야 합니다.

- 파일 삭제 또는 대량 수정
- 네트워크 요청
- 서버 시작
- 사용자 입력 대기
- 프로세스 종료
- 긴 계산 작업

상수 정의, 함수 정의, 클래스 정의처럼 모듈을 사용할 준비를 하는 작업은 최상위에 둘 수 있습니다. 실제 프로그램 동작은 `main()` 같은 함수에 넣고 명시적인 진입점에서 호출하는 편이 안전합니다.

## `__name__`과 프로그램 진입점

Python은 각 모듈에 `__name__`이라는 이름을 제공합니다.

파일을 직접 실행하면 그 파일의 `__name__`은 `"__main__"`이 됩니다.

```python
# app.py
print(__name__)
```

```sh
python3 app.py
```

출력:

```text
__main__
```

반대로 다른 코드에서 `import app`으로 불러오면 `app.py`의 `__name__`은 일반적으로 `"app"`입니다.

이 차이를 이용하면 "직접 실행했을 때만 실행할 코드"를 구분할 수 있습니다.

```python
def main() -> int:
    print("프로그램을 실행합니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

이 파일을 직접 실행하면 `main()`이 호출되지만, 다른 모듈이 `import`할 때는 `main()`이 자동 호출되지 않습니다.

작은 단일 파일 프로그램에는 이 형태로 충분합니다. 프로그램이 패키지로 커지면 보통 다음처럼 역할을 나누는 편이 명확합니다.

```text
checker/
├── __main__.py   # python -m checker의 진입점
└── cli.py        # main()과 실제 CLI 처리
```

주의할 점은 `python3 -m checker`로 `checker/__main__.py`를 실행해도 실행되는 `__main__.py`의 `__name__`은 `"__main__"`이라는 것입니다. 파일의 원래 위치만 보고 `__name__ == "checker.__main__"`이라고 생각하면 안 됩니다.

상대 import가 가능한지는 `__name__` 하나만으로 결정되지 않습니다. 패키지 문맥은 `__package__` 같은 정보와 함께 결정됩니다. 그래서 패키지 내부 진입점은 `-m`으로 실행하는 방식이 중요합니다.

## 현재 작업 디렉터리와 소스 파일 위치

다음 두 경로는 서로 다른 의미를 가집니다.

```python
from pathlib import Path

working_directory = Path.cwd()
source_directory = Path(__file__).resolve().parent
```

`Path.cwd()`는 **프로세스를 시작한 현재 작업 디렉터리**를 나타냅니다. 소스 파일이 어디에 있는지와는 무관합니다.

`Path(__file__).resolve().parent`는 현재 모듈 파일의 위치를 기준으로 한 디렉터리를 나타냅니다.

예를 들어 다음 구조를 생각해 봅니다.

```text
project/
├── data/
│   └── input.csv
└── tools/
    └── report.py
```

`project/`에서 다음 명령을 실행하면:

```sh
python3 tools/report.py
```

일반적으로 다음과 같이 생각할 수 있습니다.

```text
Path.cwd()
→ project/

Path(__file__).resolve().parent
→ project/tools/
```

따라서 코드에 있는 같은 상대 경로 문자열도 무엇을 기준으로 결합하느냐에 따라 다른 파일을 가리킵니다.

```python
from pathlib import Path

user_path = Path("data/input.csv")
bundled_path = Path(__file__).resolve().parent / "defaults.json"
```

보통 다음 원칙을 사용하면 의도가 분명해집니다.

- 사용자가 명령줄에서 전달한 상대 경로는 현재 작업 디렉터리를 기준으로 해석합니다.
- 소스 코드와 함께 배포한 리소스는 소스 또는 패키지 위치를 기준으로 찾습니다.
- 어느 기준을 사용하는지 문서와 오류 메시지에 명시합니다.

테스트가 저장소 루트에서만 우연히 통과하고 다른 디렉터리에서 실행하면 실패한다면, 코드가 현재 작업 디렉터리에 암묵적으로 의존하고 있을 가능성이 있습니다.

다만 설치된 패키지의 데이터 파일을 찾는 문제는 단순히 `__file__`에 상대 경로를 붙이는 것보다 패키지 리소스 API를 사용하는 편이 적절한 경우도 있습니다. 이 문서에서는 우선 **현재 작업 디렉터리와 소스 위치가 서로 다른 기준**이라는 점을 구분하는 데 집중합니다.

## 가상 환경과 인터프리터 확인

한 컴퓨터에 여러 Python 인터프리터와 여러 프로젝트가 공존할 수 있습니다. 따라서 터미널에서 `python`이라고 입력했을 때 어느 실행 파일이 선택되는지 확인하는 습관이 중요합니다.

프로젝트마다 가상 환경을 만들면 프로젝트가 사용하는 Python 패키지 설치 공간을 다른 프로젝트와 분리할 수 있습니다.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -c 'import sys; print(sys.executable)'
python --version
```

위 활성화 명령은 POSIX 계열 셸용입니다. Windows에서는 사용하는 셸에 맞는 활성화 명령을 선택해야 합니다.

가상 환경은 완전히 별개의 Python 구현체를 새로 만드는 개념이라기보다, 가상 환경을 생성할 때 선택한 Python 인터프리터를 바탕으로 **프로젝트 전용 실행 경로와 패키지 설치 환경**을 구성하는 기능입니다.

활성화는 편의를 위한 기능입니다. 활성화하지 않아도 가상 환경의 인터프리터를 직접 실행할 수 있습니다.

POSIX 계열에서는 예를 들어 다음과 같습니다.

```sh
.venv/bin/python -c 'import sys; print(sys.executable)'
```

현재 코드가 실제로 어떤 Python에서 실행되는지는 `sys.executable`로 확인하는 것이 가장 직접적입니다.

```python
import sys

print(sys.executable)
```

### 시스템 Python과 프로젝트 가상 환경

**시스템 Python**이라는 표현은 보통 운영체제나 시스템 도구가 제공·관리하거나, 사용자가 프로젝트 외부에서 공통으로 사용하는 Python 설치를 가리킵니다. 환경에 따라 설치 방식은 다를 수 있습니다.

프로젝트 의존성을 시스템 Python에 무분별하게 설치하면 다음 문제가 생길 수 있습니다.

- 프로젝트 A와 프로젝트 B가 서로 다른 버전의 같은 패키지를 요구할 수 있습니다.
- 운영체제나 다른 도구가 사용하는 Python 패키지와 충돌할 수 있습니다.
- 어떤 패키지가 어느 프로젝트를 위해 설치되었는지 추적하기 어려워질 수 있습니다.

가상 환경을 사용하면 프로젝트별 의존성을 분리하기 쉬워집니다.

중요한 것은 "가상 환경을 활성화했는가" 자체보다 **현재 어떤 인터프리터와 패키지 환경에서 실행하고 있는가**입니다.

## 현재 인터프리터로 하위 Python 실행하기

Python 프로그램에서 다른 Python 모듈을 하위 프로세스로 실행해야 한다면, 현재 실행 중인 인터프리터 경로를 재사용하는 편이 안전합니다.

```python
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "checker"],
    check=False,
)

raise SystemExit(result.returncode)
```

`"python3"` 같은 문자열을 직접 적으면 셸 또는 실행 환경의 `PATH`에 따라 현재 프로그램과 다른 Python이 선택될 수 있습니다.

반면 `sys.executable`을 사용하면 현재 프로그램을 실행 중인 Python 실행 파일을 그대로 지정할 수 있습니다. 가상 환경에서 실행 중이라면 보통 그 가상 환경의 Python 실행 파일이 사용됩니다.

즉 다음 둘은 의미가 다릅니다.

```python
subprocess.run(["python3", "-m", "checker"])
```

```python
subprocess.run([sys.executable, "-m", "checker"])
```

첫 번째는 `PATH`에서 `python3`를 다시 찾습니다. 두 번째는 현재 인터프리터 경로를 명시적으로 재사용합니다.

## 오류 유형부터 구분하기

오류를 해결할 때는 모든 실패를 "Python이 안 된다"로 묶지 말고 어느 단계에서 실패했는지 먼저 구분합니다.

| 실패 | 의미 | 먼저 확인할 항목 |
|---|---|---|
| `SyntaxError` | 소스 코드를 Python 문법에 맞게 해석할 수 없음 | 표시된 줄과 바로 앞 줄, 괄호·따옴표·들여쓰기 |
| `ModuleNotFoundError` | 요청한 모듈을 현재 모듈 탐색 경로와 설치 환경에서 찾지 못함 | 이름 철자, 실행 위치, `-m` 사용 여부, 설치된 의존성, `sys.executable` |
| `ImportError` | 모듈 import 과정에서 요청한 항목을 가져오지 못했거나 import 문맥에 문제가 있음 | 상대 import 여부, 순환 import, 가져오려는 이름 |
| `NameError` | 현재 이름 공간에서 해당 이름을 찾을 수 없음 | 철자, 실행되지 않은 분기, 누락된 `import`, 변수 정의 위치 |
| `TypeError` | 현재 연산이나 함수 호출이 받은 객체의 타입 또는 인자 형태와 맞지 않음 | 실제 타입, 인자 개수와 이름, 지원하는 연산 |
| 0이 아닌 종료 상태 | 프로그램 또는 하위 프로그램이 실패를 나타내는 상태로 종료함 | `stderr`, 입력 규칙, 반환 코드의 의미 |

예를 들어 `ModuleNotFoundError`가 발생했다고 해서 반드시 패키지를 새로 설치해야 하는 것은 아닙니다. 잘못된 디렉터리에서 실행했거나, 다른 가상 환경의 Python을 사용했거나, 패키지 내부 파일을 직접 실행해 import 문맥이 달라졌을 수도 있습니다.

오류 메시지는 해결 전에 지우거나 요약하지 말고, 재현 입력과 함께 보관합니다. 특히 다음 정보가 있으면 문제를 다시 확인하기 쉽습니다.

```text
실행한 명령
현재 작업 디렉터리
sys.executable
전체 traceback
입력값
종료 상태
```

## 프로젝트에 적용하기

### 필수: `data-report`

- `pyproject.toml`에서 `data-report = "data_report.cli:main"` 콘솔 스크립트를 선언합니다.
- `data_report/__main__.py`도 같은 `data_report.cli.main`을 호출합니다.
- `python -m data_report`와 설치된 `data-report` 명령이 가능한 한 같은 진입 함수와 동작 규칙을 공유하게 만듭니다.
- 소스 트리에서 실행했을 때와 설치된 패키지에서 실행했을 때 같은 입력에 대해 같은 종료 상태를 반환하는지 확인합니다.
- 테스트에서는 `main([...])`에 인자를 직접 전달해 CLI 처리 로직을 검증할 수 있게 구성합니다.

예를 들면 구조는 다음과 같이 나눌 수 있습니다.

```text
data_report/
├── __init__.py
├── __main__.py
└── cli.py
```

```python
# data_report/__main__.py
from .cli import main

raise SystemExit(main())
```

### 선택: `command-checker`

- `python -m command_checker`와 설치된 `command-checker` 명령이 같은 `main()`을 호출하게 구성합니다.
- Python으로 작성한 외부 테스트 프로그램을 하위 프로세스로 실행할 때는 가능하면 `sys.executable`을 사용합니다.
- 실행 디렉터리가 달라져도 상대 경로의 기준이 의도대로 유지되는지 확인합니다.

## 완료 기준

- Python 인터프리터, 스크립트, 모듈, 패키지의 차이를 설명할 수 있습니다.
- 파일 경로 실행과 `-m` 모듈 실행의 차이를 설명할 수 있습니다.
- 패키지 내부에서 상대 import를 사용할 때 `-m` 실행이 중요한 이유를 설명할 수 있습니다.
- 모듈을 import할 때 최상위 코드가 실행될 수 있음을 알고, 큰 부작용을 진입점 밖으로 분리했습니다.
- `main()`이 정수 종료 상태를 반환하도록 구성할 수 있습니다.
- 테스트에서 명령줄 인자를 직접 전달할 수 있습니다.
- `__name__ == "__main__"` 조건이 필요한 이유를 설명할 수 있습니다.
- 현재 사용 중인 Python 인터프리터 경로를 `sys.executable`로 확인할 수 있습니다.
- 시스템 Python과 프로젝트 가상 환경의 역할을 구분할 수 있습니다.
- 현재 작업 디렉터리와 소스 파일 디렉터리가 서로 다른 기준임을 설명할 수 있습니다.
- 상대 경로가 어떤 디렉터리를 기준으로 해석되는지 문서와 코드에서 명확히 할 수 있습니다.

다음은 [객체와 컬렉션](02-objects-and-collections.md)입니다.
