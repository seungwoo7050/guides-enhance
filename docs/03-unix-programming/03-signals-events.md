# 시그널과 비동기 이벤트 전달

시그널 처리기(signal handler)는 프로그램의 일반 실행 흐름과 **비동기적으로** 실행될 수 있습니다. 즉, 일반 코드가 어떤 함수의 내부 상태를 수정하고 있는 순간에도 처리기가 끼어들 수 있습니다.

이 때문에 처리기에서 동적 메모리 할당, `stdio` 출력, mutex 잠금처럼 내부적으로 공유 상태나 잠금을 사용하는 작업을 수행하면 문제가 생길 수 있습니다. 예를 들어 일반 코드가 `malloc` 내부 잠금을 잡은 상태에서 시그널 처리기가 다시 `malloc`을 호출하면 같은 잠금을 기다리며 교착 상태가 될 수 있습니다.

따라서 시그널 처리기는 가능한 한 **사건이 발생했다는 사실만 기록하고**, 실제 처리는 일반 실행 흐름으로 넘기는 것이 기본 원칙입니다.

## 시그널 처리기에서 할 일을 줄이기

가장 단순한 방법은 `volatile sig_atomic_t` 플래그를 사용하는 것입니다.

```c
static volatile sig_atomic_t usr1_pending;

static void handle_signal(int signal_number) {
    if (signal_number == SIGUSR1) {
        usr1_pending = 1;
    }
}
```

`sig_atomic_t`는 시그널 처리기와 일반 코드 사이에서 **개별 값의 단순한 읽기·쓰기**에 사용할 수 있는 정수형입니다. `volatile`은 컴파일러가 해당 값을 일반 변수처럼 장기간 레지스터에만 보관하지 않고 실제 객체의 변경을 관찰하도록 하는 데 사용합니다.

하지만 다음까지 보장하는 타입은 아닙니다.

```text
여러 필드를 하나의 트랜잭션처럼 갱신
복합 연산 전체의 원자성
여러 스레드 사이의 일반적인 동기화
복잡한 자료구조 보호
```

예를 들어 다음 연산은 단순 대입과 다릅니다.

```c
counter++;
```

이는 개념적으로 읽기, 증가, 쓰기의 여러 단계로 이루어질 수 있으므로 "시그널이 올 때마다 정확히 1씩 증가하는 카운터"로 사용한다고 가정하면 안 됩니다. 표준 시그널 자체도 여러 발생이 하나의 pending 상태로 합쳐질 수 있으므로 정확한 발생 횟수 기록에는 적합하지 않습니다.

처리기에서는 가능한 한 다음만 수행합니다.

- `volatile sig_atomic_t` 플래그 변경
- POSIX가 **async-signal-safe**라고 명시한 함수 호출
- 필요한 경우 `errno` 저장과 복원

`printf`, `fprintf`, `malloc`, `free`, 대부분의 mutex 관련 함수는 처리기 안에서 일반적으로 사용하면 안 됩니다.

## async-signal-safe

**async-signal-safe 함수**는 시그널 처리기에서 호출해도 안전하다고 POSIX가 명시한 함수입니다.

대표적으로 `write`는 async-signal-safe이므로 self-pipe에 한 바이트를 쓰는 용도로 사용할 수 있습니다.

```c
unsigned char byte = 1;
write(signal_pipe[1], &byte, 1);
```

반대로 `stdio` 함수는 내부 버퍼와 잠금을 사용하므로 처리기에서 호출하지 않습니다.

```c
/* 처리기에서 피해야 하는 예 */
printf("signal\n");
fprintf(stderr, "signal\n");
```

"평소에는 잘 동작한다"는 것은 안전성의 근거가 아닙니다. 시그널은 일반 코드가 해당 라이브러리 내부 상태를 수정하는 정확한 순간에도 도착할 수 있습니다.

## `errno` 보존

