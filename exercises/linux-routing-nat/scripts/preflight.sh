#!/bin/sh
set -eu

MODE=${1:-routing}
SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

# [Implementation 2] Required privilege and command checks
# 실험을 시작하기 전에 필요한 권한과 명령을 모두 확인해 부분 생성 상태를 피합니다.
require_root
for command in ip ping sysctl python3 grep; do
    require_command "$command"
done
case "$MODE" in
    routing) ;;
    nat) require_command iptables ;;
    loss)
        require_command tc
        require_command tcpdump
        ;;
    all)
        require_command iptables
        require_command tc
        require_command tcpdump
        ;;
    *)
        printf '%s\n' "Usage: $0 [routing|nat|loss|all]" >&2
        exit 2
        ;;
esac

# [Implementation 2-1] Network namespace capability probe
# 명령 존재 여부만 보지 않고 네임스페이스 생성과 내부 명령 실행까지 확인합니다.
assert_names_available
probe="cn-probe-$RUN_SUFFIX"
probe_owned=0
cleanup_probe() {
    [ "$probe_owned" -eq 0 ] || ip netns del "$probe" 2>/dev/null || true
}
trap cleanup_probe EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
ip netns add "$probe"
probe_owned=1
ip netns exec "$probe" true
printf '%s\n' "Linux network namespace capability verified: $MODE"
