package dev.guides.spring.publication;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Optional;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

// [Implementation 6] 사용자별 Redis cache key와 TTL 관리
// 사용자와 멱등성 key가 섞이지 않게 hash하고, Redis 실패는 DB 결과에 영향을 주지 않습니다.
@Component
public class PublicationCache {
  private final StringRedisTemplate redis;
  private final JsonMapper mapper;
  private final PublicationMetrics metrics;
  private final PublicationCacheProperties properties;

  public PublicationCache(
      StringRedisTemplate redis,
      JsonMapper mapper,
      PublicationMetrics metrics,
      PublicationCacheProperties properties) {
    this.redis = redis;
    this.mapper = mapper;
    this.metrics = metrics;
    this.properties = properties;
  }

  public Optional<PublicationResponse> find(
      String actorId,
      String idempotencyKey) {
    try {
      String value = redis.opsForValue().get(key(actorId, idempotencyKey));
      if (value == null) {
        return Optional.empty();
      }
      return Optional.of(mapper.readValue(value, PublicationResponse.class));
    } catch (RuntimeException exception) {
      metrics.cacheFailure();
      return Optional.empty();
    }
  }

  public void put(
      String actorId,
      String idempotencyKey,
      PublicationResponse response) {
    try {
      redis.opsForValue().set(
          key(actorId, idempotencyKey),
          mapper.writeValueAsString(response),
          properties.ttl());
    } catch (RuntimeException exception) {
      metrics.cacheFailure();
    }
  }

  public static String key(String actorId, String idempotencyKey) {
    String material = actorId.length() + ":" + actorId + idempotencyKey;
    try {
      byte[] digest = MessageDigest.getInstance("SHA-256")
          .digest(material.getBytes(StandardCharsets.UTF_8));
      return "publication:result:v1:" + HexFormat.of().formatHex(digest);
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256 is unavailable.", exception);
    }
  }
}
