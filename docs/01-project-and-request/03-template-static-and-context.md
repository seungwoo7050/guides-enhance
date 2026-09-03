# Template, static file과 context

## 학습 목표

- template 상속을 사용해 공통 HTML 구조를 한곳에서 관리합니다.
- view가 준비한 값을 context를 통해 template에 전달하는 흐름을 설명합니다.
- 사용자 입력이 HTML에 출력될 때 Django template의 자동 escaping을 유지해야 하는 이유를 이해합니다.
- app별 template와 static file의 이름이 충돌하지 않도록 namespace 형태로 배치합니다.
- form validation 실패 시 입력값과 오류를 보존하는 이유를 이해합니다.
- 계산, database 조회, 권한 판단 같은 application 로직을 template에 숨기지 않습니다.

## Template 위치

Django는 설정된 template engine의 loader를 사용해 template 파일을 찾습니다. app 내부에 template을 둘 때는 app 이름으로 한 번 더 감싸는 구조가 안전합니다.

```text
catalog/
└── templates/
    └── catalog/
        ├── entry_list.html
        └── entry_detail.html

accounts/
└── templates/
    └── accounts/
        └── signup.html
```

이렇게 하면 서로 다른 app에 같은 파일명이 있어도 실제 template 이름이 달라집니다.

```text
catalog/entry_detail.html
accounts/entry_detail.html
```

반대로 다음처럼 app 이름 없이 바로 `detail.html`을 두면 여러 app에서 같은 이름을 사용할 때 어떤 파일이 먼저 발견되는지에 의존하게 될 수 있습니다.

```text
catalog/templates/detail.html
accounts/templates/detail.html
```

따라서 app별 template에는 일반적으로 다음 형태의 이름을 사용합니다.

```text
<app_name>/<template_name>.html
```

view에서도 같은 전체 경로를 지정합니다.

```python
return render(
    request,
    "catalog/entry_list.html",
    {"entries": entries},
)
```

### 공통 `base.html`

여러 app이 함께 사용하는 공통 layout은 project 수준의 template directory에 둘 수 있습니다.

예를 들어 다음과 같이 구성할 수 있습니다.

```text
templates/
└── base.html
```

그리고 settings의 `TEMPLATES`에서 이 directory를 검색 대상으로 등록합니다.

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                # ...
            ],
        },
    },
]
```

`APP_DIRS=True`이면 설치된 Django app의 `templates/` directory도 탐색할 수 있습니다. 즉, project 공통 template와 app 전용 template를 함께 사용할 수 있습니다.

```text
project 공통 template
    └── templates/base.html

app 전용 template
    └── catalog/templates/catalog/entry_list.html
```

핵심은 `base.html`이 반드시 app 안에 있어야 한다는 것이 아니라, **Django template loader가 찾을 수 있는 directory에 있어야 한다**는 것입니다.

## Template 상속

여러 화면이 공통 header, navigation, message 영역, footer를 사용한다면 각 template에 markup을 복사하지 않고 상속 구조를 만듭니다.

공통 layout은 `base.html`에 둡니다.

```django
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>{% block title %}Catalog{% endblock %}</title>
</head>
<body>
  <header>
    <a href="/">Catalog</a>
  </header>

  <main>
    {% block content %}{% endblock %}
  </main>

  <footer>
    <small>Catalog site</small>
  </footer>
</body>
</html>
```

개별 화면은 `extends`로 부모 template을 지정하고 필요한 block만 채웁니다.

```django
{% extends "base.html" %}

{% block title %}{{ entry.title }}{% endblock %}

