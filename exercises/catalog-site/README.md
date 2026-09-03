# catalog-site

`catalog-site`는 분류 가능한 항목을 게시하고, 사용자가 후기와 신규 항목 제보를 남길 수 있도록 구성한 Django 5.2 application입니다.

이 project의 목적은 Django의 개별 기능을 따로 연습하는 것이 아니라, 서버 렌더링 화면, Django ORM, form validation, 인증, object ownership, admin 검수, transaction, test, 운영 settings가 하나의 application 안에서 어떻게 연결되는지 학습하는 것입니다.

별도 frontend 없이 Django template만으로 독립적으로 실행할 수 있습니다. 선택 기능으로 동일한 공개 데이터에 접근하는 read-only JSON API도 제공합니다.

## 주요 기능

- 공개 상태인 `Entry` 목록과 상세 조회
- 제목·요약 기준 검색
- `Category`, `Tag` 기준 filter
- Pagination
- 회원가입과 로그인
- GET 요청으로 상태를 변경하지 않는 POST 방식 logout
- 사용자당 `Entry`별 후기 1건 작성·수정·삭제
- 사용자의 신규 항목 제보 제출과 본인 제보 처리 상태 조회
- Staff의 제보 승인 또는 거절
- 승인된 제보를 즉시 공개하지 않고 draft `Entry`로 변환
- Django admin의 검색, filter, bulk action
- HTML 목록과 동일한 공개 조건을 사용하는 read-only JSON API
- 개발 settings와 운영 settings 분리
- Model, query, view, permission, transaction, API 동작 test

## 요구 환경

- Python 3.12 이상
- Django 5.2.17

기본 database는 SQLite입니다. SQLite는 별도 database server 없이 바로 실행할 수 있어 학습과 로컬 개발에 적합합니다.

다만 실제 운영에서 다음 요구가 중요하다면 PostgreSQL 같은 운영용 database를 고려해야 합니다.

- 여러 요청이 동시에 write하는 환경
- 명확한 row-level locking 동작
- 체계적인 backup과 restore
- replication
- 운영 monitoring과 확장성

이 project의 transaction 구조를 PostgreSQL에서 사용할 수 있도록 설계하더라도, SQLite에서 관찰한 locking 동작을 PostgreSQL에서도 동일하다고 가정해서는 안 됩니다.

## 설치

Project root에서 다음 순서로 실행합니다.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
python manage.py migrate
python manage.py loaddata catalog/sample_catalog
python manage.py createsuperuser
python manage.py runserver
```

각 명령의 역할은 다음과 같습니다.

1. `python3 -m venv .venv`
   - project 전용 Python virtual environment를 생성합니다.
   - system Python에 package를 직접 설치하지 않도록 실행 환경을 분리합니다.

2. `. .venv/bin/activate`
   - 생성한 virtual environment를 현재 shell에 활성화합니다.
   - Windows PowerShell에서는 활성화 명령이 다릅니다.

3. `python -m pip install .`
   - `pyproject.toml`에 정의된 project와 dependency를 현재 virtual environment에 설치합니다.

4. `python manage.py migrate`
   - Django migration을 현재 database에 적용해 필요한 table과 constraint를 생성합니다.

5. `python manage.py loaddata catalog/sample_catalog`
   - 학습에 사용할 sample fixture를 database에 적재합니다.

6. `python manage.py createsuperuser`
   - Django admin에 로그인할 superuser 계정을 생성합니다.

7. `python manage.py runserver`
   - 개발용 HTTP server를 실행합니다.

`runserver`는 개발 편의를 위한 server이므로 운영 배포용 server로 사용하지 않습니다.

## 주요 URL

```text
/                         Entry 목록
/entries/<slug>/          Entry 상세
/accounts/signup/         회원가입
/accounts/login/          로그인
/submissions/new/         신규 항목 제보
/submissions/mine/        본인 제보 내역
/admin/                   운영자 화면
/api/entries/             JSON 목록
/api/entries/<slug>/      JSON 상세
```

`<slug>`는 실제 URL에서 특정 `Entry`를 식별하는 문자열로 바뀝니다.

예를 들어 slug가 `django`라면 상세 URL은 다음과 같습니다.

```text
/entries/django/
```

HTML endpoint와 `/api/entries/` endpoint는 표현 형식은 다르지만 같은 공개 조건을 사용하도록 구성합니다. 따라서 draft가 HTML에서는 숨겨지지만 API에서는 노출되는 것과 같은 불일치를 줄일 수 있습니다.

## Test와 확인

기본 확인 명령은 다음과 같습니다.

```sh
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

