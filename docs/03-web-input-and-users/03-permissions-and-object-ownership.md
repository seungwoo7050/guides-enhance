# 권한과 object ownership

## 학습 목표

- 로그인 여부와 특정 작업에 대한 권한 검사를 분리합니다.
- 작성자만 자신의 후기(review)를 수정하거나 삭제하도록 제한합니다.
- object ownership을 view와 QuerySet 수준에서 안전하게 검사합니다.
- staff 여부와 Django permission을 구분합니다.
- 화면에서 button을 숨기는 것과 server에서 권한을 강제하는 것이 서로 다른 작업임을 이해합니다.
- 권한 실패 시 403과 404 중 어떤 응답을 사용할지 의도를 갖고 선택합니다.

## 인증과 권한

**인증(authentication)**은 요청한 사용자가 누구인지 확인하는 작업입니다.

**권한 검사(authorization)**는 인증된 사용자가 특정 작업을 수행해도 되는지 판단하는 작업입니다.

```text
로그인했는가?
→ 인증 상태 확인

이 review를 수정할 수 있는가?
→ 권한 확인
```

따라서 로그인한 모든 사용자가 모든 후기를 수정하거나 삭제할 수 있는 것은 아닙니다.

예를 들어 review 작성자만 수정할 수 있다면 다음 조건이 필요합니다.

```python
review.author_id == request.user.id
```

Class-based view에서 `UserPassesTestMixin`을 사용할 경우 다음처럼 작성할 수 있습니다.

```python
def test_func(self):
    return self.get_object().author_id == self.request.user.id
```

이 검사는 단순히 로그인 여부를 확인하는 것이 아니라, **현재 사용자가 현재 object의 소유자인지** 확인합니다.

## 화면 제어와 server 권한 검사는 다르다

Template에서 권한이 없는 사용자에게 수정 button을 숨기는 것은 사용자 경험을 위한 처리입니다.

```django
{% if review.author_id == request.user.id %}
  <a href="{% url 'review-update' review.pk %}">수정</a>
{% endif %}
```

하지만 button이 보이지 않아도 사용자는 URL을 직접 입력하거나 HTTP client를 사용해 요청을 만들 수 있습니다.

```text
화면에서 button 숨김
→ 사용자가 실수로 접근하는 것을 줄임

server에서 권한 검사
→ 실제로 권한 없는 요청을 차단
```

따라서 **보안 규칙은 반드시 server에서 다시 검사해야 합니다.**

Template 조건만으로 권한을 보장해서는 안 됩니다.

## Object ownership

Object ownership은 특정 row가 어느 사용자에게 속하는지를 나타냅니다.

예를 들어 `Review`에 다음 relation이 있다고 가정합니다.

```python
class Review(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
```

이 경우 일반 사용자가 수정하거나 삭제할 수 있는 review를 자신의 row로 제한할 수 있습니다.

```python
Review.objects.filter(author=request.user)
```

`author=request.user`와 `author_id=request.user.id`는 같은 관계를 기준으로 조회하지만, 이미 user object가 있다면 일반적으로 전자가 더 읽기 쉽습니다.

## 먼저 조회한 뒤 검사하는 방식

다음 방식도 권한을 구현할 수 있습니다.

```python
review = get_object_or_404(Review, pk=pk)

if review.author_id != request.user.id:
    raise PermissionDenied
```

이 경우 object가 실제로 존재하지만 소유자가 다르면 403을 반환할 수 있습니다.

```text
object 없음
→ 404 Not Found

object는 있지만 권한 없음
→ 403 Forbidden
```

이 방식은 "resource는 존재하지만 당신에게 권한이 없다"는 의미를 명확히 표현할 수 있습니다.

그러나 object의 존재 여부 자체를 다른 사용자에게 알려 주고 싶지 않은 경우에는 QuerySet 자체를 현재 사용자에게 허용된 범위로 제한하는 방식이 더 적절할 수 있습니다.

## QuerySet에서 처음부터 제한하기

다른 사용자의 object를 먼저 가져온 뒤 검사하는 대신, 처음부터 현재 사용자가 접근할 수 있는 row만 조회할 수 있습니다.

```python
review = get_object_or_404(
    Review,
    pk=pk,
    author=request.user,
)
```

