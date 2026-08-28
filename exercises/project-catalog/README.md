# Project Catalog

`Project Catalog`는 Next.js App Router로 만든 프로젝트 검색·편집 애플리케이션입니다. 검색 조건을 URL로 공유할 수 있으며, Server Component가 첫 화면의 데이터를 만들고 Client Component가 이후의 검색과 제목 변경을 처리합니다.

HTTP 응답은 필요한 필드와 허용 범위를 확인한 뒤에만 화면에 반영합니다. 제목을 저장할 때는 현재 `version`을 함께 전송해 다른 변경이 먼저 저장되었는지 확인합니다. 일반적인 저장 실패에서는 마지막 서버 값으로 되돌리고, `409 Conflict`에서는 최신 서버 값과 사용자가 작성한 초안을 함께 남깁니다.

## 이 저장소에서의 사용 시점

이 프로그램은 실제 프로젝트에 들어가기 전에 풀어야 하는 과제가 아닙니다. 외부의 실제 프로젝트를 통과한 뒤, Guide를 다시 읽지 않고 다음 능력을 재현할 수 있는지 확인하는 역량 검증용 프로그램입니다.

- URL 쿼리와 서버의 첫 렌더링이 같은 입력을 사용하도록 구성합니다.
- 외부 JSON을 `unknown`으로 받고 필요한 값을 검사합니다.
- 요청 중이거나 요청이 실패해도 마지막으로 확인한 결과를 유지합니다.
- 이전 요청의 늦은 응답이 최신 화면을 덮지 못하게 합니다.
- 낙관적 갱신, 일반 실패와 `version` 충돌을 서로 다르게 처리합니다.
- 키보드 조작과 초점 이동을 실제 브라우저에서 확인합니다.
- 운영 서버를 직접 실행해 health 응답과 비밀값 비노출을 검사합니다.

## 주요 기능

- `q`, `status`, `page` 쿼리를 정규화하고 첫 화면과 URL을 같은 조건으로 복원합니다.
- 검색 조건을 브라우저 history에 기록하고 back/forward 이동에서 입력값과 결과를 다시 맞춥니다.
- `AbortController`와 증가하는 generation을 함께 사용해 이전 검색 결과를 버립니다.
- 검색 실패나 형식이 잘못된 JSON 응답이 와도 마지막 정상 결과를 유지합니다.
- 제목을 먼저 화면에 표시하고, 저장 실패 시 요청 전 서버 값으로 되돌립니다.
- `409 Conflict`에서는 최신 서버 값과 사용자가 작성한 초안을 함께 보존합니다.
- 키보드 편집, 초점 복구, `aria-live`, `:focus-visible`, motion 감소 설정과 좁은 화면을 지원합니다.
- health endpoint, 테스트 전용 초기화 Route Handler, 단위 테스트, 브라우저 E2E, 성능 예산과 운영 smoke test를 포함합니다.

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

- `lib/project-types.ts`
  - Route Handler, Server Component와 Client Component가 함께 사용하는 직렬화 가능한 타입을 정의합니다.
- `lib/projects.ts`
  - 서버 프로세스의 `Map`에 프로젝트와 `version`을 저장합니다.
  - 검색 결과와 수정 결과는 복사본으로 반환해 호출자가 저장된 값을 직접 바꾸지 못하게 합니다.
- `lib/catalog-contract.ts`
  - URL 쿼리를 길이와 허용값에 맞게 정규화합니다.
  - HTTP 응답의 필드, 숫자 범위, enum과 중복 id를 확인한 뒤 내부 타입으로 변환합니다.
- `lib/catalog-model.ts`
  - `ready`, `empty`, `pending`, `error` 상태만 허용합니다.
  - 새 요청 중이거나 요청이 실패한 경우 마지막 정상 결과를 계속 제공합니다.
- `lib/request-coordinator.ts`
  - 새 요청이 시작되면 이전 `AbortController`를 중단합니다.
  - 증가하는 generation을 비교해 늦게 끝난 작업의 결과 적용을 막습니다.
- `app/page.tsx`
  - URL 쿼리를 한 번 읽고 같은 값으로 첫 검색 조건과 결과를 계산합니다.
- `app/project-catalog.tsx`
  - 검색 입력, 결과, 안내 문구, 요청 생명주기와 편집 상태를 관리합니다.
  - back/forward 이동, 검색 실패, 낙관적 갱신과 초점 이동을 처리합니다.
