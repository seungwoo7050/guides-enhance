# HTML 폼과 접근성

HTML 요소는 화면 모양만 정하는 태그가 아닙니다. 링크, 버튼, 입력 필드, 제목, `header`, `nav`, `main` 같은 요소에는 브라우저와 보조 기술이 이해하는 **의미(semantic)** 와 기본 동작이 있습니다.

예를 들어 `<button>`은 기본적으로 키보드 포커스를 받을 수 있고 Enter나 Space로 활성화할 수 있으며, 스크린 리더는 이를 버튼으로 알립니다. 같은 모양을 `<div>`로 만든 뒤 클릭 이벤트만 붙이면 이런 동작과 의미를 직접 다시 구현해야 합니다.

따라서 접근성의 출발점은 ARIA 속성을 많이 추가하는 것이 아니라 **용도에 맞는 기본 HTML 요소를 먼저 사용하는 것**입니다.

이 문서는 폼이나 복잡한 화면을 구현하기 직전에 읽는 JIT 문서입니다.

## 목표

- 문서의 주요 영역과 제목 순서를 의미에 맞게 구성합니다.
- 이동에는 링크, 현재 화면의 동작에는 버튼을 사용합니다.
- 입력 요소에 사용자가 볼 수 있는 레이블을 연결합니다.
- 버튼의 `click`이 아니라 폼의 `submit` 동작을 중심으로 제출을 구현합니다.
- 키보드 사용자가 현재 포커스 위치를 알 수 있게 합니다.
- 비동기 진행 상태와 오류를 시각 사용자와 보조 기술 사용자 모두에게 전달합니다.
- 기본 HTML 요소와 ARIA의 역할 차이를 설명합니다.

## 의미론적 HTML을 먼저 사용합니다

브라우저는 HTML 요소의 이름을 단순한 스타일 표시로만 해석하지 않습니다.

예를 들어 다음 요소들은 각각 기본 의미를 가집니다.

| 요소 | 기본 의미 |
|---|---|
| `<header>` | 페이지나 구역의 머리말 |
| `<nav>` | 주요 탐색 링크 묶음 |
| `<main>` | 페이지의 핵심 콘텐츠 |
| `<h1>`~`<h6>` | 내용의 제목과 계층 |
| `<a href="...">` | 다른 위치로 이동하는 링크 |
| `<button>` | 사용자가 실행하는 동작 |
| `<label>` | 폼 입력 요소의 이름 |
| `<form>` | 하나의 제출 가능한 입력 묶음 |

이 의미는 CSS를 제거해도 남고, 키보드 동작과 접근성 트리에도 영향을 줍니다.

ARIA는 부족한 의미를 보완하기 위한 도구입니다. 이미 적절한 HTML 요소가 의미를 제공한다면 같은 의미의 ARIA 역할을 반복해서 붙이지 않습니다.

```html
<!-- 불필요합니다. -->
<button role="button">저장</button>
```

다음이면 충분합니다.

```html
<button type="button">저장</button>
```

기본 HTML 요소로 표현할 수 없는 사용자 인터페이스를 만들 때만 ARIA가 필요한지 검토합니다.

## 문서의 기본 요소

```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>내 작업</title>
</head>
<body>
  <header>
    <nav aria-label="주 메뉴">
      <a aria-current="page" href="/">작업</a>
    </nav>
  </header>

  <main id="main">
    <h1>내 작업</h1>
  </main>
</body>
</html>
```

각 부분의 의미는 다음과 같습니다.

### `lang`

```html
<html lang="ko">
```

`lang`은 문서의 기본 언어를 나타냅니다.

보조 기술은 이 정보를 사용해 적절한 발음 규칙을 선택할 수 있습니다. 페이지 내용이 한국어인데 `lang="en"`으로 잘못 지정하면 스크린 리더가 문장을 부자연스럽게 읽을 수 있습니다.

### `title`

```html
<title>내 작업</title>
```

`title`은 브라우저 탭, 방문 기록, 북마크 등에서 페이지를 식별하는 이름으로 사용됩니다.

페이지 안의 `<h1>`과 역할이 다릅니다.

```text
<title> → 브라우저와 문서 자체를 식별하는 이름
<h1>    → 현재 문서 내용의 최상위 제목
```

둘이 완전히 같은 문자열일 필요는 없지만 사용자가 서로 다른 페이지를 구분할 수 있도록 의미 있는 이름을 사용합니다.

