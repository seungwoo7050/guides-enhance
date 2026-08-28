# 분산 서비스의 실패와 복구

이 저장소는 서비스를 여러 개로 나누는 방법보다, 서비스가 나뉜 뒤 생기는 실패를 어떻게 다룰지를 설명합니다.

네트워크 호출은 응답이 없더라도 서버가 이미 상태를 바꿨을 수 있습니다. 메시지는 같은 내용이 여러 번 전달되거나 순서가 바뀔 수 있으며, 원본 상태와 조회용 복제본은 한동안 서로 다를 수 있습니다. 이 저장소에서는 이런 상황을 예외적인 사고가 아니라 정상적으로 발생할 수 있는 입력으로 다룹니다.

각 문서를 읽은 뒤 바로 관련 프로젝트를 실행합니다. 모든 프로젝트는 `exercises/<project>/`만 복사해도 빌드하고 테스트할 수 있는 완성된 구현입니다.

## 완료 후 갖춰야 할 능력

필수 과정을 마치면 다음을 코드와 테스트로 설명할 수 있어야 합니다.

- 데이터마다 정본과 유일한 변경 주체를 정합니다.
- timeout과 업무 실패를 구분하고 `PENDING`, `UNKNOWN`, `ACCEPTED`, `REJECTED`를 적절히 사용합니다.
- 같은 request나 event가 다시 들어와도 업무 효과를 한 번만 적용합니다.
- 주문 상태와 Outbox를 함께 저장하고, 중단 뒤 남은 작업을 다시 처리합니다.
- event ID, schema version과 aggregate sequence를 검증합니다.
- 조회 모델 적용 뒤 checkpoint를 전진시키고 전체 로그로 다시 구축합니다.
- 전체 deadline 안에서 재시도를 제한하고, 과부하에서는 대기열을 무한히 늘리지 않습니다.
- request, operation, event, trace, correlation과 causation ID를 구분합니다.
- 정본과 조회 모델이 같은 최종 상태에 도달했는지 확인합니다.

## 필수 학습 경로

### 1. 상태 소유자와 불확실한 결과

문서:

- [`docs/01-boundaries-and-failure/01-partial-failure-and-uncertain-outcomes.md`](docs/01-boundaries-and-failure/01-partial-failure-and-uncertain-outcomes.md)
- [`docs/01-boundaries-and-failure/02-service-boundaries-and-data-ownership.md`](docs/01-boundaries-and-failure/02-service-boundaries-and-data-ownership.md)
- [`docs/01-boundaries-and-failure/03-synchronous-and-asynchronous-decisions.md`](docs/01-boundaries-and-failure/03-synchronous-and-asynchronous-decisions.md)

프로젝트:

- [`exercises/service-boundary/`](exercises/service-boundary/)
- [`exercises/request-decision/`](exercises/request-decision/)

### 2. 중복 전달과 상태 수렴

문서:

- [`docs/02-delivery-and-consistency/01-idempotency-and-single-effects.md`](docs/02-delivery-and-consistency/01-idempotency-and-single-effects.md)
- [`docs/02-delivery-and-consistency/02-outbox-saga-and-reconciliation.md`](docs/02-delivery-and-consistency/02-outbox-saga-and-reconciliation.md)
- [`docs/02-delivery-and-consistency/03-contracts-versioning-and-order.md`](docs/02-delivery-and-consistency/03-contracts-versioning-and-order.md)
- [`docs/02-delivery-and-consistency/04-read-models-and-late-events.md`](docs/02-delivery-and-consistency/04-read-models-and-late-events.md)

프로젝트:

- [`exercises/outbox-reconciliation/`](exercises/outbox-reconciliation/)
- [`exercises/contracts-and-order/`](exercises/contracts-and-order/)
- [`exercises/read-model-rebuild/`](exercises/read-model-rebuild/)

### 3. 재시도와 과부하 제한

문서:

