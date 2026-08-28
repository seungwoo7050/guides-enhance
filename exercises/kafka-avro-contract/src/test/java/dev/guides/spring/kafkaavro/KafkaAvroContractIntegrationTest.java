package dev.guides.spring.kafkaavro;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Duration;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.kafka.KafkaContainer;
import org.testcontainers.utility.DockerImageName;

@SpringBootTest
@Testcontainers
class KafkaAvroContractIntegrationTest {
  private static final String KAFKA_IMAGE =
      "apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837";

  @Container
  static final KafkaContainer KAFKA =
      new KafkaContainer(
              DockerImageName.parse(KAFKA_IMAGE).asCompatibleSubstituteFor("apache/kafka"))
          .withLabel("project.test-run", testRunId());

  @Autowired EventPublisher publisher;
  @Autowired EventProbe probe;

  private static String testRunId() {
    return System.getenv().getOrDefault("PROJECT_TEST_RUN_ID", "manual");
  }

  @DynamicPropertySource
  static void kafkaProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.kafka.bootstrap-servers", KAFKA::getBootstrapServers);
  }

  @BeforeEach
  void clear() {
    probe.clear();
  }

  @Test
  void preservesPartitionKeyAndAvroFields() throws Exception {
    var expected = new TaskSubmitted("task-1", 15, "STANDARD");
    publisher.publish("batch-7", expected);

    EventProbe.ObservedEvent observed = probe.poll(Duration.ofSeconds(10));
    assertThat(observed).isNotNull();
    assertThat(observed.key()).isEqualTo("batch-7");
    assertThat(observed.event()).isEqualTo(expected);
  }
}
