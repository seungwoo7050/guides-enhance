package dev.guides.java.jobledger;

import java.util.Objects;

// [Implementation 2-2] 양수 금액을 가진 DebitJob만 생성합니다.
public record DebitJob(JobId id, long amount) implements JobCommand {
  public DebitJob {
    Objects.requireNonNull(id, "job identifier is required");
    if (amount <= 0) {
      throw new IllegalArgumentException("debit amount must be positive");
    }
  }
}
