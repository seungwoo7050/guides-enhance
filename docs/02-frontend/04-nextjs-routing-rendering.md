# Next.js 라우팅과 렌더링

Next.js App Router의 파일은 서버에서만 실행될 수도 있고 브라우저 번들에 포함될 수도 있습니다. 실행 위치를 잘못 판단하면 비밀값이 노출되거나, 서버에서 `window`를 읽어 오류가 나거나, 처음 받은 HTML과 브라우저의 첫 렌더링이 달라질 수 있습니다.

## 목표

- `app/` 디렉터리로 페이지와 동적 경로를 만듭니다.
- Server Component와 Client Component를 구분합니다.
- 비밀값과 브라우저 API를 올바른 위치에서 사용합니다.
- 서버 HTML과 브라우저의 첫 화면을 일치시킵니다.
- 동적 URL 직접 접근과 프로덕션 빌드를 확인합니다.

## 파일로 경로를 만듭니다

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

- `app/page.tsx`는 `/`
- `app/boards/[id]/page.tsx`는 `/boards/:id`

링크로 이동하는 경우뿐 아니라 주소창에서 동적 URL을 직접 열고 새로고침해도 동작해야 합니다.

## 루트 레이아웃

```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

공통 문서 요소와 화면 틀을 둡니다. 모든 Provider와 상태를 루트에 넣어 전체 페이지를 브라우저 코드로 만들지 않습니다.

## 기본은 Server Component입니다

App Router의 컴포넌트는 기본적으로 서버에서 렌더링됩니다. 서버에서는 데이터베이스와 비공개 환경 변수를 사용할 수 있지만, `window`, `document`, 이벤트 처리기와 클라이언트 Hook은 사용할 수 없습니다.

```tsx
export default async function BoardPage({ params }: Props) {
  const { id } = await params;
  const board = await loadBoard(id);
  return <BoardView initialBoard={board} />;
}
```

서버에서 읽은 값은 직렬화 가능한 형태로 브라우저 컴포넌트에 전달합니다.

## `"use client"`는 필요한 파일에만 둡니다

```tsx
"use client";

export function BoardFilter() {
  const [query, setQuery] = useState("");
  return <input value={query} onChange={(event) => setQuery(event.target.value)} />;
}
```

이 선언이 있는 파일과 그 파일이 가져오는 모듈은 브라우저에서 실행될 수 있어야 합니다. 데이터베이스 클라이언트나 서버 비밀 설정을 가져오지 않습니다.

## 서버에서 브라우저로 전달하는 값

함수, 데이터베이스 연결, 클래스 인스턴스는 전달할 수 없습니다. 날짜는 ISO 문자열처럼 명확한 형식으로 바꿉니다.

```ts
type BoardInitialData = {
  id: string;
  title: string;
  updatedAt: string;
};
```

## hydration 결과를 맞춥니다

서버가 만든 첫 HTML과 브라우저의 첫 렌더링이 다르면 경고가 나고 화면이 교체될 수 있습니다.

첫 렌더링에서 바로 쓰기 어려운 값은 다음과 같습니다.

- `Date.now()`
- `Math.random()`
- `localStorage`
- 뷰포트 크기
- 서버와 브라우저에서 결과가 달라질 수 있는 로케일 포맷

서버가 값을 정해 전달하거나, 브라우저에서만 알 수 있는 값은 hydration이 끝난 뒤 Effect에서 읽습니다.

## 로딩과 오류 파일

`loading.tsx`, `error.tsx`, `not-found.tsx`로 경로별 상태를 표시할 수 있습니다. 입력 오류, 권한 부족, 충돌처럼 예상 가능한 결과를 모두 프레임워크 예외로 보내지는 않습니다. 해당 요청이 반환해야 할 상태와 안내를 직접 정합니다.

## 이동은 링크를 우선합니다

```tsx
<Link href={`/boards/${board.id}`}>{board.title}</Link>
```

다른 주소로 이동하는 작업은 링크로 만들면 새 탭 열기와 주소 복사 같은 브라우저 기능을 유지할 수 있습니다. 현재 화면의 상태를 바꾸는 동작에는 버튼을 사용합니다.

## 타입 검사와 빌드는 다릅니다

```sh
npm run typecheck
npm run build
```

타입 검사를 통과해도 서버 전용 모듈을 브라우저 파일에서 가져왔거나 동적 경로 생성에 문제가 있으면 프로덕션 빌드가 실패할 수 있습니다. 개발 서버가 열린다는 사실만으로 완료로 판단하지 않습니다.

## 흔한 실수

- 모든 페이지에 `"use client"`를 붙입니다.
- 브라우저 코드에서 서버 비밀값이나 데이터베이스 모듈을 가져옵니다.
- 첫 렌더링에서 현재 시각, 난수, 브라우저 저장소를 읽습니다.
- 링크 이동만 확인하고 URL 직접 접근을 검사하지 않습니다.
- 타입 검사만 실행하고 프로덕션 빌드는 생략합니다.

## 완료 기준

- 파일과 디렉터리로 정적·동적 경로를 만들 수 있습니다.
- 코드가 서버와 브라우저 중 어디에서 실행되는지 설명합니다.
- 서버 값은 직렬화 가능한 형태로 전달합니다.
- 서버 HTML과 브라우저의 첫 화면이 일치합니다.
- 동적 URL 직접 접근과 프로덕션 빌드를 통과합니다.

## 연결 exercise

[`user-directory`](../../exercises/user-directory/README.md)에서 동적 프로필 경로와 브라우저 검색 상태를 함께 확인합니다.
