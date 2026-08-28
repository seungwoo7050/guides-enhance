package dev.guides.spring.idempotency;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface OutboxRepository extends JpaRepository<OutboxEvent, UUID> {
  @Query("""
      select event
      from OutboxEvent event
      where event.publishedAt is null
        and event.nextAttemptAt <= :now
      order by event.createdAt
      """)
  List<OutboxEvent> findDue(@Param("now") Instant now, Pageable pageable);
}
