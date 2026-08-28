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

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    parse_arguments "$@"
    assert_runtime_boundary
fi
