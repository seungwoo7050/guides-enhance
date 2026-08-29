# Content Collections

Content Collection은 metadata 구조가 같은 문서나 data entry가 여러 개 생겼을 때 사용합니다. 파일이 하나뿐이거나 각 page가 완전히 다른 경우에는 collection을 만들 필요가 없습니다. 먼저 자료가 반복되는지, 같은 필드를 반드시 가져야 하는지 확인합니다.

## 이 문서를 읽는 시점

- Markdown 문서가 여러 개 생겼습니다.
- 제품, 장소, 게임, 도구처럼 같은 metadata를 가진 entry를 관리합니다.
- frontmatter 누락을 build에서 막아야 합니다.
- local file, CMS 또는 API data를 같은 query 방식으로 다루고 싶습니다.
- entry id로 dynamic route를 만들어야 합니다.

## Collection이 적합한 경우

다음 조건 가운데 하나 이상을 만족할 때 사용합니다.

- 여러 entry가 같은 필드를 공유합니다.
- `getCollection()`으로 전체 목록을 읽고 정렬·filter해야 합니다.
- 잘못된 metadata가 production에 배포되기 전에 build를 실패시켜야 합니다.
- editor autocomplete와 TypeScript type이 필요합니다.
- 수백·수천 entry를 build에서 반복해서 읽습니다.

다음 경우에는 일반 page나 import가 더 단순합니다.

- about page 하나뿐입니다.
- PDF처럼 Astro가 처리하지 않을 static file입니다.
- data source SDK를 직접 사용하는 편이 명확합니다.
- 서로 다른 형식의 작은 설정값 몇 개만 있습니다.

## `src/content.config.ts`에서 collection을 등록합니다

Astro 7의 build-time collection은 loader가 필수이며 schema는 선택 사항입니다. 실제 project에서는 schema를 두는 편이 안전합니다.

```ts
import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

const articles = defineCollection({
  loader: glob({
    base: "./src/content/articles",
    pattern: "**/*.md"
  }),
  schema: z.object({
    title: z.string().trim().min(1).max(80),
    summary: z.string().trim().min(1).max(180),
    publishedAt: z.coerce.date(),
    draft: z.boolean().default(false)
  })
});

export const collections = { articles };
```

`src/content.config.ts`는 application code에서 사용하는 collection 이름과 loader를 한 곳에 등록합니다. collection별 config를 다른 module로 나눌 수 있지만 최종 `collections` export는 하나입니다.

## Loader가 entry를 읽습니다

### `glob()`

파일 하나를 entry 하나로 읽을 때 사용합니다.

```ts
loader: glob({
  base: "./src/content/resources",
  pattern: "**/*.{md,mdx}"
})
```

기본 id는 file name과 path에서 만듭니다. 공개 URL에 사용할 id라면 file rename이 URL 변경으로 이어진다는 점을 고려합니다.

### `file()`

JSON, YAML 또는 TOML 파일 하나에 여러 entry가 있을 때 사용합니다.

```ts
import { file } from "astro/loaders";

const categories = defineCollection({
  loader: file("src/data/categories.json"),
  schema: z.object({
    id: z.string(),
    label: z.string()
  })
});
```

각 entry에 고유한 `id`가 있어야 합니다. parser가 기본 형식을 지원하지 않으면 `parser` option으로 변환 함수를 제공합니다.

### Custom loader

remote API나 CMS를 build에서 읽고 싶을 때 사용합니다. 다음 내용을 직접 소유해야 합니다.

- 요청 timeout
- pagination
- retry 범위
- 인증값 비노출
- stable id 생성
- 삭제된 entry 반영
- source가 실패했을 때 build를 중단할지 이전 snapshot을 사용할지

loader를 만들었다는 이유만으로 remote data가 자동으로 신뢰 가능한 값이 되지는 않습니다. schema와 source별 validation이 모두 필요할 수 있습니다.

## Schema는 build 전에 entry를 검사합니다

schema에는 page가 실제로 사용하는 필드와 허용 범위를 적습니다.

```ts
schema: z.object({
  title: z.string().trim().min(1).max(80),
  category: z.enum(["web", "data", "tooling"]),
  tags: z.array(z.string().min(1).max(24)).max(6),
  sourceUrl: z.string().url().optional(),
  publishedAt: z.coerce.date()
})
```

검사할 항목:

- 필수 field 누락
- 빈 문자열과 과도한 길이
- 허용하지 않은 enum
- 잘못된 URL
- 날짜 parsing 실패
- 배열 개수와 중복값
- draft와 공개 상태

