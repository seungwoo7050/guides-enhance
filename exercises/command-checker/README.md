# command-checker

`command-checker`는 JSON에 기록한 예상값에 따라 외부 CLI 프로그램을 실행하고 `returncode`, `stdout`, `stderr`를 검사하는 Python 도구입니다.

단순한 출력 비교에 그치지 않고 다음 상황까지 처리합니다.

- 타임아웃
- `stdout`과 `stderr`에 각각 적용하는 출력 상한
- 자식 프로세스를 포함한 POSIX 프로세스 그룹 종료
- 제한된 병렬 실행
- 입력 순서를 유지하는 결과 수집
- JSON/JUnit 보고서
- 완성된 임시 파일을 사용한 보고서 교체
- 외부 의존성이 없는 wheel 빌드

## 요구 환경

- Python 3.12 이상
- macOS 또는 Linux

실행 시 필요한 외부 Python 패키지는 없습니다. 프로세스 그룹 종료와 논블로킹 파일 디스크립터 처리는 POSIX 환경을 기준으로 구현했습니다.

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

## 설치

프로젝트 디렉터리에서 설치합니다.

```sh
python3 -m pip install .
command-checker --help
```

설치하지 않고 모듈로 실행할 수도 있습니다.

```sh
python3 -m command_checker --help
```

두 실행 방법은 모두 `command_checker.cli.main()`을 호출합니다.

## 사용법

```text
command-checker --cases CASES [--jobs N]
                [--json-report PATH]
                [--junit-report PATH]
                -- COMMAND [ARG ...]
```

포함된 예제를 실행하려면 다음 명령을 사용합니다.

```sh
python3 -m command_checker \
  --cases examples/sort_cases.json \
  --jobs 2 \
  -- \
  python3 examples/line_sort.py
```

모든 사례가 일치하면 각 사례의 `PASS`와 전체 요약을 `stdout`에 출력하고 종료 상태 0을 반환합니다.

## 사례 명세

최상위 JSON 값은 비어 있지 않은 배열이어야 합니다.

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

### `cwd`

`cwd`를 생략하거나 `null`로 지정하면 `command-checker`의 현재 작업 디렉터리를 상속합니다.

문자열을 지정하면 사례 파일이 있는 디렉터리를 기준으로 해석합니다. 절대 경로와 빈 문자열은 거부합니다. `..`는 허용하므로 `cwd`를 샌드박스 용도로 사용하면 안 됩니다.

### `env`

`env`는 부모 프로세스의 환경 변수 위에 덮어씁니다. 키에는 NUL과 `=`을 사용할 수 없고 값에는 NUL을 사용할 수 없습니다.

### 실행 파일 선택

검사할 실행 파일은 모든 사례를 시작하기 전에 한 번 선택합니다.

- 경로 구분자가 없는 명령은 호출 환경의 `PATH`에서 찾습니다.
- 경로 구분자가 있는 명령은 호출 당시 작업 디렉터리를 기준으로 절대 경로를 만듭니다.

선택한 절대 경로를 모든 사례에서 사용하므로 사례별 `cwd`나 `env.PATH`가 실행 파일을 바꾸지 못합니다.

## 결과 비교

다음 값을 각각 정확히 비교합니다.

- `returncode`
- `stdout`
- `stderr`

공백과 줄바꿈도 결과에 포함합니다. 앞뒤 공백 제거 또는 줄바꿈 정규화를 암묵적으로 수행하지 않습니다.

타임아웃과 출력 상한 초과는 일반 출력 불일치와 별도로 기록합니다. 이 두 경우에는 프로세스를 더 기다리지 않고 정리 절차를 시작합니다.

## 종료 상태

| 종료 상태 | 의미 |
|---:|---|
| `0` | 모든 사례가 예상값과 일치함 |
| `1` | 실행은 끝났지만 하나 이상의 사례가 일치하지 않음 |
| `2` | 명세, 실행 파일, 프로세스 관리 또는 보고서 저장 오류 |

사례 하나가 예상과 다르더라도 다른 사례는 계속 실행합니다. 반면 실행 파일을 찾을 수 없거나 프로세스를 시작할 수 없으면 검사를 정상적으로 수행할 수 없으므로 종료 상태 2를 반환합니다.

## 프로세스 실행과 정리

각 대상은 `start_new_session=True`로 별도 POSIX 프로세스 그룹에서 시작합니다.

`stdin`, `stdout`, `stderr`를 논블로킹 모드로 전환하고 하나의 `selector`에서 다음 상태를 처리합니다.

