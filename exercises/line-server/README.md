# Line Server

## 개요

`line_server`는 여러 TCP 연결을 **하나의 non-blocking event loop**에서 처리하는 C++98 서버입니다.

platform별 readiness API는 다음을 사용합니다.

```text
Linux
→ epoll

macOS / BSD 계열
→ kqueue
```

핵심 학습 목표는 socket API 호출 자체보다 다음 상태를 연결별로 정확히 관리하는 것입니다.

```text
입력 바이트 누적
출력 바이트 누적
partial read/write
readiness 등록
연결 종료
fd 소유권
```

TCP는 **메시지 단위가 아니라 바이트 스트림**을 전달합니다.

따라서 한 번의 `recv()`가 한 줄과 정확히 일치한다고 가정하면 안 됩니다.

예를 들어 client가:

```text
hello\nworld\n
```

를 한 번에 보냈더라도 server는 다음처럼 받을 수 있습니다.

```text
recv #1: "hel"
recv #2: "lo\nwor"
recv #3: "ld\n"
```

반대로 두 줄 이상이 한 번의 `recv()`에 함께 들어올 수도 있습니다.

따라서 각 연결은 자체 입력 버퍼를 유지하고 **완전한 줄이 생길 때만 protocol 처리를 수행**합니다.

출력도 마찬가지로 한 번의 `send()`가 전체 응답을 모두 전송한다고 가정하지 않습니다.

각 연결은 출력 buffer와 현재 전송 위치를 별도로 보관해야 합니다.

## 프로토콜

### 일반 줄

`COUNT`와 `QUIT`이 아닌 일반 줄을 받으면:

```text
ECHO <line>
```

을 반환하고 해당 연결에서 처리한 일반 줄 수를 1 증가시킵니다.

예:

```text
hello
```

응답:

```text
ECHO hello
```

### `COUNT`

현재 연결에서 지금까지 받은 일반 줄 수를 반환합니다.

```text
COUNT <n>
```

예:

```text
hello
world
COUNT
```

응답:

```text
ECHO hello
ECHO world
COUNT 2
```

count는 server 전체가 아니라 **각 연결별 상태**입니다.

### `QUIT`

다음을 출력 buffer에 넣습니다.

```text
BYE
```

그리고 이 문자열이 **실제로 전부 전송된 뒤** 연결을 닫습니다.

즉 `QUIT`을 읽은 즉시 `close(fd)`하면 안 됩니다.

잘못된 순서:

```text
QUIT 수신
→ close(fd)
→ BYE 전송 시도
```

올바른 순서:

```text
QUIT 수신
→ BYE enqueue
→ 남은 출력 전송
→ BYE 전체 전송 확인
→ fd close
```

## 입력 제한

한 줄은 최대 `8192`바이트입니다.

이 제한은 newline을 기다리며 한 연결의 입력 buffer가 무한히 커지는 것을 막기 위한 것입니다.

완전한 줄이 아직 만들어지지 않았는데 허용 크기를 초과하면 해당 연결을 종료할 수 있습니다.

정확한 판정 시점은 구현에서 일관되게 정의해야 합니다.

핵심 invariant는 다음과 같습니다.

```text
한 연결의 미완성 line이 설정된 최대 크기를 무제한 초과하지 않음
```

## 출력 제한

한 연결이 아직 전송하지 못한 output은 최대 `65536`바이트입니다.

이 제한은 느리게 읽는 client 하나가 server memory를 계속 소비하는 것을 막기 위한 backpressure 정책입니다.

```text
출력 대기량 <= 65536
```

새 응답을 추가하면 제한을 초과하는 경우 해당 연결만 닫습니다.

다른 client는 계속 처리합니다.

즉 하나의 느린 client 때문에 event loop 전체를 종료하거나 blocking해서는 안 됩니다.

## non-blocking I/O

socket을 non-blocking mode로 사용하면 `recv()`와 `send()`가 즉시 완료되지 않을 수 있습니다.

예를 들어:

```text
현재 읽을 데이터 없음
→ recv()가 would-block 상태 반환

현재 kernel send buffer에 공간 부족
→ send()가 would-block 상태 반환
```

이 상태는 치명적 오류가 아닙니다.

event loop는 해당 operation을 나중 readiness event에서 다시 시도해야 합니다.

## partial read

다음 한 줄을 client가 보냈다고 가정합니다.

