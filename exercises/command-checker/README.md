# command-checker

`command-checker`는 JSON에 기록한 기대값에 따라 외부 CLI 프로그램을 실제 프로세스로 실행하고 `returncode`, `stdout`, `stderr`를 검사하는 Python 도구입니다.

함수를 직접 호출하는 테스트와 달리 CLI 검사는 운영체제 프로세스 경계를 통과합니다. 따라서 단순한 출력 문자열 비교뿐 아니라 실행 시간, 출력 크기, 자식 프로세스 정리, 병렬 실행 순서, 보고서 저장처럼 **실제 실행 환경에서만 드러나는 동작**도 함께 다룹니다.

다음 상황을 처리합니다.

- 타임아웃
- `stdout`과 `stderr`에 각각 적용하는 출력 상한
- 자식 프로세스를 포함한 POSIX 프로세스 그룹 종료
- 제한된 병렬 실행
- 실제 완료 순서와 관계없이 입력 순서를 유지하는 결과 수집
- JSON/JUnit 보고서
- 완성된 임시 파일을 사용한 보고서 교체
- 외부 런타임 의존성이 없는 wheel 빌드

## 요구 환경

- Python 3.12 이상
- macOS 또는 Linux

실행 시 필요한 외부 Python 패키지는 없습니다.

프로세스 그룹 종료와 논블로킹 파일 디스크립터 처리는 POSIX 환경을 기준으로 구현합니다. 따라서 Windows 네이티브 프로세스 트리 종료는 이 프로젝트의 지원 범위에 포함하지 않습니다.

## 프로젝트 구성

```text
command-checker/
├── README.md
├── pyproject.toml
├── _command_checker_build.py
├── command_checker/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── comparison.py
│   ├── model.py
│   ├── process.py
│   ├── reports.py
│   ├── runner.py
│   ├── specification.py
│   └── py.typed
├── examples/
│   ├── line_sort.py
│   └── sort_cases.json
└── tests/
    ├── fixture_program.py
    └── test_command_checker.py
```

| 파일 | 수행하는 작업 |
|---|---|
| `model.py` | 검증된 `Case`, 실행 결과 `Result`, 입력·실행 예외 정의 |
| `comparison.py` | 수집한 종료 상태와 두 출력 스트림을 예상값과 비교 |
| `specification.py` | JSON을 읽고 필드·경로·환경 값을 검사해 `Case`로 변환 |
| `process.py` | 프로세스 시작, 파이프 수집, 마감 시각 확인, 신호 전송과 정리 |
| `runner.py` | 실행 파일 선택, 순차·병렬 실행, 결과 출력, 종료 상태 계산 |
| `reports.py` | JSON/JUnit 문자열 생성과 보고서 파일 교체 |
| `cli.py` | 인자 파싱, 오류 메시지, 전체 기능 호출 |
| `_command_checker_build.py` | wheel 메타데이터와 패키지 파일 생성 |

모듈을 이렇게 나누는 이유는 프로세스 실행, 결과 비교, 명세 검증, 보고서 저장이 서로 다른 이유로 변경되기 때문입니다. 예를 들어 JUnit 형식이 바뀌어도 `process.py`는 바뀔 필요가 없고, 타임아웃 처리 방식이 바뀌어도 JSON 사례 검증 규칙은 독립적으로 유지할 수 있습니다.

## 설치

프로젝트 디렉터리에서 설치합니다.

```sh
python3 -m pip install .
command-checker --help
```

설치하지 않고 소스 트리에서 모듈로 실행할 수도 있습니다.

```sh
python3 -m command_checker --help
```

두 실행 방법은 모두 `command_checker.cli.main()`을 호출합니다.

```text
python3 -m command_checker
        │
        └── command_checker.__main__
                └── cli.main()

command-checker
        │
        └── 설치된 console script
                └── cli.main()
```

진입점마다 인자 파싱이나 종료 상태 처리를 따로 구현하지 않으므로 두 실행 방법의 동작이 달라지는 일을 피할 수 있습니다.

## 사용법

```text
command-checker --cases CASES [--jobs N]
                [--json-report PATH]
                [--junit-report PATH]
                -- COMMAND [ARG ...]
```

`--` 앞은 `command-checker` 자체의 인자이고, `--` 뒤는 검사할 대상 명령과 기본 인자입니다.

포함된 예제를 실행하려면 다음 명령을 사용합니다.

