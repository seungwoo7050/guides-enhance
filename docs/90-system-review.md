# Database Systems 종합 검토

## 문서의 역할

이 문서는 새로운 기능을 설명하지 않습니다. 앞에서 배운 내용을 하나의 요청, 느린 query, deadlock, crash와 migration 상황에 연결해 최종 이해를 확인합니다.

완료 후 다음을 할 수 있어야 합니다.

- 논리 데이터 규칙과 physical 저장 방식을 구분하면서 같은 설명에 연결합니다.
- SQL 결과와 execution plan을 함께 검토합니다.
- schema constraint, transaction, lock, MVCC와 WAL이 각각 막는 실패를 구분합니다.
- index와 buffer pool이 읽기, 쓰기와 복구에 미치는 영향을 추적합니다.
- migration이나 장애가 발생했을 때 먼저 확인할 증거를 정합니다.
- 현재 exercise가 자동으로 검증하지 않는 범위를 명시합니다.

## Ticket 생성 요청을 끝까지 추적합니다

다음 API를 생각해 보겠습니다.

```text
POST /organizations/7/projects/3/tickets
```

입력:

```json
{
  "title": "checkout timeout",
  "assigneeId": 19,
  "priority": 5
}
```

### 1. 논리 데이터 규칙

먼저 다음을 답합니다.

- ticket을 유일하게 식별하는 key는 무엇입니까?
- `project_id=3`이 organization 7에 속하는지 어떻게 검사합니까?
- assignee 19가 organization 7의 member인지 어디에서 검사합니까?
- title이 빈 문자열이면 누가 거부합니까?
- 초기 status와 `closed_at` 값은 무엇입니까?
- 성공 후 어떤 row가 생기며 실패하면 무엇도 남지 않아야 합니까?

Schema에서는 organization ID를 포함한 composite foreign key, `CHECK`, `NOT NULL`과 unique key를 사용할 수 있습니다. Membership 활성 상태처럼 현재 축소 schema에 없는 값은 application과 transaction에서 추가로 검사해야 합니다.

### 2. SQL과 transaction

다음 작업이 필요할 수 있습니다.

```text
project와 membership 확인
→ ticket insert
→ activity insert
→ project 통계 갱신
```

확인할 내용:

- 하나의 statement에서 함께 검사할 수 있는 조건은 무엇입니까?
- 동시에 membership이 비활성화되면 어떤 결과를 허용합니까?
- 어느 row를 어떤 순서로 lock합니까?
- 같은 ticket 번호 insert 경쟁은 unique constraint로 처리할 수 있습니까?
- serialization failure와 deadlock은 전체 transaction에서 재시도합니까?
- 외부 알림은 commit 뒤에 전달합니까?

Atomicity만으로 write skew나 check-then-insert race가 해결되지 않는다는 점을 설명해야 합니다.

### 3. Page와 index 변경

Ticket row는 record로 변환되어 heap page의 slot에 들어갑니다.

```text
ticket tuple
→ record encoding
→ target heap page
→ slot ID
→ RID(page_id, slot_id)
```

다음도 함께 바뀔 수 있습니다.

- primary key index
- organization별 open-ticket index
- assignee queue index
- project backlog를 지원하는 index

Page에 공간이 없으면 다른 page를 선택하거나 새 page를 할당합니다. B+ tree leaf가 가득 차면 split하고 parent에 separator를 추가합니다. Record가 compaction으로 움직여도 slot ID가 유지되어 index RID가 같은 record를 가리켜야 합니다.

### 4. Buffer pool과 WAL

Heap page와 index page를 수정하려면 buffer pool에서 fetch하고 pin합니다. 변경 후 dirty로 unpin합니다.

```text
WAL record append
→ page byte 변경과 page_lsn 갱신
→ commit record append
→ commit WAL flush
→ 성공 응답
→ dirty data page는 나중에 flush될 수 있음
```

Dirty frame을 다른 page에 사용하기 전에 WAL이 해당 `page_lsn`까지 durable해야 합니다.

Crash 위치에 따라 결과가 달라집니다.

