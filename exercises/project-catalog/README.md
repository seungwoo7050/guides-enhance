# Project Catalog

`Project Catalog`는 Next.js App Router로 만든 프로젝트 검색·편집 애플리케이션입니다. 이 저장소의 목적은 특정 제품을 제공하는 것이 아니라, 실제 프로젝트에서 필요한 프런트엔드 역량을 작은 프로그램 안에서 다시 구현하고 검증하는 것입니다.

이 프로그램은 다음 흐름을 하나의 예제로 연결합니다.

```text
URL query
→ Server Component의 첫 렌더링
→ Client Component의 후속 검색
→ 외부 응답 runtime 검증
→ history 복원
→ 비동기 요청 최신성 판정
→ 낙관적 제목 변경
→ version 충돌 처리
→ 접근성·반응형·성능 검증
→ 운영 build/start와 smoke test
```

검색 조건은 URL로 공유할 수 있습니다. Server Component는 URL을 정규화한 뒤 첫 화면의 검색 조건과 결과를 같은 입력으로 만듭니다. 이후의 검색과 제목 변경은 Client Component가 처리합니다.

HTTP 응답은 TypeScript 타입 단언만으로 신뢰하지 않고 필요한 필드, 숫자 범위, enum과 중복 식별자를 runtime에서 검사한 뒤에만 화면 상태로 반영합니다.

제목을 저장할 때는 현재 `version`을 함께 전송합니다. 서버의 현재 `version`과 요청의 `version`이 다르면 다른 변경이 먼저 저장된 것으로 보고 `409 Conflict`를 반환합니다.

```text
일반 저장 실패
→ 목록은 마지막 서버 확정값으로 복구
→ 사용자의 입력 초안은 유지

409 Conflict
→ 목록은 응답의 최신 서버 값으로 갱신
→ 사용자의 입력 초안은 유지

저장 성공
→ 서버가 반환한 title과 새 version을 최종값으로 사용
```

## 이 저장소의 사용 시점

이 프로그램은 실제 프로젝트에 들어가기 전에 반드시 풀어야 하는 선행 과제가 아닙니다.

권장 사용 순서는 다음과 같습니다.

```text
실제 프로젝트 경험
→ Guide 학습
→ Guide를 보지 않고 Project Catalog 구현 또는 검증
→ 실패한 역량만 Guide에서 다시 확인
```

즉, 이 저장소는 **역량 검증용 프로그램**입니다. 완성된 코드를 외우는 것이 목적이 아니라 다음 능력을 스스로 재현할 수 있는지 확인하는 것이 목적입니다.

- URL query와 서버 첫 렌더링이 같은 정규화된 입력을 사용하게 합니다.
- 외부 JSON을 `unknown`으로 받고 필요한 구조와 의미 제약을 검사합니다.
- 요청 중이거나 요청이 실패해도 마지막으로 확인한 정상 결과를 유지할 수 있습니다.
- 이전 요청의 늦은 성공 또는 실패가 최신 화면을 덮지 못하게 합니다.
- 낙관적 갱신, 일반 실패와 `version` 충돌을 서로 다른 상태 전이로 처리합니다.
- 키보드 조작, accessible name과 focus 이동을 실제 브라우저에서 확인합니다.
- 좁은 화면, 긴 문자열과 motion 감소 설정을 검증합니다.
- 운영 서버를 직접 실행해 health, release와 서버 전용 값 비노출을 검사합니다.

## 주요 기능

### 검색과 URL

- `q`, `status`, `page` query를 정규화합니다.
- 서버 첫 화면과 Client Component가 같은 query 규칙을 사용합니다.
- 검색 조건을 browser history에 기록합니다.
- back/forward 이동에서는 현재 URL을 다시 읽고 입력값과 결과를 복원합니다.
- 검색을 새로 제출하면 `page=1`부터 다시 시작합니다.

### 비동기 요청

- 새 검색이 시작되면 이전 `AbortController`를 중단합니다.
- 각 요청에 증가하는 generation을 부여합니다.
- 응답을 반영하기 직전에 현재 generation인지 확인합니다.
- 이전 generation의 성공과 실패는 모두 화면을 바꾸지 못합니다.
- 검색 실패나 응답 계약 검증 실패가 발생해도 마지막 정상 결과를 유지합니다.