```text
hello world\n
```

server가 받을 수 있는 형태:

```text
recv #1 → "hello "
recv #2 → "wor"
recv #3 → "ld\n"
```

따라서 첫 `recv()` 뒤 즉시 응답하면 안 됩니다.

연결별 입력 buffer는 다음처럼 동작합니다.

```text
bytes 수신
→ input buffer 뒤에 append
→ newline 검색
→ 완전한 줄이 있으면 하나씩 처리
→ 남은 미완성 bytes 유지
```

한 `recv()` 안에 여러 줄이 들어온 경우도 모두 처리해야 합니다.

예:

```text
recv() → "a\nb\nc\n"
```

처리:

```text
a
b
c
```

세 줄 모두 protocol handler로 전달되어야 합니다.

## partial write

`send()`의 반환값이 요청한 byte 수보다 작을 수 있습니다.

예:

```text
전송 예정:
"abcdefghijklmnopqrstuvwxyz"

send() 반환:
8
```

그러면 첫 8바이트만 전송된 것입니다.

연결은 다음 정보를 유지해야 합니다.

```text
전체 output buffer
현재까지 전송한 offset
```

다음 writable event에서:

```text
buffer + offset
```

부터 이어서 전송해야 합니다.

partial write 뒤 offset을 잃으면 다음 문제가 생깁니다.

```text
처음부터 다시 전송
→ 중복 출력

또는

남은 데이터를 버림
→ 잘린 출력
```

## writable event 등록

non-blocking socket은 대부분의 시간에 writable일 수 있습니다.

출력할 데이터가 없는데도 항상 writable event를 감시하면 event loop가 계속 깨어나는 busy loop를 만들 수 있습니다.

따라서 일반적으로:

```text
output 없음
→ writable 관심 해제

output 생김
→ writable 관심 등록

output 모두 전송
→ writable 관심 다시 해제
```

로 관리합니다.

## 빌드와 실행

```sh
make
./line_server 8080
```

port에 `0`을 전달하면 운영체제가 사용 가능한 임시 port를 선택합니다.

server는 bind/listen 이후 실제 port를 다음 형식으로 출력합니다.

```text
PORT 43127
```

테스트는 이 값을 읽어 실제 연결 port를 알아낼 수 있습니다.

## 파일별 역할

### `Poller.hpp`

server core가 사용할 공통 readiness 의미를 정의합니다.

예:

```text
readable
writable
hangup
error
```

server core는 가능하면 `EPOLLIN`, `EVFILT_READ` 같은 platform-specific flag를 직접 알지 않습니다.

### `Poller_epoll.cpp`

Linux `epoll` fd를 소유하고 `epoll_event`를 공통 `PollEvent`로 변환합니다.

### `Poller_kqueue.cpp`

macOS/BSD `kqueue` filter 등록 상태를 추적하고, 같은 fd에서 발생한 read/write event를 server가 소비할 공통 event로 합칩니다.

### `main.cpp`

다음 핵심 상태를 관리합니다.

```text
listener
client connection map
accept loop
input buffering
output buffering
event dispatch
signal 기반 종료
fd cleanup
```

### `test_server.py`

실제 TCP connection을 사용하여 다음을 검증합니다.

```text
분할 입력
여러 줄 동시 입력
partial write
backpressure
동시 접속
fd cleanup
signal shutdown
```

## `Connection`과 fd 소유권

`Connection`이 client fd의 유일한 owner입니다.

```text
Connection 생성
→ fd ownership 획득

Connection 소멸
→ fd close
```

같은 fd를 여러 객체가 owner처럼 다루면 double close 위험이 있습니다.

특히 fd는 정수이므로 double close가 단순한 "같은 번호를 두 번 닫음"으로 끝나지 않을 수 있습니다.

예:

```text
fd 7 close
→ OS가 번호 7을 새 파일에 재사용
→ 오래된 코드가 다시 close(7)
→ 새 파일까지 잘못 닫힘
```

따라서 fd ownership은 하나의 객체에 고정하는 것이 중요합니다.

## 새 client 등록과 ownership 이전

accept된 socket을 바로 connection map에 넣는 것보다, 필요한 초기화가 모두 성공한 뒤 ownership을 넘기는 편이 안전합니다.

권장 순서:

