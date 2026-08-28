# Git 복구 절차

## 목표

문제가 생겼을 때 “되돌리기”라는 말만 보고 명령을 고르지 않습니다. 변경이 어디에 있고 다른 사람과 공유됐는지 확인한 뒤 손실 범위가 가장 작은 방법을 선택합니다.

먼저 세 가지를 구분합니다.

```text
1. 아직 커밋하지 않은 변경인가?
2. 로컬에만 있는 커밋인가?
3. 이미 원격에 게시한 커밋인가?
```

## 가장 먼저 할 일

위험한 명령을 실행하기 전에 현재 상태를 기록합니다.

```bash
git status
git branch --show-current
git branch -vv
git log --oneline --decorate --graph --all -15
git reflog -15
```

진행 중인 작업도 확인합니다.

```text
merge in progress
rebase in progress
cherry-pick in progress
revert in progress
```

현재 `HEAD`를 잃을 가능성이 있으면 보존 브랜치를 만듭니다.

```bash
git branch backup/before-recovery-$(date +%Y%m%d-%H%M%S)
```

중요한 미추적 파일은 브랜치와 reflog가 보호하지 않습니다. 별도 디렉터리에 복사할지 확인합니다.

## 상황별 선택표

| 상황 | 먼저 검토할 명령 | 결과 |
| --- | --- | --- |
| 스테이징하지 않은 추적 파일 변경 취소 | `git restore FILE` | 작업 트리 수정 제거 |
| 스테이징만 취소하고 수정 유지 | `git restore --staged FILE` | 인덱스만 HEAD 기준으로 복원 |
| 마지막 로컬 커밋 보완 | `git commit --amend` | 마지막 커밋을 새 커밋으로 교체 |
| 로컬 커밋을 다시 작업 상태로 | `git reset --soft HEAD~1` 또는 `git reset HEAD~1` | 브랜치 이동, 변경 보존 |
| 잘못된 로컬 브랜치에 커밋 | 새 브랜치 생성 또는 `cherry-pick` | 커밋을 먼저 보존 |
| 이미 공유한 잘못된 커밋 취소 | `git revert SHA` | 반대 변경을 새 커밋으로 기록 |
| reset/rebase 뒤 커밋이 보이지 않음 | `git reflog`와 새 브랜치 | 이전 위치를 다시 참조 |
| 진행 중인 merge/rebase 중단 | `--abort` | 시작 전 상태로 복귀 시도 |
| 미추적 파일 삭제 검토 | `git clean -nd` | 삭제 예정 목록만 표시 |
| push가 거부됨 | `fetch` 뒤 그래프 확인 | 원격 차이 조사 |

## 작업 트리 변경 복구

### 스테이징하지 않은 추적 파일 변경 버리기

먼저 diff를 확인합니다.

```bash
git diff -- src/app.py
```

정말 버릴 내용이면:

```bash
git restore src/app.py
```

이 명령은 작업 트리 수정을 제거합니다. 복구할 브랜치나 reflog 기록이 생기는 명령이 아닙니다.

### 스테이징만 취소하기

```bash
git diff --staged -- src/app.py
git restore --staged src/app.py
```

파일 수정은 작업 트리에 남아야 합니다.

```bash
git status --short
git diff -- src/app.py
git diff --staged -- src/app.py
```

## 로컬 커밋 복구

### 마지막 커밋에 누락 추가

아직 공유하지 않았다면:

```bash
# 파일 수정
git add path/to/file
git diff --staged
git commit --amend --no-edit
```

해시가 바뀐다는 점을 확인합니다.

### 마지막 커밋을 다시 나누기

먼저 보존 브랜치를 만듭니다.

```bash
git branch backup/before-split
```

커밋을 취소하고 변경을 인덱스에 유지합니다.

```bash
git reset --soft HEAD~1
```

다시 스테이징하려면:

```bash
git restore --staged .
git add -p
git diff --staged
```

옵션 없는 `git reset HEAD~1`은 브랜치와 인덱스를 이전 커밋으로 돌리지만 작업 트리 변경은 유지합니다.

### 잘못된 브랜치에 커밋

현재 커밋을 먼저 새 브랜치로 보존합니다.

```bash
git switch -c feature/correct-topic
```

이미 올바른 브랜치가 있다면 커밋 SHA를 기록하고 `cherry-pick`합니다.

```bash
git switch feature/correct-topic
git cherry-pick COMMIT_SHA
```

잘못된 원래 브랜치를 정리할 때는 그 브랜치가 공유됐는지에 따라 `reset` 또는 `revert`를 선택합니다.

## 공유한 커밋 취소

원격에 게시한 커밋은 일반적으로 이력에서 지우지 않고 반대 변경을 새 커밋으로 남깁니다.

```bash
git fetch origin
git show BAD_COMMIT_SHA
git revert BAD_COMMIT_SHA
```

충돌이 나면:

```bash
git status
# 파일 수정
git add path/to/resolved-file
git revert --continue
```

취소하려면:

```bash
git revert --abort
```

merge 커밋을 `revert`할 때는 기준 부모를 확인해야 합니다.

```bash
git show --no-patch --pretty=raw MERGE_COMMIT_SHA
git revert -m 1 MERGE_COMMIT_SHA
```

`-m 1`을 관례처럼 복사하지 않습니다. 어느 부모를 유지할지 이해한 뒤 사용합니다.

## 진행 중인 작업 중단

```bash
git merge --abort
git rebase --abort
git cherry-pick --abort
git revert --abort
```

