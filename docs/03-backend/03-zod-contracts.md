# Zod를 이용한 요청·응답 검증

HTTP 본문, 경로 매개변수, 쿼리, 헤더와 WebSocket 메시지는 모두 **외부에서 들어오는 신뢰할 수 없는 값**입니다. TypeScript 타입은 컴파일할 때만 존재하고 실행 중에는 사라지므로, 서버가 실제로 받은 값이 타입 선언과 일치하는지는 TypeScript만으로 확인할 수 없습니다.

Zod 같은 런타임 스키마를 사용하면 외부 값을 애플리케이션 내부에서 사용할 수 있는 형태로 검사하고 변환할 수 있습니다.

```text
unknown 외부 값
→ Zod 파싱
→ 검증·정규화된 값
→ 업무 처리
```

중요한 점은 **스키마 검증과 업무 규칙 검증은 서로 다른 단계**라는 것입니다. 문자열 길이와 UUID 형식은 스키마가 검사할 수 있지만, 현재 사용자의 권한이나 데이터베이스에 저장된 현재 버전은 스키마만으로 판단할 수 없습니다.

## 목표

- 요청에서 받은 본문·경로·쿼리·헤더·WebSocket 메시지를 실행 중에 검사합니다.
- 문자열 정리와 필요한 타입 변환을 입력 경계에서 처리합니다.
- 스키마가 검사할 수 있는 규칙과 현재 사용자·저장 데이터가 필요한 업무 규칙을 구분합니다.
- `parse()`가 반환하는 값과 원래 입력 값을 구분합니다.
- 응답에 내부 필드가 실수로 섞이지 않도록 공개 DTO를 정의합니다.
- Zod 오류를 클라이언트가 의존할 수 있는 안정적인 API 오류 형식으로 바꿉니다.
- 브라우저와 서버가 공유할 계약과 서버 내부 구현을 구분합니다.

## TypeScript 타입만으로는 외부 값을 검증할 수 없습니다

다음 타입이 있다고 가정합니다.

```ts
type CreateBoardRequest = {
  title: string;
};
```

이 타입은 TypeScript 코드가 컴파일될 때 다음과 같은 실수를 검사하는 데 도움을 줍니다.

```ts
const request: CreateBoardRequest = {
  title: 123
};
```

하지만 실제 HTTP 요청은 TypeScript 타입을 거치지 않고 서버에 도착할 수 있습니다.

```http
POST /boards
Content-Type: application/json

{
  "title": 123
}
```

또는 필요한 필드가 아예 없을 수도 있습니다.

```json
{}
```

다음처럼 타입 단언을 해도 실제 값은 검사되지 않습니다.

```ts
const body = request.body as CreateBoardRequest;
```

`as CreateBoardRequest`는 런타임 검증이 아닙니다. 개발자가 컴파일러에게 "이 값을 해당 타입으로 취급하라"고 알려 줄 뿐입니다.

따라서 외부 경계에서는 먼저 값을 `unknown`이라고 생각하고 실제 검증을 수행해야 합니다.

```ts
const body = CreateBoardSchema.parse(request.body);
```

검증이 성공한 뒤의 `body`를 내부 코드에서 신뢰합니다.

## 입력 스키마

보드 생성 요청을 다음과 같이 정의할 수 있습니다.

```ts
import * as z from "zod";

export const CreateBoardSchema = z.strictObject({
  title: z.string().trim().min(1).max(80)
});
```

이 스키마는 다음을 한 번에 표현합니다.

```text
입력은 객체여야 함
title이 반드시 존재해야 함
title은 문자열이어야 함
앞뒤 공백 제거
제거 후 길이가 최소 1
최대 길이는 80
알 수 없는 필드는 거부
```

예를 들어:

```ts
CreateBoardSchema.parse({
  title: "  Backend Study  "
});
```

결과는 다음과 같습니다.

```ts
{
  title: "Backend Study"
}
```

즉 Zod의 파싱 결과는 단순히 "원래 값이 유효한지"만 나타내는 것이 아니라, 스키마가 정의한 변환을 거친 **새로운 출력 값**일 수 있습니다.

## `z.object()`와 알 수 없는 필드

Zod 4의 일반적인 `z.object()`는 정의되지 않은 객체 키를 기본적으로 파싱 결과에서 제거합니다.

```ts
const Schema = z.object({
  title: z.string()
});

Schema.parse({
  title: "HTTP",
  unexpected: true
});
```

결과:

```ts
{
  title: "HTTP"
}
```

`unexpected` 필드는 결과에서 제거됩니다.

알 수 없는 키 자체를 오류로 만들고 싶다면 `z.strictObject()`를 사용할 수 있습니다.

```ts
const Schema = z.strictObject({
  title: z.string()
});
```

이제 다음 입력은 실패합니다.

```ts
Schema.parse({
  title: "HTTP",
  unexpected: true
});
```

