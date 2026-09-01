# POSIX socket과 event loop

## 사용 시점

실제 프로젝트에서 여러 TCP 연결을 한 thread로 처리하거나, 한 연결의 blocking I/O 때문에 다른 연결까지 멈추는 문제를 해결할 때 참고합니다.

이 문서는 특정 application protocol의 명령 형식보다 먼저 다음 문제를 다룹니다.

- TCP가 message가 아니라 byte stream이라는 점
- listener와 client socket의 수명
- non-blocking I/O의 성공·재시도·종료 조건
- 부분 읽기와 부분 쓰기
- 연결별 input/output buffer
- writable event를 등록하고 해제하는 시점
- 느린 client에 대한 backpressure
- `epoll`/`kqueue` 같은 event backend와 상위 event loop의 분리
- signal 기반 종료와 file descriptor 정리

핵심은 다음과 같습니다.

> event가 왔다는 사실과 application 요청 하나가 완성되었다는 사실을 구분하고, 각 연결의 미완성 상태를 객체에 보관합니다.

## TCP는 바이트 스트림입니다

TCP는 application이 `send()`한 호출 단위를 그대로 보존하지 않습니다.

client가 다음처럼 두 번 보냈다고 가정합니다.

```text
send("HEL")
send("LO\n")
```

server가 같은 경계로 받는다는 보장은 없습니다.

예를 들어:

```text
recv #1: "HE"
recv #2: "LLO\n"
```

처럼 받을 수 있습니다.

반대로 client가 여러 요청을 따로 보냈더라도 server의 한 번의 `recv()`에서 함께 들어올 수 있습니다.

```text
recv: "one\ntwo\nthree\n"
```

즉, 다음 대응 관계를 가정하면 안 됩니다.

```text
한 번의 send()
↔
한 번의 recv()
```

TCP가 보장하는 것은 연결된 byte stream의 순서이지 application message 경계가 아닙니다.

## framing은 application protocol의 책임입니다

TCP 위에서 줄 단위 protocol을 사용한다면 application이 `'\n'`을 message delimiter로 정의해야 합니다.

연결마다 input buffer를 둡니다.

```text
recv 결과
→ connection input buffer에 append
→ delimiter 검색
→ 완성된 frame만 parser에 전달
→ 남은 불완전 byte는 buffer에 유지
```

예를 들어:

```text
첫 recv : "PUT a "
둘째 recv: "1\nGET a\nPAR"
```

이라면 두 번째 recv 뒤에는:

```text
완성 frame:
"PUT a 1\n"
"GET a\n"

남은 incomplete data:
"PAR"
```

처럼 처리할 수 있습니다.

다음 recv에서:

```text
"TIAL\n"
```

이 오면 남아 있던 `"PAR"`과 합쳐 하나의 frame이 됩니다.

## delimiter가 없다고 오류는 아닙니다

non-blocking socket에서 한 번 읽은 뒤 delimiter가 없다는 것은 요청이 잘못되었다는 뜻이 아닙니다.

단지 아직 frame 전체가 도착하지 않았을 수 있습니다.

```text
recv: "HEL"
```

만 받은 상태라면:

```text
input buffer = "HEL"
```

을 유지하고 다음 readable event를 기다립니다.

다만 protocol에서 허용하는 최대 frame 크기나 input buffer 크기는 반드시 제한해야 합니다.

delimiter 없이 무한히 데이터를 보내는 client가 server memory를 계속 소비하게 두면 안 됩니다.

## listener 만들기

일반적인 listener 생성 순서는 다음과 같습니다.

```text
socket
→ SO_REUSEADDR 설정
→ non-blocking 설정
→ close-on-exec 설정
→ bind
→ listen
→ event backend에 등록
```

실제 코드에서는 각 단계가 실패할 수 있으므로 이미 획득한 자원을 역순으로 정리해야 합니다.

예를 들어:

```text
socket 성공
setsockopt 성공
fcntl 성공
bind 실패
```

라면 이미 열린 listener fd는 반드시 `close()`해야 합니다.

listener 객체가 fd를 소유하도록 만들면 생성 실패와 정상 소멸에서 같은 소유권 규칙을 적용하기 쉽습니다.

## `SO_REUSEADDR`

server를 종료한 직후 같은 주소와 포트에 다시 `bind()`하려 할 때 TCP 연결 상태 때문에 실패할 수 있습니다.

일반적인 TCP server에서는 listener에 다음 option을 설정할 수 있습니다.

```cpp
int yes = 1;

if (::setsockopt(
        fd,
        SOL_SOCKET,
        SO_REUSEADDR,
        &yes,
        sizeof(yes)) == -1) {
    // 오류 처리
}
```

`SO_REUSEADDR`의 정확한 의미는 운영체제와 socket 상태에 따라 세부 차이가 있으므로 "어떤 상황에서도 이미 사용 중인 port를 강제로 공유한다"는 의미로 이해하면 안 됩니다.

## port `0`

`bind()`할 port에 `0`을 지정하면 운영체제가 사용 가능한 ephemeral port를 선택할 수 있습니다.

이는 테스트에서 고정 port 충돌을 피할 때 유용합니다.

```text
bind(port = 0)
→ kernel이 실제 port 선택
→ getsockname()으로 선택된 port 확인
```

따라서 테스트 코드에서 "0번 port에 연결한다"는 뜻이 아닙니다.

