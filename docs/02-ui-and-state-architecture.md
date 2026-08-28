# UI 상태와 값의 소유 위치

React 화면은 컴포넌트 트리만으로 설명할 수 없습니다. 어떤 값이 존재할 수 있는지, 그 값을 어디에 저장하는지, 어떤 이벤트가 값을 바꾸는지 함께 정해야 합니다. 저장 위치가 불분명하면 URL, 서버 응답과 사용자가 입력 중인 값이 서로 덮어쓰게 됩니다.

이 문서는 특정 상태 관리 라이브러리가 아니라 대부분의 React 프로젝트에서 반복해서 필요한 판단을 다룹니다.

## 목표

이 문서를 읽은 뒤에는 다음 작업을 수행할 수 있어야 합니다.

- URL 상태, 서버 상태, 화면 상태, 입력 초안과 계산값을 구분합니다.
- 서로 동시에 존재할 수 없는 화면 상태를 discriminated union으로 표현합니다.
- 외부 값을 `unknown`으로 받고 필요한 필드를 검사합니다.
- Server Component와 Client Component에 코드를 배치할 기준을 설명합니다.
- 컴포넌트 props에 저장 방식보다 허용할 동작을 표현합니다.

## 값의 종류를 먼저 구분합니다

| 값의 종류 | 예 | 주로 저장할 위치 |
| --- | --- | --- |
| URL 상태 | 검색어, status, page, 선택한 tab | URL과 browser history |
| 서버 상태 | 프로젝트 목록, `version`, 권한 | 서버 저장소와 요청 결과 |
| 화면 상태 | 메뉴 열림, 편집 중 여부, 선택 항목 | 가장 가까운 Client Component |
| 입력 초안 | 아직 저장하지 않은 제목 | 해당 편집 컴포넌트 |
| 지속 설정 | 언어, theme, 열 표시 설정 | 서버 사용자 설정 또는 browser storage |
| 계산값 | 필터 결과 수, 제출 가능 여부 | 렌더링 중 계산 |

같은 값을 여러 곳에 복사하면 그 값들을 다시 맞추는 코드가 필요합니다. URL에 있어야 할 검색 조건을 컴포넌트 상태에만 두면 새로 고침과 뒤로 이동에서 복원할 수 없습니다. 서버가 확정한 제목과 사용자가 작성 중인 제목을 같은 변수에 넣으면 저장 실패와 충돌에서 어느 값으로 돌아가야 할지 알 수 없습니다.

저장 위치를 정할 때 다음 질문을 사용합니다.

1. 새로 고침 뒤에도 남아야 합니까?
2. link로 공유하거나 뒤로 이동할 때 복원해야 합니까?
3. 서버가 최종 값을 결정합니까?
4. 사용자가 저장 전까지 자유롭게 수정해야 합니까?
5. 이미 가진 값에서 바로 계산할 수 있습니까?

## 동시에 존재할 수 없는 상태를 타입으로 막습니다

다음처럼 여러 boolean과 nullable 값을 따로 저장하면 의미 없는 조합이 생깁니다.

```ts
const [pending, setPending] = useState(false);
const [error, setError] = useState<string | null>(null);
const [projects, setProjects] = useState<Project[]>([]);
```

`pending === true`이면서 `error`가 있고 `projects`가 비어 있는 상태가 무엇을 뜻하는지 별도 규칙이 필요합니다. 서로 배타적인 상태는 하나의 union으로 표현하는 편이 안전합니다.

```ts
type CatalogState =
  | { status: "ready"; result: SearchResult }
  | { status: "empty"; result: SearchResult }
  | { status: "pending"; previous: SearchResult }
  | { status: "error"; message: string; previous: SearchResult };
```

이 타입은 다음 동작을 코드에 직접 기록합니다.

- 새 검색 중에는 마지막 정상 결과를 유지합니다.
- 빈 결과는 성공한 응답이며 오류가 아닙니다.
- 요청이 실패해도 마지막 정상 결과와 입력값을 유지합니다.
- 컴포넌트는 `status`를 기준으로 가능한 모든 경우를 처리합니다.