반대로 정의하지 않은 키도 그대로 통과시켜야 한다면 `z.looseObject()` 같은 동작을 선택할 수 있습니다.

따라서 객체 스키마를 만들 때는 다음 정책을 명시적으로 생각해야 합니다.

```text
알 수 없는 필드를 제거할 것인가?
알 수 없는 필드를 거부할 것인가?
알 수 없는 필드를 그대로 허용할 것인가?
```

API 요청에서 알 수 없는 필드를 거부하면 클라이언트 실수를 빨리 발견할 수 있지만, 새로운 필드가 추가된 서버와 오래된 중간 계층이 함께 동작해야 하는 환경에서는 호환성에 영향을 줄 수 있습니다.

어느 정책이 항상 옳은 것은 아니며 API의 버전 호환 전략에 맞춰 정해야 합니다.

> Zod 4에서도 `.strict()`는 호환성을 위해 사용할 수 있지만, 새 코드에서는 `z.strictObject()`처럼 객체 생성 시 엄격성을 명시하면 의도가 더 분명합니다.

## `parse()`와 `safeParse()`

Zod는 대표적으로 두 가지 방식으로 파싱 결과를 받을 수 있습니다.

### `parse()`

성공하면 파싱된 값을 반환하고 실패하면 `ZodError`를 던집니다.

```ts
const body = CreateBoardSchema.parse(request.body);
```

오류를 상위 error handler에서 일괄 처리하는 구조라면 사용할 수 있습니다.

```text
route
→ schema.parse()
→ 실패 시 throw
→ 공통 error handler
```

### `safeParse()`

성공과 실패를 값으로 반환합니다.

```ts
const result = CreateBoardSchema.safeParse(request.body);

if (!result.success) {
  return reply.code(400).send({
    code: "invalid_request",
    details: toValidationDetails(result.error)
  });
}

const body = result.data;
```

성공했을 때는 `result.data`가 파싱된 값입니다.

```text
success = true
→ result.data

success = false
→ result.error
```

둘 중 하나가 항상 더 좋은 것은 아닙니다. 애플리케이션의 오류 처리 구조에 맞춰 선택합니다.

중요한 것은 실패한 외부 값을 타입 단언으로 계속 사용하지 않는 것입니다.

## 스키마의 입력 타입과 출력 타입은 다를 수 있습니다

변환이나 강제 변환을 사용하면 스키마에 들어가는 값의 타입과 파싱 뒤 나오는 값의 타입이 달라질 수 있습니다.

예:

```ts
const LimitSchema = z.coerce.number().int().min(1).max(100);
```

외부에서는 문자열이 들어올 수 있습니다.

```text
"20"
```

파싱 결과는 숫자입니다.

```ts
20
```

따라서 개념적으로 다음 두 타입을 구분해야 합니다.

```text
input
외부에서 스키마에 들어오는 값

output
스키마 파싱이 성공한 뒤 애플리케이션이 사용하는 값
```

Zod 타입 유틸리티를 사용하면 구분해서 얻을 수 있습니다.

```ts
type LimitInput = z.input<typeof LimitSchema>;
type LimitOutput = z.output<typeof LimitSchema>;
```

일반적인 스키마는 입력과 출력 타입이 같지만, `coerce`, `transform`, 정규화를 사용하면 달라질 수 있습니다.

이 차이를 이해하면 "HTTP에서는 문자열이었는데 왜 서비스에서는 숫자인가?"를 명확히 설명할 수 있습니다.

## 경로 매개변수도 검사합니다

라우터가 경로 값을 제공한다고 해서 올바른 식별자라는 뜻은 아닙니다.

```text
GET /boards/not-a-uuid
```

다음처럼 검사할 수 있습니다.

```ts
const BoardParamsSchema = z.strictObject({
  id: z.uuid()
});
```

사용할 때:

```ts
const params = BoardParamsSchema.parse(request.params);

await boardService.getBoard(params.id);
```

서비스 계층은 이미 형식 검증이 끝난 ID를 받을 수 있습니다.

경로에 들어 있다는 이유만으로 다음 값을 신뢰해서는 안 됩니다.

```text
UUID
정수 ID
slug
날짜
enum 값
```

모두 외부 입력입니다.

## 쿼리도 검사합니다

쿼리 문자열은 HTTP 수준에서는 일반적으로 문자열 형태로 들어오는 경우가 많습니다.

예:

```text
GET /boards?limit=20&cursor=abc
```

스키마를 다음과 같이 정의할 수 있습니다.

```ts
const BoardQuerySchema = z.strictObject({
  limit: z.coerce
    .number()
    .int()
    .min(1)
    .max(100)
    .default(20),

  cursor: z.string().min(1).optional()
});
```

파싱 후에는:

```ts
const query = BoardQuerySchema.parse(request.query);

query.limit;
```