`bind()`가 끝난 뒤 listener에 실제로 할당된 port를 `getsockname()`으로 읽어 client에게 알려 주어야 합니다.

## non-blocking mode

일반적인 event loop에서는 listener와 client socket을 non-blocking으로 설정합니다.

`fcntl()`로 현재 file status flag를 읽은 뒤 `O_NONBLOCK`을 추가합니다.

```cpp
int flags = ::fcntl(fd, F_GETFL, 0);

if (flags == -1)
    throw SocketError("F_GETFL failed");

if (::fcntl(
        fd,
        F_SETFL,
        flags | O_NONBLOCK) == -1) {
    throw SocketError("F_SETFL failed");
}
```

기존 flag를 읽지 않고 다음처럼 덮어쓰지 않습니다.

```cpp
fcntl(fd, F_SETFL, O_NONBLOCK);
```

다른 status flag가 이미 있었다면 사라질 수 있기 때문입니다.

## `FD_CLOEXEC`는 다른 종류의 flag입니다

`O_NONBLOCK`과 `FD_CLOEXEC`는 같은 방식으로 설정하지 않습니다.

`O_NONBLOCK`은 file status flag이므로:

```text
F_GETFL
F_SETFL
```

을 사용합니다.

반면 `FD_CLOEXEC`는 file descriptor flag이므로:

```text
F_GETFD
F_SETFD
```

를 사용합니다.

예:

```cpp
int flags = ::fcntl(fd, F_GETFD, 0);

if (flags == -1)
    throw SocketError("F_GETFD failed");

if (::fcntl(
        fd,
        F_SETFD,
        flags | FD_CLOEXEC) == -1) {
    throw SocketError("F_SETFD failed");
}
```

`FD_CLOEXEC`를 설정하면 이 process가 `exec` 계열 함수로 새 실행 파일을 실행할 때 해당 fd가 자동으로 닫힙니다.

이는 child process가 의도하지 않은 server socket이나 client socket을 계속 보유하는 문제를 줄입니다.

## listener와 accepted socket은 별도입니다

listener를 non-blocking으로 설정했다고 해서 새로 `accept()`한 모든 client fd가 모든 POSIX 환경에서 같은 설정을 자동으로 가진다고 가정하면 안 됩니다.

새 client fd마다 필요한 설정을 적용합니다.

```text
accept
→ 새 fd에 O_NONBLOCK
→ 새 fd에 FD_CLOEXEC
→ Connection 준비
→ event backend 등록
→ 소유 container에 저장
```

플랫폼별로 flag를 원자적으로 설정하면서 accept하는 확장 API가 있을 수 있지만, 이식 가능한 코드에서는 플랫폼 지원 여부를 별도로 구분합니다.

## `accept()`는 한 번만 호출하지 않습니다

listener가 readable이라는 event를 받았다고 해서 대기 중인 connection이 정확히 하나라는 뜻은 아닙니다.

event loop가 다시 wait로 돌아가기 전에 현재 받을 수 있는 connection을 모두 처리하려면 `accept()`를 반복합니다.

개념적인 구조:

```cpp
for (;;) {
    int client = ::accept(listener, 0, 0);

    if (client >= 0) {
        // 새 connection 준비
        continue;
    }

    if (errno == EINTR)
        continue;

    if (errno == EAGAIN
        || errno == EWOULDBLOCK)
        break;

    // 다른 오류 처리
}
```

## `accept()` 오류의 의미

### 성공

```cpp
client >= 0
```

새 client fd를 얻었습니다.

이 fd의 설정과 connection 등록을 처리한 뒤 다음 `accept()`를 시도합니다.

### `EINTR`

signal 때문에 system call이 중단되었습니다.

현재 server 정책상 다시 시도할 수 있다면:

```cpp
continue;
```

합니다.

단, 종료 signal 때문에 종료 flag가 설정되었다면 무조건 재시도하기보다 상위 종료 조건을 확인할 수 있습니다.

### `EAGAIN` 또는 `EWOULDBLOCK`

non-blocking listener에 현재 더 이상 즉시 받아 올 connection이 없습니다.

이는 일반적인 loop 종료 조건이지 server 오류가 아닙니다.

```cpp
break;
```

후 event wait로 돌아갑니다.

POSIX에서는 두 값이 같을 수도 있고 다를 수도 있으므로 둘 다 검사하는 형태가 안전합니다.

### 그 밖의 오류

server 정책에 따라:

- 오류 기록 후 계속 실행
- listener 복구 시도
- server 종료

중 하나를 선택합니다.

모든 `accept()` 오류를 server 전체 종료로 취급할 필요는 없지만, 무시하고 무한 반복해서도 안 됩니다.

## 새 connection 등록은 여러 단계입니다

`accept()`가 성공했다고 즉시 connection 설정이 끝난 것은 아닙니다.

다음 단계가 각각 실패할 수 있습니다.

```text
client fd 획득
→ non-blocking 설정
→ close-on-exec 설정
→ Connection 객체 준비
→ event backend 등록
→ connection map 삽입
```

소유권 이전 시점을 명확히 정해야 합니다.

예를 들어:

```text
map 삽입 성공 전
→ 지역 코드가 client fd를 책임짐

map 삽입 성공 후
→ Connection/Server가 fd를 소유
```

이라고 정할 수 있습니다.

중간 실패 시 아직 소유권이 넘어가지 않은 fd와 객체를 역순으로 정리합니다.

