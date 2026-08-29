# 인증, session과 CSRF

## 학습 목표

- 인증과 권한 검사를 구분합니다.
- Django session이 로그인 상태를 request user로 복원하는 과정을 이해합니다.
- password를 직접 저장하거나 비교하지 않습니다.
- 상태를 바꾸는 form에 CSRF token을 포함합니다.

## 인증

인증은 요청한 사용자가 누구인지 확인하는 작업입니다. Django의 `authenticate()`와 `login()`은 configured authentication backend와 session을 사용합니다.

Password는 평문으로 저장하지 않습니다. `UserCreationForm`, `set_password()`, `check_password()`를 사용하면 configured password hasher가 적용됩니다.

## Session

로그인에 성공하면 session key가 cookie로 전달됩니다. 다음 요청에서 `SessionMiddleware`와 `AuthenticationMiddleware`가 session을 읽어 `request.user`를 설정합니다.

- 인증됨: `request.user.is_authenticated`가 `True`
- 인증되지 않음: `AnonymousUser`

Session cookie가 탈취되면 로그인 상태도 탈취될 수 있습니다. 운영에서는 HTTPS와 secure cookie 설정이 필요합니다.

## Login 제한

Function view에서는 decorator를 사용할 수 있습니다.

```python
@login_required
def submit_entry(request):
    ...
```

Class-based view에서는 mixin을 가장 왼쪽에 둡니다.

```python
class SubmissionCreateView(LoginRequiredMixin, CreateView):
    ...
```

비로그인 사용자는 `LOGIN_URL`로 이동하고 원래 URL이 `next` parameter에 들어갑니다.

## CSRF

사용자가 로그인한 사이트에 공격자가 다른 사이트에서 POST 요청을 보내는 일을 막기 위해 CSRF token을 검사합니다.

```django
<form method="post">
  {% csrf_token %}
  ...
</form>
```

`CsrfViewMiddleware`를 제거하거나 view 전체에 `csrf_exempt`를 붙여 오류를 피하지 않습니다. 별도 frontend에서 cookie 기반 인증으로 write API를 호출한다면 CSRF token 전달 방법을 함께 설계해야 합니다.

## Logout

Logout은 session 상태를 바꾸므로 POST form으로 호출합니다.

```django
<form method="post" action="{% url 'logout' %}">
  {% csrf_token %}
  <button type="submit">로그아웃</button>
</form>
```

## Custom user

Project 시작 시 `AbstractUser`를 상속한 `accounts.User`를 만들고 `AUTH_USER_MODEL`을 설정합니다. 다른 model의 relation은 `settings.AUTH_USER_MODEL`을 참조합니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/auth/
- https://docs.djangoproject.com/en/5.2/topics/http/sessions/
- https://docs.djangoproject.com/en/5.2/howto/csrf/
