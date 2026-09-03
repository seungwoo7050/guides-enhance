# URL, view, request와 response

## 학습 목표

- URL pattern에 이름과 namespace를 부여하고, 요청 URL이 view 인자로 전달되는 과정을 설명합니다.
- view가 `HttpRequest`에서 입력을 읽고 반드시 `HttpResponse` 계열 객체를 반환해야 한다는 점을 이해합니다.
- redirect와 404를 오류 회피가 아니라 의도된 HTTP 동작으로 사용합니다.
- URL 문자열을 직접 조립하지 않고 `reverse()`와 named URL을 사용합니다.
- function-based view와 class-based view에서 query 범위와 저장 시점을 명시적으로 제어합니다.

## 요청 처리 순서

Django의 요청 처리를 단순화하면 다음 흐름으로 볼 수 있습니다.

```text
client
  ↓
web server
  ↓
Django middleware chain
  ↓
root URLconf
  ↓
app URLconf
  ↓
view
  ↓
HttpResponse
  ↓
middleware chain
  ↓
web server
  ↓
client
```

여기서 URLconf는 **요청 path를 어떤 view가 처리할지 결정하는 규칙 집합**입니다. Django는 root URLconf에서 시작해 `include()`된 app URLconf를 따라가며 처음으로 일치하는 URL pattern을 찾습니다.

middleware는 view 바깥을 감싸는 공통 처리 계층입니다. 인증, session, CSRF, security header 같은 기능이 middleware를 통해 요청 또는 response 처리 과정에 참여합니다.

다만 "모든 middleware가 요청 전에 한 번, 응답 후에 한 번씩 동일한 함수를 실행한다"는 뜻은 아닙니다. 각 middleware의 구현에 따라 요청을 다음 계층으로 전달하기 전이나, 반환된 response를 client로 보내기 전에 동작할 수 있습니다.

또한 일부 middleware hook은 URL resolution 뒤, 실제 view 호출 직전에 실행되기도 합니다. 따라서 위 그림은 전체 구조를 이해하기 위한 개념적 순서입니다.

## URLconf

project의 root URLconf는 project 전체의 최상위 경로를 정의하고, 기능별 URL은 각 app의 URLconf에 위임할 수 있습니다.

예를 들어 `config/urls.py`는 다음처럼 구성할 수 있습니다.

```python
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("catalog.urls")),
]
```

`include("catalog.urls")`는 해당 위치부터 남은 URL path의 처리를 `catalog.urls`에 넘깁니다.

예를 들어 app URLconf를 다음처럼 정의할 수 있습니다.

```python
# catalog/urls.py

from django.urls import path

from . import views


app_name = "catalog"

urlpatterns = [
    path("", views.EntryListView.as_view(), name="entry-list"),
    path(
        "entries/<slug:slug>/",
        views.EntryDetailView.as_view(),
        name="entry-detail",
    ),
]
```

`app_name`은 이 app의 **application namespace**를 정의합니다. 따라서 `"entry-detail"`이라는 이름이 다른 app에도 존재하더라도 다음처럼 구분할 수 있습니다.

```text
catalog:entry-detail
accounts:entry-detail
```

named URL과 namespace를 사용하면 Python 코드와 template이 실제 URL 문자열 대신 **논리적인 URL 이름**을 참조할 수 있습니다.

### Path converter

다음 pattern을 살펴봅니다.

```python
path(
    "entries/<slug:slug>/",
    views.EntryDetailView.as_view(),
    name="entry-detail",
)
```

`<slug:slug>`는 다음 두 부분으로 나뉩니다.

```text
<converter:argument_name>
     │          │
     │          └─ view에 전달할 keyword argument 이름
     └─ URL 값의 형식을 검사하고 변환하는 converter
```

예를 들어 요청이 다음과 같다면,

```text
/entries/django-urls/
```

URL resolver는 `slug` 값이 `slug` converter의 형식에 맞는지 검사한 뒤 view에 다음과 같이 전달합니다.

```python
slug="django-urls"
```

기본 `slug` converter는 ASCII 문자, 숫자, 하이픈(`-`), 밑줄(`_`)로 구성된 slug 문자열을 매칭합니다.

중요한 점은 converter가 **URL의 문법적 형식만 확인한다**는 것입니다.

