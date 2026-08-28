package dev.guides.spring.failclosed;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

// [Implementation 1] 주소·timeout·재시도 횟수 검증
// 잘못된 외부 주소와 비양수 timeout은 요청을 보내기 전에 시작 단계에서 거부합니다.
@ConfigurationProperties("clients.decision")
@Validated
public record DecisionClientProperties(
    @NotBlank String baseUrl,
    @NotNull Duration connectTimeout,
    @NotNull Duration readTimeout,
    @Min(1) @Max(3) int maxAttempts) {
  public DecisionClientProperties {
    requirePositive(connectTimeout, "connect-timeout");
    requirePositive(readTimeout, "read-timeout");
  }

  private static void requirePositive(Duration value, String name) {
    if (value != null && (value.isZero() || value.isNegative())) {
      throw new IllegalArgumentException(name + " must be positive.");
    }
  }
}
