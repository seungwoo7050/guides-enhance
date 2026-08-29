# Event delivery, concurrency와 idempotency

FaaS에서 중요한 실패는 handler가 예외를 던졌다는 사실만이 아닙니다. Event source가 언제 진행 위치를 바꾸는지, timeout 뒤 외부 write가 반영됐는지, 같은 event가 다시 왔을 때 결과가 어떻게 하나로 수렴하는지를 확인해야 합니다.

## 1. Source의 완료 시점을 먼저 찾습니다

`event source`라는 이름만으로 전달 의미를 통일하면 안 됩니다.

| Source 형태 | 진행 상태 | 성공 뒤 변경 | 실패나 timeout 뒤 확인할 것 |
|---|---|---|---|
| Managed queue | visible message, lease 또는 visibility deadline | delete 또는 ack | lease 만료 뒤 다시 보이는지, DLQ 이동 조건 |
| Ordered stream | partition, offset 또는 sequence | checkpoint 이동 | batch 중 어디까지 반영되는지, partition별 concurrency |
| Object notification·event bus | source object/version, delivery attempt | source별 성공 처리 | delivery ID가 재전달에도 같은지, replay 가능 기간 |
| Scheduler·HTTP | schedule occurrence 또는 request ID | response 또는 dispatch 기록 | caller가 timeout 뒤 다시 호출하는지 |

공식 문서에서 delivery 방식, ack/checkpoint 시점, retry 담당자, 보존 기간, 최대 event age, batch 의미와 failure destination을 확인합니다. 확인하지 못한 항목은 `unknown`으로 남깁니다.

## 2. Invocation과 외부 결과의 상태를 나눕니다

```text
SOURCE_AVAILABLE
→ INVOCATION_RUNNING
→ EFFECT_COMMITTED
→ ACK_COMMITTED
```

대표 실패:

```text
INVOCATION_RUNNING → RETRYABLE_FAILURE → SOURCE_AVAILABLE
INVOCATION_RUNNING → TERMINAL_FAILURE → FAILURE_DESTINATION
EFFECT_COMMITTED → timeout 또는 ack 유실 → SOURCE_AVAILABLE
```

`EFFECT_COMMITTED`와 `ACK_COMMITTED` 사이가 핵심입니다. Database commit, object write, function 성공 응답과 source ack는 서로 다른 사건입니다.

## 3. Timeout은 취소됐다는 증거가 아닙니다

Invocation timeout은 실행 시간이 끝났다는 관측일 뿐, 외부 write가 없었다는 뜻이 아닙니다.

```text
event_id=E1 attempt=1
output write=committed
status update=unknown
invocation=timeout
source ack=not committed
```

Retry는 새 결과를 만들기 전에 다음을 조회해야 합니다.

- 안정적인 output key로 결과가 이미 있는지
- event 처리 기록이 있는지
- 이전 write가 조건부로 반영됐는지
- 상태가 불확실하면 어떤 reconciliation을 수행할지

## 4. Event identity와 payload를 고정합니다

업무 event key는 적어도 다음 범위를 구분해야 합니다.

```text
tenant_id + event_id + object_version + operation
```

Provider delivery ID가 attempt마다 바뀔 수 있으므로 안정성을 확인하지 않고 정본 key로 사용하면 안 됩니다.

- schema version과 지원 consumer version을 기록합니다.
- function version과 output version을 연결합니다.
- 오래된 object version이 최신 결과를 덮어쓰지 않게 합니다.
- deduplication record는 가능한 replay 기간보다 오래 보존합니다.
- 다른 tenant는 같은 문자열 event ID를 독립적으로 사용할 수 있습니다.

같은 tenant와 event ID를 다른 payload에 재사용하면 새 event로 처리하지 말고 충돌로 보고해야 합니다.

## 5. Batch와 checkpoint

Batch 한 건이 실패했을 때 성공한 record까지 다시 전달되는지, record별 실패 응답을 지원하는지 확인합니다.

| 결정 | 확인할 내용 |
|---|---|
| Record별 결과 | 성공 record는 ack하고 실패 record만 다시 전달하는지 |
| Batch 전체 실패 | 성공 record도 다시 오므로 모두 duplicate-safe한지 |
| Ordered stream | 실패 record 뒤 checkpoint를 멈출지, 건너뛸지, 격리할지 |
| Poison record | retry 횟수와 event age 한도, failure destination 담당자 |

Record별 실패 기능을 켰다는 사실만으로 안전하지 않습니다. Handler가 반환한 ID가 source record와 정확히 연결되는지 시험해야 합니다.

## 6. Retry와 dead letter

Retry를 event source, function platform 또는 application scheduler 중 누가 수행하는지 구분합니다.

정할 항목:

