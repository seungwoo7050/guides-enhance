# Django JSON API와 Astro 연동

이 문서는 선택 과정입니다. Django template로 목록, 상세, form, 인증, 권한을 먼저 완성한 뒤, 같은 데이터를 별도 frontend에서도 사용해야 할 때 진행합니다.

여기서 핵심은 **Django model을 그대로 외부에 노출하는 것**이 아니라, 기존 Django 애플리케이션의 공개 규칙을 재사용하면서 별도의 **JSON API 계약(contract)** 을 만드는 것입니다. API 계약에는 어떤 field를 공개하는지뿐 아니라 pagination, URL, HTTP status, error body의 의미도 포함됩니다.

## 학습 목표

- Django model을 JSON으로 직접 노출하지 않고 필요한 field만 명시적으로 직렬화합니다.
- HTML view와 API가 같은 공개 query 규칙을 사용하게 합니다.
- pagination과 URL을 안정적인 response 형식으로 제공합니다.
- server-to-server 요청과 browser cross-origin 요청을 구분합니다.
- read API와 cookie 기반 write API에서 필요한 보안 요구 사항이 다름을 이해합니다.

## Read-only API부터 시작합니다

처음에는 조회만 가능한 API부터 만드는 편이 안전합니다. 쓰기 API는 입력 검증, 인증, 권한, CSRF, 동시 수정 같은 추가 문제가 생기지만, read-only API는 기존의 공개 조회 규칙을 JSON으로 표현하는 데 집중할 수 있습니다.

예를 들어 목록 endpoint는 다음처럼 항상 JSON object를 반환하도록 만들 수 있습니다.

```python
return JsonResponse({
    "results": [...],
    "page": page.number,
    "pages": paginator.num_pages,
    "count": paginator.count,
})
```

Model instance의 `__dict__`를 그대로 반환하지 않습니다. `__dict__`에는 API 공개 여부와 무관한 내부 상태가 포함될 수 있고, 나중에 moderation 상태나 사용자 관련 field가 추가되면 의도하지 않은 정보가 자동으로 노출될 수 있습니다.

대신 API에 필요한 field를 명시적으로 선택합니다.

```python
def serialize_entry(entry):
    return {
        "slug": entry.slug,
        "title": entry.title,
        "summary": entry.summary,
        "published_at": entry.published_at.isoformat(),
    }
```

이 방식의 장점은 model schema와 API schema를 분리한다는 점입니다. Model에 field가 추가되어도 API response는 자동으로 바뀌지 않으며, 공개 field를 변경할 때는 코드와 test에서 의도적으로 결정하게 됩니다.

## HTML과 같은 공개 query 사용

HTML 목록 화면과 API 목록이 각각 공개 조건을 구현하면 시간이 지나면서 규칙이 달라질 수 있습니다. 예를 들어 HTML에서는 draft를 제외하지만 API에서는 실수로 draft를 반환하는 문제가 생길 수 있습니다.

따라서 **어떤 row를 공개할지 결정하는 query 로직**을 한 곳에 둡니다.

```python
entries = filter_published_entries(request.GET)
```

예를 들어 이 함수가 다음 규칙을 함께 담당할 수 있습니다.

- 공개 상태인 entry만 선택
- 검색어 적용
- category/tag filter 적용
- 정렬 순서 적용
- 필요한 relation을 `select_related()` 또는 `prefetch_related()`로 미리 로딩

HTML view와 API view는 같은 `QuerySet` 생성 규칙을 사용하고, 최종 표현만 각각 HTML과 JSON으로 나눕니다.

```python
# HTML
entries = filter_published_entries(request.GET)
return render(request, "catalog/entry_list.html", {"entries": entries})

# JSON API
entries = filter_published_entries(request.GET)
# pagination 후 명시적으로 JSON 직렬화
```

상세 endpoint도 같은 원칙을 적용해야 합니다. 단순히 전체 model에서 `slug`만 검색하면 비공개 entry가 노출될 수 있으므로, **공개 가능한 queryset 안에서** 상세 객체를 찾습니다.

```python
entries = published_entries()
entry = get_object_or_404(entries, slug=slug)
```

즉, HTML과 API가 공유해야 하는 것은 template이나 response 코드가 아니라 **공개 데이터의 선택 규칙**입니다.

## Pagination

목록 전체 row를 한 response에 반환하지 않습니다. 데이터가 늘어날수록 response 크기, database 작업량, serialization 비용, network 전송 시간이 함께 증가하기 때문입니다.

예를 들어 page 기반 API는 다음처럼 일관된 형식을 사용할 수 있습니다.

```json
{
  "page": 1,
  "pages": 4,
  "count": 63,
  "results": []
}
```

