# 테스트, 접근성·성능 확인

테스트의 목적은 테스트 개수나 coverage 수치를 늘리는 것이 아닙니다. **변경으로 깨질 수 있는 사용자 동작과 시스템 계약을, 그 문제를 가장 빠르고 결정적으로 재현할 수 있는 위치에서 검증하는 것**이 목적입니다.

형 검사, 순수 함수 테스트, Route Handler 테스트, 운영 빌드와 실제 브라우저 테스트는 서로 대체 관계가 아닙니다. 각각 볼 수 있는 오류의 범위가 다릅니다.

```text
typecheck 성공
≠ 실제 HTTP 응답이 올바름

단위 테스트 성공
≠ browser history와 focus가 올바름

개발 서버 성공
≠ 운영 빌드와 운영 서버가 정상임

자동 접근성 검사 성공
≠ 키보드 사용 흐름과 초점 이동이 올바름
```

따라서 "무슨 테스트를 추가할까?"보다 먼저 **어떤 실패를 막아야 하는가?**를 적고, 그 실패를 가장 낮은 비용으로 확실하게 잡을 수 있는 테스트 위치를 선택합니다.

이 문서는 실제 프로젝트에서 테스트 위치를 정하거나 키보드·반응형·성능 문제를 확인해야 할 때 JIT로 읽습니다.

## 목표

이 문서를 읽은 뒤에는 다음 작업을 수행할 수 있어야 합니다.

- 기능의 주요 위험을 먼저 적고 적절한 테스트 위치를 고릅니다.
- 순수 로직과 실제 브라우저 동작을 서로 다른 수준에서 검증합니다.
- 고정된 `sleep` 없이 요청 완료 순서, 실패, 취소와 충돌을 재현합니다.
- 테스트가 내부 구현이 아니라 사용자에게 보이는 계약을 검증하도록 만듭니다.
- accessible name, 키보드 조작, live region과 초점 이동을 실제 브라우저에서 확인합니다.
- 좁은 viewport, 확대, 긴 문자열과 motion 감소 설정을 검사합니다.
- 초기 JavaScript와 DOM 크기에 회귀 탐지용 성능 예산을 둡니다.
- 개발 서버가 아니라 운영 빌드와 실제 운영 시작 명령을 검증합니다.
- 불안정한 테스트를 retry나 임의의 대기 시간으로 숨기지 않습니다.

## 구현 파일보다 위험을 먼저 적습니다

테스트 파일을 만들기 전에 기능이 잘못되었을 때 사용자에게 어떤 문제가 생기는지 적습니다.

| 위험 | 사용자에게 생기는 문제 | 먼저 사용할 테스트 |
| --- | --- | --- |
| URL과 입력값이 어긋남 | 공유, 새로 고침과 뒤로 이동이 깨짐 | query 단위 테스트 + 브라우저 navigation |
| 잘못된 응답을 믿음 | 잘못된 화면 또는 실행 중 오류 | 응답 parser 단위 테스트 + HTTP 경계 테스트 |
| 이전 응답이 최신 결과를 덮음 | 사용자가 이전 검색 결과를 봄 | 완료 순서를 직접 제어한 비동기 테스트 |
| 충돌에서 입력 초안을 잃음 | 사용자가 작성한 내용이 사라짐 | 상태 전이 테스트 + 저장 충돌 브라우저 테스트 |
| 취소 또는 저장 후 초점을 잃음 | 키보드 사용자가 다음 작업 위치를 찾지 못함 | 실제 브라우저 focus 테스트 |
| 좁은 화면에서 내용이 넘침 | 일부 control이나 텍스트를 사용할 수 없음 | 여러 viewport와 긴 데이터의 브라우저 테스트 |
| Client Component 범위가 커짐 | 초기 JavaScript가 불필요하게 증가 | 운영 빌드 기반 성능 예산 |
| 운영 설정이 잘못됨 | 로컬 개발은 되지만 배포 후 실행 실패 | build + 실제 start + smoke/E2E |

각 테스트는 다음 질문에 한 문장으로 답할 수 있어야 합니다.

```text
이 테스트가 실패하면 어떤 잘못된 사용자 동작 또는 시스템 계약을 발견한 것입니까?
```

예를 들어 다음 테스트는 구현에 지나치게 묶일 수 있습니다.

```ts
expect(fetchProjects).toHaveBeenCalledTimes(1);
```

호출 횟수가 정말 계약이라면 의미가 있지만, 사용자가 올바른 최신 결과를 보는 것이 핵심이라면 다음과 같은 검증이 더 직접적입니다.

```text
old 요청이 new 요청보다 늦게 완료되어도
화면에는 new 결과가 남아 있어야 한다.
```

내부 함수 호출 횟수보다 사용자에게 관찰되는 결과를 우선합니다.

## 테스트 위치를 나눕니다

각 테스트 수준이 잘 잡는 문제와 잡기 어려운 문제를 구분합니다.

| 검사 방법 | 잘 잡는 문제 | 직접 확인하기 어려운 문제 |
| --- | --- | --- |
| 정적 검사 | syntax, type 오류, 빠진 union 분기 | 실제 외부 데이터, browser 동작 |
| route type + typecheck | Next.js route signature, 일부 Server/Client 경계 오류 | 실제 HTTP 전송, layout, focus |
| 순수 단위 테스트 | parser, validation, 상태 전이, 요청 coordinator | DOM, CSS layout, 실제 history |
| Route Handler/API 테스트 | 입력 검증, status code, header, 응답 body | 실제 bundle, focus, browser navigation |
| 운영 빌드 | module graph, route 생성, 환경 설정 일부, 배포 산출물 | 실제 사용자 상호작용 |
| 브라우저 E2E | history, network 흐름, keyboard, focus, viewport | 모든 내부 알고리즘 경곗값 |
| standalone smoke | 실제 start, 핵심 endpoint, release 구성 | 복잡한 전체 사용자 시나리오 |
| 성능 예산 검사 | JS/DOM 급증 같은 회귀 | 실제 사용자 체감 성능 전체 |