이 경우 다음 두 상황이 모두 404가 됩니다.

```text
해당 pk의 review가 실제로 없음
→ 404

해당 pk의 review는 있지만 다른 사용자의 것임
→ 404
```

따라서 권한이 없는 사용자에게 다른 사용자의 object 존재 여부를 노출하지 않을 수 있습니다.

목록 화면에서도 같은 원칙을 적용합니다.

```python
reviews = Review.objects.filter(author=request.user)
```

이렇게 하면 다른 사용자의 row가 애초에 QuerySet에 포함되지 않습니다.

## 403과 404 선택

권한이 없는 요청에 항상 같은 status code를 사용해야 하는 것은 아닙니다.

### 403 Forbidden

사용자는 인증되었지만 해당 작업을 수행할 권한이 없다는 사실을 명시적으로 알려도 되는 경우에 적합합니다.

```text
resource 존재
+
현재 사용자는 접근 권한 없음
→ 403
```

### 404 Not Found

resource의 존재 여부 자체를 감추고 싶다면 허용된 QuerySet에서만 조회하고 404를 반환할 수 있습니다.

```text
현재 사용자에게 보이는 resource가 아님
→ 없는 것처럼 404
```

어느 쪽을 사용할지는 API와 보안 정책에 따라 결정합니다. 중요한 점은 같은 종류의 endpoint에서 일관된 정책을 유지하는 것입니다.

## `LoginRequiredMixin`과 `UserPassesTestMixin`

로그인한 사용자 중 일부에게만 접근을 허용하려면 두 mixin을 함께 사용할 수 있습니다.

```python
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.views.generic import UpdateView

class ReviewUpdateView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    UpdateView,
):
    model = Review
    fields = ("rating", "body")

    def test_func(self):
        review = self.get_object()
        return review.author_id == self.request.user.id
```

상속 순서에서는 일반적으로 `LoginRequiredMixin`을 먼저 둡니다.

```text
비로그인 사용자
→ LoginRequiredMixin
→ 로그인 화면으로 redirect

로그인했지만 test_func() 실패
→ UserPassesTestMixin
→ 권한 거부
```

Django의 `AccessMixin` 동작상 인증된 사용자가 권한 검사에 실패하면 기본적으로 `PermissionDenied`가 발생하여 403 응답으로 처리됩니다.

`raise_exception = True`는 비로그인 사용자의 경우에도 로그인 화면으로 redirect하지 않고 권한 오류를 발생시키고 싶을 때 영향을 줍니다.

따라서 "인증된 사용자가 권한이 없는데 다시 로그인 화면으로 계속 redirect되는 상황"을 막기 위해 임의로 설정을 추가하기보다, 먼저 mixin의 기본 동작과 상속 순서를 확인해야 합니다.

## `get_object()`에서 ownership 제한하기

`test_func()`에서 object를 가져와 비교하는 대신, view가 조회할 수 있는 object 자체를 제한할 수도 있습니다.

```python
class ReviewUpdateView(LoginRequiredMixin, UpdateView):
    model = Review
    fields = ("rating", "body")

    def get_queryset(self):
        return super().get_queryset().filter(
            author=self.request.user
        )
```

이 방식에서는 다른 사용자의 review가 QuerySet에 포함되지 않으므로 해당 URL을 직접 호출해도 404가 됩니다.

```text
UpdateView가 object 조회
→ 현재 사용자 소유 row만 포함된 QuerySet 사용
→ 다른 사용자 object는 조회되지 않음
```

단순한 "본인 소유 object만 접근 가능" 규칙에서는 이 방식이 읽기 쉽고 안전한 경우가 많습니다.

## 목록 조회에도 ownership을 적용한다

Detail, update, delete view만 보호하고 목록 조회를 제한하지 않으면 다른 사용자의 데이터가 노출될 수 있습니다.

예를 들어 본인의 submission만 보여 주어야 한다면 다음과 같이 제한합니다.

```python
class MySubmissionListView(LoginRequiredMixin, ListView):
    model = Submission

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(author=self.request.user)
        )
```

권한 검사는 "변경 가능한가"뿐 아니라 "조회 가능한가"에도 적용됩니다.

## Staff 권한

`is_staff`는 Django user model이 제공하는 boolean flag입니다.

