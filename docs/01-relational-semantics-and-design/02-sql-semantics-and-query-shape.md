# SQL 의미와 질의 형태

## 학습 목표

이 문서를 마치면 다음을 할 수 있어야 합니다.

- SQL의 논리 처리 순서로 alias, filter와 grouping의 유효 범위를 설명합니다.
- `NULL`과 three-valued logic 때문에 생기는 잘못된 결과를 찾습니다.
- 외부 조인에서 `ON`과 `WHERE`의 조건 위치가 결과를 바꾸는 이유를 설명합니다.
- 집계 전후에 결과 한 행이 무엇을 뜻하는지 정합니다.
- pagination에 필요한 완전한 정렬 key를 구성합니다.
- index를 설계하기 전에 대표 질의의 조건과 반환 형태를 기록합니다.

먼저 [`관계 모델과 관계 대수`](01-relational-model-and-algebra.md)를 읽습니다.

## SQL은 선언적이지만 결과 의미가 자동으로 정해지지는 않습니다

SQL은 원하는 결과를 적고 DBMS가 실행 방법을 선택하게 합니다. 문장이 오류 없이 실행됐다고 해서 업무상 맞는 결과라는 뜻은 아닙니다.

SQL은 다음 특성 때문에 순수 집합 연산보다 주의할 부분이 많습니다.

- 중복을 기본으로 보존합니다.
- `NULL` 비교는 `TRUE`, `FALSE`, `UNKNOWN` 중 하나가 됩니다.
- 외부 조인은 일치하지 않은 행을 보존하기 위해 반대쪽 열에 `NULL`을 만듭니다.
- `ORDER BY`가 없으면 순서를 보장하지 않습니다.
- 집계는 결과 한 행의 의미를 바꿉니다.
- `LIMIT`은 전체 결과 중 일부만 보여 줍니다.

느린 SQL처럼 보이는 문제도 실제로는 결과 행의 의미가 잘못 정해진 경우가 있습니다. 먼저 맞는 결과를 고정해야 합니다.

## 논리 처리 순서

SQL 문장은 `SELECT`부터 보이지만 의미를 판단할 때는 다음 순서로 생각하는 편이 정확합니다.

```text
FROM / JOIN / ON
WHERE
GROUP BY
HAVING
SELECT
DISTINCT
ORDER BY
LIMIT / OFFSET
```

이 순서는 physical 실행 순서가 아닙니다. 옵티마이저는 결과를 유지하면서 filter를 아래로 내리거나 join 순서를 바꿀 수 있습니다.

`SELECT`에서 만든 alias를 같은 level의 `WHERE`에서 바로 사용할 수 없는 이유도 이 순서로 설명할 수 있습니다. `WHERE`가 논리적으로 먼저 처리되기 때문입니다. 반면 `ORDER BY`는 `SELECT` 뒤이므로 alias를 허용하는 DBMS가 많습니다.

## `NULL`과 three-valued logic

`NULL`은 0이나 빈 문자열이 아닙니다. 값이 알려지지 않았거나 적용되지 않는 상태를 나타냅니다.

```sql
WHERE deleted_at = NULL   -- 올바른 NULL 검사가 아닙니다.
WHERE deleted_at IS NULL
```

일반 비교에 `NULL`이 들어가면 `UNKNOWN`이 될 수 있습니다. `WHERE`는 `TRUE`인 행만 남기므로 `FALSE`와 `UNKNOWN`은 모두 제거됩니다.

### `NOT IN`에 `NULL`이 섞이는 경우

```sql
SELECT id
FROM users
WHERE id NOT IN (
    SELECT user_id
    FROM blocked_users
);
```

하위 결과가 `(2, NULL)`이면 `id=1`이 목록에 없다고 확정할 수 없습니다. `1 <> NULL`이 `UNKNOWN`이기 때문입니다. 따라서 차단되지 않은 사용자까지 결과에서 사라질 수 있습니다.

질문이 “같은 행이 존재하지 않는가”라면 `NOT EXISTS`가 더 직접적입니다.

```sql
SELECT u.id
FROM users AS u
WHERE NOT EXISTS (
    SELECT 1
    FROM blocked_users AS b
    WHERE b.user_id = u.id
);
```

문법 취향이 아니라 업무 질문에 맞는 연산을 사용해야 합니다.

## 외부 조인의 `ON`과 `WHERE`

다음 질의는 사용자를 모두 남기는 것처럼 보이지만 양수 주문이 없는 사용자를 제거합니다.

```sql
SELECT u.id, o.id
FROM users AS u
LEFT JOIN orders AS o
  ON o.user_id = u.id
WHERE o.total_cents > 0;
```

주문이 없는 사용자에게는 `o.total_cents=NULL`이 만들어집니다. `NULL > 0`은 `UNKNOWN`이므로 `WHERE`에서 제거됩니다.

사용자는 남기되 결합할 주문만 양수로 제한하려면 조건을 `ON`에 둡니다.

```sql
SELECT u.id, o.id
FROM users AS u
LEFT JOIN orders AS o
  ON o.user_id = u.id
 AND o.total_cents > 0;
```

조건을 배치할 때 다음을 구분합니다.

