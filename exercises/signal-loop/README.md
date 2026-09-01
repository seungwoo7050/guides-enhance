# signal-loop

`signal-loop`는 POSIX 시그널 처리기에서는 최소한의 기록만 수행하고, **self-pipe**를 통해 일반 제어 흐름에 "처리할 사건이 생겼다"는 사실을 전달하는 실행 프로그램입니다.

핵심 설계는 다음 두 실행 문맥을 분리하는 것입니다.

```text
시그널 처리기:
    async-signal-safe한 최소 작업만 수행

일반 코드:
    printf, 상태 변경, 종료 판단 같은 실제 처리를 수행
```

## 동작

프로그램이 self-pipe와 시그널 처리기 설치 등 초기 준비를 마치면 다음 줄을 출력합니다.

```text
ready pid=<PID>
```

이 `ready` 줄은 외부 테스트나 다른 프로세스가 **이제 시그널을 보내도 되는 시점**을 알 수 있게 하는 동기화 지점입니다.

그 뒤 동작은 다음과 같습니다.

- `SIGUSR1`을 받으면 `event=SIGUSR1`을 출력하고 계속 실행
- `SIGTERM`을 받으면 `event=SIGTERM`을 출력하고 상태 `0`으로 종료

## 왜 시그널 처리기에서 직접 모든 작업을 하지 않는가

시그널 처리기는 프로그램의 일반 코드가 실행되는 도중 비동기적으로 끼어들 수 있습니다.

따라서 일반 함수 대부분은 시그널 처리기에서 안전하게 호출할 수 있다고 가정하면 안 됩니다.

예를 들어 복잡한 메모리 할당, stdio 상태 변경, 일반적인 라이브러리 호출을 처리기에서 수행하면 이미 같은 내부 상태를 사용하던 코드에 끼어들어 문제가 생길 수 있습니다.

이 프로그램은 처리기 안의 작업을 다음으로 제한합니다.

```text
pending flag 설정
self-pipe에 한 바이트 write 시도
```

`sig_atomic_t`는 시그널 처리기와 일반 코드 사이에서 단순한 플래그 값을 읽고 쓰기 위한 타입으로 사용하고, `write`는 POSIX에서 시그널 처리 문맥에서 사용할 수 있는 핵심 시스템 호출 중 하나입니다.

## self-pipe란 무엇인가

self-pipe는 프로세스가 자기 자신을 깨우기 위해 만든 일반 pipe입니다.

개념적으로:

```text
signal handler
    │
    │ write 1 byte
    ▼
┌──────────────┐
│  self-pipe   │
└──────────────┘
    │
    │ read
    ▼
main loop
```

시그널 처리기는 "SIGUSR1을 완전히 처리"하려고 하지 않고, 일반 코드가 잠들어 있다면 pipe를 통해 깨울 수 있게 한 바이트 쓰기를 시도합니다.

실제 어떤 사건이 pending 상태인지는 별도의 flag가 보존합니다.

## 제공 기능

- `sig_atomic_t` pending 플래그와 `write`만 사용하는 시그널 처리기
- 쓰기 끝을 `O_NONBLOCK`으로 설정한 self-pipe
- 두 pipe 끝의 `FD_CLOEXEC` 설정
- 두 번째 처리기 설치 실패 시 첫 처리기 복원
- 초기화와 정리 중 관련 시그널 차단
- 기존 시그널 처리 방법 저장과 종료 시 복원
- 표준 시그널이 여러 번 발생해도 하나로 합쳐질 수 있음을 허용

## 빌드와 실행

```sh
make
./build/signal-loop
```

준비되면 예를 들어 다음을 출력합니다.

```text
ready pid=12345
```

다른 터미널에서 해당 PID로 시그널을 보낼 수 있습니다.

```sh
kill -USR1 12345
kill -TERM 12345
```

실행 예시는 개념적으로 다음과 같습니다.

```text
ready pid=12345
event=SIGUSR1
event=SIGTERM
```

그 뒤 프로그램은 상태 `0`으로 종료합니다.

## 주요 구현 결정

### pending 플래그가 사건의 존재를 보존

