package dev.guides.spring.idempotency;

import java.util.Optional;

public interface IdempotencyHintStore {
  Optional<OperationResult> get(String key);

  void put(String key, OperationResult result);
}
