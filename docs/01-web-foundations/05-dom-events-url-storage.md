# DOM, 이벤트, URL과 저장소

DOM(Document Object Model)은 브라우저가 HTML 문서를 해석해 만든 객체 트리입니다. JavaScript는 이 객체를 조회하고 변경하여 화면을 갱신하고, 클릭·입력·제출 같은 이벤트에 반응합니다.

브라우저 애플리케이션에서는 같은 의미의 값을 여러 곳에 중복 저장하지 않는 것이 중요합니다. 예를 들어 검색어를 전역 변수, 입력 요소, URL, `localStorage`에 각각 독립적으로 저장하면 값이 달라졌을 때 어느 것이 최신인지 판단하기 어렵습니다.

따라서 상태마다 **기준이 되는 위치(source of truth)** 를 하나 정하고, 다른 표현은 그 값을 읽어 만들어 내는 방식으로 구성합니다.

이 문서는 브라우저 상태와 URL 탐색을 구현하기 직전에 읽는 JIT 문서입니다.

## 목표

- DOM이 HTML을 표현하는 객체 트리라는 점을 설명합니다.
- 필요한 DOM 요소를 조회하고 기대한 종류의 요소인지 확인합니다.
- 사용자 문자열을 HTML로 오해석하지 않도록 안전하게 출력합니다.
- 폼의 기본 동작과 이벤트 버블링을 이해합니다.
- `event.target`과 `event.currentTarget`을 구분합니다.
- 이벤트 위임으로 동적으로 추가되는 목록 항목도 처리합니다.
- 메모리, URL, 브라우저 저장소, 서버 중 값의 기준 위치를 선택합니다.
- History API와 `popstate`를 사용해 뒤로 가기와 앞으로 가기에서 화면을 복원합니다.
- `localStorage`의 문자열 데이터도 외부 입력처럼 파싱하고 검증합니다.
- 상태 변경, 저장, 화면 그리기의 책임을 구분합니다.

## DOM은 HTML의 객체 표현입니다

다음 HTML이 있다고 가정합니다.

```html
<main>
  <h1>작업</h1>
  <ul id="task-list">
    <li>문서 읽기</li>
  </ul>
</main>
```

브라우저는 이 문서를 대략 다음과 같은 계층의 객체로 표현합니다.

```text
main
├─ h1
└─ ul#task-list
   └─ li
```

JavaScript는 원본 HTML 문자열을 매번 직접 수정하는 것이 아니라 이 DOM 객체를 통해 현재 문서를 읽고 변경합니다.

예를 들어:

```js
const list = document.querySelector("#task-list");
```

`document.querySelector()`는 CSS 선택자와 일치하는 첫 번째 DOM 요소를 찾습니다.

중요한 점은 찾지 못할 수도 있다는 것입니다.

```js
document.querySelector("#missing"); // null
```

따라서 필요한 요소가 반드시 존재해야 한다면 시작 시점에 확인하는 편이 좋습니다.

## DOM 요소 확인

검색 폼이 반드시 있어야 하는 애플리케이션을 생각해 봅니다.

```js
const form = document.querySelector("#search-form");

if (!(form instanceof HTMLFormElement)) {
  throw new Error("검색 폼을 찾을 수 없습니다.");
}
```

이 코드는 두 가지를 함께 확인합니다.

```text
1. 요소를 찾았는가?
2. 찾은 요소가 실제 form 요소인가?
```

단순히 다음처럼 사용하면

```js
const form = document.querySelector("#search-form");
form.addEventListener("submit", handleSubmit);
```

요소를 찾지 못했을 때 `form`은 `null`이므로 나중에 다음과 비슷한 오류가 발생합니다.

```text
Cannot read properties of null
```

반면 시작할 때 명확하게 검사하면 HTML의 `id`가 바뀌었거나 필요한 요소가 빠진 문제를 즉시 알 수 있습니다.

### 필요한 요소와 선택적인 요소를 구분합니다

모든 `querySelector()` 결과에 무조건 오류를 던질 필요는 없습니다.

현재 기능에 반드시 필요한 요소라면 실패시키는 것이 적절할 수 있습니다.

```js
const form = document.querySelector("#search-form");

if (!(form instanceof HTMLFormElement)) {
  throw new Error("검색 폼이 필요합니다.");
}
```

반대로 페이지에 있을 수도 있고 없을 수도 있는 선택적 UI라면 조건부로 처리할 수 있습니다.

```js
const helpButton = document.querySelector("#help-button");

if (helpButton instanceof HTMLButtonElement) {
  helpButton.addEventListener("click", openHelp);
}
```

중요한 것은 요소의 존재 여부에 대한 가정을 코드에 명확하게 표현하는 것입니다.

## DOM 속성을 변경합니다

DOM 요소는 JavaScript 객체이므로 속성을 읽고 변경할 수 있습니다.

```js
const button = document.querySelector("#save");

if (!(button instanceof HTMLButtonElement)) {
  throw new Error("저장 버튼을 찾을 수 없습니다.");
}

button.disabled = true;
button.textContent = "저장 중";
```

이 코드는 버튼의 현재 상태를 DOM에 반영합니다.

