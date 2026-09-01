# Next.js 라우팅과 렌더링

Next.js App Router에서는 파일과 디렉터리 구조가 URL 경로를 만들고, 같은 컴포넌트 트리 안에서도 서버에서만 실행되는 코드와 브라우저에서도 실행되는 코드가 섞일 수 있습니다.

여기서 반드시 구분해야 하는 것은 다음 두 가지입니다.

```text
Server Component / Client Component
→ 코드가 어느 환경의 기능을 사용할 수 있는가

정적 렌더링 / 요청 시 렌더링
→ 경로의 결과를 언제 만드는가
```

Server Component라고 해서 반드시 매 요청마다 실행되는 것은 아니며, Client Component라고 해서 최초 페이지 로드 때 서버가 HTML을 전혀 만들지 않는 것도 아닙니다. 이 구분을 잘못 이해하면 비밀값이 노출되거나, 서버에서 브라우저 API를 읽어 오류가 나거나, hydration 시 서버 HTML과 브라우저의 첫 렌더링이 달라질 수 있습니다.

## 목표

- `app/` 디렉터리 구조로 정적 경로와 동적 경로를 만듭니다.
- `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, `not-found.tsx`의 역할을 구분합니다.
- Server Component와 Client Component의 실행 환경과 경계를 설명합니다.
- 서버 비밀값과 브라우저 API를 올바른 위치에서 사용합니다.
- 서버에서 Client Component로 전달할 데이터 경계를 명확히 만듭니다.
- 서버가 만든 초기 HTML과 브라우저의 첫 렌더링을 일치시킵니다.
- 링크 이동뿐 아니라 동적 URL 직접 접근과 프로덕션 빌드도 확인합니다.

## 파일과 디렉터리로 경로를 만듭니다

App Router는 `app/` 아래의 디렉터리를 URL의 **route segment**로 사용합니다.

```text
app/
├── layout.tsx
├── page.tsx
├── loading.tsx
├── error.tsx
├── not-found.tsx
└── boards/
    └── [id]/
        └── page.tsx
```

위 구조에서 공개적으로 접근 가능한 페이지는 다음과 같습니다.

```text
app/page.tsx
→ /

app/boards/[id]/page.tsx
→ /boards/<id>
```

예를 들어 다음 주소는 `[id]`가 `"42"`인 동적 경로입니다.

```text
/boards/42
```

디렉터리를 만들었다고 해서 그 자체가 브라우저에서 접근 가능한 페이지가 되는 것은 아닙니다. 일반적으로 해당 segment에 `page.tsx`가 있어야 페이지 경로가 공개됩니다.

## 동적 경로와 `params`

대괄호로 감싼 디렉터리 이름은 동적 segment입니다.

```text
app/
└── boards/
    └── [id]/
        └── page.tsx
```

현재 App Router에서 페이지의 `params`는 Promise로 전달되므로 `await`해서 읽습니다.

```tsx
type Props = {
  params: Promise<{ id: string }>;
};

export default async function BoardPage({ params }: Props) {
  const { id } = await params;
  const board = await loadBoard(id);

  return <h1>{board.title}</h1>;
}
```

URL에서 들어온 값은 신뢰할 수 있는 내부 값이 아닙니다. 사용자는 주소창에 임의의 문자열을 입력할 수 있으므로 필요한 형식과 존재 여부를 검사합니다.

```tsx
import { notFound } from "next/navigation";

export default async function BoardPage({ params }: Props) {
  const { id } = await params;

  if (!isValidBoardId(id)) {
    notFound();
  }

  const board = await loadBoard(id);

  if (!board) {
    notFound();
  }

  return <h1>{board.title}</h1>;
}
```

링크를 통해 정상적인 값만 전달한다고 가정해서는 안 됩니다. `/boards/42`를 주소창에서 직접 열거나 새로고침해도 같은 결과가 나와야 합니다.

## 루트 레이아웃

App Router에는 애플리케이션 전체를 감싸는 루트 레이아웃이 필요합니다.

```tsx
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

