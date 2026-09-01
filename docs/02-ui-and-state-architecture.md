# UI 상태와 값의 소유 위치

React 화면은 컴포넌트 트리만으로 설명할 수 없습니다. 화면에 나타나는 각 값이 **무엇을 의미하는지**, **어디가 그 값의 기준(source of truth)인지**, **어떤 이벤트가 값을 바꾸는지**, **다른 값에서 계산할 수 있는지**를 함께 정해야 합니다.

여기서 **값의 소유 위치**란 단순히 변수를 어느 파일에 선언할지를 뜻하지 않습니다. 어떤 저장소가 그 값의 최종 기준인지 정하는 것입니다. 같은 의미의 값을 URL, 서버 응답과 여러 `useState`에 동시에 독립적으로 저장하면 서로 다른 시점의 값이 생길 수 있고, 이를 다시 맞추기 위한 동기화 코드가 필요해집니다.

예를 들어 검색 조건 `q=network`가 URL에도 있고 `useState`에도 있다면 다음 질문이 생깁니다.

```text
URL은 network인데 useState는 net이면 어느 쪽이 맞습니까?
뒤로 이동하면 useState도 자동으로 바뀌어야 합니까?
새로 고침하면 어떤 값을 복원해야 합니까?
```

이런 문제를 피하려면 먼저 값의 종류와 기준 위치를 정합니다.

이 문서는 특정 상태 관리 라이브러리가 아니라 대부분의 React·Next.js 프로젝트에서 반복해서 필요한 상태 설계 판단을 다룹니다.

## 목표

이 문서를 읽은 뒤에는 다음 작업을 수행할 수 있어야 합니다.

- URL 상태, 서버 상태, 화면 상태, 입력 초안, 지속 설정과 계산값을 구분합니다.
- 각 값의 source of truth를 정하고 같은 의미의 상태를 불필요하게 복제하지 않습니다.
- 서로 동시에 존재할 수 없는 화면 상태를 discriminated union으로 표현합니다.
- 외부 값을 `unknown`으로 받고 필요한 구조와 의미 제약을 검사합니다.
- Server Component와 Client Component에 코드를 배치할 기준을 설명합니다.
- 서버가 확정한 값과 사용자가 편집 중인 초안을 별도로 유지합니다.
- 컴포넌트 props에 내부 저장 방식보다 허용할 동작과 도메인 의미를 표현합니다.
- 상태 변경과 함께 focus, live region 등 접근성 동작을 설계합니다.

## 값의 종류를 먼저 구분합니다

모든 상태를 `useState`에 넣는 것이 React 상태 설계는 아닙니다. 값이 어디에서 왔고 어떤 수명을 가지는지에 따라 적절한 소유 위치가 달라집니다.

| 값의 종류 | 예 | 주로 저장할 위치 | 특징 |
| --- | --- | --- | --- |
| URL 상태 | 검색어, status, page, 선택한 tab | URL과 browser history | 공유·새로 고침·뒤로/앞으로 이동과 관련됨 |
| 서버 상태 | 프로젝트 목록, 저장된 제목, `version`, 권한 | 서버 저장소와 요청 결과 | 서버가 최종 값을 결정함 |
| 화면 상태 | 메뉴 열림, dialog 열림, 현재 선택 항목 | 가장 가까운 Client Component | 현재 화면 상호작용에만 필요한 경우가 많음 |
| 입력 초안 | 아직 저장하지 않은 제목, 작성 중인 설명 | 해당 편집 컴포넌트 | 서버 값과 달라도 정상임 |
| 지속 설정 | 언어, theme, 열 표시 설정 | 서버 사용자 설정 또는 browser storage | 세션이나 기기 간 유지 요구에 따라 위치가 달라짐 |
| 계산값 | 필터 결과 수, 전체 가격, 제출 가능 여부 | 가능하면 렌더링 중 계산 | 다른 상태로부터 결정 가능함 |

이 표의 "주로"는 절대 규칙이 아닙니다. 같은 개념도 제품 요구에 따라 위치가 달라질 수 있습니다.

예를 들어 theme은 다음 중 어느 것이 요구사항인지에 따라 저장 위치가 달라집니다.

```text
현재 브라우저에서만 기억
→ localStorage 등이 적합할 수 있음

로그인한 사용자가 모든 기기에서 동일하게 사용
→ 서버 사용자 설정이 기준이 되어야 함
```

따라서 저장 기술부터 고르지 말고 먼저 **어떤 동작을 복원해야 하는지**를 정합니다.

## source of truth를 하나씩 정합니다

같은 의미의 값을 여러 곳에 독립적으로 저장하면 동기화 문제가 생깁니다.

예를 들어 URL이 검색 조건의 기준이라면 다음 형태가 단순합니다.

```text
URL searchParams
      ↓
정규화된 검색 조건
      ↓
검색 결과 + 입력 UI
```

반대로 URL 값을 읽어 별도의 `useState`에 복사하고 두 값을 계속 맞추려 하면 다음과 같은 코드가 생기기 쉽습니다.

```tsx
const [query, setQuery] = useState(searchParams.get("q") ?? "");

useEffect(() => {
  setQuery(searchParams.get("q") ?? "");
}, [searchParams]);
```

