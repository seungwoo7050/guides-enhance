# React 폼과 목록

폼과 목록에서는 입력값 자체뿐 아니라 제출 시점, 검증 책임, 비동기 요청 상태, 항목 식별자, 키보드와 보조 기술의 동작까지 함께 다뤄야 합니다. 먼저 입력의 현재 값을 React 상태가 보유할지 DOM이 보유할지 정하고, 제출 중·성공·실패 때 어떤 화면을 보여 줄지, 서버 응답 전에 화면을 바꾸는 경우 실패한 변경을 어떻게 복구할지 정합니다.

## 목표

- 제어 입력과 비제어 입력의 차이를 설명하고 상황에 맞게 선택합니다.
- 버튼의 클릭 이벤트가 아니라 폼의 `submit`을 기준으로 제출을 처리합니다.
- 빠른 안내를 위한 클라이언트 검사와 신뢰 경계인 서버 검사를 구분합니다.
- 초기 로딩, 빈 결과, 성공, 오류와 필요하면 백그라운드 새로고침을 구분합니다.
- 목록 항목의 안정적인 식별자를 `key`로 사용합니다.
- 여러 요청이 겹쳐도 낙관적 변경을 안전하게 확정하거나 되돌립니다.

## 제어 입력

제어 입력(controlled input)은 입력 요소의 현재 값을 React의 `state`나 `props`가 결정하는 방식입니다.

```tsx
const [title, setTitle] = useState("");

<input
  id="title"
  name="title"
  value={title}
  onChange={(event) => setTitle(event.target.value)}
/>
```

위 코드에서는 다음 순서로 값이 바뀝니다.

```text
사용자가 입력
→ onChange 실행
→ setTitle로 다음 상태 요청
→ 다시 렌더링
→ 새 title이 input의 value가 됨
```

즉 DOM의 값이 독립적인 기준값이 아니라 React의 `title`이 기준값입니다. 현재 입력값을 다른 UI에 즉시 반영해야 할 때 유용합니다.

```tsx
<p>{title.length}/50</p>
```

체크박스와 라디오 버튼은 문자열 `value`가 아니라 선택 여부인 `checked`를 제어합니다.

```tsx
const [published, setPublished] = useState(false);

<input
  type="checkbox"
  checked={published}
  onChange={(event) => setPublished(event.target.checked)}
/>
```

`value`나 `checked`로 제어하면서 사용자가 값을 바꿀 수 있어야 한다면 그 변경을 반영하는 `onChange`도 필요합니다. 초기값만 주고 이후에는 브라우저가 관리하게 하려면 `defaultValue`나 `defaultChecked`를 사용합니다.

입력할 때마다 상태가 갱신되므로, 입력값을 필요로 하지 않는 큰 페이지 전체가 함께 다시 렌더링되지 않도록 상태를 가능한 한 가까운 컴포넌트에 둡니다.

## 비제어 입력

비제어 입력(uncontrolled input)은 DOM이 입력 요소의 현재 값을 보유하는 방식입니다. React는 필요할 때 `FormData`나 `ref`를 통해 값을 읽습니다.

간단한 폼이라면 제출 시점에 `FormData`로 읽을 수 있습니다.

```tsx
function handleSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();

  const data = new FormData(event.currentTarget);
  const title = String(data.get("title") ?? "").trim();

  // title을 사용해 요청합니다.
}
```

```tsx
<form onSubmit={handleSubmit}>
  <label htmlFor="title">보드 제목</label>
  <input id="title" name="title" defaultValue="" />
  <button type="submit">만들기</button>
</form>
```

`FormData`는 폼 컨트롤의 `name`을 키로 사용하므로, 서버로 보낼 입력에는 적절한 `name`이 있어야 합니다. `id`는 주로 `<label htmlFor>` 같은 요소 연결에 사용되며 `name`을 대신하지 않습니다.

비제어 입력은 다음과 같은 경우에 잘 맞습니다.

- 제출할 때만 현재 값이 필요합니다.
- 입력 도중 다른 UI가 그 값에 의존하지 않습니다.
- 기존 HTML 폼이나 DOM 중심 코드와 함께 사용합니다.
- 파일 입력처럼 브라우저가 실제 선택값을 관리하는 요소를 다룹니다.

제어 방식과 비제어 방식 중 하나가 항상 우월한 것은 아닙니다. **현재 값을 언제 읽어야 하는지**, **누가 그 값을 기준값으로 가져야 하는지**를 기준으로 선택합니다.

## 폼 제출

폼이 수행하는 작업은 `<form>`의 제출 이벤트를 기준으로 처리합니다.

