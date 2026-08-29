# 학습 로드맵

이 문서는 Astro 개발 트랙의 정확한 학습 순서와 완료 조건을 정리합니다. 실제 프로젝트는 이 저장소 밖에서 진행합니다. `docs/`는 프로젝트 진입 전에 읽을 최소 문서와 구현 중 찾아볼 자료를 제공하며, `exercises/`는 실제 프로젝트를 마친 뒤 역량을 확인하는 프로그램을 제공합니다.

```text
Stable Core Guide
→ Actual Project
→ JIT Guide as needed
→ Project PASS
→ Competency Suite without Guide
→ Rewind where needed
```

## 대상 독자

다음 작업을 한 번 이상 해 본 개발자를 대상으로 합니다.

- HTML 문서와 form을 직접 작성했습니다.
- Flexbox 또는 Grid로 responsive layout을 만들었습니다.
- JavaScript module과 `async` 함수를 사용했습니다.
- TypeScript로 object와 function type을 작성했습니다.
- JSON API를 호출하고 반환값을 처리했습니다.
- Node.js 프로젝트의 `package.json`과 script를 사용했습니다.

다음 항목이 낯설다면 별도의 기초 과정에서 먼저 보완합니다.

- semantic HTML과 접근 가능한 이름
- CSS cascade, box model과 responsive unit
- ESM import/export
- Promise, `async`, `await`
- TypeScript union, `unknown`, narrowing
- HTTP URL, method, header와 status

## 1. Stable Core

외부 실제 프로젝트를 시작하기 전에 다음 세 문서만 읽습니다.

### `01-runtime-rendering-and-project-model.md`

- Astro project의 주요 디렉터리와 설정 파일을 확인합니다.
- dev, build, preview의 차이를 확인합니다.
- component script가 build 또는 server에서 실행되고 browser로 전달되지 않는다는 점을 이해합니다.
- static output과 on-demand rendering을 구분합니다.
- integration과 adapter의 용도가 다르다는 점을 확인합니다.

### `02-components-pages-and-composition.md`

- `.astro` component script와 template을 구분합니다.
- typed props, slot, layout과 scoped style을 사용합니다.
- `src/pages/`의 file-based route와 `getStaticPaths()`를 이해합니다.
- page, layout과 component를 변경 이유에 맞게 나눕니다.

### `03-islands-and-client-execution.md`

- Astro page가 기본적으로 browser JavaScript를 추가하지 않는다는 점을 이해합니다.
- 일반 `<script>`, Web API와 UI framework component 가운데 필요한 방식을 고릅니다.
- `client:*` directive가 hydration 시점을 정한다는 점을 이해합니다.
- page 전체를 하나의 React island로 바꾸지 않고 상호작용이 필요한 부분만 분리합니다.

Stable Core의 정확한 목록은 다음과 같습니다.

```text
01-runtime-rendering-and-project-model.md
02-components-pages-and-composition.md
03-islands-and-client-execution.md
```

commerce, blog, directory, portfolio, documentation 등 프로젝트 종류가 바뀌어도 이 목록은 유지합니다. 인증, database, realtime과 결제는 해당 기능이 실제로 필요할 때 JIT로 다룹니다.

## 2. Actual Project

Stable Core를 읽은 뒤에는 외부 실제 프로젝트를 시작합니다. competency exercise를 먼저 구현하지 않습니다.

프로젝트에 들어가면 다음 순서로 확인합니다.

1. Node.js, package manager, lockfile과 scripts를 확인합니다.
2. `astro.config.mjs`의 output, `site`, `base`, integrations와 adapter를 확인합니다.
3. `src/pages/`에서 URL과 page file을 연결합니다.
4. 콘텐츠와 외부 데이터가 build에서 읽히는지 요청마다 읽히는지 확인합니다.
5. browser에 전송되는 `<script>`와 hydrated island를 찾습니다.
6. 가장 작은 사용자 결과 하나를 구현하고 build 결과에서 확인합니다.

## 3. JIT / Rewind

다음 문서는 관련 문제가 실제로 등장했을 때 읽습니다. 프로젝트를 마친 뒤 competency exercise가 실패하면 같은 문서의 관련 절을 Rewind 자료로 사용합니다.

| 문서 | 읽는 시점 |
| --- | --- |
| `10-content-collections.md` | 같은 metadata를 가진 문서나 data entry가 여러 개 생겼을 때 |
| `11-markdown-mdx-and-content-rendering.md` | Markdown body, MDX component 또는 authoring 규칙이 필요할 때 |
| `12-react-integration.md` | React component를 재사용하거나 browser state가 필요할 때 |
| `13-data-loading-and-runtime-validation.md` | CMS, API, storage와 remote data를 읽을 때 |
| `14-images-fonts-and-seo.md` | image 처리, metadata, canonical, RSS 또는 sitemap을 만들 때 |
| `15-actions-forms-and-endpoints.md` | form submission, JSON/XML file 또는 runtime command가 필요할 때 |
| `16-on-demand-rendering-and-adapters.md` | 요청별 HTML, cookie, session, database 또는 server island가 필요할 때 |
| `17-testing-and-performance.md` | 검사 위치, browser E2E, JavaScript와 DOM 예산을 정할 때 |
| `18-deployment-and-production-checks.md` | static host 또는 adapter runtime에 배포할 때 |
| `90-practical-checklist.md` | 구현·review·장애 분석·Rewind 범위를 좁힐 때 |

JIT/Rewind의 정확한 목록은 다음과 같습니다.

