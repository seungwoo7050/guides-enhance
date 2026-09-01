# 비동기 작업과 `fetch`

비동기 코드에서 가장 중요한 것은 `await` 문법 자체가 아닙니다.

실제로 판단해야 하는 것은 다음과 같습니다.

- 작업은 언제 시작되었는가?
- 호출자는 그 작업의 완료를 기다리는가?
- 실패하면 어느 코드가 처리하는가?
- 사용자가 다른 화면으로 이동했는데 결과가 아직 필요한가?
- 여러 요청의 완료 순서가 시작 순서와 달라져도 안전한가?
- 일정 시간 안에 끝나지 않으면 어떻게 중단하는가?
- 중단하거나 실패한 뒤 타이머, 이벤트 리스너 같은 자원을 정리했는가?

비동기 작업은 "나중에 결과가 도착한다"는 점 때문에 **작업을 시작한 시점의 상태와 결과를 적용하는 시점의 상태가 다를 수 있습니다.**

예를 들어 사용자가 `cat`을 검색한 직후 `dog`을 검색했다고 가정합니다.

```text
cat 요청 시작
dog 요청 시작
dog 응답 완료
cat 응답 완료
```

요청을 시작한 순서와 완료된 순서는 다릅니다. 아무 확인 없이 마지막으로 도착한 결과를 그리면 화면에는 최신 검색어인 `dog`이 아니라 오래된 `cat` 결과가 나타날 수 있습니다.

따라서 비동기 코드는 단순히 "기다렸다가 결과를 사용한다"가 아니라 **실패, 취소, 오래된 결과, 자원 정리까지 포함하여 작업의 생명주기를 관리하는 코드**라고 이해하는 것이 좋습니다.

## 목표

- Promise가 아직 끝나지 않은 작업의 결과를 표현한다는 점을 설명합니다.
- `async` 함수가 Promise를 반환하고 `throw`가 Promise 거부로 전달되는 과정을 이해합니다.
- `await`가 현재 JavaScript 실행 전체를 멈추는 것이 아니라 현재 `async` 함수의 진행을 일시 중단한다는 점을 설명합니다.
- 태스크와 마이크로태스크의 최소 실행 순서를 이해합니다.
- 네트워크 실패와 HTTP 오류 응답을 구분합니다.
- HTTP 성공 여부와 응답 본문 파싱 성공 여부를 별도로 처리합니다.
- 대기, 빈 결과, 성공, 오류를 서로 다른 화면 상태로 표현합니다.
- 필요 없어진 요청을 `AbortController`로 취소합니다.
- 취소와 실제 실패를 구분합니다.
- 이전 요청의 늦은 응답이 최신 화면을 덮지 않도록 합니다.
- 타임아웃과 일반 취소의 의미를 구분합니다.
- 독립적인 작업만 병렬로 실행합니다.
- 타이머와 이벤트 리스너 같은 자원을 명시적으로 정리합니다.
- 변경 요청을 재시도할 때 중복 실행 가능성을 고려합니다.

## Promise는 미래의 결과를 나타냅니다

Promise는 지금 즉시 결과를 가지고 있지 않을 수 있는 작업의 완료 상태를 나타내는 객체입니다.

개념적으로 Promise는 다음 상태 중 하나에 있습니다.

```text
pending
  │
  ├─ 성공 → fulfilled
  │
  └─ 실패 → rejected
```

예를 들어 `fetch()`는 HTTP 요청이 끝날 때까지 기다렸다가 결과를 직접 반환하지 않습니다.

```js
const promise = fetch("/api/boards");
```

`promise`는 `Response` 자체가 아니라 나중에 `Response`를 제공할 Promise입니다.

```js
console.log(promise instanceof Promise); // true
```

결과가 필요하면 `await`하거나 Promise 메서드로 후속 작업을 연결합니다.

```js
const response = await fetch("/api/boards");
```

또는:

```js
fetch("/api/boards")
  .then((response) => {
    console.log(response.status);
  })
  .catch((error) => {
    console.error(error);
  });
```

이 문서에서는 흐름을 읽기 쉬운 `async`/`await`를 중심으로 설명합니다.

## `async` 함수는 항상 Promise를 반환합니다

다음 함수는 문자열을 반환하는 것처럼 보입니다.

```js
async function getTitle() {
  return "학습 보드";
}
```

하지만 `async` 함수의 실제 반환값은 Promise입니다.

```js
const result = getTitle();

console.log(result instanceof Promise); // true
```

호출자는 다음처럼 결과를 기다릴 수 있습니다.

```js
const title = await getTitle();

console.log(title); // "학습 보드"
```

개념적으로 다음 두 함수는 비슷한 의미를 가집니다.

```js
async function getTitle() {
  return "학습 보드";
}
```

```js
function getTitle() {
  return Promise.resolve("학습 보드");
}
```

즉 `async` 함수 안의 일반 `return` 값은 호출자에게 Promise의 성공 결과로 전달됩니다.

## `throw`는 Promise 거부로 전달됩니다

`async` 함수 안에서 오류를 던지면 함수 호출 자체가 동기적으로 값을 던지는 것이 아니라 반환한 Promise가 거부됩니다.

```js
async function loadBoard(id) {
  if (!id) {
    throw new Error("id가 필요합니다.");
  }

  return { id };
}
```

호출자는 `await` 시점에서 오류를 받습니다.

```js
try {
  await loadBoard("");
} catch (error) {
  console.error(error);
}
```

흐름은 다음과 같습니다.

```text
loadBoard("")
   ↓
async 함수가 Promise 반환
   ↓
함수 내부 throw
   ↓
Promise rejected
   ↓
호출자의 await에서 throw처럼 전달
   ↓
catch
```

이 규칙 때문에 비동기 함수에서도 동기 함수와 비슷한 방식으로 오류를 위쪽 호출자로 전달할 수 있습니다.

## `await`는 무엇을 기다리는가

다음 코드를 생각해 봅니다.

```js
async function loadBoard(id) {
  const response =
    await fetch(`/api/boards/${id}`);

  return response.json();
}
```

`await`를 만나면 현재 `loadBoard()`의 이후 실행은 Promise가 완료될 때까지 중단됩니다.

그러나 JavaScript 실행 환경 전체가 멈추는 것은 아닙니다.

그동안 브라우저는 다음과 같은 일을 계속 처리할 수 있습니다.

- 다른 이벤트 처리
- 다른 네트워크 요청
- 타이머
- 렌더링 관련 작업
- 다른 Promise 후속 작업

즉 다음처럼 이해합니다.

```text
await
→ 현재 async 함수의 다음 줄 실행을 나중으로 미룸
→ 브라우저 전체를 동기적으로 멈추는 기능은 아님
```

## `await`하지 않은 Promise

다음 코드에는 문제가 있습니다.

```js
async function unsafe() {
  saveBoard();
}
```

`saveBoard()`가 Promise를 반환한다고 가정하면 `unsafe()`는 저장 작업의 완료를 기다리지 않습니다.

