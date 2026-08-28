# 예약 처리 복구 시뮬레이터

## 개요

예약 접수, 재고 차감, Outbox 발행, 순서가 뒤바뀔 수 있는 조회 모델, 정본 조회를 통한 재조정과 제한된 Dispatcher를 하나의 Java 모델로 연결합니다.

## 주요 기능

- operation ID와 입력을 묶어 같은 예약을 한 번만 생성합니다.
- 재고 차감과 결과를 event ID와 operation ID로 중복 처리합니다.
- broker 장애와 전송 뒤 중단에서 Outbox를 다시 발행합니다.
- 순서가 바뀐 상태 이벤트를 보류하고 앞선 이벤트가 오면 이어서 적용합니다.
- 지원하지 않는 schema version을 격리하고 전체 이력으로 조회 모델을 재구축합니다.
- 정본 조회가 실패하면 `UNKNOWN`과 다음 재조정 시각을 기록합니다.
- Dispatcher가 실행 수, 대기열 크기와 deadline을 제한합니다.

## 구성

`ReservationService`는 예약 상태와 Outbox를, `InventoryService`는 재고와 operation별 결과를 저장합니다. `Broker`와 `Publisher`가 이벤트 전달을 재현하고, `QueryService`가 예약별 조회 상태와 sequence gap을 관리합니다. `SystemUnderTest`가 복구 순서를 연결하며 `Dispatcher`가 접수량을 제한합니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.capstone.ReservationFlowTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

예약 정본과 조회 모델이 모두 같은 최종 상태이고 미발행 Outbox가 없을 때만 수렴으로 판정합니다. 두 상태가 모두 `PENDING`인 경우는 아직 업무 결과가 확정되지 않았으므로 완료로 보지 않습니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 서비스 간 공유 상태와 이벤트 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — status, event, evidence types` |
| 2 | Outbox 이벤트의 생성 시각과 발행 상태 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — OutboxRecord` |
| 3 | 예약 상태와 Outbox 저장 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — ReservationService` |
| 3-1 | 예약 요청 멱등 처리 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — ReservationService.submit` |
| 3-2 | 재고 결과 검증과 최종 상태 전이 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — ReservationService.applyInventoryResult` |
| 3-3 | 미발행 이벤트 스냅샷 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — ReservationService.pendingOutbox` |
| 3-4 | 가장 오래된 미발행 이벤트 시간 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — ReservationService.oldestPendingOutboxAge` |
| 4 | 재고와 operation별 결과 저장 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — InventoryService` |
| 4-1 | 재고 차감 한 번만 적용 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — InventoryService.handle` |
| 4-2 | 원래 operation ID로 결과 조회 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — InventoryService.findResultByOperation` |
| 5 | 브로커 전달 기록 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — Broker` |
| 6 | Outbox 발행 순서 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — Publisher` |
| 6-1 | 전송 성공 후 발행 완료 표시 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — Publisher.publishPending` |
| 7 | 조회 모델의 스키마와 순서 처리 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — QueryService` |
| 7-1 | Envelope·식별자·순서 검증 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — QueryService.consume` |
| 7-2 | 조회 모델 전체 재구축 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — QueryService.rebuild` |
| 7-3 | 연속된 보류 이벤트 적용 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — QueryService.drain` |
| 7-4 | 모순된 최종 상태 방지 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — QueryService.apply` |
| 8 | 서비스 조합과 복구 기록 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — SystemUnderTest` |
| 8-1 | deadline 검사 후 예약 접수 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — SystemUnderTest.submit` |
| 8-2 | 미발행 이벤트부터 조회 모델까지 복구 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — SystemUnderTest.reconcile` |
| 8-3 | 미확정 예약 재조정 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — SystemUnderTest.reconcilePending` |
| 8-4 | 최종 상태 수렴 판정 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — SystemUnderTest.converged` |
| 9 | 실행·대기 수를 제한하는 Dispatcher | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — Dispatcher` |
| 9-1 | 대기열 접수 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — Dispatcher.enqueue` |
| 9-2 | 실행 자리 확보 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — Dispatcher.beginNext` |
| 9-3 | 기존 식별자와 deadline을 보존한 실행 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — Dispatcher.execute` |
| 9-4 | 실행 자리 반환 | `src/main/java/dev/guides/distributed/capstone/ReservationFlow.java — Dispatcher.complete` |

## 범위와 제한

- 모든 서비스와 Broker를 한 프로세스 안에서 실행합니다.
- 실제 database transaction, network, clock과 인증은 제공하지 않습니다.
- thread timing보다 상태 전이의 정확성을 결정적으로 검사하는 모델입니다.
