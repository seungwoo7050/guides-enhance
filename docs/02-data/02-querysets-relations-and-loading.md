# QuerySet, relation과 loading

## 학습 목표

- `QuerySet`이 실제 SQL을 실행하는 시점을 설명합니다.
- 검색 조건을 조합하고 공개된 row만 반환합니다.
- `select_related()`와 `prefetch_related()`를 relation 종류에 맞게 사용합니다.
- pagination 전에 filter와 ordering을 확정합니다.

## QuerySet은 지연 실행됩니다

```python
entries = Entry.objects.filter(status=Entry.Status.PUBLISHED)
```

이 줄만으로 SQL이 실행되는 것은 아닙니다. 반복, `list()`, `len()`, template rendering처럼 결과가 필요한 시점에 query가 실행됩니다.

QuerySet을 여러 번 평가하면 같은 SQL이 반복될 수 있습니다. 반대로 너무 일찍 `list()`로 바꾸면 이후 filter와 pagination을 database가 처리하지 못합니다.

## 공개 row 제한

공개 화면은 항상 공개 상태를 먼저 제한합니다.

```python
Entry.objects.filter(status=Entry.Status.PUBLISHED)
```

상세 view에서만 제한하고 목록이나 API에서 빠뜨리면 draft가 노출됩니다. 공통 query function이나 custom `QuerySet` method로 반복을 줄일 수 있습니다.

## 검색 조건

```python
from django.db.models import Q

queryset.filter(
    Q(title__icontains=term)
    | Q(summary__icontains=term)
)
```

사용자가 입력한 검색어를 SQL 문자열에 직접 붙이지 않습니다. ORM lookup 값으로 전달하면 database driver가 parameter를 분리합니다.

Filter parameter는 허용된 field에만 연결합니다. request의 key를 그대로 `filter(**request.GET)`에 넘기면 의도하지 않은 relation과 field를 조회할 수 있습니다.

## Relation loading

Foreign key와 one-to-one relation은 join으로 읽을 수 있습니다.

```python
entries.select_related("category", "created_by")
```

Many-to-many와 reverse foreign key는 별도 query로 묶어 읽습니다.

```python
entries.prefetch_related("tags")
```

목록 row마다 `entry.category`나 `entry.tags.all()`을 읽을 때 query 수가 계속 늘어나는 문제를 N+1 query라고 부릅니다. template가 실제로 접근하는 relation을 확인한 뒤 필요한 항목만 미리 읽습니다.

## `Prefetch`

Reverse relation에서 공개 후기만 읽고 싶다면 query를 지정할 수 있습니다.

```python
Prefetch(
    "reviews",
    queryset=Review.objects.filter(is_visible=True).select_related("author"),
    to_attr="visible_reviews",
)
```

`to_attr`를 사용하면 template에서 다시 `reviews.all()`을 호출해 전체 후기를 읽는 실수를 줄일 수 있습니다.

## Ordering과 pagination

Pagination에는 안정적인 ordering이 필요합니다.

```python
queryset.order_by("-published_at", "-pk")
```

같은 `published_at` 값을 가진 row의 순서도 `pk`로 고정합니다. ordering 없이 page를 나누면 요청할 때마다 row가 다른 page로 이동할 수 있습니다.

## Query 확인

개발 중에는 다음 방법을 사용할 수 있습니다.

```python
print(queryset.query)
```

Test에서는 `assertNumQueries()`로 특정 화면의 query 수가 relation 수에 따라 증가하지 않는지 확인할 수 있습니다. query 수 자체를 무조건 최소화하기보다 데이터 크기와 화면 요구를 기준으로 판단합니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/db/queries/
- https://docs.djangoproject.com/en/5.2/ref/models/querysets/
- https://docs.djangoproject.com/en/5.2/topics/pagination/
