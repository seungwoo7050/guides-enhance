# React·Next.js 실전 개발 가이드

이 저장소는 React와 Next.js 문법을 처음 배우는 입문서가 아닙니다. TypeScript와 React로 작은 기능을 구현해 본 개발자가 실제 프로젝트에 들어가 코드를 읽고, 기능을 완성하고, 운영 환경에서 확인하는 데 필요한 판단 기준을 다룹니다.

실제 프로젝트는 이 저장소 밖에서 진행합니다. `docs/`에는 프로젝트 진입 전에 읽을 최소 문서와 구현 중 찾아볼 자료가 있으며, `exercises/`에는 실제 프로젝트를 통과한 뒤 Guide 없이 역량을 확인할 완성된 프로그램이 있습니다.

## 학습 순서

```text
Stable Core Guide
→ Actual Project
→ JIT Guide as needed
→ Project PASS
→ Competency Suite without Guide
→ Rewind where needed
```

## 1. Stable Core Guide

프로젝트 종류와 관계없이 먼저 읽을 문서는 두 개입니다.

1. [`docs/01-project-onboarding.md`](docs/01-project-onboarding.md)
   - Node.js, 패키지 관리자, 잠금 파일, 빌드와 테스트 명령을 확인합니다.
   - Server Component, Client Component와 Route Handler가 어디에서 실행되는지 구분합니다.
   - 처음 보는 저장소에서 URL 하나가 어떤 파일과 요청을 거쳐 화면에 나타나는지 추적합니다.
2. [`docs/02-ui-and-state-architecture.md`](docs/02-ui-and-state-architecture.md)
   - URL 상태, 서버 상태, 화면 상태, 입력 초안과 계산값을 구분합니다.
   - 외부 입력을 `unknown`으로 받고 필요한 값을 검사한 뒤 내부 타입으로 변환합니다.
   - 값을 어느 컴포넌트가 저장하고 어떤 이벤트가 바꿀지 정합니다.

이 두 문서는 commerce, portfolio, realtime, collaboration 등 대상 프로젝트가 달라져도 그대로 유지합니다. 특정 프로젝트에만 필요한 기능을 선행 조건으로 추가하지 않습니다.

## 2. Actual Project

Stable Core를 읽은 뒤에는 실제 프로젝트 구현을 시작합니다. 이 저장소의 exercise를 먼저 수행하지 않습니다.

프로젝트에 들어가면 다음 항목부터 확인합니다.

- 설치, 개발 서버, 형 검사, 테스트, 빌드와 운영 시작 명령
- 사용자 행동 하나가 통과하는 URL, 서버 코드, 클라이언트 코드와 HTTP 요청
- 외부 입력을 검사하는 위치
- URL, 서버 응답과 입력 초안을 저장하는 위치
- 실패해도 유지해야 할 마지막 정상 결과와 사용자 입력

## 3. JIT / Rewind Guide

구현이 해당 문제에 도달했을 때만 읽습니다.

- [`docs/03-nextjs-data-effects-and-concurrency.md`](docs/03-nextjs-data-effects-and-concurrency.md)
  - URL과 history, Effect 정리, 요청 취소, 늦은 응답 차단, 낙관적 갱신과 `version` 충돌
- [`docs/04-testing-accessibility-and-performance.md`](docs/04-testing-accessibility-and-performance.md)
  - 테스트 위치 선택, 브라우저 E2E, 키보드와 초점, 좁은 화면, motion 감소 설정과 성능 예산
- [`docs/05-production-runtime-contract.md`](docs/05-production-runtime-contract.md)
  - 운영 빌드와 시작, health 응답, 릴리스 식별자, 비밀값 노출 검사와 smoke test
- [`docs/90-practical-checklist.md`](docs/90-practical-checklist.md)
  - 구현, 코드 리뷰, 장애 분석 또는 Rewind 범위를 정할 때 필요한 항목만 골라 보는 점검표

