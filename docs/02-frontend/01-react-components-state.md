# React 컴포넌트와 상태

React 컴포넌트는 현재의 `props`와 `state`를 입력으로 받아 화면을 계산합니다. 상태가 바뀌면 React는 컴포넌트를 다시 렌더링하고, 새 결과에 맞게 화면을 갱신합니다.

따라서 중요한 질문은 단순히 “컴포넌트를 몇 개로 나눌까?”가 아니라 다음과 같습니다.

- 어떤 값이 실제 상태입니까?
- 그 값의 기준값(source of truth)은 어디에 있습니까?
- 어느 컴포넌트가 그 상태를 소유하고 변경합니까?
- 다른 값에서 계산할 수 있어 저장하지 않아도 되는 값은 무엇입니까?

## 목표

- `props`와 `state`의 차이를 설명합니다.
- 한 렌더링이 보는 값이 하나의 스냅샷이라는 점을 이해합니다.
- 상태를 실제로 함께 사용하는 가장 가까운 컴포넌트에 둡니다.
- 이전 상태를 바탕으로 갱신할 때 updater 함수를 사용합니다.
- 배열과 객체를 직접 변경하지 않고 새 값으로 갱신합니다.
- 기존 값에서 계산할 수 있는 값을 별도 상태로 저장하지 않습니다.
- 서버, URL, 실시간 연결, 컴포넌트 중 어디를 기준값으로 삼을지 구분합니다.

## 컴포넌트는 입력으로 화면을 만듭니다

다음과 같은 작업 항목이 있다고 가정합니다.

```tsx
type Task = {
  id: string;
  title: string;
  completed: boolean;
};
```

목록의 한 항목을 표시하는 컴포넌트는 다음처럼 작성할 수 있습니다.

```tsx
type TaskItemProps = {
  task: Task;
  onToggle: (id: string) => void;
};

export function TaskItem({ task, onToggle }: TaskItemProps) {
  return (
    <li>
      <label>
        <input
          type="checkbox"
          checked={task.completed}
          onChange={() => onToggle(task.id)}
        />
        {task.title}
      </label>
    </li>
  );
}
```

`props`는 부모 컴포넌트가 자식 컴포넌트에 전달하는 입력입니다. 위 예제에서는 `task`와 `onToggle`이 `TaskItem`의 `props`입니다.

`props`는 해당 렌더링에서 읽기 전용으로 다룹니다. 자식이 다음처럼 전달받은 객체를 직접 수정해서는 안 됩니다.

```tsx
// 피합니다.
task.completed = true;
```

대신 사용자의 동작을 부모가 전달한 콜백으로 알립니다.

```tsx
onChange={() => onToggle(task.id)}
```

이 콜백을 호출한다고 해서 자식이 부모 상태를 직접 수정하는 것은 아닙니다. 자식은 “이 항목을 토글해 달라”고 요청하고, 실제 변경 방법은 상태를 소유한 컴포넌트가 결정합니다.

```text
부모의 state
    ↓ props
  자식 UI
    ↓ 사용자 입력
  콜백 호출
    ↓
부모가 state 갱신
```

## 렌더링 사이에 유지할 값만 state로 둡니다

`useState`는 컴포넌트가 렌더링 사이에 기억해야 하는 값을 저장합니다.

```tsx
const [tasks, setTasks] = useState<Task[]>([]);
```

여기서:

- `tasks`는 현재 렌더링에서 읽는 상태 값입니다.
- `setTasks`는 다음 상태를 설정하도록 React에 요청하는 함수입니다.
- `[]`는 첫 렌더링에 사용할 초기값입니다.

컴포넌트 안의 일반 지역 변수는 렌더링 사이의 상태 저장소가 아닙니다.

```tsx
function Counter() {
  let count = 0;

  function handleClick() {
    count += 1;
  }

  return <button onClick={handleClick}>{count}</button>;
}
```

`count`를 바꿔도 React에는 다시 렌더링해야 한다는 사실이 전달되지 않습니다. 또한 다음 렌더링에서 컴포넌트 함수가 다시 실행되면 `count`는 다시 `0`으로 만들어집니다.

화면에 영향을 주면서 렌더링 사이에 유지되어야 하는 값이라면 `state`가 될 수 있습니다.

- 입력 중인 문자열
- 선택한 탭
- 대화 상자의 열림 여부
- 현재 펼쳐진 메뉴
- 서버 저장이 끝나기 전 화면에 먼저 보여 주는 임시 항목