테스트 위치 선택의 기본 원칙은 다음과 같습니다.

```text
DOM이 없어도 검증 가능
→ 순수 단위 테스트 우선

HTTP 경계가 핵심
→ Route Handler/API 테스트

browser API나 layout이 핵심
→ 실제 브라우저 테스트

배포 산출물이 핵심
→ 운영 build/start 검증
```

### 같은 동작을 모든 계층에서 반복하지 않습니다

예를 들어 `page` query가 양의 정수인지 확인하는 규칙은 parser 단위 테스트에서 경곗값을 충분히 검사할 수 있습니다.

```text
?page=
?page=0
?page=-1
?page=abc
?page=1
?page=20
```

이 모든 조합을 브라우저 E2E에서 반복하면 테스트는 느려지지만 얻는 추가 정보가 적습니다.

반대로 다음 동작은 parser 단위 테스트만으로는 확인할 수 없습니다.

```text
검색 조건 변경
→ URL 갱신
→ Back
→ 이전 검색 조건과 결과 복원
```

이런 동작은 실제 browser history가 참여하므로 브라우저 테스트가 적합합니다.

## 최소한의 테스트 조합으로 계약을 덮습니다

하나의 기능에 모든 테스트 종류가 필요한 것은 아닙니다.

예를 들어 검색 화면이라면 다음 조합만으로도 핵심 위험을 나눠 잡을 수 있습니다.

```text
query parser 단위 테스트
→ 잘못된 URL 값과 기본값 검증

request coordinator 단위 테스트
→ abort와 generation 불변식 검증

Route Handler 테스트
→ HTTP 입력과 응답 계약 검증

브라우저 E2E
→ URL, Back/Forward, 늦은 응답, focus 검증

운영 build/start
→ 실제 배포 산출물 실행 가능 여부 검증
```

테스트 수보다 **각 위험이 어느 테스트에 책임 있게 배치되어 있는가**가 중요합니다.

## Route type을 만든 뒤 형 검사합니다

Next.js의 route와 navigation type은 프로젝트 버전에 따라 생성 파일에 의존할 수 있습니다. 깨끗한 checkout에서도 같은 형 검사가 재현되도록 필요한 type generation을 script에 포함합니다.

예를 들어 프로젝트가 해당 명령을 지원한다면 다음처럼 구성할 수 있습니다.

```json
{
  "scripts": {
    "typecheck": "next typegen && tsc --noEmit"
  }
}
```

이 명령은 **예시**입니다. 실제 명령 이름과 지원 여부는 프로젝트가 사용하는 Next.js 버전과 기존 scripts를 기준으로 확인합니다.

중요한 기준은 다음과 같습니다.

```text
새로운 개발자가 clean checkout
→ 저장소가 정한 설치 명령 실행
→ 저장소의 typecheck 실행
→ 필요한 생성 파일이 자동 준비됨
→ 같은 결과 재현
```

생성 디렉터리를 commit하지 않는 프로젝트라면 CI도 같은 방식으로 다시 생성할 수 있어야 합니다.

## 형 검사가 보장하지 않는 것도 구분합니다

다음 코드가 typecheck를 통과해도 외부 HTTP 응답의 실제 내용은 검증되지 않습니다.

```ts
const result =
  (await response.json()) as SearchResult;
```

따라서 다음 두 검증은 서로 다른 역할을 가집니다.

```text
TypeScript
→ 코드가 SearchResult를 어떻게 사용할 수 있는지 검사

runtime parser
→ 실제 외부 값이 SearchResult 계약에 맞는지 검사
```

runtime parser의 성공과 실패 경곗값은 순수 단위 테스트로 검증하는 것이 좋습니다.

## 네트워크 테스트에서는 시간을 기다리지 말고 사건을 제어합니다

다음처럼 일정 시간을 기다리는 테스트는 실행 환경에 따라 실패할 수 있습니다.

```ts
await new Promise((resolve) =>
  setTimeout(resolve, 500),
);
```

이 방식은 다음 문제가 있습니다.

```text
느린 CI
→ 500ms 안에 조건이 충족되지 않아 실패

빠른 환경
→ 이미 끝난 작업을 500ms 동안 불필요하게 기다림

race test
→ 어떤 요청이 먼저 끝나는지 실제로 통제하지 못함
```

race condition을 테스트하려면 **시간의 길이**가 아니라 **완료 순서**를 직접 제어합니다.

## 요청을 보류하고 원하는 순서로 해제합니다

브라우저 네트워크 mock을 사용할 수 있다면 특정 요청의 응답을 보류합니다.

개념적으로 다음 순서를 만듭니다.

```text
old 요청 시작
→ 응답 보류

new 요청 시작
→ new 응답 완료
→ 화면에 new 결과 표시 확인

old 응답 해제
→ 화면이 여전히 new 결과인지 확인
```

Playwright 형태의 예시는 다음과 같이 작성할 수 있습니다.

```ts
let releaseOld:
  (() => void) | undefined;

const oldGate =
  new Promise<void>((resolve) => {
    releaseOld = resolve;
  });

await page.route(
  "**/api/projects?*",
  async (route) => {
    const url =
      new URL(
        route.request().url(),
      );

    const query =
      url.searchParams.get("q");

    if (query === "old") {
      await oldGate;
    }

    await route.continue();
  },
);
```

실제 mock 방식은 테스트가 API 서버를 직접 호출하는지, route interception으로 응답을 만드는지에 따라 달라집니다. 핵심은 **테스트가 완료 순서를 결정적으로 통제한다는 것**입니다.

