package dev.guides.spring.publication;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static com.github.tomakehurst.wiremock.core.WireMockConfiguration.wireMockConfig;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.github.tomakehurst.wiremock.WireMockServer;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.micrometer.core.instrument.MeterRegistry;
import java.net.URI;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

@SpringBootTest
@AutoConfigureMockMvc
class PublicationServiceIntegrationTest {
  private static final PostgreSQLContainer POSTGRES =
      new PostgreSQLContainer(DockerImageName.parse(
          "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15")
          .asCompatibleSubstituteFor("postgres"))
          .withLabel("project.test-run", testRunId());
  private static final GenericContainer<?> REDIS =
      new GenericContainer<>(
          "redis:8.8.0-alpine@sha256:9d317178eceac8454a2284a9e6df2466b93c745529947f0cd42a0fa9609d7005")
          .withExposedPorts(6379)
          .withLabel("project.test-run", testRunId());
  private static final WireMockServer POLICY =
      new WireMockServer(wireMockConfig().dynamicPort());

  private static String testRunId() {
    return System.getenv().getOrDefault("PROJECT_TEST_RUN_ID", "manual");
  }

  static {
    POSTGRES.start();
    REDIS.start();
    POLICY.start();
  }

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
    registry.add("spring.datasource.username", POSTGRES::getUsername);
    registry.add("spring.datasource.password", POSTGRES::getPassword);
    registry.add("spring.data.redis.host", REDIS::getHost);
    registry.add("spring.data.redis.port", () -> REDIS.getMappedPort(6379));
    registry.add("policy.client.base-url", POLICY::baseUrl);
  }

  @Autowired private MockMvc mvc;
  @Autowired private PublicationService service;
  @Autowired private PublicationRepository publications;
  @Autowired private OutboxEventRepository outbox;
  @Autowired private StringRedisTemplate redis;
  @Autowired private MeterRegistry meters;
  @Autowired private CircuitBreakerRegistry circuitBreakers;

  @BeforeEach
  void resetState() {
    outbox.deleteAll();
    publications.deleteAll();
    try (RedisConnection connection = Objects.requireNonNull(
        redis.getConnectionFactory()).getConnection()) {
      connection.serverCommands().flushAll();
    }
    circuitBreakers.circuitBreaker("policy").reset();
    POLICY.resetAll();
    allowPolicy();
  }

  @AfterAll
  static void stopDependencies() {
    POLICY.stop();
    REDIS.stop();
    POSTGRES.stop();
  }

  @Test
  void authenticationIsRequired() throws Exception {
    mvc.perform(post("/api/publications")
            .header("Idempotency-Key", "anonymous-key")
            .contentType(MediaType.APPLICATION_JSON)
            .content(requestBody("Public document")))
        .andExpect(status().isUnauthorized())
        .andExpect(content().contentTypeCompatibleWith(
            MediaType.APPLICATION_PROBLEM_JSON))
        .andExpect(jsonPath("$.errorCode")
            .value("AUTHENTICATION_REQUIRED"));
  }

  @Test
  void editorRoleIsRequired() throws Exception {
    mvc.perform(post("/api/publications")
            .with(httpBasic("reader", "reader-password"))
            .header("Idempotency-Key", "reader-key")
            .contentType(MediaType.APPLICATION_JSON)
            .content(requestBody("Read-only user")))
        .andExpect(status().isForbidden())
        .andExpect(content().contentTypeCompatibleWith(
            MediaType.APPLICATION_PROBLEM_JSON))
        .andExpect(jsonPath("$.errorCode").value("ACCESS_DENIED"));
  }

  @Test
  void invalidIdempotencyKeyIsRejectedAtMvcBoundary() throws Exception {
    mvc.perform(post("/api/publications")
            .with(httpBasic("editor", "editor-password"))
            .header("Idempotency-Key", "   ")
            .contentType(MediaType.APPLICATION_JSON)
            .content(requestBody("Invalid key")))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.errorCode").value("INVALID_REQUEST"));

    assertThat(publications.count()).isZero();
    assertThat(outbox.count()).isZero();
  }

  @Test
  void creationWritesPublicationOutboxCacheAndMetric() throws Exception {
    double before = counter("publication.created");

    String response = mvc.perform(post("/api/publications")
            .with(httpBasic("editor", "editor-password"))
            .header("Idempotency-Key", "create-001")
            .contentType(MediaType.APPLICATION_JSON)
            .content(requestBody("Spring boundaries")))
        .andExpect(status().isCreated())
        .andExpect(header().string(
            "Location",
            org.hamcrest.Matchers.startsWith("/api/publications/")))
        .andExpect(jsonPath("$.actorId").value("editor"))
        .andExpect(jsonPath("$.title").value("Spring boundaries"))
        .andReturn()
        .getResponse()
        .getContentAsString();

    String cacheKey = PublicationCache.key("editor", "create-001");
    assertThat(publications.count()).isEqualTo(1);
    assertThat(outbox.count()).isEqualTo(1);
    assertThat(redis.hasKey(cacheKey)).isTrue();
    assertThat(Objects.requireNonNull(redis.getExpire(cacheKey)))
        .isPositive();
    assertThat(counter("publication.created")).isEqualTo(before + 1.0);
    assertThat(response).contains("Spring boundaries");
  }

  @Test
  void duplicateRequestReturnsExistingResult() throws Exception {
    String first = createThroughHttp("duplicate-001", "Duplicate prevention", 201);
    double beforeDuplicate = counter("publication.duplicate");
    String second = createThroughHttp("duplicate-001", "Duplicate prevention", 200);

    assertThat(second).isEqualTo(first);
    assertThat(publications.count()).isEqualTo(1);
    assertThat(outbox.count()).isEqualTo(1);
    assertThat(counter("publication.duplicate"))
        .isEqualTo(beforeDuplicate + 1.0);
  }

  @Test
  void databaseResultWinsWhenCacheIsEmpty() throws Exception {
    String first = createThroughHttp("db-fallback-001", "Database source of truth", 201);
    flushRedis();
    POLICY.resetAll();
    rejectPolicy();

    String second = createThroughHttp("db-fallback-001", "Different input", 200);

    assertThat(second).isEqualTo(first);
    assertThat(POLICY.getAllServeEvents()).isEmpty();
    assertThat(publications.count()).isEqualTo(1);
    assertThat(outbox.count()).isEqualTo(1);
  }

  @Test
  void concurrentDuplicateRequestsCreateOnePublicationAndOneOutbox() throws Exception {
    int requestCount = 8;
    var executor = Executors.newFixedThreadPool(requestCount);
    var ready = new CountDownLatch(requestCount);
    var start = new CountDownLatch(1);
    List<Future<PublicationResult>> futures = new ArrayList<>();
    CreatePublicationRequest request = new CreatePublicationRequest(
        "Concurrent request",
        URI.create("https://example.test/concurrent"));

    try {
      for (int index = 0; index < requestCount; index++) {
        futures.add(executor.submit(() -> {
          ready.countDown();
          if (!start.await(10, TimeUnit.SECONDS)) {
            throw new IllegalStateException("Timed out while waiting to start concurrent requests.");
          }
          return service.create("editor", "concurrent-001", request);
        }));
      }
      assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
      start.countDown();

      List<PublicationResult> results = new ArrayList<>();
      for (Future<PublicationResult> future : futures) {
        results.add(future.get(30, TimeUnit.SECONDS));
      }

      assertThat(results.stream().filter(PublicationResult::created).count())
          .isEqualTo(1);
      assertThat(publications.count()).isEqualTo(1);
      assertThat(outbox.count()).isEqualTo(1);
    } finally {
      executor.shutdownNow();
      assertThat(executor.awaitTermination(10, TimeUnit.SECONDS)).isTrue();
    }
  }

  @Test
  void policyRejectionDoesNotChangeDatabaseOrOpenCircuit() throws Exception {
    POLICY.resetAll();
    rejectPolicy();
    double before = counter("publication.policy.rejected");

    mvc.perform(post("/api/publications")
            .with(httpBasic("editor", "editor-password"))
            .header("Idempotency-Key", "rejected-001")
            .contentType(MediaType.APPLICATION_JSON)
            .content(requestBody("Rejected document")))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.errorCode").value("POLICY_REJECTED"));

    assertThat(publications.count()).isZero();
    assertThat(outbox.count()).isZero();
    assertThat(counter("publication.policy.rejected"))
        .isEqualTo(before + 1.0);
    assertThat(circuitBreakers.circuitBreaker("policy")
        .getMetrics().getNumberOfFailedCalls()).isZero();
  }

  @Test
  void dependencyFailureBecomesServiceUnavailable() throws Exception {
    POLICY.resetAll();
    POLICY.stubFor(com.github.tomakehurst.wiremock.client.WireMock.post(
        urlEqualTo("/policy/check"))
        .willReturn(aResponse().withStatus(500)));

    mvc.perform(post("/api/publications")
            .with(httpBasic("editor", "editor-password"))
            .header("Idempotency-Key", "dependency-001")
            .contentType(MediaType.APPLICATION_JSON)
            .content(requestBody("Dependency failure")))
        .andExpect(status().isServiceUnavailable())
        .andExpect(jsonPath("$.errorCode")
            .value("DEPENDENCY_UNAVAILABLE"));

    assertThat(publications.count()).isZero();
    assertThat(outbox.count()).isZero();
    assertThat(circuitBreakers.circuitBreaker("policy")
        .getMetrics().getNumberOfFailedCalls()).isEqualTo(1);
  }

  private String createThroughHttp(
      String idempotencyKey,
      String title,
      int expectedStatus) throws Exception {
    return mvc.perform(post("/api/publications")
            .with(httpBasic("editor", "editor-password"))
            .header("Idempotency-Key", idempotencyKey)
            .contentType(MediaType.APPLICATION_JSON)
            .content(requestBody(title)))
        .andExpect(status().is(expectedStatus))
        .andReturn()
        .getResponse()
        .getContentAsString();
  }

  private void allowPolicy() {
    POLICY.stubFor(com.github.tomakehurst.wiremock.client.WireMock.post(
        urlEqualTo("/policy/check"))
        .willReturn(aResponse()
            .withHeader("Content-Type", "application/json")
            .withBody("{\"allowed\":true}")));
  }

  private void rejectPolicy() {
    POLICY.stubFor(com.github.tomakehurst.wiremock.client.WireMock.post(
        urlEqualTo("/policy/check"))
        .willReturn(aResponse().withStatus(409)));
  }

  private void flushRedis() {
    try (RedisConnection connection = Objects.requireNonNull(
        redis.getConnectionFactory()).getConnection()) {
      connection.serverCommands().flushAll();
    }
  }

  private double counter(String name) {
    return Objects.requireNonNull(meters.find(name).counter()).count();
  }

  private String requestBody(String title) {
    return "{\"title\":\"" + title + "\","
        + "\"source\":\"https://example.test/source\"}";
  }
}