HTML 속성과 DOM 프로퍼티가 항상 완전히 같은 개념인 것은 아니지만, 일반적인 폼 요소의 현재 상태를 다룰 때는 해당 DOM 프로퍼티를 사용하는 경우가 많습니다.

예를 들어 입력의 현재 값은 다음처럼 읽습니다.

```js
const input = document.querySelector("#title");

if (!(input instanceof HTMLInputElement)) {
  throw new Error("제목 입력을 찾을 수 없습니다.");
}

const title = input.value;
```

## 사용자 문자열은 텍스트로 출력합니다

사용자가 입력한 제목이나 메모처럼 HTML 문법으로 해석할 필요가 없는 문자열은 `textContent`로 출력합니다.

```js
const title = document.createElement("span");
title.textContent = userInput;
```

예를 들어 사용자가 다음 문자열을 입력했다고 가정합니다.

```text
<strong>중요</strong>
```

`textContent`에 넣으면 브라우저는 이것을 HTML 요소로 만들지 않고 그대로 텍스트로 표시합니다.

```text
<strong>중요</strong>
```

### `innerHTML`은 문자열을 HTML로 해석합니다

다음 코드는 문자열을 HTML 문법으로 해석합니다.

```js
element.innerHTML = userInput;
```

따라서 사용자 입력이나 서버에서 받은 신뢰할 수 없는 문자열을 그대로 넣으면 의도하지 않은 HTML이 만들어질 수 있고, 상황에 따라 XSS 취약점으로 이어질 수 있습니다.

일반적인 제목, 이름, 메모를 출력하려는 목적이라면 다음을 기본으로 사용합니다.

```js
element.textContent = userInput;
```

### 실제 HTML 입력이 필요한 경우

일부 제품은 게시물 본문처럼 제한된 HTML 입력을 허용할 수 있습니다.

이 경우 단순히 `innerHTML`을 사용하는 것이 아니라 다음이 필요합니다.

- 허용할 HTML 요소와 속성의 명확한 규칙
- 검증된 HTML 새니타이저
- URL과 속성 등 위험한 입력에 대한 별도 정책

이 문서의 일반적인 UI 문자열에는 `textContent`를 사용한다고 기억하면 됩니다.

## 상태에서 DOM을 다시 만듭니다

목록처럼 상태를 화면에 반영하는 경우에는 현재 상태를 기준으로 DOM 노드를 만든 뒤 필요한 영역을 교체하는 방식이 단순할 수 있습니다.

```js
function renderTask(task) {
  const item = document.createElement("li");
  item.textContent = task.title;
  return item;
}

list.replaceChildren(
  ...tasks.map(renderTask)
);
```

흐름은 다음과 같습니다.

```text
tasks 상태
   ↓
renderTask()
   ↓
DOM 노드들
   ↓
replaceChildren()
   ↓
현재 화면
```

이 방식에서는 화면의 DOM을 다시 읽어 업무 데이터를 복원하려 하지 않습니다.

예를 들어 다음과 같은 방향보다

```text
DOM에 표시된 문자열
→ 다시 읽어서 현재 tasks 상태라고 판단
```

다음 방향이 더 명확합니다.

```text
tasks 상태
→ DOM을 렌더링
```

즉 DOM은 상태의 **표현 결과**이고, 업무 데이터의 기준은 별도로 유지합니다.

## 이벤트

이벤트(event)는 브라우저에서 발생한 동작이나 상태 변화를 JavaScript가 처리할 수 있도록 전달하는 객체입니다.

대표적인 이벤트는 다음과 같습니다.

```text
click   → 클릭
input   → 입력값 변경
change  → 값 변경 확정
submit  → 폼 제출
keydown → 키 누름
```

요소에 이벤트 리스너를 등록하면 해당 이벤트가 발생할 때 함수를 실행할 수 있습니다.

```js
button.addEventListener("click", () => {
  console.log("클릭했습니다.");
});
```

## 폼의 기본 동작

폼에는 브라우저가 제공하는 기본 제출 동작이 있습니다.

```html
<form id="search-form" action="/search" method="get">
  <label for="query">검색어</label>
  <input id="query" name="q" />

  <button type="submit">검색</button>
</form>
```

브라우저의 기본 제출을 사용하면 폼 데이터에 따라 URL로 이동합니다.

JavaScript가 이 제출을 직접 처리하려면 `submit` 이벤트에서 기본 동작을 막을 수 있습니다.

```js
form.addEventListener("submit", (event) => {
  event.preventDefault();

  // 입력을 읽고 JavaScript에서 처리합니다.
});
```

`preventDefault()`의 의미는 다음과 같습니다.

```text
이벤트 자체를 없앤다          → 아님
이벤트 전파를 막는다          → 아님
브라우저의 기본 동작을 막는다 → 맞음
```

폼의 경우 기본 페이지 이동이나 제출 동작을 막고 JavaScript가 대신 처리하도록 할 때 사용합니다.

`preventDefault()`를 호출했다면 이후 실제로 무엇을 할지는 애플리케이션 코드가 책임져야 합니다.

## `preventDefault()`와 이벤트 전파는 다릅니다

이벤트에는 **기본 동작**과 **전파**라는 서로 다른 개념이 있습니다.

예를 들어 링크를 클릭하면:

