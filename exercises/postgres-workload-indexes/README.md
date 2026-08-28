# PostgreSQL Workload Indexes

두 PostgreSQL 조회에 composite, covering, partial index를 적용하고 실제 catalog, `EXPLAIN`과 반환 순서를 검사하는 프로젝트입니다. Index가 존재하는지만 보지 않고, 조회가 지정한 index를 사용하며 별도의 `Sort` 없이 정확한 행을 반환하는지 확인합니다.

## 대상 조회

1. 한 tenant의 최신 event 20개를 `created_at DESC, id DESC` 순서로 조회합니다.
2. 실행 가능한 `PENDING` job을 `scheduled_at, id` 순서로 조회합니다.

## 주요 기능

- equality 조건 뒤에 전체 pagination cursor 배치
- 검색·정렬에 쓰지 않는 반환 열을 `INCLUDE`에 저장
- `PENDING` 행만 유지하는 partial index
- planner가 선택도를 판단할 수 있는 고정 150,000행 데이터
- catalog 정의, plan node, `Sort` 부재와 정확한 결과 순서 검증

## 실행

Docker Engine과 Docker Compose v2가 필요합니다.

```bash
make test
```

데이터 생성 뒤 `ANALYZE`까지 실행하므로 빈 데이터 검사보다 시간이 더 걸릴 수 있습니다. 검사가 끝나면 컨테이너와 volume을 제거합니다.

## 파일 구성

- `schema.sql`: event와 job table을 정의합니다.
- `seed.sql`: planner가 통계를 만들 수 있는 고정 분포의 데이터를 생성합니다.
- `indexes.sql`: 두 조회에 사용할 index를 정의합니다.
- `scripts/test.sh`: catalog, 실행 계획과 반환 ID를 검사합니다.

## 설계에서 확인할 점

- Event index는 equality 조건인 `tenant_id`를 먼저 두고 `(created_at DESC, id DESC)`를 이어서 둡니다. 같은 시각의 event도 `id`가 마지막 순서를 정합니다.
- `kind`, `payload`는 검색이나 정렬에 사용하지 않으므로 key가 아니라 `INCLUDE`에 넣습니다.
- Job index에는 `status = 'PENDING'`인 행만 저장합니다. 조회의 WHERE 조건이 이 predicate를 만족할 때만 planner가 partial index를 사용할 수 있습니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | 두 대표 조회가 사용할 table | `schema.sql` |
| 1-1 | planner가 분포를 판단할 수 있는 고정 데이터 | `seed.sql` |
| 2 | tenant별 최신 event 조회 index | `indexes.sql` · `events_tenant_created_id_idx` |
| 3 | 대기 중인 job partial index | `indexes.sql` · `jobs_pending_schedule_idx` |
| 4 | index 정의, 실행 계획과 결과 순서 검증 | `scripts/test.sh` |

## 범위와 제한

이 프로젝트는 PostgreSQL 16과 고정 데이터에서 두 읽기 조회만 검사합니다. 운영 환경의 쓰기 증가분, vacuum 상태, cache 상태, parameter별 plan 차이, 동시 부하, index bloat와 장기 통계 변화는 측정하지 않습니다.
