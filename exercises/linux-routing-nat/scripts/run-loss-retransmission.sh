#!/bin/sh
set -eu
export LC_ALL=C

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
VERIFIER="$SCRIPT_DIR/verify_syn_retransmission.py"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

"$SCRIPT_DIR/preflight.sh" loss

# [Implementation 6-2] Loss-run process, qdisc, and file tracking
# 이 실행에서 만든 qdisc, 프로세스와 임시 파일만 종료할 때 정리합니다.
TRACE=$(mktemp)
REPORT=$(mktemp)
SERVER_PID=
CLIENT_PID=
CAPTURE_PID=
cleanup() {
    ip netns exec "$ROUTER" tc qdisc del dev r1 root 2>/dev/null || true
    for pid in "$CLIENT_PID" "$SERVER_PID" "$CAPTURE_PID"; do
        if [ -n "$pid" ]; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    rm -f "$TRACE" "$REPORT"
    cleanup_topology
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
configure_routed_topology

# [Implementation 6-3] Deterministic SYN loss and recovery
# 캡처를 먼저 시작한 뒤 손실을 적용해야 최초 SYN과 반복 SYN을 모두 남길 수 있습니다.
ip netns exec "$SERVER" python3 "$SCRIPT_DIR/tcp_probe.py" server \
    --bind 10.201.2.2 --port 9000 &
SERVER_PID=$!
sleep 0.2

ip netns exec "$CLIENT" tcpdump -i c0 -nn -tt -l -c 2 \
    'tcp dst port 9000 and (tcp[tcpflags] & tcp-syn != 0)' \
    >"$TRACE" 2>/dev/null &
CAPTURE_PID=$!
sleep 0.2

ip netns exec "$ROUTER" tc qdisc add dev r1 root netem loss 100%
ip netns exec "$CLIENT" python3 "$SCRIPT_DIR/tcp_probe.py" client \
    --target 10.201.2.2 --port 9000 --timeout 10 &
CLIENT_PID=$!

count=0
attempt=0
while [ "$count" -lt 2 ] && [ "$attempt" -lt 60 ]; do
    sleep 0.1
    count=$(grep -c 'Flags \[S\]' "$TRACE" 2>/dev/null || true)
    attempt=$((attempt + 1))
done
if [ "$count" -lt 2 ]; then
    printf '%s\n' "The initial SYN and a repeated SYN were not observed in time." >&2
    exit 1
fi

ip netns exec "$ROUTER" tc qdisc del dev r1 root

wait "$CLIENT_PID"
CLIENT_PID=
wait "$SERVER_PID"
SERVER_PID=
wait "$CAPTURE_PID"
CAPTURE_PID=

python3 "$VERIFIER" "$TRACE" >"$REPORT"
printf '%s\n' "[loss] captured SYN packets"
cat "$TRACE"
printf '%s\n' "[loss] retransmission report"
cat "$REPORT"
printf '%s\n' "[loss] The connection recovered after deterministic loss was removed."
