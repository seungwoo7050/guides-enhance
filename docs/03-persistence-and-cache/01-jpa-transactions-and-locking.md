# JPA 트랜잭션과 잠금

> 읽는 시점: 실제 프로젝트에서 여러 데이터 변경을 한 번에 처리하거나 동시 수정을 제어할 때

`@Transactional`은 데이터베이스 transaction을 시작하는 Spring 기능입니다. annotation이 붙어 있다고 해서 업무 규칙, proxy 호출, 잠금 방식이 자동으로 올바르게 결정되는 것은 아닙니다. 먼저 어떤 상태가 함께 성공하거나 함께 실패해야 하는지 정해야 합니다.

## 함께 저장할 상태부터 정합니다

transaction 범위는 repository 호출 개수가 아니라 업무 불변식으로 결정합니다.

```text
재고 수량 감소
+ 예약 기록 저장
+ Outbox 행 저장
```

이 세 변경이 하나의 업무 결정이라면 같은 transaction에서 저장합니다. 반대로 외부 HTTP 요청이나 Kafka 응답을 기다리는 동안 DB connection과 row lock을 오래 잡지 않습니다.

## 실제 proxy 호출을 확인합니다

다음 코드는 `reserve()`의 transaction이 적용되지 않을 수 있습니다.

```java
@Service
class ReservationService {
  void handle() {
    reserve();
  }

  @Transactional
  void reserve() {
    // ...
  }
}
```

같은 객체 안의 직접 호출은 Spring proxy를 통과하지 않을 수 있습니다. transaction을 시작해야 하는 작업을 별도 Bean의 public method로 분리하고, Spring Context를 사용하는 통합 테스트에서 commit과 rollback을 확인합니다.

순수 단위 테스트는 entity의 계산 규칙을 확인할 수 있지만 `@Transactional` 적용 여부까지 검증하지는 못합니다.

## JPA entity를 HTTP 응답으로 직접 내보내지 않습니다

Open Session in View에 기대어 응답 직렬화 중 lazy query가 실행되게 하지 않습니다. application service의 transaction 안에서 필요한 값을 읽고 DTO로 변환한 뒤 Controller에 전달합니다.

cascade와 orphan removal은 단순 편의 기능이 아닙니다. 어떤 entity를 함께 저장하거나 삭제할지 결정하므로 aggregate 안의 실제 소유 관계에만 사용합니다. 관계 양쪽에 무조건 cascade를 붙이면 예상하지 않은 대량 저장과 삭제가 생길 수 있습니다.

## 비관적 잠금은 같은 행의 수정을 순서대로 처리합니다

같은 행을 읽고 조건을 검사한 뒤 즉시 수정해야 한다면 비관적 쓰기 잠금을 사용할 수 있습니다.

```java
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("select item from InventoryItem item where item.id = :id")
Optional<InventoryItem> findByIdForUpdate(UUID id);
```

- 실제로 경쟁하는 행만 잠급니다.
- 여러 행을 잠글 때는 항상 같은 순서로 조회합니다.
- 잠금 대기 시간 초과와 교착 상태를 애플리케이션 오류로 바꿉니다.
- 재시도할 때 외부 효과가 반복되지 않는지 확인합니다.

잠금은 transaction이 끝날 때까지 유지되므로 잠금 조회와 상태 변경을 같은 transaction 안에서 수행해야 합니다.

## 낙관적 잠금과 조건부 update도 검토합니다

충돌이 드물고 작업을 다시 시도해도 안전하다면 `@Version`을 사용할 수 있습니다. 단순 수량 차감은 조건부 SQL이 더 직접적일 수 있습니다.

```sql
update inventory
set available = available - :amount
where id = :id
  and available >= :amount;
```

수정된 행이 1개면 성공이고 0개면 재고 부족 또는 대상 없음으로 처리할 수 있습니다.

아직 존재하지 않는 행을 생성하는 경쟁은 row lock만으로 막을 수 없습니다. PostgreSQL을 사용하는 경우 안정적인 key로 transaction-scoped advisory lock을 얻은 뒤 다시 조회하고 생성할 수 있습니다.

```text
transaction 시작
→ advisory lock 획득
→ 같은 key의 기존 결과 재조회
→ 없으면 새 행 저장
→ commit과 함께 lock 해제
```

advisory lock을 사용한다면 key 생성 규칙과 충돌 가능성을 테스트에 고정합니다. DBMS 독립성이 필요하면 별도 잠금 행, 조건부 insert, unique constraint 처리 같은 다른 방식을 선택합니다.

## 최종 상태를 함께 검사합니다

동시성 테스트는 성공 응답 개수만 확인하지 않습니다.

- 성공한 요청 수
- 최종 데이터베이스 값
- 생성된 행 수
- constraint 위반 여부
- 모든 thread와 executor 종료 여부

thread를 많이 만들고 `sleep`하는 것만으로는 경쟁 구간을 재현하기 어렵습니다. latch나 barrier로 작업자 준비와 시작을 나누고, 모든 `Future`의 결과를 제한 시간 안에 회수합니다.

## Rewind가 필요한 징후

- `@Transactional` method가 같은 클래스 안에서 호출됩니다.
- 일부 행만 저장되고 나머지 변경이 빠집니다.
- 동시에 같은 요청이 들어오면 중복 행이나 음수 수량이 생깁니다.
- transaction 안에서 외부 HTTP 응답을 오래 기다립니다.
- 테스트가 응답 상태만 확인하고 최종 DB 상태를 확인하지 않습니다.

프로젝트 완료 뒤 이 능력을 확인하려면 [`inventory-reservation`](../../exercises/inventory-reservation/)을 Guide 없이 구현합니다.
