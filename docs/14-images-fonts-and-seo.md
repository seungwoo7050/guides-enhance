# Image, font와 SEO

콘텐츠 중심 site에서는 image와 metadata가 page 품질과 build 비용을 함께 결정합니다. image를 `src/`와 `public/` 가운데 어디에 둘지, local transformation을 할지, canonical URL을 어떻게 만들지 먼저 정합니다.

## 이 문서를 읽는 시점

- hero, card 또는 Markdown image를 추가합니다.
- remote CMS image를 사용합니다.
- font file과 loading 전략을 정합니다.
- canonical, Open Graph, sitemap 또는 RSS가 필요합니다.
- page별 metadata를 반복해서 작성하고 있습니다.

## `src/`와 `public/` image를 구분합니다

### `src/`에 둡니다

- import해서 width와 height metadata를 얻습니다.
- `<Image />`, `<Picture />`로 transform합니다.
- file name에 hash가 붙습니다.
- unused asset을 bundle에서 제외할 수 있습니다.

```astro
---
import { Image } from "astro:assets";
import cover from "../assets/cover.png";
---

<Image src={cover} alt="자료 카드 배치 예시" />
```

### `public/`에 둡니다

- 원본 path가 그대로 필요합니다.
- favicon, robots.txt, download file입니다.
- Astro transformation을 원하지 않습니다.
- 외부 system이 고정 URL을 요구합니다.

`public/` image는 자동 최적화되지 않습니다. layout shift를 막기 위해 width와 height를 직접 제공합니다.

## `<Image />`와 `<Picture />`

`<Image />`는 local 또는 허용한 remote image를 처리하고 필수 `alt`와 size metadata를 제공합니다.

```astro
<Image
  src={cover}
  alt="자료 분류 화면"
  widths={[480, 800, 1200]}
  sizes="(max-width: 48rem) 100vw, 50vw"
/>
```

`<Picture />`는 여러 format과 source를 만들 때 사용합니다.

```astro
<Picture src={cover} formats={["avif", "webp"]} alt="자료 분류 화면" />
```

한 image에서 여러 width와 format을 만들면 build output 수가 늘어납니다. 실제 viewport와 source size에 맞는 조합만 사용합니다.

## Responsive image를 확인합니다

- `srcset`과 `sizes`가 실제 layout과 맞는가?
- mobile에서 desktop 크기 image를 받지 않는가?
- image container가 width를 미리 확보하는가?
- `loading="eager"`는 LCP image 한두 개에만 사용하는가?
- below-the-fold image는 lazy loading하는가?
- source image 자체가 지나치게 큰가?

Image optimization은 file size만 줄이는 문제가 아닙니다. build 시간, transform 수와 hosting image service 비용도 함께 봅니다.

## Remote image는 허용 source를 제한합니다

Astro가 remote image를 transform하려면 `image.domains` 또는 `image.remotePatterns`를 설정합니다.

```js
export default defineConfig({
  image: {
    remotePatterns: [
      { protocol: "https", hostname: "images.example.com" }
    ]
  }
});
```

모든 HTTPS host를 무제한으로 허용하지 않습니다. CMS가 반환한 URL도 protocol, hostname과 필요하면 path를 확인합니다.

## Alt text는 image 역할로 결정합니다

- 정보 전달: image가 보여 주는 핵심 내용을 적습니다.
- 링크 안의 image: 링크 목적을 설명합니다.
- 주변 text와 완전히 중복되는 장식: `alt=""`
- chart: 짧은 alt와 별도 text summary를 제공합니다.
- screenshot: 화면의 모든 text를 옮기기보다 설명하려는 상태를 적습니다.

File name이나 "이미지"라는 단어만 쓰지 않습니다.

## Markdown image와 Content Collection

Content Collection schema의 `image()` helper를 사용하면 local image metadata를 type-safe하게 받을 수 있습니다. Content entry와 image를 함께 이동하는 authoring 방식에 적합합니다.

반면 remote CMS URL은 string validation과 allowed remote source 설정이 필요합니다. build-time collection에서는 image 처리 비용이 build에 들어가고 live collection에서는 동일한 기능을 사용할 수 없는 경우가 있으므로 공식 version 문서를 확인합니다.

