# Publication Service

인증된 `EDITOR` 사용자가 publication을 생성하는 Spring Boot 서비스입니다. 같은 사용자가 같은 `Idempotency-Key`를 다시 보내면 PostgreSQL에 저장된 기존 결과를 반환합니다. 새 요청은 외부 판단 API를 거친 뒤 publication과 Outbox event를 같은 transaction에 저장하고, commit 후 Redis에 결과를 cache합니다.

## 주요 기능

- HTTP Basic 인증과 `EDITOR` 전용 생성 API를 제공합니다.
- `Idempotency-Key` header와 요청 본문을 검증합니다.
- 사용자와 멱등성 key를 결합해 PostgreSQL advisory transaction lock을 얻습니다.
- publication과 Outbox event를 같은 transaction에 저장합니다.
- PostgreSQL 완료 결과를 기준으로 사용하고 Redis는 조회 cache로만 사용합니다.
- 외부 판단 API에 timeout과 Circuit Breaker를 적용합니다.
- 409 업무 거절과 5xx·통신 장애를 구분합니다.
- 발행 대기 Outbox event를 Kafka에 보낸 뒤 별도 transaction으로 완료 처리합니다.
- 생성, 중복, 판단 거절, cache 실패 횟수를 Micrometer counter로 기록합니다.
- PostgreSQL, Redis, WireMock을 사용하는 통합 테스트를 제공합니다.

## 요청 처리 순서

```text
HTTP 인증과 역할 검사
→ header와 body 검증
→ Redis 완료 결과 조회
→ PostgreSQL 완료 결과 조회
→ 새 요청일 때 외부 판단 API 호출
→ advisory lock 획득
→ PostgreSQL 완료 결과 재조회
→ publication과 Outbox event 저장
→ commit
→ Redis cache 저장
→ 201 또는 200 응답
```

## 구성

- `PublicationController`는 인증 사용자, 멱등성 header, 요청 본문을 읽고 service를 호출합니다.
- `PublicationService`는 Redis 조회, DB 조회, 외부 판단, 쓰기 순서를 정합니다.
- `PublicationWriter`는 사용자와 key로 advisory lock을 얻은 뒤 DB를 다시 확인하고 publication과 Outbox event를 저장합니다.
- `PublicationCache`는 사용자와 key를 구분해 SHA-256 기반 Redis key를 만들고 TTL과 함께 결과를 저장합니다.
- `PolicyClient`는 409를 업무 거절로, timeout·5xx·잘못된 응답을 의존성 장애로 반환합니다.
- `OutboxPublisher`는 Kafka 발행 성공 뒤 `OutboxCompletionService`의 별도 transaction으로 `published_at`을 기록합니다.
- `PublicationMetrics`는 결과별 counter를 관리합니다.

## 요구 사항

- JDK 21
- Maven 3.9 이상
- Docker 호환 컨테이너 실행 환경
- 애플리케이션을 직접 실행할 때 PostgreSQL, Redis, 외부 판단 API
- Outbox publisher를 활성화할 때 Kafka broker

## 빌드와 테스트

```sh
mvn clean test
mvn clean package
```

통합 테스트는 실제 PostgreSQL·Redis container와 process 내부 WireMock을 사용해 다음 내용을 확인합니다.

- 인증 없음, 역할 부족, 잘못된 멱등성 key를 각각 401, 403, 400으로 거부합니다.
- 첫 생성은 201과 `Location`을 반환하고 publication, Outbox, 양수 TTL cache, 생성 counter를 남깁니다.
- Redis를 비운 뒤 외부 판단을 거절 상태로 바꿔도 DB에 저장된 기존 결과를 먼저 반환합니다.
- 동시 요청 8개가 publication 하나와 Outbox event 하나로 수렴합니다.
- 외부 판단 API의 409는 DB를 바꾸지 않고 Circuit Breaker 실패에도 포함되지 않습니다.
- 외부 판단 API의 500은 503으로 변환되고 Circuit Breaker 실패로 기록됩니다.

## 실행

기본 설정에는 datasource URL과 Redis host를 고정하지 않습니다. 최소한 다음 값을 환경에 맞게 제공합니다.