루트 레이아웃에는 `<html>`과 `<body>` 같은 공통 문서 구조를 둡니다. 중첩된 디렉터리에 `layout.tsx`를 추가하면 해당 경로 하위에서만 공유하는 UI를 만들 수 있습니다.

```text
app/
├── layout.tsx
└── boards/
    ├── layout.tsx
    └── [id]/
        └── page.tsx
```

이 경우 `app/boards/layout.tsx`는 `/boards/...` 하위 UI를 감쌉니다.

모든 Provider와 상호작용 상태를 루트 레이아웃에 몰아넣을 필요는 없습니다. Client Component가 필요한 Provider라면 가능한 한 실제로 필요한 하위 트리 가까이에 두어 불필요하게 큰 클라이언트 경계를 만들지 않습니다.

## 기본은 Server Component입니다

App Router의 `page.tsx`와 `layout.tsx`는 기본적으로 Server Component입니다.

```tsx
type Props = {
  params: Promise<{ id: string }>;
};

export default async function BoardPage({ params }: Props) {
  const { id } = await params;
  const board = await loadBoard(id);

  return <BoardView board={board} />;
}
```

Server Component에서는 서버에서만 안전하게 수행할 수 있는 작업을 할 수 있습니다.

- 데이터베이스 접근
- 서버 전용 파일이나 내부 서비스 접근
- 비공개 환경 변수 사용
- 서버 가까이에서 데이터 요청
- 브라우저로 보내지 않아도 되는 코드 실행

반면 Server Component에서는 브라우저 상호작용을 위한 기능을 직접 사용할 수 없습니다.

```text
useState
useEffect
onClick 같은 이벤트 처리기
window
document
localStorage
navigator
```

예를 들어 다음 코드는 Server Component에서 사용할 수 없습니다.

```tsx
// Server Component에서는 사용할 수 없습니다.
export default function Page() {
  const [open, setOpen] = useState(false);

  return <button onClick={() => setOpen(true)}>열기</button>;
}
```

상호작용이 필요한 부분만 Client Component로 분리합니다.

## `"use client"`는 클라이언트 경계를 만듭니다

Client Component가 필요한 파일의 맨 위에 `"use client"`를 둡니다.

```tsx
"use client";

import { useState } from "react";

export function BoardFilter() {
  const [query, setQuery] = useState("");

  return (
    <input
      value={query}
      onChange={(event) => setQuery(event.target.value)}
    />
  );
}
```

Client Component가 필요한 대표적인 경우는 다음과 같습니다.

- `useState`, `useReducer` 같은 상태 Hook
- `useEffect` 같은 수명 주기 로직
- `onClick`, `onChange` 같은 이벤트 처리
- `window`, `localStorage`, `navigator` 같은 브라우저 API
- 위 기능을 사용하는 커스텀 Hook

`"use client"`는 모든 Client Component 파일에 반복해서 붙이는 표지가 아닙니다. 이 지시어가 있는 파일이 **서버 모듈 그래프와 클라이언트 모듈 그래프 사이의 경계**가 됩니다.

```text
Server Component
└── BoardView
    ├── BoardHeader
    └── BoardFilter   ← "use client"
        ├── FilterInput
        └── FilterButton
```

`BoardFilter`가 `"use client"` 경계라면 그 파일이 정적으로 import하는 모듈들도 클라이언트 번들의 일부가 될 수 있습니다. 따라서 경계 안에서 데이터베이스 모듈, 서버 비밀 설정, Node.js 전용 코드 등을 import하지 않습니다.

## Client Component도 최초 로드에서 서버 HTML에 참여할 수 있습니다

Client Component라는 이름 때문에 “이 컴포넌트는 서버에서는 전혀 렌더링되지 않는다”고 이해하면 안 됩니다.

최초 전체 페이지 로드에서는 개념적으로 다음 과정이 일어납니다.

