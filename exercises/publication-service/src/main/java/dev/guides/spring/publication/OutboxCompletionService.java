package dev.guides.spring.publication;

import java.time.Clock;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OutboxCompletionService {
  private final OutboxEventRepository events;
  private final Clock clock;

  public OutboxCompletionService(
      OutboxEventRepository events,
      Clock clock) {
    this.events = events;
    this.clock = clock;
  }

  @Transactional
  public void markPublished(UUID eventId) {
    OutboxEventEntity event = events.findById(eventId).orElseThrow();
    event.markPublished(clock.instant());
  }
}