반면 현재의 `props`나 `state`에서 바로 계산할 수 있는 값은 보통 별도 상태로 저장하지 않습니다.

```tsx
const openCount = tasks.filter((task) => !task.completed).length;
```

다음처럼 `tasks`와 `openCount`를 모두 상태로 두면 두 값을 항상 함께 갱신해야 합니다.

```tsx
// 피합니다.
const [tasks, setTasks] = useState<Task[]>([]);
const [openCount, setOpenCount] = useState(0);
```

어느 한쪽만 갱신되면 서로 모순된 값이 됩니다. 따라서 기준이 되는 상태만 저장하고 나머지는 렌더링 중 계산합니다.

```tsx
const [tasks, setTasks] = useState<Task[]>([]);
const openCount = tasks.filter((task) => !task.completed).length;
```

같은 이유로 필터링한 목록도 원본 목록과 필터 값에서 계산할 수 있다면 별도 상태로 저장하지 않습니다.

```tsx
const visibleTasks = tasks.filter((task) => {
  if (filter === 'open') return !task.completed;
  if (filter === 'done') return task.completed;
  return true;
});
```

`openCount`, `visibleTasks`처럼 다른 값에서 계산한 값을 **파생 값(derived value)**이라고 볼 수 있습니다.

## state는 현재 렌더링의 스냅샷입니다

상태 설정 함수를 호출했다고 해서 현재 실행 중인 코드의 상태 변수가 즉시 바뀌지는 않습니다.

```tsx
function Counter() {
  const [count, setCount] = useState(0);

  function handleClick() {
    console.log(count); // 0
    setCount(1);
    console.log(count); // 여전히 0
  }

  return <button onClick={handleClick}>{count}</button>;
}
```

`setCount(1)`은 현재의 `count` 변수를 직접 수정하는 명령이 아닙니다. React에 다음 렌더링에서 사용할 상태를 바꿔 달라고 요청합니다.

현재 실행 중인 이벤트 핸들러는 자신이 만들어진 렌더링의 `count`를 계속 봅니다. 이후 React가 컴포넌트를 다시 실행하면 새 렌더링에서 새로운 `count` 값을 받습니다.

이 때문에 상태를 일반적인 변경 가능한 변수처럼 생각하면 안 됩니다.

```text
현재 렌더링: count = 0
      ↓
setCount(1)
      ↓ 다음 렌더링 요청
새 렌더링: count = 1
```

## 이전 상태에 의존하면 함수형 갱신을 사용합니다

다음 상태가 이전 상태로부터 계산된다면 상태 설정 함수에 **updater 함수**를 전달합니다.

```tsx
setTasks((current) =>
  current.map((task) =>
    task.id === id
      ? { ...task, completed: !task.completed }
      : task
  )
);
```

여기서 `current`는 React가 처리 중인 최신 대기 상태(pending state)입니다. updater 함수는 그 값을 받아 다음 상태를 반환합니다.

같은 이벤트에서 상태를 여러 번 변경하면 차이가 더 분명합니다.

```tsx
const [count, setCount] = useState(0);

function handleClick() {
  setCount(count + 1);
  setCount(count + 1);
}
```

두 줄 모두 현재 렌더링의 같은 `count`를 읽습니다. `count`가 `0`이었다면 둘 다 `1`로 바꾸라는 요청이 됩니다.

이전 갱신 결과에 이어서 계산하려면 updater 함수를 사용합니다.

```tsx
function handleClick() {
  setCount((value) => value + 1);
  setCount((value) => value + 1);
}
```

React는 updater를 순서대로 적용합니다.

```text
0 -> 1 -> 2
```

React는 여러 상태 갱신을 묶어서 처리할 수 있습니다. 하지만 updater 함수가 필요한 이유를 단순히 “배칭 때문”이라고만 이해하면 부족합니다. 핵심은 현재 이벤트 핸들러가 **현재 렌더링의 상태 스냅샷**을 보고 있다는 점입니다.

다음 상태가 현재 상태와 관계없는 고정값이면 updater 함수가 필요하지 않습니다.

```tsx
setIsOpen(true);
setSelectedTab('settings');
```

반대로 이전 값을 이용해 다음 값을 계산한다면 updater 형태가 안전하고 의도도 명확합니다.

```tsx
setIsOpen((open) => !open);
setCount((count) => count + 1);
```

