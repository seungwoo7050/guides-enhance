#!/usr/bin/env bash
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
compose=(docker compose -f "$root/compose.yaml" -p ticketing-database)

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
psql_stdin < "$root/migration.sql"
psql_stdin < "$root/migration.sql"
psql_stdin < "$root/queries.sql"
psql_stdin < "$root/queries.sql"
psql_stdin < "$root/indexes.sql"
psql_stdin < "$root/indexes.sql"
psql_stdin < "$root/tests/verify.sql"
psql_cmd "ANALYZE tickets;" >/dev/null

assert_index_definition() {
    local name="$1" required_keys="$2" required_predicate="$3" actual
    actual="$(psql_cmd "SELECT pg_get_indexdef('$name'::regclass);")"
    [[ "$actual" == *"$required_keys"* ]] || {
        printf '%s key definition mismatch:\n%s\n' "$name" "$actual" >&2
        exit 1
    }
    [[ "$actual" == *"$required_predicate"* ]] || {
        printf '%s predicate mismatch:\n%s\n' "$name" "$actual" >&2
        exit 1
    }
}

assert_plan() {
    local name="$1" query="$2" label="$3" plan
    plan="$(psql_cmd "SET enable_seqscan=off; SET enable_bitmapscan=off; EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF) $query")"
    grep -Eq "Index (Only )?Scan using $name" <<<"$plan" || {
        printf '%s plan did not use %s:\n%s\n' "$label" "$name" "$plan" >&2
        exit 1
    }
    if grep -Eq '(^|[[:space:]])Sort([[:space:]]|$)' <<<"$plan"; then
        printf '%s plan contains an explicit Sort:\n%s\n' "$label" "$plan" >&2
        exit 1
    fi
}

assert_index_definition \
    tickets_org_open_priority_created_idx \
    '(org_id, priority DESC, created_at DESC, id DESC)' \
    "WHERE (status <> 'DONE'::text)"
assert_index_definition \
    tickets_project_open_created_idx \
    '(org_id, project_id, created_at, id)' \
    "WHERE (status <> 'DONE'::text)"
assert_index_definition \
    tickets_assignee_queue_idx \
    '(org_id, assignee_id, priority DESC, created_at, id)' \
    "((status <> 'DONE'::text) AND (assignee_id IS NOT NULL))"

assert_plan \
    tickets_org_open_priority_created_idx \
    "SELECT id, priority, created_at FROM tickets WHERE org_id=1 AND status <> 'DONE' AND (priority, created_at, id) < (4, TIMESTAMPTZ '2025-01-02 00:00:00+00', 101) ORDER BY priority DESC, created_at DESC, id DESC LIMIT 2;" \
    'organization page'
assert_plan \
    tickets_assignee_queue_idx \
    "SELECT id, priority, created_at FROM tickets WHERE org_id=1 AND assignee_id=2 AND status <> 'DONE' ORDER BY priority DESC, created_at, id;" \
    'assignee queue'
assert_plan \
    tickets_project_open_created_idx \
    "SELECT id, created_at FROM tickets WHERE org_id=1 AND project_id=10 AND status <> 'DONE' ORDER BY created_at, id;" \
    'project backlog scan'
