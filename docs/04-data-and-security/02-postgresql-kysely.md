# PostgreSQL과 Kysely

Kysely는 TypeScript에서 SQL을 조립할 때 테이블 이름, 열 이름, 연산에 사용하는 타입과 조회 결과 타입을 정적으로 확인하는 데 도움을 주는 **타입 안전 SQL 쿼리 빌더**입니다.

하지만 Kysely의 타입은 PostgreSQL 스키마를 자동으로 검사하거나 데이터베이스의 런타임 동작을 대신하지 않습니다. 실제 테이블, 제약 조건, 격리 수준, 잠금, 트랜잭션, 인덱스와 저장 가능한 값은 PostgreSQL이 결정합니다.

따라서 다음 네 계층을 서로 같은 것으로 취급하지 않습니다.

```text
PostgreSQL 실제 스키마와 데이터
↔ Kysely TypeScript 테이블 타입
↔ 애플리케이션 내부 값
↔ HTTP 요청·응답 스키마
```

이 문서의 예시는 PostgreSQL, `pg`(node-postgres), Kysely를 함께 사용하는 구성을 기준으로 합니다.

## 목표

- 하나의 연결 풀을 애플리케이션 인스턴스 수명에 맞춰 생성하고 종료합니다.
- 풀 크기와 PostgreSQL 최대 연결 수의 관계를 설명합니다.
- 시작 시점에 환경 변수의 형식을 검사합니다.
- Kysely 테이블 타입과 실제 마이그레이션 스키마를 일치시킵니다.
- `Generated`, `ColumnType`, `Selectable`, `Insertable`의 역할을 구분합니다.
- 필요한 열만 조회하고 데이터베이스 행을 애플리케이션 값으로 변환합니다.
- `INSERT`, 조건부 `UPDATE`, 트랜잭션과 원시 SQL을 안전하게 작성합니다.
- PostgreSQL 오류 코드를 도메인 오류와 시스템 오류로 구분합니다.
- 실제 PostgreSQL에서 제약 조건, 경쟁 요청, 타입 변환과 롤백을 검사합니다.

## 연결 풀

PostgreSQL에 쿼리를 실행하려면 데이터베이스 연결이 필요합니다. 매 요청마다 새 TCP 연결을 만들고 인증하는 대신 여러 연결을 재사용하는 **연결 풀(connection pool)**을 사용합니다.

```ts
import { Kysely, PostgresDialect } from "kysely";
import pg from "pg";

const pool = new pg.Pool({
  connectionString: config.databaseUrl,
  max: config.databasePoolSize,
  connectionTimeoutMillis: 5_000
});

export const db = new Kysely<Database>({
  dialect: new PostgresDialect({ pool })
});
```

일반적인 서버 애플리케이션에서는 요청마다 새 `Pool`이나 새 `Kysely` 인스턴스를 만들지 않습니다.

```text
프로세스 시작
    ↓
Pool 생성
    ↓
Kysely 생성
    ↓
여러 HTTP 요청에서 재사용
    ↓
프로세스 종료
    ↓
db.destroy()
```

종료 시에는 다음처럼 Kysely가 관리하는 리소스를 닫습니다.

```ts
await db.destroy();
```

`PostgresDialect`에 전달한 풀은 Kysely의 종료 과정에서 정리됩니다. 종료 처리를 하지 않으면 테스트 프로세스가 끝나지 않거나 배포 중 연결이 불필요하게 남을 수 있습니다.

### 풀 크기

`max: 10`은 애플리케이션 전체에서 10개의 연결만 사용한다는 뜻이 아닙니다. **애플리케이션 인스턴스 하나의 풀**이 최대 10개의 연결을 가질 수 있다는 뜻입니다.

예를 들어 애플리케이션 인스턴스가 8개라면 이론적으로 다음만큼의 연결이 필요할 수 있습니다.

```text
인스턴스 8개 × 풀 최대 10개
= 최대 80개
```

PostgreSQL의 `max_connections`를 모두 애플리케이션 풀이 사용하도록 잡으면 관리용 연결, 마이그레이션, 백그라운드 작업 등에 사용할 여유가 사라질 수 있습니다.

따라서 풀 크기를 정할 때는 적어도 다음을 함께 봅니다.

- 동시에 실행되는 애플리케이션 인스턴스 수
- 각 인스턴스의 풀 `max`
- PostgreSQL의 최대 연결 수
- 관리자·마이그레이션·배치 작업을 위한 여유 연결
- 실제 쿼리 지연 시간과 동시 요청 수