updater 함수는 상태 계산만 하고 부수 효과를 일으키지 않는 순수 함수로 작성합니다.

## 배열과 객체를 직접 바꾸지 않습니다

JavaScript의 배열과 객체는 변경 가능한 값이지만, React state에 저장한 배열과 객체는 읽기 전용처럼 다룹니다.

다음 코드는 피합니다.

```tsx
// 피합니다.
tasks.push(newTask);
setTasks(tasks);
```

`push()`는 기존 배열 자체를 수정합니다. 그 뒤 `setTasks(tasks)`에 넘기는 값도 이전과 같은 배열 객체입니다.

React는 상태를 갱신할 때 새 값과 기존 값이 같은지 비교합니다. 같은 객체 참조를 다시 전달하면 상태가 바뀌지 않은 것으로 판단되어 렌더링을 생략할 수 있습니다. 더 중요한 문제는 이전 렌더링이 사용하던 상태 객체 자체를 변경해 렌더링 스냅샷을 깨뜨린다는 점입니다.

대신 새 배열을 만들어 전달합니다.

```tsx
setTasks((current) => [...current, newTask]);
```

자주 사용하는 배열 갱신은 다음과 같습니다.

```tsx
// 추가
setTasks((current) => [...current, newTask]);

// 삭제
setTasks((current) =>
  current.filter((task) => task.id !== id)
);

// 항목 변경
setTasks((current) =>
  current.map((task) =>
    task.id === id
      ? { ...task, title: nextTitle }
      : task
  )
);
```

배열만 복사하고 내부 객체를 직접 바꾸는 것도 피합니다.

```tsx
// 피합니다.
setTasks((current) => {
  const next = [...current];
  next[0].completed = true;
  return next;
});
```

`next` 배열은 새 배열이지만 `next[0]`은 기존 배열의 객체와 같은 객체일 수 있습니다. 변경되는 객체도 새로 만듭니다.

```tsx
setTasks((current) =>
  current.map((task) =>
    task.id === id
      ? { ...task, completed: true }
      : task
  )
);
```

### 스프레드는 얕은 복사입니다

스프레드 문법은 한 단계만 복사합니다.

```tsx
const profile = {
  name: 'Kim',
  address: {
    city: 'Busan',
    zipCode: '00000',
  },
};

const next = { ...profile };

console.log(next !== profile);                 // true
console.log(next.address === profile.address); // true
```

따라서 중첩된 값을 바꿀 때는 실제로 변경되는 경로마다 새 객체를 만듭니다.

```tsx
setProfile((current) => ({
  ...current,
  address: {
    ...current.address,
    city: 'Seoul',
  },
}));
```

중첩이 너무 깊어 복사가 복잡하다면 상태 구조를 더 평평하게 만들 수 있는지도 검토합니다.

## 상태를 저장할 위치

모든 값을 `useState`에 넣는 것이 좋은 상태 관리는 아닙니다. 먼저 **어디가 그 값의 기준값인지**를 판단합니다.

| 값 | 기준이 되는 위치 | 예시 |
|---|---|---|
| 서버가 소유하는 지속 데이터 | API와 데이터베이스 | 사용자, 보드, 경기 기록 |
| 주소로 복원·공유할 값 | URL | 검색어, 필터, 정렬, 페이지 번호 |
| 실시간 연결에서 받은 원격 상태 | 서버 메시지와 동기화 기준 | 접속 상태, 이벤트 시퀀스, 실시간 변경 |
| 현재 화면에서만 쓰는 임시 값 | 컴포넌트 | 입력 초안, 메뉴 열림 여부 |

“기준이 서버에 있다”는 말은 클라이언트가 서버 응답을 메모리에 보관하면 안 된다는 뜻이 아닙니다. 화면에 표시하기 위해 서버 데이터를 클라이언트에서 보관할 수 있습니다. 중요한 것은 **같은 의미의 데이터를 여러 독립적인 state에 복사해 각각 별도의 기준값처럼 관리하지 않는 것**입니다.

예를 들어 서버에서 받은 같은 목록을 여러 컴포넌트의 `useState`에 각각 복사하면 한쪽이 변경된 뒤 다른 쪽이 오래된 값을 보여 줄 수 있습니다. 한곳에서 읽고 필요한 컴포넌트에 전달하거나, 하나의 서버 데이터 캐시 계층이 같은 데이터를 관리하도록 합니다.

`props`를 state에 그대로 복사하는 경우도 같은 문제를 만들 수 있습니다.

