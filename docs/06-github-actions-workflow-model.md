# GitHub Actions 워크플로 실행 모델

## 목표

GitHub Actions YAML을 복사해 붙이는 데서 끝내지 않습니다. 어떤 이벤트가 워크플로 실행을 만들고, 각 `job`이 어느 runner에서 어떤 명령을 실행하며, 실패가 어디서 발생했는지 설명합니다.

```text
이벤트
→ 워크플로 실행
→ `job`
→ runner
→ `step`
→ 명령 또는 Action
→ 종료 상태
→ 검사 결과
```

## 워크플로 파일 위치

GitHub는 다음 경로의 YAML 파일을 워크플로로 읽습니다.

```text
.github/workflows/*.yml
.github/workflows/*.yaml
```

파일 이름은 자유롭게 정할 수 있지만, 한 파일이 어떤 검사를 담당하는지 알 수 있게 짓습니다.

```text
ci.yml
lint.yml
release.yml
```

이 과정에서는 빌드와 테스트를 담당하는 `ci.yml` 하나만 사용합니다.

## 이벤트와 워크플로 실행

`on`은 워크플로를 시작할 이벤트를 지정합니다.

```yaml
on:
  pull_request:
  push:
    branches:
      - main
  workflow_dispatch:
```

의미:

- `pull_request`: Pull Request 생성, 새 push 등 지정된 PR 이벤트에서 실행합니다.
- `push`: 여기서는 `main`에 push된 커밋을 확인합니다.
- `workflow_dispatch`: Actions 화면에서 수동 실행할 수 있게 합니다.

같은 워크플로라도 이벤트마다 `github.ref`, checkout 대상과 토큰 권한이 달라질 수 있습니다. 이벤트 이름만 보고 같은 실행이라고 가정하지 않습니다.

## `job`

`job`은 독립된 runner에서 실행되는 단위입니다.

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: ./scripts/check.sh
```

기본적으로 `job`끼리는 독립적이며 동시에 실행될 수 있습니다. 다른 `job`의 성공이 필요하면 `needs`를 명시합니다.

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: ./scripts/check.sh

  package:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: ./scripts/package.sh
```

검사 하나를 억지로 여러 `job`으로 나누지 않습니다. runner를 따로 써야 하거나, 독립적으로 실패 원인을 구분할 가치가 있을 때 나눕니다.

## runner

`runs-on`은 `job`을 실행할 환경 이미지를 고릅니다.

```yaml
runs-on: ubuntu-latest
```

GitHub-hosted runner는 `job`마다 새 환경에서 시작합니다. 이전 실행에서 만든 파일이나 설치 상태가 자동으로 남지 않습니다.

따라서 워크플로는 필요한 저장소 checkout, 실행 환경 설정과 명령을 명시해야 합니다.

## `step`: `uses`와 `run`

### Action 실행

```yaml
- name: Checkout repository
  uses: actions/checkout@COMMIT_SHA
```

`uses`는 다른 Action 또는 현재 저장소의 Action을 실행합니다.

### 셸 명령 실행

```yaml
- name: Run project checks
  run: ./scripts/check.sh
```

`run`은 runner의 셸에서 명령을 실행합니다. 명령이 0이 아닌 종료 상태를 반환하면 기본적으로 `step`과 `job`이 실패합니다.

## checkout과 실행 환경 설정

runner에는 현재 저장소 파일이 자동으로 준비되지 않습니다. 먼저 checkout합니다.

```yaml
- name: Checkout repository
  uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
  with:
    persist-credentials: false
```

Python 버전도 명시합니다.

```yaml
- name: Set up Python
  uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
  with:
    python-version: '3.13'
```

runner 이미지의 기본 Python은 바뀔 수 있습니다. 지원 버전을 검증하는 워크플로에서는 버전을 입력으로 고정합니다.

외부 Action은 나중에 다른 커밋을 가리킬 수 있는 major tag 대신 검토한 커밋 SHA로 고정합니다. 뒤의 버전 주석은 사람이 업데이트 후보를 찾기 위한 정보이며 실제 실행 대상은 SHA입니다.

## 로컬과 CI가 같은 명령을 사용해야 하는 이유

워크플로 안에 테스트 명령을 길게 다시 작성하면 로컬과 CI가 쉽게 달라집니다.

피할 형태:

```yaml
- run: python -m compileall src
- run: python -m unittest discover -s tests
- run: 여러 추가 검사
```

권장 형태:

```yaml
- run: ./scripts/check.sh
```

개발자도 같은 명령을 실행합니다.

```bash
./scripts/check.sh
```

검사 순서를 바꿀 때 `scripts/check.sh` 한 곳을 수정하면 로컬과 CI가 함께 바뀝니다.

## matrix

여러 실행 환경 버전에서 같은 `job`을 반복하려면 matrix를 사용합니다.

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version:
      - '3.11'
      - '3.13'
