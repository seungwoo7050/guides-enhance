# Fastify 애플리케이션 수명

Fastify 애플리케이션은 단순히 라우트를 등록하고 `listen()`을 호출하는 코드가 아닙니다. 애플리케이션을 **구성하는 단계**, 플러그인과 훅이 **부팅되는 단계**, 실제 요청을 **처리하는 단계**, 프로세스를 **종료하며 자원을 정리하는 단계**가 서로 연결되어 있습니다.

라우트를 등록하는 코드와 실제 포트를 여는 코드를 분리하면 같은 애플리케이션 구성을 테스트와 실제 서버 실행에서 재사용할 수 있습니다. 데이터베이스 풀, 타이머, 작업 큐, WebSocket 같은 외부 자원도 누가 만들고 언제 닫는지 명확하게 정해야 합니다.

## 목표

- Fastify 애플리케이션 생성 함수와 실제 실행 파일을 나눕니다.
- 플러그인의 캡슐화 범위와 등록 순서가 무엇에 영향을 주는지 이해합니다.
- 요청 처리 단계와 각 훅이 실행되는 시점을 구분합니다.
- 저장소와 서비스 같은 의존성을 애플리케이션 생성 시점에 전달합니다.
- 시작 시점의 설정 오류를 요청을 받기 전에 발견합니다.
- liveness와 readiness의 목적을 구분합니다.
- 정상 종료 시 서버와 함께 사용한 자원을 정리합니다.

## 애플리케이션 생성과 실행을 분리합니다

애플리케이션 생성 함수는 Fastify 인스턴스를 만들고 플러그인과 라우트를 구성하지만 포트는 열지 않습니다.

```ts
export async function buildApp(deps: Dependencies) {
  const app = Fastify({
    logger: deps.logger
  });

  await app.register(errorPlugin);
  await app.register(boardRoutes, {
    service: deps.boardService
  });

  return app;
}
```

이 함수의 책임은 다음과 같습니다.

```text
Fastify 인스턴스 생성
→ 공통 플러그인 등록
→ 라우트 등록
→ 필요한 의존성 연결
→ 구성된 app 반환
```

반대로 다음 작업은 실제 실행 파일의 책임으로 둡니다.

```text
환경 변수 읽기
→ 운영용 의존성 생성
→ 애플리케이션 생성
→ 포트 열기
→ 종료 시그널 처리
```

예:

```ts
const env = EnvSchema.parse(process.env);
const deps = await createProductionDependencies(env);
const app = await buildApp(deps);

await app.listen({
  host: "0.0.0.0",
  port: env.PORT
});
```

이렇게 나누면 애플리케이션 모듈을 import하는 것만으로 실제 네트워크 포트가 열리지 않습니다.

## 테스트에서는 실제 포트를 열 필요가 없습니다

Fastify의 `app.inject()`는 실제 TCP 포트를 열지 않고 애플리케이션에 HTTP 요청을 주입합니다.

```ts
const app = await buildApp(createTestDependencies());

const response = await app.inject({
  method: "GET",
  url: "/boards"
});

expect(response.statusCode).toBe(200);

await app.close();
```

`inject()`를 실행하면 등록된 플러그인이 부팅되어 요청을 처리할 준비가 된 뒤 테스트 요청이 실행됩니다.

따라서 테스트에서 다음과 같은 준비를 할 필요가 없습니다.

```text
임의의 테스트 포트 찾기
실제 서버 listen
HTTP 클라이언트로 localhost 접속
테스트 종료 후 포트 해제 대기
```

이 구조의 핵심은 **같은 `buildApp()`을 테스트와 실제 실행에서 사용한다는 것**입니다.

```text
production
createProductionDependencies()
        ↓
     buildApp()
        ↓
      listen()

test
createTestDependencies()
        ↓
     buildApp()
        ↓
      inject()
```

## Fastify 플러그인은 캡슐화 범위를 만듭니다

Fastify의 `register()`는 기본적으로 새로운 **캡슐화 컨텍스트(encapsulation context)**를 만듭니다.

플러그인 안에서 등록한 다음 요소는 해당 컨텍스트와 그 자식 컨텍스트에 적용됩니다.

```text
routes
hooks
decorators
error handlers
```

예:

```ts
await app.register(async function boardPlugin(scope) {
  scope.decorateRequest("actor", null);

  scope.addHook("preHandler", authenticate);

  await scope.register(boardRoutes, {
    prefix: "/boards"
  });
});
```

구조를 그리면 다음과 같습니다.

```text
app
└─ boardPlugin
   ├─ decorateRequest("actor")
   ├─ preHandler(authenticate)
   └─ boardRoutes
      ├─ GET /boards/...
      └─ POST /boards/...
```