이 코드가 항상 잘못된 것은 아니지만, `query`가 단순히 URL 값을 복사한 것뿐이라면 두 상태를 유지할 이유를 먼저 의심해야 합니다.

다만 **사용자가 아직 확정하지 않은 입력 초안**은 예외가 될 수 있습니다.

예를 들어 검색 폼에서 글자를 입력할 때마다 URL을 바꾸지 않고 "검색"을 눌렀을 때만 적용한다면 다음 두 값은 의미가 다릅니다.

```text
URL q
→ 마지막으로 적용된 검색 조건

inputDraft
→ 사용자가 현재 입력 중인 아직 적용되지 않은 문자열
```

이 경우 둘을 별도 상태로 두는 것이 올바릅니다. 중요한 것은 같은 문자열처럼 보여도 **의미와 수명**이 다르면 서로 다른 상태라는 점입니다.

## 저장 위치를 정할 때 사용할 질문

값마다 다음 질문을 순서대로 확인합니다.

1. 새로 고침 뒤에도 남아야 합니까?
2. link로 공유했을 때 같은 상태가 재현되어야 합니까?
3. 뒤로/앞으로 이동할 때 이전 상태가 복원되어야 합니까?
4. 서버가 최종 값을 결정합니까?
5. 사용자가 저장 또는 제출 전까지 자유롭게 수정해야 합니까?
6. 다른 상태에서 항상 다시 계산할 수 있습니까?
7. 여러 컴포넌트가 이 값을 바꿔야 합니까?
8. 이 값을 가장 가까이에서 필요로 하는 공통 조상은 어디입니까?

대체로 다음처럼 판단할 수 있습니다.

```text
공유·history 복원이 중요
→ URL 후보

서버가 최종 권한을 가짐
→ 서버 상태

현재 상호작용에만 필요
→ 로컬 Client Component 상태

저장 전 사용자의 임시 입력
→ 입력 초안

다른 값에서 항상 계산 가능
→ 별도 상태로 저장하지 않고 계산
```

## 계산할 수 있는 값은 가능하면 저장하지 않습니다

이미 가진 값에서 결정적으로 계산할 수 있는 값을 또 상태로 저장하면 불일치 가능성이 생깁니다.

다음 예를 봅니다.

```tsx
const [items, setItems] = useState<Item[]>([]);
const [itemCount, setItemCount] = useState(0);
```

`itemCount`가 언제나 `items.length`와 같아야 한다면 두 상태를 맞추는 코드가 필요합니다.

```tsx
setItems(nextItems);
setItemCount(nextItems.length);
```

둘 중 하나만 갱신되면 상태가 어긋납니다. 이 경우 다음처럼 계산하는 편이 단순합니다.

```tsx
const itemCount = items.length;
```

같은 원칙은 다음 값에도 적용됩니다.

```text
firstName + lastName → fullName
items → totalPrice
required fields → canSubmit
selectedIds + items → selectedItems
```

계산 비용이 크다면 memoization을 검토할 수 있지만, **성능 최적화 여부와 상태의 기준 위치는 별개의 문제**입니다. 먼저 파생값인지 판단하고, 실제 성능 문제가 있을 때 최적화를 고려합니다.

## 상태는 가능한 가장 가까운 곳에서 소유합니다

둘 이상의 컴포넌트가 같은 값을 읽거나 바꿔야 한다면 그 값은 보통 둘의 가장 가까운 공통 조상으로 올립니다.

```text
ProjectEditor
├─ TitleInput
└─ SaveButton
```

`TitleInput`과 `SaveButton`이 모두 같은 입력 초안과 제출 가능 여부를 알아야 한다면 `ProjectEditor`가 초안을 소유할 수 있습니다.

하지만 프로젝트 전체가 쓰지 않는 값을 무조건 최상위 provider나 전역 store로 올릴 필요는 없습니다. 상태 범위를 지나치게 넓히면 다음 문제가 생깁니다.

- 누가 값을 변경하는지 찾기 어려워집니다.
- 관련 없는 화면도 같은 상태의 영향을 받습니다.
- 상태 초기화 시점을 판단하기 어려워집니다.
- 테스트할 때 더 많은 전역 환경을 준비해야 합니다.

전역 상태는 "편해서"가 아니라 **여러 멀리 떨어진 소비자가 같은 장기 상태를 실제로 공유해야 하는가**를 기준으로 결정합니다.

## 동시에 존재할 수 없는 상태를 타입으로 막습니다

다음처럼 여러 boolean과 nullable 값을 따로 저장하면 의미 없는 조합이 생길 수 있습니다.

```ts
const [pending, setPending] = useState(false);
const [error, setError] = useState<string | null>(null);
const [projects, setProjects] = useState<Project[]>([]);
```

이 표현만으로는 다음 조합의 의미가 명확하지 않습니다.

```text
pending = true
error = "Network error"
projects = []
```

현재 요청 중이면서 동시에 오류가 난 상태입니까? 오류는 이전 요청의 것입니까? 목록이 비어 있는 것은 정상 빈 결과입니까?

이런 문제는 boolean 자체가 나빠서가 아니라, **서로 배타적인 상태를 서로 독립적인 변수로 표현했기 때문**입니다.

