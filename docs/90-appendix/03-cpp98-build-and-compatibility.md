# C++98 빌드와 호환성

## 목적

C++98 프로젝트가 최신 compiler의 기본 language mode, 저장소 루트의 공용 build script, 다른 exercise의 header, 이전 build 결과 같은 **암묵적 환경**에 우연히 의존하지 않게 합니다.

프로젝트 디렉터리 하나만 다른 위치로 복사해도 문서에 적힌 명령만으로 다음이 가능해야 합니다.

```text
clean build
→ test
→ 필요하면 sanitizer build
```

핵심 원칙은 다음과 같습니다.

- 모든 C++ compile에 C++98 mode를 명시합니다.
- compile option, preprocessor option, link option, library를 역할별로 구분합니다.
- source와 header dependency를 build system이 정확히 추적하게 합니다.
- platform별 구현은 정확히 하나만 선택되게 합니다.
- 일반 build와 sanitizer build 결과를 섞지 않습니다.
- 저장소 외부에서도 독립적으로 build/test할 수 있게 합니다.

## 기본 compiler option

Makefile에서는 보통 다음 변수를 역할별로 구분합니다.

```make
CXX ?= c++

CPPFLAGS += -Iinclude
CXXFLAGS += -std=c++98 -Wall -Wextra -Werror -pedantic
```

각 변수의 역할은 다음과 같습니다.

| 변수 | 주 용도 |
| --- | --- |
| `CPPFLAGS` | include path, preprocessor macro (`-I`, `-D`) |
| `CXXFLAGS` | C++ language mode, warning, optimization, debug 정보 |
| `LDFLAGS` | linker 자체에 전달할 option, library search path 등 |
| `LDLIBS` | link할 library 또는 library 관련 option |

예:

```make
CPPFLAGS += -Iinclude -DPROJECT_POSIX
CXXFLAGS += -std=c++98 -Wall -Wextra -Werror -pedantic
LDFLAGS  += -Lvendor/lib
LDLIBS   += -pthread
```

실제 compile command:

```make
$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c source.cpp -o source.o
```

실제 link command:

```make
$(CXX) $(LDFLAGS) objects... $(LDLIBS) -o program
```

compile option과 link library를 한 변수에 모두 넣어도 우연히 동작할 수 있지만, 역할이 섞이면 target별 option 조정과 문제 추적이 어려워집니다.

## `?=`와 필수 option

다음과 같이 작성할 때는 주의해야 합니다.

```make
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
```

`?=`는 변수가 아직 정의되지 않았을 때만 값을 설정합니다.

따라서 사용자가 다음처럼 실행하면:

```sh
make CXXFLAGS=-O2
```

Makefile의 C++98 mode와 warning option이 모두 사라집니다.

```text
실제 CXXFLAGS
→ -O2
```

그러면 프로젝트가 더 이상 `-std=c++98`로 build된다고 보장할 수 없습니다.

C++98 mode처럼 프로젝트가 반드시 요구하는 option은 별도 변수로 두는 편이 명확합니다.

```make
CXX ?= c++

PROJECT_CPPFLAGS := -Iinclude
PROJECT_CXXFLAGS := -std=c++98 -Wall -Wextra -Werror -pedantic

CPPFLAGS += $(PROJECT_CPPFLAGS)
CXXFLAGS += $(PROJECT_CXXFLAGS)
```

또는 compile rule에서 필수 option을 직접 추가할 수도 있습니다.

중요한 점은 **사용자가 optimization 같은 option을 추가할 수 있게 하면서도 프로젝트가 요구하는 C++98 mode는 사라지지 않게 하는 것**입니다.

## 한 파일 build와 여러 source build

source가 하나뿐인 작은 프로그램은 한 command로 compile과 link를 함께 수행할 수 있습니다.

```sh
c++ -std=c++98 -Wall -Wextra -Werror -pedantic \
    src/main.cpp -o app
```

