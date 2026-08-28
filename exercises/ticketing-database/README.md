# Ticketing Database

여러 조직이 함께 사용하는 ticket 서비스를 PostgreSQL schema, migration, view와 index로 구성한 프로젝트입니다. Project, reporter, assignee가 같은 조직에 속하는지 복합 foreign key로 검사하고, 조직별 미완료 ticket 목록과 담당자 queue의 정렬 순서를 명시합니다.

## 주요 기능

- 조직 범위를 포함한 membership과 project 식별
- 다른 조직의 project, reporter, assignee 참조 거부
- ticket `status`와 `closed_at` 조합 검증
- `severity`에서 `priority`로 이동하는 재실행 가능한 migration
- project backlog, 조직별 keyset page, 담당자 queue view
- 세 대표 조회에 맞춘 partial composite index
- 결과 행, 제약 위반, catalog 정의와 실제 실행 계획 검증

## 파일 구성

- `schema.sql`: organization, user, membership, project와 ticket을 정의합니다.
- `seed.sql`: 두 조직과 순서 검증에 필요한 ticket을 넣습니다.
- `migration.sql`: priority 열 추가, backfill, 기존 행 검증과 `NOT NULL` 전환을 수행합니다.
- `queries.sql`: 세 대표 조회를 view로 정의합니다.
- `indexes.sql`: 각 조회의 조건과 정렬에 맞는 index를 정의합니다.
- `tests/verify.sql`: 결과 집합과 거부되어야 할 INSERT를 검사합니다.
- `scripts/test.sh`: migration, view, index의 재실행과 실제 plan을 검사합니다.

## 실행

Docker Engine과 Docker Compose v2가 필요합니다.

```bash
make test
```

검사 스크립트는 migration, view와 index SQL을 각각 두 번 적용합니다. 이후 세 조회가 지정한 index를 사용하고, 정렬용 `Sort` node를 추가하지 않는지 확인합니다.

## 대표 조회

```sql
SELECT id, priority, created_at
FROM q_org_open_tickets
WHERE org_id = 1
  AND (priority, created_at, id)
      < (4, TIMESTAMPTZ '2025-01-02 00:00:00+00', 101)
ORDER BY priority DESC, created_at DESC, id DESC
LIMIT 20;
```

## 설계에서 확인할 점

- 조직 불일치는 `(project_id, org_id)`와 `(org_id, user_id)` 복합 foreign key가 거부합니다. `project_id`나 `user_id`만 검사하면 다른 조직의 행이 연결될 수 있습니다.
- Keyset cursor는 `(priority, created_at, id)` 전체 값입니다. 마지막 `id`가 없으면 같은 priority와 시각을 가진 ticket이 page 사이에서 중복되거나 누락될 수 있습니다.
- 호환 기간에는 `severity`를 제거하지 않습니다. 기존 행의 `priority` 범위를 검증한 뒤 `NOT NULL`로 바꾸므로 이전 버전이 읽는 열과 새 버전이 쓰는 열을 함께 유지할 수 있습니다.
- View에서 WHERE 조건과 결과 행을 먼저 정한 뒤, index의 partial 조건과 key 순서를 실제 조회에 맞춥니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | 조직과 사용자 식별 | `schema.sql` · `organizations`, `users` |
| 2 | 조직 범위를 포함한 membership과 project 식별 | `schema.sql` · `memberships`, `projects` |
| 3 | ticket의 조직 참조와 상태 조합 제한 | `schema.sql` · `tickets` |
| 4 | priority 열 추가와 재실행 가능한 backfill | `migration.sql` · `ADD COLUMN`, `UPDATE` |
| 5 | 기존 행 검증과 필수 값 전환 | `migration.sql` · `tickets_priority_range`, `SET NOT NULL` |
| 6 | 조직 조건을 포함한 조회 view | `queries.sql` |
| 6-1 | project별 미완료 ticket 집계 | `queries.sql` · `q_project_backlog` |
| 6-2 | 조직별 keyset page 조회 행 | `queries.sql` · `q_org_open_tickets` |
| 6-3 | 담당자별 미완료 ticket 조회 행 | `queries.sql` · `q_assignee_queue` |
| 7 | 대표 조회에 맞춘 index | `indexes.sql` |
| 7-1 | 조직별 내림차순 keyset 조회 index | `indexes.sql` · `tickets_org_open_priority_created_idx` |
| 7-2 | project별 backlog 조회 index | `indexes.sql` · `tickets_project_open_created_idx` |
| 7-3 | 담당자별 우선순위 queue index | `indexes.sql` · `tickets_assignee_queue_idx` |
| 8 | 조직 참조, migration, 조회 결과와 제약 통합 검증 | `tests/verify.sql`, `scripts/test.sh` |

## 범위와 제한

현재 schema는 membership의 존재와 조직 일치 여부만 확인합니다. Membership 활성 상태, ticket activity table과 비활성화 절차는 모델링하지 않습니다. 해당 기능을 추가할 때는 membership 변경과 assignee 변경이 같은 행을 어떤 순서로 잠그는지 정하고, deadlock이나 serialization failure가 발생하면 transaction 전체를 다시 실행해야 합니다.
