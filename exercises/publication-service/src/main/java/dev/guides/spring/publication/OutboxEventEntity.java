package dev.guides.spring.publication;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

// [Implementation 3-1] Outbox 대기·발행 완료 상태 관리
// 발행 전 event와 Kafka 전달 완료 시각을 같은 행에 기록합니다.
@Entity
@Table(name = "outbox_event")
public class OutboxEventEntity {
  @Id
  private UUID id;

  @Column(name = "aggregate_id", nullable = false)
  private UUID aggregateId;

  @Column(name = "event_type", nullable = false, length = 100)
  private String eventType;

  @Column(nullable = false, columnDefinition = "text")
  private String payload;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "published_at")
  private Instant publishedAt;

  protected OutboxEventEntity() {}

  private OutboxEventEntity(
      UUID id,
      UUID aggregateId,
      String eventType,
      String payload,
      Instant createdAt) {
    this.id = id;
    this.aggregateId = aggregateId;
    this.eventType = eventType;
    this.payload = payload;
    this.createdAt = createdAt;
  }

  public static OutboxEventEntity publicationCreated(
      PublicationEntity publication,
      String payload,
      Instant createdAt) {
    return new OutboxEventEntity(
        UUID.randomUUID(),
        publication.id(),
        "publication.created.v1",
        payload,
        createdAt);
  }

  public void markPublished(Instant time) {
    this.publishedAt = time;
  }

  public UUID id() {
    return id;
  }

  public UUID aggregateId() {
    return aggregateId;
  }

  public String eventType() {
    return eventType;
  }

  public String payload() {
    return payload;
  }
}
