package dev.guides.spring.publication;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OutboxEventRepository
    extends JpaRepository<OutboxEventEntity, UUID> {
  List<OutboxEventEntity> findTop50ByPublishedAtIsNullOrderByCreatedAtAsc();
}
