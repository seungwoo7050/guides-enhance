package dev.guides.spring.kafkaavro;

import java.util.concurrent.TimeUnit;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class EventPublisher {
  private final KafkaTemplate<String, byte[]> kafka;
  private final AvroEventCodec codec;
  private final String topic;

  public EventPublisher(
      KafkaTemplate<String, byte[]> kafka,
      AvroEventCodec codec,
      @Value("${guide.kafka.publish-topic}") String topic) {
    this.kafka = kafka;
    this.codec = codec;
    this.topic = topic;
  }

  // [Implementation 4] key를 보존하고 제한 시간 안에 발행 결과 확인
  // 같은 aggregate의 순서를 유지하며 발행 완료 대기를 무기한 허용하지 않습니다.
  public void publish(String key, TaskSubmitted event) {
    try {
      kafka.send(topic, key, codec.encode(event)).get(10, TimeUnit.SECONDS);
    } catch (Exception exception) {
      throw new IllegalStateException("Kafka event publication failed.", exception);
    }
  }
}
