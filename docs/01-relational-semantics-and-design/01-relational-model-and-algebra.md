# 관계 모델과 관계 대수

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 합니다.

- 현재 보이는 행 순서와 disk 위치가 relation의 의미가 아닌 이유
- attribute, tuple, relation과 key의 차이
- 선택, 사영, 조인과 집합 연산으로 질의를 분해하는 방법
- SQL의 중복 허용 방식이 순수 관계 모델과 달라지는 지점
- 실행 계획을 보기 전에 질의 결과를 먼저 정해야 하는 이유

## 논리적 의미에서 시작합니다

데이터베이스를 “행을 저장한 파일”로만 보면 질문이 곧바로 저장 위치와 탐색 방법으로 내려갑니다. 그러나 heap file을 사용하다가 index를 추가해도, page 크기가 달라져도, 같은 SQL은 같은 논리 결과를 내야 합니다.

관계 모델은 저장 방법보다 먼저 다음을 정합니다.

```text
어떤 사실을 저장하는가
각 사실을 어떤 attribute로 표현하는가
무엇이 tuple 하나를 식별하는가
어떤 연산이 결과 의미를 보존하는가
```

예를 들어 다음 두 relation을 생각해 보겠습니다.

```text
User(id, email, grade)
Order(id, user_id, total_cents)
```

`User.id`가 사용자를 식별하고 `Order.user_id`가 사용자를 참조한다는 규칙은 파일 안의 byte 위치와 무관합니다. Index는 이 규칙을 더 적은 I/O로 만족시키기 위한 자료구조이지, 저장된 사실의 의미를 바꾸지 않습니다.

## 기본 용어

- **attribute**: relation이 표현하는 속성입니다. SQL의 column과 가깝습니다.
- **tuple**: 하나의 사실을 이루는 attribute 값 묶음입니다. SQL의 row와 가깝습니다.
- **heading**: attribute 이름과 허용 값의 종류를 모은 것입니다.
- **relation**: 같은 heading을 가진 tuple의 집합입니다.
- **candidate key**: tuple 하나를 유일하게 식별하는 최소 attribute 집합입니다.

Relation에는 본래 순서가 없습니다. 다음 결과에서 `id=1`이 지금 첫 번째로 보인다고 해서 다음 실행에서도 첫 번째라는 보장은 없습니다.

```text
id | email
1  | a@example.test
2  | b@example.test
```

순서가 결과의 일부라면 `ORDER BY`로 명시해야 합니다.

## 관계 대수의 기본 연산

관계 대수의 중요한 성질은 연산 결과가 다시 relation이라는 점입니다. 따라서 작은 연산을 이어 붙여 복잡한 질의를 표현할 수 있습니다.

| 연산 | 확인하는 내용 | SQL에서 가까운 표현 |
| --- | --- | --- |
| 선택 `σ` | 어떤 tuple을 남길지 | `WHERE` |
| 사영 `π` | 어떤 attribute를 반환할지 | `SELECT column` |
| 이름 변경 `ρ` | 이름 충돌을 어떻게 피할지 | alias |
| 합집합 | 양쪽 결과를 합칠지 | `UNION` |
| 차집합 | 왼쪽에만 있는 tuple을 찾을지 | `EXCEPT` |
| 곱 | 가능한 모든 tuple 조합을 만들지 | `CROSS JOIN` |
| 조인 | 조건을 만족하는 조합만 남길지 | `JOIN ... ON` |

“양수 금액의 주문이 있는 사용자 email”은 다음처럼 나눌 수 있습니다.

```text
paid_orders = σ total_cents > 0 (Order)
matched = User ⋈ User.id = paid_orders.user_id paid_orders
answer = π email (matched)
```

이 표현은 physical 실행 순서를 강제하지 않습니다. DBMS는 결과를 유지하는 범위에서 filter를 먼저 적용하거나, index를 사용하거나, join 순서를 바꿀 수 있습니다.

## 조인 결과 수를 먼저 판단합니다

조인은 두 table을 화면에서 옆으로 붙이는 문법이 아닙니다. 후보 행 조합을 만들고 조건을 만족하는 조합을 남기는 연산입니다.

```text
|A × B| = |A| × |B|
|A ⋈ B| = key 유일성, 값 분포와 조건에 따라 달라짐
```

Join key가 양쪽에서 유일하지 않으면 결과가 곱으로 늘어납니다.

```text
left에 key=7인 행 2개
right에 key=7인 행 3개
→ inner join 결과 6개
```