`boardRoutes`는 `boardPlugin`의 자식이므로 `actor` 데코레이터와 `authenticate` 훅의 영향을 받습니다.

## 캡슐화는 부모에서 자식 방향으로 상속됩니다

Fastify 플러그인 범위에서 가장 중요한 규칙은 다음과 같습니다.

```text
부모에 등록한 기능
→ 자식에서 사용 가능

자식에 등록한 기능
→ 부모에서는 기본적으로 보이지 않음

한 자식에 등록한 기능
→ 다른 형제 플러그인에서는 기본적으로 보이지 않음
```

예를 들어 다음 구조를 봅니다.

```text
root
├─ pluginA
│  └─ routeA
└─ pluginB
   └─ routeB
```

`pluginA` 내부의 데코레이터나 훅은 기본적으로 `pluginB`에 전달되지 않습니다.

따라서 다음 두 등록은 서로 형제 범위입니다.

```ts
app.register(authPlugin);
app.register(boardRoutes);
```

`authPlugin` 안에서 만든 데코레이터가 캡슐화되어 있다면 `boardRoutes`가 자동으로 그 값을 사용할 수 있다고 가정해서는 안 됩니다.

공통 기능을 어디까지 공유할 것인지에 따라 플러그인 구조를 정해야 합니다.

## 인증 훅의 범위를 의도적으로 제한합니다

인증이 필요한 API와 공개 API가 함께 있다고 가정합니다.

```text
GET /health
POST /login
GET /boards
POST /boards
```

루트 범위에 인증 훅을 붙이면 모든 하위 라우트에 영향을 줄 수 있습니다.

```ts
app.addHook("preHandler", authenticate);
```

이 경우 `/health`와 `/login`도 인증 대상으로 포함될 수 있습니다.

인증이 필요한 라우트만 하나의 플러그인 범위로 묶는 방법이 더 명확할 수 있습니다.

```ts
app.get("/health", healthHandler);
app.post("/login", loginHandler);

app.register(async function authenticatedRoutes(scope) {
  scope.addHook("preHandler", authenticate);

  await scope.register(boardRoutes, {
    prefix: "/boards"
  });
});
```

이제 구조는 다음과 같습니다.

```text
root
├─ GET /health
├─ POST /login
└─ authenticatedRoutes
   └─ preHandler(authenticate)
      └─ /boards/*
```

플러그인 캡슐화는 단순한 코드 정리 기능이 아니라 **훅과 데코레이터가 적용되는 경계를 만드는 기능**입니다.

## 플러그인 등록 순서와 의존 관계

플러그인이 다른 플러그인이 제공하는 기능을 필요로 한다면 등록 순서와 캡슐화 범위를 함께 고려해야 합니다.

개념적으로 다음 관계가 있다고 가정합니다.

```text
database plugin
      ↓
board routes
```

board 라우트가 `db` 데코레이터에 의존한다면 해당 데코레이터가 board 라우트의 컨텍스트에서 보이는 구조여야 합니다.

단순히 소스 코드에서 먼저 적혀 있다는 사실만 확인해서는 충분하지 않습니다.

```text
1. 필요한 플러그인이 먼저 부팅되는가?
2. 그 플러그인이 만든 값이 현재 캡슐화 범위에서 보이는가?
```

두 조건을 모두 확인해야 합니다.

Fastify에서 여러 플러그인이 서로 강하게 의존하기 시작하면 등록 순서를 암묵적으로 기억하기보다 의존 관계가 코드 구조에서 드러나도록 구성하는 편이 좋습니다.

## `register()`와 애플리케이션 부팅

플러그인을 등록하는 것은 애플리케이션 구성 과정입니다.

Fastify는 `ready()`, `listen()`, `inject()` 같은 동작이 수행될 때 등록된 플러그인을 부팅해 사용할 준비를 합니다.

```ts
app.register(pluginA);
app.register(pluginB);

await app.ready();
```

테스트에서는 `inject()`가 준비 과정을 수행하므로 일반적인 요청 테스트에서 별도로 `ready()`를 먼저 호출할 필요는 없습니다.

```ts
const response = await app.inject({
  method: "GET",
  url: "/boards"
});
```

반면 라우트가 실제 요청을 받기 전에 애플리케이션의 부팅 자체가 성공하는지만 검사하고 싶다면 `ready()`를 명시적으로 사용할 수 있습니다.

```ts
const app = await buildApp(deps);

await app.ready();

// 플러그인 부팅 성공

await app.close();
```

## 요청 처리 수명 주기

정상적인 HTTP 요청의 주요 처리 흐름은 다음과 같습니다.

```text
Incoming Request
→ Routing
→ onRequest
→ preParsing
→ Body Parsing
→ preValidation
→ Validation
→ preHandler
→ Handler
→ preSerialization
→ onSend
→ Outgoing Response
→ onResponse
```

