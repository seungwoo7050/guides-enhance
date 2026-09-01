# JavaScript 기초

웹 애플리케이션을 시작하기 위해 JavaScript 문법 전체를 먼저 외울 필요는 없습니다. 실제 기능을 만들 때 자주 사용하는 핵심은 값과 변수, 조건문과 반복문, 함수, 배열과 객체, 모듈, 오류 전달입니다.

이 문서에서는 문법을 나열하기보다 다음 질문에 답할 수 있도록 정리합니다.

- 어떤 값을 변수에 저장하고 다시 바꿀 수 있는가?
- 함수는 어떤 값을 입력받고 무엇을 반환하는가?
- 배열과 객체를 바꿀 때 이전 값은 보존되는가?
- 외부 상태를 읽거나 바꾸는 코드를 어떻게 분리할 수 있는가?
- 파일 사이에서 어떤 기능을 공개하고 가져오는가?
- 현재 함수가 처리할 수 없는 실패를 어떻게 상위 코드로 전달하는가?

## 목표

- 값과 변수를 구분하고 조건문과 반복문을 작성합니다.
- `const`와 `let`의 차이를 설명합니다.
- 함수의 입력, 반환값, 외부 상태 변경을 구분합니다.
- 문자열 입력을 필요한 타입으로 변환한 뒤 유효성을 검사합니다.
- 배열의 `map`, `filter`, `some`, `forEach`, `reduce`를 목적에 맞게 사용합니다.
- 배열과 객체를 새 값으로 갱신합니다.
- 객체 참조 공유와 얕은 복사를 이해합니다.
- `null`, `undefined`, truthy/falsy 값을 구분합니다.
- ESM으로 파일 사이의 공개 범위를 정합니다.
- 처리할 수 없는 실패를 `Error`로 전달합니다.

## 값과 변수

JavaScript 프로그램은 문자열, 숫자, 불리언, 객체 같은 **값(value)** 을 다룹니다.

```js
"첫 작업"
3
false
null
```

변수(variable)는 이런 값을 이름으로 가리키기 위한 바인딩입니다.

```js
const title = "첫 작업";
const count = 3;
const completed = false;
let selectedId = null;
```

여기서 `title`, `count`, `completed`, `selectedId`가 변수 이름이고, 오른쪽이 변수에 저장된 값입니다.

### `const`와 `let`

다시 대입하지 않는 변수는 기본적으로 `const`로 선언합니다.

```js
const title = "첫 작업";
```

다음과 같이 같은 변수에 다른 값을 다시 넣을 수 없습니다.

```js
const title = "첫 작업";
title = "두 번째 작업"; // TypeError
```

반대로 값이 바뀌어야 한다면 `let`을 사용합니다.

```js
let selectedId = null;
selectedId = "task-1";
```

`const`를 기본으로 사용하면 "이 변수 이름이 나중에 다른 값을 가리키는가?"를 코드만 보고 판단하기 쉬워집니다.

### `const`는 객체 자체를 불변으로 만들지 않습니다

다음 코드는 허용됩니다.

```js
const task = {
  title: "읽기",
  completed: false,
};

task.completed = true;
```

`const`가 막는 것은 `task`라는 변수에 **다른 값을 다시 대입하는 것**입니다.

```js
task = {
  title: "쓰기",
  completed: false,
}; // TypeError
```

하지만 `task`가 가리키는 객체 내부의 속성 변경까지 막는 것은 아닙니다.

따라서 다음 두 문장을 구분해야 합니다.

```text
const → 변수 재대입을 막음
불변성 → 객체 내부 값까지 바꾸지 않는 설계
```

객체의 이전 상태를 보존해야 한다면 기존 객체를 직접 수정하는 대신 새 객체를 만듭니다.

```js
const nextTask = {
  ...task,
  completed: true,
};
```

## 기본 타입과 `typeof`

JavaScript에서 자주 접하는 값은 다음과 같습니다.

```js
const title = "읽기";       // string
const count = 3;            // number
const completed = false;    // boolean
const task = { id: "1" };   // object
const tasks = [];           // object
const missing = undefined;  // undefined
const empty = null;         // object로 표시되는 역사적 특이점
```

`typeof`를 사용하면 값의 기본 타입을 확인할 수 있습니다.

```js
typeof "읽기";      // "string"
typeof 3;           // "number"
typeof false;       // "boolean"
typeof undefined;   // "undefined"
typeof {};          // "object"
```