## abort와 오래된 결과 폐기는 별도로 검사합니다

새 요청이 이전 요청을 abort하는 구현이라면 다음 두 사실은 서로 다릅니다.

```text
이전 signal이 abort되었다.
```

```text
이전 결과가 늦게 도착해도 화면을 바꾸지 않는다.
```

첫 번째는 불필요한 작업을 줄였다는 의미이고, 두 번째는 최신성 계약을 지켰다는 의미입니다.

구현에서 `AbortController`와 generation을 함께 사용한다면 가능하면 각각의 책임을 검증합니다.

### coordinator 단위 테스트

```text
begin #2
→ begin #1의 signal abort

isCurrent(oldGeneration)
→ false
```

### 사용자 결과 테스트

```text
old 응답을 마지막에 완료
→ 최신 결과가 그대로 유지
```

abort 테스트 하나로 race condition까지 검증했다고 간주하지 않습니다.

## 오래된 실패도 테스트합니다

race condition은 성공 응답만 문제가 아닙니다.

다음 순서를 생각합니다.

```text
A 요청 시작
B 요청 시작
B 성공
A 실패
```

A가 오래된 요청인데 마지막에 오류 UI를 표시하면 최신 B 결과를 보고 있던 사용자에게 잘못된 오류가 나타납니다.

따라서 다음 시나리오도 결정적으로 검사합니다.

```text
old 요청 보류
→ new 요청 성공
→ old 요청 실패
→ 화면에 old 오류가 나타나지 않음
```

최신성 검사는 성공 경로와 실패 경로 모두에 필요합니다.

## 취소는 일반 오류와 구분합니다

사용자가 새 검색을 시작해 이전 검색이 취소된 것은 일반적으로 애플리케이션 오류가 아닙니다.

다음 상황을 테스트합니다.

```text
old 검색 시작
→ new 검색 시작
→ old 요청 abort
→ "검색 실패" 같은 오류 문구가 표시되지 않음
```

다만 사용자가 명시적으로 "업로드 취소"를 눌렀다는 사실을 알려야 하는 기능처럼 취소 자체가 사용자 결과인 경우에는 별도 UI를 가질 수 있습니다.

## unmount 뒤 결과도 반영하지 않는지 확인합니다

컴포넌트가 사라진 뒤 비동기 작업이 끝나는 경우도 race의 한 종류입니다.

```text
요청 시작
→ 다른 화면으로 이동
→ 이전 요청 완료
```

이전 화면의 요청이 현재 화면 상태를 변경하면 안 됩니다.

테스트에서는 다음을 확인할 수 있습니다.

```text
요청 시작
→ navigation 또는 component unmount
→ 응답 완료
→ 이전 화면의 성공/오류 UI가 나타나지 않음
```

## 충돌과 일반 실패를 별도로 재현합니다

낙관적 저장에서 `503`과 `409 Conflict`는 같은 실패가 아닙니다.

### 일반 실패

```text
서버 확정 제목 = Network
사용자 초안 = Networking

optimistic 표시
→ Networking

503
→ 목록은 Network로 rollback
→ 초안은 Networking 유지
→ 편집기와 focus 유지
```

### 충돌

```text
내 기준 version = 3
서버 최신 version = 4
최신 서버 제목 = Network Platform
내 초안 = Networking

409
→ 목록은 Network Platform
→ 초안은 Networking 유지
→ conflict 안내
```

충돌 테스트에서 요청 전 값으로 단순 rollback하면 안 됩니다. 최신 서버 값이 존재한다면 그것을 반영하면서 사용자 초안을 보존하는지를 검사합니다.

## 예상하지 않은 애플리케이션 요청을 찾습니다

네트워크 mock이 모든 URL에 무조건 성공 응답을 주면 잘못된 구현도 통과할 수 있습니다.

예를 들어 다음 문제가 숨겨질 수 있습니다.

- query parameter가 잘못된 API 요청
- 같은 요청이 불필요하게 두 번 발생
- 예상하지 않은 mutation
- 잘못된 endpoint 호출

테스트 대상 기능이 사용하는 API namespace를 명확히 안다면 예상한 요청만 허용하고 그 범위의 예상 밖 요청은 실패로 처리할 수 있습니다.

```text
/api/projects
→ 명시적으로 mock

예상하지 않은 /api/projects 요청
→ 테스트 실패
```

하지만 browser 자체 요청이나 framework asset까지 전부 막으면 테스트가 구현 환경에 지나치게 결합됩니다.

따라서 보통 다음 범위를 구분합니다.

```text
애플리케이션의 핵심 API 경로
→ 엄격하게 검사

framework asset / browser 내부 요청
→ 필요 이상으로 간섭하지 않음
```

## Route Handler는 HTTP 계약을 직접 검사합니다

Route Handler 테스트에서는 내부 service가 호출되었다는 사실만 보지 말고 HTTP 계약을 확인합니다.

예를 들어 다음 항목을 검사합니다.

- method
- path parameter
- query parameter
- request body
- authentication/authorization 결과
- status code
- response header
- response body
- 잘못된 입력의 오류 형식

예를 들어 잘못된 `page` 값의 계약이 다음과 같다고 가정합니다.

```text
GET /api/projects?page=abc
→ 400
→ JSON 오류 body
```

Route Handler 테스트는 이 HTTP 경계를 직접 검증합니다.

반면 parser 자체의 모든 숫자 경곗값까지 Route Handler를 통해 반복할 필요는 없습니다. parser의 세부 경곗값은 순수 단위 테스트로 더 빠르게 검사할 수 있습니다.

## 접근성은 정적 HTML과 시간에 따른 동작을 함께 봅니다

접근성 문제는 두 종류로 나눠 생각하는 편이 좋습니다.