### `main`

```html
<main id="main">
  ...
</main>
```

`main`은 페이지의 핵심 콘텐츠를 나타냅니다.

페이지 전체에 반복되는 사이트 헤더, 주 탐색, 푸터와 달리 해당 페이지의 주된 내용을 포함합니다.

### `nav`

```html
<nav aria-label="주 메뉴">
  ...
</nav>
```

`nav`는 주요 탐색 링크의 묶음을 나타냅니다.

한 페이지에 `nav`가 여러 개 있다면 각각의 목적을 구분할 수 있도록 이름을 붙이는 것이 유용합니다.

```html
<nav aria-label="주 메뉴">...</nav>
<nav aria-label="문서 목차">...</nav>
```

`aria-label`은 화면에 별도의 제목이 없는 탐색 영역에 접근 가능한 이름을 제공하는 방법입니다.

### `aria-current`

```html
<a aria-current="page" href="/">작업</a>
```

`aria-current="page"`는 여러 링크 중 현재 페이지에 해당하는 링크를 나타냅니다.

단순히 글자 색만 다르게 표시하는 것보다 현재 위치라는 상태를 보조 기술에도 전달할 수 있습니다.

## 제목은 내용의 계층을 나타냅니다

제목 요소는 글자 크기를 정하기 위한 도구가 아니라 문서의 구조를 나타냅니다.

```html
<h1>보드 설정</h1>

<section>
  <h2>구성원</h2>

  <article>
    <h3>Kim</h3>
  </article>
</section>
```

구조를 읽으면 다음과 같습니다.

```text
보드 설정
└─ 구성원
   └─ Kim
```

`h1`, `h2`, `h3`의 시각적 크기가 마음에 들지 않는다면 제목 단계를 바꾸는 대신 CSS로 모양을 조정합니다.

```css
h2 {
  font-size: 1.25rem;
}
```

다음처럼 단지 작게 보이게 하려고 계층을 건너뛰는 것은 피합니다.

```html
<h1>보드 설정</h1>
<h4>구성원</h4>
```

제목 단계는 **이 내용이 어느 제목 아래에 속하는가**를 기준으로 정합니다.

## 링크와 버튼

링크와 버튼은 겉모양이 비슷할 수 있지만 목적이 다릅니다.

```html
<a href="/boards/42">보드 열기</a>
<button type="button">메모 추가</button>
```

기본 기준은 다음과 같습니다.

```text
다른 주소나 위치로 이동한다 → 링크
현재 화면에서 동작을 실행한다 → 버튼
```

### 링크

링크는 다른 URL이나 문서 위치로 이동할 때 사용합니다.

```html
<a href="/boards/42">보드 열기</a>
<a href="#members">구성원으로 이동</a>
```

클라이언트 사이드 라우터를 사용하는 애플리케이션이라도 사용자 관점에서 "다른 페이지나 주소로 이동"하는 동작이라면 링크 의미를 유지하는 것이 좋습니다.

실제 링크로 동작하려면 일반적으로 `href`가 있어야 합니다.

```html
<!-- 이동 대상이 없는 요소는 링크로 사용하지 않습니다. -->
<a onclick="save()">저장</a>
```

이런 작업에는 버튼이 더 적절합니다.

```html
<button type="button">저장</button>
```

### 버튼

버튼은 현재 화면에서 작업을 실행하거나 상태를 변경할 때 사용합니다.

```html
<button type="button">메모 추가</button>
<button type="button">메뉴 열기</button>
<button type="button">삭제</button>
```

버튼을 사용하면 브라우저가 기본적으로 포커스와 키보드 활성화 동작을 제공합니다.

### 폼 안의 버튼 타입

폼과 연결된 `<button>`은 `type`을 생략하면 기본적으로 제출 버튼으로 동작할 수 있습니다.

```html
<form>
  <input name="title" />

  <!-- 폼 제출 -->
  <button type="submit">저장</button>

  <!-- 폼을 제출하지 않는 동작 -->
  <button type="button">미리보기</button>
</form>
```

제출용이 아닌 버튼에는 `type="button"`을 명시하면 의도하지 않은 폼 제출을 막을 수 있습니다.

### 클릭 가능한 `div`가 문제가 되는 이유

다음 코드는 마우스 클릭만 생각한 구현입니다.

```html
<div id="add-note">메모 추가</div>
```

```js
document.querySelector("#add-note")?.addEventListener("click", addNote);
```

