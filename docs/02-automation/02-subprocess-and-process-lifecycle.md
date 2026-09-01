# 외부 프로세스와 수명 관리

> 선택 심화 문서입니다. 일반 Python 개발의 필수 선행 과정은 아닙니다.

## 학습 목표

Python 프로그램이 다른 프로그램을 실행하면 단순히 함수 하나를 호출하는 것보다 더 많은 상태를 직접 관리해야 합니다.

외부 프로세스에는 다음 요소가 함께 존재합니다.

- 실행할 프로그램과 명령줄 인자
- `stdin`, `stdout`, `stderr`
- 작업 디렉터리
- 환경 변수
- 종료 상태
- 실행 시간
- 자식 프로세스
- 파이프와 파일 디스크립터

이 문서에서는 다음 내용을 설명합니다.

- 명령과 인자를 문자열 하나가 아니라 목록으로 전달하는 이유
- `stdin`, `stdout`, `stderr`, 종료 상태를 구분해서 수집하는 방법
- 현재 Python 인터프리터를 재사용하는 방법
- 실행 파일을 한 번 선택해 테스트 간 대상을 고정하는 이유
- 작업 디렉터리와 환경 변수를 명시적으로 전달하는 방법
- 타임아웃을 단순한 숫자가 아니라 프로세스 수명 규칙으로 보는 이유
- 부모 프로세스뿐 아니라 그 자식 프로세스까지 함께 정리하는 방법
- 큰 입력과 큰 출력을 동시에 처리할 때 발생할 수 있는 파이프 교착
- 논블로킹 I/O와 `selectors`로 여러 파이프를 함께 관리하는 방법
- 출력량을 읽는 도중 제한해야 하는 이유
- 정상적인 결과 불일치와 실행 환경 자체의 오류를 구분하는 방법

연결 프로젝트는 [`command-checker`](../../exercises/command-checker/README.md)입니다.

---

## 선행 개념

이 문서를 읽기 전에 다음 내용을 알고 있어야 합니다.

- CLI의 명령줄 인자, `stdin`, `stdout`, `stderr`, 종료 상태를 구분할 수 있습니다.
- `try/finally`와 컨텍스트 관리자로 자원을 정리할 수 있습니다.
- 파일과 JSON 입력을 검증할 수 있습니다.
- `bytes`와 `str`을 구분할 수 있습니다.
- 파일 디스크립터가 운영체제가 열린 파일이나 파이프를 식별하기 위해 사용하는 정수 핸들이라는 정도를 이해합니다.

이 문서의 후반부는 macOS와 Linux 같은 POSIX 환경을 기준으로 설명합니다.

---

## 가장 단순한 경우에는 `subprocess.run()`을 사용합니다

외부 프로세스를 한 번 실행하고 종료될 때까지 기다린 뒤 결과를 받는 가장 단순한 경우에는 `subprocess.run()`이 적합합니다.

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

이 호출은 대략 다음 흐름으로 동작합니다.

```text
프로세스 시작
→ 필요하면 입력 전달
→ 프로세스 종료까지 대기
→ stdout/stderr 수집
→ CompletedProcess 반환
```

반환값에서는 다음 정보를 확인할 수 있습니다.

```python
result.returncode
result.stdout
result.stderr
```

`subprocess.run()`은 일반적인 일회성 실행에는 편리하지만, 실행 중간에 출력량을 제한하거나 여러 스트림을 직접 논블로킹 방식으로 제어해야 한다면 `subprocess.Popen()`으로 더 낮은 수준의 수명 관리를 해야 합니다.

---

## 명령과 인자를 목록으로 전달하기

```python
import subprocess

result = subprocess.run(
    ["git", "status", "--short"],
    check=False,
)
```

기본값인 `shell=False`에서 목록의 각 원소는 명령줄 인자 하나를 나타냅니다.

```python
[
    "git",
    "status",
    "--short",
]
```

따라서 원소 안에 공백이 있어도 다시 여러 인자로 나뉘지 않습니다.

```python
subprocess.run(
    ["tool", "hello world"],
    check=False,
)
```

여기서 대상 프로그램은 `"hello world"`를 하나의 인자로 받습니다.

반면 다음과 같이 문자열을 만들고 `shell=True`로 실행하면 문자열이 셸 문법으로 다시 해석됩니다.

```python
subprocess.run(
    f"grep {user_input} application.log",
    shell=True,
)
```

`user_input`에 셸 메타 문자가 들어 있으면 파이프, 리디렉션, 명령 구분, 명령 치환 같은 셸 기능으로 해석될 수 있습니다. 신뢰할 수 없는 입력이 포함된다면 명령 주입 위험이 생길 수 있습니다.

셸의 파이프나 리디렉션 자체가 실제 요구사항이 아니라면 기본값인 `shell=False`와 인자 목록을 사용합니다.

```python
subprocess.run(
    ["grep", user_input, "application.log"],
    check=False,
)
```

