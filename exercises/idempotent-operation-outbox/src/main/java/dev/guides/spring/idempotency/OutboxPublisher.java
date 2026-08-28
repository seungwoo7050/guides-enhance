package dev.guides.spring.idempotency;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OutboxPublisher {
  private final OutboxRepository repository;
  private final EventSink sink;
  private final int batchSize;
  private final Duration retryDelay;

  public OutboxPublisher(
      OutboxRepository repository,
      EventSink sink,
      @Value("${guide.outbox.batch-size:20}") int batchSize,
      @Value("${guide.outbox.retry-delay:PT5S}") Duration retryDelay) {
    this.repository = repository;
    this.sink = sink;
    this.batchSize = batchSize;
    this.retryDelay = retryDelay;
  }

  // [Implementation 5] Outbox 발행 성공·실패 결과 저장
  // 각 시도 뒤 성공 시각 또는 실패 횟수와 다음 시각을 반드시 DB에 남깁니다.
  @Transactional
  public int publishDueEvents() {
    Instant now = Instant.now();
    List<OutboxEvent> events = repository.findDue(now, PageRequest.of(0, batchSize));
    for (OutboxEvent event : events) {
      try {
        sink.publish(event.id(), event.eventType(), event.payload());
        event.markPublished(now);
      } catch (RuntimeException exception) {
        String message = exception.getMessage() == null
            ? exception.getClass().getSimpleName()
            : exception.getMessage();
        event.markFailed(now.plus(retryDelay), message);
      }
    }
    return events.size();
  }
}
