# signal-loop

`signal-loop`은 POSIX 시그널 처리기에서는 최소한의 기록만 하고, self-pipe를 통해 일반 코드에 사건이 발생했다는 사실을 전달하는 실행 프로그램입니다.

## 동작

프로그램이 준비를 마치면 다음 줄을 출력합니다.

```text
ready pid=<PID>
```

- `SIGUSR1`을 받으면 `event=SIGUSR1`을 출력하고 계속 실행합니다.
- `SIGTERM`을 받으면 `event=SIGTERM`을 출력하고 상태 `0`으로 종료합니다.

## 제공 기능

- `sig_atomic_t` pending 플래그와 `write`만 사용하는 시그널 처리기
- 쓰기 끝을 `O_NONBLOCK`으로 설정한 self-pipe
- 두 파이프 끝의 `FD_CLOEXEC` 설정
- 두 번째 처리기 설치 실패 시 첫 처리기 복원
- 초기화와 정리 중 관련 시그널 차단
- 기존 시그널 처리 방법 저장과 종료 시 복원
- 표준 시그널이 여러 번 발생해도 하나로 합쳐질 수 있음을 허용

## 빌드와 실행

```sh
make
./build/signal-loop
```

다른 터미널에서 PID에 시그널을 보냅니다.

```sh
kill -USR1 <PID>
kill -TERM <PID>
```

## 주요 구현 결정

시그널 처리기에서는 pending 플래그를 설정하고 self-pipe에 한 바이트 쓰기를 시도합니다. 파이프가 가득 차 `write`가 실패하더라도 pending 플래그가 사건의 존재를 남깁니다.

일반 코드는 깨우기 바이트를 읽은 뒤 `SIGUSR1`과 `SIGTERM`을 잠시 막고 pending 플래그를 읽고 지웁니다. 이 구간에 같은 시그널이 들어와 flag를 다시 설정한 직후 지워지는 상황을 막기 위해서입니다.

초기화와 정리 중에도 관련 시그널을 막습니다. 시그널 처리기가 아직 준비되지 않은 파일 디스크립터를 사용하거나, 이미 닫은 파일 디스크립터에 쓰는 상황을 피합니다.

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

`SIGUSR1`과 `SIGTERM`만 처리합니다. 실시간 시그널 큐, 데이터 전달, 여러 사건 소스를 함께 기다리는 `poll`/`select` 루프는 포함하지 않습니다.