### 제목 편집

- 사용자가 입력한 제목을 서버 응답 전에 목록에 먼저 표시하는 낙관적 갱신을 사용합니다.
- 요청 전 서버 값을 별도로 보관해 일반 실패 시 rollback할 수 있습니다.
- 입력 초안은 서버 확정값과 별도로 유지합니다.
- `409 Conflict`에서는 응답의 최신 서버 값과 사용자의 입력 초안을 함께 보존합니다.
- 성공 시 서버가 반환한 보정된 title과 새 `version`을 최종값으로 사용합니다.

### 접근성·반응형·성능

- keyboard만으로 제목 편집을 완료할 수 있습니다.
- 편집 시작, 취소, 성공, 실패와 충돌 뒤 focus 위치를 관리합니다.
- `aria-live`로 필요한 비동기 상태를 전달합니다.
- `:focus-visible`이 실제 화면에서 보이도록 합니다.
- 좁은 viewport와 공백 없는 긴 문자열에서 page overflow를 확인합니다.
- `prefers-reduced-motion` 설정을 반영합니다.
- 초기 JavaScript 응답 크기와 DOM element 수에 회귀 탐지용 예산을 둡니다.

### 운영 검증

- health endpoint가 현재 `release`와 최소 상태만 반환합니다.
- 테스트 전용 reset endpoint는 test mode와 token이 모두 맞을 때만 동작합니다.
- smoke test가 실제 운영 서버 프로세스를 직접 시작합니다.
- health, root HTML, 핵심 API와 server-only canary 비노출을 확인합니다.
- 성공과 실패 모두 child process를 정리합니다.

## 디렉터리

```text
project-catalog/
├── app/
│   ├── api/
│   │   ├── health/route.ts
│   │   ├── projects/route.ts
│   │   ├── projects/[id]/route.ts
│   │   └── test/reset/route.ts
│   ├── layout.tsx
│   ├── page.tsx
│   ├── project-catalog.tsx
│   └── styles.css
├── lib/
│   ├── catalog-contract.ts
│   ├── catalog-model.ts
│   ├── project-types.ts
│   ├── projects.ts
│   └── request-coordinator.ts
├── scripts/
│   ├── run-playwright.mjs
│   └── smoke-production.mjs
├── tests/
│   ├── e2e/
│   └── *.test.ts
├── .nvmrc
├── package.json
├── performance-budget.json
├── playwright.config.ts
├── tsconfig.json
└── vitest.config.ts
```

## 파일별 역할

### `lib/project-types.ts`

Route Handler, Server Component와 Client Component가 공유하는 데이터 타입을 정의합니다.

이 파일에는 서버 runtime 객체가 아니라 다음처럼 경계를 넘어 전달할 수 있는 데이터 구조만 둡니다.

```text
Project
SearchResult
ProjectQuery
Rename command/outcome
```

### `lib/projects.ts`

서버 프로세스 메모리의 `Map`에 프로젝트와 `version`을 저장합니다.

이 저장소는 예제 프로그램의 동시 수정과 검색 동작을 재현하기 위한 최소 구현입니다.

- 검색 조건에 맞는 프로젝트를 계산합니다.
- pagination 결과와 전체 개수를 계산합니다.
- 요청의 `version`이 현재 값과 같을 때만 제목을 변경합니다.
- 변경 성공 시 `version`을 증가시킵니다.
- 테스트에서 같은 초기 상태로 돌아갈 수 있도록 reset 기능을 제공합니다.
- 호출자에게 내부 저장 객체 자체가 아니라 복사본을 반환합니다.

호출자가 반환 객체를 수정해도 서버 저장소가 함께 바뀌지 않게 하는 것이 목적입니다.

### `lib/catalog-contract.ts`

외부 입력과 내부 타입 사이의 runtime 경계를 담당합니다.

주요 역할은 다음과 같습니다.

```text
URL query
→ 허용 범위로 정규화
→ ProjectQuery

unknown JSON
→ 구조·범위·enum·중복 id 검사
→ 애플리케이션 타입
```

외부 입력 형식 오류는 `ContractError`로 통일해 호출부가 같은 방식으로 처리할 수 있게 합니다.