따라서 다음 두 가지가 불명확해집니다.

```text
저장이 언제 완료되는가?
저장이 실패하면 누가 처리하는가?
```

작업의 성공이 다음 동작에 필요하다면 기다립니다.

```js
async function safe() {
  await saveBoard();
  showSavedMessage();
}
```

이제 `showSavedMessage()`는 저장이 성공한 뒤 실행됩니다.

저장이 실패하면 그 실패는 `safe()` 호출자에게 전달됩니다.

## 반환만 해도 Promise를 연결할 수 있습니다

다음처럼 `await` 없이 Promise를 그대로 반환할 수도 있습니다.

```js
async function save() {
  return saveBoard();
}
```

호출자는 여전히 `save()`의 Promise를 기다릴 수 있습니다.

```js
await save();
```

단순히 하위 Promise를 전달하는 경우에는 불필요한 `await`가 없어도 됩니다.

반면 현재 함수에서 `try...catch`나 `finally`로 하위 작업의 완료를 처리해야 한다면 `await`가 필요할 수 있습니다.

```js
async function save() {
  try {
    return await saveBoard();
  } catch (error) {
    throw new Error(
      "보드를 저장하지 못했습니다.",
      { cause: error }
    );
  }
}
```

## 의도적으로 기다리지 않는 작업

일부 작업은 호출자가 결과를 기다리지 않아도 될 수 있습니다.

예를 들어 중요하지 않은 사용 통계 전송을 별도 작업으로 시작할 수 있습니다.

하지만 다음처럼 호출만 버리면 실패 처리 위치가 없습니다.

```js
sendAnalytics();
```

다음처럼 `void`를 붙이는 코드도 볼 수 있습니다.

```js
void sendAnalytics();
```

`void`는 "이 반환값을 사용하지 않겠다"는 의도를 표현할 수 있지만 **Promise 실패를 처리해 주지는 않습니다.**

```text
void promise
→ 결과값을 사용하지 않음
→ 실패가 자동으로 처리됨: 아님
```

기다리지 않는 작업이라도 실패를 어디에서 관찰할지 정합니다.

```js
void sendAnalytics().catch((error) => {
  console.error("통계 전송 실패", error);
});
```

중요한 저장이나 결제 같은 작업은 단순한 fire-and-forget으로 만들지 않습니다.

## Promise 실패를 놓치지 않습니다

Promise가 거부되었는데 아무 코드도 기다리거나 `catch`하지 않으면 환경에서 처리되지 않은 Promise 거부로 보고될 수 있습니다.

다음 코드를 생각해 봅니다.

```js
function onSaveClick() {
  saveBoard();
}
```

`saveBoard()`가 실패해도 `onSaveClick()`에는 오류 처리 코드가 없습니다.

사용자에게 오류를 표시해야 하는 작업이라면 다음처럼 명시적으로 처리합니다.

```js
async function onSaveClick() {
  try {
    await saveBoard();
    showSuccess();
  } catch (error) {
    showError(toUserMessage(error));
  }
}
```

비동기 호출을 볼 때는 항상 다음 질문을 할 수 있어야 합니다.

```text
이 Promise의 성공과 실패는 누가 관찰하는가?
```

## 이벤트 루프의 최소 모델

브라우저 JavaScript는 비동기 작업을 처리하기 위해 이벤트 루프를 사용합니다.

전체 세부 규칙을 처음부터 외울 필요는 없지만 다음 세 가지는 구분할 수 있어야 합니다.

```text
현재 동기 코드
마이크로태스크
다음 태스크
```

예를 들어:

```js
console.log("sync");

queueMicrotask(() => {
  console.log("microtask");
});

setTimeout(() => {
  console.log("task");
}, 0);
```

출력은 다음 순서입니다.

```text
sync
microtask
task
```

현재 실행 중인 동기 코드가 먼저 끝납니다.

그 뒤 예약된 마이크로태스크가 처리되고, 이후 다음 태스크로 넘어갑니다.

## Promise 후속 작업도 마이크로태스크로 이어집니다

다음 코드를 생각해 봅니다.

```js
console.log("A");

Promise.resolve().then(() => {
  console.log("B");
});

console.log("C");
```

출력은:

```text
A
C
B
```

`.then()`의 콜백은 현재 동기 코드 중간에 끼어들지 않고 이후 마이크로태스크에서 실행됩니다.

`await` 뒤의 코드도 Promise가 준비된 뒤 비슷하게 이후 실행으로 이어집니다.

```js
async function example() {
  console.log("1");
  await Promise.resolve();
  console.log("2");
}

console.log("A");
example();
console.log("B");
```

출력은:

```text
A
1
B
2
```

핵심은 다음입니다.

```text
비동기 콜백이 실행될 때는
현재 함수 호출 시점보다 시간이 지난 뒤일 수 있음
```

따라서 그 사이 애플리케이션 상태가 바뀌었을 가능성을 항상 고려해야 합니다.

## 비동기 작업 사이에 상태가 달라질 수 있습니다

다음 코드는 요청을 시작할 때 선택한 `boardId`가 응답 시점에도 최신이라고 가정합니다.

```js
let selectedBoardId = "1";

async function loadSelectedBoard() {
  const board =
    await loadBoard(selectedBoardId);

  render(board);
}
```

하지만 기다리는 동안 사용자가 다른 보드를 선택할 수 있습니다.

```text
selectedBoardId = "1"
loadBoard("1") 시작

사용자가 "2" 선택
selectedBoardId = "2"

loadBoard("1") 완료
render(board1)
```

따라서 비동기 코드에서는 **작업을 시작했을 때의 상태와 작업이 끝났을 때의 상태가 같다고 자동으로 가정하면 안 됩니다.**

이 문제는 뒤에서 요청 취소와 버전 검사로 다룹니다.

## `fetch()`의 기본 결과

`fetch()`는 HTTP 요청을 보내고 서버에서 응답을 받으면 `Response` 객체를 제공합니다.

```js
const response =
  await fetch("/api/boards/42");
```

`Response`에는 다음과 같은 정보가 있습니다.

```js
response.status
response.ok
response.headers
```

예를 들어:

```js
console.log(response.status); // 200
console.log(response.ok);     // true
```

`response.ok`는 HTTP 상태 코드가 일반적인 성공 범위인 `200`부터 `299` 사이인지 나타냅니다.

## `fetch()`는 404나 500에서 자동으로 거부되지 않습니다

이 부분은 매우 중요합니다.

서버가 다음처럼 HTTP 오류 응답을 정상적으로 반환했다고 가정합니다.

```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{"message":"보드를 찾을 수 없습니다."}
```

이 경우 서버와 연결하고 HTTP 응답을 받는 데 성공했으므로 `fetch()` 자체는 일반적으로 `Response`를 반환합니다.

```js
const response =
  await fetch("/api/boards/missing");

console.log(response.status); // 404
console.log(response.ok);     // false
```

따라서 다음 코드는 `404`를 성공 흐름으로 그대로 통과시킬 수 있습니다.

