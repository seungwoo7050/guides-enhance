package dev.guides.spring.publication;

import org.springframework.stereotype.Service;

@Service
public final class PublicationService {
  private final PolicyClient policy;
  private final PublicationWriter writer;
  private final PublicationCache cache;
  private final PublicationMetrics metrics;

  public PublicationService(
      PolicyClient policy,
      PublicationWriter writer,
      PublicationCache cache,
      PublicationMetrics metrics) {
    this.policy = policy;
    this.writer = writer;
    this.cache = cache;
    this.metrics = metrics;
  }

  // [Implementation 7] cache·DB·판단 API·쓰기 순서 조정
  // 완료 결과를 먼저 찾고, 새 요청일 때만 외부 판단과 DB 쓰기를 수행합니다.
  public PublicationResult create(
      String actorId,
      String idempotencyKey,
      CreatePublicationRequest request) {
    var cached = cache.find(actorId, idempotencyKey);
    if (cached.isPresent()) {
      metrics.duplicate();
      return new PublicationResult(cached.orElseThrow(), false);
    }

    var stored = writer.findExisting(actorId, idempotencyKey);
    if (stored.isPresent()) {
      PublicationResponse response = stored.orElseThrow();
      cache.put(actorId, idempotencyKey, response);
      metrics.duplicate();
      return new PublicationResult(response, false);
    }

    try {
      policy.ensureAllowed(actorId, request);
    } catch (PolicyRejectedException exception) {
      metrics.rejected();
      throw exception;
    }

    PublicationResult result = writer.createOrFind(actorId, idempotencyKey, request);
    cache.put(actorId, idempotencyKey, result.response());
    if (result.created()) {
      metrics.created();
    } else {
      metrics.duplicate();
    }
    return result;
  }
}
