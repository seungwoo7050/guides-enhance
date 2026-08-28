# merge, rebase와 충돌 해결

## 목표

- merge와 rebase가 커밋 그래프를 어떻게 바꾸는지 설명합니다.
- 충돌 표시의 한쪽을 무조건 선택하지 않고 두 변경 의도를 확인합니다.
- 해결할 수 없으면 시작 전 상태로 돌아갑니다.
- 이력 재작성 뒤 push 조건을 확인합니다.

## 분기된 그래프 읽기

공통 커밋 `B`에서 두 브랜치가 갈라졌다고 가정합니다.

```text
A──B──C        main
    \
     D──E      feature
```

### merge

feature에서 `main`을 merge하면 기존 커밋을 유지한 채 두 이력을 연결합니다.

```text
A──B──C────M   feature
    \      /
     D────E
```

- `C`, `D`, `E`의 해시를 바꾸지 않습니다.
- 두 부모를 가진 merge 커밋 `M`이 생길 수 있습니다.
- 분기와 통합 사실이 그래프에 남습니다.

### rebase

feature를 `main` 위로 rebase하면 `D`, `E`의 변경을 `C` 뒤에 다시 적용합니다.

```text
A──B──C──D'──E'   feature
```

- `D'`, `E'`는 새 커밋입니다.
- 원래 `D`, `E`와 해시가 다릅니다.
- 이미 게시한 브랜치를 rebase하면 원격 브랜치를 갱신할 때 이력 재작성이 필요합니다.

## 선택 기준

| 상황 | 먼저 검토할 선택 |
| --- | --- |
| 여러 사람이 함께 쓰는 공유 브랜치 | merge 또는 팀이 정한 비재작성 방식 |
| 아직 push하지 않은 개인 브랜치 | rebase 가능 |
| 작성자 한 명만 쓰는 PR 브랜치 | 팀 규칙과 리뷰 상태 확인 뒤 rebase 가능 |
| 분기와 통합 기록을 남겨야 함 | merge 검토 |
| 기준 브랜치 위에 로컬 커밋을 다시 정렬하려 함 | rebase 검토 |

“merge는 안전하고 rebase는 깔끔하다”처럼 단순화하지 않습니다. 누가 브랜치를 사용하고 있는지, 커밋이 이미 공유됐는지가 판단 기준입니다.

## 충돌이 발생하는 이유

Git은 공통 조상과 양쪽 변경을 비교합니다.

```text
기준:      title, status
변경 A:    title, status, priority
변경 B:    title, status, assignee
```

같은 부분을 서로 다르게 고치면 Git이 최종 결과를 결정하지 못할 수 있습니다. 충돌은 Git이 고장 난 상태가 아니라 사람이 의미를 확인해야 하는 상태입니다.

해결 전에 다음을 확인합니다.

```text
각 변경은 왜 필요했는가?
둘 다 남아야 하는가?
최종 파일 형식은 유효한가?
프로젝트 검사가 통과하는가?
```

## `local-git-lab`에서 rebase 충돌 만들기

기존 `team` 상태를 버려도 되는지 확인한 뒤 다시 만듭니다.

```bash
cd exercises/local-git-lab
./git-lab.sh --reset team
cd lab/team-app-dev-b
```

현재 그래프를 확인합니다.

```bash
git fetch origin
git log --oneline --decorate --graph --all -15
```

`feature/add-assignee`는 이전 `main`에서 분기했고, 최신 `origin/main`에는 `priority` 필드가 들어 있습니다.

rebase합니다.

```bash
git rebase origin/main
```

충돌이 발생하면 먼저 상태를 읽습니다.

```bash
git status
git diff
```

rebase 중에는 새 기준점 쪽 상태와 다시 적용 중인 커밋을 다음처럼 비교할 수 있습니다.

```bash
git show HEAD:config/task-fields.yml
git show REBASE_HEAD:config/task-fields.yml
```

merge와 rebase에서는 `ours`, `theirs`가 가리키는 관점이 달라질 수 있습니다. 사람 이름처럼 외우지 말고 `HEAD`, `MERGE_HEAD`, `REBASE_HEAD`의 실제 내용을 확인합니다.

## 두 변경을 보존해 해결하기

최종 파일을 다음처럼 만듭니다.

```yaml
fields:
  - title
  - status
  - priority
  - assignee
```

