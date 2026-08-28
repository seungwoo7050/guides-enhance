# User Directory

React로 검색 상태를 관리하고 Next.js App Router로 프로필 경로를 제공하는 사용자 디렉터리입니다. 사용자가 검색어를 빠르게 바꿨을 때 이전 요청을 취소하고, 로딩·오류·빈 결과·성공 화면을 서로 다르게 표시합니다.

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

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Root document metadata | `app/layout.tsx` |
| 2 | Abortable search adapter | `lib/fake-api.ts` |
| 3 | Request-state union | `app/page.tsx` |
| 4 | Search cancellation on query change | `app/page.tsx` |
| 5 | Loading, error, empty, and result rendering | `app/page.tsx` |
| 6 | Server-rendered profile route | `app/profile/[handle]/page.tsx` |

## 범위와 제한

사용자 데이터는 메모리에 고정되어 있습니다. 실제 HTTP 서버, 인증, 페이지네이션, 캐시와 프로필 저장 기능은 포함하지 않습니다. 검색어 `error`는 오류 화면을 확인하기 위한 입력입니다.
