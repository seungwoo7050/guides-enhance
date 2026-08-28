package dev.guides.spring.publication;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.net.URI;
import java.time.Instant;
import java.util.UUID;

// [Implementation 3] publication 저장 상태와 응답 변환
// DB에 저장한 값을 기준으로 같은 응답을 다시 만들 수 있게 합니다.
@Entity
@Table(name = "publication")
public class PublicationEntity {
  @Id
  private UUID id;

  @Column(name = "actor_id", nullable = false, length = 100)
  private String actorId;

  @Column(name = "idempotency_key", nullable = false, length = 120)
  private String idempotencyKey;

  @Column(nullable = false, length = 120)
  private String title;

  @Column(nullable = false, length = 500)
  private String source;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  protected PublicationEntity() {}

  private PublicationEntity(
      UUID id,
      String actorId,
      String idempotencyKey,
      String title,
      URI source,
      Instant createdAt) {
    this.id = id;
    this.actorId = actorId;
    this.idempotencyKey = idempotencyKey;
    this.title = title;
    this.source = source.toString();
    this.createdAt = createdAt;
  }

  public static PublicationEntity create(
      String actorId,
      String idempotencyKey,
      CreatePublicationRequest request,
      Instant createdAt) {
    return new PublicationEntity(
        UUID.randomUUID(),
        actorId,
        idempotencyKey,
        request.title(),
        request.source(),
        createdAt);
  }

  public PublicationResponse toResponse() {
    return new PublicationResponse(id, actorId, title, URI.create(source));
  }

  public UUID id() {
    return id;
  }

  public String actorId() {
    return actorId;
  }
}
