#!/usr/bin/env bash
set -euo pipefail

PROJECT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
MAVEN=${MAVEN:-mvn}
WORK=$(mktemp -d "${TMPDIR:-/tmp}/maven-artifact-boundary.XXXXXX")
REPOSITORY="$WORK/repository"
BEFORE_LOG="$WORK/before-install.log"

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

cleanup() {
  rm -rf \
    "$WORK" \
    "$PROJECT/contract-library/target" \
    "$PROJECT/consumer-service/target"
}

trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

command -v "$MAVEN" >/dev/null 2>&1 || fail "Maven executable not found: $MAVEN"
mkdir -p "$REPOSITORY"

SEED=${MAVEN_REPOSITORY_SEED:-${HOME:-}/.m2/repository}
if [[ -n "$SEED" && -d "$SEED" ]]; then
  cp -a "$SEED"/. "$REPOSITORY"/
fi
rm -rf "$REPOSITORY/dev/guides/contract-library"

COMMON=(-B -ntp -Dmaven.repo.local="$REPOSITORY")

set +e
"$MAVEN" "${COMMON[@]}" -f "$PROJECT/consumer-service/pom.xml" test \
  >"$BEFORE_LOG" 2>&1
before_status=$?
set -e

[[ $before_status -ne 0 ]] || fail "consumer succeeded before producer installation"
if ! grep -Eq 'dev\.guides:contract-library|contract-library:jar:1\.0-SNAPSHOT' "$BEFORE_LOG"; then
  cat "$BEFORE_LOG" >&2
  fail "consumer failed for a reason other than the missing producer artifact"
fi
printf '[PASS] consumer failed before producer installation\n'

# [Implementation 3] 격리한 로컬 저장소에서 설치 전 실패와 설치 후 성공을 재현합니다.
"$MAVEN" "${COMMON[@]}" -f "$PROJECT/contract-library/pom.xml" clean install
"$MAVEN" "${COMMON[@]}" -f "$PROJECT/consumer-service/pom.xml" clean test
printf '[PASS] consumer succeeded after producer installation\n'
