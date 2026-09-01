# Next.js 데이터 요청과 어댑터

여러 컴포넌트에서 URL 조합, 인증 정보 설정, `fetch`, JSON 파싱, 상태 코드 해석, 오류 문구 변환을 반복하면 API 변경의 영향이 화면 전체로 퍼집니다. 화면은 “어떤 데이터를 읽고 어떤 상태를 보여 줄지”에 집중하고, HTTP 세부사항은 별도의 어댑터가 맡도록 경계를 만듭니다.

또한 Next.js에서는 데이터를 **서버에서 읽을지 브라우저에서 읽을지**, 읽은 값을 **어디에서 기준값으로 관리할지**, 변경 뒤 **어떤 캐시를 갱신할지**를 함께 정해야 합니다.

## 목표

- 컴포넌트와 HTTP 처리 코드를 분리합니다.
- 서버와 브라우저 중 어디에서 데이터를 읽을지 이유를 설명합니다.
- 외부 응답을 TypeScript 타입만 믿지 않고 런타임에 검증합니다.
- HTTP 오류, 응답 형식 오류, 업무 오류를 애플리케이션이 다룰 형태로 변환합니다.
- 캐시 키에 데이터의 실제 정체성을 결정하는 값을 포함합니다.
- 변경 성공 뒤 경로 또는 데이터 태그를 적절히 갱신합니다.
- 테스트에서 대기·실패·응답 순서 역전·충돌을 원하는 순서로 재현합니다.

## 어댑터가 HTTP 세부사항을 맡습니다

화면 컴포넌트가 다음 세부사항을 직접 알고 있으면 같은 코드가 여러 곳에 퍼지기 쉽습니다.

```text
API 기본 주소
URL 경로와 query string
HTTP method
인증 헤더와 credentials
상태 코드의 의미
JSON 파싱
응답 스키마
네트워크 오류 문구
```

컴포넌트가 필요한 동작을 인터페이스로 먼저 표현합니다.

```ts
export interface BoardApi {
  listBoards(signal?: AbortSignal): Promise<BoardSummary[]>;
  createBoard(input: CreateBoardInput): Promise<BoardSummary>;
  renameBoard(
    id: string,
    input: RenameBoardInput
  ): Promise<BoardSummary>;
}
```

이 인터페이스를 사용하는 컴포넌트는 실제 URL이나 상태 코드 해석 방법을 알 필요가 없습니다.

```tsx
async function handleRename(id: string, title: string) {
  try {
    const board = await api.renameBoard(id, { title });
    // 성공 결과 반영
  } catch (error) {
    // 애플리케이션 오류에 맞는 UI 표시
  }
}
```

HTTP 구현은 별도 어댑터에 둡니다.

```ts
export function createHttpBoardApi(baseUrl: string): BoardApi {
  return {
    async listBoards(signal) {
      const response = await fetch(`${baseUrl}/boards`, {
        signal,
        credentials: "include",
      });

      return parseJsonResponse(response, BoardListSchema);
    },

    async createBoard(input) {
      const response = await fetch(`${baseUrl}/boards`, {
        method: "POST",
        credentials: "include",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify(input),
      });

      return parseJsonResponse(response, BoardSummarySchema);
    },

    async renameBoard(id, input) {
      const response = await fetch(
        `${baseUrl}/boards/${encodeURIComponent(id)}`,
        {
          method: "PATCH",
          credentials: "include",
          headers: {
            "content-type": "application/json",
          },
          body: JSON.stringify(input),
        }
      );

      return parseJsonResponse(response, BoardSummarySchema);
    },
  };
}
```

이렇게 하면 API 주소, 인증 방식, 상태 코드 규칙, 응답 형식이 바뀌어도 수정 범위를 어댑터 쪽으로 제한할 수 있습니다.

## 어댑터와 업무 로직을 구분합니다

HTTP 어댑터는 전송 형식을 애플리케이션이 사용할 값으로 바꾸는 역할을 맡습니다.

```text
HTTP 요청/응답
→ 어댑터
→ 애플리케이션 값과 오류
→ 화면 또는 업무 로직
```

예를 들어 다음 책임은 어댑터에 잘 맞습니다.

- URL 만들기
- HTTP method 선택
- 헤더와 body 직렬화
- 응답 body 읽기
- 상태 코드 분류
- 외부 JSON의 런타임 검증
- 네트워크 오류를 애플리케이션 오류로 변환

반면 다음 규칙은 단순 HTTP 세부사항이 아닙니다.