시그널 처리기는 해당 시그널의 pending flag를 설정합니다.

예:

```text
SIGUSR1 발생
→ pending_usr1 = 1
```

이 flag의 의미는 정확한 발생 횟수가 아니라:

```text
"처리하지 않은 SIGUSR1 사건이 적어도 하나 있다"
```

입니다.

표준 시그널은 같은 종류가 짧은 시간에 여러 번 발생했을 때 모든 발생 횟수가 독립적으로 큐에 보존된다고 일반화할 수 없습니다. 따라서 이 프로그램도 burst를 정확한 횟수 카운터로 표현하지 않습니다.

### self-pipe의 쓰기 끝은 non-blocking

시그널 처리기에서 pipe에 쓰다가 pipe가 가득 찬 상태로 block되면 처리기 자체가 멈출 수 있습니다.

이를 피하기 위해 쓰기 끝에 `O_NONBLOCK`을 설정합니다.

따라서 pipe가 가득 찬 경우 `write`가 실패할 수 있지만, 이 프로그램에서는 pending flag가 이미 사건의 존재를 기록하고 있으므로 "깨우기 바이트 하나를 더 넣지 못했다"는 이유로 사건 자체를 잃었다고 보지 않습니다.

즉 두 메커니즘의 역할은 다릅니다.

```text
pending flag:
    처리할 사건이 있다는 상태 보존

self-pipe byte:
    일반 실행 흐름을 깨우는 알림
```

### 두 pipe 끝에 `FD_CLOEXEC`

self-pipe FD는 프로그램 내부의 이벤트 전달용입니다.

외부 명령을 `exec`하는 코드가 생기더라도 이 내부 FD가 새 프로그램에 불필요하게 상속되지 않도록 양쪽 끝에 `FD_CLOEXEC`를 설정합니다.

FD가 의도하지 않은 프로세스에 남으면 EOF 판단이나 자원 정리에 영향을 줄 수 있습니다.

### pending flag를 읽고 지울 때 시그널 차단

다음 순서를 아무 보호 없이 수행한다고 가정합니다.

```text
1. pending_usr1을 읽음
2. pending_usr1을 0으로 지움
```

1과 2 사이에 새 `SIGUSR1`이 들어오면 처리기가 flag를 다시 `1`로 만든 직후 일반 코드가 `0`으로 덮어써 새 사건을 잃을 수 있습니다.

따라서 일반 코드는 관련 시그널을 잠시 차단한 상태에서:

```text
pending flag snapshot
→ flag clear
```

를 하나의 논리적 구간으로 수행합니다.

그 뒤 시그널 차단을 해제하고 snapshot에 따라 일반 코드에서 실제 출력을 수행합니다.

### 초기화 중 시그널 차단

초기화가 다음 순서로 진행된다고 가정합니다.

```text
pipe 일부만 준비됨
handler 설치됨
나머지 상태는 아직 준비 안 됨
```

이 사이에 시그널이 들어오면 handler가 아직 사용할 준비가 되지 않은 FD를 참조할 수 있습니다.

따라서 초기화 중에는 관련 시그널을 차단하고:

```text
self-pipe 생성
→ FD 설정
→ 기존 handler 저장
→ 새 handler 설치
→ 상태 완성
→ 시그널 차단 해제
→ ready 출력
```

처럼 준비가 끝난 뒤 정상적으로 받도록 합니다.

### 정리 중 시그널 차단

종료 시에도 반대 문제가 생길 수 있습니다.

```text
self-pipe FD를 닫음
→ 기존 handler 복원 전
→ 시그널 도착
→ 새 handler가 이미 닫힌 FD에 write
```

같은 경쟁을 피하려면 정리 중에도 관련 시그널을 차단합니다.

일반적인 정리 흐름은 다음 관계를 유지해야 합니다.

```text
관련 시그널 차단
→ 새 handler가 더 이상 위험한 자원을 사용하지 않게 처리
→ 기존 handler 복원
→ pipe FD 정리
→ 필요한 시그널 mask 복원
```

구체적인 순서는 구현의 자원 소유 관계에 맞춰 일관되게 정해야 합니다.

### handler 설치 실패 시 rollback

