# Resource Directory

`Resource Directory`는 구조가 같은 Markdown 자료를 build에서 검사하고, 목록·분류·상세 page와 JSON 파일을 정적으로 생성하는 Astro application입니다. 기본 page는 HTML만 보내며, 상세 page의 즐겨찾기 button 하나만 React로 hydration합니다.

이 project는 특정 사업이나 서비스의 예제가 아닙니다. Astro project를 한 번 완성한 뒤 다음 능력을 다른 문맥에서 다시 확인하는 post-project competency artifact입니다.

- Content Collection loader와 schema validation
- content id를 사용한 static dynamic route 생성
- Astro component, layout, typed props와 slot 조합
- Markdown body를 상세 page에서만 render
- local image import와 optimized asset 생성
- 필요한 control 하나만 React island로 hydration
- static JSON endpoint
- canonical metadata와 custom 404
- unit, production browser와 static artifact 검증

완성된 application으로 바로 실행할 수 있으며, 역량 검증에는 README·공개 동작·tests를 기준으로 동일 기능을 별도 작업 공간에서 다시 구현하는 방식을 사용할 수 있습니다.

## 주요 기능

- `src/content/resources/*.md`의 metadata를 build 전에 검사합니다.
- Draft를 제외한 자료만 공개 page와 JSON에 포함합니다.
- 추천 여부, 수정일 또는 게시일, 제목 순으로 자료를 정렬합니다.
- 전체 목록과 `web`, `data`, `tooling` 분류 page를 생성합니다.
- 각 content id에 대응하는 상세 page를 생성합니다.
- Markdown heading으로 상세 page 목차를 만듭니다.
- 같은 분류의 관련 자료를 최대 세 개 표시합니다.
- 상세 page의 즐겨찾기를 `localStorage`에 저장합니다.
- `resources.json`에는 본문을 제외한 공개 summary만 내보냅니다.
- Home page에는 browser JavaScript를 보내지 않습니다.
- 상세 page에는 React island를 정확히 하나만 사용합니다.

## 실행 모델

```text
Markdown files
→ Content Collection loader
→ schema validation
→ published resource model
→ sort/filter/serialize
→ static pages and resources.json
```

Browser에서 실행되는 코드는 다음 부분으로 제한합니다.

```text
FavoriteButton
→ client:load
→ localStorage read/write
```

나머지 component script, content query와 Markdown render는 build 중 실행됩니다.

## Project 구성

```text
.
├── astro.config.mjs
├── package.json
├── performance-budget.json
├── playwright.config.ts
├── public/
│   ├── favicon.svg
│   └── robots.txt
├── scripts/
│   ├── run-playwright.mjs
│   └── smoke-static-build.mjs
├── src/
│   ├── assets/
│   ├── components/
│   ├── content/
│   │   └── resources/
│   ├── content.config.ts
│   ├── layouts/
│   ├── lib/
│   ├── pages/
│   └── styles/
├── tests/
│   ├── e2e/
│   └── *.test.ts
├── tsconfig.json
└── vitest.config.ts
```

## 요구 환경

- Node.js `22.12.0` 이상 23 미만 또는 24 이상 25 미만
- npm
- Playwright Chromium은 E2E 실행 전에 별도로 설치

`.nvmrc`는 Node.js `24.19.0`을 지정합니다.

## 설치

```sh
nvm use
npm install
npx playwright install chromium
```

## 개발 서버

```sh
npm run dev
```

기본 개발 URL은 Astro가 출력한 주소를 사용합니다.

## Production build와 preview

```sh
npm run build
npm run preview
```

Build 결과는 `dist/`에 생성됩니다. 이 project에는 adapter가 없으므로 page와 `resources.json`은 모두 build에서 생성됩니다.

## 검사

### 형 검사와 unit test

```sh
npm run check
```

`astro check` 뒤 Vitest를 실행합니다.

### Production browser test

```sh
npm run test:e2e
```

Production build를 만든 뒤 사용 가능한 port에서 `astro preview`를 실행하고 Playwright로 다음을 확인합니다.

- route, metadata와 JSON 결과 일치
- 분류별 자료 제한
- Home page island 0개
- 상세 page island 1개
- 즐겨찾기 저장, 저장 실패 안내와 reload 복원
- keyboard focus 표시
- JavaScript, DOM과 island 예산
- 320px 화면과 reduced motion

### Static build smoke

```sh
npm run smoke
```

다음을 확인합니다.

