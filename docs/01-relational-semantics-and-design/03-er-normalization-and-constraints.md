# ER 모델, 정규화와 제약

## 학습 목표

이 문서를 마치면 다음을 할 수 있어야 합니다.

- 업무 문장에서 entity, relationship, cardinality와 optionality를 찾습니다.
- candidate key와 surrogate key의 역할을 구분합니다.
- 함수 종속성으로 갱신 이상을 설명합니다.
- 1NF, 2NF, 3NF와 BCNF를 분해 판단에 사용합니다.
- 애플리케이션 검증과 데이터베이스 제약이 각각 막는 실패를 구분합니다.
- 비정규화를 선택할 때 갱신, 불일치 탐지와 복구 방법을 함께 정합니다.

먼저 [`SQL 의미와 질의 형태`](02-sql-semantics-and-query-shape.md)를 읽고 primary key와 foreign key의 기본 문법을 알고 있어야 합니다.

## Schema는 column 목록이 아니라 허용 상태를 정하는 장치입니다

다음 요구를 예로 들겠습니다.

```text
사용자는 여러 project에 참여할 수 있습니다.
Project에는 여러 사용자가 참여할 수 있습니다.
참여자는 project마다 역할을 가집니다.
Task 담당자는 해당 project의 참여자여야 합니다.
DONE task에는 완료 시각이 반드시 있어야 합니다.
```

이를 table 네 개로 나누는 것만으로는 충분하지 않습니다.

```text
User
Project
Membership(project_id, user_id, role)
Task(project_id, assignee_id, status, completed_at)
```

`Membership`은 다대다 관계를 풀면서 관계 자체의 `role`도 저장합니다. `Task(project_id, assignee_id)`가 `Membership(project_id, user_id)`를 참조하면 “담당자는 같은 project의 참여자”라는 규칙을 데이터베이스가 직접 확인할 수 있습니다.

## Entity와 relationship을 구분합니다

명사가 나온다고 모두 table로 만들 필요는 없습니다. 다음을 확인합니다.

- 독립적인 식별자가 필요합니까?
- 다른 사실이 이 대상을 참조합니까?
- 자체 상태 변화와 수명이 있습니까?
- 두 대상의 연결 자체에 저장할 값이 있습니까?

주문과 상품의 연결에는 수량, 주문 당시 가격, 할인처럼 연결 자체의 값이 있습니다. 이런 경우 `OrderLine`이 필요합니다.

```text
OrderLine(order_id, product_id, quantity, unit_price)
```

상품 ID를 쉼표로 이어 붙인 문자열에 저장하면 다음을 데이터베이스가 검사하기 어렵습니다.

- 상품이 실제로 존재하는지
- 특정 상품이 포함된 주문을 찾을 수 있는지
- 상품 하나의 수량만 바꿀 수 있는지
- 주문 당시 가격을 별도로 저장할 수 있는지
- 동시에 수정할 때 어떤 행에서 충돌해야 하는지

## Cardinality와 optionality

관계의 수량은 foreign key 위치와 `UNIQUE` 여부를 정합니다.

| 관계 | 대표 구현 |
| --- | --- |
| 1:1 | 한쪽 foreign key에 `UNIQUE` |
| 1:N | N 쪽에 foreign key |
| N:M | 연결 table과 복합 key |
| optional | foreign key의 `NULL` 허용 여부 |

“사용자에게 기본 배송지 하나가 있다”와 “여러 배송지 중 하나를 기본으로 표시한다”는 다른 모델입니다. 후자는 Address table과 사용자마다 기본 주소가 하나만 있도록 하는 추가 제약이나 transaction이 필요합니다.

현재 화면만 보고 cardinality를 정하지 않습니다. 다음 변경도 묻습니다.

```text
한 사용자가 같은 project에서 역할을 여러 개 가질 수 있습니까?
Project owner는 바뀔 수 있습니까?
사용자를 삭제해도 주문 기록은 남아야 합니까?
```