원문에서 훅 이름만 외우는 것보다 **각 단계에서 어떤 데이터가 준비되어 있는지** 이해하는 것이 중요합니다.

## `onRequest`

요청 처리 초기에 실행됩니다.

```ts
app.addHook("onRequest", async (request, reply) => {
  // 요청 초기에 필요한 처리
});
```

이 시점에는 요청 본문이 아직 파싱되지 않았습니다.

따라서 다음과 같이 `request.body`에 의존하는 처리를 `onRequest`에 두면 안 됩니다.

```ts
app.addHook("onRequest", async (request) => {
  // request.body는 아직 준비되지 않음
});
```

본문이 필요 없는 인증 토큰 검사, 요청 추적 정보 설정처럼 요청 초기에 수행할 작업에 사용할 수 있습니다.

## `preParsing`

본문 파싱 직전에 실행됩니다.

```text
onRequest
→ preParsing
→ body parsing
```

일반적인 애플리케이션에서는 직접 사용할 일이 많지 않지만, 원시 요청 스트림을 본문 파서에 전달하기 전에 처리해야 할 경우 사용할 수 있습니다.

## 본문 파싱

`Content-Type`에 맞는 파서가 요청 본문을 해석합니다.

예를 들어 JSON 요청은 파싱된 뒤 `request.body`로 사용할 수 있습니다.

```http
POST /boards
Content-Type: application/json

{
  "title": "Fastify"
}
```

파싱 이후:

```ts
request.body
```

에는 JSON에서 해석된 값이 들어갑니다.

본문이 필요한 로직은 이 단계 이후의 훅을 사용해야 합니다.

## `preValidation`

본문 파싱 이후, 스키마 검증 전에 실행됩니다.

```text
body parsing
→ preValidation
→ validation
```

따라서 파싱된 `body`, `params`, `query` 등을 사용할 수 있습니다.

요청 데이터를 검증 전에 정규화하거나 보조 값을 준비해야 하는 특수한 경우에 사용할 수 있습니다.

다만 일반적인 입력 형식 검사는 직접 훅에 반복해서 작성하기보다 Fastify의 요청 스키마 검증을 활용하는 편이 좋습니다.

## Validation

라우트에 요청 스키마가 지정되어 있다면 Fastify가 입력을 검증합니다.

예:

```ts
app.post("/boards", {
  schema: {
    body: {
      type: "object",
      required: ["title"],
      properties: {
        title: { type: "string", minLength: 1 }
      }
    }
  }
}, handler);
```

잘못된 입력을 handler 안까지 가져간 뒤 수동으로 검사하는 것보다 요청 경계에서 형식을 검증하면 이후 업무 코드가 기대하는 입력 형태가 더 명확해집니다.

스키마 검증은 **형식 검증**에 적합합니다.

```text
title이 문자열인가?
필수 값이 존재하는가?
값이 허용 범위인가?
```

반면 다음은 업무 규칙입니다.

```text
현재 사용자가 board를 수정할 수 있는가?
이미 같은 이름의 board가 존재하는가?
현재 상태에서 삭제가 허용되는가?
```

이런 규칙은 서비스나 업무 계층에서 처리하는 편이 좋습니다.

## `preHandler`

스키마 검증을 통과한 뒤 실제 handler 직전에 실행됩니다.

```text
validation
→ preHandler
→ handler
```

이 시점에는 일반적으로 다음 값들이 준비되어 있습니다.

```text
request.params
request.query
request.body
인증 훅에서 만든 사용자 정보
```

따라서 권한 검사처럼 실제 handler 실행 직전에 필요한 작업에 적합합니다.

```ts
app.addHook("preHandler", async (request, reply) => {
  await authorize(request.actor, request.params);
});
```

인증도 `preHandler`에 둘 수 있습니다. 다만 요청 본문이 필요 없는 인증을 가능한 앞 단계에서 거부하고 싶다면 `onRequest`를 선택할 수도 있습니다.

훅 선택은 단순한 관례가 아니라 **그 로직이 어떤 데이터에 의존하는지**를 기준으로 결정합니다.

## Handler

라우트의 실제 요청 처리를 수행합니다.

```ts
app.get("/boards/:id", async (request, reply) => {
  return boardService.getBoard(request.params.id);
});
```

handler는 가능한 한 HTTP 세부 구현보다 애플리케이션 서비스 호출에 집중하도록 구성합니다.

```text
HTTP 입력 해석
→ 인증/권한 확인
→ service 호출
→ HTTP 응답 변환
```

업무 규칙 전체를 handler에 직접 넣으면 테스트와 재사용이 어려워집니다.

## `preSerialization`

handler가 반환한 payload를 직렬화하기 전에 실행됩니다.