```text
서버:
Server Component 렌더링
+ Client Component를 포함한 초기 HTML 미리 렌더링
+ RSC Payload와 필요한 클라이언트 JavaScript 준비

브라우저:
초기 HTML 표시
→ RSC 결과와 컴포넌트 트리 연결
→ Client Component JavaScript 실행
→ hydration으로 이벤트 처리 활성화
```

따라서 Client Component의 렌더링 코드도 최초 페이지 로드에서는 서버 환경에서 평가될 수 있습니다. 다음처럼 렌더링 중 `window`를 직접 읽으면 문제가 됩니다.

```tsx
"use client";

// 피합니다.
export function Width() {
  return <p>{window.innerWidth}px</p>;
}
```

브라우저 API가 필요하다는 이유만으로 `"use client"`를 추가하면 서버 렌더링 문제까지 자동으로 사라지는 것은 아닙니다.

## Server Component와 렌더링 시점은 다른 개념입니다

Server Component는 **서버 환경에서 실행되는 컴포넌트 종류**를 뜻합니다. 이것이 곧 “매 HTTP 요청마다 서버에서 새로 렌더링된다”는 뜻은 아닙니다.

경로는 사용하는 데이터와 Next.js 설정에 따라 미리 렌더링되거나 요청 시점에 렌더링될 수 있습니다.

```text
Server Component
├── 빌드나 재검증 과정에서 미리 렌더링될 수 있음
└── 요청 시점에 렌더링될 수도 있음
```

따라서 다음 두 질문을 별도로 해야 합니다.

```text
이 코드는 서버와 브라우저 중 어디에서 실행 가능한가?
이 경로의 결과는 빌드 시점과 요청 시점 중 언제 만들어지는가?
```

이 문서에서는 첫 번째 질문인 Server/Client Component 경계와 초기 렌더링 일치에 집중합니다.

## 서버 비밀값은 서버 경계 안에 둡니다

비공개 API 키, 데이터베이스 접속 정보, 내부 토큰은 Client Component로 가져오지 않습니다.

```ts
// lib/boards.ts
import "server-only";

export async function loadBoard(id: string) {
  const databaseUrl = process.env.DATABASE_URL;

  // 서버 전용 데이터 접근
}
```

`server-only`로 서버 전용 모듈을 표시하면 Client Component에서 실수로 import했을 때 잘못된 경계를 더 일찍 발견할 수 있습니다.

Next.js에서 일반 환경 변수는 기본적으로 서버 쪽에서 사용합니다. `NEXT_PUBLIC_` 접두사가 붙은 환경 변수는 클라이언트 번들에서 사용할 목적으로 공개되는 값이므로 비밀값을 넣으면 안 됩니다.

```text
DATABASE_URL
→ 서버 비밀값

NEXT_PUBLIC_API_BASE_URL
→ 브라우저에도 공개되어도 되는 값
```

중요한 원칙은 단순합니다.

> Client Component에 포함될 수 있는 코드는 사용자가 받아 볼 수 있는 코드라고 가정합니다.

## 서버에서 Client Component로 전달하는 값을 제한합니다

Server Component는 Client Component에 props를 전달할 수 있습니다.

```tsx
export default async function BoardPage({ params }: Props) {
  const { id } = await params;
  const board = await loadBoard(id);

  const initialBoard: BoardInitialData = {
    id: board.id,
    title: board.title,
    updatedAt: board.updatedAt.toISOString(),
  };

  return <BoardEditor initialBoard={initialBoard} />;
}
```

```ts
type BoardInitialData = {
  id: string;
  title: string;
  updatedAt: string;
};
```

서버에서 Client Component로 넘기는 props는 React가 직렬화할 수 있어야 합니다. 또한 **직렬화 가능하다는 것과 브라우저에 보내도 안전하다는 것은 별개**입니다.

예를 들어 다음 값은 그대로 전달하지 않습니다.

- 데이터베이스 연결 객체
- ORM 클라이언트
- 서버 전용 서비스 객체
- 일반 함수
- 비밀 토큰
- 사용자에게 공개하면 안 되는 내부 필드