각 명령은 서로 다른 문제를 확인합니다.

### `check`

```sh
python manage.py check
```

Django의 system check framework를 실행합니다. settings, model 구성, URL 설정 등에서 Django가 감지할 수 있는 구성 오류를 검사합니다.

### `makemigrations --check`

```sh
python manage.py makemigrations --check
```

현재 model 변경 사항에 대응하는 migration file이 빠져 있는지 확인합니다. 이 명령이 실패하면 model 코드는 변경되었지만 필요한 migration이 아직 생성되지 않았을 가능성이 있습니다.

### `test`

```sh
python manage.py test
```

project의 automated test를 실행합니다. 이 project에서는 model, query, view, permission, transaction, API 동작을 test 대상으로 포함합니다.

## 운영 settings 확인

운영 settings를 대상으로 Django의 deployment check를 실행할 수 있습니다.

```sh
DJANGO_SETTINGS_MODULE=config.settings.production \
DJANGO_SECRET_KEY='replace-with-a-long-random-value' \
DJANGO_ALLOWED_HOSTS='example.com' \
python manage.py check --deploy
```

여기서 중요한 점은 운영에 필요한 값을 source code에 고정하지 않고 environment variable로 주입한다는 것입니다.

- `DJANGO_SETTINGS_MODULE`
  - 사용할 settings module을 지정합니다.
- `DJANGO_SECRET_KEY`
  - cryptographic signing 등에 사용하는 Django secret key를 제공합니다.
- `DJANGO_ALLOWED_HOSTS`
  - 이 application이 응답할 Host를 제한합니다.

`check --deploy`는 운영에 적합하지 않은 Django 설정을 찾는 데 도움을 주지만, 이것만 통과했다고 운영 구성이 완성되는 것은 아닙니다.

운영에서는 일반적으로 다음 요소를 별도로 구성해야 합니다.

- WSGI 또는 ASGI application server
- TLS 종료
- static file 제공
- process 시작과 restart
- log 수집
- database backup
- secret 관리

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

각 영역의 책임은 다음과 같이 나눕니다.

### `config/`

Project 전체에 적용되는 구성을 둡니다.

- settings
- root URL configuration
- WSGI entry point
- ASGI entry point

### `accounts/`

사용자 계정과 직접 관련된 기능을 둡니다.

- custom user model
- 회원가입 form
- 계정 관련 view
- 계정 관련 template

### `catalog/`

Catalog domain의 핵심 기능을 둡니다.

- `models.py`: 데이터 구조와 database constraint
- `queries.py`: 재사용 가능한 조회 로직
- `forms.py`: 사용자 입력 validation
- `views.py`: HTML 요청 처리
- `services.py`: 여러 model 변경을 함께 수행하는 domain operation
- `admin.py`: 운영자용 admin 구성
- `api.py`: JSON API
- `fixtures/`: sample data
- `tests/`: 자동화된 검증

이 구분의 목적은 모든 로직을 view나 model 하나에 집중시키지 않고, 조회·입력 검증·상태 변경·표현의 책임을 분리하는 것입니다.

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

핵심 관계를 풀어서 보면 다음과 같습니다.

### `User`

사용자는 여러 역할로 catalog 데이터와 연결될 수 있습니다.

- `Entry.created_by`
  - 어떤 사용자가 `Entry`를 만들었는지 기록합니다.
- `Review.author`
  - 후기 작성자를 기록합니다.
- `Submission.submitted_by`
  - 신규 항목을 제보한 사용자를 기록합니다.
- `Submission.reviewed_by`
  - 제보를 검수한 사용자를 기록합니다.

### `Category`와 `Tag`

`Entry`를 분류하는 taxonomy입니다.

`Category` 삭제는 관련 `Entry`가 존재할 때 거부합니다. 즉, 분류를 삭제하면서 기존 `Entry`의 의미가 의도치 않게 바뀌거나 관계가 끊어지는 것을 방지합니다.

### `Entry`

실제로 사용자에게 공개될 수 있는 catalog 항목입니다.

`Entry.created_by`는 사용자가 삭제되더라도 `Entry` 자체는 유지할 수 있도록 `SET_NULL`을 사용합니다. 따라서 작성자 계정 삭제와 catalog 데이터 삭제를 같은 사건으로 취급하지 않습니다.

또한 승인된 `Submission`에서 생성된 `Entry`는 바로 공개하지 않고 draft 상태로 시작합니다. 제보 승인과 실제 게시를 별도의 결정으로 분리하기 위한 구조입니다.

### `Review`

사용자가 특정 `Entry`에 남기는 후기입니다.