```js
const response = await fetch(url);
return response.json();
```

애플리케이션에서 HTTP 오류를 실패로 취급하려면 직접 검사해야 합니다.

```js
const response = await fetch(url);

if (!response.ok) {
  throw new Error(
    `HTTP 오류: ${response.status}`
  );
}
```

## 네트워크 실패와 HTTP 실패

두 종류를 구분합니다.

### HTTP 오류 응답

서버가 HTTP 응답을 반환했습니다.

```text
브라우저
  ↓ 요청
서버
  ↓
404 / 500 응답
```

이 경우:

```text
fetch Promise → fulfilled
response.ok   → false
response.status → 404 또는 500
```

### 응답을 받지 못한 실패

서버의 HTTP 응답까지 도달하지 못한 경우가 있습니다.

예를 들어:

- DNS 실패
- 연결 실패
- 일부 TLS 실패
- 브라우저가 네트워크 요청을 실패로 처리한 경우
- 요청 취소
- 브라우저에서 허용되지 않아 네트워크 오류로 노출되는 경우

이 경우 `fetch()` Promise가 거부됩니다.

```js
try {
  await fetch(url);
} catch (error) {
  // Response를 받지 못한 실패일 수 있습니다.
}
```

따라서 다음 두 단계의 실패를 구분합니다.

```text
fetch 자체 실패
→ Response 없음

HTTP 상태 실패
→ Response 있음
→ response.ok === false
```

## 응답 본문 파싱도 별도의 실패 단계입니다

`fetch()`가 성공하고 `response.ok`가 `true`라고 해서 JSON 파싱까지 반드시 성공하는 것은 아닙니다.

```js
const response = await fetch(url);

if (!response.ok) {
  throw new Error("HTTP 오류");
}

const data = await response.json();
```

서버가 잘못된 JSON을 반환하면 마지막 줄에서 실패할 수 있습니다.

예를 들어 본문이 다음과 같다면:

```text
{broken-json
```

`response.json()`이 거부됩니다.

따라서 네트워크 요청은 다음과 같이 여러 경계를 가집니다.

```text
연결과 HTTP 응답
      ↓
HTTP 상태 확인
      ↓
본문 형식 확인
      ↓
본문 파싱
      ↓
애플리케이션 데이터 구조 검증
```

"요청 성공"이라는 말만으로 이 모든 단계가 성공했다고 판단하면 안 됩니다.

## `Content-Type`도 확인합니다

JSON API를 기대하는데 프록시나 서버가 HTML 오류 페이지를 반환할 수 있습니다.

```html
<!doctype html>
<h1>Bad Gateway</h1>
```

그 상태에서 `response.json()`을 호출하면 JSON 파싱 오류만 보이게 됩니다.

따라서 필요하면 `Content-Type`을 확인합니다.

```js
function isJsonResponse(response) {
  const contentType =
    response.headers.get("content-type") ?? "";

  return contentType
    .toLowerCase()
    .includes("application/json");
}
```

사용 예:

```js
const response = await fetch(url);

if (!isJsonResponse(response)) {
  throw new Error(
    "서버가 JSON 응답을 반환하지 않았습니다."
  );
}
```

실제 API가 `application/problem+json`처럼 다른 JSON 계열 미디어 타입을 사용하는 경우도 있으므로 프로젝트의 응답 계약에 맞게 검사 규칙을 정합니다.

## 응답 본문은 한 번 소비하는 것으로 생각합니다

`Response` 본문은 스트림이므로 일반적으로 한 번 읽고 나면 다시 같은 방식으로 읽을 수 없습니다.

다음처럼 먼저 텍스트를 읽고 다시 JSON으로 읽으려 하면 문제가 됩니다.

```js
const text = await response.text();
const data = await response.json();
```

보통은 어떤 방식으로 읽을지 한 번 결정합니다.

오류 응답이 JSON일 수도 있고 텍스트일 수도 있다면 먼저 텍스트로 읽은 뒤 필요하면 JSON 파싱을 시도하는 방식도 사용할 수 있습니다.

```js
async function readResponseText(response) {
  return await response.text();
}
```

혹은 응답 복제가 실제로 필요한 특별한 경우 `response.clone()`을 사용할 수 있지만, 일반적인 API 처리에서는 불필요하게 복잡하게 만들지 않습니다.

## 안전한 오류 본문 읽기

오류 응답이 항상 JSON이라고 가정하지 않는 간단한 함수는 다음처럼 만들 수 있습니다.

```js
async function readSafeError(response) {
  const text = await response.text();

  if (!text) {
    return null;
  }

  const contentType =
    response.headers.get("content-type") ?? "";

  if (
    contentType
      .toLowerCase()
      .includes("application/json")
  ) {
    try {
      const value = JSON.parse(text);

      if (
        typeof value === "object" &&
        value !== null &&
        typeof value.message === "string"
      ) {
        return value.message;
      }
    } catch {
      // JSON이라고 선언했지만 실제 본문이 잘못된 경우
      // 아래의 일반 텍스트 처리로 이어집니다.
    }
  }

  return text.slice(0, 500);
}
```

실제 제품에서는 서버 내부 정보나 개인정보를 그대로 사용자에게 보여 주지 않도록 별도 정책이 필요합니다.

## HTTP 오류 타입 만들기

화면마다 `response.ok` 처리 방식을 반복하기보다 요청 계층에서 애플리케이션이 구분할 수 있는 오류로 바꿀 수 있습니다.

```js
class HttpError extends Error {
  constructor(status, message) {
    super(message ?? `HTTP ${status}`);
    this.name = "HttpError";
    this.status = status;
  }
}
```

요청 함수:

```js
async function requestJson(url, options) {
  const response =
    await fetch(url, options);

  if (!response.ok) {
    const message =
      await readSafeError(response);

    throw new HttpError(
      response.status,
      message
    );
  }

  const contentType =
    response.headers.get("content-type") ?? "";

  if (
    !contentType
      .toLowerCase()
      .includes("application/json")
  ) {
    throw new Error(
      "JSON 응답을 기대했지만 다른 형식이 왔습니다."
    );
  }

  return response.json();
}
```

이제 호출자는 HTTP 상태를 구분할 수 있습니다.

```js
try {
  const board =
    await requestJson("/api/boards/42");

  renderBoard(board);
} catch (error) {
  if (
    error instanceof HttpError &&
    error.status === 404
  ) {
    showNotFound();
    return;
  }

  showGenericError();
}
```

## 파싱 뒤에도 데이터 검증이 필요합니다

JSON 파싱 성공은 데이터 구조가 올바르다는 뜻이 아닙니다.

다음 JSON은 문법적으로 유효합니다.

```json
{
  "unexpected": true
}
```

하지만 코드가 다음 구조를 기대한다면 올바른 보드가 아닙니다.

```json
{
  "id": "42",
  "title": "학습 보드"
}
```

따라서 외부 응답은 필요에 따라 구조까지 검사합니다.