```text
click 이벤트 발생
        │
        ├─ 이벤트가 DOM을 따라 전파됨
        │
        └─ 브라우저가 href로 이동하는 기본 동작 수행
```

`preventDefault()`는 아래쪽 기본 동작만 취소합니다.

```js
link.addEventListener("click", (event) => {
  event.preventDefault();
});
```

이벤트가 부모 요소로 전달되는 것까지 막는 것은 아닙니다.

전파를 멈추는 `stopPropagation()`은 별도의 기능입니다.

```js
event.stopPropagation();
```

하지만 이벤트 위임을 사용하는 구조에서는 전파가 필요하므로 이유 없이 `stopPropagation()`을 추가하지 않습니다.

## 이벤트 버블링

많은 이벤트는 발생한 요소에서 시작해 조상 요소 방향으로 전달됩니다. 이를 **버블링(bubbling)** 이라고 합니다.

다음 구조를 생각해 봅니다.

```html
<ul id="task-list">
  <li>
    <button type="button" data-task-id="42">
      삭제
    </button>
  </li>
</ul>
```

버튼을 클릭하면 이벤트는 개념적으로 다음처럼 위로 전달될 수 있습니다.

```text
button
  ↓
li
  ↓
ul#task-list
  ↓
상위 요소들
```

그래서 각 버튼에 별도의 리스너를 등록하지 않고 목록 부모 하나에서 클릭을 처리할 수 있습니다.

이 방식을 **이벤트 위임(event delegation)** 이라고 합니다.

## 이벤트 위임

목록의 모든 삭제 버튼을 부모 리스너 하나에서 처리할 수 있습니다.

```js
list.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) {
    return;
  }

  const button =
    event.target.closest("button[data-task-id]");

  if (
    !(button instanceof HTMLButtonElement) ||
    !list.contains(button)
  ) {
    return;
  }

  const taskId = button.dataset.taskId;

  if (!taskId) {
    return;
  }

  removeTask(taskId);
});
```

`event.target`은 `EventTarget` 타입이므로 항상 `Element`라고 가정하지 않고 확인한 뒤 `closest()`를 호출합니다.

### 왜 `closest()`를 사용합니까?

버튼 내부에 아이콘이나 텍스트 요소가 있을 수 있습니다.

```html
<button type="button" data-task-id="42">
  <span aria-hidden="true">×</span>
  삭제
</button>
```

사용자가 `<span>`을 클릭하면 실제 `event.target`은 버튼이 아니라 `<span>`일 수 있습니다.

```text
클릭 위치
span
 ↓ closest("button[data-task-id]")
button
```

`closest()`는 자신부터 부모 방향으로 올라가면서 선택자와 일치하는 가장 가까운 요소를 찾습니다.

### 동적으로 추가한 항목에도 동작합니다

부모인 `list`에 리스너가 하나만 있으므로 나중에 `replaceChildren()` 등으로 새 버튼을 추가해도 별도 리스너 등록이 필요하지 않습니다.

```text
list에 리스너 등록
   ↓
기존 버튼 클릭 처리 가능
   ↓
새 버튼 추가
   ↓
새 버튼의 클릭도 같은 부모까지 버블링
   ↓
같은 리스너에서 처리
```

이벤트 버블링을 이용하는 주요 이유 중 하나입니다.

## `target`과 `currentTarget`

두 속성은 자주 혼동합니다.

```js
list.addEventListener("click", (event) => {
  console.log(event.target);
  console.log(event.currentTarget);
});
```

- `event.target`: 이벤트가 실제로 시작된 요소
- `event.currentTarget`: 현재 실행 중인 리스너가 등록된 요소

예를 들어 `list` 안의 버튼을 클릭했다면:

```text
event.target        → 클릭한 button 또는 그 내부 요소
event.currentTarget → 리스너를 등록한 list
```

이벤트 위임에서는 이 차이를 이해해야 합니다.

## 상태의 기준 위치를 하나 정합니다

웹 애플리케이션의 상태는 성격에 따라 적절한 위치가 다릅니다.

| 값 | 적합한 기준 위치 | 예시 |
|---|---|---|
| 현재 화면에서만 잠깐 필요한 값 | 컴포넌트·모듈 메모리 | 모달 열림 여부, 전송 중 상태 |
| 공유하거나 뒤로 가기로 복원해야 하는 탐색 상태 | URL | 검색어, 필터, 정렬, 선택한 탭 |
| 새로 고침 뒤에도 유지할 비민감 사용자 편의 정보 | `localStorage` | 테마, 임시 초안 |
| 여러 기기·사용자와 공유되거나 권한 검사가 필요한 업무 데이터 | 서버 | 계정, 역할, 주문, 보드 내용 |

이 표는 절대적인 법칙이라기보다 상태를 어디에 둘지 판단하기 위한 기준입니다.

중요한 원칙은 **같은 의미의 값을 여러 곳에서 독립적으로 수정하지 않는 것**입니다.

## 중복 상태가 만드는 문제

검색어를 다음 두 곳에 각각 저장한다고 가정합니다.

```js
let query = "cat";
```

URL도 별도로 바꿉니다.

```text
?q=dog
```

이제 현재 검색어가 무엇인지 애매합니다.

```text
메모리 → cat
URL    → dog
```