필요한 필드만 뽑은 명확한 데이터 계약을 만드는 것이 안전합니다.

```tsx
// 피합니다.
return <BoardEditor board={rawDatabaseRecord} />;

// 권장
return (
  <BoardEditor
    initialBoard={{
      id: board.id,
      title: board.title,
      updatedAt: board.updatedAt.toISOString(),
    }}
  />
);
```

날짜를 반드시 문자열로만 전달해야 한다는 뜻은 아닙니다. 다만 서버와 브라우저 사이의 데이터 계약을 명확히 하고 API·저장소와도 일관된 표현을 사용하려면 ISO 8601 문자열처럼 명시적인 형태가 이해하기 쉽습니다.

## Server Component에 이벤트 함수를 전달하지 않습니다

일반적인 서버 함수 객체를 Client Component의 이벤트 handler prop으로 넘길 수는 없습니다.

```tsx
// 이런 일반 함수 전달을 기대하지 않습니다.
export default function Page() {
  function handleClick() {
    // ...
  }

  return <ClientButton onClick={handleClick} />;
}
```

브라우저의 클릭 이벤트는 Client Component 내부에서 처리합니다.

```tsx
"use client";

export function ClientButton() {
  function handleClick() {
    // 브라우저 상호작용
  }

  return <button onClick={handleClick}>실행</button>;
}
```

서버에서 수행해야 하는 변경 작업은 Server Action 같은 별도의 서버 호출 경계를 사용할 수 있지만, 그것은 “임의의 서버 함수가 자동으로 브라우저에 전달된다”는 의미가 아닙니다.

## hydration은 Client Component의 초기 결과를 맞추는 과정입니다

최초 페이지 로드에서 서버가 만든 HTML을 브라우저에서 React가 상호작용 가능한 UI로 연결하는 과정을 hydration이라고 합니다.

서버의 초기 HTML과 브라우저의 첫 렌더링 결과가 다르면 hydration mismatch가 발생할 수 있습니다.

예를 들어 다음 값은 서버와 브라우저에서 서로 다른 결과가 나오기 쉽습니다.

- 현재 시각
- 난수
- `localStorage`
- 브라우저 창 크기
- 브라우저에만 있는 API 값
- 서버와 브라우저의 환경 차이에 영향을 받는 포맷 결과

다음 코드는 렌더링할 때마다 값이 바뀔 수 있습니다.

```tsx
// 피합니다.
export function CreatedNow() {
  return <p>{Date.now()}</p>;
}
```

다음처럼 서버와 브라우저에서 조건을 달리해 첫 UI를 만드는 것도 피합니다.

```tsx
// 피합니다.
const isBrowser = typeof window !== "undefined";

return <p>{isBrowser ? "브라우저" : "서버"}</p>;
```

서버 렌더링 결과와 브라우저의 첫 렌더링 결과가 달라지기 때문입니다.

## 브라우저에서만 알 수 있는 값은 hydration 뒤에 읽습니다

브라우저 전용 값이 꼭 필요하다면 첫 렌더링은 서버와 브라우저가 동일하게 만들고 Effect 이후에 갱신합니다.

```tsx
"use client";

import { useEffect, useState } from "react";

export function SavedTheme() {
  const [theme, setTheme] = useState<string | null>(null);

  useEffect(() => {
    setTheme(localStorage.getItem("theme"));
  }, []);

  if (theme === null) {
    return <p>기본 테마</p>;
  }

  return <p>현재 테마: {theme}</p>;
}
```

개념적인 순서는 다음과 같습니다.

```text
서버 초기 렌더링
→ "기본 테마"

브라우저 첫 렌더링
→ "기본 테마"

hydration 완료
→ Effect에서 localStorage 읽기
→ 필요한 경우 다시 렌더링
```

첫 두 결과가 같으므로 hydration이 안정적입니다.

다만 Effect를 모든 hydration 문제의 해결책처럼 사용해서는 안 됩니다. 가능하면 서버가 이미 알고 있는 값은 서버에서 결정해 props로 전달합니다.