```js
function isBoard(value) {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof value.id === "string" &&
    typeof value.title === "string"
  );
}
```

```js
const value =
  await requestJson("/api/boards/42");

if (!isBoard(value)) {
  throw new Error(
    "서버 응답 형식이 올바르지 않습니다."
  );
}
```

비동기 요청의 성공 조건은 단순히 Promise가 fulfilled되었다는 것보다 더 구체적일 수 있습니다.

## 화면 상태를 하나의 값으로 표현합니다

데이터를 불러오는 화면에는 보통 여러 상태가 있습니다.

```text
아직 요청하지 않음
요청 중
성공했지만 결과 없음
성공했고 데이터 있음
실패
```

이를 빈 배열 하나로 모두 표현하면 구분이 사라집니다.

```js
let users = [];
```

이 `[]`만 보고는 다음을 알 수 없습니다.

```text
아직 요청하지 않았는가?
요청 중인가?
정상적으로 요청했는데 결과가 0개인가?
```

## 여러 불리언보다 상태 유니언이 안전합니다

다음처럼 여러 불리언을 따로 두면:

```js
let loading = false;
let error = false;
let empty = false;
```

실수로 불가능한 조합을 만들 수 있습니다.

```text
loading = true
error   = true
```

TypeScript에서는 상태를 서로 배타적인 값으로 표현할 수 있습니다.

```ts
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "empty" }
  | { status: "ready"; data: T }
  | { status: "error"; message: string };
```

이제 상태는 한 번에 하나입니다.

```text
idle
loading
empty
ready
error
```

렌더링 코드도 상태별로 명확하게 나눌 수 있습니다.

```ts
function renderUsers(
  state: LoadState<User[]>
) {
  switch (state.status) {
    case "idle":
      renderIdle();
      return;

    case "loading":
      renderLoading();
      return;

    case "empty":
      renderEmpty();
      return;

    case "ready":
      renderList(state.data);
      return;

    case "error":
      renderError(state.message);
      return;
  }
}
```

## `empty`는 성공 상태의 한 종류입니다

빈 결과와 오류를 구분합니다.

```text
검색 결과 0건
→ 요청과 응답은 정상
→ empty

서버 연결 실패
→ 요청 실패
→ error
```

사용자에게 보여 줄 메시지도 달라집니다.

```text
empty → "검색 결과가 없습니다."
error → "결과를 불러오지 못했습니다."
```

이 둘을 같은 빈 배열로 처리하면 실제 장애가 정상적인 빈 검색 결과처럼 보일 수 있습니다.

## 요청 시작과 완료에서 상태를 명시합니다

간단한 흐름은 다음과 같습니다.

```js
let state = { status: "idle" };

async function loadUsers() {
  state = { status: "loading" };
  render(state);

  try {
    const users = await fetchUsers();

    state =
      users.length === 0
        ? { status: "empty" }
        : {
            status: "ready",
            data: users,
          };
  } catch (error) {
    state = {
      status: "error",
      message: toUserMessage(error),
    };
  }

  render(state);
}
```

이 예제는 아직 취소와 요청 경쟁을 처리하지 않습니다. 뒤에서 보완합니다.

## 요청 취소

사용자가 더 이상 결과를 필요로 하지 않는데 네트워크 요청이 계속 실행될 수 있습니다.

예를 들어 검색창에서:

```text
c 입력  → 요청 A
ca 입력 → 요청 B
cat 입력 → 요청 C
```

A와 B의 결과는 C가 시작된 시점에서 이미 필요 없을 수 있습니다.

브라우저 `fetch()`에서는 `AbortController`를 사용해 요청 취소 신호를 전달할 수 있습니다.

```js
const controller =
  new AbortController();

const promise = fetch(url, {
  signal: controller.signal,
});
```

나중에:

```js
controller.abort();
```

호출하면 해당 신호를 사용하는 작업에 취소를 요청합니다.

## 취소 신호는 작업에 전달해야 합니다

`AbortController`를 만들기만 해서는 아무 일도 일어나지 않습니다.

다음처럼 `signal`을 실제 작업에 전달해야 합니다.

```js
async function loadUsers(signal) {
  const response = await fetch(
    "/api/users",
    { signal }
  );

  return response.json();
}
```

호출하는 쪽:

```js
const controller =
  new AbortController();

loadUsers(controller.signal);

controller.abort();
```

하나의 신호를 여러 작업에 전달하면 같은 취소 의도로 여러 작업을 중단시킬 수도 있습니다.

## 취소는 일반 오류와 의미가 다를 수 있습니다

사용자가 새 검색어를 입력해서 이전 요청을 취소한 상황은 보통 "서비스 장애"가 아닙니다.

따라서 일반적인 오류 메시지를 보여 주지 않는 경우가 많습니다.

```js
try {
  await fetch(url, { signal });
} catch (error) {
  if (
    error instanceof DOMException &&
    error.name === "AbortError"
  ) {
    return;
  }

  throw error;
}
```

여기서는 사용자가 의도적으로 취소한 경우만 무시하고 다른 실패는 다시 상위 코드로 전달합니다.

중요한 점은 다음입니다.

```text
catch 모든 오류
→ 전부 무시
```

가 아니라:

```text
의도한 취소
→ 별도 처리

그 외 오류
→ 정상 오류 흐름으로 전달
```

입니다.

## 취소 오류 이름만 맹목적으로 믿지 않습니다

실행 환경과 취소 방법에 따라 오류 표현이 달라질 수 있습니다.

따라서 프로젝트에서 취소 처리를 공통 함수로 모으는 것이 유용할 수 있습니다.

```js
function isAbortError(error) {
  return (
    error instanceof DOMException &&
    error.name === "AbortError"
  );
}
```

사용:

```js
try {
  await loadUsers(signal);
} catch (error) {
  if (isAbortError(error)) {
    return;
  }

  throw error;
}
```

타임아웃 신호는 일반 취소와 다른 오류 이유로 표현될 수 있으므로 뒤에서 별도로 다룹니다.

## 이전 검색 요청을 취소합니다

검색할 때 새 요청이 시작되면 이전 요청을 취소할 수 있습니다.

```js
let activeController = null;

async function search(query) {
  activeController?.abort();

  const controller =
    new AbortController();

  activeController = controller;

  try {
    const result = await searchUsers(
      query,
      controller.signal
    );

    render(result);
  } catch (error) {
    if (isAbortError(error)) {
      return;
    }

    throw error;
  }
}
```

이제 새 검색은 이전 네트워크 요청에 취소 신호를 보냅니다.

## 취소만으로 늦은 결과 문제가 완전히 해결되지 않을 수 있습니다

취소에는 중요한 한계가 있습니다.

- 모든 비동기 API가 취소를 지원하는 것은 아닙니다.
- 취소 요청 직전에 작업이 이미 완료되었을 수 있습니다.
- 네트워크 이후 별도 계산이 진행 중일 수 있습니다.
- 취소가 "이미 적용된 결과"를 되돌려 주지는 않습니다.

