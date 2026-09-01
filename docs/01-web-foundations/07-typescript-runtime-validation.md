# TypeScript와 런타임 검증

TypeScript의 타입 정보는 개발과 빌드 과정에서 코드를 검사하기 위한 정보입니다. JavaScript로 실행될 때는 대부분의 타입 정보가 사라지므로, 런타임에 들어오는 값이 실제로 타입 선언과 일치하는지는 TypeScript만으로 보장할 수 없습니다.

예를 들어 다음 코드는 TypeScript 관점에서는 `Board`를 반환하는 것처럼 보일 수 있습니다.

```ts
type Board = {
  id: string;
  title: string;
};

async function loadBoard(): Promise<Board> {
  const response = await fetch("/api/board");
  return response.json();
}
```

하지만 서버가 실제로 다음 값을 반환할 수도 있습니다.

```json
{
  "id": 42,
  "title": null
}
```

TypeScript 타입 선언은 네트워크 응답을 실행 중에 검사하지 않습니다.

따라서 HTTP 본문, 환경 변수, URL, WebSocket 메시지, 브라우저 저장 값, 데이터베이스 드라이버 결과처럼 **프로그램 바깥에서 들어오는 값은 신뢰 경계에서 런타임 검증이 필요합니다.**

핵심 흐름은 다음과 같습니다.

```text
외부 값
  ↓
unknown으로 받음
  ↓
런타임 검증과 정규화
  ↓
애플리케이션 내부의 신뢰 가능한 타입
```

## 목표

- 타입 추론에 맡길 부분과 명시적으로 타입을 적을 부분을 구분합니다.
- 리터럴 유니온으로 허용 가능한 값을 제한합니다.
- 판별 가능한 유니온으로 모순된 상태를 만들기 어렵게 합니다.
- `never`를 사용해 빠짐없는 분기를 확인합니다.
- `unknown`, `any`, 타입 단언의 차이를 설명합니다.
- 타입 가드와 파서 함수로 외부 값을 검사합니다.
- Zod 같은 런타임 스키마가 무엇을 보장하고 무엇을 보장하지 않는지 구분합니다.
- HTTP DTO, 서비스에서 사용하는 값, 데이터베이스 행을 서로 다른 경계의 타입으로 구분합니다.
- 환경 변수를 프로세스 시작 시 한 번 검증하고 정규화합니다.

## TypeScript 타입은 언제 존재하는가

다음 TypeScript 코드를 생각해 봅니다.

```ts
function double(value: number): number {
  return value * 2;
}
```

TypeScript 컴파일러는 개발 중에 다음과 같은 잘못된 호출을 찾을 수 있습니다.

```ts
double("3");
// 타입 오류
```

하지만 타입 정보는 JavaScript로 변환될 때 대부분 제거됩니다.

개념적으로 실행되는 코드는 다음과 비슷합니다.

```js
function double(value) {
  return value * 2;
}
```

즉 런타임에는 다음 정보가 자동으로 존재하지 않습니다.

```text
value는 number여야 한다.
반환값도 number여야 한다.
```

따라서 외부 입력이 `number`인지 확인해야 하는 위치에서는 실제 JavaScript 검사가 필요합니다.

```ts
function parseNumber(value: unknown): number {
  if (typeof value !== "number") {
    throw new Error("숫자가 필요합니다.");
  }

  return value;
}
```

TypeScript는 **코드가 타입 규칙을 따르는지 정적으로 검사**하고, 런타임 검증은 **실제 값이 규칙을 만족하는지 실행 중에 검사**합니다.

```text
TypeScript 타입 검사
→ 개발·빌드 시점

런타임 검증
→ 프로그램 실행 시점
```

둘은 서로 대체하지 않습니다.

## 타입 추론과 명시적 타입

TypeScript는 많은 경우 타입을 자동으로 추론할 수 있습니다.

```ts
const retryCount = 0;
```

이 변수의 타입을 다음처럼 반복해서 적을 필요는 없습니다.

```ts
const retryCount: number = 0;
```

둘 다 가능하지만 지역 변수에서는 추론만으로 충분한 경우가 많습니다.

```ts
const title = "학습 보드";
const completed = false;
const tags = ["web", "typescript"];
```

TypeScript는 초기값을 이용해 대략 다음 타입을 추론합니다.

```text
title     → string
completed → boolean
tags      → string[]
```

### 공개 경계에서는 타입을 명시하는 것이 유용합니다

다른 파일이나 모듈에서 호출하는 함수는 입력과 반환 타입을 명시하면 API를 이해하기 쉽습니다.

```ts
export function normalizeTitle(
  input: string
): string {
  return input.trim();
}
```

함수 선언만 보고 다음을 알 수 있습니다.

```text
입력  → string
출력  → string
```

반대로 내부의 짧은 지역 변수까지 모든 타입을 반복해서 적으면 코드가 장황해질 수 있습니다.

일반적인 기준은 다음처럼 생각할 수 있습니다.

```text
지역 구현 세부사항
→ 타입 추론 활용

모듈의 공개 함수
→ 입력·반환 타입을 명확하게 표현

외부 입력 경계
→ unknown으로 받고 런타임 검사
```

