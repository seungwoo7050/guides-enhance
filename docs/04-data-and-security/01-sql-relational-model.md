# 관계형 모델과 SQL

여러 사용자가 같은 데이터를 읽고 동시에 변경하는 시스템에서는 데이터를 단순한 배열이나 한 덩어리의 JSON으로만 관리하기 어렵습니다. 데이터 사이의 관계, 중복 금지 규칙, 참조 대상의 존재 여부처럼 **항상 지켜져야 하는 조건**을 모든 애플리케이션 코드 경로에서 일관되게 유지해야 하기 때문입니다.

관계형 데이터베이스는 데이터를 테이블로 나누어 저장하고, 기본 키·외래 키·고유 제약 조건·검사 제약 조건 등을 사용해 허용되지 않는 상태의 저장을 데이터베이스 수준에서 거부할 수 있습니다.

이 문서의 SQL 예시는 PostgreSQL 문법을 기준으로 합니다. `uuid`, `timestamptz`, `$1` 형태의 매개변수, `RETURNING`, 행 값 비교 `(a, b) < (...)` 등은 PostgreSQL에서 사용할 수 있는 문법입니다. 다른 DBMS나 드라이버에서는 타입이나 매개변수 표기법이 다를 수 있습니다.

## 목표

- 행·열·테이블과 스키마의 역할을 설명합니다.
- 기본 키, 외래 키, `UNIQUE`, `CHECK`, `NOT NULL`의 차이를 설명합니다.
- 개체와 다대다 관계를 여러 테이블로 표현합니다.
- 애플리케이션 검증과 데이터베이스 제약 조건의 역할을 구분합니다.
- 사용자 입력을 매개변수화된 SQL로 전달합니다.
- 조회·수정·삭제할 행을 `WHERE` 조건으로 정확히 제한합니다.
- `NULL`, 정렬, 조인과 페이지네이션에서 발생하는 기본 문제를 구분합니다.
- 버전 열을 이용한 낙관적 동시성 제어의 원리를 설명합니다.

## 관계형 데이터의 기본 단위

SQL에서 데이터를 이해할 때 먼저 다음 네 가지를 구분합니다.

```text
테이블(table)  → 같은 종류의 데이터를 행들의 집합으로 저장
행(row)        → 하나의 사용자, 메모처럼 한 개체에 대한 값들의 묶음
열(column)     → id, email, title처럼 각 값의 의미와 타입을 정의
스키마(schema) → 어떤 테이블과 열이 존재하고 어떤 제약 조건을 가지는지에 대한 구조
```

예를 들어 `users` 테이블의 한 행은 사용자 한 명을 나타낼 수 있고, `email` 열은 각 사용자 행의 이메일 값을 나타낼 수 있습니다.

관계형 모델에서는 데이터를 한 곳에 모두 중첩해서 저장하기보다 개체와 관계를 나누어 표현합니다. 이렇게 나누면 사용자와 메모처럼 서로 독립적으로 존재하는 개체를 각각 관리하면서, 외래 키를 통해 둘 사이의 관계를 명시할 수 있습니다.

## 테이블과 열

다음은 사용자와 메모를 별도의 테이블로 표현한 예입니다.

```sql
create table users (
  id uuid primary key,
  email text not null unique,
  display_name text not null,
  created_at timestamptz not null
);

create table notes (
  id uuid primary key,
  owner_id uuid not null references users(id),
  title text not null,
  body text not null,
  version integer not null default 0 check (version >= 0),
  created_at timestamptz not null,
  updated_at timestamptz not null
);
```

각 열에는 단순한 저장 형식뿐 아니라 데이터가 만족해야 할 조건도 표현되어 있습니다.

- `id uuid primary key`: 각 행을 식별하는 기본 키입니다.
- `email text not null unique`: 값이 반드시 존재해야 하고 다른 사용자와 중복될 수 없습니다.
- `owner_id ... references users(id)`: 실제 `users.id`를 참조해야 하는 외래 키입니다.
- `version ... check (version >= 0)`: 버전 값은 음수가 될 수 없습니다.

