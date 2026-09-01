# compiler와 운영체제 차이

## 목적

같은 C++ source라도 **compiler, C++ standard library, 운영체제, CPU architecture, build option** 조합에 따라 warning, 지원 기능, ABI와 system API가 달라질 수 있습니다.

따라서 "내 환경에서 compile된다"는 사실만으로 portable하다고 판단하지 않습니다. 차이를 숨기기보다 **build matrix와 test에서 의도적으로 드러내고**, platform별 코드는 가능한 한 작은 경계에 격리합니다.

이 문서에서 구분해야 할 층은 다음과 같습니다.

```text
C++ source
↓
compiler front-end
↓
C++ standard library headers / implementation
↓
system library와 ABI
↓
operating system / kernel API
↓
CPU architecture
```

문제가 발생했을 때 어느 층의 차이인지 먼저 구분하면 원인을 훨씬 빠르게 찾을 수 있습니다.

## GCC와 Clang

GCC와 Clang은 모두 표준 C++을 폭넓게 지원하지만 다음은 동일하지 않습니다.

- warning 종류
- warning 발생 조건
- diagnostic 문구
- 일부 compiler extension
- 최적화 동작
- sanitizer 지원 범위
- 특정 표준 기능의 구현 시기

기본적으로 두 compiler에서 같은 warning 수준으로 build해 보는 것이 좋습니다.

```sh
g++ -std=c++20 -Wall -Wextra -Wpedantic source.cpp
clang++ -std=c++20 -Wall -Wextra -Wpedantic source.cpp
```

여기서 각 옵션의 의미는 대략 다음과 같습니다.

- `-Wall`: 자주 유용한 warning 묶음
- `-Wextra`: `-Wall`에 포함되지 않은 추가 warning
- `-Wpedantic`: 선택한 C++ 표준을 벗어나는 extension 사용을 추가로 진단

이 옵션들이 "모든 가능한 warning을 활성화한다"는 뜻은 아닙니다. 필요한 warning은 프로젝트 성격에 따라 추가합니다.

### `-Werror`

`-Werror`는 warning을 build failure로 바꾸므로 자신의 source 품질을 일정하게 유지하는 데 유용합니다.

```sh
g++ -std=c++20 -Wall -Wextra -Wpedantic -Werror source.cpp
```

다만 외부 dependency의 header까지 동일한 기준으로 실패시키면 compiler upgrade나 dependency 변경만으로 build가 깨질 수 있습니다.

가능하면 다음을 구분합니다.

```text
project source
→ warning을 엄격하게 적용
→ 필요하면 -Werror 적용

외부 library header
→ project가 직접 고칠 수 없는 warning은 별도 취급
```

GCC/Clang에서는 외부 header를 system header로 취급하도록 include 경로를 구성하는 방식도 사용할 수 있습니다.

핵심은 **한 compiler에서 warning이 없다는 사실이 다른 compiler에서도 문제가 없다는 뜻은 아니라는 것**입니다.

가능하면 CI 또는 기본 build matrix에 GCC와 Clang을 모두 포함합니다.

## compiler와 standard library는 별개

compiler version과 C++ standard library version은 같은 것이 아닙니다.

대표적으로 다음 조합이 가능합니다.

```text
GCC   + libstdc++
Clang + libstdc++
Clang + libc++
```

즉 Clang을 사용한다고 해서 반드시 `libc++`를 사용하는 것은 아닙니다.

이 구분은 C++ 표준 기능 지원을 판단할 때 중요합니다.

예를 들어 compiler가 C++20 문법을 이해하더라도 사용하는 standard library에 필요한 C++20 타입이나 함수가 아직 구현되지 않았을 수 있습니다.

문제가 발생하면 최소한 다음 세 경우를 구분합니다.

### 1. compiler가 문법을 이해하지 못함

예:

```text
syntax error
unknown keyword
unsupported language feature
```

이 경우는 compiler front-end 또는 선택한 `-std=` mode 문제일 가능성이 큽니다.