주의할 점은 다음입니다.

```js
typeof null; // "object"
```

`null`이 실제로 일반 객체라는 뜻은 아닙니다. JavaScript에 오래전부터 존재하는 동작이므로 `null` 여부는 보통 직접 비교합니다.

```js
value === null
```

배열도 `typeof` 결과는 `"object"`이므로 배열인지 확인할 때는 다음을 사용합니다.

```js
Array.isArray(value)
```

## 엄격한 비교를 사용합니다

JavaScript의 `==`는 비교 전에 암시적 형 변환을 수행할 수 있습니다.

```js
0 == false;   // true
"" == false;  // true
```

이런 규칙을 모두 기억하면서 코드를 읽기보다 일반적으로 엄격한 비교 연산자를 사용합니다.

```js
0 === false;   // false
"" === false;  // false
```

같지 않음을 비교할 때도 `!==`를 사용합니다.

```js
value !== null
```

암시적 형 변환이 필요한 특별한 이유가 없다면 `===`, `!==`를 기본으로 사용하면 의도를 읽기 쉽습니다.

## 조건문

조건문은 조건에 따라 다른 코드를 실행합니다.

```js
function describeCount(count) {
  if (count === 0) {
    return "작업 없음";
  }

  return `${count}개 작업`;
}
```

조건이 여러 개라면 다음처럼 작성할 수 있습니다.

```js
function getStatusLabel(task) {
  if (task.completed) {
    return "완료";
  }

  if (task.blocked) {
    return "차단됨";
  }

  return "진행 중";
}
```

조건문을 작성할 때는 어떤 값이 참 또는 거짓으로 평가되는지 알고 있어야 합니다. 이 내용은 뒤의 `null`, `undefined`, 참·거짓 절에서 다룹니다.

## 입력 검사와 빠른 반환

함수의 입력이 항상 올바르다고 가정하면 잘못된 값이 깊은 곳까지 전달되어 원인을 찾기 어려워질 수 있습니다.

```js
function describeCount(count) {
  if (!Number.isInteger(count) || count < 0) {
    throw new Error("count는 0 이상의 정수여야 합니다.");
  }

  if (count === 0) {
    return "작업 없음";
  }

  return `${count}개 작업`;
}
```

잘못된 입력을 먼저 검사하고 함수 실행을 끝내는 방식을 **빠른 반환(early return)** 또는 빠른 실패(fail fast) 패턴으로 볼 수 있습니다.

다음처럼 정상 코드 전체를 깊게 중첩하는 것보다

```js
function describeCount(count) {
  if (Number.isInteger(count) && count >= 0) {
    if (count === 0) {
      return "작업 없음";
    } else {
      return `${count}개 작업`;
    }
  } else {
    throw new Error("잘못된 count입니다.");
  }
}
```

잘못된 경우를 먼저 끝내면 정상 흐름을 읽기 쉽습니다.

```js
function describeCount(count) {
  if (!Number.isInteger(count) || count < 0) {
    throw new Error("count는 0 이상의 정수여야 합니다.");
  }

  if (count === 0) {
    return "작업 없음";
  }

  return `${count}개 작업`;
}
```

## 문자열 입력은 변환과 검증을 나눠 생각합니다

폼 입력과 환경 변수는 자주 문자열로 들어옵니다.

예를 들어 HTML 입력의 값은 일반적으로 문자열입니다.

```js
const input = document.querySelector("input");
console.log(typeof input.value); // "string"
```

환경 변수도 보통 문자열입니다.

따라서 숫자가 필요한 코드에서는 다음 두 단계를 구분합니다.

```text
문자열 → 숫자로 변환 → 허용되는 숫자인지 검증
```

예를 들어 페이지 크기를 읽는 함수는 다음처럼 작성할 수 있습니다.

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

여기서는 세 가지를 확인합니다.

```text
1. 문자열이 실제로 제공되었는가?
2. 숫자로 변환할 수 있는가?
3. 변환된 숫자가 허용 범위에 있는가?
```

### `Number("")`에 주의합니다

다음 결과는 처음 보면 예상과 다를 수 있습니다.

```js
Number("");     // 0
Number("   ");  // 0
```

따라서 빈 입력을 허용하지 않는다면 숫자로 바꾸기 전에 먼저 검사해야 합니다.

```js
if (!input.trim()) {
  throw new Error("값이 필요합니다.");
}
```