{% block content %}
  <h1>{{ entry.title }}</h1>
  <p>{{ entry.description }}</p>
{% endblock %}
```

이 구조에서 다음 부분은 `base.html`이 관리합니다.

```text
DOCTYPE
<html>, <head>, <body>
header
footer
공통 navigation
공통 CSS/JS 연결
```

개별 template은 화면별로 달라지는 부분만 관리합니다.

```text
page title
main content
화면 전용 script 또는 추가 block
```

따라서 공통 markup을 수정해야 할 때 `base.html` 한곳만 변경하면 됩니다.

### `extends`의 위치

Django template에서 `{% extends %}`를 사용할 경우 보통 template의 첫 template tag로 둡니다.

```django
{% extends "base.html" %}
```

부모 template 밖에 일반 HTML을 작성한 뒤 상속하려고 하면 기대한 block 구조로 동작하지 않을 수 있으므로, 상속받는 template은 부모 block을 채우는 형태로 구성하는 것이 명확합니다.

## Context

view와 template의 역할은 구분하는 것이 좋습니다.

```text
view
  ├─ request 해석
  ├─ query 수행
  ├─ 권한과 공개 범위 적용
  ├─ pagination/filter 계산
  └─ template에 필요한 값을 준비
        ↓
      context
        ↓
    template
  └─ 이미 준비된 값을 HTML로 표현
```

view는 `render()`의 세 번째 인자로 context dictionary를 전달할 수 있습니다.

```python
return render(
    request,
    "catalog/entry_list.html",
    {
        "entries": entries,
        "categories": categories,
    },
)
```

이 경우 template에서는 key 이름으로 값을 참조합니다.

```django
{% for entry in entries %}
  <h2>{{ entry.title }}</h2>
{% endfor %}

{% for category in categories %}
  <span>{{ category.name }}</span>
{% endfor %}
```

context는 단순히 "template에서 사용할 변수 모음"이 아니라, **view가 표현 계층에 전달하는 명시적인 데이터 경계**로 이해하는 편이 좋습니다.

### Template에서 복잡한 처리를 피하는 이유

Django template language는 단순한 표현을 지원합니다.

```django
{% if entries %}
  ...
{% endif %}

{% for entry in entries %}
  ...
{% endfor %}
```

간단한 formatting filter도 사용할 수 있습니다.

```django
{{ entry.created_at|date:"Y-m-d" }}
```

하지만 다음과 같은 application 로직을 template에 넣는 것은 피하는 편이 좋습니다.

```text
복잡한 database query
권한 결정
여러 단계의 계산
business rule
pagination 계산
검색 조건 조합
```

예를 들어 template에서 각 row마다 관련 object를 조회하게 만드는 구조는 N+1 query를 만들 수도 있습니다. 필요한 관계는 view/query 계층에서 `select_related()`나 `prefetch_related()` 등을 고려해 준비하는 편이 낫습니다.

```python
entries = (
    Entry.objects.published()
    .select_related("author")
)
```

그 뒤 template은 준비된 값을 표시합니다.

```django
{{ entry.author.username }}
```

핵심은 template을 **application 로직을 실행하는 장소가 아니라 presentation을 담당하는 장소**로 유지하는 것입니다.

## Context processor

모든 view에서 반복해서 필요한 값은 context processor를 통해 공통 context로 제공할 수 있습니다.

Django 기본 설정에서도 `request`, 인증 사용자, message 등을 지원하는 context processor를 사용할 수 있습니다.

예를 들어 인증 middleware와 관련 context processor가 구성되어 있다면 template에서 다음 값을 사용할 수 있습니다.

```django
{% if user.is_authenticated %}
  <span>{{ user.username }}</span>
{% endif %}
```

다만 context processor에 무거운 database query를 넣으면 거의 모든 template rendering에서 해당 query가 실행될 수 있습니다. 따라서 "전역에서 사용 가능하다"는 이유만으로 계산 비용이 큰 값을 넣는 것은 피해야 합니다.

## 자동 escaping

Django template는 변수 출력 시 기본적으로 HTML에서 의미가 있는 문자를 escape합니다.

```django
{{ review.body }}
```

예를 들어 사용자 입력이 다음과 같다고 가정합니다.

```html
<script>alert("xss")</script>
```

자동 escaping이 유지되면 브라우저가 이를 실제 `<script>` element로 해석하지 않도록 HTML special character가 escape된 형태로 출력됩니다.

개념적으로 다음과 같습니다.

```text
<  → &lt;
>  → &gt;
&  → &amp;
"  → &quot;  상황에 따라 escape
'  → &#x27;   상황에 따라 escape
```

따라서 일반적인 사용자 입력은 다음처럼 그대로 출력하는 것이 기본입니다.

```django
<p>{{ review.body }}</p>
```

### `safe` filter의 의미

다음 코드는 해당 값을 HTML로 안전하다고 template engine에 표시합니다.

```django
{{ review.body|safe }}
```

이때 Django는 해당 문자열을 일반 text처럼 escape하지 않습니다. 따라서 `review.body`가 사용자 입력이라면 악성 markup이나 script가 browser에서 실행될 수 있습니다.

즉, `safe`는 "문자열을 안전하게 만들어 주는 filter"가 아닙니다.

```text
safe
  ≠ HTML을 정화(sanitize)함