### discriminated union으로 불변식을 표현합니다

서로 동시에 존재할 수 없는 경우는 하나의 구분 필드를 가진 union으로 표현할 수 있습니다.

```ts
type CatalogState =
  | { status: "ready"; result: SearchResult }
  | { status: "empty"; result: SearchResult }
  | { status: "pending"; previous: SearchResult }
  | { status: "error"; message: string; previous: SearchResult };
```

`status`처럼 union의 각 경우를 구분하는 필드를 **discriminant**라고 부릅니다.

이 타입은 다음 규칙을 타입 수준에서 표현합니다.

- `"ready"`와 `"empty"`에는 정상 응답이 존재합니다.
- `"pending"`에는 표시할 마지막 정상 결과가 존재합니다.
- `"error"`에는 오류 메시지와 마지막 정상 결과가 존재합니다.
- 한 상태가 동시에 `"pending"`과 `"error"`일 수 없습니다.

이 설계는 "새 검색 중에는 마지막 정상 결과를 유지한다"는 제품 결정을 포함합니다. 모든 애플리케이션이 반드시 이렇게 해야 하는 것은 아닙니다.

첫 요청처럼 이전 결과가 없을 수도 있다면 타입도 그 사실을 표현해야 합니다.

```ts
type CatalogState =
  | { status: "initial" }
  | { status: "pending"; previous: SearchResult | null }
  | { status: "ready"; result: SearchResult }
  | { status: "empty"; result: SearchResult }
  | { status: "error"; message: string; previous: SearchResult | null };
```

중요한 것은 실제로 가능한 상태만 표현하고, 불가능한 조합을 타입에서 제거하는 것입니다.

## 상태 전이를 명시적으로 만듭니다

상태의 종류만 정의하고 어떤 전이가 가능한지 정하지 않으면 여전히 코드가 흩어질 수 있습니다.

예를 들어 검색 기능의 상태 전이는 다음처럼 생각할 수 있습니다.

```text
initial
  └─ search → pending

ready
  └─ search → pending(previous = current result)

empty
  └─ search → pending(previous = current result)

pending
  ├─ success with items → ready
  ├─ success with no items → empty
  └─ failure → error

error
  └─ retry/search → pending
```

이 흐름을 순수 함수로 분리하면 DOM 없이 검사할 수 있습니다.

```ts
function completeSearch(result: SearchResult): CatalogState {
  return result.projects.length === 0
    ? { status: "empty", result }
    : { status: "ready", result };
}
```

더 복잡한 경우에는 event와 reducer 형태로 표현할 수도 있습니다.

```ts
type CatalogEvent =
  | { type: "searchStarted" }
  | { type: "searchSucceeded"; result: SearchResult }
  | { type: "searchFailed"; message: string };
```

`useReducer`를 반드시 써야 한다는 뜻은 아닙니다. 핵심은 **가능한 상태와 상태를 바꾸는 사건을 명확히 구분하는 것**입니다.

## 외부 값을 타입 단언만으로 믿지 않습니다

TypeScript 타입은 컴파일 시점에 개발자가 작성한 코드의 타입 관계를 검사합니다. 실행 중에 서버, URL, storage 등에서 들어오는 값의 실제 모양까지 확인하지는 않습니다.

다음 코드는 런타임 검증을 하지 않습니다.

```ts
const result = (await response.json()) as SearchResult;
```

`as SearchResult`는 "이 값을 `SearchResult`로 취급하겠다"는 TypeScript 단언일 뿐입니다. 실제 JSON에 필드가 없거나 잘못된 타입이어도 실행 중 자동으로 거부되지 않습니다.

외부 경계에서 들어오는 값은 먼저 `unknown`으로 취급하고 필요한 구조와 의미를 확인합니다.

검사 대상에는 다음이 포함됩니다.

- HTTP와 WebSocket 응답
- URL path와 query parameter
- cookie와 browser storage
- `postMessage`
- CMS와 원격 설정
- 파일 업로드와 clipboard
- 사용자가 직접 입력한 값
- 외부 SDK나 third-party script가 반환하는 값

### 구조 검사와 의미 검사를 구분합니다

응답에 필드가 존재한다고 해서 애플리케이션에서 유효한 값이라는 뜻은 아닙니다.

예를 들어 다음 JSON은 구조상 숫자 필드를 가지고 있습니다.

```json
{
  "projects": [],
  "total": -1,
  "page": 0,
  "pageSize": 20
}
```

하지만 애플리케이션 계약이 다음과 같다면 잘못된 값입니다.

```text
total ≥ 0
page ≥ 1
pageSize ≥ 1
```

따라서 parser는 두 종류를 모두 검사해야 할 수 있습니다.

```text
구조 검사
→ object인가?
→ projects가 array인가?
→ id가 string인가?

의미 검사
→ page가 양의 정수인가?
→ id가 중복되지 않는가?
→ status가 허용 목록에 있는가?
```

예를 들어 다음처럼 작성할 수 있습니다.

