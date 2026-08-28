# Outbox와 Spring 스케줄링

> 읽는 시점: 데이터베이스 저장과 메시지 발행을 분리하거나 예약 작업으로 발행 대기 행을 처리할 때

업무 데이터 저장과 외부 broker 발행은 하나의 데이터베이스 transaction으로 묶을 수 없습니다. Outbox는 업무 데이터와 발행할 event를 같은 DB transaction에 저장하고, 별도 작업이 나중에 broker로 전달하게 합니다.

## 업무 행과 Outbox 행을 같은 transaction에 저장합니다

application service에서 broker를 직접 호출하지 않습니다.

```text
@Transactional writer
  → 업무 entity 저장
  → Outbox entity 저장
  → commit

별도 publisher
  → 발행 대기 행 조회
  → message gateway 호출
  → 성공 또는 실패 상태 저장
```

업무 저장이 rollback되면 Outbox 행도 남지 않아야 합니다. 반대로 DB commit이 끝난 뒤 broker 발행이 실패해도 업무 행은 유지되고 Outbox에서 재시도할 수 있어야 합니다.

`@Transactional` method가 같은 객체 안의 직접 호출로 우회되지 않는지도 확인합니다.

## scheduler는 실행 시점만 결정하게 합니다

`@Scheduled` method 하나가 긴 transaction을 열고 여러 network 요청까지 처리하지 않게 합니다.

```java
@Scheduled(fixedDelayString = "${outbox.poll-interval}")
void publishBatch() {
  for (UUID id : pendingFinder.nextBatch()) {
    publisher.publishOne(id);
  }
}
```

- finder는 제한된 개수와 일정한 정렬 순서로 ID를 반환합니다.
- publisher는 한 event의 발행과 상태 갱신을 처리합니다.
- 여러 instance가 실행되면 `SKIP LOCKED`, claim 상태, lease 중 하나로 같은 행을 동시에 처리하지 않게 합니다.
- 발행 성공 뒤 상태 저장 전에 process가 종료될 수 있음을 전제로 합니다.

발행 성공 여부가 불확실할 수 있으므로 event ID를 재시도마다 새로 만들지 않습니다. consumer는 같은 event ID가 다시 들어와도 중복 효과를 만들지 않아야 합니다.

## 실패 정보를 저장합니다

재시도 가능한 Outbox 행에는 보통 다음 값이 필요합니다.

```text
attemptCount
nextAttemptAt
lastErrorCode
publishedAt
```

credential이나 응답 본문 전체를 `lastError`에 저장하지 않습니다. 오류 종류를 짧은 코드로 남기고 자세한 내용은 로그에서 확인합니다.

최대 시도 횟수를 넘긴 행을 어떻게 격리하고 누가 다시 처리할지도 정합니다. 한 행의 반복 실패가 전체 batch를 계속 막지 않게 합니다.

## 중복 실행과 종료를 검사합니다

scheduler가 같은 instance에서 겹쳐 실행되는지, 여러 instance가 같은 행을 가져가는지 확인합니다. 종료 신호를 받은 뒤 새 batch를 시작하지 않고, 이미 시작한 발행은 제한 시간 안에 끝냅니다.

운영에서 확인할 값은 다음과 같습니다.

- 발행 대기 행 수
- 가장 오래된 대기 행의 나이
- 발행 성공·실패 수
- 재시도·격리 수
- batch 처리 시간

## Rewind가 필요한 징후

- 업무 데이터는 저장됐지만 발행할 event 기록이 없습니다.
- broker 장애 때문에 업무 transaction까지 rollback됩니다.
- 재시도할 때 event ID가 바뀝니다.
- 여러 instance가 같은 Outbox 행을 동시에 발행합니다.
- 발행 실패 이유와 다음 시도가 언제인지 알 수 없습니다.
- 종료 중 scheduler가 새 batch를 계속 시작합니다.

Redis 조회 힌트와 Outbox 재시도를 함께 연습하려면 전문 exercise인 [`idempotent-operation-outbox`](../../exercises/idempotent-operation-outbox/)를 수행합니다.