safe
  = 이 문자열을 이미 신뢰 가능한 HTML로 취급하라고 표시함
```

따라서 신뢰할 수 없는 사용자 입력에 `safe`를 적용해서는 안 됩니다.

### 자동 escaping이 모든 XSS 문제를 해결하는 것은 아니다

자동 escaping은 HTML context에서 매우 중요한 기본 방어이지만, 어떤 위치에 값을 넣는지에 따라 별도의 주의가 필요합니다.

예를 들어 사용자 값을 임의의 JavaScript 코드 안에 직접 삽입하거나, 안전하지 않은 URL scheme을 허용하는 방식은 자동 escaping만으로 충분하지 않을 수 있습니다.

따라서 기본 원칙은 다음과 같습니다.

```text
사용자 입력은 text로 출력
`safe`를 임의로 적용하지 않음
JavaScript에 데이터를 전달할 때는 적절한 JSON 전달 방식을 사용
HTML을 허용해야 한다면 별도의 신뢰 가능한 sanitization 정책을 설계
```

이 문서 범위에서는 우선 **Django의 자동 escaping을 기본 상태로 유지하는 것**을 가장 중요한 원칙으로 기억하면 됩니다.

## Form 출력

Django form을 template에서 출력할 수 있습니다.

```django
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">저장</button>
</form>
```

`{% csrf_token %}`은 CSRF 보호가 활성화된 POST form에 필요한 token을 hidden field로 출력합니다.

`form.as_p`는 form field를 `<p>` 기반 markup으로 간단히 렌더링하는 편의 기능입니다. 실제 application에서는 디자인과 접근성 요구에 따라 field를 직접 렌더링할 수도 있습니다.

```django
<form method="post">
  {% csrf_token %}

  {{ form.non_field_errors }}

  <div>
    {{ form.title.label_tag }}
    {{ form.title }}
    {{ form.title.errors }}
  </div>

  <div>
    {{ form.body.label_tag }}
    {{ form.body }}
    {{ form.body.errors }}
  </div>

  <button type="submit">저장</button>
</form>
```

## Bound form과 validation 오류

POST 요청에서 form에 입력 데이터를 전달하면 **bound form**이 됩니다.

```python
form = EntryForm(request.POST)
```

검증하면 `is_valid()` 결과와 함께 field 오류가 form instance에 저장됩니다.

```python
if form.is_valid():
    ...
```

일반적인 흐름은 다음과 같습니다.

```python
from django.shortcuts import redirect, render


def entry_create(request):
    if request.method == "POST":
        form = EntryForm(request.POST)

        if form.is_valid():
            entry = form.save()
            return redirect(entry)
    else:
        form = EntryForm()

    return render(
        request,
        "catalog/entry_form.html",
        {"form": form},
    )
