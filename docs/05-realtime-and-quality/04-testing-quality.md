# 테스트와 품질

모든 기능을 하나의 브라우저 시나리오로 검사하면 실제 사용자 흐름을 확인할 수는 있지만 테스트가 느리고, 실패했을 때 어느 계층에서 문제가 생겼는지 찾기 어렵습니다. 반대로 순수 함수 테스트만 있으면 계산 로직은 검증할 수 있어도 실제 HTTP 라우트, 데이터베이스 제약, WebSocket 연결, 브라우저 동작과 빌드 단계에서 생기는 문제는 발견하지 못합니다.

따라서 테스트는 **문제가 처음 드러나는 가장 짧은 실행 범위**에 두는 것이 기본 원칙입니다.

```text
순수 계산 오류
→ 단위 테스트

네트워크 입력 형식 오류
→ 스키마 테스트

DOM 상호작용 오류
→ 컴포넌트 테스트

HTTP 훅·상태 코드·직렬화 오류
→ API 테스트

DB 제약·트랜잭션·잠금 오류
→ 실제 DB 테스트

실시간 연결·방 전송 오류
→ 실제 WebSocket 테스트

브라우저 라우팅·포커스·CSS·히스토리 오류
→ 브라우저 E2E

서버/클라이언트 번들 분리 오류
→ 프로덕션 빌드
```

그리고 소수의 종단 간 테스트로 전체 시스템이 실제로 조립되어 동작하는지 확인합니다.

## 목표

- 단위·스키마·컴포넌트·API·데이터베이스·WebSocket·브라우저 테스트의 역할을 구분합니다.
- 각 위험이 처음 드러나는 가장 짧은 테스트 계층을 선택합니다.
- 정상·실패·경계값·최댓값·경쟁 조건·순서 역전을 반복해서 재현합니다.
- 가짜 구현과 실제 인프라 테스트가 각각 무엇을 놓치는지 설명합니다.
- 타입 검사, 런타임 테스트, 프로덕션 빌드와 E2E를 서로 다른 검사로 취급합니다.
- 테스트가 올바른 구현만 통과시키는지, 즉 잘못된 구현을 실제로 거부하는지 확인합니다.
- 테스트 실패가 구현 오류인지 테스트 자체의 간헐적 실패인지 구분하기 쉽게 만듭니다.

## 위험에 맞는 검사

테스트 종류를 먼저 정하고 기능을 끼워 맞추기보다, **어떤 종류의 실패를 잡고 싶은가**부터 생각합니다.

| 위험 | 먼저 둘 테스트 |
|---|---|
| 좌표 제한과 상태 전이 | 순수 함수 단위 테스트 |
| Zod가 잘못된 값 거부 | 스키마 테스트 |
| 레이블·버튼·오류 안내 | 컴포넌트 또는 브라우저 테스트 |
| Fastify 훅·상태 코드·JSON 변환 | `app.inject` API 테스트 |
| 고유·외래 키·롤백 | 실제 PostgreSQL 테스트 |
| 잠금·동시 쓰기·경쟁 조건 | 실제 PostgreSQL 동시성 테스트 |
| 방별 전송·재연결 | 실제 WebSocket 연결 두 개 이상 |
| 라우팅·키보드·히스토리 | 실제 브라우저 테스트 |
| CSS 넘침·뷰포트·Canvas 포인터 | 실제 브라우저 테스트 |
| 서버/브라우저 import 오류 | Next.js 프로덕션 빌드 |

예를 들어 "같은 좌석을 동시에 예약하면 하나만 성공해야 한다"는 요구사항은 단순한 서비스 함수 단위 테스트만으로 충분하지 않습니다. 실제로 PostgreSQL의 제약과 트랜잭션이 경쟁 상황에서 올바르게 동작하는지 확인해야 하기 때문입니다.

반대로 숫자를 허용 범위로 자르는 `clampPoint()` 같은 함수는 브라우저 E2E까지 올릴 이유가 없습니다.

## 테스트 이름은 관찰 가능한 결과를 적습니다

테스트 이름을 내부 구현에 맞추면 리팩터링할 때 테스트의 의미가 약해집니다.

다음 이름보다:

```text
calls updateBoard()
uses AbortController
sets isLoading false
```

다음처럼 시스템의 행동을 적는 편이 좋습니다.

