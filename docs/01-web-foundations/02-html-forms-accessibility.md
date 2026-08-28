# HTML 폼과 접근성

HTML 요소는 모양만 정하는 태그가 아닙니다. 링크, 버튼, 입력 필드, 제목, `main`, `nav`에는 브라우저와 보조 기술이 이해하는 의미와 기본 동작이 있습니다. 용도에 맞는 요소를 사용하면 키보드 조작과 폼 제출을 JavaScript로 다시 만들 필요가 줄어듭니다.

이 문서는 폼이나 복잡한 화면을 구현하기 직전에 읽는 JIT 문서입니다.

## 목표

- 문서의 주요 영역과 제목 순서를 정합니다.
- 이동에는 링크, 현재 화면의 동작에는 버튼을 사용합니다.
- 입력 요소에 보이는 레이블을 연결합니다.
- 폼의 `submit` 동작을 활용합니다.
- 포커스와 비동기 오류를 시각 사용자와 비시각 사용자에게 함께 전달합니다.

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

`lang`은 문서 언어를, `title`은 브라우저 탭과 방문 기록에 표시할 이름을 정합니다. `main`은 페이지의 핵심 내용을 나타냅니다. HTML 요소가 이미 의미를 제공한다면 같은 ARIA 역할을 반복해서 붙이지 않습니다.

## 제목은 문서 순서를 나타냅니다

```html
<h1>보드 설정</h1>
<section>
  <h2>구성원</h2>
  <article>
    <h3>Kim</h3>
  </article>
</section>
```

글자 크기를 맞추려고 제목 단계를 고르지 않습니다. 시각적 크기는 CSS로 정하고, 제목은 내용의 포함 관계에 맞춥니다.

## 링크와 버튼

```html
<a href="/boards/42">보드 열기</a>
<button type="button">메모 추가</button>
```

- 링크는 다른 주소로 이동합니다.
- 버튼은 현재 화면에서 작업을 실행하거나 상태를 바꿉니다.

폼 안의 버튼은 기본값이 `submit`일 수 있습니다. 제출용이 아니라면 `type="button"`을 명시합니다.

클릭 이벤트를 붙인 `div`를 버튼처럼 사용하면 Enter·Space 키, 포커스, 비활성화 상태를 모두 직접 구현해야 합니다.

## 레이블과 입력 요소

플레이스홀더는 입력 예시일 뿐 이름이 아닙니다.

```html
<form id="task-form">
  <label for="task-title">새 작업</label>
  <input id="task-title" name="title" autocomplete="off" />
  <button type="submit">추가</button>
</form>
```

`for`와 `id`를 연결하면 레이블을 클릭했을 때 입력 요소로 포커스가 이동하고, 스크린 리더도 입력 이름을 읽을 수 있습니다.

오류 설명이 있다면 입력과 연결합니다.

```html
<input
  id="email"
  aria-invalid="true"
  aria-describedby="email-error"
/>
<p id="email-error">이메일 형식을 확인해 주세요.</p>
```

## 폼 제출

버튼의 `click`만 처리하지 말고 폼의 `submit` 이벤트를 처리합니다.

```js
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  // 입력을 검증하고 저장합니다.
});
```

이 방식은 버튼 클릭과 Enter 키 제출을 같은 코드로 처리합니다.

## 포커스

포커스 표시를 대체하지 않고 제거하면 현재 위치를 알 수 없습니다.

```css
:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 3px;
}
```

반복되는 탐색 영역을 건너뛰는 링크도 사용할 수 있습니다.

```html
<a class="skip-link" href="#main">본문으로 건너뛰기</a>
<main id="main" tabindex="-1">...</main>
```

모달을 열면 적절한 요소로 포커스를 옮기고, 닫으면 모달을 열었던 버튼으로 되돌립니다. 화면 위에 표시하는 것만으로 키보드 조작이 완성되지는 않습니다.

## 진행 상태와 오류

```html
<p role="status" aria-live="polite">저장 중입니다.</p>
<p role="alert">저장하지 못했습니다.</p>
```

일반적인 진행 상태는 `status`, 즉시 알려야 하는 오류는 `alert`를 사용합니다. 모든 텍스트를 라이브 영역으로 만들면 알림이 지나치게 반복됩니다.

색만으로 성공·실패·권한을 구분하지 않습니다. 텍스트와 상태 속성을 함께 제공합니다.

## 테스트에서 찾는 방법

브라우저 테스트는 CSS 클래스보다 사용자가 인식하는 역할과 이름을 우선합니다.

```ts
page.getByRole("button", { name: "메모 추가" });
page.getByLabel("새 작업");
page.getByRole("alert");
```

레이블이나 버튼 이름이 사라지면 테스트도 실패해야 합니다.

## 흔한 실수

- 모양만 보고 링크와 버튼을 선택합니다.
- 플레이스홀더를 레이블 대신 사용합니다.
- 버튼 클릭만 처리해 Enter 키 제출이 동작하지 않습니다.
- 다른 표시 없이 포커스 윤곽선을 제거합니다.
- 화면에서 버튼을 숨긴 것으로 서버 권한 검사를 대신합니다.
- 기본 HTML 요소 대신 불필요한 ARIA 역할을 붙입니다.

## 관련 exercise

[`browser-directory`](../../exercises/browser-directory/README.md)는 검색 폼, 건너뛰기 링크, 결과 상태와 키보드 포커스를 검사합니다.

## 완료 기준

- `header`, `nav`, `main`과 제목 순서를 구성할 수 있습니다.
- 링크와 버튼을 선택한 이유를 설명할 수 있습니다.
- 레이블이 연결된 폼을 Enter 키로 제출할 수 있습니다.
- 포커스, 진행 상태, 오류를 보조 기술에도 전달할 수 있습니다.