```text
/entries/django-urls/
         │
         ├─ 올바른 slug 형식인가?      → URL converter가 검사
         └─ 실제 Entry가 존재하는가?   → view/query가 검사
```

따라서 converter가 성공했다고 해서 해당 database row가 존재하거나, 현재 사용자에게 공개되어 있다는 뜻은 아닙니다.

일치하는 URL pattern 자체가 없다면 Django는 최종적으로 404 response를 반환합니다.

## `HttpRequest`와 view

Django view는 요청을 받아 HTTP response를 만드는 코드입니다.

function-based view의 기본 형태는 다음과 같습니다.

```python
def my_view(request, ...):
    ...
    return response
```

첫 번째 인자인 `request`는 `HttpRequest` 객체입니다. 여기에는 요청 method, query string, POST form data, header, cookie, 인증된 사용자 등 요청 처리에 필요한 정보가 들어 있습니다.

대표적인 값은 다음과 같습니다.

```python
request.method
request.GET
request.POST
request.headers
request.COOKIES
request.user
```

예를 들어 query string이 다음과 같다면,

```text
/search/?q=django&page=2
```

view에서는 `request.GET`을 통해 읽을 수 있습니다.

```python
query = request.GET.get("q", "")
page = request.GET.get("page", "1")
```

`request.GET`과 `request.POST`의 값은 기본적으로 문자열로 들어옵니다. 따라서 정수, 날짜, 선택값처럼 형식 검증이 필요한 입력은 form이나 serializer 등의 검증 계층을 통해 처리하는 편이 안전합니다.

view는 처리 결과로 `HttpResponse` 또는 그 subclass를 반환해야 합니다. `render()`, `redirect()`, `JsonResponse` 같은 도구도 결국 Django가 처리할 수 있는 response 객체를 만듭니다.

## 상세 view와 404

공개된 항목 하나를 조회하는 function-based view는 다음처럼 작성할 수 있습니다.

```python
from django.shortcuts import get_object_or_404, render

from .models import Entry


def entry_detail(request, slug):
    entry = get_object_or_404(
        Entry.objects.published(),
        slug=slug,
    )

    return render(
        request,
        "catalog/entry_detail.html",
        {"entry": entry},
    )
```

여기서 중요한 것은 `get_object_or_404()`의 첫 번째 인자로 **전체 `Entry`가 아니라 공개 가능한 queryset**을 넘겼다는 점입니다.

```python
Entry.objects.published()
```

따라서 다음 두 경우를 client 입장에서는 동일하게 404로 처리할 수 있습니다.

```text
slug에 해당하는 row가 없음
slug에는 해당하지만 published queryset에는 포함되지 않음
```

즉, URL converter는 입력 형식을 제한하고, queryset은 **어떤 object를 조회 가능한 대상으로 볼 것인지** 제한합니다.

### 404는 정상적인 HTTP 결과일 수 있다

404는 항상 서버 코드의 버그를 뜻하지 않습니다.

다음과 같은 상황에서는 의도된 response가 될 수 있습니다.

- 요청한 route가 존재하지 않음
- 요청한 object가 존재하지 않음
- 이미 삭제된 object를 요청함
- 현재 공개 범위에 포함되지 않는 object를 요청함

특히 비공개 object에 대해 사용자가 존재 여부 자체를 알아서는 안 되는 정책이라면, 권한 부족을 403으로 구분하는 대신 **조회 가능한 queryset에서 제외하여 404로 처리**할 수도 있습니다.

다만 이것은 모든 권한 오류를 무조건 404로 바꾸라는 뜻은 아닙니다. 사용자가 object의 존재를 알아도 되고, "존재하지만 이 작업을 수행할 권한이 없다"는 사실을 구분해야 한다면 403이 더 적절할 수 있습니다.

## Class-based view

Django의 class-based view(CBV)는 HTTP 요청 처리에서 반복되는 구조를 class와 method로 구성할 수 있게 합니다.

특히 목록, 상세, 생성, 수정, 삭제 같은 일반적인 화면에는 generic view를 사용할 수 있습니다.

예를 들어 공개된 항목의 목록만 보여 주는 view는 다음처럼 작성할 수 있습니다.

