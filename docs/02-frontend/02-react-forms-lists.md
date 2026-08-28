# React 폼과 목록

폼과 목록에서는 입력값, 서버 오류, 항목 식별자, 키보드 동작을 함께 다뤄야 합니다. 입력을 React가 관리할지 브라우저가 관리할지, 제출 중 어떤 상태를 보여 줄지, 실패한 변경을 어떻게 되돌릴지를 먼저 정합니다.

## 목표

- 제어 입력과 비제어 입력을 상황에 맞게 선택합니다.
- 버튼 클릭이 아니라 폼의 `submit`을 처리합니다.
- 빠른 안내를 위한 클라이언트 검사와 서버 검사를 구분합니다.
- 로딩, 빈 결과, 성공, 오류를 따로 표현합니다.
- 목록 항목의 식별자와 낙관적 변경을 안전하게 관리합니다.

## 제어 입력

```tsx
const [title, setTitle] = useState("");

<input
  id="title"
  value={title}
  onChange={(event) => setTitle(event.target.value)}
/>
```

현재 입력값을 다른 UI에 바로 반영하거나 글자 수를 표시할 때 적합합니다. 키 입력마다 상태가 바뀌므로, 큰 페이지 전체가 이 값을 관리하지 않게 합니다.

## 비제어 입력

간단한 폼은 제출할 때 `FormData`로 읽을 수 있습니다.

```tsx
function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const title = String(data.get("title") ?? "").trim();
}
```

파일 입력처럼 브라우저가 값의 수명을 관리하는 요소에도 적합합니다. 어느 방식이 항상 우월한 것은 아닙니다. 입력값이 필요한 시점과 사용하는 범위를 기준으로 선택합니다.

## 폼 제출

```tsx
<form onSubmit={handleSubmit}>
  <label htmlFor="title">보드 제목</label>
  <input id="title" name="title" />
  <button type="submit">만들기</button>
</form>
```

버튼의 `onClick`만 처리하면 입력 필드에서 Enter를 눌렀을 때의 동작을 빠뜨리기 쉽습니다. 제출 중에는 같은 요청이 다시 전송되지 않게 하고, 진행 중임을 화면에 알립니다.

## 입력 오류를 필드와 연결합니다

```tsx
<label htmlFor="title">보드 제목</label>
<input
  id="title"
  aria-invalid={Boolean(error)}
  aria-describedby={error ? "title-error" : undefined}
/>
{error ? <p id="title-error">{error}</p> : null}
```

제출 뒤 첫 오류 필드로 포커스를 옮길 수 있습니다. 사용자가 글자를 입력할 때마다 포커스를 강제로 이동하지는 않습니다.

클라이언트는 빈 문자열이나 길이 같은 기본 조건을 빠르게 안내합니다. 서버는 같은 값을 다시 검사하고, 중복·권한·현재 버전처럼 서버 데이터가 필요한 조건도 확인합니다.

## 목록 상태를 나눕니다

```tsx
if (state.status === "loading") return <p role="status">불러오는 중입니다.</p>;
if (state.status === "error") return <p role="alert">{state.message}</p>;
if (state.items.length === 0) return <p>표시할 항목이 없습니다.</p>;
```

아직 요청이 끝나지 않은 상태와 정상적으로 빈 결과를 받은 상태는 다릅니다. 기존 목록을 보여 주면서 새로고침하는 경우도 별도 상태로 표현할 수 있습니다.

## 항목 식별자

```tsx
{boards.map((board) => <BoardCard key={board.id} board={board} />)}
```

정렬되거나 삭제되는 목록에 배열 인덱스를 사용하면 다른 카드에 입력값이나 메뉴 상태가 연결될 수 있습니다. 서버 ID가 아직 없는 임시 항목에는 클라이언트가 만든 안정적인 ID를 사용합니다.

## 낙관적 변경

서버 응답 전에 화면을 바꿀 수 있지만, 실패했을 때 어떤 값이 남는지도 정해야 합니다.

```text
현재 값 보존
→ 작업 ID가 있는 임시 변경 추가
→ 요청 전송
→ 성공하면 서버 결과로 교체
→ 실패하면 해당 변경만 되돌리거나 실패 표시
```

전체 배열을 과거 값으로 되돌리면 그사이에 성공한 다른 변경까지 사라질 수 있습니다. 작업별 ID를 사용해 실패한 항목만 처리합니다. `409` 충돌이면 최신 서버 값을 받아 사용자의 초안과 비교해야 할 수 있습니다.

## 삭제와 확인

삭제 버튼의 이름에는 대상을 포함합니다.

```tsx
<button aria-label={`${board.title} 삭제`}>삭제</button>
```

확인 대화 상자를 사용한다면 열 때 포커스를 옮기고, 닫을 때 원래 버튼으로 되돌립니다. 실행 취소가 가능한 작업이라면 매번 확인 창을 띄우는 대신 실행 취소를 제공하는 방법도 검토합니다.

## 흔한 실수

- 버튼의 클릭만 처리하고 폼 제출은 처리하지 않습니다.
- 클라이언트 검사를 서버 권한 검사로 간주합니다.
- 로딩과 빈 결과를 같은 화면으로 표시합니다.
- 배열 인덱스를 `key`로 사용합니다.
- 낙관적 변경 하나가 실패했을 때 전체 목록을 과거 상태로 되돌립니다.
- 오류 메시지를 입력 요소와 연결하지 않습니다.

## 완료 기준

- 입력을 제어 방식 또는 비제어 방식으로 선택한 이유를 설명합니다.
- Enter 키와 제출 버튼 모두 같은 처리 코드를 사용합니다.
- 클라이언트 검사와 서버 검사가 각각 무엇을 확인하는지 구분합니다.
- 로딩·빈 결과·성공·오류를 따로 표시합니다.
- 낙관적 변경이 실패하거나 충돌했을 때 남길 상태를 정합니다.

## 연결 exercise

[`user-directory`](../../exercises/user-directory/README.md)에서 입력 상태, 목록 식별자, 비동기 결과 표시를 다시 확인합니다.