```sh
python3 -m command_checker \
  --cases examples/sort_cases.json \
  --jobs 2 \
  -- \
  python3 examples/line_sort.py
```

모든 사례가 일치하면 각 사례의 `PASS`와 전체 요약을 `stdout`에 출력하고 종료 상태 0을 반환합니다.

사례가 하나 이상 불일치하면 다른 사례도 계속 실행한 뒤 전체 종료 상태 1을 반환합니다. 명세 오류나 프로세스 시작 실패처럼 검사를 정상적으로 수행할 수 없는 문제가 생기면 종료 상태 2를 반환합니다.

## 사례 명세

최상위 JSON 값은 **비어 있지 않은 배열**이어야 합니다. 배열의 각 원소는 서로 이름이 다른 하나의 실행 사례를 나타냅니다.

```json
[
  {
    "name": "ascending",
    "stdin": "3 1 2\n",
    "stdout": "1\n2\n3\n",
    "stderr": "",
    "returncode": 0
  }
]
```

지원하는 필드는 다음과 같습니다.

| 필드 | 형식 | 기본값 |
|---|---|---|
| `name` | 비어 있지 않은 문자열 | 필수 |
| `args` | 문자열 배열 | `[]` |
| `stdin` | 문자열 | `""` |
| `stdout` | 문자열 | `""` |
| `stderr` | 문자열 | `""` |
| `returncode` | 정수 | `0` |
| `timeout` | 유한한 양수 | `2.0` |
| `output_limit` | 양의 정수 바이트 수 | `1048576` |
| `cwd` | 비어 있지 않은 상대 경로 또는 `null` | `null` |
| `env` | 문자열 키와 값으로 이루어진 객체 | `{}` |

각 사례는 다음 실행을 의미합니다.

```text
고정된 실행 파일
+ 기본 명령 인자
+ 사례별 args
+ 사례별 stdin
+ 사례별 cwd
+ 부모 환경에 사례별 env를 덮어쓴 환경
→ 프로세스 실행
```

실행 뒤 실제 `returncode`, `stdout`, `stderr`를 사례에 기록된 기대값과 비교합니다.

### `cwd`

`cwd`를 생략하거나 `null`로 지정하면 `command-checker`의 현재 작업 디렉터리를 상속합니다.

문자열을 지정하면 사례 파일이 있는 디렉터리를 기준으로 해석합니다.

예를 들어 사례 파일이 다음 위치에 있다고 가정합니다.

```text
/project/tests/cases.json
```

사례에 다음 값을 지정하면:

```json
{
  "cwd": "../fixture"
}
```

실행 디렉터리는 사례 파일의 위치를 기준으로 계산됩니다.

```text
/project/tests/../fixture
→ /project/fixture
```

절대 경로와 빈 문자열은 거부합니다.

`..`는 허용하므로 `cwd`는 단순히 실행 위치를 선택하는 기능일 뿐 **파일 시스템 샌드박스가 아닙니다.** 대상 프로그램의 파일 접근을 격리하는 보안 경계로 사용해서는 안 됩니다.

### `env`

`env`는 부모 프로세스의 환경 변수를 모두 버리고 새 환경을 만드는 값이 아닙니다. 부모 환경을 복사한 뒤 사례에서 지정한 키만 덮어씁니다.

```text
부모 환경
+ 사례의 env
→ 대상 프로세스 환경
```

키에는 NUL과 `=`을 사용할 수 없고 값에는 NUL을 사용할 수 없습니다. 이는 운영체제 프로세스 환경 변수 표현에서 허용되지 않는 값을 미리 거부하기 위한 검증입니다.

### `timeout`

`timeout`은 각 사례가 실행을 끝내야 하는 최대 시간입니다.

다음과 같은 값은 허용하지 않습니다.

```text
0
음수
NaN
Infinity
```

타임아웃이 발생하면 단순히 `Result`를 실패로 표시하는 데서 끝나지 않고 대상 프로세스 그룹 정리 절차를 시작합니다.

### `output_limit`

`output_limit`은 `stdout`과 `stderr`에 **각각** 적용하는 최대 바이트 수입니다.

예를 들어 `1048576`이면 다음 두 제한이 독립적으로 존재합니다.

```text
stdout ≤ 1 MiB
stderr ≤ 1 MiB
```

문자 수가 아니라 UTF-8로 디코딩하기 전 수집한 **바이트 수**를 기준으로 제한합니다. UTF-8에서는 문자 하나가 여러 바이트일 수 있기 때문입니다.

## 실행 파일 선택

