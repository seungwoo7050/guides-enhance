# Form, endpoint와 Astro Actions

Astro에서 사용자의 입력을 처리하는 방법은 하나가 아닙니다. 정적 site에서도 외부 service로 제출하는 HTML form을 만들 수 있고, build 시 JSON·XML 파일을 생성할 수 있습니다. 요청을 받을 server runtime이 있다면 server endpoint나 Astro Actions를 사용할 수 있습니다.

기능을 구현하기 전에 먼저 **build에서 끝나는 작업인지, 사용자의 요청이 들어올 때 server code가 필요한지** 구분합니다.

## 이 문서를 읽는 시점

- 문의, 구독, 검색 또는 편집 form을 추가합니다.
- JSON, RSS, XML, text 파일을 build 결과에 생성합니다.
- browser에서 호출할 server function이 필요합니다.
- 입력 검사와 오류 반환을 여러 곳에서 반복하고 있습니다.
- Astro Actions와 일반 API endpoint 중 무엇을 쓸지 결정해야 합니다.

## 먼저 실행 시점을 정합니다

| 요구사항 | 적합한 방식 |
| --- | --- |
| JavaScript 없이 다른 service로 제출 | HTML form |
| build 때 JSON·RSS·XML 생성 | static endpoint |
| 외부 client도 호출하는 HTTP API | server endpoint |
| 같은 Astro application의 form·client code가 server function 호출 | Astro Actions |
| browser 안에서만 끝나는 작은 입력 | 일반 `<script>` 또는 island |

모든 form에 Actions가 필요한 것은 아닙니다. 정적 site의 newsletter form이 provider URL로 바로 제출된다면 Astro server를 추가할 이유가 없습니다.

## HTML form을 기본으로 시작합니다

```astro
<form method="post" action="https://forms.example.com/subscribe">
  <label for="email">이메일</label>
  <input id="email" name="email" type="email" required />
  <button type="submit">구독</button>
</form>
```

다음을 먼저 확인합니다.

- JavaScript가 없어도 제출할 수 있는가?
- 입력 이름과 method가 수신 service의 요구와 맞는가?
- 성공·실패 뒤 사용자가 볼 page가 있는가?
- 개인정보 수집 목적과 보관 기간을 알리는가?
- spam 방지와 rate limit은 누가 처리하는가?

Browser validation은 사용자 입력을 돕는 기능입니다. server 또는 외부 service에서도 같은 조건을 다시 검사해야 합니다.

## Static endpoint는 build 파일을 생성합니다

`src/pages/resources.json.ts`처럼 파일 이름에 출력 확장자를 포함합니다.

```ts
import type { APIRoute } from "astro";

export const GET = (async () => {
  const resources = await readResources();
  return new Response(JSON.stringify(resources), {
    headers: { "content-type": "application/json; charset=utf-8" }
  });
}) satisfies APIRoute;
```

기본 static output에서는 이 함수가 build 중 실행되고 `dist/resources.json`을 만듭니다. 요청마다 실행되는 API가 아닙니다.

적합한 용도:

- 공개 JSON index
- RSS·Atom feed
- sitemap 보조 파일
- manifest
- 고정 text export

주의할 점:

- private field를 제거합니다.
- HTML page와 같은 source data를 사용합니다.
- build마다 결과가 재생성됨을 명시합니다.
- `content-type`과 cache 설정을 확인합니다.
- endpoint가 실패하면 build를 실패시킬지 결정합니다.

## Server endpoint는 요청마다 실행됩니다

Server endpoint를 사용하려면 adapter가 있어야 합니다. 기본 static output에서 특정 endpoint만 요청 시 실행하려면 다음을 추가합니다.

```ts
export const prerender = false;

export async function POST({ request }: { request: Request }) {
  const raw: unknown = await request.json().catch(() => null);
  const command = parseCommand(raw);
  const result = await saveCommand(command);

  return Response.json(result, { status: 201 });
}
```

Server endpoint가 적합한 경우:

- 외부 client가 명시적인 HTTP contract를 사용합니다.
- method, status, header와 body 형식을 직접 소유해야 합니다.
- webhook을 받습니다.
- file upload나 streaming response가 필요합니다.
- 다른 application과 공유할 API입니다.

다음을 직접 구현해야 합니다.

- body parsing과 size 제한
- authentication과 authorization
- runtime validation
- status code와 error body
- CORS
- CSRF 대응
- rate limit
- timeout과 logging

## Astro Actions는 같은 application의 server function 호출에 적합합니다

