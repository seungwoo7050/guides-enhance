package dev.guides.spring.publication;

public final class DependencyUnavailableException extends RuntimeException {
  public DependencyUnavailableException(String message, Throwable cause) {
    super(message, cause);
  }
}
