# Next.js 데이터, Effect와 비동기 요청

브라우저 화면에는 여러 종류의 값이 서로 다른 시점에 도착합니다.

```text
URL
→ 현재 사용자가 선택한 검색 조건

서버가 만든 첫 화면
→ 첫 요청 시점의 데이터

클라이언트 요청
→ 사용자가 이후에 시작한 비동기 작업의 결과

입력 초안
→ 사용자가 아직 확정하지 않은 값

저장 응답
→ 서버가 최종적으로 확정한 값
```

이 값들은 같은 시점의 상태를 나타내지 않을 수 있습니다. JavaScript가 한 스레드에서 실행되더라도 `fetch`, timer, event, WebSocket 같은 비동기 작업의 **완료 순서**는 시작 순서와 다를 수 있습니다.

예를 들어 사용자가 `net`을 검색한 직후 `network`를 검색했다고 가정합니다.

```text
요청 A: net 시작
요청 B: network 시작
요청 B 완료
요청 A 완료
```

오래된 요청 A의 결과를 마지막에 그대로 반영하면 화면은 최신 사용자 입력인 `network`가 아니라 이전 입력인 `net`의 결과로 되돌아갑니다.

따라서 비동기 UI에서는 다음 두 질문을 분리해야 합니다.

```text
이 작업을 중단할 수 있는가?
이 결과를 지금 화면에 반영해도 되는가?
```

첫 번째는 `AbortController` 같은 취소 수단의 문제이고, 두 번째는 generation, request id, version 같은 **최신성 판정 기준**의 문제입니다.

이 문서는 실제 프로젝트에 URL 동기화, 클라이언트 요청, history 복원, 낙관적 갱신 또는 실시간 동기화가 필요해졌을 때 JIT로 읽습니다.

## 목표

이 문서를 읽은 뒤에는 다음 작업을 수행할 수 있어야 합니다.

- URL 쿼리의 읽기, 정규화와 쓰기를 하나의 규칙으로 관리합니다.
- `push`, `replace`, back/forward가 서로 다른 history 의미를 가진다는 점을 설명합니다.
- browser history 변화 뒤 현재 URL을 다시 읽어 화면을 복원합니다.
- 요청 취소와 generation 확인이 서로 다른 문제를 해결한다는 점을 설명합니다.
- HTTP 실패, JSON 해석 실패와 계약 검증 실패를 구분합니다.
- 오래된 응답을 화면에 반영하지 않습니다.
- 낙관적 갱신의 성공, 일반 실패와 `version` 충돌을 각각 처리합니다.
- Effect를 외부 시스템과 연결하는 코드에 사용하고 정리 함수를 둡니다.
- 실시간 연결에서도 snapshot, event sequence와 로컬 초안을 구분합니다.

## URL을 공유 가능한 상태로 사용합니다

검색어, `status`, `page`, 정렬 방식처럼 다음 동작과 함께 복원되어야 하는 값은 URL에 두는 편이 좋습니다.

- 새로 고침
- link 공유
- bookmark
- 브라우저 back/forward
- 서버 첫 렌더링
- 클라이언트 navigation

예를 들어 다음 URL은 화면 상태를 설명하는 하나의 외부 입력입니다.

```text
/projects?q=network&status=active&page=2
```

중요한 점은 URL 문자열 자체를 애플리케이션 내부 상태로 사용하지 않고, 먼저 **정규화된 query 타입**으로 바꾸는 것입니다.

```ts
type ProjectQuery = {
  q: string;
  status: "any" | "active" | "archived";
  page: number;
};
```

URL은 다음처럼 잘못되거나 모호한 값을 포함할 수 있습니다.

```text
?page=
?page=0
?page=-3
?page=abc
?status=unknown
?status=active&status=archived
```

따라서 URL을 읽는 함수가 입력 형식과 허용 범위를 결정합니다.

```ts
function parseProjectQuery(
  params: URLSearchParams,
): ProjectQuery {
  return {
    q: (params.get("q") ?? "").trim(),
    status: parseStatus(params.get("status")),
    page: parsePage(params.get("page")),
  };
}
```

## 읽기와 쓰기는 같은 정규화 규칙을 사용합니다

URL을 읽는 함수와 쓰는 함수가 서로 다른 기본값을 사용하면 URL을 한 번 왕복했을 때 의미가 바뀔 수 있습니다.

예를 들어 애플리케이션 내부 query를 URL로 바꾸고 다시 읽었을 때 다음 성질을 만족하는지 확인합니다.

```ts
const normalized = normalizeProjectQuery(query);
const params = toProjectSearchParams(normalized);
const reparsed = parseProjectQuery(params);
```

```text
parse(serialize(query)) = normalized query
```

여기서 중요한 것은 원본 입력 문자열이 완전히 같아지는 것이 아니라 **애플리케이션에서 사용하는 의미가 같아지는 것**입니다.

예를 들어 기본값 `page=1`을 URL에서 생략할 수 있습니다.

```text
내부 상태
{ q: "", status: "any", page: 1 }

URL
/projects
```

다시 `/projects`를 읽었을 때 같은 내부 상태가 만들어진다면 올바른 왕복입니다.

### 기본값을 URL에서 생략할지 결정합니다

다음 두 URL이 같은 의미라면 둘 중 하나를 canonical한 형태로 정할 수 있습니다.

```text
/projects
/projects?status=any&page=1
```