## 결정적이지 않은 값은 서버에서 한 번 정할 수 있습니다

현재 시각이나 난수처럼 렌더링마다 바뀌는 값이 실제로 페이지의 초기 데이터라면 서버에서 한 번 계산하고 같은 값을 전달할 수 있습니다.

```tsx
export default function Page() {
  const generatedAt = new Date().toISOString();

  return <ClientTimestamp generatedAt={generatedAt} />;
}
```

```tsx
"use client";

export function ClientTimestamp({
  generatedAt,
}: {
  generatedAt: string;
}) {
  return <time dateTime={generatedAt}>{generatedAt}</time>;
}
```

이 경우 서버가 정한 하나의 값이 초기 결과의 기준이 됩니다.

## 로케일 포맷도 초기 결과가 달라질 수 있습니다

날짜와 숫자 포맷은 실행 환경의 locale이나 time zone에 따라 달라질 수 있습니다.

```tsx
// 환경에 따라 결과가 달라질 여지가 있습니다.
new Date(updatedAt).toLocaleString();
```

초기 HTML에서 반드시 같은 결과가 필요하다면 locale과 time zone을 명시하거나 서버가 포맷된 문자열을 정해서 전달합니다.

```tsx
const formatter = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  dateStyle: "medium",
  timeStyle: "short",
});
```

핵심은 서버와 브라우저가 같은 입력으로 같은 첫 결과를 만들도록 하는 것입니다.

## `loading.tsx`는 경로의 로딩 UI를 만듭니다

특정 route segment에 `loading.tsx`를 두면 해당 구간의 콘텐츠가 준비되는 동안 표시할 fallback UI를 정의할 수 있습니다.

```text
app/
└── boards/
    ├── loading.tsx
    └── [id]/
        └── page.tsx
```

```tsx
export default function Loading() {
  return <p>보드를 불러오는 중입니다.</p>;
}
```

`loading.tsx`는 React Suspense를 기반으로 해당 route segment의 로딩 UI를 구성합니다. 따라서 느린 서버 데이터 때문에 전체 화면이 아무것도 표시하지 않은 채 기다리는 대신 준비된 부분과 fallback을 단계적으로 보여 줄 수 있습니다.

로딩 UI와 “데이터가 정상적으로 0개인 상태”는 다른 상태입니다.

```text
로딩 중
→ 아직 결과를 모름

빈 결과
→ 요청 또는 조회는 성공했고 항목이 없음
```

## `error.tsx`는 예상하지 못한 렌더링 오류 경계입니다

경로에 `error.tsx`를 두면 해당 route segment 아래에서 처리되지 않은 오류가 발생했을 때 대체 UI를 제공할 수 있습니다.

```tsx
"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div>
      <p>화면을 불러오지 못했습니다.</p>
      <button onClick={() => reset()}>다시 시도</button>
    </div>
  );
}
```

`error.tsx`는 오류 상태와 `reset` 동작을 다뤄야 하므로 Client Component입니다.

하지만 사용자가 입력을 잘못했거나, 권한이 없거나, 저장 충돌이 발생한 것처럼 **예상 가능한 결과를 모두 예외로 던져 `error.tsx`에 보내는 방식**은 피합니다.

예상 가능한 실패는 해당 작업의 결과로 처리하고 사용자에게 구체적으로 안내합니다.

```text
잘못된 입력
→ 필드 오류

로그인 필요 또는 권한 부족
→ 인증/권한 흐름

존재하지 않는 리소스
→ notFound() 또는 명시적인 404 처리

버전 충돌
→ 충돌 안내와 재시도/병합 흐름

예상하지 못한 렌더링 오류
→ error.tsx
```

## `not-found.tsx`와 `notFound()`

요청한 리소스가 존재하지 않는 경우 `notFound()`를 호출해 해당 경로의 not-found UI로 보낼 수 있습니다.

```tsx
import { notFound } from "next/navigation";

export default async function BoardPage({ params }: Props) {
  const { id } = await params;
  const board = await loadBoard(id);

  if (!board) {
    notFound();
  }

  return <h1>{board.title}</h1>;
}
```

