# 변경을 검토 가능한 커밋으로 만들기

## 목표

수정한 파일을 한꺼번에 커밋하지 않습니다. 변경 목적을 나누고, 다음 커밋에 들어갈 정확한 diff를 확인한 뒤 프로젝트 검사를 실행합니다.

```text
변경 확인
→ 목적 결정
→ 필요한 변경만 스테이징
→ 스테이징한 diff 검토
→ 프로젝트 검사
→ 커밋
→ 결과 재확인
```

## 세 상태를 다시 확인하기

```text
작업 트리     현재 파일 내용
인덱스        다음 커밋에 넣을 파일 상태
HEAD          현재 브랜치의 마지막 커밋
```

비교 명령은 대상이 다릅니다.

```bash
git diff             # 작업 트리와 인덱스
git diff --staged    # 인덱스와 HEAD
git diff HEAD        # 작업 트리 전체와 HEAD
```

`git diff`가 비어 있어도 스테이징한 변경이 남아 있을 수 있습니다. 다음 커밋의 실제 내용은 `git diff --staged`로 확인합니다.

## `git status --short` 읽기

일반적인 출력은 두 칸으로 상태를 표시합니다.

```text
M  src/app.py      인덱스에 수정이 있음
 M README.md       작업 트리에만 수정이 있음
MM config.yml      스테이징한 뒤 다시 수정함
?? notes.txt       아직 추적하지 않는 파일
```

첫째 칸은 인덱스, 둘째 칸은 작업 트리 상태입니다. 축약 코드만 보고 판단이 어렵다면 일반 `git status`와 diff를 함께 봅니다.

## 파일 수가 아니라 변경 목적을 정하기

예를 들어 한 작업 중 다음 변경이 섞였다고 가정합니다.

```text
A. 제목 검증 규칙 변경
B. 관련 테스트 추가
C. README의 제목 설명 수정
D. README의 무관한 오탈자 수정
E. 개인 디버그 메모 생성
```

합리적인 결과는 다음과 같습니다.

```text
커밋 1: 검증 규칙 + 테스트 + 관련 문서
커밋 2: 무관한 오탈자 수정
커밋에서 제외: 개인 디버그 메모
```

한 커밋을 독립적으로 리뷰하거나 되돌려도 한 가지 목적이 유지되어야 합니다.

## 스테이징하기 전 diff 읽기

```bash
git status --short
git diff --stat
git diff
```

확인할 내용:

- 예상한 파일만 바뀌었는가?
- 파일 삭제나 권한 변경이 섞이지 않았는가?
- 생성 파일이나 개인 설정이 들어오지 않았는가?
- 테스트와 문서 변경이 실제 동작 변경과 맞는가?

미추적 파일의 내용은 일반 `git diff`에 나오지 않습니다. `status`에서 찾은 뒤 직접 확인합니다.

## 필요한 변경만 스테이징하기

파일 전체가 같은 목적이면 경로를 명시합니다.

```bash
git add src/validator.py tests/test_validator.py
```

한 파일에 여러 목적이 섞였으면 변경 조각을 선택합니다.

```bash
git add -p README.md
```

자주 쓰는 입력:

```text
y  현재 변경 조각을 스테이징
n  현재 변경 조각을 제외
s  가능한 경우 더 작은 변경 조각으로 분리
q  종료
?  도움말
```

`git add .` 자체가 잘못된 것은 아닙니다. 문제는 포함될 파일과 변경을 확인하지 않고 사용하는 것입니다.

## 잘못 스테이징했을 때

파일 수정은 유지하고 인덱스에서만 내립니다.

```bash
git restore --staged path/to/file
```

전체를 다시 고르려면:

```bash
git restore --staged .
```

`git restore path/to/file`은 작업 트리 수정 자체를 버릴 수 있습니다. `--staged` 유무를 확인합니다.

## 커밋 직전 확인

최소한 다음 세 명령을 실행합니다.

```bash
git status --short
git diff --staged --check
git diff --staged
```

점검할 사항:

```text
[ ] 한 가지 변경 목적만 포함했는가?
[ ] 동작 변경과 관련 테스트가 함께 있는가?
[ ] 관련 문서만 포함했는가?
[ ] 비밀값, 개인 메모와 생성 파일이 없는가?
[ ] 예상하지 못한 삭제나 실행 권한 변경이 없는가?
```

## 프로젝트 검사와 커밋

저장소가 지정한 검사를 실행합니다.

```bash
./scripts/check.sh
```

검사가 성공한 뒤 커밋합니다.

```bash
git commit -m "feat: validate change record title"
```

Git은 `feat:` 같은 형식을 요구하지 않습니다. 저장소가 Conventional Commits를 사용하면 따르고, 별도 규칙이 없으면 결과와 이유가 드러나는 명령형 제목을 사용합니다.

피할 제목:

```text
update files
fix stuff
work in progress
```

결과를 확인합니다.

```bash
git show --stat --oneline HEAD
git show --format=fuller --no-ext-diff HEAD
git status --short
```

## 관련 없는 변경은 별도 커밋으로 분리하기

첫 커밋 뒤 남은 diff를 다시 읽습니다.

```bash
git diff
git status --short
```

남은 변경이 독립된 목적이면 같은 절차를 반복합니다.

```bash
git add README.md
git diff --staged --check
git diff --staged
git commit -m "docs: fix dependency spelling"
```

커밋 수를 줄이려고 관계없는 변경을 묶지 않습니다. 반대로 한 기능을 지나치게 잘게 나눠 각 커밋만 checkout했을 때 프로젝트 검사가 실패하게 만들 필요도 없습니다.

## ignore 위치 선택하기

### 모든 복제본에서 무시할 파일

공통 빌드 결과물이나 도구 캐시는 `.gitignore`에 기록하고 커밋합니다.

```gitignore
build/
__pycache__/
.env.local
```

### 현재 복제본에서만 무시할 파일

개인 메모처럼 공유할 필요가 없는 규칙은 `.git/info/exclude`에 둘 수 있습니다.

```bash
printf '%s\n' 'notes/' >> .git/info/exclude
```

이 파일은 원격에 공유되지 않습니다.

### 이미 추적 중인 파일

`.gitignore`는 이미 추적하는 파일을 자동으로 제거하지 않습니다. 팀이 추적을 중단하기로 합의한 경우 별도 커밋으로 처리합니다.

## 마지막 로컬 커밋 수정하기

아직 push하지 않은 마지막 커밋에 작은 누락이 있다면 `amend`할 수 있습니다.

```bash
# 파일 수정
git add path/to/file
git diff --staged
git commit --amend --no-edit
```

`amend`는 기존 커밋을 내부에서 고치는 명령이 아닙니다. 새 커밋으로 교체하므로 해시가 바뀝니다. 이미 공유한 커밋을 `amend`하면 이력 재작성과 강제 push가 필요합니다.

## `local-git-lab`에서 연습하기

먼저 `sample` 구성을 새로 만듭니다. 기존 상태를 버려도 되는지 확인합니다.

```bash
cd exercises/local-git-lab
./git-lab.sh --reset sample
cd lab/sample-app
```

작업 브랜치를 만듭니다.

```bash
git switch --no-track -c feature/document-title origin/main
```

서로 다른 목적의 변경을 일부러 만듭니다. 첫 번째 변경은 제목 규칙 설명이고, 두 번째 변경은 의존성 문장 보완입니다.

```bash
python3 - <<'PY'
from pathlib import Path

path = Path("README.md")
text = path.read_text(encoding="utf-8")
text = text.replace(
    "이 저장소에는 3자 이상 60자 이하의 작업 제목만 허용하는\n"
    "POSIX 셸 검증 도구가 포함되어 있습니다.",
    "작업 제목은 3자 이상 60자 이하여야 합니다.\n"
    "POSIX 셸 스크립트가 이 규칙을 검사합니다.",
)
text = text.replace(
    "외부 패키지는 필요하지 않습니다.",
    "실행 시 외부 패키지는 필요하지 않습니다.",
)
path.write_text(text, encoding="utf-8")
PY

mkdir -p notes
printf '개인 메모\n' > notes/debug.txt
```

두 README 변경은 서로 떨어진 위치에 있으므로 `git add -p README.md`에서 별도 변경 조각으로 선택할 수 있습니다. 제목 설명과 의존성 문장을 다른 커밋으로 나누고, `notes/debug.txt`는 커밋에서 제외합니다. 각 커밋 전후에 다음을 확인합니다.

```bash
git status --short
git diff
git diff --staged
./scripts/test.sh
git log --oneline origin/main..HEAD
```

문장 두 개가 같은 변경 조각으로 잡히면 파일에서 간격을 늘리거나 직접 편집해 변경을 나눕니다. 목표는 `git add -p` 조작 자체가 아니라 목적별 diff를 만드는 것입니다.

## 표준 절차

```bash
git status --short --branch
git diff

git add path/to/file
git add -p path/to/mixed-file

git diff --staged --check
git diff --staged

./scripts/check.sh
git commit

git show --stat --oneline HEAD
git status --short
```

## 완료 기준

- 작업 트리, 인덱스와 `HEAD`의 차이를 명령 결과로 설명합니다.
- 같은 파일에 섞인 변경을 다른 커밋으로 나눕니다.
- 잘못 스테이징한 변경을 파일 손실 없이 취소합니다.
- 프로젝트 테스트와 스테이징한 diff를 확인한 뒤 커밋합니다.
- 개인 파일을 `.gitignore`와 `.git/info/exclude` 중 알맞은 위치에 둡니다.