```text
정적인 구조
→ element 의미
→ accessible name
→ label
→ heading 구조
→ ARIA 사용

시간에 따른 동작
→ focus 이동
→ loading/error 안내
→ dialog 열기/닫기
→ 저장 성공/실패 후 위치
```

자동 검사 도구는 이름이 없는 control, 잘못된 ARIA 관계 등 정적인 문제를 잘 찾을 수 있습니다. 하지만 사용자가 작업을 수행한 뒤 **어디에 focus가 있어야 하는가**까지 제품 의도에 맞게 판단해 주지는 못합니다.

따라서 자동 검사와 실제 keyboard flow를 함께 봅니다.

## 의미에 맞는 HTML을 먼저 사용합니다

ARIA를 추가하기 전에 기본 HTML element가 이미 필요한 의미를 제공하는지 확인합니다.

일반적인 기준은 다음과 같습니다.

- 페이지의 주요 내용은 `<main>`에 둡니다.
- heading 계층을 내용 구조에 맞게 유지합니다.
- 입력에는 programmatic label을 제공합니다.
- 이동에는 link를 사용합니다.
- 동작에는 button을 사용합니다.
- 목록 구조라면 list semantics를 고려합니다.
- 독립된 콘텐츠 단위라면 `article`이 적합한지 판단합니다.
- 중요한 비동기 상태 변화는 필요한 경우 live region으로 알립니다.

다음처럼 click handler를 붙인 generic element보다 기본 button이 적절합니다.

```html
<button type="button">
  제목 수정
</button>
```

기본 semantic element는 keyboard 동작, role과 접근 가능한 기본 동작을 이미 제공합니다.

## accessible name을 실제로 확인합니다

화면에 텍스트가 보인다고 해서 항상 control의 accessible name이 충분한 것은 아닙니다.

반복되는 목록에서 다음 버튼이 여러 개 존재한다고 가정합니다.

```html
<button>수정</button>
<button>수정</button>
<button>수정</button>
```

보조 기술 사용자는 어느 프로젝트의 수정 버튼인지 구분하기 어려울 수 있습니다.

예를 들어 각 대상의 이름을 포함할 수 있습니다.

```tsx
<button
  aria-label={`${project.name} 제목 수정`}
>
  수정
</button>
```

실제 구현에서는 visible text, `<label>`, `aria-labelledby`, `aria-label` 중 가장 자연스러운 방식을 선택합니다.

테스트에서는 CSS selector보다 role과 accessible name을 이용하면 사용자에게 노출되는 의미를 함께 검증할 수 있습니다.

```ts
page.getByRole(
  "button",
  {
    name: "Network 제목 수정",
  },
);
```

## keyboard로 주요 작업 전체를 완료합니다

키보드 접근성은 버튼 하나가 Enter에 반응하는지만 확인하지 않습니다. 하나의 사용자 작업을 시작부터 끝까지 수행합니다.

예를 들어 inline editor라면 다음 흐름을 확인합니다.

```text
Tab
→ "Network 제목 수정" 버튼에 도달

Enter
→ 편집기 열림

focus
→ 제목 input으로 이동

문자 입력
→ draft 변경

Escape 또는 취소
→ 편집기 닫힘

focus
→ 원래 수정 버튼으로 복귀
```

저장 경로도 별도로 확인합니다.

```text
편집 시작
→ input focus

저장
→ 성공

편집기 닫힘
→ 수정 버튼으로 focus 복귀
```

일반 실패와 충돌에서는 다음이 필요할 수 있습니다.

```text
편집기 유지
초안 유지
input focus 유지
오류 또는 충돌 안내
```

접근성 요구사항은 상태 전이와 함께 정의합니다.

## focus는 "어딘가에 존재"하는 것으로 충분하지 않습니다

focus 테스트에서는 `document.activeElement`가 존재하는지만 확인하지 않습니다.

사용자가 다음 작업을 계속할 수 있는 **논리적인 element**에 focus가 있는지 확인합니다.

예를 들어 dialog가 닫힌 뒤 body로 focus가 사라지는 것보다 dialog를 열었던 버튼으로 돌아가는 편이 자연스럽습니다.

```text
삭제 버튼
→ 확인 dialog
→ 취소
→ 원래 삭제 버튼
```

동적 element가 사라진 뒤 focus를 잃는 문제는 실제 브라우저에서 확인하는 것이 좋습니다.

## `autoFocus`만으로 focus 정책을 대신하지 않습니다

`autoFocus`는 특정 element를 처음 렌더링할 때 focus하는 데 도움이 될 수 있지만 다음 전체 흐름을 자동으로 해결하지는 않습니다.

- 편집기 재오픈
- 저장 성공 후 복귀
- 취소 후 복귀
- dialog 닫힘
- route 이동 후 main heading 또는 주요 영역으로 이동
- validation 오류 발생 후 적절한 위치 유지

focus는 UI 상태 전이의 결과로 설계합니다.

## live region은 중요한 상태 변화에 사용합니다

비동기 요청은 화면을 보고 있지 않은 사용자에게도 상태가 전달되어야 할 수 있습니다.

예를 들어 다음은 안내할 가치가 있는 상태입니다.

```text
검색 중
검색 결과 12개
저장 완료
저장 실패
다른 사용자가 먼저 수정함
```

하지만 모든 작은 UI 변화에 live region을 사용하면 과도한 음성 출력이 발생할 수 있습니다.

다음을 기준으로 판단합니다.

```text
이 변화가 사용자가 현재 작업이 끝났는지,
실패했는지,
다음 행동이 필요한지 판단하는 데 중요한가?
```

테스트에서는 단순히 `aria-live` attribute가 존재하는지보다 상태 변화 뒤 실제 안내 텍스트가 예상대로 바뀌는지도 확인합니다.

## 눈에 보이는 focus를 확인합니다

