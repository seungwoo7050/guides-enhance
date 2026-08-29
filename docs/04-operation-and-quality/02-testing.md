# Django 테스트

## 학습 목표

- database를 사용하는 test는 `django.test.TestCase`로 격리합니다.
- model, query, form, view, permission, transaction을 다른 실패 원인으로 나눠 검사합니다.
- Django test client로 실제 URL과 response를 확인합니다.
- 실행 순서와 외부 데이터에 의존하지 않는 test를 작성합니다.

## Test 실행

```sh
python manage.py test
```

Django test runner는 별도 test database를 만들고 `test*.py`를 찾습니다. 실제 개발 database를 test 데이터로 사용하지 않습니다.

## Test module 분리

Test가 늘어나면 `tests.py` 하나에 계속 추가하지 않습니다.

```text
catalog/tests/
├── test_models.py
├── test_queries.py
├── test_views.py
├── test_moderation.py
└── test_api.py
```

파일 수를 늘리기 위한 구분이 아니라 실패 원인을 빨리 찾기 위한 구분입니다.

## Model과 constraint

```python
class ReviewConstraintTests(TestCase):
    def test_rejects_duplicate_review_for_same_entry_and_author(self):
        ...
```

정상 저장뿐 아니라 rating 범위와 중복 후기 같은 database constraint를 확인합니다. `IntegrityError`를 검사할 때는 깨진 transaction이 다음 assertion에 영향을 주지 않도록 내부 `transaction.atomic()` block을 사용할 수 있습니다.

## Query

Filter가 draft를 제외하는지, 검색과 category/tag가 함께 적용되는지 확인합니다. Relation loading은 `assertNumQueries()`로 N+1 회귀를 찾을 수 있습니다.

Query 수는 database backend와 구현에 따라 달라질 수 있으므로, 실제로 유지하려는 query 계획만 고정합니다.

## View와 permission

Django test client는 route, middleware, session, template rendering까지 연결합니다.

```python
response = self.client.get(reverse("catalog:entry-list"))
self.assertEqual(response.status_code, 200)
```

다음 실패 요청도 포함합니다.

- draft 상세 URL은 404
- 비로그인 후기 작성은 login redirect
- 다른 사용자의 후기 수정은 403
- 일반 사용자의 제보 승인 service 호출은 `PermissionDenied`

## Form

Form test는 입력값과 error code를 확인합니다. View test에서 모든 field validation 조합을 반복할 필요는 없습니다.

## Transaction service

제보 승인 후 다음 세 상태를 함께 검사합니다.

- draft Entry가 한 건 생성됨
- Submission이 approved로 바뀜
- `created_entry`, `reviewed_by`, `reviewed_at`가 기록됨

같은 제보를 다시 승인하면 새 Entry가 추가되지 않아야 합니다.

## API

JSON key, pagination metadata, draft 제외를 확인합니다. HTML 문자열 전체를 snapshot으로 고정하기보다 사용자가 의존하는 status, template, context, JSON field를 검사합니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/testing/
- https://docs.djangoproject.com/en/5.2/topics/testing/overview/
- https://docs.djangoproject.com/en/5.2/topics/testing/tools/