`query.limit`을 숫자로 사용할 수 있습니다.

그러나 강제 변환은 입력을 넓게 받아들이기 때문에 어떤 값이 무엇으로 변하는지 알고 사용해야 합니다.

## `z.coerce`는 JavaScript 변환 규칙을 사용합니다

예를 들어 `z.coerce.number()`는 입력을 숫자로 바꾸려고 시도합니다.

개념적으로 다음 JavaScript 변환과 비슷한 성질을 가집니다.

```ts
Number(input)
```

따라서 예상하지 못한 입력도 숫자로 변할 수 있습니다.

```ts
Number("");
// 0
```

즉 쿼리에서 빈 문자열을 유효한 `0`으로 받아들이는 것이 원하는 API 의미인지 확인해야 합니다.

다음처럼 범위 검사가 있으면 일부 문제는 뒤 단계에서 걸러집니다.

```ts
z.coerce.number().int().min(1)
```

하지만 "빈 문자열을 숫자로 변환하지 않는다"는 정책 자체가 필요하다면 변환 전에 입력 형태를 더 제한해야 합니다.

## `z.coerce.boolean()`의 함정

불리언 강제 변환은 특히 주의해야 합니다.

JavaScript의 `Boolean()`은 빈 문자열이 아닌 문자열을 대부분 `true`로 변환합니다.

```ts
Boolean("true");
// true

Boolean("false");
// true
```

따라서 다음 스키마는 HTTP 쿼리의 `"false"` 문자열을 사용자가 기대하는 `false`로 바꾸지 않습니다.

```ts
z.coerce.boolean()
```

예를 들어 다음 요청이 있다고 가정합니다.

```text
GET /boards?archived=false
```

쿼리 파서가 `"false"`를 문자열로 전달한다면 단순한 `z.coerce.boolean()`은 올바른 API 의미가 아닐 수 있습니다.

이런 경우 허용할 문자열을 명시적으로 정의하는 편이 안전합니다.

```ts
const BooleanQuerySchema = z
  .enum(["true", "false"])
  .transform((value) => value === "true");
```

이제:

```text
"true"  → true
"false" → false
그 외   → 검증 실패
```

강제 변환은 편리하지만 "변환 가능하다"와 "API 의미상 허용해야 한다"는 서로 다른 문제입니다.

## 헤더도 외부 입력입니다

인증, 버전 조건, 콘텐츠 협상 등에 사용하는 헤더도 검증 대상입니다.

예를 들어 조건부 요청에 사용하는 값이 있다고 가정합니다.

```http
If-Match: "12"
```

애플리케이션에서 특정 형식을 기대한다면 읽은 뒤 형식을 검사해야 합니다.

```ts
const IfMatchSchema = z.string().min(1);
```

헤더 이름의 대소문자 처리나 배열 가능성 등은 사용하는 HTTP 프레임워크가 어떤 형태로 값을 제공하는지 먼저 확인해야 합니다.

즉 Zod 스키마는 **프레임워크가 제공한 런타임 값의 실제 형태**를 기준으로 작성해야 합니다.

## 정규화

검증 단계에서 외부 표현을 내부에서 비교하거나 저장하기 좋은 형태로 정규화할 수 있습니다.

예:

```ts
const EmailSchema = z
  .string()
  .trim()
  .toLowerCase()
  .pipe(z.email());
```

입력:

```text
"  USER@example.com  "
```

출력:

```text
"user@example.com"
```

정규화는 여러 코드 경로에서 같은 규칙을 반복하지 않게 해 줍니다.

```text
HTTP 생성 요청
HTTP 수정 요청
WebSocket 메시지
배치 입력
```

이들이 같은 의미의 값을 받는다면 가능한 한 같은 스키마 또는 같은 정규화 규칙을 재사용합니다.

## 정규화와 원본 보존은 별개의 결정입니다

항상 정규화된 값만 저장해야 하는 것은 아닙니다.

예를 들어 사용자가 입력한 표시 이름이 있다고 가정합니다.

```text
"  My Board  "
```

비교에는 정규화된 값을 쓰고 UI에는 원래 입력 형태를 유지해야 할 수 있습니다.

또는 이메일 주소처럼 시스템 정책에 따라 정규화 규칙을 매우 신중히 적용해야 하는 식별자도 있습니다.

다음 두 목적을 구분합니다.

```text
canonical value
비교·중복 검사·검색에 사용할 형태

display value
사용자에게 다시 보여 줄 원래 표현
```

필요하다면 둘을 별도로 저장합니다.

유니코드 정규화, 대소문자 변환, 공백 처리 규칙은 식별자의 실제 의미에 맞춰 정해야 합니다. 무조건 `.toLowerCase()`나 `.trim()`을 붙이는 것이 정답은 아닙니다.

## 스키마만으로 확인할 수 있는 규칙

Zod 스키마는 주어진 값 자체를 보고 판단할 수 있는 규칙에 적합합니다.

