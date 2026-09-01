# User Directory

React로 검색 상태를 관리하고 Next.js App Router로 프로필 경로를 제공하는 사용자 디렉터리입니다.

이 프로젝트는 두 가지 문제를 집중적으로 다룹니다.

```text
빠르게 바뀌는 검색어
→ 이전 비동기 요청이 최신 화면을 덮어쓰지 않게 함

프로필 화면
→ 브라우저 메모리가 아니라 URL만으로 직접 접근 가능하게 함
```

검색어가 바뀌면 이전 요청을 취소하고, 로딩·오류·빈 결과·성공 상태를 서로 다른 UI 상태로 표현합니다.

## 주요 기능

- 제어 입력으로 표시 이름과 검색어 관리
- `loading | success | error` 유니언으로 요청 상태 제한
- Effect 정리 함수에서 이전 검색 요청 취소
- 로딩, 오류, 빈 결과와 목록을 따로 표시
- 사용자 ID를 React `key`로 사용
- `/profile/[handle]` 동적 서버 경로
- 한국어 문서 언어와 메타데이터

## 설치와 실행

```sh
npm install
npm run dev
```

프로덕션 상태를 확인하려면 다음 명령을 실행합니다.

```sh
npm run typecheck
npm run build
npm start
```

각 명령의 역할은 다릅니다.

```text
dev
→ 개발 서버에서 빠른 확인

typecheck
→ 정적 TypeScript 오류 확인

build
→ Next.js 프로덕션 컴파일과 서버/클라이언트 경계 확인

start
→ 생성된 프로덕션 빌드 실제 실행
```

개발 서버가 정상이라고 해서 프로덕션 빌드까지 반드시 성공하는 것은 아니므로 `build`를 별도로 확인합니다.

## 제어 입력

검색 입력은 React 상태가 현재 표시값을 결정하는 제어 입력입니다.

개념적으로:

```tsx
<input
  value={query}
  onChange={event => setQuery(event.target.value)}
/>
```

따라서 화면에 보이는 검색어와 React가 알고 있는 검색어를 별도의 독립 값으로 두지 않습니다.

## 요청 상태 유니언

로딩과 오류를 여러 불리언으로 관리하면 모순된 조합이 생길 수 있습니다.

예:

```text
isLoading = true
hasError = true
```

이 상태가 실제로 허용되는지 매번 해석해야 합니다.

프로젝트는 다음처럼 판별 가능한 상태를 사용합니다.

```text
loading
success
error
```

이 구조에서는 한 요청이 동시에 `loading`과 `error`인 상태를 표현하지 못합니다.

`success` 안에서도 결과 배열이 비어 있으면 빈 결과 UI를 별도로 보여 줄 수 있습니다.

```text
loading
error
success + users.length === 0
success + users.length > 0
```

즉 "빈 결과"는 요청 실패가 아니라 성공적으로 검색했지만 일치하는 데이터가 없는 상태입니다.

## 검색 요청 취소

사용자가 검색어를 빠르게 바꾸면 이전 요청이 나중에 끝날 수 있습니다.

예:

```text
query=a
→ request A 시작

query=beta
→ request B 시작

request B 완료
→ beta 결과 표시

request A 완료
→ 잘못 처리하면 a 결과가 beta를 덮음
```

이 프로젝트는 Effect가 다시 실행될 때 이전 Effect에서 만든 `AbortController`를 정리합니다.

개념적인 흐름:

```text
query 변경
→ Effect 실행
→ AbortController 생성
→ search(query, signal)

query 다시 변경
→ 이전 Effect cleanup
→ previous controller.abort()
→ 새 Effect 시작
```

따라서 이전 요청이 늦게 완료되어 최신 검색 결과를 덮는 일을 막습니다.

## Effect cleanup의 의미

Effect cleanup은 컴포넌트가 완전히 사라질 때만 실행되는 것이 아닙니다. dependency가 바뀌어 Effect를 다시 실행하기 전에도 이전 cleanup이 실행됩니다.

이 프로젝트에서는 그 성질을 이용합니다.

```text
query="a" Effect
→ request A

query="beta"로 변경
→ request A Effect cleanup
→ A abort
→ request B Effect 시작
```

이 흐름을 이해해야 "왜 검색어가 바뀔 때 이전 요청이 취소되는가"가 명확해집니다.

## 취소와 실제 오류를 구분합니다

이전 검색을 의도적으로 abort한 것은 사용자에게 보여 줄 서버 오류와 같은 의미가 아닙니다.

따라서 요청 코드에서는:

```text
AbortError
→ 이전 요청 정리
→ 일반 오류 UI로 만들지 않음

실제 검색 실패
→ error 상태
→ 오류 UI 표시
```

처럼 구분해야 합니다.

## 테스트 가능한 검색 adapter

검색 지연과 실패는 UI 파일 바깥의 `lib/fake-api.ts`에 있습니다.

이 분리의 목적:

```text
UI
→ 상태 전이와 화면 표시 책임

fake API
→ 지연, 결과, 오류, 취소 재현
```