JIT 문서는 프로젝트 요구 사항이 생기기 전에 미리 정독하지 않습니다. 프로젝트를 마친 뒤 역량 검증 프로그램에서 실패한 경우에는 같은 문서의 관련 절만 다시 읽습니다.

## 4. Competency Suite

현재 필수 역량 검증 프로그램은 하나입니다.

- [`exercises/project-catalog/`](exercises/project-catalog/)

`Project Catalog`는 다음 능력을 작은 다른 문맥에서 다시 구현할 수 있는지 확인합니다.

- URL 쿼리 정규화와 서버의 첫 렌더링
- `unknown` JSON 검사
- 서로 모순되지 않는 화면 상태 표현
- 요청 취소와 generation 확인
- 낙관적 제목 변경과 `409 Conflict` 복구
- 키보드 조작과 초점 이동
- Route Handler의 입력·응답 처리
- 단위 테스트, 브라우저 테스트와 운영 smoke test

이 프로그램은 프로젝트 진입 과제가 아닙니다. 실제 프로젝트가 PASS한 뒤 README와 테스트를 확인하고, Guide를 다시 읽지 않은 상태에서 구현하거나 재구성합니다.

```text
PASS
→ 역량 확인 완료

FAIL
→ 실패한 영역에 해당하는 Guide만 다시 읽기
→ 같은 검증 다시 실행
```

## 선행 지식

다음 내용을 이미 사용해 본 개발자를 대상으로 합니다.

- 의미에 맞는 HTML 요소와 폼 `label`
- CSS 기본 배치, Flexbox와 Grid
- JavaScript module, Promise, `async`, `await`
- TypeScript union, `unknown`, narrowing
- React props, state, event, Effect와 정리 함수
- Next.js App Router의 `page.tsx`, `layout.tsx`, Route Handler
- HTTP method, 상태 코드, 헤더와 JSON 본문
- Node.js, `package.json`, script와 잠금 파일

위 항목이 낯설다면 별도의 기초 과정에서 먼저 보완해야 합니다. 이 저장소는 문법 설명을 반복하지 않습니다.

## 권장 사용법

1. [`docs/00-roadmap.md`](docs/00-roadmap.md)에서 전체 순서와 완료 조건을 확인합니다.
2. Stable Core 두 문서를 읽습니다.
3. 외부의 실제 프로젝트를 시작합니다.
4. 구현 중 필요한 JIT 문서만 읽습니다.
5. 프로젝트의 빌드, 테스트와 운영 실행 조건을 통과시킵니다.
6. `exercises/project-catalog/`를 Guide 없이 검증합니다.
7. 실패한 항목이 있을 때만 관련 문서로 돌아갑니다.

## 저장소 구성

```text
.
├── .gitignore
├── README.md
├── docs/
│   ├── 00-roadmap.md
│   ├── 01-project-onboarding.md
│   ├── 02-ui-and-state-architecture.md
│   ├── 03-nextjs-data-effects-and-concurrency.md
│   ├── 04-testing-accessibility-and-performance.md
│   ├── 05-production-runtime-contract.md
│   └── 90-practical-checklist.md
└── exercises/
    └── project-catalog/
```

## 완료 기준

다음 조건을 모두 만족하면 이 개발 트랙을 완료한 것으로 봅니다.

- Stable Core를 읽고 처음 보는 React·Next.js 프로젝트의 실행 방법과 주요 파일을 스스로 확인할 수 있습니다.
- 외부 실제 프로젝트에서 사용자 기능 하나를 운영 빌드와 실제 브라우저 동작까지 확인했습니다.
- 프로젝트에 필요한 JIT 문서를 골라 적용했으며, 필요하지 않은 문서를 선행 조건으로 만들지 않았습니다.
- `exercises/project-catalog/`의 전체 검증을 Guide 없이 통과했습니다.
- 실패한 영역이 있었다면 관련 문서만 다시 읽고 같은 검증을 통과했습니다.