```text
"보드 이름은 중복될 수 없다."
"작성자만 보드를 삭제할 수 있다."
"마감된 보드는 수정할 수 없다."
```

이런 규칙의 최종 판정은 서버의 업무 계층에서 수행해야 합니다. 어댑터는 서버가 반환한 결과를 해석할 뿐 권한과 무결성을 대신 결정하지 않습니다.

## 오류를 문자열 하나로 만들지 않습니다

모든 실패를 `"요청에 실패했습니다"`라는 문자열 하나로 바꾸면 화면에서 적절한 복구 동작을 선택하기 어렵습니다.

예를 들어 애플리케이션 오류를 분류할 수 있습니다.

```ts
export type BoardApiError =
  | { type: "unauthorized" }
  | { type: "forbidden" }
  | { type: "not-found" }
  | { type: "conflict"; message: string }
  | { type: "validation"; fields: Record<string, string> }
  | { type: "invalid-response"; message: string }
  | { type: "network"; message: string }
  | { type: "server"; message: string };
```

화면은 오류 종류에 따라 다른 행동을 할 수 있습니다.

```ts
switch (error.type) {
  case "validation":
    // 필드 오류 표시
    break;

  case "conflict":
    // 최신 서버 값과 사용자 초안 비교
    break;

  case "unauthorized":
    // 로그인 흐름
    break;

  default:
    // 일반 재시도 안내
}
```

상태 코드와 애플리케이션 오류의 대응은 API 계약에 따라 한곳에서 관리합니다.

## 서버에서 읽을 데이터

첫 화면에 꼭 필요하고 브라우저 상호작용 없이 읽을 수 있는 데이터는 Server Component에서 가져오는 것이 자연스러울 수 있습니다.

```tsx
export default async function BoardsPage() {
  const boards = await loadBoardsForCurrentUser();

  return <BoardList boards={boards} />;
}
```

Server Component에서 데이터를 읽으면 다음 장점이 있습니다.

- 데이터베이스 비밀값을 브라우저 번들에 넣지 않습니다.
- 초기 화면에 필요한 데이터를 클라이언트 Effect 이후까지 미루지 않아도 됩니다.
- 서버 전용 서비스나 데이터베이스를 직접 호출할 수 있습니다.
- 브라우저에 필요한 결과만 골라 전달할 수 있습니다.

하지만 “서버에서 읽는다”는 것 자체가 인증과 권한 검사를 대신하지는 않습니다. 서버 코드에서도 현재 사용자가 어떤 데이터에 접근할 수 있는지 확인해야 합니다.

## 같은 애플리케이션 내부라면 HTTP를 거칠 필요가 없는지 확인합니다

Server Component가 같은 Next.js 애플리케이션의 Route Handler를 다시 HTTP로 호출하는 구조가 항상 필요한 것은 아닙니다.

```text
Server Component
→ /api/boards Route Handler
→ boardService.list()
→ 데이터베이스
```

서버 안에서 이미 동일한 업무 서비스를 호출할 수 있다면 다음처럼 직접 재사용할 수 있습니다.

```text
Server Component
→ boardService.list()
→ 데이터베이스
```

이 방식은 불필요한 HTTP 직렬화·파싱과 내부 URL 설정을 줄일 수 있습니다.

```tsx
export default async function BoardsPage() {
  const user = await requireUser();
  const boards = await boardService.listForUser(user.id);

  return <BoardList boards={boards} />;
}
```

반대로 별도 백엔드 서비스나 제3자 API가 실제 경계라면 HTTP 어댑터를 사용하는 것이 맞습니다.

따라서 “서버에서도 항상 API endpoint를 호출한다” 또는 “서버에서는 절대로 HTTP를 쓰지 않는다”라고 정하지 않습니다. 실제 시스템 경계를 기준으로 선택합니다.

## 서버 요청에서 인증 정보의 출처를 확인합니다

브라우저에서는 같은 출처 요청에 쿠키가 자연스럽게 포함될 수 있지만, 서버에서 다른 API를 호출할 때는 인증 정보가 자동으로 전달된다고 가정하면 안 됩니다.

먼저 다음을 정합니다.

```text
현재 사용자 세션은 어디에 있는가?
→ 쿠키 / Authorization 헤더 / 서버 세션 저장소

Server Component가 그 값을 어떻게 읽는가?

외부 API 호출에도 전달해야 하는가?

전달한다면 어떤 최소 정보만 전달하는가?
```

예를 들어 현재 요청의 쿠키를 사용해야 하는 서버 코드는 Next.js의 서버 요청 API를 통해 필요한 값을 읽고, 해당 API 계약에 맞게 인증 정보를 전달합니다.

