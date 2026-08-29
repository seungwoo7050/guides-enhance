# Serverless와 FaaS runtime

`serverless`는 server가 없다는 뜻이 아닙니다. 사용자가 개별 server instance를 만들고 patch하고 확장하는 작업을 직접 수행하지 않고, request나 event에 가까운 단위로 compute를 사용하는 방식입니다.

FaaS는 function invocation을 핵심 실행 단위로 사용합니다.

## 1. Invocation 상태

한 invocation은 대략 다음 순서로 진행됩니다.

```text
event 수락
→ queue 또는 dispatch
→ 실행 환경 선택 또는 생성
→ runtime 초기화
→ handler 호출
→ 외부 write나 API 호출
→ 결과 또는 실패
→ 실행 환경 재사용 또는 폐기
```

구현 방식은 공급자마다 다르지만 사용자가 확인할 상태는 비슷합니다.

- event identity
- attempt
- runtime과 function version
- 실행 환경 수명
- deadline
- memory와 temporary storage
- 외부에 반영된 결과
- completion acknowledgment
- retry와 dead letter

## 2. 실행 환경은 일시적입니다

Function environment는 다음 invocation에 재사용될 수도 있고 바로 없어질 수도 있습니다. 따라서 다음 가정은 안전하지 않습니다.

```text
다음 호출에도 global variable이 남습니다.
local file이 보존됩니다.
한 instance는 같은 tenant 요청만 처리합니다.
handler가 반환된 뒤에도 background thread가 끝까지 실행됩니다.
```

다음 원칙을 적용합니다.

- 보존해야 할 상태는 외부 durable service에 저장합니다.
- Local storage는 cache와 scratch 용도로만 씁니다.
- Cache hit 여부가 결과의 정확성을 바꾸지 않게 합니다.
- Credential과 tenant context를 invocation마다 다시 확정합니다.
- 필요한 외부 write와 acknowledgment를 handler return 전에 끝냅니다.

## 3. Cold start와 warm reuse

새 실행 환경을 만들면 runtime, code와 dependency를 초기화합니다. 시간은 언어, package 크기, network 연결과 설정 읽기에 따라 달라집니다.

Warm environment는 지연을 줄이지만 다음 상태가 남을 수 있습니다.

- 이전 invocation의 mutable global 값
- 오래된 설정
- 이전 tenant 데이터가 든 cache
- 만료된 credential
- 끊어진 connection
- 누적된 memory leak

성능 최적화가 tenant isolation과 결과 정확성을 깨지 않는지 확인해야 합니다.

## 4. Timeout은 전체 시간 예산으로 봅니다

Function timeout만 계산하면 부족합니다.

```text
queue 대기
+ cold start
+ dependency 호출
+ retry
+ 결과 저장
+ acknowledgment
≤ end-to-end deadline
```

Handler가 timeout 직전에 외부 write를 끝내고 acknowledgment 전에 종료되면 같은 event가 다시 전달될 수 있습니다. Timeout 설계는 idempotency와 함께 해야 합니다.

Dependency timeout은 invocation deadline보다 짧아야 합니다. 남은 시간 안에 결과를 확정할 수 없으면 새 외부 작업을 시작하지 않는 편이 안전합니다.

## 5. Concurrency

동시성은 단순히 function instance 수가 아닙니다.

- account 또는 region limit
- function별 reserved limit
- event source poller
- partition 수
- batch size
- database connection limit
- 외부 API rate limit
- tenant quota
- 같은 key의 순차 처리 요구

Function이 빠르게 늘어도 database와 외부 API가 먼저 포화될 수 있습니다.

통제 방법:

- maximum concurrency
- reserved capacity
- queue buffering
- tenant별 limiter
- partition key
- semaphore 또는 lease
- batch size 조정
- backpressure

Latency뿐 아니라 retry와 비용도 함께 측정합니다.

## 6. 호출 방식별 차이

### 동기 request

Client가 결과를 기다립니다.

- client timeout
- gateway timeout
- function timeout
- 누가 retry하는지
- idempotency key
- 일부 결과만 보낸 경우

### 비동기 event

