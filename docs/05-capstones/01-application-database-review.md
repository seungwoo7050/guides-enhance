# 애플리케이션 데이터베이스 검토

## 문서의 역할

이 문서는 필수 개념을 하나의 ticket 관리 시나리오에 다시 적용하는 참고 자료입니다. 새로운 개념을 추가하지는 않습니다. 다음 내용을 한 schema와 workload 안에서 함께 확인합니다.

- 업무 규칙을 key와 constraint로 표현합니다.
- SQL의 `NULL`, 중복, outer join과 정렬 결과를 확인합니다.
- 동시 변경에서 깨질 수 있는 조건과 실제 충돌 지점을 정합니다.
- 대표 query의 실행 계획을 측정합니다.
- composite·partial index를 workload에 맞춰 설계합니다.
- 이전 application과 새 application이 함께 실행되는 동안 migration을 진행합니다.
- 변경 전후의 결과, 성능과 운영 비용을 기록합니다.

필수 exercise인 [`ticketing-database`](../../exercises/ticketing-database/)를 진행할 때 통합 검토가 필요하면 이 문서를 사용합니다.

## 시나리오

여러 조직이 사용하는 ticket 관리 database를 다룹니다.

```text
organization
user
organization membership
project
ticket
assignee
status와 priority
```

대표 업무 규칙은 다음과 같습니다.

- 사용자 email은 대소문자를 무시하고 유일합니다.
- project 이름은 organization 안에서 유일합니다.
- ticket이 참조하는 project, reporter와 assignee는 같은 organization에 있어야 합니다.
- `DONE` ticket에는 `closed_at`이 반드시 있고, 그 외 상태에는 없어야 합니다.
- organization별 미완료 ticket 목록은 `priority DESC, created_at DESC, id DESC`로 정렬합니다.
- assignee별 queue와 project별 backlog를 빠르게 조회합니다.
- 기존 `severity` 값을 새 `priority` column으로 옮기되 이전 column은 호환 기간 동안 남깁니다.

어떤 규칙은 foreign key나 `CHECK`만으로 검사할 수 있습니다. Membership 활성 상태와 ticket 담당자 변경이 동시에 일어나는 경우처럼 여러 row를 함께 확인해야 하는 규칙은 transaction과 lock을 추가로 검토해야 합니다.

## 1. 용어와 한 row가 뜻하는 대상을 정합니다

먼저 다음 표를 작성합니다.

| 대상 | 식별자 | organization 범위 | 삭제 뒤 남길 정보 |
| --- | --- | --- | --- |
| Organization |  |  |  |
| User |  | 전역 |  |
| Membership |  | organization별 |  |
| Project |  | organization별 |  |
| Ticket |  | organization별 |  |

전역 사용자와 organization membership은 서로 다른 대상을 나타냅니다. User가 존재한다고 해서 모든 organization의 ticket assignee가 될 수 있는 것은 아닙니다.

Query가 반환하는 한 row의 의미도 정합니다.

```text
organization별 미완료 ticket 목록 → ticket 하나당 한 row
assignee queue → 담당 ticket 하나당 한 row
project backlog → project 하나당 한 row
```

Comment나 activity table을 join했을 때 ticket이 comment 수만큼 반복되면 첫 두 query의 결과가 잘못된 것입니다.

## 2. 업무 규칙을 schema에 기록합니다

최소한 다음 항목을 확인합니다.

- primary key
- 업무상 유일한 candidate key
- organization ID가 포함된 composite key
- foreign key
- `NOT NULL`
- 값 범위와 column 조합을 검사하는 `CHECK`
- 삭제 시 참조 처리

Multi-tenant table에서 전역 ID 하나만 foreign key로 참조하면 다른 organization의 row를 연결할 수 있습니다.

예를 들어 ticket의 project를 다음처럼 제한할 수 있습니다.

```text
projects: UNIQUE(id, org_id)
tickets: FOREIGN KEY(project_id, org_id)
         REFERENCES projects(id, org_id)
```

Assignee도 `(org_id, assignee_id)`가 membership을 참조하게 하면 다른 organization의 user를 지정하는 insert를 DB가 거부합니다.

Constraint 이름은 운영 중 오류를 분류할 수 있도록 의미 있게 정합니다.

## 3. Query 결과를 실패 사례로 검사합니다

정상 결과만 확인하지 말고 다음 잘못된 query를 의도적으로 만들어 봅니다.

- nullable subquery를 사용하는 `NOT IN`
- `LEFT JOIN` 뒤 오른쪽 조건을 `WHERE`에 두어 unmatched row를 제거하는 query
- one-to-many join 뒤 ticket이 반복되는 query
- unique tie-breaker가 없는 `ORDER BY`
- organization filter가 빠진 query
- outer join 뒤 실제 child 수 대신 `count(*)`를 사용하는 query

각 query에 다음을 적습니다.

```text
한 row가 뜻하는 대상
반환 column
join key와 multiplicity
filter
group key
정렬과 tie-breaker
organization 제한
```

[`ticketing-database`](../../exercises/ticketing-database/)의 view는 다음 세 workload를 제공합니다.

- `q_project_backlog`
- `q_org_open_tickets`
- `q_assignee_queue`

View가 row 집합을 정의하더라도 호출 query의 `ORDER BY`까지 대신하지는 않습니다. Pagination을 수행할 때는 호출 query에 전체 정렬 key를 다시 명시해야 합니다.

## 4. 동시에 바뀌는 row를 확인합니다

Assignee 변경은 다음 작업을 포함할 수 있습니다.

