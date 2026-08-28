package dev.guides.spring.failclosed;

public final class BusinessDeclineException extends RuntimeException {
  public BusinessDeclineException(String message) {
    super(message);
  }
}
