package dev.guides.spring.locking;

import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class InventoryService {
  private final InventoryRepository repository;

  public InventoryService(InventoryRepository repository) {
    this.repository = repository;
  }

  @Transactional
  public void create(UUID id, long initialQuantity) {
    repository.save(new InventoryItem(id, initialQuantity));
  }

  // [Implementation 5] 잠금 획득부터 commit까지 한 transaction에서 수행
  // 잠금 조회와 수량 변경을 분리하면 보호가 사라지므로 같은 transaction에 둡니다.
  @Transactional
  public boolean reserve(UUID id, long quantity) {
    InventoryItem item = repository.findByIdForUpdate(id).orElseThrow();
    return item.reserve(quantity);
  }

  @Transactional(readOnly = true)
  public long availableQuantity(UUID id) {
    return repository.findById(id).orElseThrow().availableQuantity();
  }
}