- 핵심 HTML과 JSON file 존재
- `resources.json`의 공개 field
- private environment canary가 `dist/`에 없음
- Home page에 island가 없음
- 상세 page에 island가 하나만 있음
- preview process가 성공·실패 뒤 종료됨

### 전체 검사

```sh
npm run verify
```

## 공개 Route

| URL | 생성 방식 | 내용 |
| --- | --- | --- |
| `/` | static page | Home, 분류 수, 추천 자료 |
| `/resources/` | static page | 공개 자료 전체 목록 |
| `/resources/[id]/` | `getStaticPaths()` | Markdown 상세 page |
| `/categories/[category]/` | `getStaticPaths()` | 분류별 목록 |
| `/resources.json` | static endpoint | 공개 summary JSON |
| `/404.html` | static page | 찾을 수 없는 URL 안내 |

## Content 작성

자료는 `src/content/resources/*.md`에 둡니다.

```yaml
---
title: HTTP 상태 코드 빠른 참조
summary: 상태 코드의 숫자보다 실패 종류와 다음 행동을 먼저 구분합니다.
category: web
tags:
  - HTTP
  - 오류 처리
publishedAt: 2026-02-12
updatedAt: 2026-07-03
featured: true
draft: false
---
```

검사하는 field:

| Field | 조건 |
| --- | --- |
| `title` | 1~80자 |
| `summary` | 1~180자 |
| `category` | `web`, `data`, `tooling` 중 하나 |
| `tags` | 1~6개, 각 1~24자 |
| `publishedAt` | date로 변환 가능 |
| `updatedAt` | 선택, date로 변환 가능 |
| `featured` | 선택, 기본값 `false` |
| `draft` | 선택, 기본값 `false` |
| `sourceUrl` | 선택, 유효한 URL |

File name은 공개 content id와 URL에 사용됩니다. 공개 뒤에는 단순 문구 변경을 이유로 file name을 바꾸지 않습니다.

## Browser JavaScript 사용 원칙

Astro component와 React component는 기본적으로 정적 HTML을 만들 수 있습니다. 이 project에서는 실제 browser state가 필요한 `FavoriteButton`에만 `client:load`를 사용합니다.

`client:load`를 선택한 이유는 button이 상세 page 첫 화면에 바로 보이고 사용자가 즉시 누를 수 있어야 하기 때문입니다. Home, 목록, 분류, Markdown 본문과 관련 자료에는 hydration을 사용하지 않습니다.

`localStorage` 값은 이전 version이나 사용자가 수정한 문자열일 수 있으므로 JSON을 `unknown`으로 읽습니다. Array가 아니거나 string이 아닌 항목은 버리고 최대 200개만 사용합니다. 읽기·쓰기 실패는 즐겨찾기 widget 안에서 처리하며 article 본문은 계속 읽을 수 있습니다.

## Performance budget

`performance-budget.json`은 상세 page의 초기 비용을 제한합니다.

```json
{
  "maximumDetailJavaScriptBytes": 220000,
  "maximumDetailDomNodes": 220,
  "maximumHydratedIslands": 1
}
```

예산은 project 규모와 dependency version이 바뀌면 production browser 측정을 근거로 조정합니다. 단순히 검사를 통과하도록 숫자를 올리지 않습니다.

## 주요 설계 결정

### Content query를 한 함수에 모읍니다

모든 page와 endpoint는 `getPublishedResources()`를 사용합니다. Draft 제외, 정렬과 summary 변환이 서로 달라져 목록·상세·JSON이 다른 자료를 보이는 문제를 막습니다.

### ID와 표시 이름을 분리합니다

Category URL에는 `web`, `data`, `tooling`을 사용하고 화면에는 `웹`, `데이터`, `도구`를 표시합니다. 화면 문구가 바뀌어도 공개 URL을 유지할 수 있습니다.

### Markdown body는 상세 page에서만 compile합니다

목록, 분류와 JSON은 title·summary·tag만 사용합니다. Content body를 card props나 endpoint response에 넣지 않습니다.

### Static output을 유지합니다

이 project에는 사용자별 HTML, private database와 request-time mutation이 없습니다. Adapter와 server runtime을 추가하지 않고 build output만 배포합니다.

### Production artifact를 직접 검사합니다

Unit test만으로 route file, island 수와 secret 노출을 확인할 수 없습니다. Build output 검사, Playwright와 preview process smoke를 별도로 실행합니다.

## Implementation Order