```text
handler
→ preSerialization
→ serialization
```

응답 객체를 직렬화 직전에 변환해야 할 때 사용할 수 있습니다.

예를 들어 공통 응답 구조를 추가하는 방식이 가능하지만, 모든 응답을 무조건 훅에서 변형하면 API 계약을 추적하기 어려워질 수 있으므로 적용 범위를 명확하게 관리해야 합니다.

## `onSend`

직렬화된 응답을 클라이언트에 보내기 직전에 실행됩니다.

```text
serialization
→ onSend
→ outgoing response
```

응답 헤더를 추가하거나 전송 직전 처리에 사용할 수 있습니다.

## `onResponse`

응답 전송이 완료된 뒤 실행됩니다.

```text
outgoing response
→ onResponse
```

클라이언트에 보낼 응답을 수정하는 단계가 아니라, 요청 처리가 끝난 사실을 기록하는 단계로 이해하는 편이 좋습니다.

예:

```text
요청 처리 시간 기록
메트릭 기록
완료 로그
```

응답 시간을 측정한다면 성공 handler 내부에만 기록하는 것보다 요청 완료 단계에서 공통 처리하는 편이 실패 요청도 함께 관찰하기 쉽습니다.

## 오류 경로는 정상 경로와 다를 수 있습니다

앞의 흐름은 정상적인 성공 경로를 단순화한 것입니다.

```text
onRequest
→ ...
→ handler
→ ...
→ onResponse
```

중간 훅이나 handler에서 오류가 발생하면 정상적인 다음 단계로 그대로 진행하지 않고 Fastify의 오류 처리 경로로 이동합니다.

```text
hook 또는 handler에서 오류 발생
→ onError
→ setErrorHandler
→ 오류 응답
```

따라서 모든 요청이 반드시 `handler`와 `preSerialization`을 지나간다고 가정해서는 안 됩니다.

다만 응답이 완료되면 `onResponse`를 완료 관찰 지점으로 사용할 수 있습니다.

## 훅에서 요청 처리를 조기에 끝낼 때

인증 실패처럼 handler까지 진행하지 않고 바로 응답해야 하는 경우가 있습니다.

```ts
app.addHook("preHandler", async (request, reply) => {
  if (!request.user) {
    return reply.code(401).send({
      code: "unauthorized"
    });
  }
});
```

특히 `async` 훅에서 `reply.send()`로 응답을 끝낸다면 `return reply`처럼 반환하여 Fastify에 해당 비동기 훅의 처리가 끝났음을 명확히 전달하는 방식이 안전합니다.

다음 두 스타일을 섞지 않습니다.

```text
callback 스타일
done() 사용

async 스타일
Promise/async 반환
```

`async` 함수에서 동시에 `done()`까지 호출하면 훅이나 handler가 중복 실행되는 등 예상하지 못한 동작이 생길 수 있습니다.

## 훅은 목적과 필요한 데이터에 맞게 고릅니다

대표적인 선택 기준은 다음과 같습니다.

| 목적 | 일반적으로 고려할 단계 | 이유 |
|---|---|---|
| 요청 ID·초기 로그 정보 | `onRequest` | 요청 처리 초기에 필요함 |
| 헤더 기반 인증 | `onRequest` 또는 `preHandler` | 본문이 필요하지 않음 |
| 파싱된 입력의 사전 가공 | `preValidation` | 본문 파싱 후, 스키마 검증 전 |
| 입력 형식 확인 | route schema validation | 요청 경계에서 일관되게 검사 |
| 권한 확인 | `preHandler` | 인증 정보와 경로·본문 값이 준비됨 |
| 응답 직전 헤더 처리 | `onSend` | 전송 직전 응답에 접근 가능 |
| 요청 완료 시간·메트릭 | `onResponse` | 응답이 끝난 뒤 기록 가능 |

무조건 특정 기능은 특정 훅이라고 외우기보다 다음 질문을 먼저 합니다.

```text
이 로직은 request.body가 필요한가?
스키마 검증 전이어야 하는가?
handler보다 먼저 실패해야 하는가?
응답을 수정해야 하는가?
응답 완료 뒤 관찰만 하면 되는가?
```

## 의존성을 애플리케이션 생성 시점에 전달합니다

서비스나 저장소를 모듈 전역에서 직접 가져오는 대신 애플리케이션 생성 시점에 전달할 수 있습니다.

```ts
type Dependencies = {
  boardService: BoardService;
  sessionService: SessionService;
  clock: Clock;
  ids: IdGenerator;
};
```

운영 환경에서는 실제 구현을 전달합니다.

```ts
const deps: Dependencies = {
  boardService: productionBoardService,
  sessionService: productionSessionService,
  clock: systemClock,
  ids: randomIdGenerator
};

const app = await buildApp(deps);
```

