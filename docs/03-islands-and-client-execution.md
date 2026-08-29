# Island와 browser 실행

Astro의 기본 출력은 HTML입니다. `.astro` component와 UI framework component를 page에 넣어도 `client:*` directive가 없다면 browser에서 component code를 실행하지 않습니다. 필요한 상호작용만 island로 만들면 page 전체 hydration을 피할 수 있습니다.

## 목표

- Astro component가 browser runtime을 포함하지 않는다는 점을 이해합니다.
- server-rendered framework component와 hydrated island를 구분합니다.
- 일반 `<script>`와 UI framework island를 필요한 만큼만 사용합니다.
- `client:load`, `client:idle`, `client:visible`, `client:media`, `client:only`를 구분합니다.
- island props와 상태 저장 위치를 정합니다.
- 여러 island를 하나의 전역 React application처럼 연결하지 않습니다.

## 기본값은 JavaScript 없음입니다

다음 component는 React integration이 있어도 browser에서 React를 실행하지 않습니다.

```astro
---
import PriceLabel from "../components/PriceLabel.tsx";
---

<PriceLabel value={12000} />
```

Astro는 build 또는 server에서 React component를 HTML로 render합니다. event handler와 state는 동작하지 않습니다.

상호작용이 필요하면 directive를 추가합니다.

```astro
<FavoriteButton client:load resourceId="http-status" />
```

이때 해당 component와 필요한 React runtime이 browser bundle에 포함됩니다.

## 먼저 일반 HTML과 `<script>`로 해결 가능한지 봅니다

다음 기능은 React state가 없어도 구현할 수 있습니다.

- menu button 하나
- `<details>`를 사용한 펼치기
- form submit
- copy button
- theme class 변경
- 작은 custom element

Astro component의 `<script>`는 bundling과 TypeScript 처리를 받을 수 있으며 page에서 필요한 browser code를 추가합니다.

```astro
<button data-copy="값">복사</button>
<script>
  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(button.dataset.copy ?? "");
    });
  });
</script>
```

여러 상태와 복잡한 component lifecycle이 필요하거나 기존 React component를 재사용할 때 UI framework island를 선택합니다.

## Hydration directive 선택

| Directive | 사용하는 경우 |
| --- | --- |
| `client:load` | 첫 화면에 보이며 바로 조작해야 하는 control |
| `client:idle` | 초기 표시보다 우선순위가 낮고 곧 사용할 가능성이 있는 기능 |
| `client:visible` | 화면 아래쪽의 무거운 widget처럼 실제로 보일 때만 필요한 기능 |
| `client:media` | 특정 media query에서만 나타나는 control |
| `client:only="react"` | server render 자체가 불가능한 browser 전용 component |

`client:load`를 기본값처럼 붙이지 않습니다. 해당 component가 언제 interactive해야 하는지 사용자 행동으로 결정합니다.

### `client:load`

즉시 보여야 하는 search input, cart button, favorite button처럼 사용자가 page load 직후 조작할 수 있는 control에 사용합니다.

### `client:idle`

feedback widget이나 낮은 우선순위의 personalization처럼 초기 HTML 뒤에 준비되어도 되는 기능에 사용합니다. 너무 늦게 interactive해지지 않도록 필요하면 timeout을 지정합니다.

### `client:visible`

viewport에 들어올 때 hydration합니다. 아래쪽 chart, carousel처럼 사용자가 보지 않으면 JavaScript를 받을 필요가 없는 component에 적합합니다. layout 공간은 server HTML에서 먼저 확보해 CLS를 막습니다.

### `client:only`

server render를 건너뜁니다. 초기 HTML과 접근 가능한 fallback을 잃을 수 있으므로 browser API가 render 자체에 필수인 경우에만 사용합니다.

## Island를 가능한 작게 둡니다

좋지 않은 형태:

```astro
<App client:load allPageData={everything} />
```

이 형태는 page 전체를 React application으로 만들고 Astro의 static HTML 장점을 줄입니다.

더 나은 분리:

```astro
<StaticArticle />
<FavoriteButton client:load resourceId={id} />
<HeavyChart client:visible data={chartData} />
```

본문과 navigation은 HTML로 남기고 각 상호작용만 필요한 시점에 실행합니다.

## Props는 직렬화 비용입니다

island props는 HTML 또는 hydration payload를 통해 browser로 이동합니다.

- 필요하지 않은 Markdown body를 넘기지 않습니다.
- private field와 token을 넘기지 않습니다.
- 큰 collection 전체 대신 해당 component에 필요한 summary만 넘깁니다.
- Date, Map, class instance보다 명시적인 string과 object를 사용합니다.
- 같은 data를 여러 island에 중복 전달하지 않는지 확인합니다.

UI framework component가 server에서 render될 수 있다고 해서 server-only object를 props로 넘길 수 있다는 뜻은 아닙니다. hydration하는 순간 browser가 같은 props를 받아야 합니다.

## Island 상태는 기본적으로 서로 분리됩니다

서로 다른 React island는 하나의 React context tree를 공유하지 않습니다. 상태를 공유해야 한다면 다음 가운데 실제 요구에 맞는 방법을 선택합니다.

- URL query 또는 hash
- server state와 다시 fetch
- `localStorage`와 `storage` event
- custom browser event
- 작은 shared store
- island를 하나로 합쳐야 할 만큼 강하게 결합된 UI인지 재검토

page 여러 곳을 하나의 전역 client store로 묶기 전에 static HTML로 남길 수 있는 부분을 먼저 분리합니다.

## Hydration 실패와 지연을 고려합니다

JavaScript가 늦게 오거나 실패해도 다음 내용은 가능하면 사용할 수 있어야 합니다.

- 문서 읽기
- navigation
- 연락처와 기본 정보 확인
- server가 이미 만든 목록
- 일반 HTML form submit

보조 기능의 button은 hydration 전 상태를 명확히 표시하거나 disabled 상태로 둡니다. server HTML과 client 첫 render가 달라 hydration mismatch가 발생하지 않도록 초기 state를 맞춥니다.

browser storage는 server render에서 읽지 않습니다. client Effect 이후 읽고 같은 초기 markup에서 시작합니다.

## Server island는 다른 문제를 해결합니다

`server:defer`는 browser hydration이 아니라 page 일부의 server rendering을 늦추는 기능입니다. 사용자별 avatar나 느린 server data가 전체 HTML 응답을 막지 않게 할 때 사용합니다. adapter가 필요하며 client island와 목적이 다릅니다.

- client island: browser 상호작용
- server island: server에서 늦게 생성하는 HTML 조각

구체적인 사용법은 on-demand rendering 문제에 도달했을 때 확인합니다.

## Stable Core 완료 조건

- framework component에 directive가 없으면 browser에서 state와 event가 동작하지 않는 이유를 설명할 수 있습니다.
- 일반 `<script>`와 React island 중 더 작은 방법을 고를 수 있습니다.
- 상호작용 우선순위에 맞는 `client:*` directive를 선택할 수 있습니다.
- page 전체 hydration을 피하고 island props를 줄일 수 있습니다.
- browser storage를 hydration 뒤에 읽을 수 있습니다.

## 공식 문서

- [Islands architecture](https://docs.astro.build/en/concepts/islands/)
- [Template directives](https://docs.astro.build/en/reference/directives-reference/)
- [Scripts and event handling](https://docs.astro.build/en/guides/client-side-scripts/)
- [UI framework components](https://docs.astro.build/en/guides/framework-components/)
