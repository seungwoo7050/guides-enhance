#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON=${PYTHON:-python3}

# [Implementation 3] Shared application verification command
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$ROOT/src" \
    "$PYTHON" -m unittest discover --start-directory "$ROOT/tests" --pattern 'test_*.py' --verbose
