# Django 테스트

## 학습 목표

- database를 사용하는 test를 Django가 제공하는 격리된 test database에서 실행합니다.
- model, query, form, view, permission, transaction을 서로 다른 실패 원인으로 나누어 검사합니다.
- Django test client로 URL routing부터 middleware, view, template 또는 JSON response까지 연결된 동작을 확인합니다.
- test 실행 순서, 개발 database의 기존 데이터, 외부 API 상태에 의존하지 않는 재현 가능한 test를 작성합니다.

## Test 실행

기본 test runner는 다음 명령으로 실행합니다.

```sh
python manage.py test
```

Django test runner는 설정된 database를 바탕으로 **별도의 test database**를 준비하고 test를 실행합니다. 따라서 정상적인 test 구성에서는 개발·운영 database의 기존 데이터를 test fixture처럼 사용하지 않습니다.

Django는 기본적으로 `test*.py` 패턴에 맞는 test module을 찾습니다. 예를 들어 다음 파일은 자동 발견 대상입니다.

```text
catalog/
├── tests.py
└── tests/
    ├── test_models.py
    └── test_views.py
```

각 test가 필요한 데이터는 test 내부, `setUp()`, `setUpTestData()`, factory, fixture 등으로 명시적으로 준비해야 합니다. 이렇게 해야 특정 test를 단독 실행하거나 실행 순서가 바뀌어도 같은 결과를 얻을 수 있습니다.

특정 app이나 test class만 실행할 수도 있습니다.

```sh
python manage.py test catalog
python manage.py test catalog.tests.test_views
python manage.py test catalog.tests.test_views.EntryViewTests
```

실패 범위를 좁혀 다시 실행할 때 유용합니다.

## `TestCase`와 database 격리

Database를 사용하는 일반적인 Django test는 `django.test.TestCase`를 사용합니다.

```python
from django.test import TestCase

class EntryModelTests(TestCase):
    def test_entry_is_created_as_draft(self):
        ...
```

`TestCase`는 각 test가 다른 test의 database 변경을 관찰하지 않도록 transaction을 이용해 격리합니다. 따라서 한 test가 만든 row를 다음 test가 전제로 삼아서는 안 됩니다.

여러 test가 공통으로 읽기만 하는 초기 데이터를 준비한다면 `setUpTestData()`를 사용할 수 있습니다.

```python
class EntryModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Backend")
```

반면 `setUp()`은 각 test 실행 전에 다시 호출되므로, test마다 독립적으로 변경할 객체나 client 상태를 준비할 때 적합합니다.

중요한 구분은 다음과 같습니다.

- **일반적인 model/query/view test**: `TestCase`
- **실제 commit, rollback, transaction 경계 자체의 동작을 검증해야 하는 test**: `TransactionTestCase`를 검토

`TestCase` 자체가 transaction 격리를 사용하므로, 실제 transaction commit 발생 여부가 test 대상인 경우에는 그 특성이 결과를 가릴 수 있습니다.

## Test module 분리

Test가 늘어나면 `tests.py` 하나에 모든 test를 계속 추가하기보다 실패 원인과 책임에 따라 module을 나눕니다.

```text
catalog/tests/
├── __init__.py
├── test_models.py
├── test_queries.py
├── test_views.py
├── test_moderation.py
└── test_api.py
```

예를 들면 다음처럼 책임을 구분할 수 있습니다.

- `test_models.py`: model method와 database constraint
- `test_queries.py`: custom manager/queryset, 검색 조건, relation loading
- `test_views.py`: URL, HTTP status, template, context, redirect
- `test_moderation.py`: 승인·거절 service와 permission, transaction
- `test_api.py`: JSON schema, pagination, 공개 범위

목적은 단순히 파일 수를 늘리는 것이 아니라, 실패했을 때 **어느 계층의 계약이 깨졌는지 빠르게 식별하는 것**입니다.

## Model과 constraint

Model test는 정상 저장만 검사하지 않습니다. Database가 반드시 지켜야 하는 불변 조건도 확인합니다.

예를 들어 다음과 같은 조건이 있을 수 있습니다.

- rating은 허용 범위를 벗어날 수 없음
- 같은 `entry`와 `author` 조합의 review는 하나만 존재할 수 있음
- 특정 상태에서는 필수 field가 `NULL`일 수 없음

```python
class ReviewConstraintTests(TestCase):
    def test_rejects_duplicate_review_for_same_entry_and_author(self):
        ...
```

Database constraint 위반으로 `IntegrityError`가 발생하는 상황을 검사할 때는 `TestCase`의 바깥 transaction을 직접 깨뜨리지 않도록 내부 `transaction.atomic()` block에서 예외를 발생시키는 방법이 안전합니다.

```python
from django.db import IntegrityError, transaction

with self.assertRaises(IntegrityError):
    with transaction.atomic():
        Review.objects.create(
            entry=entry,
            author=author,
            rating=5,
        )
```

