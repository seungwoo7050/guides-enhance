# 다중 저장소 빌드와 릴리스 명세

## 목표

여러 저장소의 코드와 산출물이 한 시스템을 구성할 때, 어떤 조합을 검증하고 배포했는지 고정합니다. 개발 중인 작업 디렉터리와 릴리스 검증 환경도 분리합니다.

이 문서는 분산 서비스의 필수 학습 경로가 아니라 릴리스 엔지니어링 심화 자료입니다.

## 최신 branch를 차례로 빌드하면 같은 릴리스를 만들 수 없습니다

다음 정보만으로는 검증한 조합을 다시 찾기 어렵습니다.

```text
reservation-service: v1.4.0
inventory-service: main
contract-library: 2.3
```

`main`은 계속 이동합니다. tag를 다시 만들 수도 있고, 로컬 dependency cache에 예상하지 않은 library가 남아 있을 수도 있습니다. 저장소마다 빌드하는 사이에 다른 commit이 들어오면 처음과 끝이 서로 다른 시점의 코드가 됩니다.

## 움직이지 않는 식별자를 기록합니다

릴리스 명세에는 필요에 따라 다음 값을 넣습니다.

- 저장소 이름과 검증한 remote URL
- 전체 commit SHA
- annotated tag와 이를 peel한 commit
- API 또는 schema version
- build tool과 주요 runtime version
- build artifact digest
- container image digest
- 적용할 migration 목록
- 생성 시각과 검증 실행 ID

version과 tag는 사람이 읽기 편한 이름입니다. 실제로 고정할 값은 commit과 digest입니다.

## clean detached HEAD에서 검증합니다

개발 작업 디렉터리에는 수정 파일, 미추적 파일과 local build 결과가 섞일 수 있습니다. 릴리스 검증은 별도 checkout에서 수행합니다.

```text
manifest 읽기
→ 저장소별 지정 commit checkout
→ detached HEAD 확인
→ tracked·untracked 변경 없음 확인
→ build와 test 실행
→ 산출물 digest 기록
→ build 뒤 source tree가 바뀌지 않았는지 확인
```

build가 추적 파일을 바꾼다면 같은 source에서 같은 결과를 만들기 어렵습니다. 생성 파일은 source tree 밖이나 ignore된 디렉터리에 저장합니다.

## 저장소 조합도 검사합니다

각 저장소의 test가 따로 통과해도 조합이 맞지 않을 수 있습니다.

- producer와 consumer의 event version
- DB migration과 이전 application version
- 새 service와 이전 gateway 설정
- channel과 schema registry 설정
- image와 environment variable 이름
- rollback할 application이 새 schema를 읽을 수 있는지

manifest는 저장소 목록이 아니라 실제로 함께 검증한 버전 조합입니다.

## 배포와 rollback도 같은 명세를 사용합니다

배포 도구가 `latest`나 branch 이름을 다시 해석하면 검증한 것과 다른 image를 실행할 수 있습니다. 배포에는 manifest에 기록한 image digest를 사용합니다.

rollback은 이전 manifest를 선택해야 합니다. migration을 되돌릴 수 없다면 이전 application이 변경된 DB schema에서 동작하는지도 사전에 확인합니다.

## 흔한 잘못

- branch 이름이나 이동할 수 있는 tag만 기록합니다.
- lightweight tag를 annotated tag와 같은 검증 자료로 사용합니다.
- 개발 중인 worktree에서 릴리스 build를 실행합니다.
- build 전 상태만 확인하고 build 뒤 source 변경은 보지 않습니다.
- 공통 library를 local Maven cache에서 임의로 가져옵니다.
- artifact 이름만 기록하고 digest를 남기지 않습니다.
- rollback할 application과 migration의 호환성을 검사하지 않습니다.

## 검증 방법

릴리스 검사기는 다음 상태를 이유와 함께 거절해야 합니다.

- 같은 저장소 이름이나 경로가 manifest에 두 번 들어 있습니다.
- 현재 HEAD가 지정 commit과 다릅니다.
- branch가 checkout되어 있습니다.
- tracked 또는 untracked 변경이 있습니다.
- tag가 annotated tag가 아닙니다.
- tag를 peel한 commit이 manifest와 다릅니다.
- `origin` remote가 manifest와 다릅니다.

## 관련 프로젝트

[`release-manifest`](../../exercises/release-manifest/)는 임시 Git 저장소를 만들어 remote, clean detached HEAD, commit과 annotated tag를 검사합니다.

## 완료 기준

- 여러 저장소의 한 릴리스를 commit과 digest로 고정할 수 있습니다.
- 개발 worktree와 릴리스 검증 checkout을 분리할 수 있습니다.
- 저장소별 test와 저장소 조합 검증의 차이를 설명할 수 있습니다.
- 모호한 branch, tag와 dirty tree를 자동으로 거절할 수 있습니다.