### `lib/catalog-model.ts`

검색 결과 화면의 허용 상태를 정의합니다.

```text
ready
empty
pending
error
```

`pending`과 `error`는 마지막 정상 결과를 보존합니다. 따라서 새 요청이 진행 중이거나 현재 요청이 실패해도 사용자가 마지막으로 확인한 목록을 계속 볼 수 있습니다.

### `lib/request-coordinator.ts`

검색 요청의 수명을 관리합니다.

- 새 요청 시작 시 이전 `AbortController`를 abort합니다.
- generation을 증가시킵니다.
- 완료된 작업이 현재 generation인지 확인합니다.
- cancel 시 기존 generation의 결과 적용 권한도 무효화합니다.

`AbortController`는 불필요한 작업을 줄이고, generation은 늦게 도착한 결과가 화면을 바꾸지 못하게 합니다.

### `app/page.tsx`

Server Component입니다.

현재 URL query를 읽고 한 번 정규화한 뒤 같은 `ProjectQuery`를 사용하여 다음 두 값을 만듭니다.

```text
첫 검색 조건
첫 검색 결과
```

따라서 첫 input 값과 첫 목록이 서로 다른 query 규칙을 사용할 가능성을 줄입니다.

### `app/project-catalog.tsx`

Client Component입니다.

다음 브라우저 동작과 UI 상태를 담당합니다.

- 검색 입력 초안
- 적용된 검색 결과
- 검색 request 수명
- history 기록과 back/forward 복원
- loading/error 안내
- 제목 편집 초안
- 낙관적 갱신과 rollback
- `409 Conflict` 처리
- keyboard event
- focus 이동

### Route Handler

각 Route Handler의 책임을 분리합니다.

```text
GET /api/projects
→ 검색 query 검사
→ SearchResult 반환

PATCH /api/projects/:id
→ title/version 검사
→ 성공, 입력 오류, 없음, conflict 구분

GET /api/health
→ 최소 health와 release 반환

POST /api/test/reset
→ test mode + token 조건에서만 데이터 reset
```

### `tests/`, Playwright와 smoke script

검사 종류에 따라 책임을 분리합니다.

```text
Vitest
→ parser, model, coordinator, repository, Route Handler

Playwright
→ history, race, keyboard, focus, responsive, motion, performance budget

smoke script
→ production start, health, root/API, secret canary, process cleanup
```

## 요구 환경

- Node.js `24.19.0`
- npm
- Playwright Chromium

`.nvmrc`를 사용하는 경우 다음과 같이 준비합니다.

```sh
nvm use
npm install
npx playwright install chromium
```

잠금 파일을 재현해야 하는 CI나 검증 환경에서는 저장소가 정한 고정 설치 명령을 사용합니다.

예를 들어 `package-lock.json`을 기준으로 재현하는 환경이라면 일반적으로 다음과 같은 명령을 사용할 수 있습니다.

```sh
npm ci
```

실제 기준은 `package.json`, 잠금 파일과 CI 설정을 따릅니다.

## 실행

### 개발 서버

```sh
npm run dev
```

기본 주소는 다음과 같습니다.

```text
http://localhost:3000
```

검색 조건을 URL에 직접 넣어 첫 화면 복원을 확인할 수 있습니다.

```text
/?q=Storage&status=active&page=1
```

### 운영 서버

먼저 운영 build를 만듭니다.

```sh
npm run build
```

그 뒤 release id를 주입하여 운영 서버를 실행합니다.

```sh
APP_RELEASE=local-build npm run start
```

운영 검증에서는 개발 서버가 아니라 이 build 결과를 대상으로 테스트합니다.

## HTTP API

| Method | Path | 처리 내용 |
| --- | --- | --- |
| `GET` | `/api/projects` | `q`, `status`, `page`를 검사하고 검색 결과를 반환합니다. |
| `PATCH` | `/api/projects/:id` | `{ "title": string, "version": number }`를 검사하고 현재 `version`일 때만 제목을 변경합니다. |
| `GET` | `/api/health` | `{ "status", "release" }`만 반환하며 응답을 cache하지 않습니다. |
| `POST` | `/api/test/reset` | test mode와 token이 모두 맞을 때만 프로세스 내 데이터를 초기화합니다. |

