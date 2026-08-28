package dev.guides.spring.publication;

public final class PolicyRejectedException extends RuntimeException {
  public PolicyRejectedException() {
    super("The external policy rejected publication creation.");
  }
}