```

POST validation이 실패하면 새 form을 만들지 않고 **검증에 실패한 기존 `form` 객체를 그대로 template에 전달**합니다.

```text
POST 입력
    ↓
EntryForm(request.POST)
    ↓
validation 실패
    ↓
같은 bound form을 render
    ├─ 사용자가 입력한 값 유지
    └─ validation 오류 유지
```

반대로 validation 실패 뒤 다음처럼 새 form을 만들면 문제가 생깁니다.

```python
form = EntryForm()
```

새 form에는 이전 POST data와 validation error가 없기 때문에 사용자가 입력한 값과 오류 메시지가 사라집니다.

따라서 POST 실패 경로에서는 bound form instance를 유지해야 합니다.

## Static file

CSS, JavaScript, image처럼 application 코드와 함께 배포되는 정적 파일은 Django의 staticfiles 기능으로 관리할 수 있습니다.

app 전용 static file도 template과 비슷하게 app 이름으로 namespace를 두는 것이 좋습니다.

```text
catalog/
└── static/
    └── catalog/
        ├── site.css
        └── catalog.js
```

그 이유는 여러 app의 static directory가 하나의 논리적인 static namespace로 검색되기 때문입니다.

다음처럼 두 app에 같은 이름이 있으면 충돌할 수 있습니다.

```text
catalog/static/site.css
accounts/static/site.css
```

반면 app 이름으로 감싸면 논리적인 static path가 구분됩니다.

```text
catalog/site.css
accounts/site.css
```

## `{% static %}` tag

Template에서 static URL을 직접 문자열로 조립하지 않고 `static` tag를 사용합니다.

```django
{% load static %}

<link
  rel="stylesheet"
  href="{% static 'catalog/site.css' %}"
