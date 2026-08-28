#!/bin/sh
set -eu

# [Implementation 10-1] Restore the selected SQL backup into appdb
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
backup=${1:-$base_dir/backups/appdb.sql}

[ -r "$backup" ] || {
    echo "backup 파일을 읽을 수 없습니다: $backup" >&2
    exit 1
}

password=$(cat "$base_dir/secrets/db_password.txt")
docker compose -f "$base_dir/compose.yaml" exec -T db \
    mariadb -uappuser -p"$password" appdb < "$backup"
