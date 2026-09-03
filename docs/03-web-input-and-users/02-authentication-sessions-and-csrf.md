# 인증, session과 CSRF

## 학습 목표

- 인증(authentication)과 권한 검사(authorization)를 구분합니다.
- Django가 로그인 성공 정보를 session에 저장하고, 이후 요청에서 `request.user`를 복원하는 과정을 이해합니다.
- password를 직접 저장하거나 평문으로 비교하지 않습니다.
- 로그인이 필요한 view와 권한이 필요한 동작을 구분해 보호합니다.
- 상태를 바꾸는 cookie 기반 요청에 CSRF 보호가 필요한 이유를 이해합니다.
- custom user model을 프로젝트 초기에 설정해야 하는 이유를 이해합니다.

## 인증과 권한 검사

**인증(authentication)**은 요청한 사용자가 누구인지 확인하는 작업입니다.

예를 들어 로그인 화면에서 username과 password를 받아 실제 사용자 계정인지 확인하는 것이 인증입니다.

**권한 검사(authorization)**는 인증된 사용자가 특정 작업을 수행해도 되는지 판단하는 작업입니다.

예를 들어 다음 두 조건은 서로 다릅니다.

```text
로그인했는가?                 → 인증 상태 확인
이 글을 수정할 수 있는가?    → 권한 확인
```

따라서 `request.user.is_authenticated`가 `True`라는 사실만으로 사용자가 모든 객체를 수정하거나 삭제할 수 있는 것은 아닙니다. 객체의 소유자, 역할, Django permission 등 애플리케이션의 규칙에 따라 별도의 권한 검사가 필요합니다.

## Django의 로그인 흐름

일반적인 로그인 흐름은 다음과 같습니다.

```text
로그인 form 제출
→ authenticate()
→ authentication backend가 자격 증명 확인
→ User 반환
→ login()
→ 로그인 정보를 session에 기록
→ 응답에서 session cookie 전달
```

예를 들면 다음과 같습니다.

```python
from django.contrib.auth import authenticate, login

user = authenticate(
    request,
    username=username,
    password=password,
)

if user is not None:
    login(request, user)
```

`authenticate()`는 설정된 authentication backend를 차례로 사용해 전달된 자격 증명을 검사합니다. 인증에 성공하면 보통 `User` 객체를 반환하고, 실패하면 `None`을 반환합니다.

`login()`은 password를 다시 검사하는 함수가 아닙니다. 이미 인증된 사용자의 식별 정보 등을 현재 session에 기록하여 이후 요청에서도 로그인 상태를 유지하도록 합니다.

애플리케이션에서 password를 직접 조회하여 다음처럼 비교하지 않습니다.

```python
# 잘못된 방식
if user.password == submitted_password:
    ...
```

Django의 `user.password`에는 일반적으로 평문 password가 아니라 hasher 정보와 salt를 포함한 hash 표현이 저장되므로 평문 비교 자체가 올바르지 않습니다.

## Password 저장과 검증

Password는 평문으로 저장하지 않습니다.

사용자를 생성하거나 password를 변경할 때는 Django가 제공하는 API를 사용합니다.

```python
user.set_password("new-password")
user.save()
```

Password가 맞는지 확인해야 하는 코드에서는 다음 API를 사용합니다.

```python
if user.check_password(submitted_password):
    ...
```

회원가입 form에서는 `UserCreationForm`을 사용할 수 있습니다.

이 API들은 프로젝트에 설정된 password hasher를 사용합니다. 따라서 애플리케이션 코드가 직접 hash 알고리즘이나 salt를 관리할 필요가 없습니다.

로그인 처리 자체는 가능한 한 `authenticate()`를 사용합니다. 그래야 설정된 authentication backend의 정책을 그대로 적용할 수 있습니다.

## Session

HTTP 요청 자체에는 "이 요청이 이전 요청의 로그인 사용자와 같은 사용자다"라는 상태가 자동으로 유지되지 않습니다. Django는 session을 이용해 여러 요청 사이에서 상태를 연결합니다.