Producer는 보통 event가 수락됐다는 사실까지만 확인합니다.

- event가 얼마나 보존되는지
- attempt를 어떻게 식별하는지
- retry schedule
- dead letter
- 처리 결과를 어떻게 알리는지
- duplicate와 ordering

### Queue와 stream source

Poller가 여러 record를 묶어 function을 호출할 수 있습니다.

- batch 전체 실패 여부
- record별 실패 응답
- partition ordering
- offset, checkpoint 또는 visibility timeout
- poison record
- replay

세부 동작은 선택한 source의 공식 문서와 실제 시험으로 확인합니다.

## 7. 배포할 상태

Function code만 versioning하면 부족합니다.

- runtime version
- dependency lock
- environment 설정
- layer 또는 shared package
- trigger mapping
- permission
- concurrency setting
- destination과 dead letter
- event schema

Code artifact와 trigger 설정을 같은 release record에서 추적합니다. Traffic shifting 기능이 있어도 event schema와 저장 데이터의 호환성은 별도로 확인해야 합니다.

## 8. Network 연결

Function을 private network에 연결하면 database에 접근할 수 있지만 startup 시간과 egress 비용이 바뀔 수 있습니다.

- public API와 private service에 어떤 route로 접근합니까?
- NAT 또는 proxy의 비용과 capacity는 얼마입니까?
- private DNS가 실패하면 어떤 error가 남습니까?
- function identity와 network rule을 모두 요구합니까?
- metadata 또는 credential endpoint 접근을 제한할 수 있습니까?

## 9. 관측 자료

Invocation log만으로 최종 업무 결과를 알 수 없습니다. 다음 값을 연결합니다.

```text
event_id
request_id
attempt
function_version
tenant_id
source_partition_or_queue
external_effect_id
deadline
result
retry_decision
duration_or_cost
```

필요한 metric:

- invocation 수
- success, error와 timeout
- throttle
- concurrency
- cold start
- duration 분포
- queue age
- retry 수
- dead-letter 수
- downstream latency
- 성공한 업무 결과당 비용

## 10. 비용

FaaS 비용은 보통 request, 실행 시간, 할당 memory, warm capacity와 data transfer에 연결됩니다.

다음 항목이 비용을 크게 늘릴 수 있습니다.

- 끝나지 않는 retry
- 필요한 것보다 큰 memory
- 작은 외부 요청을 지나치게 많이 보냄
- 큰 payload
- 긴 실행 시간
- 과도한 log
- egress
- provisioned concurrency

저빈도 burst workload에는 유리할 수 있지만, 사용량이 꾸준히 높으면 instance 기반 실행과 다시 비교해야 합니다.

## 11. 적합성 검토가 필요한 workload

- 실행 시간이 매우 깁니다.
- 강한 local state가 필요합니다.
- persistent connection을 유지해야 합니다.
- 항상 준비된 낮은 latency가 필수입니다.
- custom OS, driver나 privileged 작업이 필요합니다.
- 사용량이 높고 일정합니다.
- GPU나 특수 hardware가 필요합니다.
- 여러 저장소를 묶는 복잡한 transaction이 필요합니다.

FaaS를 전혀 쓸 수 없다는 뜻은 아닙니다. Function 단위를 줄이거나 다른 compute 방식과 조합해야 할 수 있습니다.

## 12. 검토 질문

1. 같은 invocation이 반복돼도 외부 결과가 하나입니까?
2. 실행 환경이 바로 사라져도 결과가 정확합니까?
3. Concurrency가 database와 외부 API capacity를 넘지 않습니까?
4. Timeout 뒤 외부 write가 반영됐는지 확인할 수 있습니까?
5. 처리할 수 없는 event를 제한된 횟수 뒤 격리합니까?
6. Event source 설정과 function version을 함께 추적합니까?
7. 성공한 업무 결과당 비용을 계산할 수 있습니까?

## 다음 단계

실행 환경의 수명을 이해했다면 [`08-event-delivery-concurrency-and-idempotency.md`](08-event-delivery-concurrency-and-idempotency.md)에서 effect와 acknowledgment 사이의 실패를 구체적으로 다루십시오.
