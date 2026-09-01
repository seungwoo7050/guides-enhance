# 서비스, 리포지터리와 오류 처리

라우트 한곳에서 입력 검사, SQL, 권한 확인, 트랜잭션과 HTTP 응답 생성을 모두 처리하면 작은 기능을 바꿀 때 여러 관심사가 함께 흔들립니다. 반대로 역할이 명확하지 않은 파일과 인터페이스를 기계적으로 늘리면 단순 전달 코드만 증가합니다.

코드를 나누는 기준은 파일 이름이 아니라 **각 계층이 어떤 결정을 책임지는가**입니다.

이 문서에서는 다음 세 경계를 중심으로 봅니다.

```text
HTTP route
→ application service
→ repository / database
```

각 계층의 책임을 분리하면 테스트할 대상과 오류를 변환할 위치, 트랜잭션 범위가 더 명확해집니다.

## 목표

- 라우트, 서비스와 리포지터리가 각각 처리할 일을 구분합니다.
- 저장소, 시계, ID 생성기 같은 의존성을 생성 시점에 전달합니다.
- 예상 가능한 업무 실패와 예상하지 못한 시스템 오류를 구분합니다.
- 데이터베이스 고유 제약과 애플리케이션 사전 검사의 역할을 구분합니다.
- 함께 성공하거나 실패해야 하는 쓰기를 하나의 트랜잭션으로 묶습니다.
- 트랜잭션을 어느 계층이 소유해야 하는지 설명합니다.
- 메모리 구현과 실제 데이터베이스 테스트가 서로 다른 문제를 찾는다는 점을 이해합니다.

## 전체 책임 분리

한 요청의 흐름을 단순화하면 다음과 같습니다.

```text
HTTP request
    ↓
route
    ↓
service
    ↓
repository
    ↓
database
```

응답은 반대 방향으로 올라옵니다.

```text
database result / error
    ↑
repository
    ↑
service
    ↑
route / error handler
    ↑
HTTP response
```

각 계층이 주로 책임지는 것은 다음과 같습니다.

| 계층 | 주된 책임 |
|---|---|
| route | HTTP 입력과 출력, 인증된 사용자 읽기, 서비스 호출 |
| service | 한 업무 작업의 순서와 업무 규칙 |
| repository | 데이터베이스에 필요한 저장·조회 연산 |
| database | 제약 조건, 격리, 원자적 커밋과 롤백 |

이 표는 절대적인 프레임워크 규칙이 아니라 책임을 나누기 위한 기준입니다.

## 라우트가 하는 일

라우트는 HTTP 프로토콜과 애플리케이션 서비스 사이의 어댑터 역할을 합니다.

```ts
app.post("/boards", async (request, reply) => {
  const input = CreateBoardSchema.parse(request.body);
  const actor = requireActor(request);

  const board = await service.createBoard({
    actorId: actor.id,
    title: input.title
  });

  return reply
    .code(201)
    .send(toBoardDto(board));
});
```

라우트는 일반적으로 다음을 처리합니다.

- 경로·쿼리·헤더·본문 읽기
- 외부 입력의 형식 검증과 정규화
- 인증된 사용자 정보 읽기
- 서비스 함수 호출
- 서비스 결과를 응답 DTO로 변환
- 성공 상태 코드 선택

예를 들어 다음 두 값은 HTTP 계층의 입력입니다.

```text
request.params.boardId
request.body.title
```

라우트에서 검증한 뒤 서비스에는 내부에서 사용할 명확한 command를 전달합니다.

```ts
type RenameBoardCommand = {
  actorId: string;
  boardId: string;
  title: string;
};
```

서비스는 `request`, `reply`, 헤더 이름, HTTP 상태 코드 같은 Fastify 세부 사항을 알 필요가 없습니다.

## 라우트에서 하지 않는 일

라우트가 다음 책임까지 직접 가지기 시작하면 업무 규칙과 HTTP 처리가 결합됩니다.

```ts
app.post("/boards", async (request, reply) => {
  const input = CreateBoardSchema.parse(request.body);

  const existing = await db
    .selectFrom("boards")
    .selectAll()
    .where("owner_id", "=", request.user.id)
    .where("title", "=", input.title)
    .executeTakeFirst();

  if (existing) {
    return reply.code(409).send(...);
  }

  // SQL 추가 실행
  // 이벤트 기록
  // 감사 로그
  // 업무 규칙
});
```

이 방식은 처음에는 짧아 보일 수 있지만 다음 변경이 모두 route에 영향을 줄 수 있습니다.

```text
중복 규칙 변경
저장 방법 변경
트랜잭션 추가
다른 프로토콜에서 같은 기능 재사용
서비스 단위 테스트
```

라우트는 가능한 한 다음 형태에 가깝게 유지합니다.

```text
HTTP 입력
→ 내부 command
→ service
→ HTTP 출력
```

## 서비스가 하는 일

서비스는 **한 업무 작업이 어떤 순서와 규칙으로 실행되는지** 결정합니다.

```ts
class BoardService {
  constructor(
    private readonly boards: BoardRepository,
    private readonly ids: IdGenerator,
    private readonly clock: Clock
  ) {}

  async createBoard(
    command: CreateBoardCommand
  ): Promise<Board> {
    const existing =
      await this.boards.findByOwnerAndTitle(
        command.actorId,
        command.title
      );

    if (existing) {
      throw new ConflictError("board_title_exists");
    }

    const board = Board.create(
      this.ids.next(),
      command.actorId,
      command.title,
      this.clock.now()
    );

    await this.boards.insert(board);

    return board;
  }
}
```

이 서비스는 다음 결정을 합니다.