### `PATCH /api/projects/:id`

요청 예시는 다음과 같습니다.

```json
{
  "title": "Network Platform",
  "version": 3
}
```

서버의 현재 `version`이 `3`이면 변경을 적용하고 새 `version`을 반환합니다.

```text
request version = 3
server version = 3
→ 저장 성공
→ server version = 4
```

다른 변경이 먼저 저장되어 서버 `version`이 이미 `4`라면 요청을 적용하지 않습니다.

```text
request version = 3
server version = 4
→ 409 Conflict
→ 최신 project 반환
```

주요 상태 코드는 다음과 같습니다.

```text
200 또는 성공 status
→ 저장 성공

400
→ request body가 계약에 맞지 않음

404
→ project가 없음

409
→ request version이 서버 최신 version과 다름
```

## 환경 변수

| 이름 | 용도 | 기본값 |
| --- | --- | --- |
| `APP_RELEASE` | health와 운영 진단에 사용할 릴리스 식별자 | `local` |
| `PLAYWRIGHT` | 값이 `1`이면 테스트 모드 중 하나로 사용 | 없음 |
| `CATALOG_TEST_RESET_TOKEN` | reset 요청 header와 비교할 서버 전용 token | 없음 |

`/api/test/reset`은 다음 두 조건을 모두 만족할 때만 동작합니다.

1. `NODE_ENV=test` 또는 `PLAYWRIGHT=1`
2. `x-catalog-test-token` header와 `CATALOG_TEST_RESET_TOKEN`이 일치

둘 중 하나라도 충족하지 않으면 endpoint 존재를 드러내지 않기 위해 `404`를 반환합니다.

이 endpoint는 일반 운영 관리 API가 아닙니다. 테스트 자동화를 위한 제한된 제어 경로입니다.

## 검증

### 형 검사

Next.js route type을 생성한 뒤 TypeScript를 검사합니다.

```sh
npm run typecheck
```

실제 script는 프로젝트의 Next.js 버전에서 지원하는 type generation 방식과 `tsc --noEmit`을 조합합니다.

### 단위 테스트와 Route Handler 테스트

```sh
npm test
```

주요 검사 대상은 다음과 같습니다.

- query 정규화
- 외부 JSON 계약 검증
- 검색 상태 전이
- request coordinator
- repository 검색과 `version` 처리
- HTTP status와 response body
- health/test reset 운영 계약
- performance budget 파일 형식

### 브라우저 E2E

```sh
npm run test:e2e
```

이 명령은 운영 build 뒤 production server를 대상으로 실행하는 것을 전제로 합니다.

주요 검사 대상은 다음과 같습니다.

- URL query와 서버 첫 화면 일치
- 검색 history와 back/forward 복원
- 오래된 성공/실패 응답 폐기
- 잘못된 JSON 응답 거부
- 낙관적 저장 일반 실패
- `409 Conflict`
- keyboard 조작과 focus 복귀
- accessible name과 live region
- 좁은 viewport와 긴 문자열
- reduced motion
- JavaScript/DOM 성능 예산

### 운영 smoke test

```sh
npm run smoke
```

smoke test는 이미 실행 중인 개발 서버에 의존하지 않고 실제 운영 서버 프로세스를 직접 시작합니다.

개념적 흐름은 다음과 같습니다.

```text
사용 가능한 port 선택
→ production start
→ health 준비 대기
→ release 확인
→ root HTML 확인
→ 핵심 API 최소 확인
→ server-only canary 비노출 확인
→ SIGTERM
→ child process 종료 확인
```

smoke test는 다음을 확인합니다.

- health 응답의 공개 필드
- `Cache-Control: no-store`
- 실행 시 주입한 release id
- root HTML의 핵심 heading
- 프로젝트 API의 최소 응답 형식
- 서버 전용 canary가 health, HTML와 초기 JavaScript 응답에 포함되지 않음
- 성공과 실패 모두 child process가 정리됨

### 전체 검증

```sh
npm run verify
```

이 명령은 저장소가 정의한 전체 검증 순서를 한 번에 실행합니다.

실제 세부 순서는 `package.json`의 scripts를 기준으로 확인합니다.

## 성능 예산

