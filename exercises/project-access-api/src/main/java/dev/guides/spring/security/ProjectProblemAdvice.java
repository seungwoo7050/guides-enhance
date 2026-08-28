package dev.guides.spring.security;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public final class ProjectProblemAdvice {
  @ExceptionHandler(ProjectNotFoundException.class)
  ProblemDetail projectNotFound(ProjectNotFoundException exception) {
    ProblemDetail problem = ProblemDetail.forStatusAndDetail(
        HttpStatus.NOT_FOUND,
        "Project not found.");
    problem.setProperty("errorCode", "PROJECT_NOT_FOUND");
    return problem;
  }
}