```text
1. 같은 소유자 범위에 같은 제목이 있는지 확인
2. 중복이면 업무 충돌로 처리
3. 새 ID 생성
4. 현재 시각 사용
5. Board 생성
6. 저장
7. 생성된 Board 반환
```

이 순서 자체가 업무 동작의 일부입니다.

서비스는 Fastify의 `reply.code(409)` 같은 HTTP 표현을 몰라도 됩니다.

```text
service
→ "board_title_exists"라는 충돌 발생

HTTP layer
→ 그 충돌을 409로 표현
```

이렇게 하면 같은 서비스를 HTTP가 아닌 다른 진입점에서도 재사용할 수 있습니다.

예:

```text
HTTP route
WebSocket command
CLI
background job
```

모든 진입점이 동일한 업무 규칙을 사용할 수 있습니다.

## 서비스는 업무 규칙을 표현합니다

서비스에서 다룰 수 있는 규칙의 예는 다음과 같습니다.

```text
사용자는 자신이 소유한 board만 삭제할 수 있다
archive된 board에는 item을 추가할 수 없다
같은 workspace에서 title은 중복될 수 없다
version이 현재 값과 같을 때만 수정한다
작업 성공 시 audit event도 함께 기록한다
```

중요한 점은 "서비스 파일에 코드를 넣는다"가 아니라 **업무 의미가 있는 결정을 서비스가 소유한다**는 것입니다.

다음처럼 단순 전달만 하는 서비스라면 계층이 실제 가치를 주는지 다시 검토할 수 있습니다.

```ts
class BoardService {
  async getById(id: string) {
    return this.boards.getById(id);
  }
}
```

이 함수가 별도의 권한, 규칙, 변환, 트랜잭션을 전혀 담당하지 않는다면 단순한 중간 계층일 수 있습니다.

모든 함수에 서비스 계층이 반드시 필요한 것은 아닙니다.

## 의존성은 생성 시점에 전달합니다

서비스가 직접 전역 저장소를 가져오는 대신 필요한 값을 생성자에서 받습니다.

```ts
class BoardService {
  constructor(
    private readonly boards: BoardRepository,
    private readonly ids: IdGenerator,
    private readonly clock: Clock
  ) {}
}
```

운영 환경에서는 실제 구현을 전달합니다.

```ts
const boardService = new BoardService(
  postgresBoardRepository,
  randomIdGenerator,
  systemClock
);
```

테스트에서는 제어 가능한 구현을 전달합니다.

```ts
const boardService = new BoardService(
  memoryBoardRepository,
  sequentialIds,
  fixedClock
);
```

이렇게 하면 서비스는 구체적인 저장 기술보다 자신이 필요한 동작에 의존합니다.

## 시계와 ID 생성기도 의존성입니다

현재 시각이나 랜덤 ID도 외부 상태입니다.

다음처럼 서비스 내부에서 직접 호출하면:

```ts
const id = crypto.randomUUID();
const now = new Date();
```

테스트가 실행될 때마다 값이 달라집니다.

대신 인터페이스를 통해 전달할 수 있습니다.

```ts
interface Clock {
  now(): Date;
}

interface IdGenerator {
  next(): string;
}
```

테스트:

```ts
const clock: Clock = {
  now: () => new Date("2026-01-01T00:00:00Z")
};

const ids: IdGenerator = {
  next: () => "board-1"
};
```

이제 서비스 결과를 정확히 예측할 수 있습니다.

```text
createdAt = 항상 같은 시각
id = 항상 같은 값
```

이 방식은 테스트를 결정적으로 만들고, 업무 코드가 시간이나 난수에 얼마나 의존하는지도 드러냅니다.

## 리포지터리가 하는 일

리포지터리는 애플리케이션이 필요로 하는 저장 작업을 표현합니다.

```ts
interface BoardRepository {
  findVisibleById(
    actorId: string,
    boardId: string
  ): Promise<Board | null>;

  insert(board: Board): Promise<void>;

  updateTitleIfVersion(
    input: RenameInput
  ): Promise<Board | null>;
}
```

리포지터리의 목적은 데이터베이스의 모든 기능을 감추는 것이 아니라 **서비스가 필요한 저장 연산을 명확한 함수로 표현하는 것**입니다.

예를 들어 다음 함수는 의미가 약합니다.

```ts
save(value: any): Promise<any>
```

호출자 입장에서 무엇이 보장되는지 알기 어렵습니다.

반면 다음 함수는 저장 조건을 드러냅니다.

```ts
updateTitleIfVersion(input): Promise<Board | null>
```

이 함수 이름과 반환값에서 다음 의미를 읽을 수 있습니다.

```text
현재 version이 기대한 값과 같을 때만 수정
성공하면 Board 반환
조건 불일치면 null
```

저장소 계층의 API가 실제 업무에 필요한 원자적 연산을 표현하면 경쟁 조건을 줄이는 데도 도움이 됩니다.

## 리포지터리는 SQL 한 줄을 감싸는 것만이 목적이 아닙니다

리포지터리 메서드 하나가 SQL 하나와 정확히 대응할 필요는 없습니다.

예를 들어 서비스가 원하는 의미가 다음과 같다면:

```text
현재 version이 12일 때만 title 변경
```

PostgreSQL 구현은 하나의 조건부 UPDATE로 처리할 수 있습니다.

```sql
UPDATE boards
SET
  title = $1,
  version = version + 1
WHERE id = $2
  AND version = $3
RETURNING *;
```

영향받은 행이 없으면 두 가능성이 있습니다.

```text
리소스가 없음
또는
version이 다름
```

