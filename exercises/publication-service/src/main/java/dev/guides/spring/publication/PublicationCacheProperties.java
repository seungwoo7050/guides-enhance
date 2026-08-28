package dev.guides.spring.publication;

import jakarta.validation.constraints.NotNull;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@ConfigurationProperties("publication.cache")
@Validated
public record PublicationCacheProperties(@NotNull Duration ttl) {
  public PublicationCacheProperties {
    if (ttl != null && (ttl.isZero() || ttl.isNegative())) {
      throw new IllegalArgumentException("publication.cache.ttl must be positive.");
    }
  }
}
