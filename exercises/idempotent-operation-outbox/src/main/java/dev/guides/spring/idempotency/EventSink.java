package dev.guides.spring.idempotency;

import java.util.UUID;

public interface EventSink {
  void publish(UUID eventId, String eventType, String payload);
}
