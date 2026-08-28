# GitHub Actions CI

## 개요

이 프로젝트는 JSON 변경 기록을 검사하는 작은 Python CLI와 Pull Request CI 워크플로를 함께 제공합니다. 개발자와 GitHub Actions가 모두 `./scripts/check.sh`를 실행하므로 로컬과 CI의 통과 기준이 달라지지 않습니다.

외부 Python 패키지는 사용하지 않습니다. Python 표준 라이브러리, Bash와 GitHub-hosted runner만으로 실행할 수 있습니다.

## 기능

`src/change_record.py`는 다음 형식의 JSON 파일을 읽습니다.

```json
{
  "title": "Add CI checks",
  "summary": "Run the same verification locally and in CI.",
  "checks": [
    "./scripts/check.sh"
  ]
}
```

검사 항목:

- 입력이 JSON 객체인지 확인합니다.
- `title`, `summary`, `checks`가 모두 있는지 확인합니다.
- 알 수 없는 필드를 거부합니다.
- `title`이 비어 있지 않고 72자를 넘지 않는지 확인합니다.
- `summary`가 비어 있지 않은지 확인합니다.
- `checks`가 비어 있지 않은 문자열 배열인지 확인합니다.

## 요구 사항

- Python 3.11 이상
- Bash
- GitHub Actions 실습 시 GitHub 저장소와 Pull Request 생성 권한

## 사용법

JSON 파일을 준비합니다.

```bash
cat > /tmp/change-record.json <<'JSON'
{
  "title": "Add CI checks",
  "summary": "Run the same verification locally and in CI.",
  "checks": ["./scripts/check.sh"]
}
JSON
```

검사합니다.

```bash
python3 src/change_record.py /tmp/change-record.json
```

성공 출력:

```text
valid change record: Add CI checks
```

종료 상태:

- `0`: JSON을 읽었고 모든 검사를 통과했습니다.
- `2`: 인자, 파일 읽기, JSON 문법 또는 필드 검사가 실패했습니다.

오류는 `stderr`에 기록합니다.

## 로컬 검증

```bash
./scripts/check.sh
```

이 명령은 다음을 수행합니다.

1. `src/`와 `tests/`의 Python 소스 코드를 컴파일해 문법 오류를 찾습니다.
2. 검증 규칙 테스트를 실행합니다.
3. 실제 하위 프로세스로 CLI를 실행해 표준 출력, 표준 오류와 종료 상태를 확인합니다.

`PYTHON` 환경 변수로 실행할 Python을 바꿀 수 있습니다.

```bash
PYTHON=python3.13 ./scripts/check.sh
```

## GitHub Actions 워크플로

`.github/workflows/ci.yml`은 다음 이벤트에서 실행됩니다.

- Pull Request 생성과 새 push
- `main` 브랜치 push
- Actions 화면의 수동 실행

각 실행은 Python 3.11과 3.13에서 같은 검사를 실행합니다.

```text
이벤트
→ CI 워크플로 실행
→ Python 버전별 테스트 `job`
→ 저장소 checkout
→ Python 설정
→ ./scripts/check.sh
→ 검사 결과
```

## 권한과 외부 Action

워크플로는 소스 코드를 읽고 테스트만 실행하므로 다음 권한만 요청합니다.

```yaml
permissions:
  contents: read
```

checkout 뒤 Git 인증 정보가 필요하지 않으므로 `persist-credentials: false`를 사용합니다.

외부 Action은 전체 커밋 SHA로 고정합니다.

```yaml
uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
```

뒤의 버전은 업데이트 검토를 위한 주석입니다. 실제로 실행되는 revision은 SHA입니다.

## Pull Request에서 확인하기

1. 이 디렉터리를 독립 저장소나 연습 브랜치에 게시합니다.
2. 새 작업 브랜치에서 소스 코드 또는 테스트를 작게 수정합니다.
3. `./scripts/check.sh`를 실행한 뒤 커밋하고 push합니다.
4. Pull Request를 엽니다.
5. `CI / Python 3.11`, `CI / Python 3.13` 결과를 확인합니다.
6. 테스트를 의도적으로 한 번 실패시켜 실패한 `step`을 찾습니다.
7. 로컬에서 같은 명령으로 재현한 뒤 고치고 다시 push합니다.

워크플로가 실행되는 것만으로 병합이 자동 차단되지는 않습니다. 저장소 ruleset 또는 브랜치 보호 규칙에서 필요한 검사를 병합 조건으로 지정해야 합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Change record validation and CLI result | `src/change_record.py` |
| 2 | Validation rule tests | `tests/test_change_record.py` |
| 3 | Shared local and CI check command | `scripts/check.sh` |
| 4 | Pull request and main-branch workflow | `.github/workflows/ci.yml` |
| 5 | CLI exit status and error output tests | `tests/test_cli.py` |

## 제한

- 배포, 릴리스와 패키지 게시는 수행하지 않습니다.
- 비밀값이나 쓰기 권한이 필요한 `job`은 포함하지 않습니다.
- 브랜치 보호 규칙과 ruleset은 저장소 설정이므로 파일로 자동 구성하지 않습니다.
- GitHub-hosted runner의 실제 워크플로 실행은 로컬 테스트만으로 대체할 수 없습니다. GitHub에 게시한 뒤 별도로 확인해야 합니다.