API가 둘을 구분해야 한다면 추가 조회 또는 다른 쿼리 전략이 필요할 수 있습니다.

핵심은 리포지터리 API가 단순한 CRUD 이름보다 서비스가 필요로 하는 저장 의미를 표현할 수 있다는 것입니다.

## 리포지터리가 하지 않는 일

리포지터리는 일반적으로 다음 책임을 갖지 않습니다.

- HTTP 상태 코드 선택
- `reply.send()` 호출
- Fastify request 사용
- 외부 응답 DTO 생성
- UI용 오류 문장 선택

예를 들어 다음 반환값은 저장 계층과 HTTP를 결합합니다.

```ts
return {
  statusCode: 404,
  body: {
    code: "board_not_found"
  }
};
```

대신 저장 계층은 저장 결과 또는 저장 관련 오류를 반환하고, 상위 계층에서 업무 의미와 HTTP 표현으로 변환합니다.

## 데이터베이스 행과 도메인 객체를 구분합니다

데이터베이스에서 읽은 행은 저장 구조입니다.

```ts
type BoardRow = {
  id: string;
  owner_id: string;
  title: string;
  version: number;
  created_at: Date;
};
```

서비스가 사용하는 모델은 다른 이름과 구조를 가질 수 있습니다.

```ts
type Board = {
  id: string;
  ownerId: string;
  title: string;
  version: number;
  createdAt: Date;
};
```

리포지터리 구현에서 매핑할 수 있습니다.

```ts
function toBoard(row: BoardRow): Board {
  return {
    id: row.id,
    ownerId: row.owner_id,
    title: row.title,
    version: row.version,
    createdAt: row.created_at
  };
}
```

데이터베이스 행을 그대로 HTTP 응답 DTO로 사용하는 것은 서로 다른 경계를 하나로 묶는 일입니다.

```text
database schema 변경
→ application type 변경
→ API response 변경
```

이 결합이 의도된 것이 아니라면 각 경계에서 필요한 형태로 변환합니다.

## 사전 조회만으로 중복을 막을 수 없습니다

다음 서비스 코드는 자연스러워 보입니다.

```ts
const existing =
  await boards.findByOwnerAndTitle(
    actorId,
    title
  );

if (existing) {
  throw new ConflictError(
    "board_title_exists"
  );
}

await boards.insert(board);
```

하지만 동시에 두 요청이 들어오면 경쟁 조건이 생길 수 있습니다.

```text
요청 A: 중복 조회 → 없음
요청 B: 중복 조회 → 없음
요청 A: insert 성공
요청 B: insert 성공
```

두 요청 모두 사전 조회를 통과했기 때문입니다.

따라서 "같은 owner 안에서 title은 반드시 유일해야 한다"가 데이터 무결성 규칙이라면 데이터베이스에도 제약 조건을 둬야 합니다.

예:

```sql
UNIQUE (owner_id, title)
```

그러면 경쟁 요청이 들어와도 데이터베이스가 최종적으로 중복을 막습니다.

## 애플리케이션 검사와 데이터베이스 제약은 역할이 다릅니다

사전 조회가 항상 쓸모없는 것은 아닙니다.

```text
애플리케이션 사전 검사
→ 사용자가 이해하기 쉬운 실패를 일찍 반환

데이터베이스 제약
→ 동시 요청까지 포함해 무결성을 최종 보장
```

둘은 서로 다른 역할입니다.

예를 들어:

```text
service
findByOwnerAndTitle()
→ 이미 있으면 ConflictError

repository/database
UNIQUE(owner_id, title)
→ 경쟁 상황에서도 최종 중복 방지
```

정상적인 단일 요청에서는 서비스 사전 검사가 친절한 오류를 만들고, 경쟁 상황에서는 DB 제약이 안전망이 됩니다.

## TOCTOU 경쟁 조건

"먼저 확인한 뒤 나중에 변경"하는 패턴에서는 확인 시점과 사용 시점 사이에 상태가 바뀔 수 있습니다.

이를 흔히 **TOCTOU(Time Of Check To Time Of Use)** 문제라고 부릅니다.

```text
check
↓
다른 요청이 상태 변경
↓
use
```

예:

```text
재고가 1개 있는지 조회
→ 있음

다른 요청이 마지막 1개 구매

현재 요청이 구매 처리
```

사전 조회 결과만 믿으면 잘못된 상태가 생길 수 있습니다.

가능하면 데이터베이스의 조건부 쓰기, 제약 조건, 잠금 또는 적절한 격리 수준을 사용해 최종 변경 시점에 조건을 보장합니다.

## 조건부 UPDATE로 경쟁을 줄입니다

버전 충돌도 같은 원칙을 적용할 수 있습니다.

나쁜 패턴:

```text
SELECT version
→ version == 12 확인
→ UPDATE
```

확인과 UPDATE 사이에 다른 요청이 끼어들 수 있습니다.

대신 한 SQL에서 조건과 변경을 묶을 수 있습니다.

```sql
UPDATE boards
SET
  title = $1,
  version = version + 1
WHERE id = $2
  AND version = $3
RETURNING *;
```

이 연산은 데이터베이스가 한 statement로 처리하므로 다음 의미를 만들 수 있습니다.

```text
version이 기대한 값이면 수정
아니면 수정하지 않음
```

리포지터리 메서드가:

```ts
updateTitleIfVersion(...)
```

처럼 설계되는 이유가 여기에 있습니다.

## 트랜잭션이 필요한 경우

여러 데이터베이스 변경이 하나의 업무 작업을 구성하고, 중간 상태가 외부에 남으면 안 된다면 하나의 트랜잭션으로 묶습니다.

