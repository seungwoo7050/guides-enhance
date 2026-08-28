-- [Implementation 1] 처리 결과와 Outbox 재시도 상태 스키마 정의
-- 멱등성 key의 중복 완료를 막고 발행 실패와 다음 시도를 DB에 남깁니다.
create table operation_record (
  id uuid primary key,
  idempotency_key varchar(200) not null,
  quantity bigint not null,
  constraint uq_operation_idempotency_key unique (idempotency_key),
  constraint ck_operation_quantity_positive check (quantity > 0)
);

create table outbox_event (
  id uuid primary key,
  aggregate_id uuid not null,
  event_type varchar(100) not null,
  payload text not null,
  created_at timestamptz not null,
  published_at timestamptz,
  attempt_count integer not null default 0,
  next_attempt_at timestamptz not null,
  last_error varchar(500)
);

create index ix_outbox_event_due
  on outbox_event (next_attempt_at, created_at)
  where published_at is null;
