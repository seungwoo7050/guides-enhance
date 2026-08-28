#!/bin/sh
set -eu
export LC_ALL=C

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

"$SCRIPT_DIR/preflight.sh" nat

# [Implementation 5-1] NAT-run process and file tracking
# 이 실행에서 시작한 서버와 임시 파일만 정리해 다른 프로세스나 파일에 영향을 주지 않습니다.
PEER_FILE=$(mktemp)
READY_FILE=$(mktemp)
rm -f "$READY_FILE"
SERVER_PID=
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -f "$PEER_FILE" "$READY_FILE"
    cleanup_topology
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
configure_nat_topology

# [Implementation 5-2] SNAT and reverse-path verification
# 서버가 본 출발지와 클라이언트가 받은 응답을 함께 확인해야 양방향 변환을 검증할 수 있습니다.
ip netns exec "$ROUTER" iptables -t nat -A POSTROUTING \
    -s 10.202.1.0/24 -o r1 -j SNAT --to-source 198.18.0.1

ip netns exec "$SERVER" python3 "$SCRIPT_DIR/udp_probe.py" server \
    --bind 198.18.0.2 --port 9000 --output "$PEER_FILE" --ready "$READY_FILE" &
SERVER_PID=$!

attempt=0
while [ ! -s "$READY_FILE" ]; do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        wait "$SERVER_PID"
        printf '%s\n' "The UDP server exited before becoming ready." >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 100 ]; then
        printf '%s\n' "The UDP server did not bind within five seconds." >&2
        exit 1
    fi
    sleep 0.05
done

ip netns exec "$CLIENT" python3 "$SCRIPT_DIR/udp_probe.py" client \
    --target 198.18.0.2 --port 9000
wait "$SERVER_PID"
SERVER_PID=

printf '%s\n' "[nat] request source observed by the server"
cat "$PEER_FILE"
case "$(cat "$PEER_FILE")" in
    198.18.0.1:*) ;;
    *)
        printf '%s\n' "The server did not observe the translated source address." >&2
        exit 1
        ;;
esac
printf '%s\n' "[nat] SNAT and reverse translation verified."
