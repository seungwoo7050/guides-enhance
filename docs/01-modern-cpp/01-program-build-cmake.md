# Modern C++ 프로그램·빌드·CMake

## 목표

C++ source가 실행 파일이 되는 과정을 단계별로 구분하고, library·application·test를 각각 독립적인 CMake target으로 구성합니다. CMake 명령을 많이 외우는 것보다 다음 질문에 답할 수 있는 것이 중요합니다.

- 어느 `.cpp`가 어느 target에 포함됩니까?
- 공개 헤더를 include하는 데 필요한 경로와 의존성은 누가 제공합니까?
- C++ 표준과 compiler warning은 어느 target에 적용됩니까?
- compile 오류와 link 오류는 어느 단계에서 발생하며, 무엇을 먼저 확인해야 합니까?

이 질문에 답할 수 있으면 빌드 오류가 발생했을 때 문제를 source code, target 구성, dependency 설정 중 어디에서 찾아야 하는지 빠르게 좁힐 수 있습니다.

---

## source에서 실행 파일까지

C++ 프로그램은 일반적으로 다음 단계를 거쳐 만들어집니다.

```text
source/header
    ↓ 전처리
translation unit
    ↓ compile
object file
    ↓ link
executable 또는 library
```

실제 compiler driver는 여러 단계를 한 명령으로 실행할 수 있지만, 오류를 분석할 때는 각 단계를 구분해서 생각해야 합니다.

### 번역 단위

compiler는 프로젝트의 모든 `.cpp`를 한꺼번에 하나의 프로그램으로 읽지 않습니다. 각 `.cpp`를 기준으로, 그 파일이 `#include`한 헤더의 내용까지 전처리한 결과를 하나의 **번역 단위(translation unit)** 로 처리합니다.

예를 들어 다음과 같은 프로젝트가 있다고 가정합니다.

```text
app/main.cpp
src/job.cpp
include/job.hpp
```

`main.cpp`와 `job.cpp`가 모두 `job.hpp`를 include하더라도 두 `.cpp`는 서로 다른 번역 단위입니다.

```text
main.cpp + 포함된 headers
    → translation unit
    → main.o

job.cpp + 포함된 headers
    → translation unit
    → job.o

main.o + job.o
    → linker
    → executable
```

따라서 `main.cpp`를 compile하는 동안 compiler는 일반적으로 `job.cpp`의 구현을 직접 보지 않습니다. `main.cpp`에서는 `job.hpp`에 적힌 선언을 보고 호출이 올바른지만 검사하고, 실제 함수 정의를 찾는 작업은 나중의 link 단계에서 이루어집니다.

---

## compile 오류와 link 오류

### compile 오류

compile 오류는 하나의 번역 단위를 object file로 만들지 못했을 때 발생합니다. 대표적인 원인은 다음과 같습니다.

- 문법이 잘못되었습니다.
- 이름이 선언되지 않았습니다.
- 타입이 맞지 않습니다.
- 필요한 헤더를 include하지 않았습니다.
- template 인스턴스화 중 타입 조건을 만족하지 못했습니다.

예:

```cpp
int main() {
    std::vector<int> values;
}
```

`<vector>`를 include하지 않았다면 compiler는 `std::vector`를 알 수 없으므로 compile 단계에서 실패합니다.

### link 오류

link 오류는 각 `.cpp`의 compile은 성공했지만, object file과 library를 최종 결과물로 결합하지 못했을 때 발생합니다.

대표적인 원인은 다음과 같습니다.

- 선언된 함수나 변수의 정의를 찾을 수 없습니다.
- 필요한 library target을 link하지 않았습니다.
- 구현 `.cpp`를 target source 목록에 넣지 않았습니다.
- 같은 비-`inline` 정의가 여러 object file에 들어갔습니다.

예를 들어 헤더에 선언만 있고,

```cpp
// include/job.hpp
#pragma once

void run_job();
```

`main.cpp`에서 호출하지만,

```cpp
#include "job.hpp"

int main() {
    run_job();
}
```

`run_job()`의 정의가 들어 있는 `.cpp`를 target에 포함하지 않았다면 compile은 성공할 수 있지만 link 단계에서 `undefined reference`와 같은 오류가 발생할 수 있습니다.

따라서 `undefined reference`, `unresolved external symbol`처럼 **정의가 없다는 형태의 오류**가 나오면 헤더 문법만 다시 보기보다 다음을 먼저 확인합니다.

