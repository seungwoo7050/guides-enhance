# Transaction, 격리와 lock

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 합니다.

- atomicity와 isolation이 서로 다른 실패를 막는 이유
- read-modify-write가 transaction 안에서도 잘못된 결과를 만들 수 있는 이유
- lost update, non-repeatable read, phantom과 write skew의 차이
- row lock, guard row와 unique constraint가 충돌을 만드는 범위
- deadlock이 발생하는 조건과 lock 순서를 통일하는 이유
- serialization failure와 deadlock을 전체 transaction 단위로 재시도해야 하는 이유

## Transaction은 상태 변경을 하나로 묶습니다

`BEGIN`과 `COMMIT`을 추가했다고 해서 동시 실행까지 자동으로 안전해지는 것은 아닙니다. 먼저 변경할 상태를 구체적으로 적습니다.

```text
시작할 때 참이어야 하는 조건:
읽는 row와 검색 조건:
변경할 row:
성공 후 값:
실패 후 남아야 할 값:
동시에 실행될 수 있는 다른 transaction:
```

예를 들어 재고 10개에서 7개를 예약한다면 다음처럼 적을 수 있습니다.

```text
조건: available >= 0
변경: available := available - 7
허용: 변경 직전 available >= 7인 경우만 성공
```

한 요청이 실패했을 때 일부 값만 남지 않아야 할 뿐 아니라, 두 요청이 겹쳐도 재고가 음수가 되거나 두 요청이 모두 성공했다고 판단하면 안 됩니다.

## ACID를 실패 종류로 구분합니다

### Atomicity

한 transaction의 변경이 모두 적용되거나 모두 취소됩니다. 여러 table을 수정하다가 중간에 실패했을 때 일부만 남는 문제를 막습니다.

### Consistency

DBMS가 업무 규칙을 스스로 알지는 못합니다. Schema constraint와 transaction 코드가 허용 상태를 정의하며, 성공한 변경은 허용 상태에서 다른 허용 상태로 이동해야 합니다.

### Isolation

동시에 실행되는 transaction이 서로의 read와 write에 영향을 줄 때 잘못된 성공을 막습니다. 어떤 현상을 막는지는 isolation level, SQL 문장과 명시적 lock 사용 방식에 따라 달라집니다.

### Durability

Commit 성공을 반환한 변경이 crash 뒤에도 복구됩니다. WAL과 recovery가 이 속성을 구현합니다.

“Transaction을 사용했습니다”라는 말만으로는 충분하지 않습니다. 어느 실패를 어떤 SQL이나 lock이 막는지 설명해야 합니다.

## Read-modify-write가 만드는 lost update

다음 두 transaction을 보겠습니다.

```text
A: SELECT available → 10
B: SELECT available → 10
A: UPDATE available = 3
B: UPDATE available = 3
A: COMMIT
B: COMMIT
```

두 요청은 각각 7개 예약에 성공했다고 생각하지만 최종 값은 3입니다. 한 변경이 다른 변경을 덮었습니다.

판단과 변경을 같은 statement에 넣으면 같은 row update가 충돌 지점이 됩니다.

```sql
UPDATE inventory
SET available = available - $1
WHERE sku = $2
  AND available >= $1
RETURNING available;
```

같은 row를 갱신하는 두 statement는 row lock에서 순서를 기다립니다. 뒤에 실행되는 statement는 앞선 변경이 반영된 값을 기준으로 `available >= $1`을 다시 확인합니다.

애플리케이션이 예전에 읽은 절대값을 다시 쓰기보다 DBMS가 현재 값을 기준으로 조건과 변경을 함께 수행하게 하는 편이 안전합니다.

## 대표적인 이상 현상

### Dirty read

다른 transaction이 아직 commit하지 않은 값을 읽습니다. 해당 transaction이 rollback하면 실제로 존재하지 않았던 값을 업무 판단에 사용한 셈이 됩니다. PostgreSQL의 `READ COMMITTED`는 dirty read를 허용하지 않습니다.

### Non-repeatable read

같은 transaction에서 같은 row를 두 번 읽었는데, 그 사이 다른 transaction이 commit해서 값이 달라집니다.

### Phantom

같은 검색 조건을 다시 실행했는데 다른 transaction의 insert나 delete로 결과 row 집합이 달라집니다.

### Lost update

