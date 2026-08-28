package dev.guides.spring.publication;

import jakarta.validation.constraints.NotNull;
import java.net.URI;
import java.time.Duration;
import java.util.Set;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@ConfigurationProperties("policy.client")
@Validated
public record PolicyClientProperties(
    @NotNull URI baseUrl,
    @NotNull Duration timeout) {
  private static final Set<String> ALLOWED_SCHEMES = Set.of("http", "https");

  public PolicyClientProperties {
    if (baseUrl != null
        && (!baseUrl.isAbsolute()
            || !ALLOWED_SCHEMES.contains(baseUrl.getScheme()))) {
      throw new IllegalArgumentException(
          "policy.client.base-url must be an absolute HTTP or HTTPS URI.");
    }
    if (timeout != null && (timeout.isZero() || timeout.isNegative())) {
      throw new IllegalArgumentException("policy.client.timeout must be positive.");
    }
  }
}