```tsx
type User = {
  id: string;
  name: string;
};

function UserName({ user }: { user: User }) {
  // 단순 표시가 목적이라면 보통 필요 없습니다.
  const [localUser, setLocalUser] = useState(user);

  return <strong>{localUser.name}</strong>;
}
```

`useState(user)`의 초기값은 첫 렌더링에 사용됩니다. 이후 부모가 새로운 `user`를 전달한다고 해서 `localUser`가 자동으로 같은 값으로 바뀌지는 않습니다.

단순히 표시하는 값이라면 prop을 직접 사용합니다.

```tsx
function UserName({ user }: { user: User }) {
  return <strong>{user.name}</strong>;
}
```

반면 서버에 저장하기 전 사용자가 수정하는 **편집 초안**처럼 원본과 별도로 존재해야 할 의미가 있다면 로컬 state를 두는 것이 자연스럽습니다.

```tsx
const [draftName, setDraftName] = useState(user.name);
```

즉, 값을 복사하는 행위 자체가 항상 잘못인 것은 아닙니다. 같은 의미의 값을 이유 없이 중복 저장하는 것이 문제입니다.

URL도 같은 기준으로 판단합니다. 검색어와 페이지 번호가 새로고침하거나 링크를 공유한 뒤에도 유지되어야 한다면 URL이 기준값이 될 수 있습니다.

```text
/users?q=kim&page=2
```

반대로 아직 제출하지 않은 검색창의 입력 초안처럼 URL에 즉시 반영할 필요가 없는 값은 컴포넌트 state에 둘 수 있습니다.

## 상태를 위로 올릴 때

형제 컴포넌트가 같은 값을 읽거나 함께 변경해야 한다면 각자 같은 상태를 복사하지 않고 **가장 가까운 공통 부모**가 상태를 소유하도록 옮길 수 있습니다. 이를 상태 끌어올리기(lifting state up)라고 합니다.

예를 들어 두 패널 중 하나만 열려 있어야 한다면 각 패널이 별도의 `isOpen` 상태를 가지는 대신 부모가 하나의 식별자를 관리할 수 있습니다.

```tsx
function Accordion() {
  const [activeId, setActiveId] = useState<string | null>(null);

  return (
    <>
      <Panel
        isOpen={activeId === 'first'}
        onOpen={() => setActiveId('first')}
      />
      <Panel
        isOpen={activeId === 'second'}
        onOpen={() => setActiveId('second')}
      />
    </>
  );
}
```

상태 위치는 다음 질문으로 정합니다.

1. 이 값은 다른 `props`나 `state`에서 계산할 수 있습니까?
2. 서버나 URL에 이미 기준값이 있습니까?
3. 누가 이 값을 읽습니까?
4. 누가 이 값을 바꿉니까?
5. 그 컴포넌트들의 가장 가까운 공통 부모는 어디입니까?

모든 상태를 페이지 최상단으로 올릴 필요는 없습니다. 한 컴포넌트에서만 사용하는 입력 초안이나 메뉴 열림 상태까지 위로 올리면 전달 범위만 불필요하게 커집니다.

상태는 **실제로 공유해야 하는 범위 안에서 가능한 한 가까운 곳**에 둡니다.

## 컴포넌트를 나누는 기준

컴포넌트는 JSX 줄 수가 아니라 책임과 재사용 경계를 기준으로 나눕니다.

다음과 같은 실제 이유가 있을 때 분리를 고려합니다.

- 독립적인 UI 단위로 이름을 붙일 수 있습니다.
- 여러 화면이나 위치에서 반복해서 사용합니다.
- 상태나 사용자 상호작용의 책임이 독립적입니다.
- 별도의 Effect나 외부 시스템 연동 책임을 분리하는 것이 의미 있습니다.
- 단독 테스트가 의미 있는 동작 단위입니다.
- 서버에서 실행할 코드와 브라우저에서 실행할 코드를 구분해야 합니다.

컴포넌트가 작다는 사실 자체는 문제가 아닙니다. 그러나 “JSX가 몇 줄을 넘었다”는 이유만으로 작은 래퍼 컴포넌트를 계속 만들면 데이터 흐름을 따라가기 어려워질 수 있습니다.

## 목록의 `key`

목록을 렌더링할 때 각 형제 항목에는 안정적인 `key`가 필요합니다.