DOM상 focus가 올바른 element에 있어도 시각적인 focus indicator가 제거되어 있다면 키보드 사용자는 현재 위치를 알기 어렵습니다.

브라우저에서 다음을 확인합니다.

- outline이 제거되지 않았는가
- border 또는 box-shadow로 대체했다면 충분히 구분되는가
- hover와 focus가 같은 색 하나에만 의존하지 않는가
- 높은 확대에서도 focus indicator가 보이는가

필요하다면 computed style을 확인하여 outline이 실질적으로 제거되지 않았는지 검사할 수 있습니다.

```text
outline-style: none
outline-width: 0
```

다만 computed style 한 값만으로 전체 시각적 명확성을 완전히 판단할 수는 없습니다. 시각적 회귀나 수동 확인이 함께 필요할 수 있습니다.

## 좁은 화면과 확대를 함께 확인합니다

반응형 검증은 흔히 mobile viewport 하나만 확인하고 끝나기 쉽습니다.

하지만 사용 가능한 공간은 다음 이유로 줄어들 수 있습니다.

- 좁은 기기
- browser zoom
- OS 또는 browser 글자 크기 확대
- 긴 번역 문자열
- 사용자가 입력한 긴 텍스트
- 확대 도구
- side panel이나 browser UI

따라서 작은 viewport와 확대 상황을 함께 확인합니다.

권장할 수 있는 예시 조건은 다음과 같습니다.

- `320px × 720px`
- `640px` 너비에서 200% 확대에 가까운 사용 조건
- 공백 없는 80자 제목
- 긴 button label
- 긴 input/select 값
- 브라우저 기본 글자 크기 증가

이 값들은 절대 표준이 아니라 **작은 화면에서 회귀를 빠르게 찾기 위한 대표 조건**입니다. 실제 제품의 지원 환경과 접근성 기준에 맞춰 조정합니다.

## browser zoom과 viewport 축소는 완전히 같은 검사가 아닙니다

200% 확대는 단순히 viewport width를 절반으로 만드는 것과 동일하다고 가정하지 않습니다.

browser zoom은 렌더링 배율, device pixel, viewport 계산과 browser 동작에 영향을 줄 수 있습니다. 테스트 도구가 실제 zoom을 정확히 제어하지 못한다면 좁은 CSS viewport를 사용해 비슷한 layout 압력을 확인할 수 있지만, 이를 "실제 200% zoom을 완전히 검증했다"고 표현하지 않습니다.

가능하다면 실제 지원 browser에서 확대 동작을 별도로 확인합니다.

핵심은 다음 두 위험을 모두 확인하는 것입니다.

```text
좁은 layout에서 control이 겹치는가?
텍스트 확대에서 내용을 읽거나 조작하지 못하게 되는가?
```

## 가로 넘침을 여러 수준에서 확인합니다

페이지 전체 overflow는 다음처럼 확인할 수 있습니다.

```ts
const hasHorizontalOverflow =
  await page.evaluate(() => {
    const root =
      document.documentElement;

    return (
      root.scrollWidth >
      root.clientWidth
    );
  });

expect(
  hasHorizontalOverflow,
).toBe(false);
```

하지만 전체 문서에 scrollbar가 없다고 해서 모든 component가 올바른 것은 아닙니다.

다음도 확인할 수 있습니다.

- heading이 container 밖으로 밀려나지 않는가
- form control이 viewport를 넘지 않는가
- card 내부 긴 문자열이 잘리는가
- action button이 화면 밖으로 사라지지 않는가
- horizontal scrolling이 의도된 component와 의도되지 않은 page overflow를 구분했는가

예를 들어 코드 표나 data grid처럼 horizontal scroll이 의도된 component까지 모두 금지해서는 안 됩니다. **페이지 전체의 의도치 않은 overflow와 component 내부의 의도된 scroll 영역을 구분**합니다.

## 긴 문자열은 실제 layout stress test입니다

개발용 fixture가 항상 짧은 영어 문자열이면 실제 production layout 문제를 놓칠 수 있습니다.

다음 값을 테스트 데이터에 포함합니다.

```text
매우 긴 프로젝트 제목
공백 없는 긴 URL
긴 사용자 이름
긴 번역 문자열
긴 select option
긴 오류 메시지
```

예를 들어 다음 CSS는 긴 내용을 container 안에서 줄바꿈하는 데 도움이 될 수 있습니다.

```css
article {
  overflow-wrap: anywhere;
}
```

form control에서는 flex/grid item의 intrinsic width 때문에 넘침이 생기는 경우가 있으므로 다음 값이 필요할 수 있습니다.

```css
input,
select,
textarea {
  min-width: 0;
  max-width: 100%;
}
```

`box-sizing`도 layout 계산을 일관되게 만드는 일반적인 기본값입니다.

```css
*,
*::before,
*::after {
  box-sizing: border-box;
}
```

이 CSS를 무조건 복사하는 것이 목적이 아니라, 어떤 layout 제약 때문에 overflow가 발생했는지 이해하고 필요한 규칙을 적용합니다.

## motion 감소 설정은 실제 동작으로 확인합니다

CSS 파일에 다음 문자열이 존재하는지만 검사하면 실제 적용 여부를 보장하지 못합니다.

```css
@media (prefers-reduced-motion: reduce)
```

브라우저 테스트에서 motion 감소 설정을 활성화할 수 있다면 실제 computed style이나 동작을 확인합니다.

```ts
await page.emulateMedia({
  reducedMotion: "reduce",
});
```

예를 들어 장식적인 transition이 사실상 제거되는지 확인할 수 있습니다.

```text
일반 설정
→ transition-duration: 200ms

reduced motion
→ transition-duration: 0s 또는 매우 짧은 값
```

단, reduced motion은 모든 상태 변화를 없애라는 의미가 아닙니다.