각 field의 의미를 명확히 정합니다.

- `page`: 현재 page 번호
- `pages`: 전체 page 수
- `count`: filter 적용 후 전체 결과 수
- `results`: 현재 page에 포함된 항목

`count`가 전체 table row 수인지, 검색과 filter를 적용한 뒤의 결과 수인지도 API 계약의 일부입니다. 일반적으로 사용자가 보고 있는 결과 집합의 크기를 의미하도록 filter 적용 후의 count를 사용합니다.

Client가 다음 page URL을 직접 조립하게 할 수도 있고, API가 `next`와 `previous` URL을 제공할 수도 있습니다.

```json
{
  "page": 1,
  "pages": 4,
  "count": 63,
  "next": "/api/entries/?page=2",
  "previous": null,
  "results": []
}
```

어느 방식을 선택하든 다음 사항을 test합니다.

- 첫 page와 마지막 page의 동작
- 존재하지 않는 page 번호의 처리
- 검색·filter parameter가 다음 page URL에도 유지되는지
- 빈 결과가 정상적으로 빈 `results`를 반환하는지

Pagination 형식은 frontend가 의존하는 API 계약이므로 endpoint마다 임의로 다르게 만들지 않습니다.

## Astro server rendering

Astro 코드가 **browser가 아니라 server 측에서** Django API를 호출하면 browser의 CORS 정책이 적용되지 않습니다.

```text
browser
→ Astro server
→ Django API
```

CORS(Cross-Origin Resource Sharing)는 browser가 다른 origin에 요청할 때 적용하는 보안 정책입니다. 여기서 origin은 일반적으로 다음 세 요소의 조합입니다.

```text
scheme + host + port
```

예를 들어 다음 두 URL은 port가 다르므로 서로 다른 origin입니다.

```text
http://localhost:4321
http://localhost:8000
```

Astro의 server-side 코드가 Django에 요청하는 경우 Django가 보는 요청 주체는 Astro server입니다. 이 네트워크 요청 자체는 browser가 수행하지 않으므로 browser CORS 검사 대상이 아닙니다.

```astro
---
const response = await fetch(`${import.meta.env.DJANGO_API_URL}/api/entries/`);

if (!response.ok) {
  throw new Error(`Django API request failed: ${response.status}`);
}

const data = await response.json();
---
```

다만 Astro 코드는 실행 방식에 따라 build 시점에 실행될 수도 있고 SSR 환경에서 요청마다 실행될 수도 있습니다. 어느 경우든 **server 측 실행이라면 browser CORS와는 별개**이지만, Django API가 해당 실행 환경에서 실제로 접근 가능한 주소인지 확인해야 합니다.

반대로 browser JavaScript가 Django의 다른 origin으로 직접 요청하면 다음 구조가 됩니다.

```text
browser
→ Django API
```

이 경우 browser가 CORS 정책을 검사하므로 Django API가 적절한 CORS response header를 제공해야 합니다. Django core는 일반적인 cross-origin 허용 정책을 설정하는 전용 CORS middleware를 제공하지 않으므로 보통 다음 중 하나를 선택합니다.

- reverse proxy를 이용해 frontend와 API를 같은 origin 아래에 배치
- 검증된 Django CORS package를 사용해 허용할 origin을 명시

개발 편의를 위해 모든 origin을 무조건 허용하는 설정을 기본값으로 두지 않습니다. 특히 cookie나 인증 정보가 포함되는 요청은 허용 origin과 credential 정책을 명확히 제한해야 합니다.

## Server-side fetch와 browser fetch의 차이

두 방식은 API URL이 같아 보여도 보안과 인증 동작이 다릅니다.

| 구분 | Astro server → Django | Browser → Django |
| --- | --- | --- |
| Browser CORS 적용 | 아니요 | 다른 origin이면 적용 |
| Browser cookie 자동 전송 | 아니요 | cookie 설정과 `credentials` 정책에 따라 가능 |
| 내부 API 주소 사용 | 가능 | browser에서 접근 가능한 주소여야 함 |
| 인증 전달 | Astro가 명시적으로 전달해야 함 | browser가 cookie/token을 전달할 수 있음 |

따라서 "Astro를 사용한다"는 사실만으로 CORS 필요 여부를 결정할 수 없습니다. **실제 HTTP 요청을 browser가 보내는지, Astro server가 보내는지**를 기준으로 판단합니다.

## Write API와 CSRF

조회 전용 `GET` API와 상태를 변경하는 write API는 요구 사항이 다릅니다.