이것은 절대적인 규칙은 아니지만 타입을 어디에 명시할지 판단하기 좋은 출발점입니다.

## 리터럴 유니온으로 허용 값을 제한합니다

값이 아무 문자열이나 될 수 있는 것이 아니라 정해진 몇 가지 값 중 하나라면 리터럴 유니온을 사용할 수 있습니다.

```ts
type Role =
  | "owner"
  | "editor"
  | "viewer";
```

이제 다음 값은 허용됩니다.

```ts
const role: Role = "editor";
```

하지만 정의되지 않은 문자열은 타입 오류입니다.

```ts
const role: Role = "admin";
// 타입 오류
```

단순히 `string`으로 선언하면 다음과 같은 잘못된 값도 타입 수준에서는 허용됩니다.

```ts
let role: string = "whatever";
```

허용 가능한 값이 정해져 있다면 가능한 범위를 타입에 표현하는 것이 좋습니다.

## 리터럴 타입은 런타임 검증을 대신하지 않습니다

다음 타입이 있다고 해도:

```ts
type Role =
  | "owner"
  | "editor"
  | "viewer";
```

외부 JSON이 자동으로 이 타입에 맞는 것은 아닙니다.

```json
{
  "role": "admin"
}
```

다음처럼 타입 단언을 하면 컴파일러는 믿지만 실제 값은 그대로입니다.

```ts
const role =
  value.role as Role;
```

따라서 외부 입력은 실제로 확인해야 합니다.

```ts
function isRole(
  value: unknown
): value is Role {
  return (
    value === "owner" ||
    value === "editor" ||
    value === "viewer"
  );
}
```

## 판별 가능한 유니온

상태마다 필요한 값이 다르면 여러 선택적 필드를 가진 하나의 객체보다 **판별 가능한 유니온(discriminated union)** 이 더 안전할 수 있습니다.

예를 들어 다음 상태를 생각해 봅니다.

```ts
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: T }
  | {
      status: "error";
      message: string;
    };
```

`status`가 각 상태를 구분하는 판별자입니다.

이 타입에서는 다음이 가능합니다.

```ts
const state: LoadState<string[]> = {
  status: "ready",
  data: ["A", "B"],
};
```

하지만 다음과 같은 모순된 상태는 만들기 어렵습니다.

```ts
const state: LoadState<string[]> = {
  status: "loading",
  data: ["A"],
};
// 타입 오류
```

`loading` 상태에는 `data`가 정의되어 있지 않기 때문입니다.

## 여러 불리언보다 상태 하나가 안전합니다

다음처럼 상태를 여러 불리언으로 나누면:

```ts
type State = {
  loading: boolean;
  error: boolean;
  ready: boolean;
};
```

이런 모순된 상태가 가능합니다.

```ts
const state = {
  loading: true,
  error: true,
  ready: true,
};
```

반면 판별 가능한 유니온에서는 한 번에 하나의 상태만 표현합니다.

```text
idle
loading
ready
error
```

각 상태에서 필요한 데이터도 함께 묶을 수 있습니다.

```ts
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: T }
  | {
      status: "error";
      message: string;
    };
```

## 상태에 따라 타입이 좁혀집니다

판별자를 검사하면 TypeScript가 해당 분기에서 타입을 좁힙니다.

```ts
function render<T>(
  state: LoadState<T>
) {
  if (state.status === "ready") {
    console.log(state.data);
  }
}
```

`status === "ready"` 분기 안에서는 TypeScript가 `state`를 다음 타입으로 이해합니다.

```ts
{
  status: "ready";
  data: T;
}
```

따라서 `data`에 안전하게 접근할 수 있습니다.

반대로 `loading` 상태에서는 `data`가 없습니다.

```ts
if (state.status === "loading") {
  console.log(state.data);
  // 타입 오류
}
```

## 빠짐없는 분기와 `never`

판별 가능한 유니온의 모든 상태를 처리하고 싶은 경우 `never`를 사용할 수 있습니다.

```ts
function assertNever(
  value: never
): never {
  throw new Error(
    `처리하지 않은 상태: ${
      JSON.stringify(value)
    }`
  );
}
```

예를 들어:

```ts
function render(
  state: LoadState<string[]>
) {
  switch (state.status) {
    case "idle":
      return "대기";

    case "loading":
      return "불러오는 중";

    case "ready":
      return state.data.join(", ");

    case "error":
      return state.message;

    default:
      return assertNever(state);
  }
}
```

현재 모든 상태를 처리했다면 `default`에서 `state`의 타입은 `never`입니다.

나중에 새로운 상태를 추가했다고 가정합니다.

```ts
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "empty" }
  | { status: "ready"; data: T }
  | {
      status: "error";
      message: string;
    };
```

그런데 `switch`에 `"empty"` 분기를 추가하지 않았다면 `default`에서 `state`가 `never`가 아니므로 컴파일 오류가 발생합니다.

