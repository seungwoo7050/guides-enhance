# Data loading과 runtime validation

TypeScript type은 API, CMS와 browser storage의 실제 값을 검사하지 않습니다. Astro가 build에서 data를 읽더라도 source가 잘못된 JSON을 반환하면 page가 잘못 생성되거나 build가 예측하기 어려운 위치에서 실패할 수 있습니다. 외부 data를 사용하는 위치에서 `unknown`으로 받고 필요한 field를 확인합니다.

## 이 문서를 읽는 시점

- build에서 remote API나 CMS를 읽습니다.
- on-demand route가 database 또는 service를 호출합니다.
- browser island가 JSON endpoint를 호출합니다.
- environment variable과 secret을 사용합니다.
- data 최신성과 build 실패 기준을 정해야 합니다.

## 먼저 data가 필요한 시점을 정합니다

### Build-time fetch

```astro
---
const response = await fetch("https://example.test/resources");
const data = await response.json();
---
```

적합한 경우:

- 모든 방문자가 같은 data를 봅니다.
- build 주기만큼 늦어도 됩니다.
- static HTML과 SEO가 중요합니다.
- remote source 호출 횟수를 줄이고 싶습니다.

문제:

- source 장애가 build를 막을 수 있습니다.
- deploy 전까지 data가 갱신되지 않습니다.
- 대량 fetch가 build 시간을 늘립니다.

### On-demand server fetch

적합한 경우:

- 요청마다 data가 달라집니다.
- cookie, session 또는 사용자 권한이 필요합니다.
- 최신 data가 중요합니다.

문제:

- adapter와 server 비용이 필요합니다.
- remote source latency가 page 응답에 영향을 줍니다.
- timeout, cache와 장애 처리가 runtime 문제로 바뀝니다.

### Browser fetch

적합한 경우:

- 사용자 event 뒤에만 data가 필요합니다.
- public API이고 browser에서 직접 호출해도 됩니다.
- 초기 HTML에 없어도 됩니다.

문제:

- loading/error UI가 필요합니다.
- CORS와 public credential을 고려합니다.
- SEO와 no-JS 접근에서 data가 보이지 않을 수 있습니다.

## HTTP 성공과 data 형식 성공을 분리합니다

```ts
const response = await fetch(url, { signal: AbortSignal.timeout(5_000) });
if (!response.ok) {
  throw new Error(`Resource request failed: ${response.status}`);
}

const raw: unknown = await response.json();
const resources = parseResources(raw);
```

`response.ok`는 status 범위만 확인합니다. body가 예상한 object인지, field가 누락됐는지와 중복 id가 있는지는 별도로 검사합니다.

## 작은 parser로 필요한 field를 검사합니다

Library를 쓰지 않는 경우 다음처럼 작성할 수 있습니다.

```ts
type Resource = {
  id: string;
  title: string;
};

export function parseResource(value: unknown): Resource {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("resource가 object가 아닙니다.");
  }

  const record = value as Record<string, unknown>;
  if (typeof record.id !== "string" || record.id.length === 0) {
    throw new Error("resource.id가 비어 있습니다.");
  }
  if (typeof record.title !== "string" || record.title.length > 80) {
    throw new Error("resource.title 길이가 올바르지 않습니다.");
  }

  return { id: record.id, title: record.title };
}
```

Zod, Valibot 등 validation library를 사용할 수 있지만, schema가 실제 사용자 조건과 일치하는지 확인해야 합니다.

## Content Collection schema와 runtime parser를 구분합니다

- Content Collection schema: loader가 읽은 entry를 build에서 검사합니다.
- Runtime parser: browser fetch, on-demand API와 storage처럼 실행 중 들어오는 값을 검사합니다.

같은 data shape를 사용한다면 schema를 공유할 수 있습니다. 그러나 build-time `Date` object와 JSON ISO string처럼 source 형식이 다르면 별도 parser가 더 명확할 수 있습니다.

## Page에 맞는 model로 줄입니다

