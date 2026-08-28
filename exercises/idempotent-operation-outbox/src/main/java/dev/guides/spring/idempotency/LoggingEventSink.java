package dev.guides.spring.idempotency;

import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class LoggingEventSink implements EventSink {
  private static final Logger LOGGER = LoggerFactory.getLogger(LoggingEventSink.class);

  @Override
  public void publish(UUID eventId, String eventType, String payload) {
    LOGGER.info("Published an outbox event. eventId={}, eventType={}", eventId, eventType);
  }
}