```python
from django.views.generic import ListView

from .models import Entry


class EntryListView(ListView):
    model = Entry
    paginate_by = 20

    def get_queryset(self):
        return Entry.objects.published()
```

`ListView`는 목록 조회, pagination, template rendering 같은 반복 구조를 제공하지만 **도메인에 맞는 공개 범위나 권한 조건까지 자동으로 결정하지는 않습니다.**

다음 코드는 모든 `Entry`가 기본 queryset에 포함될 수 있습니다.

```python
class EntryListView(ListView):
    model = Entry
```

따라서 공개 상태, tenant, 소유자처럼 요청마다 조회 범위를 제한해야 한다면 `get_queryset()`을 명시적으로 재정의해야 합니다.

```python
def get_queryset(self):
    return Entry.objects.published()
```

사용자별 object라면 예를 들어 다음과 같이 요청 사용자 기준으로 제한할 수 있습니다.

```python
def get_queryset(self):
    return Entry.objects.filter(owner=self.request.user)
```

핵심은 **generic view가 HTTP 처리의 반복을 줄여 줄 뿐, application의 접근 정책까지 대신 결정하지는 않는다**는 것입니다.

## 생성 view와 `form_valid()`

생성·수정 generic view는 유효한 form을 저장하는 흐름도 제공할 수 있습니다. 그러나 `request.user`처럼 사용자가 form field로 직접 보내서는 안 되는 값은 server가 설정해야 합니다.

예를 들어 다음과 같이 작성할 수 있습니다.

```python
from django.views.generic import CreateView

from .models import Entry


class EntryCreateView(CreateView):
    model = Entry
    fields = ["title", "body"]

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
```

여기서 `author`를 form field에 포함하지 않았다는 점이 중요합니다.

```text
client가 입력
    ├─ title
    └─ body

server가 결정
    └─ author = request.user
```

사용자가 임의의 다른 사용자 ID를 보내 `author`를 지정하게 두는 대신, 인증된 `request.user`를 server가 저장 대상으로 지정합니다.

`form_valid()`은 **form validation이 성공한 뒤 호출되는 hook**입니다. 따라서 저장 직전에 request에서 얻은 값을 model instance에 설정하는 용도로 사용할 수 있습니다.

## GET과 POST

HTTP method는 요청이 어떤 의미를 가지는지 표현합니다.

일반적인 Django HTML form 흐름에서는 다음처럼 구분합니다.

- `GET`: 조회와 같이 server 상태를 변경하지 않는 요청
- `POST`: 생성, 수정, 삭제 같은 상태 변경을 요청하거나 form data를 제출하는 요청

예를 들어 검색은 일반적으로 GET이 적절합니다.

```text
GET /search/?q=django
```

URL 자체에 검색 조건이 남기 때문에 bookmark하거나 공유하기 쉽습니다.

반면 새 후기를 작성하는 요청은 POST가 적절합니다.

```text
POST /entries/django/reviews/
```

### GET 요청에서 상태를 바꾸지 않는다

다음과 같은 URL을 클릭하는 것만으로 데이터를 삭제하도록 만들면 안 됩니다.

```text
GET /entries/10/delete/
```

GET은 crawler, browser prefetch, cache 같은 HTTP 구성 요소에서도 조회 요청으로 취급될 수 있습니다. 상태 변경 작업은 GET과 분리해야 합니다.

전통적인 HTML form은 주로 GET과 POST를 직접 지원하므로 Django의 일반적인 form 기반 화면에서는 상태 변경을 POST로 처리하는 경우가 많습니다.

## POST-Redirect-GET

POST로 저장을 성공시킨 뒤 동일한 form 화면을 `200 OK`로 바로 반환하는 대신 redirect를 사용하는 패턴을 **POST-Redirect-GET(PRG)**이라고 합니다.

```text
1. client
   │
   │ POST /entries/new/
   ▼
2. server
   │
   │ 저장 성공
   │ 302 redirect
   ▼
3. client
   │
   │ GET /entries/example/
   ▼
4. server
   │
   │ 200 response
   ▼
5. 결과 화면
```

이 방식의 중요한 효과는 저장 결과 화면을 새로고침할 때 browser가 마지막 POST를 그대로 다시 전송해야 하는 상황을 줄이는 것입니다.

즉,

```text
POST
→ 저장
→ redirect
→ GET
```