풀을 크게 만든다고 항상 처리량이 증가하는 것은 아닙니다. PostgreSQL이 동시에 처리해야 하는 작업과 메모리 사용량도 증가하므로 실제 부하를 측정해 조정합니다.

## 환경 변수 검사

데이터베이스 설정은 프로세스가 시작될 때 검사합니다.

```ts
import { z } from "zod";

const EnvSchema = z.object({
  DATABASE_URL: z.string().url(),
  DATABASE_POOL_SIZE: z.coerce
    .number()
    .int()
    .min(1)
    .max(20)
    .default(5)
});

const env = EnvSchema.parse(process.env);
```

이 검사는 잘못된 URL 형식이나 허용 범위를 벗어난 풀 크기를 첫 쿼리까지 미루지 않고 시작 시점에 발견하는 데 도움을 줍니다.

다만 문자열 검증이 성공했다고 실제 PostgreSQL 서버에 접속할 수 있다는 뜻은 아닙니다.

```text
환경 변수 검증
→ 값의 형식과 범위를 확인

실제 연결 검사
→ DNS, 네트워크, 인증, PostgreSQL 가용성을 확인
```

배포 환경에서 데이터베이스 연결 가능 여부를 시작 시 확인해야 한다면 별도의 연결 또는 준비 상태(readiness) 검사 정책을 둡니다.

데이터베이스 URL에는 비밀번호가 포함될 수 있으므로 다음과 같은 값을 로그에 그대로 출력하지 않습니다.

```text
postgresql://user:password@db.example.com/app
```

설정 오류를 기록할 때도 비밀번호와 토큰 같은 비밀 값은 제거하거나 마스킹합니다.

## 마이그레이션과 스키마

애플리케이션 코드에서 사용하는 Kysely 타입보다 먼저 실제 PostgreSQL 스키마가 존재해야 합니다.

예를 들어 다음 마이그레이션이 있다고 가정합니다.

```sql
create table notes (
  id uuid primary key,
  owner_id uuid not null references users(id),
  title text not null,
  body text not null,
  version integer not null default 0 check (version >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

이 SQL이 실제 저장 규칙을 결정합니다.

TypeScript에서 다음처럼 타입을 선언했다고 해서 PostgreSQL 열이 자동으로 생기거나 제약 조건이 추가되는 것은 아닙니다.

```ts
interface NoteTable {
  id: string;
  owner_id: string;
  title: string;
  body: string;
  version: number;
  created_at: Date;
  updated_at: Date;
}
```

따라서 스키마를 변경할 때는 다음 항목이 함께 맞는지 확인합니다.

```text
마이그레이션 SQL
↔ 실제 적용된 PostgreSQL 스키마
↔ Kysely 테이블 타입
↔ 데이터베이스 행 변환 코드
↔ HTTP 요청·응답 스키마
```

예를 들어 SQL에서 `title`을 `NULL` 허용으로 바꾸었는데 Kysely 타입이 계속 `string`이라면 TypeScript는 실제로 `NULL`이 들어올 가능성을 표현하지 못합니다.

반대로 Kysely 타입을 `string | null`로 바꿔도 PostgreSQL의 `NOT NULL` 제약은 자동으로 제거되지 않습니다.

## Kysely 테이블 타입

Kysely의 테이블 인터페이스는 **열의 런타임 값을 검증하는 스키마가 아니라 쿼리 타입 계산에 사용하는 TypeScript 선언**입니다.

```ts
interface NoteTable {
  id: string;
  owner_id: string;
  title: string;
  body: string;
  version: number;
  created_at: Date;
  updated_at: Date;
}

interface Database {
  notes: NoteTable;
}
```

이 선언을 잘못 작성해도 TypeScript 컴파일러는 실제 PostgreSQL에 접속해서 수정해 주지 않습니다.

예를 들어 실제 드라이버가 문자열을 반환하는 열을 타입 선언에서 `number`라고 적으면 컴파일은 성공할 수 있지만 런타임 값은 여전히 문자열일 수 있습니다.

## `Generated`와 `ColumnType`

조회할 때의 타입과 삽입·수정할 때 허용할 타입이 서로 다를 수 있습니다.

Kysely는 이를 표현하기 위해 `Generated`와 `ColumnType`을 제공합니다.

```ts
import type {
  ColumnType,
  Generated
} from "kysely";

interface NoteTable {
  id: string;
  owner_id: string;
  title: string;
  body: string;

