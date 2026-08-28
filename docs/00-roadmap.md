# 학습 로드맵

이 문서는 React·Next.js 개발 트랙의 학습 순서와 완료 조건을 정리합니다. 실제 프로젝트는 이 저장소 밖에서 진행합니다. `docs/`는 프로젝트 진입 전에 읽을 최소 문서와 구현 중 찾아볼 자료를 제공하고, `exercises/`는 실제 프로젝트를 마친 뒤 역량을 확인하는 프로그램을 제공합니다.

최종 학습 순서는 다음과 같습니다.

```text
Stable Core Guide
→ Actual Project
→ JIT Guide as needed
→ Project PASS
→ Competency Suite without Guide
→ Rewind where needed
```

## 대상 독자

다음 작업을 한 번 이상 해 본 개발자를 대상으로 합니다.

- React 컴포넌트에 props를 전달하고 컴포넌트 상태를 변경했습니다.
- 폼 제출과 목록 렌더링을 구현했습니다.
- `fetch`로 JSON API를 호출하고 대기·실패 상태를 표시했습니다.
- TypeScript로 객체와 함수의 타입을 작성했습니다.
- App Router의 `page.tsx`, `layout.tsx`, Route Handler를 사용했습니다.
- 패키지 관리자의 잠금 파일을 유지하면서 기능 브랜치를 수정했습니다.

다음 항목이 익숙하지 않다면 별도의 기초 과정에서 먼저 보완해야 합니다.

- 의미에 맞는 HTML 요소와 폼 `label`
- CSS 기본 배치, Flexbox와 Grid
- JavaScript module, Promise, `async`, `await`
- TypeScript union, `unknown`, narrowing
- HTTP method, 상태 코드, 헤더와 JSON 본문
- React props, state, event, Effect와 정리 함수
- Node.js, `package.json`, script와 잠금 파일

## 1. Stable Core

외부 실제 프로젝트를 시작하기 전에 다음 두 문서만 읽습니다.

### `01-project-onboarding.md`

다음 내용을 확인합니다.

- 저장소가 요구하는 Node.js와 패키지 관리자
- 잠금 파일, scripts, 환경 변수와 CI 명령
- 개발 서버와 운영 서버의 차이
- 브라우저, Next.js 서버와 빌드 시점에 실행되는 코드
- URL에서 page, 데이터 읽기 함수, Client Component와 테스트까지 추적하는 방법
- 첫 변경을 작고 확인 가능한 사용자 기능으로 제한하는 방법

처음 보는 프로젝트를 실행하고 수정 위치를 찾으려면 반드시 필요한 내용입니다. 프로젝트가 commerce인지 portfolio인지와 관계없이 달라지지 않습니다.

### `02-ui-and-state-architecture.md`

다음 내용을 확인합니다.

- URL 상태, 서버 상태, 화면 상태, 입력 초안과 계산값의 차이
- 상태를 저장하고 변경할 컴포넌트 결정
- 서로 배타적인 상태를 discriminated union으로 표현하는 방법
- URL, HTTP, storage 입력을 `unknown`으로 받아 검사하는 방법
- Server Component와 Client Component의 실행 위치에 따른 코드 배치
- 서버가 확정한 값과 사용자가 편집 중인 값의 분리

React 기능을 구현할 때 반복해서 필요한 판단이며 특정 라이브러리나 한 프로젝트의 기능에 묶이지 않습니다.

Stable Core의 정확한 목록은 다음과 같습니다.

```text
01-project-onboarding.md
02-ui-and-state-architecture.md
```

새 프로젝트에 authentication, realtime, payment 같은 기능이 추가되어도 Stable Core를 늘리지 않습니다. 해당 기능은 실제 구현이 그 문제에 도달했을 때 JIT 자료로 다룹니다.

## 2. Actual Project

Stable Core를 읽은 뒤에는 외부 실제 프로젝트를 시작합니다. 이 저장소의 competency exercise를 먼저 구현하지 않습니다.

프로젝트에 들어가면 다음 순서로 확인합니다.