기본값을 생략하면 URL이 짧아지고 공유하기 쉽습니다. 반대로 디버깅이나 외부 연동에서 명시적인 값이 필요할 수도 있습니다.

어느 방식을 쓰든 읽기와 쓰기가 같은 규칙을 따라야 합니다.

## 이 화면이 소유한 parameter만 변경합니다

한 URL을 여러 기능이 함께 사용할 수 있습니다.

```text
/projects?q=network&page=2&panel=filters&debug=1
```

검색 UI가 `q`, `status`, `page`만 소유한다면 URL을 갱신할 때 다른 기능의 parameter를 지울지 유지할지 정해야 합니다.

일반적으로 현재 기능이 소유하지 않은 parameter를 유지해야 한다면 기존 값을 복사한 뒤 자신이 관리하는 key만 바꿉니다.

```ts
const next = new URLSearchParams(window.location.search);

next.set("q", query.q);
next.set("status", query.status);
next.set("page", String(query.page));
```

다만 제거해야 하는 parameter가 명확한 경우에는 명시적으로 삭제합니다.

```ts
if (query.page === 1) {
  next.delete("page");
}
```

URL 전체를 새로 만드는 코드가 다른 기능의 parameter를 우연히 지우지 않는지 확인합니다.

## `push`와 `replace`의 의미를 구분합니다

history를 바꿀 때는 단순히 주소 문자열을 바꾸는 것이 아니라 사용자의 뒤로 가기 경험을 결정합니다.

```text
push
→ 새로운 사용자 이동으로 기록
→ Back으로 이전 상태에 돌아갈 수 있음

replace
→ 현재 history 항목을 교체
→ Back에 새 단계가 추가되지 않음
```

예를 들어 사용자가 검색 폼을 제출한 행위가 의미 있는 상태 변경이라면 새 history 항목으로 기록할 수 있습니다.

```text
/projects
→ 검색 "network"
/projects?q=network
→ status를 active로 변경
/projects?q=network&status=active
```

이 경우 Back을 누르면 이전 검색 조건으로 돌아갈 수 있습니다.

반면 잘못된 URL을 canonical 형태로 정리하거나 현재 항목만 수정하려는 경우에는 replace가 더 적합할 수 있습니다.

어떤 동작에 push와 replace를 사용할지는 제품 요구사항입니다. 중요한 것은 **모든 URL 변경을 같은 history 동작으로 취급하지 않는 것**입니다.

## History 변경과 화면 변경을 함께 처리합니다

주소가 바뀌었다는 사실과 React 화면 상태가 바뀌었다는 사실은 항상 같은 일이 아닙니다.

직접 history API를 사용하는 코드에서는 `pushState`나 `replaceState`를 호출했다고 해서 일반적인 `popstate` 이벤트가 즉시 발생하는 것은 아닙니다. 반대로 사용자가 browser back/forward를 사용하면 현재 history 항목이 바뀌므로 **새 URL을 다시 읽어 화면을 복원해야 합니다**.

프로젝트가 Next.js router API를 사용한다면 navigation과 URL 구독은 해당 프로젝트의 router 패턴을 우선 따릅니다. 직접 History API를 사용하는 경우에는 framework와의 통합 방식을 프로젝트의 Next.js 버전에 맞게 확인합니다.

핵심 흐름은 다음과 같습니다.

```text
사용자가 검색 제출
→ 정규화된 query 생성
→ 필요한 경우 history 기록
→ 같은 query로 데이터 요청
→ 결과 표시

사용자가 Back/Forward
→ 현재 URL 다시 읽기
→ query 정규화
→ 입력 UI 복원
→ 데이터 요청
→ 결과 표시
```

### back/forward에서 history를 다시 쓰지 않습니다

`popstate`로 복원한 상태에서 다시 `pushState`를 호출하면 사용자가 뒤로 이동할 때마다 새 history 항목이 생길 수 있습니다.

```text
Back
→ popstate
→ URL 읽음
→ 다시 push
→ history가 다시 늘어남
```

이 구조에서는 사용자가 원래 위치로 돌아가기 어려워질 수 있습니다.

따라서 요청을 시작한 이유를 구분합니다.

```ts
type SearchOptions = {
  writeHistory: boolean;
};
```

예를 들면 다음과 같습니다.

```ts
void runSearch(query, {
  writeHistory: true,
});
```

사용자가 Back/Forward로 이동한 경우에는 다음과 같이 history를 다시 쓰지 않습니다.

```ts
void runSearch(query, {
  writeHistory: false,
});
```

## `popstate`에서는 URL을 다시 읽습니다

직접 History API를 사용하는 예를 보면 다음과 같습니다.

```ts
useEffect(() => {
  function handlePopState() {
    const query = parseProjectQuery(
      new URLSearchParams(
        window.location.search,
      ),
    );

    setDraftQuery(query.q);
    setDraftStatus(query.status);

    void runSearch(query, {
      writeHistory: false,
    });
  }

  window.addEventListener(
    "popstate",
    handlePopState,
  );

  return () => {
    window.removeEventListener(
      "popstate",
      handlePopState,
    );
  };
}, [runSearch]);
```

이 Effect는 browser history라는 외부 시스템을 구독합니다.

```text
setup
→ popstate listener 등록

cleanup
→ 같은 listener 제거
```

### draft와 적용된 query를 구분합니다

위 예제에서 `setDraftQuery()`를 호출하는 이유는 검색 input이 URL과 별도의 **입력 초안**을 가지고 있다고 가정했기 때문입니다.

