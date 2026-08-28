#!/usr/bin/env bash
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
compose=(docker compose -f "$root/compose.yaml" -p sql-semantics-views)

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

psql_stdin < "$root/schema.sql"
psql_stdin < "$root/seed.sql"
psql_stdin < "$root/views.sql"
psql_stdin < "$root/tests/verify.sql"