## 등록 성공과 map 삽입 성공 사이도 고려합니다

예를 들어 poller에는 fd를 등록했지만 connection map 삽입이 실패할 수 있습니다.

```text
poller.add(fd) 성공
map.insert(...) 실패
```

이 경우 poller 등록을 제거하고 fd를 닫아야 합니다.

반대 순서라면:

```text
map.insert(...) 성공
poller.add(fd) 실패
```

map에서 다시 제거하면서 Connection 소멸을 통해 fd를 닫는 식으로 정리할 수 있습니다.

핵심은 각 단계마다 다음 질문에 답할 수 있어야 한다는 것입니다.

```text
현재 fd의 소유자는 누구인가?
현재 poller에 등록되어 있는가?
실패하면 어떤 순서로 되돌릴 것인가?
```

## readable event의 의미

readable event는 대략 다음을 의미합니다.

> 지금 읽기를 시도하면 적어도 현재 알려진 상태를 처리할 수 있다.

하지만 다음 의미는 아닙니다.

```text
요청 하나 전체가 도착했다.
```

TCP는 byte stream이므로 요청 경계는 application buffer에서 직접 찾아야 합니다.

또한 readable event는 정상 data뿐 아니라 EOF를 관찰할 수 있는 상황에서도 발생할 수 있습니다.

## 부분 읽기

non-blocking socket은 한 번의 `recv()`에서 현재 kernel buffer에 있는 일부 byte만 반환할 수 있습니다.

일반적인 처리 구조는 다음과 같습니다.

```cpp
for (;;) {
    ssize_t count =
        ::recv(fd, buffer, sizeof(buffer), 0);

    if (count > 0) {
        input.append(
            buffer,
            static_cast<std::size_t>(count));
    }
    else if (count == 0) {
        peer_read_closed = true;
        break;
    }
    else if (errno == EINTR) {
        continue;
    }
    else if (errno == EAGAIN
             || errno == EWOULDBLOCK) {
        break;
    }
    else {
        fail_connection();
        break;
    }
}
```

한 readable event에서 가능한 data를 `EAGAIN`까지 drain하는 방식은 특히 edge-triggered event backend를 사용할 때 중요합니다.

level-triggered backend에서도 여러 system call을 한 번의 event 처리에서 수행하면 불필요한 event loop 회전을 줄일 수 있습니다.

## `recv() > 0`

정상적으로 byte를 읽었습니다.

```cpp
count > 0
```

읽은 byte 수만큼 input buffer에 append합니다.

C 문자열이라고 가정하지 않습니다. `recv()`는 자동으로 `'\0'`을 붙여 주지 않으며, application protocol이 binary data를 포함할 수도 있습니다.

따라서 실제 길이 `count`를 사용합니다.

```cpp
input.append(
    buffer,
    static_cast<std::size_t>(count));
```

## `recv() == 0`

TCP stream에서 `recv()`가 `0`을 반환하면 peer가 자신의 **송신 방향을 정상적으로 종료**하여 더 이상 받을 byte가 없음을 의미합니다.

흔히 "peer가 연결을 닫았다"라고 표현하지만, TCP는 half-close가 가능하므로 다음을 구분하는 편이 정확합니다.

```text
recv() == 0
→ peer로부터 더 이상 data는 오지 않음
```

이 상태에서도 local side가 아직 보낼 data가 있고 protocol과 socket 상태가 허용한다면 송신을 시도할 수 있는 경우가 있습니다.

따라서 `recv() == 0`을 발견했다고 무조건 즉시 모든 pending output을 버릴지, 남은 응답을 보낸 뒤 닫을지는 protocol 정책에 따라 정합니다.

## `EAGAIN`과 `EWOULDBLOCK`

non-blocking socket에서 현재 더 읽을 data가 없으면:

```text
recv() == -1
errno == EAGAIN 또는 EWOULDBLOCK
```

이 될 수 있습니다.

이는 connection 실패가 아니라:

```text
현재 읽을 수 있는 만큼 모두 읽었다.
```

는 의미로 처리합니다.

event loop로 돌아가 다음 readable event를 기다립니다.

## `EINTR`

system call이 signal로 중단되면:

```text
errno == EINTR
```

이 될 수 있습니다.

현재 operation을 계속해도 된다면 다시 `recv()`합니다.

하지만 종료 signal 처리와 결합되어 있다면 종료 flag를 먼저 확인하고 loop를 빠져나갈 수도 있습니다.

`EINTR`을 모든 상황에서 무조건 영원히 재시도한다는 규칙으로 만들지 않습니다.

## input buffer 상한

client가 delimiter를 보내지 않고 계속 byte를 전송하면:

```text
input buffer
1 KB
10 KB
1 MB
100 MB
...
```

처럼 memory가 계속 증가할 수 있습니다.

따라서 protocol에 최대 frame 크기 또는 최대 pending input 크기를 둡니다.

예:

```text
MAX_FRAME_SIZE = 64 KiB
```

buffer가 상한을 넘으면:

- protocol error 응답 후 종료
- 즉시 connection 종료

등 정책을 정합니다.

이 제한은 단순 최적화가 아니라 memory resource 보호 규칙입니다.

## 한 번 읽은 뒤 여러 frame을 처리합니다

한 번의 `recv()`로 여러 요청이 들어올 수 있으므로 delimiter 하나만 처리하고 끝내면 input buffer에 이미 완성된 다음 요청이 남을 수 있습니다.

