# C++98 객체지향 HTTP server

## 사용 시점

HTTP/1.x 요청 parsing, route 선택, keep-alive, CGI process 실행이 실제 요구사항일 때 참고합니다. socket event loop를 처음 배우기 위한 선행 문서는 아닙니다. 먼저 [`POSIX socket과 event loop`](08-posix-sockets-and-event-loop.md)의 다음 내용을 이해해야 합니다.

- TCP는 message가 아니라 byte stream입니다.
- 한 번의 `recv()`에 요청 전체가 들어온다고 가정하면 안 됩니다.
- `send()`는 일부 byte만 전송할 수 있습니다.
- connection마다 input/output 상태를 보관해야 합니다.
- non-blocking I/O에서는 `EINTR`, `EAGAIN`, EOF와 일반 오류를 구분해야 합니다.
- fd ownership과 poller 등록 상태를 별도로 관리해야 합니다.

이 문서에서는 그 위에 HTTP/1.x 요청/응답 규칙과 CGI process 상태를 추가합니다.

## HTTP 요청도 여러 조각으로 도착합니다

HTTP 요청은 개념적으로 다음과 같은 부분으로 이루어집니다.

```text
request line
headers
empty line
optional body bytes
```

예:

```text
POST /echo HTTP/1.1\r\n
Host: example.test\r\n
Content-Length: 5\r\n
\r\n
hello
```

TCP에서는 이 전체가 한 번의 `recv()`에 들어온다는 보장이 없습니다.

예를 들어 실제 수신은 다음처럼 나뉠 수 있습니다.

```text
recv #1:
"POST /echo HT"

recv #2:
"TP/1.1\r\nHost: example.test\r\nContent-Len"

recv #3:
"gth: 5\r\n\r\nhe"

recv #4:
"llo"
```

따라서 parser는 현재 connection의 input buffer에 들어온 byte를 조금씩 소비하면서 상태를 유지해야 합니다.

## incremental parser

parser는 한 번 호출될 때마다 현재 buffer에서 가능한 만큼 해석하고 다음과 같은 결과를 반환할 수 있습니다.

```text
NeedMore
Complete
Error
```

의미는 다음과 같습니다.

```text
NeedMore
→ 현재까지의 byte는 유효하지만 요청을 완성하려면 더 필요함

Complete
→ 요청 하나가 완성됨

Error
→ 현재 요청을 더 이상 유효한 HTTP 요청으로 해석할 수 없음
```

`NeedMore`와 `Error`를 구분하는 것이 중요합니다.

예를 들어:

```text
"Content-Len"
```

까지만 들어왔다면 아직 header가 잘못된 것이 아니라 단순히 입력이 덜 도착한 상태일 수 있습니다.

반면 header 문법상 절대 허용할 수 없는 형식이 확인되었다면 `Error`입니다.

## parser 상태를 단계로 나눕니다

incremental parser는 내부 상태를 명시적으로 두면 이해하기 쉽습니다.

예:

```text
ReadingRequestLine
ReadingHeaders
ReadingBody
Complete
Error
```

흐름:

```text
ReadingRequestLine
→ CRLF 발견
→ request line 검증
→ ReadingHeaders

ReadingHeaders
→ 각 header 검증
→ 빈 줄 발견
→ body 길이 결정
→ body 없음이면 Complete
→ body 있음이면 ReadingBody

ReadingBody
→ 필요한 byte 수만큼 수신
→ Complete
```

이렇게 하면 incomplete input과 malformed input을 구분하기 쉽습니다.

## CRLF 기준을 명확히 합니다

HTTP/1.x의 line delimiter는 일반적으로 `"\r\n"`입니다.

parser가 단순히 `'\n'` 하나만 찾도록 만들면 잘못된 line ending을 의도치 않게 허용할 수 있습니다.

프로젝트에서 엄격한 HTTP parsing을 요구한다면 다음처럼 line 종료 규칙을 고정합니다.

```text
request line 종료
→ "\r\n"

각 header 종료
→ "\r\n"

header section 종료
→ "\r\n\r\n"
```

반대로 과제나 제한된 구현에서 LF-only 입력까지 허용하기로 했다면 그 규칙을 명시해야 합니다.

parser 구현의 우연으로 허용 범위가 결정되지 않게 합니다.

## `Complete` 뒤에도 byte가 남을 수 있습니다

keep-alive connection에서는 하나의 TCP connection으로 여러 HTTP 요청이 들어올 수 있습니다.

예:

```text
GET /a HTTP/1.1\r\n
Host: x\r\n
\r\n
GET /b HTTP/1.1\r\n
Host: x\r\n
\r\n
```

한 번의 `recv()`에서 두 요청이 모두 들어올 수 있습니다.

따라서 첫 요청을 완성한 뒤 input buffer 전체를 지우면 안 됩니다.

```text
완성된 첫 요청 byte
→ consume

남은 byte
→ 다음 요청 parsing에 유지
```

pipelining을 지원한다면 남은 byte에서 다음 요청을 즉시 이어서 parse할 수 있습니다.

## pipelining과 응답 순서

HTTP/1.1 pipelining을 지원한다면 여러 요청을 응답 완료 전에 연속해서 받을 수 있습니다.

이 경우 server는 최소한 다음을 보장해야 합니다.

```text
요청 A
요청 B
요청 C
```

에 대한 응답이 connection에서:

```text
응답 A
응답 B
응답 C
```

순서로 전송됩니다.

각 요청 처리 완료 시점이 다르더라도 같은 connection에서 response 순서를 뒤섞으면 안 됩니다.

단순한 구현에서는 한 요청의 response를 output queue에 넣은 뒤 다음 요청을 처리하는 방식으로 순서를 유지할 수 있습니다.

pipelining을 지원하지 않는다면 다음 요청을 언제 읽고 언제 거부할지 명확히 정합니다.

## 요청 모델

외부 byte stream을 검증한 뒤 내부 요청 객체로 바꿉니다.