예를 들어 item 위치 변경과 감사 이벤트 기록이 반드시 함께 성공해야 한다고 가정합니다.

```ts
await unitOfWork.transaction(async (tx) => {
  const item =
    await tx.items.updateIfVersion(command);

  if (!item) {
    throw new ConflictError("stale_item");
  }

  await tx.events.append(
    createEvent(item)
  );
});
```

의도는 다음과 같습니다.

```text
item update 성공
AND
event insert 성공

둘 다 성공
→ COMMIT

둘 중 하나 실패
→ ROLLBACK
```

트랜잭션이 없다면 다음 상태가 남을 수 있습니다.

```text
item 변경 성공
event 기록 실패
```

업무 규칙상 이 상태가 허용되지 않는다면 트랜잭션이 필요합니다.

## 트랜잭션의 원자성

트랜잭션에서 가장 중요한 성질 중 하나는 **원자성(atomicity)**입니다.

여러 쓰기를 하나의 작업으로 묶으면 애플리케이션 관점에서 다음 둘 중 하나만 남도록 할 수 있습니다.

```text
모두 반영됨
또는
아무것도 반영되지 않음
```

예:

```text
좌석 예약 생성
결제 대기 레코드 생성
감사 이벤트 기록
```

세 작업이 하나의 업무 단위이고 일부만 저장된 상태가 허용되지 않는다면 하나의 트랜잭션 범위를 고려합니다.

## 트랜잭션 범위는 업무 작업 단위로 정합니다

트랜잭션은 SQL 파일 단위나 repository 메서드 개수로 정하는 것이 아니라 **함께 성공해야 하는 데이터 변경 범위**로 정합니다.

예:

```text
Board 생성
+
소유자 membership 생성
```

둘 중 하나만 남아서는 안 된다면 같은 트랜잭션에 둘 수 있습니다.

반대로 서로 독립적으로 성공할 수 있는 작업을 불필요하게 하나의 긴 트랜잭션에 묶으면 잠금 유지 시간이 늘어날 수 있습니다.

## 트랜잭션을 누가 시작할 것인가

서비스가 여러 repository 작업을 하나의 업무 단위로 조정한다면 트랜잭션 범위도 서비스 수준에서 결정할 필요가 있습니다.

예:

```ts
await unitOfWork.transaction(
  async (repos) => {
    const board =
      await repos.boards.insert(...);

    await repos.members.insert(...);

    return board;
  }
);
```

여기서 서비스는:

```text
board insert
membership insert
```

가 함께 성공해야 한다는 업무 의미를 알고 있습니다.

각 repository가 자기 내부에서 독립적으로 트랜잭션을 시작한다면 둘을 하나의 원자적 작업으로 묶기 어려울 수 있습니다.

따라서 여러 저장소를 걸치는 트랜잭션은 **작업 전체의 일관성을 아는 계층**이 범위를 결정하는 편이 자연스럽습니다.

구체적인 트랜잭션 객체를 서비스가 직접 SQL 클라이언트 타입으로 다룰 필요는 없으며, `UnitOfWork` 같은 추상화를 사용할 수 있습니다.

## 모든 repository 호출을 트랜잭션으로 감쌀 필요는 없습니다

단순 조회 한 번이나 원자적인 단일 UPDATE는 별도 애플리케이션 트랜잭션이 필요하지 않을 수 있습니다.

예:

```sql
UPDATE boards
SET version = version + 1
WHERE id = $1
RETURNING *;
```

데이터베이스 statement 자체가 원자적으로 수행됩니다.

트랜잭션은 "데이터베이스를 쓰면 항상 필요하다"가 아니라 **여러 연산을 하나의 원자적 업무 단위로 묶어야 할 때** 사용합니다.

## 트랜잭션 안에서 외부 네트워크 호출을 오래 기다리지 않습니다

다음 구조는 주의해야 합니다.

```text
BEGIN
→ DB row 조회/잠금
→ 외부 결제 API 호출
→ 응답 대기
→ DB update
→ COMMIT
```

외부 API가 느리면 데이터베이스 트랜잭션과 잠금이 오래 유지될 수 있습니다.

그 결과:

```text
다른 요청 대기
연결 풀 점유
deadlock 가능성 증가
타임아웃 가능성 증가
```

같은 문제가 생길 수 있습니다.

일반적으로 데이터베이스 트랜잭션은 가능한 짧게 유지합니다.

다만 "DB 변경과 외부 시스템 호출을 어떻게 하나의 업무 작업처럼 보장할 것인가"는 단순한 트랜잭션만으로 해결되지 않습니다. 외부 시스템은 같은 데이터베이스 트랜잭션에 참여하지 않기 때문입니다.

이 경우에는 작업 상태 저장, 재시도, outbox 같은 별도 설계가 필요할 수 있지만 이 문서에서는 트랜잭션 범위를 짧게 유지해야 한다는 원칙까지만 다룹니다.

## 오류를 종류별로 구분합니다

모든 실패를 같은 `Error`로 취급하면 HTTP 계층에서 어떤 오류가 사용자의 잘못이고 어떤 오류가 서버 장애인지 구분하기 어려워집니다.

오류를 크게 두 종류로 나눌 수 있습니다.

```text
예상 가능한 실패
업무적으로 발생할 수 있다고 알고 있는 경우

시스템 오류
현재 요청에서 정상적으로 처리하기 어려운 인프라·프로그램 실패
```

## 예상 가능한 실패

다음은 정상적인 업무 흐름에서 발생할 수 있는 실패입니다.