### 2. header에 필요한 선언이 없음

예:

```text
std::something is not a member of std
no member named ...
```

필요한 header를 빠뜨린 경우도 있지만, 해당 standard library 버전이 기능을 구현하지 않은 경우도 있습니다.

### 3. compile은 되지만 link가 실패함

예:

```text
undefined reference
symbol not found
```

header에는 선언이 존재하지만 실제 구현 library가 없거나, 잘못된 library를 link했거나, ABI가 맞지 않을 수 있습니다.

따라서 다음을 따로 기록하는 편이 좋습니다.

```text
compiler 종류와 version
standard library 종류와 version
linker / runtime library 조합
```

## Linux와 macOS

Linux와 macOS는 모두 POSIX 계열이지만 모든 system API가 같지는 않습니다.

POSIX 공통 기능과 platform 전용 기능을 구분하고, platform 전용 코드는 adapter 뒤에 숨기는 것이 좋습니다.

## readiness API

대량의 file descriptor readiness를 감시할 때 대표적으로 다음 API가 사용됩니다.

- Linux: `epoll`
- macOS/BSD: `kqueue`

두 API의 event 표현은 서로 다릅니다.

예를 들어 애플리케이션 전체가 `EPOLLIN`, `EPOLLOUT`, `EVFILT_READ`, `EV_EOF` 같은 platform bit를 직접 다루면 platform 분기가 빠르게 퍼집니다.

대신 작은 adapter가 공통 의미로 변환하게 할 수 있습니다.

```cpp
struct Event {
    bool readable;
    bool writable;
    bool hangup;
    bool error;
};
```

개념적인 구조는 다음과 같습니다.

```text
Linux epoll event
          \
           → platform adapter → Event → server core
          /
BSD/macOS kqueue event
```

이렇게 하면 server core는 운영체제별 flag보다 "읽을 수 있음", "쓸 수 있음", "연결 종료", "오류" 같은 의미만 처리합니다.

단, `epoll`과 `kqueue`의 동작을 완전히 동일한 것으로 가정하면 안 됩니다. edge-triggered 동작, EOF 표현, 등록/수정 방식처럼 세부 의미가 다를 수 있으므로 adapter 자체에 platform별 test가 필요합니다.

## SIGPIPE와 socket write

peer가 이미 닫은 socket에 `write()` 또는 `send()`를 수행하면 일부 POSIX 환경에서 `SIGPIPE`가 발생할 수 있습니다.

기본 동작을 그대로 두면 process가 종료될 수 있으므로 network server는 이 동작을 의도적으로 처리해야 합니다.

### Linux

Linux에서는 `send()` 호출에 `MSG_NOSIGNAL`을 사용할 수 있습니다.

```cpp
send(fd, buffer, size, MSG_NOSIGNAL);
```

이 flag는 해당 `send()` 호출에서 `SIGPIPE` 발생을 억제합니다.

### macOS

macOS에서는 socket에 `SO_NOSIGPIPE` option을 설정하는 방식이 일반적으로 사용됩니다.

개념적으로:

```cpp
int one = 1;
setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof(one));
```

그 뒤 해당 socket의 write에서 `SIGPIPE`가 발생하지 않도록 합니다.

두 방식은 이름과 적용 위치가 다릅니다.

```text
Linux
→ send() 호출별 MSG_NOSIGNAL

macOS
→ socket별 SO_NOSIGPIPE
```

따라서 한쪽 macro가 모든 platform에 있다고 가정해 공통 코드에서 직접 사용하지 않습니다.

예를 들어 wrapper를 둘 수 있습니다.

```cpp
ssize_t socketSend(int fd, const void *buf, size_t size);
```

wrapper 내부에서 platform별 SIGPIPE 억제 방식을 처리하면 호출자는 차이를 알 필요가 줄어듭니다.

## descriptor 검사

test나 debugging에서 "열린 file descriptor가 남았는가"를 확인하는 방법도 platform마다 다릅니다.