만약 input 자체가 항상 URL의 현재 값만 표시한다면 별도 draft state가 필요하지 않을 수 있습니다.

다시 말해 다음 두 설계를 구분합니다.

```text
입력할 때마다 URL 갱신
→ URL이 입력값의 source of truth가 될 수 있음

제출할 때만 URL 갱신
→ 입력 중 draft와 적용된 URL query가 서로 다를 수 있음
```

Effect로 URL 값을 state에 복사하기 전에 두 값이 정말 다른 의미를 가지는지 확인합니다.

## Effect dependency를 임의로 생략하지 않습니다

Effect 안에서 참조하는 값이 바뀔 수 있다면 dependency와 함수 identity를 함께 확인합니다.

예를 들어 다음 Effect는 `runSearch`를 사용합니다.

```ts
useEffect(() => {
  // ...
  void runSearch(query);
}, [runSearch]);
```

`runSearch`가 매 렌더링마다 새 함수로 만들어지면 Effect도 계속 다시 연결될 수 있습니다. 반대로 dependency에서 빼 버리면 오래된 props나 state를 캡처한 함수를 계속 사용할 수 있습니다.

따라서 문제를 다음처럼 해결하지 않습니다.

```text
Effect가 자꾸 실행됨
→ dependency를 그냥 삭제
```

대신 다음을 확인합니다.

- `runSearch`가 어떤 값을 캡처해야 합니까?
- 함수가 안정된 identity를 가져야 합니까?
- Effect 안으로 필요한 로직을 옮기는 편이 더 단순합니까?
- event handler와 Effect의 책임이 섞여 있습니까?

dependency 경고는 단순 문법 문제가 아니라 **Effect가 어떤 값의 최신 버전을 사용해야 하는가**를 보여 주는 신호입니다.

## 요청 취소만으로는 늦은 결과를 막을 수 없습니다

새 검색이 시작되면 이전 요청을 중단할 수 있습니다.

```ts
activeController?.abort();

const controller =
  new AbortController();
```

`fetch`에 `signal`을 전달하면 브라우저는 가능한 범위에서 요청을 취소합니다.

```ts
await fetch(url, {
  signal: controller.signal,
});
```

그러나 `abort()`는 "이 요청과 관련된 모든 작업이 세상에서 사라진다"는 뜻이 아닙니다.

다음은 별개의 문제입니다.

- 서버가 이미 작업을 시작했을 수 있습니다.
- 서버의 데이터 변경 작업은 취소되지 않을 수 있습니다.
- 응답이 이미 도착했을 수 있습니다.
- `response.json()` 같은 후속 비동기 단계가 진행 중일 수 있습니다.
- 다른 Promise나 callback이 `AbortSignal`을 사용하지 않을 수 있습니다.
- cache나 middleware에서 이미 결과가 만들어졌을 수 있습니다.

따라서 화면에 값을 반영하기 직전에 별도의 최신성 검사가 필요합니다.

## generation으로 최신 요청을 식별합니다

generation은 요청을 시작할 때마다 증가하는 번호입니다.

```text
첫 요청
generation = 1

두 번째 요청
generation = 2

세 번째 요청
generation = 3
```

현재 generation이 `3`이라면 `1`이나 `2`의 결과는 더 이상 최신이 아닙니다.

예를 들어 요청을 시작할 때 다음 값을 얻습니다.

```ts
const request = coordinator.begin();
```

요청이 완료된 뒤 화면 상태를 바꾸기 직전에 확인합니다.

```ts
if (
  coordinator.isCurrent(
    request.generation,
  )
) {
  setState(
    completeCatalogRequest(result),
  );
}
```

이 검사는 다음 상황을 막습니다.

```text
A 시작: generation 1
B 시작: generation 2
B 완료: 2는 최신 → 반영
A 완료: 1은 최신 아님 → 폐기
```

### generation은 "결과 적용 권한"입니다

generation을 요청 번호 정도로만 생각하면 목적을 놓치기 쉽습니다.

```text
AbortController
→ 이전 작업을 가능하면 중단

generation
→ 완료된 결과가 현재 화면을 바꿀 권한이 있는지 판정
```

둘은 같은 기능이 아닙니다.

## 요청 생명주기를 한 객체에 모읍니다

컴포넌트 여러 곳에서 sequence 번호와 `AbortController`를 직접 수정하면 새 요청, 취소와 unmount 처리가 서로 어긋나기 쉽습니다.

요청 생명주기만 담당하는 작은 객체를 둘 수 있습니다.

```ts
type CoordinatedRequest = {
  generation: number;
  signal: AbortSignal;
};

function createRequestCoordinator() {
  let generation = 0;
  let controller:
    AbortController | null = null;

  return {
    begin(): CoordinatedRequest {
      controller?.abort();

      controller =
        new AbortController();

      generation += 1;

      return {
        generation,
        signal: controller.signal,
      };
    },

    isCurrent(candidate: number) {
      return candidate === generation;
    },

    cancel() {
      controller?.abort();
      controller = null;

      // 이전 모든 결과의 반영 권한도 제거합니다.
      generation += 1;
    },
  };
}
```

`cancel()`에서 generation도 증가시키는 이유는 단순히 network 작업만 취소하는 것이 아니라 **이미 진행 중이던 generation의 결과가 이후 화면을 바꾸지 못하게 하기 위해서**입니다.

## coordinator의 불변식을 테스트합니다