예:

- 필드 존재 여부
- 문자열·숫자·불리언 같은 타입
- 문자열 길이
- 숫자 범위
- UUID·이메일 등의 형식
- 배열 길이
- 열거형 값
- 메시지 종류에 따른 필드 구조
- 여러 필드 사이의 로컬한 관계

예를 들어 시작 날짜와 종료 날짜가 같은 객체 안에 있다면 두 값의 관계도 스키마에서 검사할 수 있습니다.

```ts
const RangeSchema = z
  .object({
    start: z.number(),
    end: z.number()
  })
  .refine(
    (value) => value.start <= value.end,
    {
      message: "start must not be greater than end",
      path: ["end"]
    }
  );
```

두 값만으로 판단할 수 있기 때문입니다.

## 스키마만으로 확인할 수 없는 규칙

다음 규칙은 외부 입력만 보고 결정할 수 없습니다.

- 현재 사용자가 해당 보드의 구성원인가
- 현재 사용자가 수정 권한을 가지고 있는가
- 같은 범위에서 제목이 이미 존재하는가
- `baseVersion`이 데이터베이스의 현재 버전과 같은가
- 계정이 정지되었는가
- 주문이 현재 취소 가능한 상태인가

예를 들어 다음 값은 형식 자체는 완전히 올바를 수 있습니다.

```json
{
  "boardId": "4f5b4f23-65ec-4d42-8ca8-d9e67c4be111"
}
```

하지만 현재 사용자가 해당 board에 접근할 수 있는지는 데이터베이스 상태와 인증 정보를 봐야 합니다.

따라서 처리 흐름을 다음처럼 구분합니다.

```text
외부 입력
→ Zod 형식 검증·정규화
→ 인증된 사용자 확인
→ 업무 규칙 확인
→ 데이터베이스 조회·변경
```

스키마 검사를 통과했다는 것은 **입력 형태가 기대한 계약에 맞는다**는 뜻이지 **작업이 허용되었다**는 뜻이 아닙니다.

## 비동기 검사를 무조건 스키마에 넣지 않습니다

Zod에는 비동기 refinement를 사용할 수 있지만, 데이터베이스 조회가 필요한 모든 업무 규칙을 스키마 안에 넣는 것은 책임을 흐릴 수 있습니다.

예를 들어 다음 규칙을 생각합니다.

```text
"이 board 이름이 현재 workspace에서 중복인가?"
```

이 규칙은 데이터베이스와 현재 workspace라는 업무 문맥이 필요합니다.

이런 규칙을 서비스 계층에 두면 다음 경계가 분명해집니다.

```text
schema
입력의 형식과 값 자체의 조건

service/domain
현재 사용자·DB 상태·업무 규칙
```

스키마는 가능하면 전송 계약을 표현하는 역할에 집중시킵니다.

## 요청 스키마에서 타입을 추론합니다

스키마와 TypeScript 타입을 따로 작성하면 둘이 서로 달라질 수 있습니다.

```ts
const CreateBoardSchema = z.strictObject({
  title: z.string().trim().min(1).max(80)
});

type CreateBoard = z.output<typeof CreateBoardSchema>;
```

이렇게 하면 검증 규칙에서 실제 파싱 결과 타입을 얻을 수 있습니다.

서비스가 정규화된 값을 받는다면 `z.output` 기준 타입을 사용하는 것이 의미가 명확합니다.

```ts
async function createBoard(input: CreateBoard) {
  // input.title은 검증·trim이 끝난 문자열
}
```

외부 원본 타입과 출력 타입이 같다면 `z.infer<typeof Schema>`를 사용해도 됩니다. 변환이 있는 코드에서는 입력과 출력의 차이를 의식하는 것이 중요합니다.

## 응답도 외부 계약입니다

요청만 검증하고 응답은 데이터베이스 객체를 그대로 반환하면 내부 필드가 API에 노출될 수 있습니다.

다음 데이터베이스 행이 있다고 가정합니다.

```ts
type BoardRow = {
  id: string;
  title: string;
  ownerId: string;
  internalFlags: number;
  deletedAt: Date | null;
  version: number;
};
```

다음처럼 그대로 반환하면:

```ts
return boardRow;
```

원래 공개할 생각이 없었던 필드까지 JSON에 포함될 수 있습니다.

따라서 응답에서 공개할 필드를 별도의 계약으로 정의합니다.

```ts
const BoardResponseSchema = z.strictObject({
  id: z.uuid(),
  title: z.string(),
  role: z.enum(["owner", "editor", "viewer"]),
  version: z.number().int().nonnegative()
});
```

그러나 스키마만 만든 것으로 충분하지 않습니다. 실제 응답 객체도 의도적으로 구성해야 합니다.