따라서 `owner_id`는 단순히 UUID 형식의 값을 담는 열이 아닙니다. 외래 키 제약 때문에 해당 값과 일치하는 `users.id`가 존재해야 합니다.

타입과 제약 조건은 서로 다른 역할을 합니다.

```text
uuid
→ 값의 표현 형식을 제한

not null
→ 값이 NULL인 상태를 금지

unique
→ 중복되는 값을 금지

references users(id)
→ 참조 대상 행이 존재하지 않는 상태를 금지

check (version >= 0)
→ 열의 값이 지정한 조건을 위반하는 상태를 금지
```

## 키와 식별자

### 기본 키

기본 키(primary key)는 테이블의 각 행을 식별하는 기준입니다.

```sql
id uuid primary key
```

PostgreSQL에서 기본 키에는 중복되지 않는다는 조건과 `NULL`이 될 수 없다는 조건이 함께 적용됩니다. 따라서 같은 `id`를 가진 두 행을 만들 수 없습니다.

한 테이블에는 기본 키를 하나만 지정하지만, 기본 키가 반드시 열 하나로 이루어질 필요는 없습니다. 여러 열을 묶은 복합 기본 키도 사용할 수 있습니다.

### 외래 키

외래 키(foreign key)는 한 테이블의 값이 다른 테이블의 행을 참조하도록 만드는 제약 조건입니다.

```sql
owner_id uuid not null references users(id)
```

이 정의는 `notes.owner_id`가 존재하는 `users.id` 중 하나여야 한다는 의미입니다.

외래 키가 보장하는 것은 **참조 무결성**입니다. 외래 키만으로 "현재 요청을 보낸 사용자가 이 메모를 수정할 권한이 있다"는 애플리케이션 권한까지 보장되는 것은 아닙니다. 권한 조건은 별도로 검사해야 합니다.

### 고유 제약 조건

`UNIQUE`는 지정한 열 또는 열 조합에서 중복을 금지합니다.

```sql
email text not null unique
```

이 예에서는 이메일이 사용자 식별에 사용할 수 있을 정도로 중복되지 않도록 만들지만, 다른 테이블의 참조 키로 반드시 이메일을 사용해야 한다는 뜻은 아닙니다.

## 내부 식별자와 사용자에게 보이는 값

이메일은 고유하게 관리할 수 있지만 사용자가 변경할 수 있는 값입니다. 다른 테이블이 사용자를 장기간 참조해야 한다면 변경 가능성이 낮은 내부 식별자를 사용하는 편이 일반적으로 단순합니다.

```text
users.id
→ 다른 행이 참조하는 안정적인 내부 식별자

users.email
→ 사용자에게 보이고 변경될 수 있지만 중복은 허용하지 않는 값
```

예를 들어 메모가 `owner_email`을 직접 저장한다면 사용자가 이메일을 변경할 때 메모의 참조 값도 함께 바꾸어야 합니다. 대신 `owner_id`를 저장하면 이메일이 바뀌어도 메모와 사용자의 관계는 유지됩니다.

모든 테이블에 UUID를 사용해야 하는 것은 아닙니다. 정수형 자동 증가 키, UUID 등은 각각 특성이 다릅니다. 식별자를 선택할 때는 다음과 같은 조건을 고려합니다.

- ID를 여러 서버나 클라이언트에서 생성해야 하는가
- ID가 외부 API에 노출되는가
- 삽입 순서와 ID 순서의 관계가 필요한가
- 인덱스와 저장 공간의 크기가 중요한가

중요한 것은 특정 타입을 항상 사용하는 것이 아니라 **행을 안정적으로 식별할 수 있는 키를 정하고 일관되게 사용하는 것**입니다.

## 다대다 관계

한 메모를 여러 사용자가 공유할 수 있고, 한 사용자도 여러 메모에 참여할 수 있다고 가정합니다.

```text
한 note  → 여러 user
한 user  → 여러 note
```

이 관계를 다대다(many-to-many) 관계라고 합니다.