하지만 source가 늘어나면 각 `.cpp`를 object file로 따로 compile하고 마지막에 link하는 구조가 적합합니다.

예:

```make
NAME := app

OBJ_DIR := build/obj

SOURCES := \
	src/main.cpp \
	src/Store.cpp \
	src/Parser.cpp

OBJECTS := $(SOURCES:src/%.cpp=$(OBJ_DIR)/%.o)

$(NAME): $(OBJECTS)
	$(CXX) $(LDFLAGS) $(OBJECTS) $(LDLIBS) -o $@

$(OBJ_DIR)/%.o: src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@
```

의존 관계는 다음과 같습니다.

```text
main.cpp   → main.o
Store.cpp  → Store.o
Parser.cpp → Parser.o

main.o + Store.o + Parser.o
→ app
```

이 구조에서는 변경된 source만 다시 compile할 수 있습니다.

## header dependency

단순한 pattern rule만 사용하면 `.cpp`가 변경되었을 때는 rebuild되지만, 포함된 header가 변경되었을 때 object를 자동으로 다시 만들지 못할 수 있습니다.

예:

```text
Store.cpp
  └─ #include "Store.hpp"

Store.hpp 변경
→ Store.o도 다시 compile해야 함
```

GCC와 Clang 계열에서는 `-MMD -MP`를 이용해 dependency file을 생성할 수 있습니다.

```make
DEPFLAGS := -MMD -MP

$(OBJ_DIR)/%.o: src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(DEPFLAGS) -c $< -o $@
```

각 object 옆에 `.d` 파일이 만들어진다고 가정하면:

```make
DEPS := $(OBJECTS:.o=.d)

-include $(DEPS)
```

전체 예시는 다음과 같습니다.

```make
NAME := app

OBJ_DIR := build/obj

SOURCES := \
	src/main.cpp \
	src/Store.cpp \
	src/Parser.cpp

OBJECTS := $(SOURCES:src/%.cpp=$(OBJ_DIR)/%.o)
DEPS := $(OBJECTS:.o=.d)

$(NAME): $(OBJECTS)
	$(CXX) $(LDFLAGS) $(OBJECTS) $(LDLIBS) -o $@

$(OBJ_DIR)/%.o: src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MMD -MP -c $< -o $@

-include $(DEPS)
```

`-MMD`와 `-MP`는 ISO C++ 기능이 아니라 compiler option입니다. 따라서 프로젝트가 GCC/Clang 계열을 지원한다는 전제에서 사용하거나, 다른 compiler도 지원한다면 capability를 확인해야 합니다.

## template build

C++ template은 일반 함수와 달리 **사용되는 타입에 대한 정의가 instantiation 시점에 보여야 합니다.**

예를 들어 header에 선언만 있고:

```cpp
// Array.hpp

template <typename T>
class Array {
public:
    T &at(unsigned int index);
};
```

정의를 `.cpp`에만 두면:

```cpp
// Array.cpp

template <typename T>
T &Array<T>::at(unsigned int index)
{
    // ...
}
```

다른 translation unit에서 `Array<int>`를 사용해도 compiler가 해당 정의를 보지 못해 필요한 specialization을 생성할 수 없습니다.

따라서 일반적인 template library는 정의까지 header에 둡니다.

```cpp
// Array.hpp

template <typename T>
class Array {
public:
    T &at(unsigned int index);
};

template <typename T>
T &Array<T>::at(unsigned int index)
{
    // ...
}
```

또는 implementation을 별도 파일에 두되 header 끝에서 포함할 수도 있습니다.

```cpp
#include "Array.tpp"
```

중요한 것은 file extension 자체가 아니라 **template 정의가 instantiation 지점에 보인다는 것**입니다.

## explicit instantiation

template 정의를 `.cpp`에 숨기고 싶다면 사용할 타입을 명시적으로 instantiation하는 방법이 있습니다.

예:

```cpp
// Array.cpp

#include "Array.hpp"
#include <string>

// template 정의 ...

template class Array<int>;
template class Array<std::string>;
```