```

`step`에서 값을 사용합니다.

```yaml
- uses: actions/setup-python@COMMIT_SHA
  with:
    python-version: ${{ matrix.python-version }}
```

`fail-fast: false`는 한 버전이 실패해도 다른 버전 결과를 계속 수집합니다. 지원 버전마다 독립적인 결과가 필요한 경우에 적합합니다.

matrix를 조합 수만 늘리는 용도로 사용하지 않습니다. 실제 지원 범위를 검증하는 항목만 넣습니다.

## context와 expression

`${{ ... }}`는 GitHub가 워크플로를 해석할 때 값을 읽는 expression입니다.

```yaml
${{ github.ref }}
${{ matrix.python-version }}
${{ secrets.DEPLOY_TOKEN }}
```

주요 context:

- `github`: 이벤트, 저장소, ref와 실행 주체 정보
- `matrix`: 현재 matrix 조합
- `runner`: runner OS와 임시 경로
- `env`: 워크플로, `job` 또는 `step` 환경 변수
- `secrets`: 저장소나 GitHub environment에 등록한 비밀값
- `needs`: 선행 `job`의 결과와 출력값

신뢰하지 않는 입력을 셸 명령 문자열에 직접 삽입하지 않습니다. 필요한 값은 환경 변수로 전달하고 프로그램에서 검증합니다.

```yaml
env:
  PR_TITLE: ${{ github.event.pull_request.title }}
run: python scripts/check_title.py
```

## 권한

워크플로 또는 `job`에서 `GITHUB_TOKEN` 권한을 명시합니다.

읽기 전용 CI 예:

```yaml
permissions:
  contents: read
```

저장소를 checkout하고 테스트만 실행하는 `job`에는 저장소 쓰기 권한이 필요하지 않습니다.

모든 권한을 비우고 `job`에 필요한 권한만 추가할 수도 있습니다.

```yaml
permissions: {}
```

권한이 부족해 실패하면 필요한 작업을 먼저 확인합니다. 편의를 위해 `write-all`을 주지 않습니다.

## 중복 실행 취소

같은 Pull Request에 연속 push하면 오래된 실행이 계속 실행될 수 있습니다.

```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```

같은 PR 또는 브랜치의 이전 실행을 취소해 최신 커밋 결과에 집중합니다. 서로 다른 PR은 다른 `group`을 사용합니다.

## 실패 위치 찾기

Actions 화면에서 다음 순서로 좁힙니다.

```text
워크플로 실행
→ 실패한 `job`
→ 실패한 `step`
→ 실행한 명령
→ 처음 발생한 의미 있는 오류
→ 종료 상태
```

마지막 줄만 보지 않습니다. 의존성 설치 실패 뒤 테스트 `step`이 건너뛰었을 수도 있고, 테스트의 기대값 불일치가 실제 원인일 수도 있습니다.

로컬에서 같은 명령을 실행합니다.

```bash
./scripts/check.sh
```

로컬에서는 성공하지만 CI에서만 실패하면 다음 차이를 확인합니다.

- Python 버전, runner OS와 CPU 아키텍처
- 환경 변수
- 파일 이름 대소문자
- 실행 권한
- 시간대와 로케일
- checkout 깊이
- 비밀값과 토큰 권한
- 네트워크 접근 여부

## `cache`와 `artifact`

둘은 목적이 다릅니다.

- `cache`: 다음 실행에서 의존성 설치 시간을 줄이기 위한 재사용 데이터
- `artifact`: 현재 실행의 결과 파일을 내려받거나 다음 `job`에서 사용하기 위한 보관물

cache 적중을 정상 동작의 전제 조건으로 만들지 않습니다. cache가 없어도 워크플로는 정상 동작해야 합니다.

이 실습 프로젝트에는 외부 의존성이 없으므로 `cache`와 `artifact`를 사용하지 않습니다.

## `github-actions-ci` 워크플로 읽기

```bash
cd exercises/github-actions-ci
sed -n '1,240p' .github/workflows/ci.yml
./scripts/check.sh
```

다음을 찾아 설명합니다.

- 워크플로를 시작하는 세 이벤트
- `contents: read`
- 중복 실행을 취소하는 concurrency `group`
- Python matrix
- checkout과 setup-python의 고정 SHA
- 로컬과 동일한 `./scripts/check.sh`

## 완료 기준

- 이벤트, 워크플로 실행, `job`, runner, `step`의 관계를 설명합니다.
- `uses`와 `run`의 차이를 설명합니다.
- 0이 아닌 종료 상태가 `job` 실패로 이어지는 과정을 확인합니다.
- 로컬과 CI가 같은 검사 명령을 사용하도록 구성합니다.
- matrix가 실제 지원 버전을 검증하도록 제한합니다.
- 워크플로가 요청하는 `GITHUB_TOKEN` 권한을 설명합니다.
