package dev.guides.spring.kafkaavro;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

@Component
public class EventConsumer {
  private final AvroEventCodec codec;
  private final EventProbe probe;

  public EventConsumer(AvroEventCodec codec, EventProbe probe) {
    this.codec = codec;
    this.probe = probe;
  }

  // [Implementation 5] 디코딩과 처리 성공 후 offset 확정
  // 처리 기록 전에 offset을 올리면 이후 실패에서 record를 잃을 수 있습니다.
  @KafkaListener(topics = "${guide.kafka.consume-topic}", groupId = "${guide.kafka.group-id}")
  public void consume(ConsumerRecord<String, byte[]> record, Acknowledgment acknowledgment) {
    TaskSubmitted event = codec.decode(record.value());
    probe.record(record.key(), event);
    acknowledgment.acknowledge();
  }
}