일반적으로 admin site에 접근 가능한 사용자를 구분할 때 사용합니다.

```python
if not reviewer.is_active or not reviewer.is_staff:
    raise PermissionDenied
```

여기서 두 값은 의미가 다릅니다.

```text
is_active
→ 이 사용자 계정을 활성 사용자로 취급할지 여부

is_staff
→ admin site 접근 자격이 있는 staff인지 여부
```

`is_staff=True`라고 해서 애플리케이션의 모든 작업에 자동으로 권한이 생기는 것은 아닙니다.

예를 들어 submission 승인 기능을 staff에게만 허용한다면 그 규칙을 해당 변경 경로에서 명시적으로 검사해야 합니다.

```python
def approve_submission(*, reviewer, submission):
    if not reviewer.is_active or not reviewer.is_staff:
        raise PermissionDenied

    ...
```

이렇게 service function 자체가 해당 규칙을 책임지도록 설계하면 여러 view나 management command가 같은 service를 호출하더라도 동일한 제약을 유지하기 쉽습니다.

다만 모든 service가 항상 사용자 권한을 검사해야 한다는 뜻은 아닙니다. 중요한 것은 **권한을 어느 계층에서 강제하는지 명확히 정하고, 우회 가능한 호출 경로를 만들지 않는 것**입니다.

## Admin 접근과 실제 작업 권한은 별개다

"이 사용자가 admin 화면에 들어갈 수 있다"는 사실만으로 특정 business operation의 권한을 추론해서는 안 됩니다.

예를 들어 다음 두 규칙은 별개일 수 있습니다.

```text
admin site에 로그인 가능
→ is_staff

submission 승인 가능
→ 프로젝트가 정의한 별도 권한 규칙
```

프로젝트 규모가 커지면 단순한 `is_staff` 대신 Django permission을 사용해 역할을 더 세밀하게 나눌 수 있습니다.

## Django permission

Django는 model마다 기본적으로 다음 permission을 생성합니다.

```text
add
change
delete
view
```

예를 들어 app label이 `reviews`, model이 `Review`라면 다음과 같은 codename이 만들어집니다.

```text
reviews.add_review
reviews.change_review
reviews.delete_review
reviews.view_review
```

사용자는 직접 permission을 가질 수도 있고, 자신이 속한 group을 통해 permission을 받을 수도 있습니다.

```python
request.user.has_perm("reviews.change_review")
```

여러 역할을 관리해야 한다면 group을 사용할 수 있습니다.

```text
Moderators group
→ submissions.change_submission
→ submissions.view_submission
```

이렇게 하면 사용자별로 조건문을 직접 늘리는 대신 역할별 permission을 관리할 수 있습니다.

## Model permission과 object-level permission은 다르다

Django의 기본 `add`, `change`, `delete`, `view` permission은 **model 수준 permission**입니다.

예를 들어 다음 검사는 사용자가 `Review` model을 변경할 permission이 있는지를 확인합니다.

```python
request.user.has_perm("reviews.change_review")
```

하지만 이 검사만으로 다음 규칙이 자동으로 구현되지는 않습니다.

```text
사용자는 자신의 review만 수정 가능
```

이것은 특정 row에 대한 **object-level 규칙**이므로 ownership 검사 같은 별도 로직이 필요합니다.

즉 다음 두 질문을 구분해야 합니다.

```text
Review라는 종류의 데이터를 변경할 수 있는가?
→ model permission

이 특정 Review row를 변경할 수 있는가?
→ object-level authorization
```

Django의 기본 authentication backend는 일반적인 object-level permission을 자동으로 제공하지 않습니다. 그런 정책이 필요하다면 ownership 검사, custom backend, 별도 authorization 계층 등 프로젝트에 맞는 방법을 사용해야 합니다.

## Staff와 superuser

현재 project의 역할을 다음처럼 단순화할 수 있습니다.

- 일반 사용자: 자신의 review와 submission 조회·변경
- staff: admin 접근과 submission 검수
- superuser: Django permission 검사를 사실상 모두 통과하는 관리자

`is_superuser`와 `is_staff`도 같은 의미는 아닙니다.

```text
is_staff
→ admin site 접근 자격

is_superuser
→ 활성 사용자라면 Django permission 검사에서 모든 permission을 가진 것으로 취급
```