```text
viewer는 메모 내용을 수정할 수 없다
같은 좌석을 예약하는 두 요청 중 하나만 성공한다
뒤로 가면 이전 검색어와 결과가 복원된다
오래된 항목 버전으로 저장하면 충돌 응답을 받는다
```

테스트 이름만 읽어도 어떤 보장 조건을 검사하는지 알 수 있어야 합니다.

## 단위 테스트

외부 자원을 사용하지 않는 계산은 단위 테스트에서 많은 입력을 빠르게 검사할 수 있습니다.

```ts
it("보드 밖 좌표를 허용 범위로 줄입니다", () => {
  expect(
    clampPoint(
      { x: -10, y: 900 },
      { width: 800, height: 600 }
    )
  ).toEqual({
    x: 0,
    y: 600
  });
});
```

단위 테스트에 적합한 예:

- 좌표 제한
- 상태 전이 함수
- 권한 판정 함수
- 정렬과 필터링
- 문자열 파싱
- 날짜 계산
- 충돌 해결 정책
- 순수 reducer

### 경계값을 포함합니다

정상적인 중간값 하나만 검사하면 경계 오류를 놓치기 쉽습니다.

예를 들어 좌표 제한이라면:

```text
x = 0
x = width
x = -1
x = width + 1
```

같이 경계를 포함합니다.

숫자 입력이라면 필요에 따라:

```text
최솟값 바로 아래
최솟값
최댓값
최댓값 바로 위
NaN
Infinity
```

를 구분합니다.

## 시간과 난수를 제어합니다

현재 시각이나 난수가 함수 내부에 직접 숨겨져 있으면 테스트가 재현하기 어려워집니다.

예를 들어:

```ts
function createSession() {
  return {
    id: crypto.randomUUID(),
    createdAt: new Date()
  };
}
```

대신 테스트에서 제어해야 하는 값은 의존성으로 분리할 수 있습니다.

```ts
interface Clock {
  now(): Date;
}

interface IdGenerator {
  next(): string;
}
```

테스트에서는 고정 구현을 넣습니다.

```ts
const clock = {
  now: () => new Date("2026-01-01T00:00:00Z")
};

const ids = {
  next: () => "fixed-id"
};
```

목적은 모든 API를 인터페이스로 만드는 것이 아니라 **재현성에 영향을 주는 외부 요인만 통제하는 것**입니다.

## 비공개 구현을 억지로 노출하지 않습니다

테스트하려고 `private` 함수를 public으로 바꾸거나 내부 helper를 외부 API로 노출하면 테스트가 설계를 왜곡할 수 있습니다.

다음 기준을 우선합니다.

```text
공개 동작을 통해 검증 가능한가?
→ 공개 동작으로 검사

복잡한 로직이 독립된 개념인가?
→ 순수 함수나 별도 모듈로 추출

단순한 내부 구현 세부사항인가?
→ 직접 테스트하지 않아도 됨
```

테스트는 구현 구조를 고정하는 도구가 아니라 **동작을 보장하는 도구**입니다.

## 스키마 테스트

TypeScript 타입은 컴파일 이후 사라지므로 네트워크 입력 검증을 대신하지 못합니다.

Zod 같은 런타임 스키마는 직접 테스트해야 합니다.

다음 값을 포함합니다.

- 필수 필드 누락
- 잘못된 타입
- 빈 문자열
- 최소·최대 길이
- 알 수 없는 메시지 종류
- `NaN`, `Infinity`
- 허용 범위 밖의 숫자
- 추가 필드 처리
- 이전·새 메시지 버전 호환
- 잘못된 중첩 객체
- 너무 큰 배열

예:

```ts
it("무한대 좌표를 거부합니다", () => {
  const result = MoveSchema.safeParse({
    type: "item.move",
    x: Infinity,
    y: 10
  });

  expect(result.success).toBe(false);
});
```

### 추가 필드 정책도 명시합니다

스키마가 다음 입력을 받았다고 가정합니다.

```json
{
  "name": "A",
  "isAdmin": true
}
```

애플리케이션이 `isAdmin`을 정의하지 않았다면:

```text
추가 필드를 제거하는가?
추가 필드를 그대로 유지하는가?
알 수 없는 필드를 거부하는가?
```

중 어떤 정책인지 테스트로 고정합니다.

