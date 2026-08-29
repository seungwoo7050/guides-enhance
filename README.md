# Astro 실전 개발 가이드

이 저장소는 Astro 문법을 처음부터 차례로 설명하는 입문서가 아닙니다. HTML·CSS·JavaScript·TypeScript를 사용해 본 개발자가 Astro 프로젝트에 들어가 정적 HTML을 만들고, 필요한 부분만 브라우저에서 실행하며, 콘텐츠와 배포 결과를 검증하는 데 필요한 판단 기준을 다룹니다.

실제 프로젝트는 이 저장소 밖에서 진행합니다. `docs/`에는 프로젝트에 들어가기 전에 읽을 최소 문서와 구현 중 필요한 자료가 있으며, `exercises/`에는 실제 프로젝트를 통과한 뒤 Guide 없이 역량을 확인할 완성된 프로그램이 있습니다.

## 학습 순서

```text
Stable Core Guide
→ Actual Project
→ JIT Guide as needed
→ Project PASS
→ Competency Suite without Guide
→ Rewind where needed
```

## Stable Core Guide

프로젝트 종류와 관계없이 먼저 읽을 문서는 세 개입니다.

1. [`docs/01-runtime-rendering-and-project-model.md`](docs/01-runtime-rendering-and-project-model.md)
   - `astro.config.mjs`, `src/`, `public/`, `dist/`가 어떤 파일을 소유하는지 확인합니다.
   - build 시 생성되는 HTML과 요청 시 생성되는 HTML을 구분합니다.
   - component script, server 실행과 browser script가 언제 동작하는지 구분합니다.
2. [`docs/02-components-pages-and-composition.md`](docs/02-components-pages-and-composition.md)
   - `.astro` component, typed props, slot, layout과 scoped style을 사용합니다.
   - `src/pages/`의 파일 배치가 route로 바뀌는 규칙과 `getStaticPaths()`를 이해합니다.
   - page, layout과 작은 component를 변경 이유에 맞게 나눕니다.
3. [`docs/03-islands-and-client-execution.md`](docs/03-islands-and-client-execution.md)
   - Astro component가 기본적으로 browser JavaScript를 보내지 않는 이유를 이해합니다.
   - 일반 `<script>`와 UI framework island 가운데 필요한 실행 방식을 고릅니다.
   - `client:load`, `client:idle`, `client:visible` 등을 기능 우선순위에 맞게 사용합니다.

이 세 문서는 blog, directory, commerce, portfolio, documentation 등 대상 프로젝트가 달라져도 그대로 유지합니다. 새 프로젝트가 인증이나 실시간 기능을 사용한다고 해서 Stable Core를 늘리지 않습니다.

## Actual Project

Stable Core를 읽은 뒤에는 외부의 실제 프로젝트를 시작합니다. 이 저장소의 exercise를 먼저 구현하지 않습니다.

프로젝트에 들어가면 다음 내용을 먼저 확인합니다.

- Node.js, package manager, lockfile과 scripts
- `astro.config.mjs`의 `site`, `base`, adapter와 integration
- 정적으로 생성되는 route와 요청마다 실행되는 route
- 콘텐츠가 로컬 파일, CMS, API 중 어디에서 오는지
- browser JavaScript를 실제로 보내는 component와 그 이유
- build, preview, test와 배포 산출물 확인 방법

## JIT / Rewind Guide

실제 구현이 해당 문제에 도달했을 때만 읽습니다.

- [`docs/10-content-collections.md`](docs/10-content-collections.md): 구조가 같은 콘텐츠 묶음, schema, loader와 route 생성
- [`docs/11-markdown-mdx-and-content-rendering.md`](docs/11-markdown-mdx-and-content-rendering.md): Markdown, MDX, 본문 render와 작성 형식 선택
- [`docs/12-react-integration.md`](docs/12-react-integration.md): React component 재사용, hydration과 island 상태
- [`docs/13-data-loading-and-runtime-validation.md`](docs/13-data-loading-and-runtime-validation.md): API·CMS 입력 검사, build 실패와 최신성
- [`docs/14-images-fonts-and-seo.md`](docs/14-images-fonts-and-seo.md): `astro:assets`, image 처리, metadata와 검색 노출
- [`docs/15-actions-forms-and-endpoints.md`](docs/15-actions-forms-and-endpoints.md): HTML form, static endpoint, server endpoint와 Astro Actions
- [`docs/16-on-demand-rendering-and-adapters.md`](docs/16-on-demand-rendering-and-adapters.md): adapter, 요청 시 render, cookie와 server island
- [`docs/17-testing-and-performance.md`](docs/17-testing-and-performance.md): `astro check`, Vitest, Playwright, JavaScript와 DOM 예산
- [`docs/18-deployment-and-production-checks.md`](docs/18-deployment-and-production-checks.md): `dist/`, adapter output, 배포 설정과 smoke test
- [`docs/90-practical-checklist.md`](docs/90-practical-checklist.md): 구현·리뷰·장애 분석 때 필요한 항목만 확인하는 점검표