다대다 관계는 보통 두 개체를 연결하는 별도의 연결 테이블로 표현합니다.

```sql
create table note_members (
  note_id uuid not null references notes(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('editor', 'viewer')),
  primary key (note_id, user_id)
);
```

`note_members`의 한 행은 다음 의미를 가집니다.

```text
(note_id, user_id, role)
→ 이 사용자가 이 메모에 이 역할로 참여한다
```

`primary key (note_id, user_id)`는 두 열의 **조합**을 기본 키로 사용합니다. 따라서 같은 사용자와 같은 메모의 조합을 두 번 삽입할 수 없습니다.

예를 들어 다음 두 행은 동시에 존재할 수 없습니다.

```text
(note-1, user-7, editor)
(note-1, user-7, viewer)
```

두 행의 `(note_id, user_id)`가 같기 때문입니다.

이 규칙을 애플리케이션 코드에서 다음처럼 구현하는 것만으로는 충분하지 않을 수 있습니다.

```text
1. 같은 멤버십이 있는지 SELECT
2. 없으면 INSERT
```

두 요청이 동시에 실행되면 둘 다 1단계에서 "없음"을 확인한 뒤 둘 다 삽입을 시도할 수 있습니다. 복합 기본 키 또는 `UNIQUE` 제약은 최종적으로 중복 상태가 저장되는 것을 데이터베이스에서 막습니다.

### 관계의 의미를 한 곳에서 관리하기

소유자를 `notes.owner_id`에 저장할지, `note_members.role = 'owner'`처럼 멤버십 테이블에 저장할지는 데이터 모델에서 하나의 기준을 정해야 합니다.

같은 사실을 두 곳에 독립적으로 저장하면 다음처럼 서로 모순되는 상태가 생길 수 있습니다.

```text
notes.owner_id = user-a
note_members에서 owner 역할 = user-b
```

정말 두 표현이 모두 필요하다면 둘이 항상 일치하도록 유지할 방법까지 설계해야 합니다. 그렇지 않다면 하나를 기준 정보(source of truth)로 두는 편이 안전합니다.

## 참조 삭제와 `ON DELETE`

연결 테이블의 외래 키에는 다음과 같이 `ON DELETE CASCADE`가 지정되어 있습니다.

```sql
note_id uuid not null
  references notes(id)
  on delete cascade
```

이 경우 부모 행인 `notes`의 메모가 삭제되면 그 메모를 참조하는 `note_members` 행도 함께 삭제됩니다.

```text
notes 행 삭제
    ↓
그 note_id를 참조하는 note_members 행 자동 삭제
```

이 동작은 연결 행처럼 부모 없이 존재할 의미가 없는 데이터에는 편리합니다. 그러나 모든 관계에 무조건 사용하면 안 됩니다. 감사 기록처럼 부모가 삭제되어도 남아야 하는 데이터라면 `CASCADE`가 적절하지 않을 수 있습니다.

삭제 정책은 "부모가 사라졌을 때 자식 행을 어떻게 처리해야 하는가"라는 데이터 모델의 의미에 따라 정합니다.

## 제약 조건의 역할

데이터 검증은 애플리케이션과 데이터베이스 모두에서 필요할 수 있지만 두 계층의 목적은 다릅니다.

애플리케이션은 사용자가 이해하기 쉬운 오류를 빠르게 반환할 수 있습니다.

```text
제목을 입력해 주세요.
제목은 120자를 넘을 수 없습니다.
```

데이터베이스 제약 조건은 어떤 코드 경로에서 쓰기가 발생하더라도 허용되지 않는 최종 상태가 저장되는 것을 막는 마지막 경계가 됩니다.

```sql
alter table notes
  add constraint notes_title_not_blank
  check (length(trim(title)) between 1 and 120);
```

이 제약은 공백만 있는 제목과 120자를 초과하는 제목을 거부합니다. `title`에는 이미 `NOT NULL`도 있으므로 `NULL` 역시 허용되지 않습니다.

대표적인 제약 조건의 역할은 다음과 같습니다.