### `Number.isNaN()`과 `Number.isInteger()`

숫자로 변환할 수 없는 문자열은 `NaN`이 됩니다.

```js
Number("abc"); // NaN
```

정수인지 확인해야 한다면 다음 검사가 편리합니다.

```js
Number.isInteger(value)
```

예를 들어:

```js
Number.isInteger(3);    // true
Number.isInteger(3.5);  // false
Number.isInteger(NaN);  // false
```

값이 정수여야 하는 입력이라면 별도로 `NaN` 검사를 하지 않아도 이 조건에서 함께 걸러집니다.

## 반복문

배열 메서드만 사용해야 하는 것은 아닙니다. 명시적인 반복문이 더 읽기 쉬운 경우도 있습니다.

```js
let total = 0;

for (const task of tasks) {
  if (task.completed) {
    total += 1;
  }
}
```

`for...of`는 배열 같은 iterable의 값을 순서대로 읽을 때 자주 사용합니다.

중요한 것은 가장 짧은 문법이 아니라 **무엇을 계산하거나 실행하는지 분명한 코드**입니다.

## 배열 다루기

배열은 같은 종류의 여러 값을 순서대로 다룰 때 자주 사용합니다.

```js
const tasks = [
  { id: "1", title: "읽기", completed: false },
  { id: "2", title: "쓰기", completed: true },
];
```

배열을 다룰 때 자주 사용하는 메서드는 목적이 서로 다릅니다.

## `filter`: 조건에 맞는 항목만 남깁니다

```js
const openTasks = tasks.filter((task) => !task.completed);
```

`filter`는 각 항목에 조건 함수를 적용하고 결과가 참인 항목만 모아 **새 배열**을 반환합니다.

```text
원본 tasks
  ↓ filter
조건에 맞는 항목만 포함한 새 배열
```

원래 배열 자체를 제거하거나 수정하지 않습니다.

## `map`: 각 항목을 다른 값으로 바꿉니다

```js
const titles = tasks.map((task) => task.title);
```

결과는 다음과 비슷합니다.

```js
["읽기", "쓰기"]
```

`map`은 원본 배열의 각 항목을 하나씩 변환하여 같은 개수의 새 배열을 만듭니다.

객체 하나를 갱신할 때도 사용할 수 있습니다.

```js
const nextTasks = tasks.map((task) =>
  task.id === targetId
    ? { ...task, completed: true }
    : task
);
```

여기서는 대상 작업만 새 객체로 만들고 나머지는 기존 객체를 그대로 사용합니다.

## `some`: 하나라도 조건을 만족하는지 확인합니다

```js
const hasDone = tasks.some((task) => task.completed);
```

하나라도 `completed === true`인 항목이 있으면 결과는 `true`입니다.

```text
배열 → 조건을 만족하는 항목이 하나라도 있는가? → boolean
```

비슷하게 모든 항목이 조건을 만족하는지 확인할 때는 `every`가 있습니다.

```js
const allDone = tasks.every((task) => task.completed);
```

## `forEach`: 각 항목마다 동작을 실행합니다

```js
tasks.forEach((task) => {
  console.log(task.title);
});
```

`forEach`는 새 배열을 만들기 위한 메서드가 아닙니다. 각 항목마다 로그 출력, DOM 변경 같은 외부 동작을 실행할 때 사용할 수 있습니다.

다음처럼 `forEach`의 반환값을 결과 배열로 기대하면 안 됩니다.

```js
const result = tasks.forEach((task) => task.title);
console.log(result); // undefined
```

새 배열이 필요하면 `map`을 사용합니다.

## `reduce`: 여러 값을 하나의 결과로 누적합니다

예를 들어 완료된 작업 개수를 계산할 수 있습니다.

```js
const completedCount = tasks.reduce(
  (count, task) => task.completed ? count + 1 : count,
  0
);
```

`reduce`는 강력하지만 항상 가장 읽기 쉬운 것은 아닙니다.

같은 계산이 명시적인 반복문으로 더 분명하다면 다음처럼 작성해도 됩니다.

```js
let completedCount = 0;

for (const task of tasks) {
  if (task.completed) {
    completedCount += 1;
  }
}
```

메서드를 짧게 쓰는 것보다 코드가 실제로 무엇을 계산하는지 분명한지가 더 중요합니다.

## 함수를 작게 나누기

함수는 입력을 받아 어떤 결과를 계산하거나 어떤 동작을 수행하는 코드 묶음입니다.