```ts
function toBoardResponse(
  row: BoardRow,
  role: "owner" | "editor" | "viewer"
) {
  return BoardResponseSchema.parse({
    id: row.id,
    title: row.title,
    role,
    version: row.version
  });
}
```

이제 공개 필드를 코드에서 명시적으로 확인할 수 있습니다.

## 데이터베이스 행을 그대로 응답하지 않습니다

특히 다음 값은 실수로 노출되면 안 됩니다.

- 비밀번호 해시
- 세션 토큰 또는 토큰 다이제스트
- 비밀 키
- 내부 권한 플래그
- 관리자용 메모
- 삭제·감사용 내부 상태
- 사용자에게 공개할 필요가 없는 외래 키
- 내부 서비스 식별자

응답 DTO(Data Transfer Object)는 단순한 타입 복사가 아니라 **외부에 무엇을 공개할지 결정하는 경계**입니다.

```text
database model
내부 저장 구조

domain model
업무 처리 구조

response DTO
외부 공개 구조
```

이 세 구조가 우연히 같을 수는 있지만 같은 개념은 아닙니다.

## 응답 스키마와 알 수 없는 필드 제거에만 의존하지 않습니다

`z.object()`가 알 수 없는 키를 제거한다는 성질을 이용하면 데이터베이스 객체를 파싱해서 공개 필드만 남길 수도 있습니다.

```ts
const PublicBoardSchema = z.object({
  id: z.uuid(),
  title: z.string()
});

const response = PublicBoardSchema.parse(boardRow);
```

파싱 결과에는 선언된 필드만 남습니다.

하지만 보안상 중요한 응답에서는 "우연히 제거되겠지"에만 의존하지 않고 공개 DTO를 명시적으로 만드는 편이 의도를 읽기 쉽습니다.

```ts
const response = {
  id: row.id,
  title: row.title
};
```

그리고 필요하면 응답 스키마로 다시 검증합니다.

```ts
return PublicBoardSchema.parse(response);
```

이렇게 하면 공개 필드의 선택과 형식 검증이 분리되어 명확합니다.

## 오류 내용 변환

Zod 검증 실패를 그대로 외부 API 계약으로 사용하지 않는 편이 좋습니다.

```ts
const result = CreateBoardSchema.safeParse(input);

if (!result.success) {
  console.log(result.error.issues);
}
```

`issues`에는 Zod가 사용하는 오류 코드, 경로, 메시지와 오류 종류별 추가 정보가 들어 있습니다.

예를 들어 외부 API에는 필요한 부분만 안정적인 형식으로 변환할 수 있습니다.

```ts
function toValidationDetails(error: z.ZodError) {
  return error.issues.map((issue) => ({
    path: issue.path.join("."),
    reason: issue.code
  }));
}
```

응답:

```json
{
  "code": "invalid_request",
  "message": "요청 형식이 올바르지 않습니다.",
  "details": [
    {
      "path": "title",
      "reason": "too_small"
    }
  ]
}
```

클라이언트는 Zod가 생성한 영어 오류 문장에 직접 의존하지 않습니다.

## 라이브러리 오류 코드와 API 오류 코드를 구분합니다

`issue.code`를 그대로 API에 내보낼 수도 있지만, 그러면 외부 계약이 Zod의 오류 코드 체계와 결합됩니다.

예를 들어 서버가 다음 라이브러리로 교체되는 경우를 생각합니다.

```text
Zod
→ 다른 validation library
```

클라이언트가 Zod의 세부 코드에 강하게 의존하면 서버 내부 구현을 교체하기 어렵습니다.

따라서 장기간 유지할 공개 API라면 애플리케이션 수준의 오류 이유를 별도로 정의할 수도 있습니다.

예:

```ts
type ValidationReason =
  | "required"
  | "invalid_type"
  | "invalid_format"
  | "too_short"
  | "too_long"
  | "out_of_range";
```

Zod issue를 이 코드로 매핑합니다.

```text
Zod issue
→ API validation reason
→ client
```

내부 라이브러리 오류 형식과 외부 API 계약을 얼마나 분리할지는 프로젝트의 규모와 호환성 요구에 맞춰 결정합니다.

## 오류 메시지에 입력 값을 포함할 때 주의합니다

검증 오류를 로깅하거나 응답으로 보낼 때 실제 입력 값을 그대로 포함하면 민감한 값이 노출될 수 있습니다.

예:

```text
Authorization 헤더
비밀번호
토큰
개인정보
비밀 키
```

오류 정보에는 일반적으로 다음만 있어도 충분합니다.

```text
필드 경로
안정적인 오류 이유 코드
필요한 최소 설명
requestId
```

문제 분석에 원본 입력이 필요하더라도 로그의 민감 정보 정책과 마스킹 규칙을 먼저 적용합니다.

## 중첩 필드 경로

Zod issue의 `path`는 배열입니다.

예를 들어 다음 입력을 검증한다고 가정합니다.

