# 테스트, 접근성·성능 확인

테스트의 목적은 개수를 늘리는 것이 아닙니다. 변경으로 깨질 수 있는 동작을 가장 낮고 결정적인 위치에서 잡아야 합니다. 형 검사, 순수 함수 테스트, Route Handler 테스트, 운영 빌드와 실제 브라우저는 서로 다른 오류를 발견합니다.

이 문서는 실제 프로젝트에서 테스트 위치를 정하거나 키보드·반응형·성능 문제를 확인해야 할 때 JIT로 읽습니다.

## 목표

이 문서를 읽은 뒤에는 다음 작업을 수행할 수 있어야 합니다.

- 기능의 주요 위험을 먼저 적고 적절한 테스트 위치를 고릅니다.
- 고정된 sleep 없이 응답 순서와 실패를 재현합니다.
- accessible name, 키보드 조작과 초점 이동을 실제 브라우저에서 확인합니다.
- 320px 화면, 200% 확대, 긴 문자열과 motion 감소 설정을 검사합니다.
- JavaScript 응답 크기와 DOM element 수에 예산을 둡니다.
- 개발 서버가 아닌 운영 빌드와 운영 서버를 테스트합니다.

## 구현 파일보다 위험을 먼저 적습니다

| 위험 | 사용자에게 생기는 문제 | 먼저 사용할 테스트 |
| --- | --- | --- |
| URL과 입력값이 어긋남 | 공유, 새로 고침과 뒤로 이동이 깨짐 | query 단위 테스트 + 브라우저 이동 |
| 잘못된 응답을 믿음 | 잘못된 화면 또는 실행 중 오류 | 응답 검사 단위 테스트 + route mock |
| 이전 응답이 최신 결과를 덮음 | 사용자가 다른 검색 결과를 봄 | 응답 순서를 제어한 브라우저 테스트 |
| 충돌에서 입력 초안을 잃음 | 사용자가 작성한 내용이 사라짐 | 저장 실패 브라우저 테스트 |
| 취소 뒤 초점을 잃음 | 키보드 사용자가 다음 위치를 찾지 못함 | 운영 브라우저 테스트 |
| Client Component 범위가 커짐 | 초기 JavaScript가 불필요하게 증가 | 운영 빌드의 응답 크기 예산 |

각 테스트가 어떤 잘못된 구현을 잡는지 한 문장으로 설명할 수 있어야 합니다. 내부 함수 호출 횟수만 확인하고 사용자 결과를 놓치지 않습니다.

## 테스트 위치를 나눕니다

| 검사 방법 | 잘 잡는 문제 | 직접 확인하기 어려운 문제 |
| --- | --- | --- |
| 정적 검사 | syntax, type, 빠진 분기 | 외부 응답의 실제 형식 |
| route type + typecheck | Next.js route signature, module 분리 | 브라우저 동작 |
| 순수 단위 테스트 | parser, 상태 전이, 요청 수명 | DOM, layout, history |
| Route Handler 테스트 | 상태 코드, 응답 본문, 입력 검사 | 실제 bundle과 초점 |
| 운영 빌드 | Server/Client module 구성, route 생성 | 실제 사용자 조작 |
| 브라우저 E2E | history, network, 초점, viewport | 내부 알고리즘의 모든 경곗값 |
| standalone smoke | 실제 start, health, release, 비밀값 비노출 | 복잡한 전체 사용자 시나리오 |

순수 함수로 충분히 잡을 수 있는 오류를 E2E로만 검사하지 않습니다. 반대로 초점, 가로 넘침과 browser history를 DOM 모방 환경만으로 단정하지 않습니다.

## Route type을 만든 뒤 형 검사합니다

Next.js의 route와 navigation type은 생성 파일에 의존할 수 있습니다. 깨끗한 checkout에서도 형 검사가 재현되도록 type generation을 script에 포함합니다.

```json
{
  "scripts": {
    "typecheck": "next typegen && tsc --noEmit"
  }
}
```

생성 디렉터리는 commit하지 않더라도 개발자와 CI가 같은 명령으로 다시 만들 수 있어야 합니다.

## 네트워크 테스트에서는 시간을 직접 제어합니다