비밀 토큰 전체나 필요하지 않은 쿠키를 무조건 다른 서비스로 전달하지 않습니다.

## 배포 환경의 API 주소를 브라우저 주소와 혼동하지 않습니다

서버와 브라우저는 같은 URL을 사용할 필요가 없습니다.

```text
브라우저:
https://example.com/api/boards

서버 내부:
http://board-service.internal/boards
```

브라우저에서 접근 가능한 공개 주소와 서버 내부 네트워크 주소가 다를 수 있으므로 `baseUrl`의 소유 위치를 명확히 합니다.

또한 브라우저 번들에서 사용되는 환경 변수에는 비밀값을 넣지 않습니다.

## 브라우저에서 읽을 데이터

브라우저 상호작용에 밀접하게 묶인 데이터는 클라이언트에서 읽는 편이 적합할 수 있습니다.

예를 들면 다음과 같습니다.

- 사용자가 입력할 때마다 바뀌는 검색 결과
- 브라우저에서 주기적으로 다시 읽는 상태
- WebSocket으로 이어서 받는 실시간 데이터
- 특정 사용자 조작 뒤 즉시 갱신해야 하는 목록
- 브라우저에서만 알 수 있는 조건을 사용하는 요청

```tsx
useEffect(() => {
  const controller = new AbortController();

  api.searchUsers(query, controller.signal)
    .then(setUsers)
    .catch(handleError);

  return () => controller.abort();
}, [api, query]);
```

이 경우 컴포넌트 또는 데이터 라이브러리가 다음 수명을 관리해야 합니다.

```text
요청 시작
요청 취소
늦게 도착한 이전 응답
로딩
빈 결과
오류
재시도
```

## 서버와 브라우저 중 한쪽을 기준값으로 정합니다

서버와 브라우저가 같은 데이터를 각각 독립적인 기준값으로 관리하면 서로 다른 화면을 만들기 쉽습니다.

예를 들어 Server Component에서 보드 목록을 읽은 뒤 Client Component가 그 목록을 별도의 `useState`로 복사한다고 가정합니다.

```tsx
// 주의가 필요한 구조
const [boards, setBoards] = useState(initialBoards);
```

이 자체가 항상 잘못된 것은 아닙니다. 문제는 그다음에 서버 데이터와 로컬 복사본 중 **어느 쪽이 최신값의 기준인지 정의하지 않는 것**입니다.

한 가지 구조는 다음과 같습니다.

```text
서버:
초기 데이터를 읽어 전달

브라우저:
초기 데이터를 캐시의 초기값으로 사용
→ 이후 조회·변경·재검증은 하나의 브라우저 캐시가 관리
```

다른 구조는 변경 뒤 서버 데이터를 다시 렌더링해 서버 결과를 계속 기준으로 사용할 수도 있습니다.

중요한 것은 동일한 데이터를 여러 독립 상태에 복사하고 각각 갱신하지 않는 것입니다.

## 외부 응답은 런타임에 검증합니다

TypeScript 타입은 컴파일할 때만 존재합니다. 서버가 실제로 보낸 JSON을 런타임에 검사하지 않습니다.

다음 코드는 안전한 런타임 검증이 아닙니다.

```ts
// 실제 JSON 구조를 검사하지 않습니다.
const board = (await response.json()) as BoardSummary;
```

서버가 다음처럼 잘못된 데이터를 보내도 타입 단언 자체는 실패하지 않습니다.

```json
{
  "id": 42,
  "title": null
}
```

외부 경계에서는 Zod 같은 런타임 스키마로 검사할 수 있습니다.

```ts
const BoardSummarySchema = z.object({
  id: z.string(),
  title: z.string(),
  updatedAt: z.string(),
});

type BoardSummary = z.infer<typeof BoardSummarySchema>;
```

```ts
const raw: unknown = await response.json();
const board = BoardSummarySchema.parse(raw);
```

이제 애플리케이션 내부는 검증을 통과한 값을 사용합니다.

## 응답 파서는 성공 상태와 body 형식을 함께 다룹니다

단순히 `response.ok` 뒤 `response.json()`만 호출하면 여러 경우를 구분하지 못합니다.

