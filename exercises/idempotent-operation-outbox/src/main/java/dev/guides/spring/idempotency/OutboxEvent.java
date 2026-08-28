package dev.guides.spring.idempotency;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

// [Implementation 2-1] Outbox 발행·재시도 상태 전이 관리
// 발행 대기, 성공 시각, 실패 횟수와 다음 시도를 같은 행에 보관합니다.
@Entity
@Table(name = "outbox_event")
public class OutboxEvent {
  @Id private UUID id;

  @Column(name = "aggregate_id", nullable = false)
  private UUID aggregateId;

  @Column(name = "event_type", nullable = false)
  private String eventType;

  @Column(nullable = false, columnDefinition = "text")
  private String payload;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "published_at")
  private Instant publishedAt;

  @Column(name = "attempt_count", nullable = false)
  private int attemptCount;

  @Column(name = "next_attempt_at", nullable = false)
  private Instant nextAttemptAt;

  @Column(name = "last_error", length = 500)
  private String lastError;

  protected OutboxEvent() {}

  public OutboxEvent(UUID id, UUID aggregateId, String eventType, String payload, Instant createdAt) {
    this.id = id;
    this.aggregateId = aggregateId;
    this.eventType = eventType;
    this.payload = payload;
    this.createdAt = createdAt;
    this.nextAttemptAt = createdAt;
  }

  public UUID id() {
    return id;
  }

  public String eventType() {
    return eventType;
  }

  public String payload() {
    return payload;
  }

  public Instant publishedAt() {
    return publishedAt;
  }

  public int attemptCount() {
    return attemptCount;
  }

  public Instant nextAttemptAt() {
    return nextAttemptAt;
  }

  public String lastError() {
    return lastError;
  }

  public void markPublished(Instant publishedAt) {
    this.publishedAt = publishedAt;
    this.lastError = null;
  }

  public void markFailed(Instant nextAttemptAt, String lastError) {
    this.attemptCount++;
    this.nextAttemptAt = nextAttemptAt;
    this.lastError = lastError.substring(0, Math.min(lastError.length(), 500));
  }
}