```json
{
  "items": [
    {
      "title": ""
    }
  ]
}
```

오류 경로가 다음과 같을 수 있습니다.

```ts
["items", 0, "title"]
```

단순히 점으로 연결하면:

```text
items.0.title
```

처럼 표현할 수 있습니다.

클라이언트가 이 경로를 폼 필드와 연결한다면 배열 인덱스와 특수 키를 어떤 문자열 표현으로 직렬화할지 API 전체에서 일관되게 정해야 합니다.

## HTTP와 WebSocket 계약 공유

HTTP와 WebSocket이 같은 개념을 전송한다면 스키마 일부를 공유할 수 있습니다.

예를 들어 role이 두 프로토콜에서 모두 사용된다면:

```ts
export const BoardRoleSchema = z.enum([
  "owner",
  "editor",
  "viewer"
]);

export type BoardRole = z.output<typeof BoardRoleSchema>;
```

HTTP 응답:

```ts
const BoardResponseSchema = z.object({
  role: BoardRoleSchema
});
```

WebSocket 메시지:

```ts
const MemberChangedSchema = z.object({
  type: z.literal("member.changed"),
  role: BoardRoleSchema
});
```

같은 의미를 서로 다른 위치에서 중복 정의하지 않으면 값 목록이 어긋날 가능성이 줄어듭니다.

## 공유 패키지는 전송 계약에 집중합니다

브라우저와 서버가 함께 사용하는 패키지에는 다음처럼 네트워크 경계를 넘는 계약을 둘 수 있습니다.

- 요청·응답 DTO 스키마
- WebSocket 메시지 스키마
- 역할 enum
- 공개 식별자 형식
- 페이지네이션 cursor 구조
- 공개 오류 코드 타입

반면 다음 값은 공유하지 않습니다.

- 데이터베이스 클라이언트 타입
- ORM 내부 모델
- 서버 비밀 설정
- 서버 전용 환경 변수 스키마
- 서버 전용 오류 클래스
- 저장소 구현
- 내부 서비스 구현
- React 컴포넌트의 로컬 상태
- 서버에서만 의미가 있는 권한 계산 상태

공유 패키지는 "서버 구현 전체"가 아니라 **클라이언트와 서버 사이에서 실제로 전송되는 값**을 표현하는 데 집중합니다.

## 공유 스키마가 서버 내부 모델이 되어서는 안 됩니다

공유 패키지의 타입을 서버의 모든 내부 함수에 그대로 사용하면 외부 API 계약과 내부 업무 모델이 강하게 결합될 수 있습니다.

예를 들어 HTTP 요청에는 다음 필드만 있을 수 있습니다.

```ts
{
  title: string;
}
```

하지만 업무 처리에서는 다음 정보도 필요할 수 있습니다.

```ts
{
  actorId: string;
  workspaceId: string;
  normalizedTitle: string;
  requestedAt: Date;
}
```

이 값들은 서버가 인증·정규화·현재 문맥을 통해 만든 내부 값입니다.

따라서 다음 경계를 유지합니다.

```text
transport schema
외부에서 주고받는 형태

application/domain input
서버 내부 업무 처리에 필요한 형태
```

둘이 비슷하더라도 항상 같은 타입일 필요는 없습니다.

## WebSocket 메시지도 매번 검증합니다

WebSocket 연결이 한 번 인증되었다고 해서 이후 들어오는 메시지의 구조까지 신뢰할 수 있는 것은 아닙니다.

클라이언트 메시지를 다음과 같이 정의할 수 있습니다.

```ts
const ClientMessageSchema = z.discriminatedUnion("type", [
  z.strictObject({
    type: z.literal("board.join"),
    boardId: z.uuid()
  }),

  z.strictObject({
    type: z.literal("item.move"),
    boardId: z.uuid(),
    itemId: z.uuid(),
    baseVersion: z.number().int().nonnegative(),
    x: z.number().finite(),
    y: z.number().finite(),
    final: z.boolean()
  })
]);
```

`type`이 discriminator입니다.

```text
type = "board.join"
→ board.join 스키마로 검사

type = "item.move"
→ item.move 스키마로 검사
```

각 메시지 종류에 필요한 필드를 명확하게 정의할 수 있고, TypeScript도 `type`을 확인한 뒤 해당 메시지 타입으로 좁힐 수 있습니다.

```ts
const message = ClientMessageSchema.parse(value);

if (message.type === "item.move") {
  message.itemId;
  message.x;
  message.y;
}
```

## JSON 파싱과 스키마 검증은 다른 단계입니다

WebSocket에서 문자열 메시지를 받았다고 가정합니다.

먼저 JSON 문법 자체를 파싱해야 합니다.

```ts
const raw = socketMessage.toString();

let value: unknown;

try {
  value = JSON.parse(raw);
} catch {
  // 잘못된 JSON 처리
}
```

그 다음 Zod로 구조를 검사합니다.