```tsx
{tasks.map((task) => (
  <TaskItem
    key={task.id}
    task={task}
    onToggle={handleToggle}
  />
))}
```

`key`는 React가 이전 렌더링의 항목과 다음 렌더링의 항목을 대응시키기 위해 사용하는 식별자입니다. 특히 정렬, 삽입, 삭제가 있는 목록에서 중요합니다.

예를 들어 다음 목록 앞에 새 항목 `X`가 삽입된다고 가정합니다.

```text
이전: A B C
다음: X A B C
```

`task.id`처럼 항목 자체의 안정적인 식별자를 `key`로 사용하면 React는 `A`, `B`, `C`가 위치만 바뀌었고 `X`가 새로 생겼다는 사실을 구분할 수 있습니다.

배열 인덱스는 항목 자체가 아니라 현재 위치를 나타냅니다.

```tsx
// 정렬·삽입·삭제가 있는 목록에서는 피합니다.
{tasks.map((task, index) => (
  <TaskItem key={index} task={task} onToggle={handleToggle} />
))}
```

앞쪽 항목이 삽입되거나 삭제되면 같은 데이터의 인덱스가 바뀝니다. 그 결과 컴포넌트 내부 상태, 입력값, 선택 상태, 포커스 등이 다른 항목과 연결된 것처럼 보이는 문제가 생길 수 있습니다.

렌더링할 때마다 새 값을 만드는 것도 피합니다.

```tsx
// 피합니다.
key={Math.random()}
```

좋은 `key`는 다음 조건을 만족합니다.

- 같은 형제 목록 안에서 고유합니다.
- 렌더링할 때마다 바뀌지 않습니다.
- 항목의 위치가 아니라 항목 자체를 식별합니다.

서버 데이터라면 보통 데이터의 `id`가 적절합니다.

또한 `key`는 React가 내부적으로 사용하는 특별한 값이므로 자식 컴포넌트의 일반 `props`로 전달되지 않습니다. 자식도 식별자가 필요하다면 별도 prop이나 `task.id` 같은 데이터 필드를 사용합니다.

## 흔한 실수

- 전달받은 `props`의 객체나 배열을 직접 수정합니다.
- 계산 가능한 값을 별도 상태로 저장해 서로 동기화해야 하는 값을 늘립니다.
- 배열과 객체를 제자리에서 수정한 뒤 같은 참조를 다시 상태로 전달합니다.
- 이전 상태에 의존하면서 updater 함수 대신 현재 렌더링의 상태 값을 사용합니다.
- `props`를 이유 없이 `useState` 초기값으로 복사하고 이후 prop 변경도 자동으로 반영될 것이라 기대합니다.
- 서버 값과 URL 값을 컴포넌트 state에 다시 복제해 여러 기준값을 만듭니다.
- 목록의 `key`로 정렬·삽입·삭제에 따라 달라지는 배열 인덱스를 사용합니다.
- `key={Math.random()}`처럼 렌더링마다 달라지는 값을 사용합니다.
- 작은 입력값까지 모두 페이지 최상단에서 관리합니다.

## 완료 기준

- `props`는 부모가 전달하는 읽기 전용 입력이고, `state`는 컴포넌트가 렌더링 사이에 기억하는 값이라고 설명할 수 있습니다.
- 상태 설정 함수가 현재 렌더링의 변수를 즉시 바꾸는 것이 아니라 다음 렌더링을 요청한다는 점을 설명할 수 있습니다.
- 이전 상태를 바탕으로 다음 상태를 계산할 때 updater 함수를 사용할 수 있습니다.
- 기존 상태를 직접 변경하지 않고 새 배열과 새 객체를 만들어 갱신할 수 있습니다.
- 스프레드가 얕은 복사라는 점을 이해하고 중첩된 객체를 올바르게 갱신할 수 있습니다.
- 계산 가능한 값을 중복 상태로 저장하지 않습니다.
- 서버, URL, 실시간 연결, 컴포넌트 중 어디를 기준값으로 삼을지 판단할 수 있습니다.
- 여러 컴포넌트가 공유하는 상태를 가장 가까운 공통 부모로 올릴 수 있습니다.
- 목록에서 항목 자체를 나타내는 안정적인 식별자를 `key`로 사용합니다.

## 연결 exercise

프로젝트를 PASS한 뒤 [`user-directory`](../../exercises/user-directory/README.md)를 가이드 없이 구현해 상태 분리와 요청 결과 반영을 다시 확인합니다.