  version: Generated<number>;

  created_at: ColumnType<
    Date,                 // SELECT 결과에서 기대하는 타입
    Date | string | undefined, // INSERT에 허용할 타입
    never                 // UPDATE에서는 직접 수정하지 않음
  >;

  updated_at: ColumnType<
    Date,
    Date | string | undefined,
    Date | string
  >;
}
```

`Generated<number>`는 데이터베이스 기본값이나 자동 생성 때문에 삽입 시 값을 생략할 수 있지만, 조회 시에는 값이 존재한다고 표현할 때 유용합니다.

`ColumnType<SelectType, InsertType, UpdateType>`은 같은 열에 대해 세 상황의 타입을 따로 지정합니다.

```text
SelectType
→ SELECT 결과에서 보게 되는 타입

InsertType
→ INSERT 시 제공할 수 있는 타입

UpdateType
→ UPDATE 시 제공할 수 있는 타입
```

`never`를 사용하면 애플리케이션 코드에서 해당 열을 일반적인 `UPDATE` 값으로 설정하지 못하게 제한할 수 있습니다.

중요한 점은 이 역시 **컴파일 타임 타입 모델링**이라는 것입니다. Kysely가 PostgreSQL 드라이버의 런타임 값을 자동으로 변환해 주는 것은 아닙니다.

## `Selectable`, `Insertable`, `Updateable`

같은 테이블 타입에서 작업별 타입을 파생할 수 있습니다.

```ts
import type {
  Insertable,
  Selectable,
  Updateable
} from "kysely";

type NoteRow = Selectable<NoteTable>;
type NewNoteRow = Insertable<NoteTable>;
type NoteUpdate = Updateable<NoteTable>;
```

이렇게 하면 다음을 별도의 수동 인터페이스로 중복 작성할 필요를 줄일 수 있습니다.

```text
조회 결과 행
삽입 가능한 값
수정 가능한 값
```

하지만 도메인 객체나 HTTP 응답 타입까지 데이터베이스 타입으로 통일해야 한다는 뜻은 아닙니다. 데이터베이스 표현과 외부 API 표현은 목적이 다르므로 필요하면 별도의 타입과 변환 함수를 둡니다.

## 드라이버 런타임 타입을 확인합니다

Kysely 타입 선언과 실제 JavaScript 런타임 값 사이에는 `pg` 드라이버가 있습니다.

예를 들어 PostgreSQL `bigint`(`int8`) 값은 JavaScript `number`의 안전한 정수 범위를 넘을 수 있기 때문에 `pg`에서는 기본적으로 문자열로 받을 수 있습니다.

```text
PostgreSQL bigint
→ pg parser
→ JavaScript string일 수 있음
```

이를 Kysely 타입에서 무조건 `number`라고 선언하면 타입과 실제 값이 어긋날 수 있습니다.

날짜·시간 열도 드라이버 파서와 프로젝트 설정을 확인해야 합니다.

```text
PostgreSQL timestamptz
→ pg 타입 파서
→ JavaScript Date 등 프로젝트에서 정의한 런타임 표현
```

따라서 다음 두 항목을 따로 확인합니다.

```text
TypeScript에서 무엇이라고 선언했는가?
실제 드라이버가 런타임에 무엇을 반환하는가?
```

필요하다면 `pg`의 타입 파서를 프로젝트 정책에 맞게 설정하거나 변환 계층에서 명시적으로 변환합니다.

## 필요한 열만 조회합니다

조회 결과가 필요한 데이터보다 넓어지지 않도록 필요한 열을 명시합니다.

```ts
const rows = await db
  .selectFrom("notes")
  .select([
    "id",
    "title",
    "version",
    "updated_at"
  ])
  .where("owner_id", "=", actorId)
  .orderBy("updated_at", "desc")
  .orderBy("id", "desc")
  .limit(limit)
  .execute();