이 정책이 अस्पष्ट하면 클라이언트와 서버가 서로 다른 메시지 의미를 가질 수 있습니다.

## 응답 스키마도 검사합니다

입력만 검증하고 응답은 아무 객체나 직렬화하면 내부 필드가 노출될 수 있습니다.

예를 들어 사용자 응답에 다음 값이 들어가지 않는지 확인합니다.

```text
passwordHash
sessionSecret
internalNote
databaseOnlyField
```

예:

```ts
expect(response.json()).not.toHaveProperty("passwordHash");
```

가능하면 응답도 명시적인 DTO나 스키마를 통해 직렬화합니다.

## 컴포넌트 테스트

컴포넌트 테스트는 사용자가 DOM에서 관찰하는 동작을 검사합니다.

가능하면 다음을 우선합니다.

- role
- label
- accessible name
- 보이는 텍스트
- 상태 메시지

예:

```ts
await user.type(
  screen.getByLabelText("제목"),
  "회의 기록"
);

await user.click(
  screen.getByRole("button", { name: "저장" })
);

expect(
  await screen.findByRole("status")
).toHaveTextContent("저장됨");
```

이 테스트는 내부 상태 변수나 CSS 클래스 이름을 알 필요가 없습니다.

### 피해야 할 결합

다음은 구현 세부사항에 지나치게 결합될 수 있습니다.

```ts
container.querySelector(".save-button")
expect(component.state.isSaving).toBe(false)
expect(mockSetState).toHaveBeenCalled()
```

가능하면 다음처럼 사용자 관점의 결과를 봅니다.

```text
버튼이 비활성화되었다
상태 메시지가 나타났다
폼 오류가 표시되었다
화면에 최신 결과가 남았다
```

## 비동기 컴포넌트 상태를 모두 만들어 봅니다

네트워크를 사용하는 UI라면 성공 상태 하나만 테스트하지 않습니다.

예:

```text
초기 상태
로딩 중
빈 결과
성공
검증 오류
서버 오류
재시도
늦게 도착한 이전 응답
```

각 상태에서 사용자가 실제로 무엇을 보는지 검사합니다.

## 실제 시간을 기다리지 않습니다

다음 테스트는 느리고 간헐적으로 실패하기 쉽습니다.

```ts
await new Promise(resolve => setTimeout(resolve, 1000));
expect(screen.getByText("완료")).toBeInTheDocument();
```

테스트가 필요한 것은 "1초가 흘렀다"가 아니라 대개 "비동기 작업이 완료되었다"입니다.

따라서 완료 시점을 직접 제어하는 가짜 API나 deferred promise를 사용할 수 있습니다.

```ts
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;

  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return {
    promise,
    resolve,
    reject
  };
}
```

테스트가 원하는 순간에 요청 A와 B의 완료 순서를 결정할 수 있습니다.

## API 테스트

Fastify의 `app.inject()`는 실제 TCP 포트를 열지 않고도 Fastify 애플리케이션의 상당 부분을 실행합니다.

일반적으로 다음을 포함합니다.

```text
plugin 등록
route matching
hook
schema validation
handler
serializer
error handler
```

따라서 단순한 handler 함수 호출보다 실제 HTTP 애플리케이션 동작에 더 가깝습니다.

검사할 항목:

- 정상 요청의 상태 코드와 본문
- 잘못된 입력의 `400`
- 인증 없음 `401`
- 권한 부족 `403` 또는 정책에 따른 `404`
- 없는 리소스 `404`
- 버전·고유성 충돌 `409`
- 예상하지 못한 내부 오류 `500`
- 내부 오류 정보 비노출
- 쿠키 설정·삭제
- 요청 ID
- 응답 헤더
- 직렬화 결과

예:

```ts
const response = await app.inject({
  method: "POST",
  url: "/boards",
  payload: {
    title: "새 보드"
  }
});

expect(response.statusCode).toBe(201);
expect(response.json()).toMatchObject({
  title: "새 보드"
});
```

## 애플리케이션 수명을 정리합니다

테스트에서 애플리케이션을 만들었다면 종료도 테스트 책임입니다.

```ts
const app = buildApp();

try {
  await app.ready();

  // assertions
} finally {
  await app.close();
}
```

`app.close()`가 중요한 이유:

- DB pool 종료
- timer 종료
- plugin cleanup
- WebSocket 종료
- 열린 handle 제거

