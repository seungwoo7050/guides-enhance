package dev.guides.spring.publication;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PublicationRepository
    extends JpaRepository<PublicationEntity, UUID> {
  Optional<PublicationEntity> findByActorIdAndIdempotencyKey(
      String actorId,
      String idempotencyKey);
}
