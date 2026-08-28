package dev.guides.spring.locking;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

@SpringBootTest
@Testcontainers
class InventoryConcurrencyIntegrationTest {
  @Container
  static final PostgreSQLContainer POSTGRES =
      new PostgreSQLContainer(DockerImageName.parse(
          "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15")
          .asCompatibleSubstituteFor("postgres"))
          .withLabel("project.test-run", testRunId());

  private static String testRunId() {
    return System.getenv().getOrDefault("PROJECT_TEST_RUN_ID", "manual");
  }

  @DynamicPropertySource
  static void database(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
    registry.add("spring.datasource.username", POSTGRES::getUsername);
    registry.add("spring.datasource.password", POSTGRES::getPassword);
  }

  @Autowired InventoryService service;
  @Autowired InventoryRepository repository;
  UUID itemId;

  @BeforeEach
  void setUp() {
    repository.deleteAll();
    itemId = UUID.randomUUID();
    service.create(itemId, 1_000);
  }

  @Test
  void exactlyTenOfTwentyConcurrentDebitsSucceed() throws Exception {
    int workers = 20;
    var executor = Executors.newFixedThreadPool(workers);
    CountDownLatch ready = new CountDownLatch(workers);
    CountDownLatch start = new CountDownLatch(1);
    try {
      List<Future<Boolean>> futures = new ArrayList<>();
      for (int i = 0; i < workers; i++) {
        futures.add(executor.submit(() -> {
          ready.countDown();
          if (!start.await(10, TimeUnit.SECONDS)) {
            throw new IllegalStateException("Timed out while waiting to start concurrent requests.");
          }
          return service.reserve(itemId, 100);
        }));
      }
      assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
      start.countDown();
      int accepted = 0;
      for (Future<Boolean> future : futures) {
        if (future.get(30, TimeUnit.SECONDS)) {
          accepted++;
        }
      }
      assertThat(accepted).isEqualTo(10);
      assertThat(service.availableQuantity(itemId)).isZero();
    } finally {
      executor.shutdownNow();
      assertThat(executor.awaitTermination(10, TimeUnit.SECONDS)).isTrue();
    }
  }
}