개념적으로:

```cpp
for (;;) {
    std::size_t pos = input.find('\n');

    if (pos == std::string::npos)
        break;

    std::string frame =
        input.substr(0, pos);

    input.erase(0, pos + 1);

    processFrame(frame);
}
```

실제 구현에서는 큰 문자열에서 앞부분을 반복 `erase()`하는 비용이 문제가 된다면 별도 offset이나 다른 buffer 구조를 사용할 수 있습니다.

핵심은 **현재 buffer에 완성된 frame이 여러 개 있으면 모두 처리할 수 있어야 한다**는 점입니다.

## frame 처리량 상한도 고려합니다

한 client가 한 번에 매우 많은 완성 frame을 보내면 event loop가 그 client의 요청만 오래 처리할 수도 있습니다.

공정성이 중요한 server라면 한 event에서 처리할 frame 수나 byte 수에 budget을 둘 수 있습니다.

예:

```text
한 connection당 한 loop iteration에서 최대 N개 frame 처리
```

그 뒤 남은 frame은 다음 loop에서 이어서 처리합니다.

이는 correctness보다 fairness와 latency 설계 문제입니다.

## 부분 쓰기

`send()`도 요청한 byte를 한 번에 모두 보내 준다고 보장하지 않습니다.

예:

```text
pending output: 1000 bytes
send() result : 320
```

이 경우 전송 완료 상태는:

```text
[0, 320)     전송 완료
[320, 1000)  아직 전송 필요
```

입니다.

따라서 연결마다 다음 상태를 보관합니다.

```text
output buffer
send offset
```

예:

```cpp
std::string output_;
std::size_t outputOffset_;
```

## 쓰기 가능한 만큼 반복합니다

개념적인 전송 loop:

```cpp
while (outputOffset_ < output_.size()) {
    const char *data =
        output_.data() + outputOffset_;

    const std::size_t remaining =
        output_.size() - outputOffset_;

    ssize_t count =
        ::send(fd, data, remaining, SEND_FLAGS);

    if (count > 0) {
        outputOffset_ +=
            static_cast<std::size_t>(count);
    }
    else if (count < 0 && errno == EINTR) {
        continue;
    }
    else if (count < 0
             && (errno == EAGAIN
                 || errno == EWOULDBLOCK)) {
        break;
    }
    else {
        fail_connection();
        break;
    }
}
```

실제 `SEND_FLAGS`는 플랫폼별 `SIGPIPE` 정책에 따라 달라질 수 있습니다.

## 모든 출력이 끝난 뒤 상태를 초기화합니다

```cpp
if (outputOffset_ == output_.size()) {
    output_.clear();
    outputOffset_ = 0;
}
```

그리고 writable interest를 제거합니다.

buffer 앞부분을 매번 `erase()`하는 대신 offset을 증가시키면 부분 전송마다 큰 문자열을 이동시키는 비용을 피할 수 있습니다.

필요하다면 전체 전송 완료 후 한 번에 buffer를 비웁니다.

## output queue가 여러 응답을 포함할 수 있습니다

한 요청의 응답을 아직 다 보내지 못한 상태에서 다음 요청의 응답이 생길 수 있습니다.

예:

```text
output buffer:
"OK\nVALUE 123\nERROR\n"
```

새 응답은 기존 pending data 뒤에 append해야 합니다.

아직 보내지 않은 byte를 덮어쓰면 안 됩니다.

따라서 output state는 "현재 응답 하나"가 아니라 **아직 peer에게 전달되지 않은 전체 pending byte sequence**라고 이해하는 편이 정확합니다.

## writable event의 의미

socket은 kernel send buffer에 여유가 있으면 대부분 writable 상태입니다.

따라서 모든 connection에 항상 writable interest를 등록하면 event loop가 계속 write-ready event를 받을 수 있습니다.

이 상태에서는 실제 보낼 data가 없어도 loop가 반복해서 깨어날 수 있습니다.

따라서 일반적인 정책은 다음과 같습니다.

```text
pending output 없음
→ readable만 감시

pending output 생김
→ readable + writable 감시

pending output 모두 전송
→ writable 감시 제거
```

## 종료 응답 중 interest

protocol에 "응답을 모두 보낸 뒤 connection을 닫는다"는 상태가 있을 수 있습니다.

예:

```text
QUIT 요청 수신
→ "BYE\n" output에 추가
→ 더 이상 새 요청은 읽지 않음
→ pending output만 전송
→ 모두 보낸 뒤 close
```

이 경우 상태는:

```text
readable interest 제거
writable interest 유지
```

가 될 수 있습니다.

즉, event interest는 단순 socket 속성이 아니라 connection의 현재 protocol 상태와 pending I/O 상태를 반영합니다.

## backpressure

server가 빠르게 응답을 만들더라도 client가 응답을 읽지 않으면 무한히 보낼 수 없습니다.

흐름은 다음과 같습니다.

```text
application이 output 생성
→ kernel send buffer로 send
→ client가 읽지 않음
→ kernel send buffer가 가득 참
→ send()가 EAGAIN
→ application output buffer에 pending data 누적
```

이 상태를 **backpressure** 관점에서 처리해야 합니다.

## output buffer 상한

연결별 pending output에 상한을 둡니다.

예:

```text
MAX_PENDING_OUTPUT = 1 MiB
```