```js
function normalizeTitle(input) {
  return input.trim();
}
```

여기서는

```text
입력  → input
출력  → trim된 문자열
외부 상태 변경 → 없음
```

입니다.

반면 다음 함수는 새 작업 객체를 만듭니다.

```js
function createTask(title, createId) {
  const normalized = normalizeTitle(title);

  if (!normalized) {
    throw new Error("제목이 필요합니다.");
  }

  return {
    id: createId(),
    title: normalized,
    completed: false,
  };
}
```

`createId`를 매개변수로 받는 이유가 중요합니다.

ID 생성이 함수 내부에 직접 고정되어 있다면 테스트할 때 결과가 매번 달라질 수 있습니다.

```js
function createTask(title) {
  return {
    id: crypto.randomUUID(),
    title,
  };
}
```

반면 외부에서 생성 함수를 전달하면 테스트에서 고정된 값을 사용할 수 있습니다.

```js
const task = createTask(
  "읽기",
  () => "test-id"
);

console.log(task.id); // "test-id"
```

이처럼 현재 시각, 무작위 값, 파일, DOM, 네트워크 같은 **외부 환경에 따라 달라지는 값이나 동작**을 필요에 따라 매개변수로 넘기면 계산 로직을 더 쉽게 테스트할 수 있습니다.

## 계산 코드와 외부 동작을 구분합니다

다음 함수는 입력만으로 결과를 계산합니다.

```js
function normalizeTitle(input) {
  return input.trim();
}
```

같은 입력에는 같은 결과를 만들고 외부 상태를 바꾸지 않습니다.

이런 함수는 테스트하기 쉽습니다.

```js
normalizeTitle("  읽기  "); // "읽기"
```

반면 다음 코드들은 외부 상태와 상호작용합니다.

```js
document.querySelector("#title").textContent = "완료";
localStorage.setItem("theme", "dark");
await fetch("/api/tasks");
console.log("saved");
```

이런 동작은 DOM, 브라우저 저장소, 네트워크, 콘솔처럼 함수 바깥의 상태를 읽거나 바꿉니다.

실제 애플리케이션에서는 계산과 외부 동작이 모두 필요합니다. 중요한 것은 한 함수 안에서 모든 책임을 섞지 않는 것입니다.

예를 들어 다음처럼 나눌 수 있습니다.

```js
function normalizeTitle(input) {
  const title = input.trim();

  if (!title) {
    throw new Error("제목이 필요합니다.");
  }

  return title;
}

async function saveTask(input) {
  const title = normalizeTitle(input);

  const response = await fetch("/api/tasks", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });

  return response;
}
```

입력 정규화와 검증은 별도의 계산 함수로 두고, 네트워크 요청은 외부 동작을 담당하는 함수에서 수행합니다.

## 객체 참조

JavaScript 객체를 변수에 대입할 때 객체 전체가 새로 복사되는 것이 아닙니다.

```js
const current = { version: 1 };
const alias = current;

alias.version = 2;

console.log(current.version); // 2
```

`current`와 `alias`가 같은 객체를 가리키기 때문입니다.

개념적으로 다음과 같습니다.

```text
current ─┐
         ├──→ { version: 1 }
alias ───┘
```

`alias.version = 2`를 실행하면 둘이 가리키는 하나의 객체가 바뀝니다.

```text
current ─┐
         ├──→ { version: 2 }
alias ───┘
```

따라서 단순 대입은 객체 복사가 아닙니다.

## 객체를 새 값으로 갱신하기

이전 객체를 보존하고 싶다면 새 객체를 만듭니다.

```js
const current = {
  version: 1,
  title: "읽기",
};

const next = {
  ...current,
  version: current.version + 1,
};
```

결과는 개념적으로 다음과 같습니다.

```text
current → { version: 1, title: "읽기" }
next    → { version: 2, title: "읽기" }
```

스프레드 문법은 기존 객체의 속성을 새 객체에 복사하고 뒤에 작성한 속성으로 같은 이름의 값을 덮어씁니다.

```js
const next = {
  ...current,
  version: 2,
};
```

## 배열을 새 값으로 갱신하기

새 항목을 추가할 때 기존 배열을 직접 수정하지 않고 새 배열을 만들 수 있습니다.

```js
const nextTasks = [
  ...tasks,
  newTask,
];
```

특정 항목만 변경할 때는 `map`을 사용할 수 있습니다.

