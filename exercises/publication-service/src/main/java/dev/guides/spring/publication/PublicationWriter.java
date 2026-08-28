package dev.guides.spring.publication;

import java.sql.PreparedStatement;
import java.time.Clock;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import org.springframework.jdbc.core.ConnectionCallback;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.json.JsonMapper;

@Service
public class PublicationWriter {
  private final PublicationRepository publications;
  private final OutboxEventRepository outbox;
  private final JsonMapper mapper;
  private final JdbcTemplate jdbc;
  private final Clock clock;

  public PublicationWriter(
      PublicationRepository publications,
      OutboxEventRepository outbox,
      JsonMapper mapper,
      JdbcTemplate jdbc,
      Clock clock) {
    this.publications = publications;
    this.outbox = outbox;
    this.mapper = mapper;
    this.jdbc = jdbc;
    this.clock = clock;
  }

  @Transactional(readOnly = true)
  public Optional<PublicationResponse> findExisting(
      String actorId,
      String idempotencyKey) {
    return publications.findByActorIdAndIdempotencyKey(actorId, idempotencyKey)
        .map(PublicationEntity::toResponse);
  }

  // [Implementation 5] key별 잠금 후 publication과 Outbox 저장
  // 잠금 안에서 기존 결과를 다시 확인하고 두 행을 같은 transaction에 저장합니다.
  @Transactional
  public PublicationResult createOrFind(
      String actorId,
      String idempotencyKey,
      CreatePublicationRequest request) {
    lock(actorId, idempotencyKey);

    var existing = publications.findByActorIdAndIdempotencyKey(
        actorId,
        idempotencyKey);
    if (existing.isPresent()) {
      return new PublicationResult(existing.orElseThrow().toResponse(), false);
    }

    Instant now = clock.instant();
    PublicationEntity publication = publications.saveAndFlush(
        PublicationEntity.create(actorId, idempotencyKey, request, now));
    outbox.saveAndFlush(OutboxEventEntity.publicationCreated(
        publication,
        payload(publication),
        now));
    return new PublicationResult(publication.toResponse(), true);
  }

  private void lock(String actorId, String idempotencyKey) {
    String lockKey = actorId.length() + ":" + actorId + idempotencyKey;
    jdbc.execute((ConnectionCallback<Void>) connection -> {
      try (PreparedStatement statement = connection.prepareStatement(
          "select pg_advisory_xact_lock(hashtextextended(?, 0))")) {
        statement.setString(1, lockKey);
        statement.execute();
      }
      return null;
    });
  }

  private String payload(PublicationEntity publication) {
    try {
      return mapper.writeValueAsString(Map.of(
          "publicationId", publication.id(),
          "actorId", publication.actorId()));
    } catch (JacksonException exception) {
      throw new IllegalStateException(
          "Unable to create the outbox payload.",
          exception);
    }
  }
}
