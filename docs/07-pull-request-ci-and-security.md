# Pull Request CI와 GitHub Actions 보안

## 목표

Pull Request에 CI가 보인다는 사실만으로 안전한 협업이 완성되지는 않습니다. 어떤 커밋을 검사했는지, 검사를 병합 조건으로 사용하는지, 워크플로가 신뢰하지 않는 코드에 어떤 권한을 주는지 확인합니다.

```text
브랜치 push
→ Pull Request 갱신
→ 워크플로 실행
→ 검사 결과
→ 실패 조사 또는 리뷰
→ 필수 상태 검사 통과
→ 병합
```

## Pull Request에서 무엇을 검사하는가

`pull_request` 이벤트의 기본 checkout은 GitHub가 만든 merge 커밋을 사용할 수 있습니다. 이는 head 브랜치가 현재 base에 통합되는지 검사하는 데 유용합니다.

실패한 실행에서 다음을 확인합니다.

- 이벤트가 `pull_request`인지 `push`인지
- base와 head 저장소/브랜치
- 워크플로 실행이 가리키는 커밋 SHA
- checkout `step`이 실제로 선택한 ref
- base 브랜치가 실행 사이에 바뀌었는지

“내 브랜치에서는 성공했다”와 “현재 base와 합쳐도 성공한다”는 같은 말이 아닙니다.

## 필수 상태 검사

워크플로가 실행된다는 사실과 병합을 막는다는 사실은 다릅니다. 저장소 ruleset 또는 브랜치 보호 규칙에서 필요한 상태 검사를 병합 조건으로 지정해야 합니다.

확인할 사항:

```text
[ ] 보호할 base 브랜치가 맞는가?
[ ] 필요한 CI `job` 이름을 필수 상태 검사로 지정했는가?
[ ] 브랜치가 최신 base를 포함해야 하는가?
[ ] 리뷰 승인 수가 정해져 있는가?
[ ] 관리자 우회가 허용되는가?
[ ] 강제 push와 브랜치 삭제가 제한되는가?
```

워크플로 `job` 이름을 바꾸면 필수 상태 검사 설정과 맞지 않을 수 있습니다. 이름 변경도 저장소 설정까지 함께 검토합니다.

## CI 실패 처리

### 먼저 분류하기

- 소스 코드 또는 테스트 실패
- 워크플로 문법 오류
- Action 또는 의존성 다운로드 실패
- 실행 환경/OS 차이
- 권한 또는 비밀값 부족
- 간헐적으로 실패하는 테스트
- base 브랜치 변경
- GitHub 서비스 장애

### 조사 순서

```text
실패한 실행의 커밋 확인
→ 실패한 `job`과 `step` 확인
→ 실행 명령과 첫 오류 확인
→ 같은 명령을 로컬에서 실행
→ base와 head의 차이 확인
→ 수정 뒤 로컬 검증
→ push하고 새 실행 확인
```

재실행은 원인을 확인한 뒤 사용합니다. 같은 커밋을 재실행해 통과했다면 간헐적 테스트 실패나 외부 서비스 문제일 수 있습니다. 결과만 통과로 바꾸고 원인을 숨기지 않습니다.

## `GITHUB_TOKEN` 최소 권한

GitHub는 워크플로 실행마다 `GITHUB_TOKEN`을 제공합니다. `job`이 저장소를 checkout하고 테스트만 실행한다면 읽기 권한이면 충분합니다.

```yaml
permissions:
  contents: read
```

이슈 작성, 패키지 게시, Pull Request 댓글 등 쓰기 작업이 필요할 때만 해당 권한을 `job` 단위로 추가합니다.

```yaml
jobs:
  comment:
    permissions:
      contents: read
      pull-requests: write
```

하나의 `job`에 모든 작업을 모아 넓은 권한을 주기보다, 읽기 전용 테스트와 쓰기 작업을 분리합니다.

## 비밀값

비밀값은 워크플로 파일에 직접 기록하지 않습니다.

```yaml
env:
  API_TOKEN: ${{ secrets.API_TOKEN }}
```

주의할 점:

- 비밀값은 로그에 출력하지 않습니다.
- `set -x`, 디버그 출력과 전체 환경 변수 출력에 주의합니다.
- Pull Request의 코드가 비밀값을 읽을 수 있는 `job`에서 실행되는지 확인합니다.
- 사용하지 않는 비밀값은 워크플로에 전달하지 않습니다.
- 노출이 의심되면 먼저 폐기·교체합니다.

자동 마스킹은 보조 수단입니다. 변형된 값이나 인코딩된 값이 항상 가려진다고 가정하지 않습니다.

## fork Pull Request

외부 fork의 Pull Request는 저장소 소유자가 신뢰하지 않는 코드를 포함합니다. 일반적으로 쓰기 토큰과 저장소 비밀값이 제한됩니다.

이 제한을 우회하려고 신뢰하지 않는 코드에 비밀값을 전달하지 않습니다. 통합 테스트에 비밀값이 필요하면 다음을 검토합니다.

- 유지관리자가 승인한 별도 워크플로
- 최소 권한의 테스트용 인증 정보
- 실제 운영 자원과 분리된 환경
- 신뢰하지 않는 코드를 실행하지 않는 API 기반 검사

외부 기여자의 첫 실행에 유지관리자 승인이 필요한 설정도 확인합니다.

## `pull_request`와 `pull_request_target`

### `pull_request`

- Pull Request 코드를 검사하는 일반적인 이벤트입니다.
- fork PR에서는 토큰과 비밀값이 제한됩니다.
- 빌드와 테스트처럼 신뢰하지 않는 코드 실행에 사용합니다.

### `pull_request_target`