이 경우 `user_input`은 셸 문법이 아니라 `grep`에 전달되는 하나의 인자입니다.

### 목록을 사용한다고 모든 입력이 안전해지는 것은 아닙니다

인자 목록을 사용하면 **셸 재해석**은 피할 수 있지만 대상 프로그램 자체의 옵션 해석은 여전히 존재합니다.

예를 들어 사용자 문자열이 `-r`처럼 시작하면 어떤 프로그램은 이를 파일 이름이 아니라 옵션으로 해석할 수 있습니다.

필요하면 대상 프로그램이 제공하는 `--` 같은 옵션 종료 구문을 사용할 수 있습니다.

```python
subprocess.run(
    ["grep", "--", user_input, "application.log"],
    check=False,
)
```

따라서 다음 두 문제는 구분해야 합니다.

```text
shell=True에 의한 셸 명령 해석
≠
대상 프로그램 자체의 인자/옵션 해석
```

---

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

각 값의 의미는 서로 다릅니다.

- `returncode`: 프로세스 종료 상태
- `stdout`: 정상 출력
- `stderr`: 오류와 진단 출력

테스트 도구에서는 세 값을 따로 비교해야 합니다.

예를 들어 대상 프로그램이 다음처럼 동작할 수 있습니다.

```text
stdout: "3\n"
stderr: ""
returncode: 0
```

또는:

```text
stdout: ""
stderr: "invalid input\n"
returncode: 2
```

둘은 서로 다른 결과입니다.

---

## `check=True`와 `check=False`

`subprocess.run()`의 `check`는 비영(非零) 종료 상태를 예외로 바꿀지 결정합니다.

```python
subprocess.run(
    command,
    check=True,
)
```

대상 프로세스가 `0`이 아닌 종료 상태로 끝나면 `CalledProcessError`가 발생합니다.

일반 애플리케이션에서는 실패한 명령을 즉시 예외로 처리하는 데 유용할 수 있습니다.

하지만 테스트 도구에서는 비영 종료 상태 자체가 비교해야 하는 정상적인 관찰값일 수 있습니다.

```python
result = subprocess.run(
    command,
    check=False,
)

if result.returncode != expected_returncode:
    ...
```

`command-checker`처럼 종료 상태 자체를 명세와 비교하는 프로그램에서는 보통 `check=False`가 더 자연스럽습니다.

---

## 텍스트 모드와 바이트 모드 구분하기

다음 옵션을 사용하면 파이프의 데이터를 문자열로 처리할 수 있습니다.

```python
text=True
encoding="utf-8"
errors="replace"
```

예:

```python
result = subprocess.run(
    command,
    text=True,
    encoding="utf-8",
    errors="replace",
    capture_output=True,
)
```

그러면 `result.stdout`과 `result.stderr`는 `str`입니다.

반대로 `text=True`를 사용하지 않으면 기본적으로 바이트를 받습니다.

```python
result = subprocess.run(
    command,
    capture_output=True,
)
```

이 경우 출력은 `bytes`입니다.

고수준의 단순한 CLI 비교에서는 텍스트 모드가 편리할 수 있습니다. 하지만 출력량을 **바이트 단위로 정확히 제한**하거나 논블로킹 파일 디스크립터를 직접 읽어야 하는 구현에서는 먼저 `bytes`로 수집한 뒤 경계에서 디코딩하는 편이 단순한 경우가 많습니다.

```text
프로세스 pipe bytes
→ 바이트 수 제한
→ 실행 종료
→ 정해진 인코딩으로 decode
```

---

## 현재 Python 인터프리터 재사용하기

Python 프로그램을 다시 실행할 때 `"python3"` 문자열을 직접 적을 수 있습니다.

```python
command = ["python3", "-m", "sample"]
```

하지만 현재 프로그램이 가상 환경 안에서 실행되고 있다면 `"python3"`이 다른 인터프리터를 가리킬 수도 있습니다.

현재 Python 인터프리터를 그대로 재사용하려면 `sys.executable`을 사용합니다.

```python
import sys

command = [sys.executable, "-m", "sample"]
```

이 방식은 다음 조건을 유지하는 데 도움이 됩니다.

- 현재 선택된 Python 버전
- 현재 가상 환경
- 해당 인터프리터가 사용하는 설치 패키지

테스트가 "지금 이 프로그램을 실행 중인 Python"과 동일한 환경을 사용해야 한다면 `sys.executable`을 우선합니다.

---

## 실행 파일을 한 번 선택하기

명령에 경로 구분자가 없다면 운영체제는 보통 `PATH`를 검색해서 실행 파일을 찾습니다.

예를 들어 `tool`이라는 명령이 환경에 따라 다음처럼 서로 다른 파일을 가리킬 수 있습니다.

```text
/usr/local/bin/tool
/home/user/bin/tool
/tmp/test-bin/tool
```

