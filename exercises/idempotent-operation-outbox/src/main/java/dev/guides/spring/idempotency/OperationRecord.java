package dev.guides.spring.idempotency;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

// [Implementation 2] PostgreSQL 완료 행을 멱등 처리 결과로 사용
// Redis 유무와 관계없이 commit된 행이 같은 key의 최종 결과를 결정합니다.
@Entity
@Table(name = "operation_record")
public class OperationRecord {
  @Id private UUID id;

  @Column(name = "idempotency_key", nullable = false, unique = true)
  private String idempotencyKey;

  @Column(nullable = false)
  private long quantity;

  protected OperationRecord() {}

  public OperationRecord(UUID id, String idempotencyKey, long quantity) {
    this.id = id;
    this.idempotencyKey = idempotencyKey;
    this.quantity = quantity;
  }

  public OperationResult result() {
    return new OperationResult(id, quantity);
  }
}