- rating 범위: 1~5
- `(entry, author)` 조합은 unique

따라서 한 사용자가 같은 `Entry`에 여러 개의 `Review` row를 만들지 못하도록 database 수준에서도 제한합니다.

### `Submission`

사용자가 아직 catalog에 없는 항목을 제보하기 위한 model입니다.

승인 처리에서는 다음 변경을 하나의 transaction 안에서 수행합니다.

1. 대상 `Submission` row를 검수 대상으로 확정합니다.
2. 현재 상태가 여전히 승인 가능한 상태인지 확인합니다.
3. draft `Entry`를 생성합니다.
4. `Submission`의 처리 상태와 검수 기록을 변경합니다.

이 작업들을 하나의 transaction으로 묶는 이유는 `Entry`는 생성되었는데 `Submission`은 미처리 상태로 남거나, 반대로 승인 상태만 기록되고 `Entry`가 생성되지 않는 부분 완료 상태를 피하기 위해서입니다.

## Implementation Order

다음 순서는 file order나 HTTP request 실행 순서가 아니라, project를 처음부터 구축할 때의 **구현 의존성**을 나타냅니다.

앞 단계에서 만든 구조를 뒤 단계가 사용하므로, 학습할 때는 단순히 파일별로 읽기보다 이 의존 관계를 따라가는 편이 전체 구조를 이해하기 쉽습니다.

Source annotation에서는 같은 번호를 두 번 사용하지 않습니다.

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

이 순서에서 특히 중요한 의존 관계는 다음과 같습니다.

- custom user model은 첫 migration 전에 결정해야 합니다.
- query layer는 HTML view와 JSON API가 함께 사용할 수 있도록 먼저 분리합니다.
- permission 검사는 수정·삭제 같은 object-level operation보다 먼저 설계합니다.
- admin action은 transaction을 직접 구현하지 않고 service function을 호출합니다.
- production settings는 기능 구현과 별개로 마지막에 검증하지만, 운영 보안 요구 자체를 생략한다는 뜻은 아닙니다.

## 설계 선택

### Custom user를 먼저 만듭니다

`accounts.User`는 Django의 `AbstractUser`를 상속하고 email uniqueness만 추가합니다.

`AUTH_USER_MODEL`은 첫 migration 전에 설정합니다.

Django project가 이미 기본 user model을 기준으로 여러 migration과 관계를 만든 뒤 custom user model로 바꾸려 하면 foreign key, migration dependency, 기존 데이터 이동 문제를 함께 해결해야 합니다. 처음부터 custom user model을 사용하면 이러한 중간 교체 문제를 피할 수 있습니다.

이 project에서는 기능 차이가 작더라도 "나중에 바꿀 수 있으니 우선 기본 user를 사용한다"는 접근보다 초기 단계에서 user model을 확정하는 방식을 선택합니다.

### 공개 query를 한곳에서 사용합니다

HTML 목록과 JSON API는 `filter_published_entries()`를 함께 사용합니다.

이 함수가 다음과 같은 공개 조회 조건을 한곳에서 책임지도록 합니다.

- draft 제외
- 검색 조건
- Category/Tag filter
- 필요한 relation loading

HTML view와 API가 각각 같은 조건을 다시 구현하면 시간이 지나면서 한쪽만 수정될 수 있습니다. 예를 들어 HTML에서는 draft를 숨기지만 API에서는 빠뜨리는 문제가 발생할 수 있습니다.

따라서 "어떤 row가 공개 대상인가"라는 조회 규칙은 재사용하고, 최종 표현만 HTML template과 JSON response로 나눕니다.

### Form과 database constraint가 서로 다른 경계에서 오류를 막습니다

Form validation과 database constraint는 같은 역할을 중복해서 수행하는 것이 아니라 서로 다른 경계를 보호합니다.

Form은 사용자 입력 단계에서 빠르고 이해하기 쉬운 오류를 보여 주는 역할을 합니다.

예를 들어 rating이 허용 범위를 벗어났다면 database 오류가 발생할 때까지 기다리지 않고 form 단계에서 사용자에게 설명할 수 있습니다.

하지만 form만으로는 모든 write를 보호할 수 없습니다.

다음 경로는 HTML form을 거치지 않을 수 있습니다.

- Django admin
- management command
- script
- 다른 내부 코드
- 동시에 들어온 요청

따라서 rating 범위와 `(entry, author)` 중복 같은 핵심 invariant는 database constraint로도 보호합니다.

즉 다음과 같이 역할을 나눕니다.

```text
Form validation
→ 사용자에게 빠르고 이해하기 쉬운 오류 제공

Database constraint
→ 어떤 write 경로에서도 핵심 데이터 규칙을 최종 보장
```

