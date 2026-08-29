#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
TMP=''
HOLD_PID=''
RACE_PID=''
IDENTITY_PID=''

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

cleanup() {
    local status=$?
    local child

    trap - EXIT HUP INT TERM
    for child in "$HOLD_PID" "$RACE_PID" "$IDENTITY_PID"; do
        if [[ -n "$child" ]]; then
            kill -TERM "$child" 2>/dev/null || true
            wait "$child" 2>/dev/null || true
        fi
    done
    if [[ -n "$TMP" && -d "$TMP" ]]; then
        rm -rf -- "$TMP"
    fi
    exit "$status"
}

wait_for_file() {
    local path=$1
    local child=$2
    local attempt

    for ((attempt = 0; attempt < 500; attempt++)); do
        if [[ -s "$path" ]]; then
            return 0
        fi
        if ! kill -0 "$child" 2>/dev/null; then
            return 1
        fi
        sleep 0.02
    done
    return 1
}

assert_no_transaction_artifacts() {
    local project=$1
    local artifacts

    [[ ! -e "$project/.lab.lock" ]] || fail 'transaction lock was not removed'
    artifacts=$(printf '%s\n' "$project"/.lab.tmp.*)
    if [[ "$artifacts" != "$project/.lab.tmp.*" ]]; then
        fail 'staging directory was not removed'
    fi
}