테스트에서는 실제 시간을 무작정 기다리기보다 adapter의 동작을 독립적으로 확인할 수 있습니다.

## 테스트

```sh
npm run test:adapter
```

의존성 설치 없이 가짜 검색 API의 다음 동작을 확인합니다.

- 빈 검색어의 전체 목록
- 공백과 대소문자 정리
- 정해 둔 오류 전달
- `AbortSignal`로 이전 요청 취소

화면과 동적 경로는 의존성을 설치한 뒤 프로덕션 빌드와 브라우저에서 확인합니다.

즉 adapter 테스트가 통과했다고 다음까지 자동으로 증명되지는 않습니다.

```text
React 화면이 올바른 상태를 표시함
프로필 경로가 빌드됨
직접 URL 접근이 성공함
브라우저 이벤트가 정상임
```

각 검사는 서로 다른 범위를 가집니다.

## 리스트의 `key`

검색 결과 목록에서는 사용자 ID를 React `key`로 사용합니다.

```text
key = user.id
```

배열 index를 key로 쓰면 정렬, 필터링, 삽입과 삭제 시 React가 항목 정체성을 잘못 연결할 수 있습니다.

사용자 ID처럼 데이터의 안정적인 식별자를 사용해야 같은 사용자를 같은 항목으로 인식할 수 있습니다.

## 동적 프로필 경로

프로필 페이지는 다음 경로를 사용합니다.

```text
/profile/[handle]
```

예:

```text
/profile/alpha
```

이 페이지는 이전 화면에서 넘겨 준 브라우저 메모리 상태에 의존하지 않습니다.

즉 다음 접근이 가능해야 합니다.

```text
주소창에 /profile/alpha 직접 입력
→ 서버가 URL의 handle을 읽음
→ 프로필 페이지 렌더링
```

이 성질은 새로고침, 북마크와 링크 공유에 중요합니다.

## 내부 이동과 직접 접근은 다릅니다

클라이언트에서 링크를 눌러 이동하는 경로만 확인하면 다음 문제를 놓칠 수 있습니다.

```text
앱 내부 링크 이동
→ 성공

새 탭에서 /profile/alpha 직접 접근
→ 실패
```

따라서 동적 경로는 프로덕션 빌드 후 브라우저에서 직접 URL을 열어 확인하는 것이 중요합니다.

## 문서 언어와 메타데이터

루트 layout은 한국어 문서 언어와 메타데이터를 제공합니다.

문서 언어는 브라우저와 보조 기술이 콘텐츠 언어를 이해하는 데 사용됩니다.

메타데이터는 페이지 제목과 설명 같은 문서 수준 정보를 관리합니다.

이 정보는 개별 검색 결과 상태와 별개로 앱 전체 shell의 책임입니다.

## 코드 구성

- `app/layout.tsx`: 문서 언어와 메타데이터
- `lib/fake-api.ts`: 지연, 오류와 취소를 재현하는 검색 함수
- `app/page.tsx`: 검색어, 요청 상태와 화면 출력
- `app/profile/[handle]/page.tsx`: URL의 사용자 이름을 읽는 서버 페이지

## 주요 선택

- 여러 불리언 값 대신 판별 가능한 유니언을 사용해 로딩과 오류가 동시에 참인 상태를 만들지 않습니다.
- 검색어가 바뀌면 이전 Effect가 만든 `AbortController`를 취소합니다. 늦게 끝난 이전 요청이 최신 목록을 덮지 않습니다.
- 검색 지연과 실패는 UI 파일 밖에 두어 테스트에서 독립적으로 재현합니다.
- 프로필 페이지는 브라우저 메모리 상태에 의존하지 않아 URL을 직접 열어도 동작합니다.
- 안정적인 사용자 ID를 React list key로 사용해 필터링과 재정렬에서도 항목 정체성을 유지합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Root document metadata | `app/layout.tsx` |
| 2 | Abortable search adapter | `lib/fake-api.ts` |
| 3 | Request-state union | `app/page.tsx` |
| 4 | Search cancellation on query change | `app/page.tsx` |
| 5 | Loading, error, empty, and result rendering | `app/page.tsx` |
| 6 | Server-rendered profile route | `app/profile/[handle]/page.tsx` |

먼저 독립적으로 테스트 가능한 검색 adapter와 상태 모델을 만든 뒤 UI를 연결하고, 마지막에 URL만으로 직접 접근 가능한 서버 경로를 추가합니다.

## 범위와 제한

사용자 데이터는 메모리에 고정되어 있습니다. 실제 HTTP 서버, 인증, 페이지네이션, 캐시와 프로필 저장 기능은 포함하지 않습니다. 검색어 `error`는 오류 화면을 확인하기 위한 입력입니다.

따라서 이 프로젝트의 검색 API는 실제 네트워크 검색 서비스가 아니라 다음 비동기 UI 문제를 재현하기 위한 adapter입니다.

```text
지연
실패
취소
응답 순서 역전
```