상태 변경을 순수 함수로 분리하면 DOM 없이 검사할 수 있습니다.

```ts
function completeSearch(result: SearchResult): CatalogState {
  return result.projects.length === 0
    ? { status: "empty", result }
    : { status: "ready", result };
}
```

## 외부 값을 타입 단언만으로 믿지 않습니다

TypeScript 타입은 실행 중에 들어오는 HTTP 응답을 검사하지 않습니다.

```ts
const result = (await response.json()) as SearchResult;
```

위 코드는 필드 누락, 잘못된 `status`, 중복 id와 음수 `page`를 그대로 통과시킵니다. 외부에서 들어온 값은 `unknown`으로 받고 필요한 내용을 직접 확인합니다.

검사 대상에는 다음이 포함됩니다.

- HTTP와 WebSocket 응답
- URL path와 쿼리
- cookie와 browser storage
- `postMessage`
- CMS와 원격 설정
- 파일 업로드와 clipboard

```ts
export function parseSearchResult(value: unknown): SearchResult {
  if (!isRecord(value) || !Array.isArray(value.projects)) {
    throw new ContractError("프로젝트 검색 응답 형식이 올바르지 않습니다.");
  }

  const projects = value.projects.map(parseProject);
  const ids = new Set(projects.map((project) => project.id));
  if (ids.size !== projects.length) {
    throw new ContractError("프로젝트 식별자가 중복되었습니다.");
  }

  return {
    projects,
    total: parseNonNegativeInteger(value.total, "total"),
    page: parsePositiveInteger(value.page, "page"),
    pageSize: parsePositiveInteger(value.pageSize, "pageSize"),
  };
}
```

검사를 통과한 값은 화면에서 사용하기 좋은 형태로 한 번 더 정리할 수 있습니다. 컴포넌트마다 API 필드 이름과 optional 값을 반복해서 해석하지 않습니다.

```text
외부 응답
→ 필요한 필드와 범위 검사
→ 애플리케이션에서 사용할 타입으로 변환
→ 화면에 필요한 값 계산
→ 컴포넌트에 전달
```

## Server Component와 Client Component를 실행 위치로 나눕니다

서버에 두기 좋은 작업은 다음과 같습니다.

- 데이터베이스, 파일과 서버 전용 환경 변수 접근
- authentication과 authorization을 반영한 첫 화면 생성
- 초기 HTML에 필요한 데이터 읽기
- 큰 라이브러리를 사용한 서버 전용 변환
- 사용자 이벤트 없이 완성할 수 있는 화면 출력

브라우저에서 실행해야 하는 작업은 다음과 같습니다.

- click, input, drag와 keyboard event
- 초점, selection, scroll과 history
- `localStorage`, Clipboard와 observer API
- 클라이언트 요청과 실시간 연결
- 사용자가 아직 저장하지 않은 입력 초안

`"use client"`는 해당 파일만 표시하는 문구가 아닙니다. 그 파일이 불러오는 module도 브라우저 bundle에 들어갈 수 있습니다. page 전체를 Client Component로 바꾸기보다 브라우저 API나 사용자 이벤트가 필요한 가장 작은 파일에서 시작합니다.

Server Component가 Client Component에 넘기는 값은 직렬화할 수 있어야 합니다. 함수, 데이터베이스 연결, class instance와 서버 전용 설정을 props로 넘기지 않습니다.

## 컴포넌트는 함께 바뀌는 이유로 나눕니다

파일 길이만 보고 컴포넌트를 분리하지 않습니다. 다음과 같이 변경 이유가 다를 때 나누는 편이 좋습니다.

- 데이터 읽기와 화면 표시가 서로 다른 이유로 바뀝니다.
- 서버 렌더링과 브라우저 이벤트가 다른 환경에서 실행됩니다.
- 같은 키보드 동작을 여러 화면에서 재사용합니다.
- 초점 이동처럼 별도로 확인해야 할 동작이 있습니다.
- 순수 상태 변경과 DOM 동작의 검사 방법이 다릅니다.

반대로 한 곳에서만 사용하는 짧은 표현을 모두 파일로 나누거나, props를 그대로 전달하는 wrapper를 여러 겹 만드는 것은 탐색 비용만 늘립니다.

