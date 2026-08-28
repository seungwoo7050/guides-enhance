package dev.guides.spring.security;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.AccessDeniedHandler;
import tools.jackson.databind.json.JsonMapper;

// [Implementation 4] 사용자·비밀번호 인코더·method security 구성
// 인증 사용자와 객체 권한 검사를 실제 Spring proxy에 연결합니다.
@Configuration(proxyBeanMethods = false)
@EnableMethodSecurity
public class SecurityConfiguration {
  @Bean
  UserDetailsService users(PasswordEncoder encoder) {
    return new InMemoryUserDetailsManager(
        User.withUsername("owner")
            .password(encoder.encode("owner-password"))
            .roles("EDITOR")
            .build(),
        User.withUsername("viewer")
            .password(encoder.encode("viewer-password"))
            .roles("VIEWER")
            .build());
  }

  @Bean
  PasswordEncoder passwordEncoder() {
    return org.springframework.security.crypto.factory.PasswordEncoderFactories
        .createDelegatingPasswordEncoder();
  }

  // [Implementation 4-1] 요청 인증·CSRF·401·403 응답 구성
  // health 외 요청은 인증하고, 변경 요청의 CSRF 검사를 유지합니다.
  @Bean
  SecurityFilterChain securityFilterChain(HttpSecurity http, JsonMapper mapper)
      throws Exception {
    return http
        .authorizeHttpRequests(authorize -> authorize
            .requestMatchers("/actuator/health/**").permitAll()
            .anyRequest().authenticated())
        .httpBasic(Customizer.withDefaults())
        .exceptionHandling(errors -> errors
            .authenticationEntryPoint(authenticationEntryPoint(mapper))
            .accessDeniedHandler(accessDeniedHandler(mapper)))
        .build();
  }

  private AuthenticationEntryPoint authenticationEntryPoint(JsonMapper mapper) {
    return (request, response, exception) -> writeProblem(
        response,
        mapper,
        HttpStatus.UNAUTHORIZED,
        "AUTHENTICATION_REQUIRED",
        "Authentication is required.");
  }

  private AccessDeniedHandler accessDeniedHandler(JsonMapper mapper) {
    return (request, response, exception) -> writeProblem(
        response,
        mapper,
        HttpStatus.FORBIDDEN,
        "ACCESS_DENIED",
        "The request is not authorized.");
  }

  private void writeProblem(
      HttpServletResponse response,
      JsonMapper mapper,
      HttpStatus status,
      String errorCode,
      String detail) throws java.io.IOException {
    ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detail);
    problem.setProperty("errorCode", errorCode);
    response.setStatus(status.value());
    response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
    mapper.writeValue(response.getOutputStream(), problem);
  }
}
