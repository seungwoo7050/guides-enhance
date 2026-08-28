# C++ 개발 가이드

이 저장소는 C++ 문법을 모두 익힌 뒤 개발을 시작하는 과정을 권하지 않습니다. 프로젝트 종류와 상관없이 반복해서 필요한 내용만 먼저 익히고, 나머지는 실제 구현 중 필요한 시점에 찾아봅니다.

```text
공통 기반 정독
→ 실제 프로젝트 구현
→ 필요한 문서와 명세를 그때그때 확인
→ 프로젝트 검사 통과
→ 시간이 지난 뒤 exercise를 명세만 보고 재구현
```

핵심은 무작정 코드를 쓰는 것이 아닙니다. 언어가 객체와 자원을 다루는 방식은 먼저 이해하되, 네트워크·렌더링·파일 형식처럼 특정 문제에만 필요한 내용은 구현 과정에서 배웁니다.

## 저장소 구성

```text
.
├── .gitignore
├── README.md
├── docs/
└── exercises/
```

- `docs/`: 공통 기반과 필요할 때 찾아볼 참고 문서를 제공합니다.
- `exercises/`: 프로젝트 경험 이후 개발 능력을 다시 확인하는 완성된 프로그램입니다.

각 exercise는 자체 빌드 파일과 테스트를 갖고 있으며 다른 exercise나 저장소 루트의 스크립트에 의존하지 않습니다.

## 먼저 읽을 문서

### Modern C++ 공통 기반

다음 여섯 문서는 프로젝트 종류가 달라져도 목록을 늘리지 않습니다.

1. [`프로그램·빌드·CMake`](docs/01-modern-cpp/01-program-build-cmake.md)
2. [`값·수명·복사·이동`](docs/01-modern-cpp/02-values-lifetimes-and-move.md)
3. [`RAII·smart pointer·Rule of Zero`](docs/01-modern-cpp/03-raii-smart-pointers-and-rule-of-zero.md)
4. [`클래스·역할 분리·다형성`](docs/01-modern-cpp/04-classes-responsibilities-and-polymorphism.md)
5. [`오류·optional·variant·expected`](docs/01-modern-cpp/05-errors-optional-variant-and-expected.md)
6. [`algorithm·range·template·concept`](docs/01-modern-cpp/06-algorithms-ranges-templates-and-concepts.md)

### C++98도 사용하는 경우

Modern C++의 개념을 먼저 익힌 뒤 다음 문서를 추가로 읽습니다.

1. [`Modern C++에서 C++98로 옮기기`](docs/90-appendix/01-modern-to-cpp98-crosswalk.md)
2. [`프로그램과 타입 모델`](docs/02-cpp98-systems/01-program-and-type-model.md)
3. [`수명·값·소유권`](docs/02-cpp98-systems/02-lifetime-value-and-ownership.md)
4. [`객체에 역할 나누기`](docs/02-cpp98-systems/03-assigning-object-responsibilities.md)
5. [`상속과 다형성`](docs/02-cpp98-systems/04-inheritance-and-polymorphism.md)
6. [`오류 처리·입력 검증·캐스트`](docs/02-cpp98-systems/05-errors-validation-and-casts.md)
7. [`template·iterator·STL`](docs/02-cpp98-systems/06-templates-iterators-and-stl.md)

## 프로젝트 중 찾아볼 문서

다음 문서는 선행 과제가 아닙니다. 관련 문제가 실제로 나타났을 때 사용합니다.

- [`동시성·시간·filesystem`](docs/01-modern-cpp/07-concurrency-time-and-filesystem.md)
- [`테스트·디버깅·도구`](docs/01-modern-cpp/08-testing-debugging-and-tooling.md)
- [`STL로 문제 풀기`](docs/02-cpp98-systems/07-solving-problems-with-stl.md)
- [`POSIX socket과 event loop`](docs/02-cpp98-systems/08-posix-sockets-and-event-loop.md)
- [`객체지향 HTTP server`](docs/02-cpp98-systems/09-object-oriented-http-server.md)
- [`compiler와 운영체제 차이`](docs/90-appendix/02-compiler-platform-notes.md)
- [`C++98 빌드와 호환성`](docs/90-appendix/03-cpp98-build-and-compatibility.md)
- [`STL 내부 동작`](docs/90-appendix/04-stl-internals.md)

## 개발 능력 재확인용 exercise

시간 대비 검증 범위가 넓은 네 프로젝트만 남겼습니다.

| Project | 주로 확인하는 능력 |
| --- | --- |
| [`mini-vector`](exercises/mini-vector/) | raw storage, 객체 수명, template, 예외 발생 후 복구 |
| [`command-service`](exercises/command-service/) | C++98 소유권, 역할 분리, 입력 검증, 다형성, 오류 변환 |
| [`local-job-runner`](exercises/local-job-runner/) | 상태 변화, 제한된 queue, 취소, 동시 종료, journal |
| [`line-server`](exercises/line-server/) | file descriptor 수명, 부분 입출력, event loop, backpressure |

이 exercise들은 프로젝트 진입 조건이 아닙니다. 실제 프로젝트를 끝내고 일정 시간을 둔 뒤, README와 공개 API만 보고 다시 구현합니다.

### 재구현할 때 허용하는 자료

- 언어 문법과 표준 라이브러리 API 문서
- compiler 오류 메시지
- 운영체제와 프로토콜의 공식 문서

### 재구현할 때 보지 않는 자료

- 해당 exercise의 구현 파일
- 같은 문제를 설명하는 가이드
- 이전에 작성한 자신의 코드
- 동일한 설계를 그대로 제공하는 해설

## 빌드와 테스트

각 exercise 디렉터리에서 README에 적힌 명령을 실행합니다. 예를 들면 다음과 같습니다.

```sh
cd exercises/mini-vector
make test
```

```sh
cd exercises/local-job-runner
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

## Implementation Order

exercise의 `[Implementation N]` 주석은 파일 순서나 함수 순서가 아닙니다. 데이터를 정의하고, 소유자를 정하고, 실패를 처리하고, 실행 파일로 연결하는 순서를 나타냅니다.

같은 번호는 프로젝트 안에서 한 번만 사용합니다. README의 표와 source 주석은 번호, 설명, 파일 위치가 일치해야 합니다.

## 범위

이 저장소는 특정 제품이나 업무 분야의 규칙을 미리 가르치지 않습니다. 특정 네트워크 프로토콜, 렌더링 수학, 파일 형식, 데이터베이스 업무 규칙은 실제 프로젝트에서 명세와 함께 학습합니다.

전체 진행 방법은 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 정리되어 있습니다.