즉 새로운 상태를 추가했는데 처리 코드를 빼먹은 문제를 컴파일 단계에서 찾을 수 있습니다.

## `unknown`

외부에서 들어온 값인데 아직 타입을 신뢰할 수 없다면 `unknown`이 적합합니다.

```ts
function parseBoard(
  value: unknown
) {
  // 검사 전에는 자유롭게 사용할 수 없습니다.
}
```

`unknown` 값의 속성에는 바로 접근할 수 없습니다.

```ts
function readTitle(
  value: unknown
) {
  return value.title;
  // 타입 오류
}
```

먼저 값의 종류를 확인해야 합니다.

```ts
function readTitle(
  value: unknown
) {
  if (
    typeof value !== "object" ||
    value === null
  ) {
    throw new Error(
      "객체가 필요합니다."
    );
  }

  // 이후에도 필요한 속성을 더 검사해야 합니다.
}
```

이 제약은 번거로운 것이 아니라 **검사하지 않은 값을 실수로 신뢰하지 못하게 하는 안전 장치**입니다.

## `any`

`any`는 대부분의 타입 검사를 끕니다.

```ts
function readTitle(
  value: any
) {
  return value.board.title.trim();
}
```

`value`가 실제로 무엇인지 TypeScript가 확인하지 않으므로 잘못된 코드도 컴파일될 수 있습니다.

예를 들어 런타임에서 `value`가 `null`이라면 오류가 발생합니다.

```ts
readTitle(null);
```

`any`를 사용하면 타입 시스템의 보호를 해당 값 주변에서 크게 잃게 됩니다.

따라서 외부 입력의 기본 타입으로 `any`를 두는 것보다 `unknown`을 두고 필요한 검사를 수행하는 편이 안전합니다.

```text
unknown
→ 검사 전에는 사용할 수 없음

any
→ 거의 모든 사용을 허용
→ 타입 오류를 숨길 수 있음
```

## 타입 단언

타입 단언(type assertion)은 개발자가 컴파일러에게 값의 타입을 더 구체적으로 알려 주는 문법입니다.

```ts
const board =
  JSON.parse(text) as Board;
```

중요한 점은 `as Board`가 실행 시 어떤 검사도 하지 않는다는 것입니다.

다음 JSON이 들어와도:

```json
{
  "id": 123,
  "title": null
}
```

다음 코드는 값을 그대로 `Board`라고 믿게 만듭니다.

```ts
const board =
  JSON.parse(text) as Board;
```

그러나 런타임 값은 여전히:

```text
id    → number
title → null
```

입니다.

타입 단언은:

```text
값 변환 → 아님
값 검증 → 아님
컴파일러에게 개발자의 지식을 전달 → 맞음
```

따라서 외부 데이터를 검증하는 도구로 사용하면 안 됩니다.

## `JSON.parse()`와 타입

`JSON.parse()`는 문자열을 JavaScript 값으로 바꿉니다.

```ts
const value =
  JSON.parse(text);
```

하지만 JSON 문법이 유효하다는 것과 애플리케이션이 기대하는 구조라는 것은 다른 문제입니다.

다음 JSON은 문법적으로 유효합니다.

```json
{
  "unexpected": true
}
```

그러나 `Board`는 아닙니다.

따라서 다음 두 단계를 구분해야 합니다.

```text
JSON 파싱
→ JSON 문법이 유효한가?

런타임 검증
→ 애플리케이션이 기대하는 구조와 제약을 만족하는가?
```

## 객체인지 검사하는 타입 가드

외부 값을 직접 검사할 때 다음과 같은 보조 함수를 사용할 수 있습니다.

```ts
function isRecord(
  value: unknown
): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}
```

반환 타입의:

```ts
value is Record<string, unknown>
```

부분은 이 함수가 `true`를 반환한 뒤 TypeScript가 `value`를 해당 타입으로 좁히게 하는 **타입 가드(type guard)** 입니다.

사용 예:

```ts
function readId(
  value: unknown
) {
  if (!isRecord(value)) {
    throw new Error(
      "객체가 필요합니다."
    );
  }

  const id = value.id;

  if (typeof id !== "string") {
    throw new Error(
      "id는 문자열이어야 합니다."
    );
  }

  return id;
}
```

## 타입 가드는 검증 로직과 일치해야 합니다

타입 가드의 반환 타입은 TypeScript에 강한 약속을 합니다.

따라서 다음처럼 실제 검사보다 더 강한 타입을 선언하면 위험합니다.

```ts
type Board = {
  id: string;
  title: string;
};

function isBoard(
  value: unknown
): value is Board {
  return true;
}
```

컴파일러는 `true`가 반환된 뒤 값을 `Board`라고 믿지만 실제 검증은 전혀 하지 않았습니다.

타입 가드의 구현과 선언된 타입이 일치해야 합니다.

## 검증과 정규화를 함께 하는 파서

외부 값을 검사만 하고 그대로 반환할 수도 있지만, 애플리케이션에서 사용하기 좋은 형태로 정규화하면서 반환할 수도 있습니다.

