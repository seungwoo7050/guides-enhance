# 웹 애플리케이션 학습 로드맵

이 로드맵은 문서를 처음부터 끝까지 읽는 순서가 아니라, 실제 프로젝트를 중심으로 가이드를 사용하는 방법을 설명합니다.

## 전체 모델

```text
고정 Core Guide
→ 실제 웹 프로젝트 시작
→ 기능 구현 직전에 JIT Guide 확인
→ 프로젝트 PASS
→ 7개 Competency Exercise 재구현
→ 부족한 주제만 Rewind
```

프로젝트가 포트폴리오, 실시간 게임, 쇼핑몰, 협업 도구로 바뀌어도 Core Guide 목록은 달라지지 않습니다. 특정 기능과 업무 규칙은 프로젝트에서 실제 문제가 되었을 때 익힙니다.

## 1. 프로젝트 전에 읽는 Core Guide

Core Guide는 언어, 실행 환경, 프레임워크와 애플리케이션 구성의 기본 원리를 다룹니다. 총 13개입니다.

### Web Foundations

1. [`웹은 어떻게 동작하는가`](01-web-foundations/01-how-the-web-works.md)
2. [`JavaScript 기초`](01-web-foundations/04-javascript-foundations.md)
3. [`비동기 작업과 fetch`](01-web-foundations/06-async-fetch-errors.md)
4. [`TypeScript와 런타임 검증`](01-web-foundations/07-typescript-runtime-validation.md)
5. [`Node.js, 패키지와 워크스페이스`](01-web-foundations/08-node-packages-workspaces.md)

### Frontend

6. [`React 컴포넌트와 상태`](02-frontend/01-react-components-state.md)
7. [`React Effect와 비동기 요청`](02-frontend/03-react-effects-async.md)
8. [`Next.js 라우팅과 렌더링`](02-frontend/04-nextjs-routing-rendering.md)
9. [`Next.js 데이터 요청과 어댑터`](02-frontend/05-nextjs-data-boundaries.md)

### Backend

10. [`HTTP API 모델`](03-backend/01-http-api-model.md)
11. [`Fastify 생명주기`](03-backend/02-fastify-lifecycle.md)
12. [`Zod를 이용한 요청·응답 검증`](03-backend/03-zod-contracts.md)
13. [`서비스, 리포지터리와 오류 처리`](03-backend/04-service-repository-errors.md)

### Core 완료 기준

다음 내용을 설명할 수 있으면 프로젝트를 시작합니다.

- URL, HTTP 요청, HTTP 오류 응답, 연결 실패가 각각 어디에서 발생하는지 구분합니다.
- JavaScript 값과 객체 참조, 비동기 작업의 완료 순서를 이해합니다.
- 외부 JSON과 환경 변수를 `unknown`에서 검증된 값으로 바꿉니다.
- Node.js 패키지의 공개 진입점과 실제 실행 파일을 분리합니다.
- React 상태를 필요한 가장 가까운 컴포넌트에 두고, Effect에서 시작한 작업을 정리합니다.
- Next.js 코드가 서버와 브라우저 중 어디에서 실행되는지 판단합니다.
- HTTP 라우트는 요청과 응답을 처리하고, 서비스는 업무 순서를 정하며, 리포지터리는 저장 작업을 수행하도록 나눕니다.
- Fastify 애플리케이션을 실제 포트 없이 생성하고 테스트할 수 있습니다.

이 단계에서 데이터베이스, 인증, WebSocket을 미리 완벽하게 익힐 필요는 없습니다.

## 2. 프로젝트 중에 읽는 JIT Guide

JIT Guide는 해당 기능을 구현하기 직전에 읽습니다. 기능이 없는 프로젝트에서는 읽지 않아도 됩니다.

### HTML, CSS와 브라우저 상태

- [`HTML 폼과 접근성`](01-web-foundations/02-html-forms-accessibility.md)
- [`CSS 레이아웃과 반응형 화면`](01-web-foundations/03-css-layout-responsive.md)
- [`DOM, 이벤트, URL과 저장소`](01-web-foundations/05-dom-events-url-storage.md)
- [`React 폼과 목록`](02-frontend/02-react-forms-lists.md)

폼, URL 검색 조건, 브라우저 방문 기록, 반응형 화면을 구현하기 직전에 확인합니다.

### 데이터베이스

- [`관계형 모델과 SQL`](04-data-and-security/01-sql-relational-model.md)
- [`PostgreSQL과 Kysely`](04-data-and-security/02-postgresql-kysely.md)
- [`마이그레이션과 트랜잭션`](04-data-and-security/03-migrations-transactions.md)

테이블과 제약 조건을 정하기 전에 관계형 모델을 읽고, 실제 PostgreSQL 코드를 작성할 때 Kysely 문서를 확인합니다. 여러 쓰기가 함께 성공해야 하는 기능을 구현하기 전에 트랜잭션 문서를 읽습니다.