```text
이 조건은 오른쪽에서 결합할 행을 제한하는가?
이 조건은 조인이 끝난 전체 결과에서 행을 제거하는가?
```

첫 번째는 `ON`, 두 번째는 `WHERE`에 가깝습니다.

## 집계는 결과 한 행의 의미를 바꿉니다

집계 전에는 한 행이 주문 하나를 뜻할 수 있습니다. `GROUP BY user_id` 뒤에는 한 행이 사용자 한 명의 주문 묶음을 뜻합니다.

```sql
SELECT user_id, count(*), sum(total_cents)
FROM orders
GROUP BY user_id;
```

`SELECT`에 있는 비집계 열은 group key로 결정되어야 합니다. 그렇지 않으면 그룹 안의 어느 행 값을 반환할지 정할 수 없습니다.

외부 조인과 집계를 함께 쓸 때는 `COUNT(*)`와 `COUNT(o.id)`를 구분합니다.

```sql
SELECT
    u.id,
    count(*) AS joined_rows,
    count(o.id) AS actual_orders
FROM users AS u
LEFT JOIN orders AS o ON o.user_id = u.id
GROUP BY u.id;
```

주문이 없는 사용자도 외부 조인 결과에는 `NULL`로 채운 행 하나가 생깁니다. 따라서 `COUNT(*)`는 1일 수 있지만 `COUNT(o.id)`는 0입니다.

집계 질의마다 다음을 한 문장으로 적습니다.

```text
결과 한 행은 무엇을 뜻하는가?
```

## `DISTINCT`로 잘못된 join을 숨기지 않습니다

Join 뒤 행이 예상보다 많으면 먼저 다음을 확인합니다.

- join key가 한쪽에서 실제로 유일합니까?
- 다대다 관계를 의도했습니까?
- 연결 table의 조건이 빠졌습니까?
- 여러 버전 중 현재 행만 골라야 합니까?

`DISTINCT`가 업무상 필요한 경우도 있습니다. 다만 “중복이 보기 싫어서”가 아니라 “사용자별 한 행이 결과 단위이기 때문”처럼 이유를 설명할 수 있어야 합니다.

## 안정적인 정렬과 pagination

다음 정렬은 같은 `created_at`을 가진 행 사이의 순서를 정하지 않습니다.

```sql
ORDER BY created_at DESC
LIMIT 20;
```

실행 계획이나 동시에 들어온 행에 따라 동률 순서가 달라질 수 있습니다. 유일한 동률 해소 key를 추가합니다.

```sql
ORDER BY created_at DESC, id DESC
```

변경이 잦은 목록에서 깊은 `OFFSET`은 앞쪽 행의 추가나 삭제 때문에 중복과 누락을 만들 수 있습니다.

```sql
OFFSET 100 LIMIT 20
```

마지막으로 본 전체 정렬 key를 사용하면 같은 기준으로 다음 page를 찾을 수 있습니다.

```sql
WHERE (created_at, id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, id DESC
LIMIT 20
```

정렬 방향과 tuple 비교 방향을 일치시켜야 합니다.

## View가 숨기는 것과 드러내는 것

일반 view는 보통 데이터를 복사하지 않고 질의 정의에 이름을 붙입니다. 반복되는 결과 의미와 권한 범위를 명확히 하는 데 유용하지만 내부 join과 집계 비용을 숨길 수 있습니다.

Materialized view는 결과를 저장하므로 다음 질문이 추가됩니다.

```text
언제 refresh하는가
얼마나 오래된 결과를 허용하는가
refresh 실패 시 이전 결과를 계속 제공하는가
refresh 중 읽기를 허용하는가
```

## 대표 질의를 기록합니다

Index나 실행 계획을 보기 전에 다음을 적습니다.

```text
결과 한 행의 의미:
시작 relation:
join key와 중복 가능성:
filter:
group key:
반환 column:
정렬과 동률 해소 key:
예상 결과 수:
데이터 변경 빈도:
```

예:

```text
결과 한 행의 의미: 사용자 한 명
시작 relation: users
join: orders.user_id → users.id, 사용자마다 주문 여러 개
filter: 주문 시각 범위, status='PAID'
group: users.id
반환: users.id, sum(total_cents)
정렬: 합계 내림차순, users.id 오름차순
limit: 100
```

이 기록은 뒤의 index 설계와 실행 계획 판정에 그대로 사용합니다.

## 연결 exercise

[`sql-semantics-views`](../../exercises/sql-semantics-views/)에서 다음을 실제 PostgreSQL 결과로 확인합니다.

- 하위 결과에 `NULL`이 있는 anti-join
- 주문 없는 사용자를 남기는 외부 조인 집계
- `COUNT(o.id)`와 `COALESCE`
- 동률까지 고정한 순위

## 완료 기준

다음 잘못된 질의를 설명하고 수정할 수 있어야 합니다.

1. nullable 하위 질의를 사용한 `NOT IN`
2. 오른쪽 table 조건을 `WHERE`에 둔 `LEFT JOIN`
3. 주문 없는 사용자를 1건으로 세는 `COUNT(*)`
4. 동률 해소 key가 없는 pagination
5. 잘못된 join multiplicity를 `DISTINCT`로 숨긴 질의
6. 결과 한 행의 의미를 설명하지 못하는 집계 질의