```

`selectAll()`은 편리하지만 쿼리가 실제로 필요로 하는 데이터 범위를 코드에서 확인하기 어렵게 만들 수 있습니다.

예를 들어 나중에 테이블에 다음 열이 추가되었다고 가정합니다.

```text
internal_moderation_note
encryption_key_id
deleted_at
```

기존 `selectAll()` 쿼리는 의도하지 않았던 열까지 상위 계층으로 전달하기 시작할 수 있습니다.

필요한 열을 명시하면 다음 장점이 있습니다.

- 쿼리가 사용하는 데이터가 코드에 드러납니다.
- 불필요한 데이터 전송을 줄일 수 있습니다.
- 이후 추가된 내부 열이 자동으로 결과에 섞이는 것을 막습니다.
- 결과 타입이 실제 사용 목적에 더 좁게 유지됩니다.

`selectAll()` 자체가 항상 잘못된 것은 아니지만, API 경계나 민감한 데이터가 있는 테이블에서는 의도적인 선택인지 검토합니다.

## 행을 애플리케이션 값으로 바꿉니다

데이터베이스 행과 애플리케이션 객체를 별도의 형태로 관리할 수 있습니다.

```ts
interface Note {
  id: string;
  ownerId: string;
  title: string;
  body: string;
  version: number;
  createdAt: Date;
  updatedAt: Date;
}

function toNote(row: NoteRow): Note {
  return {
    id: row.id,
    ownerId: row.owner_id,
    title: row.title,
    body: row.body,
    version: row.version,
    createdAt: row.created_at,
    updatedAt: row.updated_at
  };
}
```

이 변환 계층은 단순한 `snake_case` → `camelCase` 변환만 담당하는 것이 아닙니다.

다음과 같은 차이도 한 곳에서 처리할 수 있습니다.

```text
database NULL
→ application의 null 또는 다른 표현

PostgreSQL bigint
→ string 또는 bigint

PostgreSQL enum/text
→ 애플리케이션의 제한된 유니언 타입

timestamp
→ Date 또는 ISO 8601 문자열
```

데이터베이스 행을 그대로 HTTP 응답으로 내보내면 데이터베이스 스키마 변경이 외부 API 변경으로 바로 이어질 수 있습니다.

따라서 다음 경계를 구분합니다.

```text
DB row
   ↓ 변환
domain/application value
   ↓ 응답 직렬화
HTTP response
```

HTTP 응답으로 날짜를 보낼 때는 일반적으로 JSON에서 `Date` 객체 자체가 아니라 ISO 8601 문자열처럼 외부 계약에 맞는 표현으로 직렬화합니다.

## `INSERT`와 반환값

PostgreSQL의 `RETURNING`을 사용하면 삽입 후 별도의 `SELECT` 없이 필요한 열을 받을 수 있습니다.

```ts
const note = await db
  .insertInto("notes")
  .values({
    id,
    owner_id: ownerId,
    title,
    body,
    version: 0,
    created_at: now,
    updated_at: now
  })
  .returning([
    "id",
    "owner_id",
    "title",
    "body",
    "version",
    "created_at",
    "updated_at"
  ])
  .executeTakeFirstOrThrow();
```

이 코드에서 애플리케이션 논리상 반드시 한 행이 삽입되어야 한다면 `executeTakeFirstOrThrow()`를 사용할 수 있습니다.

다만 이 메서드가 던지는 오류를 모두 같은 종류의 사용자 오류로 처리하면 안 됩니다.

예를 들어 실패 원인은 다음처럼 다를 수 있습니다.

```text
UNIQUE 제약 위반
FOREIGN KEY 제약 위반
CHECK 제약 위반
데이터베이스 연결 끊김
쿼리 시간 초과
프로그램 로직 오류
```

오류 분류는 데이터베이스 어댑터 또는 저장소 계층에서 명시적으로 수행합니다.

### 데이터베이스 기본값 사용

`version`, `created_at`, `updated_at`에 PostgreSQL 기본값이 정의되어 있다면 애플리케이션이 값을 직접 넣지 않고 생략하는 설계도 가능합니다.

```sql
version integer not null default 0,
created_at timestamptz not null default now(),
updated_at timestamptz not null default now()
```

그 경우 Kysely 타입에서도 해당 열을 `Generated` 또는 적절한 `ColumnType`으로 모델링해 `INSERT`에서 생략 가능하다는 사실을 표현합니다.

```ts
const note = await db
  .insertInto("notes")
  .values({
    id,
    owner_id: ownerId,
    title,
    body
  })
  .returningAll()
  .executeTakeFirstOrThrow();
```

애플리케이션 시각과 데이터베이스 시각 중 어느 쪽을 기준으로 사용할지 프로젝트에서 일관된 정책을 정합니다.

## 조건부 `UPDATE`

동일한 행을 여러 요청이 수정할 수 있다면 조회와 수정을 별도 단계로 나누는 것만으로는 충돌을 막을 수 없습니다.

```text
요청 A: version 5 조회
요청 B: version 5 조회

