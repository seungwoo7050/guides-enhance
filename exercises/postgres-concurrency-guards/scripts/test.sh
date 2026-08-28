#!/usr/bin/env bash
set -Eeuo pipefail

# [Implementation 4] 실제로 겹쳐 실행되는 두 session을 검증합니다.
# 독립된 psql process를 동시에 실행해 행 잠금과 guard 잠금이 성공 건수를 제한하는지 확인합니다.
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
compose=(docker compose -f "$root/compose.yaml" -p postgres-concurrency-guards)
temporary="$(mktemp -d)"

if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose v2 is required." >&2
    exit 1
fi

cleanup() {
    rm -rf "$temporary"
    "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT
"${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
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
    "${compose[@]}" exec -T db psql \
        -v ON_ERROR_STOP=1 \
        -U project \
        -d project \
        -Atq \
        -c "SET statement_timeout = '10s'; $1"
}

psql_stdin < "$root/setup.sql"
psql_stdin < "$root/functions.sql"

psql_cmd "SELECT reserve_inventory('book', 7);" >"$temporary/inventory-1" & first_pid=$!
psql_cmd "SELECT reserve_inventory('book', 7);" >"$temporary/inventory-2" & second_pid=$!
wait "$first_pid"
wait "$second_pid"

inventory_successes="$(grep -h -c '^t$' "$temporary/inventory-1" "$temporary/inventory-2" | awk '{sum += $1} END {print sum + 0}')"
available="$(psql_cmd "SELECT available FROM inventory WHERE sku = 'book';")"
[[ "$inventory_successes" == 1 ]] || {
    echo "inventory: expected one successful reservation, got $inventory_successes" >&2
    exit 1
}
[[ "$available" == 3 ]] || {
    echo "inventory: expected 3 units remaining, got $available" >&2
    exit 1
}

psql_cmd "UPDATE doctors SET on_call = true;" >/dev/null
psql_cmd "SELECT take_off_call(1);" >"$temporary/on-call-1" & first_pid=$!
psql_cmd "SELECT take_off_call(2);" >"$temporary/on-call-2" & second_pid=$!
wait "$first_pid"
wait "$second_pid"

on_call_successes="$(grep -h -c '^t$' "$temporary/on-call-1" "$temporary/on-call-2" | awk '{sum += $1} END {print sum + 0}')"
remaining="$(psql_cmd "SELECT count(*) FROM doctors WHERE on_call;")"
[[ "$on_call_successes" == 1 ]] || {
    echo "on-call: expected one successful removal, got $on_call_successes" >&2
    exit 1
}
[[ "$remaining" == 1 ]] || {
    echo "on-call: expected one doctor to remain, got $remaining" >&2
    exit 1
}

if psql_cmd "SELECT reserve_inventory('book', 0);" >/dev/null 2>&1; then
    echo "inventory: non-positive quantity was accepted" >&2
    exit 1
fi
