# Zod를 이용한 요청·응답 검증

HTTP 본문, 경로 값, 쿼리, 헤더와 WebSocket 메시지는 모두 신뢰할 수 없는 값입니다. TypeScript 타입은 실행 중에 사라지므로 Zod 같은 스키마로 실제 값을 검사해야 합니다.

## 목표

- 요청에서 받은 모든 값을 실행 중에 검사합니다.
- 문자열 정리와 타입 변환을 한곳에서 처리합니다.
- 권한과 현재 데이터가 필요한 규칙은 스키마 검사와 구분합니다.
- 응답에 내부 필드가 섞이지 않게 합니다.
- 검증 오류를 안정적인 API 오류 형식으로 바꿉니다.

## 입력 스키마

```ts
export const CreateBoardSchema = z.object({
  title: z.string().trim().min(1).max(80)
}).strict();
```

`trim()` 뒤 빈 문자열을 거부합니다. `.strict()`로 알 수 없는 필드를 거부할지, 무시할지는 API의 호환 방식에 맞춰 정합니다.

경로와 쿼리도 검사합니다.

```ts
const BoardParamsSchema = z.object({ id: z.string().uuid() });
const BoardQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).default(20),
  cursor: z.string().min(1).optional()
});
```

강제 변환은 편리하지만 빈 문자열과 불리언이 어떤 값으로 바뀌는지 확인하고 사용합니다.

## 정규화

```ts
const EmailSchema = z.string().trim().toLowerCase().email();
```

외부 표현을 비교와 저장에 쓸 형태로 바꿀 수 있습니다. 사용자가 입력한 원래 표시 문자열이 필요하다면 별도로 보존합니다. 유니코드와 대소문자 규칙은 식별자의 실제 의미에 맞춰 정합니다.

## 스키마만으로 확인할 수 없는 규칙

스키마는 다음을 확인할 수 있습니다.

- 필드 존재 여부와 타입
- 문자열 길이와 패턴
- 숫자 범위
- 메시지 종류별 필드

하지만 다음 항목은 현재 사용자와 저장된 데이터를 함께 봐야 합니다.

- 사용자가 해당 보드의 구성원인가
- 같은 범위에서 제목이 중복되는가
- `baseVersion`이 현재 버전과 같은가
- 계정이 정지되었는가

```text
외부 입력
→ Zod 파싱
→ 현재 사용자 확인
→ 업무 처리 함수 호출
→ 데이터베이스 조회와 변경
```

스키마 검사를 통과했다고 권한과 업무 규칙까지 통과한 것은 아닙니다.

## 응답 필드 제한

데이터베이스 행을 그대로 응답하지 않습니다.

```ts
const BoardResponseSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  role: z.enum(["owner", "editor", "viewer"]),
  version: z.number().int().nonnegative()
});
```

비밀번호 해시, 세션 토큰 다이제스트와 내부 상태 값이 실수로 포함되지 않게 필요한 필드만 DTO로 만듭니다.

## 오류 내용 변환

Zod의 전체 issue를 그대로 외부에 보내면 내부 스키마 이름과 구현 세부 정보가 공개될 수 있습니다.

```ts
function toValidationDetails(error: z.ZodError) {
  return error.issues.map((issue) => ({
    path: issue.path.join("."),
    reason: issue.code
  }));
}
```

클라이언트는 Zod의 기본 영어 문장이 아니라 안정적인 오류 코드와 필드 경로를 사용합니다.

## 공유할 스키마

HTTP와 WebSocket이 같은 역할, 항목과 좌표 형식을 쓴다면 별도 패키지에서 공유할 수 있습니다. 다음 항목은 브라우저와 공유하지 않습니다.

- 데이터베이스 클라이언트 타입
- 서버 비밀 설정
- 서버 전용 오류 클래스
- 저장소 구현
- 컴포넌트의 로컬 상태

공유 패키지는 전송할 값에 집중합니다.

## WebSocket 메시지

```ts
const ClientMessageSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("board.join"),
    boardId: z.string().uuid()
  }),
  z.object({
    type: z.literal("item.move"),
    boardId: z.string().uuid(),
    itemId: z.string().uuid(),
    baseVersion: z.number().int().nonnegative(),
    x: z.number().finite(),
    y: z.number().finite(),
    final: z.boolean()
  })
]);
```

`type` 값으로 먼저 나누면 각 메시지에 필요한 필드를 정확히 검사할 수 있습니다. JSON 파싱 실패 하나가 서버 프로세스 전체를 종료하게 해서는 안 됩니다.

## 버전 호환

클라이언트와 서버가 동시에 배포되지 않을 수 있습니다. 선택 필드 추가, 열거형 값 추가와 필드 제거가 이전 버전에서 어떻게 보일지 검토합니다. 알 수 없는 열거형 값을 받았을 때의 동작도 정합니다.

## 흔한 실수

- 본문만 검사하고 경로·쿼리·헤더는 문자열로 신뢰합니다.
- 타입 단언으로 실제 검사를 대신합니다.
- 스키마 통과를 권한 승인으로 간주합니다.
- 데이터베이스 행을 응답에 그대로 사용합니다.
- Zod의 내부 오류 메시지에 클라이언트가 직접 의존합니다.

## 완료 기준

- 본문·경로·쿼리·헤더·메시지를 실행 중에 검사합니다.
- 정규화와 현재 데이터 확인을 구분합니다.
- 응답 DTO에 공개할 필드만 포함합니다.
- 검증 오류를 안정적인 코드와 필드 경로로 바꿉니다.
- 브라우저와 공유할 스키마의 범위를 설명합니다.

## 연결 exercise

[`notes-api`](../../exercises/notes-api/README.md)에서 생성 요청과 오류 응답을 검증합니다. [`realtime-board`](../../exercises/realtime-board/README.md)에서는 메시지 종류별 스키마를 사용합니다.
