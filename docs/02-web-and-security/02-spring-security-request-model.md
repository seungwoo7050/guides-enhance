# Spring Security 요청 모델

> 읽는 시점: 실제 프로젝트에서 인증과 요청 권한을 구현하기 직전

Spring Security는 Controller보다 먼저 요청을 검사하고, 인증에 성공한 사용자를 `SecurityContext`에 저장합니다. 이 순서를 모르면 임시 `permitAll()`이 전체 API를 열거나, 이미 검증된 사용자 대신 요청 본문의 사용자 ID를 신뢰하는 문제가 생길 수 있습니다.

## 요청은 `SecurityFilterChain`을 먼저 통과합니다

일반적인 처리 순서는 다음과 같습니다.

```text
HTTP request
→ SecurityFilterChain
→ credential 추출
→ AuthenticationManager / provider
→ SecurityContext 저장
→ URL 권한 검사
→ DispatcherServlet
→ method 권한 검사
```

공개 경로부터 구체적으로 선언하고 마지막에는 닫힌 기본값을 둡니다.

```java
@Bean
SecurityFilterChain apiSecurity(HttpSecurity http) throws Exception {
  return http
      .authorizeHttpRequests(auth -> auth
          .requestMatchers("/actuator/health/**").permitAll()
          .requestMatchers(HttpMethod.GET, "/api/catalog/**")
              .authenticated()
          .anyRequest().denyAll())
      .httpBasic(Customizer.withDefaults())
      .build();
}
```

개발 중 임시로 추가한 `permitAll()`을 남기지 않습니다. path pattern과 HTTP method 조합이 실제 endpoint를 모두 덮는지 security test로 확인합니다.

## 사용자는 인증 결과에서 가져옵니다

Controller는 요청 본문이나 임의 헤더의 사용자 ID를 기준으로 삼지 않습니다. Spring Security가 만든 `Authentication`이나 principal에서 인증 사용자를 가져옵니다.

```java
@PostMapping("/projects")
ProjectResponse create(
    Authentication authentication,
    @Valid @RequestBody CreateProjectRequest request) {
  return service.create(authentication.getName(), request);
}
```

외부 gateway가 서명한 사용자 header를 전달하는 방식이라면 다음 조건도 함께 확인해야 합니다.

- 애플리케이션이 gateway를 거치지 않고 직접 공개되지 않습니다.
- 외부에서 들어온 같은 이름의 header를 gateway가 제거합니다.
- 애플리케이션은 신뢰할 수 있는 네트워크 경로에서 온 요청만 받습니다.

## 인증 방식과 session 저장 방식을 함께 정합니다

인증 방식을 선택할 때 credential을 어디에 저장하고 어떻게 만료할지도 정해야 합니다.

- browser session은 server가 session을 저장하고 cookie로 사용자를 식별합니다.
- HTTP Basic은 단순한 내부 도구와 테스트에는 편하지만 매 요청에 credential이 전송됩니다.
- bearer token은 서명 검증, 만료, 회전, audience 확인이 필요합니다.

서로 다른 방식을 무작정 섞지 않습니다. logout이 무엇을 없애는지, credential이 만료되었을 때 어떤 응답을 주는지, 폐기된 credential을 어떻게 거부하는지 명시합니다.

## 비밀번호는 `PasswordEncoder`로 처리합니다

비밀번호를 평문이나 단순 hash로 저장하지 않습니다. `PasswordEncoder`를 사용하고 `{id}encoded` 형식을 유지해 알고리즘 변경 가능성을 남깁니다. 로그인 실패 응답으로 사용자 존재 여부가 드러나지 않게 합니다.

in-memory user는 filter와 권한 검사를 작은 범위에서 확인할 때만 사용합니다. 실제 사용자 저장 방식과 비밀번호 변경, 잠금, 복구 절차를 대신하지 않습니다.

## 401과 403을 구분합니다

- 인증 정보가 없거나 검증에 실패했다면 401을 반환합니다.
- 인증은 성공했지만 요청한 작업을 수행할 권한이 없다면 403을 반환합니다.

API에서는 기본 HTML login page 대신 `AuthenticationEntryPoint`와 `AccessDeniedHandler`를 구성해 `ProblemDetail`을 반환할 수 있습니다. 두 응답의 `errorCode`를 다르게 두면 클라이언트와 운영자가 원인을 구분하기 쉽습니다.

## method security는 객체 단위 권한에 사용합니다

URL 규칙만으로 특정 프로젝트나 주문의 소유권까지 표현하기는 어렵습니다.

```java
@PreAuthorize("@projectAccess.canEdit(#projectId, authentication.name)")
public ProjectResponse rename(long projectId, String title) {
  // ...
}
```

`@EnableMethodSecurity`를 실제로 켜야 하며, 같은 객체 안에서 method를 직접 호출해 proxy를 우회하지 않는지도 확인합니다. URL 권한 검사는 endpoint를 크게 닫고, method 권한 검사는 조회한 객체와 인증 사용자의 관계를 확인합니다.

## 확인 사항

- 모든 요청이 의도한 `SecurityFilterChain`을 통과합니까?
- 마지막 URL 규칙이 열린 기본값으로 끝나지 않습니까?
- 사용자 식별자를 요청 body나 임의 header에서 신뢰하지 않습니까?
- 401과 403을 다른 응답으로 반환합니까?
- method security가 실제 Spring proxy를 통해 호출됩니까?
- 인증 방식에 맞는 session, 만료, logout 규칙이 정해져 있습니까?

객체 소유권이나 cookie 기반 변경 요청을 구현한다면 [`인증, 객체 권한과 CSRF`](03-authentication-authorization-and-csrf.md)를 이어서 읽습니다.