상한을 넘으면 정책에 따라:

- 해당 client 종료
- 새 요청 읽기 일시 중지
- protocol별 overload 응답

등을 선택할 수 있습니다.

단순한 server라면 느린 client 하나를 닫는 방식이 전체 process memory를 보호하기 쉽습니다.

무제한 application output buffer는 한 client만으로도 server memory를 소진하게 만들 수 있습니다.

## 읽기까지 멈추는 backpressure

output이 계속 쌓이는데도 같은 client의 요청을 계속 읽고 처리하면 더 많은 응답이 생성될 수 있습니다.

따라서 일정 수준 이상 pending output이 쌓이면 해당 connection의 readable interest도 일시적으로 끌 수 있습니다.

예:

```text
pending output 작음
→ read + 필요 시 write

pending output high-water mark 초과
→ write만 감시

pending output low-water mark 아래로 감소
→ read 다시 활성화
```

이 방식은 입력 생산 속도를 출력 소비 속도에 맞추는 backpressure입니다.

단, protocol과 fairness 요구에 맞게 threshold를 정해야 합니다.

## `SIGPIPE`

peer가 더 이상 읽을 수 없는 socket에 `send()`하면 단순한 오류 반환뿐 아니라 `SIGPIPE`가 발생해 process가 종료될 수 있는 플랫폼이 있습니다.

server 전체가 한 client 때문에 종료되어서는 안 된다면 `SIGPIPE` 정책을 명확히 정합니다.

플랫폼에 따라 다음 방법이 있을 수 있습니다.

```text
Linux 계열 send의 MSG_NOSIGNAL
BSD/macOS 계열 socket option인 SO_NOSIGPIPE
process 수준 SIGPIPE 처리
```

이 기능들은 동일한 플랫폼 지원을 갖는 하나의 POSIX 공통 API라고 가정하면 안 됩니다.

portable layer에서 플랫폼별 차이를 감추는 편이 좋습니다.

signal을 무시하거나 차단하는 process-wide 정책은 다른 코드에도 영향을 줄 수 있으므로 범위를 확인합니다.

## `epoll`과 `kqueue`

event backend의 raw 표현을 application logic 전체에 퍼뜨리지 않는 편이 좋습니다.

상위 event loop가 이해하는 공통 event를 정의할 수 있습니다.

```text
readable
writable
hangup
error
```

platform adapter가 실제 backend event를 이 공통 의미로 변환합니다.

## Linux `epoll`

`epoll`에서는 하나의 event mask에 여러 bit가 함께 올 수 있습니다.

개념적으로:

```text
EPOLLIN
EPOLLOUT
EPOLLHUP
EPOLLERR
```

등이 한 fd의 같은 event에 동시에 포함될 수 있습니다.

따라서 다음처럼 단일 `else if` 체인으로 하나만 처리하면 필요한 상태를 놓칠 수 있습니다.

```cpp
if (readable) {
    // ...
}
else if (writable) {
    // ...
}
```

하나의 event에서 read와 write가 모두 가능한 경우가 있으므로 connection 상태를 고려해 각각 처리합니다.

## BSD 계열 `kqueue`

`kqueue`에서는 read와 write가 서로 다른 filter event로 전달될 수 있습니다.

같은 fd에 대해 한 wait 결과 안에 여러 event record가 올 수 있으므로 상위 loop가 "connection 하나의 현재 상태"로 처리하려면 fd별로 의미를 합치거나 순서 독립적인 처리 구조를 둘 수 있습니다.

즉:

```text
epoll
→ 한 event mask 안에 여러 상태

kqueue
→ 같은 fd의 여러 filter event가 따로 올 수 있음
```

이라는 표현 차이를 adapter가 흡수할 수 있습니다.

## backend adapter가 소유할 것

poller/event adapter는 최소한 다음 책임을 명확히 가질 수 있습니다.

```text
event queue fd
fd 등록/수정/삭제
platform event → 공통 event 변환
```

반면 connection의 protocol buffer와 application state까지 poller가 직접 소유하게 만들면 역할이 섞입니다.

예:

```text
Poller
→ 어떤 fd에 어떤 I/O interest가 있는가

Connection
→ input/output buffer와 protocol 상태

Server
→ Connection lifecycle과 전체 orchestration
```

처럼 나눌 수 있습니다.

## level-triggered와 edge-triggered

일부 event backend에서는 level-triggered와 edge-triggered 방식의 차이를 선택할 수 있습니다.

### level-triggered

조건이 계속 참이면 event가 다시 보고될 수 있습니다.

예:

```text
아직 읽을 data가 남아 있음
→ 다음 wait에서도 readable 가능
```

### edge-triggered

상태 변화의 경계를 중심으로 event가 보고되므로 event를 받았을 때 가능한 I/O를 `EAGAIN`까지 drain하지 않으면 남은 data가 있는데도 새 event가 기대대로 오지 않을 수 있습니다.

따라서 edge-triggered 방식을 사용한다면 다음 패턴이 특히 중요합니다.

```text
readable
→ recv를 EAGAIN까지 반복

writable
→ send를 EAGAIN 또는 output 완료까지 반복

listener readable
→ accept를 EAGAIN까지 반복
```

어떤 trigger mode를 쓰는지 adapter의 계약에 명확히 적습니다.

## hangup과 남은 data

hangup event를 받았다고 해서 아직 읽지 않은 data가 반드시 없다는 뜻은 아닙니다.

