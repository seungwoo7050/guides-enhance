# DOM, 이벤트, URL과 저장소

DOM은 브라우저가 HTML을 해석해 만든 객체입니다. JavaScript는 DOM을 읽고 이벤트를 처리해 화면을 바꿉니다. 같은 값을 DOM, 전역 변수, URL, `localStorage`에 각각 저장하면 어느 값이 최신인지 판단하기 어렵습니다. 상태마다 기준이 될 위치를 하나 정해야 합니다.

이 문서는 브라우저 상태와 URL 탐색을 구현하기 직전에 읽는 JIT 문서입니다.

## 목표

- 필요한 DOM 요소를 확인하고 안전하게 변경합니다.
- 폼 기본 동작과 이벤트 버블링을 이해합니다.
- 메모리, URL, 브라우저 저장소, 서버 중 값의 기준 위치를 선택합니다.
- History API와 `popstate`로 이전 화면을 복원합니다.
- 브라우저 저장소의 값도 외부 입력처럼 검사합니다.

## DOM 요소 확인

```js
const form = document.querySelector("#search-form");
if (!(form instanceof HTMLFormElement)) {
  throw new Error("검색 폼을 찾을 수 없습니다.");
}
```

요소가 항상 존재한다고 단언하면 HTML이 바뀌었을 때 관련 없는 코드에서 오류가 납니다. 시작할 때 필요한 요소를 확인하면 원인을 바로 찾을 수 있습니다.

## 사용자 문자열 출력

```js
const title = document.createElement("span");
title.textContent = userInput;
```

일반적인 제목과 메모는 `textContent`로 출력합니다. 사용자 문자열을 `innerHTML`에 넣으면 HTML로 해석될 수 있습니다. 제품에서 HTML 입력을 허용한다면 검증된 새니타이저와 명확한 허용 규칙이 필요합니다.

```js
list.replaceChildren(...tasks.map(renderTask));
```

상태에서 DOM 노드를 새로 만든 뒤 자식을 교체하면 화면과 상태를 맞추기 쉽습니다.

## 이벤트와 기본 동작

```js
form.addEventListener("submit", (event) => {
  event.preventDefault();
  // 입력을 읽고 저장합니다.
});
```

`preventDefault()`는 폼 제출이나 링크 이동 같은 기본 동작을 막지만 이벤트 전파는 막지 않습니다.

이벤트 버블링을 이용하면 목록의 부모에서 동적으로 추가된 버튼까지 처리할 수 있습니다.

```js
list.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-task-id]");
  if (!button) return;
  removeTask(button.dataset.taskId);
});
```

`target`은 이벤트가 시작된 요소이고 `currentTarget`은 현재 리스너가 붙은 요소입니다.

## 상태를 둘 위치

| 값 | 적합한 위치 | 예시 |
|---|---|---|
| 잠깐 쓰는 화면 값 | 컴포넌트·모듈 메모리 | 모달 열림, 입력 초안 |
| 공유하거나 뒤로 가기로 복원할 값 | URL | 검색어, 필터, 선택한 탭 |
| 새로 고침 뒤 복원할 비민감 편의 정보 | `localStorage` | 테마, 임시 초안 |
| 권한과 업무 데이터 | 서버 | 계정, 역할, 주문, 보드 내용 |

같은 검색어를 전역 변수와 URL에서 각각 바꾸지 않습니다. URL을 기준으로 정했다면 화면을 그릴 때도 URL을 다시 읽습니다.

## History API

```js
function readQuery() {
  return new URL(location.href).searchParams.get("q")?.trim() ?? "";
}

function writeQuery(query) {
  const url = new URL(location.href);
  if (query) url.searchParams.set("q", query);
  else url.searchParams.delete("q");
  history.pushState(null, "", url);
  render(readQuery());
}
```

- `pushState()`는 방문 기록에 새 항목을 추가합니다.
- `replaceState()`는 현재 항목을 바꿉니다.

사용자가 되돌아갈 검색·필터 변경은 `pushState()`가 적합합니다. 초기 URL 정리처럼 별도 기록이 필요 없는 변경은 `replaceState()`를 사용할 수 있습니다.

```js
window.addEventListener("popstate", () => {
  render(readQuery());
});
```

뒤로 가기와 앞으로 가기에서는 이동한 URL을 다시 읽습니다. `pushState()`를 호출했다고 `popstate`가 자동으로 발생하지는 않으므로 변경 직후 화면도 직접 갱신합니다.

## 브라우저 저장소 검사

사용자는 개발자 도구에서 값을 바꿀 수 있고, 이전 버전의 데이터가 남아 있을 수도 있습니다.

```js
function readTasks() {
  try {
    const value = JSON.parse(localStorage.getItem("tasks.v1") ?? "[]");
    return Array.isArray(value) ? value.filter(isTask) : [];
  } catch {
    return [];
  }
}
```

키 이름에 버전을 넣거나 저장 값 안에 버전을 둡니다. 읽지 못하는 값 때문에 애플리케이션 전체가 시작되지 않게 안전한 기본값을 정합니다.

`localStorage`에는 다음 값을 저장하지 않습니다.

- 세션 토큰과 비밀번호
- 장기 API 키
- 서버만 알아야 하는 비밀값
- 저장할 필요가 없는 민감한 개인정보

## 상태 변경과 화면 그리기

```js
let tasks = readTasks();

function add(title) {
  tasks = [...tasks, createTask(title)];
  persist(tasks);
  render(tasks, readFilter());
}
```

작은 애플리케이션에서는 이 정도면 충분합니다. DOM에서 업무 데이터를 다시 추출하지 않고, `render()`가 저장이나 네트워크 요청까지 몰래 실행하지 않게 합니다.

## 흔한 실수

- 사용자 문자열을 `innerHTML`에 직접 넣습니다.
- 목록 항목마다 리스너를 계속 추가하고 제거하지 않습니다.
- URL과 메모리가 같은 검색 조건을 각각 보관합니다.
- URL만 바꾸고 `popstate`를 처리하지 않습니다.
- `localStorage` 값을 검증 없이 사용합니다.
- 브라우저 저장소에 인증 정보를 저장합니다.

## 관련 exercise

[`browser-directory`](../../exercises/browser-directory/README.md)는 URL을 검색 조건의 기준으로 사용하고 뒤로 가기에서 화면을 복원합니다.

## 완료 기준

- 사용자 문자열을 DOM 텍스트로 출력합니다.
- 폼 제출과 이벤트 버블링을 목적에 맞게 사용합니다.
- 값마다 메모리, URL, 브라우저 저장소, 서버 중 한 곳을 기준으로 정합니다.
- 두 번 검색한 뒤 뒤로 가기로 이전 결과를 복원합니다.
- 잘못된 저장 값이 있어도 안전한 기본 상태로 시작합니다.