| 제약 조건 | 막는 상태 |
|---|---|
| `NOT NULL` | 필수 값이 없는 상태 |
| `UNIQUE` | 고유해야 하는 값 또는 열 조합의 중복 |
| `PRIMARY KEY` | 행 식별자의 중복 또는 `NULL` |
| `FOREIGN KEY` | 존재하지 않는 행을 참조하는 상태 |
| `CHECK` | 지정한 조건식을 위반하는 값 |

한 행의 열 값만으로 표현할 수 있는 핵심 규칙은 `CHECK`, `NOT NULL` 같은 제약 조건으로 표현하기 쉽습니다.

여러 행이나 여러 테이블의 현재 상태를 함께 확인해야 하는 규칙은 단순한 `CHECK` 하나로 표현하기 어려울 수 있습니다. 이런 규칙은 트랜잭션, 고유 제약, 적절한 잠금, 데이터베이스 기능과 애플리케이션 로직을 조합해 지켜야 합니다.

### `CHECK`와 `NULL`

SQL 조건식에는 `TRUE`, `FALSE`뿐 아니라 `UNKNOWN`이 존재합니다. PostgreSQL의 `CHECK` 제약은 조건식의 결과가 `FALSE`일 때 위반되고, `TRUE` 또는 `NULL`인 경우에는 통과할 수 있습니다.

따라서 값의 존재 자체가 필수라면 `CHECK`만 믿지 말고 `NOT NULL`도 별도로 지정해야 합니다.

```sql
score integer not null check (score >= 0)
```

이렇게 해야 `NULL`과 음수 값을 모두 거부할 수 있습니다.

## 매개변수화된 SQL

사용자 입력을 SQL 문자열에 직접 이어 붙이면 입력값이 SQL 문법의 일부로 해석될 수 있습니다.

다음과 같은 문자열 조합 방식은 피합니다.

```text
"select ... where email = '" + user_input + "'"
```

대신 SQL 문장과 데이터 값을 분리하여 드라이버의 매개변수 바인딩 기능을 사용합니다.

```sql
insert into notes (
  id,
  owner_id,
  title,
  body,
  created_at,
  updated_at
)
values ($1, $2, $3, $4, now(), now());
```

여기서 `$1`부터 `$4`는 SQL 소스 코드에 문자열로 삽입될 값이 아니라 드라이버가 별도의 데이터 값으로 전달하는 매개변수 자리입니다.

```text
SQL 구조
→ insert into ... values ($1, $2, ...)

데이터
→ note id, owner id, title, body
```

이 분리는 SQL 인젝션을 막는 핵심 방법입니다.

다만 일반적인 값 매개변수는 테이블 이름, 열 이름, `ASC`/`DESC` 같은 SQL 문법 요소를 대신하지 못합니다. 사용자가 정렬 열을 선택하게 해야 한다면 허용할 열 이름을 애플리케이션에서 목록으로 제한한 뒤 안전한 SQL 조각을 선택하는 방식이 필요합니다.

## 조회할 행 제한하기

`WHERE`는 어떤 행을 대상으로 할지 결정합니다.

```sql
select id, title
from notes
where owner_id = $1;
```

이 쿼리는 모든 메모가 아니라 `owner_id = $1`인 행만 반환합니다.

특히 `UPDATE`와 `DELETE`에서는 `WHERE` 조건을 먼저 확인하는 습관이 중요합니다.

```sql
update notes
set title = $1;
```

위 쿼리는 조건이 없으므로 `notes`의 모든 행을 변경합니다.

```sql
delete from notes;
```

위 쿼리 역시 모든 행을 삭제합니다.

따라서 쓰기 쿼리를 검토할 때는 먼저 다음을 확인합니다.

```text
어떤 행을 바꾸려는가?
그 조건이 WHERE에 모두 들어 있는가?
조건이 예상보다 넓어질 가능성은 없는가?
```

## 안정적인 정렬

SQL에서 `ORDER BY`가 없으면 행의 반환 순서는 보장되지 않습니다.

