#!/bin/sh
set -eu

# [Implementation 12-2] Check source and configuration syntax without Docker
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)

# 시작 전에 셸 문법 오류를 찾아, 컨테이너가 즉시 종료되는 구현을 검출합니다.
for script in \
    "$base_dir/prepare-secrets.sh" \
    "$base_dir/backup.sh" \
    "$base_dir/restore.sh" \
    "$base_dir/db/docker-entrypoint.sh" \
    "$base_dir/app/docker-entrypoint.sh" \
    "$base_dir/gateway/docker-entrypoint.sh" \
    "$base_dir/tests/integration.sh" \
    "$base_dir/tests/fault-injection.sh"
do
    sh -n "$script"
done

# PHP 구문 오류는 FPM을 띄우기 전에 확인합니다.
php -l "$base_dir/app/bin/bootstrap.php" >/dev/null
php -l "$base_dir/app/public/index.php" >/dev/null

# Compose와 override 파일의 최상위 값이 매핑인지 확인합니다.
python - "$base_dir/compose.yaml" "$base_dir/tests/scenarios" <<'PY'
import sys
from pathlib import Path

import yaml

paths = [Path(sys.argv[1]), *sorted(Path(sys.argv[2]).glob("*.yaml"))]
for path in paths:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"YAML 문서의 최상위 값이 mapping이 아닙니다: {path}")
PY

printf '%s\n' '통과: shell, PHP와 YAML 정적 검사'