1. 고정 설치, 개발 실행, 형 검사, 테스트, 빌드와 운영 시작 명령을 찾습니다.
2. 사용자 기능 하나가 어떤 URL, 서버 코드, 클라이언트 코드와 HTTP 요청을 거치는지 추적합니다.
3. 외부 입력을 검사하는 파일과 함수를 찾습니다.
4. URL, 서버 응답과 입력 초안을 각각 어디에 저장하는지 확인합니다.
5. 실패해도 유지해야 할 마지막 정상 결과와 사용자 입력을 정합니다.
6. 가장 작은 사용자 기능 하나를 구현하고 해당 기능에 필요한 검증을 추가합니다.

실제 프로젝트가 이 과정의 중심입니다. Guide를 모두 읽어야만 구현을 시작할 수 있다는 전제를 만들지 않습니다.

## 3. JIT / Rewind

다음 문서는 관련 문제가 실제로 등장했을 때 읽습니다. 프로젝트를 마친 뒤 competency exercise가 실패하면 같은 문서의 관련 절을 Rewind 자료로 다시 사용합니다.

### `03-nextjs-data-effects-and-concurrency.md`

다음 상황에서 읽습니다.

- 검색 조건이나 tab을 URL과 history에 저장할 때
- Client Component에서 비동기 요청을 시작할 때
- Effect 정리 함수가 필요할 때
- 이전 요청의 늦은 응답이 최신 화면을 덮을 수 있을 때
- 낙관적 갱신을 구현할 때
- 서버의 `version` 충돌을 처리할 때

### `04-testing-accessibility-and-performance.md`

다음 상황에서 읽습니다.

- parser, 상태 전이, Route Handler와 브라우저 동작 중 어디에서 검사할지 정할 때
- 응답 순서를 결정적으로 재현해야 할 때
- 키보드 조작과 초점 이동을 구현할 때
- 좁은 화면, 확대, 긴 문자열과 motion 감소 설정을 확인할 때
- JavaScript 크기나 DOM 수에 예산을 둘 때
- 개발 서버가 아닌 운영 빌드를 브라우저에서 검사할 때

### `05-production-runtime-contract.md`

다음 상황에서 읽습니다.

- 애플리케이션의 빌드와 시작 명령을 배포 환경에 제공할 때
- health 응답과 릴리스 식별자를 만들 때
- 서버 전용 환경 변수가 HTML이나 JavaScript에 포함되지 않는지 확인할 때
- 테스트 전용 endpoint를 운영 환경에서 닫을 때
- 운영 프로세스를 직접 실행하는 smoke test를 만들 때

### `90-practical-checklist.md`

다음 상황에서 필요한 항목만 확인합니다.

- 기능 구현 전에 위험 항목을 점검할 때
- 코드 리뷰를 할 때
- 운영 장애의 원인을 좁힐 때
- competency exercise 실패 후 다시 읽을 문서를 고를 때

JIT/Rewind의 정확한 목록은 다음과 같습니다.

```text
03-nextjs-data-effects-and-concurrency.md
04-testing-accessibility-and-performance.md
05-production-runtime-contract.md
90-practical-checklist.md
```

## 4. Project PASS

외부 실제 프로젝트는 최소한 다음 조건을 통과해야 합니다.

- 저장소가 고정한 패키지 관리자와 잠금 파일로 설치할 수 있습니다.
- 형 검사와 프로젝트 내부 테스트가 통과합니다.
- 운영 빌드가 성공합니다.
- 핵심 사용자 기능을 실제 브라우저에서 확인했습니다.
- 입력 오류, HTTP 실패, 늦은 응답과 저장 충돌 중 프로젝트에서 중요한 실패를 재현했습니다.
- 운영 시작 방법과 필요한 환경 변수가 문서화되어 있습니다.
- 프로젝트가 health 또는 smoke 검증을 제공한다면 해당 검증이 통과합니다.

프로젝트마다 필요한 검사 종류는 다를 수 있습니다. 개발 서버에서 화면이 보인다는 이유만으로 PASS로 처리하지 않습니다.

## 5. Competency Suite

프로젝트 완료 후 수행할 필수 역량 검증 프로그램은 다음 하나입니다.

```text
exercises/project-catalog/
```

분류: **CORE COMPETENCY**

이 프로그램은 다음 능력을 확인합니다.

