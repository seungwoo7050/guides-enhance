# React Effect와 비동기 요청

Effect는 렌더링 뒤에 실행하고 싶은 코드를 모두 넣는 곳이 아닙니다. 네트워크 요청, 타이머, 브라우저 이벤트, WebSocket처럼 React 밖에서 움직이는 대상과 컴포넌트의 수명을 맞출 때 사용합니다.

## 목표

- 렌더링 중 계산, 사용자 이벤트, Effect를 구분합니다.
- Effect가 읽는 값을 의존성 배열에 반영합니다.
- 요청·리스너·타이머·연결을 정리합니다.
- 오래된 클로저와 늦게 도착한 응답을 처리합니다.
- 개발 모드에서 설정과 정리가 반복되어도 자원이 중복되지 않게 합니다.

## Effect가 필요하지 않은 경우

`props`와 `state`에서 바로 계산할 수 있는 값은 렌더링 중 계산합니다.

```tsx
const visible = tasks.filter((task) => filter === "all" || task.status === filter);
```

아래처럼 Effect에서 같은 값을 다시 상태로 저장하면 화면 반영이 한 번 늦고 값도 두 군데에 생깁니다.

```tsx
// 피합니다.
useEffect(() => setVisible(filterTasks(tasks, filter)), [tasks, filter]);
```

버튼을 눌렀을 때 바로 실행할 작업은 이벤트 처리기에 둡니다. 제출 여부를 상태로 바꾼 뒤 Effect에서 실제 요청을 보내는 우회 방식은 중복 요청을 만들기 쉽습니다.

## 브라우저 값과 맞추기

```tsx
useEffect(() => {
  document.title = `${board.title} · 협업 보드`;
}, [board.title]);
```

이 Effect는 React 값과 브라우저 탭 제목을 맞춥니다. 의존성 배열은 임의의 실행 조건이 아니라 Effect가 읽는 React 값의 목록입니다.

## 요청 수명

```tsx
useEffect(() => {
  const controller = new AbortController();
  setState({ status: "loading" });

  searchUsers(query, controller.signal)
    .then((users) => setState({ status: "ready", users }))
    .catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ status: "error", message: toMessage(error) });
    });

  return () => controller.abort();
}, [query]);
```

`query`가 바뀌면 이전 요청을 취소한 뒤 새 요청을 시작합니다. 컴포넌트가 사라질 때도 같은 정리 함수가 실행됩니다. API가 취소를 지원하지 않는다면 요청 번호를 비교해 오래된 결과를 무시합니다.

## 오래된 클로저

콜백은 만들어진 렌더링 시점의 값을 기억합니다.

```tsx
useEffect(() => {
  const timer = setInterval(() => console.log(count), 1_000);
  return () => clearInterval(timer);
}, []);
```

위 타이머는 계속 초기 `count`를 출력합니다. 최신 값을 읽어야 한다면 `count`를 의존성에 넣어 타이머를 다시 만들거나, 타이머는 유지하고 `ref`에서 최신 값을 읽는 방법을 사용합니다. 린트 경고를 없애려고 실제 의존성을 숨기지 않습니다.

## 이벤트 리스너 정리

```tsx
useEffect(() => {
  function onPopState() {
    setFilter(readFilter(location.href));
  }

  window.addEventListener("popstate", onPopState);
  return () => window.removeEventListener("popstate", onPopState);
}, []);
```

등록과 해제에는 같은 함수 객체가 필요합니다. 각각 다른 인라인 함수를 쓰면 등록한 리스너가 남습니다.

## 타이머와 WebSocket

```tsx
useEffect(() => {
  const socket = new WebSocket(url);
  const heartbeat = setInterval(() => sendPing(socket), 20_000);

  return () => {
    clearInterval(heartbeat);
    socket.close(1000, "화면을 닫았습니다.");
  };
}, [url]);
```

프로토콜 처리 전체를 컴포넌트 안에 넣지 않습니다. 별도 클라이언트가 메시지 검증과 재연결을 담당하고, Effect는 그 클라이언트를 만들고 닫는 시점만 관리하는 편이 읽기 쉽습니다.

## 개발 모드의 반복 실행

개발 모드에서는 Effect의 설정과 정리가 한 번 더 실행될 수 있습니다. 올바른 코드는 “설정 → 정리 → 다시 설정”을 해도 리스너나 연결이 두 개 남지 않아야 합니다. 전역 플래그로 한 번만 실행되게 막으면 실제 라우트 전환과 재연결 문제를 숨길 수 있습니다.

## 서버에서 처리할 수 있는 요청

초기 페이지에 필요한 데이터까지 모두 클라이언트 Effect에서 가져올 필요는 없습니다. Next.js Server Component나 데이터 도구가 요청, 캐시, 중복 제거를 맡을 수 있습니다. 브라우저 상호작용이 필요한지 먼저 확인합니다.

## 흔한 실수

- 계산 가능한 값을 Effect에서 상태로 복사합니다.
- 사용자 이벤트를 상태 플래그와 Effect를 거쳐 처리합니다.
- 의존성 배열에서 실제로 읽는 값을 뺍니다.
- 요청·리스너·타이머·소켓을 정리하지 않습니다.
- 취소 오류와 실제 오류를 모두 무시합니다.
- 개발 모드에서 연결이나 구독이 중복됩니다.

## 완료 기준

- 렌더링 계산, 이벤트 처리기, Effect의 용도를 구분합니다.
- 요청이 바뀌거나 화면이 닫힐 때 이전 작업을 정리합니다.
- 늦은 이전 응답이 최신 화면을 덮지 않게 합니다.
- 등록한 리스너와 타이머를 같은 코드에서 해제합니다.
- 설정과 정리가 반복되어도 외부 자원이 하나만 남습니다.

## 연결 exercise

[`user-directory`](../../exercises/user-directory/README.md)는 느린 이전 검색이 최신 결과를 덮지 않는지 검사합니다.