```ts
type Board = {
  id: string;
  title: string;
};

function parseBoard(
  value: unknown
): Board {
  if (!isRecord(value)) {
    throw new Error(
      "board는 객체여야 합니다."
    );
  }

  if (
    typeof value.id !== "string" ||
    !value.id
  ) {
    throw new Error(
      "id가 필요합니다."
    );
  }

  if (
    typeof value.title !== "string"
  ) {
    throw new Error(
      "title은 문자열이어야 합니다."
    );
  }

  const title =
    value.title.trim();

  if (!title) {
    throw new Error(
      "title이 필요합니다."
    );
  }

  return {
    id: value.id,
    title,
  };
}
```

이 함수는 세 가지 일을 합니다.

```text
1. 구조 검사
2. 필드 제약 검사
3. 값 정규화
```

함수를 통과한 뒤에는 반환값을 `Board`로 신뢰할 수 있습니다.

```ts
const board =
  parseBoard(externalValue);

console.log(
  board.title.toUpperCase()
);
```

## 검사 함수와 파서 함수의 차이

다음 함수는 불리언을 반환합니다.

```ts
function isRole(
  value: unknown
): value is Role {
  return (
    value === "owner" ||
    value === "editor" ||
    value === "viewer"
  );
}
```

검사 결과에 따라 호출자가 행동을 결정할 수 있습니다.

```ts
if (isRole(value)) {
  useRole(value);
}
```

반면 파서 함수는 실패하면 오류를 던지고 성공하면 검증된 값을 반환합니다.

```ts
function parseRole(
  value: unknown
): Role {
  if (!isRole(value)) {
    throw new Error(
      "올바르지 않은 역할입니다."
    );
  }

  return value;
}
```

사용:

```ts
const role =
  parseRole(externalValue);
```

대략 다음 기준으로 선택할 수 있습니다.

```text
검사 결과에 따라 호출자가 분기하고 싶음
→ isXxx()

실패하면 즉시 중단하고 검증된 값을 받고 싶음
→ parseXxx()
```

## 런타임 스키마 라이브러리

필드가 많아지면 직접 검증 함수를 계속 작성하기보다 런타임 스키마 라이브러리를 사용할 수 있습니다.

Zod를 예로 들면:

```ts
import { z } from "zod";

const BoardSchema = z.object({
  id: z.string().uuid(),
  title:
    z.string()
      .trim()
      .min(1)
      .max(80),
  version:
    z.number()
      .int()
      .nonnegative(),
});
```

이 스키마는 런타임에서 실제 값을 검사합니다.

```ts
const board =
  BoardSchema.parse(value);
```

검증에 성공하면 검사된 값을 반환하고, 실패하면 Zod 오류를 던집니다.

## 스키마에서 TypeScript 타입 추론하기

Zod 스키마에서 TypeScript 타입을 만들 수 있습니다.

```ts
type BoardDto =
  z.infer<typeof BoardSchema>;
```

이렇게 하면 스키마와 TypeScript 타입을 따로 작성하면서 둘이 어긋나는 문제를 줄일 수 있습니다.

```text
BoardSchema
  ├─ 런타임 검증
  └─ z.infer
       ↓
    BoardDto 타입
```

사용 예:

```ts
const value: unknown =
  await response.json();

const board: BoardDto =
  BoardSchema.parse(value);
```

## `parse()`와 `safeParse()`

`parse()`는 검증 실패 시 예외를 던집니다.

```ts
const board =
  BoardSchema.parse(value);
```

예외 흐름이 자연스러운 경계에서는 간단합니다.

반면 실패를 값으로 다루고 싶다면 `safeParse()`를 사용할 수 있습니다.

```ts
const result =
  BoardSchema.safeParse(value);

if (!result.success) {
  console.error(result.error);
  return;
}

const board = result.data;
```

다음처럼 선택할 수 있습니다.

```text
검증 실패를 예외로 처리
→ parse()

검증 성공·실패를 값으로 분기
→ safeParse()
```

프로젝트에서 한 경계의 오류 처리 방식을 일관되게 정하면 좋습니다.

## 스키마는 구조와 값 제약을 검사합니다

다음 스키마는:

```ts
const BoardSchema = z.object({
  id: z.string().uuid(),
  title:
    z.string()
      .trim()
      .min(1)
      .max(80),
  version:
    z.number()
      .int()
      .nonnegative(),
});
```

다음과 같은 사실을 확인할 수 있습니다.

```text
id
→ 문자열
→ UUID 형식

title
→ 문자열
→ trim 후 최소 1자
→ 최대 80자

version
→ 숫자
→ 정수
→ 0 이상
```

하지만 이 스키마만으로는 다음 질문에 답할 수 없습니다.

```text
현재 사용자가 이 보드의 소유자인가?
이 version이 DB의 현재 version과 같은가?
이 제목이 조직 정책상 허용되는가?
이 보드가 현재 삭제 가능한 상태인가?
```

이런 규칙은 다른 현재 상태를 함께 봐야 합니다.

## 구조 검증과 업무 규칙을 구분합니다

검증 규칙을 크게 두 종류로 나눠 생각할 수 있습니다.