# [Implementation 10]
# Standalone behavior and failure verification
run_tests() {
    local sandbox
    local script
    local ready
    local release
    local status
    local sample
    local developer_a
    local developer_b
    local maintainer
    local recovery
    local remote
    local tree_before_revert
    local tree_after_revert

    printf '%s\n' '[1/7] syntax and command contract'
    bash -n "$ROOT/git-lab.sh"
    bash -n "$ROOT/tests/test_git_lab.sh"

    TMP=$(mktemp -d "${TMPDIR:-/tmp}/local-git-lab-test.XXXXXX")
    TMP=$(cd -- "$TMP" && pwd -P)
    sandbox="$TMP/project"
    mkdir -p "$sandbox"
    cp "$ROOT/git-lab.sh" "$sandbox/git-lab.sh"
    chmod +x "$sandbox/git-lab.sh"
    script="$sandbox/git-lab.sh"

    export GIT_CONFIG_GLOBAL="$TMP/global.gitconfig"
    export GIT_CONFIG_NOSYSTEM=1
    export GIT_TERMINAL_PROMPT=0
    export GIT_PAGER=cat
    export PAGER=cat
    export GIT_EDITOR=true
    export LC_ALL=C
    git config --file "$GIT_CONFIG_GLOBAL" lab.sentinel preserved

    "$script" --help >/dev/null
    if "$script" unknown >/dev/null 2>&1; then
        fail 'unknown command was accepted'
    fi

    printf '%s\n' '[2/7] lock, interruption, and no-replace publication'
    # 두 번째 실행이 성공하면 같은 `lab/`을 동시에 교체할 수 있습니다.
    # 따라서 잠금 디렉터리를 만들지 못한 실행은 반드시 거부해야 합니다.
    ready="$TMP/hold-ready"
    LOCAL_GIT_LAB_TEST_HOLD=1 \
        LOCAL_GIT_LAB_TEST_READY_FILE="$ready" \
        "$script" sample >"$TMP/hold.log" 2>&1 &
    HOLD_PID=$!
    wait_for_file "$ready" "$HOLD_PID" || fail 'held transaction did not reach publish boundary'
    [[ -d "$sandbox/.lab.lock" ]] || fail 'transaction lock was not acquired'
    if "$script" sample >/dev/null 2>&1; then
        fail 'concurrent transaction bypassed the lock'
    fi
    kill -TERM "$HOLD_PID"
    if wait "$HOLD_PID" 2>/dev/null; then
        fail 'interrupted transaction returned success'
    fi
    HOLD_PID=''
    [[ ! -e "$sandbox/lab" ]] || fail 'interrupted transaction published a lab'
    assert_no_transaction_artifacts "$sandbox"

    # 최종 교체 직전에 다른 프로세스가 만든 `lab/`은
    # 먼저 시작한 프로세스가 덮어쓰면 안 됩니다.
    ready="$TMP/race-ready"
    release="$TMP/race-release"
    LOCAL_GIT_LAB_TEST_HOLD=1 \
        LOCAL_GIT_LAB_TEST_READY_FILE="$ready" \
        LOCAL_GIT_LAB_TEST_RELEASE_FILE="$release" \
        "$script" sample >"$TMP/race.log" 2>&1 &
    RACE_PID=$!
    wait_for_file "$ready" "$RACE_PID" || fail 'race transaction did not reach publish boundary'
    mkdir "$sandbox/lab"
    printf 'competitor\n' > "$sandbox/lab/sentinel"
    touch "$release"
    if wait "$RACE_PID" 2>/dev/null; then
        fail 'initial publication replaced a competing destination'
    fi
    RACE_PID=''
    [[ "$(cat "$sandbox/lab/sentinel")" == competitor ]] ||
        fail 'competing destination was modified'
    assert_no_transaction_artifacts "$sandbox"
    rm -rf -- "$sandbox/lab"

    printf '%s\n' '[3/7] boundary protection and complete generation'
    mkdir "$TMP/external-lab"
    printf 'preserve\n' > "$TMP/external-lab/sentinel"
    ln -s "$TMP/external-lab" "$sandbox/lab"
    if "$script" --reset all >/dev/null 2>&1; then
        fail 'symbolic-link lab directory was accepted'
    fi
    [[ -e "$TMP/external-lab/sentinel" ]] || fail 'symbolic-link target was modified'
    rm -- "$sandbox/lab"

    "$script" all >/dev/null
    sample="$sandbox/lab/sample-app"
    developer_a="$sandbox/lab/team-app-dev-a"
    developer_b="$sandbox/lab/team-app-dev-b"
    maintainer="$sandbox/lab/team-app-maintainer"
    recovery="$sandbox/lab/recovery-lab"
    remote="$sandbox/lab/remotes/team-app.git"

    [[ -d "$sample/.git" ]] || fail 'sample clone was not created'
    [[ -d "$developer_a/.git" ]] || fail 'developer A clone was not created'
    [[ -d "$developer_b/.git" ]] || fail 'developer B clone was not created'
    [[ -d "$maintainer/.git" ]] || fail 'maintainer clone was not created'
    [[ -d "$recovery/.git" ]] || fail 'recovery repository was not created'
    [[ -d "$sandbox/lab/remotes/sample-app.git" ]] || fail 'sample bare remote was not created'
    [[ -d "$remote" ]] || fail 'team bare remote was not created'

    if "$script" all >/dev/null 2>&1; then
        fail 'create mode replaced an existing complete lab'
    fi

    printf '%s\n' '[4/7] generated project and topology contracts'
    "$sample/scripts/test.sh" >/dev/null
    "$developer_a/scripts/check.sh" >/dev/null
    "$developer_b/scripts/check.sh" >/dev/null
    "$maintainer/scripts/check.sh" >/dev/null

    [[ -z "$(git -C "$sample" status --porcelain)" ]] || fail 'sample clone is dirty'
    [[ -z "$(git -C "$developer_a" status --porcelain)" ]] || fail 'developer A clone is dirty'
    [[ -z "$(git -C "$developer_b" status --porcelain)" ]] || fail 'developer B clone is dirty'
    [[ -z "$(git -C "$maintainer" status --porcelain)" ]] || fail 'maintainer clone is dirty'
    [[ -z "$(git -C "$recovery" status --porcelain)" ]] || fail 'recovery repository is dirty'

    [[ "$(git -C "$sample" remote get-url origin)" == "$sandbox/lab/remotes/sample-app.git" ]] ||
        fail 'sample origin does not point to the published remote'
    for repo in "$developer_a" "$developer_b" "$maintainer"; do
        [[ "$(git -C "$repo" remote get-url origin)" == "$remote" ]] ||
            fail 'team origin does not point to the published remote'
        [[ "$(git -C "$repo" config core.hooksPath)" == "$sandbox/lab/.empty-hooks" ]] ||
            fail 'team hooks path still points to staging'
    done
    [[ "$(git -C "$sample" config core.hooksPath)" == "$sandbox/lab/.empty-hooks" ]] ||
        fail 'sample hooks path still points to staging'
    [[ "$(git -C "$recovery" config core.hooksPath)" == "$sandbox/lab/.empty-hooks" ]] ||
        fail 'recovery hooks path still points to staging'

    [[ "$(git -C "$developer_a" branch --show-current)" == feature/add-priority ]] ||
        fail 'developer A branch is unexpected'
    [[ "$(git -C "$developer_b" branch --show-current)" == feature/add-assignee ]] ||
        fail 'developer B branch is unexpected'
    [[ "$(git -C "$maintainer" branch --show-current)" == main ]] ||
        fail 'maintainer branch is unexpected'
    grep -qx '  - priority' "$developer_a/config/task-fields.yml" ||
        fail 'priority field is missing from developer A'
    grep -qx '  - assignee' "$developer_b/config/task-fields.yml" ||
        fail 'assignee field is missing from developer B'
    grep -qx '  - priority' "$maintainer/config/task-fields.yml" ||
        fail 'priority field is missing from main'
    git --git-dir="$remote" show-ref --verify --quiet refs/heads/feature/add-priority ||
        fail 'priority branch was not published'
    git --git-dir="$remote" show-ref --verify --quiet refs/heads/feature/add-assignee ||
        fail 'assignee branch was not published'
    git -C "$maintainer" merge-base --is-ancestor origin/feature/add-priority main ||
        fail 'priority branch is not integrated into main'
    if git -C "$maintainer" merge-base --is-ancestor origin/feature/add-assignee main; then
        fail 'assignee branch should remain divergent from main'
    fi

    # 두 브랜치가 같은 YAML 위치를 수정하므로
    # 실제 rebase 충돌이 발생해야 합니다.
    set +e
    GIT_EDITOR=true git -C "$developer_b" rebase origin/main >/dev/null 2>&1
    status=$?
    set -e
    [[ $status -ne 0 ]] || fail 'divergent branches did not produce the expected rebase conflict'
    grep -Eq '^(<<<<<<<|=======|>>>>>>>)' "$developer_b/config/task-fields.yml" ||
        fail 'rebase conflict markers were not produced'
    git -C "$developer_b" rebase --abort >/dev/null
    [[ -z "$(git -C "$developer_b" status --porcelain)" ]] ||
        fail 'rebase abort did not restore a clean clone'

    printf '%s\n' '[5/7] recovery reference state'
    [[ "$(git -C "$recovery" show recovery/reset:reset.txt)" == 'reset target' ]] ||
        fail 'reset recovery branch does not preserve its target'
    [[ "$(git -C "$recovery" show recovery/detached:detached.txt)" == 'detached target' ]] ||
        fail 'detached recovery branch does not preserve its target'
    tree_before_revert=$(git -C "$recovery" rev-parse HEAD~2^{tree})
    tree_after_revert=$(git -C "$recovery" rev-parse HEAD^{tree})
    [[ "$tree_before_revert" == "$tree_after_revert" ]] ||
        fail 'revert pair did not restore the prior tree'
    [[ "$(git -C "$recovery" stash list | wc -l | tr -d ' ')" == 1 ]] ||
        fail 'recovery stash was not preserved'
    git -C "$recovery" stash show --name-only 'stash@{0}' | grep -qx state.txt ||
        fail 'tracked recovery change is missing from the stash'
    git -C "$recovery" ls-tree -r --name-only 'stash@{0}^3' | grep -qx untracked.txt ||
        fail 'untracked recovery change is missing from the stash'

    printf '%s\n' '[6/7] selective reset isolation'
    printf 'sample\n' > "$sample/.sample-marker"
    printf 'team\n' > "$developer_a/.team-marker"
    printf 'recovery\n' > "$recovery/.recovery-marker"

    "$script" --reset sample >/dev/null
    [[ ! -e "$sample/.sample-marker" ]] || fail 'sample reset preserved sample state'
    [[ -e "$developer_a/.team-marker" ]] || fail 'sample reset modified team state'
    [[ -e "$recovery/.recovery-marker" ]] || fail 'sample reset modified recovery state'

    printf 'sample\n' > "$sample/.sample-marker"
    "$script" --reset team >/dev/null
    [[ -e "$sample/.sample-marker" ]] || fail 'team reset modified sample state'
    [[ ! -e "$developer_a/.team-marker" ]] || fail 'team reset preserved team state'
    [[ -e "$recovery/.recovery-marker" ]] || fail 'team reset modified recovery state'

    printf 'team\n' > "$developer_a/.team-marker"
    "$script" --reset recovery >/dev/null
    [[ -e "$sample/.sample-marker" ]] || fail 'recovery reset modified sample state'
    [[ -e "$developer_a/.team-marker" ]] || fail 'recovery reset modified team state'
    [[ ! -e "$recovery/.recovery-marker" ]] || fail 'recovery reset preserved recovery state'

    printf 'recovery\n' > "$recovery/.recovery-marker"
    "$script" --reset all >/dev/null
    [[ ! -e "$sample/.sample-marker" ]] || fail 'all reset preserved sample state'
    [[ ! -e "$developer_a/.team-marker" ]] || fail 'all reset preserved team state'
    [[ ! -e "$recovery/.recovery-marker" ]] || fail 'all reset preserved recovery state'

    printf '%s\n' '[7/7] identity-checked exchange and global-config isolation'
    # 잠금 디렉터리를 만든 뒤 `lab/`의 inode가 바뀌면
    # 준비한 결과를 새 대상과 교환하지 않아야 합니다.
    ready="$TMP/identity-ready"
    release="$TMP/identity-release"
    LOCAL_GIT_LAB_TEST_HOLD=1 \
        LOCAL_GIT_LAB_TEST_READY_FILE="$ready" \
        LOCAL_GIT_LAB_TEST_RELEASE_FILE="$release" \
        "$script" --reset sample >"$TMP/identity.log" 2>&1 &
    IDENTITY_PID=$!
    wait_for_file "$ready" "$IDENTITY_PID" ||
        fail 'exchange transaction did not reach publish boundary'
    mv "$sandbox/lab" "$sandbox/lab-original"
    mkdir "$sandbox/lab"
    printf 'competitor\n' > "$sandbox/lab/sentinel"
    touch "$release"
    if wait "$IDENTITY_PID" 2>/dev/null; then
        fail 'exchange replaced a destination with a changed identity'
    fi
    IDENTITY_PID=''
    [[ "$(cat "$sandbox/lab/sentinel")" == competitor ]] || fail 'changed destination was modified'
    assert_no_transaction_artifacts "$sandbox"
    rm -rf -- "$sandbox/lab"
    mv "$sandbox/lab-original" "$sandbox/lab"

    [[ "$(git config --file "$GIT_CONFIG_GLOBAL" lab.sentinel)" == preserved ]] ||
        fail 'global Git configuration was modified'

    printf '%s\n' 'local-git-lab verification passed'
}

trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
run_tests