```text
membership이 활성 상태인지 확인합니다.
ticket이 변경 가능한 상태인지 확인합니다.
assignee를 바꿉니다.
activity를 기록합니다.
updated_at을 변경합니다.
```

동시에 membership이 비활성화되거나 ticket이 닫힐 수 있습니다. Transaction 안에서 `SELECT`를 두 번 했다는 이유만으로 안전하다고 볼 수 없습니다.

다음 질문에 답합니다.

- 판단과 변경을 조건부 `UPDATE` 하나로 묶을 수 있습니까?
- 어느 row를 어떤 순서로 잠급니까?
- 모든 변경 경로가 같은 순서를 사용합니까?
- unique constraint가 경쟁 결과를 결정할 수 있습니까?
- serialization failure나 deadlock을 어디서 재시도합니까?
- 외부 알림은 commit 뒤 어떻게 전달합니까?

현재 `ticketing-database`의 축소 schema에는 membership 활성 상태와 activity table이 없습니다. 따라서 해당 경쟁을 자동 검사했다고 주장하면 안 됩니다. 실제 시스템에서 column과 table을 추가할 때 별도의 두-session 테스트를 작성해야 합니다.

## 5. 대표 workload와 index를 연결합니다

최소 세 query를 사용합니다.

```text
organization별 미완료 ticket page
assignee별 미완료 queue
project별 미완료 ticket 집계
```

### Organization ticket page

정렬은 다음 tuple 전체를 사용합니다.

```text
priority DESC, created_at DESC, id DESC
```

다음 page는 마지막 row의 tuple보다 작은 값을 찾습니다.

```sql
WHERE org_id = $1
  AND status <> 'DONE'
  AND (priority, created_at, id) < ($2, $3, $4)
ORDER BY priority DESC, created_at DESC, id DESC
LIMIT $5;
```

마지막 `id`가 없으면 같은 priority와 시각을 가진 ticket이 page 사이에서 반복되거나 누락될 수 있습니다.

### Assignee queue

```text
org_id equality
assignee_id equality
status <> 'DONE'
priority DESC, created_at, id
```

### Project backlog

```text
org_id와 project_id로 범위를 좁힙니다.
미완료 ticket을 셉니다.
가장 오래된 created_at을 찾습니다.
```

각 query에 대해 다음을 기록합니다.

- 호출 빈도와 tenant 크기 분포
- 실제 반환 row 수
- filter, join과 ordering
- 현재 plan과 실제 block read
- 허용 latency
- index 추가 뒤 증가한 write와 저장 공간

## 6. 기존 값을 새 column으로 옮깁니다

`severity`를 유지하면서 새 `priority`를 추가한다고 가정합니다.

```text
1. nullable priority column을 추가합니다.
2. 새 application이 priority를 기록합니다.
3. 기존 severity를 priority로 backfill합니다.
4. 허용 범위 constraint를 NOT VALID로 추가합니다.
5. 기존 row를 validate합니다.
6. priority에 NOT NULL을 적용합니다.
7. compatibility 기간이 끝난 뒤 severity 제거를 별도 배포로 진행합니다.
```

Backfill은 다음 조건을 가져야 합니다.

- 안정적인 key 순서로 진행합니다.
- 작은 transaction으로 나눌 수 있습니다.
- 같은 작업을 다시 실행해도 이미 채운 row를 망가뜨리지 않습니다.
- 중단 위치를 기록하고 다시 시작할 수 있습니다.
- 새 write와 충돌할 때 어느 값을 우선할지 정합니다.
- WAL, replica lag와 disk 여유를 관찰합니다.

Exercise의 데이터는 작지만 실제 운영 table에서는 한 번의 큰 `UPDATE`를 사용하지 않을 수 있습니다.

## 7. 검증 결과를 남깁니다

통합 검토에는 다음 증거가 필요합니다.

```text
schema에서 막는 잘못된 insert
query별 예상 row 집합과 정렬
동시 변경 시 허용·금지 결과
index 적용 전후 plan
migration을 두 번 실행한 결과
잘못된 priority와 NULL insert 거부
남아 있는 비보장 범위
```

코드가 실행된다는 사실만으로 끝내지 않습니다. 어느 test가 어떤 잘못된 schema, query나 migration을 검출하는지 설명할 수 있어야 합니다.

## 연결 exercise

[`ticketing-database`](../../exercises/ticketing-database/)는 다음 파일로 구성됩니다.

```text
schema.sql
seed.sql
migration.sql
queries.sql
indexes.sql
tests/verify.sql
scripts/test.sh
```

필수 학습 순서에서는 schema 부분을 관계 모델과 제약 문서 뒤에 먼저 읽고, 통계·실행 계획·migration 문서까지 마친 뒤 나머지 파일을 완성합니다.

## 완료 기준

다음 질문에 SQL과 실행 결과로 답할 수 있어야 합니다.

1. 어떤 업무 규칙을 DB constraint가 직접 검사합니까?
2. 어떤 규칙은 transaction이나 application code가 추가로 검사해야 합니까?
3. 각 query가 반환하는 한 row는 무엇을 뜻합니까?
4. Organization ID가 key, query와 index에 빠짐없이 포함되어 있습니까?
5. Stable keyset pagination에 `id`가 필요한 이유는 무엇입니까?
6. 각 index가 어느 filter와 ordering을 지원합니까?
7. Migration 중 이전 application과 새 application이 함께 실행될 수 있습니까?
8. 실패 시 이전 단계로 되돌릴지 수정 migration으로 진행할지 정했습니까?
