package dev.guides.spring.locking;

import jakarta.persistence.LockModeType;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface InventoryRepository extends JpaRepository<InventoryItem, UUID> {
  // [Implementation 4] 재고 행을 쓰기 잠금으로 조회
  // 같은 행을 수정하는 transaction이 잠금 해제 전까지 순서대로 대기하게 합니다.
  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query("select item from InventoryItem item where item.id = :id")
  Optional<InventoryItem> findByIdForUpdate(@Param("id") UUID id);
}