시그널 처리기는 일반 코드가 실행되던 도중 끼어듭니다. 처리기에서 `write` 같은 함수를 호출하면 `errno`가 바뀔 수 있으므로, 중단된 일반 코드가 관찰해야 할 값을 보존합니다.

```c
static void handle_signal(int signal_number) {
    int saved_errno = errno;

    if (signal_number == SIGUSR1) {
        usr1_pending = 1;

        unsigned char byte = 1;
        (void)write(signal_pipe[1], &byte, 1);
    }

    errno = saved_errno;
}
```

처리기 안에서 호출한 `write`가 실패하더라도 일반 코드의 `errno`를 그 실패 값으로 덮어쓰지 않는 것이 목적입니다.

## `sigaction`

POSIX에서는 일반적으로 `signal`보다 `sigaction`을 사용해 시그널 동작을 설치합니다.

```c
struct sigaction action;
struct sigaction old_action;

memset(&action, 0, sizeof action);
action.sa_handler = handle_signal;
sigemptyset(&action.sa_mask);
action.sa_flags = 0;

if (sigaction(SIGUSR1, &action, &old_action) == -1) {
    return -1;
}
```

각 필드의 의미는 다음과 같습니다.

```text
sa_handler  호출할 처리기
sa_mask     이 처리기가 실행되는 동안 추가로 차단할 시그널 집합
sa_flags    처리 방식에 대한 옵션
```

특별히 설정하지 않아도 현재 처리 중인 시그널은 보통 그 처리기가 실행되는 동안 자동으로 차단됩니다. 동일 시그널의 재진입을 허용하는 `SA_NODEFER` 같은 옵션을 사용하지 않는 한 처리기 하나가 같은 시그널로 계속 중첩 호출되는 상황을 피할 수 있습니다.

설치 전 동작을 `old_action`에 저장하면 정리할 때 원래 처리기로 복원할 수 있습니다.

여러 시그널을 설치하는 중간에 하나가 실패했다면 이미 바꾼 시그널 동작도 원래 상태로 되돌려야 합니다.

```text
SIGUSR1 설치 성공
→ SIGTERM 설치 실패
→ SIGUSR1의 이전 동작 복원
→ 오류 반환
```

## `SA_RESTART`

일부 시스템 호출은 시그널 처리기 실행 때문에 중단되어 `-1`과 `errno == EINTR`을 반환할 수 있습니다.

`sigaction`의 `SA_RESTART`를 사용하면 일부 중단 가능한 시스템 호출이 자동으로 재시작될 수 있습니다.

```c
action.sa_flags = SA_RESTART;
```

하지만 다음 점을 구분해야 합니다.

```text
SA_RESTART를 설정했다고 모든 시스템 호출이 항상 재시작되는 것은 아님
SA_RESTART를 사용하지 않았다고 모든 호출이 반드시 EINTR이 되는 것도 아님
```

따라서 시그널을 사용하는 프로그램은 자신이 호출하는 함수가 `EINTR`을 어떻게 처리해야 하는지 별도로 정해야 합니다.

self-pipe를 사용하는 이벤트 루프에서는 시그널 자체가 대기 함수를 깨우는 것보다 **파이프가 읽기 가능해져 대기 함수가 정상적으로 반환되는 구조**를 만드는 것이 핵심입니다.

## 시그널 마스크

처리기와 처리기가 사용할 자원을 준비하는 사이에 시그널이 도착하면 처리기가 아직 초기화되지 않은 FD나 상태를 사용할 수 있습니다.

예를 들어 다음 순서는 위험합니다.

```text
처리기 설치
→ 아직 self-pipe 미생성
→ SIGUSR1 도착
→ 처리기가 존재하지 않는 쓰기 FD 사용
```

따라서 관련 시그널을 먼저 차단하고 모든 준비가 끝난 뒤 이전 마스크를 복원합니다.

