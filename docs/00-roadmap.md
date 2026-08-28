# C++ 학습 로드맵

## 목표

이 로드맵은 가능한 한 빨리 실제 구현을 시작하면서도, 언어 자체를 잘못 이해해 같은 문제를 반복하지 않도록 최소한의 공통 기반을 정합니다.

프로젝트가 추가된다고 선행 문서가 계속 늘어나면 이 방식의 의미가 없습니다. 따라서 선행 범위는 언어·빌드·수명·오류 처리처럼 어떤 프로그램에서도 반복되는 내용으로 고정합니다. 특정 분야의 지식은 구현 중 필요한 시점에 확인합니다.

## 전체 진행 방식

```text
1. 공통 기반을 한 번 정독합니다.
2. 실제 프로젝트의 요구사항을 읽고 가장 작은 실행 경로부터 만듭니다.
3. 막힌 문제와 직접 관련된 문서·명세만 찾아봅니다.
4. 정상·실패·종료 조건을 검사해 프로젝트를 통과시킵니다.
5. 일정 시간을 둡니다.
6. exercise를 구현 파일 없이 다시 작성합니다.
7. 원래 구현과 비교해 놓친 불변식과 실패 조건을 기록합니다.
```

## 1. Modern C++ 공통 기반

다음 여섯 문서는 고정 선행 범위입니다.

1. [`01-program-build-cmake.md`](01-modern-cpp/01-program-build-cmake.md)
2. [`02-values-lifetimes-and-move.md`](01-modern-cpp/02-values-lifetimes-and-move.md)
3. [`03-raii-smart-pointers-and-rule-of-zero.md`](01-modern-cpp/03-raii-smart-pointers-and-rule-of-zero.md)
4. [`04-classes-responsibilities-and-polymorphism.md`](01-modern-cpp/04-classes-responsibilities-and-polymorphism.md)
5. [`05-errors-optional-variant-and-expected.md`](01-modern-cpp/05-errors-optional-variant-and-expected.md)
6. [`06-algorithms-ranges-templates-and-concepts.md`](01-modern-cpp/06-algorithms-ranges-templates-and-concepts.md)

이 구간을 마치면 다음을 할 수 있어야 합니다.

- library, executable, test target을 나눠 빌드합니다.
- 값, 참조, 비소유 view와 자원 소유자를 구분합니다.
- 복사와 이동 뒤 어느 객체가 무엇을 소유하는지 설명합니다.
- 생성 시 유효 상태를 만들고 잘못된 입력을 거부합니다.
- 예상 가능한 실패와 예외를 구분합니다.
- container와 algorithm을 주요 연산과 복잡도에 맞게 고릅니다.
- template API가 받아들일 타입을 제한합니다.

여기까지 읽었다면 networking, graphics, database 같은 문서를 더 읽지 않고 프로젝트를 시작합니다.

## 2. C++98 추가 기반

C++98로도 구현한다면 Modern C++ 공통 기반 뒤에 다음을 읽습니다.

1. [`01-modern-to-cpp98-crosswalk.md`](90-appendix/01-modern-to-cpp98-crosswalk.md)
2. [`01-program-and-type-model.md`](02-cpp98-systems/01-program-and-type-model.md)
3. [`02-lifetime-value-and-ownership.md`](02-cpp98-systems/02-lifetime-value-and-ownership.md)
4. [`03-assigning-object-responsibilities.md`](02-cpp98-systems/03-assigning-object-responsibilities.md)
5. [`04-inheritance-and-polymorphism.md`](02-cpp98-systems/04-inheritance-and-polymorphism.md)
6. [`05-errors-validation-and-casts.md`](02-cpp98-systems/05-errors-validation-and-casts.md)
7. [`06-templates-iterators-and-stl.md`](02-cpp98-systems/06-templates-iterators-and-stl.md)

목표는 Modern C++ 문법을 흉내 내는 것이 아닙니다. move, smart pointer, lambda, scoped enum이 없을 때 깊은 복사·복사 금지·명시적인 소멸자·함수 객체로 같은 요구사항을 처리하는 방법을 익힙니다.

## 3. 실제 프로젝트에서 배우는 내용

프로젝트를 시작할 때는 전체 분야를 정독하지 않습니다. 먼저 현재 기능의 입력, 출력, 상태 변화와 실패 조건만 확인합니다.

예를 들어 socket을 처음 사용한다면 다음 순서로 진행합니다.

```text
listener를 열고 한 client를 처리
→ recv가 나뉘는 문제 확인
→ 연결별 입력 버퍼 추가
→ send 일부 전송 확인
→ 출력 버퍼와 writable event 추가
→ 느린 client의 출력 제한 추가
```