### 값 자체만 보면 판단할 수 있는 규칙

```text
문자열인가?
UUID 형식인가?
1~80자인가?
정수인가?
허용된 enum 값인가?
```

이런 규칙은 스키마에서 확인하기 좋습니다.

### 다른 상태가 필요한 규칙

```text
현재 사용자가 소유자인가?
DB의 현재 버전과 일치하는가?
잔액이 충분한가?
이미 삭제된 리소스인가?
```

이런 규칙은 요청 값만 봐서는 판단할 수 없습니다.

서비스나 저장 계층에서 현재 사용자, 데이터베이스 상태 등을 조회한 뒤 판단해야 합니다.

```text
요청 스키마 검증
→ 값 자체의 형식과 범위

서비스·저장 로직
→ 현재 사용자와 현재 DB 상태를 함께 보는 규칙
```

스키마를 통과했다고 업무적으로 요청을 허용할 수 있다는 뜻은 아닙니다.

## 입력 경계에서 검증합니다

외부 값을 애플리케이션 깊숙이 `unknown` 상태로 흘려보내기보다 들어오는 경계에서 검증하는 것이 좋습니다.

예를 들어 HTTP 요청 본문:

```ts
const body: unknown =
  request.body;

const input =
  CreateBoardSchema.parse(body);

await createBoard(input);
```

WebSocket 메시지:

```ts
const message: unknown =
  JSON.parse(rawMessage);

const event =
  ClientEventSchema.parse(message);

handleClientEvent(event);
```

브라우저 저장소:

```ts
const raw =
  localStorage.getItem("settings");

const parsed: unknown =
  raw === null
    ? null
    : JSON.parse(raw);

const settings =
  SettingsSchema.parse(parsed);
```

경계를 통과한 뒤 내부 코드에서는 검증된 타입을 사용합니다.

```text
외부
→ unknown
→ 검증
→ 내부 신뢰 타입
```

## 전송 값과 내부 값은 다를 수 있습니다

HTTP 요청과 응답에 사용하는 값은 네트워크로 직렬화 가능한 데이터여야 합니다.

예를 들어 응답 DTO는 다음처럼 만들 수 있습니다.

```ts
type BoardDto = {
  id: string;
  title: string;
  updatedAt: string;
};
```

하지만 애플리케이션 내부에서는 날짜를 `Date`로 사용할 수도 있습니다.

```ts
type Board = {
  id: string;
  title: string;
  updatedAt: Date;
};
```

HTTP 응답으로 보낼 때 변환합니다.

```ts
function toBoardDto(
  board: Board
): BoardDto {
  return {
    id: board.id,
    title: board.title,
    updatedAt:
      board.updatedAt.toISOString(),
  };
}
```

즉 같은 개념이라도 경계에 따라 표현이 다를 수 있습니다.

```text
내부 Board
updatedAt: Date

HTTP BoardDto
updatedAt: string
```

## DTO란 무엇인가

DTO(Data Transfer Object)는 계층이나 프로세스 사이에서 데이터를 전달하기 위한 값의 구조를 의미합니다.

HTTP API에서는 보통 다음과 같이 생각할 수 있습니다.

```text
요청 DTO
→ 클라이언트가 서버로 보내는 데이터

응답 DTO
→ 서버가 클라이언트로 공개하는 데이터
```

DTO는 외부 계약이므로 내부 데이터 구조와 분리하면 다음 장점이 있습니다.

- 데이터베이스 스키마 변경이 API에 바로 노출되지 않습니다.
- 내부 전용 필드를 실수로 응답에 포함할 가능성을 줄입니다.
- 날짜, enum, 식별자 등을 전송 형식으로 명확히 변환할 수 있습니다.
- API가 공개하는 필드를 의도적으로 선택할 수 있습니다.

## 데이터베이스 행을 그대로 응답하지 않습니다

데이터베이스 조회 결과에 다음 필드가 있다고 가정합니다.

```ts
type BoardRow = {
  id: string;
  title: string;
  owner_id: string;
  internal_note: string | null;
  deleted_at: Date | null;
  updated_at: Date;
};
```

이를 그대로 API 응답으로 반환하면 원하지 않는 내부 정보가 노출될 수 있습니다.

```ts
return row;
```

대신 공개할 값만 새 객체로 만듭니다.

```ts
type BoardDto = {
  id: string;
  title: string;
  updatedAt: string;
};

function toBoardDto(
  row: BoardRow
): BoardDto {
  return {
    id: row.id,
    title: row.title,
    updatedAt:
      row.updated_at.toISOString(),
  };
}
```

이 변환은 단순한 스타일 문제가 아니라 **외부 계약의 경계**입니다.

## 서비스 명령 타입을 따로 둘 수 있습니다

HTTP 요청 DTO가 서비스 계층에서 그대로 필요한 형태와 항상 같지는 않습니다.

예를 들어 요청은 다음과 같을 수 있습니다.

```ts
type CreateBoardRequest = {
  title: string;
};
```

하지만 서비스에는 현재 사용자 ID도 필요합니다.