```ts
export function parseSearchResult(value: unknown): SearchResult {
  if (!isRecord(value) || !Array.isArray(value.projects)) {
    throw new ContractError(
      "프로젝트 검색 응답 형식이 올바르지 않습니다.",
    );
  }

  const projects = value.projects.map(parseProject);

  const ids = new Set(
    projects.map((project) => project.id),
  );

  if (ids.size !== projects.length) {
    throw new ContractError(
      "프로젝트 식별자가 중복되었습니다.",
    );
  }

  return {
    projects,
    total: parseNonNegativeInteger(
      value.total,
      "total",
    ),
    page: parsePositiveInteger(
      value.page,
      "page",
    ),
    pageSize: parsePositiveInteger(
      value.pageSize,
      "pageSize",
    ),
  };
}
```

이 parser를 통과한 뒤에야 나머지 애플리케이션 코드가 `SearchResult`의 불변식을 신뢰할 수 있습니다.

## 모든 외부 값을 같은 강도로 검사할 필요는 없습니다

런타임 검증에는 비용과 코드가 필요하므로 경계를 기준으로 우선순위를 정합니다.

일반적으로 다음처럼 신뢰 수준을 생각할 수 있습니다.

```text
브라우저 URL / 사용자 입력
→ 신뢰하지 않음

외부 API / third-party SDK
→ 신뢰하지 않음

자신이 운영하는 서버의 HTTP 응답
→ 계약 위반 가능성을 고려해 경계에서 검사할 가치가 큼

이미 검증된 내부 함수의 반환값
→ 같은 검사를 매 단계 반복할 필요는 없음
```

중요한 원칙은 **검증을 애플리케이션 내부 곳곳에 흩뿌리지 않고 신뢰 경계에서 한 번 수행한 뒤 내부 타입으로 변환하는 것**입니다.

```text
외부 값: unknown
      ↓
구조·범위·허용값 검사
      ↓
애플리케이션 타입
      ↓
도메인 로직
      ↓
화면에 필요한 계산값
```

스키마 라이브러리를 사용할 수도 있고 직접 parser를 작성할 수도 있습니다. 도구보다 중요한 것은 경계와 계약이 명시되어 있는지입니다.

## 검사 후 화면에 맞는 형태로 변환합니다

외부 API 타입을 UI 전체로 그대로 전파하면 컴포넌트마다 optional 필드와 외부 naming 규칙을 알아야 할 수 있습니다.

예를 들어 외부 응답이 다음과 같다고 가정합니다.

```ts
type ApiProject = {
  project_id: string;
  display_name?: string | null;
};
```

UI에서 항상 `id`와 표시 가능한 `name`이 필요하다면 경계에서 변환할 수 있습니다.

```ts
type Project = {
  id: string;
  name: string;
};

function toProject(value: ApiProject): Project {
  return {
    id: value.project_id,
    name: value.display_name ?? "(이름 없음)",
  };
}
```

이렇게 하면 컴포넌트가 API의 세부 표현보다 애플리케이션이 보장하는 타입을 사용하게 됩니다.

## Server Component와 Client Component를 실행 위치로 나눕니다

Server Component와 Client Component의 구분은 "데이터 컴포넌트"와 "UI 컴포넌트"의 구분이 아닙니다. 둘 다 UI를 렌더링할 수 있습니다. 차이는 **어디에서 실행할 코드인가**와 **어떤 기능이 필요한가**에 있습니다.

서버에 두기 좋은 작업은 다음과 같습니다.

- 데이터베이스, 파일과 서버 전용 환경 변수 접근
- authentication과 authorization을 반영한 첫 화면 생성
- 초기 HTML에 필요한 데이터 읽기
- 서버 내부 서비스 호출
- 큰 라이브러리를 사용한 서버 전용 변환
- 사용자 이벤트 없이 완성할 수 있는 UI 렌더링

브라우저에서 실행해야 하는 작업은 다음과 같습니다.

- click, input, drag와 keyboard event 처리
- focus, selection, scroll과 history 조작
- `localStorage`, Clipboard, observer 같은 browser API
- 사용자 입력 초안 유지
- 브라우저에서 관리해야 하는 실시간 상호작용
- event handler와 local interactive state

### `"use client"`는 경계를 만듭니다

`"use client"`는 단순한 주석이 아닙니다. Client Component 진입점을 선언합니다.

```tsx
"use client";

export function ProjectSearch() {
  // browser event와 local state 사용 가능
}
```

이 파일이 import하는 module은 클라이언트 쪽 module graph에 포함될 수 있으므로 다음 값을 가져오지 않도록 주의합니다.

- 서버 전용 환경 변수
- 데이터베이스 연결
- Node.js 전용 module에 의존하는 서버 코드
- 브라우저에 노출되면 안 되는 비밀 설정

page 전체를 Client Component로 바꾸기보다 브라우저 API나 사용자 이벤트가 필요한 가장 작은 경계에서 `"use client"`를 시작하는 편이 좋습니다.

```text
Server Component
├─ 정적 제목
├─ 서버에서 읽은 데이터
└─ Client Component
   ├─ 입력 초안
   ├─ 클릭 처리
   └─ focus 관리
```

이 구조에서는 상위 화면 대부분을 서버에서 구성하면서 상호작용이 필요한 부분만 브라우저 코드로 만들 수 있습니다.

