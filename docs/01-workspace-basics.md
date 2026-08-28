# 작업을 시작하기 전 Git 상태 확인

## 목표

코드를 고치기 전에 현재 저장소와 기준점을 확인합니다. 이 문서를 마치면 다음 질문에 명령으로 답할 수 있어야 합니다.

- 지금 어느 저장소에 있습니까?
- 커밋 작성자 이름과 이메일은 무엇입니까?
- 어느 원격 저장소와 연결되어 있습니까?
- 현재 브랜치와 upstream은 무엇입니까?
- `origin/main`은 언제 갱신됐습니까?
- 작업 트리에 다른 작업이 남아 있습니까?
- 새 작업 브랜치는 어느 커밋에서 시작합니까?

## 먼저 구분할 상태

### 작업 트리, 인덱스와 `HEAD`

```text
작업 트리     현재 디렉터리의 파일
인덱스        다음 커밋에 넣기로 선택한 파일 상태
HEAD          현재 체크아웃한 커밋
```

파일을 수정해도 인덱스와 `HEAD`는 즉시 바뀌지 않습니다.

```text
파일 수정
→ 작업 트리만 변경
→ git add
→ 인덱스 변경
→ git commit
→ 새 커밋 생성, 현재 브랜치 이동
```

### 로컬 브랜치와 원격 추적 브랜치

```text
main          현재 컴퓨터의 로컬 브랜치
origin/main   마지막 fetch에서 확인한 원격 `main`의 로컬 기록
```

`origin/main`은 서버를 실시간으로 읽는 이름이 아닙니다. 다른 사람이 원격 `main`을 갱신해도 내가 `fetch`하기 전까지는 이전 위치를 가리킬 수 있습니다.

### `HEAD`

보통 `HEAD`는 현재 브랜치를 통해 커밋을 가리킵니다.

```text
HEAD → feature/title-check → 커밋 C
```

새 커밋을 만들면 `feature/title-check`가 앞으로 이동합니다.

### 작성자 정보와 인증 계정

둘은 별개입니다.

```text
user.name, user.email
→ 커밋에 기록될 작성자 정보

HTTPS 인증 정보, SSH 키, SSO
→ 원격 저장소 접근 권한을 증명하는 인증 정보
```

원격 저장소에 push할 수 있다고 작성자 정보까지 올바른 것은 아닙니다.

## 팀에서 먼저 확인할 사항

다음 항목은 Git 기능이 아니라 저장소 운영 규칙입니다.

- 저장소 URL과 기본 브랜치 이름
- 조직 저장소에 직접 push하는지, fork를 사용하는지
- 브랜치 이름 규칙
- 회사 이메일 또는 noreply 이메일 사용 여부
- HTTPS, SSH, SSO 중 사용할 인증 방식
- 작업 브랜치의 강제 push 허용 여부
- Pull Request에 필요한 리뷰와 CI 검사

모르면 추측하지 말고 저장소의 `README`, `CONTRIBUTING`, 브랜치 규칙을 확인합니다.

## 현재 저장소 확인

다음 명령은 파일을 바꾸지 않습니다.

```bash
git rev-parse --show-toplevel
git status --short --branch
git branch --show-current
git branch -vv
git remote -v
git log -1 --oneline --decorate
```

### 저장소 루트

```bash
git rev-parse --show-toplevel
```

여러 복제본과 터미널을 함께 사용할 때 디렉터리 이름만 믿지 않습니다. 출력 경로가 작업하려던 저장소인지 확인합니다.

### 작성자 정보

```bash
git config --show-origin --get user.name
git config --show-origin --get user.email
```

회사와 개인 저장소를 같은 컴퓨터에서 사용한다면 저장소마다 작성자 정보를 따로 설정해 계정이 섞이는 일을 줄입니다.

```bash
git config --local user.name "Seungwoo Kim"
git config --local user.email "name@example.com"
```

`--show-origin`은 값을 어느 설정 파일에서 읽었는지도 보여 줍니다.

### 원격 URL

```bash
git remote -v
```

다음을 확인합니다.

