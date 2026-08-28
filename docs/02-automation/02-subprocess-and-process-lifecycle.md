# 외부 프로세스와 수명 관리

> 선택 심화 문서입니다. 일반 Python 개발의 필수 선행 과정은 아닙니다.

## 학습 목표

Python 프로그램이 다른 프로그램을 실행하면 프로세스, 파이프, 파일 디스크립터와 실행 시간에 따라 달라지는 실패를 직접 다뤄야 합니다. 이 문서에서는 다음 내용을 설명합니다.

- 명령과 인자를 분리해서 전달하는 이유
- `stdin`, `stdout`, `stderr`, 종료 상태 수집
- 작업 디렉터리와 환경 변수 전달
- 타임아웃과 출력 상한
- 부모와 자식 프로세스를 함께 정리하는 방법
- 논블로킹 파이프로 교착을 피하는 방법

연결 프로젝트는 [`command-checker`](../../exercises/command-checker/README.md)입니다.

## 선행 개념

- CLI의 인자, `stdin`, `stdout`, `stderr`, 종료 상태를 구분할 수 있어야 합니다.
- 컨텍스트 관리자와 `try/finally`로 자원을 정리할 수 있어야 합니다.
- 파일과 JSON 입력을 검증할 수 있어야 합니다.

## 명령과 인자를 목록으로 전달하기

```python
import subprocess

result = subprocess.run(
    ["git", "status", "--short"],
    text=True,
    encoding="utf-8",
    errors="replace",
    capture_output=True,
    check=False,
)
```

목록의 원소 하나가 명령줄 인자 하나가 됩니다. 원소 안에 공백이 있어도 다시 여러 인자로 나뉘지 않습니다.

다음 코드는 신뢰할 수 없는 입력을 셸 문법으로 다시 해석하게 만들 수 있습니다.

```python
subprocess.run(
    f"grep {user_input} application.log",
    shell=True,
)
```

셸 확장, 파이프, 리디렉션이 실제 요구사항이 아니라면 기본값인 `shell=False`와 인자 목록을 사용합니다.

```python
subprocess.run(
    ["grep", user_input, "application.log"],
    check=False,
)
```

## 종료 상태와 두 출력 스트림 분리하기

```python
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "tool.py"],
    input="3 1 2\n",
    text=True,
    encoding="utf-8",
    errors="replace",
    capture_output=True,
    check=False,
)
```

확인할 값은 다음과 같습니다.

```text
result.returncode
result.stdout
result.stderr
```

0이 아닌 종료 상태도 정상적인 비교 대상이라면 `check=True`를 사용하지 않습니다. `check=True`는 0이 아닌 종료 상태를 `CalledProcessError`로 바꾸므로 출력 비교 코드가 예외 처리로 이동합니다.

## 현재 Python 인터프리터 재사용하기

```python
import sys

command = [sys.executable, "-m", "sample"]
```

현재 가상 환경과 Python 버전을 그대로 사용하려면 `python3` 문자열을 직접 적지 말고 `sys.executable`을 사용합니다.

## 실행 파일을 한 번 선택하기

경로 구분자가 없는 명령을 각 사례의 환경에서 다시 찾으면 사례별 `PATH`가 서로 다른 실행 파일을 선택할 수 있습니다. 검사 대상이 실행 중에 바뀌면 결과를 비교하기 어렵습니다.

```text
호출한 환경의 `PATH`에서 실행 파일을 찾습니다.
→ 절대 경로로 고정합니다.
→ 모든 사례가 같은 실행 파일을 실행합니다.
```

경로 구분자가 들어 있는 명령은 호출 당시 작업 디렉터리를 기준으로 절대 경로를 만듭니다.

## 작업 디렉터리와 환경 변수

```python
import os
import subprocess

custom_env = os.environ.copy()
custom_env.update(case_environment)

subprocess.run(
    command,
    cwd=working_directory,
    env=custom_env,
    check=False,
)
```

환경 변수를 빈 `dict`로 새로 만들면 `PATH`, 로케일 등 실행에 필요한 값이 사라질 수 있습니다. 반대로 부모 프로세스의 환경을 모두 무조건 상속하면 테스트 결과가 외부 상태에 따라 달라질 수 있습니다. 유지할 값과 덮어쓸 값을 명확히 정해야 합니다.

## 타임아웃은 프로세스 수명 규칙입니다

```python
try:
    subprocess.run(command, timeout=2.0, check=False)
except subprocess.TimeoutExpired:
    ...
```

제한 시간이 없으면 끝나지 않는 프로세스 하나가 전체 작업을 멈출 수 있습니다. 하지만 직접 실행한 부모 프로세스 하나만 종료해서는 충분하지 않을 수 있습니다.

```text
검사기
└─ 검사 대상 부모 프로세스
   └─ 검사 대상이 만든 자식 프로세스
```

자식 프로세스가 계속 실행되거나 `stdout` 파이프를 열어 둔 채 남아 있으면 부모가 종료된 뒤에도 검사기가 EOF를 받지 못할 수 있습니다.