```ts
type CreateBoardCommand = {
  actorId: string;
  title: string;
};
```

HTTP 계층에서 검증한 요청과 인증 정보를 조합합니다.

```ts
const body =
  CreateBoardSchema.parse(
    request.body
  );

const command: CreateBoardCommand = {
  actorId: request.user.id,
  title: body.title,
};

const board =
  await boardService.create(command);
```

이렇게 하면 클라이언트가 `actorId`를 직접 결정하지 못하게 할 수 있습니다.

```text
HTTP 요청 DTO
→ 클라이언트가 제공할 수 있는 값

서비스 명령
→ 서버가 신뢰 가능한 정보까지 조합한 값
```

## 하나의 타입을 모든 계층에서 공유하지 않습니다

다음 하나의 타입을:

```ts
type Board = {
  id: string;
  ownerId: string;
  title: string;
  internalNote: string | null;
  updatedAt: Date;
};
```

다음 모든 곳에서 그대로 사용하려고 하면 문제가 생길 수 있습니다.

```text
HTTP 요청
HTTP 응답
서비스 내부
DB 조회 결과
브라우저 상태
```

각 경계는 요구사항이 다릅니다.

예를 들어:

```text
HTTP 요청
→ id가 아직 없을 수 있음
→ ownerId는 클라이언트가 정하면 안 될 수 있음

DB 행
→ snake_case 열 이름
→ 내부 열 포함 가능

서비스 객체
→ Date 사용 가능

HTTP 응답
→ Date를 문자열로 직렬화
→ 내부 필드 제외
```

따라서 타입 이름이 조금 늘어나더라도 경계별 역할을 분리하는 편이 명확할 수 있습니다.

## 예제: 요청부터 응답까지

다음은 값을 경계별로 구분한 간단한 예입니다.

### 요청 스키마

```ts
const CreateBoardSchema = z.object({
  title:
    z.string()
      .trim()
      .min(1)
      .max(80),
});

type CreateBoardRequest =
  z.infer<
    typeof CreateBoardSchema
  >;
```

### 서비스 명령

```ts
type CreateBoardCommand = {
  actorId: string;
  title: string;
};
```

### 데이터베이스 행

```ts
type BoardRow = {
  id: string;
  owner_id: string;
  title: string;
  updated_at: Date;
};
```

### 응답 DTO

```ts
type BoardDto = {
  id: string;
  title: string;
  updatedAt: string;
};
```

### 흐름

```ts
const body =
  CreateBoardSchema.parse(
    request.body
  );

const command:
  CreateBoardCommand = {
    actorId: request.user.id,
    title: body.title,
  };

const row =
  await repository.create(command);

const responseBody: BoardDto = {
  id: row.id,
  title: row.title,
  updatedAt:
    row.updated_at.toISOString(),
};

return responseBody;
```

전체 데이터 흐름은 다음과 같습니다.

```text
HTTP의 unknown 값
        ↓
CreateBoardSchema
        ↓
CreateBoardRequest
        ↓
인증 정보와 결합
        ↓
CreateBoardCommand
        ↓
repository
        ↓
BoardRow
        ↓
공개 필드 선택과 변환
        ↓
BoardDto
        ↓
HTTP 응답
```

각 타입은 같은 데이터를 중복 표현하는 것이 아니라 서로 다른 신뢰 경계와 책임을 나타냅니다.

## 환경 변수는 문자열 외부 입력입니다

Node.js의 환경 변수는 일반적으로 문자열 또는 `undefined`입니다.

예를 들어:

```ts
process.env.PORT
```

타입은 보통 다음과 비슷합니다.

```ts
string | undefined
```

환경 변수에:

```text
PORT=3000
```

이라고 적혀 있어도 JavaScript 값은 숫자 `3000`이 아니라 문자열 `"3000"`입니다.

따라서 다음 두 단계가 필요합니다.

```text
문자열
→ 원하는 타입으로 변환
→ 범위와 허용값 검증
```

## 환경 변수 스키마

Zod를 사용하면 다음처럼 작성할 수 있습니다.

```ts
const EnvSchema = z.object({
  PORT:
    z.coerce
      .number()
      .int()
      .min(1)
      .max(65535),

  DATABASE_URL:
    z.string().url(),

  NODE_ENV:
    z.enum([
      "development",
      "test",
      "production",
    ]),
});
```

`z.coerce.number()`는 문자열 입력을 숫자로 변환한 뒤 숫자 규칙을 적용합니다.

```ts
export const env =
  EnvSchema.parse(process.env);
```

이후 애플리케이션에서는 다음처럼 검증된 값을 사용합니다.

```ts
env.PORT
// number

env.NODE_ENV
// "development" | "test" | "production"
```

## 환경 변수는 시작 시 한 번 검증합니다

환경 변수를 사용하는 곳마다 제각각 변환하면 코드가 일관되지 않을 수 있습니다.

예를 들어:

```ts
// server.ts
const port =
  Number(process.env.PORT);

// worker.ts
const port =
  parseInt(
    process.env.PORT ?? "",
    10
  );

// test.ts
const port =
  process.env.PORT as unknown as number;
```