```cpp
struct HttpRequest {
    std::string method;
    std::string target;
    std::string version;
    std::map<std::string, std::string> headers;
    std::string body;
};
```

이 타입은 이미 parser의 기본 검증을 통과한 요청을 표현해야 합니다.

즉, handler가 raw request line을 다시 parsing하지 않게 합니다.

## request line 검증

예:

```text
GET /health HTTP/1.1
```

parser는 최소한 다음을 확인합니다.

```text
method
target
version
```

세 부분이 기대한 형태로 존재하는가?

추가로:

- 지원하는 method인가
- method token에 허용되지 않는 문자가 없는가
- target이 허용한 형식인가
- version 문자열이 정확히 지원 대상인가

를 검사합니다.

예를 들어 구현이 HTTP/1.0과 HTTP/1.1만 지원한다면:

```text
HTTP/1.0
HTTP/1.1
```

외의 version은 명시적으로 거부합니다.

## target 검증

request target을 단순 문자열로 보관하더라도 허용 범위를 정해야 합니다.

예를 들어 origin-form만 지원한다면 일반적으로 path가 `/`로 시작하는 형태를 기대할 수 있습니다.

```text
/health
/users?id=10
```

프로젝트가 absolute-form, authority-form, asterisk-form까지 지원하지 않는다면 parser나 route 단계에서 이를 명시적으로 거부합니다.

"어떤 target도 문자열이니까 일단 저장한다"는 방식은 이후 route matching이나 보안 검증을 어렵게 만듭니다.

## header parsing

header line은 개념적으로:

```text
name ":" value
```

형태입니다.

parser는 최소한 다음을 정해야 합니다.

- header name에 어떤 문자를 허용하는가
- `:` 앞뒤 공백을 어떻게 처리하는가
- value 앞뒤의 optional whitespace를 어떻게 처리하는가
- 빈 value를 허용하는가
- 같은 header가 여러 번 등장하면 어떻게 처리하는가

특히 중복 header는 무조건 마지막 값을 덮어쓰지 않습니다.

일부 header는 여러 값을 합칠 수 있지만, 일부는 중복 자체가 오류일 수 있습니다.

프로젝트에서 필요한 header만 지원한다면 header별 정책을 명시적으로 두는 편이 안전합니다.

## header 이름의 대소문자

HTTP header field-name은 대소문자를 구분하지 않는 방식으로 처리해야 합니다.

예:

```text
Host
host
HOST
```

를 서로 다른 header로 취급하면 안 됩니다.

따라서 내부 저장 전에 이름을 canonical form으로 바꿀 수 있습니다.

예:

```text
lowercase
```

```cpp
headers["host"] = value;
```

또는 map comparator를 case-insensitive 방식으로 구성할 수도 있습니다.

중요한 것은 lookup마다 대소문자 처리가 달라지지 않게 하는 것입니다.

## `Host`

HTTP/1.1 요청에서는 `Host`가 중요합니다.

프로젝트가 HTTP/1.1 요청을 지원한다면 최소한 다음을 검사합니다.

```text
Host header가 필요한가
비어 있어도 되는가
중복 Host를 허용하는가
```

예를 들어 하나의 `Host`만 허용한다고 정했다면 두 개 이상 등장한 요청을 명시적으로 오류 처리합니다.

HTTP/1.0에서는 같은 요구를 그대로 적용하지 않을 수 있으므로 version과 함께 판단합니다.

## `Content-Length`

`Content-Length`가 있으면 문자열 전체가 유효한 10진수인지 검사합니다.

예:

```text
Content-Length: 123
```

검사 항목:

```text
빈 값이 아닌가
숫자 외 문자가 없는가
음수를 허용하지 않는가
정수 변환 overflow가 없는가
server의 body size 상한 이하인가
```

`atoi()`로 단순 변환하지 않습니다.

`strtol()` 또는 적절한 unsigned 범위 검사로 전체 문자열 소비와 범위를 확인합니다.

## 중복 `Content-Length`

`Content-Length`가 여러 번 등장하는 요청을 어떻게 처리할지 명시해야 합니다.

단순 구현에서는 다음처럼 보수적으로 처리할 수 있습니다.

```text
Content-Length가 둘 이상 등장
→ Bad Request
```

같은 값이면 허용하는 구현도 있을 수 있지만, 해석 차이는 request smuggling 같은 문제와 연결될 수 있으므로 제한된 server에서는 한 값만 허용하는 정책이 더 단순합니다.

중요한 것은 map에 마지막 값만 덮어써 중복 여부 자체를 잃지 않는 것입니다.

## `Transfer-Encoding`

body framing은 요청 경계를 결정하는 핵심 정보입니다.

구현이 chunked transfer coding을 지원하지 않는다면:

```text
Transfer-Encoding 존재
→ 명시적으로 거부
```

하는 편이 안전합니다.

특히 `Content-Length`와 `Transfer-Encoding`이 함께 있는 요청을 단순히 하나를 우선해서 처리하지 않습니다.

지원하지 않는 framing 조합은 parsing 단계에서 명시적으로 거부합니다.

그래야 client와 server가 body 끝을 서로 다르게 해석하는 문제를 줄일 수 있습니다.

## body 길이는 framing이 결정합니다

지원 범위를 단순화해 다음만 허용한다고 가정할 수 있습니다.

```text
Content-Length 없음
→ body 없음

Content-Length: N
→ 정확히 N byte body
```

이 경우 parser는 header section이 끝난 뒤 `N` byte가 모두 들어올 때까지 `NeedMore`를 반환합니다.

예:

```text
Content-Length: 5
body buffer: "hel"
```

이면 아직 complete가 아닙니다.

```text
body buffer: "hello"
```

가 되었을 때 요청 하나가 완성됩니다.

그 뒤 남은 byte가 있다면 다음 pipeline 요청에 속할 수 있습니다.

## body byte 수와 문자열 길이

