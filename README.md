# Spring Boot 백엔드 개발 가이드

이 저장소는 Java, HTTP, SQL의 기본기를 익힌 개발자가 Spring Boot 애플리케이션을 실제 프로젝트에서 구현할 때 참고하는 문서와, 프로젝트 완료 뒤 핵심 역량을 다시 확인하는 독립 실행형 예제를 제공합니다.

이 저장소 자체가 최종 프로젝트를 대신하지는 않습니다. 학습의 중심은 외부의 실제 프로젝트이며, 문서는 프로젝트 시작 전 반드시 알아야 할 최소 내용과 구현 중 필요한 주제를 나누어 제공합니다.

## 학습 순서

```text
Stable Core Guide
→ Actual Project
→ 필요한 시점에 JIT Guide
→ Project PASS
→ Competency Suite
→ 부족한 부분만 Rewind
```

- **Stable Core Guide**는 어떤 Spring Boot 백엔드 프로젝트를 시작하더라도 먼저 읽어야 하는 최소 문서입니다.
- **Actual Project**는 이 저장소 밖에서 진행하는 실제 구현 프로젝트입니다.
- **JIT Guide**는 프로젝트에서 해당 기능을 구현하기 직전이나 구현 중에 읽습니다.
- **Rewind**는 프로젝트 완료 뒤 역량 검증에서 약점이 드러난 문서만 다시 읽는 방식입니다.
- **Competency Suite**는 Guide를 다시 보지 않고 작은 독립 프로젝트를 구현해, 실제 프로젝트에서 익힌 능력을 다른 문제에도 적용할 수 있는지 확인합니다.

## Stable Core

프로젝트에 들어가기 전에 다음 세 문서를 읽습니다.

1. [`Application Context와 Bean 수명`](docs/01-spring-core/01-application-context-and-lifecycle.md)
2. [`설정, 프로필과 준비 상태`](docs/01-spring-core/02-configuration-profiles-and-readiness.md)
3. [`Spring MVC 검증과 ProblemDetail`](docs/02-web-and-security/01-mvc-validation-and-problem-detail.md)

이 세 문서는 객체 생성과 수명, 설정 검증, HTTP 요청 처리처럼 프로젝트 종류와 관계없이 필요한 Spring Boot 실행 원리를 다룹니다. 인증, 데이터베이스, Redis, Kafka 같은 기능은 모든 프로젝트에 필요한 것이 아니므로 Stable Core에 포함하지 않습니다.

## JIT / Rewind 문서

프로젝트가 해당 기능에 도달했을 때 필요한 문서만 읽습니다.

| 구현할 내용 | 문서 |
|---|---|
| 인증과 요청 권한 | [`Spring Security 요청 모델`](docs/02-web-and-security/02-spring-security-request-model.md) |
| 객체 소유권과 CSRF | [`인증, 객체 권한과 CSRF`](docs/02-web-and-security/03-authentication-authorization-and-csrf.md) |
| JPA 트랜잭션과 동시성 | [`JPA 트랜잭션과 잠금`](docs/03-persistence-and-cache/01-jpa-transactions-and-locking.md) |
| 스키마 변경 | [`Flyway와 스키마 연결`](docs/03-persistence-and-cache/02-flyway-and-schema-integration.md) |
| Redis 캐시와 임시 상태 | [`Spring Data Redis 어댑터`](docs/03-persistence-and-cache/03-spring-data-redis.md) |
| Kafka와 Avro | [`Spring Kafka와 Avro 어댑터`](docs/04-distributed-adapters/01-spring-kafka-and-avro.md) |
| Outbox와 예약 실행 | [`Outbox와 Spring 스케줄링`](docs/04-distributed-adapters/02-outbox-and-scheduling.md) |
| 외부 HTTP 호출과 Circuit Breaker | [`Resilience4j HTTP 클라이언트`](docs/04-distributed-adapters/03-resilience4j-http-clients.md) |
| 테스트 범위 선택 | [`테스트 범위, Testcontainers와 WireMock`](docs/05-quality-and-operations/01-test-boundaries-testcontainers-and-wiremock.md) |
| 상태 확인과 운영 신호 | [`Actuator, metric, logging과 tracing`](docs/05-quality-and-operations/02-actuator-metrics-logging-and-tracing.md) |

같은 문서는 프로젝트 구현 중에는 JIT 자료로, 역량 검증 실패 뒤에는 Rewind 자료로 사용합니다.

## 프로젝트 완료 뒤 역량 검증

실제 프로젝트가 테스트와 실행 검증을 모두 통과한 뒤 다음 네 프로젝트를 수행합니다. 이때 Guide를 먼저 다시 읽지 않습니다.

| 필수 프로젝트 | 확인하는 능력 |
|---|---|
| [`request-preview-api`](exercises/request-preview-api/) | 설정 검증, 요청 본문 검증, 업무 규칙 검사, 오류 응답 변환 |
| [`project-access-api`](exercises/project-access-api/) | 인증, 요청 권한, 객체 소유권, CSRF, 보안 오류 응답 |
| [`inventory-reservation`](exercises/inventory-reservation/) | JPA 트랜잭션, 행 잠금, 데이터베이스 불변식, 동시성 테스트 |
| [`policy-decision-client`](exercises/policy-decision-client/) | 외부 HTTP 오류 분류, timeout, 제한된 재시도, Circuit Breaker |

실행 순서는 다음과 같습니다.

```text
프로젝트 PASS
→ exercise의 README와 테스트만 확인
→ Guide 없이 구현
→ 테스트 실행
→ PASS: 역량 확인
→ FAIL: 관련 문서만 다시 읽고 재시도
```

다음 프로젝트는 저장소에 남겨 두지만 필수 검증에는 포함하지 않습니다.

- [`idempotent-operation-outbox`](exercises/idempotent-operation-outbox/): Redis, 멱등 처리, Outbox 재시도를 함께 다루는 심화 주제입니다.
- [`kafka-avro-contract`](exercises/kafka-avro-contract/): Kafka와 Avro를 사용하는 프로젝트에 필요한 전문 주제입니다.
- [`publication-service`](exercises/publication-service/): 여러 기능을 한 서비스에 통합한 프로젝트 규모의 예제입니다. 실제 외부 프로젝트를 마친 뒤 다시 필수로 수행할 필요는 없습니다.

## 저장소 구성

```text
.
├── .gitignore
├── README.md
├── docs/
│   ├── Stable Core 문서
│   └── JIT / Rewind 문서
└── exercises/
    ├── 필수 역량 검증 프로젝트
    ├── 전문 주제 프로젝트
    └── 통합 프로젝트 예제
```

각 `exercises/<project>/` 디렉터리는 자체 `pom.xml`, 소스, 설정, 테스트와 README를 가진 독립 프로젝트입니다. 저장소 루트의 빌드 설정이나 별도 학습 관리 도구에 의존하지 않습니다.

세부 학습 순서와 완료 기준은 [`docs/00-roadmap.md`](docs/00-roadmap.md)에서 확인합니다.