각 테스트 사례가 서로 다른 `PATH`를 사용한다면 사례마다 다른 실행 파일을 실행할 수도 있습니다.

```text
case A PATH
→ /usr/local/bin/tool

case B PATH
→ /tmp/test-bin/tool
```

그러면 입력만 바뀌는 것이 아니라 **검사 대상 자체가 바뀌므로** 결과를 비교하기 어렵습니다.

`command-checker`에서는 실행 파일을 사례 실행 전에 한 번 결정해 고정하는 방식이 적합합니다.

```text
검사기를 호출한 환경에서 실행 파일 선택
→ 절대 경로로 고정
→ 모든 사례에서 동일한 실행 파일 사용
```

경로 구분자가 없는 명령은 예를 들어 `shutil.which()`로 찾을 수 있습니다.

```python
import shutil

resolved = shutil.which(command[0])

if resolved is None:
    raise CheckerError("실행 파일을 찾을 수 없습니다.")
```

그 뒤 고정된 절대 경로를 사용합니다.

```python
command = [resolved, *command[1:]]
```

### 경로가 직접 포함된 명령

다음처럼 명령 자체에 경로가 포함될 수도 있습니다.

```text
./build/tool
../bin/tool
```

`command-checker`가 **사례별 `cwd`와 무관하게 처음 선택한 실행 파일을 계속 사용하려는 설계**라면 검증 시점의 기준 디렉터리에서 절대 경로로 바꿔 둡니다.

```python
from pathlib import Path

executable = Path(command[0])

if not executable.is_absolute():
    executable = (Path.cwd() / executable).resolve()
```

이 설명은 모든 `subprocess` 프로그램의 필수 규칙이 아니라, 테스트 대상이 사례별 `cwd` 변화 때문에 바뀌지 않도록 하기 위한 `command-checker`의 정책입니다.

---

## 작업 디렉터리와 환경 변수

외부 프로세스의 실행 환경은 명령과 인자만으로 결정되지 않습니다.

다음 값도 동작에 영향을 줍니다.

- 현재 작업 디렉터리
- `PATH`
- 로케일 관련 환경 변수
- 프로그램별 설정 환경 변수

`subprocess`에서는 `cwd`와 `env`로 명시할 수 있습니다.

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

### `cwd`

```python
cwd=working_directory
```

는 자식 프로세스가 시작할 작업 디렉터리를 지정합니다.

자식 프로세스에서 다음과 같은 상대 경로는 이 디렉터리를 기준으로 해석될 수 있습니다.

```text
input.txt
./config.json
../data
```

### `env`

```python
env=custom_env
```

는 자식 프로세스가 받을 환경 변수 전체를 지정합니다.

빈 `dict`를 넘기면 부모 환경을 자동으로 합쳐 주는 것이 아닙니다.

```python
subprocess.run(
    command,
    env={},
)
```

이렇게 하면 `PATH`, 로케일 등 기존 환경 변수가 사라질 수 있습니다.

반대로 부모 환경을 모두 그대로 상속하면 테스트 결과가 사용자의 셸 설정에 따라 달라질 수 있습니다.

따라서 테스트 도구에서는 정책을 명확하게 정해야 합니다.

```text
부모 환경 복사
→ 테스트가 의도적으로 지정한 값 덮어쓰기
→ 재현성에 방해되는 값은 필요하면 제거
```

---

## 타임아웃은 프로세스 수명 규칙입니다

가장 단순한 경우에는 `subprocess.run()`의 `timeout`을 사용할 수 있습니다.

```python
import subprocess

try:
    subprocess.run(
        command,
        timeout=2.0,
        check=False,
    )
except subprocess.TimeoutExpired:
    ...
```

타임아웃이 없으면 끝나지 않는 프로세스 하나가 전체 검사 작업을 멈출 수 있습니다.

하지만 테스트 도구에서 타임아웃은 단순히 "2초 후 예외를 발생시킨다"는 의미만으로는 부족합니다.

다음 질문까지 함께 정해야 합니다.

```text
시간 초과 시 어떤 프로세스를 종료하는가?
열린 stdin/stdout/stderr는 어떻게 정리하는가?
자식 프로세스도 종료하는가?
종료를 요청한 뒤 얼마 동안 기다리는가?
그래도 종료하지 않으면 어떻게 하는가?
```

즉, 타임아웃은 **프로세스 수명 정책**입니다.

---

## 직접 실행한 부모만 종료해서는 충분하지 않을 수 있습니다

대상 프로그램이 다시 자식 프로세스를 만들 수 있습니다.

```text
검사기
└─ 검사 대상 부모 프로세스
   └─ 검사 대상이 만든 자식 프로세스
```

검사 대상 부모만 종료하면 자식이 계속 살아 있을 수 있습니다.

더 중요한 문제는 자식이 파이프의 쓰기 끝을 상속한 경우입니다.

```text
검사기
└─ 부모 ─ stdout pipe
   └─ 자식 ─ stdout pipe를 계속 보유
```

