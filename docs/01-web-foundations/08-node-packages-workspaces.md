# Node.js, 패키지와 워크스페이스

웹 애플리케이션은 소스 파일만으로 실행되지 않습니다. 같은 코드라도 어떤 Node.js 버전에서 실행하는지, 어떤 패키지 버전이 설치되었는지, 어떤 TypeScript 설정으로 컴파일하는지, 어떤 환경 변수가 주어졌는지에 따라 결과가 달라질 수 있습니다.

따라서 실제 실행 환경은 다음 요소를 함께 봐야 합니다.

```text
소스 코드
+ Node.js 버전
+ package.json
+ 패키지 관리자
+ lockfile
+ TypeScript 설정
+ 환경 변수
+ 실행 명령
```

여러 앱과 공유 패키지를 한 저장소에 두는 워크스페이스에서는 여기에 한 가지 문제가 더 생깁니다.

```text
어느 패키지가
어떤 코드를
어떤 이름으로
다른 패키지에 공개하는가?
```

이 경계를 분명하게 만들면 내부 구현을 바꿔도 소비 코드가 덜 깨지고, 테스트와 운영 실행도 분리하기 쉬워집니다.

## 목표

- 브라우저와 Node.js가 제공하는 런타임 API를 구분합니다.
- `package.json`의 의존성, 개발 의존성, 스크립트, `type`의 역할을 설명합니다.
- 버전 범위와 lockfile이 서로 다른 역할을 가진다는 점을 설명합니다.
- ESM과 TypeScript의 Node 계열 모듈 해석에서 파일 확장자가 왜 중요할 수 있는지 이해합니다.
- 워크스페이스 패키지를 `workspace:*`와 공개 진입점으로 연결합니다.
- 내부 파일 경로와 공개 API를 구분합니다.
- 애플리케이션 생성과 실제 서버 실행을 분리합니다.
- 프로세스 시작 시 설정을 검증합니다.
- 종료 시 서버, 데이터베이스, 소켓, 타이머 같은 자원을 정리합니다.
- liveness와 readiness의 목적 차이를 설명합니다.

## 먼저 구분할 것: 실행 위치

같은 TypeScript나 JavaScript 파일이라도 **브라우저에서 실행되는지 Node.js에서 실행되는지**에 따라 사용할 수 있는 API가 다릅니다.

예를 들어 브라우저에는 DOM이 있습니다.

```js
document.querySelector("#app");
location.href;
```

Node.js에는 기본적으로 DOM이나 브라우저 주소창이 없습니다.

반대로 Node.js에는 파일 시스템과 프로세스 API가 있습니다.

```js
import { readFile } from "node:fs/promises";

console.log(process.env.NODE_ENV);
```

브라우저에서는 일반 웹 페이지 코드가 임의의 서버 파일 시스템을 `node:fs`처럼 직접 읽을 수 없습니다.

## 브라우저와 Node.js

| 기능 | 브라우저 | Node.js |
|---|---|---|
| 문서 DOM | `document` | 기본 제공하지 않음 |
| 현재 페이지 주소 | `location` | 브라우저 의미의 `location` 없음 |
| 파일 시스템 | 일반 페이지에서 직접 접근하지 않음 | `node:fs` |
| 프로세스 정보 | 없음 | `process` |
| 환경 변수 | 직접적인 `process.env` 없음 | `process.env` |
| HTTP 요청 | `fetch` | `fetch` |
| TCP 서버 | 제공하지 않음 | `node:net`, 서버 프레임워크 |
| 타이머 | `setTimeout`, `setInterval` | `setTimeout`, `setInterval` |

같은 이름의 API가 양쪽에 존재하더라도 세부 동작과 주변 환경이 완전히 같다고 가정하지 않습니다.

예를 들어 `fetch`는 브라우저와 Node.js 모두에서 사용할 수 있지만:

- 브라우저에는 CORS 같은 브라우저 보안 정책이 적용될 수 있습니다.
- Node.js 서버 코드에는 브라우저의 페이지 Origin 개념이 같은 방식으로 적용되지 않습니다.

따라서 "이 API가 존재하는가?"뿐 아니라 **어느 런타임에서 어떤 규칙으로 실행되는가**를 봐야 합니다.

## 서버 전용 값과 브라우저 공개 값

다음 환경 변수는 서버 전용 비밀값이라고 가정합니다.

```text
DATABASE_URL=...
API_SECRET=...
```

이런 값을 브라우저 번들에 포함하면 사용자가 개발자 도구나 내려받은 JavaScript 파일에서 볼 수 있습니다.

```text
서버 환경 변수
→ 서버 프로세스만 사용해야 함

브라우저 번들에 포함된 값
→ 사용자에게 공개된 값으로 간주
```

따라서 프런트엔드 빌드 도구가 특정 접두사의 환경 변수를 브라우저 코드에 주입하는 기능을 제공한다면, 그 값은 비밀값으로 취급하지 않습니다.

파일을 볼 때는 다음 질문을 먼저 합니다.

```text
이 파일은 브라우저에서 실행되는가?
Node.js에서 실행되는가?
빌드 시점에만 실행되는가?
```

## Node.js 버전도 실행 환경의 일부입니다

Node.js 버전이 달라지면 사용할 수 있는 내장 API, ESM 동작, 테스트 도구 호환성 등이 달라질 수 있습니다.

따라서 프로젝트에서는 사용 Node.js 버전을 명확히 정하는 편이 좋습니다.

방법은 도구에 따라 다를 수 있습니다.

예:

```text
.nvmrc
.node-version
package.json의 engines
CI 설정
컨테이너 이미지
```

중요한 것은 특정 파일 형식 하나가 아니라 **개발자 환경과 CI가 같은 버전 범위를 사용하도록 만드는 것**입니다.

예를 들어 `package.json`에 다음을 둘 수 있습니다.

```json
{
  "engines": {
    "node": ">=22"
  }
}
```