이 객체는 React와 DOM에 의존하지 않으므로 단위 테스트하기 쉽습니다.

확인할 내용은 다음과 같습니다.

```text
begin #1
→ generation 1
→ signal #1 생성

begin #2
→ signal #1 abort
→ generation 2
→ signal #2 생성

isCurrent(1)
→ false

isCurrent(2)
→ true

cancel()
→ signal #2 abort
→ generation 증가
→ 이전 generation은 모두 false
```

이런 순수 로직은 실제 network 지연을 만들지 않고도 검사할 수 있습니다.

## 요청 함수에서 최신성 검사를 적용합니다

검색 요청 전체 흐름은 다음처럼 구성할 수 있습니다.

```ts
async function loadProjects(
  query: ProjectQuery,
) {
  const request =
    coordinator.begin();

  try {
    const response = await fetch(
      toSearchURL(query),
      {
        signal: request.signal,
      },
    );

    if (!response.ok) {
      throw await parseHttpError(
        response,
      );
    }

    const raw: unknown =
      await response.json();

    const result =
      parseSearchResult(raw);

    if (
      !coordinator.isCurrent(
        request.generation,
      )
    ) {
      return;
    }

    setState(
      completeSearch(result),
    );
  } catch (error) {
    if (
      !coordinator.isCurrent(
        request.generation,
      )
    ) {
      return;
    }

    if (isAbortError(error)) {
      return;
    }

    setState(
      failSearch(error),
    );
  }
}
```

핵심은 성공 경로에서만 최신성을 검사하지 않는 것입니다.

오래된 요청이 실패한 뒤 현재 화면에 오류를 띄우는 것도 잘못된 결과일 수 있습니다.

```text
A 시작
B 시작
B 성공 → 최신 결과 표시
A 실패 → 오래된 오류가 화면을 덮음
```

따라서 성공과 실패 모두 **현재 generation인지 확인한 뒤** 화면 상태를 바꿉니다.

## 취소와 오류를 구분합니다

새 요청 때문에 이전 요청을 취소했다면 이것은 사용자에게 보여 줄 서비스 장애가 아닙니다.

예를 들어 사용자가 빠르게 검색어를 바꿔 이전 요청이 abort된 경우 다음 문구를 보여 줄 필요가 없습니다.

```text
"검색 요청이 실패했습니다."
```

취소는 보통 정상적인 제어 흐름입니다.

```text
사용자가 새 작업 시작
→ 이전 작업 취소
→ 이전 작업의 오류 UI 없음
```

다만 사용자가 직접 "업로드 취소"처럼 명시적인 취소 결과를 알아야 하는 기능이라면 제품 요구에 따라 별도 상태를 보여 줄 수 있습니다.

## HTTP 성공과 응답 계약 성공을 구분합니다

HTTP 상태 코드가 성공이라고 해서 애플리케이션 데이터까지 올바른 것은 아닙니다.

예를 들어 다음 응답은 HTTP 관점에서는 성공입니다.

```text
200 OK
```

그러나 본문이 다음과 같다면 애플리케이션 계약에는 맞지 않을 수 있습니다.

```json
{
  "projects": "not-an-array",
  "page": -1
}
```

따라서 요청 성공을 여러 단계로 나눕니다.

```text
network 전송 성공
      ↓
HTTP 상태 성공
      ↓
body 해석 성공
      ↓
runtime 계약 검사 성공
      ↓
현재 generation 확인
      ↓
화면 반영
```

하나라도 실패하면 정상 데이터로 반영하지 않습니다.

## 실패 종류를 구분합니다

비동기 요청의 실패를 모두 하나의 `"error"`로만 기록하면 사용자 동작과 디버깅 정보가 부족해질 수 있습니다.

| 종류 | 예 | 화면 처리 |
| --- | --- | --- |
| 의도된 취소 | 새 검색이 이전 요청을 abort | 보통 오류 문구 없음 |
| network 실패 | 연결 끊김, DNS 문제 | 재시도 안내 |
| HTTP 실패 | `401`, `403`, `404`, `503` | 상태 코드 의미에 맞는 처리 |
| JSON 해석 실패 | 잘린 JSON, 잘못된 body | 계약 또는 응답 오류 |
| 계약 검증 실패 | 필드 누락, 잘못된 타입, 중복 id | 잘못된 값을 화면에 반영하지 않음 |
| 오래된 결과 | 이전 generation의 성공/실패 | 조용히 폐기 |

`401`, `403`, `404`, `503`은 모두 HTTP 실패지만 사용자 행동은 서로 다를 수 있습니다.

```text
401
→ 다시 인증이 필요할 수 있음

403
→ 현재 사용자에게 권한이 없음

404
→ 대상이 이미 사라졌을 수 있음

503
→ 일시 장애이므로 재시도가 의미 있을 수 있음
```

구체적인 처리는 API 계약과 제품 요구사항에 따릅니다.

## JSON 해석 실패와 계약 실패도 다릅니다

다음 코드는 JSON 문법 자체가 잘못되면 예외를 던질 수 있습니다.

```ts
const raw: unknown =
  await response.json();
```

JSON 해석에는 성공했더라도 애플리케이션 타입이 잘못될 수 있습니다.

```ts
const result =
  parseSearchResult(raw);
```

따라서 다음을 구분할 수 있습니다.

```text
JSON parser 실패
→ body가 JSON 형식 자체가 아님

parseSearchResult 실패
→ JSON은 맞지만 SearchResult 계약에는 맞지 않음
```