### Object ownership은 URL만으로 신뢰하지 않습니다

후기 수정·삭제에서는 URL에 포함된 `Review` 식별자만으로 권한을 인정하지 않습니다.

인증된 사용자가 실제 `Review.author`인지 확인해야 합니다. URL을 알고 있다는 사실과 해당 object를 변경할 권한이 있다는 사실은 서로 다릅니다.

`ReviewAuthorRequiredMixin`은 이 ownership 검사를 view마다 반복하지 않도록 공통화하는 역할을 합니다.

### 제보 검수는 service function에서 처리합니다

Admin action은 `Submission` 상태를 직접 바꾸지 않고 `approve_submission()`과 `reject_submission()`을 호출합니다.

service function은 다음과 같이 한 operation에 묶여야 하는 규칙을 담당합니다.

- staff 권한 확인
- 대상 row lock
- 현재 moderation 상태 확인
- `Entry` 생성
- 처리 상태 변경
- 검수자 기록

이렇게 하면 admin 이외의 다른 호출 경로가 생겨도 같은 검수 규칙을 재사용할 수 있습니다.

### 승인은 게시와 다릅니다

제보 승인 시 생성되는 `Entry`는 draft 상태입니다.

따라서 다음 두 결정은 구분됩니다.

```text
Submission 승인
→ catalog 항목으로 받아들일 가치가 있다고 판단

Entry 게시
→ 일반 사용자에게 공개할 준비가 되었다고 판단
```

이 구분을 두면 제보 내용을 승인한 뒤에도 제목, 설명, Category, Tag 등 실제 게시 정보를 검토할 수 있습니다.

### JSON API는 HTML과 별개의 공개 정책을 만들지 않습니다

JSON API는 read-only이며, HTML 목록과 같은 공개 query를 사용합니다.

따라서 API를 추가하는 목적은 별도의 데이터 접근 정책을 만드는 것이 아니라 같은 공개 데이터를 다른 표현 형식으로 제공하는 것입니다.

API가 별도 frontend에서 사용되기 시작하면 response field 이름과 의미가 consumer와의 계약이 되므로, HTML template context보다 변경에 더 신중해야 합니다.

## 요청 처리 흐름

주요 기능을 전체 흐름으로 보면 다음과 같습니다.

### 공개 목록 조회

```text
HTTP GET
→ URL routing
→ EntryListView
→ filter_published_entries()
→ 공개 가능한 QuerySet
→ pagination
→ template rendering
→ HTML response
```

### JSON 목록 조회

```text
HTTP GET
→ URL routing
→ entry_list_api
→ filter_published_entries()
→ 공개 가능한 QuerySet
→ pagination
→ 필요한 field만 JSON으로 변환
→ JSON response
```

두 경로의 핵심 차이는 공개 데이터를 찾는 방식이 아니라 최종 표현 형식입니다.

### 후기 작성

```text
authenticated user
→ ReviewForm validation
→ application-level permission/ownership rule
→ database constraint
→ Review 저장
```

Form validation을 통과했다고 database invariant 검증이 불필요해지는 것은 아닙니다.

### 제보 승인

```text
staff admin action
→ approve_submission()
→ transaction 시작
→ 대상 Submission 상태 확인/lock
→ draft Entry 생성
→ Submission 승인 상태와 검수 정보 기록
→ commit
```

중간 단계에서 오류가 발생하면 operation 전체가 완료된 것처럼 보이지 않도록 transaction 경계 안에서 처리합니다.

## 범위와 제한

이 project는 Django application의 핵심 경계를 학습하기 위한 범위를 유지하며 다음 기능은 포함하지 않습니다.

- File upload
- Review 평균 점수 cache
- token 기반 API 인증
- CORS 설정
- Email verification
- password reset용 mail server
- social login
- Background task
- 별도 cache server
- WebSocket

Review 평균 점수는 별도 cache field에 저장하지 않고 필요할 때 aggregate합니다. 따라서 이 project에서는 cache invalidation 문제보다 ORM aggregate 동작과 query 비용을 직접 관찰하는 데 집중합니다.

JSON API는 read-only입니다. Browser에서 다른 origin의 frontend가 이 API를 직접 호출하려면 별도의 CORS 정책이 필요하지만, 이 project 자체는 그 설정을 제공하지 않습니다.

SQLite에서는 PostgreSQL과 동일한 row-level lock 동작을 검증할 수 없습니다. 따라서 transaction code가 존재한다는 사실과 특정 database의 concurrency semantics가 검증되었다는 사실을 구분해야 합니다.
