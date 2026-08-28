-- [Implementation 2] 재고 테이블과 음수 방지 제약 정의
-- 애플리케이션 검사를 우회한 쓰기에서도 가용 수량이 음수가 되지 않게 합니다.
create table inventory_item (
  id uuid primary key,
  available_quantity bigint not null,
  constraint ck_inventory_available_quantity_non_negative check (available_quantity >= 0)
);