같은 설정을 서로 다르게 해석하고 있습니다.

대신 시작 시 한 번 검증합니다.

```ts
// env.ts
export const env =
  EnvSchema.parse(process.env);
```

다른 코드에서는 검증된 값만 가져옵니다.

```ts
import { env } from "./env.js";

server.listen(env.PORT);
```

이렇게 하면 설정 오류를 가능한 한 빨리 발견할 수 있습니다.

## 잘못된 설정은 요청을 받기 전에 실패시킵니다

예를 들어:

```text
PORT=abc
```

인데 서버가 먼저 시작되고 첫 요청을 처리할 때만 오류가 나면 원인을 찾기 어렵습니다.

프로세스 시작 시 검증하면:

```text
프로세스 시작
  ↓
환경 변수 검증
  ↓
실패
  ↓
즉시 종료
```

와 같이 잘못된 설정을 초기에 발견할 수 있습니다.

설정이 잘못된 상태로 일부 기능만 어설프게 실행되는 것보다 명확한 시작 실패가 보통 더 안전합니다.

## 기본값도 스키마에서 명시합니다

선택적 환경 변수에 기본값이 있다면 한 곳에서 정할 수 있습니다.

```ts
const EnvSchema = z.object({
  PORT:
    z.coerce
      .number()
      .int()
      .min(1)
      .max(65535)
      .default(3000),

  LOG_LEVEL:
    z.enum([
      "debug",
      "info",
      "warn",
      "error",
    ])
    .default("info"),
});
```

그러면 다른 코드에서 반복해서:

```ts
process.env.LOG_LEVEL ?? "info"
```

같은 기본값 로직을 작성하지 않아도 됩니다.

중요한 설정에는 무조건 기본값을 주기보다 값이 없을 때 시작을 실패시키는 것이 더 적절할 수도 있습니다.

예를 들어 데이터베이스 연결 주소가 반드시 필요하다면:

```ts
DATABASE_URL:
  z.string().url()
```

처럼 필수로 두는 편이 명확합니다.

## 정규화된 환경 값만 내부에서 사용합니다

환경 변수 검증 이후에는 `process.env`를 애플리케이션 곳곳에서 다시 읽지 않는 편이 좋습니다.

```ts
// 피하고 싶은 형태
function connect() {
  const url =
    process.env.DATABASE_URL;
}
```

대신 검증된 설정 객체를 사용합니다.

```ts
import { env } from "./env.js";

function connect() {
  const url =
    env.DATABASE_URL;
}
```

흐름은 다음과 같습니다.

```text
process.env
   ↓
EnvSchema.parse()
   ↓
env
   ↓
애플리케이션 전체에서 사용
```

이렇게 하면 내부 코드는 환경 변수가 실제로 존재하고 올바른 타입이라는 전제로 작성할 수 있습니다.

## 값이 이동하는 순서

외부 입력은 다음처럼 단계적으로 신뢰 수준을 높입니다.

```text
외부의 unknown 값
        ↓
런타임 검사와 정규화
        ↓
요청 DTO
        ↓
서비스 명령
        ↓
저장 코드
```

응답은 반대 방향으로 이동할 수 있습니다.

```text
데이터베이스 결과
        ↓
서비스에서 사용할 값
        ↓
외부에 공개할 필드 선택
        ↓
응답 DTO
        ↓
JSON 직렬화
```

핵심은 **외부 값, 내부 값, 저장 값, 전송 값을 하나의 타입으로 억지로 통일하지 않는 것**입니다.

각 경계에서 필요한 조건과 공개 범위가 다르기 때문입니다.

## 검증 경계를 정합니다

모든 함수에서 같은 값을 반복 검증할 필요는 없습니다.

예를 들어 HTTP 경계에서 다음 값을 검증했다고 가정합니다.

```ts
const input =
  CreateBoardSchema.parse(
    request.body
  );
```

그 뒤 서비스 함수가 오직 이 검증된 타입으로만 호출된다면 서비스 내부에서 다시 `"title이 문자열인가?"`를 검사할 필요는 없습니다.

```ts
type CreateBoardCommand = {
  actorId: string;
  title: string;
};

async function createBoard(
  command: CreateBoardCommand
) {
  // title이 문자열이라는 구조 검사는
  // 이미 경계에서 끝났다고 볼 수 있습니다.
}
```

하지만 서비스에서 확인해야 하는 다른 규칙은 남아 있습니다.

```text
현재 사용자가 보드를 만들 권한이 있는가?
같은 이름의 보드가 허용되는가?
조직 한도를 초과했는가?
```

즉 검증은 무조건 모든 계층에서 반복하는 것이 아니라 **각 규칙을 가장 적절한 경계에서 한 번 명확하게 확인하는 것**이 중요합니다.

## TypeScript 타입과 데이터베이스 제약도 서로 대체하지 않습니다

애플리케이션 타입이 다음과 같다고 가정합니다.

```ts
type User = {
  email: string;
};
```

