# Git 협업과 GitHub Actions CI 학습 지도

## 목표

이 과정의 목표는 Git 명령을 많이 아는 것이 아닙니다. 다음 반복을 안전하게 수행하는 것입니다.

```text
현재 상태 확인
→ 작은 변경
→ 목적별 검토와 커밋
→ 작업 브랜치 게시
→ Pull Request와 CI
→ 리뷰 반영
→ 통합
→ 문제가 생기면 손실 범위를 확인하고 복구
```

## 선행 조건

- 터미널에서 현재 디렉터리를 확인하고 명령을 실행할 수 있어야 합니다.
- 텍스트 파일을 편집할 수 있어야 합니다.
- Python 3.11 이상, Git 2.23 이상과 Bash를 사용할 수 있어야 합니다.
- GitHub Actions 실습에는 GitHub 저장소를 만들고 Pull Request를 열 수 있는 계정이 필요합니다.

`local-git-lab`은 Linux와 macOS를 지원합니다. Windows에서는 WSL2를 사용합니다.

## 완료 시 남아야 하는 능력

### Git 상태를 읽는 능력

- 작업 트리, 인덱스, `HEAD`를 구분합니다.
- 로컬 브랜치와 원격 추적 브랜치를 구분합니다.
- `fetch`가 현재 파일을 자동으로 바꾸지 않는 이유를 설명합니다.

### 변경을 검토 가능한 단위로 기록하는 능력

- `git diff`와 `git diff --staged`를 구분합니다.
- 같은 파일에 섞인 변경도 목적별로 스테이징합니다.
- 커밋 전 프로젝트 검사를 실행하고 커밋될 정확한 diff를 확인합니다.

### 원격 협업과 통합 능력

- 최신 기준 브랜치에서 작업 브랜치를 만들고 최초 push로 upstream을 설정합니다.
- Pull Request의 base, head와 merge base를 기준으로 한 diff를 확인합니다.
- merge와 rebase의 차이, 충돌 상태와 중단 방법을 설명합니다.

### 복구 능력

- 아직 커밋하지 않은 변경, 로컬 커밋, 이미 공유한 커밋을 구분합니다.
- 상황에 맞게 `restore`, `reset`, `revert`, `reflog`, `stash`를 사용합니다.
- 손실 가능성이 있는 명령 전에 보존 지점을 만듭니다.

### GitHub Actions CI 운영 능력

- 이벤트, 워크플로 실행, `job`, runner, `step`의 관계를 설명합니다.
- 로컬과 CI가 같은 검사 명령을 실행하도록 구성합니다.
- 실패한 `job`과 `step`의 로그를 읽고 로컬에서 재현합니다.
- 최소 `permissions`, 비밀값 제한, fork Pull Request와 외부 Action 고정 방식을 설명합니다.

## 필수 경로

### 1단계: 작업 시작 상태

읽을 문서:

- [`01-workspace-basics.md`](01-workspace-basics.md)

바로 실행할 항목:

```bash
cd exercises/local-git-lab
./git-lab.sh sample

git -C lab/sample-app status --short --branch
git -C lab/sample-app branch -vv
git -C lab/sample-app remote -v
```

완료 기준:

- 현재 브랜치, upstream, 원격 저장소와 작업 트리 상태를 설명합니다.
- `origin/main`이 언제 갱신되는지 설명합니다.

### 2단계: 목적별 커밋

읽을 문서:

- [`02-commit-workflow.md`](02-commit-workflow.md)

실행 위치:

```text
exercises/local-git-lab/lab/sample-app
```

완료 기준:

- 관련 변경과 무관한 변경을 다른 커밋으로 나눕니다.
- `git diff --staged`가 다음 커밋의 내용을 보여 준다는 것을 확인합니다.

### 3단계: 원격 협업

읽을 문서:

- [`03-remote-pr-workflow.md`](03-remote-pr-workflow.md)

바로 실행할 항목:

```bash
cd exercises/local-git-lab
./git-lab.sh team

git -C lab/team-app-dev-a branch -vv
git -C lab/team-app-dev-b branch -vv
git -C lab/team-app-maintainer log --oneline --decorate --graph --all
```

완료 기준:

