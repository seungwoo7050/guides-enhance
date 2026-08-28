package dev.guides.spring.failclosed;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.equalToJson;
import static com.github.tomakehurst.wiremock.client.WireMock.post;
import static com.github.tomakehurst.wiremock.client.WireMock.postRequestedFor;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.github.tomakehurst.wiremock.core.WireMockConfiguration;
import com.github.tomakehurst.wiremock.http.Fault;
import com.github.tomakehurst.wiremock.stubbing.Scenario;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

@SpringBootTest
class DecisionClientIntegrationTest {
  static final WireMockServer WIREMOCK =
      new WireMockServer(WireMockConfiguration.wireMockConfig().dynamicPort());

  static {
    WIREMOCK.start();
  }

  @DynamicPropertySource
  static void clientProperties(DynamicPropertyRegistry registry) {
    registry.add("clients.decision.base-url", WIREMOCK::baseUrl);
  }

  @AfterAll
  static void stopServer() {
    WIREMOCK.stop();
  }

  @Autowired DecisionClient client;
  @Autowired CircuitBreakerRegistry registry;
  CircuitBreaker breaker;

  @BeforeEach
  void reset() {
    WIREMOCK.resetAll();
    breaker = registry.circuitBreaker("decisionClient");
    breaker.reset();
  }

  @Test
  void businessDeclinesDoNotOpenCircuit() {
    WIREMOCK.stubFor(post("/decision").willReturn(aResponse().withStatus(409)));
    for (int i = 0; i < 5; i++) {
      String requestId = "request-" + i;
      assertThatThrownBy(() -> client.check(new DecisionRequest(requestId, 100)))
          .isInstanceOf(BusinessDeclineException.class);
    }
    assertThat(breaker.getState()).isEqualTo(CircuitBreaker.State.CLOSED);
  }

  @Test
  void infrastructureFailuresOpenCircuit() {
    WIREMOCK.stubFor(post("/decision").willReturn(aResponse().withStatus(500)));
    for (int i = 0; i < 2; i++) {
      String requestId = "request-" + i;
      assertThatThrownBy(() -> client.check(new DecisionRequest(requestId, 100)))
          .isInstanceOf(DependencyUnavailableException.class);
    }
    assertThat(breaker.getState()).isEqualTo(CircuitBreaker.State.OPEN);
  }

  @Test
  void delayedResponseUsesTheReadTimeout() {
    WIREMOCK.stubFor(
        post("/decision")
            .willReturn(
                aResponse()
                    .withStatus(200)
                    .withFixedDelay(750)
                    .withHeader("content-type", "application/json")
                    .withBody("{\"approved\":true}")));
    assertThatThrownBy(() -> client.check(new DecisionRequest("slow-request", 10)))
        .isInstanceOf(DependencyUnavailableException.class);
    WIREMOCK.verify(2, postRequestedFor(urlEqualTo("/decision")));
  }

  @Test
  void connectionResetBecomesDependencyFailure() {
    WIREMOCK.stubFor(
        post("/decision").willReturn(aResponse().withFault(Fault.CONNECTION_RESET_BY_PEER)));
    assertThatThrownBy(() -> client.check(new DecisionRequest("reset-request", 10)))
        .isInstanceOf(DependencyUnavailableException.class);
    WIREMOCK.verify(2, postRequestedFor(urlEqualTo("/decision")));
  }

  @Test
  void malformedJsonBecomesDependencyFailure() {
    WIREMOCK.stubFor(
        post("/decision")
            .willReturn(
                aResponse()
                    .withStatus(200)
                    .withHeader("content-type", "application/json")
                    .withBody("{\"approved\":")));
    assertThatThrownBy(() -> client.check(new DecisionRequest("invalid-json", 10)))
        .isInstanceOf(DependencyUnavailableException.class);
    WIREMOCK.verify(2, postRequestedFor(urlEqualTo("/decision")));
  }

  @Test
  void retryBudgetReusesTheSameRequestIdentifier() {
    WIREMOCK.stubFor(
        post("/decision")
            .inScenario("retry")
            .whenScenarioStateIs(Scenario.STARTED)
            .willSetStateTo("recovered")
            .willReturn(aResponse().withStatus(500)));
    WIREMOCK.stubFor(
        post("/decision")
            .inScenario("retry")
            .whenScenarioStateIs("recovered")
            .willReturn(
                aResponse()
                    .withStatus(200)
                    .withHeader("content-type", "application/json")
                    .withBody("{\"approved\":true}")));

    assertThat(client.check(new DecisionRequest("stable-request", 10)).approved()).isTrue();
    WIREMOCK.verify(
        2,
        postRequestedFor(urlEqualTo("/decision"))
            .withRequestBody(equalToJson("{\"requestId\":\"stable-request\",\"itemCount\":10}")));
  }
}