```c
sigset_t blocked;
sigset_t previous;

sigemptyset(&blocked);
sigaddset(&blocked, SIGUSR1);
sigaddset(&blocked, SIGTERM);

if (sigprocmask(SIG_BLOCK, &blocked, &previous) == -1) {
    return -1;
}

/* self-pipe 생성 */
/* FD 플래그 설정 */
/* pending 상태 초기화 */
/* sigaction 설치 */

if (sigprocmask(SIG_SETMASK, &previous, NULL) == -1) {
    /* 오류 처리 */
}
```

이 구조에서 중요한 것은 **시그널이 처리기를 호출할 수 있는 시점에는 처리기가 참조하는 모든 상태가 이미 유효해야 한다**는 것입니다.

정리할 때는 반대 방향으로 보호합니다.

```text
관련 시그널 차단
→ 처리기가 더 이상 자원을 사용하지 않게 만듦
→ 이전 처리기 복원
→ self-pipe 닫기
→ 이전 시그널 마스크 복원
```

### 다중 스레드 프로그램

`sigprocmask`는 단일 스레드 프로그램의 설명에 적합합니다. POSIX 스레드를 사용하는 프로그램에서는 각 스레드의 시그널 마스크를 다루기 위해 일반적으로 `pthread_sigmask`를 사용합니다.

또한 시그널은 프로세스 전체와 스레드별 마스크의 상호작용을 받으므로, 여러 스레드가 있는 프로그램에서는 "어느 스레드가 어떤 시그널을 받는가"까지 별도로 설계해야 합니다.

이 문서의 self-pipe 예시는 우선 **단일 스레드 이벤트 루프**를 기준으로 이해하면 됩니다.

## Self-pipe

self-pipe는 시그널 처리기에서 복잡한 작업을 하지 않고, 일반 이벤트 루프를 깨우기 위한 기법입니다.

```text
시그널 처리기
  pending 플래그 설정
  self-pipe 쓰기 끝에 한 바이트 쓰기 시도
          │
          ▼
이벤트 루프의 poll/select가 깨어남
          │
          ▼
일반 코드
  self-pipe를 비움
  관련 시그널을 잠시 차단
  pending 상태를 가져와 초기화
  실제 출력·종료·상태 변경 수행
```

역할을 분리해서 이해해야 합니다.

```text
pending 플래그
    사건이 발생했다는 논리적 상태를 보존

self-pipe의 바이트
    poll/select 같은 대기 함수를 깨우는 알림
```

즉, 파이프의 각 바이트를 "시그널 한 번"과 정확히 대응시키지 않습니다.

## 대기하지 않는 쓰기 끝

self-pipe가 가득 찬 상태에서 처리기가 blocking `write`를 호출하면, 일반 코드는 처리기가 끝나기를 기다리고 처리기는 파이프 공간이 생기기를 기다리는 형태로 프로그램 전체가 멈출 수 있습니다.

따라서 처리기에서 사용하는 쓰기 끝은 `O_NONBLOCK`으로 설정합니다.

```c
int flags = fcntl(signal_pipe[1], F_GETFL);
if (flags == -1) {
    /* 오류 처리 */
}

if (fcntl(signal_pipe[1], F_SETFL, flags | O_NONBLOCK) == -1) {
    /* 오류 처리 */
}
```

기존 상태 플래그를 보존하기 위해 `F_GETFL` 결과에 `O_NONBLOCK`을 추가합니다.

처리기에서는 쓰기가 실패해도 기다리지 않습니다.

```c
static void handle_signal(int signal_number) {
    int saved_errno = errno;

    if (signal_number == SIGUSR1) {
        usr1_pending = 1;

        unsigned char byte = 1;
        ssize_t result = write(signal_pipe[1], &byte, 1);

        /*
         * EAGAIN/EWOULDBLOCK이라면 파이프가 이미 가득 찬 상태입니다.
         * pending 플래그가 사건의 존재를 보존하므로 여기서 대기하지 않습니다.
         */
        (void)result;
    }

    errno = saved_errno;
}
```