검사할 실행 파일은 모든 사례를 시작하기 전에 한 번 선택합니다.

### 경로 구분자가 없는 명령

예를 들어:

```text
python3
```

호출 환경의 `PATH`에서 한 번 찾고 절대 경로로 고정합니다.

```text
python3
→ /usr/bin/python3
```

### 경로 구분자가 있는 명령

예를 들어:

```text
./bin/tool
```

호출 당시 `command-checker`의 작업 디렉터리를 기준으로 절대 경로를 만듭니다.

### 한 번만 선택하는 이유

선택한 절대 경로는 모든 사례에서 그대로 사용합니다.

따라서 사례별 `cwd`나 `env.PATH`가 달라져도 실행 파일 자체는 바뀌지 않습니다.

```text
호출 환경 PATH에서 tool 선택
→ /opt/tools/tool

case A env.PATH = /tmp/a
case B env.PATH = /tmp/b

두 사례 모두 /opt/tools/tool 실행
```

사례별 `PATH`에서 실행 파일을 다시 찾는 구현은 같은 검사 실행 안에서 서로 다른 프로그램을 실행할 수 있으므로 잘못된 구현입니다.

## 결과 비교

다음 값을 각각 정확히 비교합니다.

- `returncode`
- `stdout`
- `stderr`

공백과 줄바꿈도 결과에 포함합니다. 앞뒤 공백 제거 또는 줄바꿈 정규화를 암묵적으로 수행하지 않습니다.

예를 들어 다음 두 출력은 서로 다릅니다.

```text
"ok\n"
"ok"
```

CLI 출력의 마지막 줄바꿈도 외부 동작의 일부이기 때문입니다.

타임아웃과 출력 상한 초과는 일반적인 문자열 또는 종료 상태 불일치와 별도로 기록합니다.

```text
returncode 불일치
stdout 불일치
stderr 불일치
timeout
output_limit 초과
```

이 구분을 유지해야 사용자가 프로그램이 틀린 이유를 정확히 알 수 있습니다.

## 종료 상태

| 종료 상태 | 의미 |
|---:|---|
| `0` | 모든 사례가 예상값과 일치함 |
| `1` | 대상 프로그램은 실행했지만 하나 이상의 사례가 일치하지 않음 |
| `2` | 명세, 실행 파일, 프로세스 관리 또는 보고서 저장 오류 |

종료 상태 1과 2는 의미가 다릅니다.

```text
1 → 검사할 수 있었고 대상 프로그램의 결과가 기대와 다름
2 → 검사를 정상적으로 수행하거나 마무리할 수 없음
```

예를 들어 사례 하나의 `stdout`이 틀리면 종료 상태 1입니다. 반면 사례 JSON이 잘못되어 `Case`를 만들 수 없다면 종료 상태 2입니다.

사례 하나가 예상과 다르더라도 다른 사례는 계속 실행합니다. 사용자는 한 번의 검사로 가능한 많은 불일치를 확인할 수 있습니다.

반면 실행 파일을 찾을 수 없거나 프로세스를 시작할 수 없다면 검사를 정상적으로 수행할 수 없으므로 종료 상태 2를 반환합니다.

## 프로세스 실행과 정리

각 대상은 `start_new_session=True`로 별도 POSIX 세션에서 시작합니다. 이때 대상 프로세스는 독립된 프로세스 그룹의 기준이 되며, 타임아웃이나 출력 상한 초과 시 그룹 전체를 종료 대상으로 삼을 수 있습니다.

```text
command-checker
   │
   └── 새 POSIX 세션/프로세스 그룹
         └── target
               └── child
```

`stdin`, `stdout`, `stderr`를 논블로킹 모드로 전환하고 하나의 `selector`에서 다음 상태를 처리합니다.

- 아직 보내지 않은 `stdin`의 위치
- `stdout`과 `stderr`에서 읽을 수 있는 바이트
- 각 스트림에 저장한 바이트 수
- 절대 마감 시각
- 직접 시작한 부모 프로세스 종료 여부
- 파이프가 여전히 열려 있는지

### 왜 세 파이프를 함께 처리하는가

`stdout`을 전부 읽은 뒤 `stderr`를 읽는 식으로 한 스트림씩 처리하면 교착이 생길 수 있습니다.

예를 들어 대상 프로그램이 `stderr`를 대량 출력한다고 가정합니다.