- 아직 보내지 않은 `stdin`의 위치
- `stdout`과 `stderr`에서 읽을 수 있는 바이트
- 각 스트림에 저장한 바이트 수
- 절대 마감 시각
- 부모 프로세스 종료 여부

### 타임아웃

마감 시각이 지나면 프로세스 그룹 전체에 `SIGTERM`을 보냅니다. 짧은 유예 시간 뒤에도 프로세스가 남아 있으면 `SIGKILL`을 보냅니다. 마지막으로 직접 시작한 부모 프로세스를 `wait()`로 회수합니다.

### 출력 상한

`stdout`과 `stderr`에 각각 `output_limit`을 적용합니다. 상한을 넘긴 스트림은 최대 허용 바이트까지만 보관하고 프로세스 그룹을 정리합니다.

### 자식 프로세스

부모가 먼저 종료하더라도 자식 프로세스가 파이프를 열어 둔 채 남아 있을 수 있습니다. `selector`는 파이프가 닫힐 때까지 확인하며, 마감 시각을 넘으면 같은 프로세스 그룹 정리 절차를 적용합니다.

### 예외 발생 시 정리

수집 중 예상하지 못한 예외가 발생해도 `run_case()`가 자신이 시작한 프로세스 그룹을 정리한 뒤 원래 예외를 다시 발생시킵니다.

## 병렬 실행

`--jobs`가 1이면 순차적으로 실행합니다. 2 이상이면 다음 방식으로 실행합니다.

```python
ThreadPoolExecutor(max_workers=jobs)
```

`executor.map()`을 사용하므로 실제 완료 순서와 관계없이 입력 JSON의 사례 순서대로 `Result`를 반환합니다.

각 작업자는 자신이 시작한 프로세스와 파이프만 관리하고 `Result`를 반환합니다. JSON/JUnit 파일은 모든 결과가 확정된 뒤 주 스레드에서 작성합니다.

## 보고서

```sh
python3 -m command_checker \
  --cases examples/sort_cases.json \
  --json-report artifacts/result.json \
  --junit-report artifacts/result.xml \
  -- \
  python3 examples/line_sort.py
```

JSON과 JUnit은 터미널 출력에 사용한 것과 같은 `Result` 목록으로 만듭니다.

보고서는 다음 순서로 저장합니다.

```text
최종 파일과 같은 디렉터리에 임시 파일을 만듭니다.
→ 전체 내용을 기록합니다.
→ flush와 fsync를 수행합니다.
→ os.replace로 최종 경로를 교체합니다.
```

기록 중 실패하면 임시 파일을 삭제하고 기존 보고서는 그대로 둡니다.

JUnit에 들어가는 사례 이름, 실패 메시지, `stdout`, `stderr`에는 XML 1.0에서 허용하지 않는 문자가 있을 수 있습니다. 이런 문자는 대체 문자로 바꿉니다.

## 테스트

표준 라이브러리 `unittest`를 사용합니다.

```sh
python3 -m unittest discover -s tests -v
```

테스트는 다음 동작을 확인합니다.

- JSON 필드 검증과 상대 `cwd` 해석
- 환경 변수 정렬과 저장
- 인자, `stdin`, `stdout`, `stderr`, `returncode` 보존
- 타임아웃과 출력 상한을 서로 다른 실패로 기록
- 출력 상한까지만 바이트를 보관
- 병렬 완료 순서와 관계없이 입력 순서 유지
- JSON과 JUnit이 같은 결과를 사용
- XML 1.0에서 허용하지 않는 문자 교체
- 예제와 두 보고서의 종단 간 실행
- POSIX 타임아웃 뒤 자식 프로세스를 포함한 프로세스 그룹 종료

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

## 범위와 제한

- Python 3.12 이상을 대상으로 합니다.
- Windows 네이티브 프로세스 트리 종료는 지원하지 않습니다.
- 셸 파이프라인 문법을 해석하지 않습니다. 명령과 인자는 분리된 목록으로 받습니다.
- UTF-8 텍스트 CLI를 검사합니다. 디코딩할 수 없는 바이트는 대체 문자로 바꿉니다.
- `cwd`는 실행 위치를 정할 뿐 샌드박스를 제공하지 않습니다.
- JSON과 JUnit을 하나의 트랜잭션으로 묶지는 않습니다.
- 원격 실행, 컨테이너 오케스트레이션, 분산 스케줄링은 다루지 않습니다.