>
```

`{% load static %}`은 현재 template에서 `static` template tag library를 사용할 수 있게 합니다.

`{% static 'catalog/site.css' %}`는 settings의 static configuration을 기준으로 실제 URL을 만듭니다.

예를 들어 개발 환경에서 `STATIC_URL`이 다음과 같다면,

```python
STATIC_URL = "static/"
```

결과 URL은 구성에 따라 다음과 같은 형태가 될 수 있습니다.

```text
/static/catalog/site.css
```

중요한 점은 template이 `/static/` 문자열을 직접 가정하지 않는다는 것입니다.

```django
{# 피하는 편이 좋은 형태 #}
<link rel="stylesheet" href="/static/catalog/site.css">
```

대신 static 설정을 통해 URL을 계산합니다.

## 개발 환경과 운영 환경의 static file

Django 개발 server는 `django.contrib.staticfiles`가 올바르게 구성되어 있을 때 개발 편의를 위해 static file을 제공할 수 있습니다.

```sh
python manage.py runserver
```

하지만 이것은 운영용 static file serving 구성을 대신하지 않습니다.

운영에서는 일반적으로 `collectstatic` 명령을 사용해 여러 app과 지정된 static directory의 파일을 `STATIC_ROOT` 아래에 모읍니다.

```sh
python manage.py collectstatic
```

개념적인 흐름은 다음과 같습니다.

```text
catalog/static/catalog/site.css
accounts/static/accounts/site.css
project static directories
            │
            │ collectstatic
            ▼
        STATIC_ROOT
            │
            ▼
web server / CDN / object storage 등에서 제공
```

예를 들어 settings에 다음 값을 둘 수 있습니다.

```python
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
```

이때 `STATIC_ROOT`는 개발 중 원본 static 파일을 직접 작성하는 장소라기보다, **배포를 위해 `collectstatic`이 결과 파일을 모으는 대상 directory**로 이해하는 것이 중요합니다.

운영에서는 실제 배포 구조에 따라 web server, CDN, object storage 또는 static file middleware 등의 방식으로 해당 파일을 제공할 수 있습니다.

따라서 다음 두 개념을 구분합니다.

```text
app/static/... 또는 STATICFILES_DIRS
    └─ 원본 static file 위치

STATIC_ROOT
    └─ collectstatic 결과를 모으는 배포용 위치
```

## Message framework

사용자가 POST 요청으로 데이터를 저장하거나 삭제한 뒤 redirect된 다음 화면에서 한 번만 안내를 보여 주고 싶을 수 있습니다.

예를 들어 저장 성공 메시지를 추가할 수 있습니다.

```python
from django.contrib import messages

messages.success(request, "후기를 저장했습니다.")
```

그 뒤 template에서 message를 출력합니다.

```django
{% if messages %}
  <ul>
    {% for message in messages %}
      <li>{{ message }}</li>
    {% endfor %}
  </ul>
{% endif %}
```

전형적인 흐름은 다음과 같습니다.

```text
POST /reviews/new/
    ↓
저장 성공
    ↓
messages.success(...)
    ↓
redirect
    ↓
GET /entries/example/
    ↓
message 출력
```

이 방식은 POST-Redirect-GET 흐름에서도 성공 안내를 다음 GET까지 전달할 수 있게 합니다.

### Message는 영속적인 기록이 아니다

message framework의 목적은 **사용자에게 일시적인 UI 알림을 전달하는 것**입니다.

예를 들어 다음에는 적합합니다.

```text
"후기를 저장했습니다."
"프로필을 수정했습니다."
"항목을 삭제했습니다."
```

하지만 다음 용도로 사용하면 안 됩니다.

```text
감사 로그(audit log)
결제 상태의 유일한 기록
중요한 업무 처리 이력
장기 보관해야 할 오류 기록
```

중요한 처리 결과는 목적에 맞게 database나 log에 영속적으로 기록해야 합니다.

```text
message
  └─ 사용자가 잠시 확인할 UI 피드백

database/log
  └─ 이후에도 남아야 하는 시스템 기록
```

## 전체 연결 관계

이 문서의 요소를 하나의 화면 처리 흐름으로 연결하면 다음과 같습니다.

```text
request
   │
   ▼
view
   │
   ├─ database query
   ├─ filter / pagination
   ├─ form validation
   └─ 권한·공개 범위 결정
   │
   ▼
context
   │
   ▼
template
   │
   ├─ base.html 상속
   ├─ context 값 출력
   ├─ 자동 escaping
   ├─ form 오류 출력
   └─ static URL 생성
   │
   ▼
HTML response
```

저장 성공 뒤 redirect가 필요한 경우에는 message가 다음 요청까지 전달될 수 있습니다.

```text
POST
  ↓
validation 성공
  ↓
저장 + message 추가
  ↓
redirect
  ↓
GET
  ↓
template에서 message 표시
```

역할을 다음처럼 구분하면 코드의 책임이 명확해집니다.

```text
view/query 계층
    └─ 무엇을 보여 줄지 준비

template
    └─ 준비된 값을 어떻게 HTML로 보여 줄지 결정

staticfiles
    └─ CSS/JS/image 같은 정적 자원을 찾고 배포

message framework
    └─ 요청 사이의 일시적인 사용자 알림 전달
```

## 확인할 것

Template과 static file 구성을 만들었다면 다음 사항을 확인합니다.

```text
app별 template path에 app 이름 namespace가 있는가
공통 HTML이 base.html에 모여 있는가
view가 필요한 context를 명시적으로 준비하는가
template에서 불필요한 query나 복잡한 계산을 하지 않는가
사용자 입력에 safe를 적용하지 않았는가
POST validation 실패 시 bound form을 그대로 다시 렌더링하는가
static file에도 app 이름 namespace가 있는가
static URL을 {% static %}으로 생성하는가
운영 배포에서 collectstatic과 STATIC_ROOT의 역할을 구분하는가
message를 영속적인 기록으로 사용하지 않는가
```

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/templates/
- https://docs.djangoproject.com/en/5.2/howto/static-files/
- https://docs.djangoproject.com/en/5.2/ref/contrib/messages/
