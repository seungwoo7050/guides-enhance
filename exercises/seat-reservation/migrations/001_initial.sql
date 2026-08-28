-- [Implementation 1] Database-enforced reservation rules
create extension if not exists pgcrypto;

create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists reservations (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  user_id text not null,
  seat_no integer not null check (seat_no > 0),
  created_at timestamptz not null default now(),
  unique (event_id, seat_no)
);

create table if not exists reservation_audit (
  id uuid primary key default gen_random_uuid(),
  reservation_id uuid not null references reservations(id) on delete cascade,
  action text not null check (action in ('reserved')),
  created_at timestamptz not null default now()
);