아래 순서는 file 배치나 Git commit 수가 아니라 완성된 application을 처음부터 구성할 때의 기술 의존 순서입니다. 번호는 project 전체에서 한 번씩만 사용합니다.

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 0 | Static Astro application configuration | `astro.config.mjs` |
| 1 | Content metadata schema | `src/content.config.ts` |
| 1-1 | Local Markdown content loader | `src/content.config.ts` |
| 2 | Stable resource category model | `src/lib/resource-model.ts` |
| 2-1 | Deterministic resource ordering | `src/lib/resource-model.ts` |
| 2-2 | Public summary serialization | `src/lib/resource-model.ts` |
| 2-3 | Category counts and related-item selection | `src/lib/resource-model.ts` |
| 3 | Published content query | `src/lib/resources.ts` |
| 4 | Shared title and canonical generation | `src/lib/seo.ts` |
| 5 | Shared document layout | `src/layouts/SiteLayout.astro` |
| 5-1 | Resource summary card | `src/components/ResourceCard.astro` |
| 5-2 | Category navigation | `src/components/CategoryNav.astro` |
| 6 | Home-page content composition | `src/pages/index.astro` |
| 6-1 | Optimized local hero image | `src/pages/index.astro` |
| 6-2 | Complete resource archive | `src/pages/resources/index.astro` |
| 7 | Static detail-route generation | `src/pages/resources/[id].astro` |
| 7-1 | Detail-only Markdown rendering | `src/pages/resources/[id].astro` |
| 7-2 | Finite category-route generation | `src/pages/categories/[category].astro` |
| 8 | Browser favorite storage | `src/components/FavoriteButton.tsx` |
| 8-1 | Single immediately hydrated island | `src/pages/resources/[id].astro` |
| 9 | Static public JSON endpoint | `src/pages/resources.json.ts` |
| 10 | Custom static 404 page | `src/pages/404.astro` |
| 11 | Responsive and accessible visual rules | `src/styles/global.css` |
| 12 | Unit verification configuration | `vitest.config.ts` |
| 12-1 | Resource ordering and serialization tests | `tests/resource-model.test.ts` |
| 12-2 | Metadata helper tests | `tests/seo.test.ts` |
| 12-3 | Performance-budget schema test | `tests/performance-budget.test.ts` |
| 13 | Production browser runtime | `playwright.config.ts` |
| 13-1 | Isolated Playwright port selection | `scripts/run-playwright.mjs` |
| 13-2 | Route and endpoint browser verification | `tests/e2e/static-navigation.spec.ts` |
| 13-3 | Island, accessibility and performance verification | `tests/e2e/island-accessibility-performance.spec.ts` |
| 14 | Static artifact and preview smoke verification | `scripts/smoke-static-build.mjs` |

## 역량 검증 방식

외부 실제 Astro project를 PASS한 뒤 다음 순서를 사용합니다.

```text
README, public behavior and tests 확인
→ Guide를 다시 읽지 않고 별도 작업 공간에서 구현
→ npm run verify
→ PASS: 역량 확인
→ FAIL: 실패 영역 문서만 다시 읽기
→ 같은 검사 재실행
```

Rewind 기준:

| 실패 | 다시 볼 문서 |
| --- | --- |
| build/static route/component | [`docs/01`](../../docs/01-runtime-rendering-and-project-model.md), [`docs/02`](../../docs/02-components-pages-and-composition.md) |
| island와 browser storage | [`docs/03`](../../docs/03-islands-and-client-execution.md), [`docs/12`](../../docs/12-react-integration.md) |
| Content Collection/Markdown | [`docs/10`](../../docs/10-content-collections.md), [`docs/11`](../../docs/11-markdown-mdx-and-content-rendering.md) |
| metadata/image | [`docs/14`](../../docs/14-images-fonts-and-seo.md) |
| testing/performance | [`docs/17`](../../docs/17-testing-and-performance.md) |
| static deployment/smoke | [`docs/18`](../../docs/18-deployment-and-production-checks.md) |

## 범위와 제한

이 project는 다음을 의도적으로 포함하지 않습니다.

- adapter와 on-demand rendering
- authentication과 authorization
- database와 migration
- Astro Actions와 runtime mutation
- remote CMS와 webhook
- MDX
- realtime connection
- search index
- pagination
- production domain과 analytics

이 기능들은 Astro의 project-entry 전제조건이 아닙니다. 실제 project가 해당 문제에 도달했을 때 관련 JIT 문서를 사용합니다.