## Server Component에서 Client Component로 넘기는 값

서버와 클라이언트 경계를 넘는 props는 해당 렌더링 경계에서 전달할 수 있는 값이어야 합니다. 일반적으로 화면 데이터는 문자열, 숫자, boolean, 배열과 plain object처럼 전송 가능한 형태로 구성합니다.

다음처럼 서버 자원 자체를 넘기지 않습니다.

```text
데이터베이스 연결
파일 descriptor
서버 전용 service instance
비밀 설정 object
```

대신 그 자원을 사용해 서버에서 결과를 만들고 필요한 데이터만 전달합니다.

```tsx
const project = await projectRepository.findById(id);

return <ProjectEditor project={project} />;
```

함수 전달도 일반적인 Client Component prop과 같은 방식으로 단순화해서 생각하면 오해할 수 있습니다. 서버와 클라이언트 사이에는 framework가 특별히 지원하는 호출 방식이 있을 수 있으므로 프로젝트가 사용하는 Next.js 버전과 패턴을 따릅니다. 핵심은 **임의의 서버 runtime 객체를 브라우저 prop처럼 넘긴다고 생각하지 않는 것**입니다.

## 컴포넌트는 함께 바뀌는 이유로 나눕니다

파일 길이만 보고 컴포넌트를 분리하지 않습니다. 다음처럼 책임과 변경 이유가 다를 때 경계를 만드는 편이 좋습니다.

- 데이터 읽기와 화면 표시가 서로 다른 이유로 바뀝니다.
- 서버 렌더링과 브라우저 이벤트가 다른 환경에서 실행됩니다.
- 같은 키보드 동작을 여러 화면에서 재사용합니다.
- focus 이동처럼 별도로 확인해야 할 동작이 있습니다.
- 순수 상태 변경과 DOM 동작의 검사 방법이 다릅니다.
- 반복되는 UI 단위가 독립된 props 계약을 가집니다.

반대로 한 곳에서만 사용하는 짧은 표현을 모두 파일로 나누거나, props를 그대로 전달하는 wrapper를 여러 겹 만드는 것은 탐색 비용만 늘릴 수 있습니다.

각 컴포넌트가 다음 질문에 한 문장으로 답할 수 있는지 확인합니다.

```text
이 컴포넌트가 직접 소유하거나 결정하는 것은 무엇입니까?
```

예를 들면 다음처럼 답할 수 있습니다.

```text
ProjectCatalog
→ 현재 검색 결과를 표시하고 검색 상태별 화면을 결정합니다.

ProjectEditor
→ 저장 전 제목 초안과 편집 상태를 소유합니다.

ProjectRow
→ 하나의 프로젝트 정보를 표시하지만 서버 데이터를 직접 저장하지 않습니다.
```

책임을 설명하기 어려우면 컴포넌트가 너무 많은 일을 하거나, 반대로 의미 없이 나뉘어 있을 가능성이 있습니다.

## Props에는 허용할 값과 동작을 표현합니다

여러 boolean prop은 모순되는 조합을 만들 수 있습니다.

```tsx
<Button primary danger compact />
```

`primary`와 `danger`를 동시에 주면 어떤 스타일이 우선인지 별도 규칙이 필요합니다.

허용된 선택지를 하나의 값으로 제한하면 불가능한 조합을 줄일 수 있습니다.

```tsx
<Button tone="danger" size="compact" />
```

도메인 컴포넌트의 callback도 내부 구현보다 사용자의 의도를 나타내는 이름이 읽기 쉽습니다.

```ts
type ProjectEditorProps = {
  project: Project;
  onSave(
    command: RenameProjectCommand,
  ): Promise<RenameOutcome>;
  onCancel(): void;
};
```

여기서 `onSave`는 "버튼이 클릭되었다"가 아니라 "사용자가 편집 내용을 저장하려 한다"는 의미입니다.

반대로 저수준 UI 컴포넌트는 DOM 의미를 그대로 공개하는 것이 자연스러울 수 있습니다.

```tsx
<Button onClick={handleClick}>저장</Button>
```

따라서 무조건 `onClick`을 피하는 것이 아니라 컴포넌트의 추상화 수준에 맞춰 이름을 정합니다.

```text
기본 Button
→ onClick

ProjectEditor
→ onSave, onCancel

SearchForm
→ onSearch

DeleteDialog
→ onConfirm, onCancel
```

## Props가 내부 저장 방식을 노출하지 않게 합니다

부모가 자식의 내부 state setter를 직접 알아야 하는 구조는 결합도가 높아질 수 있습니다.

다음 형태를 생각해 봅니다.

```ts
type Props = {
  setEditing: React.Dispatch<
    React.SetStateAction<boolean>
  >;
};
```

이 prop은 자식이 "편집을 끝낸다"는 의미보다 부모가 `useState<boolean>`을 사용한다는 구현 세부사항을 노출합니다.

가능하면 의도를 표현합니다.

```ts
type Props = {
  onEditComplete(): void;
};
```

그러면 부모가 이후 state machine, router navigation 또는 다른 저장 방식을 사용해도 자식의 계약은 유지될 수 있습니다.

## 서버 값과 입력 초안을 분리합니다