HTTP의 `Content-Length`는 전송되는 body의 byte 수입니다.

C++ `std::string`은 embedded null byte도 저장할 수 있으므로 byte container처럼 사용할 수 있습니다.

따라서 다음처럼 실제 저장된 byte 수를 사용합니다.

```cpp
body.size()
```

문자 encoding의 "글자 수"와 byte 수를 같은 것으로 생각하지 않습니다.

UTF-8처럼 한 문자가 여러 byte를 사용할 수 있는 encoding에서는:

```text
문자 수
≠
전송 byte 수
```

일 수 있습니다.

HTTP `Content-Length`에는 전송 byte 수를 사용합니다.

## 요청 객체는 candidate로 완성합니다

parsing 중 일부 필드만 실제 ready request 객체에 기록하면 오류 뒤 불완전한 상태가 남을 수 있습니다.

예:

```text
method 저장
target 저장
headers 일부 저장
잘못된 Content-Length 발견
```

이런 partial state를 handler가 실수로 사용하면 안 됩니다.

따라서 지역 candidate를 완성한 뒤 성공 시 ready 상태로 옮깁니다.

개념:

```cpp
HttpRequest candidate;

parseRequestLine(candidate);
parseHeaders(candidate);
parseBody(candidate);
validate(candidate);

request.swap(candidate);
```

또는 parser 내부에서 현재 작업용 객체와 완료된 객체를 구분합니다.

핵심은 `Complete` 상태에서만 외부가 완전한 `HttpRequest`를 얻도록 만드는 것입니다.

## 입력 상한

HTTP server는 connection마다 입력 크기 상한을 정해야 합니다.

최소한 다음을 고려합니다.

- request line 최대 길이
- 전체 header section 최대 크기
- header 개수
- 개별 header line 최대 길이
- body 최대 크기
- connection별 input buffer 최대 크기
- connection별 pending output 최대 크기
- 한 connection에서 대기할 pipeline 요청 수

상한이 없으면 느리거나 악성인 client가 delimiter나 body 끝을 보내지 않은 채 server memory를 계속 사용하게 만들 수 있습니다.

## 상한은 parsing 이전에도 적용합니다

header 종료 `"\r\n\r\n"`을 아직 찾지 못했다고 해서 input buffer를 무제한으로 늘려서는 안 됩니다.

예:

```text
현재 header section 미완성
input buffer > MAX_HEADER_BYTES
→ 즉시 오류
```

body도 `Content-Length`를 읽는 순간 상한과 비교합니다.

```text
Content-Length > MAX_BODY_BYTES
→ body를 실제로 다 받을 때까지 기다리지 않고 거부
```

이렇게 하면 거대한 입력을 memory에 쌓은 뒤에야 오류를 발견하는 일을 피할 수 있습니다.

## 오류 응답과 연결 종료 정책

parse 오류가 발생했을 때 어떤 HTTP status를 보낼지와 connection을 닫을지 정합니다.

예:

```text
잘못된 request syntax
→ 400 Bad Request
→ Connection: close
→ 응답 전송 후 close
```

body가 너무 큰 경우:

```text
→ 413 Payload Too Large
```

지원하지 않는 transfer coding이라면 요구사항에 맞는 4xx/5xx 정책을 정합니다.

중요한 것은 parser 내부 예외 메시지를 그대로 HTTP body나 status line으로 사용하지 않는 것입니다.

외부 응답은 안정된 status code와 formatter를 통해 만듭니다.

## route 설정

route 설정 예:

```text
route GET /health health;
route POST /echo echo;
route POST /cgi cgi;
```

설정 파일을 읽을 때 각 줄을 즉시 기존 Router에 반영하지 않습니다.

먼저 candidate 설정 전체를 검증합니다.

확인 항목:

- directive 형식이 올바른가
- 지원 method인가
- path가 허용한 형식인가
- handler 이름이 등록된 값인가
- 같은 method/path가 중복되지 않는가
- 필요한 CGI 실행 파일이나 설정이 유효한가

전체가 유효할 때만 새 Router를 활성화합니다.

## route key

route는 method와 path의 조합으로 식별될 수 있습니다.

예:

```text
GET /health
POST /health
```

은 서로 다른 route입니다.

따라서 단순 path만 key로 쓰면 method별 route를 구분할 수 없습니다.

예를 들어 별도 key 타입을 둘 수 있습니다.

```cpp
struct RouteKey {
    std::string method;
    std::string path;
};
```

또는 문자열 조합을 사용할 수 있지만 충돌 없는 encoding 규칙을 정해야 합니다.

타입으로 표현하면 comparator와 중복 규칙을 명확히 만들기 쉽습니다.

## Router의 책임

Router는 요청을 어느 handler로 보낼지 결정합니다.

개념:

```text
(method, path)
→ handler
```

Router가 직접 다음 작업까지 모두 맡지 않게 합니다.

```text
HTTP response serialization
socket write
CGI pipe 관리
connection close
```

Router의 역할은 route 선택입니다.

handler는 선택된 요청을 처리해 내부 `HttpResponse`를 만들고, serializer가 최종 HTTP byte string을 만들 수 있습니다.

## handler 이름과 handler 객체

설정 파일에 문자열 handler 이름이 들어 있더라도 runtime의 Router는 가능한 한 실제 handler를 직접 선택하도록 변환할 수 있습니다.

예:

```text
"health"
→ HealthHandler

"echo"
→ EchoHandler

"cgi"
→ CgiHandler
```

설정 parsing 때 등록되지 않은 handler 이름을 모두 거부하면 request 처리 시점에 다시 문자열 검증을 반복할 필요가 줄어듭니다.

## Connection이 보유하는 상태

연결마다 독립적인 상태가 필요합니다.

예:

```text
socket fd
HttpParser
raw input buffer
pending output buffer
write offset
close-after-write 여부
peer read closed 여부
pipeline queue
shared Router 참조
shared server configuration 참조
현재 CGI 작업 상태
```

