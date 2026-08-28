# 관계형 모델과 SQL

여러 사용자가 같은 데이터를 읽고 동시에 바꾸기 시작하면 배열이나 한 덩어리의 JSON만으로는 관계와 허용 가능한 상태를 지키기 어렵습니다. 관계형 데이터베이스는 값을 저장할 뿐 아니라 기본 키, 외래 키와 제약 조건으로 잘못된 최종 상태를 거부합니다.

## 목표

- 행·열·테이블과 키의 역할을 설명합니다.
- 개체와 다대다 관계를 테이블로 나눕니다.
- 기본 키, 외래 키, 고유 제약 조건과 검사 제약 조건을 사용합니다.
- 조회·수정·삭제할 행을 조건으로 정확히 제한합니다.
- `NULL`, 정렬, 조인과 페이지네이션의 기본 문제를 구분합니다.

## 테이블과 열

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

`owner_id`는 임의의 문자열이 아니라 실제 사용자 행을 가리킵니다. `version`은 음수가 될 수 없습니다. 열의 타입과 제약 조건은 저장할 값의 의미를 함께 표현합니다.

## 내부 식별자와 사용자에게 보이는 값

이메일은 고유할 수 있지만 바뀔 수 있습니다. 다른 테이블이 사용자를 참조할 때는 안정적인 내부 ID를 사용하고, 이메일에는 별도의 고유 제약 조건을 둡니다.

```text
users.id     → 다른 행이 참조할 내부 식별자
users.email  → 사용자에게 보이며 변경될 수 있는 고유 값
```

모든 테이블에 UUID를 써야 하는 것은 아닙니다. 생성 위치, 외부 노출, 정렬, 저장 크기를 고려해 선택합니다.

## 다대다 관계

한 메모를 여러 사용자가 공유하고, 한 사용자도 여러 메모에 참여할 수 있습니다.

```sql
create table note_members (
  note_id uuid not null references notes(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('editor', 'viewer')),
  primary key (note_id, user_id)
);
```

복합 기본 키는 같은 사용자가 같은 메모에 두 번 등록되는 상태를 막습니다. 애플리케이션에서 먼저 조회한 뒤 삽입하는 방식만으로는 동시에 들어온 요청을 완전히 막지 못합니다.

소유자를 `notes.owner_id`에 저장할지, 멤버십 테이블의 `owner` 역할로 저장할지 하나를 기준으로 정합니다. 같은 의미를 두 곳에 중복 저장하면 값이 어긋날 수 있습니다.

## 제약 조건의 역할

애플리케이션은 사용자가 이해하기 쉬운 오류를 빠르게 반환합니다. 데이터베이스는 다른 코드 경로나 경쟁 요청에서도 잘못된 값이 저장되지 않게 합니다.

```sql
alter table notes
  add constraint notes_title_not_blank
  check (length(trim(title)) between 1 and 120);
```

한 행의 값만으로 확인할 수 있는 핵심 조건은 데이터베이스에도 표현할 수 있습니다. 여러 테이블이나 외부 시스템의 상태가 필요한 규칙은 트랜잭션 안의 애플리케이션 코드가 처리합니다.

## 매개변수화된 SQL

```sql
insert into notes (id, owner_id, title, body, created_at, updated_at)
values ($1, $2, $3, $4, now(), now());
```

사용자 입력을 SQL 문자열에 이어 붙이지 않습니다. 드라이버의 매개변수 바인딩을 사용합니다.

## 안정적인 정렬

```sql
select id, title, version, updated_at
from notes
where owner_id = $1
order by updated_at desc, id desc
limit $2;
```

`ORDER BY`가 없으면 반환 순서는 보장되지 않습니다. `updated_at` 값이 같을 수 있으므로 `id` 같은 보조 정렬 키를 추가합니다.

## 조건부 UPDATE

```sql
update notes
set title = $1,
    version = version + 1,
    updated_at = now()
where id = $2
  and version = $3
returning id, title, version, updated_at;
```

`version = $3` 조건은 오래된 화면에서 보낸 요청이 최신 변경을 덮어쓰는 것을 막습니다. 반환된 행이 없다면 리소스 없음, 권한 부족, 버전 충돌 중 무엇인지 API에서 정한 방식으로 처리합니다.

쓰기 쿼리는 `WHERE` 조건부터 확인합니다. 조건이 빠진 `UPDATE`와 `DELETE`는 모든 행을 바꿀 수 있습니다.

## 삭제와 보관

```sql
delete from notes
where id = $1 and owner_id = $2
returning id;
```

물리 삭제, 보관 상태, `deleted_at`을 사용하는 논리 삭제 중 하나를 선택할 때는 복구, 감사와 개인정보 삭제 요구사항을 함께 봅니다. `deleted_at` 열만 추가한다고 삭제된 행이 자동으로 조회에서 제외되는 것은 아닙니다.

## `NULL`

`NULL`은 빈 문자열이 아닙니다. 값이 없거나 적용되지 않음을 뜻합니다.

```sql
-- 잘못된 비교
where archived_at = null

-- NULL 여부 확인
where archived_at is null
```

필수 값에는 `NOT NULL`을 지정합니다. `NULL`을 허용한다면 그 값이 “아직 없음”, “알 수 없음”, “적용되지 않음” 중 무엇을 뜻하는지 설명할 수 있어야 합니다.

## JOIN과 결과 행 수

```sql
select n.id, n.title, m.role
from notes as n
join note_members as m on m.note_id = n.id
where m.user_id = $1
order by n.updated_at desc, n.id desc;
```

메모 하나에 구성원이 세 명이면 조인 결과에 같은 메모가 세 번 나타날 수 있습니다. 이유를 확인하지 않고 `DISTINCT`로 감추지 않습니다. 원하는 결과 단위와 관계의 개수를 먼저 확인합니다.

## 페이지네이션

작은 목록은 `LIMIT`과 `OFFSET`으로 시작할 수 있습니다.

```sql
order by updated_at desc, id desc
limit $1 offset $2;
```

조회 사이에 행이 추가되면 중복과 누락이 생길 수 있습니다. 커서 방식은 마지막으로 읽은 정렬 키 다음부터 조회합니다.

```sql
where (updated_at, id) < ($1, $2)
order by updated_at desc, id desc
limit $3;
```

## 흔한 실수

- 모든 관계를 배열이나 JSON 열 하나에 넣습니다.
- 애플리케이션 검사만 믿고 고유·외래 키 제약을 생략합니다.
- 사용자 입력을 SQL 문자열에 직접 삽입합니다.
- `ORDER BY` 없이 반환 순서가 고정된다고 생각합니다.
- `NULL`을 빈 문자열처럼 비교합니다.
- 조인으로 행이 늘어난 이유를 확인하지 않고 `DISTINCT`를 사용합니다.
- `UPDATE`와 `DELETE`의 대상 조건을 확인하지 않습니다.

## 완료 기준

- 개체와 다대다 관계를 테이블로 표현합니다.
- 기본 키, 외래 키, `UNIQUE`, `CHECK`, `NOT NULL`의 용도를 설명합니다.
- 매개변수화된 쿼리와 안정적인 정렬을 사용합니다.
- `NULL`, 조인 결과 수와 페이지네이션 문제를 구분합니다.
- 애플리케이션 검사와 데이터베이스 제약이 각각 막는 문제를 설명합니다.

## 연결 exercise

[`seat-reservation`](../../exercises/seat-reservation/README.md)은 같은 좌석을 동시에 예약하는 두 요청을 데이터베이스 고유 제약으로 처리합니다.
