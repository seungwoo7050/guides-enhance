# 비동기 작업과 `fetch`

비동기 코드에서 중요한 것은 `await` 문법이 아니라 작업이 언제 시작되고 끝나는지, 실패와 취소를 누가 처리하는지, 늦게 도착한 결과를 아직 적용해도 되는지 판단하는 일입니다.

## 목표

- Promise와 `async` 함수의 결과 전달 방식을 이해합니다.
- 네트워크 오류와 HTTP 오류 응답을 구분합니다.
- 대기, 빈 결과, 성공, 오류를 다른 상태로 표현합니다.
- 필요 없어진 요청을 취소합니다.
- 이전 요청의 늦은 응답이 최신 화면을 덮지 않게 합니다.
- 타임아웃과 자원 정리를 명시합니다.

## Promise와 오류 전달

```js
async function loadBoard(id) {
  const response = await fetch(`/api/boards/${id}`);
  return response.json();
}
```

`async` 함수는 Promise를 반환합니다. 호출자가 `await`하거나 Promise를 반환하지 않으면 실패를 놓칠 수 있습니다.

```js
async function unsafe() {
  saveBoard(); // 완료와 실패를 확인하지 않습니다.
}
```

의도적으로 기다리지 않는 작업이라면 실패를 기록할 위치와 프로그램 종료 시 처리 방법을 따로 정합니다. `void saveBoard()`는 경고만 없앨 뿐 실패를 처리하지 않습니다.

## 이벤트 루프의 최소 모델

```js
console.log("sync");
queueMicrotask(() => console.log("microtask"));
setTimeout(() => console.log("task"), 0);
```

출력은 `sync`, `microtask`, `task` 순서입니다. 콜백이 실행될 때는 현재 함수가 끝난 뒤이므로 그사이에 상태가 달라질 수 있습니다.

## `fetch`와 HTTP 상태 코드

```js
async function requestJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new HttpError(response.status, await readSafeError(response));
  }
  return response.json();
}
```

서버가 404나 500을 반환해도 `fetch()`는 `Response`를 정상적으로 돌려줍니다. 연결 실패, DNS 오류, 요청 취소처럼 응답을 받지 못한 경우에 Promise가 주로 거부됩니다.

응답이 항상 JSON이라고 가정하지 않습니다. `Content-Type`과 실제 본문을 확인하고, 프록시가 HTML 오류 페이지를 반환한 경우도 처리합니다.

## 화면 상태

```ts
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "empty" }
  | { status: "ready"; data: T }
  | { status: "error"; message: string };
```

빈 배열 하나로 “아직 불러오지 않음”과 “정상적으로 불러왔지만 결과가 없음”을 함께 표현하지 않습니다. 여러 불리언 값으로 표현하면 `loading`과 `error`가 동시에 참인 상태를 만들기 쉽습니다.

## 요청 취소

```js
const controller = new AbortController();
fetch(url, { signal: controller.signal });
controller.abort();
```

검색어가 바뀌거나 페이지를 떠나 결과가 필요 없어지면 요청을 취소합니다.

```js
try {
  await fetch(url, { signal });
} catch (error) {
  if (error instanceof DOMException && error.name === "AbortError") return;
  throw error;
}
```

취소는 사용자에게 실패 알림을 보여 줄 필요가 없는 경우가 많습니다. 그렇다고 다른 오류까지 모두 무시하지 않습니다.

## 늦은 응답 방지

취소를 지원하지 않는 작업이 있거나 취소 직전에 응답이 끝날 수 있습니다. 결과를 적용하기 전에 현재 요청인지 확인할 수 있습니다.

```js
let requestVersion = 0;

async function search(query) {
  const version = ++requestVersion;
  const result = await searchUsers(query);
  if (version !== requestVersion) return;
  render(result);
}
```

`AbortController`는 불필요한 작업을 중단하고, 버전 검사는 오래된 결과가 적용되는 일을 막습니다. 함께 사용할 수 있습니다.

## 타임아웃

```js
const response = await fetch(url, {
  signal: AbortSignal.timeout(5_000)
});
```

타임아웃은 서버가 작업을 수행하지 않았다는 뜻이 아닙니다. 서버는 처리했지만 응답만 잃었을 수 있습니다. 데이터를 바꾸는 요청을 재시도하려면 중복 실행을 막을 방법이 필요합니다.

직접 타이머를 만들었다면 `finally`에서 해제합니다.

## 병렬 작업

서로 의존하지 않는 요청만 동시에 시작합니다.

```js
const [profile, boards] = await Promise.all([
  loadProfile(),
  loadBoards()
]);
```

하나가 실패해도 이미 시작한 다른 작업은 자동으로 취소되지 않습니다. 공유 `AbortSignal`이나 별도의 정리 코드를 준비합니다.

## 오류 문장 만들기

네트워크 오류, HTTP 오류, 응답 검증 실패를 모든 화면에서 제각각 문자열로 바꾸지 않습니다. 요청 함수에서 애플리케이션이 구분할 수 있는 오류로 바꾸고, 화면에서는 사용자에게 필요한 문장만 표시합니다. 내부 스택, SQL 오류, 개인정보는 노출하지 않습니다.

## 흔한 실수

- `fetch()`가 404에서 Promise를 거부한다고 생각합니다.
- 대기 상태를 빈 배열로 표현합니다.
- 이전 요청을 취소하지 않고 결과가 현재 요청인지도 확인하지 않습니다.
- 모든 오류를 `AbortError`처럼 무시합니다.
- 타이머와 이벤트 리스너를 정리하지 않습니다.
- 타임아웃 뒤 변경 요청을 중복 방지 없이 자동 재시도합니다.

## 관련 exercise

[`runtime-workspace`](../../exercises/runtime-workspace/README.md)는 태스크와 마이크로태스크의 실행 순서를 보여 줍니다. [`user-directory`](../../exercises/user-directory/README.md)는 검색 요청의 완료 순서가 뒤바뀌는 상황을 검증합니다.

## 완료 기준

- Promise 실패가 호출자에게 전달되는 과정을 설명할 수 있습니다.
- 네트워크 오류와 HTTP 오류 응답을 구분합니다.
- 대기, 빈 결과, 성공, 오류를 별도 상태로 표현합니다.
- 필요 없어진 요청을 취소하고 취소 오류만 따로 처리합니다.
- 이전 요청이 늦게 끝나도 최신 화면이 유지됩니다.
