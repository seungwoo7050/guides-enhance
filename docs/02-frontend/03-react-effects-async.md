# React Effect와 비동기 요청

React의 Effect는 “렌더링 뒤에 실행하고 싶은 코드”를 모두 넣는 장소가 아닙니다. Effect는 **렌더링 결과 때문에 외부 시스템과 동기화해야 할 때** 사용하는 탈출구입니다. 여기서 외부 시스템은 브라우저 API, 네트워크 연결, 이벤트 리스너, 타이머, WebSocket, React가 관리하지 않는 라이브러리 등을 뜻합니다.

먼저 다음 세 가지를 구분합니다.

```text
화면에 필요한 값을 계산한다
→ 렌더링 중 계산

사용자의 특정 행동 때문에 작업한다
→ 이벤트 처리기

컴포넌트가 화면에 존재하는 동안 외부 시스템과 상태를 맞춘다
→ Effect
```

이 구분이 명확하면 불필요한 Effect와 상태 복사를 크게 줄일 수 있습니다.

## 목표

- 렌더링 중 계산, 사용자 이벤트, Effect의 역할을 구분합니다.
- Effect가 읽는 반응형 값을 의존성 배열에 정확히 반영합니다.
- Effect의 설정과 정리를 하나의 수명 주기로 이해합니다.
- 요청·리스너·타이머·연결을 중단하거나 해제합니다.
- 오래된 클로저와 늦게 도착한 응답이 최신 상태를 덮는 문제를 처리합니다.
- 개발 모드에서 설정과 정리가 반복되어도 외부 자원이 중복되지 않게 합니다.
- 초기 데이터 요청을 반드시 클라이언트 Effect에서 해야 하는 것은 아님을 이해합니다.

## Effect가 필요하지 않은 경우

`props`와 `state`에서 바로 계산할 수 있는 값은 렌더링 중 계산합니다.

```tsx
const visible = tasks.filter(
  (task) => filter === "all" || task.status === filter
);
```

아래처럼 같은 값을 Effect에서 다시 상태로 저장하지 않습니다.

```tsx
// 피합니다.
const [visible, setVisible] = useState<Task[]>([]);

useEffect(() => {
  setVisible(filterTasks(tasks, filter));
}, [tasks, filter]);
```

이 구조는 다음과 같은 문제가 있습니다.

```text
tasks 또는 filter 변경
→ 먼저 이전 visible로 렌더링
→ Effect 실행
→ setVisible
→ 다시 렌더링
```

즉 원래 한 번의 렌더링에서 계산할 수 있는 값을 별도 상태로 복사하면서 추가 렌더링이 생기고, `tasks`·`filter`·`visible`이라는 서로 맞춰야 할 값도 늘어납니다.

계산이 비싸서 최적화가 필요한 경우에도 먼저 Effect가 아니라 렌더링 계산을 유지한 채 필요한 경우 `useMemo` 같은 메모이제이션을 검토합니다. 메모이제이션은 값의 의미를 바꾸는 상태 저장 수단이 아니라 계산 비용을 줄이기 위한 최적화입니다.

## 사용자 행동은 이벤트 처리기에서 처리합니다

버튼 클릭이나 폼 제출처럼 **어떤 사용자 행동 때문에 작업하는지 명확한 경우** 그 작업을 이벤트 처리기에 둡니다.

```tsx
async function handleSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  await saveBoard();
}
```

다음처럼 “제출해야 함”이라는 상태를 만들고 Effect가 실제 제출을 감지하게 우회하지 않습니다.

```tsx
// 피합니다.
const [shouldSubmit, setShouldSubmit] = useState(false);

useEffect(() => {
  if (shouldSubmit) {
    saveBoard();
  }
}, [shouldSubmit]);
```

이 방식은 실제 원인인 사용자 이벤트와 실행할 작업이 떨어져 있어 흐름을 추적하기 어렵고, 상태 변화나 재실행 조건 때문에 중복 요청을 만들기 쉽습니다.

반대로 사용자가 어떤 버튼을 눌렀는지와 관계없이 **컴포넌트가 화면에 존재하기 때문에** 연결해야 하는 외부 시스템이라면 Effect가 적합합니다.