1. 함수 정의가 실제로 존재합니까?
2. 그 정의가 들어 있는 `.cpp`가 올바른 target에 포함되어 있습니까?
3. 그 정의가 library에 있다면 현재 target이 그 library를 link합니까?
4. 선언과 정의의 함수 이름·namespace·parameter type·`const` 여부 등이 정확히 일치합니까?

### runtime 실패와 test 실패

build가 성공했다고 프로그램이 올바른 것은 아닙니다.

- **runtime 실패**: 실행 중 crash, 잘못된 입력 처리, object lifetime 문제, 파일·권한·환경 문제 등이 발생한 경우입니다.
- **test 실패**: test program 자체는 실행되었지만 실제 결과가 기대한 결과와 다른 경우입니다.

즉 다음 네 단계는 서로 다른 문제입니다.

```text
compile 실패
    ↓ 해결
link 실패
    ↓ 해결
실행 실패
    ↓ 해결
test assertion 실패
```

오류가 발생한 단계를 먼저 구분하면 조사 범위를 크게 줄일 수 있습니다.

---

## 헤더에는 무엇을 둘까

공개 헤더(public header)는 **그 library를 사용하는 코드가 알아야 하는 선언과 타입**을 제공합니다. 구현 세부사항은 가능하면 `.cpp`에 둡니다.

예:

```cpp
// include/task_store.hpp
#pragma once

#include <cstddef>
#include <string>

class TaskStore {
public:
    void add(std::string name);
    std::size_t size() const noexcept;
};
```

구현은 `.cpp`에 둡니다.

```cpp
// src/task_store.cpp
#include "task_store.hpp"

void TaskStore::add(std::string name) {
    // implementation
}

std::size_t TaskStore::size() const noexcept {
    // implementation
    return 0;
}
```

### 헤더는 스스로 필요한 선언을 포함해야 합니다

위 헤더는 `std::string`과 `std::size_t`를 직접 사용하므로 각각에 필요한 `<string>`과 `<cstddef>`를 직접 include합니다.

다른 헤더가 우연히 먼저 include되어 있어서 compile되는 상태에 의존하면 include 순서가 바뀌었을 때 깨질 수 있습니다.

좋은 공개 헤더는 가능하면 다음 코드처럼 단독으로 include해도 compile되어야 합니다.

```cpp
#include "task_store.hpp"

int main() {}
```

이를 흔히 **self-contained header**라고 생각할 수 있습니다.

---

## 헤더의 정의와 ODR

"헤더에는 정의를 넣으면 안 된다"라고 단순하게 외우면 정확하지 않습니다. 중요한 것은 **같은 정의가 여러 번 나타나도 언어 규칙상 허용되는가**입니다.

C++에는 하나의 프로그램에서 정의가 어떻게 존재해야 하는지를 규정하는 **ODR(One Definition Rule)** 이 있습니다.

다음과 같은 일반 함수 정의를 헤더에 두고 여러 `.cpp`가 그 헤더를 include하면 문제가 될 수 있습니다.

```cpp
// 잘못 사용하기 쉬운 예
int answer() {
    return 42;
}
```

이 헤더를 `a.cpp`와 `b.cpp`가 모두 include하면 두 object file에 `answer()`의 정의가 생기고 link 단계에서 multiple definition 오류가 날 수 있습니다.

반면 다음과 같은 정의는 헤더에 두는 것이 일반적입니다.

- class 정의
- template 정의
- class 내부에서 정의된 member function
- 명시적으로 `inline`인 함수
- C++17 이후의 `inline` 변수

예:

```cpp
inline int answer() {
    return 42;
}
```

template은 사용할 번역 단위에서 정의를 볼 수 있어야 하므로 보통 선언과 정의를 모두 헤더에 둡니다.

```cpp
template <typename T>
T twice(T value) {
    return value + value;
}
```

전역 변수 역시 비슷한 주의가 필요합니다.

```cpp
// 여러 번 정의될 수 있으므로 공개 헤더에 그대로 두면 위험합니다.
int global_count = 0;
```

단순히 여러 파일에서 같은 변수를 참조하게 하려는 경우에는 보통 헤더에 `extern` 선언을 두고 `.cpp` 하나에 정의를 둡니다.

```cpp
// include/state.hpp
extern int global_count;
```

```cpp
// src/state.cpp
int global_count = 0;
```

---