일반적인 server-side session backend에서는 browser가 session 식별자가 들어 있는 cookie를 보내고, Django가 그 식별자를 이용해 server 쪽 session 데이터를 찾습니다.

```text
첫 로그인 요청
→ login()이 session에 인증 정보 저장
→ browser가 session cookie 보관

다음 요청
→ browser가 session cookie 전송
→ SessionMiddleware가 session 복원
→ AuthenticationMiddleware가 인증 사용자 복원
→ request.user 설정
```

실제 session 데이터가 어디에 저장되는지는 설정한 session backend에 따라 달라집니다. 기본 database backend를 사용할 수도 있고 cache, file, signed cookie 등의 backend를 사용할 수도 있습니다. 따라서 "모든 session 데이터가 cookie 안에 저장된다"고 이해하면 안 됩니다.

### Middleware의 역할

`SessionMiddleware`는 요청에 `request.session`을 제공합니다.

`AuthenticationMiddleware`는 그 session의 인증 정보를 사용해 `request.user`를 설정합니다. 이 middleware는 session을 사용하므로 일반적으로 `SessionMiddleware`보다 뒤에 위치해야 합니다.

요청을 처리할 때 결과는 다음과 같습니다.

- 인증된 사용자: `request.user.is_authenticated`가 `True`
- 인증되지 않은 사용자: `request.user`가 `AnonymousUser`

`is_authenticated`는 method가 아니라 boolean 성격의 property이므로 다음처럼 사용합니다.

```python
if request.user.is_authenticated:
    ...
```

## Session cookie 보안

Session cookie를 탈취한 공격자는 password를 알지 못하더라도 해당 session이 유효한 동안 사용자의 로그인 상태를 가장할 수 있습니다.

따라서 운영 환경에서는 HTTPS를 사용하고 cookie 관련 보안 설정을 적절히 구성해야 합니다. 대표적으로 다음 설정을 검토합니다.

```python
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

`Secure` cookie는 HTTPS 연결에서만 cookie가 전송되도록 제한합니다.

또한 session 탈취 위험은 cookie 설정 하나로 완전히 해결되지 않습니다. HTTPS 강제, 적절한 session 만료 정책, XSS 방어 등도 함께 필요합니다.

## Login 제한

단순히 "로그인한 사용자만 접근할 수 있는가"를 검사하려면 Django가 제공하는 도구를 사용할 수 있습니다.

### Function-based view

```python
from django.contrib.auth.decorators import login_required

@login_required
def submit_entry(request):
    ...
```

비로그인 사용자가 이 view에 접근하면 로그인 페이지로 redirect됩니다.

일반적으로 원래 접근하려던 URL이 `next` query parameter로 전달됩니다.

```text
/accounts/login/?next=/entries/submit/
```

로그인 후 이 값을 사용하면 사용자를 원래 페이지로 돌려보낼 수 있습니다.

### Class-based view

Class-based view에서는 `LoginRequiredMixin`을 사용할 수 있습니다.

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView

class SubmissionCreateView(LoginRequiredMixin, CreateView):
    ...
```

`LoginRequiredMixin`은 일반적으로 상속 목록의 가장 왼쪽에 둡니다. Python의 method resolution order(MRO)에 따라 mixin의 `dispatch()` 처리가 먼저 적용되어야 로그인 검사가 정상적으로 실행되기 때문입니다.

단, 로그인 제한은 **인증 여부만 확인**합니다. 예를 들어 특정 게시물을 수정하는 view라면 로그인 여부와 별도로 현재 사용자가 그 게시물을 수정할 권한이 있는지도 검사해야 합니다.

## CSRF

CSRF(Cross-Site Request Forgery)는 사용자가 이미 로그인한 사이트에 대해 공격자가 사용자의 browser를 이용해 원하지 않는 요청을 보내게 만드는 공격입니다.