```text
대상 프로그램이 stderr를 계속 씀
→ stderr 파이프 버퍼가 가득 참
→ 대상 프로그램이 stderr 쓰기에서 멈춤
→ 검사기는 stdout EOF만 기다림
→ 대상 프로그램은 종료할 수 없음
```

논블로킹 I/O와 `selector`를 사용하면 준비된 스트림만 조금씩 처리하면서 `stdin`, `stdout`, `stderr`, 타임아웃을 한 실행 루프에서 함께 관리할 수 있습니다.

### 타임아웃

각 사례는 시작 시점에서 계산한 절대 마감 시각을 가집니다.

마감 시각이 지나면 다음 순서로 정리합니다.

```text
프로세스 그룹 전체에 SIGTERM
→ 짧은 유예 시간 동안 종료 확인
→ 남아 있으면 SIGKILL
→ 직접 시작한 부모 프로세스를 wait()로 회수
→ 남은 파이프 정리
```

`SIGTERM`은 대상이 정상적인 정리 작업을 수행할 기회를 주고, `SIGKILL`은 응답하지 않는 프로세스를 강제로 끝내기 위한 마지막 수단입니다.

### 출력 상한

`stdout`과 `stderr`에 각각 `output_limit`을 적용합니다.

상한을 넘긴 스트림은 최대 허용 바이트까지만 보관하고 프로세스 그룹 정리를 시작합니다.

예를 들어 제한이 1024바이트라면:

```text
stdout에서 1300바이트 발생
→ 최대 1024바이트까지만 결과에 보관
→ output_limit 초과로 기록
→ 프로세스 그룹 정리
```

상한을 넘긴 뒤에도 계속 출력 전체를 메모리에 저장하면 출력 제한이 메모리 사용을 제한하는 안전장치 역할을 하지 못합니다.

### 자식 프로세스

직접 시작한 부모 프로세스가 먼저 종료하더라도 자식 프로세스가 `stdout` 또는 `stderr` 파이프를 상속받아 열어 둔 채 남아 있을 수 있습니다.

```text
target 종료
└── child 계속 실행
      └── stdout/stderr 파이프 열려 있음
```

이 경우 부모의 종료만 보고 수집을 끝내면 자식 프로세스가 남을 수 있습니다.

`selector`는 파이프 상태까지 확인하며, 마감 시각을 넘으면 같은 프로세스 그룹 정리 절차를 적용합니다.

### 예외 발생 시 정리

수집 중 예상하지 못한 예외가 발생해도 `run_case()`가 자신이 시작한 프로세스 그룹을 정리한 뒤 원래 예외를 다시 발생시킵니다.

즉, 프로세스를 시작한 함수가 그 프로세스와 파이프의 정리 책임도 가집니다.

```text
run_case()가 프로세스 시작
→ 정상 종료든 예외든
→ run_case()가 프로세스 그룹과 파이프 정리
```

상위 코드가 프로세스가 남아 있는지 추측하거나 별도의 복구 절차를 알아야 하지 않도록 소유권을 한 위치에 둡니다.

## 병렬 실행

`--jobs`가 1이면 순차적으로 실행합니다.

2 이상이면 다음 방식으로 실행합니다.

```python
ThreadPoolExecutor(max_workers=jobs)
```

`max_workers`는 동시에 실행되는 사례 수를 제한합니다. 모든 사례를 무제한으로 한꺼번에 시작하지 않습니다.

`executor.map()`을 사용하므로 실제 완료 순서와 관계없이 입력 JSON의 사례 순서대로 `Result`를 반환합니다.

예를 들어 입력 순서가:

```text
0: slow
1: fast
2: medium
```

실제 완료 순서는 다음일 수 있습니다.

```text
1 → 2 → 0
```

하지만 최종 결과 순서는 그대로 유지합니다.

```text
0 → 1 → 2
```

이렇게 해야 `--jobs 1`과 `--jobs 4`가 같은 사례 파일에 대해 사용자에게 같은 순서의 결과를 보여 줍니다.

각 작업자는 자신이 시작한 프로세스와 파이프만 관리하고 `Result`를 반환합니다.

JSON/JUnit 파일은 모든 결과가 확정된 뒤 주 스레드에서 작성합니다. 작업자가 같은 보고서 파일을 동시에 수정하지 않습니다.

## 보고서

보고서를 만들려면 다음과 같이 경로를 지정합니다.

```sh
python3 -m command_checker \
  --cases examples/sort_cases.json \
  --json-report artifacts/result.json \
  --junit-report artifacts/result.xml \
  -- \
  python3 examples/line_sort.py
```