```text
장식적 이동·확대 animation
→ 줄이거나 제거

loading이 끝났다는 상태 변화
→ 여전히 전달해야 함
```

사용자가 기능을 이해하는 데 필요한 상태 변화와 장식적인 motion을 구분합니다.

## 성능 예산은 회귀 탐지 기준입니다

성능 테스트를 처음 도입할 때 모든 실제 사용자 지표를 완벽하게 재현하기는 어렵습니다.

작은 프로젝트에서는 환경 차이에 비교적 덜 민감한 구조적 지표부터 사용할 수 있습니다.

예를 들어 다음과 같은 예산을 둘 수 있습니다.

```json
{
  "maximumInitialJavaScriptBytes": 800000,
  "maximumDomNodes": 180
}
```

이 숫자는 보편적인 권장값이 아니라 **해당 프로젝트의 회귀 탐지 기준 예시**입니다.

실제 기준은 현재 baseline, 지원 device, network, 실제 사용자 측정과 기능 요구를 근거로 정해야 합니다.

## 무엇을 측정하는지 정확히 정의합니다

"JavaScript 크기"라는 표현만으로는 측정값이 모호합니다.

다음을 구분합니다.

```text
원본 bundle 크기
압축 전 전송 크기
gzip/brotli 전송 크기
첫 route에서 실제 요청한 script의 합
실행된 JavaScript 양
parse/compile/execute 시간
```

예를 들어 문서의 예산이 다음을 의미한다고 명시할 수 있습니다.

```text
maximumInitialJavaScriptBytes
→ 첫 route load에서 browser가 요청한
  application JavaScript response body의 합
```

그렇다면 측정 스크립트와 CI도 같은 정의를 사용해야 합니다.

숫자 하나를 정하기보다 **측정 정의를 먼저 고정**합니다.

## DOM node 수 예산의 목적을 이해합니다

DOM element 수는 사용자 체감 성능 전체를 설명하지 않습니다.

하지만 다음과 같은 회귀 신호가 될 수 있습니다.

```text
작은 기능 추가
→ 숨겨진 component 수백 개 생성

목록 20개 표시
→ 각 row가 지나치게 깊은 markup 생성

Client Component 경계 확대
→ 중복 UI tree 생성
```

DOM 예산은 이런 급격한 구조 증가를 빨리 찾는 데 유용합니다.

그러나 다음 문제를 직접 측정하지는 못합니다.

- layout cost 전체
- style recalculation
- long task
- interaction latency
- image decode
- network latency

따라서 구조적 예산은 실제 성능 지표의 대체물이 아니라 초기 회귀 감지 장치입니다.

## baseline과 예산을 함께 기록합니다

임의의 숫자를 바로 실패 기준으로 두기보다 현재 운영 build를 측정해 baseline을 기록합니다.

예를 들어 다음처럼 시작할 수 있습니다.

```text
현재 initial JS
620 KB

현재 DOM elements
142

초기 예산
JS ≤ 700 KB
DOM ≤ 170
```

기능을 추가한 뒤 갑자기 다음처럼 바뀌면 원인을 확인합니다.

```text
JS 620 KB → 810 KB
DOM 142 → 260
```

예산을 올려야 하는 정당한 이유가 있을 수 있습니다. 중요한 것은 **증가가 의도된 것인지 검토 없이 기준만 올리지 않는 것**입니다.

## 성능 예산은 운영 build에서 측정합니다

개발 서버에는 HMR, source map, error overlay와 개발 전용 코드가 포함될 수 있으므로 bundle과 응답 크기를 운영 환경과 동일하게 해석하기 어렵습니다.

성능 예산은 가능한 한 다음 흐름의 build 결과를 대상으로 측정합니다.

```text
고정된 dependency 설치
→ 운영 build
→ 실제 start
→ browser load
→ network/DOM 측정
```

개발 서버의 숫자와 운영 서버의 숫자를 같은 기준으로 비교하지 않습니다.

## 운영 서버를 대상으로 검사합니다

브라우저 E2E가 개발 서버만 대상으로 하면 다음 문제를 놓칠 수 있습니다.

- 운영 build에서만 발생하는 module 오류
- route generation 차이
- production environment variable 문제
- 배포 output 설정 오류
- 실제 start 명령 실패
- production caching 차이
- 정적/동적 렌더링 판단 차이

따라서 핵심 브라우저 검증은 가능하면 다음 순서로 수행합니다.

```text
고정 설치
→ 정적 검사
→ 단위/API 테스트
→ 운영 build
→ 운영 start
→ smoke
→ browser E2E
```

구체적인 순서는 CI 비용과 프로젝트 규모에 따라 조정할 수 있습니다.

## `next start`를 항상 사용할 수 있다고 가정하지 않습니다

프로젝트의 배포 방식에 따라 운영 시작 명령은 다를 수 있습니다.

예를 들어 다음과 같은 경우가 있습니다.

```text
next start

standalone output의 node server.js

container entrypoint

platform 전용 start command
```

따라서 "운영 서버 테스트"의 핵심은 `next start`라는 특정 문자열이 아니라 **실제 배포 방식과 같은 build 산출물과 시작 명령을 사용하는 것**입니다.

저장소의 `package.json`, Next.js 설정, Dockerfile과 배포 구성을 기준으로 확인합니다.

## smoke와 E2E의 역할을 구분합니다

smoke 테스트는 보통 전체 기능을 깊게 검증하는 것이 아니라 배포 산출물의 핵심 경로가 살아 있는지 빠르게 확인합니다.

예를 들어 다음 정도를 검사할 수 있습니다.

```text
서버가 시작됨
GET /health → 성공
GET / → 성공
핵심 API 하나 → 예상 status
비밀값이 client response에 노출되지 않음
```

E2E는 사용자 작업을 더 깊게 검증합니다.

