#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
FINAL_LAB_DIR="$PROJECT_DIR/lab"
LAB_DIR="$FINAL_LAB_DIR"
REMOTES_DIR="$LAB_DIR/remotes"
HOOKS_DIR="$LAB_DIR/.empty-hooks"
LOCK_DIR="$PROJECT_DIR/.lab.lock"
MODE=create
TARGET=all
TMP_DIR=''
STAGING_DIR=''
LOCK_HELD=0
FINAL_EXISTED=0
FINAL_IDENTITY=''

usage() {
    printf '%s\n' 'Usage: git-lab.sh [--reset] [sample|team|recovery|all]' \
        'Validate the selected local lab target and runtime boundary.'
}

# [Implementation 1]
# CLI argument parsing and topology selection
parse_arguments() {
    case "$#" in
        0)
            ;;
        1)
            case "$1" in
                sample|team|recovery|all)
                    TARGET=$1
                    ;;
                --reset)
                    MODE=reset
                    TARGET=all
                    ;;
                -h|--help)
                    usage
                    exit 0
                    ;;
                *)
                    printf 'Unknown option: %s\n' "$1" >&2
                    usage >&2
                    exit 2
                    ;;
            esac
            ;;
        2)
            if [[ "$1" != --reset ]]; then
                printf 'Unknown option: %s\n' "$1" >&2
                usage >&2
                exit 2
            fi
            MODE=reset
            case "$2" in
                sample|team|recovery|all)
                    TARGET=$2
                    ;;
                *)
                    printf 'Unknown reset target: %s\n' "$2" >&2
                    usage >&2
                    exit 2
                    ;;
            esac
            ;;
        *)
            usage >&2
            exit 2
            ;;
    esac
}

# [Implementation 2]
# Runtime prerequisite and lab path validation
assert_runtime_boundary() {
    local command_name

    for command_name in git python3; do
        if ! command -v "$command_name" >/dev/null 2>&1; then
            printf 'Required command was not found in PATH: %s\n' "$command_name" >&2
            exit 1
        fi
    done

    if [[ -L "$FINAL_LAB_DIR" ]]; then
        printf 'Refusing to use a symbolic-link lab directory: %s\n' "$FINAL_LAB_DIR" >&2
        exit 1
    fi
    if [[ -e "$FINAL_LAB_DIR" && ! -d "$FINAL_LAB_DIR" ]]; then
        printf 'Lab path exists but is not a directory: %s\n' "$FINAL_LAB_DIR" >&2
        exit 1
    fi
}

target_exists() {
    case "$1" in
        sample)
            [[ -e "$FINAL_LAB_DIR/sample-app" ||
               -e "$FINAL_LAB_DIR/remotes/sample-app.git" ]]
            ;;
        team)
            [[ -e "$FINAL_LAB_DIR/team-app-dev-a" ||
               -e "$FINAL_LAB_DIR/team-app-dev-b" ||
               -e "$FINAL_LAB_DIR/team-app-maintainer" ||
               -e "$FINAL_LAB_DIR/remotes/team-app.git" ]]
            ;;
        recovery)
            [[ -e "$FINAL_LAB_DIR/recovery-lab" ]]
            ;;
        all)
            [[ -e "$FINAL_LAB_DIR" ]]
            ;;
    esac
}

safe_remove() {
    local path=$1

    # 계산한 경로가 잘못되더라도 `lab/` 밖을 지우지 않도록
    # 삭제 대상을 고정합니다.
    case "$path" in
        "$LAB_DIR"|\
        "$LAB_DIR/sample-app"|\
        "$LAB_DIR/team-app-dev-a"|\
        "$LAB_DIR/team-app-dev-b"|\
        "$LAB_DIR/team-app-maintainer"|\
        "$LAB_DIR/recovery-lab"|\
        "$REMOTES_DIR/sample-app.git"|\
        "$REMOTES_DIR/team-app.git")
            rm -rf -- "$path"
            ;;
        *)
            printf 'Refusing to remove an unexpected path: %s\n' "$path" >&2
            exit 1
            ;;
    esac
}

