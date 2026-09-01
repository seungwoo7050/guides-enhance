# Session Access Control

Fastify에서 서버 세션, 브라우저 쿠키, 정확한 Origin 검사와 리소스별 권한을 구현한 프로젝트입니다.

이 프로젝트는 다음 세 질문을 서로 분리합니다.

```text
누구인가?
→ authentication

로그인 상태에서 이 요청을 보낸 것이 맞는가?
→ session / cookie / Origin 검사

이 사용자가 이 리소스에 이 작업을 할 수 있는가?
→ authorization
```

로그인 여부와 작업 권한을 같은 것으로 취급하지 않으며, 로그아웃할 때 서버 세션과 브라우저 쿠키를 함께 폐기합니다.

## 주요 기능

- 메모리 사용자와 만료되는 서버 세션
- `HttpOnly`, `SameSite=Lax`, 일관된 `Path`를 가진 쿠키
- 상태 변경 요청의 정확한 Origin 허용 목록 검사
- 인증 실패 401과 권한 부족 403 구분
- 본인 또는 관리자만 프로필 변경
- 관리자만 전체 사용자 목록 조회
- 애플리케이션 인스턴스별 독립 저장소
- 브라우저 쿠키와 서버 세션의 동일한 만료 시간

## 설치와 실행

```sh
pnpm install
pnpm typecheck
pnpm test
pnpm dev
```

환경 변수:

```text
PORT=4000
ALLOWED_ORIGINS=http://localhost:3000
NODE_ENV=development
```

`ALLOWED_ORIGINS`에는 쉼표로 여러 origin을 지정할 수 있습니다.

Origin은 다음 전체 값을 하나의 단위로 비교합니다.

```text
scheme://host:port
```

예:

```text
http://localhost:3000
```

접두사나 접미사만 비교하지 않습니다.

## API

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/auth/login` | `alpha` 또는 `admin`으로 로그인 |
| `POST` | `/auth/logout` | 서버 세션 폐기와 쿠키 삭제 |
| `GET` | `/me` | 현재 사용자 조회 |
| `PATCH` | `/profiles/:id` | 본인 또는 관리자의 표시 이름 변경 |
| `GET` | `/admin/users` | 관리자 전용 사용자 목록 |

쿠키가 있는 `POST`, `PUT`, `PATCH`, `DELETE` 요청에는 허용한 `Origin`이 필요합니다.

## 세션과 쿠키의 역할

브라우저 쿠키는 세션 토큰을 서버로 전달하는 수단입니다.

```text
브라우저 쿠키
→ session token
→ 서버 session store 조회
→ user identity 확인
```

클라이언트가 다음처럼 역할을 함께 보내더라도 신뢰하지 않습니다.

```json
{
  "role": "admin"
}
```

실제 역할은 서버가 세션 토큰으로 찾은 사용자 정보에서 결정합니다.

```text
클라이언트가 주장한 identity/role
→ 신뢰하지 않음

서버 session store가 찾은 identity/role
→ 권한 판정 기준
```

## 인증과 권한

다음 두 실패를 구분합니다.

### 401 Unauthorized

현재 요청이 인증되지 않았습니다.

예:

```text
세션 쿠키 없음
세션 토큰이 존재하지 않음
세션 만료
```

### 403 Forbidden

누구인지는 알지만 해당 작업 권한이 없습니다.

예:

```text
일반 사용자가 다른 사용자 프로필 수정
일반 사용자가 관리자 목록 조회
```

이 둘을 구분해야 클라이언트도 "로그인이 필요한가"와 "로그인했지만 권한이 없는가"를 다르게 처리할 수 있습니다.

## 리소스별 권한

프로필 수정은 URL에 들어 있는 `:id`만 믿지 않습니다.

다음 요청을 생각합니다.

```text
PATCH /profiles/user-b
```

현재 로그인 사용자가 `user-a`라면 서버는 다음을 확인합니다.

```text
currentUser.id == target.id
또는
currentUser.role == admin
```

즉 요청 URL의 대상 ID와 현재 인증된 사용자 ID를 비교합니다.

```text
인증
→ 현재 사용자 확보
→ 대상 리소스 확인
→ owner/admin 규칙 확인
→ 수정
```

## Origin 검사

쿠키 기반 인증에서는 브라우저가 쿠키를 자동으로 보낼 수 있으므로, 상태 변경 요청은 예상한 웹 애플리케이션에서 시작된 것인지 추가로 검사합니다.

이 프로젝트는 허용 origin과 정확한 문자열 비교를 사용합니다.

안전하지 않은 비교 예:

```text
origin.startsWith("http://localhost:3000")
origin.endsWith("example.com")
```

이런 방식은 예상하지 않은 문자열도 통과시킬 수 있습니다.

대신 파싱된 origin 전체를 허용 목록의 값과 비교합니다.

또한 쿠키가 있는 상태 변경 요청에 `Origin`이 없다면 허용하지 않습니다.

`Origin` 검사는 사용자 인증 자체를 대신하지 않습니다. 인증과 Origin 검사는 별도의 단계입니다.

## 쿠키 속성

세션 쿠키는 다음 속성을 사용합니다.

- `HttpOnly`
- `SameSite=Lax`
- 일관된 `Path`
- 서버 세션과 일치하는 만료 시간

### `HttpOnly`

브라우저 JavaScript에서 쿠키 값을 직접 읽는 것을 제한합니다.

### `SameSite=Lax`

일부 교차 사이트 요청에서 쿠키 자동 전송을 제한하는 브라우저 정책을 사용합니다.

하지만 `SameSite` 하나만으로 애플리케이션의 모든 CSRF 요구가 해결된다고 가정하지 않고, 이 프로젝트는 상태 변경 요청에서 Origin도 검사합니다.

### `Path`

로그인 때 만든 쿠키와 로그아웃 때 삭제하는 쿠키의 `Path`가 일치해야 브라우저가 같은 쿠키를 대상으로 처리할 수 있습니다.

## 로그아웃

로그아웃은 브라우저 쿠키를 비우는 작업만이 아닙니다.

원하는 흐름:

```text
logout 요청
→ 서버 session store에서 token 폐기
→ 응답으로 브라우저 cookie 삭제
```

둘 중 하나만 수행하면 문제가 생깁니다.

### 쿠키만 삭제

```text
브라우저에는 token 없음
하지만 서버 session은 여전히 유효
```

토큰 값이 다른 경로에서 유출되었다면 여전히 사용할 수 있습니다.

### 서버 세션만 삭제

```text
브라우저 쿠키는 남음
하지만 서버에서 더 이상 유효하지 않음
```

보안상 서버에서는 거부되더라도 브라우저 상태가 혼란스러울 수 있습니다.

따라서 둘을 함께 정리합니다.

## 세션 만료

서버 세션 만료 시간과 브라우저 쿠키 만료 시간이 일관되어야 합니다.

```text
브라우저 쿠키 30분
서버 세션 24시간
```

처럼 크게 어긋나면 한쪽이 다른 쪽보다 오래 살아 사용자가 예상하기 어려운 상태가 생길 수 있습니다.

테스트는 서버 세션이 쿠키보다 오래 유지되는 잘못된 구현을 검출합니다.

## 애플리케이션 인스턴스 격리

저장소는 애플리케이션 인스턴스마다 별도 `Map`을 사용합니다.

따라서:

```text
app A 로그인
→ app A store에 session 생성