## Effect는 외부 시스템과 동기화합니다

예를 들어 문서 제목을 현재 보드 이름과 맞추려면 다음과 같이 작성할 수 있습니다.

```tsx
useEffect(() => {
  document.title = `${board.title} · 협업 보드`;
}, [board.title]);
```

이 코드는 React의 `board.title`과 브라우저가 관리하는 `document.title`을 동기화합니다.

또 다른 예로 채팅방이 보이는 동안 외부 연결을 유지해야 한다면 연결의 시작과 종료를 같은 Effect에 둡니다.

```tsx
useEffect(() => {
  const connection = createConnection(roomId);
  connection.connect();

  return () => {
    connection.disconnect();
  };
}, [roomId]);
```

Effect를 “컴포넌트가 마운트될 때 한 번 실행되는 코드”라고만 이해하면 의존성 변경 시의 동작을 놓치기 쉽습니다. 더 정확하게는 **현재 렌더링의 반응형 값에 맞게 외부 시스템을 설정하고, 그 설정이 더 이상 유효하지 않을 때 정리하는 과정**입니다.

## Effect의 실행과 정리 순서

다음 Effect를 생각해 봅니다.

```tsx
useEffect(() => {
  const connection = connect(roomId);

  return () => {
    connection.disconnect();
  };
}, [roomId]);
```

`roomId`가 `"general"`에서 `"random"`으로 바뀌면 개념적으로 다음 순서가 됩니다.

```text
"general"로 설정
→ roomId 변경 후 새 렌더링
→ "general" 설정 정리
→ "random"으로 새 설정
```

컴포넌트가 화면에서 제거될 때는 마지막 설정을 정리합니다.

```text
"random"으로 설정
→ 컴포넌트 제거
→ "random" 설정 정리
```

따라서 cleanup 함수는 언마운트 전용 코드가 아닙니다. **의존성이 바뀌어 Effect를 다시 설정하기 전에도 이전 설정을 정리합니다.**

설정과 정리는 서로 대응해야 합니다.

```tsx
useEffect(() => {
  window.addEventListener("resize", onResize);

  return () => {
    window.removeEventListener("resize", onResize);
  };
}, [onResize]);
```

```text
addEventListener ↔ removeEventListener
setInterval       ↔ clearInterval
connect           ↔ disconnect
subscribe         ↔ unsubscribe
```

Effect가 아무 외부 자원도 만들지 않는다면 cleanup이 항상 필요한 것은 아닙니다. 중요한 것은 Effect가 만든 지속적인 영향이 있다면 그 영향을 되돌릴 방법도 같은 수명 주기에 두는 것입니다.

## 의존성 배열은 실행 조건 목록이 아닙니다

Effect가 컴포넌트 내부의 `props`, `state`, 함수, 변수처럼 렌더링에 따라 달라질 수 있는 값을 읽으면 그 값은 **반응형 값(reactive value)**입니다.

```tsx
function ChatRoom({ roomId }: { roomId: string }) {
  const [serverUrl, setServerUrl] = useState("https://example.com");

  useEffect(() => {
    const connection = createConnection(serverUrl, roomId);
    connection.connect();

    return () => connection.disconnect();
  }, [serverUrl, roomId]);
}
```

Effect는 `serverUrl`과 `roomId`를 읽으므로 두 값 모두 의존성입니다.

의존성 배열은 다음과 같이 해석합니다.

```tsx
useEffect(() => {
  // ...
}, [a, b]);
```

초기 커밋 뒤 Effect를 실행하고, 이후 `a` 또는 `b`가 이전 렌더링의 값과 달라진 커밋 뒤에 이전 Effect를 정리한 후 다시 실행합니다.

빈 배열은 “내가 한 번만 실행하고 싶다”는 명령이 아닙니다.

```tsx
useEffect(() => {
  // 이 Effect 안에는 렌더링에 따라 달라지는 반응형 의존성이 없어야 합니다.
}, []);
```

또한 의존성 배열 자체를 생략하면 Effect는 매 커밋 뒤 다시 실행됩니다.

```tsx
useEffect(() => {
  // 매 커밋 뒤 실행
});
```