`div`는 본래 버튼이 아니므로 다음 기능이 자동으로 제공되지 않습니다.

- 키보드 탭 순서에 포함되는 포커스
- Enter 또는 Space를 사용한 버튼 활성화
- 버튼이라는 역할
- `disabled` 상태
- 버튼에 기대되는 브라우저 기본 동작

필요한 기본 요소가 있다면 다음처럼 사용하는 편이 더 단순하고 안전합니다.

```html
<button type="button">메모 추가</button>
```

## 레이블과 입력 요소

폼 입력에는 사용자가 해당 입력이 무엇인지 알 수 있는 이름이 필요합니다.

플레이스홀더는 입력 예시나 보조 설명일 수 있지만 레이블을 대신하지 않습니다.

```html
<form id="task-form">
  <label for="task-title">새 작업</label>
  <input
    id="task-title"
    name="title"
    type="text"
    autocomplete="off"
  />
  <button type="submit">추가</button>
</form>
```

`label`의 `for` 값과 입력 요소의 `id`를 같은 값으로 연결합니다.

```text
<label for="task-title">
             │
             └─────────────┐
                           ▼
<input id="task-title">
```

이렇게 연결하면 다음 이점이 있습니다.

- 레이블을 클릭하면 해당 입력 요소에 포커스가 이동합니다.
- 스크린 리더가 입력 요소의 이름으로 레이블을 사용할 수 있습니다.
- 테스트에서도 사용자가 보는 레이블을 기준으로 입력을 찾기 쉬워집니다.

### 레이블 안에 입력을 넣을 수도 있습니다

다음 형태도 레이블과 입력을 연결합니다.

```html
<label>
  새 작업
  <input name="title" type="text" />
</label>
```

프로젝트에서 한 방식을 일관되게 사용하면 됩니다.

### 플레이스홀더는 레이블이 아닙니다

다음처럼 플레이스홀더만 두는 것은 피합니다.

```html
<input type="email" placeholder="name@example.com" />
```

입력을 시작하면 플레이스홀더가 사라지므로 사용자가 입력 목적을 다시 확인하기 어렵습니다.

대신 이름은 레이블로 제공하고 플레이스홀더는 필요한 경우 예시로 사용합니다.

```html
<label for="email">이메일</label>
<input
  id="email"
  name="email"
  type="email"
  placeholder="name@example.com"
/>
```

### `name`과 `id`는 목적이 다릅니다

예제에서 `id`와 `name`이 함께 사용되므로 둘의 역할을 구분해야 합니다.

```html
<label for="task-title">새 작업</label>
<input id="task-title" name="title" />
```

- `id`는 문서 안에서 요소를 식별하고 `label for` 같은 참조에 사용합니다.
- `name`은 폼을 제출할 때 값의 이름으로 사용됩니다.

예를 들어 다음 입력에

```html
<input name="title" value="문서 작성" />
```

`FormData`를 만들면 대략 다음과 같은 이름과 값이 포함됩니다.

```text
title = 문서 작성
```

레이블 연결에 `name`이 아니라 `id`를 사용하는 이유가 여기에 있습니다.

## 필수 입력과 오류 설명

브라우저의 기본 폼 속성을 활용할 수 있는 경우 먼저 사용합니다.

```html
<label for="email">이메일</label>
<input
  id="email"
  name="email"
  type="email"
  required
/>
```

`required`는 해당 입력이 필수임을 브라우저에 알립니다. `type="email"`은 이메일 형식에 맞는 입력이라는 의미를 제공합니다.

다만 브라우저 검증은 서버 검증을 대신하지 않습니다. 브라우저 요청은 사용자가 직접 수정할 수 있으므로 서버에서도 같은 비즈니스 규칙을 다시 확인해야 합니다.

### 오류 메시지를 입력과 연결합니다

검증에 실패한 뒤 오류 메시지를 보여 준다면 오류 상태와 설명을 입력에 연결할 수 있습니다.

```html
<label for="email">이메일</label>
<input
  id="email"
  name="email"
  type="email"
  aria-invalid="true"
  aria-describedby="email-error"
/>
<p id="email-error">이메일 형식을 확인해 주세요.</p>
```

각 속성의 의미는 다음과 같습니다.

- `aria-invalid="true"`: 현재 입력값이 유효하지 않음을 전달합니다.
- `aria-describedby="email-error"`: `email-error` 요소의 텍스트를 입력에 대한 추가 설명으로 연결합니다.

