# Schema, index와 안전한 tuning 절차

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 합니다.

- 성능 변경 전에 업무 규칙과 대표 workload를 먼저 정하는 이유
- schema constraint, query rewrite, index와 denormalization을 검토하는 순서
- composite index의 column 순서를 equality, range와 ordering에 맞추는 방법
- partial, covering과 expression index의 적용 조건과 쓰기 비용
- expand, backfill, validate, contract 순서가 혼합 version 배포를 안전하게 하는 이유
- 큰 table의 backfill과 index build가 lock, WAL과 replica에 미치는 영향
- rollback과 roll-forward를 구분해야 하는 이유
- correctness, latency, write cost와 운영 복구를 함께 검증하는 방법

## 변경 전에 네 가지를 적습니다

Tuning은 느린 SQL 한 줄에 index를 추가하는 작업이 아닙니다. 먼저 다음을 정합니다.

```text
업무 규칙:
대표 workload:
성공 기준:
허용 가능한 쓰기·운영 비용:
```

예:

```text
업무 규칙: 같은 조직 안에서 project slug는 유일합니다.
workload: 조직별 OPEN ticket 50개를 최신순으로 조회합니다.
성공 기준: p95 < 50ms, page 사이 중복과 누락이 없습니다.
비용 한도: ticket insert p95 증가 < 5ms, index 크기 < 2GB입니다.
```

이 정보 없이 index부터 추가하면 특정 조회는 빨라져도 write, vacuum, backup과 migration이 악화될 수 있습니다.

## 먼저 결과 의미를 확인합니다

성능 측정 전에 다음을 확인합니다.

- query가 올바른 row 단위를 반환하는지
- `NULL`, outer join과 중복 처리가 맞는지
- 정렬에 동률 해소 key가 있는지
- schema가 잘못된 상태를 거부하는지
- 동시 transaction에서도 업무 조건이 유지되는지

틀린 결과를 더 빨리 반환하는 것은 개선이 아닙니다. 애플리케이션에서 중복 제거하거나 누락을 보정하는 코드가 있다면 query나 schema가 결과 의미를 충분히 표현하지 못하는지 확인합니다.

## 대표 workload를 구체적으로 기록합니다

“이 table은 CRUD를 많이 합니다”로는 index를 설계할 수 없습니다.

```text
query ID
호출 빈도
parameter 분포
반환 row 수
허용 latency
transaction 길이
동시에 실행되는 write
filter
join
정렬과 pagination 방식
```

평균값만 보지 말고 다음 차이를 포함합니다.

- 작은 tenant와 큰 tenant
- 최근 날짜와 오래된 날짜
- 흔한 status와 드문 status
- cold cache와 warm cache
- 평시와 batch 동시 실행

## Schema를 먼저 검토합니다

### Type과 값 범위

숫자를 text로 저장하면 비교, 정렬과 index 크기가 달라집니다. Timestamp의 timezone 의미, 금액의 scale, identifier 생성 주체와 collation을 명확히 합니다.

### Key와 constraint

`UNIQUE`, foreign key와 `CHECK`는 잘못된 데이터를 막고 옵티마이저가 row 관계를 판단하는 정보도 제공합니다. 기존 table에 constraint를 추가할 때는 현재 데이터 검증 시간과 lock을 고려합니다.

### Row 폭과 update 빈도

자주 읽고 갱신하는 row에 큰 payload를 함께 두면 page당 row 수가 줄고 cache 사용량이 늘어납니다. 수명과 접근 방식이 다른 데이터를 별도 table로 나눌 수 있습니다.

반대로 table을 지나치게 나누면 join과 transaction 작업이 늘어납니다. 대표 workload를 기준으로 판단합니다.

## Query를 먼저 고칠 수 있습니다

Index를 추가하기 전에 query 자체에서 불필요한 작업을 줄일 수 있습니다.

- 필요한 column만 반환합니다.
- N+1 query를 join이나 batch query로 바꿉니다.
- 같은 correlated subquery를 여러 번 계산하지 않습니다.
- 깊은 `OFFSET` pagination을 keyset pagination으로 바꿉니다.
- index column에 불필요한 함수를 적용하지 않습니다.
- 의미가 같은지 확인한 뒤 index가 사용할 수 있는 predicate로 바꿉니다.

Keyset pagination 예:

```sql
WHERE (updated_at, id) < ($1, $2)
ORDER BY updated_at DESC, id DESC
LIMIT 50;
```

정렬 key는 전체 순서를 만들 수 있도록 unique tie-breaker까지 포함해야 합니다.

## Composite index 순서

대표적인 검토 순서는 다음과 같습니다.

