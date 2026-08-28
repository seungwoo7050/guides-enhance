# C++98 객체지향 HTTP server

## 사용 시점

HTTP/1.x 요청 parsing, route 선택, keep-alive 또는 CGI process 실행이 실제 요구사항일 때 참고합니다. socket event loop를 처음 배우기 위한 선행 문서는 아닙니다. 먼저 [`POSIX socket과 event loop`](08-posix-sockets-and-event-loop.md)의 부분 입출력과 연결 수명을 이해해야 합니다.

## HTTP 요청도 여러 조각으로 도착합니다

```text
request line
headers
empty line
body bytes
```

한 번의 `recv()`에 전체 요청이 있다고 가정하지 않습니다. parser는 내부 buffer를 보관하고 다음 세 결과를 반환할 수 있습니다.

```text
NeedMore
Complete
Error
```

`Complete` 뒤에도 buffer에 다음 요청이 남을 수 있습니다. keep-alive connection의 pipelining을 지원한다면 첫 요청을 꺼낸 뒤 남은 bytes를 다시 parsing합니다.

## 요청 모델

```cpp
struct HttpRequest {
    std::string method;
    std::string target;
    std::string version;
    std::map<std::string, std::string> headers;
    std::string body;
};
```

외부 문자열을 이 값으로 만들기 전에 다음을 검사합니다.

- 요청 줄에 정확히 method, target, version이 있는가
- 지원하는 HTTP version인가
- target이 허용한 형식인가
- header name과 value가 유효한가
- 같은 header를 어떻게 처리할 것인가
- HTTP/1.1에 `Host`가 있는가
- `Content-Length`가 숫자이며 body 상한 안인가
- 지원하지 않는 `Transfer-Encoding`을 명시적으로 거부하는가

오류가 난 요청을 부분적으로 `HttpRequest`에 반영하지 않습니다. 지역 candidate를 완성한 뒤 ready 상태로 옮깁니다.

## 입력 상한

다음 상한을 정합니다.

- 요청 header 전체 크기
- header 개수
- body 크기
- connection별 pending output
- 한 연결에 허용할 pipeline 요청 수

상한이 없으면 느린 client나 악성 입력이 메모리를 계속 사용하게 됩니다. 제한을 넘긴 요청은 명확한 HTTP status와 연결 종료 방식으로 처리합니다.

## route 설정

route 설정을 읽을 때 파일 전체를 검증한 뒤 Router를 만듭니다.

```text
route GET /health health;
route POST /echo echo;
route POST /cgi cgi;
```

- 지원 method인지 확인합니다.
- path가 `/`로 시작하는지 확인합니다.
- handler 이름이 등록된 값인지 확인합니다.
- 같은 method/path가 중복되지 않는지 확인합니다.

Router는 문자열 key를 handler 이름으로 바꾸기만 하고 실제 HTTP 응답 생성까지 맡지 않습니다.

## Connection이 보유하는 상태

연결마다 다음 값이 필요합니다.

```text
socket fd
HttpParser
pending output
write offset
close-after-write 여부
shared Router 참조
CGI 설정
```

`Connection`이 fd를 소유하면 소멸 시 close합니다. Router와 설정은 server가 더 오래 보유하고 Connection은 참조합니다.

## keep-alive

HTTP/1.1은 기본 keep-alive이며 `Connection: close`에서 닫습니다. HTTP/1.0은 반대로 명시적인 keep-alive가 필요합니다.

응답 header에 실제 선택을 기록합니다. 닫을 연결도 pending response를 모두 보낸 뒤 fd를 닫아야 합니다.

## 응답 만들기

```text
HTTP/1.1 <status> <reason>\r\n
Content-Length: <bytes>\r\n
Content-Type: text/plain\r\n
Connection: keep-alive|close\r\n
\r\n
<body>
```

body byte 수를 기준으로 `Content-Length`를 계산합니다. 문자열 문자 수와 전송 byte 수가 다를 수 있는 encoding은 별도 정책이 필요합니다.

## CGI process

CGI를 실행하면 socket 외에 child process와 pipe 수명을 관리해야 합니다.

```text
stdin pipe 생성
stdout pipe 생성
fork
child: dup2 → 불필요한 fd close → execve
parent: child 쪽 fd close → non-blocking read/write
```

parent는 다음 상태를 함께 처리합니다.

- request body 일부 쓰기
- CGI output 일부 읽기
- child 종료 여부
- timeout
- output 크기 제한
- exec 실패와 비정상 종료
- 모든 pipe close와 `waitpid`

child와 그 자식까지 timeout으로 종료해야 한다면 process group을 만듭니다. kill 뒤에는 반드시 `waitpid()`로 zombie를 회수합니다.

## CGI 결과를 HTTP로 바꿉니다

- 정상 output: CGI header와 body를 parsing합니다.
- timeout: `504 Gateway Timeout`
- 실행 실패·비정상 종료·잘못된 output: `502 Bad Gateway`
- output 제한 초과: `502`

CGI의 임의 문자열을 HTTP status line에 그대로 넣지 않습니다. `Status` header를 숫자 범위와 형식까지 확인합니다.

## event loop와 blocking CGI

socket은 non-blocking이어도 CGI 한 건을 동기적으로 끝까지 처리하면 같은 event loop의 다른 연결이 기다립니다. 작은 구현에서는 의도적인 제한으로 둘 수 있지만 README에 명시합니다.

동시 CGI가 필요하면 child pipe와 deadline도 주 event loop에 넣고 요청별 상태를 관리해야 합니다. 단순히 thread를 추가하면 shutdown, output 상한, process 회수 규칙을 다시 설계해야 합니다.

## 테스트

- 요청 줄과 header를 여러 조각으로 보냅니다.
- 두 요청을 한 번에 pipelining합니다.
- keep-alive와 close 동작을 확인합니다.
- 잘못된 version, header, `Content-Length`를 보냅니다.
- 느린 CGI, 큰 output, 없는 실행 파일을 사용합니다.
- 실패한 요청 뒤 server가 다음 연결을 처리하는지 확인합니다.
- 종료 뒤 child process와 fd가 남지 않는지 확인합니다.

## 완료 기준

- incremental parser가 입력 조각과 pipeline bytes를 보존합니다.
- 요청 상한과 header 규칙을 상태 변경 전에 검사합니다.
- Router는 설정 전체가 유효할 때만 만들어집니다.
- Connection이 socket, parser와 pending output을 함께 정리합니다.
- keep-alive와 close-after-write를 구분합니다.
- CGI timeout·output limit·exec 실패에서 pipe와 child를 회수합니다.
- blocking CGI가 가진 동시성 한계를 문서화합니다.