```tsx
function handleSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();

  // 검증 및 요청
}

<form onSubmit={handleSubmit}>
  <label htmlFor="title">보드 제목</label>
  <input id="title" name="title" />
  <button type="submit">만들기</button>
</form>
```

브라우저의 기본 폼 제출 대신 JavaScript로 요청을 처리하려면 `event.preventDefault()`로 기본 제출을 막습니다.

제출 버튼의 `onClick`에만 로직을 넣으면 폼의 제출 동작과 로직이 분리됩니다. 사용자가 입력 필드에서 Enter로 제출하거나 다른 방식으로 폼 제출을 발생시킬 수 있으므로, 실제 제출 처리는 `onSubmit` 한곳에 둡니다.

제출 중에는 두 가지를 함께 처리합니다.

1. 사용자가 요청이 진행 중임을 알 수 있게 합니다.
2. 의도하지 않은 동일 요청을 반복해서 보내지 않게 합니다.

```tsx
const [isSubmitting, setIsSubmitting] = useState(false);

async function handleSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();

  if (isSubmitting) return;

  setIsSubmitting(true);

  try {
    const data = new FormData(event.currentTarget);
    await createBoard(data);
  } finally {
    setIsSubmitting(false);
  }
}
```

```tsx
<button type="submit" disabled={isSubmitting}>
  {isSubmitting ? "만드는 중…" : "만들기"}
</button>
```

UI에서 중복 제출을 막는 것과 서버에서 중복 요청을 안전하게 처리하는 것은 별개의 문제입니다. 결제처럼 중복 실행의 비용이 큰 작업은 서버 쪽에서도 중복 요청을 어떻게 처리할지 정해야 합니다.

## 클라이언트 검사와 서버 검사를 구분합니다

클라이언트 검증은 사용자가 잘못된 입력을 빠르게 고치도록 돕기 위한 것입니다.

예를 들어 다음 조건은 브라우저나 클라이언트 코드에서 바로 확인할 수 있습니다.

- 필수값이 비어 있는가
- 문자열 길이가 허용 범위인가
- 이메일이나 날짜가 요구하는 형식에 맞는가
- 두 입력값이 서로 일치하는가

HTML 자체의 검증 기능도 사용할 수 있습니다.

```tsx
<input
  id="title"
  name="title"
  required
  minLength={2}
  maxLength={50}
/>
```

그러나 클라이언트 검증 결과를 신뢰 경계로 사용해서는 안 됩니다. 클라이언트 코드는 우회할 수 있고 요청 자체를 직접 만들 수도 있으므로 서버는 필요한 규칙을 다시 검사해야 합니다.

서버에서 확인해야 하는 예는 다음과 같습니다.

- 사용자가 이 작업을 수행할 권한이 있는가
- 같은 이름이나 식별자가 이미 존재하는가
- 요청한 대상이 아직 존재하는가
- 현재 서버 데이터의 버전과 충돌하지 않는가
- 저장 전에 적용해야 하는 도메인 규칙을 만족하는가

따라서 클라이언트 검사는 **빠른 피드백**, 서버 검사는 **최종 판정**을 담당합니다.

## 입력 오류를 필드와 연결합니다

오류 메시지는 시각적으로 가까이 두는 것뿐 아니라 어느 입력의 오류인지 프로그램적으로도 연결합니다.

```tsx
<label htmlFor="title">보드 제목</label>
<input
  id="title"
  name="title"
  aria-invalid={error ? true : undefined}
  aria-describedby={error ? "title-error" : undefined}
/>
{error ? <p id="title-error">{error}</p> : null}
```

여기서 역할은 다음과 같습니다.

- `<label htmlFor="title">`은 필드의 이름을 입력 요소와 연결합니다.
- `aria-invalid`는 검증에 실패한 필드임을 나타냅니다.
- `aria-describedby`는 입력 요소와 구체적인 오류 설명을 연결합니다.

아직 검증하지 않았거나 오류가 없다면 `aria-invalid="true"`로 표시하지 않습니다.

여러 필드가 실패한 뒤 제출이 중단되었다면 첫 오류 필드로 포커스를 옮기는 것이 도움이 될 수 있습니다. 반대로 사용자가 글자를 입력할 때마다 포커스를 강제로 이동하면 현재 작업을 방해할 수 있으므로 피합니다.

서버가 필드별 오류를 반환한다면 서버의 필드 식별자를 폼의 입력과 연결할 수 있는 구조로 변환합니다.

```ts
type FieldErrors = {
  title?: string;
  description?: string;
};
```

폼 전체에 해당하는 오류와 특정 필드 오류도 구분합니다. 예를 들어 네트워크 실패는 특정 입력 하나의 오류가 아닐 수 있습니다.

## 목록의 비동기 상태를 나눕니다

목록 요청에서 최소한 다음 상태는 의미가 다릅니다.

