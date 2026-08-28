# Next.js 데이터, Effect와 비동기 요청

브라우저 화면에는 URL, 서버가 만든 첫 화면, 클라이언트 요청, 사용자가 작성 중인 값과 저장 응답이 서로 다른 시점에 도착합니다. JavaScript가 한 스레드에서 실행되더라도 비동기 작업의 완료 순서는 시작 순서와 달라질 수 있습니다. 어떤 작업의 결과를 언제 반영할지 명시하지 않으면 오래된 응답이 최신 사용자 행동을 덮을 수 있습니다.

이 문서는 실제 프로젝트에 URL 동기화, 클라이언트 요청 또는 낙관적 갱신이 필요해졌을 때 JIT로 읽습니다.

## 목표

이 문서를 읽은 뒤에는 다음 작업을 수행할 수 있어야 합니다.

- URL 쿼리의 읽기와 쓰기를 하나의 규칙으로 관리합니다.
- browser history와 컴포넌트 상태를 back/forward 이동에 맞춰 복원합니다.
- 요청 취소와 generation 확인을 함께 사용합니다.
- HTTP 실패와 형식이 잘못된 성공 응답을 구분합니다.
- 낙관적 갱신의 성공, 일반 실패와 `version` 충돌을 각각 처리합니다.
- Effect를 외부 시스템과 연결하는 코드에만 사용하고 정리 함수를 둡니다.

## URL을 공유 가능한 상태로 사용합니다

검색어, `status`, `page`처럼 화면 이동과 함께 복원해야 하는 값은 URL에 두는 편이 좋습니다.

URL에 저장한 값은 다음 동작을 자연스럽게 지원합니다.

- 새로 고침 뒤 복원
- link 공유
- 브라우저의 back/forward
- 서버 첫 렌더링과 클라이언트 이동에서 같은 입력 사용

쿼리를 읽는 함수와 쓰는 함수가 다른 기본값을 사용하면 URL을 한 번 왕복했을 때 값이 달라집니다. 두 함수를 같은 module에 두고 다음 성질을 확인합니다.

```ts
const query = parseProjectQuery(new URLSearchParams(location.search));
const params = toProjectSearchParams(query);
```

```text
parse(serialize(query)) = normalized query
```

기본값은 URL에서 생략할 수 있습니다. 다만 다시 읽었을 때 같은 정규화 결과가 나와야 합니다.

여러 widget이 하나의 URL을 함께 사용한다면 이 화면이 소유한 parameter만 바꾸고 다른 parameter는 유지할지 결정해야 합니다.

## History 변경과 화면 변경을 함께 처리합니다

`history.pushState`와 `replaceState`는 주소를 바꾸지만 React 상태를 자동으로 바꾸지 않습니다. 반대로 사용자가 back/forward를 누르면 `popstate`가 발생하므로 현재 URL을 다시 읽고 필요한 데이터를 요청해야 합니다.

```ts
useEffect(() => {
  function handlePopState() {
    const query = parseProjectQuery(
      new URLSearchParams(window.location.search),
    );
    setDraftQuery(query.q);
    setDraftStatus(query.status);
    void runSearch(query, { writeHistory: false });
  }

  window.addEventListener("popstate", handlePopState);
  return () => window.removeEventListener("popstate", handlePopState);
}, [runSearch]);
```

검색 폼을 제출한 경우에는 URL을 기록하지만, `popstate`로 시작한 검색은 history를 다시 쓰지 않습니다. 이를 구분하지 않으면 뒤로 이동할 때 새 history 항목이 생겨 사용자가 원래 위치로 돌아가지 못할 수 있습니다.

Effect dependency에서 `runSearch`를 임의로 빼지 않습니다. 함수가 바뀌는데 Effect가 이전 함수를 계속 참조하면 오래된 props나 state를 사용할 수 있습니다.

## 요청 취소만으로는 늦은 결과를 막을 수 없습니다

새 검색이 시작되면 이전 요청을 중단할 수 있습니다.

```ts
activeController?.abort();
const controller = new AbortController();
```

그러나 abort는 다음을 보장하지 않습니다.

