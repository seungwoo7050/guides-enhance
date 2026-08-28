#!/usr/bin/env bash
set -Eeuo pipefail

# [Implementation 4] index 정의, 실행 계획, 결과 순서를 검증합니다.
# catalog와 EXPLAIN을 확인하고 별도 Sort가 없는지, 반환 ID 순서가 정확한지 검사합니다.
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
compose=(docker compose -f "$root/compose.yaml" -p postgres-workload-indexes)

if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose v2 is required." >&2
    exit 1
fi

cleanup() {
    "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT
cleanup
"${compose[@]}" up -d >/dev/null

ready=0
for _ in {1..60}; do
    if "${compose[@]}" exec -T db pg_isready -U project -d project >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 1
done
[[ "$ready" == 1 ]] || { echo "PostgreSQL did not become ready." >&2; exit 1; }

psql_stdin() {
    "${compose[@]}" exec -T db psql -v ON_ERROR_STOP=1 -U project -d project
}

psql_cmd() {
    "${compose[@]}" exec -T db psql -v ON_ERROR_STOP=1 -U project -d project -Atq -c "$1"
}

psql_stdin < "$root/schema.sql"
psql_stdin < "$root/seed.sql"
psql_stdin < "$root/indexes.sql"
psql_cmd "ANALYZE events; ANALYZE jobs;" >/dev/null

events_definition="$(psql_cmd "SELECT pg_get_indexdef('events_tenant_created_id_idx'::regclass);")"
[[ "$events_definition" == *"(tenant_id, created_at DESC, id DESC) INCLUDE (kind, payload)"* ]] || {
    printf 'events index contract mismatch: %s\n' "$events_definition" >&2
    exit 1
}

jobs_definition="$(psql_cmd "SELECT pg_get_indexdef('jobs_pending_schedule_idx'::regclass);")"
[[ "$jobs_definition" == *"(scheduled_at, id) INCLUDE (payload)"* ]] || {
    printf 'jobs index key/include mismatch: %s\n' "$jobs_definition" >&2
    exit 1
}
[[ "$jobs_definition" == *"WHERE (status = 'PENDING'::text)"* ]] || {
    printf 'jobs partial predicate mismatch: %s\n' "$jobs_definition" >&2
    exit 1
}

plan_events="$(psql_cmd "SET enable_seqscan=off; SET enable_bitmapscan=off; EXPLAIN (COSTS OFF) SELECT id, created_at, kind, payload FROM events WHERE tenant_id=7 AND created_at <= '2025-01-03' ORDER BY created_at DESC, id DESC LIMIT 20;")"
grep -q 'events_tenant_created_id_idx' <<<"$plan_events" || { printf '%s\n' "$plan_events" >&2; exit 1; }
grep -Eq 'Index Only Scan|Index Scan' <<<"$plan_events" || { printf '%s\n' "$plan_events" >&2; exit 1; }
if grep -Eq '(^|[[:space:]])Sort([[:space:]]|$)' <<<"$plan_events"; then
    printf 'events plan contains an explicit Sort:\n%s\n' "$plan_events" >&2
    exit 1
fi

plan_jobs="$(psql_cmd "SET enable_seqscan=off; SET enable_bitmapscan=off; EXPLAIN (COSTS OFF) SELECT id, scheduled_at, payload FROM jobs WHERE status='PENDING' AND scheduled_at <= '2025-03-01' ORDER BY scheduled_at, id LIMIT 50;")"
grep -q 'jobs_pending_schedule_idx' <<<"$plan_jobs" || { printf '%s\n' "$plan_jobs" >&2; exit 1; }
grep -Eq 'Index Only Scan|Index Scan' <<<"$plan_jobs" || { printf '%s\n' "$plan_jobs" >&2; exit 1; }
if grep -Eq '(^|[[:space:]])Sort([[:space:]]|$)' <<<"$plan_jobs"; then
    printf 'jobs plan contains an explicit Sort:\n%s\n' "$plan_jobs" >&2
    exit 1
fi

actual_events="$(psql_cmd "SELECT string_agg(id::text, ',' ORDER BY created_at DESC, id DESC) FROM (SELECT id, created_at FROM events WHERE tenant_id=7 AND created_at <= '2025-01-03' ORDER BY created_at DESC, id DESC LIMIT 20) AS page;")"
expected_events='99956,99906,99856,99806,99756,99706,99656,99606,99556,99506,99456,99406,99356,99306,99256,99206,99156,99106,99056,99006'
[[ "$actual_events" == "$expected_events" ]] || {
    printf 'event ordering mismatch\nexpected=%s\nactual=%s\n' "$expected_events" "$actual_events" >&2
    exit 1
}

actual_jobs="$(psql_cmd "SELECT string_agg(id::text, ',' ORDER BY scheduled_at, id) FROM (SELECT id, scheduled_at FROM jobs WHERE status='PENDING' AND scheduled_at <= '2025-03-01' ORDER BY scheduled_at, id LIMIT 50) AS page;")"
expected_jobs='20,40,60,80,100,120,140,160,180,200,220,240,260,280,300,320,340,360,380,400,420,440,460,480,500,520,540,560,580,600,620,640,660,680,700,720,740,760,780,800,820,840,860,880,900,920,940,960,980,1000'
[[ "$actual_jobs" == "$expected_jobs" ]] || {
    printf 'job ordering mismatch\nexpected=%s\nactual=%s\n' "$expected_jobs" "$actual_jobs" >&2
    exit 1
}