따라서 결과를 적용하기 직전에 **이 결과가 아직 최신 작업의 결과인지** 확인하는 것이 유용합니다.

## 요청 버전으로 최신 결과를 확인합니다

간단한 버전 번호를 사용할 수 있습니다.

```js
let requestVersion = 0;

async function search(query) {
  const version =
    ++requestVersion;

  const result =
    await searchUsers(query);

  if (version !== requestVersion) {
    return;
  }

  render(result);
}
```

동작을 따라가 봅니다.

```text
cat 검색
version = 1
요청 A 시작

dog 검색
version = 2
요청 B 시작

B 완료
2 === 2
→ 적용

A 완료
1 !== 2
→ 무시
```

요청 A가 실제로 끝났더라도 오래된 결과는 화면에 적용되지 않습니다.

## 취소와 버전 검사는 목적이 다릅니다

두 방법은 서로 대체 관계가 아닙니다.

```text
AbortController
→ 더 이상 필요 없는 작업을 가능한 한 중단
→ 네트워크·자원 낭비 감소

버전 검사
→ 작업이 끝나더라도 오래된 결과를 화면에 적용하지 않음
→ 상태 정확성 보장
```

따라서 함께 사용할 수 있습니다.

## 취소와 버전 검사를 함께 사용합니다

검색 기능을 다음처럼 구성할 수 있습니다.

```js
let activeController = null;
let requestVersion = 0;

async function search(query) {
  const version =
    ++requestVersion;

  activeController?.abort();

  const controller =
    new AbortController();

  activeController = controller;

  try {
    const users =
      await searchUsers(
        query,
        controller.signal
      );

    if (version !== requestVersion) {
      return;
    }

    renderUsers(users);
  } catch (error) {
    if (isAbortError(error)) {
      return;
    }

    if (version !== requestVersion) {
      return;
    }

    renderError(
      toUserMessage(error)
    );
  } finally {
    if (
      version === requestVersion &&
      activeController === controller
    ) {
      activeController = null;
    }
  }
}
```

여기서 `finally`에서도 현재 요청인지 확인하는 이유가 중요합니다.

오래된 요청의 `finally`가 늦게 실행되어 새 요청의 컨트롤러를 지워 버리면 안 되기 때문입니다.

비동기 코드에서는 성공 결과뿐 아니라 **정리 코드도 오래된 작업이 최신 상태를 덮지 않는지** 확인해야 합니다.

## 화면 상태와 요청 버전을 함께 관리합니다

조금 더 완전한 검색 상태를 만들 수 있습니다.

```js
let requestVersion = 0;
let activeController = null;

let state = {
  status: "idle",
};

async function search(query) {
  const version =
    ++requestVersion;

  activeController?.abort();

  const controller =
    new AbortController();

  activeController = controller;

  state = {
    status: "loading",
  };
  render(state);

  try {
    const users =
      await searchUsers(
        query,
        controller.signal
      );

    if (version !== requestVersion) {
      return;
    }

    state =
      users.length === 0
        ? { status: "empty" }
        : {
            status: "ready",
            data: users,
          };

    render(state);
  } catch (error) {
    if (isAbortError(error)) {
      return;
    }

    if (version !== requestVersion) {
      return;
    }

    state = {
      status: "error",
      message: toUserMessage(error),
    };

    render(state);
  } finally {
    if (
      version === requestVersion &&
      activeController === controller
    ) {
      activeController = null;
    }
  }
}
```

이제 이전 요청은 최신 상태를 성공이나 오류 상태로 덮지 못합니다.

## 페이지를 떠날 때 취소합니다

컴포넌트나 페이지의 수명이 끝났는데 요청이 계속 진행될 필요가 없다면 취소할 수 있습니다.

일반 DOM 코드에서는 예를 들어 별도 정리 함수를 둘 수 있습니다.

```js
function createUserSearch() {
  let controller = null;

  async function search(query) {
    controller?.abort();

    controller =
      new AbortController();

    return searchUsers(
      query,
      controller.signal
    );
  }

  function dispose() {
    controller?.abort();
    controller = null;
  }

  return {
    search,
    dispose,
  };
}
```

사용하는 코드가 화면을 제거할 때 `dispose()`를 호출합니다.

프레임워크를 사용한다면 해당 프레임워크의 effect cleanup 또는 unmount 정리 지점에서 같은 원칙을 적용합니다.

## 타임아웃

네트워크 요청이 무한히 기다려도 되는 경우는 드뭅니다.

현대적인 환경에서는 다음처럼 타임아웃 신호를 사용할 수 있습니다.

```js
const response = await fetch(url, {
  signal: AbortSignal.timeout(5_000),
});
```

이 코드는 지정한 시간이 지나면 신호를 중단시켜 요청이 더 이상 기다리지 않도록 합니다.

실행 환경이 이 API를 지원하는지는 프로젝트의 브라우저·런타임 지원 범위에 맞게 확인합니다.

## 타임아웃과 사용자 취소는 의미가 다릅니다

둘 다 요청을 중단시키지만 의미는 다릅니다.

```text
사용자 취소
→ 더 이상 결과가 필요하지 않음

타임아웃
→ 정해진 시간 안에 결과를 얻지 못함
```

사용자에게 보여 줄 문장도 다를 수 있습니다.

```text
사용자 취소
→ 보통 별도 오류 메시지 없음

타임아웃
→ "요청 시간이 초과되었습니다."
```

환경에 따라 `AbortSignal.timeout()`에서 전달되는 중단 이유가 일반적인 `"AbortError"`와 다를 수 있습니다.

따라서 타임아웃을 일반 취소와 정확히 같은 조건으로만 검사하지 않도록 설계합니다.

## 직접 타이머로 타임아웃 만들기

지원 범위 때문에 직접 타이머를 사용하는 경우도 있습니다.

```js
async function fetchWithTimeout(
  url,
  options = {},
  timeoutMs = 5_000
) {
  const controller =
    new AbortController();

  const timer = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}
```

핵심은 `finally`에서 타이머를 정리하는 것입니다.

요청이 100ms 만에 성공했는데 타이머를 남겨 두면 5초 뒤 불필요한 콜백이 실행됩니다.

## `finally`는 성공과 실패 모두에서 정리에 사용합니다

다음 코드를 생각해 봅니다.

```js
const timer = setTimeout(...);

try {
  await work();
  clearTimeout(timer);
} catch (error) {
  clearTimeout(timer);
  throw error;
}
```

성공과 실패 양쪽에서 같은 정리 코드가 반복됩니다.

`finally`를 사용하면 정리 책임을 한 곳에 둘 수 있습니다.

```js
const timer = setTimeout(...);

try {
  await work();
} finally {
  clearTimeout(timer);
}
```

`finally`는 성공하든 실패하든 실행됩니다.

따라서 다음과 같은 자원 정리에 자주 사용합니다.

- 타이머
- 이벤트 리스너
- 로딩 플래그
- AbortController 참조
- 임시 자원