이 구조에서는 library가 실제로 제공할 specialization이 미리 정해집니다.

```text
지원:
Array<int>
Array<std::string>

지원 목록에 없음:
Array<double>
```

새 타입을 지원하려면 explicit instantiation 목록도 수정해야 합니다.

따라서 임의 타입을 받아야 하는 일반 container나 algorithm template은 header에 정의를 두는 방식이 보통 더 자연스럽습니다.

## POSIX thread option

POSIX thread를 사용하는 프로그램은 compiler/toolchain이 요구하는 thread option을 compile과 link에 적용해야 합니다.

GCC와 Clang 계열에서는 일반적으로 `-pthread`를 사용합니다.

```make
CXXFLAGS += -pthread
LDLIBS   += -pthread
```

`-pthread`는 단순히 `libpthread` 하나를 link한다는 의미로만 생각하면 안 됩니다.

toolchain에 따라 compile 단계에서 thread 관련 macro나 code-generation 조건에도 영향을 줄 수 있으므로:

```text
-pthread
≠ 항상 단순한 -lpthread 치환
```

이라고 생각하는 편이 안전합니다.

실제 toolchain이 요구하는 방식을 기준으로 합니다.

## socket library

Linux/macOS 같은 일반적인 POSIX 환경에서는 BSD socket API 사용 때문에 별도의 socket library를 추가할 필요가 없는 경우가 많습니다.

예:

```cpp
socket
bind
listen
accept
connect
send
recv
```

하지만 모든 운영체제가 같은 build model을 사용하는 것은 아닙니다.

Windows는 Winsock API와 별도 초기화/build 조건이 있으므로 이 문서의 POSIX 프로젝트 범위 밖으로 둡니다.

즉 다음을 명확히 합니다.

```text
지원 범위:
Linux/macOS 등 대상 POSIX 환경

지원 범위 밖:
Windows 전용 socket build
```

## platform source 선택

Linux와 macOS/BSD에서 readiness API 구현을 나눌 수 있습니다.

예:

```text
src/poller_epoll.cpp
src/poller_kqueue.cpp
```

공통 interface는 header에 둡니다.

```cpp
class Poller {
public:
    virtual ~Poller() {}
    virtual bool add(int fd) = 0;
    virtual int wait() = 0;
};

Poller *createPoller();
```

중요한 invariant는 다음과 같습니다.

```text
최종 executable 하나에
createPoller() 정의가 정확히 하나 존재
```

## 방법 1: source 내부 `#if`

두 파일을 모두 source 목록에 넣고 각 구현을 platform macro로 감쌀 수 있습니다.

```cpp
// poller_epoll.cpp

#if defined(__linux__)

// Linux implementation
Poller *createPoller()
{
    // ...
}

#endif
```

```cpp
// poller_kqueue.cpp

#if defined(__APPLE__) || defined(__FreeBSD__)

// kqueue implementation
Poller *createPoller()
{
    // ...
}

#endif
```

장점:

```text
source 목록이 단순함
```

주의할 점:

```text
macro 조건이 잘못되면
→ factory 정의 0개
→ link failure

조건이 겹치면
→ factory 정의 여러 개
→ duplicate symbol
```

지원하지 않는 platform에서는 이를 우연한 link 오류로 발견하기보다 명시적인 compile error로 만드는 편이 낫습니다.

예:

```cpp
#if !defined(__linux__) && \
    !defined(__APPLE__) && \
    !defined(__FreeBSD__)
# error Unsupported platform
#endif
```

## 방법 2: Makefile에서 source 선택

build system에서 현재 target platform에 맞는 구현 하나만 source 목록에 넣을 수도 있습니다.

간단한 native build에서는 다음처럼 할 수 있습니다.

```make
UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Linux)
	SOURCES += src/poller_epoll.cpp
else ifeq ($(UNAME_S),Darwin)
	SOURCES += src/poller_kqueue.cpp
else
	$(error Unsupported platform: $(UNAME_S))
endif
```