다만 `engines`가 실제 설치를 강제하는지는 패키지 관리자와 설정에 따라 다를 수 있습니다. 따라서 CI나 버전 관리자 설정과 함께 사용합니다.

## `package.json`

Node.js 패키지의 주요 메타데이터와 실행 규칙은 `package.json`에 들어갑니다.

예:

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

각 항목을 따로 봅니다.

## `name`

```json
{
  "name": "@board/api"
}
```

패키지 이름입니다.

워크스페이스에서는 다른 내부 패키지가 이 이름으로 의존성을 선언하고 import할 수 있습니다.

예:

```ts
import { BoardSchema } from "@board/contracts";
```

## `private`

```json
{
  "private": true
}
```

일반적으로 이 패키지가 실수로 공개 레지스트리에 publish되는 것을 막는 데 사용합니다.

애플리케이션 패키지나 저장소 루트처럼 외부 배포용 패키지가 아니라면 `private: true`를 두는 경우가 많습니다.

이 값은 코드 접근 제어 기능이 아닙니다. 런타임에서 모듈을 숨기거나 권한을 제한하는 기능과는 다릅니다.

## `type`

```json
{
  "type": "module"
}
```

Node.js가 해당 패키지 범위의 `.js` 파일을 어떤 모듈 체계로 해석할지 결정하는 데 영향을 줍니다.

`"type": "module"`이면 일반 `.js` 파일을 ESM으로 해석합니다.

```js
import { readFile } from "node:fs/promises";
```

CommonJS와 ESM은 import/export 방식과 파일 해석 규칙이 다르므로 프로젝트의 실제 실행 방식과 TypeScript 설정을 함께 맞춰야 합니다.

## `scripts`

`scripts`는 개발자와 CI가 같은 명령을 실행할 수 있도록 이름을 붙인 명령 모음입니다.

```json
{
  "scripts": {
    "dev": "tsx watch src/server.ts",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "build": "tsc -p tsconfig.build.json"
  }
}
```

실행 예:

```sh
pnpm dev
pnpm typecheck
pnpm test
pnpm build
```

스크립트를 두는 이유는 단순히 명령을 짧게 줄이기 위해서만이 아닙니다.

```text
로컬 개발자
CI
배포 파이프라인
```

이 모두가 같은 명령 이름을 사용할 수 있습니다.

예를 들어 CI에서:

```sh
pnpm typecheck
pnpm test
pnpm build
```

를 실행하면 로컬에서도 같은 명령으로 검증할 수 있습니다.

## 개발 실행, 빌드, 운영 실행을 구분합니다

다음 명령들은 목적이 다릅니다.

```text
dev
→ 코드 변경을 감지하면서 개발용 실행

typecheck
→ TypeScript 타입 오류 검사

test
→ 자동 테스트 실행

build
→ 배포 가능한 산출물 생성

start
→ 빌드된 운영 코드 실행
```

예를 들어 운영 환경에서 `tsx watch` 같은 개발용 감시 프로세스를 그대로 실행하는 것과 빌드된 JavaScript를 실행하는 것은 다른 운영 모델입니다.

가능하면 스크립트 이름만 보고도 목적을 알 수 있게 합니다.

## `dependencies`

런타임 코드에서 실제로 import하여 사용하는 패키지는 일반적으로 `dependencies`에 둡니다.

```json
{
  "dependencies": {
    "fastify": "^5.0.0"
  }
}
```

예:

```ts
import Fastify from "fastify";
```

운영 환경에서 이 코드가 실행된다면 `fastify`는 런타임에 필요합니다.

## `devDependencies`

빌드, 타입 검사, 테스트, 포맷팅처럼 개발 과정에서만 필요한 도구는 일반적으로 `devDependencies`에 둡니다.

```json
{
  "devDependencies": {
    "typescript": "^5.0.0",
    "vitest": "^3.0.0"
  }
}
```

예를 들어 TypeScript 코드를 미리 JavaScript로 빌드한 뒤 운영에서는 결과물만 실행한다면 TypeScript 컴파일러 자체는 런타임에 필요하지 않을 수 있습니다.

## 의존성 위치는 실제 실행 모델에 따라 판단합니다

다음 기준이 중요합니다.

```text
운영 시 실행되는 코드가 직접 필요로 하는가?
→ dependencies

빌드·테스트·개발 도구로만 사용하는가?
→ devDependencies
```

단, 실제 배포 방식에 따라 차이가 있습니다.

예를 들어 운영 컨테이너에서 TypeScript 소스를 직접 `tsx`로 실행한다면 `tsx`도 운영 실행에 필요합니다.

따라서 이름만 보고 기계적으로 분류하지 않고 **실제 운영 명령이 무엇을 필요로 하는지** 확인합니다.

## 직접 의존성은 직접 선언합니다

패키지 A가 `fastify`를 import한다면, 우연히 다른 패키지 B가 `fastify`를 설치해 주고 있다고 해서 A가 그 의존성에 기대지 않는 편이 좋습니다.

```text
A가 직접 import하는 패키지
→ A의 package.json에 직접 선언
```

워크스페이스나 패키지 관리자가 의존성을 위쪽에 배치해 실제 파일이 보일 수 있어도, 그것이 패키지의 명시적 계약은 아닙니다.

직접 사용하는 의존성을 직접 선언하면 패키지를 따로 설치하거나 구조를 바꿨을 때도 의미가 명확합니다.

## 버전 범위

다음 선언은:

```json
{
  "dependencies": {
    "fastify": "^5.0.0"
  }
}
```

정확히 한 버전만을 의미하지 않습니다.

`^5.0.0`은 패키지 관리자가 허용 범위 안에서 설치 가능한 버전을 선택할 수 있는 버전 범위입니다.

즉:

```text
package.json
→ 설치 가능한 버전 범위
```

를 설명합니다.

## lockfile