`performance-budget.json`은 브라우저 테스트가 확인할 회귀 탐지용 기준을 정의합니다.

현재 예산은 다음 두 값입니다.

```text
첫 route가 받은 JavaScript 응답 본문의 합
≤ 800000 byte

첫 화면의 DOM element 수
≤ 180
```

이 숫자는 일반적인 웹 애플리케이션의 보편적 권장값이 아닙니다. 이 예제 프로그램이 작은 기능 변경으로 갑자기 무거워지는 것을 감지하기 위한 프로젝트 내부 기준입니다.

예산 파일의 key와 값 자체도 단위 테스트로 검사합니다.

예산을 변경해야 한다면 다음 순서로 확인합니다.

```text
무엇이 증가했는가?
→ 왜 증가했는가?
→ 증가가 의도된 것인가?
→ 더 작은 Client Component 경계나 lazy loading으로 줄일 수 있는가?
→ 그래도 필요한 증가라면 기준 조정
```

## 주요 구현 선택

### 마지막 정상 결과를 유지합니다

검색 상태는 다음 네 경우만 허용합니다.

```text
ready
empty
pending
error
```

`pending`과 `error`는 `previous`에 마지막 정상 `SearchResult`를 보관합니다.

따라서 다음 상황에서도 마지막 확인 결과를 계속 표시할 수 있습니다.

```text
새 검색 진행 중
HTTP 실패
JSON 해석 실패
runtime 계약 검증 실패
```

이 설계는 "현재 요청 실패로 기존 정보까지 사라지지 않게 한다"는 제품 결정을 코드에 반영한 것입니다.

### abort와 generation을 함께 사용합니다

`AbortController`와 generation은 다른 문제를 해결합니다.

```text
AbortController
→ 이전 작업을 가능한 범위에서 중단

generation
→ 완료된 결과가 현재 화면을 바꿀 권한이 있는지 판단
```

예를 들어 다음 순서에서도 최신 결과만 유지합니다.

```text
old 요청 시작
new 요청 시작
new 성공
old 성공
→ old 결과 폐기
```

오래된 실패도 같은 방식으로 폐기합니다.

```text
old 요청 시작
new 요청 시작
new 성공
old 실패
→ old 오류를 표시하지 않음
```

### 서버 값과 입력 초안을 분리합니다

제목 편집에서는 다음 값을 별도로 관리합니다.

```text
서버 확정 project
사용자의 draftTitle
현재 저장 상태
```

일반 실패에서는 목록을 요청 전 서버 값으로 되돌리지만 `draftTitle`은 유지합니다.

```text
server title = Network
draftTitle = Networking

optimistic display = Networking
저장 실패

목록
→ Network

입력창
→ Networking 유지
```

### `409 Conflict`는 rollback이 아닙니다

충돌에서 요청 전 값으로 되돌리면 서버의 최신 변경을 숨길 수 있습니다.

따라서 응답의 최신 project를 목록에 반영합니다.

```text
내가 본 version = 3
다른 변경 후 server version = 4

내 draftTitle
→ Networking

409 response
→ title = Network Platform
→ version = 4

화면
→ server title = Network Platform
→ draftTitle = Networking
```

이후 사용자가 최신 서버 값과 자신의 초안을 비교해 다시 판단할 수 있습니다.

### 서버 응답을 최종값으로 사용합니다

저장 성공 뒤에는 클라이언트가 보낸 title을 그대로 확정값으로 간주하지 않습니다.

서버가 다음 작업을 할 수 있기 때문입니다.

- 문자열 정규화
- 새 `version` 부여
- 다른 필드 보정

따라서 성공 응답을 runtime에서 검사한 뒤 응답의 project를 최종 상태로 사용합니다.

### 프로세스 내 저장소를 사용합니다

이 프로그램은 별도 database 없이 검색, `version` 검사와 conflict를 재현하기 위해 서버 프로세스 메모리의 `Map`을 사용합니다.

이 선택은 학습·검증 범위를 작게 유지하기 위한 것입니다.

장점:

- 별도 database 설치가 필요 없습니다.
- repository, Route Handler와 browser E2E가 같은 server process 상태를 사용할 수 있습니다.
- reset endpoint로 같은 초기 상태를 쉽게 복원할 수 있습니다.