A: UPDATE
B: UPDATE
```

마지막 쓰기가 앞선 변경을 덮어쓰는 것을 막기 위해 버전을 `WHERE` 조건에 함께 넣습니다.

```ts
const updated = await db
  .updateTable("notes")
  .set((eb) => ({
    title: input.title,
    version: eb("version", "+", 1),
    updated_at: now
  }))
  .where("id", "=", input.id)
  .where("version", "=", input.baseVersion)
  .returning([
    "id",
    "title",
    "version",
    "updated_at"
  ])
  .executeTakeFirst();

if (!updated) {
  throw new VersionConflict();
}
```

핵심은 버전 비교와 갱신이 **하나의 `UPDATE` 문장** 안에서 수행된다는 점입니다.

```text
WHERE version = 이전에 읽은 버전
    ↓
조건이 아직 맞는 경우에만
    ↓
version = version + 1
```

다른 요청이 먼저 수정해 버전이 바뀌었다면 해당 `UPDATE`가 일치시키는 행은 0개가 됩니다.

### "행이 없음"과 "버전 충돌" 구분

다음 조건만 사용한다면

```ts
.where("id", "=", input.id)
.where("version", "=", input.baseVersion)
```

결과가 없을 때 다음 두 경우가 모두 가능합니다.

```text
해당 id가 존재하지 않음
해당 id는 있지만 version이 다름
```

API에서 반드시 두 경우를 구분해야 한다면 추가 조회 또는 다른 쿼리 전략이 필요합니다.

하지만 권한이 포함된 조건에서는 "존재 여부"를 외부에 노출하지 않기 위해 일부러 같은 오류로 처리하는 경우도 있습니다.

오류 의미는 SQL 하나만 보고 정하는 것이 아니라 API 보안 정책과 함께 결정합니다.

## 트랜잭션

여러 SQL 문이 하나의 작업 단위로 모두 성공하거나 모두 실패해야 한다면 트랜잭션을 사용합니다.

예를 들어 메모를 만들고 생성자를 멤버로 추가하는 두 작업이 항상 함께 성공해야 한다고 가정합니다.

```ts
const note = await db.transaction().execute(async (trx) => {
  const created = await trx
    .insertInto("notes")
    .values({
      id,
      owner_id: ownerId,
      title,
      body
    })
    .returning([
      "id",
      "owner_id",
      "title",
      "body",
      "version",
      "created_at",
      "updated_at"
    ])
    .executeTakeFirstOrThrow();

  await trx
    .insertInto("note_members")
    .values({
      note_id: created.id,
      user_id: ownerId,
      role: "editor"
    })
    .execute();

  return created;
});
```

Kysely의 관리형 트랜잭션 콜백이 정상적으로 끝나면 커밋되고, 콜백에서 오류가 던져지면 롤백됩니다.

```text
callback 성공
→ COMMIT

callback throw
→ ROLLBACK
```

트랜잭션 안에서는 가능한 한 전달받은 `trx`를 사용합니다.

```ts
await db.transaction().execute(async (trx) => {
  // 좋음
  await trx.insertInto(...).execute();

  // 주의: 트랜잭션 밖의 연결에서 실행될 수 있음
  await db.insertInto(...).execute();
});
```

트랜잭션 중 일부 쿼리만 바깥의 `db`로 실행하면 "모두 성공하거나 모두 실패"해야 하는 작업이 실제로는 나뉠 수 있습니다.

### 트랜잭션을 오래 잡지 않습니다

트랜잭션 안에서 네트워크 API 호출, 사용자 입력 대기, 긴 CPU 작업을 수행하면 데이터베이스 연결과 잠금을 오래 점유할 수 있습니다.

가능하면 다음처럼 구성합니다.

```text
필요한 외부 작업 준비
    ↓
짧은 DB 트랜잭션
    ↓
커밋
```

외부 시스템과 데이터베이스를 하나의 원자적 트랜잭션으로 묶을 수 없는 경우에는 별도의 일관성 전략이 필요합니다.

## 원시 SQL

Kysely 쿼리 빌더로 표현하기 어려운 PostgreSQL 전용 기능이나 복잡한 표현식은 `sql` 템플릿을 사용할 수 있습니다.

```ts
import { sql } from "kysely";

const result = await sql<{ id: string }>`
  select id
  from notes
  where to_tsvector(
          'simple',
          title || ' ' || body
        )
        @@ plainto_tsquery(
          'simple',
          ${query}
        )
`.execute(db);
```

`${query}`는 SQL 문자열에 직접 붙는 것이 아니라 값 매개변수로 바인딩됩니다.

개념적으로 다음처럼 분리됩니다.

```text
SQL 구조
→ ... plainto_tsquery('simple', $1)

