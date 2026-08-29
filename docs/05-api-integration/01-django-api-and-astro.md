# Django JSON API와 Astro 연동

이 문서는 선택 과정입니다. Django template로 목록, 상세, form, 인증, 권한을 완성한 뒤 별도 frontend가 필요할 때 진행합니다.

## 학습 목표

- Django model을 JSON으로 직접 노출하지 않고 필요한 field만 직렬화합니다.
- HTML view와 API가 같은 공개 query를 사용하게 합니다.
- pagination과 URL을 안정적인 response 형식으로 제공합니다.
- server-to-server 요청과 browser cross-origin 요청을 구분합니다.

## Read-only API부터 시작합니다

```python
return JsonResponse({
    "results": [...],
    "page": page.number,
    "pages": paginator.num_pages,
})
```

Model instance의 `__dict__`를 그대로 반환하지 않습니다. 내부 field, moderation 상태, 사용자 정보가 새로 추가됐을 때 의도치 않게 공개될 수 있습니다.

## HTML과 같은 query 사용

목록 화면과 API가 각각 공개 조건을 구현하면 한쪽에서 draft 제한을 빠뜨릴 수 있습니다.

```python
entries = filter_published_entries(request.GET)
```

공개 상태, 검색, category/tag filter, relation loading을 같은 query function에서 처리하고 표현만 HTML과 JSON으로 나눕니다.

## Pagination

전체 row를 한 response에 반환하지 않습니다. Page 번호, 전체 page 수, 결과 수를 함께 보냅니다.

```json
{
  "page": 1,
  "pages": 4,
  "count": 63,
  "results": []
}
```

Client가 다음 URL을 직접 조립할지, `next` URL을 받을지는 API 형식으로 정하고 test합니다.

## Astro server rendering

Astro가 server에서 Django API를 호출하면 browser CORS 제한을 받지 않습니다.

```text
browser
→ Astro server
→ Django API
```

Browser JavaScript가 Django의 다른 origin으로 직접 요청하면 CORS header가 필요합니다. Django core는 일반적인 CORS 설정을 제공하지 않으므로 reverse proxy에서 같은 origin으로 합치거나 검증된 package를 추가해야 합니다.

## Write API와 CSRF

Cookie session을 사용하는 browser write API는 CSRF token이 필요합니다. `csrf_exempt`로 우회하지 않습니다.

별도 mobile client, token 인증, object permission, serializer가 필요해지면 Django REST Framework가 적합할 수 있습니다. 단순 read-only catalog API에는 core Django의 `JsonResponse`로 충분합니다.

## API 변경

Template context는 같은 project 안에서 함께 바꿀 수 있지만, 별도 frontend가 API를 사용하면 field 이름과 의미가 외부 의존성이 됩니다.

- response field를 문서화합니다.
- draft와 개인 정보가 포함되지 않는지 test합니다.
- 삭제 또는 이름 변경 전에 consumer를 함께 수정합니다.
- error status와 body 형식을 일정하게 유지합니다.

## Exercise endpoint

`catalog-site`는 다음 read-only endpoint를 제공합니다.

```text
GET /api/entries/
GET /api/entries/<slug>/
```

목록 endpoint는 HTML 화면과 같은 검색·filter parameter를 사용합니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/ref/request-response/#jsonresponse-objects
- https://docs.djangoproject.com/en/5.2/topics/pagination/
- https://docs.djangoproject.com/en/5.2/howto/csrf/