외래 키와 `UNIQUE` 제약은 잘못된 참조를 막을 뿐 아니라 결과 수를 판단하는 근거도 제공합니다.

다음 데이터를 보겠습니다.

```text
User
id | email
1  | a@example.test
2  | b@example.test

Order
id | user_id | total_cents
10 | 1       | 5000
11 | 1       | 0
12 | 3       | 9000
```

양수 주문이 있는 사용자를 내부 조인으로 찾으면 다음이 일어납니다.

- `Order.id=11`은 금액 조건에서 제외됩니다.
- `Order.id=12`는 일치하는 사용자가 없으므로 내부 조인에서 제외됩니다.
- 사용자 1은 조건을 만족하는 주문이 하나이므로 결과에 한 번 나옵니다.

질의를 작성하기 전에 어느 행이 사라지고 어느 행이 반복될 수 있는지 말할 수 있어야 합니다.

## 집합과 bag의 차이

순수 관계 모델은 보통 중복 없는 집합으로 설명합니다. SQL은 기본적으로 같은 값을 여러 번 보존하는 bag에 가깝습니다.

```sql
SELECT grade FROM users;
SELECT DISTINCT grade FROM users;
```

첫 번째 질의는 사용자 수만큼 grade가 반복될 수 있습니다. 두 번째는 서로 다른 grade만 남깁니다. `DISTINCT`는 표시 옵션이 아니라 결과 의미를 바꾸며, 실행 시 hash나 sort가 필요할 수 있습니다.

`UNION`과 `UNION ALL`도 다릅니다.

- `UNION`: 중복을 제거합니다.
- `UNION ALL`: 각 입력에 있던 중복 수를 유지합니다.

잘못된 join 때문에 행이 늘어난 상황을 `DISTINCT`로 감추면 안 됩니다. 중복 제거가 업무 요구인지, join 조건이 빠진 것인지 먼저 구분해야 합니다.

## 질의 결과를 네 항목으로 적습니다

실행 계획이나 index를 보기 전에 다음을 적어 두면 의미 오류를 줄일 수 있습니다.

```text
입력 relation:
반환 attribute:
남길 tuple 조건:
중복과 순서:
```

예:

```text
입력 relation: users, orders
반환 attribute: users.id, users.email
조건: 양수 주문이 하나 이상 존재
중복: 사용자별 한 행
순서: email 오름차순, 동률이면 id 오름차순
```

이 기록이 있어야 다음을 판단할 수 있습니다.

- 내부 조인과 외부 조인 중 어느 쪽이 맞는지
- `EXISTS`와 join 중 어느 표현이 결과 단위를 더 직접적으로 나타내는지
- 중복 제거가 필요한지
- 정렬에 동률 해소 key가 필요한지
- 실행 계획이 달라져도 결과가 같은지

## 논리 결과와 physical 실행을 연결합니다

두 개념은 분리해서 생각하되 서로 연결해야 합니다.

```text
논리 결과: 어떤 tuple을 반환해야 하는가
physical plan: 그 tuple을 어떤 page, index와 join 연산으로 찾는가
```

옵티마이저는 의미가 같은 여러 실행 방법 중 비용이 낮다고 추정한 계획을 고릅니다. 동치 변환이 가능한 이유는 관계 의미에서 나오고, 어떤 계획이 더 싼지는 통계와 저장 방식에서 나옵니다.

## 연결 exercise

다음 문서를 이어서 읽은 뒤 [`sql-semantics-views`](../../exercises/sql-semantics-views/)를 실행합니다.

- [`SQL 의미와 질의 형태`](02-sql-semantics-and-query-shape.md)

Exercise에서는 `NOT EXISTS`, 외부 조인 집계와 안정적인 순위를 실제 PostgreSQL 결과로 확인합니다.

## 완료 기준

다음 질문에 코드 없이 답할 수 있어야 합니다.

1. `SELECT DISTINCT`가 결과 의미와 실행 비용을 모두 바꾸는 이유는 무엇입니까?
2. 조인 결과 수가 양쪽 행 수만으로 결정되지 않는 이유는 무엇입니까?
3. `ORDER BY`가 없는 현재 출력 순서를 API 동작으로 사용하면 안 되는 이유는 무엇입니까?
4. 논리 결과와 실행 계획은 어떻게 다르며 어디에서 연결됩니까?
5. 하나의 질의를 선택, 사영과 조인의 조합으로 분해할 수 있습니까?
