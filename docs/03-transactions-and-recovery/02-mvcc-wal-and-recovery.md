# MVCC, WAL과 crash recovery

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 합니다.

- 여러 row version으로 일관된 snapshot을 제공하는 이유
- transaction snapshot에서 어느 version이 보이는지 판단하는 방법
- MVCC가 write conflict와 여러 row에 걸친 업무 조건을 자동으로 해결하지 않는 이유
- WAL의 write-ahead 규칙과 `page_lsn`이 필요한 이유
- commit WAL과 data page가 서로 다른 시점에 disk에 기록될 수 있는 이유
- crash 뒤 redo와 undo가 각각 필요한 상태
- checkpoint와 vacuum이 복구 시간과 저장 공간에 미치는 영향

## MVCC는 이전 값을 즉시 덮어쓰지 않습니다

한 위치의 byte를 바로 덮어쓴다면 reader와 writer가 같은 값을 두고 계속 충돌합니다. Reader가 읽는 도중 writer가 값을 바꾸면 이전 값과 새 값이 섞여 보일 수 있습니다. 모든 read가 긴 shared lock을 잡게 할 수도 있지만, 읽기와 쓰기가 서로 막히는 시간이 길어집니다.

MVCC는 논리 row의 이전 version을 즉시 없애지 않고 새 version을 만듭니다.

```text
account(id=7, balance=100, xmin=T10, xmax=T12)
account(id=7, balance=80,  xmin=T12, xmax=∞)
```

`T12`가 balance를 100에서 80으로 바꾸면 첫 version에는 `T12`가 대체했다는 정보를 기록하고 새 version을 추가합니다. Reader는 자신의 snapshot에서 볼 수 있는 version을 선택합니다.

핵심 질문은 “가장 최근 byte가 무엇입니까?”가 아니라 다음과 같습니다.

> 이 transaction의 snapshot에서 commit된 것으로 보이는 version은 무엇입니까?

## Snapshot이 보는 transaction 집합

축소해서 생각하면 snapshot에는 다음 정보가 필요합니다.

```text
snapshot을 만들기 전에 commit된 transaction
snapshot을 만들 때 아직 진행 중인 transaction
snapshot 이후에 시작한 transaction
```

Version이 보이려면 일반적으로 다음을 만족해야 합니다.

```text
version을 만든 transaction이 이 snapshot에서 commit되어 보입니다.
그리고
version을 삭제하거나 대체한 transaction이 이 snapshot에서 commit되어 보이지 않습니다.
```

실제 PostgreSQL은 transaction ID, subtransaction과 hint bit 등을 더 복잡하게 처리합니다. 기초 단계에서는 다음 세 값을 구분하면 됩니다.

1. version을 만든 transaction
2. version을 더 이상 최신이 아니게 만든 transaction
3. reader가 사용하는 snapshot

같은 page 안에 여러 version이 있어도 reader마다 다른 값을 볼 수 있습니다.

## Isolation level과 snapshot 시점

`READ COMMITTED`에서는 statement마다 새 snapshot을 사용할 수 있습니다. 같은 transaction 안에서도 첫 번째 `SELECT`와 두 번째 `SELECT`가 다른 commit 결과를 볼 수 있습니다.

`REPEATABLE READ`에서는 transaction 동안 같은 snapshot을 사용합니다. 반복 read가 안정적이지만, 서로 다른 row를 변경하는 write skew까지 자동으로 막지는 못합니다.

`SERIALIZABLE`은 snapshot 제공에 더해 transaction 사이의 위험한 의존 관계를 찾고 일부 transaction을 중단합니다. MVCC를 사용한다는 사실과 모든 실행이 serializable하다는 사실은 같지 않습니다.

## MVCC가 해결하지 않는 문제

### 같은 row를 동시에 쓰는 경우

두 writer가 같은 row를 바꾸면 하나가 기다리거나 실패해야 합니다. Version을 여러 개 만들 수 있다는 이유로 서로 모순되는 최종 write를 모두 받아들일 수는 없습니다.

### 여러 row에 걸친 업무 조건

```text
최소 한 명의 doctor는 on_call이어야 합니다.
```

두 transaction이 서로 다른 doctor row를 수정하면 각자 snapshot에서 다른 doctor가 남아 있다고 보고 모두 성공할 수 있습니다. Guard row, `SERIALIZABLE`이나 다른 명시적 충돌 지점이 필요합니다.

### 외부 시스템에 이미 전달한 작업