```tsx
// app/boards/[id]/not-found.tsx
export default function NotFound() {
  return <p>해당 보드를 찾을 수 없습니다.</p>;
}
```

“데이터가 없음”과 “예상하지 못한 서버 오류”를 구분하면 사용자에게 더 정확한 상태를 보여 줄 수 있습니다.

## 이동은 `Link`를 우선합니다

다른 URL로 이동하는 UI는 링크의 의미를 갖게 합니다.

```tsx
import Link from "next/link";

<Link href={`/boards/${board.id}`}>
  {board.title}
</Link>
```

링크를 사용하면 다음과 같은 브라우저 기본 동작을 유지할 수 있습니다.

- 새 탭에서 열기
- 링크 주소 복사
- 키보드와 보조 기술에서 링크로 인식
- URL을 목적지로 갖는 탐색 동작

현재 화면의 상태를 바꾸는 작업은 버튼을 사용합니다.

```tsx
<button type="button" onClick={openMenu}>
  메뉴 열기
</button>
```

기준은 모양이 아니라 의미입니다.

```text
다른 주소로 이동
→ Link

현재 화면에서 동작 실행
→ button
```

사용자 이벤트가 끝난 뒤 조건에 따라 이동해야 하는 등 명령형 탐색이 필요한 경우 Client Component에서 `useRouter`를 사용할 수 있지만, 단순한 목적지 이동은 `Link`가 우선입니다.

## 직접 URL 접근을 반드시 검사합니다

클라이언트 링크를 눌러 이동하는 것만 확인해서는 라우팅이 올바른지 충분히 검증할 수 없습니다.

다음 흐름도 확인합니다.

```text
/boards/42 주소 직접 입력
→ 페이지가 정상 표시됨

/boards/42에서 새로고침
→ 페이지가 정상 표시됨

존재하지 않는 /boards/unknown 접근
→ 의도한 not-found 또는 오류 처리

로그인이 필요한 주소 직접 접근
→ 의도한 인증 처리
```

Client Component의 메모리 상태가 미리 존재한다는 가정에 의존하면 직접 접근이나 새로고침에서 실패합니다.

경로를 다시 만드는 데 필요한 기준값은 URL, 서버 데이터, 쿠키 등 새 요청에서도 복구 가능한 위치에 있어야 합니다.

## 타입 검사와 프로덕션 빌드는 다른 검증입니다

프로젝트에 별도 타입 검사 스크립트가 있다면 타입 검사와 실제 프로덕션 빌드를 모두 실행합니다.

```sh
npm run typecheck
npm run build
```

각 검사는 찾는 문제가 다를 수 있습니다.

타입 검사는 주로 TypeScript 수준의 문제를 찾습니다.

```text
잘못된 props 타입
존재하지 않는 속성
함수 인자 타입 불일치
```

프로덕션 빌드는 실제 Next.js 애플리케이션의 서버/클라이언트 경계와 경로 생성 과정까지 포함하므로 개발 중에 드러나지 않은 문제를 발견할 수 있습니다.

예를 들면 다음과 같습니다.

- Client Component에서 서버 전용 모듈을 가져옴
- 정적 생성 과정에서만 실행되는 코드가 실패함
- 동적 경로와 빌드 시 생성 조건이 맞지 않음
- 특정 환경 변수가 프로덕션 빌드에 없음
- 서버와 클라이언트 번들 경계를 잘못 구성함

따라서 개발 서버가 열린다는 사실이나 에디터에 타입 오류가 없다는 사실만으로 완료로 판단하지 않습니다.

프로젝트의 실제 `package.json`에 `typecheck` 스크립트가 없다면 해당 프로젝트에서 정한 TypeScript 검사 명령을 사용합니다.

## 서버와 클라이언트 경계를 정할 때의 질문

컴포넌트를 작성할 때 다음 순서로 판단할 수 있습니다.

