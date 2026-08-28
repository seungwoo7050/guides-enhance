# Line Server

## 개요

`line_server`는 여러 TCP 연결을 하나의 non-blocking event loop에서 처리하는 C++98 서버입니다. Linux에서는 `epoll`, macOS와 BSD 계열에서는 `kqueue`를 사용합니다.

TCP는 메시지가 아니라 바이트 스트림을 전달하므로, 한 번의 `recv()` 결과가 한 줄과 일치한다고 가정하지 않습니다. 각 연결이 입력 버퍼, 출력 버퍼와 현재 전송 위치를 따로 보관합니다.

## 프로토콜

- 일반 줄: `ECHO <line>`을 반환하고 해당 연결의 줄 수를 증가시킵니다.
- `COUNT`: 지금까지 받은 일반 줄 수를 `COUNT <n>`으로 반환합니다.
- `QUIT`: `BYE`를 모두 보낸 뒤 연결을 닫습니다.

한 줄은 최대 8192바이트이며, 한 연결이 아직 보내지 못한 출력은 최대 65536바이트입니다. 출력 제한을 넘긴 연결만 닫고 다른 연결은 계속 처리합니다.

## 빌드와 실행

```sh
make
./line_server 8080
```

포트에 `0`을 전달하면 운영체제가 빈 포트를 선택합니다. 서버는 시작 직후 실제 포트를 다음 형식으로 출력합니다.

```text
PORT 43127
```

## 테스트

```sh
make test
```

세부 검사는 따로 실행할 수도 있습니다.

```sh
make stress
make backpressure
make leak-check
```

테스트는 다음 문제를 검출합니다.

- 줄이 여러 `recv()`로 나뉘었는데 줄바꿈 전에 응답하는 구현
- 한 `recv()`에 여러 줄이 들어왔을 때 첫 줄만 처리하는 구현
- 일부만 전송한 뒤 남은 출력 위치를 잃는 구현
- 느린 client 하나 때문에 event loop 전체가 멈추는 구현
- 연결 종료 경로에서 client fd를 닫지 않는 구현
- `SIGTERM` 뒤 listener나 client fd가 남는 구현

`leak-check`는 Linux의 `/proc/<pid>/fd`가 없으면 건너뜁니다.

## 파일별 역할

- `Poller.hpp`: 서버가 사용할 readiness 값을 정의합니다.
- `Poller_epoll.cpp`: epoll fd를 소유하고 epoll event를 `PollEvent`로 바꿉니다.
- `Poller_kqueue.cpp`: 등록한 filter를 추적하고 같은 fd의 read/write event를 합칩니다.
- `main.cpp`: listener 생성, 연결별 버퍼, accept, event 처리와 종료를 담당합니다.
- `test_server.py`: 실제 TCP 연결로 분할 입력, 동시 접속, backpressure와 fd 정리를 확인합니다.

## 주요 구현 선택

`Connection`이 client fd의 유일한 소유자입니다. 객체가 삭제되면 소멸자가 fd를 닫습니다. 출력할 데이터가 있을 때만 writable event를 등록해, 항상 writable인 socket 때문에 loop가 불필요하게 반복되는 일을 막습니다.

새 client는 socket flag 설정, poller 등록, map 삽입이 모두 성공한 뒤에만 map으로 소유권을 넘깁니다. 중간에 실패하면 등록한 event와 fd를 역순으로 정리합니다.

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

## 범위

단일 프로세스와 단일 event-loop thread만 사용합니다. TLS, 인증, 데이터 저장, 유휴 연결 timeout, IPv6, 여러 프로세스로의 부하 분산은 구현하지 않습니다. `kqueue` 코드는 macOS 또는 BSD 환경에서 별도로 빌드해야 합니다.