형태로 성공 경로를 구성합니다.

다만 redirect 자체가 중복 저장을 완전히 방지하는 것은 아닙니다. 사용자가 POST를 빠르게 여러 번 보내거나 network retry가 발생하는 경우까지 막으려면 별도의 중복 제출 방지나 idempotency 설계가 필요할 수 있습니다.

PRG는 주로 **browser 새로고침으로 동일 POST가 다시 제출되는 문제를 피하기 위한 기본적인 UI 흐름**으로 이해하면 됩니다.

## URL reverse

다음과 같이 URL 문자열을 Python 코드 곳곳에 직접 작성하면 URL 구조가 변경될 때 관련 코드를 모두 찾아 수정해야 합니다.

```python
url = f"/entries/{entry.slug}/"
```

대신 URLconf에 선언한 이름을 사용해 URL을 역으로 계산합니다.

```python
from django.urls import reverse


url = reverse(
    "catalog:entry-detail",
    kwargs={"slug": entry.slug},
)
```

여기서 `"catalog:entry-detail"`은 다음 의미입니다.

```text
catalog : entry-detail
   │          │
   │          └─ URL pattern의 name
   └─ app namespace
```

그리고 `kwargs={"slug": entry.slug}`는 URL pattern의 `<slug:slug>` 자리를 채웁니다.

예를 들어 URLconf가 다음과 같다면,

```python
path(
    "entries/<slug:slug>/",
    views.EntryDetailView.as_view(),
    name="entry-detail",
)
```

다음 호출은 해당 pattern을 기준으로 URL을 만듭니다.

```python
reverse(
    "catalog:entry-detail",
    kwargs={"slug": "django-urls"},
)
```

결과는 현재 URLconf 정의에 따라 다음과 같은 path가 됩니다.

```text
/entries/django-urls/
```

이후 URL 구조를 다음처럼 변경하더라도,

```python
path(
    "articles/<slug:slug>/",
    views.EntryDetailView.as_view(),
    name="entry-detail",
)
```

URL 이름과 인자 규약을 유지했다면 `reverse("catalog:entry-detail", ...)`을 호출하는 코드는 변경할 필요가 없습니다.

즉, `reverse()`의 목적은 **URL을 문자열 조립 규칙이 아니라 URLconf의 이름을 기준으로 생성하는 것**입니다.

template에서는 같은 원리를 `{% url %}` tag로 사용할 수 있습니다.

```django
<a href="{% url 'catalog:entry-detail' slug=entry.slug %}">
  {{ entry.title }}
</a>
```

## `get_absolute_url()`

model에 해당 object의 대표 URL을 정의하고 싶다면 `get_absolute_url()`을 구현할 수 있습니다.

```python
from django.db import models
from django.urls import reverse


class Entry(models.Model):
    slug = models.SlugField(unique=True)

    def get_absolute_url(self):
        return reverse(
            "catalog:entry-detail",
            kwargs={"slug": self.slug},
        )
```

그러면 object가 자신의 canonical detail URL을 다음처럼 제공할 수 있습니다.

```python
entry.get_absolute_url()
```

일부 generic editing view는 성공 URL을 별도로 지정하지 않은 경우 저장된 object의 `get_absolute_url()`을 이용할 수 있습니다.

따라서 다음 두 개념은 역할이 다릅니다.

```text
reverse(...)
    └─ named URL과 인자로 URL을 계산

model.get_absolute_url()
    └─ 특정 model instance의 대표 URL을 제공
```

`get_absolute_url()` 내부에서도 URL 문자열을 직접 조립하기보다 `reverse()`를 사용하는 것이 좋습니다.

## Redirect

redirect는 client에게 "이 요청의 다음 위치로 이동하라"고 알리는 HTTP response입니다.

Django에서는 예를 들어 다음처럼 사용할 수 있습니다.

```python
from django.shortcuts import redirect


def create_entry(request):
    ...
    return redirect("catalog:entry-detail", slug=entry.slug)
```

기본적인 `redirect()`는 일반적으로 302 redirect response를 만듭니다.

중요한 점은 redirect가 server 내부에서 다른 view를 직접 실행하는 것과 다르다는 것입니다.

```text
server가 redirect response 반환
        ↓
client가 Location header 확인
        ↓
client가 새 URL로 별도 요청
```