이 구분이 필요한 이유는 `IntegrityError`가 발생한 transaction은 rollback되기 전까지 정상 query를 계속 수행할 수 없는 상태가 될 수 있기 때문입니다. 내부 `atomic()` block이 rollback되면 바깥 `TestCase` transaction에서는 이후 assertion을 계속 수행할 수 있습니다.

또한 `Model.full_clean()`과 database constraint는 같은 것이 아닙니다. `full_clean()`은 Python/Django validation 단계이고, `UniqueConstraint`, `CheckConstraint`, `NOT NULL` 등은 database가 최종적으로 보장하는 규칙입니다. 어떤 계층의 규칙을 시험하는지 명확히 해야 합니다.

## Query

Query test는 **어떤 row가 결과에 포함되는지**와 **필요한 relation을 어떤 방식으로 읽는지**를 분리해서 확인합니다.

예를 들어 다음을 검사할 수 있습니다.

- 공개 목록에서 `draft`가 제외되는가
- 검색어와 category 조건이 동시에 적용되는가
- tag filter가 중복 row를 만들지 않는가
- 정렬 기준이 의도한 순서인가

```python
results = Entry.objects.published().filter(category=category)

self.assertIn(published_entry, results)
self.assertNotIn(draft_entry, results)
```

Relation loading에서 N+1 query가 다시 생기는 것을 막으려면 `assertNumQueries()`를 사용할 수 있습니다.

```python
with self.assertNumQueries(2):
    entries = list(
        Entry.objects
        .select_related("category")
        .prefetch_related("tags")
    )

    for entry in entries:
        _ = entry.category.name
        list(entry.tags.all())
```

여기서 중요한 것은 queryset을 만드는 행위만 세는 것이 아니라 **실제로 평가하고 relation에 접근하는 코드까지 block 안에 포함하는 것**입니다. Django queryset은 lazy하기 때문에 평가되기 전에는 SQL이 실행되지 않을 수 있습니다.

Query 수는 database backend, Django 버전, 구현 방식에 따라 달라질 수 있으므로 모든 test에 무조건 고정된 숫자를 넣지 않습니다. N+1 방지처럼 실제로 유지해야 하는 query 계획에만 사용합니다.

## View와 permission

Django test client는 별도 HTTP server를 띄우지 않고도 Django의 request 처리 경로를 통해 요청을 보낼 수 있습니다. 따라서 URL routing, middleware, session, authentication, view, template rendering 또는 response 생성을 함께 검사할 수 있습니다.

```python
from django.urls import reverse

response = self.client.get(reverse("catalog:entry-list"))

self.assertEqual(response.status_code, 200)
```

View test에서는 성공 경로뿐 아니라 접근 제어와 실패 경로도 확인합니다.

- 공개된 Entry 목록은 `200`
- 존재하지만 비공개인 draft 상세 URL은 정책에 따라 `404`
- 비로그인 사용자의 후기 작성 요청은 login page로 redirect
- 다른 사용자의 후기 수정 요청은 `403`
- 일반 사용자가 staff 전용 제보 승인 기능을 호출하면 거부됨

Redirect는 status code만 보지 말고 목적지가 중요하다면 `assertRedirects()`로 확인할 수 있습니다.

```python
response = self.client.get(reverse("catalog:review-create"))

self.assertRedirects(
    response,
    f"{reverse('login')}?next={reverse('catalog:review-create')}",
)
```

Login이 필요한 test에서는 실제 password authentication을 거칠 필요가 없다면 `force_login()`을 사용할 수 있습니다.

```python
self.client.force_login(user)
```

### HTTP permission과 service permission 구분

View와 service가 모두 permission을 검사한다면 두 계층의 책임을 섞지 않습니다.

View test에서는 HTTP 결과를 검사합니다.

```python
response = self.client.post(
    reverse("catalog:submission-approve", args=[submission.pk])
)

self.assertEqual(response.status_code, 403)
```

Service test에서는 예외 계약을 직접 검사할 수 있습니다.

```python
from django.core.exceptions import PermissionDenied

with self.assertRaises(PermissionDenied):
    approve_submission(
        submission_id=submission.pk,
        reviewer=ordinary_user,
    )
```

이렇게 나누면 실패 시 routing/view 문제인지, 실제 domain/service permission 규칙 문제인지 구분하기 쉽습니다.

## Form

Form test는 HTTP 요청과 분리해서 **입력값을 어떤 규칙으로 허용하거나 거부하는지** 검사합니다.

```python
form = ReviewForm(
    data={
        "rating": 6,
        "comment": "too high",
    }
)

self.assertFalse(form.is_valid())
```

화면에 표시되는 번역 가능한 error message 전체를 문자열로 고정하기보다, application이 의존하는 validation 종류가 있다면 error code를 확인하는 편이 안정적입니다.