# [Implementation 3]
# Lock, temporary lab copy, and cleanup
cleanup() {
    local status=$?

    trap - EXIT HUP INT TERM
    if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
        rm -rf -- "$TMP_DIR"
    fi
    if [[ -n "$STAGING_DIR" && -d "$STAGING_DIR" ]]; then
        rm -rf -- "$STAGING_DIR"
    fi
    if (( LOCK_HELD == 1 )); then
        rmdir -- "$LOCK_DIR" 2>/dev/null || true
    fi
    exit "$status"
}

acquire_lock() {
    if ! mkdir -- "$LOCK_DIR" 2>/dev/null; then
        printf '%s\n' 'Another lab transaction is active, or a stale lock exists.' >&2
        exit 1
    fi
    LOCK_HELD=1
}

capture_directory_identity() {
    python3 - "$1" <<'PY'
import os
import sys

metadata = os.lstat(sys.argv[1])
print(f"{metadata.st_dev}:{metadata.st_ino}")
PY
}

begin_staged_transaction() {
    STAGING_DIR=$(mktemp -d "$PROJECT_DIR/.lab.tmp.XXXXXX")

    # 기존 `lab/`은 직접 수정하지 않습니다.
    # 복사본에서 선택한 구성만 다시 만듭니다.
    if [[ -d "$FINAL_LAB_DIR" ]]; then
        FINAL_EXISTED=1
        FINAL_IDENTITY=$(capture_directory_identity "$FINAL_LAB_DIR")
        cp -R "$FINAL_LAB_DIR/." "$STAGING_DIR/"
    fi

    LAB_DIR="$STAGING_DIR"
    REMOTES_DIR="$LAB_DIR/remotes"
    HOOKS_DIR="$LAB_DIR/.empty-hooks"

    if [[ "$MODE" == reset ]]; then
        case "$TARGET" in
            sample)
                safe_remove "$LAB_DIR/sample-app"
                safe_remove "$REMOTES_DIR/sample-app.git"
                ;;
            team)
                safe_remove "$LAB_DIR/team-app-dev-a"
                safe_remove "$LAB_DIR/team-app-dev-b"
                safe_remove "$LAB_DIR/team-app-maintainer"
                safe_remove "$REMOTES_DIR/team-app.git"
                ;;
            recovery)
                safe_remove "$LAB_DIR/recovery-lab"
                ;;
            all)
                safe_remove "$LAB_DIR"
                mkdir -- "$LAB_DIR"
                ;;
        esac
    fi

    mkdir -p "$REMOTES_DIR" "$HOOKS_DIR"
    TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/local-git-lab.XXXXXX")
    mkdir -p "$TMP_DIR/empty-template"
}

# [Implementation 4]
# Per-repository Git configuration
configure_repository() {
    local repo=$1
    local name=$2
    local email=$3

    # 사용자 전역 설정이 커밋 작성자와 서명에 영향을 주거나
    # Git hook을 실행하지 않도록 필요한 값을 각 저장소에 고정합니다.
    git -C "$repo" config user.name "$name"
    git -C "$repo" config user.email "$email"
    git -C "$repo" config commit.gpgSign false
    git -C "$repo" config tag.gpgSign false
    git -C "$repo" config core.autocrlf false
    git -C "$repo" config protocol.file.allow always
    git -C "$repo" config core.hooksPath "$HOOKS_DIR"
}

init_repository() {
    local repo=$1

    git -c init.defaultBranch=main \
        init --template="$TMP_DIR/empty-template" "$repo" >/dev/null
}

init_bare_remote() {
    local remote=$1

    git -c init.defaultBranch=main \
        init --bare --template="$TMP_DIR/empty-template" "$remote" >/dev/null
    git -C "$remote" symbolic-ref HEAD refs/heads/main
}

clone_local_remote() {
    local remote=$1
    local destination=$2

    git -c core.autocrlf=false -c protocol.file.allow=always \
        clone --quiet --template="$TMP_DIR/empty-template" \
        "$remote" "$destination"
}

finalize_clone_paths() {
    local repo=$1
    local final_remote=$2

    git -C "$repo" remote set-url origin "$final_remote"
    git -C "$repo" config core.hooksPath "$FINAL_LAB_DIR/.empty-hooks"
}

finalize_local_paths() {
    local repo=$1

    git -C "$repo" config core.hooksPath "$FINAL_LAB_DIR/.empty-hooks"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    parse_arguments "$@"
    assert_runtime_boundary
fi
