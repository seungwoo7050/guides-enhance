package dev.guides.spring.boundaries;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

// [Implementation 1] 설정 바인딩과 수량 범위 검증
// 최소·최대 수량이 모순되면 첫 요청 전 ApplicationContext 시작을 중단합니다.
@ConfigurationProperties("request.policy")
@Validated
public record RequestPolicyProperties(
    @Min(1) long minQuantity,
    @Min(1) long maxQuantity,
    @NotNull String category) {

  public RequestPolicyProperties {
    if (maxQuantity < minQuantity) {
      throw new IllegalArgumentException("max-quantity must be greater than or equal to min-quantity.");
    }
  }
}
