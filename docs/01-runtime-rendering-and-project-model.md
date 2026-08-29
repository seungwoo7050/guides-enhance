# Astro 실행 시점과 프로젝트 구성

Astro를 React framework처럼 이해하면 browser에 보내지 않는 코드를 불필요하게 client state로 옮기거나, 반대로 요청마다 바뀌어야 할 데이터를 build에 고정할 수 있습니다. 프로젝트에 들어갈 때는 문법보다 **어떤 코드가 언제 실행되고 어떤 파일이 배포되는지** 먼저 확인합니다.

## 목표

이 문서를 읽은 뒤 다음을 수행할 수 있어야 합니다.

- Astro project의 주요 파일과 디렉터리를 설명합니다.
- `astro dev`, `astro build`, `astro preview`가 무엇을 실행하는지 구분합니다.
- component script, page render와 browser script의 실행 시점을 구분합니다.
- static prerendering과 on-demand rendering을 구분합니다.
- integration과 adapter를 서로 다른 용도로 사용합니다.
- `src/` asset과 `public/` 파일의 처리 차이를 설명합니다.

## 프로젝트에서 먼저 확인할 파일

| 파일 | 확인할 내용 |
| --- | --- |
| `.nvmrc`, `package.json#engines` | 지원하는 Node.js 범위 |
| `packageManager`, lockfile | 설치 명령과 의존성 해석 결과 |
| `package.json#scripts` | dev, check, test, build, preview 경로 |
| `astro.config.*` | `site`, `base`, output, adapter, integrations, image 설정 |
| `tsconfig.json` | Astro strictness와 UI framework JSX 설정 |
| `.env.example` | public 값과 server 전용 값의 이름 |
| CI workflow | 실제로 통과시켜야 하는 명령과 환경 |

Astro는 현재 Node.js `22.12.0` 이상을 요구하며 odd-numbered release는 지원하지 않습니다. 프로젝트가 더 좁은 버전을 지정하면 프로젝트 설정을 따릅니다.

## 주요 디렉터리

```text
src/
  components/   page에서 조합할 component
  layouts/      문서 shell과 공통 배치
  pages/        URL이 되는 page와 endpoint
  content/      프로젝트가 정한 local content 위치
  assets/       build가 처리할 image와 asset
public/         변환하지 않고 같은 경로로 복사할 파일
dist/           build가 만든 배포 결과
.astro/         type과 content 처리에 사용하는 생성 파일
```

`public/` 파일은 import graph에 들어가지 않습니다. favicon, robots.txt처럼 원본 경로가 그대로 필요한 파일에 사용합니다. image 최적화나 hash가 필요한 파일은 `src/`에서 import합니다.

`dist/`와 `.astro/`는 생성 결과입니다. source처럼 직접 수정하지 않습니다.

## 세 가지 실행 명령

### `astro dev`

- source 변경을 감지합니다.
- 빠른 개발 feedback과 development error 화면을 제공합니다.
- 최종 asset 이름과 production optimization을 그대로 재현하지 않습니다.

### `astro build`

- static route를 HTML과 asset으로 생성합니다.
- Content Collection schema와 route 생성을 실행합니다.
- client island의 JavaScript bundle을 만듭니다.
- adapter가 있으면 해당 runtime에 필요한 server output도 만듭니다.

### `astro preview`

- 이미 만든 `dist/`를 로컬에서 확인합니다.
- source를 다시 build하지 않습니다.
- production hosting platform의 CDN, header와 server runtime을 완전히 대체하지는 않습니다.

따라서 최소 확인 순서는 다음과 같습니다.

```text
고정 설치
→ astro check
→ unit test
→ astro build
→ astro preview 또는 adapter output 실행
→ browser test
```

## `.astro` 파일의 실행 시점

Astro component는 두 부분으로 나뉩니다.

```astro
---
const data = await loadData();
---

<h1>{data.title}</h1>
```

`---` 안의 component script는 HTML을 만들 때 실행됩니다.

- static route: build 중 실행됩니다.
- on-demand route: 요청을 처리하는 server runtime에서 실행됩니다.
- browser: 실행되지 않으며 source가 그대로 전달되지 않습니다.

아래 template은 component script가 만든 값을 HTML로 출력합니다. template 안에 쓴 JavaScript 표현도 browser에서 다시 실행되는 것이 아니라 HTML 생성에 사용됩니다.