## 공개 헤더에서 `using namespace`를 피합니다

공개 헤더에서는 다음과 같은 선언을 두지 않는 것이 좋습니다.

```cpp
using namespace std;
```

헤더를 include하면 그 헤더의 내용이 include한 번역 단위에 들어오기 때문에, `using namespace` 역시 해당 파일의 이름 검색에 영향을 줍니다.

즉 library 사용자가 원하지 않아도 많은 이름이 현재 scope의 이름 검색 후보에 추가될 수 있고, 다른 library와의 이름 충돌이나 overload resolution 문제를 만들 수 있습니다.

공개 헤더에서는 필요한 이름을 명시적으로 작성합니다.

```cpp
std::string
std::vector<int>
std::size_t
```

---

## CMake에서는 target을 중심으로 생각합니다

Modern CMake에서는 directory 전체에 설정을 뿌리는 것보다 **어떤 target이 무엇을 필요로 하는가**를 표현하는 방식이 중요합니다.

예:

```cmake
cmake_minimum_required(VERSION 3.20)

project(task_app LANGUAGES CXX)

add_library(task_core
    src/task.cpp
    src/task_store.cpp
)

target_include_directories(task_core
    PUBLIC
        include
)

target_compile_features(task_core
    PUBLIC
        cxx_std_20
)

target_compile_options(task_core
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

add_executable(task_app
    app/main.cpp
)

target_link_libraries(task_app
    PRIVATE
        task_core
)
```

여기서 중요한 것은 각 명령이 특정 target에 붙어 있다는 점입니다.

- `add_library(task_core ...)`: `task_core`라는 library target과 그 source를 정의합니다.
- `target_include_directories(task_core ...)`: `task_core`에 필요한 include 경로를 설정합니다.
- `target_compile_features(task_core ...)`: 해당 target에 필요한 C++ 언어 기능 수준을 설정합니다.
- `target_compile_options(task_core ...)`: 해당 target을 compile할 때 사용할 option을 설정합니다.
- `target_link_libraries(task_app ...)`: `task_app`이 어떤 target 또는 library에 의존하는지 연결합니다.

이 방식은 프로젝트가 커졌을 때 "이 option은 왜 필요한가?", "이 include 경로는 누구 때문에 필요한가?"를 target 단위로 추적할 수 있게 합니다.

---

## `PUBLIC`, `PRIVATE`, `INTERFACE`

CMake의 `PUBLIC`, `PRIVATE`, `INTERFACE`는 단순히 "보여 주는 범위"가 아닙니다. **현재 target 자신에게 필요한 설정인지, 그 target을 사용하는 다른 target에도 전달해야 하는 설정인지**를 표현합니다.

다음처럼 생각하면 됩니다.

| 키워드 | 현재 target에 적용 | 이 target을 사용하는 target에 전달 |
|---|---:|---:|
| `PRIVATE` | 예 | 아니오 |
| `PUBLIC` | 예 | 예 |
| `INTERFACE` | 아니오 | 예 |

이때 다른 target으로 전달되는 설정을 흔히 **usage requirements**라고 부릅니다.

### `PRIVATE`

현재 target의 구현을 build할 때만 필요한 설정입니다.

예를 들어 `task_core`의 `.cpp`에서만 사용하는 내부 헤더 디렉터리가 있다면:

```cmake
target_include_directories(task_core
    PRIVATE
        src/internal
)
```

`task_app`은 그 내부 헤더를 알아야 할 이유가 없습니다.

### `PUBLIC`

현재 target 자체도 필요하고, 그 target을 사용하는 코드도 필요합니다.

예를 들어 공개 헤더가 `include/`에 있고 사용자가 다음처럼 include해야 한다면:

```cpp
#include "task_store.hpp"
```

`task_core`의 사용자도 `include/` 경로가 필요합니다.

```cmake
target_include_directories(task_core
    PUBLIC
        include
)
```

이제 다음 연결만 해도:

```cmake
target_link_libraries(task_app
    PRIVATE
        task_core
)
```

`task_app`은 `task_core`가 공개한 include 경로를 함께 전달받습니다.

중요한 점은 CMake에서 `target_link_libraries()`가 단순히 binary library 파일만 연결하는 명령이 아니라, target의 공개 usage requirements를 소비자에게 연결하는 역할도 한다는 것입니다.

### `INTERFACE`

