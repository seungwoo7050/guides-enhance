# Idempotent Operation Outbox

PostgreSQL에 저장된 완료 결과를 멱등 처리의 기준으로 사용하고, Redis는 빠른 조회를 위한 힌트로만 사용하는 Spring Boot 프로젝트입니다. 새 처리 결과와 Outbox event를 같은 transaction에 저장하고, 발행 실패는 Outbox 행에 기록해 다시 시도합니다.

## 주요 기능

- 멱등성 key별 PostgreSQL advisory transaction lock을 사용합니다.
- 잠금을 얻은 뒤 DB를 다시 조회해 동시 요청을 하나의 결과로 모읍니다.
- 새 operation과 Outbox event를 같은 transaction에 저장합니다.
- Redis 조회와 저장이 실패해도 DB 결과의 정확성이 유지됩니다.
- DB commit 뒤에만 Redis cache를 갱신합니다.
- 발행할 시점이 된 Outbox 행을 제한된 개수로 조회합니다.
- 발행 성공 시 완료 시각을, 실패 시 시도 횟수·오류·다음 시각을 저장합니다.
- scheduler가 설정된 간격으로 Outbox 발행을 실행합니다.
- PostgreSQL과 Redis Testcontainers로 동시성과 복구 동작을 검증합니다.

## 구성

- `operation_record`의 unique constraint가 같은 멱등성 key의 중복 완료 행을 최종적으로 막습니다.
- `OperationService`는 Redis를 먼저 확인하되, 값이 없거나 Redis를 사용할 수 없으면 advisory lock을 얻고 PostgreSQL을 다시 조회합니다.
- 새 `OperationRecord`와 `OutboxEvent`는 같은 transaction에서 저장됩니다.
- `RedisIdempotencyHintStore`는 10분 TTL로 완료 결과를 보관하지만 결과 존재 여부를 최종 판단하지 않습니다.
- `OutboxPublisher`는 발행 시점이 된 event를 처리하고 성공 또는 재시도 상태를 DB에 남깁니다.
- `OutboxScheduler`는 주기 실행만 맡고 실제 발행 처리는 `OutboxPublisher`에 위임합니다.
- `EventSink`는 현재 로그로 출력하며 실제 broker adapter로 교체할 수 있습니다.

## 요구 사항

- JDK 21
- Maven 3.9 이상
- Docker 호환 컨테이너 실행 환경
- 애플리케이션을 직접 실행할 때 PostgreSQL과 Redis

## 빌드와 테스트

```sh
mvn clean test
mvn clean package
```

통합 테스트는 다음 내용을 확인합니다.

- commit된 결과가 Redis에 저장되고 같은 key의 재요청에서 재사용됩니다.
- Redis 읽기와 쓰기가 모두 실패해도 같은 key로 보낸 동시 요청 20개가 operation 하나와 Outbox 행 하나로 수렴합니다.
- 첫 발행 실패가 시도 횟수와 오류를 남기고, 다음 실행에서 같은 Outbox 행이 성공 처리됩니다.
- scheduler가 실행되면 publisher를 정확히 호출합니다.

## 실행

기본 연결 정보는 다음과 같습니다.

- PostgreSQL: `jdbc:postgresql://localhost:5432/idempotency`
- PostgreSQL 사용자 이름과 비밀번호: `idempotency`
- Redis: `localhost:6379`

의존 서비스를 준비한 뒤 실행합니다.

```sh
mvn spring-boot:run
```

기본 `LoggingEventSink`는 발행된 Outbox event의 ID와 종류를 로그에 남깁니다. `OperationService.apply`가 업무 진입점이며 HTTP Controller는 포함하지 않습니다.

## 주요 설계 판단

- Redis lock이나 cache hit를 완료 결과의 기준으로 사용하지 않습니다. Redis가 없어도 PostgreSQL advisory lock과 unique constraint가 중복 생성을 막습니다.
- cache는 commit 뒤에 갱신합니다. Redis 저장 실패가 이미 commit된 operation을 실패로 바꾸지 않습니다.
- Outbox 발행 실패는 operation transaction을 되돌리지 않습니다. 실패 내용을 Outbox 행에 남기고 다음 실행에서 다시 처리합니다.
- 현재 구현은 event 발행과 성공·실패 상태 갱신을 한 publisher transaction에서 처리합니다. 여러 instance와 높은 처리량을 지원하려면 claim, lease, `SKIP LOCKED` 같은 행 선점 방식이 추가로 필요합니다.

## 구현 순서

| 순서 | 구현 내용 | 기준 파일 |
|---:|---|---|
| 0 | 독립 실행 가능한 JPA·Redis 통합 테스트 구성 | `pom.xml` |
| 1 | 처리 결과와 Outbox 재시도 상태 스키마 정의 | `src/main/resources/db/migration/V1__create_operation_and_outbox.sql` |
| 2 | PostgreSQL 완료 행을 멱등 처리 결과로 사용 | `src/main/java/dev/guides/spring/idempotency/OperationRecord.java` |
| 2-1 | Outbox 발행·재시도 상태 전이 관리 | `src/main/java/dev/guides/spring/idempotency/OutboxEvent.java` |
| 3 | Redis를 TTL이 있는 조회 힌트로 제한 | `src/main/java/dev/guides/spring/idempotency/RedisIdempotencyHintStore.java` |
| 4 | key별 잠금 후 DB 재조회와 operation·Outbox 저장 | `src/main/java/dev/guides/spring/idempotency/OperationService.java` |
| 4-1 | commit 후 Redis에 결과 저장 | `src/main/java/dev/guides/spring/idempotency/OperationService.java` |
| 5 | Outbox 발행 성공·실패 결과 저장 | `src/main/java/dev/guides/spring/idempotency/OutboxPublisher.java` |
| 5-1 | 설정된 주기로 Outbox 발행 실행 | `src/main/java/dev/guides/spring/idempotency/OutboxScheduler.java` |

## 범위와 제한

- HTTP API와 실제 message broker adapter는 포함하지 않습니다.
- PostgreSQL advisory lock key의 hash 충돌을 줄이기 위한 별도 namespace는 구현하지 않습니다.
- 여러 instance가 같은 event를 가져가지 않도록 하는 claim이나 lease는 구현하지 않습니다.
- 페이로드는 문자열 JSON이며 스키마 레지스트리와 타입이 있는 이벤트 코덱을 사용하지 않습니다.