### Linux

Linux에서는 procfs가 mount되어 있다면 다음 경로에서 process가 열린 fd를 확인할 수 있습니다.

```text
/proc/<pid>/fd
```

현재 process라면 보통 다음도 사용할 수 있습니다.

```text
/proc/self/fd
```

### macOS

macOS에는 Linux의 `/proc/<pid>/fd`와 같은 procfs interface가 기본 제공되지 않습니다.

대신 `lsof` 같은 도구나 platform API를 사용할 수 있습니다.

따라서 test가 특정 diagnostic 기능을 요구한다면 다음처럼 처리합니다.

```text
기능 사용 가능
→ 검사 실행

기능 사용 불가
→ SKIP 기록
→ 왜 검사하지 못했는지 이유 기록
```

**검사를 실행하지 못한 상태를 PASS로 기록해서는 안 됩니다.**

`PASS`, `FAIL`, `SKIP`은 서로 다른 결과입니다.

## integer 크기와 data model

C++ 표준은 `int`, `long`, pointer가 정확히 몇 bit인지 고정하지 않습니다.

따라서 다음과 같은 코드는 portable하지 않습니다.

```cpp
// long이 항상 64-bit라고 가정하면 안 됨
long value;
```

64-bit Unix 계열에서는 흔히 `long`과 pointer가 64-bit이지만, 다른 platform에서는 다를 수 있습니다.

network protocol, file format, binary serialization처럼 **bit 폭이 protocol의 일부인 경우**에는 고정 폭 정수 타입을 사용합니다.

예:

```cpp
uint32_t length;
```

또한 network byte order를 요구하는 16-bit/32-bit 필드에는 다음 계열 함수를 사용합니다.

```cpp
htons
ntohs
htonl
ntohl
```

예:

```cpp
uint32_t host_value = 100;
uint32_t network_value = htonl(host_value);
```

### C++98에서의 고정 폭 타입

고정 폭 정수 타입은 C99의 `<stdint.h>`에서 널리 제공되지만, C++98 표준 자체가 이를 C++ standard library header로 보장하는 것은 아닙니다.

따라서 C++98 환경에서는 실제 compiler와 platform에서 `<stdint.h>` 지원 여부를 확인합니다.

여러 platform을 지원한다면 compatibility header에 차이를 모을 수 있습니다.

```cpp
// compat/stdint.hpp

#if defined(HAVE_STDINT_H)
# include <stdint.h>
#else
// 지원 platform에 맞는 typedef 제공
#endif
```

중요한 점은 임의로 `unsigned long` 등을 `uint32_t`라고 가정하지 않고, **실제 폭을 보장할 수 있을 때만 고정 폭 타입으로 정의하는 것**입니다.

## byte order

정수의 memory byte order는 CPU architecture에 따라 다를 수 있습니다.

대표적으로:

```text
little-endian
big-endian
```

network protocol은 일반적으로 network byte order를 명시하므로 host memory representation을 그대로 전송하지 않습니다.

잘못된 예:

```cpp
uint32_t value = 0x12345678;
send(fd, &value, sizeof(value), 0);
```

이 코드는 protocol이 host byte order를 허용한다는 보장이 없다면 architecture에 따라 wire format이 달라질 수 있습니다.

명시적인 변환을 사용합니다.

```cpp
uint32_t wire = htonl(value);
send(fd, &wire, sizeof(wire), 0);
```

수신 측도 반대로 변환합니다.

```cpp
uint32_t wire;
recv(fd, &wire, sizeof(wire), 0);

uint32_t value = ntohl(wire);
```

## path와 filesystem

C++17 이후 `std::filesystem::path`는 platform의 native path representation 차이를 추상화합니다. 그러나 path를 외부 API에 전달할 때 encoding과 native representation 차이가 다시 드러날 수 있습니다.

예를 들어 다음과 같은 코드가 있다고 가정합니다.

