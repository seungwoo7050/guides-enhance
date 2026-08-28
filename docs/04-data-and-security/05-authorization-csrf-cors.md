# 권한, CSRF와 CORS

로그인했다는 사실만으로 모든 데이터를 읽고 바꿀 수 있는 것은 아닙니다. 화면에서 버튼을 숨기는 것은 사용자에게 보이는 UI만 바꿉니다. 서버는 HTTP 요청과 WebSocket 메시지마다 현재 사용자와 대상 리소스를 다시 확인해야 합니다.

## 목표

- 인증과 권한 확인을 구분합니다.
- 역할과 리소스 소유권을 서버에서 검사합니다.
- 401·403과 존재를 숨기기 위한 404를 구분합니다.
- 쿠키 인증에서 CSRF를 방어합니다.
- CORS가 브라우저 응답 공개를 제어하는 규칙임을 설명합니다.
- 연결 중 역할이 바뀌어도 WebSocket 쓰기를 다시 검사합니다.

## 인증과 권한

```text
인증(authentication) → 누가 요청했는가
권한(authorization)  → 이 사용자가 이 작업을 할 수 있는가
```

| 역할 | 읽기 | 내용 수정 | 구성원 관리 | 삭제 |
|---|---:|---:|---:|---:|
| owner | 가능 | 가능 | 가능 | 가능 |
| editor | 가능 | 가능 | 불가 | 불가 |
| viewer | 가능 | 불가 | 불가 | 불가 |

실제 판정에는 계정 상태, 리소스 보관 여부와 현재 멤버십도 포함될 수 있습니다.

## 서버에서 한 규칙을 사용합니다

```ts
function assertCanEditNote(actor: Actor, membership: Membership, note: Note): void {
  if (actor.accountStatus !== "active") {
    throw new Forbidden("account_inactive");
  }
  if (note.archivedAt) throw new Conflict("note_archived");
  if (membership.role !== "owner" && membership.role !== "editor") {
    throw new Forbidden("note_write_forbidden");
  }
}
```

HTTP 라우트와 WebSocket 처리 코드에 서로 다른 역할 규칙을 복사하지 않습니다. 클라이언트가 보낸 역할은 믿지 않고 서버가 저장된 멤버십을 읽습니다.

## 조회할 때 사용자 조건을 포함합니다

```sql
select n.id, n.title, m.role
from notes as n
join note_members as m on m.note_id = n.id
where n.id = $1
  and m.user_id = $2;
```

먼저 모든 데이터를 읽은 뒤 권한을 확인하는 것보다 현재 사용자에게 보이는 행만 조회하면 불필요한 노출을 줄일 수 있습니다.

## 401, 403과 404

- `401`: 유효한 인증 정보가 없습니다.
- `403`: 사용자는 확인했지만 작업을 허용하지 않습니다.
- `404`: 리소스가 없거나 존재를 외부에 공개하지 않습니다.

비공개 리소스의 존재 자체를 숨겨야 하면 404를 사용할 수 있습니다. 관리 도구처럼 권한 부족을 명확히 알려야 하면 403이 적합할 수 있습니다. 선택한 규칙을 API 안에서 일관되게 사용합니다.

## 객체 수준 권한

```text
PATCH /notes/{noteId}
```

`noteId` 형식이 올바르다는 사실과 현재 사용자가 그 메모를 수정할 수 있다는 사실은 다릅니다. 목록에서 보였거나 화면에 수정 버튼이 있었다는 이유로 허용하지 않습니다.

## 역할 변경 규칙

역할 변경에는 내용 수정과 다른 조건이 필요합니다.

- 소유자만 역할을 변경할 수 있습니다.
- 마지막 소유자를 읽기 전용으로 바꿀 수 없습니다.
- 사용자가 자신의 권한을 임의로 높일 수 없습니다.
- 정지된 사용자를 초대하지 않습니다.
- 변경 전후 역할과 수행자를 기록합니다.
- 멤버십 변경과 감사 기록을 함께 커밋합니다.

## CSRF가 생기는 이유

브라우저는 다른 사이트에서 시작한 요청에도 대상 사이트의 쿠키를 자동으로 보낼 수 있습니다. 공격자 사이트가 쿠키 내용을 읽지 못해도 사용자의 인증 정보가 포함된 상태 변경 요청을 보낼 수 있습니다.