JSON과 JUnit은 터미널 출력에 사용한 것과 **같은 `Result` 목록**으로 만듭니다.

```text
모든 사례 실행
→ Result 목록 확정
   ├── 터미널 출력
   ├── JSON
   └── JUnit
```

보고서 형식마다 대상 프로그램을 다시 실행하지 않습니다. 그래야 두 보고서가 동일한 실행 사실을 표현합니다.

### 보고서 저장

보고서는 다음 순서로 저장합니다.

```text
최종 파일과 같은 디렉터리에 임시 파일을 만듭니다.
→ 전체 내용을 기록합니다.
→ flush를 수행합니다.
→ fsync를 수행합니다.
→ 파일을 닫습니다.
→ os.replace로 최종 경로를 교체합니다.
```

최종 경로에 직접 쓰면 기록 도중 오류가 발생했을 때 절반만 작성된 파일이 남을 수 있습니다.

임시 파일을 완성한 뒤 교체하면 기존 보고서는 새 보고서가 완성되기 전까지 유지됩니다.

기록 중 실패하면 임시 파일을 삭제하고 기존 보고서는 그대로 둡니다.

### JUnit과 XML 1.0 문자

JUnit에 들어가는 동적 텍스트에는 다음 값이 포함됩니다.

- 사례 이름
- 실패 메시지
- `stdout`
- `stderr`

이 값에는 XML 1.0에서 허용하지 않는 코드 포인트가 포함될 수 있습니다.

이런 문자는 JUnit 직렬화 단계에서 대체 문자로 바꿉니다.

중요한 점은 **실제 결과 비교용 문자열을 바꾸는 것이 아니라 XML로 쓸 때만 정리한다는 것**입니다.

```text
실제 stdout
├── 비교에는 원본 사용
└── JUnit에는 XML 안전 문자로 변환
```

## 테스트

표준 라이브러리 `unittest`를 사용합니다.

```sh
python3 -m unittest discover -s tests -v
```

테스트는 다음 동작을 확인합니다.

- JSON 최상위 구조와 필드 타입 검증
- 상대 `cwd` 해석
- 환경 변수 키와 값의 검증 및 저장
- 인자, `stdin`, `stdout`, `stderr`, `returncode` 보존
- 타임아웃과 출력 상한을 서로 다른 실패로 기록
- 출력 상한까지만 바이트를 보관
- 병렬 완료 순서와 관계없이 입력 순서 유지
- JSON과 JUnit이 같은 결과를 사용
- XML 1.0에서 허용하지 않는 문자 교체
- 예제와 두 보고서의 종단 간 실행
- POSIX 타임아웃 뒤 자식 프로세스를 포함한 프로세스 그룹 종료

프로세스 관련 테스트는 운영체제에 설치된 임의의 외부 명령보다 `tests/fixture_program.py`처럼 원하는 동작을 정확히 재현하는 전용 프로그램을 사용합니다.

예를 들어 테스트용 프로그램은 다음 동작을 만들 수 있습니다.

```text
즉시 성공
stderr 출력 후 실패
오랫동안 대기
stdout 무한 출력
자식 프로세스 생성
stdout과 stderr 동시 대량 출력
```

이렇게 하면 검사기의 특정 실패 경로를 반복해서 재현할 수 있습니다.

## Wheel 빌드

외부 의존성이 없는 작은 PEP 517 빌드 백엔드를 포함합니다.

```sh
python3 -m pip wheel --no-deps . -w dist
```

빌드 백엔드는 다음 항목을 확인합니다.

- 프로젝트 이름이 `command-checker`인지
- 콘솔 스크립트가 `command_checker.cli:main`인지
- 버전 형식이 지원 범위에 맞는지
- 패키지 모듈과 `py.typed`가 wheel에 포함되는지
- `RECORD`의 해시와 크기가 실제 파일과 일치하는지

wheel 파일의 타임스탬프를 고정하고 파일을 이름순으로 기록해 같은 소스에서 같은 내용을 만들 수 있도록 합니다.

이 결정성은 “wheel 파일 이름만 같다”는 뜻이 아니라, 같은 입력 소스와 같은 빌드 규칙에서 생성되는 archive 항목의 순서와 메타데이터 차이를 줄여 결과를 비교하기 쉽게 만드는 것을 목표로 합니다.

빌드된 wheel은 소스 트리에서만 확인하지 말고 새 가상 환경에 설치한 뒤 저장소 밖에서 콘솔 스크립트를 실행해 확인합니다.

