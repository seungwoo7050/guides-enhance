package dev.guides.spring.idempotency;

import jakarta.persistence.EntityManager;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Service
public class OperationService {
  private final EntityManager entityManager;
  private final OperationRepository operations;
  private final OutboxRepository outbox;
  private final IdempotencyHintStore hints;

  public OperationService(
      EntityManager entityManager,
      OperationRepository operations,
      OutboxRepository outbox,
      IdempotencyHintStore hints) {
    this.entityManager = entityManager;
    this.operations = operations;
    this.outbox = outbox;
    this.hints = hints;
  }

  // [Implementation 4] key별 잠금 후 DB 재조회와 operation·Outbox 저장
  // Redis miss 뒤 같은 key를 직렬화하고, 잠금 안에서 기존 완료 행을 다시 확인합니다.
  @Transactional
  public OperationResult apply(String key, long quantity) {
    if (key == null || key.isBlank()) {
      throw new IllegalArgumentException("An idempotency key is required.");
    }
    if (quantity <= 0) {
      throw new IllegalArgumentException("Quantity must be greater than zero.");
    }

    Optional<OperationResult> hinted = safeGet(key);
    if (hinted.isPresent()) {
      return hinted.get();
    }

    entityManager
        .createNativeQuery("select pg_advisory_xact_lock(hashtextextended(?1, 0))")
        .setParameter(1, key)
        .getSingleResult();

    Optional<OperationRecord> existing = operations.findByIdempotencyKey(key);
    if (existing.isPresent()) {
      OperationResult result = existing.get().result();
      cacheAfterCommit(key, result);
      return result;
    }

    UUID operationId = UUID.nameUUIDFromBytes(key.getBytes(StandardCharsets.UTF_8));
    OperationResult result = new OperationResult(operationId, quantity);
    operations.save(new OperationRecord(operationId, key, quantity));
    outbox.save(new OutboxEvent(
        UUID.randomUUID(),
        operationId,
        "OperationApplied",
        "{\"operationId\":\"" + operationId + "\",\"quantity\":" + quantity + "}",
        Instant.now()));
    cacheAfterCommit(key, result);
    return result;
  }

  private Optional<OperationResult> safeGet(String key) {
    try {
      return hints.get(key);
    } catch (RuntimeException ignored) {
      return Optional.empty();
    }
  }

  // [Implementation 4-1] commit 후 Redis에 결과 저장
  // DB commit이 끝난 뒤에만 cache를 채우며, Redis 실패는 완료 결과를 뒤집지 않습니다.
  private void cacheAfterCommit(String key, OperationResult result) {
    TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
      @Override
      public void afterCommit() {
        try {
          hints.put(key, result);
        } catch (RuntimeException ignored) {
          // Redis는 조회를 빠르게 할 뿐이며 완료 결과는 PostgreSQL이 결정합니다.
        }
      }
    });
  }
}
