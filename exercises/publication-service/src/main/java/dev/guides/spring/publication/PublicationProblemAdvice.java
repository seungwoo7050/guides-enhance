package dev.guides.spring.publication;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;

// [Implementation 8-1] 입력·업무·의존성 실패를 HTTP 오류로 변환
// 잘못된 입력은 400, 업무 거절은 409, 의존성 장애는 503으로 구분합니다.
@RestControllerAdvice
public final class PublicationProblemAdvice {
  @ExceptionHandler(PolicyRejectedException.class)
  ProblemDetail rejected() {
    return problem(
        HttpStatus.CONFLICT,
        "POLICY_REJECTED",
        "The external policy does not allow publication creation.");
  }

  @ExceptionHandler(DependencyUnavailableException.class)
  ProblemDetail unavailable() {
    return problem(
        HttpStatus.SERVICE_UNAVAILABLE,
        "DEPENDENCY_UNAVAILABLE",
        "A required dependency is unavailable.");
  }

  @ExceptionHandler({
      MethodArgumentNotValidException.class,
      HandlerMethodValidationException.class
  })
  ProblemDetail invalid() {
    return problem(
        HttpStatus.BAD_REQUEST,
        "INVALID_REQUEST",
        "The request is invalid.");
  }

  private ProblemDetail problem(
      HttpStatus status,
      String errorCode,
      String detail) {
    ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detail);
    problem.setProperty("errorCode", errorCode);
    return problem;
  }
}