단, `finally` 안에서 새로운 오류를 던지거나 `return`하면 원래 성공·실패 흐름을 가릴 수 있으므로 정리 코드에 집중합니다.

## 타임아웃은 서버가 작업하지 않았다는 뜻이 아닙니다

특히 데이터를 변경하는 요청에서 중요합니다.

예를 들어 주문 생성 요청을 보냈다고 가정합니다.

```text
클라이언트
  ↓ POST /orders
서버
  ↓ 주문 생성 성공
네트워크 응답 지연 또는 손실
클라이언트 타임아웃
```

클라이언트 입장에서는 응답을 받지 못했지만 서버에서는 이미 주문이 만들어졌을 수 있습니다.

따라서 타임아웃은 다음 뜻이 아닙니다.

```text
타임아웃
= 서버가 아무 작업도 하지 않음
```

더 정확한 의미는:

```text
클라이언트가 제한 시간 안에 확정된 결과를 받지 못함
```

입니다.

## 변경 요청의 자동 재시도는 중복 실행을 만들 수 있습니다

다음처럼 타임아웃 뒤 같은 요청을 자동으로 다시 보내면:

```text
첫 번째 POST
→ 서버에서는 성공
→ 응답을 못 받음

자동 재시도 POST
→ 같은 작업을 두 번 실행할 수 있음
```

읽기 전용 요청은 재시도가 비교적 단순할 수 있지만, 데이터를 변경하는 요청은 중복 실행 여부를 고려해야 합니다.

필요한 경우 API 설계에서 다음과 같은 방법을 사용합니다.

- 요청별 고유 식별자
- idempotency key
- 서버의 중복 요청 감지
- 현재 상태 조회 후 재결정

구체적인 방식은 서버 API 계약에 따라 달라집니다.

## 순차 실행과 병렬 실행

다음 코드는 두 요청을 순서대로 실행합니다.

```js
const profile = await loadProfile();
const boards = await loadBoards();
```

흐름은 다음과 같습니다.

```text
loadProfile 시작
      ↓ 완료
loadBoards 시작
      ↓ 완료
```

두 번째 작업이 첫 번째 결과를 필요로 한다면 순차 실행이 맞습니다.

```js
const user = await loadUser();

const boards =
  await loadBoards(user.id);
```

하지만 서로 독립적인 요청이라면 동시에 시작할 수 있습니다.

```js
const profilePromise =
  loadProfile();

const boardsPromise =
  loadBoards();

const profile =
  await profilePromise;

const boards =
  await boardsPromise;
```

더 간단하게 `Promise.all()`을 사용할 수 있습니다.

```js
const [profile, boards] =
  await Promise.all([
    loadProfile(),
    loadBoards(),
  ]);
```

## `Promise.all()`은 작업을 시작시키는 마법이 아닙니다

다음 배열 표현식이 평가될 때 각 함수가 호출되어 Promise가 만들어집니다.

```js
Promise.all([
  loadProfile(),
  loadBoards(),
]);
```

즉 독립된 Promise들이 거의 같은 시점에 시작되고 `Promise.all()`은 모두 완료되기를 기다립니다.

다음처럼 작성하면 이미 첫 번째 요청을 기다린 뒤 두 번째 값을 전달하므로 병렬이 아닙니다.

```js
const profile =
  await loadProfile();

const boards =
  await loadBoards();

await Promise.all([
  profile,
  boards,
]);
```

이 시점에는 두 작업이 이미 끝난 뒤입니다.

## `Promise.all()`의 실패 의미

여러 Promise 중 하나가 거부되면 `Promise.all()`도 거부됩니다.

```js
try {
  const [profile, boards] =
    await Promise.all([
      loadProfile(),
      loadBoards(),
    ]);
} catch (error) {
  // 둘 중 하나 이상 실패
}
```

하지만 한 작업이 실패했다고 해서 이미 시작한 다른 작업이 자동으로 취소되지는 않습니다.

```text
A 시작
B 시작
A 실패
Promise.all 거부
B는 자동 취소되지 않음
```

B를 중단해야 한다면 공유 `AbortSignal`이나 별도 취소 로직을 사용합니다.

## 여러 병렬 요청에 같은 취소 신호 사용하기

같은 화면에 필요한 여러 요청을 함께 취소할 수 있습니다.

```js
async function loadDashboard(signal) {
  const [profile, boards] =
    await Promise.all([
      loadProfile(signal),
      loadBoards(signal),
    ]);

  return {
    profile,
    boards,
  };
}
```

호출:

```js
const controller =
  new AbortController();

try {
  const dashboard =
    await loadDashboard(
      controller.signal
    );
} finally {
  // 필요하면 호출자 쪽 자원 정리
}
```

페이지가 더 이상 필요 없으면:

```js
controller.abort();
```

두 함수가 모두 같은 `signal`을 실제 `fetch()`에 전달한다면 함께 취소할 수 있습니다.

## 일부 실패를 허용하려면 정책을 명확히 합니다

화면에 두 데이터가 필요하지만 하나가 실패해도 다른 하나는 보여 줄 수 있는 경우가 있습니다.

그때 `Promise.all()`의 "하나라도 실패하면 전체 실패" 정책이 맞지 않을 수 있습니다.

`Promise.allSettled()`를 사용할 수 있습니다.

```js
const results =
  await Promise.allSettled([
    loadProfile(),
    loadBoards(),
  ]);
```

각 결과는 성공 또는 실패 상태를 따로 가집니다.

```js
for (const result of results) {
  if (result.status === "fulfilled") {
    console.log(result.value);
  } else {
    console.error(result.reason);
  }
}
```

중요한 것은 API 선택보다 요구사항입니다.

```text
모든 데이터가 있어야 화면이 의미 있음
→ Promise.all()

일부 실패해도 나머지를 사용할 수 있음
→ 개별 처리 또는 Promise.allSettled()
```

## 오류 종류를 애플리케이션 수준에서 정리합니다

화면마다 다음과 같은 코드를 반복하면 오류 정책이 제각각이 되기 쉽습니다.

```js
catch (error) {
  showError(String(error));
}
```

네트워크 계층에서 오류를 구분 가능한 형태로 정리할 수 있습니다.

예를 들어:

```js
class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "HttpError";
    this.status = status;
  }
}
```

필요하면 데이터 검증 오류도 별도 타입으로 만들 수 있습니다.

```js
class ResponseValidationError
  extends Error {
  constructor(message) {
    super(message);
    this.name =
      "ResponseValidationError";
  }
}
```

화면에서는 내부 오류 전체를 그대로 출력하지 않고 사용자에게 필요한 문장으로 변환합니다.

```js
function toUserMessage(error) {
  if (
    error instanceof HttpError &&
    error.status === 404
  ) {
    return "요청한 정보를 찾을 수 없습니다.";
  }

  if (
    error instanceof HttpError &&
    error.status >= 500
  ) {
    return "서버에서 요청을 처리하지 못했습니다.";
  }

  if (
    error instanceof ResponseValidationError
  ) {
    return "서버 응답 형식을 확인할 수 없습니다.";
  }

  return "요청을 완료하지 못했습니다.";
}
```