현재 target의 source를 compile하는 데는 필요 없지만, 그 target을 사용하는 코드에는 필요한 설정입니다.

대표적으로 header-only library에 사용할 수 있습니다.

```cmake
add_library(task_utils INTERFACE)

target_include_directories(task_utils
    INTERFACE
        include
)

target_compile_features(task_utils
    INTERFACE
        cxx_std_20
)
```

`task_utils` 자체에는 compile할 `.cpp`가 없지만, 그것을 사용하는 target에는 include 경로와 C++20 요구사항이 전달됩니다.

---

## 공개 헤더의 의존성은 사용자에게도 전달해야 합니다

library의 공개 헤더가 다른 library의 공개 타입이나 헤더를 노출한다면, 그 의존성은 library 사용자에게도 필요할 수 있습니다.

예를 들어 `task_core`의 공개 헤더가 외부 target `fmt::fmt`의 헤더를 직접 include한다고 가정합니다.

```cpp
// task_core의 공개 헤더
#include <fmt/format.h>
```

그러면 `task_core`만 `fmt`를 내부적으로 아는 것으로 끝나지 않습니다. `task_core`의 헤더를 include하는 사용자도 `fmt` 헤더를 찾을 수 있어야 합니다.

이 경우 보통 의존성을 공개합니다.

```cmake
target_link_libraries(task_core
    PUBLIC
        fmt::fmt
)
```

반대로 `fmt`가 `task_core.cpp` 내부 구현에서만 사용되고 공개 헤더에는 나타나지 않는다면 일반적으로 `PRIVATE`가 적합합니다.

```cmake
target_link_libraries(task_core
    PRIVATE
        fmt::fmt
)
```

핵심 질문은 다음과 같습니다.

> 이 의존성이 없으면 `task_core`의 공개 헤더를 사용하는 다른 target을 compile하거나 link할 수 없는가?

그렇다면 대체로 `PUBLIC` 또는 `INTERFACE`로 전파해야 합니다.

---

## C++ 표준도 의존성의 일부가 될 수 있습니다

다음 설정은 `task_core`를 C++20 기능으로 compile하도록 요구합니다.

```cmake
target_compile_features(task_core
    PUBLIC
        cxx_std_20
)
```

여기서 `PUBLIC`을 사용한 이유는 `task_core`의 공개 API가 C++20 기능을 요구한다고 가정했기 때문입니다. 그러면 `task_core`를 사용하는 target도 해당 요구사항을 만족해야 합니다.

반대로 C++20 기능이 `.cpp` 구현 내부에서만 필요하고 공개 헤더는 더 낮은 표준에서도 사용할 수 있다면 `PRIVATE`를 선택할 수 있습니다.

즉 C++ 표준 역시 무조건 프로젝트 전체에 하나의 값을 강제하는 문제라기보다 target의 interface와 implementation 요구사항을 보고 결정할 수 있습니다.

---

## compiler warning은 보통 `PRIVATE`로 둡니다

warning option은 일반적으로 현재 프로젝트의 source quality를 검사하기 위한 설정입니다.

```cmake
target_compile_options(task_core
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)
```

이를 `PUBLIC`으로 전파하면 `task_core`를 사용하는 다른 target까지 같은 compiler option을 강제로 받게 됩니다. 외부 dependency나 다른 팀의 target에 동일한 warning 정책을 적용할 이유가 없다면 보통 `PRIVATE`가 더 적절합니다.

또한 `-Wall`, `-Wextra`, `-Wpedantic`은 GCC·Clang 계열에서 사용하는 option입니다. MSVC는 다른 warning option을 사용합니다.

compiler별 설정이 필요하면 generator expression을 사용할 수 있습니다.

```cmake
target_compile_options(task_core PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall;-Wextra;-Wpedantic>
    $<$<CXX_COMPILER_ID:MSVC>:/W4>
)
```

여기서 중요한 것은 문법 자체를 외우는 것이 아니라 **compiler-specific option을 무조건 모든 환경에 적용하지 않는다**는 점입니다.

특히 `-Werror`나 `/WX`처럼 warning을 오류로 바꾸는 option을 dependency까지 전파하면, 자신의 코드와 관계없는 외부 source의 warning 때문에 build가 깨질 수 있습니다.

---

## library와 executable을 분리합니다

작은 프로그램에서는 모든 코드를 `main.cpp`에 넣을 수 있습니다. 그러나 상태 변경, parsing, 파일 처리, business rule까지 `main.cpp`에 몰아넣으면 test가 어려워집니다.

