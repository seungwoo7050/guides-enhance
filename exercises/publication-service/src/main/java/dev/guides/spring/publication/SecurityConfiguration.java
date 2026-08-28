package dev.guides.spring.publication;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.AccessDeniedHandler;
import tools.jackson.databind.json.JsonMapper;

@Configuration(proxyBeanMethods = false)
public class SecurityConfiguration {
  @Bean
  PasswordEncoder passwordEncoder() {
    return org.springframework.security.crypto.factory.PasswordEncoderFactories
        .createDelegatingPasswordEncoder();
  }

  @Bean
  UserDetailsService users(PasswordEncoder encoder) {
    return new InMemoryUserDetailsManager(
        User.withUsername("editor")
            .password(encoder.encode("editor-password"))
            .roles("EDITOR")
            .build(),
        User.withUsername("reader")
            .password(encoder.encode("reader-password"))
            .roles("READER")
            .build());
  }

  // [Implementation 9] EDITOR 전용 무상태 API 보안 설정
  // health와 생성 API 외 요청은 닫고 인증 실패와 역할 부족을 구분합니다.
  @Bean
  SecurityFilterChain securityFilterChain(
      HttpSecurity http,
      JsonMapper mapper) throws Exception {
    return http
        .sessionManagement(session -> session
            .sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        .csrf(csrf -> csrf.disable())
        .authorizeHttpRequests(authorize -> authorize
            .requestMatchers("/actuator/health/**").permitAll()
            .requestMatchers(HttpMethod.POST, "/api/publications")
                .hasRole("EDITOR")
            .anyRequest().denyAll())
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
