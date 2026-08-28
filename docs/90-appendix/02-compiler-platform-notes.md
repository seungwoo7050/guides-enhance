# compiler와 운영체제 차이

## 목적

같은 C++ source라도 compiler, 표준 library와 운영체제에 따라 warning, 지원 기능과 system API가 달라질 수 있습니다. 차이를 숨기지 않고 build와 test에서 확인합니다.

## GCC와 Clang

둘 다 표준 C++을 폭넓게 지원하지만 warning 문구와 진단 범위는 다릅니다.

```sh
g++ -std=c++20 -Wall -Wextra -Wpedantic source.cpp
clang++ -std=c++20 -Wall -Wextra -Wpedantic source.cpp
```

`-Werror`는 자신의 source에 적용하면 도움이 되지만 외부 header까지 같은 warning으로 실패시키지 않게 target 범위를 조정합니다.

한 compiler에서 warning이 없다는 사실이 다른 compiler에서도 문제가 없다는 뜻은 아닙니다. 가능하면 둘 다 기본 build를 확인합니다.

## 표준 library 버전

compiler version과 standard library version은 같지 않을 수 있습니다. Clang이 `libstdc++`를 사용할 수도 있고 `libc++`를 사용할 수도 있습니다.

C++20 문법은 지원하지만 일부 library 기능이 없을 수 있습니다. 오류가 발생하면 다음을 구분합니다.

- compiler parser가 문법을 모릅니다.
- header에 타입이 없습니다.
- 선언은 있지만 link할 library 구현이 없습니다.

## Linux와 macOS

### readiness API

- Linux: `epoll`
- macOS/BSD: `kqueue`

공통 server 코드는 platform bit를 직접 사용하지 않고 adapter가 `readable`, `writable`, `hangup`, `error`로 변환하게 할 수 있습니다.

### `MSG_NOSIGNAL`

Linux에서는 `send()`에 `MSG_NOSIGNAL`을 사용할 수 있습니다. macOS에서는 `SO_NOSIGPIPE`를 socket에 설정하는 방식이 일반적입니다. 단순히 한쪽 macro가 모든 플랫폼에 있다고 가정하지 않습니다.

### descriptor 검사

Linux는 `/proc/<pid>/fd`로 열린 fd를 확인할 수 있습니다. macOS에서는 `lsof` 같은 도구가 필요합니다. 테스트가 platform 기능을 요구하면 사용할 수 없을 때 명시적으로 건너뜁니다.

## integer와 byte order

`int`, `long`, pointer 크기를 고정값으로 가정하지 않습니다. network protocol에는 `uint32_t` 같은 고정 폭 타입과 `htonl`/`ntohl`을 사용합니다.

C++98에서 `<stdint.h>` 지원 여부는 compiler와 platform을 확인합니다. 필요한 고정 폭 타입을 project compatibility header로 모을 수 있습니다.

## path와 filesystem

C++20 `std::filesystem` path의 문자 encoding과 native representation은 platform마다 다릅니다. `path.string()`을 C API에 넘기는 구현은 Windows의 모든 비 ASCII 경로를 처리하지 못할 수 있습니다.

POSIX 프로젝트라면 지원 platform을 Linux/macOS로 명시하고 `/` path와 file descriptor API를 기준으로 둘 수 있습니다.

## sanitizer

sanitizer 지원은 compiler 이름만으로 확정하지 않습니다. 작은 compile·runtime probe를 먼저 실행합니다.

- ASan/UBSan은 비교적 널리 지원됩니다.
- TSan은 다른 sanitizer와 함께 쓰지 못하거나 특정 runtime에서 동작하지 않을 수 있습니다.
- leak detection 기본값은 platform마다 다를 수 있습니다.

지원하지 않는 환경에서 성공했다고 기록하지 않습니다. `SKIP`과 이유를 남깁니다.

## ABI와 compiler option

서로 다른 C++ 표준 library나 ABI option으로 빌드한 object를 섞으면 link 또는 runtime 문제가 생길 수 있습니다. 외부 prebuilt library가 요구하는 compiler, 표준 library와 ABI를 확인합니다.

Debug macro나 iterator debugging option이 container layout을 바꾸는 구현도 있습니다. library와 application은 호환되는 option으로 빌드합니다.

## signal과 process

signal 번호와 일부 flag는 platform마다 다를 수 있습니다. POSIX 공통 기능을 우선하고 platform 전용 코드는 `#if`가 있는 작은 파일로 격리합니다.

`fork()` 이후 multi-threaded process의 child에서는 async-signal-safe 함수만 사용하고 가능한 한 바로 `exec()`합니다.

## 빌드 매트릭스

최소한 다음을 기록합니다.

```text
compiler와 version
C++ standard mode
standard library
operating system과 architecture
Debug/Release
sanitizer 사용 여부
```

## 완료 기준

- compiler와 standard library 지원 문제를 구분합니다.
- Linux `epoll`과 BSD `kqueue` 코드를 작은 adapter로 분리합니다.
- platform별 SIGPIPE와 fd 검사 방법을 다룹니다.
- sanitizer를 실제 probe 뒤에 실행합니다.
- 실행하지 못한 platform 검사를 성공으로 보고하지 않습니다.
- 외부 library의 ABI와 build option 호환성을 확인합니다.
