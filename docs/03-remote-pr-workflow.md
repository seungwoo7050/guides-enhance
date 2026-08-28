# 원격 브랜치와 Pull Request 협업

## 목표

로컬 작업을 원격 브랜치에 게시하고, 리뷰 가능한 Pull Request로 제안한 뒤, CI와 리뷰 결과를 반영합니다.

```text
최신 기준 브랜치 확인
→ 작업 브랜치 생성
→ 목적별 커밋
→ 최초 push와 upstream 설정
→ Pull Request
→ CI와 리뷰 반영
→ 병합 뒤 정리
```

## 원격 상태를 구분하기

### 로컬 브랜치와 원격 추적 브랜치

```text
feature/add-priority          내 로컬 브랜치
origin/feature/add-priority   마지막 fetch 또는 push에서 확인한 원격 브랜치 위치
```

둘은 같은 ref가 아닙니다. 로컬 브랜치에서 커밋을 만들어도 push하기 전에는 원격 브랜치가 이동하지 않습니다.

### `fetch`, `pull`, `push`

| 명령 | 주된 동작 | 현재 작업 트리 |
| --- | --- | --- |
| `git fetch` | 원격 객체와 `origin/*` 갱신 | 자동 통합하지 않음 |
| `git pull` | fetch 뒤 merge, rebase 또는 fast-forward | 설정에 따라 바뀔 수 있음 |
| `git push` | 로컬 ref와 객체를 원격에 게시 | 원격 저장소가 거부할 수 있음 |

상태가 불확실하면 `pull`부터 실행하지 않고 `fetch`한 뒤 그래프를 읽습니다.

## 최신 기준 브랜치에서 브랜치 만들기

```bash
git fetch origin
git switch --no-track -c feature/add-priority origin/main
```

작업과 검증을 마친 뒤 최초 push에서 같은 이름의 원격 브랜치를 만들고 upstream을 설정합니다.

```bash
git push -u origin HEAD
```

확인합니다.

```bash
git status --short --branch
git branch -vv
git log -1 --oneline --decorate
```

이제 로컬 브랜치의 기본 비교·push 대상은 `origin/feature/add-priority`입니다. 시작점이었던 `origin/main`과 역할이 다릅니다.

## 다른 복제본이 변경을 보는 시점

개발자 A가 push해도 개발자 B의 복제본은 자동으로 갱신되지 않습니다.

```text
A의 push
→ 원격 브랜치 이동
→ B의 로컬 저장소는 그대로
→ B의 fetch
→ B의 origin/* 갱신
```

B에서 비교합니다.

```bash
git branch -r
git log --oneline --decorate --all -12

git fetch origin

git branch -r
git log --oneline --decorate --all -12
```

## Pull Request가 나타내는 관계

Pull Request는 한 브랜치의 변경을 다른 브랜치에 통합하자는 제안입니다.

```text
base: main
head: feature/add-priority
```

PR을 만들기 전에 로컬에서 범위를 확인합니다.

```bash
git fetch origin
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

`...` 비교는 두 브랜치의 merge base부터 head까지의 변경을 확인할 때 사용합니다.

다음을 점검합니다.

- base와 head 방향이 맞는가?
- 관련 없는 커밋이나 파일이 섞이지 않았는가?
- 생성 파일, 비밀값과 개인 설정이 없는가?
- 프로젝트 테스트가 통과하는가?
- 설명한 변경 범위와 diff가 일치하는가?

## Pull Request 본문

본문은 diff를 다시 나열하는 대신 이유와 검증 근거를 기록합니다.

```markdown
## 변경

- 작업 스키마에 `priority` 필드를 추가했습니다.

## 이유

- 우선순위를 저장할 필드가 없어 정렬 기준을 유지할 수 없었습니다.

## 검증

- `./scripts/check.sh`
- 기존 필수 필드 유지 확인
- 중복 필드 없음 확인

## 범위 밖