Actions는 `src/actions/index.ts`의 `server` object에서 정의합니다.

```ts
import { defineAction } from "astro:actions";
import { z } from "astro/zod";

export const server = {
  subscribe: defineAction({
    accept: "form",
    input: z.object({
      email: z.email()
    }),
    handler: async ({ email }) => {
      const subscription = await saveSubscription(email);
      return { id: subscription.id };
    }
  })
};
```

Astro page에서는 type-safe action URL을 form에 연결할 수 있습니다.

```astro
---
import { actions } from "astro:actions";

const result = Astro.getActionResult(actions.subscribe);
---

<form method="POST" action={actions.subscribe}>
  <label for="email">이메일</label>
  <input id="email" name="email" type="email" required />
  <button type="submit">구독</button>
</form>

{result?.error && <p role="alert">입력값을 확인해 주세요.</p>}
{result?.data && <p role="status">구독을 신청했습니다.</p>}
```

Actions가 처리해 주는 부분:

- JSON 또는 form data 읽기
- Zod 입력 검사
- client에서 호출할 type 생성
- 성공 결과와 `ActionError` 형식 통일

Actions가 대신하지 않는 부분:

- 사용자의 권한 확인
- transaction
- idempotency
- CSRF·rate limit 검토
- 오류 log와 monitoring
- 외부 system 실패 복구

## Action과 endpoint 선택 기준

### Action을 선택합니다

- caller가 같은 Astro application입니다.
- form과 UI code에서 server function을 호출합니다.
- 입력 schema와 return type을 공유하고 싶습니다.
- 별도 public API가 필요하지 않습니다.

### Endpoint를 선택합니다

- HTTP contract 자체가 제품의 공개 기능입니다.
- webhook 또는 외부 application이 호출합니다.
- status, header, streaming과 content type을 세밀하게 제어합니다.
- Astro 이외의 client가 같은 API를 사용합니다.

Action을 API의 일반 대체품으로 보지 않습니다. 외부 caller가 필요한데 Actions 내부 형식에 묶으면 application 교체와 debugging이 어려워집니다.

## 변경 작업은 원자적으로 처리합니다

입력 검사를 통과한 뒤에도 저장 작업이 부분적으로 실패할 수 있습니다.

```text
입력 검사
→ 사용자와 권한 확인
→ 현재 version 확인
→ transaction에서 변경
→ 결과 반환
```

예를 들어 주문과 재고를 함께 바꾸면서 둘 중 하나만 저장되면 안 됩니다. Action인지 endpoint인지와 관계없이 database transaction과 unique constraint가 correctness를 보장해야 합니다.

## 중복 제출을 처리합니다

Button을 잠그는 것만으로 중복 요청을 막을 수 없습니다. reload, network retry와 두 tab에서 같은 command가 올 수 있습니다.

- 생성 요청에 idempotency key가 필요한지 확인합니다.
- unique constraint로 중복을 막습니다.
- 이미 처리한 command의 결과를 다시 반환할 수 있게 합니다.
- 저장 중 표시와 재시도 문구를 제공합니다.
- POST를 무조건 자동 retry하지 않습니다.

## 오류를 사용자 메시지와 진단 정보로 나눕니다

사용자에게는 다음 행동이 보이게 합니다.

```text
이메일 형식을 확인해 주세요.
잠시 후 다시 시도해 주세요.
로그인한 계정에는 수정 권한이 없습니다.
다른 변경이 먼저 저장되었습니다. 최신 값을 확인해 주세요.
```

Server log에는 request id, action/route 이름, release, 오류 종류와 원인을 남깁니다. token, cookie, password와 전체 form body는 남기지 않습니다.

## 완료 기준

- build-time endpoint와 server endpoint의 실행 시점을 구분할 수 있습니다.
- HTML form, Action과 endpoint 가운데 필요한 방식만 선택할 수 있습니다.
- Actions가 자동화하는 부분과 application이 직접 보장할 부분을 구분할 수 있습니다.
- 입력 검사, 권한, transaction과 중복 제출을 서로 다른 문제로 다룰 수 있습니다.
- 사용자 오류와 운영 진단 정보를 분리할 수 있습니다.

## 공식 문서

- [Forms](https://docs.astro.build/en/recipes/build-forms/)
- [Endpoints](https://docs.astro.build/en/guides/endpoints/)
- [Actions](https://docs.astro.build/en/guides/actions/)
- [Actions API](https://docs.astro.build/en/reference/modules/astro-actions/)
