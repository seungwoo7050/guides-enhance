# 언어와 runtime 적용 기준

## 역할

이 문서는 선택 자료입니다. 공통 게임 서버 원리를 C++ 또는 Java 구현으로 옮길 때 수명, 메모리와 실행 환경 차이를 확인합니다. 특정 network library나 framework를 필수로 지정하지 않습니다.

## 공통 기준

언어와 관계없이 다음을 만족해야 합니다.

- 한 방의 정본 상태를 변경하는 실행 주체가 하나입니다.
- network callback은 검증할 명령을 상한이 있는 큐로 전달합니다.
- fixed tick을 test clock으로 실행할 수 있습니다.
- connection, session, room과 match 수명을 분리합니다.
- queue, buffer, timer, task와 socket의 최대 크기와 정리 시점을 정합니다.
- protocol framing, version과 최대 메시지 크기를 검사합니다.
- graceful shutdown과 process failure 뒤 남는 상태를 설명합니다.
- 언어가 달라도 같은 fixture를 비교할 JSON trace 또는 동등한 결과를 제공합니다.

## C++ 적용

### 권장 기반

- C++20 또는 프로젝트가 요구하는 표준
- CMake처럼 target이 드러나는 build 설정
- RAII, move, smart pointer와 값 수명
- POSIX socket 또는 선택한 network runtime
- sanitizer와 결정적 검사

### 확인할 항목

- socket, timer와 buffer를 어느 객체가 해제하는지 type으로 드러냅니다.
- callback이 이미 제거된 room이나 connection을 참조하지 않게 합니다.
- queue에 raw pointer를 넣는다면 대상의 수명이 dequeue까지 유지되는지 증명합니다.
- packet parsing 전에 length와 정수 overflow를 확인합니다.
- allocator 호출과 data layout은 측정한 뒤 최적화합니다.
- false sharing과 lock contention은 별도 metric으로 확인합니다.
- shutdown에서 thread join, callback 취소와 descriptor close 순서를 정합니다.

### 외부 service 연결

C++ room server는 account, lobby와 matchmaking service에 protocol로 연결할 수 있습니다. Spring Boot는 외부 Java service의 선택지이며 C++ server의 구성 요소가 아닙니다.

## Java 적용

### 권장 기반

- JDK 17 이상
- Maven 또는 Gradle 중 하나
- 명시적인 executor와 상한이 있는 queue
- NIO 또는 선택한 asynchronous network runtime
- JUnit과 test clock

### 확인할 항목

- event loop thread에서 blocking DB나 HTTP 요청을 실행하지 않습니다.
- 방 상태 변경을 single-writer queue 또는 명시적인 lock으로 제한합니다.
- 기본값이 무제한인 executor queue를 그대로 사용하지 않습니다.
- cancellation과 interrupt를 정상 종료 경로에서 처리합니다.
- allocation rate, heap, GC pause와 direct buffer 수명을 측정합니다.
- mutable object를 여러 thread가 암묵적으로 공유하지 않습니다.
- timeout task와 session 참조가 room 종료 뒤 남지 않게 합니다.

### Spring Boot가 맞는 위치

적합한 예:

- account와 authentication API
- lobby와 matchmaking 제어 API
- admin, health와 configuration API
- match result와 reward service
- 운영 도구

반드시 사용할 필요가 없는 예:

- fixed tick의 hot loop
- packet parsing과 message별 dispatch
- room state의 모든 update

하나의 process에 함께 둘 수는 있지만 executor, lifecycle과 실패 범위를 분리해서 설명해야 합니다.

## Python의 역할

Python은 다음 도구에 적합합니다.

- bot client와 load generator
- protocol fixture 생성
- replay와 state hash 분석
- log와 metric 검사
- 배포 전 smoke test

Python으로 authoritative server를 구현할 수 없다는 뜻은 아닙니다. 다만 성능과 runtime 동작을 별도로 측정해야 하며, 이 저장소는 Python production server의 합격 기준을 제공하지 않습니다.

## 공통 fixture

언어별 결과를 비교하려면 가능한 한 같은 입력 형식을 사용합니다.

- `initial-state.json`
- `commands.jsonl`
- `network-events.jsonl`
- `expected-checkpoints.json`
- `expected-audit-events.jsonl`

field 순서와 floating-point 직렬화 차이를 없앨 정규화 규칙을 기록합니다.

## 선택 기준

처리량 하나만 보고 언어를 선택하지 않습니다.

- 기존 팀과 codebase
- 필요한 library와 platform
- profiling과 debugging 도구
- memory와 latency 요구
- build와 release 운영 능력
- account와 lobby service 연결 방식

두 언어를 모두 선행 학습할 필요는 없습니다. 실제 프로젝트와 팀 표준에 맞는 profile 하나를 선택합니다.