- base 저장소의 기본 브랜치 워크플로를 사용합니다.
- 더 높은 권한이나 비밀값에 접근할 수 있는 경우가 있습니다.
- 신뢰하지 않는 head 브랜치를 checkout해 빌드·테스트하면 위험합니다.

다음 조합을 피합니다.

```yaml
on: pull_request_target

steps:
  - uses: actions/checkout@...
    with:
      ref: ${{ github.event.pull_request.head.sha }}
  - run: ./scripts/from-pull-request.sh
```

높은 권한이 있는 context에서 외부 기여자가 수정한 스크립트를 실행할 수 있기 때문입니다.

`pull_request_target`은 label, 댓글처럼 Pull Request 메타데이터를 다루되 head 코드를 실행하지 않는 작업에 제한합니다. 꼭 필요하지 않으면 사용하지 않습니다.

## 외부 Action 고정

외부 Action을 다음처럼 이동할 수 있는 tag로만 참조하면 tag가 다른 커밋으로 바뀔 수 있습니다.

```yaml
uses: vendor/action@v1
```

검토한 전체 커밋 SHA로 고정합니다.

```yaml
uses: vendor/action@0123456789abcdef0123456789abcdef01234567 # v1.2.3
```

검토할 항목:

- 공식 소유자 또는 신뢰할 수 있는 유지관리자인가?
- Marketplace 표시만으로 충분한가?
- Action이 요구하는 토큰과 비밀값은 무엇인가?
- `post` 단계에서 어떤 작업을 하는가?
- 소스 코드와 릴리스 결과물이 일치하는가?
- Dependabot 또는 Renovate 업데이트 PR의 diff와 릴리스 노트를 확인했는가?

버전 주석은 사람이 읽기 위한 정보입니다. 실제 고정 대상은 SHA입니다.

## checkout 인증 정보

테스트만 하는 워크플로에서는 checkout 뒤 Git 인증 정보가 필요하지 않습니다.

```yaml
- uses: actions/checkout@COMMIT_SHA
  with:
    persist-credentials: false
```

이 설정은 이후 `step`이 기본 토큰으로 push하는 것을 막는 데 도움이 됩니다. 실제 push가 필요한 별도 `job`은 최소 권한 토큰과 대상 브랜치를 명시합니다.

## 신뢰하지 않는 값을 셸 명령에 넣지 않기

Pull Request 제목, 브랜치 이름과 이슈 본문은 공격자가 제어할 수 있습니다.

피할 형태:

```yaml
- run: echo "${{ github.event.pull_request.title }}" | tool
```

셸 해석을 거치며 예상하지 못한 문자가 명령으로 해석될 수 있습니다.

환경 변수로 전달한 뒤 프로그램에서 값으로 읽습니다.

```yaml
- name: Check title
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: python scripts/check_title.py
```

프로그램에서도 길이와 허용 형식을 검증합니다.

## 워크플로 변경 리뷰

`.github/workflows/` 변경은 일반 소스 코드보다 낮은 위험의 설정 파일이 아닙니다. 토큰, 비밀값과 runner 명령을 바꿀 수 있는 실행 코드입니다.

리뷰할 때 확인합니다.

```text
[ ] 실행 이벤트 범위가 넓어지지 않았는가?
[ ] 쓰기 권한이 추가되지 않았는가?
[ ] 비밀값 전달 대상이 늘지 않았는가?
[ ] 외부 Action 소유자 또는 SHA가 바뀌지 않았는가?
[ ] 신뢰하지 않는 코드를 높은 권한으로 실행하지 않는가?
[ ] 로컬에서 재현할 수 없는 명령이 추가되지 않았는가?
[ ] 결과물에 민감한 파일이 포함되지 않는가?
```

가능하면 CODEOWNERS나 ruleset으로 워크플로 변경에 지정 리뷰어를 요구합니다.

## 동시 실행 제어와 오래된 결과

같은 Pull Request의 이전 실행이 늦게 끝나 최신 실행과 혼동되지 않도록 concurrency를 사용합니다.

```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```

병합할 때는 최신 head 커밋의 필수 상태 검사가 통과했는지 확인합니다.

## 실제 Pull Request 실습

`exercises/github-actions-ci`를 별도 저장소 또는 연습 브랜치에 게시합니다.

```bash
cd exercises/github-actions-ci
./scripts/check.sh
```

다음 순서로 확인합니다.

1. `main`에서 작업 브랜치를 만듭니다.
2. `src/change_record.py` 또는 테스트를 작게 수정합니다.
3. 로컬 검사를 통과시켜 커밋하고 push합니다.
4. Pull Request를 엽니다.
5. `CI` 워크플로의 matrix `job`을 확인합니다.
6. 테스트의 기대값을 의도적으로 한 번 바꿔 실패한 `step`을 찾습니다.
7. 로컬에서 같은 실패를 재현합니다.
8. 수정 후 push하여 새 실행이 통과하는지 확인합니다.
9. 저장소 ruleset에서 CI 검사를 병합 조건으로 지정합니다.

연습용 실패 커밋은 최종 브랜치에 남기지 않아도 됩니다. 다만 실패 원인과 수정 방법은 설명할 수 있어야 합니다.

## 완료 기준

- Pull Request 실행이 검사한 커밋과 이벤트를 확인합니다.
- 필수 상태 검사와 단순 워크플로 실행을 구분합니다.
- `GITHUB_TOKEN`에 필요한 최소 권한을 설명합니다.
- fork Pull Request에 비밀값을 제한하는 이유를 설명합니다.
- `pull_request_target`에서 신뢰하지 않는 코드를 실행하면 안 되는 이유를 설명합니다.
- 외부 Action을 전체 커밋 SHA로 고정합니다.
- 실패한 `job`과 `step`을 찾아 로컬에서 같은 명령을 재현합니다.