린터가 빠진 의존성을 지적한다면 경고를 억지로 없애기보다 Effect의 코드와 의존성이 왜 맞지 않는지 확인합니다.

```tsx
// 피합니다.
// eslint-disable-next-line react-hooks/exhaustive-deps
useEffect(() => {
  connect(roomId);
}, []);
```

위 코드는 `roomId`가 바뀌어도 Effect가 새 방과 동기화되지 않는 버그를 만들 수 있습니다.

## 객체와 함수 의존성

React는 각 의존성을 이전 값과 비교합니다. 객체와 함수는 내용이 같아 보여도 렌더링마다 새로 생성하면 다른 참조가 됩니다.

```tsx
function ChatRoom({ roomId }: { roomId: string }) {
  const options = {
    roomId,
    serverUrl: "https://example.com",
  };

  useEffect(() => {
    const connection = createConnection(options);
    connection.connect();
    return () => connection.disconnect();
  }, [options]);
}
```

`options`는 렌더링할 때마다 새 객체가 되므로 Effect가 필요 이상으로 다시 실행될 수 있습니다.

Effect 안에서만 필요한 객체라면 Effect 안에서 만드는 편이 더 단순합니다.

```tsx
useEffect(() => {
  const options = {
    roomId,
    serverUrl: "https://example.com",
  };

  const connection = createConnection(options);
  connection.connect();

  return () => connection.disconnect();
}, [roomId]);
```

함수도 같은 원칙을 적용합니다. 의존성을 줄이기 위해 무조건 `useCallback`을 추가하기보다, 먼저 그 함수가 정말 Effect 밖에 있어야 하는지 확인합니다.

## 요청 수명과 `AbortController`

검색어가 바뀔 때마다 요청하는 컴포넌트를 생각해 봅니다.

```tsx
useEffect(() => {
  const controller = new AbortController();

  setState({ status: "loading" });

  searchUsers(query, controller.signal)
    .then((users) => {
      setState({ status: "ready", users });
    })
    .catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      setState({
        status: "error",
        message: toMessage(error),
      });
    });

  return () => {
    controller.abort();
  };
}, [query]);
```

`query`가 바뀌면 다음 일이 일어납니다.

```text
query = "rea" 요청 시작
→ query = "react"로 변경
→ "rea" Effect cleanup에서 이전 요청 취소
→ "react" 요청 시작
```

컴포넌트가 제거될 때도 cleanup에서 현재 요청을 취소합니다.

`AbortController`를 사용하려면 실제 요청 함수가 전달받은 `signal`을 하위 API까지 전달해야 합니다.

```tsx
async function searchUsers(query: string, signal: AbortSignal) {
  const response = await fetch(
    `/api/users?q=${encodeURIComponent(query)}`,
    { signal }
  );

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json() as Promise<User[]>;
}
```

취소는 정상적인 수명 종료일 수 있으므로 일반 네트워크 오류와 구분합니다. 반대로 모든 오류를 무시해서는 안 됩니다.

## 늦게 도착한 응답과 경쟁 상태

비동기 요청은 시작한 순서대로 끝난다는 보장이 없습니다.

```text
"A" 검색 시작
→ "AB" 검색 시작
→ "AB" 응답 도착
→ "A" 응답이 늦게 도착
```

아무 방어가 없으면 마지막에 도착한 `"A"` 결과가 더 최신 검색인 `"AB"` 결과를 덮을 수 있습니다. 이것이 요청 경쟁 상태(race condition)의 한 예입니다.

취소 가능한 API라면 이전 요청을 취소하는 것이 좋습니다. 취소할 수 없거나 결과를 완전히 중단할 수 없는 작업이라면 cleanup에서 오래된 결과를 무시하도록 만들 수 있습니다.

```tsx
useEffect(() => {
  let ignore = false;

  setState({ status: "loading" });

  searchUsers(query)
    .then((users) => {
      if (ignore) return;
      setState({ status: "ready", users });
    })
    .catch((error: unknown) => {
      if (ignore) return;

      setState({
        status: "error",
        message: toMessage(error),
      });
    });

  return () => {
    ignore = true;
  };
}, [query]);
```