이 차이를 로그나 telemetry에서 구분하면 서버 직렬화 문제와 API 계약 변경을 찾기 쉬워집니다.

## 마지막 정상 결과를 유지할지 결정합니다

요청 실패 시 기존 결과를 모두 지울 필요는 없습니다.

예를 들어 사용자가 이미 정상 검색 결과를 보고 있는 상태에서 새 검색이 실패했다면 다음 설계를 사용할 수 있습니다.

```text
이전 정상 결과
→ 화면에 유지

현재 검색 조건
→ 유지

오류 안내
→ 별도로 표시

재시도
→ 같은 조건으로 다시 실행
```

이 방식은 사용자가 오류 때문에 기존 정보까지 잃는 것을 막습니다.

반대로 보안상 오래된 데이터를 보여 주면 안 되는 화면이나, 새로운 조건과 이전 결과를 같이 보여 주면 오해가 생기는 화면에서는 결과를 지우는 편이 맞을 수 있습니다.

중요한 것은 실패가 발생한 뒤 어떤 값을 보존할지 **제품 동작으로 명시하는 것**입니다.

## unmount에서도 이전 결과의 권한을 제거합니다

컴포넌트가 사라진 뒤 진행 중인 요청이 완료될 수 있습니다.

Effect나 컴포넌트 수명과 coordinator가 연결되어 있다면 cleanup에서 취소합니다.

```ts
useEffect(() => {
  return () => {
    coordinator.cancel();
  };
}, [coordinator]);
```

이렇게 하면 다음 두 동작을 함께 수행할 수 있습니다.

```text
가능하면 network 작업 중단
+
기존 generation의 결과 반영 권한 제거
```

실제 coordinator를 어디에서 만들고 얼마나 오래 유지할지는 컴포넌트 수명과 기능 요구에 맞게 정합니다.

## 낙관적 갱신은 "예상값"과 "서버 확정값"을 구분합니다

**낙관적 갱신(optimistic update)**은 서버 응답을 기다리기 전에 성공할 것이라고 예상한 결과를 먼저 화면에 반영하는 방식입니다.

예를 들어 프로젝트 제목을 변경한다고 가정합니다.

```text
현재 서버 값
title = "Network"
version = 3

사용자 초안
"Networking"
```

저장 버튼을 누른 즉시 목록에 `"Networking"`을 표시할 수 있습니다.

```text
확정된 서버 값 보관
→ optimistic 값 표시
→ version=3을 포함하여 PATCH 요청
→ 응답에 따라 확정 또는 복구
```

여기서 화면에 먼저 표시한 `"Networking"`은 아직 서버가 확정한 값이 아닙니다.

따라서 최소한 다음 값을 구분해야 합니다.

```text
요청 전 서버 값
→ rollback에 필요

사용자 입력 초안
→ 실패해도 보존해야 할 수 있음

optimistic 표시값
→ 응답 전 임시 화면

서버 응답
→ 성공 시 최종 확정값
```

## 낙관적 갱신의 성공

성공했다고 해서 클라이언트가 보낸 값을 그대로 확정값으로 사용하지 않습니다.

서버가 다음 작업을 할 수 있기 때문입니다.

- 공백 제거
- 대소문자 정규화
- 새 `version` 생성
- 수정 시각 갱신
- 권한에 따른 값 보정

따라서 서버 응답을 runtime에서 검사하고 그 결과를 최종값으로 사용합니다.

```text
optimistic title
"Networking "

서버 응답
title = "Networking"
version = 4

최종 화면
title = "Networking"
version = 4
```

성공 시 다음 동작을 정할 수 있습니다.

- 서버 응답의 project로 목록을 갱신합니다.
- 새 `version`을 저장합니다.
- 입력 초안을 서버 확정값과 맞춥니다.
- 편집기를 닫습니다.
- 편집 시작 버튼 등 논리적인 위치로 focus를 돌립니다.
- 필요한 경우 live region으로 성공을 알립니다.

## 일반 실패에서는 서버 값과 초안을 따로 복구합니다

network 실패나 `503`처럼 충돌이 아닌 일반 실패가 발생했다고 가정합니다.

낙관적으로 바꾼 목록은 요청 전 서버 값으로 되돌릴 수 있습니다.

```text
목록 표시값
Networking
→ Network
```

하지만 사용자가 작성한 입력 초안까지 지우면 안 될 수 있습니다.

```text
serverTitle = "Network"
draftTitle = "Networking"
```

따라서 일반 실패는 다음처럼 처리할 수 있습니다.

```text
목록
→ 요청 전 서버 값으로 rollback

입력 초안
→ 유지

편집기
→ 열린 상태 유지

focus
→ 입력칸 유지

사용자 안내
→ 저장 실패 + 재시도 가능
```

"목록을 되돌린다"와 "사용자 입력을 버린다"는 서로 다른 동작입니다.

## `409 Conflict`는 일반 실패와 다릅니다

서버가 version 기반 concurrency control을 사용한다고 가정합니다.

```text
내가 읽은 version = 3
다른 사용자가 먼저 저장
서버 version = 4

내 요청
PATCH ... version = 3

서버
409 Conflict
```

이 경우 요청 전 값 `"Network"`도 더 이상 서버의 최신값이 아닐 수 있습니다.

따라서 단순 rollback은 잘못된 상태를 다시 보여 줄 수 있습니다.

예를 들어 충돌 응답이 최신 서버 값을 포함한다고 가정합니다.