부모가 종료되어도 자식이 같은 파이프를 열어 두고 있으면 검사기가 `stdout`의 EOF를 받지 못할 수 있습니다.

따라서 타임아웃이나 출력 제한을 강제하는 테스트 도구에서는 프로세스 하나가 아니라 **대상이 만든 프로세스 집합의 수명**을 생각해야 합니다.

---

## POSIX 프로세스 그룹

macOS와 Linux에서는 검사 대상을 새 세션에서 시작할 수 있습니다.

```python
import subprocess

process = subprocess.Popen(
    command,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    start_new_session=True,
)
```

POSIX에서 `start_new_session=True`는 자식 프로세스에서 새 세션을 시작하도록 합니다.

그 결과 최초 대상 프로세스가 새 프로세스 그룹의 리더가 되고 일반적으로 다음 관계가 성립합니다.

```text
프로세스 PID == 프로세스 그룹 ID
```

대상이 일반적인 방식으로 자식 프로세스를 만들면 그 자식도 같은 프로세스 그룹에 속하게 됩니다.

따라서 그룹 전체에 신호를 보낼 수 있습니다.

```python
import os
import signal

os.killpg(process.pid, signal.SIGTERM)
```

여기서 `process.pid`를 그룹 ID로 사용할 수 있는 것은 새 세션의 최초 프로세스를 그룹 리더로 시작했기 때문입니다.

---

## `SIGTERM` 후 `SIGKILL`

타임아웃이나 출력 상한 초과 시 처음부터 `SIGKILL`을 보내는 대신 일반적으로 두 단계를 사용합니다.

```text
SIGTERM
→ 짧은 종료 유예
→ 아직 살아 있으면 SIGKILL
```

먼저:

```python
os.killpg(process.pid, signal.SIGTERM)
```

을 보내면 대상 프로그램이 신호를 처리하거나 정상적인 종료 작업을 수행할 기회를 가질 수 있습니다.

예를 들어 다음 자원을 정리할 수 있습니다.

- 임시 파일
- 열린 파일
- 소켓
- 내부 버퍼
- 자신이 만든 자식 프로세스

유예 시간이 지나도 종료하지 않으면 강제 종료합니다.

```python
os.killpg(process.pid, signal.SIGKILL)
```

`SIGKILL`은 프로세스가 잡거나 무시할 수 없습니다.

### 이미 종료된 경우

신호를 보내기 직전에 프로세스 그룹이 이미 사라질 수도 있습니다.

이 경우 `ProcessLookupError`가 발생할 수 있으므로 정리 코드에서는 "이미 종료됨"을 정상적인 정리 상태로 취급할 수 있습니다.

```python
try:
    os.killpg(process.pid, signal.SIGTERM)
except ProcessLookupError:
    pass
```

### 종료 후에는 부모를 회수해야 합니다

신호를 보낸 것과 부모 프로세스 객체를 회수하는 것은 다른 작업입니다.

종료 후에는 `wait()` 또는 그에 해당하는 처리를 수행해 자식 프로세스의 종료 상태를 회수해야 합니다.

```python
process.wait()
```

이를 하지 않으면 POSIX에서 종료된 자식이 한동안 좀비 프로세스로 남을 수 있습니다.

---

## Windows와 POSIX는 프로세스 트리 관리 방식이 다릅니다

이 문서의 프로세스 그룹 예시는 macOS와 Linux를 대상으로 합니다.

Windows 네이티브 환경에서는 POSIX 세션, `os.killpg()`, `SIGTERM`/`SIGKILL`을 같은 방식으로 사용할 수 없습니다.

Windows에서 프로세스 트리를 관리하려면 별도 API나 Job Object 같은 다른 구현 전략이 필요합니다.

`command-checker`는 macOS와 Linux만 지원하므로 이 문서에서는 POSIX 방식에 집중합니다.

---

## 파이프에는 유한한 버퍼가 있습니다

`stdin`, `stdout`, `stderr`를 `PIPE`로 연결하면 부모와 자식 사이에 운영체제 파이프가 만들어집니다.

```python
process = subprocess.Popen(
    command,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
```

파이프 버퍼의 크기는 무한하지 않습니다.

따라서 부모와 자식이 서로 상대방의 I/O를 기다리면 교착이 발생할 수 있습니다.

---

## 큰 `stdin`을 먼저 모두 쓰면 교착할 수 있습니다

다음 순서를 생각해 봅니다.

```text
검사기:
stdin에 큰 입력 전체를 쓰는 중

검사 대상:
입력을 일부 읽고 큰 stdout을 출력함

stdout 파이프:
가득 참
```

대상이 `stdout`에 더 쓰려면 검사기가 `stdout`을 읽어 공간을 만들어 줘야 합니다.

하지만 검사기는 아직 `stdin` 전체를 쓰는 데 막혀 있을 수 있습니다.