예를 들어 사용자가 `bank.example`에 로그인한 상태라고 가정합니다. 공격자가 만든 다른 사이트가 사용자의 browser에서 다음과 같은 요청을 유도할 수 있습니다.

```text
공격자 사이트
→ 사용자의 browser가 bank.example에 POST 요청
→ browser는 bank.example의 cookie를 자동으로 함께 전송
```

인증이 cookie에 의존한다면 server는 이 요청에도 사용자의 session cookie를 받을 수 있습니다. 따라서 cookie가 있다는 사실만으로 "사용자가 의도한 요청"이라고 판단할 수 없습니다.

Django의 CSRF 보호는 요청에 공격자가 임의로 알아내기 어려운 CSRF token이 포함되어 있는지 확인하여 이런 요청을 차단합니다.

## Django template에서 CSRF token 사용

Django template의 POST form에는 `{% csrf_token %}`을 넣습니다.

```django
<form method="post">
  {% csrf_token %}
  ...
</form>
```

렌더링된 HTML에는 CSRF token을 담은 hidden input이 포함됩니다.

개념적으로 요청은 다음 조건을 만족해야 합니다.

```text
browser가 보내는 CSRF 관련 cookie
+
form 또는 request header로 제출한 CSRF token
→ Django의 CSRF 검증
```

Django는 token 비교 외에도 HTTPS 요청에서는 Origin 또는 Referer 검사 등 추가 검사를 수행할 수 있습니다.

CSRF token은 사용자 인증 수단이 아닙니다. CSRF 보호와 로그인 검사는 서로 다른 문제를 해결합니다.

```text
인증/session
→ 누구의 요청인가?

CSRF
→ cookie 인증 정보를 악용한 cross-site 위조 요청인가?
```

따라서 CSRF 검사를 통과했다고 해서 사용자가 로그인되어 있거나 해당 작업의 권한을 가지고 있다는 뜻은 아닙니다.

## 상태 변경과 HTTP method

일반적으로 조회처럼 server 상태를 바꾸지 않는 작업은 GET으로 처리하고, 생성·수정·삭제·로그아웃처럼 상태를 바꾸는 작업은 POST 등의 unsafe method로 처리합니다.

다음과 같이 GET 요청만으로 삭제가 일어나도록 만들면 안 됩니다.

```text
GET /entries/10/delete/   # 피해야 함
```

링크를 열거나 crawler가 URL을 방문하는 것만으로도 상태가 바뀔 수 있기 때문입니다.

상태 변경 요청을 POST form으로 만들면 CSRF 보호도 정상적으로 적용할 수 있습니다.

## CSRF 보호를 우회하지 않기

CSRF 오류가 발생한다고 해서 다음과 같이 보호 장치를 제거하는 방식으로 해결하지 않습니다.

```python
@csrf_exempt
def update_entry(request):
    ...
```

또한 프로젝트 전체에서 `CsrfViewMiddleware`를 제거하여 문제를 피해서도 안 됩니다.

먼저 다음을 확인해야 합니다.

- POST form에 `{% csrf_token %}`이 있는가
- JavaScript 요청이라면 CSRF token을 올바른 header로 전달하는가
- cross-origin 요청이라면 origin과 cookie 정책이 올바른가
- proxy와 HTTPS 환경에서 host, scheme, trusted origin 설정이 올바른가

`csrf_exempt`가 필요한 특수한 endpoint도 있을 수 있지만, 해당 endpoint가 왜 CSRF 보호를 적용하지 않아도 안전한지 인증 방식과 threat model을 먼저 설명할 수 있어야 합니다.

## 별도 frontend와 cookie 인증

Django template이 아니라 별도 frontend에서 Django API를 호출하더라도 **browser cookie를 인증 수단으로 사용하고 상태 변경 요청을 보낸다면 CSRF 문제는 그대로 존재합니다.**

예를 들어 JavaScript가 POST 요청을 보낼 때는 프로젝트의 CSRF 전달 규칙에 맞게 token을 읽어 request header에 넣어야 합니다.