두 시그널의 handler를 차례로 설치하다가 두 번째 설치가 실패할 수 있습니다.

예:

```text
SIGUSR1 handler 설치 성공
SIGTERM handler 설치 실패
```

이 경우 프로그램이 단순히 실패 반환하면 SIGUSR1만 새 handler로 남아 프로세스의 원래 시그널 상태를 바꿔 놓습니다.

따라서 이미 바꾼 SIGUSR1 처리 방법을 원래 상태로 복원한 뒤 초기화 실패를 보고합니다.

이 원칙은 "초기화 실패 후에도 호출 전 외부 상태를 가능한 한 복원한다"는 rollback 규칙입니다.

## 일반 코드의 사건 처리

main loop는 self-pipe에서 깨우기 바이트를 읽은 뒤 pending 상태를 확인합니다.

개념적인 흐름은 다음과 같습니다.

```text
self-pipe에서 wake byte 읽음
→ SIGUSR1, SIGTERM 잠시 차단
→ pending flag snapshot
→ pending flag clear
→ 시그널 mask 복원
→ snapshot에 따라 일반 코드에서 출력/종료 처리
```

중요한 점은 pipe의 바이트 개수와 실제 시그널 발생 횟수를 일대일 대응시키지 않는 것입니다.

pipe는 깨우기 장치이고, 처리할 사건 종류는 pending flag가 결정합니다.

## `SIGTERM` 종료

`SIGTERM` 사건을 일반 코드가 관찰하면:

```text
event=SIGTERM
```

을 출력하고 정상 상태 `0`으로 종료합니다.

종료 경로에서는:

- 기존 signal disposition 복원
- self-pipe FD 정리
- 필요한 signal mask 복원

등 초기화 과정에서 변경한 프로세스 상태를 정리합니다.

## 테스트

```sh
make test
make sanitize
```

Python 테스트는 실제 프로세스를 실행해 다음을 확인합니다.

- `ready`가 먼저 출력되는지
- 순차적인 `SIGUSR1` 처리
- burst 시그널이 합쳐져도 멈추지 않는지
- `SIGTERM` 출력과 정상 종료
- 종료 뒤 추가 출력이 없는지
- timeout 안에 테스트가 끝나는지

### `ready`를 기다린 뒤 시그널 보내기

테스트는 프로세스를 시작하자마자 시그널을 보내면 안 됩니다.

먼저:

```text
ready pid=<PID>
```

를 읽은 뒤에 시그널을 보내야 초기화 완료 전 시그널 전달이라는 별도 경쟁 조건을 테스트에 섞지 않을 수 있습니다.

### burst 테스트의 기준

표준 시그널은 여러 번 빠르게 보내도 하나로 합쳐질 수 있으므로 다음을 보장 대상으로 삼지 않습니다.

```text
SIGUSR1을 100번 보냈으니 event=SIGUSR1도 정확히 100줄이어야 한다.
```

대신 burst 뒤 프로그램이 멈추지 않고 사건을 관찰하며 계속 정상적으로 `SIGTERM`까지 처리하는지를 확인합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Async-signal-safe event capture | `src/signal_loop.c` |
| 2 | Non-blocking close-on-exec self-pipe | `src/signal_loop.c` |
| 3 | Handler installation with rollback | `src/signal_loop.c` |
| 4 | Wake-byte read and blocked pending snapshot | `src/signal_loop.c` |
| 5 | Initialization while signals are blocked | `src/signal_loop.c` |
| 6 | Event handling and ordered cleanup | `src/signal_loop.c` |

## 범위

다음 두 시그널만 처리합니다.

```text
SIGUSR1
SIGTERM
```

다음 기능은 포함하지 않습니다.

- POSIX 실시간 시그널 큐
- 시그널과 함께 별도 데이터 전달
- 정확한 표준 시그널 발생 횟수 기록
- 여러 사건 소스를 함께 기다리는 `poll`/`select` 기반 event loop

이 프로그램의 핵심 목적은 **비동기 시그널 처리기와 일반 프로그램 로직 사이의 경계를 self-pipe와 pending flag로 분리하는 방법**을 보여 주는 것입니다.
