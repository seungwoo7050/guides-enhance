package dev.guides.java.jobledger;

import java.util.Objects;

// [Implementation 2-1] 양수 금액을 가진 CreditJob만 생성합니다.
public record CreditJob(JobId id, long amount) implements JobCommand {
  public CreditJob {
    Objects.requireNonNull(id, "job identifier is required");
    if (amount <= 0) {
      throw new IllegalArgumentException("credit amount must be positive");
    }
  }
}