- 리소스 없음
- 권한 부족
- 고유성 충돌
- 현재 버전과의 충돌
- 현재 상태에서는 허용되지 않는 작업
- 입력 형식 검증 이후 발견되는 업무 규칙 위반

예:

```ts
throw new ConflictError(
  "board_title_exists"
);
```

또는:

```ts
throw new NotFoundError(
  "board_not_found"
);
```

이 오류에는 클라이언트가 사용할 안정적인 업무 코드를 둘 수 있습니다.

```text
board_not_found
board_title_exists
stale_item
permission_denied
```

HTTP 계층은 이 코드를 상태 코드와 공개 오류 응답으로 바꿉니다.

## 시스템 오류

다음은 일반적으로 업무 실패가 아니라 시스템 장애에 가깝습니다.

- 데이터베이스 연결 실패
- 데이터베이스 쿼리 타임아웃
- 디스크 오류
- 네트워크 장애
- 드라이버 오류
- 예상하지 못한 프로그램 예외

예:

```text
ECONNRESET
connection refused
query timeout
disk full
```

이런 오류를 사용자에게 "board가 존재하지 않습니다" 같은 업무 오류로 바꿔서는 안 됩니다.

현재 요청에서 복구할 수 없다면 원본 오류를 보존한 채 상위로 전달하고 최종 HTTP 경계에서 일반적인 500 또는 적절한 5xx 응답으로 변환합니다.

## 원본 오류를 보존합니다

시스템 오류를 새 오류로 감쌀 때 원인을 잃어버리면 디버깅하기 어렵습니다.

나쁜 예:

```ts
catch {
  throw new Error("database failed");
}
```

원래 어떤 오류가 발생했는지 사라집니다.

가능하다면 원인을 보존합니다.

```ts
throw new RepositoryError(
  "board_insert_failed",
  { cause: error }
);
```

이렇게 하면 외부 응답에는 안전한 메시지를 보내면서 내부 로그에서는 실제 원인을 확인할 수 있습니다.

```text
client
→ internal_error

server log
→ RepositoryError
   caused by PostgreSQL connection error
```

## 오류를 바꾸는 위치

오류는 자신이 이해할 수 있는 의미 수준에서 변환합니다.

예를 들어 PostgreSQL 고유 제약 위반이 발생했다고 가정합니다.

```text
PostgreSQL unique violation
↓
repository
↓
service
↓
HTTP error handler
```

각 계층은 서로 다른 의미를 압니다.

### PostgreSQL 리포지터리

리포지터리는 데이터베이스 오류 코드와 어떤 제약 조건에서 실패했는지 알 수 있습니다.

예:

```text
PostgreSQL unique violation
constraint = boards_owner_title_key
```

이를 저장소 수준의 충돌 정보로 변환할 수 있습니다.

### 서비스

서비스는 그 제약 조건이 업무적으로 무엇을 뜻하는지 압니다.

```text
owner + title unique violation
→ board_title_exists
```

따라서 업무 오류 코드로 변환할 수 있습니다.

### HTTP 오류 처리기

HTTP 계층은 업무 오류를 HTTP 계약으로 표현합니다.

```text
board_title_exists
→ 409 Conflict
```

최종 흐름:

```text
PostgreSQL 고유 제약 위반
→ repository가 저장소 충돌로 변환
→ service가 "board_title_exists" 결정
→ HTTP error handler가 409 응답 생성
```

모든 변환을 반드시 세 단계로 해야 한다는 뜻은 아닙니다. 중요한 것은 **각 계층이 이해할 수 없는 세부 정보를 억지로 해석하지 않는 것**입니다.

## 데이터베이스 오류 코드를 HTTP 계층에서 직접 해석하지 않습니다

다음 코드는 계층을 강하게 결합합니다.

```ts
app.setErrorHandler((error, request, reply) => {
  if (error.code === "23505") {
    return reply.code(409).send(...);
  }
});
```

HTTP 계층이 PostgreSQL 전용 오류 코드 `23505`를 직접 알아야 합니다.

데이터베이스를 바꾸거나 제약 조건이 여러 개 생기면 HTTP 코드가 저장 구조에 의존하게 됩니다.

더 나은 경계는 다음과 같습니다.

```text
PostgreSQL-specific error
→ repository-level meaning
→ application-level meaning
→ HTTP
```

## 같은 오류를 여러 곳에서 반복 기록하지 않습니다

예외가 올라오는 모든 계층에서 같은 오류를 로그로 남기면 한 요청 때문에 여러 로그가 생성됩니다.

```text
repository: ERROR
service: ERROR
route: ERROR
global handler: ERROR
```

실제 장애는 하나인데 로그가 네 개 생겨 분석이 어려워질 수 있습니다.

로그 위치는 다음 기준으로 정할 수 있습니다.

```text
이 계층에서 새 문맥을 추가할 수 있는가?
여기서 오류를 최종적으로 처리하는가?
다시 상위로 던질 것인가?
```

예를 들어 최종 HTTP 오류 처리기에서 다음 정보를 함께 기록할 수 있습니다.

```text
requestId
actorId
route
업무 식별자
원본 cause
```

중간 계층에서는 오류를 변환하되 굳이 같은 stack을 다시 기록하지 않을 수 있습니다.

## 오류를 기록하지 않고 삼키는 것도 피합니다

다음은 더 위험합니다.

```ts
try {
  await repository.insert(board);
} catch {
  return null;
}
```

데이터베이스 장애와 "데이터 없음"이 같은 `null`로 바뀝니다.

```text
DB connection failure
→ null
→ service thinks "not found"
```

이러면 장애가 사용자 오류처럼 보입니다.