렌더링 코드마다 서로 다른 값을 읽으면 화면과 주소가 일치하지 않을 수 있습니다.

URL을 검색 상태의 기준으로 정했다면 메모리에 같은 값을 별도로 유지하지 않고 필요할 때 URL에서 읽습니다.

```js
function readQuery() {
  return new URL(location.href)
    .searchParams
    .get("q")
    ?.trim() ?? "";
}
```

렌더링할 때도 같은 함수를 사용합니다.

```js
render(readQuery());
```

흐름이 다음처럼 한 방향이 됩니다.

```text
URL
 ↓
readQuery()
 ↓
render()
 ↓
화면
```

## URL을 상태로 사용하는 이유

검색어, 필터, 정렬처럼 화면을 다시 열었을 때 복원되어야 하는 값은 URL에 두는 것이 유용할 수 있습니다.

예를 들어:

```text
/tasks?q=network&status=open
```

이 URL에는 현재 화면을 복원할 수 있는 정보가 들어 있습니다.

장점은 다음과 같습니다.

- 새로 고침해도 상태를 다시 읽을 수 있습니다.
- URL을 복사해 같은 화면을 공유할 수 있습니다.
- 뒤로 가기와 앞으로 가기로 이전 탐색 상태를 복원할 수 있습니다.
- 북마크할 수 있습니다.

반면 비밀번호나 민감한 개인정보처럼 노출되면 안 되는 값을 URL에 넣으면 안 됩니다. URL은 주소 표시줄, 방문 기록, 로그 등에 남을 수 있습니다.

## `URL`과 `URLSearchParams`

현재 URL은 다음처럼 안전하게 파싱할 수 있습니다.

```js
const url = new URL(location.href);
```

쿼리 문자열은 `searchParams`로 다룹니다.

```js
const query = url.searchParams.get("q");
```

값을 설정할 수 있습니다.

```js
url.searchParams.set("q", "network");
```

값을 제거할 수도 있습니다.

```js
url.searchParams.delete("q");
```

문자열을 직접 이어 붙이는 것보다 `URL`과 `URLSearchParams`를 사용하면 인코딩과 `?`, `&` 조합을 직접 관리할 필요가 줄어듭니다.

## History API

URL을 상태로 사용하면서 전체 페이지를 다시 로드하지 않으려면 History API를 사용할 수 있습니다.

예를 들어:

```js
function readQuery() {
  return new URL(location.href)
    .searchParams
    .get("q")
    ?.trim() ?? "";
}

function writeQuery(query) {
  const url = new URL(location.href);

  if (query) {
    url.searchParams.set("q", query);
  } else {
    url.searchParams.delete("q");
  }

  history.pushState(null, "", url);
  render(readQuery());
}
```

`history.pushState()`는 현재 문서를 다시 요청하지 않고 브라우저의 URL과 방문 기록을 변경할 수 있습니다.

같은 출처의 URL 범위 안에서 사용해야 하며, 다른 사이트로 이동하는 기능은 아닙니다.

## `pushState()`와 `replaceState()`

두 메서드는 방문 기록을 다르게 처리합니다.

### `pushState()`

```js
history.pushState(null, "", url);
```

현재 방문 기록 뒤에 새 항목을 추가합니다.

예를 들어:

```text
처음
/tasks

검색 A
/tasks?q=a

검색 B
/tasks?q=b
```

검색 변경마다 `pushState()`를 사용했다면 뒤로 가기를 눌렀을 때 다음처럼 이전 상태로 돌아갈 수 있습니다.

```text
/tasks?q=b
   ↓ 뒤로
/tasks?q=a
   ↓ 뒤로
/tasks
```

사용자가 "이전 검색 상태로 돌아가기"를 기대한다면 적합합니다.

### `replaceState()`

```js
history.replaceState(null, "", url);
```

새 기록을 추가하지 않고 현재 기록 항목을 교체합니다.

예를 들어 페이지를 처음 열었을 때 불필요한 기본 쿼리를 제거하는 정리 작업처럼 사용자가 별도의 탐색 단계로 되돌아갈 필요가 없는 변경에 사용할 수 있습니다.

개념적으로:

```text
pushState
현재 기록 → 새 기록 추가

replaceState
현재 기록 → 현재 기록 자체를 교체
```

## `pushState()`는 `popstate`를 발생시키지 않습니다

다음 코드를 실행했다고 해서

```js
history.pushState(null, "", url);
```

즉시 `popstate` 이벤트가 자동으로 발생하지는 않습니다.

따라서 URL을 변경한 직후 화면을 갱신해야 한다면 직접 렌더링합니다.

```js
history.pushState(null, "", url);
render(readQuery());
```

반면 사용자가 브라우저의 뒤로 가기나 앞으로 가기를 사용해 다른 기록 항목으로 이동하면 `popstate`를 처리해야 합니다.

```js
window.addEventListener("popstate", () => {
  render(readQuery());
});
```

전체 흐름은 다음과 같습니다.

```text
사용자 검색
   ↓
URL 수정
   ↓
pushState()
   ↓
직접 render()

사용자 뒤로/앞으로 가기
   ↓
브라우저가 기록 이동
   ↓
popstate
   ↓
현재 URL 다시 읽기
   ↓
render()
```

