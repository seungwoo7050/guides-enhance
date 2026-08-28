# Actuator, metric, logging과 tracing

> 읽는 시점: 실제 프로젝트에 health endpoint, 업무 metric, 구조화 로그, trace 정보를 추가할 때

운영 신호는 장애가 발생한 뒤 원인을 추측하기 위한 장식이 아닙니다. 애플리케이션이 요청을 받을 준비가 되었는지, 어떤 처리가 실패했는지, 재시도가 쌓이는지 판단할 수 있어야 합니다.

## liveness와 readiness를 따로 노출합니다

liveness는 process를 재시작해야만 회복할 수 있는 상태를 나타냅니다. 일시적인 Kafka 지연, 외부 API 오류, Outbox backlog를 liveness 실패로 만들면 재시작이 반복될 수 있습니다.

readiness는 새 요청을 받아도 되는지 나타냅니다. 다음 상태는 readiness 실패로 처리할 수 있습니다.

- 필수 migration 실패
- 요청 처리에 필요한 로컬 자원 초기화 실패
- 정상 종료를 시작해 새 요청을 받지 않는 상태

health 요청마다 느린 외부 API를 동기 호출하지 않습니다. 외부 시스템 장애는 별도 metric과 최근 상태로 확인합니다.

Actuator endpoint의 공개 범위를 제한합니다. health의 필요한 정보만 공개하고 환경 변수, 설정, heap 정보는 인증 없이 노출하지 않습니다.

## 로그에는 판단에 필요한 필드를 남깁니다

구조화 로그에는 다음과 같은 값을 사용할 수 있습니다.

```text
timestamp, level, service,
traceId, spanId,
operation, actorId, aggregateId,
errorCode, latencyMs
```

- 같은 예외의 stack trace를 Controller, service, client에서 반복 기록하지 않습니다.
- password, token, 비밀 key, 요청 본문 전체를 기록하지 않습니다.
- 시간과 금액에는 단위를 포함합니다.
- actor ID, aggregate ID는 metric tag가 아니라 로그 필드로 둡니다.
- idempotency key 원문은 민감도와 보관 기간을 검토한 뒤 제한적으로 기록합니다.

오류를 application 의미로 바꾼 위치에서 `errorCode`를 남기면 HTTP 응답, 로그, metric을 같은 원인으로 연결하기 쉽습니다.

## 업무 처리 결과를 metric으로 만듭니다

JVM과 HTTP 기본 metric만으로는 업무 처리 상태를 알기 어렵습니다. 값 종류가 제한된 metric을 추가합니다.

- 요청 성공, 업무 거절, 의존성 실패 수
- DB connection pool 사용량과 대기 수
- Redis 적중, 미적중, 대체 처리, 실패 수
- Outbox 대기 행 수와 가장 오래된 행의 나이
- Kafka 처리, retry, dead-letter 수
- Circuit Breaker 상태와 외부 호출 차단 수
- 권한 거절 수

user ID, request ID, entity ID처럼 값이 계속 늘어나는 정보를 tag로 넣지 않습니다. 이런 값은 로그나 trace에서 조회합니다.

## trace ID와 업무 식별자를 구분합니다

trace ID는 한 요청이 여러 서비스를 지나가는 과정을 연결합니다. idempotency key, event ID, aggregate ID는 업무 처리 자체를 식별합니다.

trace가 끊기거나 새로 시작되어도 중복 방지와 event 식별은 유지되어야 합니다. 외부에서 받은 trace 헤더는 형식을 검증하고 신뢰할 수 없는 값을 내부 기준값처럼 사용하지 않습니다.

동기 HTTP 요청에서 비동기 event로 trace 정보를 전달할 수 있지만, event ID와 aggregate ID를 trace ID로 대체하지 않습니다.

## metric과 health도 테스트합니다

Micrometer와 Actuator 설정은 다음 항목을 테스트할 수 있습니다.

- 성공과 실패에서 예상한 counter가 증가합니다.
- 예외가 발생해도 timer가 종료됩니다.
- 고유 사용자나 요청 ID가 tag에 들어가지 않습니다.
- readiness와 liveness에 의도한 항목만 포함됩니다.
- 외부 의존성 장애가 불필요한 liveness 실패를 만들지 않습니다.

통합 테스트에서는 HTTP 응답과 DB 상태뿐 아니라 metric 변화도 함께 확인할 수 있습니다. 다만 metric을 테스트하기 위해 production code에 고유 식별자를 tag로 추가하지 않습니다.

## Rewind가 필요한 징후

- health는 성공하지만 필수 migration이 실패했습니다.
- 외부 API가 잠시 느려지자 liveness가 실패해 재시작이 반복됩니다.
- 같은 예외가 Controller, service, client에서 각각 stack trace로 기록됩니다.
- user ID나 request ID가 metric tag에 포함되어 값 종류가 계속 늘어납니다.
- Outbox backlog가 쌓여도 확인할 metric이 없습니다.
- 오류 응답의 `errorCode`와 로그 원인을 연결할 수 없습니다.

여러 운영 신호를 한 서비스에서 확인하려면 선택적 통합 프로젝트인 [`publication-service`](../../exercises/publication-service/)를 참고할 수 있습니다. 이 프로젝트는 필수 competency suite에는 포함되지 않습니다.