```js
const nextTasks = tasks.map((task) =>
  task.id === targetId
    ? { ...task, completed: true }
    : task
);
```

특정 항목을 제거할 때는 `filter`가 자연스럽습니다.

```js
const nextTasks = tasks.filter(
  (task) => task.id !== targetId
);
```

이런 방식은 "변경 전 값"과 "변경 후 값"을 명확히 구분해야 하는 상태 관리 코드에서 특히 유용합니다.

## 스프레드는 얕은 복사입니다

객체 스프레드는 한 단계만 새로 복사합니다.

```js
const current = {
  title: "읽기",
  settings: {
    color: "blue",
  },
};

const next = {
  ...current,
};
```

`next` 자체는 새로운 객체지만 중첩된 `settings`는 같은 객체를 가리킵니다.

```js
console.log(next === current); // false

console.log(
  next.settings === current.settings
); // true
```

따라서 다음 코드는 두 값에 모두 영향을 줍니다.

```js
next.settings.color = "red";

console.log(current.settings.color); // "red"
```

중첩된 값도 독립적으로 바꿔야 한다면 해당 단계도 새 객체로 만들어야 합니다.

```js
const next = {
  ...current,
  settings: {
    ...current.settings,
    color: "red",
  },
};
```

이를 **얕은 복사(shallow copy)** 라고 합니다.

```text
얕은 복사
→ 최상위 객체는 새 객체
→ 중첩 객체는 필요하지 않으면 기존 참조를 그대로 공유
```

모든 중첩 객체를 무조건 깊게 복사하는 것이 목적은 아닙니다. 실제로 변경하는 경로에 필요한 새 객체를 만드는 것이 중요합니다.

## `null`과 `undefined`

둘 다 "값이 없음"을 나타내는 상황에서 볼 수 있지만 일반적으로 발생 방식이 다릅니다.

### `undefined`

값이 제공되지 않았거나 아직 정의되지 않은 경우 자주 나타납니다.

```js
const task = {};

console.log(task.title); // undefined
```

함수에 인수를 전달하지 않은 경우도 마찬가지입니다.

```js
function print(value) {
  console.log(value);
}

print(); // undefined
```

### `null`

`null`은 애플리케이션 코드가 "현재 값이 없다"는 상태를 명시적으로 표현할 때 사용할 수 있습니다.

```js
let selectedId = null;
```

예를 들어 아무 작업도 선택되지 않았다는 상태를 의도적으로 표현할 수 있습니다.

프로젝트에서 다음과 같이 규칙을 정할 수 있습니다.

```text
undefined → 값이 제공되지 않음
null      → 값이 없음을 명시적으로 표현
```

이 구분은 언어가 강제하는 규칙이 아니므로 코드베이스에서 일관되게 사용하는 것이 중요합니다.

## 참과 거짓으로 평가되는 값

JavaScript 조건식에서는 불리언이 아닌 값도 참 또는 거짓으로 평가됩니다.

다음 값들은 조건식에서 거짓(falsy)으로 평가됩니다.

```js
false
0
-0
0n
""
null
undefined
NaN
```

예를 들어

```js
if ("") {
  console.log("실행되지 않습니다.");
}
```

반면 빈 배열과 빈 객체는 참(truthy)입니다.

```js
Boolean([]); // true
Boolean({}); // true
```

문자열 `"false"`도 비어 있지 않은 문자열이므로 참입니다.

```js
Boolean("false"); // true
```

이 점은 환경 변수나 폼 문자열을 불리언으로 해석할 때 특히 중요합니다.

다음 코드는 의도와 다를 수 있습니다.

```js
const enabled = Boolean("false");

console.log(enabled); // true
```

문자열 값을 불리언 설정으로 사용할 때는 허용되는 문자열을 명시적으로 검사하는 편이 안전합니다.

```js
function parseBoolean(input) {
  if (input === "true") {
    return true;
  }

  if (input === "false") {
    return false;
  }

  throw new Error(
    '값은 "true" 또는 "false"여야 합니다.'
  );
}
```

## `||`와 `??`의 차이

기본값을 지정할 때 `||`와 `??`는 다르게 동작합니다.

```js
const count = 0;

console.log(count || 10); // 10
console.log(count ?? 10); // 0
```

`||`는 왼쪽 값이 falsy이면 오른쪽 값을 사용합니다.

