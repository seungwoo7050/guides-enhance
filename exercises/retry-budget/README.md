# Deadline 기반 재시도 실행기

## 개요

업무 거절과 일시 장애를 구분하고, 하나의 deadline 안에서 backoff, Circuit Breaker와 DLQ 재처리를 수행하는 Java 라이브러리입니다.

## 주요 기능

- 모든 재시도에서 처음 받은 operation ID를 유지합니다.
- 업무 거절은 재시도하지 않고 Circuit Breaker의 실패 횟수에도 포함하지 않습니다.
- 다음 backoff가 deadline을 넘으면 새 호출을 시작하지 않습니다.
- `CLOSED`, `OPEN`, `HALF_OPEN` 상태와 probe 실패 후 새 OPEN 시간을 처리합니다.
- DLQ 메시지는 재처리가 성공한 뒤에만 제거합니다.

## 구성

`VirtualClock`이 테스트에서 사용할 시간을 제공하고 `CircuitBreaker`가 일시 장애 횟수와 probe 시각을 저장합니다. `Executor`가 deadline 안에서 `Dependency` 호출을 반복하며 `DeadLetterQueue`는 실패한 입력을 보존합니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.retry.RetryBudgetTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

예외 종류가 재시도 여부를 결정합니다. HALF_OPEN 호출에서 업무 거절을 받았다는 것은 의존 서비스가 정상적으로 응답했다는 뜻이므로 업무 결과는 전달하되 Circuit Breaker는 닫습니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 실패 종류 구분 | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — failure types` |
| 2 | 결정적 가상 시계 | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — VirtualClock` |
| 3 | 의존 서비스 호출 | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — Dependency` |
| 4 | Circuit Breaker 상태 | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — CircuitBreaker` |
| 4-1 | OPEN 대기 시간과 HALF_OPEN probe | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — CircuitBreaker.beforeCall` |
| 4-2 | 응답 후 실패 횟수 초기화 | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — CircuitBreaker.recordSuccess` |
| 4-3 | 일시 장애만 실패로 집계 | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — CircuitBreaker.recordTransientFailure` |
| 5 | DLQ 재처리 입력 | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — DeadLetter` |
| 5-1 | 재처리 성공 전까지 메시지 보존 | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — DeadLetterQueue` |
| 5-2 | 재처리 성공 후 메시지 제거 | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — DeadLetterQueue.replayNext` |
| 6 | deadline 안에서 재시도 실행 | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — Executor` |
| 6-1 | 같은 operation ID로 일시 장애만 재시도 | `src/main/java/dev/guides/distributed/retry/RetryBudget.java — Executor.execute` |

## 범위와 제한

- jitter와 실제 scheduler는 포함하지 않습니다.
- Circuit Breaker 상태를 프로세스 밖에 저장하지 않습니다.
- 동시에 여러 HALF_OPEN probe가 실행되는 상황은 모델링하지 않습니다.
