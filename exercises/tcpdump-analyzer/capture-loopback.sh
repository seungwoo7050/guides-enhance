#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    printf '%s\n' "tcpdump capture requires elevated privileges; run with sudo." >&2
    exit 1
fi
for command in python3 tcpdump; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf '%s\n' "Required command not found: $command" >&2
        exit 1
    fi
done

# [Implementation 5] Capture argument validation
# 기존 캡처 파일은 덮어쓰지 않아 이전 관찰 결과를 보존합니다.
PORT=${PORT:-18080}
OUTPUT=${OUTPUT:-capture.txt}
SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
SERVER_LOG=$(mktemp)
SERVER_PID=
CAPTURE_PID=

case "$(uname -s)" in
    Darwin) INTERFACE=${INTERFACE:-lo0} ;;
    Linux) INTERFACE=${INTERFACE:-lo} ;;
    *)
        printf '%s\n' "Unsupported operating system." >&2
        exit 1
        ;;
esac

if [ -e "$OUTPUT" ]; then
    printf '%s\n' "Refusing to overwrite an existing capture: $OUTPUT" >&2
    exit 1
fi

# [Implementation 5-1] Started-process cleanup
# PID를 기록한 프로세스만 종료해 같은 호스트의 다른 서버나 tcpdump에 영향을 주지 않습니다.
cleanup() {
    if [ -n "$CAPTURE_PID" ]; then
        kill -INT "$CAPTURE_PID" 2>/dev/null || true
        wait "$CAPTURE_PID" 2>/dev/null || true
    fi
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -f "$SERVER_LOG"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

# [Implementation 5-2] Loopback capture execution
# 서버와 tcpdump가 실제로 실행 중인지 확인한 뒤 요청을 보내 캡처 누락을 줄입니다.
python3 -m http.server "$PORT" --bind 127.0.0.1 >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!
sleep 1
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    cat "$SERVER_LOG" >&2
    exit 1
fi

tcpdump -i "$INTERFACE" -nn -tt -l "tcp port $PORT" >"$OUTPUT" 2>/dev/null &
CAPTURE_PID=$!
sleep 1
if ! kill -0 "$CAPTURE_PID" 2>/dev/null; then
    printf '%s\n' "tcpdump exited before the request was generated." >&2
    exit 1
fi

python3 - "$PORT" <<'PYCLIENT'
import http.client
import sys

port = int(sys.argv[1])
connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
connection.request("GET", "/")
response = connection.getresponse()
response.read()
connection.close()
if response.status != 200:
    raise SystemExit(f"Unexpected HTTP status: {response.status}")
PYCLIENT

sleep 0.5
kill -INT "$CAPTURE_PID"
wait "$CAPTURE_PID" || true
CAPTURE_PID=
python3 "$SCRIPT_DIR/tcpdump_analyzer.py" "$OUTPUT"