따라서 `0`, `""`, `false`도 없는 값처럼 처리됩니다.

반면 `??`는 왼쪽 값이 `null` 또는 `undefined`일 때만 오른쪽 값을 사용합니다.

```js
const name = "";

console.log(name || "기본 이름"); // "기본 이름"
console.log(name ?? "기본 이름"); // ""
```

`0`, 빈 문자열, `false`가 유효한 값일 수 있다면 `??`가 의도에 더 잘 맞는 경우가 많습니다.

## 선택적 체이닝

객체의 중첩 값이 없을 수 있을 때 선택적 체이닝 `?.`을 사용할 수 있습니다.

```js
const city = user.profile?.address?.city;
```

중간 값이 `null` 또는 `undefined`이면 오류를 던지는 대신 결과가 `undefined`가 됩니다.

다음과 같은 긴 검사를 줄이는 데 유용합니다.

```js
const city =
  user.profile &&
  user.profile.address &&
  user.profile.address.city;
```

하지만 `?.`를 많이 붙여서 필수 데이터가 없어도 조용히 진행하게 만들면 오류를 숨길 수 있습니다.

값이 반드시 존재해야 하는 상황이라면 명시적으로 검사하고 실패시키는 편이 낫습니다.

## 모듈

JavaScript 파일을 역할별로 나누려면 ESM(ECMAScript Modules)을 사용할 수 있습니다.

다음 파일이 있다고 가정합니다.

```js
// tasks.js
export function addTask(tasks, task) {
  return [...tasks, task];
}
```

다른 파일에서는 필요한 이름을 가져옵니다.

```js
// app.js
import { addTask } from "./tasks.js";
```

`export`는 다른 모듈에서 사용할 수 있도록 공개하는 이름을 지정합니다.

`import`는 다른 모듈이 공개한 값을 가져옵니다.

```text
tasks.js
  export addTask
       │
       ▼
app.js
  import addTask
```

### 공개할 것만 `export`합니다

모듈 안에서만 사용하는 구현 세부사항은 굳이 공개할 필요가 없습니다.

```js
function validateTask(task) {
  if (!task.title) {
    throw new Error("제목이 필요합니다.");
  }
}

export function addTask(tasks, task) {
  validateTask(task);
  return [...tasks, task];
}
```

이 경우 외부 파일에서는 `addTask`만 사용할 수 있고 `validateTask`는 모듈 내부 구현으로 남습니다.

이렇게 하면 파일 사이의 공개 범위를 줄일 수 있습니다.

### 모듈을 가져오는 것만으로 실행을 시작하지 않습니다

공유 모듈은 가능한 한 기능을 정의하고 내보내는 역할에 집중합니다.

예를 들어 다음 모듈은 import되는 순간 서버를 시작합니다.

```js
// server.js
startServer();
```

다른 코드가 단순히 함수나 설정을 재사용하려고 이 파일을 import해도 서버가 바로 시작될 수 있습니다.

대신 다음처럼 기능 정의와 프로그램 시작을 나눌 수 있습니다.

```js
// server.js
export function createServer() {
  // 서버를 만들고 반환합니다.
}
```

```js
// main.js
import { createServer } from "./server.js";

const server = createServer();
server.listen(3000);
```

같은 원칙은 타이머 등록, 파일 쓰기, 네트워크 연결처럼 import 시점에 바로 실행되는 외부 동작에도 적용됩니다.

```text
공유 모듈
→ 기능 정의와 export

실행 진입점
→ import 후 실제 프로그램 시작
```

이렇게 나누면 테스트와 재사용이 쉬워집니다.

## 오류를 전달하는 이유

함수가 정상 결과를 만들 수 없는 상황에서는 오류를 상위 호출자에게 전달할 수 있습니다.

```js
function createTask(title, createId) {
  const normalized = title.trim();

  if (!normalized) {
    throw new Error("제목이 필요합니다.");
  }

  return {
    id: createId(),
    title: normalized,
    completed: false,
  };
}
```

`throw`가 실행되면 현재 함수의 정상 실행은 중단되고 가장 가까운 오류 처리 지점으로 전달됩니다.

```text
createTask()
   │
   └─ throw Error
          ↓
호출한 코드의 catch
```

## `try`와 `catch`

호출한 위치에서 실패를 처리할 수 있다면 `try...catch`를 사용할 수 있습니다.