## Candidate key와 surrogate key

Candidate key는 업무 의미로 tuple을 식별하는 최소 attribute 집합입니다. Surrogate key는 참조와 저장을 단순화하기 위해 만든 인공 식별자입니다.

사용자 table에 `id`가 있더라도 email이 업무상 유일하다면 두 규칙이 모두 필요할 수 있습니다.

```sql
id bigint PRIMARY KEY
CREATE UNIQUE INDEX users_email_ci_uq ON users (lower(email));
```

Surrogate key를 추가했다고 natural key의 유일성이 사라지지 않습니다. Email 중복을 막지 않으면 애플리케이션이 같은 사용자를 여러 행으로 만들 수 있습니다.

반대로 자주 바뀌는 값을 primary key로 사용하면 모든 참조에 변경이 전파됩니다. Key를 정할 때 다음을 함께 봅니다.

- 값이 바뀌는지
- index와 foreign key에 저장될 크기
- 외부에 노출하는지
- 값을 누가 생성하는지
- 유일성 범위가 전체인지 tenant 내부인지

## 함수 종속성

`X → Y`는 X 값이 같으면 Y 값도 같아야 한다는 뜻입니다.

```text
user_id → email, grade
sku → product_name
(order_id, product_id) → quantity, unit_price
```

다음 table을 보겠습니다.

```text
OrderLine(order_id, product_id, product_name, quantity)
```

Key가 `(order_id, product_id)`인데 `product_id → product_name`이면 상품명이 주문 line마다 반복됩니다.

- **수정 이상**: 상품명을 바꿀 때 여러 행을 모두 바꿔야 합니다.
- **삽입 이상**: 주문이 없으면 상품 정보를 저장하기 어렵습니다.
- **삭제 이상**: 마지막 주문 line을 지우면 상품 정보도 사라질 수 있습니다.

“중복이 많다”보다 함수 종속성을 적는 편이 분해 이유를 정확히 설명합니다.

## 정규형은 암기 항목이 아니라 오류를 찾는 기준입니다

### 1NF

한 cell에 독립적으로 검색하거나 참조해야 할 반복 값을 숨기지 않았는지 봅니다. JSON이나 문자열이 항상 잘못이라는 뜻은 아닙니다. 내부 값을 별도로 제약하고 조인해야 한다면 relation으로 분리하는 편이 맞습니다.

### 2NF

복합 candidate key의 일부에만 의존하는 non-key attribute가 있는지 봅니다.

```text
Enrollment(student_id, course_id, student_name, grade)
student_id → student_name
(student_id, course_id) → grade
```

`student_name`은 전체 key가 아니라 `student_id`에만 의존하므로 Student로 분리합니다.

### 3NF

Non-key attribute가 다른 non-key attribute를 결정하는지 봅니다.

```text
Employee(employee_id, department_id, department_name)
department_id → department_name
```

부서명을 Department로 분리하지 않으면 같은 이름을 여러 행에서 갱신해야 합니다.

### BCNF

모든 비자명한 함수 종속성의 determinant가 superkey인지 확인합니다. 일부 관계에서는 dependency preservation 때문에 3NF를 선택할 수 있습니다. 이름 자체보다 어떤 갱신 오류를 막는 분해인지 설명할 수 있어야 합니다.

## 데이터베이스 제약은 우회 경로까지 검사합니다

애플리케이션 검증은 빠르고 이해하기 쉬운 오류를 제공하는 데 필요합니다. 하지만 다음 경로는 애플리케이션 검사만으로 막을 수 없습니다.

- 두 요청이 동시에 같은 email의 존재 여부를 확인합니다.
- 관리 SQL이나 batch가 애플리케이션 코드를 거치지 않습니다.
- 여러 버전이나 여러 언어로 작성된 서비스가 같은 table을 씁니다.
- 검사와 INSERT 사이에 다른 transaction이 값을 바꿉니다.

저장되면 안 되는 상태는 가능한 한 데이터베이스 제약으로 막습니다.

