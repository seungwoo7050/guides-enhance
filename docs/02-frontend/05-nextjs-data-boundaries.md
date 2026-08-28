# Next.js 데이터 요청과 어댑터

여러 컴포넌트에서 URL 조합, 헤더 설정, JSON 파싱과 오류 문구를 반복하면 API 변경의 영향이 화면 전체로 퍼집니다. HTTP 처리를 한곳에 모으고, 컴포넌트에는 검증된 값과 분류된 오류만 전달합니다.

## 목표

- 컴포넌트와 HTTP 처리 코드를 분리합니다.
- 서버와 브라우저 중 어디에서 데이터를 읽을지 선택합니다.
- 외부 응답을 런타임에 검증합니다.
- 캐시 키와 변경 뒤 갱신 방법을 정합니다.
- 테스트에서 대기·오류·충돌을 원하는 순서로 재현합니다.

## 어댑터가 HTTP 처리를 맡습니다

```ts
export interface BoardApi {
  listBoards(signal?: AbortSignal): Promise<BoardSummary[]>;
  createBoard(input: CreateBoardInput): Promise<BoardSummary>;
  renameBoard(id: string, input: RenameBoardInput): Promise<BoardSummary>;
}
```

컴포넌트는 실제 URL이나 상태 코드 해석법을 알 필요가 없습니다.

```ts
export function createHttpBoardApi(baseUrl: string): BoardApi {
  return {
    async listBoards(signal) {
      const response = await fetch(`${baseUrl}/boards`, {
        signal,
        credentials: "include"
      });
      return parseResponse(response, BoardListSchema);
    }
  };
}
```

어댑터는 HTTP 실패와 응답 형식 오류를 애플리케이션에서 다룰 오류로 바꿉니다.

## 서버에서 읽을 데이터

첫 화면에 꼭 필요하고 브라우저 상호작용 없이 읽을 수 있는 값은 Server Component에서 가져올 수 있습니다. 다만 다음을 확인해야 합니다.

- 사용자의 세션 쿠키를 어떻게 전달합니까?
- 배포 환경에서 API 주소는 무엇입니까?
- 사용자별 응답이 공유 캐시에 섞이지 않습니까?
- 같은 애플리케이션 내부라면 HTTP를 거칠지 서비스를 직접 호출할지 결정했습니까?

서버에서 읽는다고 보안 검사가 자동으로 끝나는 것은 아닙니다.

## 브라우저에서 읽을 데이터

검색어, 폴링, WebSocket처럼 사용자 입력과 자주 바뀌는 값은 브라우저에서 읽는 편이 적합할 수 있습니다. 이때는 요청 취소, 늦은 응답, 로딩·오류 화면을 직접 관리합니다.

서버와 브라우저가 같은 데이터를 각각 읽고 둘 다 기준값으로 사용하지 않습니다. 서버가 초기값을 전달하고 이후에는 브라우저 캐시가 이어받도록 정할 수 있습니다.

## 응답 검증

```ts
async function parseResponse<T>(response: Response, schema: ZodType<T>): Promise<T> {
  if (!response.ok) throw await toApplicationError(response);
  return schema.parse(await response.json());
}
```

TypeScript 제네릭은 실제 응답을 검사하지 않습니다. `204 No Content`, JSON이 아닌 오류 페이지, 스키마와 다른 응답을 각각 처리합니다.

## 캐시를 쓸 때 답해야 할 질문

- 어떤 키가 같은 데이터를 가리킵니까?
- 얼마 동안 이전 값을 보여 줘도 됩니까?
- 변경 성공 뒤 어떤 키를 다시 읽거나 무효화합니까?
- 새 요청 중에 이전 데이터를 계속 보여 줍니까?
- 사용자, 언어, 필터가 캐시 키에 포함됩니까?

사용자별 데이터를 공개 캐시에 저장하지 않습니다. 권한이나 필터가 다른 응답이 같은 키에 섞이지 않게 합니다.

## 변경 요청과 충돌

```text
입력 검사
→ 대기 화면 또는 임시 변경 표시
→ 요청 전송
→ 성공 결과 반영
→ 409면 최신 값 조회 후 초안과 비교
→ 전송 실패면 재시도 가능 여부 판단
```

충돌을 일반 오류 알림으로만 끝내면 사용자의 초안이 사라질 수 있습니다. 최신 서버 값과 사용자가 입력한 값을 둘 다 보존할 방법을 정합니다.

## 테스트용 어댑터

테스트에서는 실제 시간과 네트워크 없이 완료 시점을 직접 제어합니다.

```ts
export function createDeferredBoardApi() {
  // 테스트가 resolve와 reject 시점을 직접 결정합니다.
}
```

다음 상황을 재현합니다.

- 요청이 계속 대기 중임
- 빈 목록을 받음
- 잘못된 응답을 받음
- 이전 요청이 더 늦게 끝남
- `409` 충돌이 발생함
- 변경 뒤 새 목록을 받음

컴포넌트 테스트는 가짜 어댑터를 사용하고, 실제 URL·헤더·상태 코드 처리는 별도 통합 테스트에서 확인합니다.

## Server Action과 Route Handler

전송 방식이 달라져도 입력 검증, 사용자 확인, 업무 규칙은 유지합니다. UI 컴포넌트 안에서 직접 데이터베이스를 수정하고 권한을 판정하지 않습니다.

## 흔한 실수

- 컴포넌트마다 `fetch`와 JSON 파싱을 반복합니다.
- TypeScript 타입만 믿고 응답을 검증하지 않습니다.
- 서버와 브라우저가 같은 데이터의 기준값을 따로 가집니다.
- 캐시 키에서 사용자나 필터를 빠뜨립니다.
- 변경 성공 뒤 오래된 캐시를 그대로 둡니다.
- `409` 충돌 뒤 사용자의 입력을 조용히 버립니다.

## 완료 기준

- 화면 코드와 HTTP 처리 코드를 나눕니다.
- 서버 또는 브라우저에서 데이터를 읽기로 한 이유를 설명합니다.
- 외부 응답을 스키마로 검사합니다.
- 캐시 키와 변경 뒤 갱신 방법을 정합니다.
- 테스트에서 응답 순서 역전과 충돌을 재현합니다.

## 연결 exercise

[`user-directory`](../../exercises/user-directory/README.md)의 가짜 검색 API로 요청 완료 순서를 제어합니다. 실제 HTTP 변환은 [`notes-api`](../../exercises/notes-api/README.md)에서 확인합니다.