두 transaction이 같은 이전 값을 읽고 각각 새 절대값을 쓴 결과 한쪽 변경이 사라집니다. Isolation level 이름만 보지 말고 실제 `UPDATE` 문장을 확인해야 합니다.

### Write skew

각 transaction은 서로 다른 row를 수정하지만, 두 변경을 합치면 여러 row에 걸친 조건이 깨집니다.

```text
doctor 1: on_call=true
doctor 2: on_call=true
조건: 최소 한 명은 on_call이어야 함

A: doctor 2가 있으므로 doctor 1을 off
B: doctor 1이 있으므로 doctor 2를 off
결과: on_call doctor가 0명
```

서로 다른 row를 갱신하므로 단순 row lock만으로는 두 transaction이 충돌하지 않을 수 있습니다.

## PostgreSQL isolation level을 실제 현상과 연결합니다

### `READ COMMITTED`

각 statement가 시작할 때 새 snapshot을 볼 수 있습니다. 같은 transaction의 두 `SELECT`가 다른 committed 값을 볼 수 있습니다. Row update가 충돌하면 기다린 뒤 최신 row에서 조건을 다시 평가할 수 있습니다.

### `REPEATABLE READ`

Transaction 동안 같은 snapshot을 사용합니다. 반복 read는 안정적이지만 서로 다른 row를 수정하는 write skew를 자동으로 막지는 못할 수 있습니다.

### `SERIALIZABLE`

동시에 실행된 결과가 어떤 순차 실행과 같은지 검사합니다. 위험한 의존 관계가 발견되면 transaction 하나를 serialization failure로 중단합니다.

`SERIALIZABLE`은 모든 transaction이 반드시 성공한다는 뜻이 아닙니다. 잘못된 결과를 commit하는 대신 한쪽을 명시적으로 실패시키며, 호출자는 전체 transaction을 재시도해야 합니다.

## 명시적 lock

### `SELECT ... FOR UPDATE`

읽은 row를 이어서 변경할 때 사용합니다.

```sql
SELECT available
FROM inventory
WHERE sku = $1
FOR UPDATE;
```

같은 row를 update하거나 lock하려는 transaction과 충돌합니다. 다만 검색 결과가 0행인 상태 자체를 항상 보호하지는 못합니다. 새 row insert를 막아야 한다면 unique constraint, predicate conflict나 guard row 같은 다른 방법이 필요합니다.

### Guard row

여러 row에 걸친 조건을 변경하는 모든 transaction이 같은 row를 먼저 잠그게 할 수 있습니다.

```sql
SELECT id
FROM shift_guard
WHERE id = 1
FOR UPDATE;

SELECT count(*)
FROM doctors
WHERE on_call;
```

당직 상태를 바꾸는 모든 코드가 같은 guard row를 잠가야 합니다. 일부 경로가 이를 생략하면 보호되지 않습니다. Guard row는 구현이 단순하지만 요청이 한 row에 몰리는 병목이 될 수 있습니다.

[`postgres-concurrency-guards`](../../exercises/postgres-concurrency-guards/)는 재고 변경에는 조건부 `UPDATE`를 사용하고, 여러 doctor row에 걸친 조건에는 guard row를 사용합니다.

### Advisory lock

Table row가 아닌 업무 key로 lock을 잡을 수 있습니다. Lock key를 만드는 방법, transaction 또는 session 수명, 모든 쓰기 경로가 같은 key를 사용하는지를 명확히 해야 합니다. Schema constraint를 대신하는 기본 수단으로 사용하면 안 됩니다.

## Unique constraint로 경쟁 결과를 결정합니다

다음 코드는 race를 만듭니다.

```text
SELECT로 값이 없음을 확인
→ INSERT
```

두 transaction이 동시에 “없음”을 확인한 뒤 같은 값을 insert할 수 있습니다. 업무상 하나만 존재해야 한다면 DB에 unique constraint를 두고 insert를 실제 충돌 지점으로 사용합니다.

```sql
INSERT INTO users(email)
VALUES ($1)
ON CONFLICT (...) DO ...;
```

또는 `unique_violation`을 중복 생성 요청으로 변환합니다. 먼저 commit한 transaction이 성공하고 다른 transaction은 명시적으로 실패하거나 기존 row를 사용합니다.

## Deadlock

다음 네 조건이 함께 있을 때 deadlock이 생길 수 있습니다.