테스트에서는 제어 가능한 구현을 전달합니다.

```ts
const deps: Dependencies = {
  boardService: fakeBoardService,
  sessionService: fakeSessionService,
  clock: fixedClock,
  ids: sequentialIdGenerator
};
```

이렇게 하면 테스트마다 독립적인 상태를 구성할 수 있습니다.

## 전역 의존성이 테스트를 방해하는 이유

다음과 같이 모듈을 import하는 순간 전역 저장소가 만들어진다고 가정합니다.

```ts
export const db = createDatabasePool();
```

여러 테스트가 같은 모듈을 사용하면 다음과 같은 문제가 생길 수 있습니다.

```text
테스트 A가 데이터 생성
        ↓
같은 전역 저장소
        ↑
테스트 B 결과에 영향
```

테스트 실행 순서나 병렬 실행 여부에 따라 결과가 달라질 수 있습니다.

반대로 테스트마다 의존성을 새로 만들면 상태를 분리하기 쉽습니다.

```text
test A → repository A

test B → repository B
```

고정 시각과 고정 ID 생성기도 같은 이유로 유용합니다.

```ts
const clock = {
  now: () => new Date("2026-01-01T00:00:00Z")
};
```

시간과 난수에 의존하는 테스트를 재현 가능하게 만들 수 있습니다.

## Fastify 데코레이터와 생성자 주입은 역할이 다릅니다

Fastify 데코레이터를 사용해 의존성을 Fastify 인스턴스나 request에 연결할 수도 있습니다.

```ts
app.decorate("boardService", deps.boardService);
```

하지만 데코레이터를 사용할 때는 다음 두 가지를 함께 관리해야 합니다.

```text
Fastify 캡슐화 범위
TypeScript 타입 선언
```

특정 라우트가 어떤 값을 사용할 수 있는지 플러그인 계층을 통해 판단해야 하기 때문입니다.

중요한 것은 특정 패턴 자체가 아니라 다음 질문에 코드만 보고 답할 수 있어야 한다는 점입니다.

```text
이 서비스는 어디에서 만들어지는가?
어떤 범위에서 사용할 수 있는가?
테스트에서는 무엇으로 교체되는가?
누가 이 자원을 종료하는가?
```

## 자원의 소유권을 정합니다

데이터베이스 풀이나 작업 큐처럼 명시적으로 닫아야 하는 자원은 **누가 생성했는지**와 **누가 닫는지**를 함께 정해야 합니다.

예를 들어 애플리케이션 플러그인이 데이터베이스 풀을 직접 만든다면 같은 플러그인이 종료 훅에서 정리하는 구조가 자연스럽습니다.

```ts
app.register(async function databasePlugin(scope) {
  const db = await createDatabasePool();

  scope.decorate("db", db);

  scope.addHook("onClose", async () => {
    await db.destroy();
  });
});
```

개념적으로 다음 규칙을 유지합니다.

```text
create resource
      ↓
define owner
      ↓
close resource at owner shutdown
```

생성 위치와 종료 위치가 서로 멀리 떨어지면 누락과 중복 종료가 생기기 쉽습니다.

## 시작 시점에 환경 설정을 검사합니다

환경 변수는 첫 요청이 들어온 뒤 읽기보다 프로세스 시작 단계에서 한 번 검증하는 편이 좋습니다.

```ts
const env = EnvSchema.parse(process.env);
```

예를 들어 다음 값을 시작 전에 확인합니다.

```text
PORT
DATABASE_URL
COOKIE_SECRET
허용할 CORS origin
외부 API endpoint
필수 기능 플래그
```

잘못된 설정으로 서버가 포트만 연 상태가 되면 다음과 같은 문제가 생깁니다.

```text
배포 성공으로 보임
→ 트래픽 유입
→ 첫 요청에서 설정 오류 발견
→ 사용자 요청 실패
```

대신 가능한 오류를 시작 단계에서 발견합니다.

```text
프로세스 시작
→ 환경 설정 검증
→ 의존성 생성
→ Fastify 부팅
→ 준비 완료
→ 트래픽 수신
```

## `ready()`와 `listen()`의 역할

`ready()`는 등록된 플러그인을 부팅하고 애플리케이션이 준비될 수 있는지 확인할 때 사용할 수 있습니다.

```ts
await app.ready();
```

`listen()`은 준비 과정을 거친 뒤 실제 네트워크 포트를 열어 요청을 받습니다.

```ts
await app.listen({
  host: "0.0.0.0",
  port: 3000
});
```

테스트의 `inject()`도 애플리케이션이 준비된 뒤 요청을 처리합니다.

즉 세 동작의 목적은 다릅니다.