## 내부 오류를 그대로 사용자에게 노출하지 않습니다

다음과 같은 내부 정보는 사용자용 오류 문장에 그대로 포함하지 않습니다.

- 스택 트레이스
- SQL 오류
- 서버 파일 경로
- 내부 서비스 주소
- 액세스 토큰
- 개인정보
- 디버깅용 상세 객체

사용자 메시지와 개발자 진단 정보는 목적이 다릅니다.

```text
사용자
→ 무엇이 실패했는지
→ 다시 시도할 수 있는지
→ 다음 행동이 무엇인지

개발자 로그
→ 원인 조사에 필요한 상세 정보
```

서버가 요청 ID나 trace ID를 제공한다면 사용자에게 문의용 식별자만 보여 주고 상세 내부 로그는 서버에서 확인하는 방식도 사용할 수 있습니다.

## 오류를 지나치게 일찍 문자열로 바꾸지 않습니다

다음 코드는 HTTP 상태 같은 구조 정보를 잃습니다.

```js
catch (error) {
  throw new Error(String(error));
}
```

가능하면 애플리케이션 내부에서는 구조화된 오류 정보를 유지하고 사용자에게 보여 주는 경계에서 문자열로 변환합니다.

```text
네트워크 계층
→ HttpError(status, ...)

도메인/서비스 계층
→ 필요한 맥락 추가

UI 계층
→ 사용자 문장으로 변환
```

그러면 화면에 따라 `404`, 인증 실패, 서버 오류 등을 다르게 처리할 수 있습니다.

## 로딩 상태 정리도 경쟁 상태를 고려합니다

다음 코드는 두 요청이 겹치면 문제가 될 수 있습니다.

```js
let loading = false;

async function search(query) {
  loading = true;

  try {
    await searchUsers(query);
  } finally {
    loading = false;
  }
}
```

요청 A가 시작된 뒤 B가 시작되고 A가 먼저 끝나면:

```text
A 시작 → loading = true
B 시작 → loading = true
A 완료 → loading = false
B는 아직 실행 중
```

화면은 B가 진행 중인데도 로딩이 끝난 것처럼 보입니다.

따라서 최신 요청 하나만 의미가 있는 검색이라면 요청 버전을 함께 검사합니다.

```js
let version = 0;

async function search(query) {
  const current =
    ++version;

  setLoading(true);

  try {
    const users =
      await searchUsers(query);

    if (current !== version) {
      return;
    }

    render(users);
  } finally {
    if (current === version) {
      setLoading(false);
    }
  }
}
```

정리 코드도 현재 작업인지 확인해야 한다는 좋은 예입니다.

## 타이머를 정리합니다

컴포넌트나 화면에서 타이머를 만들었다면 더 이상 필요하지 않을 때 제거합니다.

```js
const timer = setTimeout(() => {
  refresh();
}, 5_000);
```

필요 없어졌다면:

```js
clearTimeout(timer);
```

반복 타이머도 마찬가지입니다.

```js
const interval = setInterval(() => {
  refresh();
}, 30_000);
```

정리:

```js
clearInterval(interval);
```

화면이 제거된 뒤에도 타이머가 계속 실행되면 다음 문제가 생길 수 있습니다.

- 필요 없는 네트워크 요청
- 이미 사라진 DOM 접근
- 중복 작업
- 메모리와 자원 낭비

## 이벤트 리스너도 정리할 수 있어야 합니다

다음 리스너를 등록했다면:

```js
window.addEventListener(
  "resize",
  handleResize
);
```

해당 화면의 수명이 끝났을 때 더 이상 필요하지 않을 수 있습니다.

```js
window.removeEventListener(
  "resize",
  handleResize
);
```

제거하려면 등록할 때 사용한 함수 참조가 필요합니다.

따라서 다음처럼 익명 함수를 즉석에서 만들면 나중에 같은 함수 참조를 얻기 어렵습니다.

```js
window.addEventListener(
  "resize",
  () => render()
);
```

정리가 필요하다면 이름 있는 함수나 보관한 함수 참조를 사용합니다.

```js
function handleResize() {
  render();
}

window.addEventListener(
  "resize",
  handleResize
);

// 정리 시점
window.removeEventListener(
  "resize",
  handleResize
);
```

## 전체 검색 예제

다음 예제는 상태 구분, 요청 취소, 오래된 결과 방지, HTTP 오류 처리의 핵심을 함께 보여 줍니다.

```js
class HttpError extends Error {
  constructor(status, message) {
    super(message ?? `HTTP ${status}`);
    this.name = "HttpError";
    this.status = status;
  }
}

function isAbortError(error) {
  return (
    error instanceof DOMException &&
    error.name === "AbortError"
  );
}

async function readErrorMessage(
  response
) {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    const value = JSON.parse(text);

    if (
      typeof value === "object" &&
      value !== null &&
      typeof value.message === "string"
    ) {
      return value.message;
    }
  } catch {
    // JSON이 아니면 아래에서 일반 텍스트 사용
  }

  return text.slice(0, 500);
}

async function searchUsers(
  query,
  signal
) {
  const url = new URL(
    "/api/users",
    location.origin
  );

  url.searchParams.set("q", query);

  const response = await fetch(url, {
    signal,
  });

  if (!response.ok) {
    throw new HttpError(
      response.status,
      await readErrorMessage(response)
    );
  }

  const value = await response.json();

  if (!Array.isArray(value)) {
    throw new Error(
      "사용자 목록 형식이 올바르지 않습니다."
    );
  }

  return value;
}

let requestVersion = 0;
let activeController = null;

let state = {
  status: "idle",
};

async function search(query) {
  const version =
    ++requestVersion;

  activeController?.abort();

  const controller =
    new AbortController();

  activeController = controller;

  state = {
    status: "loading",
  };
  render(state);

  try {
    const users =
      await searchUsers(
        query,
        controller.signal
      );

    if (version !== requestVersion) {
      return;
    }

    state =
      users.length === 0
        ? {
            status: "empty",
          }
        : {
            status: "ready",
            data: users,
          };

    render(state);
  } catch (error) {
    if (isAbortError(error)) {
      return;
    }

    if (version !== requestVersion) {
      return;
    }

    state = {
      status: "error",
      message: toUserMessage(error),
    };

    render(state);
  } finally {
    if (
      version === requestVersion &&
      activeController === controller
    ) {
      activeController = null;
    }
  }
}
```

이 예제의 흐름은 다음과 같습니다.

```text
검색 시작
  ↓
이전 요청 취소
  ↓
새 requestVersion 발급
  ↓
loading 렌더링
  ↓
fetch
  │
  ├─ 취소 → 조용히 종료
  ├─ 네트워크 실패 → error
  ├─ HTTP 오류 → HttpError → error
  ├─ 응답 형식 오류 → error
  └─ 성공
       ↓
  아직 최신 요청인가?
       │
       ├─ 아니오 → 무시
       └─ 예
            ↓
       empty / ready 렌더링
```