- 같은 자원을 둘이 동시에 사용할 수 없습니다.
- 자원을 가진 채 다른 자원을 기다립니다.
- 이미 잡은 자원을 강제로 빼앗을 수 없습니다.
- 대기 관계가 원을 만듭니다.

계좌 A에서 B로 이체하는 transaction과 B에서 A로 이체하는 transaction이 각각 source account를 먼저 잠그면 서로 상대 account를 기다릴 수 있습니다.

모든 코드가 같은 순서로 lock을 잡으면 순환 가능성을 줄일 수 있습니다.

```text
항상 작은 account_id부터 lock합니다.
```

다른 table과 lock 종류가 섞이면 deadlock을 완전히 없앨 수 있다고 단정하면 안 됩니다. DBMS가 deadlock을 감지하면 transaction 하나를 중단합니다.

## 재시도는 transaction 처음부터 수행합니다

Serialization failure나 deadlock victim이 된 경우 마지막 statement만 다시 실행하면 안 됩니다. 앞에서 읽은 값과 판단이 더 이상 유효하지 않을 수 있습니다.

안전한 재시도에는 다음 조건이 필요합니다.

- transaction 전체를 하나의 함수나 작업 단위로 묶습니다.
- retry 가능한 DB 오류를 다른 오류와 구분합니다.
- 매번 최신 상태를 다시 읽고 판단합니다.
- 최대 횟수와 전체 deadline을 둡니다.
- 짧은 backoff를 사용해 즉시 같은 충돌을 반복하지 않습니다.
- unique key나 idempotency key로 중복 결과를 막습니다.
- 외부 API 호출과 email 전송을 transaction 중간에 직접 수행하지 않습니다.

DB transaction 재시도와 서비스 사이 메시지 재전송은 관련은 있지만 같은 문제는 아닙니다.

## Transaction을 오래 열지 않습니다

오래 열린 transaction은 다음 문제를 만듭니다.

- lock을 오래 보유합니다.
- 오래된 MVCC version을 정리하지 못하게 합니다.
- WAL 보존량과 replica 지연을 늘릴 수 있습니다.
- 실패했을 때 다시 수행할 작업이 많아집니다.

사용자 입력을 기다리거나 큰 파일을 처리하는 동안 transaction을 열어 두지 않습니다. DB 값을 읽고 검증하고 변경하는 최소 구간만 transaction에 포함합니다.

## 동시성 검사는 실제로 겹쳐 실행합니다

순차 unit test만으로는 race를 확인할 수 없습니다. 최소한 두 DB session을 분리하고 특정 지점에서 실행이 겹치게 해야 합니다.

```text
session A와 B를 시작합니다.
두 transaction이 필요한 초기 read를 마치게 합니다.
write 또는 lock 요청을 겹쳐 실행합니다.
각 성공 여부와 최종 row를 확인합니다.
timeout과 deadlock을 성공으로 취급하지 않습니다.
```

무작위 부하에서 한 번도 실패하지 않았다는 사실은 안전함을 증명하지 않습니다. 먼저 재현 가능한 interleaving을 만들고 금지된 결과가 나오지 않는지 검사해야 합니다.

## 연결 exercise

이 문서를 읽은 뒤 [`postgres-concurrency-guards`](../../exercises/postgres-concurrency-guards/)를 수행합니다.

Exercise는 실제 PostgreSQL session 두 개를 사용해 다음을 검사합니다.

- 재고 10개에서 7개 예약 두 건 중 최대 한 건만 성공
- 당직 doctor 두 명이 동시에 해제되어도 최소 한 명 유지
- 조건부 `UPDATE`와 guard row가 실제 충돌을 만드는지
- 두 session이 timeout 안에 종료되는지

## 완료 기준

다음 질문에 답할 수 있어야 합니다.

1. Atomicity가 보장되어도 lost update가 가능한 이유는 무엇입니까?
2. 조건부 `UPDATE`가 read-modify-write보다 안전한 이유는 무엇입니까?
3. Write skew가 서로 다른 row update에서도 발생하는 이유는 무엇입니까?
4. Row lock, guard row, unique constraint와 `SERIALIZABLE`은 각각 어떤 충돌을 만듭니까?
5. Deadlock이나 serialization failure를 statement 하나가 아니라 전체 transaction에서 재시도해야 하는 이유는 무엇입니까?
6. 동시성 테스트가 실제로 두 session의 실행을 겹치게 하는지 어떻게 확인합니까?