파이프가 가득 찼다는 것은 일반적으로 이미 읽기 가능한 바이트가 충분히 들어 있다는 뜻이므로 이벤트 루프는 깨어날 수 있습니다. 이때 사건 자체의 존재는 별도 pending 플래그가 보존합니다.

## 읽기 끝도 non-blocking으로 만드는 이유

이벤트 루프에서 self-pipe를 한 번 깨어난 뒤 **현재 쌓인 깨우기 바이트를 모두 비우려면** 읽기 끝도 `O_NONBLOCK`으로 두는 것이 편리합니다.

```c
for (;;) {
    unsigned char buffer[128];
    ssize_t count = read(signal_pipe[0], buffer, sizeof buffer);

    if (count > 0) {
        continue;
    }

    if (count == -1 && errno == EINTR) {
        continue;
    }

    if (count == -1 &&
        (errno == EAGAIN || errno == EWOULDBLOCK)) {
        break;
    }

    if (count == 0) {
        /* 쓰기 끝이 모두 닫힌 경우 */
        break;
    }

    /* 그 밖의 오류 처리 */
    break;
}
```

읽기 끝을 blocking으로 유지할 수도 있지만, 그러면 "더 이상 읽을 바이트가 없는 시점"을 확인하려고 추가 `read`를 호출했을 때 다시 대기할 수 있습니다.

따라서 self-pipe를 이벤트 알림용으로 사용한다면 양 끝을 모두 non-blocking으로 설정하는 설계가 흔합니다.

## 외부 프로그램 실행 시 닫기

self-pipe는 현재 프로세스 내부의 이벤트 전달용이므로 외부 프로그램이 `exec`된 뒤까지 남을 필요가 없는 경우가 일반적입니다.

각 끝에 `FD_CLOEXEC`를 설정합니다.

```c
int flags = fcntl(fd, F_GETFD);
if (flags == -1) {
    /* 오류 처리 */
}

if (fcntl(fd, F_SETFD, flags | FD_CLOEXEC) == -1) {
    /* 오류 처리 */
}
```

이 플래그는 **`exec` 성공 시 해당 FD를 자동으로 닫도록** 합니다. 단순한 `fork`만으로는 닫히지 않습니다.

멀티스레드 프로그램에서는 `pipe`를 만든 뒤 `fcntl`로 `FD_CLOEXEC`를 설정하는 짧은 사이에 다른 스레드가 `fork`/`exec`를 수행하는 경쟁 조건이 생길 수 있습니다. Linux의 `pipe2(..., O_CLOEXEC | O_NONBLOCK)`는 이를 줄일 수 있지만 `pipe2` 자체는 POSIX 표준 인터페이스가 아니므로 이식성이 필요한 코드에서는 구분해서 사용해야 합니다.

## 표준 시그널은 횟수를 보장하지 않습니다

동일한 **표준 시그널**이 처리되기 전에 여러 번 발생해도 여러 개가 개별적으로 큐에 저장된다는 보장은 없습니다.

예를 들어 `SIGUSR1`이 짧은 시간 동안 여러 번 발생했을 때 논리적으로 다음과 같이 합쳐질 수 있습니다.

```text
SIGUSR1
SIGUSR1
SIGUSR1
    ↓
pending SIGUSR1 하나
```

따라서 다음 플래그는 적합합니다.

```text
"SIGUSR1이 적어도 한 번 발생했다"
```

하지만 다음 정보는 보장하지 않습니다.

```text
"SIGUSR1이 정확히 64번 발생했다"
```

self-pipe에 쓴 바이트 수도 정확한 발생 횟수로 사용하면 안 됩니다. 파이프가 가득 찼을 때 알림 바이트 쓰기를 버릴 수 있기 때문입니다.

정확한 큐잉과 부가 데이터가 필요하면 POSIX 실시간 시그널이나 다른 IPC 방법을 검토합니다.

## Pending 값을 안전하게 가져오기