실제 구현은 프로젝트 범위에 맞게 단순화할 수 있지만, 서로 다른 connection의 parser/output 상태가 섞이면 안 됩니다.

## Connection의 소유권

`Connection`이 socket fd를 소유한다고 정하면:

```text
Connection 생성
→ fd ownership 획득

Connection 소멸
→ fd close
```

가 됩니다.

C++98에서는 raw fd가 정수이므로 compiler 기본 복사를 허용하면 같은 fd를 두 객체가 소유할 수 있습니다.

따라서 복사가 필요 없다면 막습니다.

```cpp
class Connection {
public:
    explicit Connection(int fd);
    ~Connection();

private:
    Connection(const Connection &);
    Connection &operator=(const Connection &);

private:
    int fd_;
};
```

## shared Router는 보통 관찰 참조입니다

Router와 server configuration은 많은 connection이 공유할 수 있습니다.

Connection이 이 객체들을 직접 소유하지 않고 reference나 pointer로 관찰한다면:

```text
Server/Router
→ Connection보다 오래 살아야 함
```

이라는 수명 조건이 생깁니다.

조립 순서를 다음처럼 구성할 수 있습니다.

```text
Server config 생성
Router 생성
listener 시작
Connection 생성
...
Connection 모두 제거
listener 종료
Router/config 소멸
```

Connection이 살아 있는 동안 shared configuration이 먼저 파괴되지 않게 합니다.

## keep-alive

HTTP/1.x에서는 connection 재사용 규칙이 version과 `Connection` header에 따라 달라집니다.

일반적인 원칙:

```text
HTTP/1.1
→ 기본적으로 persistent connection
→ Connection: close이면 닫음

HTTP/1.0
→ 기본적으로 요청 후 닫음
→ 명시적으로 keep-alive를 지원하기로 한 경우만 유지
```

프로젝트가 어떤 범위의 HTTP/1.0 keep-alive를 지원하는지 명시합니다.

## 요청마다 keep-alive 여부를 결정합니다

connection 자체가 한 번 keep-alive라고 정해지면 영원히 같은 상태인 것은 아닙니다.

각 요청에서:

```text
HTTP version
Connection header
server 정책
오류 상태
shutdown 상태
```

를 보고 response 뒤 connection을 유지할지 결정합니다.

예:

```text
HTTP/1.1 + 정상 요청
→ keep alive

HTTP/1.1 + Connection: close
→ close after response

parse error
→ 보통 close after response
```

## close-after-write

connection을 닫아야 한다고 결정해도 pending response가 있다면 즉시 fd를 닫지 않습니다.

흐름:

```text
응답 생성
→ output buffer에 추가
→ closeAfterWrite = true
→ readable interest 필요 여부 결정
→ writable event에서 output 전송
→ output이 모두 비면 close
```

`closeAfterWrite`는 다음 두 상태를 구분하기 위해 필요합니다.

```text
지금 바로 close
응답을 모두 보낸 뒤 close
```

HTTP error 응답이나 `Connection: close` 처리에서 자주 사용됩니다.

## close-after-write 상태에서 새 요청을 읽을지 정합니다

이미 이 response 뒤 연결을 닫기로 결정했다면 이후 pipelined request를 더 처리할 이유가 없을 수 있습니다.

단순한 정책:

```text
closeAfterWrite == true
→ readable interest 제거
→ pending output만 flush
→ close
```

이렇게 하면 종료 예정 connection이 새 요청을 계속 받아 output을 늘리는 일을 피할 수 있습니다.

## 응답 모델

handler가 바로 HTTP 문자열을 만들지 않고 내부 response 타입을 반환할 수 있습니다.

예:

```cpp
struct HttpResponse {
    int status;
    std::string contentType;
    std::string body;
    bool close;
};
```

실제 프로젝트에서는 header map이나 추가 필드가 필요할 수 있습니다.

serializer가 이 값을 HTTP wire format으로 바꿉니다.

## 응답 만들기

예:

```text
HTTP/1.1 200 OK\r\n
Content-Length: 5\r\n
Content-Type: text/plain\r\n
Connection: keep-alive\r\n
\r\n
hello
```

구성 순서는 다음과 같습니다.

```text
status line
headers
empty line
body bytes
```

line ending은 `"\r\n"`을 사용합니다.

## status code와 reason phrase

외부 입력 문자열을 그대로 status line에 넣지 않습니다.

예를 들어 내부에는:

```text
status = 200
```

처럼 안정된 값을 저장하고 serializer가 지원하는 reason phrase를 선택할 수 있습니다.

```text
200 → OK
400 → Bad Request
404 → Not Found
413 → Payload Too Large
500 → Internal Server Error
502 → Bad Gateway
504 → Gateway Timeout
```

지원하지 않는 임의 status나 잘못된 문자열이 wire format에 들어가지 않게 합니다.

## `Content-Length`

응답 body의 실제 byte 수로 계산합니다.

```cpp
const std::size_t length =
    response.body.size();
```

그 값을 10진수 문자열로 변환해 header에 넣습니다.

body를 생성한 뒤 길이를 계산해야 하며, body를 나중에 변경하면서 기존 `Content-Length`를 그대로 두면 안 됩니다.

## header injection을 막습니다

응답 header에 request나 CGI에서 얻은 문자열을 넣는다면 `'\r'`이나 `'\n'`이 포함되어 새 header나 status line으로 해석되지 않게 검증해야 합니다.

예:

```text
사용자 입력:
"hello\r\nX-Evil: 1"
```

를 검증 없이 header value로 사용하면 wire format이 깨질 수 있습니다.

HTTP response의 구조를 만드는 문자열과 외부 입력 값을 명확히 분리합니다.

## CGI process

CGI를 실행하면 socket 외에도 child process와 여러 pipe의 수명을 관리해야 합니다.

일반적인 구조:

```text
stdin pipe 생성
stdout pipe 생성
fork
```

그 뒤 parent와 child의 책임이 달라집니다.