`null`이나 `undefined`는 **정상적으로 가능한 부재**를 표현할 때 사용하고, 시스템 실패는 오류로 구분합니다.

예:

```ts
findById(id): Promise<Board | null>
```

여기서:

```text
row 없음
→ null

DB 연결 실패
→ throw
```

두 경우의 의미가 다릅니다.

## 반환값과 예외의 경계를 정합니다

리포지터리 API를 설계할 때 "없음"과 "실패"를 구분해야 합니다.

예:

```ts
findById(id): Promise<Board | null>
```

의미:

```text
Board 존재
→ Board

Board 없음
→ null

조회 자체 실패
→ throw
```

조건부 업데이트도 비슷합니다.

```ts
updateTitleIfVersion(
  input
): Promise<Board | null>
```

여기서 `null`이 정확히 무엇을 뜻하는지 계약으로 정해야 합니다.

```text
version 불일치만 의미하는가?
리소스 없음도 포함하는가?
둘을 구분해야 하는가?
```

호출자가 서로 다른 실패를 구분해야 한다면 하나의 `null`에 여러 의미를 넣지 않는 편이 좋습니다.

예:

```ts
type UpdateResult =
  | { kind: "updated"; board: Board }
  | { kind: "not_found" }
  | { kind: "version_conflict" };
```

프로젝트 규모와 복잡도에 따라 단순한 `null` 또는 명시적인 union을 선택할 수 있습니다.

## 트랜잭션 안에서 발생한 업무 오류

트랜잭션 콜백 안에서 예상 가능한 업무 오류를 던져도 전체 트랜잭션을 롤백하게 만들 수 있습니다.

```ts
await unitOfWork.transaction(async (tx) => {
  const item =
    await tx.items.updateIfVersion(command);

  if (!item) {
    throw new ConflictError("stale_item");
  }

  await tx.events.append(
    createEvent(item)
  );
});
```

`ConflictError`가 발생하면:

```text
현재 transaction
→ rollback
→ ConflictError가 상위로 전달
```

HTTP 계층에서는 이를 409로 변환할 수 있습니다.

즉 롤백을 위해 반드시 시스템 오류를 던질 필요는 없습니다. 업무적으로 예상 가능한 실패도 트랜잭션 전체를 취소해야 할 수 있습니다.

## 트랜잭션 재시도는 무조건 안전하지 않습니다

일부 데이터베이스 격리 수준이나 deadlock 상황에서는 트랜잭션 전체를 재시도하는 전략을 사용할 수 있습니다.

하지만 트랜잭션 안에 외부 부수 효과가 있다면 단순 재시도가 위험합니다.

예:

```text
transaction 시작
→ 이메일 발송
→ DB commit에서 충돌
→ transaction 재시도
→ 이메일 다시 발송
```

외부 부수 효과가 두 번 발생할 수 있습니다.

따라서 재시도 가능한 트랜잭션 콜백은 가능하면 데이터베이스 내부 작업 중심으로 유지합니다.

## 메모리 리포지터리

서비스 단위 테스트에서는 실제 PostgreSQL 대신 메모리 구현을 사용할 수 있습니다.

예:

```ts
class MemoryBoardRepository
  implements BoardRepository {
  private readonly boards = new Map<string, Board>();

  async insert(board: Board): Promise<void> {
    this.boards.set(board.id, board);
  }

  // ...
}
```

장점은 다음과 같습니다.

```text
빠름
외부 DB가 필요 없음
원하는 상태를 쉽게 구성
실패 시나리오를 쉽게 주입
서비스의 업무 순서 테스트에 적합
```

예를 들어 다음을 빠르게 검사할 수 있습니다.

```text
중복 제목이면 ConflictError인가?
새 board에 지정한 clock 시간이 들어가는가?
ID generator가 사용되는가?
저장 후 올바른 Board를 반환하는가?
```

## 메모리 구현은 실제 데이터베이스와 같지 않습니다

메모리 자료구조가 PostgreSQL의 동작을 완전히 재현하지는 못합니다.

예를 들어 JavaScript의 `Map`은 다음 문제를 검증하지 못합니다.

- SQL 고유 제약
- 외래 키
- PostgreSQL 정렬 규칙
- collation
- `NULL` 비교와 정렬
- 트랜잭션 격리
- deadlock
- 실제 동시성 충돌
- SQL 타입 변환
- timestamp 정밀도
- numeric 표현
- 인덱스와 쿼리 실행 특성

따라서 메모리 테스트가 통과했다고 실제 데이터베이스 연동까지 맞다고 볼 수 없습니다.

## 실제 PostgreSQL 테스트가 필요한 이유

다음은 실제 데이터베이스에서 확인해야 합니다.

### 고유 제약

두 요청이 동시에 같은 값을 삽입했을 때 실제 DB가 어떻게 실패시키는지 확인합니다.

### 외래 키

존재하지 않는 부모 ID를 저장할 수 없는지 확인합니다.

### 트랜잭션 롤백

두 번째 쓰기가 실패했을 때 첫 번째 쓰기도 실제로 취소되는지 확인합니다.

### 조건부 UPDATE

`WHERE version = ?` 조건이 실제 경쟁 상황에서 기대대로 동작하는지 확인합니다.

### 정렬과 `NULL`

SQL의 정렬 결과와 메모리 정렬 결과가 다를 수 있습니다.

### 날짜와 숫자

데이터베이스 드라이버가 값을 JavaScript에서 어떤 타입으로 반환하는지 확인해야 합니다.

예를 들어 PostgreSQL의 큰 정수나 고정 소수점 숫자는 정확도 문제를 피하기 위해 문자열로 반환되는 설정이 있을 수 있습니다.