값
→ query
```

따라서 사용자 입력을 다음처럼 `sql.raw()`에 넣지 않습니다.

```ts
// 위험
sql.raw(userInput)
```

`sql.raw()`에 들어간 문자열은 SQL 구문의 일부로 취급될 수 있기 때문입니다.

### 동적인 식별자

값 매개변수는 일반적으로 테이블 이름, 열 이름, `ASC`/`DESC` 같은 SQL 문법 요소를 대신하지 못합니다.

사용자가 정렬 열을 선택할 수 있다면 임의 문자열을 SQL 식별자로 전달하지 않고 허용 목록에서 선택합니다.

```ts
const sortColumns = {
  createdAt: "created_at",
  updatedAt: "updated_at",
  title: "title"
} as const;

const sortColumn =
  sortColumns[input.sortBy];
```

그 뒤 Kysely의 타입이 확인할 수 있는 식별자로 사용합니다.

허용 목록을 사용하면 사용자 입력 자체가 SQL 구문으로 승격되는 것을 막을 수 있습니다.

## PostgreSQL 오류 변환

PostgreSQL은 오류 유형을 SQLSTATE 코드로 제공합니다.

대표적으로 다음을 구분할 수 있습니다.

```text
23505 → unique_violation
23503 → foreign_key_violation
23514 → check_violation
23502 → not_null_violation
40001 → serialization_failure
40P01 → deadlock_detected
기타 연결·I/O 오류 → 시스템 오류
```

애플리케이션에서는 원본 데이터베이스 오류를 그대로 상위 계층으로 흘리기보다 의미 있는 오류로 변환할 수 있습니다.

```ts
try {
  await repository.create(...);
} catch (error) {
  if (isUniqueViolation(error)) {
    throw new AlreadyExists();
  }

  throw error;
}
```

### 오류 코드만으로 충분하지 않을 수 있습니다

`23505`는 "어떤 고유 제약이 위반되었는가"까지 의미하지 않습니다.

예를 들어 한 테이블에 다음 두 제약이 있을 수 있습니다.

```sql
constraint users_email_key unique (email),
constraint users_username_key unique (username)
```

두 경우 모두 SQLSTATE는 `23505`입니다.

제약 조건에 안정적인 이름을 붙이고 드라이버가 제공하는 constraint 이름을 함께 확인하면 어떤 도메인 규칙이 실패했는지 더 정확히 구분할 수 있습니다.

### 원본 오류를 클라이언트에 그대로 보내지 않습니다

데이터베이스 오류에는 다음 정보가 포함될 수 있습니다.

- 테이블 이름
- 열 이름
- 제약 조건 이름
- 내부 SQL
- 서버 구조에 관한 정보

이 정보가 외부 API 사용자에게 필요하지 않다면 공개하지 않습니다.

로그에는 운영에 필요한 정보를 남기되 비밀번호, 토큰, 민감한 사용자 값은 제거합니다.

## 재시도 가능한 오류

`40001`은 serialization failure입니다. 더 높은 격리 수준에서 동시 트랜잭션을 직렬 실행한 것처럼 만들 수 없을 때 PostgreSQL이 한 트랜잭션을 중단시키며 발생할 수 있습니다.

`40P01` deadlock도 PostgreSQL이 한 트랜잭션을 취소해 교착 상태를 해소할 때 발생합니다.

이런 오류는 경우에 따라 재시도할 수 있지만 "오류가 났으니 모든 쿼리를 자동 재시도한다"는 정책은 위험합니다.

특히 여러 문장으로 이루어진 트랜잭션은 **실패한 문장 하나가 아니라 트랜잭션 전체 단위**로 다시 실행해야 합니다.

```text
트랜잭션 시작
  SQL A
  SQL B
  SQL C
40001 발생
    ↓
전체 트랜잭션 롤백
    ↓
