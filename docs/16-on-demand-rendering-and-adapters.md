# 요청 시 rendering과 adapter

Astro는 기본적으로 page와 endpoint를 build 중 생성합니다. 로그인 사용자마다 다른 HTML, 요청 시점의 최신 data, cookie나 database 접근이 필요할 때만 일부 route를 server에서 요청마다 만듭니다.

요청 시 rendering을 사용하려면 배포 환경에 맞는 adapter가 필요합니다. Adapter는 Astro application code를 특정 server, function 또는 edge runtime에서 실행할 수 있는 build output으로 바꿉니다.

## 이 문서를 읽는 시점

- 로그인 사용자별 page가 필요합니다.
- 요청마다 바뀌는 data를 HTML에 포함해야 합니다.
- cookie, session 또는 private database를 읽습니다.
- server endpoint나 Astro Actions를 실행해야 합니다.
- server island를 사용하려고 합니다.
- 배포 대상에 맞는 adapter를 선택해야 합니다.

## Static을 기본값으로 유지합니다

다음 내용은 build에서 만들 수 있습니다.

- article, documentation, directory
- 제품 설명과 공개 목록
- release note
- category와 tag archive
- 일정 주기로 갱신해도 되는 public data

정적 route의 장점:

- 요청마다 application server가 필요하지 않습니다.
- CDN과 object storage에서 바로 전달할 수 있습니다.
- runtime 장애 범위가 작습니다.
- response time과 비용을 예측하기 쉽습니다.
- private server code가 browser request path에 들어가지 않습니다.

최신성이 필요하다고 바로 SSR로 바꾸지 않습니다. build trigger를 늘리거나 일부 data만 browser에서 갱신하는 방법도 검토합니다.

## 특정 route만 요청 시 생성합니다

Adapter를 추가한 static project에서는 필요한 route에만 다음을 표시합니다.

```astro
---
export const prerender = false;

const session = await readSession(Astro.cookies);
if (!session) return Astro.redirect("/login/");
const account = await loadAccount(session.userId);
---

<h1>{account.name}님의 계정</h1>
```

이 route는 방문할 때마다 server에서 실행됩니다. 표시가 없는 나머지 route는 계속 build에서 생성됩니다.

요청 시 실행된다는 뜻:

- cold start가 있을 수 있습니다.
- database와 external API timeout을 처리해야 합니다.
- runtime environment variable이 필요합니다.
- response cache를 직접 결정해야 합니다.
- server log와 monitoring이 필요합니다.

## `output: "server"`는 기본 동작을 뒤집습니다

대부분의 route가 요청마다 실행되는 application이라면 config에서 server output을 선택할 수 있습니다.

```js
export default defineConfig({
  output: "server",
  adapter: node({ mode: "standalone" })
});
```

이 경우 route는 기본적으로 요청 시 실행됩니다. 정적으로 만들 route에는 `export const prerender = true`를 둡니다.

`output: "server"`가 추가 기능을 주는 것은 아닙니다. 기본 prerender 여부만 바꿉니다. 공개 content route가 대부분이라면 static 기본값과 route별 `prerender = false`가 더 명확합니다.

## Adapter는 배포 runtime에 맞춰 선택합니다

확인할 내용:

- Node.js process인가, serverless function인가, edge runtime인가?
- filesystem을 읽거나 쓸 수 있는가?
- 장시간 connection과 streaming을 지원하는가?
- native module을 사용할 수 있는가?
- request body와 response size 제한은 무엇인가?
- region과 cold start 특성은 어떠한가?
- cookie, header와 IP 정보가 어떻게 전달되는가?
- local `astro preview`와 production runtime 차이는 무엇인가?

공식 adapter라도 option과 지원 기능이 다릅니다. 설치 명령만 실행하고 끝내지 말고 생성되는 output과 hosting 설정을 확인합니다.

## Adapter 추가는 지속되는 project 변경입니다

공식 adapter는 다음처럼 추가할 수 있습니다.

```sh
npx astro add node
```

명령은 package를 설치하고 `astro.config.mjs`를 수정합니다. 실제 변경 내용을 review합니다.

- 추가된 package version
- `adapter` 설정
- `output` 변경 여부
- runtime-specific option
- 배포 command와 artifact 위치

Adapter를 바꾸면 build output과 운영 방법이 달라집니다. 단순 dependency 교체로 취급하지 않습니다.

## Cookie와 session은 server에서 확인합니다

