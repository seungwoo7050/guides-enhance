#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

# [Implementation 7] Sequential experiment runner
"$SCRIPT_DIR/run-routing.sh"
"$SCRIPT_DIR/run-nat.sh"
"$SCRIPT_DIR/run-loss-retransmission.sh"