제한:

- process가 재시작되면 데이터가 초기화됩니다.
- 여러 server instance 사이에 상태를 공유하지 않습니다.
- 실제 transaction, database isolation과 distributed concurrency를 검증하지 않습니다.

## Implementation Order

아래 번호는 Git commit 순서나 실제 파일 생성 이력을 의미하지 않습니다.

완성된 프로그램을 처음부터 다시 구현할 때 **어떤 계약이 어떤 계약에 의존하는지**를 나타내는 학습용 순서입니다.

하위 번호는 같은 책임을 세분화한 단계입니다.

| Order | 구현 내용 | 주요 파일 |
| ---: | --- | --- |
| 1 | Route Handler와 Server/Client Component가 공유할 직렬화 가능한 데이터 타입을 정의합니다. | `lib/project-types.ts` |
| 2 | 서버 프로세스가 프로젝트와 `version`을 보관하고 호출자에게 복사본을 반환하게 합니다. | `lib/projects.ts` |
| 2.1 | `q`, `status`, `page`를 적용해 현재 page 결과와 전체 개수를 계산합니다. | `lib/projects.ts` |
| 2.2 | 요청 `version`이 현재 값과 같을 때만 title과 `version`을 함께 갱신합니다. | `lib/projects.ts` |
| 2.3 | 테스트가 같은 초기 데이터에서 시작하도록 저장소 reset을 제공합니다. | `lib/projects.ts` |
| 3 | 외부 입력 형식 오류를 `ContractError`로 통일합니다. | `lib/catalog-contract.ts` |
| 3.1 | URL query를 허용 범위로 정규화하고 serialize 후 다시 읽어도 같은 의미가 되게 합니다. | `lib/catalog-contract.ts` |
| 3.2 | `unknown` JSON의 필드, 숫자 범위, enum과 중복 id를 검사해 내부 타입으로 바꿉니다. | `lib/catalog-contract.ts` |
| 4 | `ready`, `empty`, `pending`, `error` 상태와 마지막 정상 결과 보존 규칙을 정의합니다. | `lib/catalog-model.ts` |
| 5 | 문서 언어, metadata와 전역 stylesheet를 설정합니다. | `app/layout.tsx` |
| 6 | URL query를 한 번 정규화해 첫 검색 조건과 첫 결과가 같은 입력을 사용하게 합니다. | `app/page.tsx` |
| 7 | abort와 generation으로 검색 request 수명을 관리합니다. | `lib/request-coordinator.ts` |
| 8 | 검색 초안, 확인된 결과, 안내 문구와 request 수명을 `ProjectCatalog`에서 연결합니다. | `app/project-catalog.tsx` |
| 8.1 | 검색 제출은 history에 기록하고 back/forward에서는 URL을 다시 읽어 복원합니다. | `app/project-catalog.tsx` |
| 8.2 | 낙관적 제목 변경, 일반 실패 rollback과 conflict 복구를 구현합니다. | `app/project-catalog.tsx` |
| 9 | 편집 초안, 저장 상태와 focus 이동을 연결합니다. | `app/project-catalog.tsx` |
| 10 | 검색 query를 검사하고 cache하지 않는 JSON 응답을 반환합니다. | `app/api/projects/route.ts` |
| 10.1 | title과 `version`을 검사하고 성공, 입력 오류, 없음과 conflict를 HTTP status로 구분합니다. | `app/api/projects/[id]/route.ts` |
| 11 | test mode와 token이 모두 맞을 때만 데이터를 reset하고 나머지는 `404`로 숨깁니다. | `app/api/test/reset/route.ts` |
| 12 | 현재 release와 최소 health 상태를 cache 없이 반환합니다. | `app/api/health/route.ts` |
| 12.1 | Route Handler 추가 뒤 Next.js route type을 생성하고 TypeScript를 검사합니다. | project scripts |
| 13 | 좁은 화면, 긴 문자열, keyboard focus와 reduced motion을 반영합니다. | `app/styles.css` |
| 14 | Vitest가 browser E2E와 생성 디렉터리를 단위 테스트 대상으로 잘못 수집하지 않게 설정합니다. | `vitest.config.ts` |
| 14.1 | query 정규화와 server bootstrap이 같은 입력을 사용하는지 검사합니다. | `tests/query-and-bootstrap.test.ts` |
| 14.2 | 잘못된 외부 값과 중복 id를 거부하는지 검사합니다. | `tests/catalog-contract.test.ts` |
| 14.3 | 검색 상태 전이가 마지막 정상 결과를 잃지 않는지 검사합니다. | `tests/catalog-model.test.ts` |
| 14.4 | 새 요청과 cancel이 이전 signal과 generation을 무효화하는지 검사합니다. | `tests/request-coordinator.test.ts` |
| 14.5 | 저장소와 Route Handler가 검색, `version` conflict와 HTTP status를 같은 규칙으로 처리하는지 검사합니다. | `tests/projects-api.test.ts` |
| 14.6 | health 공개 필드와 reset route 조건이 운영 설정에서 우회되지 않는지 검사합니다. | `tests/production-contract.test.ts` |
| 14.7 | 성능 예산 파일에 허용한 key와 양수 값만 있는지 검사합니다. | `tests/performance-budget.test.ts` |
| 15 | Playwright가 고유 port의 production server를 사용하고 실패 artifact를 남기도록 설정합니다. | `playwright.config.ts` |
| 15.1 | 사용 가능한 port를 선택해 Playwright에 전달하고 child process 종료 상태를 상위 process에 전달합니다. | `scripts/run-playwright.mjs` |
| 15.2 | URL 복원, 늦은 응답 차단, 잘못된 응답 거부, 저장 실패와 `409` 복구를 browser에서 검사합니다. | `tests/e2e/catalog-concurrency.spec.ts` |
| 15.3 | keyboard, focus, semantic HTML, reduced motion, 좁은 화면과 성능 예산을 browser에서 검사합니다. | `tests/e2e/accessibility-performance.spec.ts` |
| 16 | 운영 서버를 직접 시작해 health, HTML, API, canary 비노출과 process cleanup을 검사합니다. | `scripts/smoke-production.mjs` |