테스트는 실제 사용하는 드라이버와 설정을 기준으로 해야 합니다.

## 테스트 계층은 서로 다른 문제를 찾습니다

메모리 테스트와 실제 데이터베이스 테스트는 경쟁 관계가 아닙니다.

각각 찾는 문제가 다릅니다.

```text
service unit test
→ 업무 규칙과 호출 순서

repository integration test
→ SQL과 데이터베이스 동작

HTTP integration test
→ request/response 계약과 전체 연결
```

예:

```text
Memory repository
"중복이면 서비스가 ConflictError를 던지는가?"

PostgreSQL
"동시 insert에서 UNIQUE 제약이 실제로 하나를 막는가?"

HTTP
"ConflictError가 409와 올바른 오류 body가 되는가?"
```

세 테스트가 같은 기능을 다른 경계에서 검증합니다.

## 테스트용 리포지터리가 실제보다 더 느슨하면 생기는 문제

메모리 구현이 실제 저장소 제약을 무시하면 서비스 테스트가 지나치게 쉽게 통과할 수 있습니다.

예:

```ts
async insert(board: Board) {
  this.boards.set(board.id, board);
}
```

이 구현은 동일 owner/title 중복을 아무 제한 없이 허용할 수 있습니다.

실제 PostgreSQL에는:

```sql
UNIQUE (owner_id, title)
```

이 존재한다면 두 구현의 동작이 다릅니다.

메모리 구현이 모든 데이터베이스 세부 동작을 복제할 필요는 없지만, 서비스가 실제로 의존하는 repository 계약은 가능한 한 동일하게 유지해야 합니다.

그리고 DB 고유 동작은 실제 PostgreSQL 테스트로 따로 검증합니다.

## 의존성 방향

서비스는 가능한 한 Fastify, Kysely, PostgreSQL 드라이버 같은 구체 기술보다 자신에게 필요한 동작에 의존합니다.

예:

```ts
interface BoardRepository {
  insert(board: Board): Promise<void>;
}
```

서비스는 다음을 몰라도 됩니다.

```text
PostgreSQL인지
SQLite인지
메모리인지
Kysely를 쓰는지
직접 SQL을 쓰는지
```

실제 구현 연결은 애플리케이션 조립 지점에서 합니다.

```ts
const repository =
  new PostgresBoardRepository(db);

const service =
  new BoardService(
    repository,
    ids,
    clock
  );

const app = await buildApp({
  boardService: service
});
```

의존성 방향은 다음처럼 됩니다.

```text
HTTP
↓
service interface / application types
↓
repository abstraction
↑
PostgreSQL implementation
```

구체 구현이 서비스의 요구에 맞추는 구조입니다.

## 인터페이스를 기계적으로 만들 필요는 없습니다

"테스트할 수 있으려면 모든 클래스에 인터페이스가 필요하다"는 규칙은 없습니다.

다음과 같이 구현이 하나뿐이고 단순한 순수 함수라면 별도 인터페이스가 의미 없을 수 있습니다.

```ts
function normalizeTitle(
  title: string
): string {
  return title.trim();
}
```

반면 다음 값은 교체 가능성이나 외부 효과가 분명합니다.

```text
database repository
clock
ID generator
external API client
message publisher
```

이런 의존성은 테스트에서 대체할 이유가 명확합니다.

인터페이스의 기준은 "파일마다 하나"가 아니라 **호출자가 필요로 하는 계약이 독립적으로 의미가 있는가**입니다.

## 이름보다 책임이 중요합니다

프로젝트마다 다음 이름을 사용할 수 있습니다.

```text
service
use case
application service
repository
gateway
store
DAO
unit of work
```

이름 자체보다 다음 질문이 중요합니다.

```text
누가 HTTP를 아는가?
누가 업무 순서를 정하는가?
누가 SQL과 DB 오류를 아는가?
누가 트랜잭션 범위를 정하는가?
누가 오류를 HTTP 상태 코드로 바꾸는가?
```

각 질문에 답이 명확하면 코드 구조도 이해하기 쉬워집니다.

## 예제: 보드 이름 변경

전체 흐름을 하나로 연결해 봅니다.

### Route

```ts
app.patch(
  "/boards/:id/title",
  async (request, reply) => {
    const params =
      BoardParamsSchema.parse(
        request.params
      );

    const body =
      RenameBoardSchema.parse(
        request.body
      );

    const actor =
      requireActor(request);

    const board =
      await boardService.renameBoard({
        actorId: actor.id,
        boardId: params.id,
        title: body.title,
        baseVersion: body.baseVersion
      });

    return reply.send(
      toBoardDto(board)
    );
  }
);
```

라우트는 HTTP 값을 내부 command로 바꿉니다.

### Service

```ts
async renameBoard(
  command: RenameBoardCommand
): Promise<Board> {
  const board =
    await this.boards.findVisibleById(
      command.actorId,
      command.boardId
    );

  if (!board) {
    throw new NotFoundError(
      "board_not_found"
    );
  }

  const updated =
    await this.boards.updateTitleIfVersion({
      boardId: command.boardId,
      title: command.title,
      expectedVersion:
        command.baseVersion
    });

  if (!updated) {
    throw new ConflictError(
      "stale_board"
    );
  }

  return updated;
}
```

서비스는 리소스 가시성과 버전 충돌이라는 업무 의미를 처리합니다.

### Repository

```ts
async updateTitleIfVersion(
  input: RenameInput
): Promise<Board | null> {
  const row = await db
    .updateTable("boards")
    .set({
      title: input.title,
      version: sql`version + 1`
    })
    .where(
      "id",
      "=",
      input.boardId
    )
    .where(
      "version",
      "=",
      input.expectedVersion
    )
    .returningAll()
    .executeTakeFirst();

  return row
    ? toBoard(row)
    : null;
}
```