```cpp
std::filesystem::path path = ...;
some_c_api(path.string().c_str());
```

이 코드가 항상 모든 platform에서 모든 비 ASCII 경로를 올바르게 처리한다고 가정하면 안 됩니다.

특히 Windows에서는 native path가 wide-character 계열 API와 연결되는 경우가 많으므로 `path.string()`으로 변환하는 과정에서 encoding 문제가 생길 수 있습니다.

반대로 프로젝트가 Linux와 macOS만 지원하는 POSIX 프로젝트라면 지원 범위를 명시하고 다음을 기준으로 설계할 수 있습니다.

```text
지원 OS: Linux, macOS
path separator와 의미: POSIX 규칙
file I/O: file descriptor 기반 API
directory API: POSIX 계열
```

이처럼 portability는 "모든 운영체제를 지원한다"는 뜻이 아니라 **지원할 platform 범위를 명확히 정하고 그 범위에서 차이를 관리하는 것**입니다.

## sanitizer

sanitizer는 compiler 이름만 보고 지원 여부를 확정하지 않습니다.

같은 Clang 또는 GCC 계열이라도 다음에 따라 지원 여부가 달라질 수 있습니다.

- compiler version
- operating system
- architecture
- linker
- runtime library
- 다른 sanitizer와의 조합

따라서 실제 build 환경에서 작은 compile/runtime probe를 실행하는 편이 안전합니다.

예를 들어:

```text
1. sanitizer flag로 작은 프로그램 compile
2. link 성공 확인
3. 실행 가능 여부 확인
4. 필요한 경우 의도적인 오류를 넣어 실제 진단 확인
```

### ASan

AddressSanitizer는 대표적으로 다음 오류를 찾는 데 사용됩니다.

```text
heap/stack out-of-bounds
use-after-free
일부 double free
```

### UBSan

UndefinedBehaviorSanitizer는 지원되는 범위 안에서 여러 undefined behavior를 진단합니다.

예:

```text
signed integer overflow
invalid shift
misaligned access
```

어떤 검사 항목이 활성화되는지는 compiler와 option에 따라 달라질 수 있습니다.

### TSan

ThreadSanitizer는 data race 탐지에 사용됩니다.

하지만 모든 platform/architecture 조합에서 동일하게 지원되는 것은 아니며, 일반적으로 다른 sanitizer와 자유롭게 조합할 수 있다고 가정해서는 안 됩니다.

따라서 별도 test job으로 실행하는 편이 안전합니다.

### leak detection

leak detection은 ASan runtime과 함께 제공되는 경우가 많지만 platform과 runtime 구성에 따라 기본 활성화 여부가 다를 수 있습니다.

따라서 다음처럼 기록합니다.

```text
ASan: PASS
UBSan: PASS
TSan: SKIP - runtime unavailable
Leak check: SKIP - unsupported on this target
```

지원하지 않는 검사를 실행하지 못했는데 전체를 성공으로 기록하면 test coverage를 과대평가하게 됩니다.

## ABI와 compiler option

C++에서는 source가 compile된다는 사실만으로 object file끼리 안전하게 섞을 수 있는 것은 아닙니다.

**ABI(Application Binary Interface)** 는 object file과 binary library가 서로 호출할 때 따라야 하는 binary 수준의 규칙을 말합니다.

예를 들어 다음이 ABI에 영향을 줄 수 있습니다.

- symbol name mangling
- class layout
- virtual table layout
- exception runtime
- standard library 구현
- 일부 compile option
- debug iterator 설정

### 서로 다른 standard library

`libstdc++`로 build한 C++ library와 `libc++`로 build한 code를 C++ object interface에서 단순히 섞는 것은 일반적으로 안전하다고 가정할 수 없습니다.

특히 boundary에서 다음 타입을 주고받으면 문제가 커질 수 있습니다.

```text
std::string
std::vector
std::exception 파생 타입
standard library container
```

외부 prebuilt library를 사용할 때는 최소한 다음을 확인합니다.