- `priority` 값의 enum과 UI 표시는 포함하지 않았습니다.
```

좋은 본문은 리뷰어가 다음을 빠르게 판단하게 합니다.

- 왜 필요한가?
- 어디까지 바뀌는가?
- 어떤 명령으로 확인했는가?
- 의도적으로 제외한 것은 무엇인가?

## Draft Pull Request

구현이 끝나기 전에 방향과 위험을 공유해야 하면 Draft를 사용할 수 있습니다. Draft는 검증되지 않은 변경을 merge해 달라는 뜻이 아닙니다. 정식 리뷰를 요청하기 전에는 다음을 마칩니다.

```text
[ ] diff 범위 확인
[ ] 테스트 실행
[ ] 문서와 마이그레이션 등 관련 파일 포함
[ ] 알려진 문제 기록
[ ] 리뷰어가 확인할 지점 명시
```

## 리뷰 의견 반영

리뷰 수정도 일반 변경과 같은 절차를 사용합니다.

```bash
# 파일 수정
./scripts/check.sh
git diff
git add -p
git diff --staged
git commit -m "fix: address schema review"
git push
```

게시한 커밋을 `amend`하거나 대화형 rebase로 고치면 해시가 바뀝니다. 리뷰어가 이미 확인 중인 브랜치를 다시 쓰기 전에 팀 규칙과 시점을 확인합니다.

## CI 실패 조사

CI 실패를 모두 “GitHub 문제”로 묶지 않습니다. 먼저 실패한 워크플로, `job`, `step`과 명령을 찾습니다.

가능한 원인:

- 내 변경으로 재현되는 테스트 실패
- 지원하지 않는 실행 환경 또는 OS 차이
- 의존성 설치 실패
- 간헐적으로 실패하는 테스트
- 토큰 또는 비밀값 권한 부족
- 기준 브랜치 변경으로 생긴 충돌
- 워크플로 YAML 오류

조사 순서:

```text
실패한 `job`과 `step` 확인
→ 실제 명령과 종료 상태 확인
→ 같은 명령을 로컬에서 실행
→ 내 변경과 기준 브랜치 상태 비교
→ 원인 수정
→ 로컬 검증
→ push 뒤 새 워크플로 실행 확인
```

단순 재실행으로 통과했다면 간헐적 실패 가능성을 기록합니다. 원인을 모른 채 재실행만 반복하지 않습니다.

## 비선형 push 거부

원격 브랜치에 로컬에 없는 커밋이 있으면 일반 push가 거부됩니다.

```bash
git push
```

실패 뒤 바로 강제 push하지 않습니다.

```bash
git fetch origin
git status --short --branch
git log --oneline --decorate --graph --all -15
```

원격 커밋을 보존해야 하면 팀 규칙에 따라 merge하거나, 아직 게시하지 않은 로컬 커밋만 원격 위로 rebase합니다.

```bash
git merge origin/feature/add-priority
```

또는:

```bash
git rebase origin/feature/add-priority
```

이미 게시한 커밋을 rebase했다면 `--force-with-lease`가 필요할 수 있습니다. 해당 조건은 다음 문서에서 다룹니다.

## 병합 뒤 정리

Pull Request가 병합된 뒤 원격 정보를 정리합니다.

```bash
git fetch --prune origin
git switch main
git merge --ff-only origin/main
git branch -d feature/add-priority
```

`git branch -d`가 거부되면 무조건 `-D`를 사용하지 않습니다.

```bash
git branch --contains feature/add-priority
git log --oneline --decorate --graph --all -15
```

squash merge에서는 작업 브랜치의 원래 커밋이 `main`에 그대로 들어가지 않으므로 `-d`가 거부될 수 있습니다. PR 병합 여부와 보존할 로컬 작업이 없는지 확인한 뒤 삭제합니다.

## `local-git-lab`에서 여러 복제본 비교하기

```bash
cd exercises/local-git-lab
./git-lab.sh --reset team
```

생성된 복제본:

```text
lab/team-app-dev-a
lab/team-app-dev-b
lab/team-app-maintainer
```

각 상태를 비교합니다.

```bash
git -C lab/team-app-dev-a branch -vv
git -C lab/team-app-dev-b branch -vv
git -C lab/team-app-maintainer branch -vv

git -C lab/team-app-dev-a log --oneline --decorate --graph --all
git -C lab/team-app-dev-b log --oneline --decorate --graph --all
git -C lab/team-app-maintainer log --oneline --decorate --graph --all
```

다음을 설명합니다.

- 개발자 A와 B는 같은 원격 저장소를 사용하지만 현재 브랜치가 다릅니다.
- `feature/add-priority`는 `main`에 병합됐습니다.
- `feature/add-assignee`는 이전 `main`에서 분기된 상태입니다.
- 각 복제본의 `origin/*`는 마지막 fetch 시점에 따라 달라질 수 있습니다.

## 표준 협업 절차

```bash
git fetch origin
git switch --no-track -c feature/TOPIC origin/main

# 작업과 검토
git status --short
git diff
git add -p
git diff --staged --check
git diff --staged
./scripts/check.sh
git commit

# 게시와 PR 범위 확인
git push -u origin HEAD
git log --oneline origin/main..HEAD
git diff origin/main...HEAD

# 리뷰 반영
git push

# 병합 뒤 정리
git fetch --prune origin
git switch main
git merge --ff-only origin/main
```

## 완료 기준

- 로컬 브랜치, 원격 브랜치와 원격 추적 브랜치를 구분합니다.
- 최초 push로 upstream을 설정합니다.
- Pull Request의 base, head와 merge base를 기준으로 한 diff를 확인합니다.
- 리뷰와 CI 실패를 재현 가능한 근거와 함께 처리합니다.
- non-fast-forward 거부 뒤 원격 그래프를 먼저 확인합니다.