## pipe 방향

CGI stdin pipe:

```text
parent
→ request body write
→ child stdin
```

CGI stdout pipe:

```text
child stdout
→ response bytes
→ parent read
```

각 pipe는 read end와 write end를 가지므로 어떤 process가 어느 end를 사용하고 닫는지 명확히 적습니다.

## `fork()` 전 준비

`pipe()`를 여러 번 호출하면 중간 실패 시 이미 연 fd를 정리해야 합니다.

예:

```text
stdin pipe 성공
stdout pipe 실패
```

이면 stdin pipe의 두 fd를 모두 닫고 실패를 상위로 전달해야 합니다.

`fork()` 전까지 parent process가 모든 pipe fd를 소유합니다.

## child 경로

child에서는 일반적으로 다음 순서를 사용합니다.

```text
dup2(stdin read end, STDIN_FILENO)
dup2(stdout write end, STDOUT_FILENO)

원래 pipe fd close
listener/client/poller 등 불필요한 inherited fd close

execve(...)
```

`dup2()` 뒤 원래 fd를 닫지 않으면 child가 불필요한 descriptor를 계속 보유할 수 있습니다.

특히 server의 listener나 다른 client socket이 child에 남으면 parent가 닫아도 실제 kernel resource가 계속 열려 있을 수 있습니다.

`FD_CLOEXEC`를 적절히 사용하면 exec 성공 뒤 불필요한 fd가 남는 문제를 줄일 수 있습니다.

## `execve()` 실패

`execve()`가 성공하면 현재 child process image가 새 프로그램으로 대체되므로 기존 코드로 돌아오지 않습니다.

반대로 반환했다면 실패입니다.

child에서 `execve()` 실패 후 parent용 C++ cleanup 흐름으로 돌아가면 안 됩니다.

보통 child 경로에서는 최소한의 안전한 오류 처리 후 `_exit()`로 종료합니다.

개념:

```cpp
::execve(...);

/* 여기 도달했다면 실패 */
::_exit(127);
```

`exit()`는 parent에서 복제된 stdio buffer나 atexit handler를 실행할 수 있으므로 fork 후 exec 실패 경로에서는 `_exit()`가 더 적절한 경우가 많습니다.

## parent 경로

fork 성공 뒤 parent는 child가 사용할 pipe end를 닫습니다.

예:

```text
parent keeps:
CGI stdin write end
CGI stdout read end

parent closes:
CGI stdin read end
CGI stdout write end
```

그 뒤 parent가 보유한 pipe를 non-blocking으로 설정해 main event loop에서 처리할 수 있습니다.

## CGI 상태

하나의 CGI 작업에는 다음 상태가 필요할 수 있습니다.

```text
pid
stdin fd
stdout fd
request body
body write offset
captured output
stdout EOF 여부
child 종료 여부
deadline
output byte count
```

이 상태를 connection이나 별도 `CgiProcess` 객체에 보관합니다.

단순 boolean 몇 개만으로 관리하면 pipe EOF와 child 종료 순서를 놓치기 쉽습니다.

## request body 일부 쓰기

CGI stdin도 pipe이므로 non-blocking write에서 부분 쓰기가 발생할 수 있습니다.

```text
request body 1000 bytes
write() → 300
다음 writable event에서 offset 300부터 계속
```

모든 request body를 쓴 뒤에는 parent가 CGI stdin write end를 닫아 child가 stdin EOF를 받을 수 있게 해야 합니다.

```text
body 모두 전송
→ stdin pipe close
```

pipe를 계속 열어 두면 CGI program이 EOF를 기다리며 끝나지 않을 수 있습니다.

## CGI stdout 일부 읽기

CGI stdout도 byte stream입니다.

한 번의 `read()`에 전체 output이 들어온다고 가정하지 않습니다.

```text
read > 0
→ output buffer append

EAGAIN
→ 현재 읽을 수 있는 만큼 처리 완료

EOF
→ child stdout stream 종료

기타 오류
→ CGI 실패 처리
```

output 크기 상한을 계속 검사합니다.

```text
captured output > MAX_CGI_OUTPUT
→ CGI 실패
→ child 종료 정책 수행
```

## child 종료와 stdout EOF는 별개입니다

다음 두 사건은 순서가 항상 같다고 가정하면 안 됩니다.

```text
child process 종료
CGI stdout pipe EOF
```

child가 종료되었더라도 pipe에 아직 읽지 않은 output byte가 남아 있을 수 있습니다.

따라서:

```text
waitpid가 종료 보고
→ stdout을 즉시 버림
```

으로 처리하면 마지막 output을 잃을 수 있습니다.

반대로 stdout EOF가 왔다고 child가 이미 회수되었다는 뜻도 아닙니다.

다음 상태를 별도로 추적합니다.

```text
stdoutClosed
childExited
```

CGI 작업 완료 조건을 두 상태와 output parse 결과로 결정합니다.

## `waitpid()`

child process는 종료 후 parent가 `waitpid()`로 상태를 회수해야 합니다.

회수하지 않으면 zombie process가 남습니다.

non-blocking event loop에서는 다음처럼 사용할 수 있습니다.

```cpp
pid_t result =
    ::waitpid(pid, &status, WNOHANG);
```

의미:

```text
result == 0
→ 아직 종료하지 않음

result == pid
→ 종료 상태 회수 완료

result == -1
→ 오류
```

`EINTR` 처리와 이미 회수된 child 상태를 구분합니다.

## child exit status

`waitpid()`가 성공했다고 CGI가 정상 성공한 것은 아닙니다.

다음을 구분합니다.

```text
WIFEXITED(status)
→ 정상 exit 계열 종료

WEXITSTATUS(status) == 0
→ 일반적으로 성공으로 간주 가능

WIFSIGNALED(status)
→ signal에 의해 종료
```

프로젝트 CGI 정책에 따라 non-zero exit code를 `502 Bad Gateway`로 처리할 수 있습니다.

