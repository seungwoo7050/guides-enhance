# Local Git Lab

## 개요

Local Git Lab은 외부 호스팅 서비스 없이 여러 Git 저장소와 bare 원격 저장소를 한 번에 만드는 Bash 도구입니다. 생성된 `lab/`에서는 브랜치 게시, 여러 복제본의 원격 추적 ref, 병합된 변경, rebase 충돌, reset, detached `HEAD`, revert와 stash를 실제 Git 상태로 확인할 수 있습니다.

완성된 프로그램은 `git-lab.sh`입니다. `lab/` 아래 저장소는 실행할 때 생성되는 검사 대상이므로 배포 파일에는 포함하지 않습니다.

## 주요 기능

- `sample`, `team`, `recovery` 구성을 따로 만들거나 초기화합니다.
- 생성 모드에서는 이미 있는 대상을 덮어쓰지 않습니다.
- 기존 `lab/`을 직접 수정하지 않고 인접한 준비 디렉터리에서 결과를 완성합니다.
- 디렉터리 생성의 원자성을 이용해 동시 실행을 차단합니다.
- `lab/`이 심볼릭 링크이거나 디렉터리가 아니면 실행을 거부합니다.
- 삭제 가능한 경로를 고정해 `lab/` 밖의 파일을 지우지 않습니다.
- 각 저장소의 작성자 정보, 서명 여부, `core.autocrlf`, 파일 프로토콜과 hooks 경로를 저장소별로 고정합니다.
- 최종 교체 직전에 대상 경로가 새로 생기거나 기존 inode가 바뀌면 교체를 거부합니다.
- 프로젝트 자체 테스트로 중단 처리, 경쟁 상태, 실제 충돌과 복구 상태를 확인합니다.

## 요구 사항

- Bash 3.2 이상
- Git 2.23 이상
- Python 3.8 이상
- POSIX 기본 명령
- Linux 또는 macOS

최종 디렉터리 교체에는 Linux의 `renameat2` 또는 macOS의 `renamex_np`가 필요합니다. 현재 파일 시스템이나 운영체제가 필요한 rename 플래그를 지원하지 않으면 준비한 결과는 최종 경로로 교체되지 않고 기존 `lab/`은 그대로 남습니다.

## 사용법

전체 구성을 만듭니다.

```bash
./git-lab.sh
```

필요한 대상만 만들 수도 있습니다.

```bash
./git-lab.sh sample
./git-lab.sh team
./git-lab.sh recovery
```

생성 모드는 기존 대상을 덮어쓰지 않습니다. 현재 상태를 폐기해도 될 때만 `--reset`을 사용합니다.

```bash
./git-lab.sh --reset sample
./git-lab.sh --reset team
./git-lab.sh --reset recovery
./git-lab.sh --reset all
```

## 생성 결과

```text
lab/
├── .empty-hooks/
├── remotes/
│   ├── sample-app.git/
│   └── team-app.git/
├── sample-app/
├── team-app-dev-a/
├── team-app-dev-b/
├── team-app-maintainer/
└── recovery-lab/
```

`lab/`은 실행 결과이므로 `.gitignore`에 포함됩니다.

## `sample`

`sample-app.git` bare 원격 저장소와 복제본 하나를 만듭니다. 저장소에는 3자 이상 60자 이하의 작업 제목만 허용하는 POSIX 셸 도구와 실행 가능한 테스트가 커밋되어 있습니다.

```bash
./lab/sample-app/scripts/test.sh
git -C ./lab/sample-app status --short --branch
git -C ./lab/sample-app branch -vv
```

작업 트리, 인덱스, `HEAD`, 로컬 브랜치와 `origin/main`을 확인하거나 별도 작업 브랜치를 만들어 커밋 실습에 사용할 수 있습니다.

## `team`

bare 원격 저장소 하나와 복제본 세 개를 만듭니다.

```text
team-app-dev-a          feature/add-priority
team-app-dev-b          feature/add-assignee
team-app-maintainer     main
```

`feature/add-priority`는 merge 커밋으로 `main`에 반영되어 있습니다. `feature/add-assignee`는 이전 `main`에서 분기했으므로 개발자 B 복제본을 최신 `origin/main` 위로 rebase하면 같은 YAML 위치에서 충돌합니다.

```bash
./lab/team-app-dev-a/scripts/check.sh
./lab/team-app-dev-b/scripts/check.sh
./lab/team-app-maintainer/scripts/check.sh

git -C ./lab/team-app-dev-b \
  log --oneline --decorate --graph --all
```

각 복제본의 `scripts/check.sh`는 다음을 검사합니다.

- 최상위 `fields:` 항목 존재
- 충돌 표시 부재
- `title`, `status` 필드 존재
- 같은 필드 중복 부재

## `recovery`

`recovery-lab`에는 다음 상태가 준비되어 있습니다.

- `reset --hard` 뒤 `recovery/reset` 브랜치로 보존한 커밋
- detached `HEAD`에서 만든 뒤 `recovery/detached` 브랜치로 보존한 커밋
- 이전 tree 객체를 되살리는 change/revert 커밋 쌍
- 추적·미추적 변경을 함께 넣은 `stash@{0}`