예를 들어 다음 구조를 생각할 수 있습니다.

```text
include/
    task_store.hpp

src/
    task_store.cpp

app/
    main.cpp

tests/
    task_core_tests.cpp
```

역할은 다음처럼 나눕니다.

```text
task_core
    핵심 타입과 규칙

task_app
    command-line argument
    stdin/stdout
    종료 코드
    task_core 호출

task_core_tests
    task_core의 함수와 타입을 직접 검사
```

CMake에서는 각 역할을 별도 target으로 만듭니다.

```cmake
add_library(task_core
    src/task_store.cpp
)

target_include_directories(task_core
    PUBLIC
        include
)

add_executable(task_app
    app/main.cpp
)

target_link_libraries(task_app
    PRIVATE
        task_core
)
```

이렇게 하면 application의 입출력 계층과 핵심 로직을 분리할 수 있습니다.

---

## test도 하나의 executable target입니다

간단한 C++ test program 역시 결국 실행 가능한 프로그램입니다.

```cmake
add_executable(task_core_tests
    tests/task_core_tests.cpp
)

target_link_libraries(task_core_tests
    PRIVATE
        task_core
)
```

CTest에 등록하면 CMake build 이후 같은 방식으로 test를 실행할 수 있습니다.

```cmake
enable_testing()

add_test(
    NAME task.core
    COMMAND task_core_tests
)
```

여기서 역할을 구분해야 합니다.

- `add_executable()`은 test program을 **build할 target**을 만듭니다.
- `add_test()`는 만들어진 program을 CTest가 **어떻게 실행할지 등록**합니다.

즉 `add_test()`만 작성한다고 test executable이 자동으로 compile되는 것은 아닙니다.

핵심 로직을 library로 분리했다면 test는 application process 전체를 실행하지 않고 `task_core`의 함수와 타입을 직접 검사할 수 있습니다.

application 자체의 argument parsing, 표준 입출력, 종료 상태가 요구사항이라면 별도의 integration test에서 실행 파일을 검사할 수 있습니다.

---

## header를 include했다고 library가 link되는 것은 아닙니다

다음 코드는 header를 찾을 수 있다는 뜻일 뿐입니다.

```cpp
#include "task_store.hpp"
```

include 경로가 올바르면 compiler는 선언을 읽고 compile할 수 있습니다. 그러나 함수 구현이 library에 들어 있다면 최종 실행 파일을 만들 때 그 library도 link해야 합니다.

CMake에서는 다음처럼 dependency를 표현합니다.

```cmake
target_link_libraries(task_app
    PRIVATE
        task_core
)
```

따라서 다음 두 문제는 서로 다릅니다.

```text
헤더를 찾지 못함
    → include path 문제
    → compile 단계 실패

함수 정의를 찾지 못함
    → source/target/link dependency 문제
    → link 단계 실패
```

이 구분은 CMake 문제를 조사할 때 매우 중요합니다.

---

## 새 `.cpp` 파일을 만들었다고 자동으로 build되는 것은 아닙니다

파일을 프로젝트 디렉터리에 생성했다고 CMake target에 자동으로 포함되는 것은 아닙니다.

예를 들어 다음 파일을 추가했다면:

```text
src/task_parser.cpp
```

target의 source 목록에도 추가해야 합니다.

```cmake
add_library(task_core
    src/task_store.cpp
    src/task_parser.cpp
)
```

파일이 디렉터리에 존재하는지와 어떤 target의 일부인지는 별개의 문제입니다.

특히 함수 선언을 헤더에 추가하고 구현 `.cpp`도 작성했지만 `add_library()`의 source 목록에는 넣지 않았다면, compile은 성공하고 link에서 `undefined reference`가 발생할 수 있습니다.

---

## out-of-source build

source tree와 build 결과는 분리하는 것이 좋습니다.

예를 들어 다음처럼 구성합니다.

```text
project/
    CMakeLists.txt
    include/
    src/
    app/
    tests/

    build/
        debug/
        release/
```

Debug build:

```sh
cmake -S . -B build/debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/debug
ctest --test-dir build/debug --output-on-failure
```

Release build:

```sh
cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release
cmake --build build/release
ctest --test-dir build/release --output-on-failure
```

`-S .`는 source directory를 지정하고, `-B build/debug`는 생성되는 build system과 cache를 둘 build directory를 지정합니다.

