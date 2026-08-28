package dev.guides.spring.failclosed;

import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class DecisionClient {
  private final RestClient client;
  private final int maxAttempts;

  public DecisionClient(RestClient decisionRestClient, DecisionClientProperties properties) {
    this.client = decisionRestClient;
    this.maxAttempts = properties.maxAttempts();
  }

  // [Implementation 3] 정해진 횟수만 재시도하고 실패 유형 구분
  // 409 업무 거절은 즉시 반환하고 통신·응답 오류만 제한된 횟수로 다시 시도합니다.
  @CircuitBreaker(name = "decisionClient")
  public DecisionResponse check(DecisionRequest request) {
    DependencyUnavailableException lastFailure = null;
    for (int attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        DecisionResponse response =
            client
                .post()
                .uri("/decision")
                .body(request)
                .retrieve()
                .onStatus(
                    status -> status.value() == 409,
                    (httpRequest, httpResponse) -> {
                      throw new BusinessDeclineException("The request was declined by policy.");
                    })
                .body(DecisionResponse.class);
        if (response == null) {
          throw new DependencyUnavailableException("The dependency returned an empty response.", null);
        }
        return response;
      } catch (BusinessDeclineException exception) {
        throw exception;
      } catch (DependencyUnavailableException exception) {
        lastFailure = exception;
      } catch (RestClientException exception) {
        lastFailure = new DependencyUnavailableException("The dependency is unavailable.", exception);
      }
    }
    throw lastFailure;
  }
}
