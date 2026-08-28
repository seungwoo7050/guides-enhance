# Spring MVC 검증과 ProblemDetail

> 읽는 시점: 모든 Spring Boot 백엔드 프로젝트를 시작하기 전

HTTP 입력 오류, 업무 규칙 위반, 외부 시스템 장애는 발생 위치와 처리 방법이 다릅니다. Controller의 `try-catch` 하나에서 모두 처리하면 클라이언트가 받는 응답과 내부 복구 방법을 구분하기 어려워집니다.

## 요청 DTO와 JPA entity를 분리합니다

요청 본문을 JPA entity로 직접 받지 않습니다.

```java
public record CreateProjectRequest(
    @NotBlank @Size(max = 120) String title,
    @NotNull URI source) {}

public record ProjectResponse(
    UUID id,
    String title,
    URI source) {}
```

요청 DTO는 JSON 필드와 HTTP 입력 조건을 표현합니다. entity는 데이터베이스에 저장할 값과 영속 상태의 수명을 표현합니다. application command가 따로 필요하면 Controller에서 명시적으로 변환합니다.

## 검증 시점을 세 가지로 나눕니다

### JSON 변환과 binding

잘못된 JSON, 지원하지 않는 media type, 숫자로 바꿀 수 없는 path variable은 MVC가 Controller를 호출하기 전에 거부합니다. 이 경우 application service가 호출되지 않아야 합니다.

### Bean Validation

빈 값, 문자열 길이, 숫자 범위처럼 현재 요청만으로 판단할 수 있는 조건은 DTO와 method parameter에 둡니다.

`@Valid @RequestBody`의 실패는 주로 `MethodArgumentNotValidException`으로 전달됩니다. `@RequestHeader @NotBlank`처럼 Controller method parameter에 직접 constraint를 붙이면 `HandlerMethodValidationException`이 발생할 수 있습니다. 두 경우를 같은 외부 오류 형식으로 바꾸려면 모두 처리해야 합니다.

```java
@ExceptionHandler({
    MethodArgumentNotValidException.class,
    HandlerMethodValidationException.class
})
ProblemDetail invalidRequest() {
  // ...
}
```

Spring MVC의 method validation을 사용할 때 Controller class에 `@Validated`를 추가해 AOP 검증과 중복시키지 않습니다. 실제 method signature에 따라 어떤 예외가 발생하는지 MockMvc 테스트로 확인합니다.

### 업무 규칙 검사

저장된 상태, 인증 사용자, 다른 객체의 값이 필요한 조건은 application service에서 검사합니다.

예를 들면 다음과 같습니다.

- 이미 처리된 요청인지 확인합니다.
- 현재 상태에서 변경할 수 있는지 검사합니다.
- 인증 사용자가 대상 객체를 수정할 수 있는지 확인합니다.
- 외부 판단 서비스가 요청을 허용했는지 확인합니다.

이 실패는 이름이 분명한 예외나 결과 타입으로 표현하고, repository나 HTTP client의 기술 예외를 그대로 Controller에 전달하지 않습니다.

## HTTP 상태와 `errorCode`를 함께 사용합니다

다음 표는 일반적인 출발점입니다.

| 원인 | HTTP 상태 | `errorCode` 예시 |
|---|---:|---|
| JSON·필드 형식 오류 | 400 | `INVALID_REQUEST` |
| 인증 정보 없음·실패 | 401 | `AUTHENTICATION_REQUIRED` |
| 권한 부족 | 403 | `ACCESS_DENIED` |
| 자원 없음 | 404 | `PROJECT_NOT_FOUND` |
| 현재 상태와 충돌 | 409 | `PROJECT_CONFLICT` |
| 의존 시스템 장애 | 503 | `DEPENDENCY_UNAVAILABLE` |

클라이언트가 상태 코드만으로 모든 세부 원인을 추측하게 하지 않습니다. `ProblemDetail`에 안정적인 `errorCode`를 넣고, 필요하면 필드별 오류와 요청 추적 식별자를 추가합니다.

```java
ProblemDetail problem = ProblemDetail.forStatusAndDetail(
    HttpStatus.CONFLICT,
    "현재 상태에서는 요청을 완료할 수 없습니다.");
problem.setProperty("errorCode", "PROJECT_CONFLICT");
```

예외 클래스 이름, SQL, 내부 host, stack trace, credential은 응답에 포함하지 않습니다.

## 예외 변환을 한곳에 모읍니다

`@RestControllerAdvice`는 외부에 공개하기로 한 애플리케이션 오류를 HTTP 응답으로 바꾸는 곳입니다. 예상하지 못한 예외를 모두 같은 메시지로 숨기는 용도로 사용하지 않습니다.

- repository의 기술 예외는 저장소를 호출하는 코드에서 application 의미로 바꿉니다.
- 외부 HTTP 오류는 client adapter에서 업무 거절과 통신 장애로 나눕니다.
- Controller는 `DataAccessException`, `RestClientException` 같은 기술 예외를 직접 알지 않게 합니다.
- 예상하지 못한 예외는 500으로 응답하되 자세한 원인은 서버 로그에 한 번만 기록합니다.

## MockMvc로 실제 HTTP 처리를 확인합니다

순수 service 테스트만으로는 JSON 변환, validation, exception advice가 실제로 연결되었는지 알 수 없습니다. MockMvc 테스트는 다음 항목을 확인합니다.

- 실제 content type과 JSON 필드
- 잘못된 JSON에서 service가 호출되지 않는지
- body와 header 검증 실패가 같은 오류 형식을 사용하는지
- 업무 예외가 정해진 status와 `errorCode`로 바뀌는지
- 응답에 내부 구현 정보가 포함되지 않는지

## 확인 사항

- 요청 DTO와 JPA entity가 분리되어 있습니까?
- 형식 검증과 저장 상태를 이용한 업무 검사가 같은 위치에 섞여 있지 않습니까?
- Controller가 repository나 외부 client의 기술 예외를 직접 처리하지 않습니까?
- `ProblemDetail`의 status와 `errorCode`가 테스트로 고정되어 있습니까?
- 잘못된 입력이 application service에 도달하지 않는지 확인했습니까?

프로젝트 완료 뒤 이 내용을 다시 확인하려면 [`request-preview-api`](../../exercises/request-preview-api/)를 Guide 없이 구현해 봅니다.