JIT 문서를 미리 전부 읽지 않습니다. competency exercise에서 실패한 경우에는 같은 문서의 관련 절만 다시 읽습니다.

## Competency Suite

현재 필수 역량 검증 프로그램은 하나입니다.

- [`exercises/resource-directory/`](exercises/resource-directory/)

`Resource Directory`는 다음 능력을 작은 다른 문맥에서 다시 구현할 수 있는지 확인합니다.

- Content Collection loader와 schema validation
- 정적 page와 content-derived dynamic route 생성
- Markdown 본문 render와 목록용 summary 분리
- Astro layout, typed props와 slot composition
- `astro:assets`를 사용한 local image 처리
- React island 하나만 hydration하고 나머지 page는 정적 HTML로 유지
- static JSON endpoint 생성
- metadata, canonical URL과 custom 404
- pure unit test, production preview E2E와 static build smoke test

이 프로그램은 프로젝트 진입 과제가 아닙니다. 실제 프로젝트가 PASS한 뒤 README와 test를 확인하고, Guide를 다시 읽지 않은 상태에서 구현하거나 재구성합니다.

```text
PASS
→ Astro 역량 확인 완료

FAIL
→ 실패한 영역에 해당하는 Guide만 다시 읽기
→ 같은 검증 다시 실행
```

## 선행 지식

다음 내용을 이미 사용해 본 개발자를 대상으로 합니다.

- 의미에 맞는 HTML 요소, form과 `label`
- CSS 기본 배치, Flexbox와 Grid
- JavaScript module, Promise, `async`, `await`
- TypeScript object type, union, `unknown`, narrowing
- HTTP method, 상태 코드, header와 JSON body
- React props, state와 Effect의 기본 사용법
- Node.js, `package.json`, script와 lockfile

React를 사용할 줄 몰라도 Astro component 자체는 배울 수 있습니다. 다만 이 저장소의 competency exercise에는 작은 React island가 하나 포함되어 있으므로 해당 검증까지 수행하려면 React의 기본 상태 관리가 필요합니다.

## 버전 기준

이 자료는 2026년 8월의 Astro 7.2를 기준으로 작성했으며, competency project는 Astro `7.2.9`를 지정합니다. Astro 공식 설치 문서는 Node.js `22.12.0` 이상과 짝수 major version을 요구합니다.

버전 번호보다 다음 원리를 우선합니다.

- 정적으로 만들 수 있는 HTML은 build에서 생성합니다.
- browser JavaScript는 실제 상호작용이 필요한 component에만 보냅니다.
- 외부 데이터는 page가 사용하기 전에 검사합니다.
- 콘텐츠 id와 URL은 한 번 공개한 뒤 안정적으로 유지합니다.
- 개발 서버가 아니라 build 결과를 검증합니다.

새 major version으로 올릴 때는 route API, Content Collection loader, integration과 adapter 문서를 다시 확인합니다.

## 저장소 구성

```text
.
├── .gitignore
├── README.md
├── docs/
│   ├── 00-roadmap.md
│   ├── 01-runtime-rendering-and-project-model.md
│   ├── 02-components-pages-and-composition.md
│   ├── 03-islands-and-client-execution.md
│   ├── 10-content-collections.md
│   ├── 11-markdown-mdx-and-content-rendering.md
│   ├── 12-react-integration.md
│   ├── 13-data-loading-and-runtime-validation.md
│   ├── 14-images-fonts-and-seo.md
│   ├── 15-actions-forms-and-endpoints.md
│   ├── 16-on-demand-rendering-and-adapters.md
│   ├── 17-testing-and-performance.md
│   ├── 18-deployment-and-production-checks.md
│   └── 90-practical-checklist.md
└── exercises/
    └── resource-directory/
```

## 권장 사용법

1. [`docs/00-roadmap.md`](docs/00-roadmap.md)에서 전체 순서와 완료 조건을 확인합니다.
2. Stable Core 세 문서를 읽습니다.
3. 외부 실제 프로젝트를 시작합니다.
4. 구현 중 필요한 JIT 문서만 읽습니다.
5. 프로젝트의 build, test와 배포 조건을 통과시킵니다.
6. `exercises/resource-directory/`를 Guide 없이 검증합니다.
7. 실패한 항목이 있을 때만 관련 문서로 돌아갑니다.

## 완료 기준

다음 조건을 모두 만족하면 이 개발 트랙을 완료한 것으로 봅니다.

- 처음 보는 Astro 프로젝트의 static route, on-demand route와 browser script를 구분할 수 있습니다.
- 실제 프로젝트에서 content, page와 interactive island를 필요한 만큼만 구성했습니다.
- 실제 프로젝트의 build 결과와 핵심 browser 동작을 확인했습니다.
- 필요한 JIT 문서만 골라 적용했습니다.
- `exercises/resource-directory/`의 전체 검증을 Guide 없이 통과했습니다.
- 실패한 영역이 있었다면 관련 문서만 다시 읽고 같은 검증을 통과했습니다.