```ts
async function parseJsonResponse<T>(
  response: Response,
  schema: z.ZodType<T>
): Promise<T> {
  if (!response.ok) {
    throw await toApplicationError(response);
  }

  const contentType = response.headers.get("content-type") ?? "";

  if (!contentType.includes("application/json")) {
    throw {
      type: "invalid-response",
      message: "JSON 응답이 필요하지만 다른 형식을 받았습니다.",
    } satisfies BoardApiError;
  }

  let body: unknown;

  try {
    body = await response.json();
  } catch {
    throw {
      type: "invalid-response",
      message: "응답 JSON을 읽을 수 없습니다.",
    } satisfies BoardApiError;
  }

  const result = schema.safeParse(body);

  if (!result.success) {
    throw {
      type: "invalid-response",
      message: "서버 응답 형식이 예상한 스키마와 다릅니다.",
    } satisfies BoardApiError;
  }

  return result.data;
}
```

여기서 구분해야 하는 실패는 다음과 같습니다.

```text
HTTP 실패
→ 401, 403, 404, 409, 500 등

본문 형식 실패
→ JSON이 아님
→ 깨진 JSON

스키마 실패
→ JSON이지만 필드 구조가 예상과 다름
```

## `204 No Content`는 JSON 파서에 넣지 않습니다

`204 No Content` 응답에는 body가 없으므로 무조건 `response.json()`을 호출하면 실패합니다.

삭제 API가 `204`를 반환한다면 별도 파서를 사용할 수 있습니다.

```ts
async function expectEmptySuccess(response: Response): Promise<void> {
  if (!response.ok) {
    throw await toApplicationError(response);
  }

  if (response.status !== 204) {
    throw {
      type: "invalid-response",
      message: `204를 예상했지만 ${response.status}를 받았습니다.`,
    } satisfies BoardApiError;
  }
}
```

API가 `200`과 JSON을 반환하는 계약이라면 그 계약에 맞춰 별도의 파서를 사용합니다. 중요한 것은 실제 응답 계약을 코드로 표현하는 것입니다.

## 오류 응답도 형식을 검증합니다

성공 응답만 검증하고 오류 body는 바로 신뢰하면 같은 문제가 반복됩니다.

예를 들어 서버가 다음 형태를 약속한다고 가정합니다.

```ts
const ApiErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  fields: z.record(z.string(), z.string()).optional(),
});
```

`toApplicationError()`는 상태 코드와 오류 body를 함께 사용해 애플리케이션 오류로 변환합니다.

```text
400 + VALIDATION_ERROR
→ validation

401
→ unauthorized

403
→ forbidden

404
→ not-found

409
→ conflict

5xx
→ server
```

상태 코드만으로 충분한지, 오류 `code`까지 필요한지는 API 계약에 따라 정합니다.

## 캐시는 먼저 “무엇이 같은 데이터인가”를 정의합니다

캐시를 사용하기 전에 캐시 키가 어떤 데이터를 가리키는지 정합니다.

예를 들어 다음 요청을 생각합니다.

```text
GET /boards?owner=me&sort=updated&page=2
```

다음 값이 결과를 바꾼다면 캐시 키에도 반영되어야 합니다.

- 현재 사용자 또는 권한 범위
- 검색어
- 필터
- 정렬
- 페이지 번호
- 언어
- 조직 또는 tenant
- API 버전처럼 결과를 바꾸는 조건

개념적인 키는 다음과 같을 수 있습니다.

```ts
type BoardListKey = {
  userId: string;
  organizationId: string;
  filter: string;
  sort: string;
  page: number;
};
```

실제 라이브러리가 배열 키를 사용한다면 다음처럼 표현할 수도 있습니다.

```ts
["boards", userId, organizationId, filter, sort, page]
```

핵심은 **서로 다른 응답이 같은 캐시 항목에 섞이지 않게 하는 것**입니다.

## 사용자별 데이터와 공유 캐시를 구분합니다

사용자 A와 사용자 B가 서로 다른 결과를 받아야 하는 요청을 같은 공유 캐시 항목으로 취급하면 데이터가 잘못 노출될 수 있습니다.

예를 들어 다음 데이터는 사용자나 조직에 따라 달라질 수 있습니다.

```text
내 보드 목록
내 알림
내 권한
조직 내부 문서
```

따라서 캐시 범위를 설계할 때 다음을 확인합니다.

```text
이 데이터는 모든 사용자에게 같은가?
사용자별인가?
조직별인가?
권한에 따라 결과가 달라지는가?
```

“캐시를 사용한다”와 “공개적으로 공유 가능한 데이터다”는 같은 뜻이 아닙니다.

## 캐시의 네 가지 질문

캐시를 사용한다면 최소한 다음 질문에 답할 수 있어야 합니다.