| 제약 | 확인하는 내용 |
| --- | --- |
| `PRIMARY KEY` | 행을 무엇으로 식별하는지 |
| `UNIQUE` | 어떤 업무 값이 중복될 수 없는지 |
| `FOREIGN KEY` | 참조 대상이 존재하는지 |
| `NOT NULL` | 값 누락을 허용하는지 |
| `CHECK` | 값 범위와 여러 column 조합이 유효한지 |
| `EXCLUDE` | 시간 구간처럼 서로 겹치면 안 되는 값이 있는지 |

Unique violation을 정상적인 경쟁 결과로 사용할 수도 있습니다. “없음을 확인한 뒤 INSERT”하지 않고, 두 INSERT가 `UNIQUE`에서 경쟁하게 한 뒤 하나의 오류를 업무상 중복으로 바꿉니다.

## `NULL`의 뜻을 하나로 정합니다

`NULL`을 허용한다면 이 column에서 무엇을 뜻하는지 정해야 합니다.

```text
아직 결정되지 않음
알 수 없음
해당 행에는 적용되지 않음
외부 시스템에서 아직 전달되지 않음
```

여러 의미를 한 `NULL`에 섞으면 질의와 제약이 모호해집니다. 필요하면 상태 column이나 별도 relation으로 분리합니다.

`completed_at IS NULL`이 미완료를 뜻한다면 status와 함께 검사할 수 있습니다.

```sql
CHECK (
    (status = 'DONE' AND completed_at IS NOT NULL)
    OR
    (status <> 'DONE' AND completed_at IS NULL)
)
```

## 삭제 동작도 명시합니다

Foreign key의 `ON DELETE`는 편의 옵션이 아닙니다.

- `RESTRICT`: 참조가 남아 있으면 삭제를 거부합니다.
- `CASCADE`: parent가 사라질 때 child도 함께 삭제합니다.
- `SET NULL`: child는 남기고 관계만 끊습니다.

감사 기록이나 결제 내역에 `CASCADE`를 사용하면 필요한 과거가 사라질 수 있습니다. 반대로 project에 완전히 종속된 임시 행을 `RESTRICT`로 두면 정리가 어려워집니다. Parent 삭제 뒤 어떤 사실이 남아야 하는지 먼저 적습니다.

## 비정규화는 다시 계산할 방법과 함께 선택합니다

읽기 비용을 줄이려고 합계나 표시 값을 중복 저장할 수 있습니다. 이때 다음을 함께 정합니다.

```text
원본 값:
파생 값을 갱신하는 시점:
같은 transaction에서 바꾸는지:
불일치를 찾는 질의:
전체 재계산 방법:
허용할 수 있는 지연:
갱신 실패 시 읽을 값:
```

이 항목이 없으면 빠른 읽기를 얻는 대신 오래 남는 데이터 불일치를 만들 수 있습니다.

## 연결 exercise

[`ticketing-database`](../../exercises/ticketing-database/)의 `schema.sql`과 `seed.sql`을 먼저 봅니다.

다음을 확인합니다.

- 사용자 email의 대소문자 무시 유일성
- organization 범위를 포함한 membership과 project key
- 다른 organization의 project나 assignee를 참조하는 ticket 거부
- `status`와 `closed_at`의 허용 조합

Migration, view와 index는 실행 계획과 안전한 변경 문서를 읽은 뒤 이어서 확인합니다.

## 완료 기준

다음을 직접 작성하고 설명할 수 있어야 합니다.

1. Entity, relationship, cardinality와 optionality
2. 각 table의 candidate key와 선택한 primary key
3. 중요한 함수 종속성 `X → Y`
4. 허용하지 않을 상태를 막는 `UNIQUE`, `FOREIGN KEY`, `CHECK`, `NOT NULL`
5. 삭제 뒤 남아야 할 데이터와 `ON DELETE` 선택
6. 비정규화 값의 불일치 탐지와 재계산 방법
