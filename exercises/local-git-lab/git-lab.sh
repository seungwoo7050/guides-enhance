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

# [Implementation 5]
# Sample repository and bare remote generation
create_sample_topology() {
    local remote="$REMOTES_DIR/sample-app.git"
    local seed="$TMP_DIR/sample-app-seed"
    local clone="$LAB_DIR/sample-app"

    init_bare_remote "$remote"
    init_repository "$seed"
    configure_repository "$seed" 'Sample Maintainer' 'sample-maintainer@example.invalid'

    mkdir -p "$seed/src" "$seed/tests" "$seed/scripts"

    cat > "$seed/src/validate_title.sh" <<'SOURCE'
#!/usr/bin/env sh

is_valid_title() {
    [ "$#" -eq 1 ] || return 1

    title=$1
    length=${#title}

    [ "$length" -ge 3 ] && [ "$length" -le 60 ]
}
SOURCE

    cat > "$seed/tests/test_validate_title.sh" <<'TEST'
#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/src/validate_title.sh"

expect_valid() {
    is_valid_title "$1" || {
        printf 'Expected a valid title: %s\n' "$1" >&2
        exit 1
    }
}

expect_invalid() {
    if is_valid_title "$1"; then
        printf 'Expected an invalid title: %s\n' "$1" >&2
        exit 1
    fi
}

expect_valid 'Fix login redirect'
expect_invalid ''
expect_invalid 'ab'
expect_invalid '1234567890123456789012345678901234567890123456789012345678901'
printf '%s\n' 'title validation passed'
TEST

    cat > "$seed/scripts/test.sh" <<'SCRIPT'
#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
"$ROOT/tests/test_validate_title.sh"
SCRIPT

    chmod +x \
        "$seed/src/validate_title.sh" \
        "$seed/tests/test_validate_title.sh" \
        "$seed/scripts/test.sh"

    cat > "$seed/README.md" <<'README'
# Sample Task Application

이 저장소에는 3자 이상 60자 이하의 작업 제목만 허용하는
POSIX 셸 검증 도구가 포함되어 있습니다.

## 검증

```sh
./scripts/test.sh
```

## 의존성

외부 패키지는 필요하지 않습니다.
README

    cat > "$seed/.gitignore" <<'IGNORE'
build/
*.tmp
.env.local
.DS_Store
IGNORE

    git -C "$seed" add .
    git -C "$seed" commit -m 'feat: add title validation' >/dev/null
    git -C "$seed" remote add origin "$remote"
    git -C "$seed" push --quiet -u origin main

    clone_local_remote "$remote" "$clone"
    configure_repository "$clone" 'Sample Developer' 'sample-developer@example.invalid'
    finalize_clone_paths "$clone" "$FINAL_LAB_DIR/remotes/sample-app.git"
}

# [Implementation 6]
# Divergent team repository graph generation
create_team_topology() {
    local remote="$REMOTES_DIR/team-app.git"
    local seed="$TMP_DIR/team-app-seed"
    local developer_a="$LAB_DIR/team-app-dev-a"
    local developer_b="$LAB_DIR/team-app-dev-b"
    local maintainer="$LAB_DIR/team-app-maintainer"

    init_bare_remote "$remote"
    init_repository "$seed"
    configure_repository "$seed" 'Team Maintainer' 'team-maintainer@example.invalid'

    mkdir -p "$seed/config" "$seed/scripts"

    cat > "$seed/config/task-fields.yml" <<'CONFIG'
fields:
  - title
  - status
CONFIG

    cat > "$seed/scripts/check.sh" <<'SCRIPT'
#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FILE="$ROOT/config/task-fields.yml"

if ! grep -qx 'fields:' "$FILE"; then
    printf 'Missing fields root: %s\n' "$FILE" >&2
    exit 1
fi

if grep -Eq '^(<<<<<<<|=======|>>>>>>>)' "$FILE"; then
    printf 'Conflict marker found: %s\n' "$FILE" >&2
    exit 1
fi

for field in title status; do
    if ! grep -qx "  - $field" "$FILE"; then
        printf 'Missing required field: %s\n' "$field" >&2
        exit 1
    fi
done

duplicates=$(awk '/^  - / { count[$0]++; if (count[$0] == 2) print $0 }' "$FILE")
if [ -n "$duplicates" ]; then
    printf '%s\n' 'Duplicate fields found:' >&2
    printf '%s\n' "$duplicates" >&2
    exit 1
fi

printf '%s\n' 'team schema validation passed'
SCRIPT

    chmod +x "$seed/scripts/check.sh"

    cat > "$seed/README.md" <<'README'
# Team Task Schema

이 저장소에는 공유 작업 필드 파일과 다음 문제를 검사하는 스크립트가
포함되어 있습니다: 충돌 표시, 필수 필드 누락, 중복 필드.

## 검증

```sh
./scripts/check.sh
```
README

    cat > "$seed/.gitignore" <<'IGNORE'
*.tmp
.DS_Store
IGNORE

    git -C "$seed" add .
    git -C "$seed" commit -m 'chore: establish shared task schema' >/dev/null
    git -C "$seed" remote add origin "$remote"
    git -C "$seed" push --quiet -u origin main

    clone_local_remote "$remote" "$developer_a"
    clone_local_remote "$remote" "$developer_b"
    clone_local_remote "$remote" "$maintainer"

    configure_repository "$developer_a" 'Developer A' 'developer-a@example.invalid'
    configure_repository "$developer_b" 'Developer B' 'developer-b@example.invalid'
    configure_repository "$maintainer" 'Maintainer' 'maintainer@example.invalid'

    git -C "$developer_a" switch --quiet --no-track -c feature/add-priority origin/main
    cat > "$developer_a/config/task-fields.yml" <<'CONFIG'
fields:
  - title
  - status
  - priority
CONFIG
    "$developer_a/scripts/check.sh" >/dev/null
    git -C "$developer_a" add config/task-fields.yml
    git -C "$developer_a" commit -m 'feat: add priority field' >/dev/null
    git -C "$developer_a" push --quiet -u origin HEAD

    git -C "$developer_b" switch --quiet --no-track -c feature/add-assignee origin/main
    cat > "$developer_b/config/task-fields.yml" <<'CONFIG'
fields:
  - title
  - status
  - assignee
CONFIG
    "$developer_b/scripts/check.sh" >/dev/null
    git -C "$developer_b" add config/task-fields.yml
    git -C "$developer_b" commit -m 'feat: add assignee field' >/dev/null
    git -C "$developer_b" push --quiet -u origin HEAD

    git -C "$maintainer" fetch --quiet origin
    git -C "$maintainer" switch --quiet main
    git -C "$maintainer" merge --quiet --ff-only origin/main
    git -C "$maintainer" merge --no-ff origin/feature/add-priority \
        -m 'merge: integrate priority field' >/dev/null
    "$maintainer/scripts/check.sh" >/dev/null
    git -C "$maintainer" push --quiet origin HEAD:main

    git -C "$developer_a" fetch --quiet origin
    git -C "$developer_b" fetch --quiet origin

    finalize_clone_paths "$developer_a" "$FINAL_LAB_DIR/remotes/team-app.git"
    finalize_clone_paths "$developer_b" "$FINAL_LAB_DIR/remotes/team-app.git"
    finalize_clone_paths "$maintainer" "$FINAL_LAB_DIR/remotes/team-app.git"
}

# [Implementation 7]
# Recovery refs, revert, and stash generation
create_recovery_topology() {
    local repo="$LAB_DIR/recovery-lab"
    local reset_target
    local detached_target
    local tree_before

    init_repository "$repo"
    configure_repository "$repo" 'Recovery Operator' 'recovery-operator@example.invalid'

    cat > "$repo/README.md" <<'README'
# Recovery Reference Repository

이 저장소에는 reset 뒤 별도 브랜치로 보존한 커밋과
detached `HEAD`에서 만든 커밋이 있습니다. revert 전후 커밋과 stash도
함께 들어 있습니다.
README
    printf 'base\n' > "$repo/state.txt"
    git -C "$repo" add README.md state.txt
    git -C "$repo" commit -m 'chore: establish recovery baseline' >/dev/null
    git -C "$repo" branch -M main

    printf 'reset target\n' > "$repo/reset.txt"
    git -C "$repo" add reset.txt
    git -C "$repo" commit -m 'feat: create reset recovery target' >/dev/null
    reset_target=$(git -C "$repo" rev-parse HEAD)
    git -C "$repo" reset --hard --quiet HEAD^
    git -C "$repo" branch recovery/reset "$reset_target"

    git -C "$repo" switch --quiet --detach main
    printf 'detached target\n' > "$repo/detached.txt"
    git -C "$repo" add detached.txt
    git -C "$repo" commit -m 'feat: create detached recovery target' >/dev/null
    detached_target=$(git -C "$repo" rev-parse HEAD)
    git -C "$repo" branch recovery/detached "$detached_target"
    git -C "$repo" switch --quiet main

    tree_before=$(git -C "$repo" write-tree)
    printf 'temporary change\n' > "$repo/revert.txt"
    git -C "$repo" add revert.txt
    git -C "$repo" commit -m 'feat: add temporary recovery change' >/dev/null
    git -C "$repo" revert --no-edit --quiet HEAD
    if [[ "$(git -C "$repo" write-tree)" != "$tree_before" ]]; then
        printf '%s\n' 'Revert did not restore the baseline tree.' >&2
        exit 1
    fi

    printf 'tracked edit\n' >> "$repo/state.txt"
    printf 'untracked edit\n' > "$repo/untracked.txt"
    git -C "$repo" stash push --quiet -u -m 'recoverable working state'

    finalize_local_paths "$repo"
}

# [Implementation 8]
# Atomic lab publication

# [Implementation 8-1]
# Exclusive first publication
atomic_publish_no_replace() {
    python3 - "$1" "$2" <<'PY'
import ctypes
import os
import sys

source, destination = map(os.fsencode, sys.argv[1:])
libc = ctypes.CDLL(None, use_errno=True)

# 존재 여부 확인과 일반 rename 사이에는 대상이 새로 생길 수 있습니다.
# 커널의 no-replace 연산으로 확인과 이동을 한 번에 수행합니다.

try:
    if sys.platform == "darwin":
        function = libc.renamex_np
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        status = function(source, destination, 0x00000004)  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        function = libc.renameat2
        function.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        status = function(-100, source, -100, destination, 0x00000001)  # RENAME_NOREPLACE
    else:
        raise SystemExit(
            f"Exclusive atomic publish is unsupported on this platform: {sys.platform}"
        )
except AttributeError as error:
    raise SystemExit(f"Required atomic rename API is unavailable: {error}") from error

if status:
    error = ctypes.get_errno()
    raise OSError(error, os.strerror(error), os.fsdecode(destination))
PY
}

# [Implementation 8-2]
# Destination-identity-checked exchange
atomic_exchange() {
    python3 - "$1" "$2" "$3" <<'PY'
import ctypes
import os
import sys

source_path, destination_path, expected_identity = sys.argv[1:]
metadata = os.lstat(destination_path)
identity = f"{metadata.st_dev}:{metadata.st_ino}"
# 잠금 디렉터리를 만든 뒤 대상 inode가 바뀌었다면
# 다른 프로세스가 만든 결과를 덮어쓰지 않습니다.
if identity != expected_identity:
    raise SystemExit("Lab destination identity changed before publication.")

source, destination = map(os.fsencode, (source_path, destination_path))
libc = ctypes.CDLL(None, use_errno=True)

# 기존 `lab/`을 먼저 지우지 않습니다. exchange가 성공하는 한 순간에
# 준비한 디렉터리와 기존 디렉터리의 위치를 바꿉니다.

try:
    if sys.platform == "darwin":
        function = libc.renamex_np
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        status = function(source, destination, 0x00000002)  # RENAME_SWAP
    elif sys.platform.startswith("linux"):
        function = libc.renameat2
        function.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        status = function(-100, source, -100, destination, 0x00000002)  # RENAME_EXCHANGE
    else:
        raise SystemExit(
            f"Atomic exchange is unsupported on this platform: {sys.platform}"
        )
except AttributeError as error:
    raise SystemExit(f"Required atomic rename API is unavailable: {error}") from error

if status:
    error = ctypes.get_errno()
    raise OSError(error, os.strerror(error), destination_path)
PY
}

publish_staged_lab() {
    if (( FINAL_EXISTED == 1 )); then
        atomic_exchange "$STAGING_DIR" "$FINAL_LAB_DIR" "$FINAL_IDENTITY"
        rm -rf -- "$STAGING_DIR"
    else
        atomic_publish_no_replace "$STAGING_DIR" "$FINAL_LAB_DIR"
    fi
    STAGING_DIR=''
}

hold_before_publish_for_tests() {
    if [[ "${LOCAL_GIT_LAB_TEST_HOLD:-0}" != 1 ]]; then
        return
    fi

    local ready_file=${LOCAL_GIT_LAB_TEST_READY_FILE:-}
    local release_file=${LOCAL_GIT_LAB_TEST_RELEASE_FILE:-}

    if [[ -n "$ready_file" ]]; then
        if [[ "$ready_file" != /* || -e "$ready_file" || -L "$ready_file" ]]; then
            printf '%s\n' 'Test ready file must be a new absolute path.' >&2
            exit 1
        fi
        printf 'ready\n' > "$ready_file"
    fi

    if [[ -n "$release_file" ]]; then
        while [[ ! -e "$release_file" ]]; do
            sleep 0.02
        done
    else
        while :; do
            sleep 1
        done
    fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    parse_arguments "$@"
    assert_runtime_boundary
fi