## 뒤로 가기에서는 현재 URL을 다시 읽습니다

이전 검색어를 별도의 전역 변수에 저장해 두었다가 복원하려 하면 History와 상태를 이중 관리하게 됩니다.

URL이 기준이라면 `popstate`에서 현재 URL을 다시 읽습니다.

```js
window.addEventListener("popstate", () => {
  const query = readQuery();
  render(query);
});
```

예를 들어:

```text
1. /tasks?q=cat
2. /tasks?q=dog
3. 뒤로 가기
4. 브라우저 URL이 /tasks?q=cat으로 변경
5. popstate 발생
6. readQuery()가 "cat" 반환
7. "cat" 상태로 화면 렌더링
```

이렇게 하면 브라우저 방문 기록과 화면이 같은 기준을 사용합니다.

## URL과 입력 요소를 동기화합니다

검색어를 URL이 기준으로 관리한다면 화면을 그릴 때 검색 입력도 URL에서 읽은 값으로 맞춥니다.

```js
function render(query) {
  searchInput.value = query;
  renderResults(query);
}
```

사용자가 제출하면 입력값을 URL에 기록합니다.

```js
form.addEventListener("submit", (event) => {
  event.preventDefault();

  const query = searchInput.value.trim();
  writeQuery(query);
});
```

뒤로 가기에서는 URL을 다시 읽어 입력과 결과를 모두 복원합니다.

```js
window.addEventListener("popstate", () => {
  render(readQuery());
});
```

이 구조에서는 검색 입력, 검색 결과, 주소 표시줄이 하나의 URL 상태로부터 만들어집니다.

## `localStorage`

`localStorage`는 브라우저가 같은 출처(origin)의 데이터를 키와 문자열 값 형태로 저장하는 API입니다.

```js
localStorage.setItem("theme", "dark");

const theme = localStorage.getItem("theme");
```

값은 문자열로 저장됩니다.

```js
localStorage.setItem("count", "3");
```

`getItem()`은 키가 없으면 `null`을 반환합니다.

```js
localStorage.getItem("missing"); // null
```

객체나 배열은 보통 JSON 문자열로 변환해서 저장합니다.

```js
localStorage.setItem(
  "tasks.v1",
  JSON.stringify(tasks)
);
```

읽을 때는 다시 파싱합니다.

```js
const value = JSON.parse(
  localStorage.getItem("tasks.v1") ?? "[]"
);
```

## 저장된 값도 신뢰하지 않습니다

`localStorage`에 이전에 애플리케이션이 직접 저장한 값이라고 해서 항상 현재 코드가 기대하는 형식이라고 가정할 수 없습니다.

이유는 여러 가지입니다.

- 사용자가 개발자 도구에서 직접 수정할 수 있습니다.
- 이전 버전 애플리케이션이 다른 구조로 저장했을 수 있습니다.
- 일부 데이터만 손상되었을 수 있습니다.
- JSON이 아닌 문자열이 들어 있을 수 있습니다.

따라서 네트워크 응답이나 폼 입력과 마찬가지로 **외부 경계에서 들어오는 값**으로 보고 검증합니다.

## JSON 파싱 실패를 처리합니다

다음 값은 유효한 JSON이 아닙니다.

```text
not-json
```

이 값을 `JSON.parse()`하면 예외가 발생합니다.

애플리케이션 시작 전체가 중단되지 않도록 필요한 경우 안전한 기본값으로 복구할 수 있습니다.

```js
function readTasks() {
  try {
    const raw =
      localStorage.getItem("tasks.v1") ?? "[]";

    const value = JSON.parse(raw);

    return Array.isArray(value)
      ? value.filter(isTask)
      : [];
  } catch {
    return [];
  }
}
```

이 함수는 두 단계로 방어합니다.

```text
JSON으로 파싱 가능한가?
        ↓
배열인가?
        ↓
각 항목이 실제 Task 형식인가?
```

## 파싱과 검증은 다릅니다

다음 JSON은 문법적으로는 유효합니다.

```json
{"unexpected": true}
```

따라서 `JSON.parse()`는 성공합니다.

하지만 코드가 작업 배열을 기대한다면 올바른 데이터가 아닙니다.

```text
파싱 성공
≠
애플리케이션이 기대하는 데이터 구조라는 보장
```

그래서 파싱 뒤에 구조 검사가 필요합니다.

예를 들어:

```js
function isTask(value) {
  if (
    typeof value !== "object" ||
    value === null
  ) {
    return false;
  }

  return (
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    typeof value.completed === "boolean"
  );
}
```

읽는 함수는 다음처럼 사용할 수 있습니다.

```js
function readTasks() {
  try {
    const raw =
      localStorage.getItem("tasks.v1") ?? "[]";

    const value = JSON.parse(raw);

    if (!Array.isArray(value)) {
      return [];
    }

    return value.filter(isTask);
  } catch {
    return [];
  }
}
```

## 저장 형식에 버전을 둡니다

애플리케이션이 변경되면 저장 데이터의 구조도 바뀔 수 있습니다.

예를 들어 초기 구조가 다음과 같았다고 가정합니다.

```json
{
  "id": "1",
  "title": "읽기"
}
```

나중에 다음 필드가 추가될 수 있습니다.