- [`docs/03-resilience-and-load/01-timeouts-retries-circuit-breakers-and-dlq.md`](docs/03-resilience-and-load/01-timeouts-retries-circuit-breakers-and-dlq.md)
- [`docs/03-resilience-and-load/02-backpressure-bulkheads-and-load-shedding.md`](docs/03-resilience-and-load/02-backpressure-bulkheads-and-load-shedding.md)

프로젝트:

- [`exercises/retry-budget/`](exercises/retry-budget/)
- [`exercises/backpressure/`](exercises/backpressure/)

### 4. 처리 과정의 식별자와 최종 검증

문서:

- [`docs/04-release-and-evidence/02-distributed-observability.md`](docs/04-release-and-evidence/02-distributed-observability.md)

프로젝트:

- [`exercises/observability-correlation/`](exercises/observability-correlation/)
- [`exercises/reservation-flow/`](exercises/reservation-flow/)

`reservation-flow`는 앞선 내용을 하나의 예약 처리 과정에 연결합니다. 정본 상태, Outbox, 중복 전달, 순서가 바뀐 조회 모델, 재조정과 제한된 Dispatcher를 함께 검사하므로 필수 과정의 마지막에 수행합니다.

## 선택 자료

다음 자료는 유용하지만 필수 완료 조건에는 포함하지 않습니다.

### 기초 개념을 짧게 다시 확인하는 프로젝트

- [`exercises/uncertain-outcome/`](exercises/uncertain-outcome/) — 응답 유실 뒤 operation ID로 결과를 확인합니다.
- [`exercises/duplicate-delivery/`](exercises/duplicate-delivery/) — ACK 유실 뒤 같은 event가 다시 들어와도 효과를 한 번만 적용합니다.

### 심화 검증

- [`docs/04-release-and-evidence/03-end-to-end-chaos-and-failure-evidence.md`](docs/04-release-and-evidence/03-end-to-end-chaos-and-failure-evidence.md)
- [`exercises/chaos-evidence/`](exercises/chaos-evidence/)
- [`docs/05-capstone.md`](docs/05-capstone.md)

### 릴리스·성능·Kafka 설정

- [`docs/04-release-and-evidence/01-multi-repository-builds-and-release-manifests.md`](docs/04-release-and-evidence/01-multi-repository-builds-and-release-manifests.md)
- [`exercises/release-manifest/`](exercises/release-manifest/)
- [`docs/04-release-and-evidence/04-performance-gates-and-claims.md`](docs/04-release-and-evidence/04-performance-gates-and-claims.md)
- [`exercises/performance-gate/`](exercises/performance-gate/)
- [`docs/90-optional-labs/01-single-broker-kraft.md`](docs/90-optional-labs/01-single-broker-kraft.md)
- [`exercises/single-broker-kraft/`](exercises/single-broker-kraft/)

이 항목들은 각각 다중 저장소 릴리스 검증, 성능 근거 판정과 단일 Kafka 브로커 설정을 다룹니다. 분산 서비스의 기본 실패 처리 능력을 확인한 뒤 필요할 때 수행합니다.

## 실행 방법

Java 프로젝트는 각 디렉터리에서 다음 명령을 사용합니다.

```sh
make build
make test
make clean
```

`release-manifest`는 Python 3.10 이상과 Git이 필요합니다.

```sh
cd exercises/release-manifest
make test
```

`single-broker-kraft`의 실제 통합 검사는 Docker Engine과 Docker Compose v2가 필요합니다.

```sh
cd exercises/single-broker-kraft
./smoke-test.sh --static
./smoke-test.sh
```

## 완료 기준

필수 9개 프로젝트의 테스트를 통과한 뒤 `reservation-flow`에서 다음을 직접 설명할 수 있으면 과정을 마친 것입니다.

1. 각 상태를 어느 서비스가 변경하는지
2. operation ID와 event ID를 어디까지 유지하는지
3. Outbox 전송 중 중단되었을 때 무엇이 남는지
4. 중복 이벤트가 재고와 조회 모델을 두 번 바꾸지 않는 이유
5. 정본 조회 실패를 `UNKNOWN`으로 남기는 이유
6. 정본과 조회 모델이 언제 최종적으로 수렴했다고 판단하는지