### 인증과 권한

- [`비밀번호, 세션과 쿠키`](04-data-and-security/04-passwords-sessions-cookies.md)
- [`권한, CSRF와 CORS`](04-data-and-security/05-authorization-csrf-cors.md)

인증 기능은 잘못 구현한 뒤 고치는 비용이 크므로, 로그인과 권한 코드를 쓰기 직전에 두 문서를 모두 읽습니다.

### 실시간 기능과 테스트

- [`WebSocket 프로토콜`](05-realtime-and-quality/01-websocket-protocol.md)
- [`실시간 상태와 충돌`](05-realtime-and-quality/02-realtime-state-conflicts.md)
- [`Canvas 렌더링`](05-realtime-and-quality/03-canvas-rendering.md)
- [`테스트와 품질`](05-realtime-and-quality/04-testing-quality.md)

연결을 열기 전에 WebSocket 메시지와 종료 처리를 정하고, 여러 사용자가 같은 값을 바꾸는 기능을 만들기 전에 버전과 스냅샷 복구 방식을 정합니다. Canvas와 테스트 문서는 해당 코드를 작성할 때 읽습니다.

## 3. 프로젝트 PASS 이후 Competency Suite

실제 프로젝트를 통과한 뒤 일곱 exercise를 가이드 없이 구현합니다.

1. [`browser-directory`](../exercises/browser-directory/README.md)
2. [`runtime-workspace`](../exercises/runtime-workspace/README.md)
3. [`user-directory`](../exercises/user-directory/README.md)
4. [`notes-api`](../exercises/notes-api/README.md)
5. [`seat-reservation`](../exercises/seat-reservation/README.md)
6. [`session-access-control`](../exercises/session-access-control/README.md)
7. [`realtime-board`](../exercises/realtime-board/README.md)

### 수행 순서

```text
README와 테스트 확인
→ 구현 순서 직접 결정
→ 가이드 없이 작성
→ 프로젝트별 테스트 실행
→ 실패 원인 기록
→ 필요한 문서만 다시 읽기
→ 수정 후 재검증
```

### 평가 기준

| Exercise | 핵심 질문 |
|---|---|
| `browser-directory` | URL과 방문 기록만으로 검색 화면을 정확히 복원할 수 있습니까? |
| `runtime-workspace` | 패키지 내부 파일을 노출하지 않고 입력 검증과 실행 위치를 분리할 수 있습니까? |
| `user-directory` | 이전 요청이 늦게 끝나도 최신 React 화면을 유지할 수 있습니까? |
| `notes-api` | 요청 검증, 업무 규칙, 저장, HTTP 오류 변환을 분리할 수 있습니까? |
| `seat-reservation` | 경쟁 요청 중 하나만 성공하고 실패 시 일부 행이 남지 않게 할 수 있습니까? |
| `session-access-control` | 세션 수명과 소유권·역할 권한을 서버에서 다시 검사할 수 있습니까? |
| `realtime-board` | 연결, 방 참가, 버전 충돌, 스냅샷 복구와 종료 처리를 구현할 수 있습니까? |

정답 구현과 파일 배치가 같을 필요는 없습니다. README에 적힌 외부 동작, 실패 후 상태와 테스트 조건을 만족해야 합니다.

## 4. Rewind 방법

exercise가 실패했다고 전체 가이드를 처음부터 다시 읽지 않습니다.

1. 실패한 입력과 실제 결과를 기록합니다.
2. 상태를 누가 저장하고 있는지 확인합니다.
3. 실패 후 남은 데이터, 연결, 타이머를 확인합니다.
4. 관련 문서 한두 개만 다시 읽습니다.
5. 같은 실수를 검출하는 테스트를 보강합니다.

예를 들어 `seat-reservation`의 경쟁 테스트만 실패한다면 React나 WebSocket 문서를 다시 읽을 이유가 없습니다. 관계형 제약 조건과 트랜잭션 문서만 확인합니다.

## 5. 프로젝트가 추가될 때의 원칙

새 프로젝트가 추가되어도 Core Guide와 Competency Suite는 바꾸지 않습니다. 프로젝트에서 새로운 기능이나 업무 규칙을 만나면 JIT 문서를 추가하거나 별도의 전문 가이드로 분리합니다.

다음 항목은 Core에 넣지 않습니다.

- 특정 산업의 업무 규칙
- 특정 결제사·인증 제공자 사용법
- 아직 사용하지 않는 데이터베이스나 메시지 브로커
- 이름만 익히기 위한 아키텍처 패턴
- 프로젝트 요구사항에 없는 운영 도구

프로젝트 전에 준비를 끝내려는 대신, 코드를 시작할 수 있는 공통 기반만 갖춘 뒤 실제 문제를 통해 필요한 지식을 확장합니다.