- Route Handler
  - 검색, `version` 기반 제목 변경, health와 테스트 데이터 초기화를 각각 처리합니다.
- `tests/`, Playwright와 smoke script
  - 순수 함수, HTTP 응답, 실제 브라우저 동작과 운영 서버 실행을 서로 다른 단계에서 검사합니다.

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

의존성을 잠금 파일로 고정한 환경에서는 `npm install` 대신 해당 환경에서 정한 고정 설치 명령을 사용합니다.

## 실행

개발 서버를 시작합니다.

```sh
npm run dev
```

기본 주소는 `http://localhost:3000`입니다. 검색 조건을 URL에 직접 넣을 수 있습니다.

```text
/?q=Storage&status=active&page=1
```

운영 서버는 빌드한 뒤 실행합니다.

```sh
npm run build
APP_RELEASE=local-build npm run start
```

## HTTP API

| Method | Path | 처리 내용 |
| --- | --- | --- |
| `GET` | `/api/projects` | `q`, `status`, `page`를 검사하고 검색 결과를 반환합니다. |
| `PATCH` | `/api/projects/:id` | `{ "title": string, "version": number }`를 검사하고 현재 `version`일 때만 제목을 바꿉니다. |
| `GET` | `/api/health` | `{ "status", "release" }`만 `no-store`로 반환합니다. |
| `POST` | `/api/test/reset` | 테스트 모드와 토큰이 모두 맞을 때만 프로세스 내 데이터를 초기화합니다. |

`PATCH`에 오래된 `version`을 보내면 `409`와 최신 프로젝트를 반환합니다. 프로젝트가 없으면 `404`, 요청 본문이 잘못되면 `400`을 반환합니다.

## 환경 변수

| 이름 | 용도 | 기본값 |
| --- | --- | --- |
| `APP_RELEASE` | health 응답에 표시할 릴리스 식별자 | `local` |
| `PLAYWRIGHT` | 값이 `1`이면 테스트 데이터 초기화를 허용하는 테스트 모드 중 하나 | 없음 |
| `CATALOG_TEST_RESET_TOKEN` | 초기화 요청의 헤더와 비교할 토큰 | 없음 |

`/api/test/reset`은 다음 두 조건을 모두 만족할 때만 동작합니다.

1. `NODE_ENV=test` 또는 `PLAYWRIGHT=1`
2. `x-catalog-test-token` 헤더와 `CATALOG_TEST_RESET_TOKEN`이 일치

그 외에는 Route Handler의 존재 여부를 드러내지 않도록 `404`를 반환합니다.

## 검증

Next.js route type을 생성한 뒤 TypeScript를 검사합니다.

```sh
npm run typecheck
```

Vitest 단위 테스트와 Route Handler 테스트를 실행합니다.

```sh
npm test
```

운영 빌드 뒤 Playwright 브라우저 테스트를 실행합니다. 실행 스크립트는 사용 가능한 포트를 찾아 Playwright에 전달합니다.

```sh
npm run test:e2e
```

운영 smoke test는 실제 `next start` 프로세스를 실행해 다음을 확인합니다.

- health의 공개 필드와 release
- root HTML의 핵심 heading
- 프로젝트 API의 최소 응답 형식
- 서버 전용 canary가 health, HTML와 초기 JavaScript에 없는지
- 성공과 실패 뒤 하위 프로세스가 정리되는지

```sh
npm run smoke
```

전체 검증을 순서대로 실행합니다.

```sh
npm run verify
```

## 성능 예산

`performance-budget.json`은 브라우저 테스트가 확인할 두 값을 정의합니다.

- 첫 route가 받은 JavaScript 응답 본문의 합계: `800000` byte 이하
- 첫 화면의 DOM element 수: `180` 이하

예산 파일의 키와 값도 단위 테스트로 확인합니다. 숫자를 변경할 때는 어떤 JavaScript 또는 DOM이 늘었는지 먼저 확인합니다.

## 주요 구현 선택

### 마지막 정상 결과를 유지합니다

`pending`과 `error`는 별도의 결과를 만들지 않고 `previous`를 가리킵니다. 새 요청 중이거나 응답 형식 검사에 실패해도 마지막으로 정상 확인한 목록이 화면에 남습니다.

### abort와 generation을 함께 사용합니다

`AbortController`는 전송 중단을 요청합니다. 그러나 이미 끝난 Promise나 abort를 따르지 않는 callback까지 없애지는 못합니다. 각 요청에 증가하는 generation을 부여하고, 응답을 화면에 반영하기 직전에 최신 generation인지 다시 확인합니다.