이 타입만으로는 데이터베이스에서 이메일 중복이 발생하지 않는다는 것을 보장할 수 없습니다.

반대로 데이터베이스에 `UNIQUE` 제약이 있다고 해서 HTTP 요청이 문자열 형식인지 자동으로 친절하게 검증되는 것도 아닙니다.

각 계층의 역할은 다릅니다.

```text
TypeScript
→ 코드 수준의 정적 타입 안전성

런타임 스키마
→ 외부 값의 구조와 범위 검증

서비스 규칙
→ 현재 상태와 사용자를 고려한 업무 판단

데이터베이스 제약
→ 저장되는 데이터의 최종 무결성 보장
```

한 계층이 다른 계층을 완전히 대신한다고 생각하지 않습니다.

## 흔한 실수

- TypeScript 타입이 런타임에도 남아 실제 값을 검사한다고 생각합니다.
- HTTP 응답에 `Promise<Board>` 타입을 적으면 서버가 항상 `Board`를 반환한다고 생각합니다.
- 외부 값을 `any`로 받고 바로 속성에 접근합니다.
- `unknown`이 불편하다는 이유로 모두 `any`로 바꿉니다.
- 타입 단언 `as Board`를 런타임 검증처럼 사용합니다.
- `JSON.parse()`에 성공하면 애플리케이션 데이터 구조도 올바르다고 생각합니다.
- 타입 가드의 실제 검사보다 더 강한 반환 타입을 선언합니다.
- 여러 불리언으로 모순된 UI 상태를 만듭니다.
- 새 유니온 상태를 추가하고 `switch` 처리 분기를 빠뜨립니다.
- 리터럴 유니온을 선언하면 외부 문자열도 자동으로 그 값들 중 하나가 된다고 생각합니다.
- 스키마를 통과하면 권한과 업무 규칙도 통과한 것으로 생각합니다.
- 현재 사용자나 DB 상태가 필요한 규칙까지 요청 스키마 하나에 억지로 넣습니다.
- 데이터베이스 행을 API 응답으로 그대로 보냅니다.
- 내부 `Date` 객체와 외부 JSON 문자열을 같은 타입으로 취급합니다.
- 클라이언트가 정하면 안 되는 `actorId`, 권한, 가격 같은 값을 요청 DTO에서 그대로 신뢰합니다.
- 하나의 타입을 HTTP 요청, 응답, 서비스, DB 행에 모두 공유합니다.
- 환경 변수가 이미 숫자나 불리언이라고 생각합니다.
- 환경 변수를 사용하는 곳마다 제각각 변환합니다.
- 프로세스 시작 시 설정을 검증하지 않고 첫 요청이 들어온 뒤에야 실패하게 둡니다.
- 환경 변수 검증 후에도 애플리케이션 곳곳에서 `process.env`를 직접 다시 읽습니다.

## 관련 exercise

[`runtime-workspace`](../../exercises/runtime-workspace/README.md)는 `unknown` 포트 값을 검사합니다. [`notes-api`](../../exercises/notes-api/README.md)는 HTTP 본문을 Zod로 검사하고 안정된 오류 응답으로 바꿉니다.

## 완료 기준

다음 내용을 설명하거나 직접 구현할 수 있으면 이 문서의 목표를 달성한 것입니다.

- TypeScript 타입이 런타임 검증을 대신하지 못하는 이유를 설명할 수 있습니다.
- 지역 변수에서는 타입 추론을 활용하고 공개 함수의 입력·반환 타입은 필요에 따라 명시할 수 있습니다.
- 리터럴 유니온으로 역할이나 상태의 허용 값을 제한할 수 있습니다.
- 판별 가능한 유니온으로 모순된 상태를 만들기 어렵게 할 수 있습니다.
- `never`를 사용해 `switch`의 빠짐없는 분기를 확인할 수 있습니다.
- `unknown`, `any`, 타입 단언의 차이를 설명할 수 있습니다.
- 외부 JSON을 `unknown`으로 받고 타입 가드나 파서로 검사할 수 있습니다.
- 타입 단언이 값을 검증하거나 변환하지 않는다는 점을 설명할 수 있습니다.
- Zod 스키마로 값의 구조, 길이, 범위, enum 같은 런타임 조건을 검사할 수 있습니다.
- `parse()`와 `safeParse()`의 실패 처리 방식 차이를 설명할 수 있습니다.
- 스키마 검사와 현재 사용자·DB 상태를 함께 봐야 하는 업무 규칙을 구분할 수 있습니다.
- HTTP 요청 DTO, 서비스 명령, 데이터베이스 행, 응답 DTO를 서로 다른 경계의 타입으로 설계할 수 있습니다.
- 데이터베이스 행에서 외부에 보낼 필드만 선택해 DTO를 만들 수 있습니다.
- 환경 변수가 문자열 또는 `undefined`로 들어온다는 점을 설명할 수 있습니다.
- 환경 변수를 프로세스 시작 시 한 번 검증하고 정규화할 수 있습니다.
- 검증 이후에는 애플리케이션 내부에서 정규화된 설정 객체를 사용할 수 있습니다.