```text
항상 equality로 고정되는 column
→ range 조건 또는 필요한 정렬 column
→ 동률을 해소하는 key
→ 결과에 필요한 INCLUDE column
```

예:

```sql
WHERE tenant_id = $1
  AND status = 'OPEN'
  AND updated_at < $2
ORDER BY updated_at DESC, id DESC
LIMIT 50;
```

후보 index:

```sql
CREATE INDEX ...
ON tickets(tenant_id, status, updated_at DESC, id DESC);
```

다만 `status='OPEN'`이 대부분 row라면 `status`를 key에 둘 가치가 작을 수 있습니다. Partial index가 더 적절한지도 확인합니다. Column 순서는 공식이 아니라 실제 분포와 query plan으로 검증합니다.

## Partial index

특정 조건의 row만 저장합니다.

```sql
CREATE INDEX ...
ON jobs(scheduled_at, id)
WHERE completed_at IS NULL;
```

장점:

- index 크기를 줄입니다.
- 자주 조회하는 작은 상태 집합을 빠르게 찾을 수 있습니다.
- 해당 조건 밖 row의 index write를 줄일 수 있습니다.

주의할 점:

- query predicate가 partial 조건을 만족한다는 사실을 planner가 판단할 수 있어야 합니다.
- 상태가 바뀔 때 index entry insert/delete가 발생합니다.
- 조건에 포함되는 row 비율이 커지면 장점이 줄어듭니다.

## Covering index와 `INCLUDE`

검색과 정렬에는 쓰지 않지만 반환에 필요한 column을 leaf에 넣을 수 있습니다.

```sql
CREATE INDEX ...
ON events(tenant_id, created_at DESC, id DESC)
INCLUDE (event_type, actor_id);
```

Heap 접근을 줄일 가능성이 있지만 포함한 column도 index 크기와 write 비용을 늘립니다. 자주 바뀌거나 큰 payload를 무분별하게 포함하지 않습니다. `EXPLAIN ANALYZE`의 실제 heap fetch를 확인합니다.

## Expression index

Query가 같은 표현을 사용할 때 유용합니다.

```sql
CREATE UNIQUE INDEX users_email_lower_uq
ON users(lower(email));
```

다음 조건을 함께 정해야 합니다.

- 대소문자 정규화 방식
- locale과 collation
- 애플리케이션 validation과 DB 제약의 일치
- query가 같은 표현을 사용하는지

Expression index가 원래 column의 의미를 대신 정해 주지는 않습니다.

## Index는 모든 write에 비용을 추가합니다

Insert, delete와 key column update는 관련 index도 바꿉니다.

- WAL 양이 늘어납니다.
- index page split이 발생합니다.
- buffer pool 공간을 사용합니다.
- vacuum 작업이 늘어납니다.
- backup과 restore 크기가 커집니다.
- replica가 처리할 byte가 늘어납니다.

사용 횟수가 적다는 이유만으로 바로 삭제하지 않습니다. Unique constraint, 월간 batch, 장애 조사와 운영 query가 사용하는지 확인합니다.

## Denormalization은 복구 방법과 함께 제안합니다

측정된 병목이 있을 때 aggregate나 표시 값을 중복 저장할 수 있습니다.

예:

```text
project.open_ticket_count를 별도 column에 저장합니다.
```

추가하기 전에 다음을 답해야 합니다.

```text
원본 값은 어디에 있습니까?
언제 함께 갱신합니까?
같은 transaction에서 바뀝니까?
불일치를 어떻게 찾습니까?
전체 값을 어떻게 다시 계산합니까?
얼마 동안 불일치를 허용합니까?
갱신 실패 시 조회는 어떤 값을 사용합니까?
```

이 질문에 답하지 못하면 읽기 비용을 데이터 불일치 위험으로 바꾼 것입니다.

## Migration은 여러 application version이 공존하는 변경입니다

배포 중에는 이전 application과 새 application이 동시에 실행될 수 있습니다. Schema 변경은 한 SQL 파일 실행으로 끝나지 않습니다.

### Expand

기존 코드가 계속 작동하는 상태로 새 schema를 추가합니다.

- nullable column을 추가합니다.
- 새 table이나 index를 추가합니다.
- 이전 column과 새 column을 함께 읽거나 쓸 수 있게 합니다.

### Backfill

기존 row를 작은 batch로 채웁니다.

확인할 항목:

- stable key 순서
- batch 크기
- transaction 길이
- 중단 뒤 재개할 cursor
- 같은 batch를 다시 실행해도 안전한지
- 신규 write와의 우선순위
- replica lag와 WAL 양

### Validate

새 값이 모든 기존 row에서 허용되는지 검사합니다.