이 경우 compile되지 않는 platform source 자체가 build에서 제외됩니다.

## `uname`의 한계와 cross compilation

`uname`은 **build를 실행하는 host 운영체제**를 알려줍니다.

그러나 cross compilation에서는 host와 실제 target이 다를 수 있습니다.

```text
host:
Linux x86_64

target:
다른 architecture / 다른 platform
```

이 경우 `uname`만으로 target source를 선택하면 잘못된 구현을 고를 수 있습니다.

cross compilation 가능성이 있다면 platform을 명시적인 build variable이나 toolchain 설정에서 받는 편이 안전합니다.

예:

```make
PLATFORM ?= linux

ifeq ($(PLATFORM),linux)
	SOURCES += src/poller_epoll.cpp
else ifeq ($(PLATFORM),macos)
	SOURCES += src/poller_kqueue.cpp
else
	$(error Unsupported PLATFORM=$(PLATFORM))
endif
```

native build만 지원한다면 `uname` 사용도 충분할 수 있지만, 그 전제를 README에 적습니다.

## Debug와 Release

Debug와 Release는 목적이 다릅니다.

예:

```make
DEBUG_CXXFLAGS := -O0 -g
RELEASE_CXXFLAGS := -O2
```

Debug build:

```text
debug symbol 포함
최적화 최소화
debugger 사용 용이
```

Release build:

```text
최적화 활성화
실제 배포 조건에 가까움
```

한 object directory를 서로 다른 flag로 재사용하면 stale object가 섞일 수 있습니다.

예:

```text
build/obj/Store.o
```

이 파일이 Debug인지 Release인지 파일명만으로 구분되지 않습니다.

따라서 build directory를 분리하면 안전합니다.

```text
build/debug/obj
build/release/obj
build/asan/obj
build/tsan/obj
```

## sanitizer build

AddressSanitizer와 UndefinedBehaviorSanitizer를 사용하는 예:

```make
SAN_FLAGS := -O1 -g -fsanitize=address,undefined

sanitize: CXXFLAGS += $(SAN_FLAGS)
sanitize: LDFLAGS  += -fsanitize=address,undefined
```

sanitizer instrumentation은 compile 단계에서 object에 들어가고, sanitizer runtime은 link 단계에도 필요하므로 일반적으로 compile과 link 양쪽에 관련 option이 필요합니다.

그러나 다음처럼 단순히 target-specific flag만 추가한 뒤 기존 object directory를 공유하면 문제가 생길 수 있습니다.

```text
먼저 일반 build
→ build/obj/*.o 생성

그 뒤 sanitize
→ make가 object를 이미 최신이라고 판단
→ sanitizer 없이 compile된 object를 재사용할 가능성
```

그래서 sanitizer용 object directory를 별도로 두는 편이 안전합니다.

```text
build/normal/obj
build/asan/obj
```

## sanitizer target과 `clean`

다음 형태는 간단한 프로젝트에서는 사용할 수 있습니다.

```make
sanitize: clean
sanitize: CXXFLAGS += -O1 -g -fsanitize=address,undefined
sanitize: LDFLAGS  += -fsanitize=address,undefined
sanitize: all test
```

하지만 `clean`에 의존해 build mode를 구분하면 다음 단점이 있습니다.

- mode 전환마다 전체 rebuild가 필요함
- 서로 다른 build를 동시에 보관할 수 없음
- parallel invocation이나 CI artifact 관리가 복잡해짐

가능하면 mode별 build directory를 사용하는 것이 더 명확합니다.

## ThreadSanitizer

ThreadSanitizer는 ASan/UBSan과 별도 target으로 두는 것이 좋습니다.

예:

```text
make asan
make tsan
```

각각 별도 object/output directory를 사용합니다.

```text
build/asan/
build/tsan/
```

