#!/bin/sh
set -eu
export LC_ALL=C

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

"$SCRIPT_DIR/preflight.sh" routing
trap cleanup_topology EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

# [Implementation 4] Routing, TTL, and route recovery checks
configure_routed_topology

printf '%s\n' "[routing] client route table"
ip -n "$CLIENT" route show
printf '%s\n' "[routing] router route table"
ip -n "$ROUTER" route show

ip netns exec "$CLIENT" ping -c 2 -W 2 10.201.2.2 >/dev/null
printf '%s\n' "[routing] Forwarding between the two subnets succeeded."

if ip netns exec "$CLIENT" ping -c 1 -W 2 -t 1 10.201.2.2 >/dev/null 2>&1; then
    printf '%s\n' "A packet with TTL 1 unexpectedly reached the destination." >&2
    exit 1
fi
ip netns exec "$CLIENT" ping -c 1 -W 2 -t 2 10.201.2.2 >/dev/null
printf '%s\n' "[routing] TTL 1 expired at the router and TTL 2 reached the destination."

ip -n "$CLIENT" route del default
if ip netns exec "$CLIENT" ping -c 1 -W 1 10.201.2.2 >/dev/null 2>&1; then
    printf '%s\n' "The remote subnet remained reachable after removing the default route." >&2
    exit 1
fi
ip -n "$CLIENT" route add default via 10.201.1.1
ip netns exec "$CLIENT" ping -c 1 -W 2 10.201.2.2 >/dev/null
printf '%s\n' "[routing] Route failure and recovery verified."