오류가 없는 초기 상태부터 무조건 `aria-invalid="true"`를 두면 안 됩니다. 실제로 검증에 실패한 상태에서 사용합니다.

예를 들어 초기 상태는 다음과 같을 수 있습니다.

```html
<input id="email" name="email" type="email" />
```

검증 실패 후에는 다음 상태가 됩니다.

```html
<input
  id="email"
  name="email"
  type="email"
  aria-invalid="true"
  aria-describedby="email-error"
/>
<p id="email-error">이메일 형식을 확인해 주세요.</p>
```

오류 메시지는 색만 바꾸지 말고 사람이 읽을 수 있는 텍스트로도 제공합니다.

## 폼 제출

폼 제출 로직은 제출 버튼의 `click`보다 폼의 `submit` 이벤트를 중심으로 작성합니다.

```js
const form = document.querySelector("#task-form");

form?.addEventListener("submit", (event) => {
  event.preventDefault();

  const data = new FormData(event.currentTarget);

  // 입력을 검증하고 저장합니다.
});
```

이 방식이 중요한 이유는 **폼 제출이 버튼 클릭으로만 발생하는 것이 아니기 때문**입니다.

사용자는 상황에 따라 입력 필드에서 Enter 키를 눌러 폼을 제출할 수 있습니다.

```text
제출 버튼 클릭 ─┐
                ├─→ form의 submit 이벤트
Enter 키 제출 ──┘
```

버튼의 `click`만 처리하면 키보드 제출 경로와 동작이 달라질 수 있습니다.

폼의 `submit`을 처리하면 여러 제출 방법을 하나의 로직으로 모을 수 있습니다.

### 기본 HTML 제출도 폼의 기능입니다

JavaScript가 반드시 있어야 폼을 제출할 수 있는 것은 아닙니다.

다음 폼은 브라우저의 기본 제출 기능을 사용합니다.

```html
<form action="/tasks" method="post">
  <label for="task-title">새 작업</label>
  <input id="task-title" name="title" />

  <button type="submit">추가</button>
</form>
```

JavaScript를 사용하는 애플리케이션에서는 보통 `submit` 이벤트에서 `event.preventDefault()`를 호출하고 API 요청을 직접 보내지만, 이것은 **브라우저의 기본 폼 제출을 대체하는 것**입니다.

따라서 `preventDefault()`는 이유 없이 붙이는 코드가 아니라 "이번 폼은 기본 페이지 이동 대신 JavaScript로 제출하겠다"는 의미입니다.

## 포커스

포커스는 현재 키보드 입력을 받을 요소를 나타냅니다.

마우스 포인터를 볼 수 없는 상황에서 키보드 사용자는 포커스 표시를 통해 현재 위치를 파악합니다.

브라우저의 기본 포커스 표시를 제거한다면 반드시 그보다 명확한 표시로 대체해야 합니다.

```css
:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 3px;
}
```

다음처럼 단순히 제거하는 것은 피합니다.

```css
:focus {
  outline: none;
}
```

대체 표시가 없다면 키보드 사용자는 현재 어느 요소를 조작하고 있는지 알기 어려워집니다.

### 포커스 순서를 억지로 만들지 않습니다

기본 HTML 요소를 문서의 자연스러운 순서대로 배치하면 브라우저가 일반적으로 적절한 탭 순서를 만듭니다.

```html
<a href="/boards">보드</a>
<button type="button">추가</button>
<input type="text" />
```

큰 양수의 `tabindex`로 순서를 억지로 재배치하는 방식은 유지보수를 어렵게 만듭니다.

가능하면 DOM 순서 자체를 사용자가 읽고 조작하는 순서와 맞춥니다.

## 건너뛰기 링크

페이지마다 반복되는 탐색 항목이 많으면 키보드 사용자는 매번 같은 링크를 모두 지나야 본문에 도달합니다.

건너뛰기 링크는 반복 영역을 건너뛰고 주요 콘텐츠로 이동할 수 있게 합니다.

```html
<a class="skip-link" href="#main">본문으로 건너뛰기</a>

<header>
  ...
</header>

<main id="main" tabindex="-1">
  <h1>내 작업</h1>
</main>
```

`href="#main"`은 `id="main"`인 위치로 이동합니다.