```sql
select id, title, version, updated_at
from notes
where owner_id = $1
order by updated_at desc, id desc
limit $2;
```

`updated_at desc`만 사용하면 같은 시각을 가진 두 행 사이의 순서는 정해지지 않을 수 있습니다.

```text
updated_at                id
------------------------  ----
2026-08-29 01:00:00+09    a
2026-08-29 01:00:00+09    b
```

두 행은 첫 번째 정렬 키가 같으므로 데이터베이스가 어느 행을 먼저 반환해야 하는지 결정할 추가 기준이 없습니다.

그래서 고유한 `id`를 보조 정렬 키로 추가합니다.

```sql
order by updated_at desc, id desc
```

안정적인 페이지네이션에 사용할 정렬은 가능한 한 마지막까지 순서를 결정할 수 있어야 합니다. 즉, 정렬 키 조합이 각 행을 유일하게 구분하도록 만드는 것이 중요합니다.

## 조건부 `UPDATE`와 낙관적 동시성 제어

두 사용자가 같은 메모를 거의 동시에 읽었다고 가정합니다.

```text
현재 DB version = 5

사용자 A가 version 5를 읽음
사용자 B가 version 5를 읽음

A가 수정 저장
B도 예전 화면을 기준으로 수정 저장
```

아무 조건 없이 마지막 `UPDATE`가 실행되면 B의 요청이 A의 변경을 덮어쓸 수 있습니다. 이를 잃어버린 갱신(lost update) 문제라고 합니다.

버전 열을 조건에 포함하면 이전 상태를 기준으로 한 수정 요청을 감지할 수 있습니다.

```sql
update notes
set title = $1,
    version = version + 1,
    updated_at = now()
where id = $2
  and version = $3
returning id, title, version, updated_at;
```

클라이언트가 읽었던 버전이 `$3 = 5`라고 가정합니다.

첫 번째 요청이 성공하면 다음처럼 됩니다.

```text
version 5 → version 6
```

그 뒤 두 번째 요청이 여전히 `version = 5`를 조건으로 실행되면 일치하는 행이 없으므로 수정되지 않습니다.

이 방식을 **낙관적 동시성 제어(optimistic concurrency control)**라고 합니다. 충돌이 자주 발생하지 않는다고 가정하고 먼저 잠그지 않은 채 작업하되, 실제 쓰기 시점에 자신이 읽었던 버전이 아직 유효한지 확인합니다.

소유자만 수정할 수 있는 API라면 대상과 권한 범위를 함께 제한할 수도 있습니다.

```sql
update notes
set title = $1,
    version = version + 1,
    updated_at = now()
where id = $2
  and owner_id = $3
  and version = $4
returning id, title, version, updated_at;
```

반환된 행이 없다면 가능한 원인은 여러 가지입니다.

```text
해당 id의 메모가 없음
owner_id 조건이 맞지 않음
version이 이미 변경됨
```

API가 이 원인들을 사용자에게 각각 구분해서 보여 줄지, 권한 정보 노출을 피하기 위해 같은 오류로 처리할지는 API 정책에 따라 결정합니다.

## 삭제와 보관

물리 삭제는 실제 행을 제거합니다.

```sql
delete from notes
where id = $1
  and owner_id = $2
returning id;
```

반면 서비스에 따라 삭제 대신 상태를 남겨야 할 수 있습니다.

대표적인 방식은 다음과 같습니다.

```text
물리 삭제
→ 행 자체를 DELETE

보관 상태
→ status = 'archived' 같은 상태값 사용

논리 삭제
→ deleted_at에 삭제 시각을 기록하고 행은 유지
```

예를 들어 논리 삭제를 사용한다면 다음과 같이 값을 기록할 수 있습니다.

```sql
update notes
set deleted_at = now()
where id = $1;
```

그러나 `deleted_at` 열을 추가했다고 해서 삭제된 행이 자동으로 조회에서 제외되는 것은 아닙니다.

일반 조회에서 제외하려면 명시적으로 조건을 사용해야 합니다.

