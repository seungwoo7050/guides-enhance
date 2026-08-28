#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON=${PYTHON:-python3}

# [Implementation 3]
# Shared local and CI check command
# `__pycache__`를 남기지 않으면서 모든 Python 파일의 문법을
# 먼저 검사합니다.
"$PYTHON" - "$ROOT" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
for path in sorted((root / "src").glob("*.py")) + sorted((root / "tests").glob("*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$ROOT/src" \
    "$PYTHON" -m unittest discover \
    --start-directory "$ROOT/tests" \
    --pattern 'test_*.py' \
    --verbose