```js
try {
  createTask("", crypto.randomUUID);
} catch (error) {
  const message =
    error instanceof Error
      ? error.message
      : "알 수 없는 오류";

  console.error(message);
}
```

JavaScript에서는 `throw`로 반드시 `Error` 객체만 던져야 하는 것은 아닙니다.

다음도 문법상 가능합니다.

```js
throw "실패";
```

그래서 `catch`에서 받은 값이 실제 `Error`인지 확인하는 코드가 필요할 수 있습니다.

하지만 애플리케이션 코드에서는 일반적으로 다음처럼 `Error` 객체를 던지는 편이 좋습니다.

```js
throw new Error("작업을 저장하지 못했습니다.");
```

`Error`에는 메시지와 스택 정보 같은 오류 진단 정보가 포함될 수 있기 때문입니다.

## 처리할 수 없는 오류를 삼키지 않습니다

다음 코드는 오류를 무시하고 정상처럼 계속 실행합니다.

```js
try {
  saveTask();
} catch (error) {
  // 아무것도 하지 않음
}

showSuccessMessage();
```

저장에 실패했는데도 성공 메시지가 표시될 수 있습니다.

오류를 잡는 이유는 보통 다음 중 하나가 있어야 합니다.

```text
1. 현재 위치에서 복구한다.
2. 사용자에게 실패를 알린다.
3. 로그나 추가 정보를 남긴 뒤 다시 전달한다.
```

현재 위치에서 처리할 수 없다면 억지로 성공 흐름으로 바꾸지 않습니다.

## 원인을 보존해 오류에 설명을 추가합니다

하위 작업이 실패했는데 상위 코드에서 더 구체적인 설명이 필요할 수 있습니다.

```js
try {
  await saveTaskToFile(task);
} catch (error) {
  throw new Error(
    "작업을 저장하지 못했습니다.",
    { cause: error }
  );
}
```

이렇게 하면 상위 오류 메시지에는 현재 작업의 맥락을 담으면서 원래 오류를 `cause`로 보존할 수 있습니다.

개념적으로 다음과 같습니다.

```text
파일 쓰기 실패
   ↓ cause
"작업을 저장하지 못했습니다."
```

단, `Error`의 `cause` 옵션은 실행 환경이 이를 지원하는지 확인해야 합니다.

## 함수가 실패를 표현하는 방법을 일관되게 합니다

다음 함수는 어떤 경우에는 `null`, 어떤 경우에는 `false`, 어떤 경우에는 오류를 던지면 호출자가 처리하기 어렵습니다.

```js
function findTask(id) {
  // 상황에 따라 null, false, throw...
}
```

함수의 계약을 정할 때 다음을 분명히 합니다.

```text
정상적으로 값이 없을 수 있는가?
→ null이나 undefined 같은 반환값을 사용할 수 있음

입력이나 처리 자체가 잘못되어 정상 진행할 수 없는가?
→ Error를 던지는 방식 고려
```

예를 들어 "해당 ID의 작업이 없을 수 있음"이 정상적인 조회 결과라면 다음처럼 명시할 수 있습니다.

```js
function findTask(tasks, id) {
  return tasks.find((task) => task.id === id) ?? null;
}
```

반면 `id` 자체가 비어 있는 것은 함수 계약 위반이라면 오류로 처리할 수 있습니다.

```js
function findTask(tasks, id) {
  if (!id) {
    throw new Error("id가 필요합니다.");
  }

  return tasks.find((task) => task.id === id) ?? null;
}
```

## 작은 예제로 전체 흐름 연결하기

다음 코드는 지금까지의 핵심을 함께 사용합니다.

```js
// tasks.js
export function parseTitle(input) {
  if (typeof input !== "string") {
    throw new Error("제목은 문자열이어야 합니다.");
  }

  const title = input.trim();

  if (!title) {
    throw new Error("제목이 필요합니다.");
  }

  return title;
}

export function createTask(input, createId) {
  const title = parseTitle(input);

  return {
    id: createId(),
    title,
    completed: false,
  };
}

export function completeTask(tasks, targetId) {
  return tasks.map((task) =>
    task.id === targetId
      ? { ...task, completed: true }
      : task
  );
}
```

사용하는 쪽은 다음처럼 작성할 수 있습니다.

