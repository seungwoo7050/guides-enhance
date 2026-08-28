#!/bin/sh
set -eu

# [Implementation 2] Validate secret sources and SQL identifiers
file_env() {
    var=$1
    file_var="${var}_FILE"
    default_value=${2:-}

    # eval에는 이 파일에서 직접 지정한 변수 이름만 전달합니다.
    # 외부 입력을 넣으면 임의의 셸 코드가 실행될 수 있습니다.
    eval "value=\${$var:-}"
    eval "file_path=\${$file_var:-}"

    if [ -n "$value" ] && [ -n "$file_path" ]; then
        echo "$var와 $file_var는 함께 지정할 수 없습니다." >&2
        exit 1
    fi

    if [ -n "$file_path" ]; then
        [ -r "$file_path" ] || {
            echo "$file_var 파일을 읽을 수 없습니다." >&2
            exit 1
        }
        value=$(cat "$file_path")
    elif [ -z "$value" ]; then
        value=$default_value
    fi

    export "$var=$value"
    unset "$file_var"
}

require_identifier() {
    label=$1
    value=$2

    case "$value" in
        ''|*[!A-Za-z0-9_]*)
            echo "$label에는 영문자, 숫자와 밑줄만 사용할 수 있습니다." >&2
            exit 1
            ;;
    esac
}

sql_escape() {
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e "s/'/''/g"
}

file_env MARIADB_ROOT_PASSWORD
file_env MARIADB_PASSWORD

: "${MARIADB_ROOT_PASSWORD:?MARIADB_ROOT_PASSWORD가 필요합니다.}"
: "${MARIADB_DATABASE:?MARIADB_DATABASE가 필요합니다.}"
: "${MARIADB_USER:?MARIADB_USER가 필요합니다.}"
: "${MARIADB_PASSWORD:?MARIADB_PASSWORD가 필요합니다.}"

require_identifier MARIADB_DATABASE "$MARIADB_DATABASE"
require_identifier MARIADB_USER "$MARIADB_USER"

datadir=/var/lib/mysql
socket=/run/mysqld/mysqld.sock
install -d -m 0755 -o mysql -g mysql /run/mysqld "$datadir"

# [Implementation 2-1] Initialize an empty MariaDB data directory
if [ ! -d "$datadir/mysql" ]; then
    echo "MariaDB data directory를 초기화합니다." >&2
    mariadb-install-db \
        --user=mysql \
        --datadir="$datadir" \
        --skip-test-db \
        --auth-root-authentication-method=socket >/dev/null

    # [Implementation 2-2] Start a socket-only bootstrap server and wait for it
    # 계정과 비밀번호를 만들기 전에는 TCP 연결을 받지 않습니다.
    mariadbd \
        --user=mysql \
        --datadir="$datadir" \
        --skip-networking \
        --socket="$socket" &
    temp_pid=$!

    # 초기화가 중단돼도 임시 서버가 데이터 디렉터리를 계속 사용하지 않게 합니다.
    cleanup_temp() {
        kill -TERM "$temp_pid" 2>/dev/null || true
        wait "$temp_pid" 2>/dev/null || true
    }
    trap cleanup_temp EXIT
    trap 'exit 129' HUP
    trap 'exit 130' INT
    trap 'exit 143' TERM

    ready=0
    counter=0
    while [ "$counter" -lt 60 ]; do
        if mariadb-admin \
            --protocol=socket \
            --socket="$socket" \
            ping --silent >/dev/null 2>&1
        then
            ready=1
            break
        fi
        sleep 1
        counter=$((counter + 1))
    done

    [ "$ready" -eq 1 ] || {
        echo "초기화용 MariaDB가 제한 시간 안에 준비되지 않았습니다." >&2
        exit 1
    }

    root_password=$(sql_escape "$MARIADB_ROOT_PASSWORD")
    app_password=$(sql_escape "$MARIADB_PASSWORD")

    # [Implementation 2-3] Create accounts, stop bootstrap server, and exec the final server
    mariadb --protocol=socket --socket="$socket" -uroot <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${root_password}';
DROP DATABASE IF EXISTS test;
CREATE DATABASE IF NOT EXISTS \`${MARIADB_DATABASE}\`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MARIADB_USER}'@'%' IDENTIFIED BY '${app_password}';
ALTER USER '${MARIADB_USER}'@'%' IDENTIFIED BY '${app_password}';
GRANT ALL PRIVILEGES ON \`${MARIADB_DATABASE}\`.* TO '${MARIADB_USER}'@'%';
FLUSH PRIVILEGES;
SQL

    mariadb-admin \
        --protocol=socket \
        --socket="$socket" \
        -uroot \
        -p"$MARIADB_ROOT_PASSWORD" \
        shutdown
    wait "$temp_pid"
    trap - EXIT HUP INT TERM
    echo "MariaDB 초기화를 마쳤습니다." >&2
fi

exec "$@"