lockfile은 실제 설치에서 선택된 패키지 버전과 의존성 해석 결과를 기록합니다.

패키지 관리자에 따라 파일 이름은 다릅니다.

예:

```text
pnpm-lock.yaml
package-lock.json
yarn.lock
```

개념은 다음과 같습니다.

```text
package.json
→ "이 범위의 버전을 허용한다"

lockfile
→ "현재 프로젝트에서는 이 버전 조합을 사용한다"
```

예를 들어:

```json
{
  "dependencies": {
    "fastify": "^5.0.0"
  }
}
```

만으로는 시간이 지난 뒤 새로 설치할 때 같은 세부 버전이 선택된다고 보장하기 어렵습니다.

lockfile을 저장소에 함께 커밋하면 팀과 CI가 같은 의존성 그래프를 재현하기 쉬워집니다.

## lockfile은 패키지 전체 그래프를 기록합니다

직접 설치한 패키지만 버전이 있는 것은 아닙니다.

예를 들어:

```text
애플리케이션
  ↓
패키지 A
  ↓
패키지 B
```

처럼 간접 의존성이 있을 수 있습니다.

lockfile은 이런 간접 의존성까지 포함한 설치 해석 결과를 기록합니다.

따라서 단순히 `package.json`의 직접 의존성 버전만 같다고 해서 전체 실행 환경이 반드시 같지는 않습니다.

## CI에서는 lockfile 변경을 막을 수 있습니다

pnpm을 예로 들면:

```sh
pnpm install --frozen-lockfile
```

같은 방식으로 lockfile과 `package.json`이 맞지 않을 때 설치 중 lockfile을 자동 수정하지 않고 실패하게 할 수 있습니다.

이 방식의 목적은 다음과 같습니다.

```text
CI가 자기 판단으로 새 의존성 조합을 만들지 않게 함
```

즉 개발자가 검토하고 커밋한 lockfile을 기준으로 설치하도록 합니다.

실제 옵션 이름과 기본 동작은 사용하는 패키지 관리자와 버전에 맞게 확인해야 합니다.

## lockfile을 함부로 삭제하지 않습니다

문제가 생겼다고 lockfile을 삭제하고 다시 설치하면 의존성 그래프가 크게 달라질 수 있습니다.

```text
기존 lockfile
→ 이미 테스트한 버전 조합

삭제 후 새 설치
→ 현재 버전 범위에서 다시 선택한 조합
```

따라서 lockfile 삭제는 단순한 캐시 삭제와 같은 작업이 아닙니다.

의존성을 의도적으로 갱신하려는 경우라면 변경된 lockfile을 검토하고 테스트합니다.

## 패키지 관리자도 프로젝트 계약의 일부입니다

같은 저장소에서 npm, pnpm, Yarn을 섞어 사용하면 설치 방식과 lockfile이 달라질 수 있습니다.

프로젝트에서 사용할 패키지 관리자를 하나 정하고 버전까지 명시할 수 있습니다.

예:

```json
{
  "packageManager": "pnpm@10.0.0"
}
```

이 필드는 프로젝트가 어떤 패키지 관리자와 버전을 기대하는지 표현하는 데 사용할 수 있습니다.

실제 실행 환경에서 이 정보를 어떻게 사용하고 강제하는지는 Corepack이나 CI 설정 등 도구 구성에 따라 달라질 수 있습니다.

## ESM

ESM(ECMAScript Modules)은 JavaScript의 표준 모듈 시스템입니다.

내보내는 파일:

```ts
// board.ts
export function parseBoard() {
  // ...
}
```

가져오는 파일:

```ts
// app.ts
import { parseBoard } from "./board.js";
```

TypeScript 소스 파일은 `.ts`인데 import 경로에는 `.js`가 등장할 수 있습니다.

이 부분은 Node.js ESM과 TypeScript를 처음 사용할 때 혼동하기 쉽습니다.

## 왜 `.js`를 적을 수 있는가

Node.js가 최종적으로 실행하는 것은 보통 빌드 결과 JavaScript입니다.

예를 들어 소스가:

```text
src/app.ts
src/board.ts
```

이고 빌드 결과가:

```text
dist/app.js
dist/board.js
```

라면 최종 JavaScript의 import는 다음 파일을 가리켜야 합니다.

```js
import { parseBoard } from "./board.js";
```

TypeScript가 Node 계열 ESM 해석을 따르는 설정에서는 소스 코드에서도 **최종 실행될 JavaScript 파일 경로를 기준으로** `.js` 확장자를 작성하는 패턴을 사용할 수 있습니다.

```ts
import { parseBoard } from "./board.js";
```

컴파일러는 이것이 소스의 `board.ts`에 대응한다는 것을 해석할 수 있습니다.

## NodeNext

TypeScript에서 Node.js의 현대적인 ESM/CommonJS 해석 규칙을 따르려면 `NodeNext` 계열 설정을 사용할 수 있습니다.

예:

```json
{
  "compilerOptions": {
    "module": "NodeNext",
    "moduleResolution": "NodeNext"
  }
}
```

이 설정에서는 다음 요소가 함께 중요해집니다.

- 가장 가까운 `package.json`의 `"type"`
- 파일 확장자
- import 경로
- 패키지 `exports`

즉 단순히 `module: "ESNext"`라고 쓰는 것과 "Node.js가 실제로 이 파일을 어떻게 실행하는가"는 별개의 문제일 수 있습니다.

## 번들러와 Node 직접 실행은 경로 규칙이 다를 수 있습니다

프런트엔드 번들러는 다음과 같은 import를 편리하게 처리할 수 있습니다.

```ts
import { parseBoard } from "./board";
```

번들러가 확장자를 추론하거나 자체 모듈 해석을 수행할 수 있기 때문입니다.

하지만 Node.js가 빌드된 ESM 파일을 직접 실행한다면 명시적인 확장자가 필요할 수 있습니다.

따라서 import 문제를 볼 때는 다음을 함께 확인합니다.