다음 코드는 경쟁 조건이 있습니다.

```c
if (usr1_pending) {
    usr1_pending = 0;
    handle_usr1();
}
```

예를 들어 다음 순서가 가능하기 때문입니다.

```text
일반 코드: usr1_pending이 1임을 읽음
처리기:    새 SIGUSR1을 받고 usr1_pending = 1
일반 코드: usr1_pending = 0
```

새로 도착한 사건까지 일반 코드가 0으로 덮어써 버렸습니다.

따라서 관련 시그널을 잠시 차단한 상태에서 값을 복사하고 초기화합니다.

```c
sigset_t previous;

if (sigprocmask(SIG_BLOCK, &blocked, &previous) == -1) {
    /* 오류 처리 */
}

sig_atomic_t got_usr1 = usr1_pending;
sig_atomic_t got_term = term_pending;

usr1_pending = 0;
term_pending = 0;

if (sigprocmask(SIG_SETMASK, &previous, NULL) == -1) {
    /* 오류 처리 */
}

if (got_usr1) {
    /* 일반 코드에서 실제 처리 */
}

if (got_term) {
    /* 일반 코드에서 종료 처리 */
}
```

핵심은 **복사와 초기화가 관련 시그널 처리기와 서로 끼어들지 못하게 만드는 것**입니다.

## 이벤트 대기 직전의 경쟁 조건

pending 플래그만 사용하는 경우 다음과 같은 경쟁이 생길 수 있습니다.

```text
일반 코드: pending 없음 확인
시그널 도착: pending = 1
일반 코드: poll/select에 들어가 무기한 대기
```

self-pipe를 사용하면 처리기가 파이프에도 바이트를 쓰므로, 시그널이 대기 직전에 발생하더라도 파이프가 읽기 가능한 상태로 남아 있어 이벤트 루프가 즉시 깨어날 수 있습니다.

다만 이벤트 대기와 시그널 마스크 변경을 조합하는 더 일반적인 패턴에서는 `pselect` 또는 `ppoll`을 사용할 수 있습니다. 이 함수들은 **대기 시작과 시그널 마스크 변경을 원자적으로 연결**할 수 있어 "마스크를 풀고 실제 대기에 들어가기 직전"의 틈을 제거하는 데 유용합니다.

개념적으로는 다음 문제를 피합니다.

```text
시그널 차단
→ pending 확인
→ 시그널 차단 해제
       ← 이 순간 시그널 발생
→ poll 시작
```

`pselect`/`ppoll`은 이런 구조가 필요한 이벤트 루프에서 중요한 도구입니다. 다만 self-pipe만으로 충분한 단순 구조라면 반드시 둘을 동시에 사용해야 하는 것은 아닙니다.

## 이벤트 루프의 처리 순서

self-pipe와 pending 플래그를 함께 사용할 때 한 가지 명확한 처리 순서는 다음과 같습니다.

```text
1. poll/select로 self-pipe 읽기 가능 여부 대기
2. self-pipe에 쌓인 깨우기 바이트를 가능한 만큼 비움
3. 관련 시그널 차단
4. pending 플래그를 지역 변수로 복사
5. pending 플래그 초기화
6. 이전 시그널 마스크 복원
7. 지역 변수에 따라 실제 작업 수행
8. 다시 이벤트 대기
```

시그널이 어느 단계에 도착하는지도 생각해야 합니다.

```text
파이프를 비우기 전에 도착
→ 기존 바이트와 함께 처리 가능

파이프를 비운 직후 도착
→ 새 pending 설정 + 새 깨우기 바이트 기록
→ 다음 대기에서 즉시 관찰 가능

pending을 복사·초기화하는 동안 도착
→ 관련 시그널이 차단되어 있으므로 그 구간이 끝난 뒤 처리됨
```

이처럼 파이프는 **깨우기**, pending 플래그는 **논리적 사건 보존**이라는 두 역할을 함께 수행합니다.