1. **키**: 어떤 요청들이 같은 데이터를 의미합니까?
2. **수명**: 얼마 동안 이전 값을 보여 줘도 됩니까?
3. **변경 뒤 갱신**: 어떤 변경이 어떤 캐시 항목을 무효화합니까?
4. **재검증 UX**: 새 값을 가져오는 동안 이전 데이터를 계속 보여 줍니까?

예를 들어 게시물 목록처럼 약간 오래된 값을 잠시 보여 줘도 된다면 stale-while-revalidate가 적합할 수 있습니다.

반대로 사용자가 방금 자신의 이름을 수정했다면 변경 직후 이전 이름을 계속 보여 주지 않는 “read-your-own-writes”가 더 중요할 수 있습니다.

## Next.js의 경로 재검증과 데이터 재검증을 구분합니다

Next.js App Router에서는 변경 뒤 특정 경로나 데이터 태그를 재검증할 수 있습니다.

`revalidatePath`는 특정 페이지 또는 레이아웃 경로를 대상으로 합니다.

```ts
"use server";

import { revalidatePath } from "next/cache";

export async function createBoard(input: CreateBoardInput) {
  await boardService.create(input);

  revalidatePath("/boards");
}
```

이 코드는 `/boards` 경로를 다시 검증해야 한다고 표시합니다.

반면 같은 데이터가 여러 경로에서 사용된다면 경로보다 데이터 자체에 태그를 붙이는 편이 더 정확할 수 있습니다.

```text
/boards
/dashboard
/profile
```

세 화면이 모두 동일한 `boards` 데이터를 사용한다면 하나의 경로만 재검증해서는 다른 화면의 캐시가 남을 수 있습니다.

## 데이터 태그로 관련 캐시를 묶을 수 있습니다

캐시된 데이터에 태그를 붙였다면 변경 뒤 같은 태그를 대상으로 갱신할 수 있습니다.

현재 Next.js에서는 용도에 따라 `updateTag`와 `revalidateTag`의 의미를 구분하는 것이 중요합니다.

```text
updateTag(tag)
→ Server Action에서 사용
→ 해당 태그를 즉시 만료
→ 다음 읽기는 새 데이터를 기다림
→ 변경한 사용자가 바로 최신값을 봐야 하는 경우에 적합

revalidateTag(tag, "max")
→ Server Action 또는 Route Handler에서 사용 가능
→ stale-while-revalidate
→ 이전 값을 잠시 보여 줘도 되는 경우에 적합
```

예를 들어 사용자가 보드를 수정한 직후 반드시 최신 보드를 읽어야 한다면 Server Action에서 `updateTag`를 사용할 수 있습니다.

```ts
"use server";

import { updateTag } from "next/cache";

export async function renameBoard(
  id: string,
  input: RenameBoardInput
) {
  await boardService.rename(id, input);

  updateTag(`board:${id}`);
  updateTag("boards");
}
```

반대로 외부 webhook이 콘텐츠 갱신을 알려 주고 약간의 stale 데이터가 허용된다면 Route Handler에서 다음처럼 재검증할 수 있습니다.

```ts
import { revalidateTag } from "next/cache";

export async function POST() {
  // webhook 인증과 검증
  revalidateTag("boards", "max");

  return Response.json({ ok: true });
}
```

태그 기반 캐시를 실제로 사용하려면 해당 데이터를 캐시하고 태그를 연결하는 설정도 함께 있어야 합니다.

## `revalidatePath`와 태그 재검증은 목적이 다릅니다

다음처럼 생각하면 구분하기 쉽습니다.

```text
"이 화면을 다시 계산해야 한다."
→ revalidatePath

"이 데이터가 바뀌었으므로 사용하는 모든 곳에서 갱신해야 한다."
→ updateTag / revalidateTag
```

한 변경이 특정 화면과 공유 데이터 모두에 영향을 준다면 두 종류의 재검증을 함께 사용할 수도 있습니다.

무조건 넓은 경로를 전부 무효화하면 구현은 단순해 보이지만 불필요한 재계산이 커집니다. 반대로 너무 좁게 무효화하면 다른 화면에 오래된 값이 남습니다.

## 변경 요청의 전체 흐름을 정합니다

변경 요청은 단순히 `POST`나 `PATCH` 한 번으로 끝나지 않습니다.

```text
입력 검사
→ 사용자/권한 확인
→ 대기 UI 또는 낙관적 변경
→ 요청 전송
→ 서버 업무 규칙 검사
→ 저장
→ 성공 결과 반영
→ 관련 캐시 갱신
```

실패 종류에 따라 다음 행동도 달라집니다.