테스트 프로세스가 끝나지 않는다면 assertion보다 먼저 **열린 자원이 남았는지** 확인합니다.

## 모킹과 실제 인프라의 경계

가짜 구현은 빠르고 실패 조건을 정밀하게 만들 수 있지만 실제 시스템의 모든 동작을 재현하지는 못합니다.

예를 들어 메모리 repository로는 다음을 정확히 검증하기 어렵습니다.

- PostgreSQL의 실제 고유 제약
- 외래 키
- SQL 문법
- transaction isolation
- row lock
- JSON 타입
- bigint 표현
- timestamp 변환
- 실제 connection pool 동작

반대로 모든 단위 테스트가 실제 PostgreSQL을 사용하면 느려지고 실패 원인이 복잡해집니다.

따라서:

```text
도메인 계산
→ 가짜 또는 순수 함수

DB가 실제로 보장해야 하는 규칙
→ 실제 PostgreSQL
```

처럼 위험에 따라 나눕니다.

## 실제 데이터베이스 테스트

다음은 실제 PostgreSQL로 확인해야 합니다.

- 마이그레이션 문법
- 고유 제약
- 외래 키
- `CHECK` 제약
- 트랜잭션 commit·rollback
- 잠금
- 동시 수정
- 격리 수준에 따른 동작
- timestamp
- JSON/JSONB
- bigint
- SQL 함수와 연산자

### 빈 데이터베이스에서 마이그레이션을 검증합니다

이미 개발 데이터가 들어 있는 DB에서만 마이그레이션을 실행하면 누락된 초기 스키마나 순서 의존성을 놓칠 수 있습니다.

테스트에서는 가능하면:

```text
빈 DB
→ 첫 migration부터 전부 실행
→ 현재 스키마 완성
```

경로를 확인합니다.

필요하면 이전 버전 스키마에서 다음 버전으로 올라가는 경로도 별도로 검사합니다.

## 테스트 데이터는 서로 충돌하지 않게 합니다

병렬 테스트가 다음 값을 공유하면 충돌할 수 있습니다.

```text
user@example.com
board id = fixed
slug = test
```

각 테스트가 고유한 데이터를 생성합니다.

예:

```ts
const email = `user-${crypto.randomUUID()}@example.test`;
```

또는 테스트별 DB schema, transaction rollback, 별도 database를 사용할 수 있습니다.

중요한 것은 한 테스트의 데이터가 다른 테스트 성공 여부에 영향을 주지 않는 것입니다.

## 트랜잭션 롤백을 직접 검사합니다

예를 들어 두 작업이 하나의 트랜잭션이어야 한다면 두 번째 작업을 의도적으로 실패시킵니다.

```text
BEGIN

좌석 예약 생성
결제 기록 생성 실패

ROLLBACK
```

그 뒤 DB를 직접 확인합니다.

```text
좌석 예약도 남지 않아야 함
결제 기록도 없어야 함
```

서비스 함수가 오류를 던졌다는 사실만 검사하면 실제 DB 상태가 롤백되었는지는 증명되지 않습니다.

## 경쟁 조건 테스트

경쟁 조건은 순차 테스트로는 발견하기 어렵습니다.

예를 들어 한 좌석을 두 사용자가 동시에 예약한다고 가정합니다.

```text
request A ─┐
           ├─→ 같은 seat_id 예약
request B ─┘
```

원하는 결과:

```text
둘 중 하나만 성공
다른 하나는 충돌
DB에는 예약 하나만 존재
```

테스트에서는 두 작업을 최대한 겹치게 시작합니다.

```ts
const [a, b] = await Promise.allSettled([
  reserveSeat(seatId, userA),
  reserveSeat(seatId, userB)
]);
```

그러나 `Promise.all()`만 썼다고 실제 DB 경쟁이 반드시 원하는 지점에서 발생하는 것은 아닙니다.

정확한 경쟁 시점이 중요하다면 테스트 전용 barrier나 hook으로 두 요청을 같은 단계에 멈춘 뒤 동시에 진행시키는 방식이 더 결정적입니다.

개념적으로:

```text
A: 현재 상태 확인 ─┐
                   ├─ barrier
B: 현재 상태 확인 ─┘
                   ↓
             동시에 다음 단계 진행
```

목적은 "운 좋게 경쟁이 발생하기를 기다리는 것"이 아니라 **경쟁 조건을 반복해서 재현하는 것**입니다.

