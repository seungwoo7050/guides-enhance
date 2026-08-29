# catalog-site

`catalog-site`는 분류 가능한 항목을 게시하고 사용자가 후기와 신규 항목 제보를 남길 수 있는 Django 5.2 application입니다.

서버 렌더링 화면, Django ORM, form, 인증, object ownership, admin 검수, transaction, test, 운영 settings를 하나의 project에서 연결합니다. 별도 frontend 없이 독립적으로 실행할 수 있으며, 선택 기능으로 read-only JSON API도 제공합니다.

## 주요 기능

- 공개된 Entry 목록과 상세 조회
- 제목·요약 검색
- Category와 Tag filter
- Pagination
- 회원가입, 로그인, POST logout
- 사용자당 Entry별 후기 1건 작성·수정·삭제
- 본인 제보 제출과 처리 상태 확인
- Staff가 제보를 승인해 draft Entry로 변환하거나 거절
- Django admin의 검색, filter, bulk action
- HTML 목록과 같은 조건을 사용하는 read-only JSON API
- 개발·운영 settings 분리
- Model, query, view, permission, transaction, API test

## 요구 환경

- Python 3.12 이상
- Django 5.2.17

SQLite를 기본 database로 사용합니다. 운영에서 동시 write와 백업, 복제가 중요하면 PostgreSQL 같은 운영 database로 바꿔야 합니다.

## 설치

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
python manage.py migrate
python manage.py loaddata catalog/sample_catalog
python manage.py createsuperuser
python manage.py runserver
```

Windows PowerShell에서는 virtual environment 활성화 명령이 다릅니다.

## 주요 URL

```text
/                         Entry 목록
/entries/<slug>/          Entry 상세
/accounts/signup/         회원가입
/accounts/login/          로그인
/submissions/new/          신규 항목 제보
/submissions/mine/         본인 제보 내역
/admin/                    운영자 화면
/api/entries/              JSON 목록
/api/entries/<slug>/       JSON 상세
```

## Test와 확인

```sh
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

운영 설정 확인:

```sh
DJANGO_SETTINGS_MODULE=config.settings.production \
DJANGO_SECRET_KEY='replace-with-a-long-random-value' \
DJANGO_ALLOWED_HOSTS='example.com' \
python manage.py check --deploy
```

`runserver`는 개발 server입니다. 운영에서는 WSGI 또는 ASGI server, TLS 종료, static file 제공, process restart, log 수집을 별도로 구성해야 합니다.

## Project 구성

```text
catalog-site/
├── manage.py
├── pyproject.toml
├── config/
│   ├── settings/
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── accounts/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   └── templates/
└── catalog/
    ├── models.py
    ├── queries.py
    ├── forms.py
    ├── views.py
    ├── services.py
    ├── admin.py
    ├── api.py
    ├── templates/
    ├── static/
    ├── fixtures/
    └── tests/
```

## Data model

```text
User
 ├─ Entry.created_by
 ├─ Review.author
 └─ Submission.submitted_by / reviewed_by

Category ─ Entry ─ Review
Tag ───────┘
Submission ─ approved ─→ draft Entry
```

- `Category` 삭제는 관련 Entry가 있으면 거부합니다.
- `Entry.created_by`는 사용자가 삭제돼도 Entry를 유지하도록 `SET_NULL`을 사용합니다.
- `Review`는 rating 1~5와 `(entry, author)` unique constraint를 가집니다.
- `Submission` 승인은 row를 lock한 transaction 안에서 draft Entry 생성과 상태 변경을 함께 처리합니다.

## Implementation Order

이 순서는 file order나 request 실행 순서가 아니라 project를 처음부터 구축할 때의 구현 의존성을 나타냅니다. Source annotation에서 같은 번호를 두 번 사용하지 않습니다.

| Order | Responsibility | Primary anchor |
|---:|---|---|
| `0` | Django project and app scaffold | `manage.py` |
| `0-1` | Shared settings and application composition | `config/settings/base.py` |
| `1` | Custom user model before initial migration | `accounts/models.py` |
| `2` | Category and tag taxonomy | `catalog/models.py:Category` |
| `3` | Entry publication model and relations | `catalog/models.py:Entry` |
| `4` | Review ownership and database constraints | `catalog/models.py:Review` |
| `5` | Submission moderation state | `catalog/models.py:Submission` |
| `6` | URL routing and initial template response | `catalog/views.py:EntryListView` |
| `7` | Published search and relation loading | `catalog/queries.py:filter_published_entries` |
| `8` | Review and submission form validation | `catalog/forms.py:ReviewForm` |
| `9` | User registration | `accounts/forms.py:SignUpForm` |
| `10` | Published detail loading and user submissions | `catalog/views.py:EntryDetailView` |
| `11` | Review ownership enforcement | `catalog/views.py:ReviewAuthorRequiredMixin` |
| `12` | Transactional submission moderation | `catalog/services.py:approve_submission` |
| `13` | Admin moderation operations | `catalog/admin.py:SubmissionAdmin` |
| `14` | Read-only JSON API | `catalog/api.py:entry_list_api` |
| `15` | Project behavior verification | `catalog/tests/test_models.py:CatalogModelTests` |
| `16` | Production security settings | `config/settings/production.py` |

## 설계 선택

### Custom user를 먼저 만듭니다

`accounts.User`는 `AbstractUser`를 상속하고 email uniqueness만 추가합니다. `AUTH_USER_MODEL`은 첫 migration 전에 설정합니다. 중간에 user model을 교체하는 복잡한 migration을 피하기 위한 선택입니다.

### 공개 query를 한곳에서 사용합니다

HTML 목록과 JSON API는 `filter_published_entries()`를 함께 사용합니다. Draft 제외, 검색, filter, relation loading이 화면마다 달라지는 일을 줄입니다.

### Form과 database가 서로 다른 오류를 막습니다

Form은 사용자에게 짧은 오류를 보여 줍니다. Database constraint는 admin, script, 동시 요청을 포함해 rating 범위와 중복 후기를 최종적으로 막습니다.

### 제보 검수는 service function에서 처리합니다

Admin action은 상태를 직접 바꾸지 않고 `approve_submission()`과 `reject_submission()`을 호출합니다. 이 함수가 staff 권한, row lock, 현재 상태, Entry 생성, 검수 기록을 처리합니다.

## 범위와 제한

- File upload는 포함하지 않습니다.
- Review 평균 점수 cache는 두지 않고 필요할 때 aggregate합니다.
- SQLite에서는 PostgreSQL과 같은 row-level lock 동작을 검증할 수 없습니다.
- JSON API는 read-only이며 token 인증과 CORS 설정을 제공하지 않습니다.
- Email verification, password reset mail server, social login은 포함하지 않습니다.
- Background task, cache server, WebSocket은 포함하지 않습니다.