## CGI timeout

CGI마다 deadline을 기록합니다.

예:

```text
start time
timeout duration
deadline = start + timeout
```

event loop에서 현재 시간이 deadline을 넘었는지 확인합니다.

timeout 발생 시:

```text
새 stdin write 중단
pipe 정리
child 종료 signal 전송
필요하면 강제 종료
waitpid로 회수
HTTP 504 생성
```

처럼 상태 전이를 명확히 정합니다.

## process group

CGI program이 다시 child process를 만들 수 있습니다.

원래 CGI pid 하나만 kill하면 그 자식들이 살아남을 수 있습니다.

"CGI와 그 자식까지 timeout 때 종료"가 요구사항이라면 CGI child를 별도 process group에 넣고 group 전체에 signal을 보내는 설계를 검토합니다.

예:

```text
child
→ 별도 process group 생성

timeout
→ process group에 SIGTERM
→ grace period
→ 필요 시 SIGKILL
→ 원래 child를 waitpid
```

process group 설정 시점과 `fork()` 후 race를 고려해야 하므로 실제 구현에서는 부모/자식 어느 쪽에서 `setpgid()`를 호출할지 명확히 정합니다.

## kill 뒤에도 `waitpid()`가 필요합니다

다음만 수행하면 충분하지 않습니다.

```cpp
kill(pid, SIGKILL);
```

signal 전송은 child를 회수하는 동작이 아닙니다.

종료가 확인된 뒤 반드시 `waitpid()`를 호출해 zombie를 없애야 합니다.

```text
kill
→ child 종료
→ waitpid
→ pid lifecycle 완료
```

를 하나의 수명 규칙으로 봅니다.

## CGI 결과를 HTTP로 바꿉니다

CGI stdout은 임의 문자열이 아니라 CGI response 형식으로 해석해야 합니다.

일반적으로 다음처럼 header와 body를 구분합니다.

```text
CGI headers
blank line
body
```

CGI output도 여러 `read()`로 나뉠 수 있으므로 전체 header section을 incremental하게 수집하고 검증해야 합니다.

## CGI header 검증

CGI가 출력한 header를 그대로 HTTP response에 붙이지 않습니다.

최소한 다음을 확인합니다.

- header line 형식이 유효한가
- header name/value에 CR/LF injection이 없는가
- 전체 CGI header 크기가 상한 이하인가
- 중복 header를 어떻게 처리할 것인가
- `Status` header 형식이 유효한가
- server가 직접 관리할 header와 충돌하지 않는가

server가 최종 `Content-Length`와 `Connection`을 직접 만든다면 CGI가 같은 header를 임의로 덮어쓰지 못하게 할 수 있습니다.

## CGI `Status`

CGI가 다음처럼 status를 지정할 수 있습니다.

```text
Status: 201 Created
```

이를 그대로 HTTP status line 문자열로 복사하지 않습니다.

다음을 검사합니다.

```text
3자리 status code인가
허용 범위인가
구문이 유효한가
reason phrase에 CR/LF가 없는가
```

내부적으로:

```text
status code
optional reason
```

으로 분리한 뒤 HTTP serializer가 최종 status line을 구성합니다.

## CGI 실패와 HTTP status

정책 예:

```text
CGI timeout
→ 504 Gateway Timeout

exec 실패
→ 502 Bad Gateway

비정상 종료
→ 502 Bad Gateway

잘못된 CGI output
→ 502 Bad Gateway

CGI output 상한 초과
→ 502 Bad Gateway
```

프로젝트가 다른 status 정책을 요구한다면 그 규칙을 고정합니다.

중요한 것은 child의 임의 stderr나 exit message를 그대로 HTTP status line에 사용하지 않는 것입니다.

## CGI stderr

CGI stderr를 어떻게 처리할지도 정합니다.

가능한 정책:

```text
server log로 전달
별도 pipe로 수집
/dev/null로 보냄
```

stderr를 stdout과 같은 pipe에 섞으면 CGI response parsing이 깨질 수 있습니다.

따라서 CGI protocol output과 진단 output을 구분합니다.

## event loop와 blocking CGI

socket을 모두 non-blocking으로 만들어도 CGI를 동기적으로 끝까지 기다리면 event loop 전체가 막힙니다.

예:

```text
request 수신
→ fork
→ parent가 blocking write
→ blocking read
→ blocking waitpid
→ CGI 종료까지 다른 client 처리 중단
```

이 구조에서는 network socket만 non-blocking일 뿐 server 전체는 CGI 동안 사실상 blocking입니다.

작은 프로젝트에서는 의도적인 제한으로 둘 수 있지만 다음을 명시해야 합니다.

```text
동시에 하나의 CGI만 처리
CGI 실행 동안 다른 connection latency 증가 가능
```

## concurrent CGI

동시 CGI가 필요하다면 child pipe fd도 main event loop에 등록할 수 있습니다.

예:

```text
client socket readable
CGI stdin writable
CGI stdout readable
CGI deadline
child exit state
```

를 같은 loop에서 관리합니다.

이 경우 각 CGI request는 작은 상태 머신처럼 동작합니다.

```text
Starting
→ WritingInput
→ ReadingOutput
→ WaitingForExit
→ Complete
```

실제 pipe EOF와 child exit 순서에 따라 상태는 조금 달라질 수 있습니다.

## CGI와 connection 수명

client가 CGI 처리 중 먼저 연결을 끊을 수 있습니다.

이때 정책을 정해야 합니다.

예:

```text
client disconnect
→ CGI도 즉시 취소

또는

client disconnect
→ CGI는 끝까지 실행하지만 response는 버림
```

일반적인 request/response server에서는 불필요한 CGI를 중단하는 편이 resource 보호에 유리할 수 있습니다.

어느 정책이든:

```text
pipe close
child signal
waitpid
connection 제거
```

순서를 일관되게 처리해야 합니다.

## thread를 추가하면 문제가 자동으로 사라지지 않습니다

