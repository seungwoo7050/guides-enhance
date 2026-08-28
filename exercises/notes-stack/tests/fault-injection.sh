#!/bin/sh
set -eu

# [Implementation 12-1] Inject one fault at a time and check its expected symptom
scenario=${1:-all}
case "$scenario" in
    all|wrong-db-host|wrong-db-password|missing-secret|wrong-fcgi-port|broken-healthcheck|data-loss) ;;
    *)
        echo "사용법: $0 [all|wrong-db-host|wrong-db-password|missing-secret|wrong-fcgi-port|broken-healthcheck|data-loss]" >&2
        exit 2
        ;;
esac

base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)

run_one() {
    name=$1
    work=$(mktemp -d "${TMPDIR:-/tmp}/notes-stack-fault.XXXXXX")
    cp -R "$base_dir/." "$work"

    project="notes-stack-fault-${name}-$$"
    export COMPOSE_PROJECT_NAME="$project"
    export TLS_PORT=0

    if [ "$name" = data-loss ]; then
        compose() {
            docker compose -f "$work/compose.yaml" "$@"
        }
    else
        compose() {
            docker compose \
                -f "$work/compose.yaml" \
                -f "$work/tests/scenarios/$name.yaml" \
                "$@"
        }
    fi

    cleanup() {
        compose down --rmi local -v --remove-orphans >/dev/null 2>&1 || true
        rm -rf "$work"
    }
    trap cleanup EXIT HUP INT TERM

    "$work/prepare-secrets.sh"
    printf '%s\n' intentionally-wrong-password > "$work/secrets/wrong_db_password.txt"
    chmod 0600 "$work/secrets/wrong_db_password.txt"

    case "$name" in
        wrong-db-host|wrong-db-password|missing-secret)
            # DB 설정은 그대로 둔 채 `app` 입력 하나만 바꿉니다. `app`이 제한 시간 안에
            # 종료하지 않으면 잘못된 설정을 무한히 기다리는 구현입니다.
            compose up -d --build >/dev/null 2>&1 || true
            attempt=0
            state=
            while [ "$attempt" -lt 80 ]; do
                attempt=$((attempt + 1))
                app_id=$(compose ps -a -q app 2>/dev/null || true)
                [ -n "$app_id" ] || {
                    sleep 0.25
                    continue
                }
                state=$(docker inspect "$app_id" \
                    --format '{{.State.Status}}' 2>/dev/null || true)
                [ "$state" = exited ] && break
                sleep 0.25
            done

            [ "$state" = exited ] || {
                compose logs app >&2
                echo "잘못된 입력에도 app이 제한 시간 안에 종료되지 않았습니다." >&2
                exit 1
            }

            logs=$(compose logs --no-color app 2>&1 || true)
            case "$name" in
                wrong-db-host|wrong-db-password)
                    printf '%s' "$logs" | grep -Eq \
                        '데이터베이스가 [0-9]+회 안에 준비되지 않았습니다' || {
                        printf '%s\n' "$logs" >&2
                        echo "DB 연결 실패를 나타내는 제한된 재시도 메시지가 없습니다." >&2
                        exit 1
                    }
                    ;;
                missing-secret)
                    printf '%s' "$logs" | grep -q \
                        'DB_PASSWORD_FILE을 읽을 수 없습니다' || {
                        printf '%s\n' "$logs" >&2
                        echo "누락된 비밀값 파일을 시작 직후 거부하지 않았습니다." >&2
                        exit 1
                    }
                    ;;
            esac
            ;;

        wrong-fcgi-port)
            # Nginx 자체는 정상이고 `app` 업스트림만 잘못된 경우 502가 나와야 합니다.
            compose up -d --build >/dev/null
            attempt=0
            code=
            while [ "$attempt" -lt 160 ]; do
                attempt=$((attempt + 1))
                binding=$(compose port gateway 443 2>/dev/null || true)
                if [ -n "$binding" ]; then
                    port=${binding##*:}
                    code=$(curl -ksS \
                        -o /dev/null \
                        -w '%{http_code}' \
                        "https://127.0.0.1:$port/health" || true)
                    [ "$code" = 502 ] && break
                fi
                sleep 0.25
            done

            [ "$code" = 502 ] || {
                compose logs >&2
                echo "잘못된 FastCGI port에서 502를 확인하지 못했습니다." >&2
                exit 1
            }
            ;;

        broken-healthcheck)
            # 사용자 요청은 성공하지만 검사 명령만 실패하는 상태를 구분합니다.
            compose up -d --build >/dev/null || true
            attempt=0
            code=
            health=
            while [ "$attempt" -lt 160 ]; do
                attempt=$((attempt + 1))
                binding=$(compose port gateway 443 2>/dev/null || true)
                gateway_id=$(compose ps -q gateway 2>/dev/null || true)
                if [ -n "$binding" ] && [ -n "$gateway_id" ]; then
                    port=${binding##*:}
                    code=$(curl -ksS \
                        -o /dev/null \
                        -w '%{http_code}' \
                        "https://127.0.0.1:$port/health" || true)
                    health=$(docker inspect "$gateway_id" \
                        --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' \
                        2>/dev/null || true)
                    [ "$code" = 200 ] && [ "$health" = unhealthy ] && break
                fi
                sleep 0.25
            done

            [ "$code" = 200 ] && [ "$health" = unhealthy ] || {
                compose logs >&2
                echo "정상 요청과 고장 난 healthcheck를 동시에 재현하지 못했습니다." >&2
                exit 1
            }
            ;;

        data-loss)
            # 무상태 컨테이너 교체가 아니라 볼륨 삭제만 사용자 데이터를 없애야 합니다.
            compose up -d --build >/dev/null
            attempt=0
            port=
            while [ "$attempt" -lt 160 ]; do
                attempt=$((attempt + 1))
                binding=$(compose port gateway 443 2>/dev/null || true)
                if [ -n "$binding" ]; then
                    port=${binding##*:}
                    curl -kfsS \
                        "https://127.0.0.1:$port/health" >/dev/null 2>&1 && break
                fi
                sleep 0.25
            done
            [ -n "$port" ] || {
                compose logs >&2
                echo "데이터 손실 시나리오의 정상 stack이 준비되지 않았습니다." >&2
                exit 1
            }

            curl -kfsS \
                -H 'Content-Type: application/json' \
                -d '{"body":"deleted with volume"}' \
                "https://127.0.0.1:$port/api/notes" >/dev/null

            compose down -v --remove-orphans >/dev/null
            compose up -d >/dev/null

            attempt=0
            notes=
            while [ "$attempt" -lt 160 ]; do
                attempt=$((attempt + 1))
                binding=$(compose port gateway 443 2>/dev/null || true)
                if [ -n "$binding" ]; then
                    port=${binding##*:}
                    notes=$(curl -kfsS \
                        "https://127.0.0.1:$port/api/notes" 2>/dev/null || true)
                    printf '%s' "$notes" | grep -q 'seed note' && break
                fi
                sleep 0.25
            done

            printf '%s' "$notes" | grep -q 'seed note' || {
                compose logs >&2
                echo "새 volume의 최초 데이터가 준비되지 않았습니다." >&2
                exit 1
            }
            if printf '%s' "$notes" | grep -q 'deleted with volume'; then
                echo "volume을 삭제했는데 기존 사용자 데이터가 남아 있습니다." >&2
                exit 1
            fi
            ;;
    esac

    trap - EXIT HUP INT TERM
    cleanup
    printf '통과: %s\n' "$name"
}

if [ "$scenario" = all ]; then
    for item in \
        wrong-db-host \
        wrong-db-password \
        missing-secret \
        wrong-fcgi-port \
        broken-healthcheck \
        data-loss
    do
        run_one "$item"
    done
else
    run_one "$scenario"
fi