```text
1. 누가 최종 모듈을 해석하는가?
   - Node.js?
   - 번들러?

2. TypeScript module/moduleResolution 설정은 무엇인가?

3. package.json의 type은 무엇인가?

4. 빌드 결과 파일 확장자는 무엇인가?
```

## 경로 별칭도 실행 환경까지 연결해야 합니다

TypeScript에서 다음과 같은 별칭을 설정할 수 있습니다.

```json
{
  "compilerOptions": {
    "paths": {
      "@app/*": ["src/*"]
    }
  }
}
```

하지만 TypeScript가 타입 검사 중 별칭을 이해한다고 해서 Node.js가 빌드 결과 실행 시 자동으로 같은 별칭을 이해하는 것은 아닙니다.

```text
TypeScript 경로 해석
≠
Node.js 런타임 경로 해석
```

번들러, 별도 로더, 패키지 `exports` 등 실제 실행 환경이 같은 경로를 해석할 수 있어야 합니다.

따라서 워크스페이스 내부 공유 코드에는 임의의 소스 별칭보다 **실제 패키지 이름과 공개 진입점**을 사용하는 구조가 더 명확할 수 있습니다.

## 워크스페이스

워크스페이스는 여러 패키지를 하나의 저장소에서 함께 관리하는 구조입니다.

예:

```text
repo/
├─ apps/
│  ├─ web/
│  └─ api/
├─ packages/
│  └─ contracts/
├─ package.json
└─ pnpm-workspace.yaml
```

pnpm에서는 예를 들어 다음처럼 패키지 위치를 선언할 수 있습니다.

```yaml
packages:
  - apps/*
  - packages/*
```

이제 `apps/api`, `apps/web`, `packages/contracts`를 별도의 패키지로 관리하면서 한 저장소 안에서 연결할 수 있습니다.

## 각 패키지는 독립된 `package.json`을 가집니다

예:

```text
apps/api/package.json
apps/web/package.json
packages/contracts/package.json
```

각 패키지는 자신의 이름, 의존성, 스크립트, 공개 API를 정의할 수 있습니다.

```json
{
  "name": "@board/contracts",
  "private": true,
  "type": "module"
}
```

이렇게 하면 저장소 전체가 하나의 거대한 암묵적 모듈 공간이 아니라, **패키지 경계가 있는 여러 모듈의 집합**이 됩니다.

## `workspace:*`

내부 패키지에 의존한다는 사실을 명시할 수 있습니다.

예를 들어 API 패키지가 계약 패키지를 사용한다면:

```json
{
  "dependencies": {
    "@board/contracts": "workspace:*"
  }
}
```

이 선언의 의미는 대략 다음과 같습니다.

```text
@board/contracts라는 의존성은
현재 워크스페이스 안의 패키지를 사용한다.
```

따라서 소비 코드에서는 실제 패키지 이름을 import합니다.

```ts
import {
  BoardSchema,
} from "@board/contracts";
```

## 상대 경로로 다른 패키지 내부를 넘나들지 않습니다

다음처럼 앱에서 다른 패키지 소스 디렉터리 깊숙이 접근하면 경계가 무너집니다.

```ts
import {
  BoardSchema,
} from "../../../packages/contracts/src/board.js";
```

이 코드는 저장소 디렉터리 구조에 직접 의존합니다.

대신 패키지 의존성과 공개 API를 사용합니다.

```ts
import {
  BoardSchema,
} from "@board/contracts";
```

이제 소비자는 `contracts` 패키지 내부의 파일 배치보다 공개 API만 알면 됩니다.

## 공개 진입점

패키지에서 다른 패키지가 사용할 공개 코드를 한 곳에 모을 수 있습니다.

예:

```ts
// packages/contracts/src/index.ts
export {
  BoardSchema,
} from "./board.js";

export type {
  BoardDto,
} from "./board.js";
```

소비 코드는 다음처럼 가져옵니다.

```ts
import {
  BoardSchema,
} from "@board/contracts";
```

이 구조에서 `src/index.ts`는 소스 수준의 공개 진입점 역할을 합니다.

실제 배포 방식에 따라 `exports`는 소스가 아니라 빌드 결과를 가리킬 수도 있습니다.

## `exports`

`package.json`의 `exports`는 패키지 소비자가 접근할 수 있는 공개 진입점을 명시하는 데 사용할 수 있습니다.

예:

```json
{
  "name": "@board/contracts",
  "type": "module",
  "exports": {
    ".": "./dist/index.js"
  }
}
```

이 경우 소비자는 다음 공개 경로를 사용합니다.

```ts
import {
  BoardSchema,
} from "@board/contracts";
```

패키지가 여러 공개 하위 경로를 제공하려면 명시적으로 정의할 수도 있습니다.

```json
{
  "exports": {
    ".": "./dist/index.js",
    "./testing": "./dist/testing.js"
  }
}
```

그러면:

```ts
import {
  createBoardFixture,
} from "@board/contracts/testing";
```

처럼 문서화된 경로를 사용할 수 있습니다.

## `exports`가 소스 파일을 가리킬 때 주의합니다

다음 설정도 개발 환경에 따라 사용할 수 있습니다.

```json
{
  "exports": {
    ".": "./src/index.ts"
  }
}
```

하지만 Node.js가 TypeScript 파일을 직접 실행하지 않는 일반적인 빌드 구조라면 운영 런타임이 `.ts`를 이해하지 못할 수 있습니다.

따라서 `exports`가 무엇을 가리켜야 하는지는 실제 실행 방식에 따라 결정합니다.

```text
개발 도구가 TypeScript 소스를 직접 해석
→ src/*.ts를 가리키는 구조가 가능할 수 있음

빌드 후 Node.js가 JavaScript 직접 실행
→ dist/*.js 같은 빌드 결과를 가리키는 것이 자연스러움
```