source와 build directory를 분리하면 다음 장점이 있습니다.

- compiler가 생성한 파일이 source와 섞이지 않습니다.
- build directory를 삭제해 깨끗한 상태에서 다시 configure할 수 있습니다.
- Debug와 Release 설정을 독립적으로 유지할 수 있습니다.
- 생성 파일을 실수로 version control에 commit할 가능성이 줄어듭니다.

---

## `CMAKE_BUILD_TYPE`이 항상 사용되는 것은 아닙니다

`CMAKE_BUILD_TYPE=Debug` 같은 설정은 Makefiles나 Ninja처럼 보통 한 build directory가 한 configuration을 다루는 **single-config generator**에서 사용됩니다.

```sh
cmake -S . -B build/debug -DCMAKE_BUILD_TYPE=Debug
```

Visual Studio나 Xcode처럼 하나의 build tree에서 여러 configuration을 선택할 수 있는 **multi-config generator**에서는 build할 때 configuration을 지정하는 방식이 일반적입니다.

```sh
cmake --build build --config Debug
```

따라서 "Debug는 항상 `CMAKE_BUILD_TYPE=Debug`로 설정한다"라고 이해하면 모든 generator에 적용되는 규칙은 아닙니다.

다만 학습 초기에 Makefiles나 Ninja를 사용하는 경우에는 Debug와 Release를 서로 다른 build directory로 분리하는 방식이 이해하기 쉽고 재현성도 좋습니다.

---

## CMake cache를 이해합니다

CMake는 configure 과정에서 계산한 여러 값을 build directory의 cache에 저장합니다.

따라서 같은 build directory에서 다음과 같이 option을 계속 바꾸면 이전 configure 결과가 일부 남아 현재 설정을 착각할 수 있습니다.

```text
build/
    CMakeCache.txt
    ...
```

특히 compiler, toolchain, dependency 위치처럼 build 전체에 큰 영향을 주는 설정을 변경했을 때 문제가 생기면 기존 build directory를 삭제하고 다시 configure하는 것이 가장 단순한 확인 방법입니다.

```sh
rm -rf build/debug
cmake -S . -B build/debug -DCMAKE_BUILD_TYPE=Debug
```

source를 삭제하는 것이 아니라 생성된 build directory만 다시 만드는 것입니다.

---

## 반복되는 설정은 preset으로 기록할 수 있습니다

반복적으로 사용하는 configure·build 설정은 `CMakePresets.json`에 기록할 수 있습니다.

예를 들어 개발자마다 다음과 같은 긴 명령을 매번 기억하는 대신:

```sh
cmake -S . -B build/debug -G Ninja -DCMAKE_BUILD_TYPE=Debug
```

preset에 generator, build directory, cache variable 등을 기록할 수 있습니다.

하지만 작은 프로젝트의 첫 단계부터 package manager, 복잡한 preset 계층, custom module을 모두 도입할 필요는 없습니다.

먼저 다음 관계를 명확히 이해하는 것이 더 중요합니다.

```text
source
    ↓
target
    ↓
target dependency
    ↓
build
    ↓
test
```

---

## 자주 놓치는 문제

### source를 만들고 target에 추가하지 않음

```text
src/task_parser.cpp는 존재
↓
add_library(task_core ...)에는 없음
↓
구현이 object file로 만들어지지 않음
↓
link에서 undefined reference 가능
```

파일 존재 여부보다 target source 목록을 확인합니다.

### header include는 되지만 link하지 않음

```text
include path는 정상
↓
선언을 읽어 compile 성공
↓
필요한 library를 link하지 않음
↓
link 실패
```

`target_link_libraries()`를 확인합니다.

### 공개 header에 필요한 경로를 `PRIVATE`로 둠

library 자신은 우연히 compile되지만 사용자는 공개 헤더를 찾지 못할 수 있습니다.

공개 API를 사용하는 consumer도 필요한 include 경로라면 `PUBLIC` 또는 `INTERFACE`가 필요한지 검토합니다.

### 모든 target에 warning option을 전역으로 강제함

프로젝트 source뿐 아니라 third-party code까지 같은 warning 정책을 받을 수 있습니다.

warning은 가능하면 자신이 관리하는 target에 `PRIVATE`로 적용합니다.

### source directory 안에서 직접 build함

CMake가 만든 cache, object file, generated build file이 source와 섞여 repository 상태를 오염시키기 쉽습니다.

