package dev.guides.spring.boundaries;

import java.net.URI;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

// [Implementation 4] 검증 실패와 업무 거절을 ProblemDetail로 변환
// 입력 오류는 400, 허용 범위 위반은 409로 구분해 반환합니다.
@RestControllerAdvice
public final class ProblemDetailsAdvice {
  @ExceptionHandler(PolicyViolationException.class)
  ProblemDetail handlePolicy(PolicyViolationException exception) {
    ProblemDetail detail = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, exception.getMessage());
    detail.setType(URI.create("urn:guide:problem:policy-violation"));
    detail.setTitle("Policy violation");
    detail.setProperty("errorCode", exception.errorCode());
    return detail;
  }

  @ExceptionHandler(MethodArgumentNotValidException.class)
  ProblemDetail handleValidation(MethodArgumentNotValidException exception) {
    ProblemDetail detail =
        ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "The request values are invalid.");
    detail.setType(URI.create("urn:guide:problem:invalid-request"));
    detail.setTitle("Invalid request");
    detail.setProperty("errorCode", "INVALID_REQUEST");
    Map<String, String> fields = new LinkedHashMap<>();
    exception.getBindingResult().getFieldErrors()
        .forEach(error -> fields.putIfAbsent(error.getField(), error.getDefaultMessage()));
    detail.setProperty("fields", fields);
    return detail;
  }
}