Remote response 전체를 component에 전달하지 않습니다.

```text
remote response
→ runtime validation
→ application model
→ page summary
→ island props 또는 endpoint response
```

제거할 field:

- internal id
- 권한 정보
- token
- debug field
- page가 사용하지 않는 nested object
- authoring용 원본 body

공개 endpoint와 client bundle에 어떤 field가 들어가는지 test로 고정합니다.

## Timeout과 retry를 명시합니다

Build와 runtime fetch 모두 무한히 기다리면 안 됩니다.

- 모든 요청에 timeout을 둡니다.
- retry는 idempotent request와 일시적 오류에만 제한합니다.
- exponential backoff와 최대 횟수를 둡니다.
- `429`의 `Retry-After`를 확인합니다.
- build pipeline 전체 제한 시간보다 짧게 설정합니다.

POST와 결제처럼 상태를 바꾸는 요청을 무조건 재시도하지 않습니다. idempotency key나 source API의 보장을 확인합니다.

## Build 실패와 fallback을 선택합니다

### Build 실패가 맞는 경우

- 핵심 content가 없음
- schema가 깨짐
- canonical URL을 만들 수 없음
- 필수 asset을 읽지 못함
- 잘못된 data를 배포하는 것이 더 위험함

### 이전 snapshot을 사용할 수 있는 경우

- data가 참고용임
- 최신성이 약간 늦어도 됨
- snapshot 생성 시각을 표시할 수 있음
- source 장애와 stale data를 monitoring함

### Section을 제외할 수 있는 경우

- 선택 기능임
- page 핵심 내용이 유지됨
- 사용자에게 숨은 오류가 아니라 운영 log와 alert가 있음

Fallback을 넣었다는 이유로 build가 계속 성공하게만 만들지 않습니다. stale data가 얼마나 오래 허용되는지 정합니다.

## Secret과 public 환경 변수를 분리합니다

- private API key는 component script 또는 server function에서만 읽습니다.
- `PUBLIC_` prefix 값은 browser에 노출될 수 있다고 가정합니다.
- env object 전체를 JSON으로 출력하지 않습니다.
- log에 request header와 response body 전체를 남기지 않습니다.
- build 결과에서 canary 문자열을 검색해 client 노출을 검사할 수 있습니다.

Static build가 private API key를 사용해 data를 읽는 것은 가능하지만, 결과 HTML에 API response의 private field가 포함되지 않아야 합니다.

## Cache와 최신성

다음 값을 문서화합니다.

- source data가 바뀌는 주기
- build를 시작하는 조건
- CDN cache TTL
- on-demand route cache 여부
- stale 허용 시간
- manual purge와 rollback 방법

`fetch()`를 사용했다는 이유만으로 Astro가 application에 맞는 최신성을 자동으로 보장하지 않습니다. build trigger와 hosting cache를 함께 봅니다.

## Browser storage도 외부 입력입니다

```ts
function readIds(raw: string | null): string[] {
  try {
    const parsed: unknown = JSON.parse(raw ?? "[]");
    return Array.isArray(parsed)
      ? parsed.filter((value): value is string => typeof value === "string")
      : [];
  } catch {
    return [];
  }
}
```

이전 application version이 남긴 값, extension이나 사용자가 바꾼 값이 들어올 수 있습니다. parse 실패로 핵심 page가 crash하지 않게 보조 기능을 분리합니다.

## 완료 기준

- data가 build, server 요청, browser 가운데 언제 필요한지 결정할 수 있습니다.
- HTTP status와 body validation을 분리할 수 있습니다.
- 외부 response를 page model로 줄일 수 있습니다.
- timeout, retry와 fallback 기준을 명시할 수 있습니다.
- private env와 public output을 분리할 수 있습니다.

## 공식 문서

- [Data fetching](https://docs.astro.build/en/guides/data-fetching/)
- [Environment variables](https://docs.astro.build/en/guides/environment-variables/)
- [Content collections](https://docs.astro.build/en/guides/content-collections/)