- 서버에서 이미 시작한 작업이 되돌아갑니다.
- 모든 Promise와 callback이 abort를 따릅니다.
- 응답을 해석하는 중에 취소된 결과가 절대 도착하지 않습니다.
- cache나 중간 서버가 이미 전달한 응답이 사라집니다.

따라서 응답을 화면에 반영하기 직전에 이 요청이 여전히 최신인지 확인해야 합니다.

```ts
const request = coordinator.begin();
const response = await fetch(url, { signal: request.signal });
const result = parseSearchResult(await response.json());

if (coordinator.isCurrent(request.generation)) {
  setState(completeCatalogRequest(result));
}
```

`AbortController`는 불필요한 전송과 작업을 줄입니다. generation 확인은 이미 도착한 늦은 결과가 화면을 바꾸지 못하게 합니다. 두 방법은 서로 다른 문제를 막으므로 함께 사용합니다.

## 요청 생명주기를 한 객체에 모읍니다

컴포넌트 여러 곳에서 sequence와 `AbortController`를 직접 바꾸면 새 요청, 취소와 unmount 처리가 서로 어긋나기 쉽습니다. 다음처럼 요청 생명주기만 관리하는 객체를 둘 수 있습니다.

```ts
type CoordinatedRequest = {
  generation: number;
  signal: AbortSignal;
};

function createRequestCoordinator() {
  let generation = 0;
  let controller: AbortController | null = null;

  return {
    begin(): CoordinatedRequest {
      controller?.abort();
      controller = new AbortController();
      generation += 1;
      return { generation, signal: controller.signal };
    },
    isCurrent(candidate: number) {
      return candidate === generation;
    },
    cancel() {
      controller?.abort();
      controller = null;
      generation += 1;
    },
  };
}
```

이 객체는 React에 의존하지 않으므로 DOM 없이 다음 내용을 검사할 수 있습니다.

- 두 번째 `begin`이 첫 signal을 abort합니다.
- 첫 generation은 더 이상 최신이 아닙니다.
- `cancel` 뒤 기존 generation을 거절합니다.
- 다음 `begin`은 새 signal과 generation을 만듭니다.

## HTTP 성공과 응답 형식 성공을 구분합니다

`response.ok`가 `true`여도 JSON 본문이 애플리케이션에서 기대한 형식과 다를 수 있습니다.

```ts
const raw: unknown = await response.json();
const result = parseSearchResult(raw);
```

실패 종류에 따라 화면에서 취할 동작도 달라집니다.

| 실패 종류 | 예 | 처리 방법 |
| --- | --- | --- |
| 사용자 동작으로 인한 취소 | 새 검색이 이전 요청을 중단 | 오류 문구를 표시하지 않음 |
| HTTP 실패 | `503`, `401`, `403` | 마지막 정상 결과와 다음 행동을 유지 |
| JSON 해석 실패 | 잘린 응답 | 응답 형식 오류로 처리 |
| 필드 검사 실패 | 필드 누락, 중복 id | 잘못된 값을 화면에 반영하지 않음 |
| 늦은 결과 | 이전 generation의 응답 | 안내 없이 폐기 |

형식이 잘못된 본문을 타입 단언으로 통과시키면 더 먼 컴포넌트에서 오류가 발생하고 원인을 찾기 어려워집니다. 응답을 받은 곳에서 즉시 검사합니다.

## 낙관적 갱신의 확정 시점을 정합니다

제목 변경처럼 되돌릴 수 있고 예상 결과가 분명한 작업은 서버 응답 전에 화면에 먼저 표시할 수 있습니다.

```text
현재 서버 값과 입력 초안 보관
→ 예상 제목을 목록에 먼저 표시
→ 현재 version을 포함해 PATCH 요청
→ 응답 종류에 따라 확정 또는 복구
```

### 성공

- 응답의 project를 실행 중에 검사합니다.
- 서버가 보정한 title과 새 `version`을 최종 값으로 사용합니다.
- 편집기를 닫고 시작 버튼으로 초점을 돌립니다.
- live region으로 성공을 알립니다.

### 일반 실패

