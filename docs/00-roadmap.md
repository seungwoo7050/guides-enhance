# 학습 로드맵

## 목표

이 과정은 분산 서비스에서 다음 세 가지를 반복해서 확인합니다.

```text
어느 서비스가 상태를 바꾸는가
→ 실패했을 때 어떤 상태가 남는가
→ 남은 상태를 어떻게 다시 처리하고 검증하는가
```

모든 문서를 먼저 읽은 뒤 프로젝트를 몰아서 구현하지 않습니다. 필요한 개념을 익힌 시점에 바로 관련 프로젝트를 빌드하고 테스트합니다.

## 최종 역량

필수 과정을 마치면 다음을 할 수 있어야 합니다.

- 데이터의 정본과 유일한 writer를 정합니다.
- 전송 실패와 업무 결과를 구분합니다.
- request와 event의 중복 입력을 단일 업무 효과로 처리합니다.
- Outbox와 Saga의 보장 범위를 구분합니다.
- schema version과 aggregate sequence를 검사합니다.
- 조회 모델을 중복 없이 적용하고 전체 로그로 다시 만듭니다.
- deadline, retry, Circuit Breaker와 DLQ를 함께 설계합니다.
- 실행 수와 대기열 크기를 제한하고 과부하를 명시적으로 거절합니다.
- 처리 단계의 식별자를 연결하고 최종 상태의 수렴을 확인합니다.

## 1단계: 상태 변경 주체와 결과 상태

### 읽을 문서

1. [`01-partial-failure-and-uncertain-outcomes.md`](01-boundaries-and-failure/01-partial-failure-and-uncertain-outcomes.md)
2. [`02-service-boundaries-and-data-ownership.md`](01-boundaries-and-failure/02-service-boundaries-and-data-ownership.md)
3. [`03-synchronous-and-asynchronous-decisions.md`](01-boundaries-and-failure/03-synchronous-and-asynchronous-decisions.md)

### 수행할 프로젝트

1. [`service-boundary`](../exercises/service-boundary/)
2. [`request-decision`](../exercises/request-decision/)

먼저 데이터마다 owner와 writer를 정하고 동기 의존 순환을 찾습니다. 그다음 동기 요청과 비동기 접수에서 어떤 상태를 반환하고 언제 수량을 변경할지 구현합니다.

`uncertain-outcome`은 응답 유실만 따로 다시 확인하고 싶을 때 수행합니다.

## 2단계: 중복 전달과 상태 수렴

### 읽을 문서

1. [`01-idempotency-and-single-effects.md`](02-delivery-and-consistency/01-idempotency-and-single-effects.md)
2. [`02-outbox-saga-and-reconciliation.md`](02-delivery-and-consistency/02-outbox-saga-and-reconciliation.md)
3. [`03-contracts-versioning-and-order.md`](02-delivery-and-consistency/03-contracts-versioning-and-order.md)
4. [`04-read-models-and-late-events.md`](02-delivery-and-consistency/04-read-models-and-late-events.md)

### 수행할 프로젝트

1. [`outbox-reconciliation`](../exercises/outbox-reconciliation/)
2. [`contracts-and-order`](../exercises/contracts-and-order/)
3. [`read-model-rebuild`](../exercises/read-model-rebuild/)

`outbox-reconciliation`에서 상태 저장과 이벤트 발행 사이의 실패를 다룹니다. 이어서 event ID와 sequence를 검사하고, 마지막으로 조회 모델 적용과 checkpoint 저장 순서를 확인합니다.

`duplicate-delivery`는 중복 전달의 가장 작은 예제가 필요할 때 사용합니다.

## 3단계: 시간과 처리 용량 제한

### 읽을 문서

1. [`01-timeouts-retries-circuit-breakers-and-dlq.md`](03-resilience-and-load/01-timeouts-retries-circuit-breakers-and-dlq.md)
2. [`02-backpressure-bulkheads-and-load-shedding.md`](03-resilience-and-load/02-backpressure-bulkheads-and-load-shedding.md)

### 수행할 프로젝트

1. [`retry-budget`](../exercises/retry-budget/)
2. [`backpressure`](../exercises/backpressure/)

먼저 하나의 deadline 안에서 재시도를 제한합니다. 그다음 처리 속도보다 요청이 빠를 때 실행 수와 대기열 크기를 제한하고, 이미 만료된 작업을 실행하지 않도록 합니다.

## 4단계: 식별자 연결과 통합 검증

### 읽을 문서

1. [`02-distributed-observability.md`](04-release-and-evidence/02-distributed-observability.md)

### 수행할 프로젝트

1. [`observability-correlation`](../exercises/observability-correlation/)
2. [`reservation-flow`](../exercises/reservation-flow/)

`observability-correlation`에서 request, operation, event, trace, correlation과 causation ID를 구분합니다. 마지막에는 `reservation-flow`로 다음 전체 과정을 확인합니다.

```text
예약 접수
→ Outbox 저장
→ Broker 전달과 재전달
→ 재고 판정
→ 예약 최종 상태
→ 순서가 바뀔 수 있는 조회 모델
→ 정본 조회와 재조정
→ 최종 상태 수렴
```

## 선택 자료

### 보충 프로젝트

- [`uncertain-outcome`](../exercises/uncertain-outcome/)
- [`duplicate-delivery`](../exercises/duplicate-delivery/)

필수 프로젝트에서 막힌 개념을 더 작은 코드로 다시 확인할 때 사용합니다.

### 장애 실험 보충

- [`03-end-to-end-chaos-and-failure-evidence.md`](04-release-and-evidence/03-end-to-end-chaos-and-failure-evidence.md)
- [`chaos-evidence`](../exercises/chaos-evidence/)
- [`05-capstone.md`](05-capstone.md)

실패 가설, 장애 전·중·후의 기록과 cleanup 결과 분리를 더 자세히 확인합니다.

### 전문 영역

- [`01-multi-repository-builds-and-release-manifests.md`](04-release-and-evidence/01-multi-repository-builds-and-release-manifests.md)
- [`release-manifest`](../exercises/release-manifest/)
- [`04-performance-gates-and-claims.md`](04-release-and-evidence/04-performance-gates-and-claims.md)
- [`performance-gate`](../exercises/performance-gate/)
- [`01-single-broker-kraft.md`](90-optional-labs/01-single-broker-kraft.md)
- [`single-broker-kraft`](../exercises/single-broker-kraft/)

각각 릴리스 재현성, 성능 근거 판정과 Kafka 단일 브로커 설정을 다룹니다. 필수 과정 완료 뒤 실제 업무에서 필요할 때 선택합니다.

## 완료 기준

다음 조건을 모두 만족해야 합니다.

- 필수 9개 프로젝트의 테스트를 통과합니다.
- `reservation-flow`에서 broker 장애, 전송 뒤 중단, 순서 역전과 정본 조회 실패 테스트가 무엇을 검출하는지 설명합니다.
- 같은 operation ID와 event ID를 새 값으로 바꾸면 어떤 중복 효과가 생기는지 설명합니다.
- `PENDING`과 `UNKNOWN`을 최종 성공으로 처리하지 않는 이유를 설명합니다.
- 정본과 조회 모델이 같은 최종 상태이고 미발행 Outbox가 없을 때만 수렴으로 판정합니다.

설명이 막히는 부분만 해당 문서와 프로젝트로 돌아갑니다. 전체 과정을 처음부터 반복할 필요는 없습니다.