```ts
const result = ClientMessageSchema.safeParse(value);
```

즉 두 실패를 구분할 수 있습니다.

```text
JSON parse failure
문법적으로 JSON이 아님

schema validation failure
JSON이지만 기대한 메시지 구조가 아님
```

잘못된 메시지 하나 때문에 예외가 이벤트 루프 밖으로 전파되어 서버 프로세스 전체가 종료되지 않도록 연결 경계에서 오류를 처리해야 합니다.

## 메시지 스키마 통과와 권한 승인은 다릅니다

다음 메시지가 스키마를 통과했다고 가정합니다.

```json
{
  "type": "item.move",
  "boardId": "4f5b4f23-65ec-4d42-8ca8-d9e67c4be111",
  "itemId": "00a74264-7df4-49bb-a456-e82088970123",
  "baseVersion": 12,
  "x": 100,
  "y": 200,
  "final": true
}
```

여전히 다음 검사가 필요합니다.

```text
현재 socket 사용자가 board 멤버인가?
itemId가 실제로 board에 속하는가?
사용자가 item을 이동할 권한이 있는가?
baseVersion이 현재 버전과 같은가?
좌표 변경이 현재 업무 상태에서 허용되는가?
```

따라서 WebSocket도 HTTP와 같은 원칙을 적용합니다.

```text
메시지 parse
→ schema validation
→ actor/permission 확인
→ 업무 규칙 처리
```

## 버전 호환

클라이언트와 서버가 항상 동시에 배포되는 것은 아닙니다.

예를 들어:

```text
서버 v2 배포
모바일 앱 일부 사용자는 아직 v1
브라우저 탭 일부는 오래 열린 상태
WebSocket 연결은 배포 전부터 유지 중
```

따라서 스키마 변경이 이전 클라이언트에 어떤 영향을 주는지 생각해야 합니다.

## 필드 추가

기존 객체에 선택 필드를 추가하면 일반적으로 이전 클라이언트가 그 필드를 무시할 수 있다면 호환하기 쉽습니다.

```ts
const SchemaV1 = z.object({
  id: z.uuid(),
  title: z.string()
});

const SchemaV2 = z.object({
  id: z.uuid(),
  title: z.string(),
  color: z.string().optional()
});
```

하지만 클라이언트가 응답 객체를 엄격하게 검증하여 알 수 없는 필드를 거부한다면 서버가 새 필드를 추가하는 것만으로도 이전 클라이언트가 실패할 수 있습니다.

즉 요청과 응답에서 strict 정책을 선택할 때 버전 호환까지 함께 고려해야 합니다.

## 필수 필드 추가

기존 요청에 새 필수 필드를 추가하면 오래된 클라이언트는 그 필드를 보내지 못하므로 일반적으로 호환되지 않습니다.

```text
v1 request
{ title }

v2 server requires
{ title, color }
```

이런 변경은 기본값, 선택 필드, 새 버전 endpoint 등 별도의 호환 전략이 필요합니다.

## enum 값 추가

서버가 새로운 enum 값을 응답하기 시작하면 이전 클라이언트가 그 값을 모를 수 있습니다.

기존 타입:

```ts
z.enum(["owner", "editor", "viewer"])
```

새 값:

```text
"commenter"
```

서버에서는 단순한 값 추가처럼 보여도 이전 클라이언트가 exhaustive switch나 strict schema를 사용한다면 오류가 될 수 있습니다.

따라서 enum 값 추가는 항상 무해한 변경이라고 가정하지 않습니다.

다음 정책 중 무엇을 사용할지 결정해야 합니다.

```text
모르는 값을 오류로 처리
unknown fallback으로 처리
프로토콜 버전을 올림
서버가 구버전 클라이언트에는 새 값을 보내지 않음
```

## 필드 제거와 의미 변경

기존 필드를 제거하거나 같은 필드의 의미를 바꾸는 변경은 특히 위험합니다.

예:

```text
version = 문서 버전
```

이었던 필드를:

```text
version = API 버전
```

으로 의미만 바꾸면 타입은 같은 숫자여도 기존 클라이언트가 잘못 동작할 수 있습니다.

계약의 호환성은 단순히 JSON 모양뿐 아니라 **필드의 의미**까지 포함합니다.

## 스키마 변경도 API 변경입니다

공유 Zod 스키마를 수정하면 TypeScript 컴파일 오류만 바뀌는 것이 아닙니다.

실행 중 허용되는 입력과 생성되는 출력이 달라질 수 있습니다.

예:

```text
min(1) → min(3)
optional() → required
z.object() → z.strictObject()
enum 값 삭제
transform 규칙 변경
default 값 변경
```

따라서 공개 계약에 사용되는 스키마 변경은 API 변경으로 검토해야 합니다.

특히 기본값과 변환은 파싱 결과 자체를 바꾸므로 단순한 검증 규칙보다 더 큰 영향을 줄 수 있습니다.