1. 데이터베이스, 비밀 토큰, 서버 전용 API가 필요한가?
2. `useState`, `useEffect`, 이벤트 처리기가 필요한가?
3. `window`, `localStorage` 같은 브라우저 API가 필요한가?
4. 상호작용이 필요한 부분만 더 작은 Client Component로 분리할 수 있는가?
5. 서버에서 클라이언트로 보내는 데이터는 필요한 필드만 포함하는가?
6. 최초 서버 HTML과 브라우저 첫 렌더링이 같은가?
7. URL을 직접 열어도 필요한 상태를 복구할 수 있는가?

일반적인 방향은 다음과 같습니다.

```text
데이터 읽기와 비밀값
→ Server Component 또는 서버 전용 모듈

상호작용과 브라우저 API
→ 필요한 최소 범위의 Client Component

서버 → 클라이언트
→ 명시적이고 안전한 데이터 props
```

## 흔한 실수

- 모든 페이지와 레이아웃에 `"use client"`를 붙입니다.
- `"use client"`가 있는 컴포넌트는 최초 로드에서도 서버에서 전혀 실행되지 않는다고 생각합니다.
- Client Component에서 데이터베이스 모듈이나 서버 비밀 설정을 import합니다.
- `NEXT_PUBLIC_` 환경 변수에 비밀값을 넣습니다.
- 서버에서 읽은 데이터 객체 전체를 필터링하지 않고 Client Component로 넘깁니다.
- Server Component에서 `window`, `document`, `localStorage`를 사용합니다.
- Client Component의 렌더링 중에 `window`나 `localStorage`를 바로 읽습니다.
- 첫 렌더링에서 현재 시각이나 난수를 직접 만들어 서버와 브라우저 결과가 달라집니다.
- `typeof window !== "undefined"` 분기로 서버와 브라우저의 첫 UI를 다르게 만듭니다.
- Server Component라는 이유만으로 해당 경로가 항상 요청 시 렌더링된다고 생각합니다.
- 존재하지 않는 동적 ID를 검증하지 않습니다.
- 예상 가능한 입력·권한·충돌 오류를 모두 `error.tsx`로 보냅니다.
- URL 이동을 버튼으로만 구현해 링크의 기본 기능을 잃습니다.
- 링크 이동만 확인하고 URL 직접 접근과 새로고침을 검사하지 않습니다.
- 타입 검사만 실행하고 프로덕션 빌드를 생략합니다.

## 완료 기준

- `app/`의 디렉터리와 `page.tsx`가 URL 경로를 어떻게 만드는지 설명합니다.
- `[id]` 같은 동적 segment를 만들고 `params`를 `await`해 읽을 수 있습니다.
- 동적 URL의 값은 외부 입력이므로 검증해야 함을 설명합니다.
- Server Component와 Client Component가 각각 사용할 수 있는 기능을 구분합니다.
- `"use client"`가 클라이언트 모듈 경계를 만든다는 점을 설명합니다.
- Client Component도 최초 로드에서는 서버의 HTML 사전 렌더링에 참여할 수 있음을 이해합니다.
- Server/Client Component 구분과 정적/요청 시 렌더링 구분을 혼동하지 않습니다.
- 서버 비밀값과 서버 전용 모듈이 클라이언트 경계를 넘어가지 않습니다.
- 서버에서 Client Component로 필요한 데이터만 안전하게 전달합니다.
- 서버 HTML과 브라우저의 첫 렌더링 결과를 일치시킵니다.
- `loading.tsx`, `error.tsx`, `not-found.tsx`의 역할을 구분합니다.
- 다른 URL로 이동할 때 `Link`, 현재 화면의 동작에는 버튼을 사용합니다.
- 동적 URL 직접 접근과 새로고침을 검사합니다.
- 타입 검사와 프로덕션 빌드를 모두 통과시킵니다.

## 연결 exercise

[`user-directory`](../../exercises/user-directory/README.md)에서 동적 프로필 경로와 브라우저 검색 상태를 함께 확인합니다.
