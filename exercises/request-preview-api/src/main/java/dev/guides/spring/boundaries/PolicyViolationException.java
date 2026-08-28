package dev.guides.spring.boundaries;

public final class PolicyViolationException extends RuntimeException {
  private final String errorCode;

  public PolicyViolationException(String errorCode, String message) {
    super(message);
    this.errorCode = errorCode;
  }

  public String errorCode() {
    return errorCode;
  }
}
