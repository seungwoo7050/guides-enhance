# Session Access Control

Fastify에서 서버 세션, 브라우저 쿠키, 정확한 Origin 검사와 리소스별 권한을 구현한 프로젝트입니다. 로그인 여부와 작업 권한을 구분하고, 로그아웃할 때 서버 토큰과 브라우저 쿠키를 함께 폐기합니다.

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

## API

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/auth/login` | `alpha` 또는 `admin`으로 로그인 |
| `POST` | `/auth/logout` | 서버 세션 폐기와 쿠키 삭제 |
| `GET` | `/me` | 현재 사용자 조회 |
| `PATCH` | `/profiles/:id` | 본인 또는 관리자의 표시 이름 변경 |
| `GET` | `/admin/users` | 관리자 전용 사용자 목록 |

쿠키가 있는 `POST`, `PUT`, `PATCH`, `DELETE` 요청에는 허용한 `Origin`이 필요합니다.

## 테스트

테스트는 다음 잘못된 구현을 검출합니다.

- 로그인하지 않은 요청과 권한 부족을 같은 상태로 반환함
- URL의 사용자 ID만 믿고 다른 사용자 프로필을 변경함
- Origin을 접두사·접미사로 비교함
- Origin이 없는 쿠키 기반 상태 변경을 허용함
- 브라우저 쿠키만 삭제하고 서버 세션을 남김
- 서로 다른 Fastify 인스턴스가 세션을 공유함
- 서버 세션이 쿠키보다 오래 유지됨

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

## 범위와 제한

비밀번호 해시, 데이터베이스 저장, CSRF 토큰, 세션 토큰 다이제스트, 속도 제한과 다중 기기 관리 기능은 포함하지 않습니다. 메모리 저장소는 인증과 권한 판정 순서를 확인하기 위한 구현입니다.
