# 테스트 범위, Testcontainers와 WireMock

> 읽는 시점: 실제 프로젝트에서 단위 테스트, MockMvc, Testcontainers, WireMock 중 무엇을 사용할지 정할 때

좋은 테스트는 모든 의존성을 실제로 실행하는 테스트도 아니고, 모든 대상을 mock으로 바꾸는 테스트도 아닙니다. 확인하려는 동작을 실제로 재현할 수 있는 가장 작은 실행 범위를 선택해야 합니다.

## 확인할 질문에 맞는 테스트를 선택합니다

| 확인할 내용 | 적절한 테스트 |
|---|---|
| 순수 계산과 상태 변경 규칙 | JUnit 단위 테스트 |
| JSON 변환, validation, `ProblemDetail` | MockMvc 또는 `@WebMvcTest` |
| Security filter와 method 권한 | MockMvc + `spring-security-test` |
| JPA query와 transaction | 실제 PostgreSQL Testcontainer |
| 빈 DB에서 migration 적용 | Spring Context + PostgreSQL Testcontainer |
| Redis 직렬화, TTL, 장애 처리 | Redis Testcontainer |
| 외부 HTTP status, timeout, 잘못된 응답 | WireMock |
| Kafka serializer, listener, acknowledgement | 실제 또는 embedded broker |
| Bean과 설정 전체 연결 | 범위를 제한한 `@SpringBootTest` |

모든 테스트를 `@SpringBootTest`로 만들면 느리고 실패 원인을 찾기 어렵습니다. 반대로 실제 DB lock이나 HTTP timeout을 mock만으로 확인했다고 판단해서도 안 됩니다.

## Testcontainers 실패를 성공으로 바꾸지 않습니다

필수 통합 테스트가 Docker를 사용할 수 없을 때 조용히 skip되면 개발자마다 테스트 성공의 의미가 달라집니다. 해당 기능을 검증하는 데 container가 필수라면 시작하지 못한 것도 실패로 처리합니다.

- 테스트마다 독립적인 DB, key, topic 이름을 사용합니다.
- container reuse가 없어도 통과해야 합니다.
- migration은 빈 DB에서 첫 version부터 적용합니다.
- 테스트가 만든 thread, executor, client를 종료합니다.
- 실패하더라도 container cleanup이 실행되게 합니다.

image tag만 사용하면 같은 이름의 이미지가 나중에 달라질 수 있습니다. 재현성이 중요한 테스트는 digest를 고정할 수 있습니다. 다만 버전을 올릴 때는 코드, migration, driver 호환성을 함께 확인해야 합니다.

## 동시성 테스트는 시작 시점을 맞춥니다

thread를 많이 만들고 `sleep`하는 방식은 실제 경쟁 구간을 보장하지 않습니다. 준비용 latch와 시작용 latch 또는 barrier를 사용합니다.

```text
모든 worker 생성
→ 준비 완료 확인
→ 동시에 시작
→ 모든 Future 결과 회수
→ 최종 상태 검사
→ executor 종료
```

각 대기에는 timeout을 둡니다. 테스트가 실패했을 때 무한히 멈추는 대신 어느 단계에서 완료되지 않았는지 드러나야 합니다.

동시성 테스트는 응답만 보지 않고 다음 값을 함께 확인합니다.

- 성공한 요청 수
- 최종 DB 값
- 생성된 행 수
- Outbox 행 수
- Redis key 수와 TTL
- 외부 호출 횟수
- executor 종료 여부

## 실패 뒤 남은 상태를 확인합니다

오류 응답이 맞더라도 일부 상태가 이미 바뀌었다면 테스트가 충분하지 않습니다.

예를 들어 외부 정책 서비스가 500을 반환한 경우 다음을 함께 확인합니다.

```text
HTTP 503
publication 행 0개
Outbox 행 0개
cache key 없음
Circuit Breaker 실패 1회
```

어떤 실패에서 무엇이 남아도 되는지를 테스트 이름과 assertion으로 분명히 합니다.

## WireMock은 호출 횟수와 요청 내용까지 검사합니다

외부 HTTP 테스트에서는 반환된 예외만 확인하지 않습니다.

- 어떤 URL과 method가 호출되었는지
- request body와 header가 유지되었는지
- 재시도 횟수가 상한을 넘지 않았는지
- timeout과 연결 종료가 같은 실패로 처리되는지
- 업무 4xx가 재시도나 Circuit Breaker 실패에 포함되지 않는지

쓰기 요청의 재시도 테스트에서는 같은 idempotency key나 request ID가 유지되는지도 확인합니다.

## 테스트 이름은 보장할 내용을 드러냅니다

`works()` 같은 이름보다 실패하면 어떤 구현이 잘못되었는지 알 수 있는 이름을 사용합니다.

```text
concurrentRequestsCreateOneOperation
businessDeclinesDoNotOpenCircuit
cacheMissUsesStoredDatabaseResult
csrfTokenIsRequiredForStateChange
```

주석이 필요하다면 코드가 하는 일을 반복하지 말고 어떤 잘못된 구현을 검출하는지 설명합니다.

## Rewind가 필요한 징후

- 모든 테스트가 `@SpringBootTest`이고 작은 실패도 전체 Context를 띄워야 합니다.
- JPA 잠금이나 Flyway를 mock으로만 검사합니다.
- 동시성 테스트가 `sleep`에 의존해 간헐적으로 실패합니다.
- 오류 응답만 확인하고 DB나 cache의 최종 상태를 확인하지 않습니다.
- container가 없으면 필수 테스트가 skip되어 성공으로 끝납니다.
- 외부 client 테스트가 호출 횟수와 request ID를 확인하지 않습니다.

필수 competency exercise 네 개의 테스트는 서로 다른 실행 범위를 사용합니다. exercise가 실패했을 때 구현만 고치기 전에 테스트가 실제 보장할 내용을 검사하는지도 확인합니다.