리포지터리는 조건부 SQL을 수행합니다.

### HTTP error handler

```ts
app.setErrorHandler(
  (error, request, reply) => {
    if (
      error instanceof NotFoundError
    ) {
      return reply.code(404).send({
        code: error.code,
        requestId: request.id
      });
    }

    if (
      error instanceof ConflictError
    ) {
      return reply.code(409).send({
        code: error.code,
        requestId: request.id
      });
    }

    request.log.error(
      { err: error },
      "unexpected request failure"
    );

    return reply.code(500).send({
      code: "internal_error",
      requestId: request.id
    });
  }
);
```

각 계층이 자기 수준의 의미만 처리합니다.

```text
route
HTTP 입력과 출력

service
업무 규칙

repository
조건부 DB 연산

error handler
업무 오류 → HTTP
```

## 흔한 실수

- 라우트가 SQL과 트랜잭션을 직접 관리합니다.
- 라우트가 업무 규칙까지 모두 처리해 같은 기능을 다른 진입점에서 재사용하기 어렵습니다.
- 서비스가 Fastify `request`나 `reply`에 직접 의존합니다.
- 서비스가 `new Date()`와 랜덤 ID를 직접 만들어 테스트가 비결정적입니다.
- 리포지터리가 HTTP 상태 코드나 응답 DTO를 반환합니다.
- 데이터베이스 행을 그대로 서비스 모델과 외부 DTO로 사용합니다.
- 모든 저장 동작을 의미 없는 `save(any)` 하나로 표현합니다.
- 사전 중복 조회만으로 동시 요청의 중복 삽입까지 막았다고 생각합니다.
- 데이터 무결성 규칙인데 데이터베이스 제약 조건이 없습니다.
- 확인 후 수정하는 사이의 TOCTOU 경쟁 조건을 고려하지 않습니다.
- 여러 쓰기가 함께 성공해야 하는데 별도 트랜잭션으로 실행합니다.
- 각 repository가 자기 트랜잭션만 시작해 여러 저장소 작업을 하나의 원자적 작업으로 묶지 못합니다.
- 반대로 모든 단일 쿼리까지 불필요하게 긴 트랜잭션으로 감쌉니다.
- 트랜잭션 안에서 외부 HTTP 호출을 오래 기다립니다.
- 모든 실패를 같은 일반 `Error`로 처리합니다.
- `null` 하나에 "없음", "충돌", "DB 장애"를 모두 담습니다.
- PostgreSQL 오류 코드를 HTTP 계층에서 직접 해석합니다.
- 원본 데이터베이스 오류를 클라이언트에 그대로 보냅니다.
- 오류를 모든 계층에서 반복해서 로그로 남깁니다.
- 반대로 시스템 오류를 `null`로 바꿔 조용히 삼킵니다.
- 메모리 테스트만으로 고유 제약, 외래 키, 트랜잭션과 동시성까지 검증했다고 판단합니다.
- 실제 PostgreSQL 테스트 없이 메모리 구현의 정렬·날짜·숫자 동작이 같다고 가정합니다.
- 구현이 단순한 모든 함수까지 기계적으로 인터페이스로 감쌉니다.

## 완료 기준

다음 질문에 답할 수 있으면 이 문서의 핵심을 이해한 것입니다.

- 라우트, 서비스와 리포지터리가 각각 어떤 결정을 하는지 설명할 수 있는가?
- 서비스가 Fastify의 `reply`나 HTTP 상태 코드를 몰라도 되는 이유를 설명할 수 있는가?
- 실제 저장소, 테스트 저장소, 시계와 ID 생성기가 어디에서 연결되는지 찾을 수 있는가?
- 리포지터리 함수 이름이 저장 조건과 결과 의미를 충분히 드러내는가?
- "먼저 조회하고 나중에 삽입"만으로 동시 중복을 막을 수 없는 이유를 설명할 수 있는가?
- 사전 검사와 데이터베이스 제약 조건의 역할 차이를 설명할 수 있는가?
- 조건부 UPDATE가 버전 경쟁을 어떻게 줄이는지 설명할 수 있는가?
- 함께 성공해야 하는 여러 쓰기를 하나의 트랜잭션으로 묶는가?
- 트랜잭션 범위를 어느 계층에서 결정하는 것이 자연스러운지 설명할 수 있는가?
- 트랜잭션 안에서 외부 네트워크 호출을 오래 기다리면 왜 문제가 되는지 설명할 수 있는가?
- 예상 가능한 업무 오류와 시스템 오류를 구분할 수 있는가?
- 데이터베이스 오류를 어느 계층에서 어떤 의미로 변환할지 설명할 수 있는가?
- 정상적인 "없음"과 저장소 자체의 실패를 같은 `null`로 처리하지 않는가?
- 같은 오류를 여러 계층에서 중복 로그로 남기지 않는가?
- 메모리 repository 테스트와 실제 PostgreSQL 테스트가 각각 어떤 문제를 찾는지 설명할 수 있는가?
- 인터페이스를 만드는 이유가 실제 의존성 계약 때문인지, 단순한 관례 때문인지 구분할 수 있는가?

## 연결 exercise

[`notes-api`](../../exercises/notes-api/README.md)는 요청 검증, 중복 제목 검사와 저장을 분리합니다. [`seat-reservation`](../../exercises/seat-reservation/README.md)은 실제 PostgreSQL 트랜잭션을 검사합니다.
