# 예약 처리 통합 검증

## 목표

앞선 문서에서 다룬 operation ID, 데이터 소유권, Outbox, 중복 전달, 이벤트 순서, 조회 모델, 재조정과 과부하 제한을 하나의 예약 처리 과정에 연결합니다.

이 문서는 필수 프로젝트인 `reservation-flow`를 읽을 때 참고하는 보충 설명입니다. 프로젝트 README와 테스트만으로 구현을 이해할 수 있다면 필수로 읽을 필요는 없습니다.

## 구성 요소

```text
ReservationService
- operation ID별 예약 상태의 정본
- PENDING / UNKNOWN / ACCEPTED / REJECTED
- 예약 상태와 함께 저장하는 Outbox
- 재고 결과 적용과 상태 event 생성

InventoryService
- 가용 재고의 정본
- operation ID별 재고 차감 결과

Broker
- 같은 event의 재전달을 허용하는 전송 기록

QueryService
- 예약 상태 조회 모델
- schema version 격리
- aggregate sequence gap 보류
- 전체 EventEnvelope 이력 재생

Dispatcher
- 실행 자리 수와 대기열 크기 제한
- deadline이 지난 작업 거절
```

실제 network와 Kafka 대신 같은 실패를 빠르고 반복 가능하게 재현하는 메모리 모델을 사용합니다.

## 1. 예약 접수와 operation ID

예약 명령은 operation ID, correlation ID와 quantity를 받습니다.

- 처음 본 operation ID면 `PENDING` 예약과 첫 Outbox event를 함께 만듭니다.
- 같은 ID와 같은 입력이면 기존 결과를 반환합니다.
- 같은 ID에 다른 quantity나 correlation ID가 오면 거절합니다.
- 결과 조회는 처음 operation ID를 사용합니다.

이 조건으로 응답을 잃은 호출자가 새 예약을 만들지 않고 기존 상태를 확인할 수 있습니다.

## 2. 서비스별 정본

ReservationService는 예약 상태만 바꿉니다. 재고 수량은 InventoryService만 변경합니다.

- 재고가 충분하면 `INVENTORY_ACCEPTED`를 만듭니다.
- 재고가 부족하면 `INVENTORY_REJECTED`를 만들고 수량은 바꾸지 않습니다.
- 같은 event가 다시 오면 앞서 만든 결과를 반환합니다.
- 같은 operation ID에 다른 입력이 오면 재고를 바꾸기 전에 거절합니다.

ReservationService는 InventoryService가 만든 결과의 quantity, correlation ID와 causation ID를 확인한 뒤에만 최종 상태를 바꿉니다.

## 3. Outbox와 재전달

예약 상태와 Outbox event를 함께 저장합니다. Broker가 중단되면 event는 미발행 상태로 남습니다.

```text
Broker.send 성공
→ published 표시 전에 중단
→ 같은 event 재전송
```

이 경우 InventoryService와 QueryService가 event ID를 기록해 재전달을 한 번의 업무 효과로 처리합니다. 미발행 Outbox가 있으면 가장 오래 기다린 시간을 계산할 수 있어야 합니다.

## 4. 순서가 바뀌는 조회 모델

예약 생성 event는 sequence 1, 수락·거절 event는 sequence 2를 사용합니다.

- sequence 2가 먼저 오면 보류합니다.
- sequence 1이 오면 먼저 적용한 뒤 보류한 sequence 2를 이어서 적용합니다.
- 같은 event ID와 같은 입력은 중복으로 무시합니다.
- 같은 sequence를 다른 event가 주장하면 거절합니다.
- 지원하지 않는 schema version은 적용하지 않고 격리합니다.
- sequence 1·2 규칙에 맞지 않는 event는 보류 목록에 넣기 전에 거절합니다.

`QueryService.rebuild`는 기존 상태, 중복 기록과 보류 목록을 모두 비운 뒤 `EventEnvelope` 이력을 다시 적용합니다. schema version도 함께 재생하므로 지원하지 않는 event가 재구축 중에 적용되어서는 안 됩니다.

## 5. 미확정 상태 재조정

오래 남은 `PENDING` 또는 `UNKNOWN` 예약은 처음 operation ID로 InventoryService의 결과를 조회합니다.

- 결과가 있으면 예약 최종 상태를 갱신하고 상태 event를 만듭니다.
- 결과가 아직 없으면 `PENDING`을 유지하고 다음 조회 시각을 기록합니다.
- 조회 자체가 실패하면 `UNKNOWN`으로 바꾸고 다음 조회 시각을 기록합니다.
- 조회 실패를 자동 성공이나 자동 보상으로 바꾸지 않습니다.

재조정 기록에는 operation ID, reservation ID, 조회 결과와 다음 시각을 남깁니다.

## 6. 접수량 제한

Dispatcher는 queue와 실행 자리를 따로 제한합니다.

- deadline이 지난 작업은 queue에 넣지 않습니다.
- queue 상한을 넘으면 예약 상태를 만들기 전에 거절합니다.
- 실행 자리가 없으면 다음 작업을 queue에서 꺼내지 않습니다.
- queue에서 기다리는 동안 deadline이 지나면 ReservationService를 호출하지 않습니다.
- 재시도할 때 operation ID, correlation ID, quantity와 최초 deadline을 그대로 전달합니다.
- 작업이 끝나면 해당 실행 자리 하나만 반환합니다.

## 최종 수렴 조건

다음 조건을 모두 만족할 때만 예약 한 건이 수렴했다고 판단합니다.

- ReservationService의 상태가 `ACCEPTED` 또는 `REJECTED`입니다.
- QueryService가 같은 최종 상태를 가지고 있습니다.
- 미발행 Outbox가 없습니다.

두 서비스가 모두 `PENDING`이라는 이유로 수렴했다고 판단하면 안 됩니다. 상태가 같더라도 업무 결과는 아직 확정되지 않았기 때문입니다.

## 실패 행렬

| 실패 | 실패 중 남아야 할 상태 | 복구 뒤 확인할 결과 |
| --- | --- | --- |
| 예약 저장 뒤 응답 유실 | operation ID로 조회 가능한 예약 | 같은 예약을 반환하고 예약 수는 1 |
| 재고 부족 | 예약 `REJECTED` | 재고 차감 횟수 0 |
| Broker 중단 | 미발행 Outbox | Broker 복구 뒤 모두 발행 |
| send 뒤 표시 전 중단 | 같은 event 재전달 가능 | 재고 효과와 조회 상태는 한 번만 적용 |
| sequence 2가 먼저 도착 | 보류 event 1건 | sequence 1 뒤 최종 상태 적용 |
| 정본 조회 실패 | 예약 `UNKNOWN`, 다음 시각 | 같은 operation ID로 다시 조회해 수렴 |
| queue 포화 | 초과 작업 거절 | 기존 실행·대기 작업만 유지 |

## 관련 프로젝트

[`reservation-flow`](../exercises/reservation-flow/)의 테스트는 위 실패를 메서드별로 재현합니다.

## 완료 기준

다음 문장을 코드 위치와 테스트 이름을 들어 설명할 수 있어야 합니다.

1. 전송은 여러 번 일어나도 예약과 재고 효과는 한 번만 남습니다.
2. `PENDING`, `UNKNOWN`과 `COMPENSATING` 같은 중간 상태에는 다음 행동이 있습니다.
3. Broker와 조회 모델이 늦어도 재조정 뒤 정본과 같은 최종 상태가 됩니다.
4. queue 포화와 deadline 만료는 예약 상태를 만들기 전에 거절됩니다.