모든 sanitizer 조합이 모든 compiler/platform에서 지원된다고 가정하지 않습니다. 실제 환경에서 compile/link/runtime 가능 여부를 확인하고, 지원하지 않는 경우 test 결과를 `SKIP`으로 구분합니다.

## compile-fail test

일부 코드는 **compile되지 않는 것이 올바른 결과**입니다.

예:

- `const` 객체 수정
- private copy constructor 사용
- 지원하지 않는 template instantiation
- 허용하지 않는 conversion

이런 코드는 정상 test source와 분리합니다.

```text
tests/
  compile_fail/
    modify_const.cpp
    copy_noncopyable.cpp
```

기본 검사는 다음과 같이 작성할 수 있습니다.

```sh
if c++ -std=c++98 -Wall -Wextra -Werror -pedantic \
    -c tests/compile_fail/modify_const.cpp \
    -o /tmp/modify_const.o
then
    echo "unexpected compile success" >&2
    exit 1
fi
```

여기서 `-c`가 중요합니다.

## compile-fail test에서 `-c`가 중요한 이유

다음처럼 `-c` 없이 실행하면:

```sh
c++ -std=c++98 compile_fail/modify_const.cpp
```

source compilation은 성공했지만 `main()`이 없어서 link가 실패할 수도 있습니다.

그런데 script가 단순히 "command가 실패했다"만 검사하면:

```text
실제 결과:
compile 성공
link 실패

test 판정:
expected compile failure → PASS
```

라는 잘못된 성공이 생길 수 있습니다.

compile-fail test는 반드시 **compile 단계만 검사**해야 합니다.

```sh
c++ ... -c file.cpp -o object.o
```

그러면 실패가 실제 compiler 진단 때문인지 확인하기 쉬워집니다.

## diagnostic 문구에 과도하게 의존하지 않기

GCC와 Clang은 같은 오류도 다른 문구로 출력할 수 있습니다.

따라서 기본 compile-fail test는 다음만 확인하는 편이 portable합니다.

```text
compile 성공 → FAIL
compile 실패 → PASS
```

특정 종류의 오류까지 확인해야 한다면 diagnostic 일부를 검사할 수 있지만, 그때는 compiler별 차이를 감안해야 합니다.

compiler message 전체 문자열과 정확히 일치시키는 test는 매우 깨지기 쉽습니다.

## test executable의 exit status

runtime test도 출력 문자열만 보는 것보다 exit status를 명확하게 사용하는 편이 좋습니다.

```sh
./tests/run_tests
status=$?

if [ "$status" -ne 0 ]; then
    echo "tests failed" >&2
    exit "$status"
fi
```

관례적으로:

```text
0     → 성공
non-0 → 실패
```

를 사용합니다.

test가 platform 기능을 사용할 수 없어 실행되지 않은 경우에는 test harness 차원에서 `SKIP`을 별도로 기록할 수 있습니다.

## standalone 검사

프로젝트가 저장소 루트에 우연히 의존하는지 확인하려면 실제로 프로젝트 하나만 복사해 봅니다.

예:

```sh
tmp_dir="$(mktemp -d)"
cp -R exercises/command-service "$tmp_dir/command-service"

cd "$tmp_dir/command-service"

make clean
make
make test
```

또는 README에서 `make test`가 build까지 포함한다고 정의했다면:

```sh
make clean
make test
```

만으로 검증합니다.

standalone 검사에서는 다음 의존성이 없어야 합니다.

- 저장소 루트 Makefile
- 부모 디렉터리의 helper script
- sibling exercise header
- sibling source
- 숨겨진 reference 구현
- 개발자 machine의 절대 경로
- 이전 build 결과
- repository root를 기준으로만 동작하는 상대 경로

## 상대 경로와 working directory

test script가 다음처럼 작성되어 있다고 가정합니다.

```sh
./bin/server
```

이 명령은 script가 항상 project root에서 실행된다는 전제가 있습니다.

하지만 다른 디렉터리에서 script를 직접 호출하면 실패할 수 있습니다.

