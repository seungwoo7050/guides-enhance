# 인증, 객체 권한과 CSRF

> 읽는 시점: 객체 소유권을 검사하거나 cookie 기반 인증으로 상태를 변경할 때

역할만 확인하면 되는 요청과 특정 객체의 소유자를 확인해야 하는 요청은 다릅니다. 또한 browser가 cookie를 자동으로 보내는 인증 방식에서는 사용자가 로그인되어 있다는 사실만으로 해당 변경 요청이 사용자의 의도에서 시작되었다고 볼 수 없습니다.

## URL 권한과 객체 권한을 나눕니다

URL 규칙은 endpoint 전체를 크게 제한합니다.

```text
GET  /api/projects/**  → 인증 사용자
POST /api/projects/**  → EDITOR 역할
/admin/**              → ADMIN 역할
```

그다음 application service나 method security가 실제 객체와 사용자의 관계를 검사합니다.

```text
project.ownerId == authentication.name
organization membership가 ACTIVE
요청한 operation을 현재 역할이 허용함
```

요청 body의 `ownerId`를 믿지 않습니다. actor는 인증 결과에서 가져오고, 대상 객체는 server가 조회한 뒤 소유권이나 소속 관계를 판단합니다.

자원 존재 여부를 숨겨야 하는 API에서는 권한 부족을 404로 반환할 수도 있습니다. 이런 선택은 endpoint마다 달라지지 않게 문서와 테스트로 고정합니다.

## 권한 확인과 상태 변경 사이의 경쟁을 고려합니다

권한을 확인한 뒤 데이터를 변경하기 전에 소유권이나 membership 상태가 바뀔 수 있습니다. 중요한 변경이라면 권한 판단에 필요한 데이터와 수정할 데이터를 같은 transaction에서 읽고 처리합니다.

Controller에서 한 번 확인한 뒤 별도 transaction의 service를 호출하면 두 단계 사이에 데이터가 바뀔 수 있습니다. method security는 호출 허용 여부만 판단하며 데이터베이스 동시성까지 해결하지는 않습니다. 필요하면 version, row lock, 조건부 update를 함께 사용합니다.

## cookie 인증에서는 CSRF 방어를 유지합니다

browser는 다른 origin의 페이지에서 시작한 요청에도 사용자의 cookie를 자동으로 붙일 수 있습니다. 따라서 session cookie로 인증하는 변경 요청은 CSRF token이나 같은 수준의 방어가 필요합니다.

- GET과 HEAD는 서버 상태를 바꾸지 않게 합니다.
- cookie 기반 POST, PUT, PATCH, DELETE는 CSRF token을 검사합니다.
- SameSite cookie는 보조 수단이며 모든 경우를 대신하지 않습니다.
- JSON API라는 이유만으로 CSRF를 끄지 않습니다.

HTTP Basic이나 bearer token을 browser가 자동으로 붙이는 방식으로 저장한다면 같은 위협이 생기는지 다시 확인해야 합니다. `csrf().disable()`을 사용할 때는 어떤 client가 credential을 보관하고 요청에 붙이는지 설명할 수 있어야 합니다.

## CORS는 인증과 CSRF를 대신하지 않습니다

CORS는 browser JavaScript가 다른 origin의 응답을 읽을 수 있는지 정합니다. server-to-server 요청, HTML form 전송, 자동 cookie 첨부를 모두 막지 않습니다.

허용 origin, method, header를 구체적으로 지정합니다. credential을 허용하면서 origin을 `*`로 두지 않습니다. preflight가 성공했다고 해서 실제 요청 권한까지 허용된 것은 아닙니다.

## 실패하는 요청을 직접 테스트합니다

보안 테스트는 성공 요청보다 거부 조건을 먼저 고정하는 편이 좋습니다.

- 인증 없는 요청은 401입니다.
- 인증했지만 역할이 부족하면 403입니다.
- 다른 사용자의 객체를 변경하면 403 또는 API에서 미리 정한 404입니다.
- cookie 기반 변경 요청에 CSRF token이 없으면 거부됩니다.
- 올바른 사용자와 CSRF token을 함께 보내면 성공합니다.
- body나 임의 header로 actor를 바꿀 수 없습니다.
- logout이나 만료 뒤 기존 session으로 접근할 수 없습니다.
- 오류 응답에 credential과 내부 예외가 포함되지 않습니다.

## Rewind가 필요한 징후

다음 문제가 생기면 이 문서를 다시 확인합니다.

- 인증 사용자라면 다른 사용자의 객체도 변경할 수 있습니다.
- URL 규칙은 닫혀 있지만 service를 직접 호출하면 권한 검사를 우회합니다.
- cookie 인증 API에서 CSRF를 이유 없이 비활성화했습니다.
- 401과 403이 같은 응답으로 처리됩니다.
- 권한을 확인한 직후 소유권이 바뀌면 잘못된 변경이 적용됩니다.

프로젝트 완료 뒤 보안 능력을 확인하려면 [`project-access-api`](../../exercises/project-access-api/)를 Guide 없이 구현합니다.
