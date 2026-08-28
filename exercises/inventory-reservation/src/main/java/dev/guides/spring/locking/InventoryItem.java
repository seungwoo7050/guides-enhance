package dev.guides.spring.locking;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

// [Implementation 3] 가용 수량과 차감 불변식 유지
// 차감 성공 뒤 가용 수량이 음수가 되는 상태를 허용하지 않습니다.
@Entity
@Table(name = "inventory_item")
public class InventoryItem {
  @Id private UUID id;

  @Column(nullable = false)
  private long availableQuantity;

  protected InventoryItem() {}

  public InventoryItem(UUID id, long availableQuantity) {
    if (availableQuantity < 0) {
      throw new IllegalArgumentException("Available quantity cannot be negative.");
    }
    this.id = id;
    this.availableQuantity = availableQuantity;
  }

  public UUID id() {
    return id;
  }

  public long availableQuantity() {
    return availableQuantity;
  }

  public boolean reserve(long quantity) {
    if (quantity <= 0) {
      throw new IllegalArgumentException("Reservation quantity must be greater than zero.");
    }
    if (availableQuantity < quantity) {
      return false;
    }
    availableQuantity -= quantity;
    return true;
  }
}