다음처럼 일정 시간을 기다리는 테스트는 실행 환경에 따라 실패할 수 있습니다.

```ts
await new Promise((resolve) => setTimeout(resolve, 500));
```

느린 환경에서는 시간이 부족하고 빠른 환경에서는 불필요하게 기다립니다. 테스트가 응답을 보류하고 원하는 순서대로 해제하는 편이 결정적입니다.

```ts
let releaseSlow: (() => void) | undefined;
const slowRequest = new Promise<void>((resolve) => {
  releaseSlow = resolve;
});

await page.route("**/api/projects?*", async (route) => {
  const query = new URL(route.request().url()).searchParams.get("q");
  if (query === "old") await slowRequest;
  await route.continue();
});
```

검사 순서는 다음과 같습니다.

```text
old 요청의 응답을 보류
→ new 요청을 시작하고 결과 확인
→ old 응답을 해제
→ 화면이 new 결과를 유지하는지 확인
```

요청 signal이 abort되었는지와 늦은 결과가 화면에 반영되지 않았는지는 서로 다른 내용입니다. 가능하면 둘 다 확인합니다.

## 예상하지 않은 애플리케이션 요청을 찾습니다

네트워크 mock은 예상한 API 요청에만 응답하고, 같은 범위에서 발생한 예상 밖의 애플리케이션 요청은 실패로 처리할 수 있습니다. 잘못된 URL, 중복 fetch와 숨은 analytics 호출을 빨리 발견하는 데 도움이 됩니다.

framework asset, HMR와 브라우저 자체 요청까지 모두 막지 않습니다. 운영 서버에서 애플리케이션 API 경로를 구체적으로 지정합니다.

## 접근성은 HTML과 시간에 따른 동작을 함께 봅니다

자동 검사 도구는 이름이 없는 control과 잘못된 ARIA를 잘 찾지만, 상태가 바뀐 뒤 초점이 어디로 가야 하는지까지 판단하지는 못합니다.

### 의미에 맞는 HTML

- 페이지의 주요 내용은 `<main>`에 둡니다.
- heading 순서를 논리적으로 유지합니다.
- 검색 폼과 입력 요소에 연결된 `label`을 둡니다.
- 이동에는 link, 동작에는 button을 사용합니다.
- 반복 항목은 list와 article로 표현합니다.
- 대기, 실패와 저장 결과는 live region으로 알립니다.

### 키보드와 초점

편집 동작을 실제 키보드로 확인합니다.

```text
Tab으로 “제목 수정”에 도달
→ Enter로 편집기 열기
→ 입력칸에 초점
→ 초안 입력
→ Escape 또는 취소
→ 처음의 수정 버튼으로 초점 복귀
```

저장 성공 뒤에도 수정 버튼으로 돌아갈 수 있어야 합니다. 일반 실패와 충돌에서는 편집기를 유지하므로 입력칸 초점과 초안도 유지합니다.

`autoFocus`만으로 전체 동작이 해결되었다고 보지 않습니다. 조건부로 나타나는 편집기, dialog와 화면 이동 뒤 초점 위치를 사용자 작업 순서에 맞춰 정합니다.

### 눈에 보이는 초점

초점이 있어도 화면에서 구분되지 않으면 키보드 사용자는 현재 위치를 알 수 없습니다. 실제 computed style에서 outline의 너비, 종류와 색이 사라지지 않았는지 확인합니다.

## 좁은 화면과 확대를 함께 확인합니다

반응형 화면은 device width만 확인해서는 부족합니다. 200% 확대는 사용할 수 있는 CSS viewport를 줄이고 글자와 control을 키웁니다.

권장 확인 조건:

- `320px × 720px`
- `640px` viewport에서 200% 확대
- 공백 없는 80자 제목
- 브라우저 기본 글자 크기 확대
- input과 select의 긴 값

페이지 전체의 가로 넘침은 다음처럼 확인할 수 있습니다.

```ts
await page.evaluate(() =>
  document.documentElement.scrollWidth <=
  document.documentElement.clientWidth,
);
```

페이지 전체뿐 아니라 article, heading와 폼 요소의 위치도 viewport 안에 있는지 확인합니다.