```text
검색
→ URL 갱신
→ 결과 표시
→ Back
→ 이전 상태 복원
```

smoke가 E2E를 대신하지 않고, E2E가 서버 시작 실패를 가장 늦은 시점에 발견하게 만들지도 않습니다.

## Playwright `webServer` 사용 시 운영 명령을 명시합니다

Playwright 같은 도구에서 `webServer`를 사용한다면 기존에 떠 있는 개발 서버를 우연히 재사용하지 않게 할 수 있습니다.

개념적으로는 다음이 중요합니다.

```text
테스트 실행마다
→ 고유한 테스트 포트
→ 운영 build의 실제 start command
→ 준비 완료 확인
→ 브라우저 테스트
```

개발 편의를 위해 로컬에서는 기존 서버를 재사용할 수 있더라도 CI에서는 새 production server를 시작하게 하는 편이 재현성을 높일 수 있습니다.

구체적인 설정은 프로젝트의 실행 방식에 맞춥니다.

## 테스트 전용 endpoint는 운영에 노출하지 않습니다

E2E에서 데이터를 초기화하기 위해 다음 기능이 필요할 수 있습니다.

```text
POST /test/reset
```

이런 endpoint가 일반 운영 환경에 열려 있으면 심각한 문제가 될 수 있습니다.

테스트 전용 기능을 둔다면 최소한 다음 조건을 고려합니다.

- 명시적인 test environment에서만 활성화
- 운영 build에서 접근 불가하거나 확실히 차단
- 인증 또는 secret token 요구
- 실제 production database를 가리키지 않음
- CI용 격리 데이터 저장소 사용

테스트 편의를 위해 운영 보안 경계를 약화시키지 않습니다.

## 불안정한 테스트 원인을 줄입니다

flaky test는 "가끔 실패하는 테스트"가 아니라 **실패 원인이 테스트 결과 외부의 타이밍이나 공유 상태에 의존하는 테스트**인 경우가 많습니다.

대표적인 원인은 다음과 같습니다.

- 고정 `sleep`
- 테스트 간 공유 데이터
- 이전 테스트가 남긴 cookie/storage
- 서버 시작 준비 전에 브라우저 접근
- request 완료 순서를 통제하지 않음
- animation 종료 시간을 임의로 예상
- 외부 API를 실제로 호출
- 테스트마다 다른 timezone/locale
- 실행 순서에 의존하는 fixture

다음 원칙으로 줄입니다.

- 시간보다 관찰 가능한 조건을 기다립니다.
- 각 테스트가 독립된 데이터에서 시작합니다.
- 필요한 cookie와 storage를 명시적으로 초기화합니다.
- network 완료 순서를 mock으로 제어합니다.
- 외부 서비스는 계약에 맞는 fake/mock을 사용합니다.
- timezone, locale이 결과에 영향을 주면 고정합니다.
- 실패 시 원인을 볼 수 있는 artifact를 보존합니다.

## 조건을 기다리고 시간을 기다리지 않습니다

다음과 같은 조건은 직접 기다릴 수 있습니다.

```text
특정 URL이 됨
특정 response가 도착함
button이 enabled가 됨
live region이 "저장 완료"로 바뀜
dialog가 사라짐
heading이 표시됨
```

예를 들어 다음 의도를 테스트 도구의 조건 기반 wait로 표현합니다.

```text
"500ms 기다린다"
```

보다

```text
"저장 완료 상태가 나타날 때까지 기다린다"
```

가 더 안정적이고 의미가 명확합니다.

## 테스트 사이의 상태를 격리합니다

테스트 A가 만든 상태가 테스트 B에 남으면 실행 순서에 따라 결과가 달라질 수 있습니다.

초기화 대상은 다음을 포함할 수 있습니다.

- database fixture
- cookie
- `localStorage`
- `sessionStorage`
- service worker 상태
- mocked route
- 로그인 session
- feature flag
- server-side cache

모든 테스트에서 모든 상태를 초기화할 필요는 없지만, 어떤 상태를 공유하는지 명시해야 합니다.

## console error와 page error를 수집합니다

UI가 겉으로는 정상처럼 보여도 browser console에 다음 문제가 발생할 수 있습니다.

- hydration 오류
- unhandled rejection
- React key 경고
- network 관련 오류
- 접근성 component 경고
- runtime exception

E2E에서 `console.error`와 page-level error를 수집하면 숨은 문제를 더 빨리 발견할 수 있습니다.

다만 애플리케이션이 의도적으로 출력하는 오류와 실제 실패를 구분할 기준이 필요합니다.

예를 들어 409 conflict를 정상적으로 처리하면서도 `console.error`를 남기는 구현이라면 테스트 정책에 따라 allowlist 또는 logging 수준 조정이 필요할 수 있습니다.

## retry는 원인 분석을 대신하지 않습니다

일시적인 infrastructure 문제 때문에 제한적인 retry가 필요할 수 있습니다. 그러나 항상 재현되는 논리 오류나 race condition을 retry로 통과시키면 실패 신호가 사라집니다.

다음 패턴을 피합니다.

```text
테스트가 가끔 실패
→ 원인 확인 없이 retry 5회
→ 대부분 통과
```

먼저 다음을 확인합니다.

- 고정 sleep이 있는가
- 공유 데이터에 의존하는가
- request 순서를 통제하지 않는가
- selector가 불안정한가
- animation 완료를 임의로 추정하는가
- 테스트 대상 서버가 실제로 준비되었는가

retry는 마지막 안전망이지 동기화 방법이 아닙니다.

## 실패 artifact를 보존합니다

브라우저 테스트가 CI에서만 실패하면 당시 상태를 재현하기 어려울 수 있습니다.

실패 시 다음 artifact가 도움이 됩니다.

