#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
COMPOSE_FILE="$SCRIPT_DIR/compose.yaml"
PROJECT="single-broker-kraft-${UID:-0}-${BASHPID:-$$}-${RANDOM:-0}"
TOPIC="standalone-events"
GROUP="standalone-verification-${RANDOM:-0}"
MESSAGE="single-broker-kraft-message"

log() {
  printf '[single-broker-kraft] %s\n' "$*"
}

compose() {
  KRAFT_RUN_ID="$PROJECT" docker compose \
    -p "$PROJECT" \
    -f "$COMPOSE_FILE" \
    "$@"
}

cleanup() {
  compose down --volumes --remove-orphans >/dev/null 2>&1 || true
}

static_check() {
  python3 - "$COMPOSE_FILE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
required = {
    "apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837",
    'KAFKA_PROCESS_ROLES: broker,controller',
    'KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093',
    'KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: "1"',
    'KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: "1"',
    'KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: "1"',
    'kafka-topics.sh --bootstrap-server localhost:9092 --list',
}
missing = sorted(value for value in required if value not in text)
if missing:
    raise SystemExit("missing KRaft contract values: " + ", ".join(missing))
print("single-broker KRaft static contract verified")
PY

  if command -v docker >/dev/null 2>&1 \
      && docker compose version >/dev/null 2>&1; then
    KRAFT_RUN_ID="$PROJECT" docker compose \
      -p "$PROJECT" \
      -f "$COMPOSE_FILE" \
      config >/dev/null
  fi
}

wait_for_broker() {
  local attempt
  for attempt in $(seq 1 60); do
    if compose exec -T kafka \
      /opt/kafka/bin/kafka-topics.sh \
      --bootstrap-server localhost:9092 \
      --list >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  compose logs kafka >&2 || true
  return 1
}

# [Implementation 4] 독립된 Compose 실행과 정리
# 고유한 project name을 사용해 시작, 메시지 경로 확인과 자원 정리를 한 실행에 묶습니다.
run_integration() {
  local direct_output
  local group_output

  command -v docker >/dev/null 2>&1 || {
    printf 'docker is required for the integration smoke test\n' >&2
    return 1
  }
  docker compose version >/dev/null 2>&1 || {
    printf 'Docker Compose v2 is required\n' >&2
    return 1
  }
  docker info >/dev/null 2>&1 || {
    printf 'Docker daemon is not available\n' >&2
    return 1
  }

  trap cleanup EXIT HUP INT TERM
  cleanup
  compose up -d
  wait_for_broker

  compose exec -T kafka \
    /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create \
    --if-not-exists \
    --topic "$TOPIC" \
    --partitions 1 \
    --replication-factor 1 >/dev/null

  printf '%s\n' "$MESSAGE" | compose exec -T kafka \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server localhost:9092 \
    --topic "$TOPIC" >/dev/null

  direct_output="$(compose exec -T kafka \
    /opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic "$TOPIC" \
    --partition 0 \
    --offset earliest \
    --max-messages 1 \
    --timeout-ms 12000 2>&1)"
  [[ "$direct_output" == *"$MESSAGE"* ]] || {
    printf '%s\n' "$direct_output" >&2
    printf 'direct partition consumer did not read the message\n' >&2
    return 1
  }

  group_output="$(compose exec -T kafka \
    /opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic "$TOPIC" \
    --group "$GROUP" \
    --from-beginning \
    --max-messages 1 \
    --timeout-ms 12000 2>&1)"
  [[ "$group_output" == *"$MESSAGE"* ]] || {
    printf '%s\n' "$group_output" >&2
    printf 'consumer group did not read the message\n' >&2
    return 1
  }

  log "broker API, direct consumption, and consumer-group consumption verified"
}

case "${1:-}" in
  --static)
    static_check
    ;;
  --cleanup)
    cleanup
    ;;
  "")
    static_check
    run_integration
    ;;
  *)
    printf 'usage: %s [--static|--cleanup]\n' "$0" >&2
    exit 2
    ;;
esac