- Commit WAL이 없으면 transaction 결과를 최종 상태에 남기지 않습니다.
- Commit WAL은 있지만 data page가 이전 값이면 redo합니다.
- Uncommitted dirty page가 disk에 도달했다면 undo가 필요합니다.
- 같은 WAL을 다시 읽어도 `page_lsn`으로 이미 적용한 변경을 건너뜁니다.

클라이언트가 commit 응답을 받지 못했다면 결과가 불확실할 수 있습니다. Operation ID로 실제 상태를 조회한 뒤 재시도해야 합니다.

### 5. 조회와 execution plan

다음 query를 사용합니다.

```sql
SELECT id, title, priority, created_at
FROM tickets
WHERE org_id = 7
  AND project_id = 3
  AND status <> 'DONE'
ORDER BY priority DESC, created_at DESC, id DESC
LIMIT 50;
```

확인할 내용:

- 한 row가 ticket 하나를 뜻합니까?
- 정렬이 전체 순서를 만듭니까?
- 다음 page cursor에 `(priority, created_at, id)` 전체가 들어갑니까?
- composite 또는 partial index의 equality prefix는 무엇입니까?
- 반환 row가 많을 때 sequential scan이 더 나을 수 있습니까?
- `EXPLAIN ANALYZE, BUFFERS`에서 estimated/actual rows, loops, block read와 sort를 확인했습니까?
- 큰 tenant와 작은 tenant에서 같은 plan이 적절합니까?

Index를 추가한 뒤에는 insert latency, WAL 양과 index 크기도 측정합니다.

### 6. Migration

새 `severity` 또는 `priority` column을 필수로 추가한다고 가정합니다.

```text
expand
→ 새 write가 값을 기록하도록 배포
→ 기존 row batch backfill
→ 허용 값 검증
→ NOT NULL 적용
→ 모든 application 전환 확인
→ 이전 column 제거
```

확인할 내용:

- 이전 application이 expand 이후에도 write할 수 있습니까?
- Backfill은 어떤 stable key 순서와 batch 크기를 사용합니까?
- 새 write와 backfill이 같은 row를 수정하면 어느 값이 우선합니까?
- 중단 뒤 어디서 다시 시작합니까?
- Constraint validation과 index build가 lock을 얼마나 잡습니까?
- WAL, replica lag와 disk 여유를 어떻게 관찰합니까?
- 실패한 단계는 rollback할 수 있습니까, 아니면 수정 migration으로 진행해야 합니까?

## 장애 상황별 확인 순서

### 특정 tenant의 query가 느려졌습니다

먼저 다음을 수집합니다.

1. 실제 SQL과 parameter
2. 반환 row 수와 tenant 크기
3. 호출 빈도와 latency 분포
4. `EXPLAIN (ANALYZE, BUFFERS)`
5. estimated rows와 actual rows가 처음 크게 달라지는 node
6. table/index 크기와 마지막 `ANALYZE` 시각
7. lock wait, temp spill과 concurrent workload
8. 최근 schema 또는 데이터 분포 변경

Index부터 추가하지 않습니다. 통계 노후화, skew, deep offset, lock wait, disk saturation과 missing index는 서로 다른 문제입니다.

### Deadlock이 발생했습니다

다음을 확인합니다.

- 관련 transaction과 SQL
- 각 transaction이 이미 가진 lock
- 기다리는 lock
- 업무 key
- lock 획득 순서
- transaction 시작·종료 시각
- retry 횟수와 최종 결과

수정 방법은 공통 lock 순서, 조건부 single statement, transaction 길이 축소나 명시적인 guard row일 수 있습니다. Timeout을 늘리는 것만으로 원인을 해결하지 않습니다.

### Disk 사용량이 급증했습니다

후보를 나눠 확인합니다.

- 오래 열린 snapshot 때문에 회수하지 못한 dead tuple
- WAL 보존 증가
- index bloat와 중복 index
- 대량 backfill과 새 index
- sort/hash 임시 파일
- backup 또는 replica lag

Table 크기 하나만 보지 말고 heap, index, WAL, temp와 보존 요구를 따로 측정합니다.

### Crash 뒤 시작 시간이 길어졌습니다

다음을 확인합니다.