`--quit`은 진행 정보만 지우고 인덱스와 작업 트리를 그대로 둘 수 있습니다. 시작 전 상태로 돌아가려면 `--abort`와 차이를 확인합니다.

## reflog에서 커밋 찾기

reflog는 로컬 ref와 `HEAD`가 이전에 가리킨 위치를 기록합니다.

```bash
git reflog --date=local -30
```

후보 커밋을 확인합니다.

```bash
git show CANDIDATE_SHA
```

찾았으면 바로 이름 있는 브랜치로 보존합니다.

```bash
git branch recovery/lost-work CANDIDATE_SHA
```

reflog는 로컬 저장소마다 다르고 영구 보관소가 아닙니다. 찾은 뒤 미루지 않습니다.

## detached `HEAD` 커밋 보존

브랜치 없이 커밋을 만들었다면 현재 위치를 기록합니다.

```bash
git rev-parse HEAD
git switch main
git branch recovery/detached SAVED_SHA
```

브랜치로 이름을 붙이면 이후에도 쉽게 찾을 수 있습니다.

## stash 사용

추적·미추적 변경을 함께 보관하려면:

```bash
git stash push -u -m 'work before rebase'
```

확인합니다.

```bash
git stash list
git stash show --stat 'stash@{0}'
```

적용만 하고 stash는 남기려면:

```bash
git stash apply --index 'stash@{0}'
```

적용이 성공한 뒤 직접 삭제합니다.

```bash
git stash drop 'stash@{0}'
```

`pop`은 `apply`와 성공 시 `drop`을 함께 수행합니다. 충돌 뒤 stash가 남았는지 확인합니다. 중요한 장기 작업은 stash보다 브랜치와 커밋으로 보존합니다.

## `reset --hard`와 `clean`

### `reset --hard`

현재 브랜치, 인덱스와 추적 파일을 대상 커밋에 맞춥니다.

실행 전:

```bash
git status --short
git diff
git diff --staged
git log --oneline --decorate -10
git branch backup/before-hard-reset
```

### `clean`

미추적 파일을 삭제할 수 있습니다. 반드시 모의 실행부터 합니다.

```bash
git clean -nd
```

무시된 파일까지 보려면:

```bash
git clean -ndx
```

실제 삭제는 목록을 확인한 뒤에만 검토합니다.

```bash
git clean -fd
```

`-x`를 실제 삭제에 사용하면 로컬 환경 설정 파일과 빌드 캐시도 사라질 수 있습니다.

## 잘못된 강제 push

1. 해당 브랜치에 추가 push를 멈추라고 알립니다.
2. 강제 push 전 복제본이나 reflog에서 이전 SHA를 찾습니다.
3. 후보를 브랜치로 보존합니다.
4. 팀이 복구할 SHA와 현재 원격 SHA에 합의합니다.
5. 예상 원격 SHA를 지정해 복구합니다.

```bash
git push \
  --force-with-lease=BRANCH:CURRENT_REMOTE_SHA \
  origin RECOVERY_SHA:BRANCH
```

개인 판단으로 공유 브랜치를 다시 쓰지 않습니다.

## 비밀값을 커밋한 경우

이력 삭제보다 인증 정보 폐기·교체가 먼저입니다.

```text
토큰 폐기 또는 교체
비밀번호 변경
SSH 키 폐기·재발급
접근 로그 확인
보안 담당자와 저장소 관리자에게 알림
```

이미 push했다면 노출된 것으로 간주합니다. 최신 커밋에서 파일만 지워도 과거 이력, fork, 복제본과 CI 캐시에서는 남을 수 있습니다. 이력 재작성은 관리자가 영향 범위를 확인한 뒤 별도 절차로 진행합니다.

## `local-git-lab`의 `recovery` 상태 확인

```bash
cd exercises/local-git-lab
./git-lab.sh --reset recovery
cd lab/recovery-lab
```

전체 그래프와 reflog를 확인합니다.

```bash
git log --oneline --decorate --graph --all
git reflog
git branch --list 'recovery/*'
git stash list
```

reset 뒤 보존한 파일:

```bash
git show recovery/reset:reset.txt
```

detached `HEAD`에서 만든 파일:

```bash
git show recovery/detached:detached.txt
```

`revert` 전후 tree 비교:

```bash
git rev-parse HEAD~2^{tree}
git rev-parse HEAD^{tree}
```

stash가 보존한 파일:

```bash
git stash show --name-only 'stash@{0}'
git ls-tree -r --name-only 'stash@{0}^3'
```

## 복구 후 검증

```bash
git status --short --branch
git branch -vv
git log --oneline --decorate --graph --all -15
git diff
git diff --staged
# 프로젝트가 지정한 검사 실행
```

확인할 내용:

```text
[ ] 필요한 커밋이 브랜치로 보존됐는가?
[ ] 작업 트리와 인덱스가 예상한 상태인가?
[ ] 미추적 파일 손실이 없는가?
[ ] 다른 사람의 원격 커밋을 지우지 않았는가?
[ ] 프로젝트 검사가 통과하는가?
```

## 완료 기준

- 커밋하지 않은 변경, 로컬 커밋, 공유한 커밋을 구분합니다.
- `restore`, `reset`, `revert`의 대상을 설명합니다.
- reflog에서 커밋을 찾아 브랜치로 보존합니다.
- stash의 추적·미추적 상태를 확인합니다.
- `reset --hard`, `clean`, 강제 push 전에 손실 범위와 복구 지점을 확인합니다.
