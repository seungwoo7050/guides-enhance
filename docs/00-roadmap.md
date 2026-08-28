# Spring Boot 백엔드 개발 로드맵

이 문서는 Spring Boot 백엔드 개발을 위한 문서 사용 시점과 프로젝트 완료 뒤 역량 검증 기준을 정리합니다. 전체 문서를 먼저 읽는 방식은 권장하지 않습니다. 프로젝트를 시작하는 데 필요한 최소 문서만 읽고, 나머지는 구현할 기능이 실제로 등장했을 때 확인합니다.

## 전제 지식

이 저장소는 다음 내용을 이미 알고 있다고 가정합니다.

- Java 17 이상 문법, record, collection, 예외 처리와 JUnit
- Maven 프로젝트를 빌드하고 테스트하는 방법
- HTTP method, status, header, JSON의 기본 의미
- 관계형 데이터베이스의 table, key, constraint, transaction 기초
- 필요한 경우 Docker 컨테이너를 실행할 수 있는 환경

이 저장소는 Java 문법, SQL 일반 이론, 분산 시스템 일반 이론, 서버 배포 전체를 다시 설명하지 않습니다.

## 최종 학습 모델

```text
Stable Core Guide
→ Actual Project
→ JIT Guide
→ Project PASS
→ Competency Suite
→ 필요한 문서만 Rewind
```

Actual Project는 이 저장소 밖에서 진행합니다. 이 저장소는 특정 프로젝트의 요구 사항을 기준으로 Stable Core를 늘리지 않습니다.

## Stable Core Guide

다음 세 문서는 모든 Spring Boot 백엔드 프로젝트에 들어가기 전에 읽습니다.

| 순서 | 문서 | 프로젝트 시작 전에 알아야 하는 이유 |
|---:|---|---|
| 1 | [`01-spring-core/01-application-context-and-lifecycle.md`](01-spring-core/01-application-context-and-lifecycle.md) | Spring이 객체를 만들고 연결하는 방식, singleton 상태, Bean 수명과 proxy 적용 조건을 이해해야 합니다. |
| 2 | [`01-spring-core/02-configuration-profiles-and-readiness.md`](01-spring-core/02-configuration-profiles-and-readiness.md) | 설정을 타입으로 받고 시작 단계에서 잘못된 값을 거부하며, 시작과 종료 시 자원 수명을 관리해야 합니다. |
| 3 | [`02-web-and-security/01-mvc-validation-and-problem-detail.md`](02-web-and-security/01-mvc-validation-and-problem-detail.md) | HTTP 입력을 검증하고 Controller, service, 오류 응답이 맡을 일을 나누어야 합니다. |

인증, 데이터 저장, 메시지 브로커, 캐시는 특정 프로젝트에서만 필요할 수 있으므로 Stable Core에 포함하지 않습니다.

## JIT / Rewind Guide

### 인증과 권한

| 문서 | 읽는 시점 |
|---|---|
| [`02-web-and-security/02-spring-security-request-model.md`](02-web-and-security/02-spring-security-request-model.md) | 인증 방식, `SecurityFilterChain`, URL 권한을 구현하기 직전 |
| [`02-web-and-security/03-authentication-authorization-and-csrf.md`](02-web-and-security/03-authentication-authorization-and-csrf.md) | 객체 소유권, 역할 기반 변경, cookie 인증과 CSRF를 구현할 때 |

### 데이터 저장과 캐시

| 문서 | 읽는 시점 |
|---|---|
| [`03-persistence-and-cache/01-jpa-transactions-and-locking.md`](03-persistence-and-cache/01-jpa-transactions-and-locking.md) | 여러 DB 변경을 한 transaction으로 처리하거나 동시 변경을 제어할 때 |
| [`03-persistence-and-cache/02-flyway-and-schema-integration.md`](03-persistence-and-cache/02-flyway-and-schema-integration.md) | 운영 스키마와 migration을 처음 추가하거나 변경할 때 |
| [`03-persistence-and-cache/03-spring-data-redis.md`](03-persistence-and-cache/03-spring-data-redis.md) | Redis를 cache, rate limit, 임시 조정 수단으로 도입할 때 |

### 메시징과 백그라운드 작업

| 문서 | 읽는 시점 |
|---|---|
| [`04-distributed-adapters/01-spring-kafka-and-avro.md`](04-distributed-adapters/01-spring-kafka-and-avro.md) | Kafka producer, consumer, serializer, acknowledgement를 구현할 때 |
| [`04-distributed-adapters/02-outbox-and-scheduling.md`](04-distributed-adapters/02-outbox-and-scheduling.md) | DB 저장과 메시지 발행을 분리하거나 예약 작업으로 Outbox를 처리할 때 |

### 외부 시스템 호출