```json
{
  "id": "1",
  "title": "읽기",
  "completed": false
}
```

이전 버전 데이터가 브라우저에 남아 있다면 새 코드가 이를 어떻게 처리할지 결정해야 합니다.

간단한 애플리케이션에서는 키 자체에 버전을 넣을 수 있습니다.

```text
tasks.v1
tasks.v2
```

또는 저장 데이터에 스키마 버전을 포함할 수 있습니다.

```json
{
  "version": 2,
  "tasks": []
}
```

버전을 두는 목적은 **저장 형식이 바뀌었다는 사실을 코드가 구분할 수 있게 하는 것**입니다.

필요하면 이전 데이터를 변환하거나, 호환할 수 없는 값은 안전한 기본값으로 되돌릴 수 있습니다.

## `localStorage`에 저장할 값

`localStorage`는 새로 고침 뒤에도 복원하고 싶은 비민감 편의 정보에 사용할 수 있습니다.

예를 들어:

```text
테마 설정
일부 UI 환경설정
임시 초안
```

하지만 서버의 권한 판단이나 중요한 업무 데이터의 최종 기준으로 사용해서는 안 됩니다.

사용자는 브라우저 저장소를 직접 수정할 수 있기 때문입니다.

```text
localStorage의 role = "admin"
```

이라고 저장되어 있어도 서버가 이를 근거로 실제 관리자 권한을 부여하면 안 됩니다.

권한은 서버가 신뢰할 수 있는 데이터와 인증 정보를 기준으로 판단해야 합니다.

## 민감한 값을 저장하지 않습니다

`localStorage` 값은 같은 페이지에서 실행되는 JavaScript가 읽을 수 있습니다.

따라서 다음과 같은 비밀값을 일반적인 `localStorage` 상태처럼 저장하지 않습니다.

- 비밀번호
- 장기 API 키
- 서버만 알아야 하는 비밀값
- 저장할 필요가 없는 민감한 개인정보

인증 정보의 저장 방식은 인증 구조와 보안 요구사항에 따라 별도로 설계해야 합니다. 특히 JavaScript에서 읽을 필요가 없는 세션 자격 정보라면 브라우저 저장소에 일반 문자열처럼 보관하는 방식과 다른 설계를 검토해야 합니다.

중요한 원칙은 다음입니다.

```text
브라우저 저장소
→ 사용자가 수정할 수 있음
→ 페이지 JavaScript가 접근할 수 있음
→ 서버 비밀 저장소가 아님
```

## 메모리 상태

페이지가 열린 동안만 필요한 값은 JavaScript 메모리에 둘 수 있습니다.

```js
let isSaving = false;
let activeDialog = null;
```

이 값들은 페이지를 새로 고침하면 사라집니다.

그것이 요구사항과 맞다면 별도의 영구 저장소가 필요하지 않습니다.

예를 들어 "현재 저장 요청이 진행 중인가?" 같은 값은 새로 고침 후 복원할 필요가 없으므로 메모리 상태가 자연스럽습니다.

반대로 사용자가 URL을 공유했을 때 같은 검색 상태를 보고 싶다면 메모리만으로는 부족합니다.

상태의 위치는 **얼마나 오래 유지해야 하는가, 공유해야 하는가, 누가 신뢰해야 하는가**를 기준으로 선택합니다.

## 서버 상태

계정, 권한, 주문, 보드 내용처럼 여러 기기나 사용자 사이에 공유되고 서버가 최종 판단해야 하는 데이터는 서버가 기준이 되어야 합니다.

예를 들어:

```text
사용자의 역할
보드 소유자
주문 가격
결제 상태
```

이런 값을 브라우저 메모리나 `localStorage`에 표시용으로 복사할 수는 있어도 그 값이 최종 권한이나 업무 사실을 결정해서는 안 됩니다.

```text
서버 데이터
   ↓ HTTP 응답
브라우저 표시용 상태
```

브라우저의 값은 서버 상태의 사본일 수 있으며 오래되어 있을 수도 있다는 점을 고려해야 합니다.

## 상태 변경과 화면 그리기

작은 애플리케이션에서는 다음처럼 상태 변경, 저장, 렌더링 순서를 명시적으로 유지할 수 있습니다.

```js
let tasks = readTasks();

function add(title) {
  tasks = [
    ...tasks,
    createTask(title),
  ];

  persist(tasks);
  render(tasks, readFilter());
}
```

흐름은 다음과 같습니다.

```text
사용자 동작
   ↓
메모리 상태 변경
   ↓
필요하면 저장
   ↓
현재 상태로 render
```

핵심은 각 함수의 책임을 분명하게 하는 것입니다.

## `render()`는 화면 그리기에 집중합니다

다음처럼 `render()`가 호출될 때마다 네트워크 요청과 저장까지 몰래 실행하면 함수의 효과를 예측하기 어렵습니다.

```js
function render(tasks) {
  localStorage.setItem(
    "tasks.v1",
    JSON.stringify(tasks)
  );

  fetch("/api/log-view");

  // DOM 갱신...
}
```

호출자는 단순히 화면만 다시 그리려 했는데 저장이나 네트워크 요청까지 발생합니다.

대신 역할을 나눕니다.