blocking CGI를 피하려고 단순히 thread를 추가하면 다음 문제를 다시 설계해야 합니다.

- Connection과 Router의 thread safety
- shutdown 시 thread 회수
- CGI child ownership
- output buffer 동기화
- timeout coordination
- process-wide signal 처리
- 동시 request 상한

따라서 concurrency model을 바꾸는 것은 단순 구현 세부 변경이 아닙니다.

한 thread event loop를 유지할지, worker thread를 둘지 요구사항을 먼저 정합니다.

## HTTP response와 pending output

최종 HTTP response byte string은 바로 `send()` 한 번으로 끝난다고 가정하지 않습니다.

```text
HttpResponse
→ serialize
→ Connection output buffer append
→ writable event에서 부분 전송
→ offset 증가
```

keep-alive connection에서 여러 response가 pending될 수 있으므로 output queue의 순서를 유지합니다.

close-after-write가 설정되면 마지막 response byte까지 전송한 뒤 fd를 닫습니다.

## 오류가 난 request 뒤 parser 재사용

parse 오류 후 같은 connection을 계속 사용할지 정해야 합니다.

단순하고 안전한 정책은:

```text
parse error
→ error response 생성
→ closeAfterWrite
→ parser/input 폐기
```

입니다.

잘못된 request의 정확한 byte 경계를 신뢰할 수 없는 상태에서 다음 request를 계속 해석하면 parser synchronization이 깨질 수 있습니다.

특정 오류에서만 recovery를 지원하려면 그 조건을 명확히 정의해야 합니다.

## server shutdown

server 종료 시 CGI와 keep-alive connection도 정리해야 합니다.

예:

```text
shutdown flag 설정
→ 새 accept 중단
→ 새 request 처리 중단 또는 제한
→ pending response flush 정책 적용
→ active CGI 종료/회수
→ client poller 등록 제거
→ client close
→ listener close
→ poller close
```

CGI child가 남아 있는 상태에서 server process만 종료하면 orphan/zombie 관리 문제가 생길 수 있으므로 shutdown 완료 조건에 child 회수를 포함합니다.

## 테스트: incremental parsing

request line과 header를 여러 조각으로 나눠 보냅니다.

예:

```text
"GET / HTTP/1."
"1\r\nHo"
"st: x\r"
"\n\r\n"
```

확인:

```text
중간 조각에서 Error가 나지 않는가
완성 시점에 정확히 한 요청이 생성되는가
남은 byte가 유실되지 않는가
```

## 테스트: body fragmentation

예:

```text
Content-Length: 10
```

을 보낸 뒤 body를:

```text
"12"
"345"
"67890"
```

처럼 나눠 전송합니다.

10 byte가 모두 오기 전에는 `Complete`가 되면 안 됩니다.

## 테스트: pipelining

두 요청을 한 번에 보냅니다.

```text
GET /a HTTP/1.1\r\nHost: x\r\n\r\n
GET /b HTTP/1.1\r\nHost: x\r\n\r\n
```

확인:

```text
첫 요청 뒤 남은 byte가 보존되는가
두 번째 요청도 처리되는가
response 순서가 요청 순서와 같은가
pipeline 제한을 초과하면 정책대로 처리되는가
```

## 테스트: keep-alive와 close

검사 예:

```text
HTTP/1.1 기본 keep-alive
HTTP/1.1 + Connection: close
HTTP/1.0 기본 close
지원하는 경우 HTTP/1.0 keep-alive
parse error 뒤 close
server shutdown 중 close
```

응답의 `Connection` header와 실제 fd 종료 시점이 일치해야 합니다.

## 테스트: malformed request

다음 입력을 별도로 보냅니다.

- 잘못된 HTTP version
- request line token 부족/초과
- 잘못된 header line
- 중복 `Host`
- 잘못된 `Content-Length`
- 너무 큰 `Content-Length`
- 중복 `Content-Length`
- 지원하지 않는 `Transfer-Encoding`
- `Content-Length`와 `Transfer-Encoding` 동시 존재
- header section 상한 초과
- header 개수 상한 초과

오류 뒤 기존 connection 상태와 server 전체 상태가 손상되지 않는지 확인합니다.

## 테스트: CGI

다음 CGI program을 준비하면 failure path를 테스트하기 쉽습니다.

```text
정상 output
느린 output
stdin을 천천히 읽는 program
매우 큰 output
잘못된 CGI header 출력
non-zero exit
signal 종료
존재하지 않는 executable
자식 process를 다시 만드는 program
```

확인:

```text
504/502 정책이 맞는가
pipe fd가 남지 않는가
timeout 뒤 child가 남지 않는가
kill 뒤 waitpid가 수행되는가
stdout EOF와 child exit 순서가 달라도 처리되는가
```

## 테스트: client disconnect 중 CGI

CGI 실행 직후 client connection을 닫습니다.

확인:

```text
CGI를 취소하는 정책이면 실제로 종료되는가
pipe가 모두 닫히는가
child가 waitpid로 회수되는가
Connection 삭제 뒤 stale event가 남지 않는가
```

## 테스트: resource leak

다음 작업을 반복합니다.

```text
HTTP connect
request
keep-alive 재사용
close

CGI request
timeout
close
```

server의:

```text
open fd 수
child process 수
memory 사용량
```

이 계속 증가하지 않는지 확인합니다.

정상 요청뿐 아니라 malformed request와 CGI 실패 경로에서도 검사합니다.

## 자주 놓치는 문제