- retryable과 terminal failure 분류
- 최대 attempt
- 최대 event age
- backoff와 jitter
- attempt별 deadline
- failure destination
- alert 조건
- replay 승인과 절차

Temporary dependency failure는 제한된 retry 대상이 될 수 있습니다. 잘못된 schema, 삭제된 tenant, 지원하지 않는 version과 영구적으로 없는 object는 같은 요청을 무한히 반복하지 않습니다.

Dead letter record에는 다음 값을 남깁니다.

```text
original event
source position
attempts
function version
tenant_id
failure class
first_failed_at
last_failed_at
data classification
replay eligibility
```

Dead letter는 자동 해결 상태가 아닙니다. 누가 언제 원인을 확인하고 다시 실행할지 정하지 않으면 실패를 보관했을 뿐입니다.

## 7. Concurrency와 backpressure

확인할 limit:

- account, region과 function별 concurrency
- source mapping의 batch size와 poller 수
- database connection과 object I/O
- 외부 API quota
- warm capacity와 cold-start 비용
- throttle 뒤 source의 재시도 방식
- 특정 tenant가 shared capacity를 독점할 가능성

Maximum concurrency는 downstream이 지속해서 처리할 수 있는 양보다 낮게 잡아야 합니다. Queue age가 계속 늘 때 function 수만 늘리면 비용과 dependency 부하가 함께 증가할 수 있습니다.

## 8. Tenant별 공정성과 retry 비용

한 tenant의 많은 요청이 다른 tenant의 처리 시간을 빼앗지 않게 해야 합니다.

- tenant별 in-flight limit
- fair queue
- partitioned capacity
- plan별 capacity tier
- tenant별 retry budget
- log payload 제한

Retry 비용에는 성공한 invocation만 포함하지 않습니다.

```text
attempt cost
= invocation duration
+ source read
+ downstream I/O
+ log ingestion
+ failure destination 저장
```

## 9. Replay는 새 작업으로 기록합니다

수동 replay에는 다음 정보가 필요합니다.

- 원래 event와 failure record
- 새 replay ID
- 사용할 function과 schema version
- 이미 반영된 external effect
- 현재 tenant 상태
- 승인자
- replay 결과와 correction record

원래 실패 기록을 덮어쓰지 않고 새 기록을 연결합니다. 삭제된 tenant, 보존 기간 만료와 법적 제한 때문에 replay를 거부할 수도 있습니다.

## 10. Quota 검사는 원자적으로 적용합니다

다음 방식은 동시에 들어온 요청에서 limit를 넘길 수 있습니다.

```text
현재 사용량 읽기: 9
limit 확인: 10
두 invocation 모두 통과
두 resource 생성
결과: 11
```

실제 시스템에서는 database constraint, conditional update, compare-and-set, transaction, lease나 key별 직렬 처리를 사용합니다. Application에서 읽고 비교하는 것만으로는 보장하지 못합니다.

## 11. 관측 자료

Attempt와 업무 결과를 구분합니다.

```text
event_id=E1 attempt=1 result=timeout external_effect=unknown
event_id=E1 attempt=2 result=duplicate effect_id=R9 final=success
```

필요한 metric:

- unique event 수
- attempt 수
- 억제한 duplicate 수
- 반영된 effect 수
- retryable·terminal failure
- dead letter 수
- 가장 오래된 event age
- tenant별 backlog
- replay 결과

## 12. `local-cloud-model`이 확인하는 불변식

[`local-cloud-model`](../exercises/local-cloud-model/README.md)은 실제 provider delivery를 재현하지 않습니다. 대신 application이 지켜야 할 다음 결과를 공개 API로 검사합니다.

```text
다른 tenant의 문서는 읽을 수 없습니다.
같은 tenant와 event ID는 output과 usage를 한 번만 만듭니다.
다른 tenant는 같은 event ID를 독립적으로 처리합니다.
quota 초과는 document를 일부만 만들지 않습니다.
실패 attempt는 retry와 dead letter에 남습니다.
tenant 삭제 뒤 queue와 active resource가 남지 않습니다.
```

## 검토 질문

1. 외부 write와 source ack 사이에 실패하면 무엇을 조회합니까?
2. Event identity는 tenant와 payload version을 충분히 구분합니까?
3. Retry가 끝나는 attempt와 event age가 정해져 있습니까?
4. Poison event가 정상 event의 capacity와 비용을 소진하지 않습니까?
5. Replay 전에 현재 tenant 상태와 기존 effect를 확인합니까?
6. Quota 검사가 concurrent 요청에서도 한도를 지킵니까?

## 다음 단계

Event 처리 규칙을 정리했다면 [`09-saas-tenancy-and-isolation.md`](09-saas-tenancy-and-isolation.md)에서 tenant 식별자가 request 외의 cache, job, export와 삭제 작업에도 유지되는지 확인하십시오.