## WebSocket 테스트

실시간 동작은 함수 하나만 호출해서는 다음 문제를 발견하기 어렵습니다.

- 실제 handshake
- 연결별 상태
- 방 참가
- 방별 broadcast
- 연결 종료
- 재연결
- message ordering
- heartbeat
- socket cleanup

따라서 중요한 흐름은 실제 WebSocket 연결을 두 개 이상 만들어 검사합니다.

```text
A와 B 연결
→ 같은 방 참가
→ 둘 다 snapshot 수신
→ A가 최종 변경 전송
→ A와 B가 같은 sequence의 patch 수신
→ B 연결 종료
→ B 재연결
→ B가 최신 snapshot 수신
```

## 첫 메시지를 가정하지 않습니다

실시간 연결에는 다음 메시지가 끼어들 수 있습니다.

```text
heartbeat
presence
snapshot
patch
server notice
```

따라서 다음처럼 쓰면 취약합니다.

```ts
const message = await nextMessage(socket);
expect(message.type).toBe("board.patch");
```

대신 원하는 조건을 만족하는 메시지를 기다립니다.

```ts
const patch = await waitForMessage(
  socket,
  message =>
    message.type === "board.patch" &&
    message.sequence === expectedSequence
);
```

이 helper는 성공·실패·timeout 모든 경로에서 이벤트 리스너와 timer를 제거해야 합니다.

## WebSocket 테스트의 timeout은 실패 상한입니다

timeout은 "정상적으로 이 시간만큼 기다린다"가 아니라 **테스트가 영원히 멈추지 않도록 하는 상한**으로 사용합니다.

좋은 흐름:

```text
원하는 메시지가 오면 즉시 성공
일정 시간 안에 안 오면 실패
```

나쁜 흐름:

```text
무조건 2초 sleep
→ 그 뒤 상태 확인
```

첫 번째는 빠르고 원인이 명확하며, 두 번째는 테스트 시간을 늘리고 환경에 따라 간헐적으로 실패합니다.

## 브라우저 테스트

실제 브라우저에서만 확인할 수 있는 문제가 있습니다.

- 키보드 포커스
- 폼 기본 동작
- URL 변경
- 방문 기록
- 뒤로/앞으로 가기
- CSS overflow
- 실제 viewport
- 동적 경로 직접 접근
- hydration
- 브라우저 이벤트
- 쿠키
- CORS
- Canvas 포인터 좌표
- 모바일 viewport
- 실제 navigation

이런 문제는 jsdom 기반 컴포넌트 테스트만으로 충분하지 않을 수 있습니다.

## 브라우저 요소는 사용자 기준으로 찾습니다

Playwright에서도 가능한 경우:

- role
- accessible name
- label
- 보이는 텍스트

를 우선합니다.

예:

```ts
await page
  .getByRole("button", { name: "저장" })
  .click();
```

다음 선택자는 DOM 구조와 CSS 리팩터링에 지나치게 결합될 수 있습니다.

```ts
page.locator(".toolbar > div:nth-child(2) > button")
```

테스트가 사용자가 인식하는 의미와 가까울수록 구현 변경에 덜 취약합니다.

## 고정된 `waitForTimeout`을 피합니다

다음 테스트는 환경 속도에 의존합니다.

```ts
await page.waitForTimeout(1000);
expect(await page.textContent(...)).toBe("완료");
```

빠른 환경에서는 불필요하게 기다리고, 느린 환경에서는 1초가 부족할 수 있습니다.

대신 실제 조건을 기다립니다.

```ts
await expect(
  page.getByRole("status")
).toHaveText("저장됨");
```

Playwright의 assertion은 일정 시간 동안 조건이 만족되는지 재시도하므로 비동기 UI에 더 적합합니다.

## 브라우저 직접 접근도 검사합니다

SPA 내부 링크 클릭만 검사하면 서버 라우팅이나 배포 설정 문제를 놓칠 수 있습니다.

예:

```text
앱 내부에서 /boards/123 이동
→ 성공

브라우저 주소창에서 /boards/123 직접 접근
→ 404
```

따라서 중요한 동적 경로는 새 페이지에서 직접 열어 봅니다.

```ts
await page.goto("/boards/123");
```

이 테스트는 클라이언트 라우팅과 서버 측 경로 처리의 차이를 드러냅니다.

