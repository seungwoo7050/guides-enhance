# Node.js, 패키지와 워크스페이스

웹 애플리케이션은 소스 파일만으로 실행되지 않습니다. Node.js 버전, `package.json`, 패키지 관리자, lockfile, TypeScript 설정, 환경 변수가 함께 실행 결과를 정합니다. 여러 앱과 공유 패키지를 한 저장소에 둘 때는 어느 패키지가 어떤 코드를 공개하는지도 분명해야 합니다.

## 목표

- 브라우저와 Node.js가 제공하는 API를 구분합니다.
- 의존성, 개발 의존성, 스크립트, lockfile의 역할을 설명합니다.
- ESM과 TypeScript 모듈 해석을 이해합니다.
- 워크스페이스 패키지를 공개 진입점으로 연결합니다.
- 애플리케이션 생성과 실제 실행을 분리합니다.
- 시작할 때 설정을 검사하고 종료할 때 자원을 닫습니다.

## 브라우저와 Node.js

| 기능 | 브라우저 | Node.js |
|---|---|---|
| 문서와 현재 주소 | `document`, `location` | 기본 제공하지 않음 |
| 파일과 프로세스 | 제한적 | `node:fs`, `process` |
| HTTP 요청 | `fetch` | `fetch` |
| TCP 서버 | 제공하지 않음 | `node:net`, 서버 프레임워크 |
| 환경 변수 | 빌드 설정에 따라 공개될 수 있음 | `process.env` |

서버 비밀값이 브라우저 번들에 들어가면 사용자가 볼 수 있습니다. 파일마다 실제 실행 위치를 확인합니다.

## `package.json`

```json
{
  "name": "@board/api",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/server.ts",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "build": "tsc -p tsconfig.build.json"
  },
  "dependencies": {
    "fastify": "^5.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0"
  }
}
```

실행 코드가 가져오는 패키지는 `dependencies`에 둡니다. 빌드와 테스트에만 쓰는 도구는 `devDependencies`에 둡니다.

스크립트는 개발자와 CI가 같은 명령을 실행하도록 합니다. 개발 서버, 타입 검사, 테스트, 빌드, 운영 실행을 구분합니다.

## lockfile

패키지 버전 범위는 설치할 수 있는 범위를, lockfile은 실제로 선택한 버전을 기록합니다.

```sh
pnpm install --frozen-lockfile
```

CI에서는 lockfile이 예상치 않게 바뀌면 실패하게 합니다. lockfile을 삭제하고 다시 설치한 결과는 이전 검증 환경과 같다고 볼 수 없습니다.

## ESM과 상대 경로

`"type": "module"`인 Node.js 패키지는 ESM 규칙을 사용합니다. `NodeNext`로 TypeScript를 컴파일한다면 생성될 JavaScript 파일을 기준으로 `.js` 확장자를 적을 수 있습니다.

```ts
import { parseBoard } from "./board.js";
```

번들러가 처리하는 경로와 Node.js가 직접 실행할 때 처리하는 경로가 다를 수 있으므로 실제 실행 방식과 TypeScript 설정을 함께 봅니다.

## 워크스페이스

```yaml
packages:
  - apps/*
  - packages/*
```

내부 패키지는 `workspace:*`로 연결합니다.

```json
{
  "dependencies": {
    "@board/contracts": "workspace:*"
  }
}
```

공개 파일은 `exports`로 제한합니다.

```json
{
  "name": "@board/contracts",
  "type": "module",
  "exports": {
    ".": "./src/index.ts"
  }
}
```

소비 코드가 `@board/contracts/src/internal/ws.ts`처럼 내부 파일을 직접 가져오면 디렉터리 변경이 공개 API 변경이 됩니다.

## 라이브러리와 실행 파일

공유 모듈을 가져오는 것만으로 서버를 열거나 타이머를 시작하지 않습니다.

```ts
export function buildApp(dependencies: Dependencies) {
  return fastify().register(routes, { dependencies });
}
```

실제 포트는 실행 파일에서 엽니다.

```ts
const app = buildApp(createProductionDependencies());
await app.listen({ host: "0.0.0.0", port: env.PORT });
```

이렇게 하면 테스트에서 포트를 열지 않고 `app.inject()`를 사용할 수 있습니다.

## 시작 시 설정 검사

포트, 데이터베이스 URL, 허용할 Origin 같은 값은 요청을 받기 전에 검사합니다.

```ts
const env = EnvSchema.parse(process.env);
```

설정이 잘못되었는데 임의의 기본값으로 계속 실행해 첫 요청에서 500을 만들지 않습니다.

프로세스가 살아 있는지 확인하는 liveness와 새 요청을 처리할 준비가 되었는지 확인하는 readiness는 목적이 다릅니다.

## 정상 종료

```ts
let closing = false;

async function shutdown(signal: string) {
  if (closing) return;
  closing = true;
  app.log.info({ signal }, "shutdown started");
  await app.close();
  await db.destroy();
}
```

새 요청 수락을 멈추고 서버, 데이터베이스 풀, WebSocket, 타이머, 작업 큐를 닫습니다. 테스트도 같은 종료 함수를 호출해야 합니다.

## 흔한 실수

- 브라우저 API와 Node.js API를 같은 파일에서 항상 사용할 수 있다고 생각합니다.
- 실제 실행 의존성을 `devDependencies`에 둡니다.
- lockfile 없이 설치 결과를 재현할 수 있다고 생각합니다.
- 워크스페이스 패키지의 내부 파일을 직접 가져옵니다.
- 모듈을 가져오는 순간 서버나 타이머를 시작합니다.
- 첫 요청이 들어온 뒤 환경 변수를 검사합니다.
- 서버만 닫고 풀·소켓·타이머를 남깁니다.

## 관련 exercise

[`runtime-workspace`](../../exercises/runtime-workspace/README.md)는 앱과 라이브러리를 별도 패키지로 두고 공개 진입점, 포트 검사, 이벤트 루프 순서를 확인합니다.

## 완료 기준

- 브라우저와 Node.js의 실행 위치와 API 차이를 설명할 수 있습니다.
- 의존성, 스크립트, lockfile의 역할을 구분합니다.
- 내부 패키지를 `workspace:*`와 `exports`로 연결합니다.
- 애플리케이션 생성과 실제 `listen()` 호출을 분리합니다.
- 프로세스 시작과 종료 시 확인하고 닫아야 할 자원을 설명할 수 있습니다.
