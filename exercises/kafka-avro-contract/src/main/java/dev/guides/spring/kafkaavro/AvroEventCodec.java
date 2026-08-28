package dev.guides.spring.kafkaavro;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import org.apache.avro.Schema;
import org.apache.avro.generic.GenericData;
import org.apache.avro.generic.GenericDatumReader;
import org.apache.avro.generic.GenericDatumWriter;
import org.apache.avro.generic.GenericRecord;
import org.apache.avro.io.DecoderFactory;
import org.apache.avro.io.EncoderFactory;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

// [Implementation 2] 하나의 Avro schema로 인코딩·디코딩
// producer와 consumer가 같은 schema를 읽어 필드 해석이 달라지지 않게 합니다.
@Component
public class AvroEventCodec {
  private final Schema schema;

  public AvroEventCodec() {
    try (InputStream input = new ClassPathResource("avro/task-submitted.avsc").getInputStream()) {
      this.schema = new Schema.Parser().parse(input);
    } catch (IOException exception) {
      throw new IllegalStateException("Unable to read the Avro schema.", exception);
    }
  }

  public byte[] encode(TaskSubmitted event) {
    GenericRecord record = new GenericData.Record(schema);
    record.put("taskId", event.taskId());
    record.put("itemCount", event.itemCount());
    record.put("category", event.category());
    try (var output = new ByteArrayOutputStream()) {
      var encoder = EncoderFactory.get().binaryEncoder(output, null);
      new GenericDatumWriter<GenericRecord>(schema).write(record, encoder);
      encoder.flush();
      return output.toByteArray();
    } catch (IOException exception) {
      throw new IllegalStateException("Unable to encode the event as Avro.", exception);
    }
  }

  public TaskSubmitted decode(byte[] payload) {
    try {
      var decoder = DecoderFactory.get().binaryDecoder(payload, null);
      GenericRecord record = new GenericDatumReader<GenericRecord>(schema).read(null, decoder);
      return new TaskSubmitted(
          record.get("taskId").toString(),
          (Long) record.get("itemCount"),
          record.get("category").toString());
    } catch (IOException exception) {
      throw new IllegalArgumentException("Unable to decode the Avro event.", exception);
    }
  }
}