platform과 event backend의 의미에 따라:

```text
hangup + readable
```

상태가 함께 올 수 있습니다.

따라서 connection을 즉시 닫기 전에 아직 읽을 수 있는 data를 처리해야 하는지 backend 의미와 protocol 요구사항을 확인합니다.

일반적인 원칙은 "hangup bit 하나만 보고 읽을 data를 무조건 버리지 않는다"입니다.

## read EOF와 pending output

peer의 송신 방향이 끝났더라도 server 쪽에 이미 만들어 둔 output이 있을 수 있습니다.

예:

```text
요청 수신 완료
→ 응답 생성
→ peer가 write side 종료
→ server output 아직 pending
```

protocol상 응답을 보내야 한다면 가능한 범위에서 pending output 전송을 계속할 수 있습니다.

반대로 peer가 connection 전체를 더 이상 사용할 수 없는 상태라면 `send()`가 실패할 수 있습니다.

따라서 다음 상태를 별도로 추적할 수 있습니다.

```text
peer_read_closed
pending_output
close_after_flush
fatal_error
```

하나의 `closed` boolean만으로 모든 half-close와 pending output 상태를 표현하면 처리 순서가 모호해질 수 있습니다.

## 같은 event에서 오류와 read/write가 함께 올 수 있습니다

event backend는 하나의 fd에 대해 readable, writable, hangup, error를 동시에 보고할 수 있습니다.

따라서 event 처리 중 connection을 닫은 뒤 같은 event record의 다른 flag를 계속 처리하면 이미 닫힌 fd나 삭제된 객체를 사용할 수 있습니다.

예:

```text
read 처리 중 fatal error
→ connection 제거/close
→ 같은 event에서 write 처리 시도
```

를 피해야 합니다.

connection 처리 함수가:

```text
Alive
CloseNow
CloseAfterFlush
```

같은 결과를 반환하도록 만들거나, close 예정 상태를 표시한 뒤 event 처리 마지막에 실제 제거하는 방식으로 lifetime을 명확히 할 수 있습니다.

## fd 번호는 재사용될 수 있습니다

POSIX file descriptor는 작은 정수 번호이며 `close()`한 뒤 운영체제가 같은 번호를 다른 socket이나 file에 다시 사용할 수 있습니다.

예:

```text
client A fd = 7
close(7)

새 client B accept
→ fd = 7
```

따라서 오래된 event나 stale connection 상태가 단순히 "fd 숫자가 같다"는 이유로 새 connection에 적용되지 않게 해야 합니다.

특히 다음 문제가 위험합니다.

```text
이미 close한 fd를 실수로 다시 close
→ 그 사이 같은 번호가 새 자원에 재사용됨
→ 새 자원을 잘못 close할 가능성
```

따라서 fd 소유권을 한 객체에 모으고, close 후에는 내부 fd 값을 무효 상태로 바꾸는 습관이 도움이 됩니다.

예:

```cpp
if (fd_ != -1) {
    ::close(fd_);
    fd_ = -1;
}
```

## poller 등록 상태와 fd 소유권은 다릅니다

다음 두 상태를 구분합니다.

```text
fd를 누가 close할 책임이 있는가
poller에 현재 등록되어 있는가
```

예를 들어 Connection이 fd를 소유하고 Poller는 등록 정보만 관리할 수 있습니다.

connection 제거 시:

```text
poller에서 등록 제거
→ Connection 제거
→ Connection 소멸자에서 close
```

같은 순서를 사용할 수 있습니다.

다른 구조도 가능하지만, "poller에서 제거했다"와 "fd를 닫았다"를 같은 동작으로 암묵적으로 취급하지 않습니다.

## `close()` 오류와 ownership

`close(fd)`를 호출한 뒤 반환값이 오류라고 해서 같은 fd에 무조건 다시 `close()`하면 안 됩니다.

file descriptor 번호는 이미 재사용 가능 상태가 되었을 수 있으므로 retry가 다른 자원을 닫는 위험을 만들 수 있습니다.

따라서 close 정책은 사용하는 platform의 semantics를 확인하고, 소유 객체 내부에서는 한 번 close를 시도한 뒤 fd를 더 이상 소유하지 않는 상태로 전환하는 방식이 일반적으로 안전합니다.

핵심은 "close 실패를 보았으니 같은 정수 번호를 반복 close한다"는 단순 규칙을 만들지 않는 것입니다.

## server 종료 순서

server 종료는 signal handler 안에서 모든 작업을 직접 수행하기보다 일반 event loop 흐름으로 넘깁니다.

개념적인 순서:

```text
signal 수신
→ 종료 flag 설정
→ event wait가 깨어남
→ 새 accept 중단
→ 기존 connection 처리 정책 결정
→ client event 등록 제거
→ client fd close
→ listener 등록 제거
→ listener close
→ poller close
```

"기존 connection을 즉시 끊을지", "pending output을 일정 시간 flush할지"는 server 요구사항에 따라 정합니다.

## signal handler에서는 최소 작업만 합니다

signal handler에서는 일반 C++ library나 임의의 객체 메서드를 안전하게 호출할 수 있다고 가정하면 안 됩니다.

보통 signal handler에서는 async-signal-safe한 작업만 수행합니다.

간단한 종료 flag라면 `volatile sig_atomic_t`를 사용할 수 있습니다.