- 마지막 checkpoint 이후 WAL 범위
- redo 처리 속도
- storage read/write 지연
- recovery가 처리 중인 LSN
- replica와 backup이 보존한 WAL
- recovery 중 반복 crash가 있었는지

Recovery를 강제로 다시 시작하면 같은 WAL을 다시 읽어 시작 시간이 더 길어질 수 있습니다. 현재 진행 위치와 I/O 상태를 먼저 확인합니다.

## 구성 요소별 확인 표

| 대상 | 반드시 유지할 값 | 대표 실패 | 검증 방법 |
| --- | --- | --- | --- |
| Relation·SQL | row 단위, 중복, `NULL`, 순서 | 누락, 중복, 불안정한 page | 예상 결과 fixture |
| Schema | key, 참조, 값 범위 | orphan, 중복 업무 key | 잘못된 insert 거부 |
| Page | slot, free space, record 범위 | page 손상, RID 변경 | 직렬화 왕복과 손상 입력 |
| Index | 정렬, 검색, RID 일치 | 누락, stale RID | full scan 결과와 비교 |
| Buffer pool | pin, dirty, page table | pinned eviction, lost write | 결정적인 fetch 순서 |
| Transaction | 여러 write의 원자성 | lost update, write skew | 실제 concurrent session |
| WAL | write-ahead, LSN 순서 | committed 값 손실, uncommitted 값 잔존 | crash 위치별 recovery |
| Executor | bag 의미와 `NULL` | 잘못된 join multiplicity | 세 알고리즘 결과 비교 |
| Optimizer | row 추정과 비용 근거 | 나쁜 join 순서, spill | estimate/actual 비교 |
| Migration | 혼합 version 호환 | 긴 lock, 중간 상태 불일치 | 단계별 재실행과 검증 |

## 두 통합 project의 차이

### `ticketing-database`

질문:

> 업무 규칙을 schema, query, transaction과 migration으로 어떻게 검사합니까?

주요 증거:

- PostgreSQL constraint 실패
- query 결과와 stable ordering
- 실제 index scan
- migration 재실행
- tenant 참조 거부

필수 학습 경로에 포함됩니다.

### `mini-storage-engine`

질문:

> Page, buffer pool, WAL과 index가 하나의 insert와 crash를 어떻게 처리합니까?

주요 증거:

- Python page 직렬화
- deterministic Clock replacement
- WAL-before-data
- committed insert recovery
- heap/index 재구성

개별 내부 동작은 전용 exercise가 이미 검증하므로 선택 project입니다.

## 이 저장소가 보장하지 않는 범위

전체 과정을 마쳤다고 해서 다음 경험까지 자동으로 생기지는 않습니다.

- PostgreSQL의 모든 lock mode와 source code 이해
- production backup·restore 운영
- replication, sharding과 failover 설계
- 분산 transaction과 saga
- 모든 workload의 성능 예측
- production DBMS 구현

실제 요구가 생겼을 때 해당 DBMS의 문서와 운영 환경에서 추가로 검증해야 합니다.

## 최종 완료 절차

1. 필수 exercise 9개를 각 project directory에서 다시 검사합니다.
2. 이 문서의 ticket 생성 요청을 처음부터 끝까지 설명합니다.
3. 느린 query, deadlock, crash와 migration 상황에서 확인할 증거를 순서대로 작성합니다.
4. 설명하지 못한 부분만 관련 문서와 exercise로 돌아갑니다.
5. 자동 test가 확인한 범위와 확인하지 않은 범위를 구분합니다.

## 완료 기준

다음 내용을 하나의 설명으로 연결할 수 있어야 합니다.

```text
업무 규칙
→ schema와 SQL 결과
→ transaction과 concurrent conflict
→ page, index와 buffer 변화
→ WAL과 commit
→ crash recovery
→ 조회 execution plan
→ 통계와 index 선택
→ migration과 운영 검증
```

각 단계에서 다음을 포함해야 합니다.

- 어떤 파일이나 객체가 값을 보관하는지
- 정상 실행과 실패 뒤 어떤 값이 남는지
- 어느 test나 SQL이 그 사실을 확인하는지
- 현재 구현이 확인하지 않는 범위
- 성능 판단에 사용한 데이터와 환경