중요한 것은 설정 예제를 그대로 복사하는 것이 아니라 **소비자가 실제로 어떤 파일을 실행하는지** 확인하는 것입니다.

## 내부 파일을 직접 가져오면 왜 문제가 되는가

다음 import를 생각해 봅니다.

```ts
import {
  parseWsMessage,
} from "@board/contracts/src/internal/ws.js";
```

이 순간 소비 코드는 다음 내부 구조를 모두 알고 있습니다.

```text
src/
internal/
ws.js
```

나중에 패키지 내부를 다음처럼 바꾸면:

```text
src/internal/ws.ts
↓
src/protocol/websocket.ts
```

기능 자체는 동일해도 모든 소비 코드가 깨집니다.

반대로 공개 진입점을 사용하면:

```ts
import {
  parseWsMessage,
} from "@board/contracts";
```

패키지 내부 파일을 이동한 뒤 `index.ts`의 export만 수정하면 소비 코드는 그대로 유지할 수 있습니다.

```text
내부 경로
→ 구현 세부사항

공개 진입점
→ 패키지 계약
```

## 공개 API는 작게 유지합니다

공유 패키지의 모든 내부 함수를 무조건 export하면 사실상 내부 구현 전체가 공개 계약이 됩니다.

예:

```ts
export * from "./internal/a.js";
export * from "./internal/b.js";
export * from "./internal/c.js";
```

필요한 이름만 공개하면 소비자가 의존할 수 있는 범위를 줄일 수 있습니다.

```ts
export {
  BoardSchema,
  parseBoardMessage,
} from "./board.js";

export type {
  BoardDto,
} from "./board.js";
```

공개 API가 작을수록 내부 구조를 바꾸기 쉽습니다.

## 순환 의존성을 피합니다

워크스페이스 패키지끼리 다음처럼 서로 의존하면 구조가 복잡해질 수 있습니다.

```text
@board/api
  ↓
@board/contracts
  ↓
@board/api
```

이런 순환 의존성은 빌드 순서, 초기화 순서, 테스트를 어렵게 만들 수 있습니다.

일반적으로 계약이나 공통 타입 같은 하위 패키지는 애플리케이션 패키지를 다시 import하지 않도록 방향을 단순하게 유지합니다.

예:

```text
@board/web ─────┐
               ↓
         @board/contracts
               ↑
@board/api ─────┘
```

`contracts`는 `web`이나 `api`의 구체적인 실행 코드에 의존하지 않습니다.

## 라이브러리와 실행 파일을 분리합니다

공유 모듈을 import하는 것만으로 서버를 열거나 타이머를 시작하지 않는 것이 중요합니다.

다음 파일을 생각해 봅니다.

```ts
// app.ts
const app = fastify();

await app.listen({
  port: 3000,
});
```

테스트가 이 파일의 어떤 함수를 재사용하려고 import하기만 해도 실제 포트가 열릴 수 있습니다.

이런 모듈은 테스트와 재사용이 어렵습니다.

## 애플리케이션 생성 함수

대신 서버 객체를 만드는 함수를 분리할 수 있습니다.

```ts
export function buildApp(
  dependencies: Dependencies
) {
  return fastify()
    .register(routes, {
      dependencies,
    });
}
```

이 함수의 책임은:

```text
애플리케이션 객체 구성
```

입니다.

실제 네트워크 포트를 열지는 않습니다.

## 실행 진입점

실제 포트를 여는 코드는 별도의 실행 파일에 둡니다.

```ts
const dependencies =
  createProductionDependencies();

const app =
  buildApp(dependencies);

await app.listen({
  host: "0.0.0.0",
  port: env.PORT,
});
```

책임을 구분하면 다음과 같습니다.

```text
buildApp()
→ 앱 구성

server.ts / main.ts
→ 환경 설정 읽기
→ 실제 의존성 생성
→ listen()
→ 프로세스 종료 처리
```

## 테스트에서는 실제 포트를 열 필요가 없습니다

Fastify 같은 프레임워크는 실제 TCP 포트를 열지 않고 요청을 주입하는 테스트 기능을 제공합니다.

예:

```ts
const app =
  buildApp(testDependencies);

const response =
  await app.inject({
    method: "GET",
    url: "/health",
  });
```

이 구조의 장점은 다음과 같습니다.

- 임의의 포트를 찾을 필요가 없습니다.
- 테스트끼리 포트 충돌이 줄어듭니다.
- 서버 시작·종료 비용이 줄어듭니다.
- 테스트용 의존성을 주입하기 쉽습니다.

이 때문에 애플리케이션 생성과 실제 `listen()`을 분리하는 것이 유용합니다.

## 의존성 생성도 분리합니다

운영 환경에서는 실제 데이터베이스를 사용할 수 있습니다.

```ts
const dependencies =
  createProductionDependencies();
```

테스트에서는 가짜 저장소나 테스트 데이터베이스를 사용할 수 있습니다.

```ts
const dependencies = {
  boards: createFakeBoardRepository(),
};
```

`buildApp()`이 필요한 의존성을 매개변수로 받으면 실행 환경에 따라 교체하기 쉽습니다.

```text
운영
→ 실제 DB, 실제 메시지 큐

테스트
→ fake/in-memory/test DB
```

## 모듈 import 시 부작용을 줄입니다

다음 코드는 import하는 순간 외부 동작을 시작합니다.

```ts
setInterval(runCleanup, 60_000);
```

또는:

```ts
const db =
  await connectDatabase();
```

공유 모듈에서 이런 일이 일어나면 테스트가 단순히 함수를 import했을 뿐인데도 타이머나 연결이 생길 수 있습니다.

가능하면 기능을 함수로 정의하고 실행 진입점에서 명시적으로 시작합니다.

```ts
export function startCleanupJob() {
  return setInterval(
    runCleanup,
    60_000
  );
}
```

실행 파일:

```ts
const cleanupTimer =
  startCleanupJob();
```

