# 디버거 참고

이 문서는 재현 가능한 실행 오류가 있을 때 GDB 또는 LLDB로 값을 확인하는 기본 절차를 정리합니다. 디버거를 처음부터 끝까지 한 줄씩 실행하는 도구로 사용하지 않습니다. 먼저 잘못되었을 것으로 예상되는 값이나 시점을 정하고 그 가설을 확인합니다.

## 디버그 정보 포함하기

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -g -O0 source.c -o program
```

- `-g`: 소스 위치, 함수와 변수 정보를 실행 파일에 넣습니다.
- `-O0`: 최적화로 코드 순서와 변수 표현이 크게 바뀌는 것을 줄입니다.
- 경고 옵션은 그대로 유지합니다.

문제를 수정한 뒤에는 실제 사용할 최적화 설정에서도 다시 검사합니다.

## GDB 시작

```sh
gdb ./program
```

인자를 전달하려면 다음과 같이 실행합니다.

```text
(gdb) run one two
```

또는 시작 전에 지정합니다.

```text
(gdb) set args one two
(gdb) run
```

## LLDB 시작

```sh
lldb ./program
```

```text
(lldb) run one two
```

## 중단점

### 함수 이름

```text
(gdb) break main
(lldb) breakpoint set --name main
```

### 파일과 줄 번호

```text
(gdb) break parser.c:120
(lldb) breakpoint set --file parser.c --line 120
```

문제가 발생한 뒤가 아니라 잘못된 값이 만들어지기 직전에 중단점을 둡니다.

## 실행 제어

| 동작 | GDB | LLDB |
| --- | --- | --- |
| 현재 함수의 다음 소스 줄 | `next` | `next` |
| 호출 함수 안으로 이동 | `step` | `step` |
| 계속 실행 | `continue` | `continue` |
| 현재 함수 끝까지 실행 | `finish` | `finish` |
| 프로그램 종료 | `kill` | `process kill` |

`step`을 남용하면 표준 라이브러리 내부까지 들어가 조사 범위가 불필요하게 커질 수 있습니다. 먼저 `next`를 사용하고 실제로 필요한 함수에만 들어갑니다.

## 변수와 표현식 확인

```text
(gdb) print index
(gdb) print *pointer
(gdb) print values[3]
(gdb) print/x flags
```

```text
(lldb) frame variable index
(lldb) expression *pointer
(lldb) expression values[3]
(lldb) expression --format x -- flags
```

포인터를 역참조하기 전에 주소와 길이부터 확인합니다.

```text
pointer가 NULL입니까?
가리키는 객체의 수명이 끝나지 않았습니까?
index가 length보다 작습니까?
이 메모리를 누가 할당했습니까?
```

## 호출 스택

```text
(gdb) backtrace
(lldb) bt
```

호출 스택은 현재 함수까지 어떤 경로로 들어왔는지 보여 줍니다. 충돌 위치만 보고 수정하지 말고 잘못된 값이 처음 만들어진 호출자를 찾습니다.

특정 frame으로 이동할 수 있습니다.

```text
(gdb) frame 2
(lldb) frame select 2
```

## 메모리 확인

GDB:

```text
(gdb) x/16bx buffer
(gdb) x/s text
(gdb) x/8gx pointer
```

LLDB:

```text
(lldb) memory read --format x --size 1 --count 16 buffer
(lldb) memory read --format c --size 1 text
```

문자열 출력은 NUL 종료를 전제로 합니다. 임의 바이트 데이터는 길이를 정해 읽습니다.

## Watchpoint

특정 값이 바뀌는 순간을 찾을 수 있습니다.

```text
(gdb) watch account.balance
(lldb) watchpoint set variable account.balance
```

Watchpoint는 하드웨어 지원 수가 제한될 수 있고 실행이 느려질 수 있습니다.

## 자식 프로세스 디버깅

`fork` 이후 어느 프로세스를 따라갈지 정합니다.

GDB:

```text
(gdb) set follow-fork-mode child
(gdb) set detach-on-fork off
```

LLDB의 세부 지원은 플랫폼에 따라 다릅니다. 단순한 경우에는 자식에 별도 중단점을 두거나 PID에 attach하는 방법도 사용합니다.

프로세스가 여러 개면 어떤 PID의 stdout, stderr와 종료 상태를 보고 있는지 먼저 확인합니다.

## 스레드 확인

GDB:

```text
(gdb) info threads
(gdb) thread 3
(gdb) thread apply all backtrace
```

LLDB:

```text
(lldb) thread list
(lldb) thread select 3
(lldb) thread backtrace all
```

교착 상태를 조사할 때 모든 스레드의 호출 스택과 현재 기다리는 mutex를 함께 확인합니다.

## Core dump

시스템 설정에서 core dump가 허용되어 있다면 충돌 당시 상태를 나중에 열 수 있습니다.

```sh
ulimit -c unlimited
./program
```

```sh
gdb ./program core
lldb -c core ./program
```

운영체제와 배포 환경에 따라 core 파일 위치와 이름이 다릅니다.

## 디버거와 sanitizer 함께 사용하기

Sanitizer가 보고한 파일과 줄 번호를 시작점으로 디버거 중단점을 둘 수 있습니다.

```text
1. sanitizer로 실패 재현
2. 첫 번째 잘못된 접근 위치 확인
3. 그보다 앞선 상태 변경에 중단점 설정
4. 포인터, 길이와 소유자 확인
5. 수정 후 같은 입력과 전체 테스트 재실행
```

## 조사 기록

문제를 해결할 때 다음을 남기면 같은 오류를 다시 찾기 쉽습니다.

```text
실행 명령
입력
컴파일 옵션
중단점 위치
잘못된 값이 처음 보인 frame
수정 내용
수정 후 실행한 테스트
```

## 사용 기준

디버거는 다음 질문에 답하기 위해 사용합니다.

- 값이 언제 처음 잘못되었습니까?
- 이 포인터는 어느 객체를 가리킵니까?
- 어떤 호출자가 잘못된 인자를 전달했습니까?
- 어느 스레드가 어떤 mutex를 기다립니까?
- 자식 프로세스는 어떤 FD와 인자를 받았습니까?

단순히 충돌한 줄을 찾는 데서 끝내지 않습니다.