```js
// app.js
import {
  createTask,
  completeTask,
} from "./tasks.js";

const tasks = [
  {
    id: "1",
    title: "읽기",
    completed: false,
  },
];

try {
  const task = createTask(
    "  쓰기  ",
    () => "2"
  );

  const nextTasks = [...tasks, task];
  const completedTasks =
    completeTask(nextTasks, "1");

  console.log(completedTasks);
} catch (error) {
  const message =
    error instanceof Error
      ? error.message
      : "알 수 없는 오류";

  console.error(message);
}
```

여기서 확인할 수 있는 개념은 다음과 같습니다.

- 문자열 입력을 검사하고 정규화합니다.
- ID 생성이라는 외부 변화를 함수 인수로 전달합니다.
- 기존 배열을 직접 수정하지 않고 새 배열을 만듭니다.
- 특정 객체도 스프레드로 새 객체를 만듭니다.
- 파일 사이의 공개 기능을 `export`와 `import`로 연결합니다.
- 정상 결과를 만들 수 없는 입력은 `Error`로 전달합니다.

## 흔한 실수

- `const`를 사용하면 객체 내부도 자동으로 불변이 된다고 생각합니다.
- 모든 입력이 이미 올바른 문자열이나 숫자라고 가정합니다.
- 빈 문자열을 `Number()`로 변환하면 오류가 날 것이라고 생각합니다.
- 문자열 `"false"`를 `Boolean()`로 변환하면 `false`가 될 것이라고 생각합니다.
- `==`의 암시적 형 변환에 의존합니다.
- `filter`, `map`, `forEach`의 반환값과 목적을 구분하지 않습니다.
- `reduce`를 짧게 쓸 수 있다는 이유만으로 복잡한 누적 로직에 사용합니다.
- 객체를 다른 변수에 대입하면 독립된 복사본이 생긴다고 생각합니다.
- 스프레드 문법이 중첩 객체까지 모두 복사한다고 생각합니다.
- 배열과 객체를 직접 변경하면서 이전 값도 보존된다고 생각합니다.
- 한 함수에서 입력 검사, 계산, DOM 변경, 저장, 네트워크 요청을 모두 처리합니다.
- 모듈을 import하는 것만으로 서버나 타이머 같은 외부 동작이 시작되게 만듭니다.
- `catch`에서 오류를 무시하고 성공 화면을 표시합니다.
- 정상적인 "값 없음"과 실제 처리 실패를 같은 방식으로 표현합니다.

## 완료 기준

다음 내용을 직접 설명하거나 구현할 수 있으면 이 문서의 목표를 달성한 것입니다.

- `const`와 `let`의 차이를 설명할 수 있습니다.
- `const` 객체의 속성은 바뀔 수 있다는 점을 설명할 수 있습니다.
- `===`와 `==`의 차이를 설명하고 일반 코드에서 엄격한 비교를 사용할 수 있습니다.
- 조건문과 반복문으로 작은 계산을 작성할 수 있습니다.
- 문자열 입력을 필요한 타입으로 변환한 뒤 허용 범위를 검사할 수 있습니다.
- `filter`, `map`, `some`, `forEach`, `reduce`의 목적을 구분할 수 있습니다.
- 계산 함수와 DOM·파일·네트워크처럼 외부 상태를 바꾸는 코드를 분리할 수 있습니다.
- 외부에서 달라지는 값이나 동작을 매개변수로 전달해 테스트 가능한 함수를 만들 수 있습니다.
- 객체 대입이 참조 공유라는 점을 설명할 수 있습니다.
- 배열과 객체를 직접 수정하지 않고 새 값으로 갱신할 수 있습니다.
- 객체 스프레드가 얕은 복사라는 점을 설명할 수 있습니다.
- `null`, `undefined`, falsy 값의 차이를 설명할 수 있습니다.
- 문자열 `"false"`가 truthy라는 점을 설명할 수 있습니다.
- `||`와 `??`가 기본값을 선택하는 조건의 차이를 설명할 수 있습니다.
- ESM의 `export`와 `import`를 사용해 파일 사이 공개 범위를 정할 수 있습니다.
- 공유 모듈 import만으로 외부 동작을 시작하지 않아야 하는 이유를 설명할 수 있습니다.
- 처리할 수 없는 실패를 `Error`로 전달하고 처리 가능한 위치에서 `catch`할 수 있습니다.

## 다음 문서

브라우저 상태가 필요하면 [`DOM, 이벤트, URL과 저장소`](05-dom-events-url-storage.md)를 읽습니다. Core 학습은 [`비동기 작업과 fetch`](06-async-fetch-errors.md)로 이어집니다.