- trace
- screenshot
- video
- browser console
- page error
- network 기록
- application server stdout/stderr
- 테스트가 사용한 URL과 주요 fixture 정보

모든 artifact를 항상 영구 보관할 필요는 없지만 실패한 실행에서는 원인 분석에 필요한 정보를 남깁니다.

## 테스트 이름에는 사용자 계약을 드러냅니다

다음 이름보다

```text
calls runSearch twice
```

다음 이름이 더 많은 정보를 줍니다.

```text
keeps the newest search result
when an older request finishes later
```

또는 한국어 프로젝트라면 다음처럼 표현할 수 있습니다.

```text
이전 검색 응답이 늦게 도착해도
최신 검색 결과를 유지한다
```

테스트 이름만 읽어도 어떤 위험을 막는지 알 수 있게 합니다.

## 테스트 실패가 무엇을 의미하는지 구분합니다

같은 기능을 여러 수준에서 검사할 때 실패 원인을 빠르게 좁힐 수 있어야 합니다.

예를 들어 다음 순서로 생각합니다.

```text
parser 단위 테스트 실패
→ 입력 정규화 규칙 문제 가능성

Route Handler 테스트 실패
→ HTTP 계약 또는 service 연결 문제 가능성

운영 build 실패
→ module graph, type, build 설정 문제 가능성

E2E만 실패
→ browser history, focus, CSS, 실제 navigation 문제 가능성
```

이렇게 테스트가 실패 위치를 좁혀 주어야 디버깅 비용이 줄어듭니다.

## 구현 전 테스트 계획 예시

검색과 제목 편집 기능을 구현한다고 가정하면 다음 정도의 테스트 계획을 만들 수 있습니다.

| 위험 | 테스트 위치 | 핵심 검증 |
| --- | --- | --- |
| 잘못된 query 정규화 | parser 단위 테스트 | 잘못된 page/status가 기본값이 됨 |
| 중복 id 응답 | response parser 단위 테스트 | 계약 오류로 거부 |
| 이전 검색이 최신 결과 덮음 | coordinator + E2E | 오래된 결과 폐기 |
| Back에서 상태 미복원 | 브라우저 E2E | URL·입력·결과 복원 |
| 일반 저장 실패에서 초안 손실 | 상태 테스트 + E2E | rollback + draft 유지 |
| conflict에서 최신 서버 값 손실 | 상태 테스트 + E2E | 서버 최신값 + draft 유지 |
| 저장 후 focus 손실 | 브라우저 E2E | 시작 버튼으로 복귀 |
| 좁은 화면 overflow | 브라우저 layout 테스트 | page overflow 없음 |
| Client JS 급증 | production budget | baseline 대비 예산 이내 |
| production start 실패 | smoke | 실제 start 후 핵심 route 성공 |

이 표가 있으면 "E2E를 몇 개 만들까?"보다 어떤 계약이 아직 검증되지 않았는지 쉽게 알 수 있습니다.

## 적용 완료 기준

실제 프로젝트의 해당 기능에서 다음 내용을 확인합니다.

- 가장 큰 사용자 위험과 이를 검출할 테스트를 먼저 적었습니다.
- 각 테스트가 잡아야 할 잘못된 구현을 한 문장으로 설명할 수 있습니다.
- parser, validation, 상태 전이와 요청 수명은 가능한 범위에서 DOM 없이 검사합니다.
- Route Handler의 입력, status code와 response body를 직접 검사합니다.
- type generation이 필요하다면 clean checkout과 CI에서 재현 가능한 script로 실행합니다.
- 응답 완료 순서를 고정 `sleep` 없이 직접 제어합니다.
- 이전 요청의 abort 여부와 오래된 결과 폐기를 서로 다른 계약으로 검사합니다.
- 오래된 성공뿐 아니라 오래된 실패도 최신 화면을 덮지 않는지 확인합니다.
- component unmount 뒤 이전 요청 결과가 반영되지 않는지 확인합니다.
- 일반 저장 실패와 `409 Conflict`를 서로 다른 상태 전이로 검사합니다.
- automated accessibility 검사와 실제 keyboard flow를 함께 사용합니다.
- keyboard만으로 주요 작업을 처음부터 끝까지 완료할 수 있습니다.
- 편집 시작, 취소, 성공, 일반 실패와 충돌에서 focus 위치를 확인합니다.
- 반복 control이 구분 가능한 accessible name을 가집니다.
- 중요한 비동기 상태 변화가 필요한 경우 보조 기술에 전달됩니다.
- 좁은 viewport, 확대에 준하는 layout 압력과 긴 문자열에서 중요한 UI를 사용할 수 있습니다.
- 페이지 전체의 의도치 않은 가로 넘침과 component 내부의 의도된 scroll을 구분합니다.
- motion 감소 설정이 실제 style과 동작에 반영됩니다.
- JavaScript와 DOM 예산의 측정 정의와 baseline을 기록했습니다.
- 성능 예산은 개발 서버가 아니라 운영 build를 기준으로 검사합니다.
- 프로젝트의 실제 배포 방식과 같은 start 명령으로 서버를 실행합니다.
- smoke와 E2E가 서로 다른 역할을 담당합니다.
- 테스트 전용 데이터 초기화 기능이 운영 환경에 노출되지 않습니다.
- 고정 sleep, 공유 상태와 외부 환경 의존성을 줄였습니다.
- retry로 논리 오류나 race condition을 숨기지 않습니다.
- 실패한 브라우저 테스트에서 trace, screenshot, console과 서버 출력을 확인할 수 있습니다.

프로젝트에 해당 문제가 없다면 이 문서를 선행 조건으로 만들지 않습니다. 실제 기능에서 해당 위험이 생겼거나 역량 검증 프로그램에서 관련 테스트가 실패한 경우에만 필요한 절을 다시 읽습니다.