```text
지원 compiler
compiler ABI 조건
standard library 종류
필요한 runtime
architecture
Debug/Release 조건
특수 ABI macro
```

### 같은 compiler라도 option이 중요함

같은 compiler와 standard library를 사용하더라도 일부 option은 ABI에 영향을 줄 수 있습니다.

예를 들어 구현에 따라 다음과 같은 설정이 container layout이나 iterator 표현을 변경할 수 있습니다.

```text
iterator debugging
debug container mode
ABI compatibility macro
structure packing option
```

따라서 library와 application을 서로 호환되는 option으로 build해야 합니다.

외부 binary library가 제공된다면 그 library의 build 조건을 먼저 확인하고 application 쪽 설정을 맞춥니다.

## compile-time platform 분기

platform 전용 코드는 가능한 한 작은 파일 또는 adapter에 모읍니다.

나쁜 구조:

```cpp
// 여러 business logic 파일 곳곳에 반복
#ifdef __linux__
    ...
#elif defined(__APPLE__)
    ...
#endif
```

더 나은 구조:

```text
event_poller.hpp
event_poller_epoll.cpp
event_poller_kqueue.cpp
```

공통 interface:

```cpp
class EventPoller {
public:
    virtual ~EventPoller() {}
    virtual bool add(int fd) = 0;
    virtual int wait(Event *events, int capacity) = 0;
};
```

그리고 build system이 platform에 맞는 구현 하나만 선택합니다.

```text
Linux  → event_poller_epoll.cpp
macOS  → event_poller_kqueue.cpp
```

이렇게 하면 `#if`가 core logic으로 퍼지는 것을 줄일 수 있습니다.

## signal과 process

signal은 POSIX가 공통 개념을 제공하지만 signal 번호와 일부 flag, 세부 동작은 platform마다 다를 수 있습니다.

따라서 protocol이나 file format에 signal 번호 자체를 저장하는 식의 설계는 피합니다.

예를 들어:

```text
SIGTERM의 정수값이 모든 platform에서 같다고 가정하지 않음
```

코드에서는 이름 있는 상수인 `SIGTERM`, `SIGINT` 등을 사용합니다.

platform 전용 signal 기능이 필요하다면 `#if`가 있는 작은 source file 또는 wrapper에 격리합니다.

## `fork()`와 multi-threaded process

multi-threaded process에서 `fork()`를 호출하면 child process에는 `fork()`를 호출한 thread 하나만 남습니다.

하지만 mutex나 library 내부 상태는 다른 thread가 lock한 상태로 복제될 수 있습니다.

예를 들어 parent에서 다른 thread가 다음 mutex를 잡은 순간 `fork()`가 일어났다고 가정합니다.

```text
thread A: mutex lock 보유
thread B: fork()
```

child에는 thread B만 존재합니다.

그러나 mutex state는 "lock됨"으로 복제될 수 있고, 원래 lock을 해제할 thread A는 child에 존재하지 않습니다. 이 상태에서 child가 일반적인 library 함수나 lock을 사용하면 deadlock 또는 정의하기 어려운 상태에 빠질 수 있습니다.

POSIX에서는 multi-threaded process의 `fork()` 이후 child가 `exec()`하기 전까지 호출할 수 있는 함수를 **async-signal-safe 함수로 제한하는 것이 기본 원칙**입니다.

따라서 일반적인 구조는 다음과 같습니다.

```text
parent
→ fork()

child
→ 최소한의 fd 정리
→ 필요한 async-signal-safe 작업만 수행
→ 가능한 한 즉시 exec()

parent
→ 정상적인 multi-threaded 실행 계속
```

child에서 다음과 같은 복잡한 작업은 가능한 한 피합니다.

```text
iostream 사용
malloc 기반 작업
일반적인 logging
mutex 획득
복잡한 C++ 객체 조작
```

실제 허용 함수 목록은 대상 POSIX 환경의 문서를 기준으로 확인합니다.