## 검증 경계의 전체 흐름

HTTP 요청 하나를 예로 들면 다음과 같습니다.

```text
HTTP request
    ↓
raw params/query/headers/body
    ↓
Zod parse
    ↓
정규화된 transport DTO
    ↓
인증된 actor와 결합
    ↓
service/domain
    ↓
database
    ↓
공개 response DTO 생성
    ↓
response schema 검증
    ↓
HTTP response
```

WebSocket도 구조는 비슷합니다.

```text
WebSocket frame
    ↓
JSON.parse
    ↓
Zod message parse
    ↓
인증된 socket actor 확인
    ↓
업무 규칙 처리
    ↓
공개 event DTO
    ↓
outgoing message
```

이 경계를 명확히 하면 "어느 시점부터 값을 신뢰할 수 있는가?"를 코드에서 찾기 쉬워집니다.

## 흔한 실수

- HTTP 본문만 검사하고 경로·쿼리·헤더는 문자열이라고 신뢰합니다.
- `as SomeRequest` 타입 단언을 런타임 검증으로 착각합니다.
- 원래 입력과 Zod 파싱 결과가 항상 같다고 생각합니다.
- `z.object()`가 알 수 없는 키를 기본적으로 제거한다는 동작을 모르고 사용합니다.
- 엄격한 객체가 필요한데 unknown key 정책을 명시하지 않습니다.
- `z.coerce.number()`가 빈 문자열 같은 값도 변환할 수 있다는 점을 고려하지 않습니다.
- `z.coerce.boolean()`이 문자열 `"false"`를 `true`로 만들 수 있다는 점을 놓칩니다.
- 스키마 통과를 권한 승인 또는 업무 규칙 통과로 간주합니다.
- 데이터베이스 조회가 필요한 모든 규칙을 스키마 refinement에 넣어 계층 책임을 섞습니다.
- 데이터베이스 행이나 ORM 모델을 그대로 응답합니다.
- 응답 스키마를 정의했지만 실제 응답에서 사용하지 않습니다.
- Zod의 기본 오류 메시지나 내부 issue 구조에 클라이언트가 직접 강하게 의존합니다.
- 검증 오류 로그에 비밀번호, 토큰 같은 입력 값을 그대로 기록합니다.
- WebSocket 연결이 인증되었다는 이유로 이후 메시지 구조를 검사하지 않습니다.
- `JSON.parse()` 실패와 Zod 검증 실패를 구분하지 않습니다.
- 알 수 없는 enum 값이 이전 클라이언트에서 어떻게 처리되는지 정하지 않습니다.
- 공유 패키지에 데이터베이스 타입과 서버 내부 구현까지 넣습니다.
- 공개 스키마의 변경을 단순한 내부 리팩터링이라고 생각합니다.

## 완료 기준

다음 질문에 답할 수 있으면 이 문서의 핵심을 이해한 것입니다.

- TypeScript 타입만으로 외부 HTTP 값을 검증할 수 없는 이유를 설명할 수 있는가?
- 본문·경로·쿼리·헤더·WebSocket 메시지를 모두 외부 입력으로 취급하는가?
- `parse()`와 `safeParse()`의 차이를 설명할 수 있는가?
- 스키마의 입력 타입과 파싱 결과 타입이 달라질 수 있는 이유를 설명할 수 있는가?
- `z.object()`, `z.strictObject()`의 unknown key 정책 차이를 설명할 수 있는가?
- 강제 변환 전에 어떤 입력이 어떤 값으로 바뀌는지 확인하는가?
- 문자열 `"false"`에 단순한 boolean coercion을 적용하면 어떤 문제가 생길 수 있는지 설명할 수 있는가?
- 정규화와 사용자의 원래 표시 값을 보존하는 문제를 구분할 수 있는가?
- 스키마에서 검사할 규칙과 현재 사용자·DB 상태가 필요한 업무 규칙을 구분할 수 있는가?
- 서비스가 검증·정규화된 값을 받도록 경계를 만들었는가?
- 응답 DTO에 외부에 공개할 필드만 명시적으로 포함하는가?
- Zod 오류를 클라이언트용 안정적인 오류 코드와 경로로 변환하는가?
- WebSocket에서 JSON 문법 오류와 메시지 스키마 오류를 각각 처리하는가?
- 브라우저와 공유할 패키지가 전송 계약에 집중하고 있는가?
- 선택 필드 추가, 필수 필드 추가, enum 값 추가가 기존 클라이언트에 어떤 영향을 주는지 설명할 수 있는가?

## 연결 exercise

[`notes-api`](../../exercises/notes-api/README.md)에서 생성 요청과 오류 응답을 검증합니다. [`realtime-board`](../../exercises/realtime-board/README.md)에서는 메시지 종류별 스키마를 사용합니다.