```text
ready()
부팅 성공 여부 확인

inject()
포트 없이 테스트 요청 실행

listen()
실제 네트워크 요청 수신 시작
```

## 마이그레이션 실행 위치도 정해야 합니다

데이터베이스 마이그레이션을 서버 프로세스가 시작될 때 자동 실행할 수도 있고, 배포 과정에서 별도 작업으로 실행할 수도 있습니다.

두 방법 모두 가능하지만 의미는 다릅니다.

서버 시작마다 마이그레이션하면 여러 인스턴스가 동시에 시작할 때 같은 마이그레이션을 시도할 가능성을 고려해야 합니다.

```text
instance A ─┐
instance B ─┼→ migration
instance C ─┘
```

배포 단계에서 한 번만 실행한다면 애플리케이션 시작 과정은 단순해지지만 배포 파이프라인이 마이그레이션 성공 여부를 책임져야 합니다.

따라서 단순히 "시작할 때 실행한다"보다 다음 정책을 명확히 정합니다.

```text
누가 실행하는가?
여러 인스턴스에서 동시에 실행될 수 있는가?
실패하면 배포를 어떻게 중단하는가?
애플리케이션 버전과 스키마 버전의 호환 범위는 무엇인가?
```

## liveness와 readiness

상태 확인 endpoint는 모두 같은 의미가 아닙니다.

### liveness

liveness는 보통 **이 프로세스를 계속 살려 둘 수 있는가**를 판단하는 신호입니다.

실패하면 오케스트레이터가 프로세스를 재시작하는 정책과 연결될 수 있습니다.

따라서 일시적인 외부 의존성 문제까지 liveness 실패로 만들면 불필요한 재시작이 반복될 수 있습니다.

```text
DB가 잠시 느림
→ liveness 실패
→ 프로세스 재시작
→ DB는 여전히 느림
→ 다시 liveness 실패
→ 재시작 반복
```

프로세스를 다시 시작한다고 해결되지 않는 문제라면 liveness에 넣는 것이 적절한지 검토해야 합니다.

### readiness

readiness는 **현재 이 인스턴스가 새 요청을 받을 준비가 되었는가**를 나타냅니다.

예를 들어 필수 데이터베이스 연결을 사용할 수 없어 정상적인 업무 요청을 처리할 수 없다면 readiness를 실패시켜 트래픽 대상에서 일시적으로 제외할 수 있습니다.

```text
프로세스는 살아 있음
데이터베이스 일시 장애
        ↓
liveness = success
readiness = failure
```

데이터베이스가 복구되면 프로세스를 재시작하지 않고 다시 readiness 성공 상태로 돌아갈 수 있습니다.

## readiness에 모든 외부 서비스를 넣는 것도 주의합니다

readiness는 애플리케이션이 실제 요청을 처리할 수 있는지 판단하는 신호이므로 **필수 의존성**을 중심으로 설계해야 합니다.

부가 기능 하나가 잠시 실패했다고 애플리케이션 전체를 트래픽에서 제거할 필요가 없는 경우도 있습니다.

예:

```text
핵심 DB: 없으면 대부분의 API 처리 불가
→ readiness와 연결할 수 있음

선택적 분석 시스템: 없어도 핵심 API 처리 가능
→ 전체 readiness 실패로 만들 필요가 없을 수 있음
```

liveness와 readiness는 단순히 `/health`라는 endpoint 하나를 만드는 문제가 아니라 장애 시 시스템이 어떤 행동을 하게 할지 결정하는 정책입니다.

## 오류 처리

예상 가능한 업무 오류는 정해 둔 HTTP 상태 코드와 오류 본문으로 변환합니다.

```ts
app.setErrorHandler((error, request, reply) => {
  if (error instanceof NotFoundError) {
    return reply
      .code(404)
      .send(toErrorBody(error, request.id));
  }

  request.log.error(
    { err: error },
    "요청 처리 중 예상하지 못한 오류가 발생했습니다."
  );

  return reply.code(500).send({
    code: "internal_error",
    message: "요청을 처리하지 못했습니다.",
    requestId: request.id
  });
});
```

여기서는 두 종류의 오류를 구분합니다.

```text
예상 가능한 오류
NotFoundError
ConflictError
ValidationError
PermissionError
→ 외부 계약에 맞는 상태 코드와 오류 코드

예상하지 못한 오류
프로그램 버그
처리하지 못한 내부 예외
→ 내부 로그에 상세 원인 기록
→ 외부에는 일반적인 500 응답
```

스택 트레이스, SQL 문장, 비밀 값 같은 내부 정보를 그대로 외부 응답에 넣지 않습니다.

## 오류 처리기도 캡슐화됩니다

Fastify의 error handler도 플러그인 범위의 영향을 받습니다.

