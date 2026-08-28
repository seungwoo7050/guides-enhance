package dev.guides.spring.publication;

import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public final class KafkaEventGateway implements EventGateway {
  private final KafkaTemplate<String, String> kafka;
  private final OutboxProperties properties;

  public KafkaEventGateway(
      KafkaTemplate<String, String> kafka,
      OutboxProperties properties) {
    this.kafka = kafka;
    this.properties = properties;
  }

  @Override
  public void publish(
      UUID eventId,
      UUID aggregateId,
      String eventType,
      String payload) {
    ProducerRecord<String, String> record = new ProducerRecord<>(
        properties.topic(),
        aggregateId.toString(),
        payload);
    record.headers().add(
        "event-id",
        eventId.toString().getBytes(StandardCharsets.UTF_8));
    record.headers().add(
        "event-type",
        eventType.getBytes(StandardCharsets.UTF_8));

    try {
      kafka.send(record).get(5, TimeUnit.SECONDS);
    } catch (InterruptedException exception) {
      Thread.currentThread().interrupt();
      throw new IllegalStateException(
          "Kafka publication was interrupted: " + eventId,
          exception);
    } catch (ExecutionException | TimeoutException exception) {
      throw new IllegalStateException(
          "Kafka publication failed: " + eventId,
          exception);
    }
  }
}
