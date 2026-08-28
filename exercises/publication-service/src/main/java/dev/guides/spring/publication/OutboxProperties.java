package dev.guides.spring.publication;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@ConfigurationProperties("publication.outbox")
@Validated
public record OutboxProperties(
    boolean publisherEnabled,
    @NotBlank String topic,
    @NotNull Duration pollInterval) {
  public OutboxProperties {
    if (pollInterval != null
        && (pollInterval.isZero() || pollInterval.isNegative())) {
      throw new IllegalArgumentException(
          "publication.outbox.poll-interval must be positive.");
    }
  }
}