## 응답 순서 역전

검색이나 자동완성에서는 먼저 보낸 요청이 나중에 완료될 수 있습니다.

예:

```text
query=a     → 요청 A
query=beta  → 요청 B

완료 순서:
B 먼저
A 나중
```

최종 화면에는 최신 입력인 `beta` 결과가 남아야 합니다.

테스트는 두 요청의 완료 시점을 직접 제어합니다.

```text
A 시작
B 시작
B 완료
→ beta 결과 표시
A 완료
→ beta 결과가 그대로 남아야 함
```

이 테스트의 목적은 소스 코드에 `AbortController`라는 문자열이 있는지 확인하는 것이 아닙니다.

구현은 다음 중 어느 방식이어도 됩니다.

- 이전 요청 취소
- request id 비교
- 최신 query 비교
- 응답 version 비교

테스트는 오직 다음 결과를 검사합니다.

```text
늦게 도착한 오래된 응답이 최신 화면을 덮어쓰지 않는다
```

## 타입 검사와 런타임 검사는 다릅니다

각 검사 단계가 보장하는 것은 다릅니다.

```text
타입 검사
→ 정적 타입 오류
→ 일부 import/type 연결 오류

단위·통합 테스트
→ 실제 실행 중 동작
→ 오류 처리
→ 상태 변화

프로덕션 빌드
→ 프레임워크 컴파일
→ 서버/브라우저 번들 분리
→ 환경별 import 문제

E2E
→ 실제 프로세스
→ 네트워크
→ 브라우저
→ 전체 조립
```

하나가 통과했다고 다른 단계까지 증명되지는 않습니다.

예를 들어 TypeScript가 통과해도 다음은 여전히 실패할 수 있습니다.

```text
Zod가 런타임 입력을 잘못 허용
SQL 문법 오류
Next.js 서버 모듈을 클라이언트가 import
브라우저에서 hydration 오류
CORS 설정 오류
```

## 프로덕션 빌드를 별도 검사합니다

개발 서버는 편의를 위해 일부 문제를 늦게 발견하거나 다른 경로로 처리할 수 있습니다.

프로덕션 빌드는 특히 다음 문제를 찾는 데 중요합니다.

- 서버 전용 모듈의 클라이언트 import
- 브라우저 전용 API의 서버 실행
- 환경 변수 누락
- 번들 시점의 동적 import 문제
- 프레임워크 route 설정 오류
- production-only 최적화 문제

따라서 CI에서 테스트 성공과 별개로 프로덕션 빌드를 실행합니다.

## 테스트 순서를 독립적으로 만듭니다

다음 구조는 위험합니다.

```text
test 1: 사용자 생성
test 2: test 1 사용자가 있다고 가정
test 3: test 2가 만든 보드를 사용
```

한 테스트만 단독으로 실행하면 실패하기 때문입니다.

각 테스트는 가능한 한 자신의 준비 데이터를 직접 만듭니다.

```text
arrange
→ act
→ assert
→ cleanup
```

테스트 순서를 바꿔도 결과가 같아야 합니다.

## 잘못된 구현을 넣어 봅니다

테스트가 통과한다는 사실만으로 좋은 테스트라고 할 수 없습니다. 테스트가 실제로 실패해야 할 구현을 거부하는지 확인해야 합니다.

예를 들어 다음 변경을 잠시 적용합니다.

- 레이블 제거
- `popstate` 처리 제거
- 버전 조건 제거
- 로그아웃에서 서버 세션 삭제 제거
- `viewer` 쓰기 허용
- WebSocket 방 정리 코드 제거
- 고유 제약 제거
- 트랜잭션 rollback 제거
- 응답 순서 보호 제거

관련 테스트가 반드시 실패해야 합니다.

이것은 수동으로도 할 수 있고, 더 체계적으로는 mutation testing 도구를 사용할 수도 있습니다.

핵심 질문은 다음입니다.

```text
"이 버그를 실제로 넣었을 때 이 테스트가 실패하는가?"
```

## 테스트가 너무 많은 내부 구현을 검사하는지 확인합니다

다음 테스트는 구현을 바꾸면 쉽게 깨질 수 있습니다.

```text
helper가 정확히 두 번 호출됨
특정 private 함수가 호출됨
state 변수 이름이 특정 값임
DOM 클래스가 특정 문자열임
```