- 세 복제본의 로컬 브랜치와 원격 추적 ref가 서로 독립적임을 설명합니다.
- push와 fetch가 각각 어느 ref를 바꾸는지 설명합니다.

### 4단계: merge, rebase와 충돌

읽을 문서:

- [`04-merge-rebase-conflicts.md`](04-merge-rebase-conflicts.md)

실행 위치:

```text
exercises/local-git-lab/lab/team-app-dev-b
```

완료 기준:

- `origin/main`으로 rebase하여 충돌을 재현합니다.
- 두 필드를 모두 보존해 해결하거나 `git rebase --abort`로 돌아갑니다.
- rebase 뒤 일반 push가 거부될 수 있는 이유를 설명합니다.

### 5단계: 복구

읽을 문서:

- [`05-recovery-runbook.md`](05-recovery-runbook.md)

바로 실행할 항목:

```bash
cd exercises/local-git-lab
./git-lab.sh recovery

git -C lab/recovery-lab log --oneline --decorate --graph --all
git -C lab/recovery-lab reflog
git -C lab/recovery-lab stash list
```

완료 기준:

- reset과 detached `HEAD` 뒤의 커밋이 어느 브랜치에 보존됐는지 찾습니다.
- revert가 기존 커밋을 삭제하지 않는 이유를 설명합니다.
- stash가 보존한 추적·미추적 파일을 확인합니다.

### 6단계: GitHub Actions 실행 모델

읽을 문서:

- [`06-github-actions-workflow-model.md`](06-github-actions-workflow-model.md)

바로 실행할 항목:

```bash
cd exercises/github-actions-ci
./scripts/check.sh
```

확인할 파일:

```text
.github/workflows/ci.yml
scripts/check.sh
src/change_record.py
tests/
```

완료 기준:

- 워크플로가 어떤 이벤트에서 시작되는지 설명합니다.
- 각 `job`이 어떤 runner에서 어떤 명령을 실행하는지 설명합니다.
- 로컬과 CI가 동일한 `./scripts/check.sh`를 사용함을 확인합니다.

### 7단계: Pull Request CI와 보안

읽을 문서:

- [`07-pull-request-ci-and-security.md`](07-pull-request-ci-and-security.md)

실제 GitHub 저장소에서 확인할 항목:

1. `github-actions-ci`를 독립 저장소나 연습 브랜치에 게시합니다.
2. 일부 코드를 수정한 브랜치로 Pull Request를 엽니다.
3. Actions 검사가 실행되는지 확인합니다.
4. 의도적인 실패를 한 번 만들고 실패한 `step`을 찾습니다.
5. 수정 후 다시 push하여 검사가 통과하는지 확인합니다.

완료 기준:

- `pull_request` 이벤트에서 신뢰하지 않은 코드가 실행된다는 사실을 설명합니다.
- 워크플로의 `permissions`와 Action SHA 고정 이유를 설명합니다.
- 필수 상태 검사가 통과하기 전 병합을 막는 저장소 설정을 확인합니다.

## 선택 경로

- [`90-open-source-contribution.md`](90-open-source-contribution.md)

fork 기반 기여를 할 때만 읽습니다. 일반 팀 내부 협업과 GitHub Actions CI를 완료하는 데 필수는 아닙니다.

## 최종 검증

다음 질문에 명령과 상태 그림으로 답할 수 있어야 합니다.

- `git diff`가 비어 있는데 커밋될 변경이 남아 있을 수 있습니까?
- 작업 브랜치의 시작점과 upstream은 왜 다를 수 있습니까?
- `fetch` 전후에 어느 ref가 바뀝니까?
- merge와 rebase 중 기존 커밋 해시를 바꾸는 것은 무엇입니까?
- 공유한 잘못된 커밋은 왜 일반적으로 `reset`보다 `revert`로 취소합니까?
- GitHub Actions에서 실패한 명령의 종료 상태는 어떻게 `job` 결과가 됩니까?
- `GITHUB_TOKEN`에 쓰기 권한이 필요하지 않은 `job`은 왜 `contents: read`만 요청해야 합니까?
- fork Pull Request에서 비밀값을 사용할 수 없도록 제한하는 이유는 무엇입니까?

모든 답을 재현할 수 있으면 필수 과정이 끝납니다.