```text
검사기
→ stdin 쓰기를 끝내야 stdout을 읽으려 함

대상
→ stdout이 비워져야 stdin을 더 읽으려 함
```

그러면 양쪽이 서로를 기다립니다.

```text
검사기: stdin write에서 대기
검사 대상: stdout write에서 대기
```

이것이 파이프 교착의 한 형태입니다.

---

## 단순한 경우에는 `communicate()`가 파이프를 함께 처리합니다

`Popen.communicate()`는 입력을 보내고 `stdout`과 `stderr`를 함께 읽는 일반적인 방법입니다.

```python
stdout, stderr = process.communicate(input_data)
```

직접 다음처럼 작성하는 것보다 안전합니다.

```python
process.stdin.write(input_data)
stdout = process.stdout.read()
stderr = process.stderr.read()
```

`communicate()`는 일반적인 파이프 교착을 피하도록 입출력을 관리합니다.

따라서 단순히:

- 입력을 전달하고
- 프로세스 종료까지 기다리고
- 전체 출력을 메모리에 수집

하면 되는 경우에는 `subprocess.run()`이나 `communicate()`를 먼저 고려합니다.

하지만 `command-checker`에는 추가 요구가 있습니다.

- 실행 중간에 출력량 상한을 확인해야 함
- 상한을 넘는 즉시 프로세스 그룹을 종료해야 함
- 절대 마감 시각을 직접 관리해야 함
- `stdout`과 `stderr`를 각각 제한해야 함

이런 요구가 있으면 전체 출력을 끝까지 수집하는 `communicate()`만으로는 충분하지 않을 수 있습니다.

---

## 논블로킹 파이프로 여러 스트림을 함께 처리하기

POSIX 환경에서는 파이프 파일 디스크립터를 논블로킹으로 만들고 `selectors.DefaultSelector`로 여러 이벤트를 하나의 반복문에서 처리할 수 있습니다.

개념적으로 다음 상태를 동시에 기다립니다.

```text
stdin에 쓸 수 있음
stdout에서 읽을 수 있음
stderr에서 읽을 수 있음
프로세스가 종료됨
마감 시각이 지남
```

먼저 파이프를 생성합니다.

```python
process = subprocess.Popen(
    command,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    start_new_session=True,
)
```

그 뒤 POSIX에서는 파일 디스크립터를 논블로킹으로 설정할 수 있습니다.

```python
import os

os.set_blocking(process.stdin.fileno(), False)
os.set_blocking(process.stdout.fileno(), False)
os.set_blocking(process.stderr.fileno(), False)
```

논블로킹 모드에서는 지금 당장 읽거나 쓸 수 없는 작업 때문에 호출이 무기한 멈추지 않습니다.

---

## `selectors`가 관리하는 이벤트

`selectors`는 파일 디스크립터가 읽기 또는 쓰기 가능한 시점을 기다립니다.

개념적인 등록은 다음과 같습니다.

```python
import selectors

selector = selectors.DefaultSelector()

selector.register(
    process.stdout,
    selectors.EVENT_READ,
    data="stdout",
)

selector.register(
    process.stderr,
    selectors.EVENT_READ,
    data="stderr",
)
```

아직 보낼 `stdin` 데이터가 있다면 쓰기 이벤트도 등록할 수 있습니다.

```python
selector.register(
    process.stdin,
    selectors.EVENT_WRITE,
    data="stdin",
)
```

그 뒤 하나의 이벤트 루프에서 준비된 스트림만 처리합니다.

```text
이벤트를 기다림
→ stdin이 쓰기 가능하면 일부 입력 전송
→ stdout이 읽기 가능하면 일부 출력 읽음
→ stderr가 읽기 가능하면 일부 출력 읽음
→ 시간과 출력량 제한 확인
→ 종료 조건 확인
```

이 구조에서는 어느 하나의 파이프 작업이 다른 스트림의 진행을 장시간 막지 않습니다.

---

## 진행 상태를 값으로 관리하기

논블로킹 이벤트 루프에서는 "현재 어디까지 처리했는가"를 명시적인 상태로 저장해야 합니다.

예를 들어:

- 아직 쓰지 않은 입력의 위치
- 수집한 `stdout` 바이트 수
- 수집한 `stderr` 바이트 수
- 각 출력 버퍼
- 절대 마감 시각
- 타임아웃 발생 여부
- 출력 제한을 넘은 스트림
- `stdin`이 이미 닫혔는지
- `stdout`과 `stderr`에서 EOF를 받았는지

입력 상태는 다음처럼 표현할 수 있습니다.

```python
input_offset = 0
```

한 번에 전체 데이터를 쓰지 않고 가능한 만큼만 씁니다.

```python
written = os.write(
    process.stdin.fileno(),
    input_data[input_offset:],
)

input_offset += written
```

모든 입력을 보냈으면 자식이 EOF를 받을 수 있도록 `stdin`을 닫습니다.