`tabindex="-1"`은 해당 요소를 일반적인 Tab 순서에 추가하지 않으면서 필요할 때 포커스 대상으로 사용할 수 있게 합니다. 건너뛰기 링크 구현에서 실제로 주요 콘텐츠로 포커스를 이동시키려는 경우 사용할 수 있습니다.

건너뛰기 링크는 평소에는 화면 밖에 두었다가 키보드 포커스를 받으면 보이도록 만드는 패턴도 자주 사용합니다.

중요한 점은 링크가 키보드로 접근 가능하고, 활성화했을 때 사용자가 반복 영역을 실제로 건너뛸 수 있어야 한다는 것입니다.

## 동적으로 열린 UI와 포커스

모달 같은 UI는 단순히 화면 위에 표시하는 것만으로 키보드 조작이 완성되지 않습니다.

일반적으로 다음 흐름을 고려해야 합니다.

```text
모달 열기
  ↓
모달 안의 적절한 위치로 포커스 이동
  ↓
모달 안에서 작업
  ↓
모달 닫기
  ↓
모달을 열었던 요소로 포커스 복원
```

예를 들어 사용자가 다음 버튼으로 모달을 열었다면

```html
<button type="button" id="open-settings">설정 열기</button>
```

모달을 닫은 뒤 사용자가 페이지의 어디로 돌아왔는지 알 수 있도록 이 버튼으로 포커스를 되돌리는 것이 자연스럽습니다.

복잡한 모달은 포커스 이동뿐 아니라 배경 콘텐츠와의 상호작용 제한, Escape 처리, 접근 가능한 이름 등 추가 규칙이 필요합니다. 이 문서에서는 우선 **열고 닫을 때 포커스가 사라지지 않도록 관리해야 한다**는 점을 기억합니다.

## 진행 상태와 오류

비동기 요청은 화면이 그대로인 동안 진행되거나 실패할 수 있습니다.

예를 들어 저장 버튼을 눌렀을 때 다음 상태가 생길 수 있습니다.

```text
저장 시작
  ↓
저장 중
  ↓
성공 또는 실패
```

시각적으로 텍스트를 바꾸는 것만으로는 모든 사용자가 상태 변화를 알 수 있는 것은 아닙니다. 필요한 경우 라이브 영역을 사용해 동적으로 바뀐 상태를 보조 기술에도 전달합니다.

### 일반적인 상태

```html
<p role="status">저장 중입니다.</p>
```

`role="status"`는 일반적인 상태 메시지를 전달할 때 사용합니다. 이 역할에는 보통 정중하게 알리는 라이브 영역 동작이 포함되어 있으므로 같은 요소에 `aria-live="polite"`를 반복해서 지정할 필요는 없습니다.

예를 들어 다음과 같은 메시지에 사용할 수 있습니다.

```text
저장 중입니다.
3개의 결과를 찾았습니다.
저장했습니다.
```

### 즉시 알려야 하는 오류

```html
<p role="alert">저장하지 못했습니다.</p>
```

`role="alert"`는 사용자가 즉시 알아야 하는 중요한 오류나 경고에 사용합니다.

`alert`는 강하게 알리는 라이브 영역 의미를 가지므로 모든 작은 상태 변화에 사용하면 안 됩니다.

```text
일반적인 진행·결과 → role="status"
즉시 알려야 할 오류 → role="alert"
```

모든 텍스트를 라이브 영역으로 만들면 화면이 조금만 바뀌어도 알림이 반복되어 오히려 내용을 이해하기 어려워질 수 있습니다.

### 라이브 영역은 동적 변화에 사용합니다

라이브 영역의 주된 목적은 **화면이 이미 열린 뒤 내용이 동적으로 바뀌었음을 알리는 것**입니다.

페이지를 처음부터 읽으면 자연스럽게 접할 수 있는 모든 정적 텍스트에 `role="status"`나 `role="alert"`를 붙일 필요는 없습니다.

## 색만으로 상태를 전달하지 않습니다

다음처럼 색만 바꾸면 색을 구분하기 어려운 사용자는 상태를 알 수 없습니다.

```text
초록색 → 성공
빨간색 → 실패
회색   → 권한 없음
```

텍스트나 아이콘의 의미 있는 레이블, 상태 속성 등을 함께 사용합니다.

예를 들어 오류 입력은 다음과 같이 표현할 수 있습니다.

```html
<label for="email">이메일</label>
<input
  id="email"
  aria-invalid="true"
  aria-describedby="email-error"
/>
<p id="email-error">이메일 형식을 확인해 주세요.</p>
```

