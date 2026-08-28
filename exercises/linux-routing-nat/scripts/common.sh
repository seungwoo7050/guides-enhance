#!/bin/sh

# [Implementation 1] Run-scoped namespace and link names
# 실행 ID를 짧은 숫자로 바꿔 이름 충돌 가능성을 낮추면서 Linux 이름 길이 제한을 지킵니다.
RUN_SEED=${NETWORK_LAB_RUN_ID:-$$}
RUN_SUFFIX=$(printf '%s' "$RUN_SEED" | cksum | awk '{print $1}')
CLIENT="cn-client-$RUN_SUFFIX"
ROUTER="cn-router-$RUN_SUFFIX"
SERVER="cn-server-$RUN_SUFFIX"
CLIENT_LINK="c${RUN_SUFFIX}a"
ROUTER_LEFT_LINK="r${RUN_SUFFIX}a"
ROUTER_RIGHT_LINK="r${RUN_SUFFIX}b"
SERVER_LINK="s${RUN_SUFFIX}a"
OWN_CLIENT=0
OWN_ROUTER=0
OWN_SERVER=0
OWN_LEFT_LINK=0
OWN_RIGHT_LINK=0

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        printf '%s\n' "This project requires root privileges to create network namespaces." >&2
        exit 1
    fi
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        printf '%s\n' "Required command not found: $1" >&2
        exit 1
    fi
}

namespace_exists() {
    ip netns list | grep -Eq "^$1([[:space:]]|$)"
}

# [Implementation 1-1] Existing-name collision check
# 같은 이름이 이미 있으면 중단합니다. 이 프로젝트가 만들지 않은 자원을 지우지 않습니다.
assert_names_available() {
    for namespace in "$CLIENT" "$ROUTER" "$SERVER"; do
        if namespace_exists "$namespace"; then
            printf '%s\n' \
                "Refusing to overwrite an existing namespace: $namespace" \
                "Inspect and remove stale resources manually." >&2
            exit 1
        fi
    done

    for interface in "$CLIENT_LINK" "$ROUTER_LEFT_LINK" "$ROUTER_RIGHT_LINK" "$SERVER_LINK"; do
        if ip link show "$interface" >/dev/null 2>&1; then
            printf '%s\n' \
                "Refusing to overwrite an existing interface: $interface" \
                "Inspect and remove stale resources manually." >&2
            exit 1
        fi
    done
}

# [Implementation 1-2] Cleanup of created namespaces and links
# 생성에 성공한 자원만 표시해 두었다가 종료 시 제거합니다.
cleanup_topology() {
    [ "$OWN_CLIENT" -eq 0 ] || ip netns del "$CLIENT" 2>/dev/null || true
    [ "$OWN_ROUTER" -eq 0 ] || ip netns del "$ROUTER" 2>/dev/null || true
    [ "$OWN_SERVER" -eq 0 ] || ip netns del "$SERVER" 2>/dev/null || true
    [ "$OWN_LEFT_LINK" -eq 0 ] || ip link del "$CLIENT_LINK" 2>/dev/null || true
    [ "$OWN_RIGHT_LINK" -eq 0 ] || ip link del "$ROUTER_RIGHT_LINK" 2>/dev/null || true
}