```text
serverTitle = "배포 상태 분석"
version = 4

내 draftTitle = "릴리스 상태 분석"
```

화면은 다음 두 정보를 동시에 유지해야 할 수 있습니다.

```text
서버 최신 제목: 배포 상태 분석
내가 입력한 제목: 릴리스 상태 분석
```

충돌 처리의 핵심은 다음과 같습니다.

- 최신 서버 값을 목록에 반영합니다.
- 최신 `version`을 보관합니다.
- 사용자 입력 초안은 유지합니다.
- 충돌임을 일반 실패와 다르게 설명합니다.
- 사용자가 비교·수정·재시도할 수 있게 합니다.

### 충돌 뒤 자동 재시도가 항상 안전한 것은 아닙니다

최신 `version`만 받아서 같은 명령을 자동으로 다시 보내면 다른 사용자의 변경을 덮어쓸 수 있습니다.

따라서 다음 질문을 먼저 확인합니다.

```text
이 명령은 최신 서버 값과 독립적으로 다시 적용해도 안전한가?
사용자가 충돌 내용을 확인해야 하는가?
서버가 merge 규칙을 제공하는가?
```

자동 재시도 여부는 API의 concurrency 계약에 따라 결정합니다.

## 연속 저장 요청도 순서를 가집니다

같은 항목에 여러 저장 요청이 동시에 진행될 수 있다면 검색보다 더 복잡해질 수 있습니다.

예를 들어 다음 순서를 생각합니다.

```text
A: title = "Net" 저장
B: title = "Network" 저장

B 성공
A 성공
```

A의 응답을 마지막에 그대로 반영하면 최신 사용자 의도인 `"Network"`가 `"Net"`으로 되돌아갈 수 있습니다.

작은 편집기에서는 저장 중 추가 제출을 막아 상태 공간을 줄이는 방법이 단순합니다.

```text
saving 중
→ Save 비활성화
→ 추가 저장 명령 생성 안 함
```

여러 저장을 허용해야 한다면 다음 정보를 고려합니다.

- command id
- request generation
- 대상 entity id
- 기준 `version`
- 요청이 표현하는 사용자 의도
- 응답이 아직 최신인지 여부

검색 요청과 마찬가지로 **응답이 도착했다는 사실만으로 화면 반영 권한이 생기는 것은 아닙니다.**

## mutation을 abort할 때는 서버 효과와 구분합니다

읽기 요청에서는 abort가 주로 불필요한 결과를 줄이는 역할을 합니다. 쓰기 요청에서는 더 주의해야 합니다.

예를 들어 클라이언트가 `PATCH` 요청을 abort했다고 해서 서버가 이미 적용한 변경까지 되돌아간다는 보장은 없습니다.

```text
클라이언트
→ PATCH 전송

서버
→ 변경 저장

클라이언트
→ 연결 abort

결과
→ 클라이언트는 실패처럼 보이지만 서버에는 저장되었을 수 있음
```

따라서 중요한 mutation은 다음 문제를 별도로 고려할 수 있습니다.

- idempotency
- command id
- 재시도 정책
- 저장 결과 재조회
- version 확인

`AbortController`를 transaction rollback처럼 해석하지 않습니다.

## Effect는 외부 시스템과 연결할 때 사용합니다

Effect의 핵심 역할은 React 렌더링 결과를 **React 바깥의 시스템과 동기화**하는 것입니다.

대표적인 예는 다음과 같습니다.

- browser event listener 등록
- WebSocket 연결
- `IntersectionObserver` 연결
- imperative third-party widget 생성
- timer 등록
- document title 변경
- 컴포넌트 수명과 요청 취소 연결

반대로 props와 state만으로 즉시 계산할 수 있는 값은 Effect를 사용할 이유가 적습니다.

다음처럼 렌더링 중 계산할 수 있습니다.

```tsx
const visibleProjects =
  projects.filter((project) =>
    matches(project, query),
  );
```

이를 state에 복사하고 Effect로 맞추면 같은 의미의 값이 두 군데 생깁니다.

```tsx
useEffect(() => {
  setVisibleProjects(
    projects.filter((project) =>
      matches(project, query),
    ),
  );
}, [projects, query]);
```

이 경우 일반적으로 다음 문제가 생길 수 있습니다.

- 한 렌더링 늦게 동기화됩니다.
- dependency가 누락될 수 있습니다.
- 원본과 복사본이 어긋날 수 있습니다.
- 불필요한 추가 렌더링이 생깁니다.

## Effect마다 세 질문에 답합니다

각 Effect를 볼 때 다음 질문에 답할 수 있어야 합니다.

```text
무엇과 연결합니까?
어떤 값이 바뀌면 다시 연결합니까?
어떻게 정리합니까?
```

예를 들어 `popstate` Effect는 다음과 같습니다.

```text
연결 대상
→ window의 popstate event

다시 연결 조건
→ listener가 사용하는 함수 identity가 바뀔 때

정리
→ removeEventListener
```

WebSocket Effect라면 다음과 같습니다.

```text
연결 대상
→ 특정 room의 WebSocket

다시 연결 조건
→ room id 또는 인증 정보가 바뀔 때

정리
→ socket close + listener 제거
```

이 세 질문에 답하기 어렵다면 Effect가 여러 책임을 섞고 있을 수 있습니다.

## setup과 cleanup은 짝을 이룹니다

Effect가 외부 자원을 만들었다면 cleanup에서 해제하는 것이 기본입니다.