```text
검증 실패
→ 입력 유지 + 필드 오류 표시

인증 실패
→ 로그인 또는 세션 복구

권한 실패
→ 작업 불가 안내

충돌
→ 최신 서버 값과 초안 비교

일시적 네트워크 실패
→ 입력 유지 + 재시도 가능

서버 내부 오류
→ 입력 보존 + 일반 오류 안내
```

사용자가 다시 입력하기 어려운 초안은 실패했다고 조용히 버리지 않습니다.

## `409 Conflict`는 “다시 시도”만으로 해결되지 않을 수 있습니다

예를 들어 사용자가 제목을 편집하는 동안 다른 사용자가 같은 보드를 수정했다고 가정합니다.

```text
사용자 A가 version 5 읽음
사용자 B가 수정 → version 6
사용자 A가 version 5 기준 수정 전송
→ 서버가 충돌 감지
→ 409 Conflict
```

이때 무조건 같은 요청을 재시도하면 여전히 오래된 version을 기준으로 하기 때문에 다시 충돌할 수 있습니다.

충돌 처리에는 보통 다음 정보가 필요합니다.

```text
사용자의 초안
최신 서버 값
어느 필드가 달라졌는지
다시 적용 가능한지
사용자 선택이 필요한지
```

예를 들어 화면 상태를 다음처럼 유지할 수 있습니다.

```ts
type ConflictState = {
  draft: RenameBoardInput;
  latest: BoardSummary;
};
```

이제 “최신 값으로 덮어쓰기”, “내 변경 다시 적용”, “취소” 같은 실제 복구 흐름을 만들 수 있습니다.

실제 API가 `409`를 사용하는지, version/ETag 같은 어떤 동시성 정보를 요구하는지는 해당 API 계약을 따릅니다.

## 낙관적 변경과 캐시 무효화는 같은 문제가 아닙니다

낙관적 변경은 **서버 응답 전에 화면을 어떻게 보일지**에 관한 문제입니다.

캐시 무효화는 **서버 변경 뒤 어떤 저장된 조회 결과를 다시 최신화할지**에 관한 문제입니다.

예를 들어 다음 흐름을 사용할 수 있습니다.

```text
클라이언트:
임시 항목 추가

서버:
실제 항목 생성 성공

클라이언트:
임시 항목을 서버 결과로 교체

캐시:
boards 관련 데이터를 무효화 또는 갱신
```

낙관적 UI를 구현했다고 해서 다른 화면의 캐시까지 자동으로 최신이 되는 것은 아닙니다.

## 변경 성공 응답을 버리지 않습니다

서버는 저장 과정에서 값을 정규화하거나 새로운 값을 생성할 수 있습니다.

예를 들어 생성 요청의 입력은 다음과 같을 수 있습니다.

```json
{
  "title": "  React Study  "
}
```

서버 응답은 다음과 같을 수 있습니다.

```json
{
  "id": "b_123",
  "title": "React Study",
  "updatedAt": "2026-08-29T00:00:00Z"
}
```

따라서 성공하면 클라이언트가 만든 임시 값을 그대로 확정하기보다 서버가 반환한 검증된 결과를 반영합니다.

```ts
const created = await api.createBoard(input);

setBoards((current) =>
  current.map((board) =>
    board.clientId === clientId ? created : board
  )
);
```

## Server Action과 Route Handler의 역할

Next.js에서는 서버 변경 경계를 여러 방식으로 만들 수 있습니다.

### Server Action

Server Action은 React/Next.js UI와 밀접한 서버 변경 작업에 적합합니다.

```ts
"use server";

export async function renameBoardAction(formData: FormData) {
  const user = await requireUser();

  const input = RenameBoardSchema.parse({
    id: formData.get("id"),
    title: formData.get("title"),
  });

  await boardService.rename(user, input);

  // 필요한 캐시 갱신
}
```

다음 책임은 여전히 필요합니다.

- 입력 검증
- 인증
- 권한 검사
- 업무 규칙
- 오류 분류
- 캐시 갱신

`"use server"`를 붙였다고 해서 함수 호출이 신뢰할 수 있는 내부 호출이 되는 것은 아닙니다. Client Component에서 호출 가능한 Server Action의 입력은 외부 입력처럼 검증합니다.

### Route Handler

Route Handler는 `app/.../route.ts`에 HTTP endpoint를 만들 때 사용합니다.

```ts
export async function POST(request: Request) {
  const user = await requireUser();
  const raw: unknown = await request.json();
  const input = CreateBoardSchema.parse(raw);

  const board = await boardService.create(user, input);

  return Response.json(board, { status: 201 });
}
```

