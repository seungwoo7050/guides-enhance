package dev.guides.java.jobledger;

import java.time.Instant;
import java.util.Objects;

// [Implementation 3-1] 적용 결과와 완료 시각을 바뀌지 않는 영수증으로 묶습니다.
public record JobReceipt(JobId id, JobKind kind, long amount, long balance, Instant completedAt) {
  public JobReceipt {
    Objects.requireNonNull(id, "job identifier is required");
    Objects.requireNonNull(kind, "job kind is required");
    Objects.requireNonNull(completedAt, "completion time is required");
  }
}