## Font를 추가하기 전에 system font를 검토합니다

Custom font는 추가 request, CSS와 layout shift를 만들 수 있습니다.

- 실제 brand 요구가 있는가?
- 필요한 weight와 language subset만 받는가?
- `font-display`를 정했는가?
- fallback font와 metric 차이가 큰가?
- Korean glyph 전체 file size를 감당할 수 있는가?
- privacy 때문에 third-party font host를 피해야 하는가?

Astro 7의 font API와 adapter별 asset 처리는 version에 따라 바뀔 수 있으므로 새 API를 사용할 때 공식 reference를 확인합니다. 일반 CSS `@font-face`를 사용할 때도 local file 위치와 cache header를 배포 설정에 포함합니다.

## Page metadata를 layout에서 통일합니다

```astro
---
interface Props {
  title?: string;
  description: string;
  canonicalPath: string;
}

const canonical = new URL(canonicalPath, Astro.site);
---

<title>{title ? `${title} | Site` : "Site"}</title>
<meta name="description" content={description} />
<link rel="canonical" href={canonical} />
<meta property="og:title" content={title} />
<meta property="og:description" content={description} />
<meta property="og:url" content={canonical} />
```

Page마다 title separator와 canonical 규칙을 다시 작성하지 않습니다. `Astro.site` 또는 project의 site origin을 한 곳에서 사용합니다.

## Canonical URL을 실제 배포 URL과 맞춥니다

확인할 내용:

- `site`가 production origin과 맞는가?
- `base` path가 있는가?
- trailing slash 규칙이 host와 일치하는가?
- query parameter가 canonical에 들어가야 하는가?
- pagination과 filter page를 별도 URL로 index할 것인가?
- staging domain이 production canonical을 내보내는가?

`new URL(path, site)`를 사용하면 slash와 origin 조합 실수를 줄일 수 있습니다.

## Sitemap, RSS와 robots.txt

### Sitemap

공개 HTML route가 많고 검색 engine이 route를 찾기 어려울 때 사용합니다. draft, private route와 duplicate URL을 제외합니다. `@astrojs/sitemap` integration은 `site` 설정이 필요합니다.

### RSS

게시 날짜가 있는 article, release note와 newsletter에 적합합니다. title, description, link와 date가 page metadata와 같은 source를 사용해야 합니다.

### robots.txt

Crawler 접근 허용 여부를 적는 file이지 보안 장치가 아닙니다. private page는 authentication과 authorization으로 막습니다.

## JSON-LD

Structured data는 화면에 실제로 보이는 정보와 일치해야 합니다. content schema에서 검증한 title, date와 author를 사용합니다. JSON을 `<script type="application/ld+json">`에 넣을 때 안전한 serialization을 사용하고 임의 HTML 문자열을 조합하지 않습니다.

## SEO 검증

- 각 page의 title과 description이 비어 있지 않은가?
- canonical이 production origin을 가리키는가?
- 한 page에 `h1`이 명확한가?
- image alt와 heading 순서가 올바른가?
- detail route를 JavaScript 없이 읽을 수 있는가?
- 404가 실제 404 status 또는 static host 설정과 맞는가?
- sitemap과 RSS URL이 build 결과에 있는가?
- social image가 공개 URL에서 접근 가능한가?

## 완료 기준

- `src/`와 `public/` image 사용 목적을 구분할 수 있습니다.
- `<Image />`와 `<Picture />`의 build 비용을 설명할 수 있습니다.
- remote image source를 제한할 수 있습니다.
- layout에서 title, description과 canonical을 일관되게 만들 수 있습니다.
- sitemap, RSS와 robots.txt의 목적을 구분할 수 있습니다.

## 공식 문서

- [Images](https://docs.astro.build/en/guides/images/)
- [Image and Assets API](https://docs.astro.build/en/reference/modules/astro-assets/)
- [Fonts](https://docs.astro.build/en/guides/fonts/)
- [Sitemap integration](https://docs.astro.build/en/guides/integrations-guide/sitemap/)
- [RSS](https://docs.astro.build/en/recipes/rss/)
