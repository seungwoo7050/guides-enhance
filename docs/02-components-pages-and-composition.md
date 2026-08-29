# Astro component와 route 구성

Astro project는 component tree만으로 이해되지 않습니다. `src/pages/`의 파일이 URL을 만들고, page가 layout과 component를 조합하며, component script가 HTML에 필요한 값을 준비합니다. 각 파일이 무엇을 직접 결정하는지 구분하면 project가 커져도 route와 rendering 위치를 추적할 수 있습니다.

## 목표

- `.astro` component script와 template을 작성합니다.
- props를 TypeScript로 제한합니다.
- default slot과 named slot을 사용합니다.
- layout이 문서 공통 부분을 한 번만 출력하게 합니다.
- scoped style과 global style을 구분합니다.
- static route와 dynamic route를 생성합니다.
- `getStaticPaths()`가 build할 URL을 고정하는 방법을 이해합니다.
- standard `<a>`로 page를 이동합니다.

## Astro component의 두 부분

```astro
---
interface Props {
  title: string;
  summary?: string;
}

const { title, summary = "설명 없음" } = Astro.props;
---

<article>
  <h2>{title}</h2>
  <p>{summary}</p>
</article>
```

component script에서는 다음 작업을 수행합니다.

- 다른 component와 asset import
- props 확인
- local file 또는 API 읽기
- template에 사용할 값 계산
- route에서 사용할 redirect 또는 response 결정

Template에는 최종 HTML과 필요한 JavaScript 표현만 둡니다. 복잡한 정렬, validation과 data 변환은 TypeScript 함수로 분리해 DOM 없이 검사할 수 있게 합니다.

## Props는 component가 허용할 입력을 나타냅니다

`Astro.props`를 바로 여러 위치에서 읽기보다 `Props`를 정의하고 한 번 destructuring합니다.

```astro
---
type Props = {
  href: string;
  label: string;
  tone?: "default" | "warning";
};

const { href, label, tone = "default" } = Astro.props;
---
```

boolean 여러 개로 모순되는 조합을 만들지 않습니다.

```text
좋지 않음: primary, danger, muted
더 명확함: tone = "default" | "danger" | "muted"
```

UI framework island에 props를 넘길 때는 JSON으로 직렬화할 수 있는 값만 사용합니다. function, class instance, database connection과 private configuration을 넘기지 않습니다.

## Slot으로 markup 소유권을 나눕니다

Layout은 공통 문서 shell을 만들고 page는 page별 본문을 제공합니다.

```astro
---
const { title } = Astro.props;
---

<html lang="ko">
  <head>
    <title>{title}</title>
    <slot name="head" />
  </head>
  <body>
    <header>...</header>
    <main><slot /></main>
  </body>
</html>
```

page는 다음처럼 사용합니다.

```astro
<SiteLayout title="자료 목록">
  <meta slot="head" property="og:type" content="website" />
  <h1>자료 목록</h1>
</SiteLayout>
```

slot은 parent가 전달한 markup을 어느 위치에 출력할지 정합니다. 단순히 props를 다시 전달하는 wrapper를 여러 겹 만들 필요는 없습니다.

## Style의 적용 범위를 확인합니다

`.astro` component의 `<style>`은 기본적으로 해당 component가 출력한 HTML에만 적용됩니다. 공통 typography, body와 focus style은 layout에서 불러오는 global stylesheet로 둡니다.

- component 내부 배치: scoped style
- site 전체 color, font, reset: global CSS
- Markdown body처럼 child markup 전체에 적용: 의도적으로 global selector 또는 wrapper class 사용

`is:global`을 사용하면 selector가 project 전체에 영향을 줄 수 있으므로 적용 범위를 wrapper 아래로 제한합니다.

## `src/pages/`가 URL을 만듭니다

```text
src/pages/index.astro                 → /
src/pages/about.astro                 → /about
src/pages/resources/index.astro       → /resources
src/pages/resources/[id].astro        → /resources/:id
src/pages/resources.json.ts           → /resources.json
```

별도의 router 설정 없이 파일 배치가 route를 정의합니다. page 이동은 standard HTML `<a>`를 사용합니다.

```astro
<a href="/resources/">전체 자료</a>
```

framework 전용 Link component가 필요하지 않습니다. `base` path를 사용하는 project에서는 hard-coded root path가 배포 경로와 맞는지 확인합니다.

## Static dynamic route는 build할 값을 미리 반환합니다

static output에서 `[id].astro`는 가능한 id를 build 전에 알아야 합니다.

```astro
---
export async function getStaticPaths() {
  const resources = await loadResources();
  return resources.map((resource) => ({
    params: { id: resource.id },
    props: { resource }
  }));
}

const { resource } = Astro.props;
---

<h1>{resource.title}</h1>
```

`params`는 URL 문자열을 정의합니다. `props`는 해당 page를 render할 때 사용할 값을 전달합니다.

확인할 내용:

- 같은 id가 두 번 나오지 않는가?
- id가 URL에서 안전하고 장기간 유지되는가?
- draft나 비공개 entry가 route에 포함되지 않는가?
- Content Collection schema를 통과한 값만 사용하는가?
- entry 수가 매우 많아 build 시간이 과도하지 않은가?

On-demand route에서는 요청의 path parameter를 바로 읽으므로 `getStaticPaths()`를 사용하지 않습니다.

## Page와 component를 변경 이유로 나눕니다

### Page가 결정하기 좋은 내용

- URL parameter와 query
- static paths
- page metadata와 canonical URL
- 어떤 data를 읽을지
- 어떤 layout과 주요 section을 조합할지

### Component가 결정하기 좋은 내용

- 반복되는 card markup
- 한 종류의 navigation
- UI 단위의 props와 slot
- component 내부 style

### TypeScript module로 분리하기 좋은 내용

- 외부 입력 validation
- 정렬과 grouping
- slug와 canonical URL 생성
- API response 변환
- test가 필요한 순수 함수

줄 수가 많다는 이유만으로 component를 나누지 않습니다. 서로 다른 이유로 변경되는 코드가 섞일 때 분리합니다.

## Endpoint도 page directory에 둡니다

`.ts` 또는 `.js` endpoint는 `Response`를 반환합니다.

```ts
import type { APIRoute } from "astro";

export const GET = (() =>
  new Response(JSON.stringify({ status: "ok" }), {
    headers: { "content-type": "application/json" }
  })) satisfies APIRoute;
```

static output에서는 build 중 실행되어 file을 생성합니다. on-demand output에서는 요청마다 실행할 수 있습니다. 같은 문법이라도 실행 시점이 다르므로 endpoint를 추가하기 전에 output mode를 확인합니다.

## Stable Core 완료 조건

- `.astro` component script와 browser script를 구분합니다.
- typed props와 slot으로 page를 조합할 수 있습니다.
- route file과 URL을 서로 연결할 수 있습니다.
- static dynamic route의 `getStaticPaths()`를 설명할 수 있습니다.
- page, component와 pure TypeScript module을 변경 이유에 맞게 나눌 수 있습니다.

## 공식 문서

- [Astro components](https://docs.astro.build/en/basics/astro-components/)
- [Layouts](https://docs.astro.build/en/basics/layouts/)
- [Routing](https://docs.astro.build/en/guides/routing/)
- [Endpoints](https://docs.astro.build/en/guides/endpoints/)