```text
wheel 생성
→ 새 가상 환경
→ wheel 설치
→ 저장소 밖으로 이동
→ command-checker 실행
```

이 검사는 소스 루트가 `sys.path`에 있을 때만 성공하는 잘못된 패키징을 잡는 데 필요합니다.

## Implementation Order

아래 순서는 소스 파일 배치나 실행 순서가 아니라 완성된 프로젝트를 처음부터 구현할 때의 구성 순서입니다. 한 번호는 소스 코드에서 한 번만 사용합니다.

| Order | Responsibility | Primary anchor |
|---:|---|---|
| `1` | Package metadata and runtime requirements | `pyproject.toml` |
| `1-1` | Module entry-point delegation | `command_checker/__main__.py` |
| `2` | Immutable case values | `command_checker/model.py:Case` |
| `2-1` | Immutable execution results | `command_checker/model.py:Result` |
| `2-2` | Specification and execution errors | `command_checker/model.py` |
| `3` | Process-result comparison | `command_checker/comparison.py:compare_observation` |
| `4` | JSON scalar and collection validation | `command_checker/specification.py` |
| `4-1` | Case field validation and conversion | `command_checker/specification.py:_case` |
| `4-2` | Case file loading and duplicate-name checks | `command_checker/specification.py:load_cases` |
| `5` | Executable path selection | `command_checker/runner.py:validate_executable` |
| `5-1` | Per-case process start and result creation | `command_checker/process.py:run_case` |
| `6` | Sequential case execution | `command_checker/runner.py:run_cases` |
| `6-1` | PASS/FAIL output placement | `command_checker/runner.py:print_results` |
| `6-2` | Final match exit status | `command_checker/runner.py:exit_status` |
| `7` | Process-group termination and parent reap | `command_checker/process.py:_terminate_group` |
| `7-1` | Non-blocking pipe collection and limits | `command_checker/process.py:_collect_process` |
| `7-2` | Cleanup after collection failure | `command_checker/process.py:run_case` |
| `8` | Temporary-file write and atomic replacement | `command_checker/reports.py:atomic_write_text` |
| `8-1` | JSON report generation | `command_checker/reports.py:render_json` |
| `8-2` | XML-safe JUnit report generation | `command_checker/reports.py:xml_text` |
| `9` | Bounded parallel case execution | `command_checker/runner.py:run_cases` |
| `10` | Localized parser error handling | `command_checker/cli.py:CommandCheckerArgumentParser` |
| `10-1` | Public CLI arguments | `command_checker/cli.py:build_parser` |
| `10-2` | Command separator and jobs validation | `command_checker/cli.py:parse_arguments` |
| `10-3` | Case execution, reports, and exit status | `command_checker/cli.py:main` |
| `10-4` | Build metadata validation | `_command_checker_build.py:_project` |
| `10-5` | Wheel file and RECORD generation | `_command_checker_build.py:build_wheel` |
| `11` | Project behavior verification | `tests/test_command_checker.py:CommandCheckerTests` |

이 순서는 복잡한 프로세스 관리부터 시작하지 않고, 데이터 모델과 순수 비교 함수처럼 외부 상태가 없는 부분을 먼저 고정한 뒤 실제 프로세스, 보고서, 병렬 실행을 단계적으로 추가하도록 구성되어 있습니다.

## 범위와 제한

- Python 3.12 이상을 대상으로 합니다.
- Windows 네이티브 프로세스 트리 종료는 지원하지 않습니다.
- 셸 파이프라인 문법을 해석하지 않습니다. 명령과 인자는 분리된 목록으로 받습니다.
- UTF-8 텍스트 CLI를 검사합니다.
- 디코딩할 수 없는 바이트는 대체 문자로 바꿉니다.
- `cwd`는 실행 위치를 정할 뿐 샌드박스를 제공하지 않습니다.
- JSON과 JUnit을 하나의 트랜잭션으로 묶지는 않습니다.
- 원격 실행, 컨테이너 오케스트레이션, 분산 스케줄링은 다루지 않습니다.

셸 파이프라인을 해석하지 않는다는 것은 다음 문자열을 셸 문법으로 다시 파싱하지 않는다는 뜻입니다.

```text
producer | consumer
```

대신 실행 파일과 인자를 이미 분리된 목록으로 취급합니다. 이 범위 제한은 셸 인용 규칙과 명령 주입 문제를 검사기 자체의 책임에서 제외합니다.