따라서 특정 플러그인 내부에서 `setErrorHandler()`를 등록하면 그 플러그인 컨텍스트에 속한 요청에 적용되는 오류 처리기를 만들 수 있습니다.

애플리케이션 전체에서 동일한 오류 계약을 사용하려는 경우에는 error handler의 등록 범위가 모든 대상 라우트를 포함하는지 확인해야 합니다.

이 역시 다음 원칙과 같습니다.

```text
훅
데코레이터
오류 처리기

모두 "어디에 등록했는가?"가 중요함
```

## 종료 처리

정상 종료는 단순히 프로세스에 `process.exit()`를 호출하는 것이 아닙니다.

종료 시에는 일반적으로 다음 순서를 고려합니다.

```text
새 요청 수락 중단
→ 진행 중인 요청 마무리
→ 장시간 연결 정리
→ 데이터베이스·큐 등 자원 정리
→ 프로세스 종료
```

Fastify에서는 `app.close()`가 서버 종료 수명 주기를 시작합니다.

```ts
await app.close();
```

`close()`가 호출되면 Fastify는 서버를 closing 상태로 전환하고 HTTP 서버를 닫은 뒤 종료 훅을 실행합니다.

## `preClose`와 `onClose`의 차이

Fastify에는 종료 단계에서 목적이 다른 훅이 있습니다.

### `preClose`

HTTP 서버가 완전히 닫히기 전에 처리해야 하는 자원에 적합합니다.

대표적으로 서버 종료 자체를 방해할 수 있는 장시간 연결이 있습니다.

```text
WebSocket
Server-Sent Events
기타 upgrade된 연결
```

예:

```ts
app.addHook("preClose", async () => {
  for (const socket of activeWebSockets) {
    socket.close();
  }
});
```

이런 연결을 그대로 두면 HTTP 서버 종료가 완료되지 않을 수 있으므로 먼저 정리해야 할 수 있습니다.

### `onClose`

HTTP 서버가 더 이상 새 요청을 받지 않고 진행 중이던 HTTP 요청이 끝난 뒤 일반 애플리케이션 자원을 해제하는 데 적합합니다.

```ts
app.addHook("onClose", async () => {
  await db.destroy();
});
```

대표적인 대상은 다음과 같습니다.

```text
데이터베이스 풀
외부 클라이언트
작업 큐 연결
애플리케이션이 만든 타이머
기타 명시적으로 닫아야 하는 자원
```

따라서 단순히 "모든 종료 작업은 onClose"라고 외우기보다 종료 전에 끊어야 서버가 닫히는 연결인지, 서버가 닫힌 뒤 해제할 일반 자원인지 구분합니다.

## 종료 훅도 플러그인 소유권과 함께 둡니다

플러그인이 자원을 만들었다면 같은 플러그인이 종료 훅도 등록하는 구조가 이해하기 쉽습니다.

```ts
async function queuePlugin(app: FastifyInstance) {
  const queue = await connectQueue();

  app.decorate("queue", queue);

  app.addHook("onClose", async () => {
    await queue.close();
  });
}
```

이렇게 하면 다음 관계가 한곳에서 보입니다.

```text
queue 생성
→ Fastify에 등록
→ 종료 시 queue 정리
```

자원 생성 코드는 한 모듈에 있고 종료 코드는 전혀 다른 실행 파일에 흩어져 있으면 어떤 자원이 아직 남아 있는지 추적하기 어렵습니다.

## 종료 시그널은 한 번만 처리합니다

운영 환경에서는 일반적으로 `SIGTERM`이나 `SIGINT`를 받아 정상 종료를 시작합니다.

개념적인 코드는 다음과 같습니다.

```ts
let closing = false;

async function shutdown() {
  if (closing) {
    return;
  }

  closing = true;

  try {
    await app.close();
  } finally {
    // 필요한 최종 종료 처리
  }
}
```

중복 시그널이 들어왔을 때 같은 데이터베이스 풀이나 큐를 여러 번 닫지 않도록 종료 작업을 한 번만 시작하는 것이 좋습니다.

## 종료가 무한히 기다리지 않도록 정책을 정합니다

진행 중인 요청이나 외부 자원 종료가 영원히 끝나지 않을 가능성도 고려해야 합니다.

예:

```text
종료 시그널
→ app.close()
→ 특정 요청이 끝나지 않음
→ 프로세스가 계속 종료되지 않음
```

운영 환경에서는 정상 종료를 기다릴 최대 시간과 그 시간을 넘겼을 때의 처리 정책을 정합니다.

중요한 것은 무조건 즉시 프로세스를 강제 종료하는 것도, 무한정 기다리는 것도 아니라 **서비스 특성에 맞는 종료 정책을 명시하는 것**입니다.

## 전체 수명 주기

애플리케이션 전체 흐름을 하나로 연결하면 다음과 같습니다.