- 한 번의 `recv()`에 HTTP 요청 전체가 들어온다고 생각합니다.
- incomplete request를 malformed request로 처리합니다.
- parser가 `Complete`가 된 뒤 input buffer의 남은 pipeline byte를 버립니다.
- pipelined request의 response 순서를 보장하지 않습니다.
- request line과 header의 CRLF 규칙을 명확히 하지 않습니다.
- header name의 대소문자를 서로 다른 header로 취급합니다.
- 중복 header를 map에 덮어써 중복 여부를 잃습니다.
- HTTP/1.1 요청에서 `Host` 규칙을 확인하지 않습니다.
- `Content-Length`를 `atoi()`로 변환하고 전체 문자열과 overflow를 검사하지 않습니다.
- 중복 `Content-Length`를 단순히 마지막 값으로 덮어씁니다.
- 지원하지 않는 `Transfer-Encoding`을 무시합니다.
- `Content-Length`와 `Transfer-Encoding`이 함께 있을 때 임의로 하나를 선택합니다.
- body 상한보다 큰 `Content-Length`인데도 실제 body를 끝까지 받습니다.
- partial parse 결과를 ready `HttpRequest`에 그대로 남깁니다.
- request/header/body/pipeline/output에 상한을 두지 않습니다.
- Router가 route 선택뿐 아니라 socket I/O와 response serialization까지 담당합니다.
- Connection이 참조하는 Router/config가 Connection보다 먼저 소멸합니다.
- HTTP/1.1이면 어떤 상황에서도 keep-alive라고 생각합니다.
- 닫을 connection을 response 전송 전에 즉시 close합니다.
- close-after-write 상태에서도 새 request를 계속 읽습니다.
- `Content-Length`를 문자 수로 계산합니다.
- 외부 문자열을 검증 없이 response header에 넣어 CRLF injection을 허용합니다.
- `fork()` 전에 일부 pipe만 만든 상태에서 실패했는데 fd를 정리하지 않습니다.
- child에서 `dup2()` 후 원래 pipe fd를 닫지 않습니다.
- child가 listener나 다른 client fd를 상속한 채 `execve()`합니다.
- `execve()` 실패 뒤 child가 parent용 제어 흐름으로 돌아옵니다.
- CGI stdin body를 다 쓴 뒤 pipe를 닫지 않아 child가 EOF를 기다립니다.
- CGI stdout을 한 번의 `read()`로 끝난다고 가정합니다.
- child exit와 stdout EOF가 항상 같은 순서라고 생각합니다.
- `waitpid()`를 호출하지 않아 zombie가 남습니다.
- `kill()`만 하면 child lifecycle 정리가 끝난다고 생각합니다.
- CGI `Status`나 header를 검증 없이 HTTP response에 복사합니다.
- CGI stderr를 stdout과 섞어 response parsing을 깨뜨립니다.
- socket만 non-blocking이면 CGI도 server를 막지 않는다고 생각합니다.
- thread를 추가하면 shutdown·ownership·signal 문제가 자동으로 해결된다고 생각합니다.
- parse error 뒤 parser synchronization을 확인하지 않고 같은 connection을 계속 사용합니다.
- server shutdown 때 active CGI child를 회수하지 않습니다.

## 완료 기준

다음 항목을 설명하고 코드에서 적용할 수 있으면 이 범위의 목표를 달성한 것입니다.

- HTTP request를 incremental하게 parsing하고 `NeedMore`, `Complete`, `Error`를 구분합니다.
- parser 상태를 request line, headers, body 단계로 나누어 설명합니다.
- `Complete` 뒤 남은 pipeline byte를 보존합니다.
- pipelining을 지원할 때 response 순서를 요청 순서대로 유지합니다.
- request line, CRLF, header name/value, version과 target 규칙을 검증합니다.
- header field-name을 case-insensitive하게 처리합니다.
- HTTP/1.1 `Host` 규칙과 중복 header 정책을 정합니다.
- `Content-Length`를 전체 문자열과 범위까지 검사하고 body 상한을 적용합니다.
- 지원하지 않는 `Transfer-Encoding`과 모호한 framing 조합을 명시적으로 거부합니다.
- partial parse 상태와 ready `HttpRequest`를 분리합니다.
- request line, header section, header 개수, body, pipeline과 output에 상한을 둡니다.
- route 설정 전체를 candidate에 읽고 검증 성공 후 Router를 활성화합니다.
- Router의 route 선택 책임과 handler/serializer/socket I/O 책임을 구분합니다.
- Connection이 socket, parser, input/output, write offset과 close-after-write 상태를 함께 관리합니다.
- Connection이 참조하는 Router/config의 수명이 더 길어야 하는 이유를 설명합니다.
- HTTP/1.0과 HTTP/1.1의 persistent connection 정책 차이를 설명합니다.
- 닫을 connection도 pending response를 모두 전송한 뒤 close합니다.
- 응답 `Content-Length`를 body byte 수로 계산합니다.
- response header에 외부 문자열을 넣을 때 CR/LF를 검증합니다.
- CGI pipe의 parent/child 방향과 각 fd의 close 책임을 설명합니다.
- `fork()`/`dup2()`/`execve()` 단계의 실패와 fd 정리를 처리합니다.
- `execve()` 실패 child 경로에서 `_exit()`를 사용해야 하는 이유를 설명합니다.
- CGI stdin 부분 쓰기와 stdout 부분 읽기를 event loop에서 처리합니다.
- body 전송 완료 뒤 CGI stdin pipe를 닫아 EOF를 전달합니다.
- child 종료와 stdout EOF를 별도 상태로 추적합니다.
- `waitpid(WNOHANG)`으로 child 종료를 회수하고 exit status를 검사합니다.
- CGI timeout에서 child/process group을 종료한 뒤 반드시 회수합니다.
- CGI output header와 `Status`를 검증한 뒤 HTTP response로 변환합니다.
- CGI stderr와 protocol stdout을 구분합니다.
- blocking CGI가 한 thread event loop 전체를 멈출 수 있음을 설명합니다.
- concurrent CGI가 필요할 때 child pipe와 deadline을 주 event loop 상태로 관리합니다.
- client disconnect와 server shutdown 시 CGI child와 pipe를 누수 없이 정리합니다.
- incremental parsing, pipelining, keep-alive, malformed framing, CGI timeout과 resource leak을 실패 테스트로 검증합니다.
