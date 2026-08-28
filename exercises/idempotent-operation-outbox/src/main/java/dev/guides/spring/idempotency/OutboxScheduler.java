package dev.guides.spring.idempotency;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

// [Implementation 5-1] 설정된 주기로 Outbox 발행 실행
// scheduler는 실행 시점만 정하고 발행과 상태 변경은 publisher에 맡깁니다.
@Component
@ConditionalOnProperty(
    name = "guide.outbox.scheduler-enabled",
    havingValue = "true",
    matchIfMissing = true)
public class OutboxScheduler {
  private final OutboxPublisher publisher;

  public OutboxScheduler(OutboxPublisher publisher) {
    this.publisher = publisher;
  }

  @Scheduled(
      initialDelayString = "${guide.outbox.initial-delay-ms:1000}",
      fixedDelayString = "${guide.outbox.poll-delay-ms:1000}")
  public void publishDueEvents() {
    publisher.publishDueEvents();
  }
}