browser에서 실행할 코드는 명시적인 `<script>` 또는 hydrated UI framework component로 추가합니다.

## Static output을 기본값으로 봅니다

Astro는 기본적으로 page와 endpoint를 build에서 prerender합니다.

```text
source + content
→ astro build
→ HTML, CSS, image, 선택한 JavaScript
→ static host 또는 CDN
```

다음 조건이라면 static generation을 우선합니다.

- 모든 방문자가 같은 HTML을 받습니다.
- 콘텐츠가 build 주기에 맞춰 갱신돼도 됩니다.
- 사용자 cookie나 session이 필요하지 않습니다.
- build에서 API를 한 번 읽고 결과를 고정할 수 있습니다.

요청마다 다른 HTML이 필요한 route만 on-demand rendering으로 바꿉니다. adapter를 추가했다는 이유만으로 모든 route를 dynamic하게 만들 필요는 없습니다.

## On-demand rendering은 별도 server 실행입니다

다음 요구가 생기면 adapter와 on-demand rendering을 검토합니다.

- 로그인한 사용자마다 다른 HTML
- request cookie 또는 header 확인
- 요청 시점의 database 조회
- POST 처리와 server redirect
- 즉시 갱신되어야 하는 값

static output project에서는 필요한 page나 endpoint에 `export const prerender = false`를 지정하고, 배포 환경에 맞는 adapter를 추가합니다. 전체 on-demand project에서도 정적으로 만들 route는 `prerender = true`로 고정할 수 있습니다.

구체적인 adapter 설정은 [`16-on-demand-rendering-and-adapters.md`](16-on-demand-rendering-and-adapters.md)에서 다룹니다.

## Integration과 adapter를 구분합니다

### Integration

Astro build와 compiler에 기능을 추가합니다.

- React, Vue, Svelte renderer
- MDX
- sitemap
- build hook 또는 Vite plugin 연결

### Adapter

on-demand page와 endpoint를 특정 runtime에서 실행할 수 있는 output으로 만듭니다.

- Node.js
- Cloudflare
- Netlify
- Vercel

React integration은 server runtime이 아닙니다. React component를 사용한다고 adapter가 자동으로 필요한 것도 아닙니다. React island를 포함한 전체 site를 static HTML과 JavaScript asset으로 배포할 수 있습니다.

## 환경 변수 공개 범위

component script는 server 또는 build에서 실행되므로 private 값을 읽을 수 있습니다. 그러나 그 값을 template이나 client props로 출력하면 최종 HTML 또는 JavaScript에 포함됩니다.

- `PUBLIC_` prefix: browser에 공개할 값으로 취급합니다.
- 그 외 값: server/build에서만 사용하고 출력하지 않습니다.
- `import.meta.env` 전체를 object로 client component에 넘기지 않습니다.
- build log에도 token을 그대로 출력하지 않습니다.

static build에 secret을 사용해 API를 호출할 수는 있지만, API 결과 안에 private field가 포함되지 않았는지 별도로 확인합니다.

## 처음 프로젝트에 들어갈 때 확인할 질문

1. 최종 output은 static files입니까, server bundle입니까?
2. 어떤 route가 build에서 생성되고 어떤 route가 요청마다 실행됩니까?
3. content와 API fetch는 어느 시점에 실행됩니까?
4. `client:*`가 붙은 component는 몇 개이며 왜 필요한가요?
5. `public/`에 둔 파일 중 hash나 optimization이 필요한 것은 없습니까?
6. `site`와 `base`가 실제 배포 URL과 맞습니까?
7. build 결과를 어떤 명령으로 확인합니까?

## Stable Core 완료 조건

- component script를 browser code로 오해하지 않습니다.
- static route와 on-demand route를 구분합니다.
- integration과 adapter의 목적을 설명할 수 있습니다.
- `src/`, `public/`, `dist/`의 처리 차이를 설명할 수 있습니다.
- 프로젝트의 실제 build와 preview 명령을 찾을 수 있습니다.

## 공식 문서

- [Install Astro](https://docs.astro.build/en/install-and-setup/)
- [Astro components](https://docs.astro.build/en/basics/astro-components/)
- [On-demand rendering](https://docs.astro.build/en/guides/on-demand-rendering/)
- [Working with integrations](https://docs.astro.build/en/guides/integrations/)