개념적인 흐름은 다음과 같습니다.

```text
frontend가 CSRF token 확보
→ POST/PUT/PATCH/DELETE 요청
→ CSRF token을 header에 전달
→ browser가 session cookie 전송
→ Django가 CSRF 검증
→ 인증 및 권한 검사
→ 상태 변경
```

CORS와 CSRF는 같은 개념이 아닙니다. CORS 설정을 허용했다고 해서 CSRF 보호가 자동으로 해결되는 것은 아닙니다.

## Logout

Logout은 현재 로그인 session의 인증 상태를 변경하는 작업이므로 GET 링크보다 POST form으로 호출합니다.

```django
<form method="post" action="{% url 'logout' %}">
  {% csrf_token %}
  <button type="submit">로그아웃</button>
</form>
```

Django의 logout 처리는 session에서 인증 상태를 제거하여 이후 요청에서 사용자가 인증되지 않은 상태가 되도록 합니다.

```text
POST logout
→ CSRF 검증
→ session의 로그인 상태 제거
→ 이후 요청에서 AnonymousUser
```

## Custom user

새 프로젝트에서 custom user model이 필요할 가능성이 있다면 프로젝트 초기에 정의하는 것이 좋습니다.

예를 들어 기본 `AbstractUser`를 상속하여 확장할 수 있습니다.

```python
# accounts/models.py

from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    pass
```

그리고 settings에 설정합니다.

```python
AUTH_USER_MODEL = "accounts.User"
```

`AUTH_USER_MODEL`은 가능하면 **첫 migration을 실행하기 전에** 정합니다. 이미 다른 model과 migration이 기본 `auth.User`를 참조한 뒤 user model을 교체하면 foreign key와 migration dependency를 함께 변경해야 하므로 작업이 훨씬 복잡해집니다.

## 다른 model에서 user 참조

Model field에서 user model과 relation을 만들 때 기본 `User` class를 직접 고정하지 않고 `settings.AUTH_USER_MODEL`을 사용합니다.

```python
from django.conf import settings
from django.db import models

class Entry(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
```

이렇게 하면 프로젝트가 기본 user model을 쓰든 custom user model을 쓰든 relation이 현재 설정을 따릅니다.

실행 중인 Python 코드에서 실제 user model class가 필요하다면 `get_user_model()`을 사용할 수 있습니다.

```python
from django.contrib.auth import get_user_model

User = get_user_model()
```

두 사용 위치를 구분합니다.

```text
model field의 relation 대상
→ settings.AUTH_USER_MODEL

실행 중 실제 User class가 필요함
→ get_user_model()
```

## 전체 요청 흐름 정리

로그인 후 보호된 POST 요청을 처리하는 흐름을 연결하면 다음과 같습니다.

```text
1. 사용자가 로그인 form 제출
2. authenticate()가 자격 증명 확인
3. login()이 인증 정보를 session에 저장
4. browser가 session cookie 보관

5. 사용자가 상태 변경 form 제출
6. browser가 session cookie를 함께 전송
7. SessionMiddleware가 session 복원
8. AuthenticationMiddleware가 request.user 복원
9. CsrfViewMiddleware가 CSRF 조건 검사
10. view에서 로그인 여부와 필요한 권한 검사
11. 허용된 경우에만 상태 변경
```

여기서 각 장치는 서로 다른 책임을 가집니다.

```text
password 검증       → 사용자 신원 확인
session             → 요청 사이에 로그인 상태 유지
request.user        → 현재 요청의 사용자 표현
권한 검사           → 해당 사용자가 이 작업을 해도 되는지 판단
CSRF 보호           → cookie를 악용한 cross-site 위조 요청 차단
```

이 구분을 유지하면 인증 문제, 권한 문제, session 문제, CSRF 문제를 서로 혼동하지 않고 진단할 수 있습니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/auth/
- https://docs.djangoproject.com/en/5.2/topics/http/sessions/
- https://docs.djangoproject.com/en/5.2/howto/csrf/