```cpp
volatile sig_atomic_t g_stop = 0;

extern "C" void handleSignal(int)
{
    g_stop = 1;
}
```

event loop의 일반 제어 흐름에서 이 flag를 확인하고 실제 cleanup을 수행합니다.

전역 flag 사용 자체가 이상적인 구조라는 뜻은 아니며, signal handler와 일반 실행 흐름 사이에서 안전하게 전달할 수 있는 최소 상태의 예입니다.

## event wait를 실제로 깨우는 방법

종료 flag만 설정해도 event wait가 signal에 의해 `EINTR`로 깨어나는 환경이 있을 수 있습니다.

하지만 signal 설치 방식이나 system call 재시작 정책에 따라 wait가 자동으로 다시 시작될 수 있으므로 "flag만 설정하면 항상 즉시 깨어난다"고 가정하지 않습니다.

필요하다면 self-pipe 같은 wakeup fd를 poller에 등록해 signal handler에서 async-signal-safe한 `write()`로 event loop를 깨우는 방식을 사용할 수 있습니다.

개념:

```text
signal handler
→ stop flag 설정
→ wakeup pipe에 1 byte write

event loop
→ wakeup fd readable
→ stop flag 확인
→ 정상 cleanup 흐름 실행
```

플랫폼별 eventfd나 다른 wakeup primitive를 사용할 수도 있지만 portability 범위를 별도로 정합니다.

## Connection이 fd를 소유하게 합니다

client socket 수명을 명확히 하려면 Connection 객체가 fd를 소유하도록 만들 수 있습니다.

개념적인 C++98 클래스:

```cpp
class Connection {
public:
    explicit Connection(int fd)
        : fd_(fd)
    {
    }

    ~Connection()
    {
        if (fd_ != -1)
            ::close(fd_);
    }

private:
    Connection(const Connection &);
    Connection &operator=(const Connection &);

private:
    int fd_;
};
```

복사를 막는 이유는 compiler 기본 복사가 fd 정수 값만 복제하기 때문입니다.

두 객체가 같은 fd를 모두 소유한다고 생각하면 두 번 close할 수 있습니다.

C++98에서는 `= delete` 대신 복사 생성자와 대입 연산자를 private으로 선언하고 정의하지 않는 방식을 사용할 수 있습니다.

## 하나의 connection을 닫는 경로를 통합합니다

다음과 같은 여러 경로에서 connection 종료가 발생할 수 있습니다.

```text
recv EOF
recv fatal error
send fatal error
protocol error
input 상한 초과
output 상한 초과
server shutdown
```

각 위치에서 직접:

```text
poller.remove
close
map.erase
```

를 제각각 수행하면 일부 경로에서 두 번 close하거나 poller 등록이 남기 쉽습니다.

가능하면 하나의 제거 함수로 모읍니다.

```text
closeConnection(fd)
→ poller 등록 제거
→ connection container에서 제거
→ 소유 객체 소멸로 fd close
```

그리고 이미 제거된 connection에 다시 같은 cleanup을 적용하지 않게 상태를 관리합니다.

## 테스트: TCP framing

TCP packet 경계를 가정하지 않는지 확인하려면 의도적으로 요청을 나눠 보냅니다.

예:

```text
send("HE")
send("LL")
send("O\n")
```

server는 최종적으로 정확히 하나의 `"HELLO"` frame으로 처리해야 합니다.

반대로 여러 frame을 한 번에 보냅니다.

```text
send("one\ntwo\nthree\n")
```

server는 세 요청을 모두 처리해야 합니다.

## 테스트: 여러 client

여러 client를 동시에 연결합니다.

확인할 내용:

```text
한 client가 입력을 천천히 보내도 다른 client 요청이 처리되는가
한 client의 output이 막혀도 다른 client 응답이 나가는가
connection별 input/output buffer가 섞이지 않는가
```

한 thread event loop의 목적은 특정 client의 blocking I/O가 전체 server를 멈추지 않게 하는 것입니다.

## 테스트: backpressure

한 client는 응답을 읽지 않게 합니다.

server에 충분한 요청을 보내 pending output 상한까지 증가시킵니다.

확인:

```text
해당 connection에 제한 정책이 적용되는가
server 전체 memory가 계속 증가하지 않는가
다른 client는 계속 처리되는가
```

## 테스트: fd leak

연결과 종료를 반복합니다.

예:

```text
connect
request
close

위 과정을 수천 번 반복
```

server process의 열린 fd 수가 계속 증가하지 않는지 확인합니다.

다음 경로도 별도로 테스트합니다.

```text
accept 직후 설정 실패
protocol error
peer EOF
send error
server shutdown
```

정상 경로만 검사하면 오류 경로의 fd leak을 놓치기 쉽습니다.

## 테스트: fd 재사용

가능하면 connection을 빠르게 열고 닫아 운영체제가 같은 fd 번호를 재사용하게 만듭니다.

이때 stale event나 중복 cleanup이 새 connection을 잘못 닫지 않는지 확인합니다.

fd 번호가 재사용된다는 사실을 고려하지 않은 lifecycle bug를 찾는 데 도움이 됩니다.

## 테스트: 종료

`SIGTERM` 같은 종료 signal을 보낸 뒤 server가 요구된 시간 안에 종료하는지 확인합니다.

검사 항목:

```text
새 connection accept가 중단되는가
client fd가 남지 않는가
listener가 닫히는가
event backend fd가 닫히는가
event wait가 실제로 깨어나는가
```