```sh
cd /tmp
/path/to/project/tests/run.sh
```

test script가 자신의 위치를 기준으로 project root를 계산하도록 만들면 더 robust합니다.

POSIX shell 예:

```sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

"$PROJECT_DIR/bin/server"
```

프로젝트가 "반드시 root에서 실행한다"는 규칙을 채택할 수도 있습니다. 어느 쪽이든 실행 조건을 README와 script에서 일치시킵니다.

## clean target

`clean`은 **프로젝트가 직접 생성한 build artifact만 삭제**해야 합니다.

예:

```make
clean:
	rm -rf build
```

필요하다면 executable까지 지우는 별도 target을 둘 수 있습니다.

```make
fclean: clean
	rm -f $(NAME)
```

주의할 점은 wildcard 삭제 범위를 불필요하게 넓히지 않는 것입니다.

위험한 형태의 예:

```make
clean:
	rm -rf *
```

또는 source와 사용자 입력이 섞인 directory에서 넓은 wildcard를 사용하는 것 역시 위험합니다.

가능하면 생성물을 전용 directory 아래에 모읍니다.

```text
build/
bin/
```

그러면 `clean`이 단순하고 안전해집니다.

## build artifact를 source와 분리하기

object, dependency file, sanitizer 결과, test temporary file을 source directory와 섞지 않는 편이 좋습니다.

권장 구조 예:

```text
project/
├── include/
├── src/
├── tests/
├── build/
│   ├── debug/
│   ├── release/
│   ├── asan/
│   └── tsan/
├── Makefile
└── README.md
```

이 구조의 장점은 다음과 같습니다.

```text
clean 범위가 명확함
build mode 충돌 감소
Git ignore가 단순함
standalone copy 검사가 쉬움
```

## Git과 배포 파일

일반적으로 다음 build artifact는 source repository에 넣지 않습니다.

```text
*.o
*.d
실행 파일
sanitizer 결과
temporary test output
```

예:

```gitignore
build/
bin/
```

다만 과제 제출 형식이나 배포 요구가 executable을 포함하도록 명시한다면 그 규칙을 따릅니다.

핵심은 "build 결과를 항상 넣지 않는다"가 아니라 **source와 생성물의 책임을 명확히 구분하는 것**입니다.

## C++11 이후 문법 탐지

C++98 프로젝트에서는 최신 compiler가 extension이나 기본 mode로 최신 문법을 받아들이지 않게 해야 합니다.

가장 중요한 검사는 실제 C++98 strict build입니다.

```sh
c++ -std=c++98 -Wall -Wextra -Werror -pedantic ...
```

단순 text search는 보조 수단으로 사용할 수 있습니다.

예를 들어 다음 키워드를 검색할 수 있습니다.

```text
auto
nullptr
override
noexcept
constexpr
decltype
```

그러나 text search에는 false positive가 있습니다.

예:

```cpp
// comment: nullptr
std::string text = "auto";
```

따라서 검색은 "의심 위치 찾기"에 사용하고 최종 판정은 compiler에 맡깁니다.

## Makefile target 전체에 C++98 적용하기

`all` target만 C++98로 build하고 test helper나 tool target은 compiler 기본 mode를 사용하는 실수가 생길 수 있습니다.

예:

```text
app
test binary
benchmark
compile-fail test
utility executable
```

프로젝트가 C++98 호환을 요구한다면 **C++ source를 compile하는 모든 관련 target**에 동일한 language mode 원칙을 적용해야 합니다.

이를 위해 공통 compile rule이나 공통 flag 변수를 사용하는 편이 좋습니다.

```make
PROJECT_CXXFLAGS := -std=c++98 -Wall -Wextra -Werror -pedantic
```

## example Makefile 구조

작은 POSIX C++98 프로젝트라면 다음처럼 구성할 수 있습니다.