CSS에서 자주 필요한 기본값은 다음과 같습니다.

```css
*,
*::before,
*::after {
  box-sizing: border-box;
}

input,
select,
textarea {
  min-width: 0;
  max-width: 100%;
}

article {
  overflow-wrap: anywhere;
}
```

## Motion 감소 설정을 실제 style로 확인합니다

CSS 파일에 media query 문자열이 있는지만 검사하지 않습니다. 브라우저에서 motion 감소 설정을 켜고 transition과 animation의 계산된 시간이 사실상 0인지 확인합니다.

```ts
await page.emulateMedia({ reducedMotion: "reduce" });
```

기능 이해에 필요한 상태 변화까지 없앨 필요는 없지만 장식적인 움직임은 줄여야 합니다.

## 성능 예산은 회귀가 생기기 전에 정합니다

작은 프로젝트에서는 환경 차이에 덜 민감한 값부터 사용할 수 있습니다.

```json
{
  "maximumInitialJavaScriptBytes": 800000,
  "maximumDomNodes": 180
}
```

- JavaScript 예산은 첫 route가 요청한 script 응답 본문의 합계를 측정합니다.
- DOM 예산은 첫 화면의 element 수를 측정합니다.

이 값이 전송 압축 크기, JavaScript 실행 시간과 실제 사용자 지표를 모두 대신하지는 않습니다. 다만 작은 기능 때문에 Client Component 범위가 넓어지거나 DOM이 급증하는 회귀를 빠르게 찾을 수 있습니다.

예산 숫자를 영구적인 기준으로 취급하지 않습니다. 대표 device와 network, 실제 사용자 측정값을 근거로 변경합니다.

## 운영 서버를 대상으로 검사합니다

개발 서버는 오류 overlay, HMR과 개발 전용 동작을 포함합니다. 브라우저 E2E는 빌드한 결과를 실제 start 명령으로 실행해 검사합니다.

```text
고정 설치
→ 형 검사와 단위 테스트
→ next build
→ next start
→ 브라우저 E2E
```

Playwright의 `webServer`는 기존 개발 서버를 재사용하지 않고 매 실행에서 고유 포트의 운영 서버를 시작하게 할 수 있습니다. 실패하면 trace, screenshot, video와 서버 출력을 보존합니다. 테스트 데이터 초기화 endpoint는 명시적인 테스트 모드와 token이 있을 때만 열어야 합니다.

## 불안정한 테스트 원인을 줄입니다

- 고정 sleep 대신 URL, 응답, live region과 DOM 상태를 기다립니다.
- 각 테스트가 같은 서버 데이터에서 시작하게 합니다.
- cookie, local/session storage와 route mock을 테스트 사이에 초기화합니다.
- 브라우저 console error와 page error를 수집합니다.
- 항상 재현되는 오류를 retry로 숨기지 않습니다.
- 실패한 실행의 trace, screenshot과 서버 출력을 보존합니다.

## 적용 완료 기준

실제 프로젝트의 해당 기능에서 다음 내용을 확인합니다.

- 가장 큰 사용자 위험과 이를 검출할 테스트를 먼저 적었습니다.
- parser, 상태 전이와 요청 수명은 DOM 없이 검사합니다.
- Route Handler의 입력, 상태 코드와 응답 본문을 직접 검사합니다.
- 응답 순서를 고정 sleep 없이 제어합니다.
- 키보드만으로 주요 작업을 완료할 수 있습니다.
- 취소와 성공 뒤 초점을 시작 요소로 돌립니다.
- 실패와 충돌에서는 입력 초안과 초점을 유지합니다.
- 320px, 200% 확대와 긴 문자열에서 가로 넘침이 없습니다.
- motion 감소 설정이 computed style에 반영됩니다.
- 초기 JavaScript와 DOM이 정한 예산을 넘지 않습니다.
- 운영 빌드와 운영 서버에서 브라우저 테스트가 통과합니다.

프로젝트에 해당 문제가 없다면 이 문서를 선행 조건으로 만들지 않습니다. 역량 검증 프로그램에서 관련 테스트가 실패한 경우에만 해당 절을 다시 읽습니다.