일반적으로 superuser는 admin에 접근할 수 있도록 `is_staff=True`도 함께 설정하지만, 두 field가 표현하는 개념은 구분해서 이해하는 것이 좋습니다.

## Draft object 조회 권한

권한 검사는 수정과 삭제에만 필요한 것이 아닙니다.

예를 들어 공개된 `Entry`만 일반 사용자가 볼 수 있고 draft는 작성자나 staff만 볼 수 있다면 detail 조회 자체를 제한해야 합니다.

개념적으로 다음과 같은 규칙이 필요합니다.

```text
published entry
→ 일반 사용자도 조회 가능

draft entry
→ 허용된 사용자만 조회 가능
```

단순히 template에서 draft 내용을 숨기는 것으로는 충분하지 않습니다. View가 실제 object를 조회하고 응답하는 단계에서 권한을 적용해야 합니다.

## 권한 검사는 가능한 한 조회 경계 가까이에 둔다

Object ownership처럼 조회 범위로 표현할 수 있는 규칙은 QuerySet에 반영하면 실수를 줄일 수 있습니다.

```python
Review.objects.filter(author=request.user)
```

이 방식의 장점은 다음과 같습니다.

```text
다른 사용자 row를 가져옴
→ 나중에 검사

보다

처음부터 다른 사용자 row를 조회하지 않음
→ 실수할 여지가 작음
```

그러나 모든 권한 규칙을 QuerySet만으로 표현할 수 있는 것은 아닙니다.

예를 들어 다음과 같은 규칙은 추가 authorization 로직이 필요할 수 있습니다.

```text
작성자 또는 staff만 수정 가능
특정 상태에서는 수정 금지
승인 권한과 거절 권한이 서로 다름
```

따라서 QuerySet 제한과 명시적 권한 검사를 규칙에 맞게 조합합니다.

## Test해야 할 요청

권한 코드는 정상 사용자가 성공하는지만 확인해서는 부족합니다.

다음 요청을 반드시 테스트합니다.

- 비로그인 사용자의 후기 작성
- 다른 사용자의 후기 수정
- 다른 사용자의 후기 삭제
- 다른 사용자의 review detail 직접 접근
- 일반 사용자의 검수 service 호출
- 비활성 사용자의 staff 작업 시도
- draft `Entry` 상세 조회
- 본인 submission 목록에 다른 사용자 row가 포함되는지 여부
- staff와 일반 사용자의 permission 차이
- 권한 없는 object 접근 시 의도한 403 또는 404가 반환되는지 여부

예를 들어 ownership 제한은 다음과 같은 형태로 테스트할 수 있습니다.

```python
def test_user_cannot_update_another_users_review(
    client,
    user,
    other_review,
):
    client.force_login(user)

    response = client.get(
        reverse("review-update", args=[other_review.pk])
    )

    assert response.status_code in {403, 404}
```

실제 테스트에서는 `{403, 404}`처럼 둘 다 허용하기보다 프로젝트가 선택한 정책에 맞춰 하나의 status code를 정확히 기대하는 것이 좋습니다.

```python
assert response.status_code == 404
```

이렇게 해야 나중에 권한 정책이 실수로 바뀌어도 테스트가 이를 발견할 수 있습니다.

## 전체 흐름 정리

Object ownership이 있는 update 요청을 예로 들면 다음 흐름으로 생각할 수 있습니다.

```text
요청 도착
→ 로그인 여부 확인
→ 현재 사용자에게 허용된 QuerySet 구성
→ 대상 object 조회
→ 필요한 추가 권한 검사
→ form validation
→ 저장
```

각 단계의 책임은 다음과 같습니다.

```text
LoginRequiredMixin
→ 인증되지 않은 사용자 차단

QuerySet ownership 제한
→ 다른 사용자의 object가 조회되지 않도록 제한

UserPassesTestMixin / permission 검사
→ QuerySet만으로 표현하기 어려운 권한 규칙 확인

Template의 button 조건
→ 사용자에게 가능한 작업만 보여 주는 UI 처리
```

보안의 기준은 항상 server의 권한 검사입니다. Template에서 보이지 않는다는 사실은 권한을 의미하지 않습니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/auth/default/#permissions-and-authorization
- https://docs.djangoproject.com/en/5.2/topics/class-based-views/mixins/
