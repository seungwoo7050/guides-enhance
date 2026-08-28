# 분산 처리의 관측 식별자

## 목표

서비스마다 로그를 많이 남기는 데서 끝내지 않고, 업무 한 건이 HTTP 요청, 명령, 이벤트와 재처리를 거치는 과정을 식별자로 연결합니다. 개별 요청을 찾는 값과 지표 집계에 사용할 값을 구분합니다.

## request ID 하나로는 부족합니다

한 request ID를 모든 단계에 복사하면 다음을 구분하기 어렵습니다.

- 사용자가 시작한 업무 한 건
- 같은 업무를 전달한 여러 HTTP 호출
- 업무가 만든 여러 event
- event를 원인으로 새로 만든 event
- 같은 event의 재전달
- 현재 상태를 가진 aggregate

식별자가 부족하면 어떤 효과가 두 번 적용되었는지, 어느 작업이 아직 `PENDING`인지 찾기 어렵습니다. 반대로 operation ID나 user ID를 metric tag로 넣으면 시계열 수가 계속 늘어납니다.

## 식별자마다 사용 기간을 구분합니다

| 식별자 | 용도 |
| --- | --- |
| `trace_id` | 동기 호출과 이어지는 비동기 처리의 추적 |
| `request_id` | HTTP 요청이나 호출 시도 한 번 |
| `operation_id` | 사용자가 시작한 업무 한 건 |
| `event_id` | 전달하는 event 한 건 |
| `correlation_id` | 관련 명령과 event 묶음 |
| `causation_id` | 현재 event를 직접 만든 명령이나 이전 event |
| `aggregate_id` | 상태를 보관하는 업무 대상 |

재시도할 때 request ID는 바뀔 수 있지만 operation ID는 유지합니다. 같은 event를 다시 전달할 때 event ID도 바꾸지 않습니다. 후속 event는 새 event ID를 만들고 causation ID로 바로 앞의 원인을 가리킵니다.

상위 시스템에서 시작된 처리를 받았다면 trace ID와 correlation ID를 그대로 사용합니다. 편의상 만든 기본값으로 전달받은 값을 덮어쓰면 안 됩니다.

## 상태 변경을 구조화해서 기록합니다

문장만 남기지 말고 검색할 필드를 따로 기록합니다.

```text
service
component
operation_id
event_id
correlation_id
causation_id
aggregate_id
state_before
state_after
outcome
attempt
elapsed_ms
```

비밀번호, token, 전체 개인정보와 payload 원문은 기록하지 않습니다. 필요한 식별자의 보존 기간과 접근 권한을 정합니다.

## metric tag는 값의 종류를 제한합니다

metric은 집계와 경보에 사용하고, 개별 ID는 log나 trace에서 찾습니다.

```text
outbox_pending_total{service,event_type}
outbox_oldest_age_seconds{service}
consumer_lag{group,topic,partition}
reconciliation_total{service,outcome}
idempotency_duplicate_total{operation_type}
dlq_messages{topic,error_class}
load_shed_total{service,reason}
```

다음 값은 보통 metric tag로 사용하지 않습니다.

```text
user_id
operation_id
event_id
reservation_id
raw_url
exception_message
```

## 업무 상태가 따라잡고 있는지 측정합니다

CPU와 HTTP latency가 정상이어도 분산 처리는 멈춰 있을 수 있습니다. 다음 값을 확인합니다.

- 가장 오래된 미발행 Outbox의 대기 시간
- `PENDING`과 `UNKNOWN`의 수와 최대 나이
- 재조정 성공·실패·수동 확인 건수
- 조회 모델의 lag와 checkpoint
- 중복 event 감지 수
- DLQ의 메시지 수와 가장 오래된 메시지
- 정본과 조회 모델의 불일치 수
- Circuit Breaker OPEN과 과부하 거절 비율

경보에는 담당자가 처음 실행할 확인 명령이나 runbook을 연결합니다.

## 흔한 잘못

- 모든 단계에 request ID 하나만 사용합니다.
- 재시도할 때 operation ID를 바꿉니다.
- 후속 event에 causation ID를 남기지 않습니다.
- operation ID와 event ID를 metric tag로 사용합니다.
- 로그에 상태 변경 전후와 결과가 없습니다.
- 프로세스 health만 보고 Outbox age와 조회 모델 lag를 보지 않습니다.
- 민감한 payload 전체를 디버깅 편의를 위해 기록합니다.

## 검증 방법

명령 한 건을 다음 순서로 처리합니다.

```text
HTTP request
→ command
→ Outbox event
→ consumer
→ projection event
```

각 단계에서 trace, operation과 correlation ID가 유지되는지 확인합니다. 후속 event의 causation ID는 이전 명령이나 event ID를 가리켜야 합니다. 중복 event는 관찰 기록을 남기되 업무 효과 횟수는 늘리지 않아야 합니다. metric registry는 고카디널리티 tag를 거절해야 합니다.

## 관련 프로젝트

[`observability-correlation`](../../exercises/observability-correlation/)은 식별자 전파, 중복 전달 기록과 metric tag allowlist를 검사합니다.

## 완료 기준

- request, operation, event, causation과 aggregate ID를 구분할 수 있습니다.
- HTTP와 event 처리 사이에서 trace와 correlation ID를 유지할 수 있습니다.
- 처리 지연과 상태 불일치를 나타내는 업무 지표를 정할 수 있습니다.
- 개별 ID를 log·trace에 남기고 metric tag에서는 제외할 수 있습니다.