PostgreSQL에서는 `CHECK ... NOT VALID`로 새 write를 먼저 제한하고 기존 row 검증을 나중에 수행할 수 있습니다. 실제 lock과 version별 동작은 사용하는 PostgreSQL 문서를 확인해야 합니다.

### Contract

실행 중인 application이 모두 새 schema를 사용한다는 사실을 확인한 뒤 이전 column, table이나 호환 코드를 제거합니다.

```text
expand와 contract를 같은 배포에 묶지 않습니다.
```

## `NOT NULL` column 추가 예

큰 table에 필수 column을 한 번에 추가하면 기존 row 때문에 실패하거나 긴 검증이 필요할 수 있습니다.

```text
1. nullable column을 추가합니다.
2. 새 application이 새 write에 값을 기록합니다.
3. 기존 row를 작은 batch로 backfill합니다.
4. NULL row가 0개인지 확인합니다.
5. 허용 값 constraint를 validate합니다.
6. NOT NULL을 적용합니다.
7. 이전 호환 코드를 제거합니다.
```

각 단계는 중단 뒤 다시 실행할 수 있어야 하며, 중간 상태에서도 이전 application이 동작해야 합니다.

## Index build와 lock을 계획합니다

큰 production table에서 일반 `CREATE INDEX`는 write를 오래 막을 수 있습니다. PostgreSQL의 concurrent build는 blocking을 줄일 수 있지만 더 오래 걸리고 실패 시 invalid index가 남을 수 있습니다.

계획에 다음을 포함합니다.

- 예상 table과 index 크기
- 필요한 추가 disk 공간
- WAL과 replica 지연
- statement와 lock timeout
- 실패 뒤 invalid object 확인
- 중복 실행 방지
- 완료 뒤 `ANALYZE`와 plan 확인

사용하는 DBMS와 version의 정확한 동작을 공식 문서에서 확인해야 합니다.

## Rollback과 roll-forward

모든 schema 변경을 단순히 되돌릴 수 있는 것은 아닙니다.

- column을 삭제하면 즉시 데이터를 되살릴 수 없습니다.
- backfill 뒤 새 application이 새 형식으로 쓰기 시작할 수 있습니다.
- index build 실패는 잘못된 object를 지우고 다시 만드는 편이 안전할 수 있습니다.
- 외부 시스템에도 변경이 전달되었을 수 있습니다.

각 단계에 다음 중 하나를 정합니다.

```text
이전 상태로 되돌릴 수 있습니다.
수정 migration으로 앞으로 진행해야 합니다.
backup restore로만 되돌릴 수 있습니다.
```

Backup이 있다는 사실만으로 즉시 rollback 가능한 것은 아닙니다. Restore 시간과 허용 데이터 손실 범위를 알아야 합니다.

## 전체 tuning 절차

```text
1. 업무 규칙과 query 결과를 확인합니다.
2. workload와 parameter 분포를 기록합니다.
3. EXPLAIN ANALYZE와 BUFFERS로 기준값을 남깁니다.
4. 가장 큰 비용 또는 추정 오차에 대한 가설을 하나 세웁니다.
5. 변경 하나를 적용합니다.
6. 결과와 동시성 검사를 다시 실행합니다.
7. latency, I/O, memory와 write 비용을 비교합니다.
8. migration, rollback 또는 roll-forward 절차를 작성합니다.
9. 제한된 범위에서 배포하고 관찰합니다.
10. 효과가 없는 변경은 제거합니다.
```

여러 query rewrite와 index를 한 번에 적용하면 어떤 변경이 효과를 냈는지 판단하기 어렵습니다.

## 연결 exercise

이 문서를 읽은 뒤 두 project를 사용합니다.

1. [`postgres-workload-indexes`](../../exercises/postgres-workload-indexes/)
   - composite, partial과 covering index를 실제 plan과 연결합니다.

2. [`ticketing-database`](../../exercises/ticketing-database/)
   - `migration.sql`, `queries.sql`, `indexes.sql`을 함께 실행합니다.
   - migration을 두 번 적용해 재실행 가능성을 확인합니다.
   - tenant filter, stable ordering과 실제 index scan을 검사합니다.

## 완료 기준

하나의 변경 제안에 다음 내용을 포함할 수 있어야 합니다.

- 정확한 업무 규칙과 query 결과
- 대표 parameter 분포와 기준 plan
- 선택한 schema, query 또는 index 변경의 이유
- 읽기 개선과 함께 증가하는 write·공간 비용
- 이전·새 application이 공존할 수 있는 migration 단계
- 중단 뒤 재개 가능한 backfill
- 실패 시 rollback 또는 roll-forward 방법
- 변경 전후 결과·동시성·성능 증거
