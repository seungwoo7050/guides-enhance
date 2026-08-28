# 오픈소스에 작은 변경 기여하기

이 문서는 선택 과정입니다. 필수 Git 협업과 GitHub Actions CI를 마친 뒤, fork 기반으로 외부 프로젝트에 변경을 제안할 때 사용합니다.

## 목표

- 원본 저장소와 자신의 fork를 구분합니다.
- 프로젝트가 요구하는 기여 절차와 검증 명령을 먼저 확인합니다.
- 리뷰어가 이해하고 되돌리기 쉬운 작은 변경을 제안합니다.
- CLA, DCO sign-off와 커밋 서명을 구분합니다.

## 수정하기 전에 읽을 파일

저장소 루트와 `.github/`에서 다음 파일을 확인합니다.

```text
README.md
CONTRIBUTING.md
SECURITY.md
CODE_OF_CONDUCT.md
LICENSE 또는 LICENSE.md
Issue 템플릿
Pull Request 템플릿
```

| 파일 | 확인할 내용 |
| --- | --- |
| README | 프로젝트 목적, 지원 범위, 빌드와 테스트 |
| CONTRIBUTING | 이슈, 브랜치, 커밋, PR 규칙 |
| SECURITY | 취약점의 비공개 신고 방법 |
| Code of Conduct | 커뮤니티 행동 기준 |
| LICENSE | 코드와 문서를 사용할 조건 |
| 템플릿 | 유지관리자가 요구하는 재현·검증 정보 |

`CONTRIBUTING.md`가 없으면 최근 병합된 Pull Request, CI 설정과 릴리스 방식을 확인합니다. 큰 변경을 임의로 시작하지 않습니다.

보안 취약점이나 비밀값을 발견했다면 공개 이슈나 PR에 먼저 올리지 않습니다. `SECURITY.md`의 비공개 신고 절차를 사용합니다.

## 첫 기여 범위 고르기

적절한 후보:

- 재현 가능한 작은 버그
- 명백한 문서 오류와 깨진 링크
- 기존 동작을 고정하는 작은 테스트
- 유지관리자가 표시한 `good first issue`
- 공개 API를 바꾸지 않는 국소적 정리

먼저 논의할 후보:

- 공개 API나 데이터 형식 변경
- 의존성 또는 빌드 시스템 교체
- 대규모 서식 변경과 이름 변경
- 새 설계나 주요 기능
- 지원 플랫폼 변경

작업 전에 확인합니다.

```text
같은 이슈가 이미 있는가?
누군가 작업 중인가?
유지관리자가 원하는 해결 방향이 있는가?
PR 전에 설계 논의를 요구하는가?
재현 절차와 완료 기준이 있는가?
```

## fork, `origin`, `upstream`

일반적인 관계:

```text
원본 저장소
    ↑ upstream
로컬 복제본
    ↓ origin
내 fork
```

- `origin`: 내가 push할 fork
- `upstream`: 변경을 가져올 원본 저장소

자신의 fork를 복제하고 원본을 추가합니다.

```bash
git clone https://github.com/YOUR_ACCOUNT/REPOSITORY.git
cd REPOSITORY
git remote add upstream \
  https://github.com/ORIGINAL_OWNER/REPOSITORY.git
```

확인합니다.

```bash
git remote -v
git branch -vv
git status --short --branch
```

## 최신 upstream에서 브랜치 만들기

```bash
git fetch upstream
git switch --no-track \
  -c fix/documentation-link \
  upstream/main
```

작업 브랜치의 시작점은 `upstream/main`이지만 upstream은 아직 없습니다. 최초 push에서 자신의 fork에 같은 이름의 브랜치를 만듭니다.

```bash
git push -u origin HEAD
```

## 변경 전 기준 검증

프로젝트가 지정한 설치·빌드·테스트·정적 검사를 변경 전에 실행합니다.

기록할 내용:

```text
운영체제와 주요 도구 버전
실행한 정확한 명령
성공 또는 실패 결과
기존 실패가 있는지
```

기준 상태가 이미 실패하면 자신의 변경이 만든 실패와 구분해 이슈나 PR에 적습니다. 원래 작업과 관계없는 기존 실패를 같은 PR에서 고치지 않습니다.