```python
if input_offset == len(input_data):
    selector.unregister(process.stdin)
    process.stdin.close()
```

`stdin`을 닫지 않으면 대상 프로그램이 추가 입력을 기다리면서 종료하지 않을 수 있습니다.

---

## 절대 마감 시각을 사용하기

타임아웃을 반복문마다 다시 `2초`로 기다리면 실제 전체 실행 시간이 2초보다 훨씬 길어질 수 있습니다.

따라서 시작할 때 절대 마감 시각을 한 번 계산합니다.

```python
import time

deadline = time.monotonic() + timeout
```

남은 시간은 매 반복마다 다시 계산합니다.

```python
remaining = deadline - time.monotonic()

if remaining <= 0:
    timed_out = True
```

`time.monotonic()`은 시스템 시계가 앞뒤로 조정되어도 경과 시간 측정에 영향을 덜 받도록 설계된 단조 증가 시계입니다.

타임아웃처럼 **경과 시간**을 측정할 때는 `time.time()`보다 적합합니다.

---

## EOF를 확인한 스트림은 등록에서 제거합니다

파이프에서 읽었는데 빈 바이트열이 반환되면 EOF입니다.

```python
chunk = os.read(fd, 65536)

if chunk == b"":
    ...
```

EOF는 더 이상 해당 스트림에서 데이터가 오지 않는다는 뜻입니다.

그 스트림은 `selector` 등록에서 제거하고 닫습니다.

```python
selector.unregister(stream)
stream.close()
```

EOF가 난 파일 디스크립터를 계속 등록해 두면 이벤트 루프가 의미 없는 이벤트를 반복해서 받을 수 있습니다.

---

## 프로세스 종료와 파이프 EOF는 같은 시점이 아닐 수 있습니다

다음 두 사실은 서로 구분해야 합니다.

```text
부모 프로세스가 종료됨
stdout/stderr 파이프에서 EOF를 받음
```

대상 프로세스가 종료되어도 그 자식이 파이프 쓰기 끝을 계속 보유하고 있다면 EOF가 늦어질 수 있습니다.

반대로 파이프가 모두 닫힌 뒤 프로세스 상태를 아직 회수하지 않았을 수도 있습니다.

따라서 이벤트 루프의 종료 조건은 다음 상태들을 함께 고려해야 합니다.

- 프로세스 종료 여부
- `stdout` EOF 여부
- `stderr` EOF 여부
- `stdin` 처리 완료 여부
- 타임아웃 여부
- 출력 제한 초과 여부

---

## 출력량 제한하기

제한 시간 안에 끝나더라도 출력을 무한히 생성하는 프로그램은 검사기의 메모리를 모두 사용할 수 있습니다.

예:

```python
while True:
    print("x" * 1000)
```

따라서 `command-checker`는 각 출력 스트림에 바이트 상한을 둘 수 있습니다.

```text
stdout 바이트 수 ≤ case.output_limit
stderr 바이트 수 ≤ case.output_limit
```

예를 들어 한 청크를 읽었다고 가정합니다.

```python
chunk = os.read(fd, 65536)
```

그 즉시 누적 크기를 검사합니다.

```python
stdout_size += len(chunk)

if stdout_size > output_limit:
    output_limit_exceeded = "stdout"
```

상한을 넘는 순간 다음 단계로 진행합니다.

```text
추가 수집 중단
→ 프로세스 그룹 종료 시작
→ 자원 정리
→ 출력 초과 결과 기록
```

### 전체 출력을 먼저 읽은 뒤 검사하면 안 됩니다

다음 방식은 제한의 목적을 달성하지 못합니다.

```python
stdout, stderr = process.communicate()

if len(stdout) > output_limit:
    ...
```

이미 무제한에 가까운 출력을 메모리에 저장한 뒤이기 때문입니다.

자원 제한은 **자원을 소비하는 도중** 검사해야 합니다.

---

## `stdout`과 `stderr` 제한 정책을 명확히 정하기

다음 두 정책은 서로 다릅니다.

```text
stdout ≤ 1 MiB
stderr ≤ 1 MiB
```

과:

```text
stdout + stderr ≤ 1 MiB
```

원문의 `command-checker` 정책처럼 각 스트림에 같은 상한을 따로 적용한다면 최대 수집량은 두 스트림을 합쳐 상한의 약 두 배가 될 수 있습니다.

따라서 명세에는 제한이:

- 스트림별인지
- 전체 합계인지

를 명확히 적어야 합니다.

---

## 실행 환경 오류와 결과 불일치 구분하기

외부 프로그램 검사는 크게 두 단계로 나눌 수 있습니다.

```text
1. 프로그램을 실제로 실행할 수 있는가?
2. 실행된 프로그램의 결과가 기대와 같은가?
```

첫 번째 단계에서 발생하는 문제는 **실행 환경 오류**입니다.

예:

