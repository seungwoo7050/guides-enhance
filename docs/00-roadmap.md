# Django 학습 로드맵

## 목표

이 과정의 종료 기준은 Django 문법을 기억하는 것이 아닙니다. 사용자의 HTTP 요청을 받아 데이터를 검증하고, database에서 필요한 row를 읽거나 수정한 뒤, 권한에 맞는 HTML 또는 JSON response를 반환하는 애플리케이션을 완성하는 것입니다.

## 선행 조건

다음 Python 내용은 먼저 알고 있어야 합니다.

- module과 package 실행
- class, function, exception
- `list`, `dict`, `set`, `tuple`
- type hint와 runtime validation의 차이
- context manager
- 기본적인 unit test
- virtual environment와 `pyproject.toml`

## 구현 대상

모든 필수 문서는 [`catalog-site`](../exercises/catalog-site/README.md)의 구현 순서와 연결됩니다.

```text
User
Category ─┐
Tag ──────┼─ Entry ─ Review
          └──────── Submission → staff 검수 → draft Entry
```

## 필수 순서

### 1. Project를 실행하고 첫 response를 반환합니다

1. [Project, app과 settings](01-project-and-request/01-project-app-and-settings.md)
2. `catalog-site`의 Implementation 0, 0-1
3. [URL, view, request와 response](01-project-and-request/02-url-view-request-response.md)
4. `catalog-site`의 Implementation 6
5. [Template, static file과 context](01-project-and-request/03-template-static-and-context.md)

여기까지 마치면 URL을 view에 연결하고 template response를 반환할 수 있어야 합니다.

### 2. Database에 데이터를 저장하고 읽습니다

6. [Model, field와 migration](02-data/01-models-fields-and-migrations.md)
7. `catalog-site`의 Implementation 1~5
8. migration을 적용하고 sample fixture를 불러옵니다.
9. [QuerySet, relation과 loading](02-data/02-querysets-relations-and-loading.md)
10. `catalog-site`의 Implementation 7

여기까지 마치면 공개된 항목만 검색하고, 관련 category와 tag를 불필요한 추가 query 없이 읽을 수 있어야 합니다.

### 3. 사용자 입력과 권한을 처리합니다

11. [Form과 입력 검증](03-web-input-and-users/01-forms-and-validation.md)
12. `catalog-site`의 Implementation 8
13. [인증, session과 CSRF](03-web-input-and-users/02-authentication-sessions-and-csrf.md)
14. `catalog-site`의 Implementation 9
15. [권한과 object ownership](03-web-input-and-users/03-permissions-and-object-ownership.md)
16. `catalog-site`의 Implementation 10~11

여기까지 마치면 로그인한 사용자만 후기를 작성하고, 작성자만 자신의 후기를 수정하거나 삭제하도록 제한할 수 있어야 합니다.

### 4. 여러 변경을 함께 처리하고 운영 기능을 완성합니다

17. [Constraint, transaction과 동시 수정](02-data/03-constraints-transactions-and-concurrency.md)
18. `catalog-site`의 Implementation 12
19. [Admin과 데이터 작업](04-operation-and-quality/01-admin-and-data-operations.md)
20. `catalog-site`의 Implementation 13
21. [Django 테스트](04-operation-and-quality/02-testing.md)
22. `catalog-site`의 Implementation 15
23. [Settings, 보안과 배포 준비](04-operation-and-quality/03-settings-security-and-deployment.md)
24. `catalog-site`의 Implementation 16

## 선택 순서

25. [Django JSON API와 Astro 연동](05-api-integration/01-django-api-and-astro.md)
26. `catalog-site`의 Implementation 14

JSON API는 필수 Django 역량을 검증한 뒤 진행합니다. 별도 frontend가 없는 프로젝트라면 생략해도 됩니다.

## 완료 기준

다음 항목을 모두 확인하면 필수 과정을 완료한 것입니다.

- `python manage.py check`가 성공합니다.
- migration이 누락되지 않았습니다.
- sample fixture를 불러온 뒤 목록과 상세 화면을 확인했습니다.
- 비로그인 사용자의 후기 작성 요청이 로그인 화면으로 이동합니다.
- 다른 사용자의 후기를 수정하거나 삭제할 수 없습니다.
- 같은 사용자가 같은 항목에 후기를 두 번 저장할 수 없습니다.
- staff만 제보를 승인하거나 거절할 수 있습니다.
- 제보 승인은 하나의 transaction에서 draft Entry 생성과 상태 변경을 함께 처리합니다.
- `python manage.py test`가 성공합니다.
- 운영 settings로 `python manage.py check --deploy`를 실행하고 남은 경고를 설명할 수 있습니다.

## 범위에서 제외하는 내용

- Django REST Framework
- async view 최적화
- WebSocket과 Channels
- Celery와 분산 task queue
- Redis 기반 cache와 session
- multi-tenant database
- Kubernetes와 cloud provider별 배포 절차

이 항목들은 Django의 기본 request, ORM, form, auth, test를 먼저 완성한 뒤 실제 요구가 생기면 학습합니다.