## 비동기 코드 디버깅 순서

비동기 문제가 발생하면 다음 순서로 확인하면 원인을 좁히기 쉽습니다.

```text
1. 작업은 실제로 시작되었는가?
2. 반환된 Promise를 누가 기다리거나 catch하는가?
3. fetch 자체가 실패했는가, Response를 받았는가?
4. HTTP status와 response.ok는 무엇인가?
5. Content-Type과 실제 본문은 무엇인가?
6. 본문 파싱은 성공했는가?
7. 파싱한 데이터 구조는 올바른가?
8. 작업이 끝났을 때도 결과가 여전히 필요한가?
9. 더 최신 요청이 이미 시작되지 않았는가?
10. finally의 정리 코드가 최신 상태를 덮고 있지 않은가?
```

검색 경쟁 상태라면 다음처럼 로그를 임시로 남길 수 있습니다.

```js
console.log(
  "start",
  version,
  query
);

const result =
  await searchUsers(query);

console.log(
  "finish",
  version,
  query
);
```

완료 순서가 시작 순서와 다르다는 사실을 직접 확인할 수 있습니다.

## 네트워크 요청 디버깅은 Network 탭과 함께 합니다

JavaScript 오류 메시지만 보지 말고 브라우저 개발자 도구의 Network 탭에서 다음을 확인합니다.

- 요청이 실제로 전송되었는가?
- 요청 URL과 메서드는 무엇인가?
- 요청이 취소되었는가?
- HTTP 상태 코드는 무엇인가?
- 응답 `Content-Type`은 무엇인가?
- 실제 응답 본문은 무엇인가?
- 얼마나 오래 걸렸는가?

예를 들어 다음 오류만 보면:

```text
Unexpected token '<'
```

JSON 파싱 코드 문제처럼 보일 수 있습니다.

하지만 실제 응답이 HTML 오류 페이지일 수 있습니다.

```html
<!doctype html>
<h1>502 Bad Gateway</h1>
```

따라서 비동기 요청 디버깅은 코드와 실제 네트워크 응답을 함께 봅니다.

## 흔한 실수

- `async` 함수가 일반 값을 직접 반환한다고 생각합니다.
- `await`가 브라우저 전체 JavaScript 실행을 멈춘다고 생각합니다.
- Promise를 호출만 하고 성공과 실패를 누가 처리하는지 정하지 않습니다.
- `void promise`가 실패까지 처리해 준다고 생각합니다.
- `fetch()`가 `404`나 `500`에서 자동으로 Promise를 거부한다고 생각합니다.
- `response.ok`만 확인하면 응답 JSON 구조까지 안전하다고 생각합니다.
- 응답이 항상 JSON이라고 가정하고 HTML 오류 페이지도 바로 `response.json()`으로 읽습니다.
- 같은 `Response` 본문을 여러 번 읽으려고 합니다.
- 대기 상태와 정상적인 빈 결과를 같은 빈 배열로 표현합니다.
- 여러 불리언으로 상태를 표현해 동시에 `loading`과 `error`가 되는 조합을 만듭니다.
- 이전 검색 요청을 취소하지 않고 결과가 현재 요청인지도 확인하지 않습니다.
- 취소만 하면 오래된 결과 적용 문제가 항상 완전히 해결된다고 생각합니다.
- 모든 오류를 `AbortError`처럼 무시합니다.
- 타임아웃과 사용자 취소를 같은 의미로 처리합니다.
- 오래된 요청의 `finally`가 최신 요청의 로딩 상태나 컨트롤러를 지우게 둡니다.
- 서로 의존하는 요청을 무조건 `Promise.all()`로 동시에 실행합니다.
- `Promise.all()`에서 하나가 실패하면 다른 작업도 자동으로 취소된다고 생각합니다.
- 타이머와 이벤트 리스너를 더 이상 필요 없는데도 정리하지 않습니다.
- 타임아웃이 발생하면 서버에서 변경 작업도 반드시 실패했다고 생각합니다.
- 타임아웃 뒤 변경 요청을 중복 방지 없이 자동 재시도합니다.
- 내부 스택, SQL 오류, 개인정보 같은 진단 정보를 그대로 사용자에게 표시합니다.
- 오류를 너무 일찍 문자열 하나로 바꿔 HTTP 상태 같은 구조 정보를 잃습니다.

## 관련 exercise

[`runtime-workspace`](../../exercises/runtime-workspace/README.md)는 태스크와 마이크로태스크의 실행 순서를 보여 줍니다. [`user-directory`](../../exercises/user-directory/README.md)는 검색 요청의 완료 순서가 뒤바뀌는 상황을 검증합니다.

## 완료 기준

다음 내용을 설명하거나 직접 구현할 수 있으면 이 문서의 목표를 달성한 것입니다.

- Promise의 `pending`, `fulfilled`, `rejected` 상태를 설명할 수 있습니다.
- `async` 함수가 항상 Promise를 반환한다는 점을 설명할 수 있습니다.
- `async` 함수 안의 `throw`가 호출자의 `await`에서 어떻게 전달되는지 설명할 수 있습니다.
- 기다리지 않는 Promise의 실패를 누가 처리하는지 명시할 수 있습니다.
- 동기 코드, 마이크로태스크, 다음 태스크의 기본 실행 순서를 설명할 수 있습니다.
- 비동기 작업이 기다리는 동안 애플리케이션 상태가 바뀔 수 있음을 설명할 수 있습니다.
- 네트워크 실패와 `404`, `500` 같은 HTTP 오류 응답을 구분할 수 있습니다.
- `response.ok`, `Content-Type`, 본문 파싱, 데이터 구조 검증을 서로 다른 단계로 볼 수 있습니다.
- 대기, 빈 결과, 성공, 오류를 별도 상태로 표현할 수 있습니다.
- 필요 없어진 `fetch()` 요청을 `AbortController`로 취소할 수 있습니다.
- 의도적인 취소만 별도로 처리하고 다른 오류는 숨기지 않을 수 있습니다.
- 요청 버전이나 동등한 식별자를 사용해 이전 요청의 늦은 결과를 무시할 수 있습니다.
- 취소와 버전 검사의 목적 차이를 설명할 수 있습니다.
- 오래된 요청의 `finally`가 최신 화면 상태를 덮지 않게 할 수 있습니다.
- 타임아웃이 서버 작업 실패를 보장하지 않는 이유를 설명할 수 있습니다.
- 데이터를 변경하는 요청의 자동 재시도에서 중복 실행 가능성을 설명할 수 있습니다.
- 서로 독립적인 요청만 `Promise.all()`로 병렬화할 수 있습니다.
- `Promise.all()`에서 한 작업이 실패해도 다른 작업이 자동 취소되지 않는다는 점을 설명할 수 있습니다.
- 타이머와 이벤트 리스너처럼 직접 만든 자원을 적절한 시점에 정리할 수 있습니다.