`12.1`의 route type 생성은 저장소가 사용하는 Next.js 버전에서 제공하는 type generation 방식을 따릅니다. 생성된 `.next/types` 같은 build artifact는 source가 아니므로 일반적으로 source control에 포함하지 않습니다.

이 문서에 framework 초기화 과정의 확인 가능한 기록이 없으므로 별도의 `Implementation 0`은 두지 않습니다.

## 범위와 제한

이 프로그램이 의도적으로 다루지 않는 범위는 다음과 같습니다.

- 데이터는 서버 프로세스 메모리에만 있으므로 process를 다시 시작하면 초기 상태로 돌아갑니다.
- 여러 server instance 사이에서 `version`과 변경 내용을 공유하지 않습니다.
- 실제 database transaction이나 distributed lock을 구현하지 않습니다.
- 인증과 사용자별 authorization을 구현하지 않습니다.
- API는 `page` query를 지원하지만 화면에는 pagination UI가 없습니다.
- 검색을 새로 제출하면 항상 `page=1`로 돌아갑니다.
- 테스트 데이터 초기화 Route Handler는 자동화 테스트 전용이며 일반 운영 API가 아닙니다.
- server-only canary 검사는 모든 secret 노출을 증명하는 보안 검사가 아니라 대표적인 accidental exposure를 찾는 regression test입니다.
- JavaScript와 DOM 예산은 실제 사용자 성능 지표 전체를 대신하지 않습니다.
- `npm run test:e2e`, `npm run smoke`, `npm run verify`를 실행하려면 같은 checkout에서 운영 build와 실제 start가 가능해야 합니다.

## 검증 실패 시 다시 볼 문서

이 프로그램은 Guide를 외우는 용도가 아니므로 실패한 영역만 다시 확인합니다.

```text
실행 환경, package, route 추적
→ 01-project-onboarding.md

state source of truth, 외부 입력, draft
→ 02-ui-and-state-architecture.md

history, Effect, race, optimistic update
→ 03-nextjs-data-effects-and-concurrency.md

test 위치, accessibility, responsive, performance
→ 04-testing-accessibility-and-performance.md

health, release, secret, smoke, process lifecycle
→ 05-production-runtime-contract.md
```