| 문서 | 읽는 시점 |
|---|---|
| [`04-distributed-adapters/03-resilience4j-http-clients.md`](04-distributed-adapters/03-resilience4j-http-clients.md) | 외부 HTTP 호출에 timeout, 재시도, 오류 변환, Circuit Breaker를 적용할 때 |

### 테스트와 운영 확인

| 문서 | 읽는 시점 |
|---|---|
| [`05-quality-and-operations/01-test-boundaries-testcontainers-and-wiremock.md`](05-quality-and-operations/01-test-boundaries-testcontainers-and-wiremock.md) | mock, MockMvc, Testcontainers, WireMock 중 어떤 테스트를 사용할지 정할 때 |
| [`05-quality-and-operations/02-actuator-metrics-logging-and-tracing.md`](05-quality-and-operations/02-actuator-metrics-logging-and-tracing.md) | readiness, metric, 구조화 로그와 trace 정보를 추가할 때 |

프로젝트 완료 뒤 exercise가 실패했다면 실패 원인과 직접 관련된 문서만 다시 읽습니다. 예를 들어 동시 재고 차감에서 최종 수량이 틀리면 JPA 트랜잭션 문서를 다시 확인하고, 409 응답 때문에 Circuit Breaker가 열리면 HTTP 클라이언트 문서를 다시 확인합니다.

## 필수 Competency Suite

다음 네 프로젝트는 실제 프로젝트를 통과한 뒤 수행합니다.

| 프로젝트 | 분류 | 검증 항목 |
|---|---|---|
| [`request-preview-api`](../exercises/request-preview-api/) | CORE COMPETENCY | 설정 바인딩, 시작 단계 검증, 요청 본문 검증, 업무 규칙 검사, `ProblemDetail` 응답 |
| [`project-access-api`](../exercises/project-access-api/) | CORE COMPETENCY | 인증, URL 권한, 객체 소유권, CSRF, 401·403 구분 |
| [`inventory-reservation`](../exercises/inventory-reservation/) | CORE COMPETENCY | Flyway, JPA transaction, 비관적 잠금, DB 제약, 동시성 테스트 |
| [`policy-decision-client`](../exercises/policy-decision-client/) | CORE COMPETENCY | timeout, 제한된 재시도, 요청 식별자 유지, 실패 분류, Circuit Breaker |

### 수행 방법

1. 실제 프로젝트의 빌드, 테스트와 실행 검증을 먼저 통과합니다.
2. exercise에서는 README, 외부 동작, 테스트만 확인합니다.
3. Guide를 다시 읽거나 다른 exercise의 구현을 복사하지 않고 구현합니다.
4. 프로젝트의 테스트를 실행합니다.
5. 실패하면 해당 원인을 설명할 수 있는 문서만 다시 읽습니다.
6. 같은 exercise를 다시 구현하거나 수정해 통과시킵니다.

## 필수 Suite에서 제외한 프로젝트

| 프로젝트 | 분류 | 제외 이유 |
|---|---|---|
| [`idempotent-operation-outbox`](../exercises/idempotent-operation-outbox/) | SPECIALIZATION | Redis 조회 힌트, advisory lock, Outbox 재시도와 scheduler를 함께 다루며 모든 백엔드 프로젝트에 필요한 능력은 아닙니다. |
| [`kafka-avro-contract`](../exercises/kafka-avro-contract/) | SPECIALIZATION | Kafka와 Avro를 사용하는 프로젝트에서만 필요한 메시지 형식과 offset 처리 방식을 검증합니다. |
| [`publication-service`](../exercises/publication-service/) | PROJECT-SCALE INTEGRATION | 여러 기능을 한 서비스에 통합한 프로젝트이므로 외부 실제 프로젝트를 통과한 뒤 다시 필수로 수행하면 역할이 겹칩니다. |

`REDUNDANT`로 분류한 exercise는 없습니다. 세 프로젝트 모두 필수 Suite에는 들어가지 않지만 독립적인 기술 주제를 검증하므로 저장소에 유지합니다.

## 최종 완료 기준

다음 조건을 모두 만족하면 이 학습 경로를 마친 것으로 봅니다.

- Stable Core 세 문서를 읽고 각 문서의 확인 질문에 답할 수 있습니다.
- 외부 실제 프로젝트가 빌드, 테스트, 실행 검증을 통과했습니다.
- 프로젝트에서 사용한 기능에 해당하는 JIT 문서를 필요한 시점에 읽었습니다.
- 필수 Competency Suite 네 프로젝트를 Guide 없이 구현해 테스트를 통과했습니다.
- 실패했던 exercise가 있다면 관련 문서를 다시 읽고 실패 원인을 설명한 뒤 재시도해 통과했습니다.

프로젝트에 사용하지 않은 JIT 문서와 전문 exercise는 완료 조건이 아닙니다.