```js
function persist(tasks) {
  localStorage.setItem(
    "tasks.v1",
    JSON.stringify(tasks)
  );
}

function render(tasks) {
  list.replaceChildren(
    ...tasks.map(renderTask)
  );
}
```

그리고 상태 변경을 담당하는 위치에서 순서를 명시합니다.

```js
function add(title) {
  tasks = [
    ...tasks,
    createTask(title),
  ];

  persist(tasks);
  render(tasks);
}
```

이 구조에서는 코드만 보고 어떤 외부 동작이 발생하는지 추적하기 쉽습니다.

## DOM을 데이터베이스처럼 사용하지 않습니다

다음처럼 렌더링된 DOM을 다시 읽어 업무 데이터를 구성하는 방식은 상태가 여러 곳에 생기기 쉽습니다.

```js
const titles = [
  ...document.querySelectorAll(".task-title"),
].map((element) => element.textContent);
```

DOM은 사용자가 보는 화면 표현으로 두고, 업무 데이터는 별도의 상태에서 관리하는 편이 단순합니다.

```js
let tasks = [
  {
    id: "1",
    title: "문서 읽기",
    completed: false,
  },
];

render(tasks);
```

사용자가 항목을 완료하면 먼저 상태를 갱신합니다.

```js
tasks = tasks.map((task) =>
  task.id === targetId
    ? { ...task, completed: true }
    : task
);

render(tasks);
```

흐름은 항상 다음 방향을 유지합니다.

```text
상태
 ↓
렌더링
 ↓
DOM
```

사용자 이벤트는 상태 변경을 요청하는 입력입니다.

```text
사용자 이벤트
 ↓
상태 변경
 ↓
렌더링
 ↓
DOM
```

## 전체 예제

다음 예제는 검색어를 URL의 기준 상태로 사용하고, 작업 목록은 `localStorage`에서 검증해 읽으며, 이벤트 위임으로 삭제를 처리합니다.

```html
<form id="search-form">
  <label for="query">검색어</label>
  <input id="query" name="q" />
  <button type="submit">검색</button>
</form>

<ul id="task-list"></ul>
```

```js
const form =
  document.querySelector("#search-form");
const queryInput =
  document.querySelector("#query");
const list =
  document.querySelector("#task-list");

if (!(form instanceof HTMLFormElement)) {
  throw new Error("검색 폼이 필요합니다.");
}

if (!(queryInput instanceof HTMLInputElement)) {
  throw new Error("검색 입력이 필요합니다.");
}

if (!(list instanceof HTMLUListElement)) {
  throw new Error("작업 목록이 필요합니다.");
}

function isTask(value) {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof value.id === "string" &&
    typeof value.title === "string"
  );
}

function readTasks() {
  try {
    const raw =
      localStorage.getItem("tasks.v1") ?? "[]";

    const value = JSON.parse(raw);

    return Array.isArray(value)
      ? value.filter(isTask)
      : [];
  } catch {
    return [];
  }
}

function readQuery() {
  return new URL(location.href)
    .searchParams
    .get("q")
    ?.trim() ?? "";
}

function writeQuery(query) {
  const url = new URL(location.href);

  if (query) {
    url.searchParams.set("q", query);
  } else {
    url.searchParams.delete("q");
  }

  history.pushState(null, "", url);
}

function renderTask(task) {
  const item = document.createElement("li");

  const title = document.createElement("span");
  title.textContent = task.title;

  const button = document.createElement("button");
  button.type = "button";
  button.dataset.taskId = task.id;
  button.textContent = "삭제";

  item.append(title, button);

  return item;
}

let tasks = readTasks();

function render() {
  const query = readQuery();

  queryInput.value = query;

  const normalized =
    query.toLocaleLowerCase();

  const visibleTasks = tasks.filter((task) =>
    task.title
      .toLocaleLowerCase()
      .includes(normalized)
  );

  list.replaceChildren(
    ...visibleTasks.map(renderTask)
  );
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  writeQuery(queryInput.value.trim());
  render();
});

list.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) {
    return;
  }

  const button =
    event.target.closest("button[data-task-id]");

  if (
    !(button instanceof HTMLButtonElement) ||
    !list.contains(button)
  ) {
    return;
  }

  const taskId = button.dataset.taskId;

  if (!taskId) {
    return;
  }

  tasks = tasks.filter(
    (task) => task.id !== taskId
  );

  localStorage.setItem(
    "tasks.v1",
    JSON.stringify(tasks)
  );

  render();
});

window.addEventListener("popstate", () => {
  render();
});

render();
```

이 예제의 상태 흐름은 다음과 같습니다.

```text
검색어
URL이 기준
  ↓
readQuery()
  ↓
render()
  ↓
입력과 결과 화면

작업 목록
메모리 tasks가 현재 화면의 기준
  ↑
localStorage에서 시작 시 검증하여 복원
  ↓
변경 시 localStorage에 저장
  ↓
render()
```

검색어를 별도의 전역 변수에도 중복 저장하지 않고, 뒤로 가기에서는 URL을 다시 읽습니다.

작업 목록은 DOM에서 다시 추출하지 않고 `tasks` 상태를 변경한 뒤 화면을 다시 그립니다.

## 디버깅 순서