```sql
select id, title
from notes
where deleted_at is null;
```

어떤 삭제 방식을 선택할지는 복구 가능성, 감사 기록, 참조 관계, 저장 비용, 개인정보 삭제 요구사항 등을 함께 고려해야 합니다.

## `NULL`

`NULL`은 빈 문자열 `''`, 숫자 `0`, `false`와 다른 값입니다.

`NULL`은 일반적으로 값이 존재하지 않거나 알려져 있지 않음을 표현합니다. 하지만 실제 의미는 해당 열의 설계에서 정해야 합니다.

예를 들어 `archived_at`이 다음 의미라고 정의할 수 있습니다.

```text
NULL
→ 아직 보관되지 않음

timestamp 값
→ 해당 시각에 보관됨
```

`NULL`은 일반 값처럼 `=`로 비교하지 않습니다.

```sql
-- 잘못된 방식
where archived_at = null
```

SQL에서 `x = NULL`은 `TRUE`나 `FALSE`가 아니라 알 수 없음(`UNKNOWN`)이 됩니다. `WHERE`는 조건이 `TRUE`인 행만 선택하므로 원하는 결과가 나오지 않습니다.

`NULL` 여부는 `IS NULL` 또는 `IS NOT NULL`로 검사합니다.

```sql
where archived_at is null
```

```sql
where archived_at is not null
```

필수 값에는 가능한 한 `NOT NULL`을 지정합니다.

`NULL`을 허용한다면 다음 중 어떤 의미인지 데이터 모델에서 설명할 수 있어야 합니다.

- 아직 값이 정해지지 않음
- 값을 알 수 없음
- 이 행에는 해당 개념이 적용되지 않음

서로 다른 의미를 모두 하나의 `NULL`로 표현하면 이후 쿼리와 비즈니스 규칙이 모호해질 수 있습니다.

## `JOIN`과 결과 행 수

`JOIN`은 관련된 여러 테이블의 행을 연결합니다.

예를 들어 특정 사용자가 참여한 메모를 조회할 수 있습니다.

```sql
select n.id, n.title, m.role
from notes as n
join note_members as m
  on m.note_id = n.id
where m.user_id = $1
order by n.updated_at desc, n.id desc;
```

현재 스키마에서는 `note_members`의 기본 키가 `(note_id, user_id)`이므로 같은 사용자가 같은 메모에 두 번 등록될 수 없습니다. 따라서 이 쿼리에서 특정 `user_id` 하나를 조건으로 조회하면 멤버십 때문에 같은 메모가 여러 번 반복되지는 않습니다.

조인 결과가 늘어나는 현상을 보려면 메모와 그 메모의 **모든 구성원**을 함께 조회하는 경우를 생각해야 합니다.

```sql
select n.id, n.title, m.user_id, m.role
from notes as n
join note_members as m
  on m.note_id = n.id
where n.id = $1;
```

메모 하나에 구성원이 세 명이면 결과는 세 행이 됩니다.

```text
note_id  user_id  role
-------  -------  ------
note-1   user-a   editor
note-1   user-b   viewer
note-1   user-c   viewer
```

`notes`의 같은 행이 세 번 저장된 것이 아닙니다. 하나의 메모 행이 서로 다른 세 개의 `note_members` 행과 각각 결합되어 조인 결과 세 행이 만들어진 것입니다.

따라서 결과 행이 예상보다 많을 때 이유를 확인하지 않고 다음처럼 `DISTINCT`부터 붙이지 않습니다.

```sql
select distinct ...
```

먼저 다음을 확인합니다.

```text
결과의 한 행이 무엇을 의미해야 하는가?
1:1, 1:N, N:M 중 어떤 관계를 JOIN하고 있는가?
한 기준 행과 몇 개의 상대 행이 매칭되는가?
```

원하는 결과가 "메모 한 행"인지 "메모와 멤버십의 각 조합 한 행"인지에 따라 쿼리 구조가 달라집니다.

## 페이지네이션

결과가 많으면 한 번에 모두 읽지 않고 일정 개수씩 나눠 조회합니다.