DB transaction이 rollback되어도 이미 보낸 email이나 외부 결제 요청은 자동으로 취소되지 않습니다. 이러한 작업은 별도의 idempotency와 전달 기록이 필요합니다.

## 오래된 version을 바로 지울 수 없습니다

Writer가 새 version을 만들었다고 이전 version을 즉시 삭제하면 오래된 snapshot을 가진 reader가 읽을 값이 사라집니다. 어떤 활성 snapshot도 이전 version을 필요로 하지 않는다는 사실이 확인된 뒤에야 공간을 회수할 수 있습니다.

오래 열린 transaction은 다음 문제를 만듭니다.

- dead tuple 회수가 늦어집니다.
- heap page와 index entry가 늘어납니다.
- vacuum이 재사용할 수 있는 공간이 줄어듭니다.
- 오래된 WAL이나 transaction ID 정보를 더 오래 보존할 수 있습니다.

읽기 전용 transaction도 오래 유지하면 저장 공간과 유지보수에 영향을 줍니다.

## WAL은 data page보다 먼저 durable해야 합니다

Buffer pool은 수정된 page를 즉시 disk에 쓰지 않을 수 있습니다. 반대로 memory가 부족하면 commit 전 dirty page가 disk로 나갈 수도 있습니다. 이 두 상황을 허용하면서 atomicity와 durability를 지키려면 변경을 재현하거나 되돌릴 정보가 먼저 저장되어야 합니다.

Write-Ahead Logging의 핵심 규칙은 다음과 같습니다.

```text
data page를 disk에 쓰기 전에
그 page의 변경을 설명하는 WAL record가 먼저 durable해야 합니다.
```

Commit 성공을 반환하기 전에는 commit을 증명하는 WAL도 durable해야 합니다.

```text
WAL record append
→ commit record append
→ WAL flush
→ commit 성공 반환
→ data page는 나중에 flush될 수 있음
```

Commit 시점에 모든 heap page가 최신 상태로 disk에 있을 필요는 없습니다. Crash 뒤 WAL을 다시 적용할 수 있으면 됩니다.

## LSN과 `page_lsn`

WAL record에는 순서를 나타내는 Log Sequence Number가 있습니다.

```text
LSN 100: T1이 page 3의 값을 A에서 B로 변경
LSN 120: T1 COMMIT
```

Page에는 마지막으로 적용한 WAL 위치를 기록합니다.

```text
page_lsn = 100
```

Recovery 중 `page_lsn >= record.lsn`이면 해당 변경은 이미 page에 반영되었다고 판단할 수 있습니다. 같은 WAL을 다시 읽어도 오래된 record를 다시 적용하지 않으므로 redo를 반복 실행하기 쉬워집니다.

값이 우연히 같다는 사실만으로는 같은 변경인지 판단하기 어렵습니다. LSN은 변경 순서를 명시적으로 기록합니다.

## WAL record에 필요한 정보

축소 모델에서는 다음 필드를 사용할 수 있습니다.

```text
LSN
transaction ID
record 종류: UPDATE / COMMIT / ABORT
page ID
before image
after image
이전 transaction record LSN
```

기록 방식은 시스템마다 다릅니다.

- **physical log**: 특정 byte의 이전 값과 새 값을 기록합니다.
- **logical log**: “key 7을 insert합니다” 같은 연산을 기록합니다.
- **physiological log**: page 위치와 page 내부 연산을 함께 기록합니다.

[`wal-recovery-simulator`](../../exercises/wal-recovery-simulator/)는 page ID와 before/after 값을 사용해 WAL ordering, redo와 undo를 작게 재현합니다.

## Steal과 no-force

Buffer 관리 방식은 두 질문으로 나눌 수 있습니다.

### Steal

Commit하지 않은 transaction의 dirty page를 frame에서 내보낼 수 있습니다. Memory를 유연하게 사용할 수 있지만 crash 시 uncommitted 값이 data file에 남을 수 있으므로 undo가 필요합니다.

### No-force

Commit할 때 변경한 모든 data page를 즉시 쓰지 않습니다. Commit 지연을 줄일 수 있지만 committed 값이 data file에 아직 없을 수 있으므로 redo가 필요합니다.

```text
steal + no-force
→ undo와 redo 모두 필요합니다.
```

## Crash recovery를 세 작업으로 나눕니다

실제 ARIES는 더 정교하지만, 기본 원리는 다음 세 작업으로 이해할 수 있습니다.

### 1. 분석

WAL을 읽고 다음을 찾습니다.

- commit된 transaction
- crash 시점에 끝나지 않은 transaction
- 변경된 page와 LSN
- redo를 시작할 위치