쿠키 인증의 상태 변경 요청에는 다음을 조합합니다.

1. 적절한 `SameSite` 쿠키
2. HTTPS와 `Secure`
3. 정확한 `Origin` 검사
4. 필요하면 CSRF 토큰
5. 상태를 바꾸는 GET 금지

## Origin 검사

```ts
function requireTrustedOrigin(origin: string | undefined, allowed: Set<string>): void {
  if (!origin || !allowed.has(origin)) {
    throw new Forbidden("untrusted_origin");
  }
}
```

접두사나 접미사 비교는 `https://trusted.example.attacker.test` 같은 주소를 잘못 허용할 수 있습니다. 정확한 origin 문자열 집합과 비교합니다. `Origin`이 없는 비브라우저 요청을 허용할지는 엔드포인트와 인증 방식별로 따로 정합니다.

## CSRF 토큰

서버 세션과 연결된 예측하기 어려운 토큰을 상태 변경 요청에 포함할 수 있습니다. 토큰은 다음 조건을 만족해야 합니다.

- 공격자 사이트에서 읽을 수 없습니다.
- 세션과 연결되거나 검증 가능한 서명이 있습니다.
- 안전한 비교를 사용합니다.
- 로그에 원문을 남기지 않습니다.
- 로그아웃이나 세션 교체 때 갱신합니다.

## CORS의 실제 역할

CORS는 브라우저가 다른 출처에서 받은 응답을 JavaScript에 보여 줄지 결정합니다. `curl`이나 서버 간 요청을 차단하지 않으며 인증과 권한을 대신하지 않습니다.

인증 정보를 포함한 요청에서는 와일드카드 출처를 사용할 수 없습니다.

```ts
const allowedOrigins = new Set([
  "https://app.example.com",
  "https://admin.example.com"
]);
```

요청의 `Origin`을 확인하지 않고 그대로 응답 헤더에 반영하지 않습니다. 허용할 메서드와 헤더도 필요한 범위로 제한합니다.

## WebSocket

업그레이드할 때 다음을 확인합니다.

- 정확한 `Origin`
- 세션 만료
- 계정 상태

연결 뒤 `board.join`을 받을 때 현재 멤버십을 확인합니다. 연결이 열린 동안 역할이 바뀔 수 있으므로 쓰기 메시지마다 현재 권한을 다시 확인하거나, 역할 변경 시 기존 연결을 무효화합니다.

## 검증 행렬

```text
인증 정보 없음           → 401
구성원이 아님            → 403 또는 정책상 404
viewer                   → 읽기 성공, 쓰기 거부
editor                   → 내용 수정 성공, 역할 변경 거부
owner                    → 허용된 관리 작업 성공
다른 사용자의 리소스 ID → 거부
신뢰하지 않는 Origin    → 거부
로그아웃한 세션          → 401
정지된 사용자의 세션    → 거부
```

HTTP와 WebSocket에 같은 역할 규칙을 적용합니다.

## 흔한 실수

- 화면에서 버튼을 숨긴 것으로 권한 검사를 끝냅니다.
- 클라이언트가 보낸 역할을 믿습니다.
- ID 형식 검사를 소유권 검사로 착각합니다.
- CORS를 인증 수단으로 설명합니다.
- 요청 Origin을 그대로 허용합니다.
- 쿠키 인증의 상태 변경 요청에 CSRF 방어가 없습니다.
- WebSocket 연결할 때만 권한을 확인합니다.

## 완료 기준

- 인증과 리소스별 권한 확인을 구분합니다.
- 401·403·404 중 선택한 응답의 이유를 설명합니다.
- 쿠키 인증에서 CSRF를 막는 방법과 CORS의 역할을 구분합니다.
- 역할과 소유권을 HTTP와 WebSocket에서 다시 검사합니다.
- 역할 변경과 관리자 작업에서 지켜야 할 조건을 설명합니다.

## 연결 exercise

[`session-access-control`](../../exercises/session-access-control/README.md)은 세션, 정확한 Origin, 소유권과 관리자 역할을 실제 요청으로 검사합니다.