```text
프로세스 시작
    ↓
환경 설정 검증
    ↓
운영 의존성 생성
    ↓
buildApp()
    ↓
플러그인·라우트 등록
    ↓
Fastify 부팅
    ↓
listen()
    ↓
readiness 성공
    ↓
요청 처리
    ↓
종료 시그널
    ↓
readiness 실패 / 새 트래픽 중단
    ↓
app.close()
    ↓
preClose
    ↓
진행 중 HTTP 요청 마무리
    ↓
onClose
    ↓
외부 자원 정리
    ↓
프로세스 종료
```

테스트에서는 같은 구성 중 네트워크 실행 부분만 달라집니다.

```text
테스트 의존성 생성
    ↓
buildApp()
    ↓
app.inject()
    ↓
응답 검증
    ↓
app.close()
```

이 구조가 있으면 실제 서버 실행 방식과 테스트 방식이 서로 다른 애플리케이션을 만들지 않습니다.

## 흔한 실수

- 애플리케이션 모듈을 import하는 즉시 `listen()`을 호출합니다.
- 테스트가 실제 TCP 포트와 전역 데이터베이스를 공유합니다.
- 테스트마다 `app.close()`를 호출하지 않아 자원이 남습니다.
- 플러그인 하나의 데코레이터가 부모나 형제 플러그인에서도 자동으로 보인다고 가정합니다.
- 플러그인 등록 순서만 확인하고 캡슐화 범위를 확인하지 않습니다.
- 인증 훅을 루트에 등록해 `/login`, `/health` 같은 공개 라우트까지 막습니다.
- `onRequest`에서 아직 파싱되지 않은 `request.body`를 사용하려 합니다.
- 스키마 형식 검증과 업무 규칙 검증을 구분하지 않습니다.
- `async` 훅에서 Promise 방식과 `done()` callback 방식을 함께 사용합니다.
- 예상 가능한 업무 오류와 예상하지 못한 내부 오류를 모두 같은 500으로 반환합니다.
- 잘못된 환경 설정을 첫 사용자 요청에서 발견합니다.
- 일시적인 데이터베이스 장애를 무조건 liveness 실패로 만들어 재시작 루프를 일으킵니다.
- 중요하지 않은 외부 서비스 장애까지 readiness 실패로 만들어 전체 트래픽을 차단합니다.
- 자원을 만든 코드와 닫는 코드의 소유자가 명확하지 않습니다.
- `app.close()` 뒤에도 데이터베이스 풀, 타이머, 큐 또는 소켓이 남습니다.
- WebSocket처럼 서버 종료를 방해할 수 있는 연결을 `preClose` 전에 정리하지 않습니다.
- 중복 종료 시그널마다 종료 로직을 다시 실행합니다.
- 정상 종료가 끝나지 않을 때의 최대 대기 정책이 없습니다.

## 완료 기준

다음 질문에 답할 수 있으면 이 문서의 핵심을 이해한 것입니다.

- `buildApp()`이 직접 `listen()`하지 않는 이유를 설명할 수 있는가?
- 실제 실행과 테스트가 같은 애플리케이션 생성 함수를 사용하는가?
- `app.inject()`가 실제 네트워크 포트 없이 무엇을 검사하는지 설명할 수 있는가?
- 부모 플러그인, 자식 플러그인, 형제 플러그인 사이에서 데코레이터와 훅이 어떻게 보이는지 설명할 수 있는가?
- 플러그인 등록 순서와 캡슐화 범위를 함께 확인하는 이유를 설명할 수 있는가?
- `onRequest`, `preValidation`, `preHandler`, `onSend`, `onResponse`가 각각 어느 시점에 실행되는지 설명할 수 있는가?
- `onRequest`에서 `request.body`를 사용할 수 없는 이유를 설명할 수 있는가?
- 요청 스키마 검증과 업무 규칙 검증을 구분할 수 있는가?
- 서비스와 저장소가 어디에서 생성되고 테스트에서는 무엇으로 교체되는지 찾을 수 있는가?
- 환경 설정 오류를 요청을 받기 전에 발견하는가?
- liveness와 readiness 실패가 운영 환경에서 서로 다른 행동을 유도하는 이유를 설명할 수 있는가?
- `preClose`와 `onClose`에 각각 어떤 자원을 정리해야 하는지 설명할 수 있는가?
- `app.close()` 뒤 서버와 함께 만든 자원이 모두 닫히는가?
- 종료 로직이 중복 실행되거나 무한정 기다리는 상황을 처리하는 정책이 있는가?

## 연결 exercise

[`notes-api`](../../exercises/notes-api/README.md)에서 포트를 열지 않는 Fastify 애플리케이션을 만들고 `app.inject`로 검사합니다.