### 2. Redo

Disk page에 아직 반영되지 않은 변경을 다시 적용합니다. `page_lsn`이 record LSN 이상이면 이미 적용된 것으로 보고 건너뜁니다.

실제 steal/no-force 복구는 crash 직전 실행 기록을 다시 적용한 뒤 loser transaction을 undo할 수 있습니다. 학습용 모델은 핵심 순서를 보기 위해 단순화할 수 있습니다.

### 3. Undo

Commit record가 없는 transaction의 update를 마지막 것부터 되돌립니다. 같은 page를 여러 번 변경했다면 log 역순으로 before image를 적용해야 원래 값으로 돌아갑니다.

실제 시스템은 undo 중 다시 crash할 수 있으므로 보상 log record를 남깁니다. 이 저장소의 축소 구현은 같은 log로 recovery를 두 번 실행해도 최종 page가 같다는 점을 검사합니다.

## Commit 여부에 따른 복구 결과

다음 세 경우를 구분해야 합니다.

```text
UPDATE WAL은 durable하지만 COMMIT WAL은 없음
→ transaction을 commit된 것으로 인정하지 않습니다.

COMMIT WAL까지 durable하지만 data page는 이전 값
→ redo로 committed 값을 적용합니다.

uncommitted dirty page가 이미 disk에 기록됨
→ undo로 이전 값을 복원합니다.
```

클라이언트가 commit 응답을 받기 직전에 연결이 끊어지면 애플리케이션은 결과를 모를 수 있습니다. DB 내부에는 commit record가 있을 수도 있습니다. 같은 업무를 무조건 다시 실행하지 말고 operation ID나 결과 조회로 상태를 확인해야 합니다.

## Checkpoint는 recovery 시작 범위를 줄입니다

WAL 전체를 처음부터 읽으면 시작 시간이 계속 늘어납니다. Checkpoint는 활성 transaction, dirty page와 특정 log 위치를 기록해 분석 시작점을 앞당깁니다.

Checkpoint를 만들었다고 다음을 자동으로 보장하는 것은 아닙니다.

- 모든 page가 clean인 것은 아닙니다.
- 이전 WAL을 즉시 삭제할 수 있는 것은 아닙니다.
- backup이나 replica가 더 오래된 WAL을 필요로 하지 않는다는 뜻이 아닙니다.
- write-ahead 규칙을 대신하지 않습니다.

Checkpoint는 복구 시간을 줄이기 위한 정보입니다.

## Crash 시점을 나누어 검사합니다

정상 종료 뒤 값만 확인하면 복구 동작을 검증할 수 없습니다. 다음 위치에서 process가 멈췄다고 가정합니다.

```text
1. WAL append 전
2. WAL append 후 flush 전
3. update WAL flush 후 commit 전
4. commit WAL flush 후 data page flush 전
5. 일부 data page만 flush된 뒤
6. recovery를 수행하는 중
```

각 시점에서 먼저 예상 결과를 적습니다.

- committed transaction의 변경은 남아야 합니다.
- commit되지 않은 변경은 최종 결과에 없어야 합니다.
- 같은 WAL로 recovery를 반복해도 결과가 같아야 합니다.
- page LSN은 이미 적용한 WAL보다 뒤로 가지 않아야 합니다.

## 연결 exercise

이 문서를 읽은 뒤 [`wal-recovery-simulator`](../../exercises/wal-recovery-simulator/)를 수행합니다.

Exercise에서는 다음을 검사합니다.

- WAL flush 전 data page write 거부
- committed update redo
- commit되지 않은 update 역순 undo
- `page_lsn`을 사용한 중복 redo 방지
- 같은 WAL로 반복 recovery
- 잘못된 LSN flush 요청 거부

## 완료 기준

다음 질문에 답할 수 있어야 합니다.

1. 여러 row version이 reader와 writer의 충돌을 줄이는 이유는 무엇입니까?
2. Snapshot이 어떤 version을 볼 수 있는지 어떤 transaction 정보로 판단합니까?
3. MVCC만으로 write skew를 막지 못하는 이유는 무엇입니까?
4. Data page보다 WAL을 먼저 기록해야 하는 이유는 무엇입니까?
5. `page_lsn`이 redo를 반복 실행할 수 있게 하는 이유는 무엇입니까?
6. Commit 없는 update를 log 역순으로 undo해야 하는 이유는 무엇입니까?
7. Checkpoint가 durability 자체를 보장하지 않는 이유는 무엇입니까?