- URL 쿼리 정규화와 서버의 첫 렌더링
- 외부 JSON의 실행 중 검증
- `ready`, `empty`, `pending`, `error` 상태 구분
- 마지막 정상 결과 보존
- `AbortController`와 generation을 이용한 늦은 응답 차단
- 낙관적 제목 변경, 일반 실패 복구와 `409 Conflict` 처리
- Route Handler 입력 검사와 HTTP 상태 코드 구분
- 키보드 편집과 초점 복구
- 단위 테스트, 브라우저 E2E와 운영 smoke test

실행 순서는 다음과 같습니다.

```text
Project PASS
→ exercise README와 test 확인
→ Guide를 다시 읽지 않고 구현 또는 재구성
→ npm run verify
```

결과는 다음과 같이 처리합니다.

```text
PASS
→ 해당 능력을 다른 문맥에서도 재현할 수 있음

FAIL
→ 실패한 영역에 해당하는 Guide만 Rewind
→ 구현 수정
→ 같은 검증 다시 실행
```

## 6. Rewind 대응표

| 실패한 영역 | 다시 읽을 문서 |
| --- | --- |
| package, 빌드, route 추적, Server/Client 실행 위치 | `01-project-onboarding.md` |
| 상태 저장 위치, discriminated union, 외부 입력 검사 | `02-ui-and-state-architecture.md` |
| history, Effect 정리, 요청 순서, 낙관적 갱신 | `03-nextjs-data-effects-and-concurrency.md` |
| 단위/E2E 선택, 키보드, 초점, 반응형, 성능 예산 | `04-testing-accessibility-and-performance.md` |
| health, 릴리스, 비밀값 노출, 운영 smoke test | `05-production-runtime-contract.md` |
| 여러 영역이 섞여 원인을 좁히기 어려움 | `90-practical-checklist.md` |

Rewind는 전체 Guide를 처음부터 다시 읽는 과정이 아닙니다. 실패를 재현한 뒤 관련 문서의 해당 절만 확인하고 같은 검증으로 수정 결과를 확인합니다.

## 7. 제외된 exercise

현재 `exercises/`에는 `project-catalog` 하나만 있으며, 같은 능력을 더 강하게 검증하는 다른 프로그램이 없습니다.

- REDUNDANT: 없음
- SPECIALIZATION: 없음
- PROJECT-SCALE INTEGRATION: 없음

`project-catalog`는 여러 기능을 함께 검사하지만 데이터베이스, authentication, realtime, 외부 시스템과 복잡한 업무 규칙을 포함하지 않습니다. 실제 외부 프로젝트를 대체하기보다는 핵심 능력을 작은 다른 문맥에서 다시 확인하는 프로그램에 가깝습니다. 따라서 더 줄일 근거가 없습니다.

## 8. 최종 학습 순서

```text
1. docs/00-roadmap.md에서 전체 순서를 확인합니다.
2. docs/01-project-onboarding.md를 읽습니다.
3. docs/02-ui-and-state-architecture.md를 읽습니다.
4. 외부 실제 프로젝트를 시작합니다.
5. 구현 중 필요한 JIT 문서만 읽습니다.
6. 프로젝트의 빌드·테스트·운영 실행 조건을 통과합니다.
7. exercises/project-catalog/을 Guide 없이 검증합니다.
8. 실패한 항목에 해당하는 문서만 다시 읽습니다.
9. 같은 검증을 다시 통과합니다.
```

## 완료 기준

다음 조건을 모두 만족하면 이 개발 트랙을 완료한 것으로 봅니다.

- 처음 보는 React·Next.js 저장소의 실행 방법과 주요 파일을 스스로 확인할 수 있습니다.
- 사용자 기능 하나를 URL, 서버 데이터, 클라이언트 상태와 HTTP 요청까지 추적할 수 있습니다.
- 외부 입력을 검사하고 상태를 한 곳에서 일관되게 변경할 수 있습니다.
- 실제 프로젝트에서 필요한 JIT 문서만 찾아 적용할 수 있습니다.
- 실제 프로젝트의 운영 빌드와 핵심 브라우저 동작을 확인했습니다.
- `exercises/project-catalog/`의 전체 검증을 Guide 없이 통과했습니다.
- 실패한 항목이 있었다면 관련 문서만 다시 읽고 같은 검증을 통과했습니다.
