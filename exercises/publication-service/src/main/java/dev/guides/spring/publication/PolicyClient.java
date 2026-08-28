package dev.guides.spring.publication;

import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class PolicyClient {
  private final RestClient client;

  public PolicyClient(RestClient policyRestClient) {
    this.client = policyRestClient;
  }

  // [Implementation 4] 업무 거절과 의존성 장애 구분
  // 409는 정상 판단으로 유지하고 통신·서버·응답 형식 오류만 장애로 변환합니다.
  @CircuitBreaker(name = "policy")
  public void ensureAllowed(
      String actorId,
      CreatePublicationRequest request) {
    try {
      PolicyDecision decision = client.post()
          .uri("/policy/check")
          .body(new PolicyRequest(
              actorId,
              request.title(),
              request.source().toString()))
          .retrieve()
          .onStatus(
              status -> status.value() == 409,
              (httpRequest, response) -> {
                throw new PolicyRejectedException();
              })
          .body(PolicyDecision.class);
      if (decision == null || !decision.allowed()) {
        throw new PolicyRejectedException();
      }
    } catch (PolicyRejectedException exception) {
      throw exception;
    } catch (HttpClientErrorException exception) {
      HttpStatusCode status = exception.getStatusCode();
      throw new DependencyUnavailableException(
          "The policy service returned an unexpected response: "
              + status.value(),
          exception);
    } catch (RestClientException exception) {
      throw new DependencyUnavailableException(
          "The policy service is unavailable.",
          exception);
    }
  }

  private record PolicyRequest(String actorId, String title, String source) {}

  private record PolicyDecision(boolean allowed) {}
}