```make
NAME := command-service

CXX ?= c++

PROJECT_CPPFLAGS := -Iinclude
PROJECT_CXXFLAGS := -std=c++98 -Wall -Wextra -Werror -pedantic

CPPFLAGS += $(PROJECT_CPPFLAGS)
CXXFLAGS += $(PROJECT_CXXFLAGS)

OBJ_DIR := build/obj

SOURCES := \
	src/main.cpp \
	src/Store.cpp \
	src/Parser.cpp

OBJECTS := $(SOURCES:src/%.cpp=$(OBJ_DIR)/%.o)
DEPS := $(OBJECTS:.o=.d)

.PHONY: all clean fclean re test

all: $(NAME)

$(NAME): $(OBJECTS)
	$(CXX) $(LDFLAGS) $(OBJECTS) $(LDLIBS) -o $@

$(OBJ_DIR)/%.o: src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MMD -MP -c $< -o $@

-include $(DEPS)

test: $(NAME)
	./tests/run.sh

clean:
	rm -rf build

fclean: clean
	rm -f $(NAME)

re: fclean all
```

이 예시는 구조를 보여주기 위한 것입니다.

프로젝트에 pthread나 platform source 선택이 필요하다면 해당 설정을 추가합니다.

## 호환성 점검 순서

1. **clean 상태를 만듭니다.**

   ```sh
   make fclean
   ```

2. **C++98 strict build를 실행합니다.**

   ```text
   -std=c++98
   -Wall
   -Wextra
   -Werror
   -pedantic
   ```

3. **가능하면 GCC와 Clang에서 각각 build합니다.**

4. **모든 test executable과 helper도 C++98 mode로 compile되는지 확인합니다.**

5. **Linux/macOS platform source가 정확히 하나 선택되는지 확인합니다.**

6. **header를 변경했을 때 필요한 object가 rebuild되는지 확인합니다.**

7. **compile-fail test가 compile 단계 실패를 실제로 검사하는지 확인합니다.**

8. **ASan/UBSan build를 일반 object와 분리해 실행합니다.**

9. **ThreadSanitizer가 필요하면 별도 build와 target으로 실행합니다.**

10. **프로젝트 하나만 임시 디렉터리로 복사해 build/test합니다.**

11. **build artifact 없이 README 명령만으로 다시 시작할 수 있는지 확인합니다.**

## 완료 기준

- C++98 표준 모드가 application뿐 아니라 관련 C++ compile target 전체에 적용됩니다.
- 외부 `CXXFLAGS` 설정 때문에 필수 `-std=c++98` option이 우연히 사라지지 않습니다.
- `CPPFLAGS`, `CXXFLAGS`, `LDFLAGS`, `LDLIBS`의 역할을 구분합니다.
- 여러 source를 object 단위로 compile하고 마지막에 link할 수 있습니다.
- header 변경이 필요한 object rebuild로 이어지도록 dependency를 추적합니다.
- template 정의가 instantiation 시점에 보여야 하는 이유를 설명할 수 있습니다.
- header 정의와 explicit instantiation 방식의 차이를 설명할 수 있습니다.
- pthread 사용 시 toolchain의 thread option을 compile/link 양쪽에서 올바르게 적용합니다.
- platform별 implementation에서 factory 정의가 최종 binary에 정확히 하나 존재합니다.
- native build의 `uname` 판정과 cross-compilation의 target 판정을 구분합니다.
- Debug, Release, ASan, TSan build 결과를 필요에 따라 별도 directory로 분리합니다.
- sanitizer option이 compile과 link 모두에 필요한 이유를 설명할 수 있습니다.
- compile-fail test가 단순 link failure를 compile failure로 오판하지 않습니다.
- compiler diagnostic 전체 문자열에 과도하게 의존하지 않습니다.
- `clean`이 project가 생성한 artifact만 안전하게 삭제합니다.
- C++11 이후 문법 검색을 보조 검사로 사용하고 최종 호환성은 strict compiler build로 확인합니다.
- 프로젝트만 다른 디렉터리에 복사해도 README 명령으로 clean build와 test를 실행할 수 있습니다.