app B
→ 같은 전역 Map을 자동 공유하지 않음
```

이 구조는 테스트 간 상태 누수를 막고, 애플리케이션 의존성을 명시적으로 주입하는 습관을 확인합니다.

## 테스트

테스트는 다음 잘못된 구현을 검출합니다.

- 로그인하지 않은 요청과 권한 부족을 같은 상태로 반환함
- URL의 사용자 ID만 믿고 다른 사용자 프로필을 변경함
- Origin을 접두사·접미사로 비교함
- Origin이 없는 쿠키 기반 상태 변경을 허용함
- 브라우저 쿠키만 삭제하고 서버 세션을 남김
- 서로 다른 Fastify 인스턴스가 세션을 공유함
- 서버 세션이 쿠키보다 오래 유지됨

테스트가 확인하는 핵심은 "로그인 기능이 있다"가 아니라 **인증, 요청 출처, 리소스 권한과 세션 수명이 서로 다른 책임으로 올바르게 연결되어 있는가**입니다.

## 코드 구성

- `src/contracts.ts`: 사용자 타입과 로그인·프로필 입력 스키마
- `src/store.ts`: 사용자와 만료 세션을 저장하는 메모리 구현
- `src/app.ts`: 쿠키, CORS, 인증과 권한 라우트
- `src/server.ts`: 저장소와 허용 origin을 선택하고 포트 열기

## 주요 선택

- 세션 토큰으로 사용자 정보를 찾는 작업은 서버 저장소만 수행합니다. 클라이언트가 보낸 역할은 사용하지 않습니다.
- 인증된 상태 변경은 라우트 실행 전에 정확한 Origin 문자열을 확인합니다.
- 프로필 수정은 현재 사용자 ID와 대상 ID를 비교하고, 다르면 관리자 역할을 확인합니다.
- 저장소는 인스턴스마다 별도 `Map`을 사용합니다. 테스트나 여러 애플리케이션이 세션을 공유하지 않습니다.
- 로그아웃은 서버 토큰 폐기와 브라우저 쿠키 삭제를 하나의 사용자 동작으로 처리합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Identity and input schemas | `src/contracts.ts` |
| 2 | Per-app users and sessions | `src/store.ts` |
| 3 | Fastify plugins and injected store | `src/app.ts` |
| 4 | Exact Origin check before mutation | `src/app.ts` |
| 5 | Session-token identity lookup | `src/app.ts` |
| 6 | Session and cookie issuance | `src/app.ts` |
| 7 | Server and browser logout cleanup | `src/app.ts` |
| 8 | Profile owner or admin check | `src/app.ts` |
| 9 | Admin-only user listing | `src/app.ts` |
| 10 | Network entry point | `src/server.ts` |

입력 계약과 저장소를 먼저 만든 뒤, 요청 출처와 인증을 확인하고, 마지막에 리소스별 권한을 올리는 순서입니다. 이 순서를 따르면 "사용자가 누구인지 확인하는 단계"와 "무엇을 할 수 있는지 확인하는 단계"를 섞지 않게 됩니다.

## 범위와 제한

비밀번호 해시, 데이터베이스 저장, CSRF 토큰, 세션 토큰 다이제스트, 속도 제한과 다중 기기 관리 기능은 포함하지 않습니다. 메모리 저장소는 인증과 권한 판정 순서를 확인하기 위한 구현입니다.

따라서 실제 서비스의 전체 인증 시스템 예제가 아니라 다음 핵심 흐름을 좁게 학습합니다.

```text
server session
cookie
Origin
authentication
resource authorization
logout cleanup
```