# Notes API

Fastify와 Zod로 만든 메모 API입니다. HTTP 요청을 실행 중에 검사하고, 제목 중복 검사와 메모 저장을 별도 함수로 나눕니다. 예상하지 못한 저장 오류는 내부 내용을 숨긴 500 응답으로 바꿉니다.

## 제공하는 API

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/memos` | 전체 메모 조회 |
| `GET` | `/memos/:id` | ID로 한 건 조회 |
| `POST` | `/memos` | 메모 생성 |

생성 본문은 다음 형식입니다.

```json
{
  "title": "회의 기록",
  "body": "결정 사항을 정리합니다."
}
```

제목은 공백을 제거한 뒤 1~80자여야 하며, 본문은 최대 500자입니다. 같은 제목은 409로 거부합니다.

## 설치와 실행

```sh
npm install
npm run typecheck
npm test
npm run dev
```

서버는 기본적으로 `0.0.0.0:4000`에서 실행됩니다.

## 테스트

테스트는 실제 포트를 열지 않고 `app.inject`로 다음을 확인합니다.

- 빈 제목과 잘못된 JSON은 400
- 정상 생성은 201
- 같은 제목의 두 번째 생성은 409
- 없는 ID는 404
- 저장소의 예상하지 못한 오류는 500
- 내부 열 이름과 스택 정보는 응답에 포함되지 않음
- 각 테스트가 만든 Fastify 애플리케이션을 종료함

## 코드 구성

- `src/contracts.ts`: 생성 본문 스키마와 메모 타입
- `src/repository.ts`: 저장에 필요한 함수와 메모리 구현
- `src/service.ts`: 중복 제목 검사
- `src/app.ts`: 요청·응답 처리와 오류 변환
- `src/server.ts`: 메모리 저장소를 선택하고 포트 열기

## 주요 선택

- 외부 본문은 TypeScript 타입 단언이 아니라 Zod로 검사합니다.
- 제목 중복은 HTTP 코드가 아니라 서비스 오류로 표현합니다. 라우트가 이를 409로 바꿉니다.
- 메모리 저장소는 인스턴스마다 별도 `Map`을 사용하므로 테스트가 값을 공유하지 않습니다.
- 분류하지 못한 오류는 로그 대상이며, 클라이언트에는 일반적인 500 본문만 반환합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Memo request schema | `src/contracts.ts` |
| 2 | Memo persistence API | `src/repository.ts` |
| 3 | Duplicate-title rule | `src/service.ts` |
| 4 | Testable Fastify app factory | `src/app.ts` |
| 5 | Memo read routes | `src/app.ts` |
| 6 | Memo creation route | `src/app.ts` |
| 7 | Network entry point | `src/server.ts` |

## 범위와 제한

메모는 프로세스 메모리에만 저장되어 재시작하면 사라집니다. 인증, 데이터베이스, 페이지네이션, 수정과 삭제 API는 포함하지 않습니다.