```astro
---
export const prerender = false;

const sessionId = Astro.cookies.get("session")?.value;
const session = sessionId ? await findSession(sessionId) : null;
---
```

주의할 점:

- cookie는 서명 또는 예측 불가능한 session id를 사용합니다.
- `HttpOnly`, `Secure`, `SameSite`, path와 만료 시간을 설정합니다.
- authentication 뒤에도 resource별 authorization을 검사합니다.
- session 내용을 HTML이나 client props에 그대로 넘기지 않습니다.
- shared cache가 사용자별 HTML을 섞지 않도록 header를 정합니다.

Static page에서는 요청 cookie를 읽을 수 없습니다. build machine의 cookie와 방문자의 cookie는 서로 무관합니다.

## Server island는 느린 일부 영역을 분리합니다

Server island는 page 전체를 요청 시 rendering하지 않고 특정 component를 server에서 지연 render할 때 사용합니다.

적합한 경우:

- page 본문은 정적이지만 사용자별 account badge가 있습니다.
- 느린 추천 영역이 전체 HTML 생성을 막지 않아야 합니다.
- private server data가 필요한 작은 영역입니다.

검토할 점:

- fallback이 의미 있는가?
- 해당 영역이 늦게 나타나도 layout이 흔들리지 않는가?
- 별도 request 비용이 이득보다 작은가?
- page 핵심 content를 island에 숨기지 않았는가?
- cache와 사용자별 data가 섞이지 않는가?

Server island는 client hydration과 다릅니다. Server에서 HTML을 만들며, browser JavaScript가 반드시 필요한 것은 아닙니다.

## Runtime data는 요청마다 검사합니다

CMS, database와 external API response는 TypeScript type만으로 안전하지 않습니다.

```text
request
→ authentication
→ input validation
→ data read
→ returned data validation
→ page model
→ HTML
```

Database driver가 반환한 값도 migration과 application version이 어긋날 수 있습니다. optional field, enum과 nullable column을 page 전에 정규화합니다.

## Cache를 명시합니다

요청 시 rendering이라고 해서 매번 원본 data를 읽어야 하는 것은 아닙니다. 반대로 platform cache가 자동으로 올바른 것도 아닙니다.

결정할 내용:

- 사용자별 response인지 public response인지
- CDN cache 가능 여부
- `Cache-Control`과 stale 허용 시간
- data cache와 rendered HTML cache의 무효화 조건
- mutation 뒤 어떤 cache를 갱신하는지
- personalized response에 `private` 또는 `no-store`가 필요한지

Cookie를 읽는 route를 public shared cache에 저장하면 사용자 data가 노출될 수 있습니다.

## 오류와 timeout을 route 안에서 제한합니다

- database와 external request에 timeout을 둡니다.
- 사용자가 다시 시도하거나 안전하게 이동할 수 있는 page를 반환합니다.
- 오류마다 전체 stack을 HTML에 표시하지 않습니다.
- request id와 release를 server log에 남깁니다.
- dependency 장애가 page 전체를 막아야 하는지 결정합니다.
- child process나 stream을 열었다면 요청 종료 뒤 정리합니다.

## 개발 서버로 production을 추정하지 않습니다

검증 순서:

```text
고정 dependency 설치
→ production build
→ adapter가 만든 command 또는 platform emulator 실행
→ static route 확인
→ on-demand route 확인
→ cookie와 redirect 확인
→ server endpoint와 Action 확인
→ process 종료와 log 확인
```

`astro dev`에서 동작해도 adapter output에서 import, filesystem, environment variable이나 runtime API가 달라질 수 있습니다.

## 완료 기준

- static route와 요청 시 route를 사용자 요구로 구분할 수 있습니다.
- 일부 route만 `prerender = false`로 전환할 수 있습니다.
- `output: "server"`가 기본값만 바꾼다는 점을 설명할 수 있습니다.
- 배포 runtime 제약을 기준으로 adapter를 선택할 수 있습니다.
- cookie, cache와 private data가 섞이지 않게 설정할 수 있습니다.
- production adapter output을 실제로 실행해 확인할 수 있습니다.

## 공식 문서

- [On-demand rendering](https://docs.astro.build/en/guides/on-demand-rendering/)
- [Adapters](https://docs.astro.build/en/guides/integrations-guide/)
- [Node adapter](https://docs.astro.build/en/guides/integrations-guide/node/)
- [Server islands](https://docs.astro.build/en/guides/server-islands/)
- [Astro cookies](https://docs.astro.build/en/reference/api-reference/#cookies)