필요하다면 처음부터 제한적으로 재시도
```

재시도에는 다음 조건을 고려합니다.

- 작업 전체를 안전하게 다시 실행할 수 있는가
- 외부 시스템에 이미 부수 효과를 발생시키지 않았는가
- 최대 재시도 횟수가 제한되어 있는가
- 재시도 사이에 지수 백오프나 지터가 필요한가

따라서 `40001`을 단순히 "항상 재시도"로 매핑하지 않고 **정해진 트랜잭션 경계에서 제한적으로 재시도할 수 있는 후보**로 취급합니다.

## 실제 PostgreSQL 테스트

Kysely 쿼리 객체나 저장소 인터페이스만 모킹하면 애플리케이션 제어 흐름은 검사할 수 있지만 실제 PostgreSQL 동작은 확인할 수 없습니다.

다음 항목은 실제 PostgreSQL을 사용한 통합 테스트가 필요합니다.

- 마이그레이션 SQL이 실제로 실행되는지
- 열 타입과 기본값이 예상대로 동작하는지
- `UNIQUE`, `FOREIGN KEY`, `CHECK`, `NOT NULL` 제약이 실제로 거부하는지
- `NULL` 처리와 정렬 결과가 예상과 같은지
- `timestamptz`, `bigint` 등 드라이버 타입 변환이 예상과 같은지
- 트랜잭션에서 오류가 발생했을 때 실제로 롤백되는지
- 조건부 `UPDATE`에서 오래된 버전이 실패하는지
- 경쟁 요청이 동시에 실행될 때 데이터베이스 제약이 최종 상태를 보호하는지
- 사용 중인 격리 수준에서 동시성 문제가 어떻게 나타나는지

### 제약 조건 테스트

예를 들어 같은 고유 값을 두 번 삽입해 두 번째 삽입이 실제 PostgreSQL에서 실패하는지 확인합니다.

```text
INSERT A
→ 성공

같은 고유 값으로 INSERT B
→ 23505
```

### 롤백 테스트

트랜잭션의 첫 번째 쓰기가 성공한 뒤 두 번째 쓰기를 의도적으로 실패시킵니다.

```text
BEGIN
  INSERT notes       → 성공
  INSERT membership  → 실패
ROLLBACK
```

테스트가 끝난 뒤 `notes`의 첫 번째 삽입도 남지 않았는지 확인해야 합니다.

### 경쟁 요청 테스트

동시성 문제는 요청을 순서대로 한 번씩 실행하는 테스트로는 재현되지 않을 수 있습니다.

예를 들어 같은 좌석을 예약하는 두 작업을 실제로 겹쳐 실행합니다.

```text
request A ─┐
           ├─ 동시에 동일한 자원 예약
request B ─┘
```

최종적으로 데이터베이스에 허용되지 않는 중복 상태가 생기지 않는지 확인합니다.

## 마이그레이션 테스트

마이그레이션 파일이 TypeScript로 컴파일된다는 사실만으로 실제 데이터베이스에서 성공한다는 보장은 없습니다.

가능하면 깨끗한 테스트 데이터베이스에 처음부터 마이그레이션을 적용하는 경로를 검사합니다.

```text
빈 PostgreSQL
    ↓
모든 migration 적용
    ↓
최종 스키마 확인
    ↓
