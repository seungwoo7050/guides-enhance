# Project Access API

프로젝트 조회와 제목 변경 API에 인증, URL 권한, 객체 소유권, 요청 검증, CSRF를 적용한 Spring Security 예제입니다. 인증 실패와 권한 거절은 `application/problem+json` 형식으로 구분해 반환합니다.

## 주요 기능

- HTTP Basic을 사용하는 메모리 내 사용자 두 명을 제공합니다.
- 인증되지 않은 요청은 `401 AUTHENTICATION_REQUIRED`로 거부합니다.
- `@PreAuthorize`에서 인증 사용자와 프로젝트 소유자를 비교합니다.
- 제목 변경 요청에 기본 CSRF 보호를 유지합니다.
- 인증 실패와 권한 부족을 각각 401과 403으로 반환합니다.
- MockMvc 테스트로 인증, 소유권, CSRF, 요청 본문 검증을 확인합니다.

## 구성

- `ProjectStore`는 프로젝트 상태와 소유자를 메모리에 보관합니다.
- `ProjectAccess`는 인증 사용자 이름과 저장된 소유자를 비교합니다.
- `ProjectController`는 요청 본문 검증과 객체 권한 검사를 통과한 뒤에만 제목을 바꿉니다.
- `SecurityConfiguration`은 사용자, 비밀번호 인코더, method security, URL 권한, CSRF, 401·403 응답을 설정합니다.

## 요구 사항

- JDK 21
- Maven 3.9 이상

## 빌드와 테스트

```sh
mvn clean test
mvn clean package
```

테스트는 다음 내용을 확인합니다.

- 인증 없이 프로젝트를 조회하면 401을 반환합니다.
- 프로젝트 소유자가 아닌 사용자의 변경 요청은 403으로 거부됩니다.
- 소유자라도 CSRF token이 없으면 제목을 바꿀 수 없습니다.
- 소유자와 CSRF token을 함께 제공하면 제목 변경이 성공합니다.
- 빈 제목은 400으로 거부되고 저장 상태가 바뀌지 않습니다.

## 실행

```sh
mvn spring-boot:run
```

프로젝트 조회 예시:

```sh
curl -i \
  -u owner:owner-password \
  http://localhost:8080/api/projects/1
```

제목 변경 endpoint는 CSRF 보호를 유지하므로 Basic Auth만 넣은 단순 `curl` POST는 거부됩니다. 실제 호출자는 CSRF token을 받아 다시 보내는 방법을 갖춰야 합니다.

기본 계정:

| 사용자 이름 | 비밀번호 | 역할 | 소유권 |
|---|---|---|---|
| `owner` | `owner-password` | `EDITOR` | project `1` 소유자 |
| `viewer` | `viewer-password` | `VIEWER` | 소유 프로젝트 없음 |

## 주요 설계 판단

- URL 규칙은 인증된 요청만 Controller로 보내고, 객체 소유권은 저장된 프로젝트를 조회한 뒤 별도로 판단합니다.
- 요청 body의 사용자 정보는 신뢰하지 않고 `Authentication`의 이름을 사용합니다.
- CSRF를 비활성화하지 않아 인증된 사용자의 cookie나 credential을 악용한 변경 요청을 별도로 거부합니다.
- 401과 403에 다른 `errorCode`를 사용해 클라이언트와 운영 로그가 원인을 구분할 수 있게 합니다.

## 구현 순서

| 순서 | 구현 내용 | 기준 파일 |
|---:|---|---|
| 0 | 독립 실행 가능한 보안 API 구성 | `pom.xml` |
| 1 | 프로젝트 상태와 소유자 보관 | `src/main/java/dev/guides/spring/security/ProjectStore.java` |
| 2 | 인증 사용자와 프로젝트 소유자 비교 | `src/main/java/dev/guides/spring/security/ProjectAccess.java` |
| 3 | 입력 검증과 소유권 확인 후 제목 변경 | `src/main/java/dev/guides/spring/security/ProjectController.java` |
| 4 | 사용자·비밀번호 인코더·method security 구성 | `src/main/java/dev/guides/spring/security/SecurityConfiguration.java` |
| 4-1 | 요청 인증·CSRF·401·403 응답 구성 | `src/main/java/dev/guides/spring/security/SecurityConfiguration.java` |

## 범위와 제한

- 사용자와 프로젝트는 메모리에만 저장되며 애플리케이션을 재시작하면 초기화됩니다.
- session, JWT, OAuth2 인증은 포함하지 않습니다.
- 운영용 비밀값 관리, 사용자 등록, 비밀번호 변경 기능은 포함하지 않습니다.
- CSRF token 발급 endpoint나 cookie 저장소는 제공하지 않습니다. 변경 요청은 MockMvc 테스트에서 검증하며 실제 배포에서는 token 전달 방식을 추가해야 합니다.