여기서 `ignore`는 각 Effect 실행마다 별도로 만들어집니다. 이전 Effect가 정리되면 이전 요청의 콜백만 무시하게 됩니다.

요청 번호를 사용할 수도 있습니다.

```tsx
const requestIdRef = useRef(0);

useEffect(() => {
  const requestId = ++requestIdRef.current;

  searchUsers(query).then((users) => {
    if (requestId !== requestIdRef.current) return;
    setState({ status: "ready", users });
  });
}, [query]);
```

중요한 목표는 **늦게 끝난 이전 작업이 현재 화면의 최신 상태를 덮지 않게 하는 것**입니다.

## 오래된 클로저

JavaScript 함수는 자신이 만들어진 렌더링의 값을 기억합니다.

```tsx
useEffect(() => {
  const timer = setInterval(() => {
    console.log(count);
  }, 1_000);

  return () => clearInterval(timer);
}, []);
```

이 Effect는 빈 의존성 배열 때문에 처음 설정된 타이머를 계속 사용합니다. 타이머의 콜백 역시 처음 Effect가 실행된 렌더링의 `count`를 기억하므로 이후 `count`가 바뀌어도 초기 값을 계속 출력합니다.

가장 단순한 해결책은 Effect가 실제로 `count` 변화에 반응해야 한다면 의존성에 포함하는 것입니다.

```tsx
useEffect(() => {
  const timer = setInterval(() => {
    console.log(count);
  }, 1_000);

  return () => clearInterval(timer);
}, [count]);
```

이 경우 `count`가 바뀔 때마다 이전 타이머를 해제하고 새 타이머를 만듭니다.

반대로 외부 구독이나 타이머 자체는 유지하면서 콜백에서 최신 값만 읽어야 하는 구조라면 `ref` 같은 별도의 패턴을 사용할 수 있습니다.

```tsx
const countRef = useRef(count);

useEffect(() => {
  countRef.current = count;
}, [count]);

useEffect(() => {
  const timer = setInterval(() => {
    console.log(countRef.current);
  }, 1_000);

  return () => clearInterval(timer);
}, []);
```

`ref`는 렌더링에 사용할 상태를 숨기는 수단이 아닙니다. **렌더링을 다시 발생시키지 않으면서 외부 콜백에서 최신 값을 참조해야 할 때** 제한적으로 사용합니다.

## 이전 상태로 갱신할 때는 함수형 갱신을 사용할 수 있습니다

Effect 안의 콜백이 이전 상태를 바탕으로 다음 상태를 만들어야 한다면 함수형 갱신이 불필요한 의존성을 줄이는 데 도움이 될 수 있습니다.

```tsx
useEffect(() => {
  const timer = setInterval(() => {
    setCount((current) => current + 1);
  }, 1_000);

  return () => clearInterval(timer);
}, []);
```

이 코드는 `count` 값을 읽는 대신 React가 제공하는 직전 상태를 바탕으로 새 값을 계산하므로 `count`를 Effect의 의존성으로 읽지 않습니다.

다만 함수형 갱신을 “의존성 경고를 없애는 기법”으로 기계적으로 사용해서는 안 됩니다. 새 결과를 만들기 위해 실제로 직전 상태만 필요한 경우에 사용합니다.

## 이벤트 리스너 정리

브라우저 이벤트를 구독했다면 같은 리스너를 해제합니다.

```tsx
useEffect(() => {
  function onPopState() {
    setFilter(readFilter(window.location.href));
  }

  window.addEventListener("popstate", onPopState);

  return () => {
    window.removeEventListener("popstate", onPopState);
  };
}, []);
```

등록과 해제에는 같은 이벤트 종류와 같은 함수 객체가 필요합니다.

다음 코드는 등록한 리스너를 제거하지 못합니다.

```tsx
// 피합니다.
useEffect(() => {
  window.addEventListener("resize", () => {
    updateSize();
  });

  return () => {
    window.removeEventListener("resize", () => {
      updateSize();
    });
  };
}, []);
```

두 화살표 함수는 모양이 같아도 서로 다른 함수 객체입니다.

## 타이머 정리

타이머를 시작한 Effect에서는 해당 타이머를 정리합니다.