Route Handler가 적합한 예는 다음과 같습니다.

- 브라우저 `fetch`가 호출해야 하는 HTTP API
- 모바일 앱이나 다른 서비스도 호출하는 endpoint
- webhook 수신
- 외부 시스템과의 HTTP 통합
- 파일이나 다른 HTTP 응답 형식 처리

Server Action과 Route Handler는 **전송 방식**이 다릅니다. 핵심 업무 규칙을 각각 복사하지 않습니다.

```text
Server Action ─┐
               ├→ boardService → repository/database
Route Handler ─┘
```

## UI 컴포넌트가 데이터베이스 책임까지 맡지 않게 합니다

다음처럼 한 함수에 모든 책임이 모이면 테스트와 변경이 어렵습니다.

```text
React UI
+ FormData 파싱
+ 인증
+ 권한 검사
+ SQL
+ 캐시 정책
+ 오류 문구
```

경계를 나누면 각 부분을 독립적으로 검증하기 쉬워집니다.

```text
UI
→ Action/Route Handler
→ 입력 검증
→ 업무 서비스
→ 저장소

외부 HTTP API
→ HTTP 어댑터
→ 검증된 애플리케이션 값
```

프로젝트 규모가 작다면 파일 수를 억지로 늘릴 필요는 없습니다. 중요한 것은 책임을 구분해 한 계층의 세부사항이 다른 계층 전체로 퍼지지 않게 하는 것입니다.

## 테스트용 어댑터

컴포넌트 테스트에서 실제 네트워크를 사용하면 응답 순서와 실패 시점을 정확하게 제어하기 어렵습니다.

테스트에서는 같은 인터페이스를 구현하는 가짜 어댑터를 사용할 수 있습니다.

```ts
type Deferred<T> = {
  promise: Promise<T>;
  resolve(value: T): void;
  reject(error: unknown): void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;

  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}
```

간단한 테스트용 API는 요청을 보관하고 테스트가 직접 완료시킬 수 있습니다.

```ts
export function createDeferredBoardApi() {
  const listRequests: Deferred<BoardSummary[]>[] = [];

  const api: BoardApi = {
    listBoards() {
      const request = deferred<BoardSummary[]>();
      listRequests.push(request);
      return request.promise;
    },

    async createBoard() {
      throw new Error("이 테스트에서는 사용하지 않습니다.");
    },

    async renameBoard() {
      throw new Error("이 테스트에서는 사용하지 않습니다.");
    },
  };

  return {
    api,
    listRequests,
  };
}
```

이제 실제 시간을 기다리지 않고 요청 순서를 제어할 수 있습니다.

```text
첫 번째 검색 시작
두 번째 검색 시작
→ 두 번째 요청 resolve
→ 첫 번째 요청 resolve
→ 화면에는 두 번째 검색 결과가 남는지 확인
```

## 테스트에서 재현할 상태

최소한 다음 상황을 재현할 수 있으면 비동기 화면의 경계가 훨씬 명확해집니다.

- 요청이 계속 대기 중임
- 정상적으로 빈 목록을 받음
- 성공 상태지만 스키마와 다른 응답을 받음
- 네트워크 오류가 발생함
- 인증 또는 권한 오류가 발생함
- 이전 요청이 최신 요청보다 늦게 끝남
- `409` 충돌이 발생함
- 변경 성공 뒤 서버가 정규화한 결과를 받음
- 변경 성공 뒤 새 목록을 다시 읽음

컴포넌트 테스트는 가짜 `BoardApi`를 사용해 UI 상태를 검사합니다.

실제 HTTP 변환은 별도의 통합 테스트에서 확인합니다.

```text
컴포넌트 테스트:
loading / success / error / conflict UI
요청 순서 역전
사용자 입력 유지

HTTP 어댑터 테스트:
URL
method
headers
body
status code 변환
JSON/스키마 검증
AbortSignal 전달
```

이렇게 하면 컴포넌트 테스트가 실제 서버의 속도나 네트워크 상태에 의존하지 않습니다.

## 데이터 경계를 정할 때 확인할 질문

새 데이터 흐름을 만들 때 다음 질문을 순서대로 확인합니다.

