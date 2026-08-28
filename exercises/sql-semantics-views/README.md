# SQL Semantics Views

PostgreSQL view 네 개로 `NULL`, anti-join, 외부 조인 집계, 결과 행의 단위와 안정적인 순위를 확인하는 프로젝트입니다. 작은 사용자·주문 데이터에서 각 질의가 반환해야 할 행과 순서를 SQL assertion으로 고정합니다.

## 주요 기능

- 주문이 없는 사용자를 찾는 `q01_users_without_orders`
- 차단 목록에 `NULL`이 있어도 올바르게 동작하는 `q02_unblocked_users`
- 주문이 없는 사용자까지 보존하는 `q03_user_totals`
- 동률 해소 기준이 포함된 `q04_ranked_spenders`
- 기대 행 집합과 정렬 순서를 검사하는 PostgreSQL 검증 SQL

## 파일 구성

- `schema.sql`: 검증에 필요한 table과 제약을 정의합니다.
- `seed.sql`: 0원 주문, 주문 없는 사용자, 같은 합계와 `NULL` 차단 항목을 넣습니다.
- `views.sql`: 완료된 view 네 개를 정의합니다.
- `tests/verify.sql`: 각 view의 행과 순서를 assertion으로 검사합니다.
- `compose.yaml`, `scripts/test.sh`: 독립된 PostgreSQL 환경에서 전체 검사를 실행합니다.

## 실행

Docker Engine과 Docker Compose v2가 필요합니다.

```bash
make test
```

명령은 임시 PostgreSQL 16 컨테이너를 시작한 뒤 schema, seed, view, 검증 SQL을 순서대로 적용합니다. 검사가 끝나면 컨테이너와 volume을 제거합니다.

기존 PostgreSQL 데이터베이스에 직접 적용할 때는 다음 순서를 사용합니다.

```bash
psql -v ON_ERROR_STOP=1 -f schema.sql
psql -v ON_ERROR_STOP=1 -f seed.sql
psql -v ON_ERROR_STOP=1 -f views.sql
```

```sql
SELECT *
FROM q04_ranked_spenders
ORDER BY position;
```

## 설계에서 확인할 점

- “같은 행이 존재하지 않는다”는 조건은 `NOT EXISTS`로 표현합니다. `NOT IN`의 하위 결과에 `NULL`이 있을 때 전체 조건이 `UNKNOWN`이 되는 문제를 피합니다.
- 사용자별 집계는 `users`에서 시작합니다. `LEFT JOIN`, `COUNT(o.id)`, `COALESCE`를 사용해 주문이 없는 사용자도 `0`건, `0`원으로 남깁니다.
- 지출 순위는 `total_cents DESC, id ASC`로 완전히 정렬합니다. 합계가 같아도 `id`가 마지막 순서를 정하므로 실행 계획이 달라져도 상위 3명의 순서가 유지됩니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | 관계와 제약 정의 | `schema.sql` |
| 1-1 | 의미 차이를 드러내는 고정 데이터 | `seed.sql` |
| 2 | NULL에 안전한 주문 없음 anti-join | `views.sql` · `q01_users_without_orders` |
| 3 | NULL에 안전한 차단 사용자 anti-join | `views.sql` · `q02_unblocked_users` |
| 4 | 사용자별 외부 조인 집계 | `views.sql` · `q03_user_totals` |
| 5 | 동률까지 고정한 지출 순위 | `views.sql` · `q04_ranked_spenders` |
| 6 | SQL 결과 검증 | `tests/verify.sql` |

## 범위와 제한

이 프로젝트는 PostgreSQL의 조회 의미만 다룹니다. 인증, 애플리케이션 API, 데이터 변경 절차, materialized view와 운영 데이터 migration은 포함하지 않습니다.