이제 누가 작업을 시작했고 누가 종료할 책임이 있는지 알기 쉽습니다.

## 시작 시 설정을 검사합니다

서버는 요청을 받기 시작하기 전에 필수 설정을 검증해야 합니다.

예:

```ts
const env =
  EnvSchema.parse(process.env);
```

검증 대상 예:

```text
PORT
DATABASE_URL
허용 Origin 목록
로그 레벨
외부 서비스 URL
필수 API 자격 정보
```

잘못된 설정을 임의의 값으로 바꾸고 계속 실행하면 실패 시점이 늦어집니다.

예를 들어:

```text
DATABASE_URL 없음
↓
서버는 일단 시작
↓
첫 DB 요청
↓
500
```

보다:

```text
프로세스 시작
↓
설정 검증 실패
↓
명확하게 시작 실패
```

가 원인을 찾기 쉽습니다.

## 설정과 업무 입력은 다른 경계입니다

환경 변수 검증은 프로세스 설정을 검증합니다.

```text
PORT
DATABASE_URL
NODE_ENV
```

HTTP 요청 검증은 사용자나 외부 시스템이 보낸 값을 검증합니다.

```text
request body
query string
path parameter
```

둘 다 런타임 검증이지만 시점과 책임이 다릅니다.

```text
환경 변수
→ 프로세스 시작 시 검증

HTTP 입력
→ 각 요청 경계에서 검증
```

## 서버 시작 전에 의존성 준비 여부를 확인합니다

설정 문법만 맞다고 실제 서비스가 준비된 것은 아닐 수 있습니다.

예를 들어 데이터베이스 URL 형식은 올바르지만 DB 서버가 내려가 있을 수 있습니다.

프로젝트 요구에 따라 시작 단계에서 다음을 확인할 수 있습니다.

```text
환경 변수 파싱
↓
필수 의존성 연결 확인
↓
마이그레이션 상태 확인
↓
요청 수락 시작
```

모든 외부 서비스를 시작 전에 반드시 확인해야 한다는 뜻은 아닙니다. 시스템의 복구 전략과 배포 방식에 따라 결정합니다.

중요한 것은 **설정 형식 검증과 실제 의존성 준비 상태가 서로 다른 문제**라는 점입니다.

## liveness와 readiness

운영 환경에서 상태 확인 엔드포인트를 둘 수 있습니다.

두 가지 목적을 구분합니다.

### liveness

프로세스 자체가 살아 있고 이벤트 루프가 응답할 수 있는지를 판단하는 신호입니다.

개념적으로:

```text
이 프로세스를 재시작해야 하는가?
```

에 답합니다.

너무 많은 외부 의존성을 liveness에 포함하면 데이터베이스가 잠시 느린 것만으로도 애플리케이션 프로세스가 반복 재시작될 수 있습니다.

### readiness

현재 인스턴스가 새 요청을 받아 처리할 준비가 되었는지 판단합니다.

개념적으로:

```text
이 인스턴스로 지금 트래픽을 보내도 되는가?
```

에 답합니다.

예를 들어 종료 절차가 시작되었다면 프로세스는 아직 살아 있어도 readiness는 false가 될 수 있습니다.

```text
프로세스 살아 있음
→ liveness true

종료 중이라 새 요청은 받지 않음
→ readiness false
```

두 상태를 하나의 의미로 섞지 않습니다.

## 정상 종료가 필요한 이유

운영 환경에서 프로세스는 여러 이유로 종료될 수 있습니다.

```text
배포
컨테이너 교체
오토스케일링
관리자 종료
운영체제 신호
```

프로세스를 즉시 끝내면 진행 중 요청이나 데이터베이스 작업이 갑자기 끊길 수 있습니다.

따라서 가능한 경우 **정상 종료(graceful shutdown)** 절차를 둡니다.

## 종료 순서

일반적인 종료 흐름은 다음과 같습니다.

```text
종료 신호 수신
   ↓
새 요청 수락 중단
   ↓
진행 중 요청 정리
   ↓
WebSocket / 큐 / 타이머 종료
   ↓
DB 풀과 외부 연결 종료
   ↓
프로세스 종료
```

실제 순서는 프레임워크와 애플리케이션 구조에 따라 달라질 수 있습니다.

핵심은 자원을 만든 코드가 **그 자원을 어떻게 닫을지도 알고 있어야 한다**는 것입니다.

## 종료 함수

예:

```ts
let closing = false;

async function shutdown(
  signal: string
) {
  if (closing) {
    return;
  }

  closing = true;

  app.log.info(
    { signal },
    "shutdown started"
  );

  await app.close();
  await db.destroy();
}
```

`closing` 플래그는 여러 종료 신호가 거의 동시에 들어와 종료 절차가 중복 실행되는 것을 막습니다.

예:

```text
SIGTERM
↓
shutdown 시작

곧바로 SIGINT
↓
두 번째 shutdown은 return
```

## 종료 신호 연결

실행 진입점에서 운영체제 신호를 종료 함수에 연결할 수 있습니다.

```ts
process.once(
  "SIGTERM",
  () => {
    void shutdown("SIGTERM");
  }
);

process.once(
  "SIGINT",
  () => {
    void shutdown("SIGINT");
  }
);
```

`void`를 붙였다고 오류가 처리되는 것은 아니므로 실제 운영 코드에서는 shutdown 실패도 적절히 기록하고 종료 코드 정책을 정해야 합니다.

예:

```ts
async function handleShutdown(
  signal: string
) {
  try {
    await shutdown(signal);
    process.exitCode = 0;
  } catch (error) {
    app.log.error(
      { error, signal },
      "shutdown failed"
    );

    process.exitCode = 1;
  }
}
```

## `process.exit()`를 성급하게 호출하지 않습니다

다음 코드는 즉시 프로세스를 종료시킬 수 있습니다.

```ts
process.exit(0);
```

이 경우 아직 출력되지 않은 로그나 진행 중 비동기 정리가 중단될 수 있습니다.