## 종료 사건 처리

예를 들어 `SIGTERM`을 즉시 프로세스를 끝내는 대신 이벤트 루프에 전달해 정상 정리를 수행하려면 처리기에서는 종료하지 않고 플래그만 설정합니다.

```c
static volatile sig_atomic_t term_pending;

static void handle_signal(int signal_number) {
    int saved_errno = errno;

    if (signal_number == SIGTERM) {
        term_pending = 1;

        unsigned char byte = 1;
        (void)write(signal_pipe[1], &byte, 1);
    }

    errno = saved_errno;
}
```

일반 코드가 플래그를 가져온 뒤 정리합니다.

```text
SIGTERM 도착
→ 처리기가 term_pending 설정
→ 이벤트 루프 깨어남
→ 일반 코드가 term_pending 확인
→ 필요한 출력 및 자원 정리
→ 상태 0 등 API가 정한 종료 상태로 종료
```

이 구조에서는 "SIGTERM을 받았으므로 반드시 시그널 종료 상태가 된다"는 뜻이 아닙니다. 처리기가 시그널을 소비하고 일반 코드가 정상 종료를 선택하면 프로세스는 일반 종료가 됩니다.

어떤 종료 상태를 사용할지는 프로그램의 공개 계약으로 명시합니다.

## 정리 순서

정리 중 가장 위험한 상황은 **처리기가 아직 사용하는 FD를 먼저 닫는 것**입니다.

예를 들어 self-pipe의 쓰기 끝이 FD `5`였다고 가정합니다.

```text
close(5)
→ 운영체제가 다른 파일을 열면서 다시 FD 5 사용
→ SIGUSR1 도착
→ 오래된 처리기가 FD 5에 write
→ 전혀 다른 자원에 쓰기
```

이를 막기 위해 관련 시그널을 차단한 상태에서 처리기가 더 이상 FD를 사용할 수 없도록 만든 뒤 닫습니다.

개념적인 순서는 다음과 같습니다.

```text
관련 시그널 차단
→ 처리기에서 사용할 self-pipe 상태를 무효화
→ 이전 sigaction 복원
→ self-pipe 읽기 끝과 쓰기 끝 닫기
→ pending 상태 정리
→ 이전 시그널 마스크 복원
```

처리기가 쓰기 FD가 유효한지 검사하는 구조라면 다음과 같은 상태를 둘 수 있습니다.

```c
static volatile sig_atomic_t signal_write_fd = -1;
```

초기화가 끝난 뒤 유효한 FD 값을 공개하고, 정리할 때 관련 시그널이 차단된 상태에서 먼저 `-1`로 바꾼 뒤 실제 FD를 닫습니다.

다만 FD 번호를 `sig_atomic_t`에 저장하는 설계는 구현에서 해당 값의 표현 범위를 확인해야 합니다. 더 단순하게는 **처리기가 설치되어 있는 동안 self-pipe FD 자체를 절대 변경하지 않고**, 관련 시그널을 차단한 상태에서 처리기를 먼저 복원한 뒤 FD를 닫는 방식도 사용할 수 있습니다.

## 초기화 실패 시 되돌리기

초기화 과정에는 여러 실패 지점이 있습니다.

```text
시그널 차단
→ pipe 생성
→ O_NONBLOCK 설정
→ FD_CLOEXEC 설정
→ 첫 번째 sigaction 설치
→ 두 번째 sigaction 설치
→ 원래 마스크 복원
```

중간에 실패하면 지금까지 획득하거나 변경한 상태를 역순으로 정리해야 합니다.

예를 들어 두 번째 `sigaction`에서 실패했다면 다음이 필요할 수 있습니다.

```text
원래 errno 저장
→ 첫 번째 시그널의 이전 처리기 복원
→ 파이프 양 끝 닫기
→ 이전 시그널 마스크 복원
→ 원래 errno 복원
→ 실패 반환
```