충돌 표시가 남았는지와 파일 형식을 확인합니다.

```bash
git diff --check
./scripts/check.sh
git add config/task-fields.yml
git status
git diff --staged
```

rebase를 계속합니다.

```bash
GIT_EDITOR=true git rebase --continue
```

완료 뒤 확인합니다.

```bash
./scripts/check.sh
git status --short --branch
git log --oneline --decorate --graph --all -15
```

로컬 커밋 해시가 `origin/feature/add-assignee`의 이전 해시와 달라졌는지 확인합니다.

## 해결하지 않고 취소하기

방향이 불분명하거나 잘못된 기준점을 골랐다면 중단합니다.

```bash
git rebase --abort
```

확인합니다.

```bash
git status --short --branch
git log --oneline --decorate --graph --all -12
```

rebase 시작 전에 작업 트리를 깨끗하게 유지해야 `--abort` 뒤 상태도 판단하기 쉽습니다.

merge를 중단할 때는:

```bash
git merge --abort
```

## rebase 뒤 일반 push가 거부되는 이유

rebase 전 원격 브랜치는 이전 커밋을 가리키고, 로컬 브랜치는 새 커밋을 가리킵니다. 두 브랜치 끝은 fast-forward 관계가 아니므로 일반 push가 거부됩니다.

```bash
git push
```

실패 뒤 확인합니다.

```bash
git fetch origin
git log --oneline --decorate --graph --all -15
```

다음 조건을 모두 확인한 뒤에만 `--force-with-lease`를 검토합니다.

```text
[ ] 이 브랜치를 다른 사람이 함께 사용하지 않는가?
[ ] 팀이 PR 브랜치 이력 재작성을 허용하는가?
[ ] 리뷰어에게 해시 변경을 알렸는가?
[ ] 원격 브랜치가 예상한 이전 커밋 그대로인가?
[ ] 필요한 로컬 커밋을 별도 브랜치로 보존했는가?
```

일반 형식:

```bash
git push --force-with-lease origin HEAD:feature/add-assignee
```

예상한 원격 SHA를 직접 지정하면 조건이 더 분명합니다.

```bash
git push \
  --force-with-lease=feature/add-assignee:EXPECTED_OLD_SHA \
  origin HEAD:feature/add-assignee
```

`--force-with-lease`는 예상과 다른 원격 갱신을 거부할 뿐입니다. 공유 브랜치를 다시 써도 된다는 허가를 대신하지 않습니다.

## 같은 상황을 merge로 처리하기

`team` 구성을 다시 만든 뒤 개발자 B에서 실행합니다.

```bash
git fetch origin
git merge origin/main
```

충돌 해결 절차는 비슷합니다.

```bash
git status
# 파일 수정
./scripts/check.sh
git diff --check
git add config/task-fields.yml
git merge --continue
```

merge는 기존 작업 브랜치 커밋을 새로 만들지 않으므로 해결 뒤 일반 push가 가능한 경우가 많습니다.

## 충돌 해결 표준 절차

```bash
# 현재 작업과 충돌 파일 확인
git status
git diff

# 각 쪽의 실제 내용과 의도 확인
git show HEAD:path/to/file

# 최종 파일 작성 뒤 검사
./scripts/check.sh
git diff --check

# 해결 표시
git add path/to/file
git diff --staged
git status

# 계속 또는 중단
git rebase --continue
# 또는 git rebase --abort
```

## 피해야 할 처리

- 충돌 표시만 지우고 테스트를 실행하지 않습니다.
- `ours` 또는 `theirs`를 사람 A/B로 고정해 외우지 않습니다.
- 작업 트리에 관련 없는 변경이 있는 상태에서 merge/rebase를 시작하지 않습니다.
- 일반 push가 거부됐다는 이유만으로 `--force`를 사용하지 않습니다.
- 생성 파일의 충돌만 고치고 원본 파일을 빠뜨리지 않습니다.

## 완료 기준

- merge와 rebase 그래프를 직접 그릴 수 있습니다.
- rebase가 커밋 해시를 바꾸는 이유를 설명합니다.
- 실제 충돌에서 두 변경 의도를 보존해 해결합니다.
- `--abort`로 시작 전 상태에 돌아갑니다.
- `--force-with-lease`가 검사하는 조건과 검사하지 않는 팀 규칙을 구분합니다.