사용자가 편집 중인 제목은 서버가 마지막으로 확정한 제목과 다릅니다.

```text
serverTitle
→ 서버가 마지막으로 저장했다고 확인한 값

draftTitle
→ 사용자가 현재 편집기에 입력 중인 값
```

예를 들어 서버 제목이 `"Network"`이고 사용자가 `"Networking"`을 입력 중이라면 다음 상태는 정상입니다.

```text
serverTitle = "Network"
draftTitle  = "Networking"
```

두 값을 하나로 합치면 저장 실패, 취소와 충돌에서 어떤 값으로 돌아가야 할지 모호해집니다.

### 저장 상태도 별도로 생각합니다

편집기는 다음 세 축을 가질 수 있습니다.

```text
확정 데이터
→ serverTitle, version

입력 초안
→ draftTitle

요청 상태
→ idle | saving | error | conflict
```

이 값들이 독립적으로 아무 조합이나 가능한 것은 아니므로 실제 프로젝트에서는 union으로 묶어 불가능한 상태를 줄일 수도 있습니다.

## 저장 결과별로 어떤 값을 유지할지 정합니다

서버가 version을 사용해 동시 수정을 감지한다고 가정합니다.

```text
클라이언트가 알고 있는 version = 3
다른 사용자가 먼저 저장하여 서버 version = 4
현재 사용자가 version = 3으로 저장 시도
→ 서버가 충돌로 판단 가능
```

각 결과에서 상태를 어떻게 바꿀지 미리 정합니다.

### 일반 실패

예: 네트워크 단절, 서버의 일시적 오류.

```text
serverTitle
→ 마지막으로 서버가 확정한 값 유지

draftTitle
→ 사용자가 작성한 값 유지

편집기
→ 열린 상태 유지

focus
→ 가능하면 입력 위치 유지

사용자 안내
→ 실패와 재시도 방법 표시
```

일반 실패에서 초안을 서버 값으로 되돌리면 사용자가 방금 입력한 내용을 잃을 수 있습니다.

### 충돌

`409 Conflict` 같은 응답은 단순한 네트워크 실패와 의미가 다릅니다. 다른 변경으로 인해 현재 클라이언트의 기준 버전이 오래되었다는 뜻일 수 있습니다.

```text
serverTitle
→ 응답 또는 재조회로 얻은 최신 서버 값으로 갱신

draftTitle
→ 사용자가 작성한 값 유지

version
→ 최신 서버 version으로 갱신

편집기
→ 열린 상태 유지

화면
→ 최신 서버 값과 사용자 초안을 비교할 수 있게 표시
```

충돌에서 사용자의 초안을 버리지 않는 이유는 서버 최신 값과 사용자 의도가 모두 중요하기 때문입니다.

실제 재시도 정책은 API 계약에 따라 다릅니다. 최신 `version`만 바꾸어 그대로 다시 저장해도 되는지, 사용자가 내용을 다시 검토해야 하는지는 서버의 concurrency 규칙과 제품 요구에 따라 결정합니다.

### 성공

저장 성공 뒤에는 클라이언트가 보낸 값을 그대로 최종값으로 간주하기보다 **서버가 반환한 확정 결과**를 사용하는 편이 안전합니다.

서버가 다음과 같은 처리를 할 수 있기 때문입니다.

- 공백 정규화
- 대소문자 또는 formatting 변경
- 새 `version` 생성
- 수정 시각 부여
- 권한에 따른 일부 필드 변경

따라서 성공 시 다음처럼 처리할 수 있습니다.

```text
serverTitle
→ 서버 응답의 제목

version
→ 서버 응답의 새 version

draftTitle
→ 서버 확정 제목과 맞춤

편집기
→ 닫음

focus
→ 편집 시작 버튼 등 논리적인 위치로 복귀
```

### 취소

취소는 서버 요청 실패와 다릅니다. 사용자가 초안을 버리기로 선택한 것입니다.

```text
draftTitle
→ 현재 serverTitle로 되돌림

편집기
→ 닫음

focus
→ 편집 시작 버튼으로 복귀
```

## props 변경과 입력 초안의 관계를 명시합니다

편집 중 서버 값이 바뀌면 흔히 다음 코드로 초안을 무조건 덮어쓰려는 문제가 생깁니다.

```tsx
useEffect(() => {
  setDraftTitle(project.title);
}, [project.title]);
```

이 코드는 서버의 새 제목을 반영할 수 있지만, 사용자가 편집 중일 때 prop이 바뀌면 작성 중인 초안을 잃게 만들 수 있습니다.

따라서 다음 정책 중 어떤 것을 원하는지 먼저 정해야 합니다.

```text
편집 중이 아닐 때만 새 서버 값으로 초안 초기화

편집 중 서버 값이 바뀌면 conflict 상태로 전환

특정 project id가 바뀔 때만 편집기를 새로 초기화
```

단순히 "props가 바뀌었으니 state도 맞춘다"는 규칙은 충분하지 않습니다. **서버 값과 초안의 의미가 다르기 때문에 동기화 조건도 제품 동작으로 정의해야 합니다.**

## 목록의 identity와 `key`를 상태 설계에 포함합니다