### `LIMIT`과 `OFFSET`

작은 목록에서는 다음 방식으로 시작할 수 있습니다.

```sql
select id, title, updated_at
from notes
where owner_id = $1
order by updated_at desc, id desc
limit $2
offset $3;
```

예를 들어 페이지 크기가 20이라면 다음과 같이 사용할 수 있습니다.

```text
첫 페이지   → LIMIT 20 OFFSET 0
둘째 페이지 → LIMIT 20 OFFSET 20
셋째 페이지 → LIMIT 20 OFFSET 40
```

이 방식은 이해하기 쉽지만 페이지를 읽는 사이에 데이터가 추가되거나 삭제되면 행의 위치가 바뀔 수 있습니다.

예를 들어 첫 페이지를 읽은 뒤 목록 맨 앞에 새 행이 추가되면 두 번째 페이지의 `OFFSET 20`이 이전 페이지에서 이미 읽었던 행을 다시 포함할 수 있습니다.

큰 `OFFSET`은 데이터베이스가 앞쪽 행을 건너뛰는 비용도 증가시킬 수 있습니다.

### 커서 기반 페이지네이션

커서 방식 또는 키셋(keyset) 페이지네이션은 "몇 번째 행부터"가 아니라 "마지막으로 읽은 정렬 키 다음부터"를 조회합니다.

정렬이 다음과 같다고 가정합니다.

```sql
order by updated_at desc, id desc
```

첫 페이지의 마지막 행이 다음 값을 가졌다면

```text
updated_at = 2026-08-29 01:30:00+09
id         = 8f...
```

다음 페이지는 그 정렬 키보다 뒤에 있는 행을 조회합니다.

```sql
select id, title, updated_at
from notes
where owner_id = $1
  and (updated_at, id) < ($2, $3)
order by updated_at desc, id desc
limit $4;
```

두 열 모두 내림차순이므로 이전 페이지 마지막 행보다 작은 `(updated_at, id)` 조합을 선택합니다.

커서에 사용되는 열과 `ORDER BY`의 열, 순서, 방향은 서로 일치해야 합니다.

```text
ORDER BY updated_at DESC, id DESC
             ↓             ↓
cursor   updated_at        id
```

`id` 같은 고유한 보조 키를 포함해야 동일한 `updated_at`을 가진 행 사이에서도 정확한 다음 위치를 표현할 수 있습니다.

커서 페이지네이션은 새 행 삽입으로 인한 `OFFSET` 위치 이동 문제를 줄여 주지만, 모든 동시 변경을 자동으로 스냅샷처럼 고정하는 것은 아닙니다. 예를 들어 페이지를 읽는 도중 기존 행의 `updated_at`이 바뀌면 그 행의 정렬 위치 자체가 이동할 수 있습니다. 완전히 동일한 시점의 데이터 집합을 여러 페이지에 걸쳐 읽어야 한다면 별도의 스냅샷 또는 트랜잭션 전략이 필요할 수 있습니다.

## 애플리케이션 검사와 데이터베이스 제약

두 종류의 검증을 경쟁 관계로 생각하지 않습니다.

```text
애플리케이션 검사
→ 사용자 친화적인 오류
→ 요청 형식과 권한 검사
→ 외부 시스템 상태가 필요한 규칙 처리

데이터베이스 제약
→ 저장 가능한 상태 자체를 제한
→ 다른 코드 경로에서도 같은 규칙 적용
→ 동시 요청 사이의 중복 같은 경쟁 상태 방어
```

예를 들어 이메일 중복을 애플리케이션에서 미리 확인하면 사용자에게 빠르게 "이미 사용 중인 이메일"이라고 안내할 수 있습니다.

하지만 다음 순서만으로 유일성을 보장할 수는 없습니다.

```text
1. 이메일이 존재하는지 SELECT
2. 없으면 INSERT
```

동시에 들어온 두 요청이 모두 1단계에서 "없음"을 볼 수 있기 때문입니다.