브라우저 상태가 예상과 다르면 다음 순서로 확인합니다.

```text
1. 어떤 값이 기준 상태인가?
2. 현재 기준 값은 실제로 무엇인가?
3. 이벤트가 발생했는가?
4. 이벤트의 target과 currentTarget은 무엇인가?
5. 상태 변경이 실제로 수행되었는가?
6. URL이나 저장소가 의도대로 바뀌었는가?
7. render가 최신 상태를 읽었는가?
8. DOM이 최신 상태를 표현하고 있는가?
```

History 관련 문제라면 다음을 확인합니다.

```text
1. pushState와 replaceState 중 의도한 것을 사용했는가?
2. URL 변경 직후 직접 render했는가?
3. 뒤로/앞으로 가기의 popstate를 처리했는가?
4. popstate에서 현재 URL을 다시 읽는가?
```

저장소 관련 문제라면 다음을 확인합니다.

```text
1. getItem()이 null을 반환할 수 있음을 처리했는가?
2. JSON.parse() 실패를 처리했는가?
3. 파싱된 값의 구조를 검증했는가?
4. 이전 버전 데이터가 남아 있을 수 있는가?
```

## 흔한 실수

- `querySelector()`가 항상 요소를 반환한다고 가정합니다.
- 필요한 요소가 실제로 `form`, `input`, `button`인지 확인하지 않습니다.
- 사용자 문자열을 `innerHTML`에 직접 넣습니다.
- `preventDefault()`가 이벤트 버블링까지 막는다고 생각합니다.
- 이벤트 위임 코드에서 `event.target`이 항상 `Element`라고 가정합니다.
- 목록 항목마다 리스너를 계속 추가하고, 다시 렌더링할 때 중복 등록합니다.
- `event.target`과 `event.currentTarget`을 같은 값이라고 생각합니다.
- DOM에 보이는 문자열을 다시 읽어 애플리케이션의 업무 상태로 사용합니다.
- URL과 메모리가 같은 검색 조건을 각각 독립적으로 보관합니다.
- URL만 바꾸고 변경 직후 화면을 다시 그리지 않습니다.
- `pushState()`를 호출하면 `popstate`도 즉시 발생한다고 생각합니다.
- 뒤로 가기에서 현재 URL을 다시 읽지 않습니다.
- `localStorage`가 문자열 저장소라는 점을 잊습니다.
- JSON 파싱에 성공하면 데이터 구조도 올바르다고 생각합니다.
- `localStorage` 값을 검증 없이 사용합니다.
- 이전 버전의 저장 형식이 브라우저에 남아 있을 가능성을 고려하지 않습니다.
- 브라우저 저장소의 값을 서버 권한 판단에 사용합니다.
- 비밀번호나 장기 API 키 같은 비밀값을 브라우저 저장소에 넣습니다.
- `render()` 안에서 저장과 네트워크 요청까지 몰래 실행해 호출 효과를 예측하기 어렵게 만듭니다.

## 관련 exercise

[`browser-directory`](../../exercises/browser-directory/README.md)는 URL을 검색 조건의 기준으로 사용하고 뒤로 가기에서 화면을 복원합니다.

## 완료 기준

다음 내용을 설명하고 직접 구현할 수 있으면 이 문서의 목표를 달성한 것입니다.

- DOM이 HTML을 브라우저 객체 트리로 표현한 것임을 설명할 수 있습니다.
- `querySelector()` 결과가 `null`일 수 있음을 처리하고 필요한 요소의 종류를 확인할 수 있습니다.
- 사용자 문자열을 `textContent`로 DOM 텍스트에 출력할 수 있습니다.
- `innerHTML`과 `textContent`의 목적 차이를 설명할 수 있습니다.
- 폼의 `submit`과 `preventDefault()`를 목적에 맞게 사용할 수 있습니다.
- `preventDefault()`와 이벤트 전파 중단이 서로 다른 기능임을 설명할 수 있습니다.
- 이벤트 버블링을 이용해 부모 요소 하나에서 동적으로 추가된 자식 버튼의 이벤트를 처리할 수 있습니다.
- `event.target`과 `event.currentTarget`의 차이를 설명할 수 있습니다.
- 값마다 메모리, URL, 브라우저 저장소, 서버 중 적절한 기준 위치를 선택할 수 있습니다.
- URL을 검색 상태의 기준으로 사용해 새로 고침과 공유가 가능한 화면을 만들 수 있습니다.
- `pushState()`와 `replaceState()`의 방문 기록 차이를 설명할 수 있습니다.
- 두 번 검색한 뒤 뒤로 가기로 이전 URL과 화면을 복원할 수 있습니다.
- `pushState()` 자체는 `popstate`를 발생시키지 않는다는 점을 설명할 수 있습니다.
- `localStorage`에서 읽은 JSON을 파싱한 뒤 실제 데이터 구조까지 검증할 수 있습니다.
- 잘못되거나 이전 버전의 저장 값이 있어도 안전한 기본 상태로 시작할 수 있습니다.
- DOM을 업무 데이터의 기준으로 사용하지 않고 상태에서 DOM을 렌더링할 수 있습니다.
- `render()`와 저장·네트워크 같은 외부 동작의 책임을 구분할 수 있습니다.