1. 이 데이터의 최종 기준값은 어디에 있습니까?
2. 첫 화면에 반드시 필요한 데이터입니까?
3. 서버에서 직접 서비스나 데이터베이스를 읽을 수 있습니까?
4. 브라우저 상호작용 때문에 클라이언트 요청이 필요합니까?
5. 외부 응답을 어느 경계에서 런타임 검증합니까?
6. HTTP 오류를 화면이 이해할 어떤 오류 종류로 바꿉니까?
7. 같은 데이터를 가리키는 캐시 키는 무엇입니까?
8. 사용자·조직·필터·언어 중 결과를 바꾸는 값이 키에 빠지지 않았습니까?
9. 변경 성공 뒤 어떤 경로나 데이터 태그가 오래된 값이 됩니까?
10. 변경 직후 최신값이 반드시 보여야 합니까, 아니면 잠시 stale 데이터가 허용됩니까?
11. 충돌이나 네트워크 실패가 발생해도 사용자의 초안을 보존합니까?
12. 테스트에서 응답 완료 순서를 직접 제어할 수 있습니까?

## 흔한 실수

- 컴포넌트마다 `fetch`, URL 조합, JSON 파싱을 반복합니다.
- HTTP 어댑터 안에 권한과 업무 규칙까지 중복 구현합니다.
- 모든 실패를 하나의 오류 문자열로 바꿉니다.
- TypeScript 타입 단언만 믿고 외부 응답을 런타임에 검증하지 않습니다.
- `204 No Content`에도 무조건 `response.json()`을 호출합니다.
- 성공 응답만 검증하고 오류 응답 body는 그대로 신뢰합니다.
- Server Component가 같은 애플리케이션의 Route Handler를 이유 없이 다시 HTTP로 호출합니다.
- 서버 요청에서 브라우저 쿠키나 인증 정보가 자동으로 전달된다고 가정합니다.
- 서버와 브라우저가 같은 데이터의 독립적인 기준값을 각각 가집니다.
- 캐시 키에서 사용자, 조직, 필터, 정렬, 언어처럼 결과를 바꾸는 값을 빠뜨립니다.
- 사용자별 데이터를 모든 사용자에게 동일한 공유 데이터처럼 취급합니다.
- 변경 성공 뒤 오래된 캐시를 그대로 둡니다.
- `revalidatePath`와 데이터 태그 재검증의 목적을 구분하지 않습니다.
- 변경 직후 최신값이 필요한데 stale-while-revalidate만 사용합니다.
- `409` 충돌 뒤 사용자의 입력을 조용히 버립니다.
- 낙관적 UI를 갱신했으므로 다른 화면의 캐시도 자동으로 최신이라고 생각합니다.
- 서버가 반환한 확정 결과를 무시하고 클라이언트의 임시 값을 그대로 확정합니다.
- Server Action을 신뢰할 수 있는 내부 함수처럼 취급해 입력과 권한 검사를 생략합니다.
- 컴포넌트 테스트가 실제 네트워크와 실제 시간에 의존합니다.

## 완료 기준

- 화면 코드와 HTTP 어댑터의 책임을 구분합니다.
- 어댑터와 서버 업무 규칙의 책임을 구분합니다.
- 서버 또는 브라우저에서 데이터를 읽기로 한 이유를 설명합니다.
- 같은 애플리케이션 내부에서 HTTP 호출과 서비스 직접 호출 중 하나를 선택한 이유를 설명합니다.
- 외부 성공·오류 응답을 런타임 스키마로 검사합니다.
- 빈 body와 JSON 응답을 API 계약에 맞게 구분합니다.
- HTTP 실패를 애플리케이션이 처리할 수 있는 오류 종류로 변환합니다.
- 같은 데이터의 기준값을 서버와 브라우저에 독립적으로 중복 저장하지 않습니다.
- 캐시 키에 결과를 바꾸는 사용자·조직·필터 등의 조건을 포함합니다.
- 변경 성공 뒤 어떤 경로나 데이터 태그를 갱신해야 하는지 설명합니다.
- 즉시 최신값이 필요한 경우와 stale-while-revalidate가 허용되는 경우를 구분합니다.
- 충돌이 발생해도 사용자의 초안과 최신 서버 값을 함께 보존할 수 있습니다.
- Server Action과 Route Handler가 전송 경계이고 업무 규칙은 공통 서버 계층에서 재사용할 수 있음을 설명합니다.
- 테스트에서 요청 대기, 실패, 응답 순서 역전, 충돌을 원하는 순서로 재현합니다.

## 연결 exercise

[`user-directory`](../../exercises/user-directory/README.md)의 가짜 검색 API로 요청 완료 순서를 제어합니다. 실제 HTTP 변환은 [`notes-api`](../../exercises/notes-api/README.md)에서 확인합니다.