이런 검사가 정말 제품 동작의 일부인지 확인합니다.

내부 호출 횟수가 중요하지 않다면 최종 결과를 검사하는 편이 낫습니다.

예:

```text
sendEmail()이 정확히 한 번 호출됨
```

이 요구가 실제로 중요한 경우도 있습니다. 예를 들어 중복 결제나 중복 이메일처럼 외부 부작용 횟수가 제품 요구사항이라면 호출 횟수 자체가 관찰 가능한 동작입니다.

즉 "내부 호출을 절대 검사하지 않는다"가 아니라 **사용자 또는 외부 시스템에 의미가 있는 결과인지**를 기준으로 판단합니다.

## 간헐적 실패 줄이기

간헐적 테스트는 코드가 틀렸는지 테스트 환경이 흔들렸는지 구분하기 어렵게 만듭니다.

다음 원칙을 사용합니다.

- 고정 대기 대신 관찰 가능한 결과를 기다립니다.
- 현재 시각을 고정하거나 주입합니다.
- 난수를 고정하거나 테스트별 고유 값으로 만듭니다.
- 네트워크 완료 순서를 테스트가 직접 제어합니다.
- 고정 포트를 여러 테스트가 공유하지 않습니다.
- 테스트마다 고유 데이터를 사용합니다.
- 파일 경로나 임시 디렉터리를 공유하지 않습니다.
- 서버, 타이머, 소켓, DB pool과 브라우저를 `finally`에서 닫습니다.
- 경쟁 조건은 barrier 등으로 의도적으로 재현합니다.
- 외부 인터넷에 의존하지 않습니다.
- 실패 메시지에 기대값과 실제값을 포함합니다.

## 재시도는 원인을 숨길 수 있습니다

CI에서 실패한 테스트를 자동 재시도하면 일시적인 환경 문제를 완화할 수는 있지만, 반복 재시도로 간헐적 실패를 숨기면 안 됩니다.

예:

```text
첫 실행 실패
두 번째 실행 성공
→ 전체 성공 처리
```

만 반복되면 실제 race condition이나 cleanup 문제를 장기간 놓칠 수 있습니다.

재시도를 사용한다면:

- 재시도 횟수를 제한하고
- 최초 실패도 기록하며
- 어떤 테스트가 반복해서 flaky한지 추적합니다.

재시도는 안정적인 테스트 설계를 대신하지 않습니다.

## 실패 메시지를 진단 가능하게 만듭니다

다음 메시지는 정보가 부족합니다.

```text
expected true, received false
```

가능하면 도메인 맥락을 남깁니다.

예:

```text
expected:
  seat 42 reservation count = 1

received:
  seat 42 reservation count = 2
```

WebSocket이라면:

```text
expected next sequence: 121
received sequence: 123
received messages: [...]
```

경쟁 조건이라면:

```text
request A result: 201
request B result: 201
database rows: 2
```

처럼 실패 시 원인을 찾는 데 필요한 정보를 남깁니다.

## 로그와 디버깅 정보는 실패할 때만 충분히 남깁니다

모든 성공 테스트에서 방대한 로그를 출력하면 CI 로그가 읽기 어려워집니다.

다음 정보는 실패 시 보존하는 편이 유용합니다.

- HTTP 요청·응답 요약
- WebSocket 최근 메시지
- 현재 DB 핵심 행
- 브라우저 screenshot
- 브라우저 console error
- network error
- 현재 URL
- 관련 request id / operation id / sequence

성공 경로에서는 로그를 최소화하고, 실패 경로에서 진단 자료를 확보합니다.

## 테스트 피라미드를 숫자 규칙으로 고정하지 않습니다

"단위 테스트 70%, 통합 테스트 20%, E2E 10%" 같은 비율은 절대 규칙이 아닙니다.

중요한 기준은:

```text
이 위험을 가장 싸고 정확하게 재현하는 테스트는 무엇인가?
```

입니다.

예를 들어 DB 경쟁 조건이 핵심인 서비스는 실제 PostgreSQL 테스트 비중이 높을 수 있습니다. Canvas 상호작용이 핵심인 앱은 브라우저 테스트가 더 중요할 수 있습니다.

테스트 계층의 목적은 특정 비율을 맞추는 것이 아니라 **빠른 피드백과 실제 시스템 신뢰성 사이의 균형**입니다.

