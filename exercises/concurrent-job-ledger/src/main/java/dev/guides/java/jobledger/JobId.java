package dev.guides.java.jobledger;

import java.util.Objects;

// [Implementation 1] 빈 값이 아닌 작업 식별자만 생성합니다.
public record JobId(String value) {
  public JobId {
    Objects.requireNonNull(value, "job identifier is required");
    if (value.isBlank()) {
      throw new IllegalArgumentException("job identifier must not be blank");
    }
  }
}
