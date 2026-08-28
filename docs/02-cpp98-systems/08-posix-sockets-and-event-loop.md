# POSIX socket과 event loop

## 사용 시점

실제 프로젝트에서 여러 TCP 연결을 한 thread로 처리하거나, blocking I/O 때문에 한 연결이 다른 연결을 멈추게 할 때 참고합니다. 특정 application protocol보다 socket 수명과 부분 입출력을 먼저 다룹니다.

## TCP는 바이트 스트림입니다

한 번의 `send()`와 한 번의 `recv()`는 대응하지 않습니다.

```text
client send: "HEL" + "LO\n"
server recv: "HE" / "LLO\n"
```

또는 여러 줄이 한 번에 들어올 수 있습니다.

```text
server recv: "one\ntwo\nthree\n"
```

따라서 연결마다 입력 buffer를 보관하고 protocol delimiter가 나타날 때만 frame을 처리합니다.

## listener 만들기

일반적인 순서는 다음과 같습니다.

```text
socket
→ setsockopt(SO_REUSEADDR)
→ non-blocking·close-on-exec 설정
→ bind
→ listen
```

중간 실패 시 이미 연 fd를 닫습니다. `bind` 성공 전후를 구분해 별도 cleanup 경로를 누락하지 않습니다.

포트 `0`을 bind하면 운영체제가 빈 포트를 고를 수 있습니다. 테스트에서는 `getsockname()`으로 실제 포트를 확인합니다.

## non-blocking mode

`fcntl()`로 `O_NONBLOCK`을 추가합니다. 기존 flag를 덮어쓰지 않습니다.

```cpp
int flags = fcntl(fd, F_GETFL, 0);
fcntl(fd, F_SETFL, flags | O_NONBLOCK);
```

`FD_CLOEXEC`도 설정해 child process가 실행 파일로 바뀔 때 불필요한 fd가 남지 않게 합니다.

## `accept()` 반복

listener가 readable이면 한 client만 받지 않고 `EAGAIN`이 나올 때까지 반복합니다. 동시에 여러 연결이 대기 중일 수 있습니다.

- `EINTR`: 다시 시도합니다.
- `EAGAIN`/`EWOULDBLOCK`: 현재 받을 연결을 모두 처리했습니다.
- 그 밖의 오류: server 정책에 따라 보고하거나 종료합니다.

새 fd 설정, event 등록, connection 객체 생성과 map 삽입 중 하나가 실패할 수 있습니다. 모두 성공한 뒤 map으로 소유권을 넘기고, 실패하면 역순으로 정리합니다.

## 부분 읽기

readable event는 지금 읽으면 block되지 않을 가능성이 있다는 뜻입니다. 요청 전체가 도착했다는 뜻이 아닙니다.

```cpp
for (;;) {
    ssize_t count = recv(fd, buffer, sizeof(buffer), 0);
    if (count > 0)
        input.append(buffer, count);
    else if (count == 0)
        peer_closed = true;
    else if (errno == EAGAIN || errno == EWOULDBLOCK)
        break;
    else if (errno == EINTR)
        continue;
    else
        fail_connection();
}
```

입력 buffer 상한을 둡니다. delimiter 없이 계속 들어오는 client가 메모리를 무한히 사용하게 두지 않습니다.

## 부분 쓰기

`send()`는 요청한 바이트보다 적게 보낼 수 있습니다.

```text
output buffer: 1000 bytes
send result: 320
다음 writable event: offset 320부터 전송
```

연결별 output과 offset을 보관합니다. 모든 데이터를 보낸 뒤 buffer와 offset을 초기화합니다.

`SIGPIPE`로 process가 종료되지 않게 `MSG_NOSIGNAL` 또는 플랫폼에 맞는 socket option을 사용합니다. 지원하지 않는 플랫폼에서는 `SIGPIPE` 처리 방식을 별도로 정합니다.

## writable event를 필요할 때만 등록합니다

대부분의 socket은 평소 writable입니다. 항상 writable을 감시하면 event loop가 계속 깨어날 수 있습니다.

```text
pending output 없음 → read만 감시
pending output 있음 → read + write 감시
QUIT 응답 전송 중 → write만 감시
```

출력 완료 뒤 interest를 갱신합니다.

## backpressure

client가 응답을 읽지 않으면 kernel send buffer와 application output buffer가 찹니다. 연결별 pending output 상한을 정합니다.

상한을 넘긴 client만 닫으면 다른 연결은 계속 처리할 수 있습니다. 무제한 buffer는 느린 client가 server 메모리를 소진하게 만듭니다.

## epoll과 kqueue

서버 코드를 플랫폼 event bit에 직접 묶지 않고 `readable`, `writable`, `hangup`, `error` 값으로 바꿀 수 있습니다.

- Linux `epoll`: 한 event bit mask에 read/write/hangup이 함께 옵니다.
- BSD `kqueue`: read와 write filter가 별도 event로 올 수 있어 fd별로 합쳐야 합니다.

adapter가 event queue fd와 등록 상태를 소유하게 합니다.

## hangup과 남은 데이터

hangup event가 있어도 읽을 데이터가 남아 있을 수 있습니다. 플랫폼 event 의미를 확인하고 readable 처리를 먼저 할지 정합니다.

protocol 응답을 보내야 한다면 peer close 뒤에도 pending output을 처리할 수 있는지 요구사항을 확인합니다. 이미 상대가 읽기까지 닫았다면 전송이 실패할 수 있습니다.

## 종료와 fd 수명

`Connection` 객체가 client fd를 소유하게 하면 map에서 객체를 삭제할 때 fd도 닫을 수 있습니다. poller 등록과 fd 소유를 별도 상태로 추적해 두 번 닫거나 등록만 남기지 않습니다.

server 종료 순서는 다음처럼 정합니다.

```text
signal에서 종료 flag 설정
→ event wait에서 깨어남
→ 새 accept 중단
→ client event 등록 제거와 fd close
→ listener 등록 제거와 close
→ poller close
```

signal handler에서는 async-signal-safe 연산만 사용합니다. 복잡한 cleanup은 일반 제어 흐름에서 수행합니다.

## 테스트

- 한 줄을 여러 `send()`로 나눕니다.
- 여러 줄을 한 번에 보냅니다.
- 여러 client를 동시에 연결합니다.
- 응답을 읽지 않는 client로 output 상한을 채웁니다.
- 연결을 반복해 server fd 수가 증가하지 않는지 확인합니다.
- `SIGTERM` 뒤 제한 시간 안에 종료하는지 확인합니다.

## 완료 기준

- TCP stream과 message framing을 구분합니다.
- `EINTR`, `EAGAIN`, EOF와 일반 오류를 다르게 처리합니다.
- 연결별 input/output buffer와 전송 offset을 보관합니다.
- pending output이 있을 때만 writable을 감시합니다.
- 느린 client에 backpressure 상한을 적용합니다.
- 모든 accept·error·shutdown 경로에서 fd를 한 번만 닫습니다.