```text
아직 결과가 없음 + 요청 중
정상 응답 + 항목 0개
정상 응답 + 항목 있음
요청 실패
```

예를 들어 상태를 다음처럼 명시적으로 표현할 수 있습니다.

```tsx
type BoardListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; items: Board[]; refreshing: boolean };
```

렌더링도 각 상태의 의미에 맞게 나눕니다.

```tsx
if (state.status === "loading") {
  return <p role="status">불러오는 중입니다.</p>;
}

if (state.status === "error") {
  return <p role="alert">{state.message}</p>;
}

if (state.items.length === 0) {
  return <p>표시할 항목이 없습니다.</p>;
}
```

`loading`과 빈 목록은 다릅니다.

- `loading`: 아직 성공 응답의 결과를 알 수 없습니다.
- 빈 목록: 요청은 성공했고 결과가 `[]`임을 알고 있습니다.

기존 목록을 이미 보여 주고 있는 상태에서 다시 가져오는 요청은 초기 로딩과도 다릅니다. 이때 목록 전체를 없애고 로딩 화면으로 바꾸기보다 기존 데이터를 유지한 채 `refreshing` 같은 상태로 새로고침 중임을 표시할 수 있습니다.

오류가 발생했을 때도 기존에 성공적으로 받은 데이터가 있다면 반드시 모두 숨겨야 하는 것은 아닙니다. 화면 요구사항에 따라 기존 목록을 유지하면서 “새로고침 실패”를 별도로 알릴 수 있습니다.

## 항목 식별자와 `key`

목록의 `key`는 React가 이전 렌더링의 항목과 다음 렌더링의 항목을 연결하는 데 사용하는 식별자입니다.

```tsx
{boards.map((board) => (
  <BoardCard key={board.id} board={board} />
))}
```

좋은 `key`는 다음 조건을 만족합니다.

- 같은 형제 목록 안에서 유일합니다.
- 항목의 순서가 바뀌어도 같은 항목이면 같은 값을 유지합니다.
- 렌더링할 때마다 새로 만들지 않습니다.

정렬·삽입·삭제가 가능한 목록에 배열 인덱스를 사용하면 항목의 위치가 바뀔 때 React가 서로 다른 항목을 같은 항목으로 연결할 수 있습니다. 그 결과 카드 내부의 입력값, 선택 상태, 포커스 같은 UI 상태가 다른 항목에 붙은 것처럼 보일 수 있습니다.

다음처럼 렌더링할 때 임의의 값을 만들면 안 됩니다.

```tsx
// 피합니다.
{boards.map((board) => (
  <BoardCard key={crypto.randomUUID()} board={board} />
))}
```

이 값은 렌더링할 때마다 달라지므로 React는 기존 항목을 이어서 사용하는 대신 새 항목으로 취급합니다.

서버 ID가 아직 없는 임시 항목이라면 **항목을 생성하는 시점에** 클라이언트 ID를 한 번 만들고 그 ID를 유지합니다.

```tsx
const optimisticBoard: Board = {
  id: crypto.randomUUID(),
  title,
  pending: true,
};
```

`key`는 React가 자체적으로 사용하는 값이므로 컴포넌트의 일반 `props`로 전달되지 않습니다. 컴포넌트 안에서도 ID가 필요하면 별도의 `id`나 객체 필드로 전달합니다.

## 낙관적 변경

낙관적 변경(optimistic update)은 서버 성공 응답을 기다리기 전에 성공할 것이라고 가정하고 UI를 먼저 바꾸는 방식입니다. 체감 응답 속도는 좋아지지만, 요청 실패나 동시 요청이 있을 때 어떤 상태가 남아야 하는지 먼저 정해야 합니다.

항목 추가라면 흐름을 다음처럼 설계할 수 있습니다.

```text
현재 확정 목록
→ 클라이언트 ID와 작업 ID를 가진 임시 항목 추가
→ 요청 전송
→ 성공: 서버가 반환한 확정 항목으로 해당 임시 항목 교체
→ 실패: 해당 작업의 임시 항목만 제거하거나 실패 상태로 표시
```

여기서 두 식별자의 역할을 구분하면 안전합니다.

- **항목 ID**: 화면에서 같은 항목을 계속 식별하고 `key`로 사용할 값
- **작업 ID**: 여러 추가·수정·삭제 요청 중 어떤 요청이 성공하거나 실패했는지 식별할 값

예를 들어 동시에 두 항목을 추가했다고 가정합니다.

```text
A 추가 요청 전송
B 추가 요청 전송
B 성공
A 실패
```

