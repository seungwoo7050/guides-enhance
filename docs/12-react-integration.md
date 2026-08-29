# React integration

Astro에서 React는 page 전체의 기본 runtime이 아니라 **필요한 component를 server에서 render하고, 선택한 component만 browser에서 hydrate하는 integration**입니다. 기존 React 경험을 그대로 사용할 수 있지만 모든 UI를 React island로 만들면 Astro를 선택한 이유가 약해집니다.

## 이 문서를 읽는 시점

- 기존 React component를 재사용합니다.
- client state와 event가 필요한 widget이 있습니다.
- chart, map, editor처럼 React 생태계 library가 필요합니다.
- 여러 hydration directive 가운데 하나를 선택해야 합니다.
- React island 사이 상태 공유 문제가 생겼습니다.

## Integration을 추가합니다

공식 CLI를 사용하면 package와 config를 함께 변경합니다.

```sh
npx astro add react
```

수동 설정은 다음 요소를 포함합니다.

```js
import { defineConfig } from "astro/config";
import react from "@astrojs/react";

export default defineConfig({
  integrations: [react()]
});
```

```json
{
  "extends": "astro/tsconfigs/strict",
  "compilerOptions": {
    "jsx": "react-jsx",
    "jsxImportSource": "react"
  }
}
```

`react`, `react-dom`, type package와 integration version이 서로 호환되는지 lockfile과 공식 integration 문서를 확인합니다.

## Directive가 없으면 server-rendered HTML만 나옵니다

```astro
---
import Badge from "../components/Badge.tsx";
---

<Badge label="정적" />
```

이 component는 build 또는 server에서 HTML로 변환되며 browser에서 React를 실행하지 않습니다. state, Effect와 click handler가 필요하면 `client:*`를 추가합니다.

```astro
<FavoriteButton client:load resourceId={entry.id} />
```

React component를 썼다는 사실과 browser JavaScript가 있다는 사실을 분리해서 확인합니다.

## Island 크기를 사용자 행동에 맞춥니다

좋은 island는 하나의 사용자 행동과 상태를 소유합니다.

- favorite toggle
- search filter
- price calculator
- chart controls
- map viewport
- rich text editor

좋지 않은 분리:

- header부터 footer까지 전체 page
- static article body 전체
- data fetching만 하려고 만든 큰 client component
- 서로 강하게 결합된 작은 island 수십 개

Component가 너무 크면 불필요한 JavaScript와 props가 늘고, 너무 잘게 나누면 상태 공유와 hydration overhead가 늘어납니다.

## Server HTML과 client 첫 render를 맞춥니다

Hydration 전에 server가 만든 HTML과 browser의 첫 React render가 다르면 mismatch가 발생할 수 있습니다.

문제가 되는 값:

- `localStorage`
- 현재 시간
- random value
- browser viewport
- `window.location`
- 사용자별 browser API

browser에서만 알 수 있는 값은 같은 초기 markup으로 시작한 뒤 Effect에서 읽습니다.

```tsx
const [ready, setReady] = useState(false);
const [value, setValue] = useState<string | null>(null);

useEffect(() => {
  setValue(localStorage.getItem("key"));
  setReady(true);
}, []);
```

Hydration 전 button을 disabled로 두거나 기본값을 명확히 표시합니다.

## Props를 작은 serializable object로 만듭니다

```astro
<SearchIsland
  client:load
  resources={resources.map(({ id, title, category }) => ({ id, title, category }))}
/>
```

전달하지 말아야 할 값:

- Markdown body 전체
- Content Collection entry object 전체
- function과 closure
- `Map`, custom class와 database client
- secret과 private environment variable
- 화면에 필요 없는 remote response field

Date는 ISO string으로 바꾸고 enum과 field를 명시적으로 제한합니다.

## React에서 `astro:assets` component를 사용할 수 없습니다

`<Image />`와 `<Picture />`는 Astro component입니다. React island에서는 React가 이해하는 `<img>`를 사용합니다. local image metadata를 import한 경우 `image.src`, `width`, `height`를 전달할 수 있습니다.

```tsx
import picture from "../assets/picture.png";

export function ReactImage() {
  return <img src={picture.src} width={picture.width} height={picture.height} alt="..." />;
}
```

가능하면 static image는 surrounding `.astro` component에서 `<Image />`로 출력하고 React island는 control만 담당합니다.

## 상태 공유는 browser application 전체를 만들기 전에 재검토합니다

서로 다른 island는 React context를 공유하지 않습니다.

공유 방법:

- URL query
- localStorage와 `storage` event
- custom event
- server에 저장하고 refetch
- nanostore 같은 작은 shared store
- 하나의 island로 합치기

두 widget이 항상 함께 변경되고 같은 state를 사용한다면 하나의 island가 더 자연스러울 수 있습니다. 반대로 article와 header를 한 store로 묶기 위해 page 전체를 hydration하지 않습니다.

## Data fetching 위치를 선택합니다

### Build 또는 server에서 읽고 props로 전달

- 첫 HTML에 반드시 필요
- 모든 사용자가 같은 data를 봄
- private API credential 사용
- SEO와 no-JS 접근이 중요

### React island가 browser에서 fetch

- 사용자의 event 뒤 필요
- 매우 자주 바뀜
- browser credential 또는 public API 사용
- skeleton과 오류 UI가 필요

Server component가 같은 Astro application의 endpoint를 HTTP로 다시 호출하지 말고 공통 TypeScript function을 직접 사용합니다. browser에서 필요한 경우에만 endpoint를 호출합니다.

## `client:only`는 마지막 선택입니다

browser API 없이는 render 자체가 불가능한 library에 사용합니다.

```astro
<Map client:only="react">
  <p slot="fallback">지도를 불러오는 중입니다.</p>
</Map>
```

단점:

- server HTML이 없음
- JavaScript 실패 시 content가 사라질 수 있음
- 초기 layout shift 가능
- SEO와 accessibility fallback을 직접 제공해야 함

대부분의 React component는 server render 후 `client:load` 또는 `client:visible`로 hydrate할 수 있습니다.

## React island 검증

- page의 `astro-island` 수를 확인합니다.
- initial JavaScript body byte를 측정합니다.
- JavaScript가 꺼져도 핵심 content와 navigation이 보이는지 확인합니다.
- hydration 전후 layout shift를 확인합니다.
- localStorage가 잘못된 JSON일 때 component가 crash하지 않는지 확인합니다.
- reload와 다른 tab에서 상태가 어떻게 동작하는지 확인합니다.
- button의 accessible name과 focus 표시를 browser에서 확인합니다.

## 완료 기준

- React component를 server-only HTML로 사용할 수 있습니다.
- 필요한 component에만 hydration directive를 붙일 수 있습니다.
- browser-only 값으로 hydration mismatch를 만들지 않습니다.
- island props를 필요한 summary로 제한할 수 있습니다.
- 여러 island의 상태 공유 방법을 요구에 맞게 선택할 수 있습니다.

## 공식 문서

- [`@astrojs/react`](https://docs.astro.build/en/guides/integrations-guide/react/)
- [UI framework components](https://docs.astro.build/en/guides/framework-components/)
- [Template directives](https://docs.astro.build/en/reference/directives-reference/)