## CI 실행 순서 예시

빠른 실패를 먼저 찾고 비싼 검사를 뒤에 둘 수 있습니다.

```text
1. lint
2. typecheck
3. unit/schema/component tests
4. API tests
5. database integration tests
6. production build
7. WebSocket integration tests
8. browser E2E
```

프로젝트에 따라 순서는 달라질 수 있습니다.

예를 들어 빌드가 매우 빠르고 import 오류가 자주 난다면 더 앞에 둘 수 있습니다.

중요한 것은 각 단계가 무엇을 검증하는지 구분하고, 한 단계의 성공으로 다른 단계를 생략하지 않는 것입니다.

## 흔한 실수

- 모든 기능을 하나의 E2E 테스트에 넣습니다.
- 계산 로직 하나를 확인하려고 브라우저까지 띄웁니다.
- CSS 선택자와 내부 클래스에 테스트를 결합합니다.
- private 구현을 테스트하려고 공개 API를 왜곡합니다.
- 정상 입력만 테스트하고 경계값과 실패 입력을 검사하지 않습니다.
- 실제 PostgreSQL 동작이 중요한데 메모리 저장소만 사용합니다.
- 실제 WebSocket 연결이 중요한데 이벤트 emitter mock만 사용합니다.
- `Promise.all()`만 사용하면 경쟁 조건이 항상 재현된다고 가정합니다.
- DB rollback을 예외 발생 여부만 보고 판단하고 실제 저장 상태는 확인하지 않습니다.
- WebSocket의 첫 메시지가 원하는 메시지라고 가정합니다.
- 고정된 시간만 기다립니다.
- timeout을 정상 동기화 수단으로 사용합니다.
- 타입 검사를 런타임 입력 검증으로 간주합니다.
- 개발 서버가 뜬다는 이유로 프로덕션 빌드를 생략합니다.
- E2E 내부 링크 이동만 검사하고 동적 경로 직접 접근은 검사하지 않습니다.
- 테스트가 서로의 데이터와 실행 순서에 의존합니다.
- 테스트 뒤 서버, 소켓, timer, observer, DB pool과 브라우저를 남깁니다.
- flaky 테스트를 재시도만 늘려 숨깁니다.
- 구현에 버그를 넣어도 테스트가 계속 통과하는지 확인하지 않습니다.
- 실패 메시지가 실제 원인을 찾는 데 필요한 상태를 보여 주지 않습니다.

## 완료 기준

- 각 위험이 처음 드러나는 가장 짧고 적절한 테스트 계층을 선택합니다.
- 테스트 이름이 내부 구현보다 관찰 가능한 결과를 설명합니다.
- 정상·실패·경계값·최댓값을 반복해서 재현합니다.
- 시각, 난수와 비동기 완료 순서를 테스트가 제어할 수 있습니다.
- 실제 PostgreSQL이 필요한 제약·트랜잭션·잠금·경쟁 조건을 실제 DB로 검사합니다.
- 경쟁 조건을 우연에 맡기지 않고 반복 가능한 방식으로 재현합니다.
- WebSocket은 실제 연결을 사용해 방 전송, sequence, 종료와 재연결을 검사합니다.
- 브라우저에서 포커스, 라우팅, history, CSS, Canvas처럼 실제 브라우저가 필요한 동작을 검사합니다.
- 고정 sleep 대신 관찰 가능한 결과를 기다립니다.
- 타입 검사, 런타임 테스트, 프로덕션 빌드와 E2E를 별도 단계로 실행합니다.
- 각 테스트는 다른 테스트의 실행 순서와 데이터에 의존하지 않습니다.
- 테스트가 만든 서버, timer, socket, DB pool과 브라우저를 항상 정리합니다.
- 의도적으로 잘못된 구현을 넣었을 때 관련 테스트가 실패합니다.
- 간헐적 실패를 재시도만으로 숨기지 않습니다.
- 실패했을 때 원인을 추적할 수 있는 진단 정보를 제공합니다.

## 연결 exercise

일곱 competency exercise는 각기 다른 테스트를 포함합니다. 특히 [`seat-reservation`](../../exercises/seat-reservation/README.md)은 PostgreSQL 경쟁과 롤백을, [`realtime-board`](../../exercises/realtime-board/README.md)는 두 WebSocket 연결과 종료를 검사합니다.