가능하면 필요한 정리를 `await`한 뒤 `process.exitCode`를 설정하고 이벤트 루프가 자연스럽게 끝나도록 하는 방식이 더 안전한 경우가 많습니다.

다만 종료 기한을 넘긴 경우 강제 종료가 필요한 시스템도 있으므로 프로젝트 정책에 따라 별도의 최종 타임아웃을 둘 수 있습니다.

## 종료해야 하는 자원

애플리케이션에 따라 다음 자원이 남아 있을 수 있습니다.

- HTTP 서버
- 데이터베이스 연결 풀
- Redis 연결
- WebSocket 서버와 연결
- 메시지 큐 consumer/producer
- `setInterval`, `setTimeout`
- 파일 watcher
- 백그라운드 작업
- 외부 SDK 연결

서버만 닫고 다른 자원을 남기면 프로세스가 종료되지 않거나 종료 중에도 외부 작업이 계속될 수 있습니다.

## 자원의 소유권을 분명하게 합니다

예를 들어 다음 함수가 데이터베이스를 만들었다면:

```ts
function createProductionDependencies() {
  const db =
    createDatabasePool();

  return {
    db,
  };
}
```

누가 `db.destroy()`를 호출할 책임이 있는지도 구조에서 분명해야 합니다.

한 가지 방법은 생성과 정리 함수를 함께 반환하는 것입니다.

```ts
function createProductionDependencies() {
  const db =
    createDatabasePool();

  return {
    dependencies: {
      db,
    },

    async close() {
      await db.destroy();
    },
  };
}
```

실행 파일:

```ts
const runtime =
  createProductionDependencies();

const app =
  buildApp(runtime.dependencies);

async function shutdown() {
  await app.close();
  await runtime.close();
}
```

이런 구조는 모든 프로젝트에 반드시 필요한 패턴은 아니지만 **생성한 자원을 누가 닫는가**를 명시하는 데 도움이 됩니다.

## 테스트도 정리해야 합니다

테스트에서 실제 데이터베이스 풀, 서버, 타이머를 만들었다면 테스트가 끝난 뒤 닫아야 합니다.

예:

```ts
const app =
  buildApp(testDependencies);

try {
  const response =
    await app.inject({
      method: "GET",
      url: "/health",
    });

  // assertions...
} finally {
  await app.close();
}
```

테스트가 끝나지 않고 계속 대기하는 경우 열려 있는 핸들, 타이머, DB 연결을 의심할 수 있습니다.

테스트도 운영 코드와 같은 종료 함수를 재사용할 수 있다면 자원 정리 경로를 실제로 검증하는 데 도움이 됩니다.

## 워크스페이스 예제 구조

다음과 같은 저장소를 생각해 봅니다.

```text
repo/
├─ apps/
│  ├─ api/
│  │  ├─ src/
│  │  │  ├─ app.ts
│  │  │  └─ server.ts
│  │  └─ package.json
│  │
│  └─ web/
│     └─ package.json
│
├─ packages/
│  └─ contracts/
│     ├─ src/
│     │  ├─ board.ts
│     │  └─ index.ts
│     └─ package.json
│
├─ package.json
├─ pnpm-lock.yaml
└─ pnpm-workspace.yaml
```

`contracts`:

```json
{
  "name": "@board/contracts",
  "private": true,
  "type": "module",
  "exports": {
    ".": "./dist/index.js"
  }
}
```

API 패키지:

```json
{
  "name": "@board/api",
  "private": true,
  "type": "module",
  "dependencies": {
    "@board/contracts": "workspace:*",
    "fastify": "^5.0.0"
  }
}
```

소비 코드:

```ts
import {
  BoardSchema,
} from "@board/contracts";
```

이 구조에서 API는 `contracts/src/...`의 실제 파일 위치를 알 필요가 없습니다.

## 실행 파일 예제

앱 구성:

```ts
// app.ts
export function buildApp(
  dependencies: Dependencies
) {
  const app = fastify();

  app.register(routes, {
    dependencies,
  });

  return app;
}
```

실행 진입점:

```ts
// server.ts
const env =
  EnvSchema.parse(process.env);

const runtime =
  createProductionDependencies(env);

const app =
  buildApp(runtime.dependencies);

let closing = false;

async function shutdown(
  signal: string
) {
  if (closing) {
    return;
  }

  closing = true;

  app.log.info(
    { signal },
    "shutdown started"
  );

  await app.close();
  await runtime.close();
}

process.once(
  "SIGTERM",
  () => {
    void shutdown("SIGTERM");
  }
);

process.once(
  "SIGINT",
  () => {
    void shutdown("SIGINT");
  }
);

await app.listen({
  host: "0.0.0.0",
  port: env.PORT,
});
```

이 구조의 책임은 다음과 같습니다.

```text
EnvSchema
→ 시작 설정 검증

createProductionDependencies()
→ 운영 자원 생성

buildApp()
→ 앱 구성

server.ts
→ 실제 포트 열기
→ 종료 신호 연결

shutdown()
→ 생성한 자원 정리
```

## 문제를 추적하는 기본 순서

Node.js 프로젝트가 실행되지 않거나 모듈을 찾지 못하면 다음 순서로 확인합니다.

```text
1. 어떤 Node.js 버전으로 실행하는가?
2. 어떤 패키지 관리자를 사용하는가?
3. lockfile 기준 설치가 되었는가?
4. 현재 명령은 어느 package.json의 script인가?
5. 이 파일은 브라우저용인가 Node.js용인가?
6. package.json의 type은 무엇인가?
7. TypeScript module/moduleResolution은 무엇인가?
8. 실제 빌드 결과 파일 경로와 확장자는 무엇인가?
9. import가 공개 패키지 경로를 사용하는가?
10. exports가 실제 실행 가능한 파일을 가리키는가?
```

서버가 시작되지만 종료되지 않는다면:

```text
1. HTTP 서버를 닫았는가?
2. DB 풀을 닫았는가?
3. WebSocket을 닫았는가?
4. setInterval이 남아 있는가?
5. 메시지 큐 consumer가 남아 있는가?
6. 테스트나 실행 코드에서 cleanup을 호출했는가?
```

환경 문제라면:

```text
1. 필수 환경 변수가 있는가?
2. 문자열을 필요한 타입으로 변환했는가?
3. 허용 범위를 검사했는가?
4. 서버가 요청을 받기 전에 검증했는가?
5. 실제 외부 의존성이 준비되어 있는가?
```

## 흔한 실수

- 브라우저 API와 Node.js API를 같은 파일에서 항상 사용할 수 있다고 생각합니다.
- 서버 비밀값을 브라우저 번들에 넣어도 숨겨진다고 생각합니다.
- 개발자마다 다른 Node.js 버전을 사용해도 실행 결과가 같다고 가정합니다.
- 실제 운영 코드가 사용하는 의존성을 `devDependencies`에 둡니다.
- 직접 import하는 패키지를 다른 의존성의 설치 결과에 암묵적으로 기대합니다.
- `package.json` 버전 범위만 있으면 설치 결과를 정확히 재현할 수 있다고 생각합니다.
- lockfile을 단순 캐시 파일처럼 삭제합니다.
- 한 저장소에서 여러 패키지 관리자를 혼용합니다.
- `"type": "module"`과 TypeScript의 모듈 해석 설정을 따로 생각합니다.
- TypeScript 소스가 `.ts`이므로 ESM import에도 항상 `.ts`를 써야 한다고 생각합니다.
- 번들러가 처리하는 import 규칙과 Node.js가 직접 실행하는 ESM 규칙이 같다고 가정합니다.
- TypeScript `paths` 별칭을 설정하면 Node.js도 자동으로 이해한다고 생각합니다.
- 워크스페이스 패키지의 내부 파일을 상대 경로나 깊은 import로 직접 가져옵니다.
- `exports`가 실제 실행 환경에서 읽을 수 없는 `.ts` 파일을 가리키는데도 문제없다고 생각합니다.
- 공유 패키지의 모든 내부 함수를 export하여 구현 세부사항까지 공개 API로 만듭니다.
- 워크스페이스 패키지 사이에 순환 의존성을 만듭니다.
- 모듈을 가져오는 순간 서버, 타이머, DB 연결을 시작합니다.
- 애플리케이션 생성과 `listen()`을 같은 함수에 묶어 테스트에서 실제 포트를 열게 만듭니다.
- 첫 요청이 들어온 뒤 환경 변수를 검사합니다.
- 설정 형식 검증과 실제 외부 서비스 준비 여부를 같은 문제라고 생각합니다.
- liveness와 readiness를 같은 상태로 취급합니다.
- 종료 신호에서 서버만 닫고 DB 풀, 소켓, 타이머, 큐를 남깁니다.
- 종료 절차를 여러 번 동시에 실행하게 둡니다.
- 비동기 정리 직후 곧바로 `process.exit()`를 호출해 정리 작업을 중단시킵니다.
- 테스트에서 만든 앱과 연결을 닫지 않아 테스트 프로세스가 끝나지 않게 합니다.

## 관련 exercise

[`runtime-workspace`](../../exercises/runtime-workspace/README.md)는 앱과 라이브러리를 별도 패키지로 두고 공개 진입점, 포트 검사, 이벤트 루프 순서를 확인합니다.

## 완료 기준

다음 내용을 설명하거나 직접 구성할 수 있으면 이 문서의 목표를 달성한 것입니다.

- 브라우저와 Node.js의 실행 위치와 API 차이를 설명할 수 있습니다.
- 서버 전용 비밀값을 브라우저 번들에 넣으면 안 되는 이유를 설명할 수 있습니다.
- Node.js 버전도 프로젝트 실행 환경의 일부라는 점을 설명할 수 있습니다.
- `package.json`의 `name`, `private`, `type`, `scripts`, `dependencies`, `devDependencies` 역할을 구분할 수 있습니다.
- 실행 의존성과 개발 도구 의존성을 실제 운영 실행 방식에 따라 구분할 수 있습니다.
- `package.json` 버전 범위와 lockfile이 서로 다른 역할을 한다는 점을 설명할 수 있습니다.
- CI에서 lockfile을 변경하지 않고 설치하는 이유를 설명할 수 있습니다.
- ESM에서 최종 JavaScript 파일 경로를 기준으로 `.js` 확장자를 적을 수 있는 이유를 설명할 수 있습니다.
- `NodeNext` 설정이 Node.js의 실제 모듈 해석과 연결된다는 점을 설명할 수 있습니다.
- 번들러의 모듈 해석과 Node.js 직접 실행의 차이를 확인할 수 있습니다.
- `workspace:*`로 내부 패키지 의존성을 선언할 수 있습니다.
- 패키지 내부 파일 대신 `exports`로 정의한 공개 진입점을 사용할 수 있습니다.
- 공개 API와 내부 구현 경로를 구분할 수 있습니다.
- 워크스페이스 패키지 사이의 의존 방향을 단순하게 유지할 수 있습니다.
- 애플리케이션 생성과 실제 `listen()` 호출을 분리할 수 있습니다.
- 테스트에서 실제 포트를 열지 않고 앱 객체를 사용할 수 있는 구조를 설명할 수 있습니다.
- 프로세스 시작 시 환경 변수와 필수 설정을 검증할 수 있습니다.
- liveness와 readiness의 목적 차이를 설명할 수 있습니다.
- 종료 시 HTTP 서버뿐 아니라 데이터베이스, WebSocket, 타이머, 작업 큐 등 생성한 자원을 닫아야 하는 이유를 설명할 수 있습니다.
- 동일한 종료 함수나 정리 경로를 테스트에서도 사용할 수 있습니다.