React 목록에서 `key`는 단순히 경고를 없애는 값이 아닙니다. 어떤 렌더링 결과가 이전의 어떤 컴포넌트 인스턴스와 같은 대상을 나타내는지 식별하는 데 사용됩니다.

편집 상태를 가진 행이 있다면 안정적인 식별자를 key로 사용합니다.

```tsx
{projects.map((project) => (
  <ProjectRow
    key={project.id}
    project={project}
  />
))}
```

배열 index를 key로 사용하고 항목이 삽입·삭제·정렬되면 기존 행의 local state가 다른 항목과 연결되는 것처럼 보일 수 있습니다.

따라서 서버 데이터에서 id의 중복을 검사하는 것은 API 계약뿐 아니라 UI identity를 안정적으로 유지하는 데도 중요할 수 있습니다.

## 접근성을 상태 변경에 포함합니다

접근성은 마지막에 markup만 검사하는 작업이 아닙니다. UI 상태가 바뀔 때 **키보드 focus가 어디에 있어야 하는지**, **보조 기술이 어떤 변화를 알 수 있어야 하는지**도 상태 전이에 포함해야 합니다.

예를 들어 편집 흐름을 다음처럼 정의할 수 있습니다.

```text
편집 시작
→ input 표시
→ input으로 focus 이동

저장 중
→ 중복 제출 방지
→ "저장 중" 상태 전달

저장 성공
→ 편집기 닫힘
→ 편집 시작 버튼으로 focus 복귀
→ 저장 완료 안내

일반 실패
→ 편집기 유지
→ 입력 초안 유지
→ input focus 유지
→ 오류 안내

충돌
→ 편집기 유지
→ 초안 유지
→ 최신 서버 값과 충돌 안내
```

### focus는 상태의 결과입니다

dialog, inline editor, 삭제 확인 UI처럼 요소가 나타나고 사라지는 화면에서는 focus 이동을 별도 요구사항으로 봅니다.

다음처럼 "DOM이 바뀌었으니 브라우저가 적당히 처리할 것"이라고 가정하지 않습니다.

- 편집기가 열리면 사용자가 바로 입력할 수 있어야 합니까?
- 편집기가 닫힌 뒤 focus가 사라지지 않아야 합니까?
- 오류 발생 시 오류 메시지로 focus를 옮길지 입력에 유지할지 결정했습니까?
- dialog가 닫히면 dialog를 연 버튼으로 focus를 돌려야 합니까?

### 상태 알림은 필요한 변화에 사용합니다

대기, 오류, 저장 결과처럼 화면에서 시각적으로만 바뀌는 중요한 정보는 보조 기술 사용자가 알 수 있는 방법을 고려합니다.

예를 들어 다음 상태는 live region 후보가 될 수 있습니다.

```text
"검색 중"
"프로젝트 12개를 찾았습니다"
"저장하지 못했습니다. 다시 시도하세요"
"다른 사용자가 먼저 수정했습니다"
```

모든 작은 UI 변화에 live region을 사용하면 오히려 과도한 알림이 될 수 있으므로 작업 결과나 현재 진행 상태처럼 사용자 판단에 필요한 변화에 사용합니다.

## 접근 가능한 이름은 데이터 identity와 구분합니다

반복 항목에서 `id`는 프로그램의 식별자이고 accessible name은 사용자가 이해할 수 있는 이름입니다.

예를 들어 다음 버튼은 시각적으로는 행 안에 있어 의미가 보여도 보조 기술에는 무엇을 편집하는 버튼인지 부족할 수 있습니다.

```tsx
<button>편집</button>
```

프로젝트 이름을 포함하면 반복 항목을 구분하기 쉬워집니다.

```tsx
<button
  aria-label={`${project.name} 편집`}
>
  편집
</button>
```

실제 markup은 디자인과 문맥에 따라 달라질 수 있지만, 반복되는 버튼과 control이 사용자에게 서로 구분 가능한 이름을 제공하는지 확인합니다.

## 상태 로직과 DOM 동작을 나누어 테스트합니다

상태 전이와 DOM 동작은 서로 다른 종류의 검증이 필요할 수 있습니다.

### 순수 상태 로직

다음은 DOM 없이 단위 테스트할 수 있습니다.

- 빈 검색 결과가 `"empty"` 상태가 되는가
- 일반 실패에서 이전 결과를 유지하는가
- 충돌에서 사용자 초안을 유지하는가
- 취소하면 초안이 서버 값으로 되돌아가는가
- 잘못된 외부 값이 parser에서 거부되는가

### 실제 브라우저 동작

다음은 DOM 또는 브라우저 수준에서 확인하는 편이 적합합니다.

- Enter로 검색 폼을 제출할 수 있는가
- 편집 시작 후 input으로 focus가 이동하는가
- 저장 성공 뒤 적절한 버튼으로 focus가 돌아가는가
- 오류와 저장 상태가 보조 기술에 전달되는가
- 뒤로 이동했을 때 URL 상태와 화면이 일치하는가

타입이 올바르다고 해서 focus 이동까지 올바른 것은 아니고, E2E가 성공한다고 해서 불가능한 상태 조합이 타입에서 제거된 것도 아닙니다. 서로 다른 검증 수단이 서로 다른 계약을 담당합니다.