schema에서 값을 변환할 때 원본과 최종 type을 구분합니다. 예를 들어 `z.coerce.date()`는 frontmatter 문자열을 `Date`로 바꿉니다. client island나 JSON endpoint로 넘기기 전에는 ISO string으로 직렬화하는 편이 명확합니다.

## Query 결과를 한 곳에서 정규화합니다

여러 page가 각각 `getCollection()`을 호출하며 다른 filter와 sort를 사용하면 목록, category page와 endpoint가 서로 달라질 수 있습니다.

```ts
export async function getPublishedArticles() {
  const entries = await getCollection("articles", ({ data }) => !data.draft);
  return entries.toSorted((left, right) =>
    right.data.publishedAt.getTime() - left.data.publishedAt.getTime()
  );
}
```

공통 module에서 다음을 처리합니다.

- draft 제거
- 정렬 기준
- category filter
- 공개 summary 변환
- 관련 entry 선택
- client로 보낼 직렬화

Markdown body는 목록에 필요하지 않으면 summary props에 포함하지 않습니다.

## Entry body는 `render()`로 컴파일합니다

```astro
---
import { getEntry, render } from "astro:content";

const entry = await getEntry("articles", Astro.params.id ?? "");
if (!entry) return Astro.redirect("/404/");

const { Content, headings } = await render(entry);
---

<article>
  <Content />
</article>
```

static route에서는 `getStaticPaths()`에서 entry를 props로 넘길 수 있습니다. body render는 상세 page에서만 수행하고 목록 page는 metadata만 사용하면 build 작업과 props 크기를 줄일 수 있습니다.

## Collection에서 static route를 만듭니다

```astro
---
export async function getStaticPaths() {
  const entries = await getPublishedArticles();
  return entries.map((entry) => ({
    params: { id: entry.id },
    props: { entry }
  }));
}
---
```

확인할 내용:

- draft entry를 제외했는가?
- duplicate id가 없는가?
- id 변경이 기존 link를 깨뜨리지 않는가?
- category나 locale parameter가 모두 포함되는가?
- entry 수가 build 시간과 memory에 적절한가?

수만 개 page를 한 번에 만들기 어렵다면 on-demand route, deferred rendering 또는 배포 platform의 cache를 검토합니다. 이를 Stable Core로 올리지 않고 실제 규모가 문제를 만들 때 JIT로 결정합니다.

## Build-time collection과 live collection을 구분합니다

### Build-time collection

- build에서 data를 읽습니다.
- static HTML, image 처리와 MDX에 적합합니다.
- deploy 후 data 변경은 새 build가 필요합니다.
- content store를 build 사이에 활용할 수 있습니다.

### Live collection

- 요청 시점에 최신 remote data를 읽습니다.
- on-demand rendering과 server runtime이 필요합니다.
- runtime latency와 source 장애를 처리해야 합니다.
- MDX와 image 처리 등 build-time collection과 다른 제한이 있습니다.

주식 가격처럼 즉시성이 필요한 data가 아니라면 build-time collection을 먼저 검토합니다.

## Stable id와 URL 변경

file name을 id로 사용하면 content 이동이 URL 변경이 될 수 있습니다. 공개 URL을 오래 유지해야 한다면 다음 방법을 고려합니다.

- frontmatter의 명시적 slug
- loader `generateId`
- 기존 URL redirect map
- locale과 category를 id에 포함할지 분리

제목을 id로 직접 쓰면 제목 수정이 URL을 바꿀 수 있습니다. content identity와 표시 제목을 분리합니다.

## 실패 처리

Collection schema 실패는 build를 중단하는 것이 일반적으로 맞습니다. 누락된 title을 빈 page로 배포하는 것보다 작성자가 즉시 고칠 수 있습니다.

remote loader 실패는 project 요구에 따라 선택합니다.

- 최신 data가 필수: build 실패
- 이전 snapshot 허용: 저장된 snapshot과 생성 시각 사용
- 일부 source만 선택사항: 해당 section 제외와 경고

오류 message에는 collection, entry id와 잘못된 field를 포함하되 token이나 전체 원본 응답을 노출하지 않습니다.

## 완료 기준

- collection을 만들지 말아야 할 경우를 구분할 수 있습니다.
- loader와 schema가 각각 무엇을 처리하는지 설명할 수 있습니다.
- draft filter, sort와 summary 변환을 한 곳에 모을 수 있습니다.
- entry id로 static route를 만들 수 있습니다.
- build-time과 live collection의 실행 시점을 구분할 수 있습니다.

## 공식 문서

- [Content collections](https://docs.astro.build/en/guides/content-collections/)
- [Content Collections API](https://docs.astro.build/en/reference/modules/astro-content/)
- [Content loader reference](https://docs.astro.build/en/reference/content-loader-reference/)