A를 보낼 때의 전체 배열을 저장해 두었다가 A 실패 시 통째로 복원하면 이미 성공한 B까지 사라질 수 있습니다. 따라서 실패한 **작업에 해당하는 변경만** 제거하거나 되돌려야 합니다.

간단한 구조는 다음과 같습니다.

```ts
type PendingBoard = {
  clientId: string;
  operationId: string;
  title: string;
  status: "pending" | "failed";
};
```

성공 시 서버가 새로운 ID나 정규화된 값을 반환할 수 있으므로, 임시 값을 무조건 그대로 확정하지 말고 서버 응답을 기준으로 확정 상태를 갱신합니다.

충돌 응답을 사용하는 API라면 단순 재시도보다 최신 서버 상태와 사용자의 변경을 비교해야 할 수 있습니다. 예를 들어 API가 `409 Conflict`를 사용한다면 최신 값을 다시 읽고, 사용자의 초안을 유지한 채 재적용할지 선택하도록 만들 수 있습니다. 실제 충돌 상태 코드와 복구 규칙은 해당 API의 계약을 따릅니다.

낙관적 변경이 모든 작업에 적합한 것은 아닙니다. 실패 가능성이 높거나 잘못된 성공 표시의 비용이 큰 작업이라면 서버 확인 뒤 화면을 바꾸는 편이 낫습니다.

## 삭제와 확인

삭제 버튼은 “무엇을 삭제하는지” 알 수 있는 접근 가능한 이름을 가져야 합니다.

```tsx
<button
  type="button"
  aria-label={`${board.title} 삭제`}
  onClick={() => deleteBoard(board.id)}
>
  삭제
</button>
```

폼 안에 있는 버튼은 의도하지 않은 제출을 일으키지 않도록 제출용이 아니라면 `type="button"`을 명시하는 것이 안전합니다.

확인 대화 상자를 사용한다면 키보드 사용자가 현재 위치를 잃지 않도록 포커스 이동도 함께 설계합니다.

```text
삭제 버튼에서 대화 상자 열기
→ 대화 상자 안의 적절한 요소로 포커스 이동
→ 확인 또는 취소
→ 닫은 뒤 가능한 경우 원래 삭제 버튼으로 포커스 복귀
```

삭제 직후 쉽게 복구할 수 있는 작업이라면 매번 확인 대화 상자를 띄우는 대신 삭제 후 “실행 취소”를 제공하는 방법도 고려할 수 있습니다. 중요한 것은 확인 창의 유무 자체가 아니라 실수했을 때의 비용과 복구 가능성을 기준으로 선택하는 것입니다.

## 흔한 실수

- 제어 입력에 `value`나 `checked`를 주고 사용자 변경을 반영할 `onChange`를 제공하지 않습니다.
- `FormData`로 읽을 입력에 `name`을 빠뜨립니다.
- 버튼의 `onClick`에만 제출 로직을 넣고 폼의 `submit`은 처리하지 않습니다.
- 클라이언트 검사를 서버 권한·무결성 검사의 대체물로 간주합니다.
- 오류 메시지를 해당 입력과 프로그램적으로 연결하지 않습니다.
- 초기 로딩과 정상적인 빈 결과를 같은 상태로 취급합니다.
- 정렬·삽입·삭제되는 목록의 `key`로 배열 인덱스를 사용합니다.
- 렌더링 중 `Math.random()`이나 `crypto.randomUUID()`로 `key`를 새로 만듭니다.
- 낙관적 변경 하나가 실패했을 때 전체 목록을 과거 스냅샷으로 되돌립니다.
- 서버가 반환한 확정 데이터를 반영하지 않고 임시 값을 그대로 유지합니다.

## 완료 기준

- 제어 입력에서는 React 값이, 비제어 입력에서는 DOM 값이 현재 값의 기준이라는 점을 설명합니다.
- `FormData`에서 `name`이 어떤 역할을 하는지 설명합니다.
- Enter 키와 제출 버튼 등 폼 제출 경로가 같은 `onSubmit` 처리로 모이게 합니다.
- 클라이언트 검증은 빠른 피드백이고 서버 검증은 최종 판정이라는 점을 구분합니다.
- 오류 메시지를 해당 필드와 연결하고 필요한 경우 제출 후 첫 오류로 포커스를 이동합니다.
- 초기 로딩·빈 결과·성공·오류와 필요한 경우 백그라운드 새로고침을 구분합니다.
- 목록에서 렌더링 사이에도 유지되는 안정적인 식별자를 `key`로 사용합니다.
- 낙관적 변경이 실패하거나 충돌했을 때 해당 작업만 복구할 수 있습니다.

## 연결 exercise

[`user-directory`](../../exercises/user-directory/README.md)에서 입력 상태, 목록 식별자, 비동기 결과 표시를 다시 확인합니다.