각 컴포넌트가 다음 질문에 한 문장으로 답할 수 있는지 확인합니다.

```text
이 컴포넌트가 직접 저장하거나 결정하는 값은 무엇입니까?
```

## Props에는 허용할 동작을 표현합니다

여러 boolean prop은 모순되는 조합을 허용할 수 있습니다.

```tsx
<Button primary danger compact />
```

허용한 조합만 만들 수 있도록 값의 종류를 제한합니다.

```tsx
<Button tone="danger" size="compact" />
```

업무 기능을 담당하는 컴포넌트의 event 이름은 DOM event보다 사용자의 의도를 나타내는 편이 읽기 쉽습니다.

```ts
type ProjectEditorProps = {
  project: Project;
  onSave(command: RenameProjectCommand): Promise<RenameOutcome>;
  onCancel(): void;
};
```

기본 button처럼 DOM 동작 자체를 공개하는 컴포넌트에는 `onClick`이 자연스럽습니다. 제목 편집기에는 `onSave`, `onCancel`이 더 구체적입니다.

## 서버 값과 입력 초안을 분리합니다

사용자가 편집 중인 제목은 서버가 마지막으로 확정한 제목과 다릅니다.

```text
서버 제목    서버가 마지막으로 저장한 값
입력 초안    사용자가 현재 작성 중인 값
```

두 값을 하나의 상태로 사용하면 실패 복구가 모호해집니다.

- 일반 실패: 서버 제목은 요청 전 값으로 되돌리되 입력 초안은 보존합니다.
- `409 Conflict`: 서버 제목은 응답의 최신 값으로 바꾸되 입력 초안은 보존합니다.
- 성공: 서버가 반환한 제목과 새 `version`을 최종 값으로 사용하고 편집기를 닫을 수 있습니다.
- 취소: 입력 초안을 현재 서버 제목으로 되돌리고 편집기를 닫습니다.

충돌에서 입력 초안을 버리면 사용자가 작성한 내용을 잃습니다. 최신 서버 값과 사용자 입력을 함께 보여 주고 다시 판단할 수 있게 해야 합니다.

## 접근성을 상태 변경에 포함합니다

접근성은 마지막에 markup만 검사하는 작업이 아닙니다. 상태가 바뀔 때 초점과 안내 문구가 어떻게 이동하는지도 정해야 합니다.

- 검색 폼은 Enter로 제출할 수 있습니다.
- 대기, 실패와 저장 결과는 live region으로 알립니다.
- 편집기를 취소하거나 저장에 성공하면 시작 버튼으로 초점을 돌립니다.
- 일반 실패와 충돌에서는 편집기, 입력 초안과 입력칸 초점을 유지합니다.
- 오류를 색 하나로만 표현하지 않습니다.
- 반복 항목에는 안정적인 accessible name을 제공합니다.

DOM 요소를 의미에 맞게 배치했더라도 초점 이동이 끊기면 키보드 사용자는 작업을 끝내기 어렵습니다. 이 동작은 실제 브라우저 테스트로 확인합니다.

## Stable Core 완료 기준

다음 항목을 설명하고 코드로 표현할 수 있으면 실제 프로젝트 구현을 시작할 준비가 된 것입니다.

- URL, 서버 응답, 화면 상태, 입력 초안과 계산값의 저장 위치를 구분합니다.
- 서로 동시에 존재할 수 없는 상태를 discriminated union으로 제한합니다.
- 외부 JSON을 `unknown`으로 받고 필요한 필드와 범위를 검사합니다.
- Server Component와 Client Component의 실행 위치를 구분합니다.
- 서버가 확정한 값과 사용자가 편집 중인 값을 별도로 유지합니다.
- 상태가 바뀔 때 필요한 안내 문구와 초점 위치를 정합니다.

실제 프로젝트에서 비동기 요청, history 또는 낙관적 갱신이 필요해지는 시점에 [`03-nextjs-data-effects-and-concurrency.md`](03-nextjs-data-effects-and-concurrency.md)를 JIT로 읽습니다.