```ts
useEffect(() => {
  const observer =
    new IntersectionObserver(
      handleIntersection,
    );

  observer.observe(element);

  return () => {
    observer.disconnect();
  };
}, [element]);
```

대표적인 짝은 다음과 같습니다.

```text
addEventListener
↔ removeEventListener

setInterval
↔ clearInterval

observer.observe
↔ observer.disconnect / unobserve

WebSocket 생성
↔ close

request 시작
↔ 필요 시 abort / generation 무효화
```

cleanup은 컴포넌트가 완전히 사라질 때만 실행되는 것이 아니라 dependency가 바뀌어 Effect를 다시 설정하기 전에도 실행될 수 있습니다.

## 개발 환경의 반복 setup을 견뎌야 합니다

개발 환경에서는 framework와 React의 개발 검사가 setup과 cleanup을 예상보다 자주 실행하게 만들 수 있습니다.

Effect는 다음 순서가 반복되어도 외부 상태가 깨지지 않도록 작성합니다.

```text
setup
→ cleanup
→ setup
```

예를 들어 event listener가 cleanup에서 제거되지 않으면 개발 중 두 번 등록되어 event가 중복 처리되는 문제가 드러날 수 있습니다.

이것을 "개발 환경에서만 두 번 실행되니 무시"하기보다 cleanup이 올바른지 확인하는 신호로 사용합니다.

## Effect 안의 async 작업도 cleanup과 연결합니다

Effect가 비동기 작업을 시작한다면 다음 두 문제를 고려합니다.

```text
dependency가 바뀜
→ 이전 작업이 여전히 진행 중일 수 있음

component unmount
→ 작업 완료 후 화면을 바꾸면 안 될 수 있음
```

읽기 요청이라면 `AbortController`와 generation을 함께 사용할 수 있습니다.

```ts
useEffect(() => {
  const request =
    coordinator.begin();

  void loadData(request);

  return () => {
    coordinator.cancel();
  };
}, [coordinator, loadData]);
```

실제 구조에서는 새 dependency마다 coordinator 전체를 취소해야 하는지, 요청 함수 내부에서 begin/cancel을 관리할지 설계가 달라질 수 있습니다. 중요한 것은 **Effect 수명과 비동기 작업의 결과 반영 권한이 일치하도록 만드는 것**입니다.

## event handler와 Effect를 구분합니다

사용자가 버튼을 눌러 저장하는 동작은 "컴포넌트가 화면에 나타났기 때문에" 실행되는 것이 아닙니다. 특정 사용자 이벤트 때문에 실행됩니다.

따라서 다음 코드는 보통 event handler가 자연스럽습니다.

```tsx
async function handleSave() {
  await saveProject();
}
```

반면 WebSocket 연결은 특정 버튼 클릭보다 "이 컴포넌트가 이 room을 보고 있는 동안 연결되어 있어야 한다"는 수명 관계가 중요하므로 Effect가 자연스럽습니다.

```text
사용자 사건 때문에 실행
→ event handler 후보

화면이 특정 외부 시스템과 연결되어 있어야 함
→ Effect 후보
```

이 구분을 사용하면 "어떤 작업이든 비동기면 Effect"라는 오해를 피할 수 있습니다.

## 실시간 데이터에도 같은 최신성 원리를 적용합니다

HTTP 요청뿐 아니라 WebSocket, Server-Sent Events 같은 실시간 연결에서도 순서와 최신성이 중요합니다.

기본 흐름은 다음처럼 생각할 수 있습니다.

```text
연결
→ 현재 snapshot 수신
→ 이후 event 적용
→ sequence 확인
→ 누락 또는 재연결 감지
→ 새 snapshot으로 복구
```

예를 들어 서버가 event에 sequence를 붙인다고 가정합니다.

```text
snapshot sequence = 40

event 41
event 42
event 44
```

`43`이 빠졌다면 단순히 `44`를 적용해서는 현재 상태가 완전하다고 확신할 수 없습니다.

이 경우 다음과 같은 정책이 필요할 수 있습니다.

```text
sequence 누락 감지
→ 현재 event stream 신뢰 중단
→ snapshot 재조회
→ 최신 sequence부터 다시 시작
```

## snapshot과 event를 구분합니다

snapshot은 특정 시점의 전체 기준 상태입니다.

```text
projects = [...]
version = 120
```

event는 그 이후의 변화를 표현합니다.

```text
projectRenamed
projectDeleted
projectCreated
```

event만 계속 적용하면 연결이 끊긴 동안 놓친 변경을 알 수 없습니다. 따라서 실시간 기능에서는 보통 다음 세 값을 구분합니다.

```text
서버 snapshot
→ 현재 기준 상태

event sequence
→ snapshot 이후 변경의 순서

로컬 입력 초안
→ 아직 서버에 확정되지 않은 사용자 의도
```

로컬 초안을 snapshot으로 덮어쓰지 않는 정책도 별도로 필요합니다.

## reconnect는 새 데이터가 아니라 새 세션일 수 있습니다

WebSocket이 끊겼다가 다시 연결되면 이전 연결에서 마지막으로 받은 event 이후부터 완벽하게 이어진다는 보장이 없을 수 있습니다.

프로토콜이 resume token이나 sequence replay를 제공하지 않는다면 안전한 기본 전략은 새 snapshot을 받아 현재 상태를 다시 확정하는 것입니다.

