# PostgreSQL과 Kysely

Kysely는 열 이름과 결과 타입을 컴파일할 때 확인하는 데 도움을 줍니다. 하지만 실제 테이블, 제약 조건과 트랜잭션 동작은 PostgreSQL이 결정합니다. TypeScript 타입과 실제 데이터베이스 스키마가 자동으로 맞춰진다고 가정하지 않습니다.

## 목표

- 하나의 연결 풀을 애플리케이션 수명에 맞춰 열고 닫습니다.
- Kysely 테이블 타입과 마이그레이션 SQL을 일치시킵니다.
- 필요한 열만 조회하고 애플리케이션 값으로 변환합니다.
- 쿼리 빌더와 원시 SQL을 안전하게 사용합니다.
- 실제 PostgreSQL에서 제약 조건, 경쟁 요청과 롤백을 검사합니다.

## 연결 풀

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

요청마다 새 풀을 만들지 않습니다. 애플리케이션이 시작될 때 만들고 종료할 때 `db.destroy()`로 닫습니다. 풀 크기는 인스턴스 수와 PostgreSQL의 최대 연결 수를 함께 고려합니다.

## 환경 변수 검사

```ts
const EnvSchema = z.object({
  DATABASE_URL: z.string().url(),
  DATABASE_POOL_SIZE: z.coerce.number().int().min(1).max(20).default(5)
});
```

잘못된 주소나 풀 크기를 첫 쿼리에서 발견하지 말고 프로세스 시작 전에 거부합니다. 로그에 데이터베이스 비밀번호를 출력하지 않습니다.

## 테이블 타입

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

실제 코드에서는 `Generated`와 `ColumnType`으로 삽입값과 조회값을 구분할 수 있습니다. 이 타입은 마이그레이션 SQL에서 자동 생성된 것이 아니므로 다음 네 가지를 함께 확인합니다.

```text
마이그레이션 SQL
↔ Kysely 테이블 타입
↔ 애플리케이션 값 변환
↔ 응답 스키마
```

## 필요한 열만 조회합니다

```ts
const rows = await db
  .selectFrom("notes")
  .select(["id", "title", "version", "updated_at"])
  .where("owner_id", "=", actorId)
  .orderBy("updated_at", "desc")
  .orderBy("id", "desc")
  .limit(limit)
  .execute();
```

`selectAll()`은 이후 추가된 비밀 열이나 내부 상태를 상위 코드에 의도치 않게 전달할 수 있습니다. 필요한 열만 선택합니다.

## 행을 애플리케이션 값으로 바꿉니다

```ts
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

이 함수는 필드 이름뿐 아니라 `NULL`, 날짜, 큰 정수와 열거형 값도 애플리케이션이 기대하는 형태로 바꿉니다. 데이터베이스 행을 그대로 HTTP 응답으로 보내지 않습니다.

## INSERT와 반환값

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
  .returning(["id", "owner_id", "title", "body", "version", "created_at", "updated_at"])
  .executeTakeFirstOrThrow();
```

반드시 한 행이 생겨야 하는 내부 작업에는 `executeTakeFirstOrThrow()`를 쓸 수 있습니다. 사용자 입력 오류와 데이터베이스 연결 오류를 같은 응답으로 처리하지 않습니다.

## 조건부 UPDATE

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
  .returning(["id", "title", "version", "updated_at"])
  .executeTakeFirst();

if (!updated) throw new VersionConflict();
```

“조회한 뒤 나중에 수정”하는 두 쿼리 사이에는 다른 요청이 끼어들 수 있습니다. 조건부 UPDATE 한 문장에서 버전 비교와 수정을 함께 처리합니다.

## 원시 SQL

PostgreSQL 전용 기능이나 복잡한 쿼리는 SQL 템플릿으로 작성할 수 있습니다.

```ts
const result = await sql<{ id: string }>`
  select id
  from notes
  where to_tsvector('simple', title || ' ' || body)
        @@ plainto_tsquery('simple', ${query})
`.execute(db);
```

`${query}`는 값으로 바인딩됩니다. 사용자 입력을 `sql.raw()`에 넣지 않습니다. 동적인 열 이름이 필요하다면 미리 정한 허용 목록에서만 선택합니다.

## PostgreSQL 오류 변환

어댑터에서 오류 코드를 애플리케이션 오류로 바꿀 수 있습니다.

```text
23505 → 고유성 충돌
23503 → 존재하지 않는 참조 또는 관계 충돌
40001 → 조건을 제한한 재시도 후보
기타 연결·I/O 오류 → 시스템 오류
```

제약 조건에 이름을 붙이면 어떤 규칙이 실패했는지 더 정확히 판단할 수 있습니다. 원본 오류 문장을 클라이언트에 보내지 않습니다.

## 실제 데이터베이스 테스트

다음은 쿼리 빌더 모킹으로 확인할 수 없습니다.

- SQL 마이그레이션 문법
- 고유·외래 키·검사 제약 조건
- `NULL`, 타임스탬프와 큰 정수 처리
- 트랜잭션 롤백
- 경쟁 요청 중 하나만 성공하는지

테스트가 끝나면 연결 풀과 컨테이너를 닫습니다.

## 흔한 실수

- 요청마다 새 연결 풀을 만듭니다.
- 잘못된 환경 값을 첫 쿼리에서 발견합니다.
- Kysely 타입이 실제 스키마를 자동으로 보장한다고 생각합니다.
- 모든 쿼리에서 `selectAll()`을 사용합니다.
- 행을 변환하지 않고 HTTP 응답으로 보냅니다.
- 사용자 입력을 `sql.raw()`에 전달합니다.
- 모킹만으로 실제 제약과 롤백을 검증합니다.

## 완료 기준

- 연결 풀의 생성과 종료 시점을 설명합니다.
- SQL, Kysely 타입, 애플리케이션 값과 응답 형식의 차이를 구분합니다.
- 필요한 열만 조회하고 명시적으로 변환합니다.
- 조건부 UPDATE와 매개변수화된 SQL을 작성합니다.
- 실제 PostgreSQL 테스트가 필요한 항목을 설명합니다.

## 연결 exercise

[`seat-reservation`](../../exercises/seat-reservation/README.md)은 실제 PostgreSQL에서 고유 제약, 트랜잭션과 경쟁 요청을 검사합니다.