각 문제가 나타날 때 [`POSIX socket과 event loop`](02-cpp98-systems/08-posix-sockets-and-event-loop.md)의 해당 절을 찾아봅니다. HTTP를 구현하지 않는다면 HTTP 문서를 읽을 이유가 없습니다.

### 필요할 때 사용하는 문서

- thread, 취소, timeout, filesystem: [`07-concurrency-time-and-filesystem.md`](01-modern-cpp/07-concurrency-time-and-filesystem.md)
- 테스트 불안정성, sanitizer, debugger: [`08-testing-debugging-and-tooling.md`](01-modern-cpp/08-testing-debugging-and-tooling.md)
- container 선택과 입력 처리: [`07-solving-problems-with-stl.md`](02-cpp98-systems/07-solving-problems-with-stl.md)
- non-blocking socket: [`08-posix-sockets-and-event-loop.md`](02-cpp98-systems/08-posix-sockets-and-event-loop.md)
- HTTP parser, keep-alive, CGI: [`09-object-oriented-http-server.md`](02-cpp98-systems/09-object-oriented-http-server.md)
- compiler·운영체제 차이: [`02-compiler-platform-notes.md`](90-appendix/02-compiler-platform-notes.md)
- C++98 빌드 문제: [`03-cpp98-build-and-compatibility.md`](90-appendix/03-cpp98-build-and-compatibility.md)
- raw storage와 iterator 무효화: [`04-stl-internals.md`](90-appendix/04-stl-internals.md)

## 4. 프로젝트 완료 기준

기능이 한 번 실행됐다는 사실만으로 끝내지 않습니다.

- 정상 입력과 잘못된 입력을 구분합니다.
- 실패하기 전에 변경된 상태가 없는지 확인합니다.
- 파일, socket, memory, thread를 누가 정리하는지 추적합니다.
- 종료 요청 뒤 새 작업을 받는지 확인합니다.
- timeout과 무한 대기를 구분합니다.
- 실행 순서에 따라 간헐적으로 실패하는 테스트가 없는지 반복합니다.
- 빌드와 테스트 명령을 새 디렉터리에서도 재현합니다.

## 5. 사후 exercise

프로젝트를 통과한 직후에는 기억이 너무 선명하므로 일정 시간을 둡니다. 그다음 아래 순서로 재구현합니다.

```text
mini-vector
→ command-service
→ local-job-runner
→ line-server
```

### `mini-vector`

raw storage와 생성된 객체를 구분하고, 재할당·복사 실패·입력 aliasing 뒤 기존 상태를 보존하는지 확인합니다.

### `command-service`

C++98에서 문자열과 handler를 직접 소유하고, 입력 해석·데이터 변경·출력 형식을 나누며 실패를 고정된 응답으로 바꾸는지 확인합니다.

### `local-job-runner`

제한된 queue, 상태 변화, callback 예외, 협력적 취소와 여러 호출자의 동시 종료를 처리하는지 확인합니다.

### `line-server`

TCP 부분 입출력, 연결별 버퍼, readiness event, backpressure와 모든 fd 종료 경로를 처리하는지 확인합니다.

## 6. 재구현 규칙

허용합니다.

- 언어 문법과 표준 라이브러리 함수 설명
- system call과 protocol의 공식 문서
- compiler·linker·sanitizer의 진단

보지 않습니다.

- exercise source
- 같은 exercise의 설계 해설
- 이전 자신의 구현
- 테스트 정답을 직접 드러내는 reference

구현을 끝낸 뒤에만 기존 source와 비교합니다. 비교할 항목은 코드 모양이 아니라 다음과 같습니다.

- 소유자가 같은가
- 유효 상태가 더 넓거나 좁은가
- 실패 시 어느 변경까지 남는가
- 종료 순서가 모든 자원의 수명을 끝내는가
- 테스트가 같은 잘못된 구현을 검출하는가

## 완료 기준

다음 질문에 구체적인 코드 위치를 들어 답할 수 있으면 이 로드맵의 목표를 달성한 것입니다.

- 이 객체가 직접 소유하는 값과 자원은 무엇입니까?
- 참조나 pointer는 언제까지 유효합니까?
- 복사와 이동 뒤 원본은 어떤 상태입니까?
- 입력 검증이 끝나기 전에 상태를 변경합니까?
- 일부 작업만 성공한 뒤 예외가 발생하면 무엇을 되돌립니까?
- 여러 thread가 같은 상태를 바꿀 때 어떤 mutex와 조건식을 사용합니까?
- socket이 writable하다는 사실과 모든 출력이 전송됐다는 사실이 왜 다릅니까?
- 종료 후 남아 있는 thread, child process, file descriptor가 있습니까?
