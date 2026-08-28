#!/bin/sh
set -eu

# [Implementation 5] Copy the injected secret to a worker-readable tmpfs file
: "${DB_HOST:?DB_HOST가 필요합니다.}"
: "${DB_NAME:?DB_NAME이 필요합니다.}"
: "${DB_USER:?DB_USER가 필요합니다.}"
: "${DB_PASSWORD_FILE:?DB_PASSWORD_FILE이 필요합니다.}"

[ -r "$DB_PASSWORD_FILE" ] || {
    echo "DB_PASSWORD_FILE을 읽을 수 없습니다: $DB_PASSWORD_FILE" >&2
    exit 1
}

# Compose가 주입한 원본은 root 사용자만 읽을 수 있습니다. tmpfs 복사본은 PHP-FPM
# 워커가 읽을 수 있지만 덮어쓰지는 못하게 합니다.
runtime_secret_dir=/run/app-secrets
runtime_password_file="$runtime_secret_dir/db_password"
install -d -m 0750 -o root -g www-data "$runtime_secret_dir"
install -m 0440 -o root -g www-data "$DB_PASSWORD_FILE" "$runtime_password_file"
export DB_PASSWORD_FILE="$runtime_password_file"

# [Implementation 5-1] Run bootstrap before replacing the shell with PHP-FPM
php /opt/app/bootstrap.php
exec "$@"
