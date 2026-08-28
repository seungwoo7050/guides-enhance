package dev.guides.spring.idempotency;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OperationRepository extends JpaRepository<OperationRecord, UUID> {
  Optional<OperationRecord> findByIdempotencyKey(String idempotencyKey);
}