따라서 PRG 흐름에서는 POST 처리 후 redirect response를 받은 browser가 새 URL에 GET 요청을 보냅니다.

## HTTP status code

HTTP status code는 response의 결과를 client에게 기계적으로 전달하는 값입니다.

이 문서에서 자주 사용하는 status는 다음과 같습니다.

| Status | 의미 | 예 |
|---|---|---|
| `200 OK` | 요청을 정상 처리함 | 목록·상세 화면 조회 |
| `302 Found` | 다른 URL로 임시 redirect | form 저장 후 detail page 이동 |
| `400 Bad Request` | 요청 자체의 형식이나 의미를 처리할 수 없음 | 잘못된 형식의 API 요청 |
| `403 Forbidden` | 요청은 이해했지만 해당 작업을 허용하지 않음 | 권한 없는 수정 요청 |
| `404 Not Found` | route 또는 조회 가능한 resource를 찾지 못함 | 없는 slug, 공개되지 않은 object |

상황에 따라 다른 status도 사용할 수 있으므로 위 표를 모든 HTTP 오류의 전체 목록으로 이해해서는 안 됩니다.

### 인증과 302

로그인이 필요한 HTML 화면에서 인증되지 않은 사용자를 login page로 보내는 경우 Django의 인증 관련 view나 mixin은 redirect를 사용할 수 있습니다.

```text
보호된 페이지 요청
→ 인증 필요
→ login URL로 redirect
```

이 경우 browser가 보는 status가 302일 수 있지만, **302 자체가 "인증 실패"를 의미하는 status는 아닙니다.** 302의 의미는 redirect이며, 어떤 이유로 redirect했는지는 application 흐름이 결정합니다.

### 400, 403, 404를 구분하는 이유

실패를 항상 다음처럼 `200 OK` 안의 문자열로만 표현하면,

```text
HTTP 200

"권한이 없습니다."
```

HTTP client나 automated test는 response body를 해석해야만 실패 여부를 알 수 있습니다.

반면 적절한 status를 사용하면,

```text
HTTP 403
```

client가 protocol 수준에서 결과를 구분할 수 있습니다.

예를 들어 Django test에서는 다음처럼 의도를 검증할 수 있습니다.

```python
response = self.client.get("/entries/missing/")

self.assertEqual(response.status_code, 404)
```

따라서 HTTP status는 단순한 표시용 숫자가 아니라 **server와 client가 요청 결과의 종류를 공유하는 protocol 정보**입니다.

## 요청 처리 예제

지금까지의 요소를 상세 페이지 요청 하나로 연결하면 다음과 같습니다.

```text
GET /entries/django-urls/
        │
        ▼
root URLconf
        │
        │ include("catalog.urls")
        ▼
catalog URLconf
        │
        │ <slug:slug>
        │ slug="django-urls"
        ▼
EntryDetailView
        │
        │ published queryset에서 조회
        ├───────────────┐
        │               │
        │ 있음          │ 없음
        ▼               ▼
template render       404 response
        │
        ▼
200 response
```

URL pattern은 **어떤 view로 보낼지와 URL 인자를 추출하는 책임**을 맡고, view와 queryset은 **해당 resource를 실제로 조회할 수 있는지 판단하는 책임**을 맡습니다.

## 확인할 것

URL과 view를 구현한 뒤에는 최소한 다음 경우를 확인하는 것이 좋습니다.

```text
정상 URL이 예상 view로 연결되는가
named URL을 reverse할 수 있는가
없는 slug가 404를 반환하는가
비공개 object가 공개 queryset에서 제외되는가
권한 없는 사용자가 제한된 작업을 수행할 수 없는가
POST 성공 후 redirect되는가
```

예를 들어 shell에서 named URL을 확인할 수 있습니다.

```sh
python manage.py shell
```

```python
from django.urls import reverse

reverse(
    "catalog:entry-detail",
    kwargs={"slug": "django-urls"},
)
```

URL 구조를 변경한 뒤에도 이 이름이 올바른 URL로 reverse되는지 확인하면 URLconf와 호출 코드의 연결을 검증할 수 있습니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/http/urls/
- https://docs.djangoproject.com/en/5.2/topics/http/views/
- https://docs.djangoproject.com/en/5.2/topics/class-based-views/
