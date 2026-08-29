# Markdown, MDX와 본문 render

Markdown과 MDX는 같은 작성 형식이 아닙니다. Markdown은 문서 내용을 data와 분리하기 쉽고, MDX는 문서 안에서 UI component를 실행할 수 있는 대신 작성자와 build가 알아야 할 범위가 커집니다. 실제 작성 요구가 나타난 뒤 형식을 선택합니다.

## 이 문서를 읽는 시점

- Content Collection entry에 본문이 필요합니다.
- 문서 작성자가 heading, code block과 image를 사용합니다.
- 일부 문서 안에 interactive component가 필요합니다.
- Markdown output의 style과 heading link를 정해야 합니다.
- remote 또는 사용자 입력 Markdown을 처리해야 합니다.

## Markdown을 기본값으로 봅니다

일반적인 글, 설명, 참고 자료에는 Markdown이 적합합니다.

- 작성자가 HTML과 component import를 몰라도 됩니다.
- content structure를 제한하기 쉽습니다.
- schema가 frontmatter를 검사합니다.
- build에서 HTML로 변환할 수 있습니다.
- page code와 문서 내용을 분리합니다.

Markdown body에 component가 꼭 필요한지 먼저 확인합니다. callout, image caption과 code example는 remark/rehype plugin이나 CSS만으로 처리할 수 있습니다.

## MDX는 component 사용이 실제 요구일 때 선택합니다

MDX는 Markdown 안에서 JSX와 imported component를 사용할 수 있습니다.

```mdx
---
title: Interactive example
---

import Demo from "../../components/Demo.tsx";

# Example

<Demo client:visible />
```

추가되는 비용:

- `@astrojs/mdx` integration
- 작성자가 component API를 알아야 함
- content와 application code 결합
- hydration directive 검토
- component 변경이 여러 문서 build에 미치는 영향
- 신뢰하지 않는 MDX를 실행할 수 없는 보안 문제

작성자가 component를 쓰지 않는다면 Markdown을 유지합니다.

## Content entry를 `render()`합니다

```astro
---
import { render } from "astro:content";

const { entry } = Astro.props;
const { Content, headings } = await render(entry);
---

<article class="prose">
  <Content />
</article>
```

`render(entry)`는 body를 출력할 `<Content />`와 heading 정보를 제공합니다. page는 frontmatter metadata로 title, canonical과 summary를 만들고 body는 상세 영역에만 render합니다.

목록 page에서 `render()`를 반복하지 않습니다. 목록에는 title, summary, date와 category처럼 실제 필요한 metadata만 사용합니다.

## Heading과 목차

`headings`에는 heading depth, slug와 text가 들어갑니다. 목차를 만들 때 모든 heading을 그대로 중첩하지 말고 project가 지원할 depth를 정합니다.

```astro
<ol>
  {headings
    .filter(({ depth }) => depth === 2)
    .map(({ slug, text }) => <li><a href={`#${slug}`}>{text}</a></li>)}
</ol>
```

확인할 내용:

- 같은 text의 heading이 중복될 때 slug가 안정적인가?
- heading level이 `h1`부터 갑자기 건너뛰지 않는가?
- 목차 link가 fixed header에 가리지 않는가?
- heading text가 너무 길 때 줄바꿈되는가?

Page의 `h1`은 frontmatter title에서 만들고 Markdown body는 `h2`부터 시작하도록 authoring rule을 둘 수 있습니다.

## Markdown style은 wrapper 아래로 제한합니다

Markdown output에는 author가 직접 class를 붙이지 않습니다. `.prose` wrapper 아래에서 element style을 정의합니다.

```css
.prose {
  overflow-wrap: anywhere;
}

.prose h2,
.prose h3 {
  scroll-margin-top: 1rem;
}

.prose pre {
  max-width: 100%;
  overflow-x: auto;
}
```

전역 `h2`, `p`, `ul`을 모두 바꾸면 navigation과 card까지 영향을 받을 수 있습니다. Markdown body wrapper 아래로 selector를 제한합니다.

## Code block을 확인합니다

- 긴 line은 가로 scroll을 허용합니다.
- inline code와 block code를 다른 style로 표시합니다.
- syntax highlighting theme의 contrast를 확인합니다.
- copy button을 추가한다면 JavaScript가 모든 page에 필요한지 확인합니다.
- line number가 실제 copy text에 섞이지 않는지 확인합니다.

코드 예제가 build 과정에서 실행되는지 단순 표시인지 구분합니다. 실행 결과를 문서에 쓸 때는 source version과 command를 함께 남깁니다.

## Image 위치를 정합니다

Markdown image는 content와 가까운 `src/`에 둘 수 있습니다. Astro가 image를 처리하려면 local asset을 import할 수 있는 위치와 syntax를 사용합니다. 원본 경로가 그대로 필요한 download file은 `public/`에 둡니다.

Image 확인 항목:

- 의미 있는 `alt`
- 장식 image의 빈 `alt`
- width와 height 또는 responsive layout
- remote source allowlist
- caption과 source attribution
- build 시 image 수가 과도하게 늘지 않는지

구체적인 image 처리 방식은 [`14-images-fonts-and-seo.md`](14-images-fonts-and-seo.md)에서 다룹니다.

## Raw HTML과 신뢰할 수 없는 입력

Repository에 commit된 Markdown과 사용자가 직접 입력한 Markdown은 같은 신뢰 수준이 아닙니다.

- repository content: code review와 build를 거칩니다.
- CMS content: CMS 권한과 publish workflow를 확인합니다.
- 사용자 입력: HTML, script와 URL을 반드시 sanitize해야 합니다.

MDX는 arbitrary component와 JavaScript를 실행할 수 있으므로 신뢰하지 않는 입력에 사용하지 않습니다. Markdown parser option으로 raw HTML을 허용할 때도 sanitizer와 허용 tag를 명시합니다.

## Frontmatter와 body를 분리합니다

Frontmatter에는 page가 query와 metadata에 사용할 값을 둡니다.

```yaml
---
title: "HTTP 상태 코드"
summary: "실패와 재시도 기준"
category: "web"
publishedAt: 2026-08-20
---
```

본문에서 title이나 category를 다시 추출하지 않습니다. 동일한 값이 두 곳에 있으면 수정할 때 어긋날 수 있습니다.

Body에는 설명, heading, list, code와 link를 둡니다. Card나 JSON endpoint는 frontmatter만 사용합니다.

## Authoring rule을 짧게 문서화합니다

프로젝트가 실제로 사용하는 규칙만 남깁니다.

- file name 또는 slug 규칙
- title 길이
- body heading 시작 level
- image 저장 위치
- draft field
- 외부 link의 source 표시
- 금지하는 raw HTML 또는 MDX component

규칙을 checker로 확인할 수 있다면 schema나 test로 옮깁니다. 사람이 지켜야 하는 규칙만 문서에 남깁니다.

## 완료 기준

- Markdown과 MDX의 비용 차이를 설명할 수 있습니다.
- 상세 page에서만 `render(entry)`를 실행할 수 있습니다.
- heading과 목차를 안정적으로 만들 수 있습니다.
- Markdown style을 wrapper 아래로 제한할 수 있습니다.
- 신뢰하지 않는 Markdown과 MDX를 그대로 실행하지 않습니다.

## 공식 문서

- [Markdown in Astro](https://docs.astro.build/en/guides/markdown-content/)
- [MDX integration](https://docs.astro.build/en/guides/integrations-guide/mdx/)
- [Content Collections API: render](https://docs.astro.build/en/reference/modules/astro-content/#render)