```tsx
useEffect(() => {
  const timer = setInterval(() => {
    refreshStatus();
  }, 5_000);

  return () => {
    clearInterval(timer);
  };
}, []);
```

`setTimeout`도 필요하다면 `clearTimeout`으로 취소합니다.

cleanup이 없으면 화면에서 사라진 컴포넌트와 관련된 콜백이 계속 실행되거나, Effect가 다시 설정될 때 타이머가 여러 개 겹칠 수 있습니다.

## WebSocket과 장기 연결

장기 연결도 Effect의 설정과 정리 수명에 맞춥니다.

```tsx
useEffect(() => {
  const socket = new WebSocket(url);

  const heartbeat = setInterval(() => {
    if (socket.readyState === WebSocket.OPEN) {
      sendPing(socket);
    }
  }, 20_000);

  return () => {
    clearInterval(heartbeat);
    socket.close(1000, "화면을 닫았습니다.");
  };
}, [url]);
```

`url`이 바뀌면 이전 소켓과 heartbeat를 정리한 뒤 새 연결을 만듭니다.

다만 프로토콜 처리 전체를 컴포넌트 Effect에 넣으면 UI 코드와 네트워크 코드가 강하게 결합됩니다.

다음 책임은 별도 클라이언트나 커스텀 Hook으로 분리할 수 있습니다.

- 메시지 형식 검증
- 재연결 정책
- heartbeat 세부 구현
- 순서 번호와 중복 처리
- 인증 갱신
- 백오프

컴포넌트의 Effect는 가능하면 “이 화면이 이 연결을 언제 시작하고 언제 끝내는가”라는 수명 관리에 집중합니다.

## 개발 모드의 반복 실행

React Strict Mode가 활성화된 개발 환경에서는 Effect의 문제를 찾기 위해 초기 설정 전에 추가적인 **설정 → 정리 → 설정** 순서를 볼 수 있습니다.

예를 들어 다음 Effect에 cleanup이 없다면 개발 중 연결이 두 개 생기는 문제가 드러날 수 있습니다.

```tsx
// 피합니다.
useEffect(() => {
  const connection = createConnection();
  connection.connect();
}, []);
```

올바른 Effect라면 설정과 정리가 대칭을 이룹니다.

```tsx
useEffect(() => {
  const connection = createConnection();
  connection.connect();

  return () => {
    connection.disconnect();
  };
}, []);
```

목표는 “개발 모드에서 Effect를 한 번만 실행시키는 것”이 아닙니다. **설정과 정리가 몇 번 반복되어도 외부 시스템에 올바른 상태 하나만 남도록 만드는 것**입니다.

따라서 다음과 같은 전역 플래그로 반복 실행을 숨기지 않습니다.

```tsx
// 피합니다.
let alreadyConnected = false;

useEffect(() => {
  if (alreadyConnected) return;
  alreadyConnected = true;

  connect();
}, []);
```

이 코드는 개발 모드의 증상만 가릴 뿐 실제 화면 이탈 후 재진입, 다른 컴포넌트 인스턴스, 연결 종료 같은 수명 문제를 해결하지 못합니다.

Strict Mode의 추가 실행은 개발 시 검사 동작이며 프로덕션에서 동일한 추가 검사 주기가 그대로 실행되는 것은 아닙니다. 그러나 프로덕션에서도 의존성 변경과 언마운트 때문에 Effect의 설정과 정리는 정상적으로 여러 번 일어날 수 있습니다.

## 서버에서 처리할 수 있는 요청

초기 페이지에 필요한 데이터를 모두 클라이언트 Effect에서 가져올 필요는 없습니다.

클라이언트 Effect에서 데이터를 가져오면 일반적으로 다음 흐름이 됩니다.

```text
HTML/JS 전달
→ 컴포넌트 렌더링
→ 브라우저에서 Effect 실행
→ 데이터 요청
→ 응답 후 다시 렌더링
```

프레임워크가 서버 데이터 로딩, Server Component, 라우트 로더, 요청 캐시 같은 기능을 제공한다면 초기 데이터는 더 앞선 단계에서 가져올 수 있습니다.

