# 서비스, 리포지터리와 오류 처리

라우트 한곳에서 입력 검사, SQL, 권한 확인과 응답 생성을 모두 처리하면 작은 기능을 바꿔도 여러 코드가 함께 흔들립니다. 반대로 이름만 다른 파일을 많이 만들면 단순 전달 함수만 늘어납니다. 각 코드가 실제로 어떤 결정을 하는지 기준으로 나눕니다.

## 목표

- 라우트, 서비스와 리포지터리가 각각 처리할 일을 구분합니다.
- 저장소와 시계 같은 값을 생성 시점에 전달합니다.
- 예상 가능한 실패와 예상하지 못한 시스템 오류를 구분합니다.
- 함께 성공해야 하는 데이터베이스 쓰기를 하나의 트랜잭션으로 묶습니다.
- 메모리 구현과 실제 데이터베이스 테스트의 차이를 설명합니다.

## 라우트가 하는 일

```ts
app.post("/boards", async (request, reply) => {
  const input = CreateBoardSchema.parse(request.body);
  const actor = requireActor(request);
  const board = await service.createBoard({
    actorId: actor.id,
    title: input.title
  });
  return reply.code(201).send(toBoardDto(board));
});
```

라우트는 다음을 처리합니다.

- 경로·쿼리·헤더·본문 읽기와 검증
- 현재 사용자 읽기
- 서비스 함수 호출
- 결과를 상태 코드와 응답 DTO로 변환

라우트에서 직접 SQL을 실행하거나 여러 저장 작업의 순서를 정하지 않습니다.

## 서비스가 하는 일

```ts
class BoardService {
  constructor(
    private readonly boards: BoardRepository,
    private readonly ids: IdGenerator,
    private readonly clock: Clock
  ) {}

  async createBoard(command: CreateBoardCommand): Promise<Board> {
    const existing = await this.boards.findByOwnerAndTitle(
      command.actorId,
      command.title
    );
    if (existing) throw new ConflictError("board_title_exists");

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

서비스는 한 작업의 실행 순서와 업무 규칙을 정합니다. Fastify의 `reply`나 HTTP 상태 코드를 알 필요는 없습니다.

먼저 조회하고 나중에 삽입하는 사이에는 다른 요청이 끼어들 수 있습니다. 중복을 최종적으로 막아야 한다면 데이터베이스에도 고유 제약 조건을 둡니다.

## 리포지터리가 하는 일

```ts
interface BoardRepository {
  findVisibleById(actorId: string, boardId: string): Promise<Board | null>;
  insert(board: Board): Promise<void>;
  updateTitleIfVersion(input: RenameInput): Promise<Board | null>;
}
```

리포지터리는 애플리케이션이 필요한 저장 작업을 표현합니다. 모든 값을 받는 `save(any)`보다 “현재 버전일 때만 제목을 바꾼다”처럼 실제 조건을 드러내는 함수가 이해하기 쉽습니다.

리포지터리는 HTTP 응답을 만들지 않고, 데이터베이스 행을 그대로 외부 DTO로 취급하지 않습니다.

## 트랜잭션 범위

여러 쓰기가 함께 성공해야 한다면 하나의 데이터베이스 트랜잭션에서 실행합니다.

```ts
await unitOfWork.transaction(async (tx) => {
  const item = await tx.items.updateIfVersion(command);
  if (!item) throw new ConflictError("stale_item");
  await tx.events.append(createEvent(item));
});
```

항목 변경은 성공했지만 감사 기록은 실패하는 상태가 남지 않아야 합니다. 반대로 외부 HTTP 요청을 기다리는 동안 데이터베이스 잠금을 오래 유지하지 않습니다.

## 오류 종류

### 예상 가능한 실패

- 입력 형식 검사 이후의 업무 규칙 위반
- 리소스 없음
- 권한 부족
- 버전·고유성 충돌

이 오류에는 클라이언트가 사용할 안정적인 코드를 둘 수 있습니다.

### 시스템 오류

- 데이터베이스 연결 실패
- 쿼리 타임아웃
- 디스크·네트워크 오류

현재 요청에서 복구할 수 없다면 원인을 보존해 상위로 전달합니다. HTTP 처리 코드에서 일반적인 500으로 바꾸고 원본 SQL 오류를 외부에 보내지 않습니다.

## 오류를 바꾸는 위치

```text
PostgreSQL 고유 제약 위반
→ PostgreSQL 리포지터리가 중복 오류로 변환
→ 서비스가 업무 오류 코드 결정
→ HTTP 오류 처리기가 409 응답 생성
```

같은 오류를 모든 위치에서 반복해서 기록하면 중복 로그만 남습니다. 요청 정보나 업무 식별자를 추가할 수 있는 곳과 최종 요청 처리 지점 중 어디에서 기록할지 정합니다.

## 메모리 구현과 실제 데이터베이스

메모리 리포지터리는 서비스의 실행 순서를 빠르게 검사할 수 있습니다. 하지만 다음은 실제 PostgreSQL에서 확인해야 합니다.

- 고유성과 외래 키
- 정렬과 `NULL` 처리
- 트랜잭션 롤백
- 동시에 들어온 변경
- 데이터베이스 숫자와 날짜 표현

메모리 테스트와 실제 데이터베이스 테스트는 서로 다른 문제를 찾습니다.

## 의존성 방향

서비스는 Fastify나 Kysely의 구체 클래스보다 필요한 함수에 의존합니다. 실제 구현은 실행 파일이나 애플리케이션 생성 코드에서 연결합니다. 구현이 하나뿐이고 교체할 이유가 없는 단순 함수까지 기계적으로 인터페이스로 감쌀 필요는 없습니다.

## 흔한 실수

- 라우트가 SQL과 트랜잭션을 직접 관리합니다.
- 리포지터리가 HTTP 응답을 반환합니다.
- 모든 실패를 같은 `Error`로 처리합니다.
- 원본 데이터베이스 오류를 클라이언트에 보냅니다.
- 트랜잭션 안에서 외부 네트워크 호출을 기다립니다.
- 메모리 테스트만으로 데이터베이스 제약 조건까지 검증했다고 판단합니다.

## 완료 기준

- 라우트, 서비스와 리포지터리가 각각 어떤 결정을 하는지 설명합니다.
- 실제 저장소와 테스트 저장소를 연결하는 위치를 찾을 수 있습니다.
- 예상 가능한 오류와 시스템 오류를 구분합니다.
- 함께 성공해야 하는 쓰기를 하나의 트랜잭션으로 묶습니다.
- 메모리 테스트와 PostgreSQL 테스트의 차이를 설명합니다.

## 연결 exercise

[`notes-api`](../../exercises/notes-api/README.md)는 요청 검증, 중복 제목 검사와 저장을 분리합니다. [`seat-reservation`](../../exercises/seat-reservation/README.md)은 실제 PostgreSQL 트랜잭션을 검사합니다.