### 서버 값과 입력 초안을 분리합니다

목록에는 변경할 제목을 먼저 표시하지만 편집기의 `draftTitle`은 별도로 유지합니다.

- 일반 실패: 목록을 요청 전 서버 값으로 되돌리고 입력 초안을 유지합니다.
- `409 Conflict`: 응답의 최신 서버 값을 목록에 반영하고 입력 초안을 유지합니다.
- 성공: 응답의 title과 새 `version`을 최종 값으로 사용합니다.

### 프로세스 내 저장소를 사용합니다

이 프로그램은 별도 데이터베이스 없이 검색, `version` 검사와 충돌 처리를 재현하기 위해 서버 프로세스의 `Map`을 사용합니다. 테스트 데이터 초기화도 같은 `Map`을 되돌리므로 Route Handler와 테스트가 서로 다른 저장소를 참조하지 않습니다.

## Implementation Order

아래 순서는 파일 배치나 Git history가 아닙니다. 완성된 프로그램을 처음부터 만들 때 필요한 데이터와 동작의 의존 순서입니다. 번호는 프로젝트 전체에서 한 번만 사용합니다.

| Order | 구현 내용 | 주요 파일 |
| ---: | --- | --- |
| 1 | Route Handler와 Server/Client Component가 함께 주고받을 수 있도록 직렬화 가능한 타입만 정의합니다. | `lib/project-types.ts` |
| 2 | 서버 프로세스가 프로젝트와 `version`을 보관하며, 호출자에게는 복사본만 돌려줍니다. | `lib/projects.ts` |
| 2-1 | `q`, `status`, `page`를 적용해 현재 페이지의 결과와 전체 개수를 계산합니다. | `lib/projects.ts` |
| 2-2 | 요청의 `version`이 현재 값과 같을 때만 제목과 `version`을 함께 갱신합니다. | `lib/projects.ts` |
| 2-3 | 각 테스트가 같은 초기 데이터에서 시작하도록 프로세스 내 저장소를 되돌립니다. | `lib/projects.ts` |
| 3 | 외부 입력 형식 오류를 모두 `ContractError`로 바꿔 호출부가 한 방식으로 처리하게 합니다. | `lib/catalog-contract.ts` |
| 3-1 | URL 쿼리를 허용 범위로 정규화하며, 다시 직렬화해도 같은 값이 나오게 합니다. | `lib/catalog-contract.ts` |
| 3-2 | `unknown` JSON의 필드, 숫자 범위와 중복 id를 확인한 뒤 내부 타입으로 바꿉니다. | `lib/catalog-contract.ts` |
| 4 | `ready`, `empty`, `pending`, `error`만 허용하며, 요청 중이거나 실패해도 마지막 정상 결과를 보존합니다. | `lib/catalog-model.ts` |
| 5 | 문서 언어와 메타데이터를 지정하고 전역 스타일시트를 불러옵니다. | `app/layout.tsx` |
| 6 | URL 쿼리를 한 번만 읽어 첫 검색 조건과 결과가 서로 어긋나지 않게 합니다. | `app/page.tsx` |
| 7 | 새 요청이 이전 요청을 중단하며, generation 비교로 늦게 끝난 결과를 버립니다. | `lib/request-coordinator.ts` |
| 8 | 검색 초안, 확인된 결과, 안내 문구와 요청 생명주기를 `ProjectCatalog`가 함께 관리합니다. | `app/project-catalog.tsx` |
| 8-1 | 검색 제출만 history에 기록하고, 뒤로/앞으로 이동에서는 URL을 읽어 최신 검증 응답만 반영합니다. | `app/project-catalog.tsx` |
| 8-2 | 제목을 먼저 표시하되, 실패하면 이전 서버 값으로 되돌리고 충돌하면 최신 서버 값과 입력 초안을 함께 남깁니다. | `app/project-catalog.tsx` |
| 9 | 편집 초안과 저장 상태를 관리하며, 열기·취소·성공·실패 뒤 초점을 알맞은 요소로 옮깁니다. | `app/project-catalog.tsx` |
| 10 | 검색 쿼리를 검사한 결과를 캐시하지 않는 JSON 응답으로 반환합니다. | `app/api/projects/route.ts` |
| 10-1 | 제목과 `version`을 검사하고 성공, 입력 오류, 없음과 충돌을 HTTP 상태 코드로 구분합니다. | `app/api/projects/[id]/route.ts` |
| 11 | 테스트 모드와 토큰이 모두 맞을 때만 데이터를 초기화하며, 나머지는 `404`로 숨깁니다. | `app/api/test/reset/route.ts` |
| 12 | 현재 릴리스와 `status`만 담은 캐시 금지 응답을 제공합니다. | `app/api/health/route.ts` |
| 12-1 | Route Handler를 추가한 뒤 `next typegen`으로 라우트 타입을 만들고 `tsc`로 검사합니다. | `app/api/health/route.ts` |
| 13 | 좁은 화면과 긴 문자열에서도 가로 넘침을 막고, 키보드 초점과 애니메이션 감소 설정을 반영합니다. | `app/styles.css` |
| 14 | Vitest가 브라우저 E2E 파일과 생성 디렉터리를 단위 테스트 대상에서 제외하도록 설정합니다. | `vitest.config.ts` |
| 14-1 | 잘못된 쿼리를 정규화하고 서버 첫 화면의 조건과 결과가 같은 입력을 쓰는지 확인합니다. | `tests/query-and-bootstrap.test.ts` |
| 14-2 | 필드 오류와 중복 id를 거절해 잘못된 외부 값이 내부 상태에 들어오지 못하게 확인합니다. | `tests/catalog-contract.test.ts` |
| 14-3 | 요청 상태 전이와 항목 교체가 마지막 정상 결과를 잃지 않는지 확인합니다. | `tests/catalog-model.test.ts` |
| 14-4 | 새 요청과 취소가 이전 signal과 generation을 무효화하는지 확인합니다. | `tests/request-coordinator.test.ts` |
| 14-5 | 저장소와 Route Handler가 검색, `version` 충돌과 HTTP 상태 코드를 같은 규칙으로 처리하는지 확인합니다. | `tests/projects-api.test.ts` |
| 14-6 | health 응답의 공개 필드와 테스트 초기화 조건이 운영 설정에서 우회되지 않는지 확인합니다. | `tests/production-contract.test.ts` |
| 14-7 | 성능 예산 파일에 허용한 키와 양수 값만 있는지 확인합니다. | `tests/performance-budget.test.ts` |
| 15 | Playwright가 매 실행마다 고유 포트에서 운영 서버를 시작하고 실패 자료를 남기도록 설정합니다. | `playwright.config.ts` |
| 15-1 | 사용 가능한 포트를 골라 Playwright에 넘기고, 하위 프로세스의 종료 상태를 그대로 반환합니다. | `scripts/run-playwright.mjs` |
| 15-2 | URL 복원, 늦은 응답 차단, 잘못된 응답 거절, 저장 실패와 `409` 복구를 브라우저에서 확인합니다. | `tests/e2e/catalog-concurrency.spec.ts` |
| 15-3 | 키보드 초점, 의미 있는 HTML, 애니메이션 감소, 좁은 화면과 JavaScript·DOM 예산을 브라우저에서 확인합니다. | `tests/e2e/accessibility-performance.spec.ts` |
| 16 | 운영 서버를 직접 띄워 health, HTML, API, 비밀값 비노출과 프로세스 정리를 확인합니다. | `scripts/smoke-production.mjs` |

`Implementation 12-1`은 Route Handler를 추가한 뒤 `npm run typecheck`가 실행하는 `next typegen` 단계입니다. 생성된 `.next/types`는 빌드 결과이므로 소스에 포함하지 않습니다. 확인 가능한 framework 초기화 기록이 없으므로 `Implementation 0`은 사용하지 않습니다.

## 범위와 제한

- 데이터는 서버 프로세스 메모리에만 있으므로 프로세스를 다시 시작하면 초기 상태로 돌아갑니다.
- 여러 서버 인스턴스 사이에서 `version`과 변경 내용을 공유하지 않습니다.
- 인증과 사용자별 권한은 구현하지 않습니다.
- API는 `page` 쿼리를 지원하지만 화면에는 페이지 이동 UI가 없습니다. 검색을 제출하면 항상 `page=1`로 돌아갑니다.
- 테스트 데이터 초기화 Route Handler는 자동화 테스트 전용이며 일반 운영 API가 아닙니다.
- `npm run test:e2e`, `npm run smoke` 또는 `npm run verify`를 실행하려면 같은 디렉터리에서 운영 빌드가 가능해야 합니다.
