# TypeScript와 런타임 검증

TypeScript 타입은 빌드할 때 사라집니다. HTTP 본문, 환경 변수, URL, WebSocket 메시지, 브라우저 저장 값은 컴파일러가 만든 값이 아니므로 실행 중에 확인해야 합니다.

## 목표

- 추론에 맡길 타입과 명시할 타입을 구분합니다.
- 리터럴 유니온으로 허용 값을 제한합니다.
- `unknown`, `any`, 타입 단언의 차이를 이해합니다.
- 외부 값을 검사해 애플리케이션에서 사용할 값으로 변환합니다.
- 전송 값, 업무에서 쓰는 값, 데이터베이스 행을 구분합니다.

## 타입 추론과 공개 함수

```ts
const retryCount = 0;

export function normalizeTitle(input: string): string {
  return input.trim();
}
```

지역 변수는 추론으로 충분한 경우가 많습니다. 외부에서 호출하는 함수의 입력과 반환 타입은 명시하면 사용법을 확인하기 쉽습니다.

## 허용 값 제한

```ts
type Role = "owner" | "editor" | "viewer";
```

상태마다 필요한 값이 다르면 판별 가능한 유니온을 사용합니다.

```ts
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "error"; message: string };
```

이렇게 하면 `ready`가 아닌데 `data`가 있거나 대기와 오류가 동시에 참인 상태를 만들기 어렵습니다.

## 빠짐없는 분기

```ts
function assertNever(value: never): never {
  throw new Error(`처리하지 않은 상태: ${JSON.stringify(value)}`);
}
```

`switch`의 마지막에서 `never`를 확인하면 새 상태를 추가하고 처리를 빠뜨렸을 때 컴파일 오류를 만들 수 있습니다.

## `unknown`, `any`, 타입 단언

```ts
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
```

`unknown`은 사용하기 전에 검사해야 합니다. `any`는 대부분의 타입 검사를 끕니다.

```ts
const board = JSON.parse(text) as Board;
```

타입 단언은 값을 바꾸거나 검증하지 않습니다. 개발자가 컴파일러에 “이 값이 맞다”고 말할 뿐입니다.

직접 검사할 수 있습니다.

```ts
function parseBoard(value: unknown): Board {
  if (!isRecord(value)) throw new Error("board는 객체여야 합니다.");
  if (typeof value.id !== "string" || !value.id) {
    throw new Error("id가 필요합니다.");
  }
  if (typeof value.title !== "string" || !value.title.trim()) {
    throw new Error("title이 필요합니다.");
  }
  return { id: value.id, title: value.title.trim() };
}
```

## Zod 스키마

```ts
const BoardSchema = z.object({
  id: z.string().uuid(),
  title: z.string().trim().min(1).max(80),
  version: z.number().int().nonnegative()
});

type BoardDto = z.infer<typeof BoardSchema>;
const board = BoardSchema.parse(await response.json());
```

스키마는 값의 모양과 범위를 확인합니다. “현재 사용자가 소유자인가”, “DB의 현재 버전과 같은가”처럼 다른 상태를 함께 봐야 하는 규칙은 서비스와 저장 코드에서 확인합니다.

## 전송 값과 내부 값

HTTP 응답에는 데이터베이스 연결이나 클래스 메서드를 넣을 수 없습니다. 외부에 공개할 필드만 담은 값을 만듭니다.

```ts
type BoardDto = {
  id: string;
  title: string;
  updatedAt: string;
};
```

데이터베이스 행을 그대로 응답으로 보내면 내부 열이나 개인정보가 노출될 수 있습니다. 필요한 필드만 새 객체로 변환합니다.

## 환경 변수

```ts
const EnvSchema = z.object({
  PORT: z.coerce.number().int().min(1).max(65535),
  DATABASE_URL: z.string().url(),
  NODE_ENV: z.enum(["development", "test", "production"])
});

export const env = EnvSchema.parse(process.env);
```

환경 변수는 프로세스 시작 시 한 번 검사합니다. 잘못된 설정으로 요청을 받기 시작한 뒤 첫 요청에서 실패하게 두지 않습니다.

## 값이 이동하는 순서

```text
외부의 unknown 값
→ 런타임 검사와 정규화
→ 요청 DTO
→ 서비스 명령
→ 저장 코드
```

응답은 저장 결과에서 공개할 필드를 골라 DTO로 만든 뒤 전송합니다. 하나의 타입을 모든 위치에서 공유하려고 하지 않습니다.

## 흔한 실수

- `any`와 타입 단언으로 외부 값을 검사 없이 사용합니다.
- 여러 불리언으로 모순된 상태를 만듭니다.
- 스키마를 통과하면 권한과 업무 규칙도 통과한 것으로 생각합니다.
- 데이터베이스 행을 API 응답으로 그대로 보냅니다.
- 환경 변수를 사용하는 곳마다 제각각 변환합니다.

## 관련 exercise

[`runtime-workspace`](../../exercises/runtime-workspace/README.md)는 `unknown` 포트 값을 검사합니다. [`notes-api`](../../exercises/notes-api/README.md)는 HTTP 본문을 Zod로 검사하고 안정된 오류 응답으로 바꿉니다.

## 완료 기준

- `unknown`, `any`, 타입 단언의 차이를 설명할 수 있습니다.
- 유니온 타입으로 상태와 역할의 허용 값을 제한합니다.
- 외부 JSON과 환경 변수를 실행 중에 검사합니다.
- 스키마 검사와 현재 사용자·DB 상태를 확인하는 규칙을 구분합니다.
- 데이터베이스 행에서 외부에 보낼 DTO를 따로 만듭니다.