- 실행 파일을 찾을 수 없음
- 실행 권한이 없음
- `cwd`가 존재하지 않음
- 프로세스를 생성할 수 없음

두 번째 단계의 문제는 **결과 불일치**입니다.

예:

- 종료 상태가 다름
- `stdout`이 다름
- `stderr`가 다름
- 제한 시간을 초과함
- 출력 상한을 초과함

예를 들어:

```text
expected returncode: 0
actual returncode:   1
```

은 프로세스가 정상적으로 시작된 뒤 확인한 결과 차이입니다.

반면 실행 파일을 찾지 못했다면 비교 자체를 시작하지 못한 것입니다.

프로세스 API에서 발생한 모든 예외를 단순한 사례 실패로 바꾸면 사용자가:

```text
테스트 명세나 실행 환경을 고쳐야 하는지
대상 프로그램의 동작을 고쳐야 하는지
```

구분하기 어려워집니다.

---

## 모든 종료 경로에서 정리하기

프로세스 실행 코드는 정상 경로만 생각해서는 안 됩니다.

다음 모든 경우에 자원을 정리해야 합니다.

- 정상 종료
- 타임아웃
- `stdout` 상한 초과
- `stderr` 상한 초과
- 입력 전송 중 오류
- 출력 읽기 중 오류
- `selector` 오류
- 예상하지 못한 예외

정리 대상에는 다음이 포함됩니다.

- `selector` 등록
- `selector` 자체
- `stdin`
- `stdout`
- `stderr`
- 직접 실행한 프로세스
- 해당 프로세스가 만든 프로세스 그룹
- 임시 출력 버퍼와 상태

구조적으로는 `try/finally`를 사용해 "어떤 경로로 빠져나가더라도 정리"되도록 만드는 편이 안전합니다.

```python
process = None
selector = None

try:
    ...
finally:
    ...
```

---

## 정리 중 오류가 원래 오류를 가리지 않게 합니다

예를 들어 수집 도중 중요한 오류가 발생했다고 가정합니다.

```text
원래 오류:
stdout 읽기 실패
```

그 뒤 정리 과정에서 이미 닫힌 파일 디스크립터를 다시 닫다가 또 오류가 발생할 수 있습니다.

```text
정리 오류:
Bad file descriptor
```

정리 오류가 그대로 전파되면 사용자는 실제 실패 원인 대신 부차적인 정리 오류만 보게 됩니다.

따라서 정리 코드는 다음 원칙을 따르는 것이 좋습니다.

```text
원래 오류를 보존
→ 가능한 자원을 최대한 정리
→ 이미 종료/닫힘 같은 예상 가능한 정리 오류는 흡수
→ 원래 오류를 다시 전달
```

모든 예외를 무조건 무시하라는 뜻은 아닙니다. 정리 과정에서 어떤 오류가 정상적으로 발생할 수 있는지 구분해야 합니다.

---

## 프로세스 수명 관리 흐름

`command-checker` 같은 POSIX 테스트 실행기는 개념적으로 다음 흐름을 가질 수 있습니다.

```text
실행 파일 검증 및 절대 경로 고정
        │
        ▼
사례별 cwd/env 구성
        │
        ▼
새 세션에서 Popen
        │
        ▼
세 파이프를 논블로킹으로 설정
        │
        ▼
selector 등록
        │
        ▼
절대 마감 시각 계산
        │
        ▼
이벤트 루프
  ├─ stdin 일부 쓰기
  ├─ stdout 일부 읽기
  ├─ stderr 일부 읽기
  ├─ 출력량 확인
  ├─ timeout 확인
  └─ 종료/EOF 상태 확인
        │
        ├─ 정상 완료
        ├─ timeout
        ├─ output limit
        └─ 예외
        ▼
필요하면 프로세스 그룹 종료
        │
        ▼
부모 프로세스 wait/reap
        │
        ▼
파이프와 selector 정리
        │
        ▼
수집한 bytes를 decode
        │
        ▼
Result 생성
```

이 구조에서 중요한 점은 **실행, 수집, 제한, 종료, 정리**가 서로 독립된 문제가 아니라 하나의 수명 관리 과정이라는 것입니다.

---

## `command-checker`에 적용하기

프로젝트에서는 책임을 다음처럼 나눌 수 있습니다.

### `runner.validate_executable()`

검사 시작 전에 실행 파일을 검증합니다.

- 경로 구분자가 없는 명령은 호출 환경의 `PATH`에서 찾습니다.
- 경로가 직접 주어진 명령은 정해진 기준 디렉터리에서 절대 경로로 고정합니다.
- 실행할 수 없는 대상이면 사례 실행을 시작하기 전에 오류로 처리합니다.
- 이후 모든 사례가 같은 실행 파일을 사용하게 합니다.

### `process.run_case()`

하나의 테스트 사례에 필요한 실행 환경을 구성합니다.

- 사례별 `cwd`
- 사례별 환경 변수
- 입력 데이터
- 타임아웃
- 출력량 제한