- 소유자와 저장소 이름
- 회사 Git 호스트인지 공개 GitHub인지
- fetch URL과 push URL이 의도한 대상인지
- HTTPS 또는 SSH 방식이 팀 안내와 같은지

URL을 고칠 때는 먼저 올바른 값을 확인합니다.

```bash
git remote set-url origin CORRECT_URL
```

### 작업 트리와 브랜치

```bash
git status --short --branch
git branch -vv
```

변경이 없는 예:

```text
## main...origin/main
* main abc1234 [origin/main] chore: baseline
```

변경이 있는 예:

```text
## main...origin/main
 M config/app.yml
?? notes/debug.txt
```

예상하지 못한 변경이 있으면 바로 `restore`, `clean`, 커밋을 실행하지 않습니다. 누가 만든 파일인지, 보존해야 하는지부터 확인합니다.

## `fetch`가 바꾸는 것

실행 전에 결과를 예상합니다.

```text
git fetch origin
```

- 원격의 새 Git 객체를 내려받을 수 있습니다.
- `origin/*` 같은 원격 추적 ref를 갱신할 수 있습니다.
- 현재 로컬 브랜치를 자동으로 이동하지 않습니다.
- 작업 트리 파일을 원격 버전으로 자동 교체하지 않습니다.

실행 뒤 비교합니다.

```bash
git fetch origin
git status --short --branch
git branch -vv
git log --oneline --decorate --graph --all -12
```

불확실할 때 `pull`부터 실행하지 않는 이유가 여기에 있습니다. `pull`은 fetch 뒤 merge 또는 rebase까지 수행할 수 있지만, `fetch`는 먼저 차이를 읽을 기회를 줍니다.

## 최신 기준점에서 작업 브랜치 만들기

원격 정보를 갱신한 뒤 새 브랜치의 시작점을 명시합니다.

```bash
git fetch origin
git switch --no-track -c feature/title-check origin/main
```

이 명령 직후의 상태는 다음과 같습니다.

```text
HEAD → feature/title-check
feature/title-check와 origin/main은 같은 커밋을 가리킴
feature/title-check의 upstream은 아직 없음
작업 트리는 변경 없음
```

`origin/main`은 시작점이지 새 작업 브랜치의 upstream이 아닙니다. 최초 push에서 같은 이름의 원격 브랜치를 만들고 연결합니다.

```bash
git push -u origin HEAD
```

## `local-git-lab`에서 확인하기

저장소 루트에서 실행합니다.

```bash
cd exercises/local-git-lab
./git-lab.sh sample
```

생성된 복제본을 확인합니다.

```bash
git -C lab/sample-app status --short --branch
git -C lab/sample-app branch -vv
git -C lab/sample-app remote -v
git -C lab/sample-app log -1 --oneline --decorate
```

직접 브랜치를 만들어 봅니다.

```bash
git -C lab/sample-app fetch origin
git -C lab/sample-app switch --no-track \
  -c feature/local-check \
  origin/main

git -C lab/sample-app branch -vv
```

실습 상태를 버려도 될 때만 다시 만듭니다.

```bash
./git-lab.sh --reset sample
```

## 작업 시작 점검표

```text
[ ] 올바른 저장소 루트인가?
[ ] 작성자 이름과 이메일이 맞는가?
[ ] 원격 저장소 URL이 맞는가?
[ ] fetch 뒤 최신 기준점을 확인했는가?
[ ] 작업 트리에 보존할 변경이 없는가?
[ ] 새 브랜치의 시작 커밋이 맞는가?
[ ] 브랜치 이름이 팀 규칙에 맞는가?
```

## 완료 기준

- 작업 트리, 인덱스, `HEAD`를 구분해 설명합니다.
- 로컬 브랜치와 `origin/main`의 차이를 설명합니다.
- `fetch` 전후 어느 ref가 바뀌는지 확인합니다.
- 최신 `origin/main`에서 upstream 없는 작업 브랜치를 만들 수 있습니다.
- 파일을 수정하기 전 저장소, 원격 저장소, 작성자 정보와 작업 트리에 남은 변경을 확인합니다.
