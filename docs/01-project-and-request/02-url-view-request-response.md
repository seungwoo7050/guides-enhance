# URL, view, request와 response

## 학습 목표

- URL pattern을 이름과 함께 선언합니다.
- view가 `HttpRequest`에서 입력을 읽고 `HttpResponse`를 반환하는 과정을 설명합니다.
- redirect와 404 response를 정상적인 HTTP 동작으로 사용합니다.
- URL 문자열을 직접 조립하지 않고 `reverse()`를 사용합니다.

## 요청 처리 순서

기본 처리 순서는 다음과 같습니다.

```text
web server
→ middleware
→ root URLconf
→ app URLconf
→ view
→ template 또는 redirect/JSON response
→ middleware
→ client
```

middleware는 모든 요청 앞뒤에서 실행될 수 있습니다. 인증, session, CSRF, security header 같은 기능이 여기에 연결됩니다.

## URLconf

root URLconf는 app URL을 포함합니다.

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("catalog.urls")),
]
```

app URL에는 namespace와 이름을 둡니다.

```python
app_name = "catalog"

urlpatterns = [
    path("", views.EntryListView.as_view(), name="entry-list"),
    path("entries/<slug:slug>/", views.EntryDetailView.as_view(), name="entry-detail"),
]
```

`slug` converter는 URL 문자열을 view keyword argument로 전달합니다. converter가 형식을 확인하더라도 해당 row의 존재 여부와 공개 상태는 view에서 다시 확인해야 합니다.

## View

view는 request를 받아 response를 반환합니다.

```python
from django.shortcuts import get_object_or_404, render


def entry_detail(request, slug):
    entry = get_object_or_404(Entry.objects.published(), slug=slug)
    return render(request, "catalog/entry_detail.html", {"entry": entry})
```

row가 없거나 공개되지 않았다면 404가 적절합니다. 권한이 없는 비공개 object의 존재를 굳이 알려 줄 필요가 없는 경우에도 404를 사용할 수 있습니다.

## Class-based view

목록, 상세, 생성, 수정, 삭제처럼 반복되는 HTTP 동작은 generic view로 줄일 수 있습니다.

```python
class EntryListView(ListView):
    model = Entry
    paginate_by = 20
```

상속했다고 권한과 query가 자동으로 올바르게 제한되는 것은 아닙니다. `get_queryset()`에서 공개 상태와 소유자를 제한하고, `form_valid()`에서 request user처럼 form이 직접 받지 않는 값을 저장해야 합니다.

## GET과 POST

- GET: 상태를 바꾸지 않는 조회
- POST: 생성, 수정, 삭제, logout처럼 상태를 바꾸는 요청

POST가 성공하면 같은 form을 다시 보여 주기보다 redirect합니다.

```text
POST
→ 저장
→ redirect
→ GET
```

이 방식은 새로고침으로 같은 요청이 다시 제출되는 일을 줄입니다.

## URL reverse

다음처럼 URL 문자열을 직접 적지 않습니다.

```python
reverse("catalog:entry-detail", kwargs={"slug": entry.slug})
```

model에 `get_absolute_url()`을 구현하면 generic view도 저장 후 이동할 위치를 사용할 수 있습니다.

## Status code

- `200`: 정상 조회
- `302`: 로그인 또는 저장 후 redirect
- `400`: 형식이 잘못된 API 요청
- `403`: 사용자는 확인됐지만 작업 권한이 없음
- `404`: route 또는 object를 찾을 수 없음

모든 실패를 200 response 안의 오류 문장으로 숨기지 않습니다. HTTP status는 client와 test가 결과를 구분하는 값입니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/http/urls/
- https://docs.djangoproject.com/en/5.2/topics/http/views/
- https://docs.djangoproject.com/en/5.2/topics/class-based-views/