CSS로 빨간 테두리를 추가할 수는 있지만 빨간색 자체가 유일한 오류 정보가 되어서는 안 됩니다.

## 화면에서 숨기는 것과 권한 검사는 다릅니다

접근성과 보안은 다른 문제입니다.

예를 들어 수정 권한이 없는 사용자에게 수정 버튼을 숨기는 것은 사용성을 개선할 수 있습니다.

```text
수정 권한 없음
→ 화면에서 수정 버튼을 표시하지 않음
```

하지만 사용자는 화면을 통하지 않고 직접 HTTP 요청을 만들 수 있습니다.

따라서 서버에서도 반드시 권한을 확인해야 합니다.

```text
클라이언트 UI
→ 사용자가 할 수 있는 작업을 이해하기 쉽게 표시

서버
→ 실제 요청이 허용되는지 최종 검사
```

버튼을 숨기는 것은 서버 권한 검사를 대신하지 않습니다.

## 테스트에서 요소를 찾는 방법

브라우저 테스트에서는 구현 세부 사항인 CSS 클래스보다 사용자가 인식하는 역할과 이름을 우선해 요소를 찾는 것이 유용합니다.

예를 들어 Playwright에서는 다음처럼 작성할 수 있습니다.

```ts
page.getByRole("button", { name: "메모 추가" });
page.getByLabel("새 작업");
page.getByRole("alert");
```

이 방식은 실제 사용자 인터페이스 의미와 테스트를 연결합니다.

예를 들어 다음 버튼의 텍스트가 사라진다면

```html
<button type="button"></button>
```

다음 테스트가 실패할 수 있습니다.

```ts
page.getByRole("button", { name: "메모 추가" });
```

이는 단순히 테스트가 약한 CSS 선택자에 의존하지 않고, 사용자에게 필요한 버튼 이름이 사라진 문제를 함께 발견하게 해 줍니다.

같은 이유로 레이블이 없는 입력은 `getByLabel()`로 찾을 수 없습니다.

테스트를 접근성 검사 도구의 완전한 대체물로 볼 수는 없지만, 역할과 이름을 기준으로 요소를 찾으면 의미론적 HTML이 무너지는 문제를 조기에 발견하는 데 도움이 됩니다.

## 폼 구현 예제

앞의 원칙을 한 번에 적용한 간단한 예제입니다.

```html
<form id="task-form">
  <div>
    <label for="task-title">새 작업</label>
    <input
      id="task-title"
      name="title"
      type="text"
      required
      aria-describedby="task-title-error"
    />
    <p id="task-title-error"></p>
  </div>

  <button type="submit">추가</button>
  <button type="button" id="clear-button">지우기</button>

  <p id="form-status" role="status"></p>
</form>
```

```js
const form = document.querySelector("#task-form");
const input = document.querySelector("#task-title");
const error = document.querySelector("#task-title-error");
const status = document.querySelector("#form-status");
const clearButton = document.querySelector("#clear-button");

form?.addEventListener("submit", (event) => {
  event.preventDefault();

  const title = input.value.trim();

  if (!title) {
    input.setAttribute("aria-invalid", "true");
    error.textContent = "작업 이름을 입력해 주세요.";
    input.focus();
    return;
  }

  input.removeAttribute("aria-invalid");
  error.textContent = "";
  status.textContent = "저장 중입니다.";

  // API 요청 등을 수행합니다.
});

clearButton?.addEventListener("click", () => {
  form.reset();
  input.removeAttribute("aria-invalid");
  error.textContent = "";
  status.textContent = "";
  input.focus();
});
```

이 예제에서 중요한 점은 다음과 같습니다.

- 입력에는 보이는 `label`이 있습니다.
- 제출은 버튼의 `click`이 아니라 폼의 `submit`에서 처리합니다.
- 제출용 버튼과 일반 동작 버튼의 `type`을 구분합니다.
- 오류가 발생했을 때 `aria-invalid`와 오류 텍스트를 사용합니다.
- 상태 변화는 `role="status"` 영역을 통해 전달합니다.
- 오류가 난 입력으로 포커스를 이동해 사용자가 바로 수정할 수 있게 합니다.

실제 프로젝트에서는 서버 응답 오류, 중복 제출 방지, 비동기 로딩 상태 등을 추가로 처리해야 하지만 기본 구조는 같습니다.