```text
10-content-collections.md
11-markdown-mdx-and-content-rendering.md
12-react-integration.md
13-data-loading-and-runtime-validation.md
14-images-fonts-and-seo.md
15-actions-forms-and-endpoints.md
16-on-demand-rendering-and-adapters.md
17-testing-and-performance.md
18-deployment-and-production-checks.md
90-practical-checklist.md
```

## 4. Project PASS

외부 실제 프로젝트는 최소한 다음 조건을 통과해야 합니다.

- lockfile이 지정한 의존성으로 설치할 수 있습니다.
- `astro check` 또는 프로젝트가 정한 형·진단 검사가 통과합니다.
- `astro build`가 성공합니다.
- 생성된 route와 asset이 예상한 URL에 있습니다.
- JavaScript가 필요한 기능과 필요하지 않은 page를 구분해 확인했습니다.
- 핵심 사용자 기능을 실제 browser에서 확인했습니다.
- 외부 데이터 실패나 잘못된 content metadata처럼 프로젝트에서 중요한 실패를 재현했습니다.
- static host 또는 adapter runtime의 배포 설정이 문서화되어 있습니다.

개발 서버에서 page가 보인다는 사실만으로 PASS로 처리하지 않습니다.

## 5. Competency Suite

필수 역량 검증 프로그램은 다음 하나입니다.

```text
exercises/resource-directory/
```

분류: **CORE COMPETENCY**

이 프로그램은 다음 능력을 확인합니다.

- Astro static project와 React integration 설정
- Content Collection loader와 Zod schema
- entry id를 사용한 static dynamic route 생성
- summary와 Markdown body 분리
- typed props, layout과 component composition
- local image import와 `astro:assets`
- React island 하나만 `client:load`로 hydration
- static JSON endpoint와 custom 404
- canonical metadata와 semantic HTML
- pure unit test, production preview E2E, build output와 process cleanup smoke test

실행 순서는 다음과 같습니다.

```text
Project PASS
→ exercise README와 test 확인
→ Guide를 다시 읽지 않고 구현 또는 재구성
→ npm run verify
```

결과는 다음과 같이 처리합니다.

```text
PASS
→ 다른 문맥에서도 Astro 실행 모델을 재현할 수 있음

FAIL
→ 실패한 영역에 해당하는 Guide만 Rewind
→ 구현 수정
→ 같은 검증 다시 실행
```

## 6. Rewind 대응표

| 실패한 영역 | 다시 읽을 문서 |
| --- | --- |
| static/on-demand 실행 시점, config, build output | `01-runtime-rendering-and-project-model.md` |
| `.astro` props, slot, layout, route와 `getStaticPaths()` | `02-components-pages-and-composition.md` |
| browser script, hydration, `client:*` 선택 | `03-islands-and-client-execution.md` |
| collection loader, schema, entry id | `10-content-collections.md` |
| Markdown body render와 authoring 형식 | `11-markdown-mdx-and-content-rendering.md` |
| React island state와 storage | `12-react-integration.md` |
| 외부 JSON과 build-time fetch 검사 | `13-data-loading-and-runtime-validation.md` |
| image, canonical과 metadata | `14-images-fonts-and-seo.md` |
| endpoint 또는 form 처리 | `15-actions-forms-and-endpoints.md` |
| adapter와 요청별 render | `16-on-demand-rendering-and-adapters.md` |
| unit/E2E 선택, JavaScript·DOM 예산 | `17-testing-and-performance.md` |
| `dist/`, preview와 smoke | `18-deployment-and-production-checks.md` |
| 여러 실패가 섞여 원인을 좁히기 어려움 | `90-practical-checklist.md` |

Rewind는 전체 Guide를 처음부터 다시 읽는 과정이 아닙니다. 실패를 재현한 뒤 관련 절만 확인하고 같은 검증으로 수정 결과를 확인합니다.

## 7. 제외된 exercise

현재 competency exercise는 `resource-directory` 하나이며 같은 능력을 더 강하게 확인하는 다른 프로그램이 없습니다.

- REDUNDANT: 없음
- SPECIALIZATION: 없음
- PROJECT-SCALE INTEGRATION: 없음

이 프로그램은 인증, database, realtime, payment와 복잡한 업무 규칙을 포함하지 않습니다. 외부 실제 프로젝트를 대체하지 않고 Astro의 공통 구현 능력을 작은 문맥에서 확인합니다.

## 8. 최종 학습 순서

```text
1. docs/00-roadmap.md에서 전체 순서를 확인합니다.
2. Stable Core 세 문서를 읽습니다.
3. 외부 실제 프로젝트를 시작합니다.
4. 구현 중 필요한 JIT 문서만 읽습니다.
5. 프로젝트의 build·test·배포 조건을 통과합니다.
6. exercises/resource-directory/를 Guide 없이 검증합니다.
7. 실패한 항목에 해당하는 문서만 다시 읽습니다.
8. 같은 검증을 다시 통과합니다.
```

## 완료 기준

- 처음 보는 Astro 프로젝트에서 static HTML과 browser JavaScript가 생성되는 위치를 설명할 수 있습니다.
- content source와 route generation을 추적할 수 있습니다.
- 실제 프로젝트에서 필요한 island만 hydration했습니다.
- 외부 실제 프로젝트의 build 결과와 핵심 browser 동작을 확인했습니다.
- `exercises/resource-directory/`의 전체 검증을 Guide 없이 통과했습니다.
- 실패한 항목이 있었다면 관련 문서만 다시 읽고 같은 검증을 통과했습니다.