```bash
git -C ./lab/recovery-lab \
  show recovery/reset:reset.txt

git -C ./lab/recovery-lab \
  show recovery/detached:detached.txt

git -C ./lab/recovery-lab stash list
```

## 완성한 `lab/`을 교체하는 방식

`git-lab.sh`는 최종 `lab/` 안에서 구성을 직접 다시 만들지 않습니다.

```text
잠금 디렉터리 생성
→ 기존 `lab/`이 있으면 device/inode 기록
→ 인접한 준비 디렉터리에 기존 상태 복사
→ 선택한 구성만 다시 생성
→ 교체 직전 대상 경로 확인
→ 원자적 rename 또는 exchange
→ 이전 디렉터리와 잠금 디렉터리 제거
```

처음 생성할 때는 대상 경로가 없어야만 성공하는 rename을 사용합니다. 기존 `lab/`을 바꿀 때는 작업 시작 시 기록한 device/inode와 교체 직전 값을 비교한 뒤 원자적 exchange를 수행합니다.

다음 상황에서는 기존 결과를 보존한 채 실패합니다.

- 다른 프로세스가 잠금 디렉터리를 가지고 있음
- 시그널로 생성이 중단됨
- 교체 직전에 다른 프로세스가 `lab/`을 만듦
- 기존 `lab/`이 다른 inode로 교체됨
- 운영체제나 파일 시스템이 필요한 원자적 rename을 지원하지 않음

남아 있는 `.lab.lock/`은 실행 중인 프로세스가 없다는 사실을 확인한 뒤 수동으로 제거해야 합니다. 자동 삭제하면 느리게 실행 중인 정상 프로세스의 잠금 디렉터리를 지울 수 있습니다.

## 검증

```bash
./tests/test_git_lab.sh
```

테스트는 프로젝트를 임시 디렉터리로 복사한 뒤 다음을 확인합니다.

- Bash 문법과 잘못된 명령행 입력의 종료 상태
- 동시 실행 거부와 시그널 뒤 임시 파일 정리
- 처음 결과를 게시할 때 기존 대상 경로를 덮어쓰지 않음
- 심볼릭 링크인 `lab/` 거부
- 생성된 모든 저장소의 변경이 없는 상태와 로컬 Git 설정
- 두 작업 브랜치 사이의 실제 rebase 충돌
- reset, detached `HEAD`, revert와 stash 상태
- `sample`, `team`, `recovery` reset이 다른 대상을 바꾸지 않음
- 대상 경로의 inode가 바뀌면 교체를 거부함
- 사용자의 전역 Git 설정을 수정하지 않음

## 주요 선택

- **인접한 준비 디렉터리:** 최종 디렉터리와 같은 파일 시스템에 두어 원자적 rename 조건을 유지합니다.
- **잠금 디렉터리:** 잠금 소유자 정보를 기록·해석하지 않고 `mkdir` 성공 여부로 한 프로세스만 진입시킵니다.
- **고정된 삭제 목록:** reset 대상 이름을 계산하더라도 허용한 경로만 삭제합니다.
- **로컬 bare 원격 저장소:** 네트워크와 인증 정보 없이 복제본, fetch, push와 non-fast-forward 상태를 만듭니다.
- **빈 Git hooks 디렉터리:** 사용자의 전역 Git hook이 생성 과정에 개입하지 않도록 각 저장소에 로컬 hooks 경로를 설정합니다.
- **복제본 경로 수정:** 준비 디렉터리에서 만든 복제본의 `origin`과 hooks 경로를 최종 `lab/` 기준으로 바꿉니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | CLI argument parsing and topology selection | `git-lab.sh` |
| 2 | Runtime prerequisite and lab path validation | `git-lab.sh` |
| 3 | Lock, temporary lab copy, and cleanup | `git-lab.sh` |
| 4 | Per-repository Git configuration | `git-lab.sh` |
| 5 | Sample repository and bare remote generation | `git-lab.sh` |
| 6 | Divergent team repository graph generation | `git-lab.sh` |
| 7 | Recovery refs, revert, and stash generation | `git-lab.sh` |
| 8 | Atomic lab publication | `git-lab.sh` |
| 8-1 | Exclusive first publication | `git-lab.sh` |
| 8-2 | Destination-identity-checked exchange | `git-lab.sh` |
| 9 | Requested topology execution and finalization | `git-lab.sh` |
| 10 | Standalone behavior and failure verification | `tests/test_git_lab.sh` |

## 제한

- Pull Request 화면, 리뷰 승인, 브랜치 보호 규칙, GitHub Actions, 조직 권한과 fork 네트워크는 재현하지 않습니다.
- `team`은 충돌을 명확히 확인하기 위해 작은 YAML 파일 하나를 사용합니다.
- `--reset`은 선택한 구성의 커밋, 브랜치, reflog, stash와 미추적 파일을 폐기합니다.
- 생성 시각과 커밋 SHA는 실행할 때마다 달라질 수 있지만 브랜치 관계와 검사 조건은 같습니다.
