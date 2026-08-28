package dev.guides.spring.publication;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.stereotype.Component;

@Component
public final class PublicationMetrics {
  private final Counter created;
  private final Counter duplicate;
  private final Counter rejected;
  private final Counter cacheFailure;

  public PublicationMetrics(MeterRegistry registry) {
    this.created = registry.counter("publication.created");
    this.duplicate = registry.counter("publication.duplicate");
    this.rejected = registry.counter("publication.policy.rejected");
    this.cacheFailure = registry.counter("publication.cache.failure");
  }

  public void created() {
    created.increment();
  }

  public void duplicate() {
    duplicate.increment();
  }

  public void rejected() {
    rejected.increment();
  }

  public void cacheFailure() {
    cacheFailure.increment();
  }
}
