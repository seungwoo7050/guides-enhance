package dev.guides.spring.idempotency;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

@SpringBootTest(properties = {
    "guide.outbox.scheduler-enabled=false",
    "guide.outbox.retry-delay=PT0S"
})
@Testcontainers
class IdempotencyIntegrationTest {
  @Container
  static final PostgreSQLContainer POSTGRES =
      new PostgreSQLContainer(DockerImageName.parse(
          "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15")
          .asCompatibleSubstituteFor("postgres"))
          .withLabel("project.test-run", testRunId());

  @Container
  static final GenericContainer<?> REDIS =
      new GenericContainer<>(
          "redis:8.8.0-alpine@sha256:9d317178eceac8454a2284a9e6df2466b93c745529947f0cd42a0fa9609d7005")
          .withExposedPorts(6379)
          .withLabel("project.test-run", testRunId());

  private static String testRunId() {
    return System.getenv().getOrDefault("PROJECT_TEST_RUN_ID", "manual");
  }

  @DynamicPropertySource
  static void dependencies(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
    registry.add("spring.datasource.username", POSTGRES::getUsername);
    registry.add("spring.datasource.password", POSTGRES::getPassword);
    registry.add("spring.data.redis.host", REDIS::getHost);
    registry.add("spring.data.redis.port", () -> REDIS.getMappedPort(6379));
  }

  @Autowired OperationService service;
  @Autowired OperationRepository operations;
  @Autowired OutboxRepository outbox;
  @Autowired OutboxPublisher publisher;
  @Autowired StringRedisTemplate redis;
  @MockitoSpyBean IdempotencyHintStore hints;
  @MockitoBean EventSink sink;

  @BeforeEach
  void setUp() {
    outbox.deleteAll();
    operations.deleteAll();
    redis.execute((RedisCallback<Void>) connection -> {
      connection.serverCommands().flushDb();
      return null;
    });
  }

  @Test
  void storesCommittedResultInRedis() {
    OperationResult result = service.apply("redis-key", 4);

    assertThat(hints.get("redis-key")).contains(result);
    assertThat(service.apply("redis-key", 999)).isEqualTo(result);
  }

  @Test
  void concurrentSameKeyCreatesOneOperationWhenRedisFails() throws Exception {
    doThrow(new IllegalStateException("Redis is unavailable."))
        .when(hints).get(anyString());
    doThrow(new IllegalStateException("Redis is unavailable."))
        .when(hints).put(anyString(), any());

    int workers = 20;
    var executor = Executors.newFixedThreadPool(workers);
    CountDownLatch ready = new CountDownLatch(workers);
    CountDownLatch start = new CountDownLatch(1);
    try {
      List<Future<OperationResult>> futures = new ArrayList<>();
      for (int index = 0; index < workers; index++) {
        futures.add(executor.submit(() -> {
          ready.countDown();
          if (!start.await(10, TimeUnit.SECONDS)) {
            throw new IllegalStateException("Timed out while waiting to start concurrent requests.");
          }
          return service.apply("fixed-key", 10);
        }));
      }
      assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
      start.countDown();

      var operationIds = new HashSet<>();
      for (Future<OperationResult> future : futures) {
        operationIds.add(future.get(30, TimeUnit.SECONDS).operationId());
      }

      assertThat(operationIds).hasSize(1);
      assertThat(operations.count()).isEqualTo(1);
      assertThat(outbox.count()).isEqualTo(1);
    } finally {
      executor.shutdownNow();
      assertThat(executor.awaitTermination(10, TimeUnit.SECONDS)).isTrue();
    }
  }

  @Test
  void retriesPersistedEventAfterPublicationFailure() {
    service.apply("outbox-key", 2);
    OutboxEvent saved = outbox.findAll().get(0);

    doThrow(new IllegalStateException("The event sink is unavailable."))
        .doNothing()
        .when(sink).publish(any(), anyString(), anyString());

    assertThat(publisher.publishDueEvents()).isEqualTo(1);
    OutboxEvent failed = outbox.findById(saved.id()).orElseThrow();
    assertThat(failed.publishedAt()).isNull();
    assertThat(failed.attemptCount()).isEqualTo(1);
    assertThat(failed.lastError()).contains("sink is unavailable");

    assertThat(publisher.publishDueEvents()).isEqualTo(1);
    OutboxEvent recovered = outbox.findById(saved.id()).orElseThrow();
    assertThat(recovered.publishedAt()).isNotNull();
    assertThat(recovered.lastError()).isNull();
    verify(sink, times(2)).publish(any(), anyString(), anyString());
  }
}