Django의 cookie 기반 session 인증을 browser에서 사용하면서 `POST`, `PUT`, `PATCH`, `DELETE` 같은 상태 변경 요청을 보낸다면 CSRF 보호를 유지해야 합니다. 공격자가 다른 site에서 사용자의 browser를 이용해 인증 cookie를 자동으로 전송하게 만들 수 있기 때문입니다.

따라서 정상적인 browser write 요청에서는 Django가 기대하는 CSRF token을 함께 전송합니다. 문제를 해결하기 위해 `csrf_exempt`를 붙여 보호를 제거하지 않습니다.

중요한 점은 **CORS와 CSRF가 서로 다른 문제**라는 것입니다.

- CORS: browser가 다른 origin의 response를 읽도록 허용할지 결정
- CSRF: 사용자의 인증 상태를 악용한 원치 않는 상태 변경 요청을 막음

Cross-origin cookie 기반 write API라면 CORS 설정만으로 충분하지 않습니다. credential 전송 설정과 CSRF 보호를 함께 고려해야 합니다.

별도 mobile client, token 인증, object-level permission, 복잡한 serializer와 validation이 필요해지면 Django REST Framework 같은 API framework가 적합할 수 있습니다. 반면 단순한 read-only catalog API라면 core Django의 `JsonResponse`, `Paginator`, 명시적인 serialization 함수만으로도 충분히 구현할 수 있습니다.

## API response와 HTTP status

API는 성공 response뿐 아니라 실패 response의 형식도 일관되어야 합니다.

예를 들어 존재하지 않는 공개 entry를 조회하면 `404 Not Found`를 반환합니다. 서버 내부 오류를 잘못된 요청처럼 `200 OK`로 감싸지 않습니다.

간단한 API라면 error body를 다음처럼 고정할 수 있습니다.

```json
{
  "error": "not_found",
  "message": "Entry not found."
}
```

중요한 것은 특정 문자열 자체가 아니라, frontend가 status와 body 의미를 예측할 수 있게 하는 것입니다.

예를 들어 다음 사항을 API 계약으로 정합니다.

- 정상 목록 조회: `200 OK`
- 정상 상세 조회: `200 OK`
- 존재하지 않는 공개 resource: `404 Not Found`
- 잘못된 query parameter: 필요에 따라 `400 Bad Request`
- error body의 field 이름과 의미

## API 변경

Template context는 같은 project 안에서 template와 view를 함께 수정하기 쉽지만, 별도 frontend가 API를 사용하기 시작하면 response field 이름과 의미가 consumer가 의존하는 인터페이스가 됩니다.

따라서 다음 항목을 명시적으로 관리합니다.

- response field와 각 field의 의미를 문서화합니다.
- draft, moderation 정보, 개인 정보가 포함되지 않는지 test합니다.
- 목록과 상세 endpoint가 동일한 공개 규칙을 따르는지 test합니다.
- field 삭제 또는 이름 변경 전에 consumer를 함께 수정합니다.
- pagination 형식을 endpoint마다 일관되게 유지합니다.
- error status와 body 형식을 일정하게 유지합니다.

특히 **새 field를 추가하는 것**과 **기존 field의 의미를 바꾸는 것**은 다릅니다. 이름은 그대로인데 의미가 달라지면 frontend 코드가 실행은 되면서 잘못된 데이터를 표시할 수 있으므로, 의미 변경도 API 변경으로 취급합니다.

## Exercise endpoint

`catalog-site`는 다음 read-only endpoint를 제공합니다.

```text
GET /api/entries/
GET /api/entries/<slug>/
```

목록 endpoint는 HTML 목록 화면과 같은 검색·filter parameter와 공개 query 규칙을 사용합니다.

예를 들어 HTML에서 다음 요청이 공개된 `django` category만 검색한다면,

```text
/entries/?q=api&category=django
```

API에서도 같은 의미의 parameter를 사용합니다.

```text
/api/entries/?q=api&category=django
```

상세 endpoint 역시 전체 entry가 아니라 공개 가능한 entry 집합에서 `slug`를 찾습니다. 따라서 draft entry의 slug를 알고 있더라도 공개 API에서는 조회되지 않아야 합니다.

최소한 다음 동작을 test합니다.

1. 공개 entry만 목록에 포함됩니다.
2. 검색과 category/tag filter가 HTML과 API에서 같은 결과 집합을 만듭니다.
3. pagination metadata가 실제 결과와 일치합니다.
4. 상세 endpoint에서 공개 entry는 `200`, 비공개 또는 존재하지 않는 entry는 `404`가 됩니다.
5. response에 의도하지 않은 내부 field나 사용자 정보가 포함되지 않습니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/ref/request-response/#jsonresponse-objects
- https://docs.djangoproject.com/en/5.2/topics/pagination/
- https://docs.djangoproject.com/en/5.2/howto/csrf/