예를 들어 Next.js의 Server Component를 사용하는 구조에서는 서버에서 데이터를 읽어 렌더링 결과에 포함할 수 있습니다. 이 경우 초기 데이터를 얻기 위한 `useEffect` 자체가 필요하지 않을 수 있습니다.

Effect에서의 데이터 요청이 적합한 경우도 있습니다.

- 브라우저에서만 알 수 있는 값에 따라 요청합니다.
- 사용자가 화면에서 값을 바꾼 뒤 다시 조회합니다.
- 특정 외부 클라이언트의 수명을 컴포넌트와 맞춰야 합니다.
- 사용하는 프레임워크에 더 적절한 데이터 로딩 계층이 없습니다.

중요한 것은 “데이터 요청이므로 Effect”라고 자동으로 결정하지 않고, **그 요청이 왜 브라우저 렌더링 이후에 시작되어야 하는지**를 확인하는 것입니다.

## Effect를 설계할 때 확인할 질문

Effect를 작성하기 전에 다음 순서로 확인하면 불필요한 Effect를 줄일 수 있습니다.

1. 이 값은 `props`와 `state`에서 렌더링 중 계산할 수 있는가?
2. 이 작업은 특정 사용자 행동 때문에 발생하는가?
3. React 밖의 시스템과 동기화해야 하는가?
4. Effect가 읽는 반응형 값은 무엇인가?
5. 그 값이 바뀌면 이전 설정을 어떻게 정리해야 하는가?
6. 컴포넌트가 사라질 때 남는 요청·리스너·타이머·연결이 있는가?
7. 비동기 결과가 늦게 도착하면 최신 결과를 덮을 수 있는가?
8. 설정 → 정리 → 설정이 반복되어도 같은 의미를 유지하는가?

1번이면 렌더링 계산, 2번이면 이벤트 처리기, 3번이면 Effect가 후보입니다.

## 흔한 실수

- `props`와 `state`에서 계산 가능한 값을 Effect에서 다시 상태로 복사합니다.
- 사용자 이벤트를 상태 플래그와 Effect를 거쳐 처리합니다.
- Effect를 단순한 “마운트 후 실행 코드”로 이해합니다.
- 의존성 배열을 임의의 실행 조건 목록처럼 작성합니다.
- 실제로 읽는 반응형 값을 의존성에서 빼고 린트 경고를 억제합니다.
- 렌더링마다 새로 만들어지는 객체나 함수 때문에 Effect가 계속 재실행됩니다.
- cleanup이 언마운트 때만 실행된다고 생각합니다.
- 요청·리스너·타이머·소켓을 정리하지 않습니다.
- 취소 오류와 실제 요청 실패를 구분하지 않습니다.
- 늦은 이전 응답이 최신 결과를 덮는 경쟁 상태를 처리하지 않습니다.
- 오래된 클로저가 처음 렌더링의 값을 계속 읽습니다.
- 개발 모드의 반복 실행을 전역 플래그로 숨깁니다.
- 초기 서버 데이터를 이유 없이 모두 클라이언트 Effect에서 다시 가져옵니다.

## 완료 기준

- 렌더링 계산, 이벤트 처리기, Effect가 각각 어떤 원인으로 실행되는지 구분합니다.
- Effect는 React 밖의 시스템과 동기화하기 위한 것이라고 설명합니다.
- Effect가 읽는 반응형 값과 의존성 배열이 일치합니다.
- 의존성이 바뀌면 이전 cleanup 후 새 setup이 실행된다는 수명을 설명합니다.
- 요청이 바뀌거나 화면이 닫힐 때 이전 작업을 취소하거나 무시합니다.
- 늦은 이전 응답이 최신 화면을 덮지 않게 합니다.
- 오래된 클로저가 생기는 이유와 해결 방향을 설명합니다.
- 등록한 리스너와 생성한 타이머·연결을 같은 Effect에서 해제합니다.
- 개발 모드에서 설정과 정리가 반복되어도 외부 자원이 중복되지 않습니다.
- 초기 데이터 요청을 Effect에 둘지 서버·프레임워크 계층에 둘지 이유를 설명합니다.

## 연결 exercise

[`user-directory`](../../exercises/user-directory/README.md)는 느린 이전 검색이 최신 결과를 덮지 않는지 검사합니다.