## 흔히 생기는 상태 설계 문제

### props를 state로 무조건 복사합니다

```tsx
const [name, setName] = useState(project.name);
```

이 자체는 잘못이 아닙니다. `name`이 **편집 초안**이라면 올바를 수 있습니다. 하지만 단지 `project.name`을 화면에 표시하기 위해 복사했다면 중복 상태일 수 있습니다.

질문은 다음과 같습니다.

```text
이 state는 원본과 달라도 정상인가?
```

정상이라면 별도 의미가 있는 상태일 가능성이 큽니다. 항상 같아야 한다면 복제하지 않는 편이 낫습니다.

### 모든 원격 데이터를 전역 store에 복사합니다

서버 응답을 받자마자 모든 값을 전역 상태에 다시 저장하면 서버 상태와 클라이언트 복사본의 최신성 규칙을 별도로 관리해야 합니다.

다음을 먼저 정합니다.

- 누가 최신성을 판단합니까?
- 다시 가져오기는 언제 합니까?
- mutation 성공 후 어떤 값을 기준으로 갱신합니까?
- 다른 탭이나 사용자의 변경은 어떻게 반영합니까?

서버 상태를 관리하는 library를 사용하더라도 이 질문 자체가 사라지지는 않습니다.

### effect로 모든 상태를 동기화합니다

두 상태가 계속 같아야 해서 `useEffect`가 필요해졌다면 둘 중 하나가 파생값인지 확인합니다.

```text
A가 바뀔 때마다 B를 같은 값으로 맞춤
→ B를 별도 상태로 저장할 필요가 있는가?
```

effect는 외부 시스템과 동기화하거나 React 렌더링 바깥의 side effect를 수행할 때 필요할 수 있지만, 단순 계산값을 맞추기 위한 기본 수단으로 사용하지 않습니다.

## 구현 전에 상태 표를 작성합니다

복잡한 상호작용은 코드를 쓰기 전에 간단한 표로 정리하면 빠르게 모순을 찾을 수 있습니다.

예를 들어 제목 편집 기능은 다음과 같이 정리할 수 있습니다.

| 상황 | 서버 값 | 초안 | 편집기 | 사용자 안내 |
| --- | --- | --- | --- | --- |
| 편집 시작 | 유지 | 서버 값으로 초기화 | 열림 | 없음 |
| 입력 중 | 유지 | 사용자 입력 | 열림 | 없음 |
| 저장 중 | 유지 | 유지 | 열림 | 저장 중 |
| 저장 성공 | 응답 값으로 갱신 | 응답 값 | 닫힘 | 성공 |
| 일반 실패 | 유지 | 유지 | 열림 | 실패 |
| 충돌 | 최신 서버 값 | 사용자 입력 유지 | 열림 | 충돌 |
| 취소 | 유지 | 서버 값으로 되돌림 | 닫힘 | 없음 |

이 표는 어떤 값이 source of truth인지와 각 이벤트에서 무엇을 보존해야 하는지를 동시에 보여 줍니다.

## Stable Core 완료 기준

다음 항목을 설명하고 코드로 표현할 수 있으면 실제 프로젝트 구현을 시작할 준비가 된 것입니다.

- URL, 서버 응답, 화면 상태, 입력 초안, 지속 설정과 계산값의 저장 위치를 구분합니다.
- 각 값의 source of truth를 설명할 수 있습니다.
- 같은 의미의 값을 여러 곳에 불필요하게 복제하지 않습니다.
- 다른 값에서 결정적으로 계산할 수 있는 값은 가능하면 별도 상태로 저장하지 않습니다.
- 여러 컴포넌트가 공유하는 상태를 필요한 범위까지만 올립니다.
- 서로 동시에 존재할 수 없는 상태를 discriminated union으로 제한합니다.
- 가능한 상태와 상태 전이를 설명할 수 있습니다.
- 외부 JSON과 URL 값을 `unknown`으로 받고 구조, 범위와 허용값을 검사합니다.
- 검증된 외부 값을 애플리케이션에서 사용하기 좋은 타입으로 변환합니다.
- Server Component와 Client Component의 실행 위치와 module 경계를 구분합니다.
- 컴포넌트 props가 내부 state 저장 방식보다 허용할 값과 동작을 표현합니다.
- 서버가 확정한 값과 사용자가 편집 중인 값을 별도로 유지합니다.
- 일반 실패, 충돌, 성공과 취소에서 어떤 값을 보존할지 정했습니다.
- props 변경이 입력 초안을 언제 초기화해야 하는지 정책을 정했습니다.
- 반복 항목의 안정적인 identity와 React `key`를 고려합니다.
- 상태가 바뀔 때 필요한 안내 문구와 focus 위치를 정합니다.
- 순수 상태 전이와 실제 브라우저 동작을 각각 적절한 수준에서 테스트합니다.

실제 프로젝트에서 비동기 요청, history 또는 낙관적 갱신이 필요해지는 시점에 [`03-nextjs-data-effects-and-concurrency.md`](03-nextjs-data-effects-and-concurrency.md)를 JIT로 읽습니다.
