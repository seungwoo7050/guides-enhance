#!/usr/bin/env bash
set -euo pipefail
binary="${1:?binary path required}"
actual="$(mktemp)"
expected="$(mktemp)"
trap 'rm -f "$actual" "$expected"' EXIT

cat >"$expected" <<'OUT'
OK
VALUE one
CONFLICT
OK
FULL
COUNT 2
alpha=one
beta=two
DELETED
NOT_FOUND
NOT_FOUND
BAD_REQUEST
BAD_REQUEST
BYE
OUT

printf '%s\n' \
    'PUT alpha one' \
    'GET alpha' \
    'PUT alpha replacement' \
    'PUT beta two' \
    'PUT gamma three' \
    'COUNT' \
    'LIST' \
    'DELETE alpha' \
    'GET alpha' \
    'DELETE alpha' \
    'PUT only-key' \
    'UNKNOWN' \
    'QUIT' \
    'GET beta' \
    | "$binary" 2 >"$actual"

diff -u "$expected" "$actual"
! "$binary" 0 </dev/null >/dev/null 2>&1
! "$binary" invalid </dev/null >/dev/null 2>&1
echo 'command-service CLI tests: passed'