## POSIX 프로세스 그룹

macOS와 Linux에서는 검사 대상을 새 세션에서 시작해 별도 프로세스 그룹의 리더로 만들 수 있습니다.

```python
process = subprocess.Popen(
    command,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    start_new_session=True,
)
```

타임아웃이나 출력 상한을 초과하면 해당 프로세스 그룹 전체에 먼저 `SIGTERM`을 보냅니다.

```python
import os
import signal

os.killpg(process.pid, signal.SIGTERM)
```

짧은 종료 유예 시간을 기다린 뒤에도 프로세스가 남아 있으면 `SIGKILL`을 보냅니다. 처음부터 강제 종료하지 않는 이유는 대상 프로세스가 임시 파일이나 하위 자원을 정리할 기회를 주기 위해서입니다.

Windows 네이티브 환경에서 프로세스 트리를 종료하려면 다른 API와 구현이 필요합니다. `command-checker`는 macOS와 Linux만 지원합니다.

## `stdin`, `stdout`, `stderr`를 함께 처리하기

검사기가 큰 `stdin`을 모두 쓴 뒤에야 `stdout`을 읽기 시작하면 파이프 교착이 발생할 수 있습니다.

```text
검사기: 큰 stdin을 쓰는 중
검사 대상: stdout 파이프가 가득 차서 쓰기 대기
검사 대상: stdin을 더 읽지 못함
검사기: stdin 쓰기를 끝내지 못함
```

POSIX 환경에서 `selectors.DefaultSelector`와 논블로킹 파일 디스크립터를 사용하면 하나의 반복문에서 다음 상태를 함께 처리할 수 있습니다.

```text
stdin에 데이터를 쓸 수 있습니다.
stdout에서 데이터를 읽을 수 있습니다.
stderr에서 데이터를 읽을 수 있습니다.
프로세스가 종료되었습니다.
마감 시각이 지났습니다.
```

진행 상태는 값으로 관리합니다.

- 아직 쓰지 않은 입력의 위치
- 수집한 stdout 바이트 수
- 수집한 stderr 바이트 수
- 절대 마감 시각
- 타임아웃 여부
- 상한을 넘은 스트림

EOF를 확인한 스트림은 `selector` 등록에서 제거한 뒤 닫습니다.

## 출력량 제한하기

제한 시간 안에 끝나더라도 출력을 무한히 생성하는 프로그램은 검사기의 메모리를 모두 사용할 수 있습니다.

```text
stdout 바이트 수 ≤ case.output_limit
stderr 바이트 수 ≤ case.output_limit
```

각 스트림이 상한을 넘는 즉시 추가 수집을 중단하고 프로세스 그룹 정리를 시작합니다. 전체 출력을 메모리에 저장한 뒤 크기를 검사하면 이미 자원 제한의 목적을 잃은 것입니다.

## 실행 환경 오류와 결과 불일치 구분하기

- 실행 파일을 찾을 수 없거나 실행 권한이 없음: 검사를 시작할 수 없는 오류
- 대상 프로그램이 예상과 다른 종료 상태를 반환함: 실행 후 확인한 결과 불일치

프로세스 API에서 발생한 모든 예외를 단순한 사례 실패로 바꾸면 사용자가 명세나 실행 환경을 고쳐야 하는지, 대상 프로그램을 고쳐야 하는지 알 수 없습니다.

## 모든 종료 경로에서 정리하기

정상 종료, 타임아웃, 출력 상한 초과, 예외 발생 여부와 관계없이 다음 자원을 정리해야 합니다.

- `selector` 등록
- `stdin`, `stdout`, `stderr` 파이프
- 직접 실행한 프로세스
- 해당 프로세스가 만든 프로세스 그룹
- 임시 버퍼와 상태

정리 중 추가 오류가 발생하더라도 원래 실패 원인을 가리지 않도록 처리 순서를 정해야 합니다.

## `command-checker`에 적용하기

- `runner.validate_executable()`이 실행 파일을 한 번 선택합니다.
- `process.run_case()`가 사례별 환경과 작업 디렉터리를 적용합니다.
- `_collect_process()`가 세 파이프, 마감 시각, 출력 상한을 함께 관리합니다.
- `_terminate_group()`이 `SIGTERM`, 유예, `SIGKILL`, 부모 프로세스 회수를 수행합니다.
- 수집 중 예외가 발생해도 `run_case()`가 자신이 시작한 프로세스 그룹을 정리합니다.

## 완료 기준

- 명령과 인자를 목록으로 전달합니다.
- 종료 상태, 표준 출력, 표준 오류를 따로 비교합니다.
- 현재 Python 인터프리터와 필요한 환경 변수를 정확하게 전달합니다.
- 타임아웃 시 자식 프로세스까지 정리합니다.
- 입력과 두 출력 스트림을 교착 없이 함께 처리합니다.
- 출력 상한을 넘는 즉시 추가 수집을 중단합니다.

다음은 [동시성, 취소와 자원 제한](03-concurrency-and-cancellation.md)입니다.