- 목록의 project를 요청 전 서버 값으로 되돌립니다.
- 사용자가 작성한 입력 초안은 유지합니다.
- 편집기를 열어 두고 입력칸 초점을 유지합니다.
- 다시 시도할 수 있다는 사실을 알립니다.

### `409 Conflict`

- 응답에 포함된 최신 서버 값을 목록에 반영합니다.
- 사용자가 작성한 입력 초안은 유지합니다.
- 최신 서버 값과 입력 초안을 함께 보여 줍니다.
- 일반 네트워크 실패와 다른 문구로 설명합니다.

```text
서버 최신 제목: 배포 상태 분석
내가 입력한 제목: 릴리스 상태 분석
```

충돌 응답에서 요청 전 값으로 단순히 되돌리면 다른 사용자가 이미 저장한 최신 값을 다시 숨기게 됩니다.

## 연속 저장 요청도 고려합니다

한 항목에 저장 요청을 여러 개 보낼 수 있다면 다음 내용을 정해야 합니다.

- 저장 중 입력과 제출을 막습니까?
- 새 저장 요청이 이전 저장 요청을 취소할 수 있습니까?
- 서버 명령을 같은 내용으로 다시 보내도 안전합니까?
- 여러 낙관적 변경을 어떤 순서로 되돌립니까?
- 응답이 현재 입력 초안보다 오래된 사용자 의도인지 어떻게 판단합니까?

작은 편집기에서는 저장 중 추가 제출을 막아 문제를 제한할 수 있습니다. 복잡한 편집기에서는 명령 id와 기준 `version`을 함께 관리하는 편이 안전합니다.

## Effect는 외부 시스템과 연결할 때 사용합니다

props와 state로 바로 계산할 수 있는 값을 Effect에서 다시 저장하지 않습니다.

```tsx
const visibleProjects = projects.filter((project) =>
  matches(project, query),
);
```

계산값을 Effect로 복사하면 한 번 늦게 갱신되고 같은 의미의 값이 두 곳에 생깁니다.

Effect가 필요한 대표적인 대상은 다음과 같습니다.

- browser history event 구독
- unmount 시 요청 취소
- WebSocket과 observer 연결
- imperative widget 생성과 정리
- document title 같은 브라우저 외부 상태

각 Effect에서는 다음 세 가지를 확인할 수 있어야 합니다.

```text
무엇과 연결합니까?
어떤 값이 바뀌면 다시 연결합니까?
어떻게 정리합니까?
```

개발 환경에서 setup → cleanup → setup이 반복되어도 같은 결과가 나와야 합니다.

## 실시간 데이터에 적용할 때

HTTP 요청뿐 아니라 WebSocket에도 같은 원리를 적용할 수 있습니다.

```text
연결
→ 현재 version의 snapshot 수신
→ 이후 event 적용
→ sequence 누락 또는 재연결 감지
→ 새 snapshot으로 현재 상태 갱신
```

event만 계속 이어 붙이면 연결이 끊긴 동안 놓친 변경을 알 수 없습니다. 서버 snapshot, event sequence와 로컬 입력 초안을 서로 다른 값으로 관리해야 합니다.

## 적용 완료 기준

실제 프로젝트의 해당 기능에서 다음 내용을 확인합니다.

- URL을 읽고 쓰는 함수가 같은 기본값과 허용 범위를 사용합니다.
- 검색 제출과 back/forward 이동이 history를 서로 다르게 처리합니다.
- 새 요청이 이전 요청을 abort합니다.
- 응답을 반영하기 전에 최신 generation인지 확인합니다.
- 형식이 잘못된 성공 응답을 화면에 반영하지 않습니다.
- 일반 실패와 `409 Conflict`에서 서버 값과 입력 초안을 알맞게 유지합니다.
- Effect마다 연결 대상, dependency와 정리 함수가 보입니다.
- 늦은 응답과 충돌을 고정된 sleep 없이 테스트로 재현합니다.

이 항목이 필요하지 않은 프로젝트라면 이 문서를 선행 학습으로 만들지 않습니다. 역량 검증 프로그램에서 관련 검증에 실패한 경우에만 해당 절을 다시 읽습니다.