## 작은 변경 만들기

- 합의한 문제만 수정합니다.
- 관련 없는 서식 변경과 이름 변경을 섞지 않습니다.
- 기존 코드 스타일과 테스트 위치를 따릅니다.
- 동작 변경에는 가능한 범위의 테스트를 추가합니다.
- 생성 파일은 프로젝트 절차가 요구할 때만 갱신합니다.
- 필요한 문서와 마이그레이션을 PR을 작게 보이게 하려고 빼지 않습니다.

커밋 전:

```bash
git status --short
git diff
git add -p
git diff --staged --check
git diff --staged
# 프로젝트 검사
git commit
```

## CLA, DCO와 커밋 서명

서로 다른 절차입니다.

### CLA

Contributor License Agreement입니다. 별도 웹 서비스나 봇에서 동의를 요구할 수 있습니다.

### DCO와 sign-off

DCO를 사용하는 프로젝트는 커밋 trailer를 요구할 수 있습니다.

```bash
git commit -s
```

`-s`는 암호학적 서명이 아닙니다. 현재 작성자 정보로 DCO 취지에 동의한다는 `Signed-off-by` trailer를 추가합니다.

### GPG 또는 SSH 서명

```bash
git commit -S
```

커밋 객체에 암호학적 서명을 추가합니다. CLA, DCO와 대체 관계가 아닙니다.

## Pull Request 방향 확인

fork에서 원본으로 PR을 만들 때 네 항목을 확인합니다.

```text
base 저장소: original-owner/repository
base 브랜치: main
head 저장소: your-account/repository
비교 브랜치: fix/documentation-link
```

본문에는 문제, 변경, 검증과 제외 범위를 적습니다.

```markdown
## 문제

설치 문서의 링크가 이동된 페이지를 가리켜 404가 발생합니다.

## 변경

- 링크를 현재 공식 페이지로 바꿨습니다.
- 주변 문장과 문서 순서는 바꾸지 않았습니다.

## 검증

- 프로젝트의 문서 검사 실행
- 렌더링과 링크 대상 확인

## 범위 밖

- 설치 절차 자체의 재작성은 포함하지 않았습니다.
```

## upstream 변경 반영

```bash
git fetch upstream
```

프로젝트 규칙에 따라 merge 또는 rebase합니다.

```bash
git merge upstream/main
```

또는:

```bash
git rebase upstream/main
```

이미 fork에 게시한 커밋을 rebase했다면 리뷰어와 규칙을 확인한 뒤 `--force-with-lease`를 사용합니다.

## 리뷰 반영

리뷰 요청을 다음처럼 나눕니다.

```text
명백한 결함이나 누락
프로젝트 관례에 따른 요청
설계 선택에 대한 질문이나 대안
```

수정할 때도 일반 검토 절차를 반복합니다.

```bash
git diff
git add -p
git diff --staged
# 프로젝트 검사
git commit
git push
```

질문의 의도를 이해하지 못했으면 임의로 고치지 말고 확인합니다. 합의하지 않는 요청에는 감정적 표현 대신 기술적 근거와 대안을 적습니다.

## 병합 또는 종료 뒤 정리

```bash
git fetch --prune upstream
git switch main
git merge --ff-only upstream/main
git branch -d fix/documentation-link
```

PR이 닫혔지만 병합되지 않았다면 필요한 커밋을 별도 브랜치나 패치 파일로 보존할지 결정합니다. fork 브랜치를 지우기 전에 리뷰 대화와 후속 작업이 남아 있는지 확인합니다.

## 완료 기준

- `origin`과 `upstream` URL을 올바르게 설명합니다.
- 원본의 최신 기준 브랜치에서 작업 브랜치를 만듭니다.
- 기여 규칙과 기준 테스트를 변경 전에 확인합니다.
- 하나의 문제만 다루는 diff와 검증 근거를 제공합니다.
- CLA, DCO sign-off와 커밋 서명을 구분합니다.
- 리뷰와 upstream 변경을 반영한 뒤 브랜치를 정리합니다.
