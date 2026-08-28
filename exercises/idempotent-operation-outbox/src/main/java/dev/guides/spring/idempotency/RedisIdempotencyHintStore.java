package dev.guides.spring.idempotency;

import java.time.Duration;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

// [Implementation 3] Redis를 TTL이 있는 조회 힌트로 제한
// 값이 없거나 Redis가 실패해도 PostgreSQL에서 완료 결과를 다시 찾을 수 있습니다.
@Component
public class RedisIdempotencyHintStore implements IdempotencyHintStore {
  private static final String PREFIX = "guide:idempotency:";
  private static final Duration TTL = Duration.ofMinutes(10);

  private final StringRedisTemplate redis;

  public RedisIdempotencyHintStore(StringRedisTemplate redis) {
    this.redis = redis;
  }

  @Override
  public Optional<OperationResult> get(String key) {
    String stored = redis.opsForValue().get(redisKey(key));
    if (stored == null) {
      return Optional.empty();
    }

    String[] fields = stored.split("\\|", 2);
    if (fields.length != 2) {
      throw new IllegalStateException("The cached idempotency result has an invalid format.");
    }
    return Optional.of(new OperationResult(UUID.fromString(fields[0]), Long.parseLong(fields[1])));
  }

  @Override
  public void put(String key, OperationResult result) {
    String value = result.operationId() + "|" + result.quantity();
    redis.opsForValue().set(redisKey(key), value, TTL);
  }

  private String redisKey(String key) {
    return PREFIX + key;
  }
}
