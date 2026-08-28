# Git 협업과 GitHub Actions CI

이 저장소는 Git으로 변경을 안전하게 공유하고, Pull Request에서 GitHub Actions 검사를 운영하는 데 필요한 최소 지식을 정리합니다. 명령을 외우는 대신 현재 저장소 상태와 다음 명령이 바꿀 대상을 먼저 확인합니다.

## 완료 후 할 수 있어야 하는 일

- 작업 트리, 인덱스, `HEAD`, 로컬 브랜치와 원격 추적 브랜치를 구분합니다.
- 최신 원격 기준에서 작업 브랜치를 만들고, 관련 변경만 모아 검토 가능한 커밋을 만듭니다.
- 작업 브랜치를 게시하고 Pull Request의 `base`, `head`와 실제 변경 범위를 확인합니다.
- merge와 rebase가 커밋 그래프를 바꾸는 방식을 설명하고 충돌을 해결하거나 중단합니다.
- 변경의 공유 여부에 따라 `restore`, `reset`, `revert`, `reflog`, `stash`를 선택합니다.
- 로컬 검사와 GitHub Actions가 같은 명령을 실행하도록 구성합니다.
- 실패한 워크플로 실행에서 `job`과 `step`을 찾아 로컬에서 재현합니다.
- `GITHUB_TOKEN`, 비밀값, fork Pull Request와 외부 Action의 위험을 구분합니다.

## 필수 문서

| 순서 | 문서 | 중심 내용 |
| ---: | --- | --- |
| 0 | [`docs/00-roadmap.md`](docs/00-roadmap.md) | 전체 순서와 완료 기준 |
| 1 | [`docs/01-workspace-basics.md`](docs/01-workspace-basics.md) | 저장소 상태, 원격, 브랜치와 시작점 |
| 2 | [`docs/02-commit-workflow.md`](docs/02-commit-workflow.md) | 변경 검토, 스테이징과 목적별 커밋 |
| 3 | [`docs/03-remote-pr-workflow.md`](docs/03-remote-pr-workflow.md) | push, upstream, Pull Request와 리뷰 |
| 4 | [`docs/04-merge-rebase-conflicts.md`](docs/04-merge-rebase-conflicts.md) | merge, rebase, 충돌과 이력 재작성 |
| 5 | [`docs/05-recovery-runbook.md`](docs/05-recovery-runbook.md) | 손실 범위를 확인한 복구 |
| 6 | [`docs/06-github-actions-workflow-model.md`](docs/06-github-actions-workflow-model.md) | 워크플로 실행 단위와 로컬 검사 연결 |
| 7 | [`docs/07-pull-request-ci-and-security.md`](docs/07-pull-request-ci-and-security.md) | Pull Request CI, 권한과 보안 |

[`docs/90-open-source-contribution.md`](docs/90-open-source-contribution.md)는 fork 기반 오픈소스 기여가 필요할 때만 읽는 선택 문서입니다.

## 실습 프로젝트

### [`exercises/local-git-lab/`](exercises/local-git-lab/)

외부 서비스 없이 여러 로컬 저장소와 bare 원격 저장소를 만듭니다. 다음 상태를 실제 Git 객체와 ref로 확인할 수 있습니다.

- 하나의 복제본과 bare 원격 저장소
- 서로 다른 작업 브랜치를 가진 여러 복제본
- 병합된 변경과 아직 분기된 변경
- rebase 충돌
- reset과 detached `HEAD` 뒤 보존한 커밋
- revert와 stash

### [`exercises/github-actions-ci/`](exercises/github-actions-ci/)

JSON 변경 기록을 검증하는 작은 Python CLI와 GitHub Actions 워크플로를 포함합니다. 개발자와 CI가 모두 `./scripts/check.sh`를 실행하므로 로컬 성공과 CI 성공의 기준이 달라지지 않습니다.

## 권장 순서

```text
01 작업 시작 상태
→ `local-git-lab`의 `sample` 생성·확인
→ 02 목적별 커밋
→ `sample-app`에서 변경·검토·커밋
→ 03 원격 협업
→ `local-git-lab`의 `team` 복제본 비교
→ 04 merge·rebase·충돌
→ `team-app-dev-b`에서 rebase 충돌 재현
→ 05 복구
→ `local-git-lab`의 `recovery` 상태 확인
→ 06 GitHub Actions 실행 모델
→ `github-actions-ci`의 로컬 검사와 워크플로 확인
→ 07 Pull Request CI와 보안
→ 실제 GitHub Pull Request에서 검사 결과 확인
```

문서를 모두 읽은 뒤 실습을 몰아서 실행하지 않습니다. 필요한 개념을 읽은 직후 해당 상태를 직접 만들고 확인합니다.

## 완료 기준

다음 작업을 설명과 명령으로 재현하면 필수 과정을 마친 것입니다.

1. 현재 저장소와 원격 URL, 브랜치, upstream, 변경 상태를 확인합니다.
2. 한 파일에 섞인 변경을 목적별로 나누어 두 커밋으로 만듭니다.
3. 작업 브랜치를 게시하고 Pull Request의 `base`, `head`와 전체 diff를 확인합니다.
4. 의도적으로 만든 rebase 충돌에서 두 변경을 모두 보존하거나 `--abort`로 돌아갑니다.
5. 사라진 커밋을 `reflog`에서 찾아 새 브랜치로 보존합니다.
6. `exercises/github-actions-ci/scripts/check.sh`를 로컬에서 통과시킵니다.
7. Pull Request에서 같은 검사가 GitHub Actions 검사로 통과하는 것을 확인합니다.
8. 워크플로가 요청하는 권한과 외부 Action의 고정 SHA를 설명합니다.

## 범위 밖

이 저장소는 다음 주제를 필수 과정으로 다루지 않습니다.

- Git object database와 plumbing 명령의 내부 구현
- 대규모 monorepo, partial clone과 submodule 운영
- 배포·릴리스 자동화와 클라우드 인증 정보 연동
- self-hosted runner 구축과 운영
- 사용자 정의 Action과 reusable workflow 설계
- 조직 전체의 ruleset, 권한과 감사 로그 운영

필요한 프로젝트에서 해당 문제가 생겼을 때 별도로 학습합니다.