```python
errors = form.errors.as_data()

self.assertEqual(
    errors["rating"][0].code,
    "max_value",
)
```

View test에서 모든 field validation 조합을 반복할 필요는 없습니다.

- **Form test**: 입력 validation 규칙
- **View test**: 올바른 form을 사용하는지, 성공·실패 시 HTTP 흐름이 맞는지

처럼 역할을 나누면 실패 원인이 더 명확해집니다.

## Transaction service

여러 model을 한 번에 변경하는 service는 최종 상태 하나만 보지 말고, transaction 안에서 함께 유지되어야 하는 상태를 모두 검사합니다.

예를 들어 제보 승인 후 다음 조건을 확인할 수 있습니다.

- draft `Entry`가 정확히 한 건 생성됨
- `Submission.status`가 `approved`로 변경됨
- `created_entry`가 새 Entry를 가리킴
- `reviewed_by`가 승인자를 가리킴
- `reviewed_at`가 기록됨

Service 호출 뒤에는 이미 메모리에 있는 model instance를 그대로 믿지 말고 database 상태를 다시 읽어 검사하는 것이 명확합니다.

```python
approve_submission(
    submission_id=submission.pk,
    reviewer=staff_user,
)

submission.refresh_from_db()

self.assertEqual(submission.status, Submission.Status.APPROVED)
self.assertIsNotNone(submission.created_entry)
self.assertEqual(submission.reviewed_by, staff_user)
self.assertIsNotNone(submission.reviewed_at)
```

### 부분 실패도 검사하기

Transaction을 사용하는 이유는 여러 변경 중 일부만 성공한 상태가 남지 않게 하기 위해서입니다. 따라서 필요한 경우 중간 단계에서 예외가 발생했을 때 모든 변경이 rollback되는지도 검사합니다.

예를 들어 Entry 생성 뒤 Submission 갱신에서 실패하도록 구성했다면, 실패 후 새 Entry가 남아 있지 않아야 합니다.

### 같은 요청을 다시 실행하는 경우

같은 제보를 다시 승인하는 동작의 계약도 명시적으로 검사해야 합니다.

예를 들어 service가 중복 승인을 거부하도록 설계되었다면:

```python
approve_submission(
    submission_id=submission.pk,
    reviewer=staff_user,
)

with self.assertRaises(...):
    approve_submission(
        submission_id=submission.pk,
        reviewer=staff_user,
    )
```

그리고 두 번째 호출 뒤에도 새 Entry가 추가되지 않았음을 검사합니다.

핵심은 "두 번째 호출이 성공하는가"가 아니라 **중복 실행이 추가 부작용을 만들지 않는가**입니다. 실제 기대 동작은 service의 상태 전이 규칙에 맞춰 정합니다.

## API

API test에서는 client가 실제로 의존하는 response 계약을 검사합니다.

예를 들어 다음 항목이 대상이 될 수 있습니다.

- HTTP status
- JSON key 이름
- 각 object에 필요한 field
- pagination metadata
- 정렬 순서
- draft 데이터 제외
- 인증·권한 실패 응답

```python
response = self.client.get(reverse("catalog:entry-api"))

self.assertEqual(response.status_code, 200)

payload = response.json()
self.assertIn("results", payload)
self.assertIn("count", payload)
```

HTML response도 마찬가지입니다. 렌더링된 HTML 문자열 전체를 snapshot으로 고정하면 사소한 markup 변경에도 test가 깨질 수 있습니다. 대신 사용자가 실제로 의존하는 계약을 검사합니다.

- status code
- 사용된 template
- 중요한 context 값
- redirect 목적지
- 필요한 HTML element 또는 내용
- JSON field와 값

Test의 목적은 구현 세부사항을 얼리는 것이 아니라, 변경되어서는 안 되는 application 동작을 보호하는 것입니다.

## 외부 상태와 실행 순서에 의존하지 않기

좋은 test는 단독으로 실행해도 결과가 같습니다.

다음과 같은 의존은 피합니다.

- 다른 test가 먼저 생성한 row
- 개발 database에 우연히 존재하는 사용자
- 현재 시각을 그대로 사용한 경계 조건
- 실제 외부 API의 응답
- test 실행 순서
- 로컬 machine에만 존재하는 파일

필요한 입력과 상태는 test가 직접 준비하고, 외부 시스템은 해당 test의 목적에 맞게 fake, stub, mock 등으로 경계를 통제합니다.

특히 model/query test가 외부 네트워크 실패 때문에 깨지거나, view permission test가 현재 운영 데이터 때문에 통과한다면 무엇을 검증하는 test인지 불명확해집니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/testing/
- https://docs.djangoproject.com/en/5.2/topics/testing/overview/
- https://docs.djangoproject.com/en/5.2/topics/testing/tools/
