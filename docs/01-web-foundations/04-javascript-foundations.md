# JavaScript 기초

웹 애플리케이션을 시작하기 위해 JavaScript 문법 전체를 외울 필요는 없습니다. 값, 조건문, 반복문, 함수, 배열, 객체, 모듈과 오류 전달을 읽고 쓸 수 있으면 실제 기능을 만들면서 나머지를 익힐 수 있습니다.

## 목표

- 값과 변수를 구분하고 조건문과 반복문을 작성합니다.
- 함수의 입력, 반환값, 외부 상태 변경을 구분합니다.
- 배열과 객체를 새 값으로 갱신합니다.
- 객체 참조 공유와 얕은 복사를 이해합니다.
- ESM으로 파일 사이의 공개 범위를 정합니다.
- 처리할 수 없는 실패를 `Error`로 전달합니다.

## 값과 변수

```js
const title = "첫 작업";
const count = 3;
const completed = false;
let selectedId = null;
```

다시 대입하지 않는 변수는 `const`로 선언합니다. `const`는 변수 재대입을 막지만 객체 내부 변경까지 막지는 않습니다.

```js
const task = { title: "읽기", completed: false };
task.completed = true;
```

객체 자체를 바꾸지 않아야 한다면 새 객체를 만듭니다.

## 입력 검사와 빠른 반환

```js
function describeCount(count) {
  if (!Number.isInteger(count) || count < 0) {
    throw new Error("count는 0 이상의 정수여야 합니다.");
  }
  if (count === 0) return "작업 없음";
  return `${count}개 작업`;
}
```

잘못된 입력을 먼저 처리하면 정상 코드의 중첩을 줄일 수 있습니다.

환경 변수와 폼 입력은 문자열로 들어옵니다. 숫자로 바꾼 뒤 허용 범위까지 확인합니다.

```js
function parseLimit(input) {
  if (typeof input !== "string" || !input.trim()) {
    throw new Error("limit이 필요합니다.");
  }
  const value = Number(input);
  if (!Number.isInteger(value) || value < 1 || value > 100) {
    throw new Error("limit은 1부터 100 사이의 정수여야 합니다.");
  }
  return value;
}
```

`Number("")`가 0이 된다는 점도 주의합니다.

## 배열 다루기

```js
const openTasks = tasks.filter((task) => !task.completed);
const titles = tasks.map((task) => task.title);
const hasDone = tasks.some((task) => task.completed);
```

- 새 배열이 필요하면 `map`, `filter`를 사용합니다.
- 하나의 결과를 계산하면 `reduce`나 명시적인 반복문을 사용합니다.
- 각 항목마다 로그 출력처럼 외부 동작을 실행하면 `forEach`를 사용할 수 있습니다.

메서드를 짧게 쓰는 것보다 코드가 실제로 무엇을 계산하는지 분명한지가 더 중요합니다.

## 함수를 작게 나누기

```js
function normalizeTitle(input) {
  return input.trim();
}

function createTask(title, createId) {
  const normalized = normalizeTitle(title);
  if (!normalized) throw new Error("제목이 필요합니다.");
  return { id: createId(), title: normalized, completed: false };
}
```

현재 시각, 무작위 ID, 파일, DOM, 네트워크처럼 외부에서 달라지는 값은 필요한 경우 매개변수로 전달합니다. 그러면 같은 입력에 대한 결과를 테스트하기 쉬워집니다.

## 객체 참조와 얕은 복사

```js
const current = { version: 1 };
const alias = current;
alias.version = 2;
console.log(current.version); // 2
```

객체를 대입하면 같은 객체를 가리키는 참조가 복사됩니다. 이전 값을 보존해야 한다면 새 객체를 만듭니다.

```js
const next = { ...current, version: current.version + 1 };
const nextTasks = tasks.map((task) =>
  task.id === targetId ? { ...task, completed: true } : task
);
```

스프레드 문법은 한 단계만 복사합니다. 중첩 객체는 여전히 이전 값과 같은 객체를 가리킬 수 있습니다.

## `null`, `undefined`, 참·거짓

`undefined`는 값이 제공되지 않았을 때 자주 나타납니다. `null`은 애플리케이션이 값의 부재를 명시할 때 사용할 수 있습니다. 둘을 어떻게 구분할지는 코드에서 일관되게 정합니다.

빈 문자열, 0, `false`, `null`, `undefined`, `NaN`은 조건식에서 거짓입니다. 문자열 `"false"`는 참입니다. 환경 변수 문자열을 단순한 `Boolean()` 호출로 해석하지 않습니다.

## 모듈

```js
// tasks.js
export function addTask(tasks, task) {
  return [...tasks, task];
}
```

```js
// app.js
import { addTask } from "./tasks.js";
```

공유 모듈을 가져오는 것만으로 서버를 시작하거나 타이머를 등록하지 않습니다. 실행 파일에서 필요한 모듈을 가져와 실제 동작을 시작합니다.

## 오류 전달

```js
try {
  createTask("", crypto.randomUUID);
} catch (error) {
  const message = error instanceof Error ? error.message : "알 수 없는 오류";
  console.error(message);
}
```

현재 위치에서 복구할 수 없는 오류를 무시하고 성공한 것처럼 계속 실행하지 않습니다. 추가 설명이 필요하면 원인을 보존합니다.

```js
throw new Error("작업을 저장하지 못했습니다.", { cause: error });
```

## 흔한 실수

- 모든 입력을 올바른 문자열이나 숫자라고 가정합니다.
- 배열과 객체를 직접 변경하면서 이전 값도 보존된다고 생각합니다.
- 한 함수에서 입력 검사, DOM 변경, 저장, 네트워크 요청을 모두 처리합니다.
- `==`의 암시적 형 변환에 의존합니다.
- `catch`에서 오류를 무시하고 성공 화면을 표시합니다.

## 완료 기준

- 조건문, 반복문, 함수로 작은 계산을 작성할 수 있습니다.
- 배열과 객체를 새 값으로 갱신할 수 있습니다.
- 객체 참조 공유와 얕은 복사를 설명할 수 있습니다.
- 문자열 입력을 숫자로 바꾼 뒤 범위를 검사합니다.
- 계산 코드와 DOM·파일·네트워크를 바꾸는 코드를 분리합니다.

## 다음 문서

브라우저 상태가 필요하면 [`DOM, 이벤트, URL과 저장소`](05-dom-events-url-storage.md)를 읽습니다. Core 학습은 [`비동기 작업과 fetch`](06-async-fetch-errors.md)로 이어집니다.
