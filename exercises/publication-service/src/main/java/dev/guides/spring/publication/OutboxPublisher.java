package dev.guides.spring.publication;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(
    prefix = "publication.outbox",
    name = "publisher-enabled",
    havingValue = "true")
public final class OutboxPublisher {
  private final OutboxEventRepository events;
  private final EventGateway gateway;
  private final OutboxCompletionService completion;

  public OutboxPublisher(
      OutboxEventRepository events,
      EventGateway gateway,
      OutboxCompletionService completion) {
    this.events = events;
    this.gateway = gateway;
    this.completion = completion;
  }

  // [Implementation 10] Kafka 발행 성공 후 Outbox 완료 기록
  // 전송이 성공한 event만 별도 transaction에서 published 상태로 바꿉니다.
  @Scheduled(fixedDelayString = "${publication.outbox.poll-interval:1s}")
  public void publishPending() {
    for (OutboxEventEntity event
        : events.findTop50ByPublishedAtIsNullOrderByCreatedAtAsc()) {
      gateway.publish(
          event.id(),
          event.aggregateId(),
          event.eventType(),
          event.payload());
      completion.markPublished(event.id());
    }
  }
}