정리 함수들이 `errno`를 바꿀 수 있으므로 호출자에게 보고할 원래 오류가 중요하다면 정리 전에 저장합니다.

## 테스트할 내용

- 초기화가 끝난 뒤에만 관련 시그널을 허용하는지
- 준비 완료 출력이 먼저 나오는지
- 순차적인 `SIGUSR1`
- 짧은 시간에 여러 `SIGUSR1`
- 여러 표준 시그널이 하나의 pending 상태로 합쳐져도 요구사항을 만족하는지
- self-pipe가 가득 찬 상황에서도 처리기가 blocking하지 않는지
- self-pipe에 깨우기 바이트가 여러 개 쌓였을 때 모두 안전하게 drain하는지
- pending 플래그를 읽고 초기화하는 동안 사건이 유실되지 않는지
- 이벤트 대기 직전에 시그널이 도착해도 무기한 잠들지 않는지
- `read`, `poll`, `select` 등이 `EINTR`을 반환하는 경우의 처리
- `SA_RESTART` 사용 여부에 따른 동작
- `SIGTERM`을 일반 코드에서 처리한 뒤 정한 상태로 종료하는지
- 종료 사건을 처리한 뒤 예상하지 않은 추가 출력이 없는지
- 정리 중 관련 시그널이 도착해도 닫힌 FD나 재사용된 FD에 쓰지 않는지
- `exec`된 외부 프로그램에 self-pipe FD가 남지 않는지
- 초기화 중간 실패 후 처리기, 마스크, FD가 모두 원래 상태로 돌아오는지
- 제한 시간 안에 끝나는지
- stderr에 예상하지 않은 출력이 없는지

## 완료 기준

1. 시그널 처리기에서 `stdio`, 동적 할당, mutex 같은 async-signal-safe가 아닌 작업을 수행하지 않습니다.
2. 처리기에서 다른 함수를 호출할 수 있으므로 `errno`를 저장하고 복원합니다.
3. `sig_atomic_t` 플래그는 사건의 존재를 기록하는 용도이며 복잡한 동기화나 정확한 횟수 기록용이 아님을 설명합니다.
4. 관련 시그널을 차단한 상태에서 처리기와 self-pipe를 준비하고, 준비 완료 뒤 이전 마스크를 복원합니다.
5. self-pipe의 쓰기 끝을 `O_NONBLOCK`으로 설정하여 처리기가 절대 파이프 공간을 기다리지 않게 합니다.
6. 필요하면 읽기 끝도 non-blocking으로 설정하여 깨우기 바이트를 안전하게 drain합니다.
7. pending 플래그는 논리적 사건을 보존하고 self-pipe 바이트는 이벤트 루프를 깨우는 역할임을 구분합니다.
8. pending 값을 가져와 초기화하는 동안 관련 시그널을 차단하여 새 사건을 잃지 않습니다.
9. 이벤트 대기 직전의 경쟁 조건을 설명하고 self-pipe 또는 `pselect`/`ppoll`이 이를 어떻게 다루는지 구분합니다.
10. `SA_RESTART`가 모든 시스템 호출의 `EINTR`을 제거하는 기능은 아님을 설명합니다.
11. self-pipe FD에 `FD_CLOEXEC`를 설정하여 외부 프로그램으로 불필요하게 상속되지 않게 합니다.
12. 표준 시그널은 여러 발생이 하나의 pending 상태로 합쳐질 수 있으므로 정확한 횟수를 보장하지 않음을 테스트에 반영합니다.
13. 이전 시그널 처리기를 저장하고 초기화 실패와 정상 종료 모두에서 복원합니다.
14. 정리 시 관련 시그널을 먼저 차단하고 처리기가 더 이상 FD를 사용할 수 없게 한 뒤 FD를 닫습니다.
15. 초기화 중간 실패에서도 이미 변경한 시그널 동작, 마스크, FD를 되돌리고 원래 오류를 보존합니다.