```text
연결 끊김
→ reconnect
→ 최신 snapshot 획득
→ sequence 기준 갱신
→ event 적용 재개
```

정확한 방식은 서버 프로토콜 계약에 따라 달라집니다.

## 비동기 동작은 고정된 sleep 없이 테스트합니다

race condition을 테스트하기 위해 다음처럼 임의의 시간을 기다리면 테스트가 느리고 불안정해질 수 있습니다.

```ts
await sleep(500);
```

대신 요청 완료 순서를 테스트가 직접 제어할 수 있게 만듭니다.

예를 들어 두 Promise를 수동으로 완료할 수 있게 하면 다음 시나리오를 결정적으로 재현할 수 있습니다.

```text
A 요청 시작
B 요청 시작
B 완료
A 완료
→ B 결과만 남아야 함
```

검사할 대표적인 시나리오는 다음과 같습니다.

### 오래된 성공 응답

```text
A 시작
B 시작
B 성공
A 성공
→ B 결과 유지
```

### 오래된 실패 응답

```text
A 시작
B 시작
B 성공
A 실패
→ A 오류를 표시하지 않음
```

### 취소

```text
A 시작
B 시작
→ A signal abort 확인
→ A 취소 오류를 사용자 오류로 표시하지 않음
```

### unmount

```text
A 시작
component unmount
A 완료
→ 상태를 반영하지 않음
```

### 낙관적 저장 일반 실패

```text
서버 값 보관
optimistic 값 표시
요청 실패
→ 서버 값 rollback
→ draft 유지
```

### 충돌

```text
optimistic 값 표시
409 + 최신 서버 값 수신
→ 최신 서버 값 표시
→ draft 유지
→ conflict 안내
```

이런 테스트는 실제 시간보다 **완료 순서와 상태 전이**를 제어해야 합니다.

## 비동기 기능을 설계할 때 확인할 표

복잡한 요청은 구현 전에 간단한 표로 정리할 수 있습니다.

| 사건 | URL | 서버/화면 데이터 | 입력 초안 | 진행 중 요청 |
| --- | --- | --- | --- | --- |
| 검색 제출 | 새 query 기록 | 이전 결과 유지 또는 pending | 적용된 query와 맞춤 | 새 요청 시작 |
| 새 검색 시작 | 새 query | pending | 새 값 유지 | 이전 요청 abort |
| 최신 요청 성공 | 유지 | 새 결과 반영 | 유지 | 완료 |
| 오래된 요청 성공 | 유지 | 변경 없음 | 유지 | 폐기 |
| 최신 요청 실패 | 유지 | 정책에 따라 이전 결과 유지 | 유지 | 완료 |
| Back/Forward | 현재 history URL | 해당 query로 재조회 | URL에 맞춰 복원 | 새 요청 시작 |
| unmount | 해당 없음 | 더 이상 반영하지 않음 | 해당 없음 | 취소·generation 무효화 |

이 표를 작성하면 URL, 화면 결과, 입력 초안과 비동기 요청을 하나의 변수처럼 취급하는 실수를 줄일 수 있습니다.

## 적용 완료 기준

실제 프로젝트의 해당 기능에서 다음 내용을 확인합니다.

- URL을 읽고 쓰는 함수가 같은 기본값, 허용값과 정규화 규칙을 사용합니다.
- `parse(serialize(query))`가 같은 정규화된 의미를 만듭니다.
- 기본값을 URL에서 생략할지 명시했습니다.
- 현재 기능이 소유하지 않은 query parameter를 어떻게 처리할지 정했습니다.
- `push`와 `replace`를 어떤 사용자 동작에 사용할지 구분했습니다.
- 검색 제출과 back/forward 복원이 history를 서로 다르게 처리합니다.
- Back/Forward에서 현재 URL을 다시 읽고 화면 상태를 복원합니다.
- 새 읽기 요청이 이전 요청을 가능한 범위에서 abort합니다.
- 성공과 실패를 반영하기 전에 최신 generation인지 확인합니다.
- abort를 서버 작업 rollback으로 해석하지 않습니다.
- HTTP 실패, JSON 해석 실패와 계약 검증 실패를 구분합니다.
- 형식이 잘못된 성공 응답을 화면에 반영하지 않습니다.
- 오래된 성공과 오래된 실패를 모두 화면에 반영하지 않습니다.
- 일반 실패에서 어떤 서버 값과 입력 초안을 유지할지 정했습니다.
- 낙관적 성공 시 클라이언트 예상값보다 서버가 반환한 확정값을 사용합니다.
- `409 Conflict`에서 최신 서버 값과 사용자 초안을 동시에 보존할 수 있습니다.
- 연속 저장 요청을 허용할지 막을지 결정했습니다.
- Effect마다 연결 대상, dependency와 cleanup을 설명할 수 있습니다.
- 계산 가능한 값을 Effect로 다시 state에 복사하지 않습니다.
- event handler와 Effect의 책임을 구분합니다.
- 실시간 기능에서는 snapshot, event sequence와 로컬 초안을 구분합니다.
- 늦은 응답, 취소, unmount와 충돌을 고정된 `sleep` 없이 테스트로 재현합니다.

이 항목이 필요하지 않은 프로젝트라면 이 문서를 선행 학습으로 만들지 않습니다. 역량 검증 프로그램에서 관련 검증에 실패했거나 실제 기능에 URL 동기화, 비동기 race, 낙관적 갱신 또는 실시간 연결이 필요해진 경우에만 해당 절을 다시 읽습니다.