을 `_collect_process()`에 전달하고, 예외가 발생해도 자신이 시작한 프로세스 그룹이 남지 않도록 최종 정리를 책임집니다.

### `_collect_process()`

실제 프로세스 I/O와 제한을 관리합니다.

- `stdin`
- `stdout`
- `stderr`
- 절대 마감 시각
- `stdout` 바이트 수
- `stderr` 바이트 수
- EOF 상태
- 타임아웃 상태
- 출력 상한 상태

를 하나의 이벤트 루프에서 관리합니다.

### `_terminate_group()`

대상 프로세스 그룹을 종료하고 부모를 회수합니다.

개념적인 순서는 다음과 같습니다.

```text
이미 종료했는지 확인
→ SIGTERM
→ 짧은 유예
→ 아직 남아 있으면 SIGKILL
→ 부모 프로세스 wait
```

정리 중 프로세스가 이미 사라졌다면 그 상태도 정상적으로 처리합니다.

---

## 언제 `subprocess.run()`만으로 충분한가

다음 조건이라면 보통 고수준 API부터 사용합니다.

```text
출력량이 충분히 작음
입력량도 충분히 작음
전체 출력을 메모리에 수집해도 됨
자식 프로세스 트리를 별도로 정리할 필요 없음
세밀한 중간 상태 제어가 필요 없음
```

예:

```python
result = subprocess.run(
    command,
    input=input_text,
    text=True,
    capture_output=True,
    timeout=2.0,
    check=False,
)
```

반대로 다음 요구가 있으면 직접적인 `Popen` 수명 관리가 필요할 수 있습니다.

```text
출력량을 읽는 도중 제한
stdout/stderr에 서로 다른 정책 적용
프로세스 그룹 전체 종료
입력과 출력을 동시에 세밀하게 처리
절대 마감 시각 관리
중간 상태 기록
```

필요 이상으로 낮은 수준의 프로세스 코드를 작성하면 오류 가능성이 커집니다. 요구사항이 단순하다면 `run()`과 `communicate()` 같은 고수준 API를 우선하고, 실제로 필요한 제한 때문에 낮은 수준으로 내려갑니다.

---

## 완료 기준

다음 항목을 설명하고 구현할 수 있으면 이 문서의 목표를 달성한 것입니다.

- 셸 기능이 필요하지 않다면 `shell=False`와 인자 목록을 사용합니다.
- 목록의 원소 하나가 명령줄 인자 하나라는 점을 설명할 수 있습니다.
- 셸 명령 주입과 대상 프로그램 자체의 옵션 해석을 구분할 수 있습니다.
- 종료 상태, `stdout`, `stderr`를 서로 다른 결과로 비교합니다.
- 결과의 비영 종료 상태를 직접 비교해야 할 때 `check=False`를 사용할 수 있습니다.
- 현재 Python 인터프리터를 다시 실행할 때 `sys.executable`을 사용할 수 있습니다.
- 사례별 `PATH` 때문에 검사 대상이 바뀌지 않도록 실행 파일을 한 번 선택해 고정할 수 있습니다.
- `cwd`와 `env`가 자식 프로세스 동작에 어떤 영향을 주는지 설명할 수 있습니다.
- 타임아웃을 단순한 예외가 아니라 프로세스 수명 정책으로 설계할 수 있습니다.
- POSIX에서 `start_new_session=True`와 프로세스 그룹을 사용해 자식 프로세스까지 정리할 수 있습니다.
- `SIGTERM` 후 유예하고 필요하면 `SIGKILL`을 보내는 이유를 설명할 수 있습니다.
- 종료한 부모 프로세스를 `wait()`로 회수해야 하는 이유를 설명할 수 있습니다.
- 큰 `stdin`과 큰 `stdout`이 동시에 존재할 때 파이프 교착이 발생할 수 있는 이유를 설명할 수 있습니다.
- 단순한 경우에는 `run()` 또는 `communicate()`를 우선할 수 있습니다.
- 세밀한 출력 제한이 필요할 때 논블로킹 파이프와 `selectors`를 사용할 수 있습니다.
- `time.monotonic()`으로 절대 마감 시각을 관리할 수 있습니다.
- EOF를 확인한 스트림을 `selector`에서 제거하고 닫을 수 있습니다.
- 출력 상한을 전체 수집 후가 아니라 수집 도중 검사합니다.
- 출력 제한이 스트림별인지 전체 합계인지 명확히 정합니다.
- 실행 환경 오류와 실행 후 결과 불일치를 구분합니다.
- 정상 종료, 타임아웃, 출력 상한 초과, 예외 등 모든 종료 경로에서 자원을 정리합니다.
- 정리 중 발생한 부차적인 오류가 원래 실패 원인을 가리지 않도록 처리합니다.

다음은 [동시성, 취소와 자원 제한](03-concurrency-and-cancellation.md)입니다.