통합 테스트 실행
```

프로젝트가 다운 마이그레이션을 지원한다면 롤백 경로도 필요한 범위에서 검사합니다.

마이그레이션과 Kysely 타입을 한쪽만 수정하는 실수를 줄이기 위해 CI에서 실제 마이그레이션 적용을 수행하는 것이 유용합니다.

## 테스트 종료 처리

테스트에서 만든 연결 풀과 컨테이너는 반드시 종료합니다.

```ts
afterAll(async () => {
  await db.destroy();
});
```

테스트 컨테이너를 직접 시작했다면 해당 컨테이너도 정리합니다.

리소스를 닫지 않으면 다음 문제가 생길 수 있습니다.

- 테스트 프로세스가 종료되지 않음
- 다음 테스트와 포트 또는 연결 충돌
- CI에서 리소스 누수
- 테스트 간 데이터 상태 간섭

테스트의 데이터 격리 방법도 프로젝트에서 명시적으로 정합니다.

예를 들어 다음 중 하나를 사용할 수 있습니다.

- 테스트마다 데이터 삭제
- 테스트마다 트랜잭션 후 롤백
- 테스트마다 별도 스키마
- 테스트 스위트마다 별도 데이터베이스 또는 컨테이너

동시성 테스트는 여러 연결이 실제로 필요할 수 있으므로 "모든 테스트를 한 연결의 롤백 트랜잭션 안에서 실행"하는 방식만으로는 충분하지 않을 수 있습니다.

## 흔한 실수

- HTTP 요청마다 새 `Pool` 또는 새 Kysely 인스턴스를 만듭니다.
- 인스턴스 수를 고려하지 않고 각 풀의 `max`만 크게 잡습니다.
- 환경 변수의 형식 검사만 통과하면 실제 DB 연결도 보장된다고 생각합니다.
- 데이터베이스 URL 전체를 로그에 출력합니다.
- Kysely 타입이 실제 PostgreSQL 스키마를 자동으로 검증하거나 생성한다고 생각합니다.
- 마이그레이션 SQL과 Kysely 타입 중 한쪽만 변경합니다.
- Kysely 타입이 `pg`의 런타임 타입 변환까지 자동으로 보장한다고 생각합니다.
- PostgreSQL `bigint`를 확인 없이 JavaScript `number`로 가정합니다.
- 모든 쿼리에서 습관적으로 `selectAll()`을 사용합니다.
- 데이터베이스 행을 변환하지 않고 그대로 HTTP 응답 계약으로 사용합니다.
- 조회 후 별도 `UPDATE`를 하면서 그 사이에 다른 요청이 끼어들 수 있다는 점을 무시합니다.
- 트랜잭션 안에서 일부 쿼리를 `trx`가 아닌 바깥 `db`로 실행합니다.
- 트랜잭션 안에서 느린 외부 API 호출을 수행해 연결과 잠금을 오래 유지합니다.
- 사용자 입력을 `sql.raw()`에 전달합니다.
- 동적인 열 이름을 허용 목록 없이 SQL에 넣습니다.
- 모든 `23505` 오류를 같은 도메인 오류로 처리합니다.
- PostgreSQL 원본 오류 메시지를 그대로 HTTP 응답으로 보냅니다.
- `40001`이 발생한 문장 하나만 재시도하면 된다고 생각합니다.
- 재시도 가능성을 고려하지 않고 외부 부수 효과와 DB 트랜잭션을 섞습니다.
- 모킹만으로 실제 제약 조건, 타입 변환, 롤백과 경쟁 상태를 검증했다고 생각합니다.
- 테스트 후 연결 풀과 컨테이너를 닫지 않습니다.

## 완료 기준

- 연결 풀을 애플리케이션 시작 시 생성하고 종료 시 닫아야 하는 이유를 설명할 수 있습니다.
- 애플리케이션 인스턴스 수와 풀 크기를 PostgreSQL 최대 연결 수와 함께 계산할 수 있습니다.
- 환경 변수 검증과 실제 데이터베이스 연결 검사의 차이를 설명할 수 있습니다.
- 실제 PostgreSQL 스키마와 Kysely TypeScript 타입이 자동으로 동기화되지 않는다는 점을 설명할 수 있습니다.
- `Generated`와 `ColumnType`으로 조회·삽입·수정 타입의 차이를 표현할 수 있습니다.
- `Selectable`, `Insertable`, `Updateable`이 어떤 타입을 파생하는지 설명할 수 있습니다.
- `pg`가 반환하는 런타임 값과 Kysely 타입 선언을 별도로 확인할 수 있습니다.
- 필요한 열만 조회하고 데이터베이스 행을 애플리케이션 값으로 명시적으로 변환할 수 있습니다.
- PostgreSQL의 `RETURNING`과 Kysely의 `executeTakeFirstOrThrow()` 사용 의미를 설명할 수 있습니다.
- 조건부 `UPDATE`가 오래된 쓰기를 어떻게 감지하는지 설명할 수 있습니다.
- 여러 SQL 문이 하나의 작업 단위일 때 Kysely 트랜잭션을 사용할 수 있습니다.
- 트랜잭션 안에서는 전달받은 `trx`를 사용해야 하는 이유를 설명할 수 있습니다.
- `sql` 템플릿의 값 바인딩과 `sql.raw()`의 차이를 설명할 수 있습니다.
- SQLSTATE 코드와 제약 조건 이름을 이용해 PostgreSQL 오류를 애플리케이션 오류로 변환할 수 있습니다.
- `40001`과 `40P01` 같은 오류를 트랜잭션 전체 단위의 제한적 재시도 후보로 설명할 수 있습니다.
- 실제 PostgreSQL에서 마이그레이션, 제약 조건, 롤백, 타입 변환과 경쟁 요청을 검사해야 하는 이유를 설명할 수 있습니다.

## 연결 exercise

[`seat-reservation`](../../exercises/seat-reservation/README.md)은 실제 PostgreSQL에서 고유 제약, 트랜잭션과 경쟁 요청을 검사합니다.