## architecture 차이

같은 운영체제라도 CPU architecture가 다르면 다음이 달라질 수 있습니다.

```text
pointer alignment
일부 integer alignment
atomic 지원
sanitizer 지원
assembly 코드
SIMD instruction
endianness 가능성
```

따라서 다음 두 환경은 같은 test target으로 간주하지 않는 편이 좋습니다.

```text
Linux x86_64
Linux arm64
```

특히 binary serialization, lock-free 코드, alignment 의존 코드, architecture-specific optimization이 있다면 architecture를 build matrix에 포함합니다.

## 빌드 매트릭스

최소한 다음을 기록합니다.

```text
compiler와 version
C++ standard mode
standard library
operating system과 version
CPU architecture
Debug/Release
sanitizer 사용 여부
중요 ABI/build option
```

예:

```text
GCC 14
C++20
libstdc++
Linux x86_64
Debug
ASan + UBSan
```

또는:

```text
Clang 18
C++20
libc++
macOS arm64
Release
sanitizer 없음
```

프로젝트가 모든 조합을 지원할 필요는 없습니다.

중요한 것은 다음을 구분하는 것입니다.

```text
지원하며 test함
지원하지만 일부 검사 SKIP
지원하지 않음
아직 확인하지 않음
```

"확인하지 않음"을 "지원함"으로 기록하지 않습니다.

## 문제를 분류하는 순서

platform 차이로 보이는 문제가 생기면 다음 순서로 확인하면 원인 분리에 도움이 됩니다.

1. **언어 문법 문제인지 확인합니다.**
   - `-std=` mode
   - compiler version
   - compiler extension 사용 여부

2. **standard library 문제인지 확인합니다.**
   - 필요한 header
   - libstdc++ / libc++
   - library version

3. **link와 ABI 문제인지 확인합니다.**
   - 필요한 library link 여부
   - external binary ABI
   - Debug/Release 및 ABI option

4. **운영체제 API 차이인지 확인합니다.**
   - `epoll` / `kqueue`
   - SIGPIPE 처리
   - filesystem / process API

5. **architecture 차이인지 확인합니다.**
   - integer 폭
   - alignment
   - byte order
   - sanitizer/runtime 지원

6. **실제 test에서 재현합니다.**
   - compile probe
   - link probe
   - runtime probe
   - unsupported 환경은 `SKIP`으로 기록

## 완료 기준

- compiler와 standard library가 서로 독립적인 구성 요소임을 설명할 수 있습니다.
- 문법 오류, header/library 기능 부재, link 오류를 구분할 수 있습니다.
- GCC와 Clang에서 warning 결과가 다를 수 있음을 전제로 build합니다.
- Linux `epoll`과 BSD/macOS `kqueue` 코드를 작은 adapter로 분리합니다.
- Linux `MSG_NOSIGNAL`과 macOS `SO_NOSIGPIPE`의 적용 방식 차이를 설명할 수 있습니다.
- platform별 fd 검사 방법을 구분하고 실행할 수 없는 검사는 `SKIP`으로 기록합니다.
- protocol integer 폭과 host integer 크기를 구분하고 byte order를 명시적으로 변환합니다.
- C++98에서 고정 폭 정수 타입 지원 여부를 platform별로 확인합니다.
- sanitizer를 compiler 이름만 보고 가정하지 않고 실제 compile/runtime probe 뒤에 실행합니다.
- 실행하지 못한 platform 검사를 성공으로 보고하지 않습니다.
- external library의 compiler, standard library, ABI와 build option 호환성을 확인합니다.
- platform 전용 `#if`가 core logic 전체로 퍼지지 않도록 격리합니다.
- multi-threaded process에서 `fork()` 이후 child가 일반적인 C++ runtime 작업을 수행하면 위험한 이유를 설명할 수 있습니다.
- 운영체제뿐 아니라 CPU architecture도 build/test 조건의 일부로 기록합니다.
