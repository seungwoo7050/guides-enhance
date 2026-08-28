# Outbox 발행과 Saga 재조정 모델

## 개요

Outbox 전송 중 발생하는 중복 전달과 결제 거절 뒤 실패할 수 있는 재고 보상을 결정적으로 재현하는 Java 모델입니다.

## 주요 기능

- 주문 상태와 Outbox 행을 같은 저장 작업에서 생성합니다.
- broker 장애나 전송 뒤 중단이 발생하면 미발행 행을 그대로 남깁니다.
- 소비자는 여러 번 전달된 같은 이벤트를 업무 효과 한 번으로 처리합니다.
- 결제가 거절되면 재고를 해제하고, 해제 실패 시 `COMPENSATING` 상태를 유지합니다.
- 다음 재조정이 미완료 발행과 보상을 이어서 처리할 수 있습니다.

## 구성

`Database`, `Consumer`, `Broker`, `Publisher`가 주문 이벤트 발행과 재전달을 재현합니다. `InventoryParticipant`, `PaymentParticipant`, `OrderSaga`는 재고 예약, 결제 거절과 보상 재시도를 처리합니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.outbox.OutboxReconciliationTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

Outbox는 Broker 전송이 성공한 뒤에만 `published`로 바꿉니다. Saga는 재고 해제가 성공한 뒤에만 `CANCELLED`로 바꿔 보상 중단을 완료 상태로 숨기지 않습니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 업무 이벤트 식별자 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — DomainEvent` |
| 2 | Outbox 행의 발행 상태 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — OutboxRow` |
| 3 | 주문과 Outbox 함께 저장 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — Database` |
| 3-1 | 주문·이벤트 ID 양방향 검증 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — Database.createOrder` |
| 4 | 소비자의 중복 처리 기록 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — Consumer` |
| 4-1 | 동일 재전달과 ID 충돌 구분 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — Consumer.onEvent` |
| 5 | 브로커 가용성과 전달 횟수 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — Broker` |
| 6 | 미발행 Outbox 처리 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — Publisher` |
| 6-1 | 전송 후 완료 표시 전 중단 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — Publisher.publishNext` |
| 6-2 | 미발행 행 재처리 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — Publisher.reconcile` |
| 7 | Saga 진행 상태 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — SagaState` |
| 8 | 재고 예약과 보상 상태 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — InventoryParticipant` |
| 8-1 | 주문별 재고 예약 한 번만 적용 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — InventoryParticipant.reserve` |
| 8-2 | 실패 후 다시 시도할 수 있는 보상 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — InventoryParticipant.release` |
| 9 | 결제 승인·거절 재현 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — PaymentParticipant` |
| 10 | 주문 Saga 실행 상태 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — OrderSaga` |
| 10-1 | 정방향 처리와 보상 전환 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — OrderSaga.execute` |
| 10-2 | 미완료 보상 재시도 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — OrderSaga.reconcile` |
| 10-3 | 보상 성공 후 취소 확정 | `src/main/java/dev/guides/distributed/outbox/OutboxReconciliation.java — OrderSaga.compensate` |

## 범위와 제한

- 실제 database transaction과 message broker를 사용하지 않습니다.
- Outbox 행을 한 건씩 순서대로 전송합니다.
- Saga 참여자는 같은 프로세스의 객체입니다.
