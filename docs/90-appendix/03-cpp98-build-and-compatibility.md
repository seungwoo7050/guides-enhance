# C++98 빌드와 호환성

## 목적

C++98 프로젝트가 최신 compiler의 기본 모드나 저장소 루트 도구에 우연히 의존하지 않게 합니다. 프로젝트 하나만 다른 디렉터리로 복사해도 build와 test를 실행할 수 있어야 합니다.

## 기본 compiler option

```make
CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -pedantic
CPPFLAGS := -Iinclude
```

- `CPPFLAGS`: include path와 preprocessor define
- `CXXFLAGS`: 언어 표준, warning, 최적화
- `LDFLAGS`: link 단계 option
- `LDLIBS`: `-lpthread` 같은 library

compile option과 link library를 한 변수에 섞지 않습니다.

## 여러 source build

작은 프로젝트는 한 command로 link할 수 있지만 파일이 늘어나면 object dependency를 분리합니다.

```make
OBJ_DIR := build/obj
SOURCES := src/main.cpp src/Store.cpp src/Parser.cpp
OBJECTS := $(SOURCES:src/%.cpp=$(OBJ_DIR)/%.o)

$(OBJ_DIR)/%.o: src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@
```

header dependency 파일을 생성하려면 compiler의 `-MMD -MP`를 사용할 수 있습니다. 단, 사용하는 compiler가 option을 지원하는지 확인합니다.

## template build

template 정의는 호출 위치에서 보여야 하므로 header에 둡니다. `.cpp`로 분리하려면 사용할 타입을 명시적으로 instantiation해야 합니다.

```cpp
template class Array<int>;
template class Array<std::string>;
```

지원 타입이 늘어날 때마다 목록을 수정해야 하므로 일반 container는 header 정의가 보통 더 적합합니다.

## POSIX library

thread를 사용하면 platform에 맞게 thread option을 link합니다.

```make
CXXFLAGS += -pthread
LDLIBS += -pthread
```

일부 compiler는 compile과 link 모두 `-pthread`가 필요합니다. 단순 `-lpthread`와 의미가 같다고 가정하지 않습니다.

socket API는 일반적으로 별도 library가 필요 없지만 Windows는 다른 API와 초기화가 필요하므로 이 가이드의 POSIX 프로젝트 범위 밖입니다.

## platform source 선택

`epoll`과 `kqueue` 구현을 함께 source 목록에 넣고 각 파일을 preprocessor로 감쌀 수 있습니다.

```cpp
#if defined(__linux__)
// epoll implementation
#endif
```

또는 Makefile에서 `uname` 결과로 하나만 선택할 수 있습니다. 어느 방식을 쓰든 현재 platform에서 factory 정의가 정확히 하나 생겨야 합니다.

지원하지 않는 platform에서는 link 오류보다 명확한 compile 오류를 내는 편이 낫습니다.

## Debug와 sanitizer

```make
sanitize: CXXFLAGS += -O1 -g -fsanitize=address,undefined
sanitize: LDFLAGS += -fsanitize=address,undefined
sanitize: clean all test
```

sanitizer option은 compile과 link에 모두 필요합니다. 일반 build object와 sanitizer object를 같은 경로에 섞지 않는 편이 안전합니다.

ThreadSanitizer는 별도 target과 build 결과를 사용합니다.

## compile-fail test

const 위반이나 지원하지 않는 타입 사용처럼 컴파일되지 않아야 하는 코드는 별도 파일로 둡니다.

```sh
if c++ -std=c++98 compile_fail/modify_const.cpp; then
    echo "unexpected compile success" >&2
    exit 1
fi
```

compiler 진단 문구 전체에 의존하지 않고 실패 여부를 확인합니다.

## standalone 검사

```sh
cp -R exercises/command-service /tmp/command-service
cd /tmp/command-service
make clean
make test
```

다음 의존성이 없어야 합니다.

- 저장소 루트 Makefile
- sibling exercise header
- 숨겨진 reference 구현
- 절대 경로
- 이전 build 결과

## clean target

`clean`은 project가 직접 만든 실행 파일과 object만 지웁니다. 사용자 입력 파일이나 source를 wildcard로 넓게 삭제하지 않습니다.

빌드 결과를 ZIP이나 Git에 넣지 않습니다.

## 호환성 점검

- GCC와 Clang 중 가능한 compiler에서 build
- Linux/macOS 전용 source 분리
- C++11 이후 문법 검색
- `-std=c++98 -pedantic` build
- project-local test
- 가능하면 ASan/UBSan
- 다른 디렉터리에서 standalone build

## 완료 기준

- C++98 표준 모드를 모든 target에 적용합니다.
- compile, link option과 library를 구분합니다.
- template 정의 위치와 explicit instantiation을 설명합니다.
- platform별 source에서 factory 정의가 하나만 생깁니다.
- sanitizer build 결과를 일반 build와 분리합니다.
- 프로젝트만 복사해도 README 명령으로 build와 test가 됩니다.