별도의 build directory를 사용합니다.

---

## dependency를 어디에 연결할지 판단하는 방법

dependency를 `PRIVATE`, `PUBLIC`, `INTERFACE` 중 무엇으로 둘지 모호하다면 다음 순서로 생각할 수 있습니다.

```text
1. 현재 target의 .cpp 구현에서 필요한가?
   └─ 예 → 현재 target에는 필요

2. 현재 target의 공개 header를 사용하는 consumer도 필요한가?
   └─ 예 → consumer에도 전달 필요
```

그 결과는 다음과 같이 정리할 수 있습니다.

```text
현재 target만 필요
    → PRIVATE

현재 target과 consumer 모두 필요
    → PUBLIC

현재 target 자체에는 source가 없거나 필요 없고 consumer만 필요
    → INTERFACE
```

이 기준은 include directory, compile feature, compile definition, linked target 등 여러 target property에 공통으로 적용할 수 있습니다.

---

## 프로젝트에서 확인할 질문

### target 구성

- 각 `.cpp`는 정확히 하나의 의도된 target에 포함되어 있습니까?
- executable이 실제로 사용하는 library target은 무엇입니까?
- test가 application process를 실행하지 않고 핵심 library를 직접 검사할 수 있습니까?

### 공개 interface

- 공개 header가 필요한 include directory는 consumer에게 전달됩니까?
- 공개 header가 사용하는 dependency도 consumer가 사용할 수 있습니까?
- 공개 header를 다른 directory의 작은 test program에서 단독으로 include해도 compile됩니까?

### compile 설정

- C++ 표준 요구사항은 실제로 필요한 target에 설정되어 있습니까?
- warning option은 compiler에 맞게 설정되어 있습니까?
- warning policy가 외부 dependency까지 불필요하게 전파되지 않습니까?

### link 설정

- 구현 `.cpp`가 올바른 target source 목록에 포함되어 있습니까?
- executable과 test가 필요한 library target을 `target_link_libraries()`로 연결합니까?
- thread 같은 platform dependency가 필요한 경우 그것을 실제로 사용하는 target에 연결되어 있습니까?

### 재현성

- 깨끗한 checkout에서도 README의 명령만으로 configure와 build가 가능합니까?
- source와 build 결과가 분리되어 있습니까?
- Debug와 Release 설정이 서로 섞이지 않습니까?

---

## 오류를 만났을 때의 확인 순서

빌드 문제를 만났을 때는 오류 메시지부터 어느 단계인지 분류합니다.

### 1. compile 오류라면

확인합니다.

```text
문법
이름 선언
타입
include
C++ 표준
compile option
```

### 2. link 오류라면

확인합니다.

```text
정의 존재 여부
.cpp의 target 포함 여부
target_link_libraries()
선언과 정의의 signature 일치 여부
중복 정의 여부
```

### 3. runtime 오류라면

확인합니다.

```text
입력
object lifetime
null/invalid state
파일과 권한
환경 변수
실행 경로
```

### 4. test만 실패한다면

확인합니다.

```text
기대값
실제값
test fixture
test data
요구사항 해석
```

단계를 구분하지 않고 모든 파일을 동시에 고치기 시작하는 것보다, 실패한 단계에서 필요한 정보부터 확인하는 것이 효율적입니다.

---

## 완료 기준

이 문서를 학습한 뒤에는 다음을 설명하고 직접 구성할 수 있어야 합니다.

- `.cpp` 하나가 하나의 번역 단위를 만드는 과정을 설명합니다.
- compile, link, runtime, test 실패를 구분합니다.
- `undefined reference`가 발생했을 때 source 목록과 link dependency를 먼저 확인합니다.
- 공개 header와 implementation `.cpp`의 역할을 구분합니다.
- ODR 때문에 일반 함수나 전역 변수 정의를 헤더에 둘 때 생길 수 있는 문제를 설명합니다.
- library, executable, test target을 각각 구성합니다.
- `PUBLIC`, `PRIVATE`, `INTERFACE`를 usage requirement 관점에서 선택합니다.
- C++ 표준과 compiler warning을 target 단위로 적용합니다.
- header include 성공과 library link 성공이 서로 다른 문제임을 설명합니다.
- 별도 build directory에서 Debug와 Release build를 재현합니다.
- CMake cache가 build 설정에 미치는 영향을 설명합니다.
