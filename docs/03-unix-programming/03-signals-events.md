# 시그널과 비동기 이벤트 전달

시그널 처리기는 프로그램의 일반 실행 중 어느 시점에든 호출될 수 있습니다. 처리기에서 동적 메모리 할당, stdio 함수 출력이나 mutex 잠금을 수행하면 중단된 코드와 같은 내부 상태를 다시 사용해 교착 상태나 손상을 일으킬 수 있습니다.

## 시그널 처리기에서 할 일을 줄이기

```c
static volatile sig_atomic_t pending;

static void handle_signal(int signal_number) {
    if (signal_number == SIGUSR1) {
        pending = 1;
    }
}
```

`sig_atomic_t`는 시그널 처리기와 일반 코드 사이에서 단순 읽기·쓰기에 사용합니다. 여러 필드를 한 번에 갱신하거나 복잡한 상태를 보호해 주는 타입은 아닙니다.

처리기에서는 가능한 한 다음만 수행합니다.

- `sig_atomic_t` 값 변경
- async-signal-safe로 명시된 함수 호출
- 필요한 경우 `errno` 저장과 복원

## `errno` 보존

시그널 처리기가 `write` 같은 함수를 호출하면 `errno`가 바뀔 수 있습니다. 중단된 코드가 보던 값을 유지합니다.

```c
static void handle_signal(int signal_number) {
    int saved_errno = errno;

    /* pending 플래그를 기록하고 write를 호출합니다. */

    errno = saved_errno;
}
```

## `sigaction`

```c
struct sigaction action;

memset(&action, 0, sizeof action);
action.sa_handler = handle_signal;
sigemptyset(&action.sa_mask);
action.sa_flags = 0;

if (sigaction(SIGUSR1, &action, &old_action) == -1) {
    return -1;
}
```

설치 전 동작을 저장하면 종료 시 복원할 수 있습니다. 여러 시그널을 설치하다 중간에 실패하면 이미 설치한 항목을 되돌립니다.

## 시그널 마스크

처리기와 처리기가 사용할 파일 디스크립터를 준비하는 사이에 시그널이 도착하면 초기화되지 않은 값을 사용할 수 있습니다. 관련 시그널을 먼저 차단하고 준비가 끝난 뒤 이전 마스크로 복원합니다.

```c
sigset_t blocked;
sigset_t previous;

sigemptyset(&blocked);
sigaddset(&blocked, SIGUSR1);
sigaddset(&blocked, SIGTERM);
sigprocmask(SIG_BLOCK, &blocked, &previous);

/* 파이프와 처리기 준비 */

sigprocmask(SIG_SETMASK, &previous, NULL);
```

정리할 때도 먼저 관련 시그널을 차단한 뒤 처리기에서 사용할 FD를 무효화하고 처리기를 복원합니다.

## Self-pipe

처리기에서 사건이 생겼다는 사실을 일반 코드에 알리기 위해 파이프를 사용할 수 있습니다.

```text
시그널 처리기
  pending 플래그 설정
  self-pipe 쓰기 끝에 한 바이트 쓰기 시도

주 반복문
  self-pipe 읽기 끝에서 깨우기 바이트 읽기
  관련 시그널을 잠시 차단
  pending 플래그를 복사한 뒤 초기화
  일반 코드에서 출력·종료 처리
```

처리기는 복잡한 작업을 하지 않고 주 반복문을 깨우는 역할만 합니다.

## 대기하지 않는 쓰기 끝

self-pipe가 가득 찬 상태에서 처리기가 대기할 수 있는 `write`를 호출하면 프로그램이 멈출 수 있습니다. 쓰기 끝을 `O_NONBLOCK`으로 설정합니다.

```c
int flags = fcntl(fd, F_GETFL);
fcntl(fd, F_SETFL, flags | O_NONBLOCK);
```

쓰기 실패를 무시할 수 있으려면 pending 플래그가 사건의 존재를 따로 보존해야 합니다. 이미 파이프 안에 깨우기 바이트가 하나라도 있으면 주 반복문은 깨어나 pending 플래그를 확인할 수 있습니다.

## 외부 프로그램 실행 시 닫기

self-pipe 양쪽에 `FD_CLOEXEC`를 설정하면 외부 명령 실행 뒤 불필요한 FD가 남는 것을 막을 수 있습니다.

```c
int flags = fcntl(fd, F_GETFD);
fcntl(fd, F_SETFD, flags | FD_CLOEXEC);
```

## 표준 시그널은 횟수를 보장하지 않습니다

동일한 표준 시그널이 여러 번 발생해도 pending 상태에서 하나로 합쳐질 수 있습니다. `SIGUSR1`이 정확히 64번 도착했다는 횟수를 세는 용도로 단순 플래그를 사용하지 않습니다.

정확한 큐와 데이터가 필요하면 실시간 시그널이나 다른 IPC 방법을 검토합니다.

## Pending 값을 안전하게 가져오기

일반 코드가 pending 플래그를 읽고 0으로 되돌리는 중에 처리기가 끼어들면 사건을 잃을 수 있습니다. 관련 시그널을 잠시 차단한 상태에서 값을 한 번에 가져옵니다.

```c
sigset_t previous;

sigprocmask(SIG_BLOCK, blocked, &previous);
*out_usr1 = usr1_pending != 0;
*out_term = term_pending != 0;
usr1_pending = 0;
term_pending = 0;
sigprocmask(SIG_SETMASK, &previous, NULL);
```

## 정리 순서

```text
관련 시그널 차단
→ 처리기가 사용할 쓰기 FD를 -1로 변경
→ 이전 처리기 복원
→ 파이프 양쪽 닫기
→ 이전 시그널 마스크 복원
```

FD를 먼저 닫고 처리기가 여전히 그 번호에 쓰게 두면 운영체제가 같은 번호를 다른 자원에 재사용했을 때 잘못된 FD에 쓸 수 있습니다.

## 테스트할 내용

- 준비 완료 출력이 먼저 나오는지
- 순차적인 `SIGUSR1`
- 짧은 시간에 여러 `SIGUSR1`
- `SIGTERM` 처리 후 상태 0 종료
- 종료 사건 뒤 추가 출력이 없는지
- 제한 시간 안에 끝나는지
- stderr에 예상하지 않은 출력이 없는지

## 완료 기준

1. 시그널 처리기에서 stdio 함수와 동적 할당을 사용하지 않습니다.
2. `errno`를 저장하고 복원합니다.
3. 관련 시그널을 차단한 상태에서 처리기와 FD를 준비합니다.
4. self-pipe 쓰기 끝을 `O_NONBLOCK`으로 설정합니다.
5. pending 플래그와 깨우기 바이트의 역할을 구분합니다.
6. 이전 처리기를 저장하고 실패·종료 시 복원합니다.
7. 표준 시그널이 합쳐질 수 있음을 테스트에 반영합니다.
