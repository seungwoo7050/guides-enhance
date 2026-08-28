# 다중 저장소 릴리스 명세 검사기

## 개요

여러 Git 저장소가 JSON 명세에 적힌 remote, annotated tag와 commit을 정확히 가리키는지 확인하는 Python CLI입니다. 움직일 수 있는 branch 이름이나 작업자의 로컬 상태 대신 고정된 Git 식별자로 릴리스 입력을 검증합니다.

## 주요 기능

- 명세 안에서 저장소 이름과 실제 경로가 중복되면 거절합니다.
- `origin` 주소를 확인하고 끝의 `/`와 `.git` 차이만 허용합니다.
- 추적 파일과 미추적 파일이 모두 없는 clean worktree만 승인합니다.
- detached `HEAD`가 40자리 commit SHA와 일치하는지 확인합니다.
- annotated tag를 peel한 commit이 명세와 같은지 검사합니다.
- 성공, 검증 실패와 잘못된 사용법을 서로 다른 종료 상태로 반환합니다.

## 구성

`verify_repository`가 저장소 하나의 Git 상태를 확인하고, `verify_manifest`가 JSON을 읽어 이름·경로 중복을 검사한 뒤 각 저장소를 순회합니다. `main`은 결과를 표준 출력·표준 오류와 종료 상태로 전달합니다.

## 실행 및 검증

입력 JSON은 다음 형식을 사용합니다.

```json
{
  "repositories": [
    {
      "name": "contracts",
      "path": "/absolute/path/to/contracts",
      "remote": "https://github.com/example/contracts.git",
      "tag": "v1.4.0",
      "commit": "0123456789abcdef0123456789abcdef01234567"
    }
  ]
}
```

각 `path`는 실제 local Git worktree의 절대 경로여야 합니다.

Python 3.10 이상과 Git이 필요하며 외부 Python package는 사용하지 않습니다.

```sh
python3 manifest_check.py release-manifest.json
```

검증에 성공하면 `release manifest verified`를 출력하고 종료 상태 `0`을 반환합니다. 명세나 저장소 상태가 잘못되면 이유를 표준 오류에 출력하고 `1`, 사용법이 잘못되면 `2`를 반환합니다.

```sh
make check
make test
```

`make test`는 임시 Git 저장소를 만들어 정상 명세와 이름·경로 중복, 원격 주소 불일치, dirty worktree, branch checkout, 잘못된 commit과 lightweight tag를 검사합니다. 테스트가 만든 저장소는 임시 디렉터리와 함께 삭제됩니다.

## 주요 설계 결정

remote 주소는 같은 저장소를 표현하는 최소한의 표기 차이만 정규화합니다. 서로 다른 host, owner나 repository 이름을 같은 값으로 취급하지 않습니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 릴리스 명세 오류 | `manifest_check.py — ManifestError` |
| 2 | Git 명령 실행과 오류 변환 | `manifest_check.py — git` |
| 3 | 원격 저장소 주소 정규화 | `manifest_check.py — normalize_remote` |
| 3-1 | 필수 문자열 검증 | `manifest_check.py — require_string` |
| 4 | 저장소 릴리스 상태 검증 | `manifest_check.py — verify_repository` |
| 5 | 명세 전체 중복 검사와 저장소 순회 | `manifest_check.py — verify_manifest` |
| 6 | 명령행 종료 상태 | `manifest_check.py — main` |

## 범위와 제한

- Git 서명 신뢰, build artifact digest와 배포 상태는 검사하지 않습니다.
- remote server에 접속하지 않고 등록된 URL 문자열만 비교합니다.
- JSON 형식은 현재 검사에 필요한 필드만 지원합니다.