graceful shutdown 정책이 있다면 pending output 처리 시간도 테스트합니다.

## 자주 놓치는 문제

- 한 번의 `send()`와 한 번의 `recv()`가 같은 message 경계를 가진다고 생각합니다.
- delimiter가 아직 없다는 이유만으로 부분 입력을 오류 처리합니다.
- input buffer 크기 상한을 두지 않습니다.
- 한 번의 `recv()`에 여러 frame이 들어왔는데 첫 frame만 처리합니다.
- listener를 non-blocking으로 만들었으니 accepted fd도 자동으로 같은 설정이라고 가정합니다.
- `FD_CLOEXEC`를 `F_GETFL`/`F_SETFL`로 설정하려고 합니다.
- listener readable event에서 `accept()`를 한 번만 호출합니다.
- `EAGAIN`/`EWOULDBLOCK`을 connection 오류로 처리합니다.
- 종료 flag가 설정된 뒤에도 `EINTR`을 무조건 재시도합니다.
- 새 connection 등록 단계 중 하나가 실패했을 때 poller 등록이나 fd를 남깁니다.
- readable event가 요청 하나 전체가 도착했다는 뜻이라고 생각합니다.
- `recv() == 0`을 TCP half-close 가능성과 구분하지 않습니다.
- `recv()` buffer를 자동으로 null-terminated 문자열이라고 생각합니다.
- `send()`가 요청한 byte 전체를 항상 전송한다고 생각합니다.
- 부분 전송 뒤 output의 처음부터 다시 보냅니다.
- pending output이 없는데도 모든 socket의 writable event를 계속 감시합니다.
- 느린 client에 output 상한을 두지 않습니다.
- output이 계속 쌓이는데도 요청을 무제한으로 계속 읽습니다.
- `MSG_NOSIGNAL`이 모든 POSIX 플랫폼에 동일하게 있다고 가정합니다.
- `epoll` event에서 read/write/hangup 중 하나만 `else if`로 처리합니다.
- edge-triggered mode에서 `EAGAIN`까지 I/O를 drain하지 않습니다.
- hangup event가 왔다는 이유만으로 남은 readable data를 버립니다.
- event 처리 중 connection을 삭제한 뒤 같은 event의 다른 flag에서 다시 접근합니다.
- close한 fd 번호가 다시 사용되지 않을 것이라고 생각합니다.
- poller 등록 제거와 fd close를 같은 상태라고 생각합니다.
- `close()` 오류가 나면 같은 fd를 무조건 반복해서 close합니다.
- signal handler에서 container 정리, logging, memory allocation 같은 복잡한 작업을 직접 수행합니다.
- 종료 flag만 설정하면 event wait가 모든 환경에서 즉시 깨어난다고 가정합니다.
- raw fd를 가진 Connection의 compiler 기본 복사를 허용합니다.
- 여러 오류 경로가 각각 직접 close를 수행해 이중 close 가능성을 만듭니다.

## 완료 기준

다음 항목을 설명하고 코드에서 적용할 수 있으면 이 범위의 목표를 달성한 것입니다.

- TCP byte stream과 application message framing을 구분합니다.
- connection별 input buffer에 부분 요청을 보관하고 완성된 frame만 처리합니다.
- 한 번의 read에 여러 frame이 들어올 수 있음을 처리합니다.
- listener와 accepted client socket의 flag 설정을 각각 관리합니다.
- `O_NONBLOCK`과 `FD_CLOEXEC`가 서로 다른 종류의 flag임을 설명합니다.
- listener readable event에서 `accept()`를 `EAGAIN`까지 반복합니다.
- `EINTR`, `EAGAIN`/`EWOULDBLOCK`, EOF와 일반 오류를 서로 다르게 처리합니다.
- `recv() == 0`이 peer 송신 방향의 EOF를 의미함을 설명합니다.
- `recv()`가 반환한 실제 byte 수를 사용하고 null termination을 가정하지 않습니다.
- 연결별 output buffer와 전송 offset을 보관해 부분 쓰기를 이어서 처리합니다.
- pending output이 있을 때만 writable interest를 활성화합니다.
- 느린 client에 input/output 상한과 필요한 backpressure 정책을 적용합니다.
- `SIGPIPE` 회피가 플랫폼별로 다를 수 있음을 구분합니다.
- `epoll`과 `kqueue`의 raw event 차이를 adapter에서 공통 의미로 변환합니다.
- edge-triggered 방식을 사용할 때 accept/read/write를 `EAGAIN`까지 drain합니다.
- hangup, EOF와 pending output의 관계를 protocol 정책에 맞게 처리합니다.
- event 처리 중 connection 삭제 뒤 stale object나 fd에 다시 접근하지 않습니다.
- fd 번호가 close 뒤 재사용될 수 있음을 고려해 이중 close를 방지합니다.
- poller 등록 상태와 fd ownership을 별도로 추적합니다.
- signal handler에서는 최소한의 async-signal-safe 작업만 수행하고 실제 cleanup은 일반 제어 흐름에서 실행합니다.
- 필요하면 wakeup fd로 blocking event wait를 명시적으로 깨웁니다.
- 모든 accept·read·write·error·shutdown 경로에서 client fd를 정확히 한 번만 닫습니다.
- framing, backpressure, fd leak, fd 재사용과 signal 종료를 실패 테스트로 검증합니다.