```sh
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/publications \
SPRING_DATASOURCE_USERNAME=publications \
SPRING_DATASOURCE_PASSWORD=publications \
SPRING_DATA_REDIS_HOST=localhost \
POLICY_CLIENT_BASE_URL=http://localhost:9999 \
mvn spring-boot:run
```

로컬 확인용 계정:

- `editor` / `editor-password`: `EDITOR`
- `reader` / `reader-password`: `READER`

생성 요청 예시:

```sh
curl -i \
  -u editor:editor-password \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: publication-001' \
  -d '{"title":"Architecture Notes","source":"https://example.test/source"}' \
  http://localhost:8080/api/publications
```

## 주요 설계 판단

- PostgreSQL 행과 unique constraint가 완료 결과의 기준입니다. Redis가 비어 있거나 실패해도 DB에서 기존 결과를 찾습니다.
- 멱등성 식별자에 사용자 ID를 포함해 서로 다른 사용자가 같은 key를 보내도 결과가 섞이지 않게 합니다.
- advisory lock을 얻은 뒤 DB를 다시 조회하므로 동시 요청은 publication과 Outbox event 하나로 수렴합니다.
- Redis 저장 실패는 이미 commit된 생성 결과를 실패로 바꾸지 않습니다.
- 409 업무 거절은 외부 시스템 장애가 아니므로 Circuit Breaker 실패에서 제외합니다.
- Kafka 발행 성공과 `published_at` 저장 사이에 process가 종료되면 같은 event가 다시 발행될 수 있습니다. consumer는 event ID를 이용해 중복 처리를 막아야 합니다.

## 구현 순서

| 순서 | 구현 내용 | 기준 파일 |
|---:|---|---|
| 0 | 웹·보안·저장소·메시징을 포함한 독립 서비스 구성 | `pom.xml` |
| 1 | DB·Redis·판단 API·Kafka·관측 설정 연결 | `src/main/resources/application.yml` |
| 2 | publication과 Outbox 저장 스키마 정의 | `src/main/resources/db/migration/V1__create_publication_and_outbox.sql` |
| 3 | publication 저장 상태와 응답 변환 | `src/main/java/dev/guides/spring/publication/PublicationEntity.java` |
| 3-1 | Outbox 대기·발행 완료 상태 관리 | `src/main/java/dev/guides/spring/publication/OutboxEventEntity.java` |
| 4 | 업무 거절과 의존성 장애 구분 | `src/main/java/dev/guides/spring/publication/PolicyClient.java` |
| 5 | key별 잠금 후 publication과 Outbox 저장 | `src/main/java/dev/guides/spring/publication/PublicationWriter.java` |
| 6 | 사용자별 Redis cache key와 TTL 관리 | `src/main/java/dev/guides/spring/publication/PublicationCache.java` |
| 7 | cache·DB·판단 API·쓰기 순서 조정 | `src/main/java/dev/guides/spring/publication/PublicationService.java` |
| 8 | 인증 사용자와 멱등성 key를 생성 요청에 연결 | `src/main/java/dev/guides/spring/publication/PublicationController.java` |
| 8-1 | 입력·업무·의존성 실패를 HTTP 오류로 변환 | `src/main/java/dev/guides/spring/publication/PublicationProblemAdvice.java` |
| 9 | EDITOR 전용 무상태 API 보안 설정 | `src/main/java/dev/guides/spring/publication/SecurityConfiguration.java` |
| 10 | Kafka 발행 성공 후 Outbox 완료 기록 | `src/main/java/dev/guides/spring/publication/OutboxPublisher.java` |

## 범위와 제한

- 메모리 내 사용자는 로컬 확인용이며 운영 인증 시스템을 대신하지 않습니다.
- 현재 API는 무상태 HTTP Basic 요청만 받으므로 CSRF를 비활성화했습니다.
- Redis와 DB에 모두 결과가 없을 때는 advisory lock을 얻기 전에 외부 판단 API를 호출합니다. 동시 요청에서 외부 호출이 중복될 수 있지만 publication과 Outbox 중복은 발생하지 않습니다.
- Outbox publisher는 claim, lease, `SKIP LOCKED`, 재시도 메타데이터, dead-letter 처리를 구현하지 않습니다.
- Kafka consumer와 event schema는 포함하지 않습니다.
- Redis value와 Outbox payload의 schema 변경 절차는 구현하지 않습니다.