## 직접 확인하기

마우스를 사용하지 않고 키보드만으로 페이지를 조작해 봅니다.

다음을 확인합니다.

```text
1. Tab으로 모든 링크, 버튼, 입력에 도달할 수 있는가?
2. 현재 포커스가 어디인지 화면에서 알 수 있는가?
3. 링크는 Enter로 이동할 수 있는가?
4. 버튼은 키보드로 실행할 수 있는가?
5. 입력 필드에서 폼을 제출할 수 있는가?
6. 오류가 발생하면 어떤 입력이 잘못되었는지 알 수 있는가?
7. 비동기 성공·실패 상태가 텍스트로도 표시되는가?
8. 모달을 닫은 뒤 포커스가 예상 가능한 위치로 돌아오는가?
```

브라우저 개발자 도구의 접근성 트리를 볼 수 있다면 버튼, 링크, 입력이 어떤 역할과 이름으로 노출되는지도 확인합니다.

예를 들어 화면에 보이는 텍스트와 접근 가능한 이름이 의도대로 연결되어 있는지 확인합니다.

## 흔한 실수

- 모양만 보고 링크와 버튼을 선택합니다.
- 이동 동작을 `div`의 클릭 이벤트로 구현합니다.
- 실제 버튼 대신 `div role="button"`을 먼저 선택합니다.
- 폼 안의 일반 버튼에 `type="button"`을 지정하지 않아 의도하지 않은 제출이 발생합니다.
- 플레이스홀더를 레이블 대신 사용합니다.
- `label for`와 입력의 `id`가 서로 다릅니다.
- `id`와 `name`의 역할을 혼동합니다.
- 오류가 없는데도 `aria-invalid="true"`를 항상 지정합니다.
- 오류 메시지를 화면에 표시하지만 해당 입력과 연결하지 않습니다.
- 버튼 클릭만 처리해 Enter 키 제출이 다른 경로로 동작하거나 작동하지 않습니다.
- 이유를 이해하지 않고 모든 폼에서 `preventDefault()`를 호출합니다.
- 다른 표시 없이 포커스 윤곽선을 제거합니다.
- DOM 순서와 다른 탭 순서를 큰 양수 `tabindex`로 억지로 만듭니다.
- 모달을 열고 닫을 때 포커스 위치를 관리하지 않습니다.
- 모든 상태 메시지를 `role="alert"`로 만들어 알림이 과도하게 발생합니다.
- 색만으로 성공, 실패, 권한 상태를 구분합니다.
- 화면에서 버튼을 숨긴 것으로 서버 권한 검사를 대신합니다.
- 기본 HTML 요소가 이미 제공하는 의미를 ARIA 역할로 불필요하게 반복합니다.

## 관련 exercise

[`browser-directory`](../../exercises/browser-directory/README.md)는 검색 폼, 건너뛰기 링크, 결과 상태와 키보드 포커스를 검사합니다.

## 완료 기준

다음 내용을 설명하고 직접 구현할 수 있으면 이 문서의 목표를 달성한 것입니다.

- `header`, `nav`, `main`과 제목 순서를 내용의 구조에 맞게 구성할 수 있습니다.
- 링크와 버튼 중 어떤 요소를 선택해야 하는지 동작의 목적을 기준으로 설명할 수 있습니다.
- `label`, `for`, `id`, `name`의 역할 차이를 설명할 수 있습니다.
- 레이블이 연결된 입력과 제출 버튼으로 폼을 만들 수 있습니다.
- 버튼 클릭과 Enter 키 제출을 같은 `submit` 처리 코드로 다룰 수 있습니다.
- 폼 안에서 `submit` 버튼과 일반 `button`을 구분할 수 있습니다.
- 오류 입력에 `aria-invalid`와 오류 설명을 적절한 시점에 연결할 수 있습니다.
- 키보드로 이동할 때 현재 포커스를 시각적으로 확인할 수 있습니다.
- 건너뛰기 링크가 필요한 이유를 설명할 수 있습니다.
- 동적으로 열린 UI를 닫은 뒤 포커스를 적절한 위치로 되돌려야 하는 이유를 설명할 수 있습니다.
- 일반적인 진행 상태와 즉시 알려야 하는 오류에 `status`와 `alert`를 구분해 사용할 수 있습니다.
- 화면에서 기능을 숨기는 것과 서버 권한 검사가 서로 다른 문제임을 설명할 수 있습니다.