최종 중복 저장을 막는 기준은 다음과 같은 데이터베이스 고유 제약이 됩니다.

```sql
email text not null unique
```

애플리케이션은 제약 위반 오류를 받아 적절한 API 오류로 변환할 수 있습니다.

## 흔한 실수

- 서로 독립적인 개체와 관계를 구분하지 않고 모든 데이터를 배열이나 JSON 열 하나에 넣습니다.
- 기본 키와 외래 키가 각각 무엇을 보장하는지 구분하지 않습니다.
- 애플리케이션에서 먼저 조회했으니 중복 삽입이 불가능하다고 생각합니다.
- 애플리케이션 검사만 믿고 `UNIQUE`, 외래 키, `CHECK`, `NOT NULL` 같은 핵심 제약을 생략합니다.
- 외래 키가 애플리케이션의 접근 권한까지 보장한다고 생각합니다.
- 모든 외래 키에 의미를 확인하지 않고 `ON DELETE CASCADE`를 사용합니다.
- 사용자 입력을 SQL 문자열에 직접 삽입합니다.
- 값 매개변수로 테이블명이나 정렬 방향까지 안전하게 바인딩할 수 있다고 생각합니다.
- `ORDER BY` 없이 반환 순서가 고정된다고 생각합니다.
- 동일한 정렬 값이 존재하는데 고유한 보조 정렬 키를 두지 않습니다.
- `NULL`을 빈 문자열이나 일반 값처럼 `= NULL`로 비교합니다.
- `CHECK` 하나만 있으면 `NULL`도 항상 거부된다고 생각합니다.
- 조인으로 행이 늘어난 이유를 확인하지 않고 `DISTINCT`로 감춥니다.
- `UPDATE`와 `DELETE`의 대상 행을 제한하는 `WHERE` 조건을 확인하지 않습니다.
- 버전 조건 없이 오래된 화면의 수정 내용을 그대로 저장해 최신 변경을 덮어씁니다.
- `deleted_at` 열만 추가하면 삭제된 행이 자동으로 모든 조회에서 제외된다고 생각합니다.
- 커서 페이지네이션을 사용하면 모든 동시 변경의 영향이 사라진다고 생각합니다.

## 완료 기준

- 테이블, 행, 열과 스키마가 각각 무엇을 의미하는지 설명할 수 있습니다.
- 기본 키와 외래 키의 역할을 구분할 수 있습니다.
- `UNIQUE`, `CHECK`, `NOT NULL`이 각각 어떤 잘못된 상태를 막는지 설명할 수 있습니다.
- 개체와 다대다 관계를 별도의 테이블과 연결 테이블로 표현할 수 있습니다.
- 내부 식별자와 변경 가능한 사용자 표시 값을 구분할 수 있습니다.
- 외래 키의 `ON DELETE` 동작을 관계의 의미에 따라 선택할 수 있습니다.
- 사용자 입력을 SQL 문자열에 직접 연결하지 않고 매개변수 바인딩을 사용할 수 있습니다.
- `WHERE` 조건으로 조회·수정·삭제 대상을 정확히 제한할 수 있습니다.
- `ORDER BY`가 필요한 이유와 고유한 보조 정렬 키의 역할을 설명할 수 있습니다.
- 버전 열을 사용하는 조건부 `UPDATE`가 오래된 쓰기를 어떻게 감지하는지 설명할 수 있습니다.
- `NULL`과 SQL의 3값 논리 때문에 `IS NULL`이 필요한 이유를 설명할 수 있습니다.
- 조인 결과의 행 수가 관계의 개수에 따라 증가하는 이유를 설명할 수 있습니다.
- `OFFSET`과 커서 기반 페이지네이션의 차이와 한계를 설명할 수 있습니다.
- 애플리케이션 검사와 데이터베이스 제약 조건이 각각 막는 문제를 설명할 수 있습니다.

## 연결 exercise

[`seat-reservation`](../../exercises/seat-reservation/README.md)은 같은 좌석을 동시에 예약하는 두 요청을 데이터베이스 고유 제약으로 처리합니다.
