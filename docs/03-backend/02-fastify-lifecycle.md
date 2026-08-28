# Fastify 애플리케이션 수명

Fastify 라우트를 등록하는 코드와 실제 포트를 여는 코드를 분리하면 테스트, 시작 시점 검사와 종료 처리를 같은 방식으로 사용할 수 있습니다. 데이터베이스 풀, 타이머와 소켓도 누가 만들고 닫는지 명확해야 합니다.

## 목표

- Fastify 애플리케이션 생성 함수와 실행 파일을 나눕니다.
- 플러그인이 적용되는 범위와 등록 순서를 이해합니다.
- 요청 처리 단계에 맞는 훅을 선택합니다.
- 저장소와 서비스 같은 의존성을 생성 시점에 전달합니다.
- 시작·준비 상태·종료를 검사합니다.

## 애플리케이션 생성 함수

```ts
export async function buildApp(deps: Dependencies) {
  const app = Fastify({ logger: deps.logger });
  await app.register(errorPlugin);
  await app.register(boardRoutes, { service: deps.boardService });
  return app;
}
```

이 함수는 포트를 열지 않습니다. 테스트에서는 독립적인 저장소를 전달하고 `app.inject`로 요청을 보냅니다.

```ts
const app = await buildApp(createTestDependencies());
const response = await app.inject({ method: "GET", url: "/boards" });
await app.close();
```

실제 실행 파일에서만 `listen`을 호출합니다.

```ts
const deps = await createProductionDependencies(env);
const app = await buildApp(deps);
await app.listen({ host: "0.0.0.0", port: env.PORT });
```

## 플러그인이 적용되는 범위

플러그인은 라우트, 데코레이터와 훅을 하나의 범위에 묶습니다.

```ts
await app.register(async function boardPlugin(scope) {
  scope.decorateRequest("actor", null);
  scope.addHook("preHandler", authenticate);
  await scope.register(boardRoutes, { prefix: "/boards" });
});
```

인증 훅을 모든 라우트에 전역으로 붙이면 로그인과 상태 확인 요청까지 막을 수 있습니다. 필요한 라우트 묶음에만 등록합니다.

## 요청 처리 단계

대표적인 순서는 다음과 같습니다.

```text
onRequest
→ preParsing
→ preValidation
→ preHandler
→ handler
→ preSerialization
→ onSend
→ onResponse
```

- 요청 ID와 기본 로그 정보: 앞쪽 단계
- 인증: 본문이 필요 없으면 `onRequest` 또는 `preHandler`
- 입력 검증: 스키마 검사 단계
- 권한 확인: 사용자와 경로 값이 준비된 `preHandler`
- 응답 시간 기록: 오류 경로까지 포함하는 `onResponse`

훅에서 응답을 보냈다면 이후 처리기가 실행되지 않도록 값을 반환합니다.

## 의존성 전달

```ts
type Dependencies = {
  boardService: BoardService;
  sessionService: SessionService;
  clock: Clock;
  ids: IdGenerator;
};
```

모듈 전역에서 저장소를 가져오지 않고 애플리케이션을 만들 때 전달합니다. 테스트마다 별도 저장소, 고정 시각과 ID 생성기를 사용할 수 있어 실행 순서에 따른 간섭이 줄어듭니다.

Fastify 데코레이터를 쓸 수 있지만 타입 선언과 플러그인 적용 범위를 함께 관리해야 합니다. 중요한 것은 필요한 값이 어디에서 만들어지는지 코드에서 확인할 수 있어야 한다는 점입니다.

## 시작 시점 검사

```ts
const env = EnvSchema.parse(process.env);
```

포트, 데이터베이스 URL, 쿠키 설정과 허용할 출처를 요청을 받기 전에 검사합니다. 마이그레이션을 서버 시작 때 자동 실행할지, 배포 단계에서 한 번만 실행할지도 정해야 합니다.

## liveness와 readiness

- liveness: 프로세스를 다시 시작해야 할 정도로 복구 불가능한가
- readiness: 지금 새 요청을 받을 준비가 되었는가

데이터베이스가 잠시 느리다고 liveness를 실패시키면 프로세스가 계속 재시작될 수 있습니다. readiness만 실패시켜 새 요청을 잠시 막는 방법을 사용할 수 있습니다.

## 오류 처리

예상 가능한 오류는 정해 둔 상태 코드와 본문으로 변환합니다. 분류하지 못한 오류는 요청 ID와 함께 로그에 남기고 일반적인 500을 반환합니다.

```ts
app.setErrorHandler((error, request, reply) => {
  if (error instanceof NotFoundError) {
    return reply.code(404).send(toErrorBody(error, request.id));
  }

  request.log.error({ err: error }, "요청 처리 중 예상하지 못한 오류가 발생했습니다.");
  return reply.code(500).send({
    code: "internal_error",
    message: "요청을 처리하지 못했습니다.",
    requestId: request.id
  });
});
```

## 종료 처리

`app.close()`는 서버를 닫고 `onClose` 훅을 실행합니다. 애플리케이션에서 만든 데이터베이스 풀, WebSocket 하트비트와 작업 큐도 종료 훅에서 정리합니다.

```ts
app.addHook("onClose", async () => {
  await db.destroy();
});
```

중복 시그널이 들어와도 종료 작업을 한 번만 실행하고, 무한히 기다리지 않도록 최대 종료 시간을 정합니다.

## 흔한 실수

- 모듈을 가져오는 즉시 포트를 엽니다.
- 테스트가 실제 포트와 전역 저장소를 공유합니다.
- 인증 훅을 공개 라우트까지 포함해 전역 등록합니다.
- 잘못된 환경 설정을 첫 요청에서 발견합니다.
- `app.close()` 뒤에도 풀, 타이머 또는 소켓이 남습니다.

## 완료 기준

- 애플리케이션 생성과 `listen` 호출을 서로 다른 파일에 둡니다.
- 플러그인과 훅이 적용되는 범위를 설명합니다.
- 저장소와 서비스가 생성되는 위치를 찾을 수 있습니다.
- liveness와 readiness의 차이를 설명합니다.
- 종료 후 서버와 함께 만든 자원이 모두 닫힙니다.

## 연결 exercise

[`notes-api`](../../exercises/notes-api/README.md)에서 포트를 열지 않는 Fastify 애플리케이션을 만들고 `app.inject`로 검사합니다.