```text
accept
→ non-blocking 설정
→ close-on-exec 설정
→ Connection 준비
→ poller 등록
→ map 삽입
→ 최종 ownership 확정
```

중간 실패 예:

```text
poller 등록 성공
→ map 삽입 실패
```

이 경우 poller 등록을 취소하고 fd를 닫아야 합니다.

즉 생성 중 rollback 순서는 획득의 역순으로 구성합니다.

```text
map insert 실패
→ poller deregister
→ fd close
```

## event 처리 중 container 변경

connection을 map에 저장하면서 event loop에서 iterator로 순회한다면, callback 처리 중 해당 연결을 삭제하는 경우 iterator 사용 방식에 주의해야 합니다.

일반적인 안전 패턴은 삭제 대상 fd를 먼저 기록하고, 현재 iterator를 더 이상 사용하지 않는 시점에 erase하는 것입니다.

핵심은 다음입니다.

```text
erase한 원소의 iterator/reference를 이후에 사용하지 않음
```

## connection 종료 조건

연결은 여러 이유로 끝날 수 있습니다.

예:

```text
peer EOF
protocol limit 위반
output limit 초과
fatal recv/send error
QUIT 응답 전송 완료
server shutdown
```

어느 경로로 종료되더라도 client fd는 정확히 한 번 닫아야 합니다.

cleanup logic을 한 함수나 `Connection` destructor에 모으면 종료 경로마다 `close()`를 중복 작성하는 실수를 줄일 수 있습니다.

## signal 종료

`SIGTERM` 같은 종료 요청을 받으면 event loop가 종료 절차를 시작합니다.

중요한 정리 순서는 다음과 같습니다.

```text
새 작업/연결 수락 중단
→ event loop 종료
→ client connection 정리
→ listener 정리
→ poller 정리
→ process 종료
```

signal handler 안에서 복잡한 C++ 작업을 직접 수행하지 않는 것이 중요합니다.

보통 signal handler는 최소한의 종료 flag만 변경하고, 실제 cleanup은 정상 control flow의 event loop가 수행하도록 만듭니다.

## 테스트

```sh
make test
```

세부 검사:

```sh
make stress
make backpressure
make leak-check
```

테스트는 다음 잘못된 구현을 검출해야 합니다.

- 줄이 여러 `recv()`로 나뉘었는데 newline 전에 응답함
- 한 `recv()`에 여러 줄이 들어왔는데 첫 줄만 처리함
- 일부만 전송한 뒤 남은 출력 offset을 잃음
- 느린 client 하나 때문에 event loop 전체가 멈춤
- writable event를 항상 등록해 busy loop 발생
- 연결 종료 경로에서 client fd를 닫지 않음
- `SIGTERM` 뒤 listener/client fd가 남음

`leak-check`는 Linux의 `/proc/<pid>/fd`가 없으면 실행할 수 없습니다.

이 경우 성공으로 처리하는 대신:

```text
SKIP - /proc/<pid>/fd unavailable
```

처럼 이유를 남깁니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Portable readiness event | `include/Poller.hpp` |
| 2 | Poller creation for the current operating system | `include/Poller.hpp` |
| 2-1 | Translate epoll flags and own the epoll descriptor | `src/Poller_epoll.cpp` |
| 2-2 | Track kqueue filters and merge events by descriptor | `src/Poller_kqueue.cpp` |
| 3 | Create non-blocking close-on-exec sockets | `src/main.cpp` |
| 4 | Own one client descriptor and its buffered state | `src/main.cpp` |
| 5 | Accumulate bytes until a complete line is available | `src/main.cpp` |
| 6 | Resume partial writes and enforce the output limit | `src/main.cpp` |
| 7 | Register an accepted client before transferring ownership | `src/main.cpp` |
| 8 | Dispatch readiness events and close every descriptor once | `src/main.cpp` |

이 순서는 platform abstraction을 먼저 만들고, 그 위에 fd ownership과 stream parsing을 쌓도록 구성되어 있습니다.

## 범위

이 프로젝트는 다음 범위로 제한합니다.

```text
process: 1개
event-loop thread: 1개
transport: TCP
protocol: line based
TLS: 없음
authentication: 없음
persistent storage: 없음
idle timeout: 없음
IPv6: 없음
multi-process load balancing: 없음
```

`kqueue` 구현은 macOS 또는 BSD 환경에서 별도로 build/test해야 합니다.