package dev.guides.spring.idempotency;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import org.junit.jupiter.api.Test;

class OutboxSchedulerTest {
  @Test
  void delegatesScheduledRunToPublisher() {
    OutboxPublisher publisher = mock(OutboxPublisher.class);
    OutboxScheduler scheduler = new OutboxScheduler(publisher);

    scheduler.publishDueEvents();

    verify(publisher).publishDueEvents();
  }
}
