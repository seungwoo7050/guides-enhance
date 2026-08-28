#!/bin/sh
set -eu

# [Implementation 12] Verify restart, recreation, backup, and restore end to end
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
project="notes-stack-test-$$"
index_log="${TMPDIR:-/tmp}/notes-stack-index-demo.$$.log"
export COMPOSE_PROJECT_NAME="$project"
export TLS_PORT=0

compose() {
    docker compose -f "$base_dir/compose.yaml" "$@"
}

cleanup() {
    compose down --rmi local -v --remove-orphans >/dev/null 2>&1 || true
    rm -f "$index_log"
}
trap cleanup EXIT HUP INT TERM

"$base_dir/prepare-secrets.sh"
compose config --quiet
compose up -d --build

wait_https() {
    attempt=0
    while [ "$attempt" -lt 180 ]; do
        attempt=$((attempt + 1))
        binding=$(compose port gateway 443 2>/dev/null || true)
        if [ -n "$binding" ]; then
            port=${binding##*:}
            if curl -kfsS --connect-timeout 1 --max-time 2 \
                "https://127.0.0.1:$port/health" >/dev/null 2>&1
            then
                return 0
            fi
        fi
        sleep 0.5
    done

    echo "gateway와 application이 제한 시간 안에 준비되지 않았습니다." >&2
    compose ps >&2 || true
    compose logs >&2 || true
    return 1
}
wait_https

compose exec -T app php -l /var/www/html/index.php >/dev/null
compose exec -T app php -l /opt/app/bootstrap.php >/dev/null
compose exec -T gateway nginx -t >/dev/null

password=$(cat "$base_dir/secrets/db_password.txt")
db() {
    compose exec -T db mariadb -uappuser -p"$password" appdb "$@"
}

# PHP-FPM 워커가 비밀값을 읽을 수는 있지만 수정할 수 없는지 확인합니다.
permissions=$(compose exec -T app stat -c '%U:%G:%a' /run/app-secrets/db_password)
[ "$permissions" = root:www-data:440 ] || {
    echo "runtime secret 권한이 예상과 다릅니다: $permissions" >&2
    exit 1
}
if compose exec -T --user www-data app sh -c 'test -w "$DB_PASSWORD_FILE"'; then
    echo "PHP-FPM worker가 runtime secret을 수정할 수 있습니다." >&2
    exit 1
fi

# 최초 시작에서 초기 데이터가 정확히 한 번만 만들어져야 합니다.
seed_count=$(db --batch --skip-column-names \
    -e "SELECT COUNT(*) FROM notes WHERE body='seed note';")
[ "$seed_count" = 1 ] || {
    echo "최초 메모가 한 건이어야 하지만 $seed_count건입니다." >&2
    exit 1
}
curl -kfsS "https://127.0.0.1:$port/static.txt" | grep -q 'served directly by nginx'
curl -kfsS "https://127.0.0.1:$port/api/notes" | grep -q 'seed note'

# `app` 재시작으로 초기화가 다시 실행돼도 최초 메모가 중복되면 안 됩니다.
compose restart app >/dev/null
wait_https
seed_count=$(db --batch --skip-column-names \
    -e "SELECT COUNT(*) FROM notes WHERE body='seed note';")
[ "$seed_count" = 1 ] || {
    echo "app 재시작 뒤 최초 메모가 중복되었습니다." >&2
    exit 1
}

curl -kfsS \
    -H 'Content-Type: application/json' \
    -d '{"body":"persisted note"}' \
    "https://127.0.0.1:$port/api/notes" | grep -q 'persisted note'

# `app`과 `gateway`를 새 컨테이너로 바꿔도 DB 볼륨의 사용자 데이터는 남아야 합니다.
compose up -d --force-recreate app gateway >/dev/null
wait_https
persisted=$(db --batch --skip-column-names \
    -e "SELECT COUNT(*) FROM notes WHERE body='persisted note';")
[ "$persisted" = 1 ] || {
    echo "무상태 container 교체 뒤 사용자 데이터가 사라졌습니다." >&2
    exit 1
}

# 삭제한 테이블을 논리 백업으로 복원해 백업이 실제로 읽히는지 확인합니다.
backup_path=$("$base_dir/backup.sh")
db -e 'DROP TABLE notes;'
"$base_dir/restore.sh" "$backup_path"
restored=$(db --batch --skip-column-names \
    -e "SELECT COUNT(*) FROM notes WHERE body='persisted note';")
[ "$restored" = 1 ] || {
    echo "논리 backup에서 table을 복원하지 못했습니다." >&2
    exit 1
}

# 고정된 행으로 인덱스 적용 전후 `EXPLAIN`을 같은 조건에서 실행합니다.
db < "$base_dir/sql/index-demo.sql" >"$index_log"

# 내부 서비스 포트를 실수로 호스트에 공개한 구성을 검출합니다.
for service in app db; do
    id=$(compose ps -q "$service")
    ports=$(docker inspect "$id" --format '{{json .NetworkSettings.Ports}}')
    case "$ports" in
        *HostPort*)
            echo "$service 내부 port가 host에 공개되었습니다." >&2
            exit 1
            ;;
    esac
done

printf '%s\n' '통과: 시작, 재시작, container 교체, backup과 restore'
