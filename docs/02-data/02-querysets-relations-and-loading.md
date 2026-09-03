# QuerySet, relation과 loading

## 학습 목표

- `QuerySet`이 실제 SQL을 실행하는 시점과 평가 결과가 재사용되는 조건을 설명합니다.
- 검색 조건을 안전하게 조합하고 공개된 row만 반환합니다.
- `select_related()`와 `prefetch_related()`를 relation 종류와 접근 방식에 맞게 사용합니다.
- pagination 전에 filter와 안정적인 ordering을 확정합니다.
- query 수를 확인해 N+1 query를 발견하고 검증합니다.

## QuerySet은 지연 실행됩니다

Django의 `QuerySet`은 **조회 결과 자체가 아니라 실행할 database query를 표현하는 객체**입니다.

```python
entries = Entry.objects.filter(status=Entry.Status.PUBLISHED)
```

위 코드는 조건이 추가된 `QuerySet`을 만들지만, 일반적으로 이 시점에는 SQL을 실행하지 않습니다. 실제 row가 필요해 `QuerySet`이 **평가(evaluation)** 될 때 SQL이 실행됩니다.

대표적인 평가 시점은 다음과 같습니다.

```python
for entry in entries:      # 반복
    ...

list(entries)              # list로 변환
len(entries)               # 결과 개수 확인
bool(entries)              # 결과 존재 여부 확인
```

template에서 `QuerySet`을 반복하는 경우에도 결과가 필요하므로 평가됩니다.

```django
{% for entry in entries %}
    {{ entry.title }}
{% endfor %}
```

따라서 다음처럼 filter와 ordering을 계속 연결하는 동안에는 보통 SQL을 실행하지 않습니다.

```python
entries = Entry.objects.all()
entries = entries.filter(status=Entry.Status.PUBLISHED)
entries = entries.filter(category=category)
entries = entries.order_by("-published_at", "-pk")
```

이 지연 실행 덕분에 view에서 조건을 단계적으로 조합한 뒤 마지막에 필요한 SQL을 실행할 수 있습니다.

### 평가 결과의 cache

일반적인 `QuerySet`은 한 번 전체 평가되면 읽어 온 결과를 내부 result cache에 보관합니다.

```python
entries = Entry.objects.filter(status=Entry.Status.PUBLISHED)

list(entries)   # SQL 실행
list(entries)   # 같은 QuerySet이면 보통 저장된 결과 재사용
```

하지만 query 연산을 더 연결하면 새로운 `QuerySet`이 만들어집니다.

```python
entries = Entry.objects.filter(status=Entry.Status.PUBLISHED)
recent = entries.filter(published_at__gte=start)
```

`entries`와 `recent`는 서로 다른 `QuerySet`이므로 한쪽의 평가 결과가 다른 쪽의 SQL 실행을 대신하지 않습니다.

반대로 너무 일찍 `list()`로 바꾸는 것도 피해야 합니다.

```python
entries = list(Entry.objects.all())
```

이제 `entries`는 `QuerySet`이 아니라 Python `list`이므로 이후 filter, ordering, pagination을 database가 처리할 수 없습니다. 가능한 한 조건과 ordering을 `QuerySet` 단계에서 완성한 뒤 필요한 시점에 평가합니다.

개수만 필요하다면 모든 row를 가져오는 `len()`보다 `count()`가 적절할 수 있습니다.

```python
count = entries.count()
```

존재 여부만 필요하다면 `exists()`를 사용할 수 있습니다.

```python
if entries.exists():
    ...
```

다만 이후 같은 `QuerySet` 전체를 곧바로 읽을 예정이라면 `exists()`와 실제 조회가 각각 별도 SQL이 될 수 있습니다. 메서드 이름만 보고 무조건 더 효율적이라고 판단하지 않고 실제 접근 흐름을 기준으로 선택합니다.

## 공개 row 제한

draft와 공개 row가 함께 저장되는 model이라면 공개 화면의 query는 처음부터 공개 상태로 제한해야 합니다.

```python
entries = Entry.objects.filter(status=Entry.Status.PUBLISHED)
```

상세 view에서만 이 조건을 적용하고 목록, 검색, API 등 다른 경로에서 빠뜨리면 비공개 데이터가 노출될 수 있습니다.

상세 조회도 공개용 `QuerySet`을 기준으로 수행합니다.

```python
from django.shortcuts import get_object_or_404

entry = get_object_or_404(
    Entry.objects.filter(status=Entry.Status.PUBLISHED),
    slug=slug,
)
```

반복되는 조건은 custom `QuerySet` method로 이름을 붙이면 의도를 명확하게 할 수 있습니다.

```python
class EntryQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Entry.Status.PUBLISHED)


class Entry(models.Model):
    objects = EntryQuerySet.as_manager()
```

그러면 공개 데이터가 필요한 위치에서 다음처럼 사용할 수 있습니다.

```python
Entry.objects.published()
```

이 방법은 보안 규칙을 자동으로 보장한다기보다 **공개 row를 선택하는 규칙을 한곳에 표현해 반복 실수를 줄이는 방법**입니다. 관리자 화면처럼 draft도 필요한 경로에서는 어떤 query를 사용하는지 별도로 명확하게 구분해야 합니다.

## 검색 조건

여러 조건을 `OR`, `AND`, `NOT`으로 조합할 때는 `Q` 객체를 사용할 수 있습니다.

```python
from django.db.models import Q

queryset = queryset.filter(
    Q(title__icontains=term)
    | Q(summary__icontains=term)
)
```

두 조건 중 하나라도 참인 row가 선택됩니다.

여기에 keyword condition을 함께 전달하면 `AND`로 결합됩니다.

```python
queryset = Entry.objects.filter(
    Q(title__icontains=term)
    | Q(summary__icontains=term),
    status=Entry.Status.PUBLISHED,
)
```

개념적으로 다음 조건입니다.

```text
(title contains term OR summary contains term)
AND status = PUBLISHED
```

조건이 복잡할수록 괄호로 의도를 분명히 표현하는 편이 좋습니다.

```python
condition = (
    Q(title__icontains=term)
    | Q(summary__icontains=term)
)

queryset = queryset.filter(condition)
```

### 사용자 입력은 lookup의 값으로 전달합니다

검색어를 직접 SQL 문자열에 이어 붙이지 않습니다.

```python
# 사용하지 않는 방식
sql = f"SELECT * FROM entry WHERE title LIKE '%{term}%'"
```

ORM lookup의 **값**으로 전달하면 Django와 database driver가 SQL과 parameter를 분리해 처리합니다.

```python
Entry.objects.filter(title__icontains=term)
```

하지만 ORM을 사용한다고 모든 동적 query가 자동으로 안전해지는 것은 아닙니다. 특히 request의 key를 그대로 field나 lookup 이름으로 사용하면 의도하지 않은 relation이나 field까지 조회하도록 허용할 수 있습니다.

```python
# 지나치게 넓은 입력 허용
Entry.objects.filter(**request.GET.dict())
```

외부에 공개할 filter는 allowlist로 제한합니다.

```python
allowed_filters = {
    "category": "category__slug",
    "author": "created_by__username",
}

queryset = Entry.objects.all()

for parameter, lookup in allowed_filters.items():
    value = request.GET.get(parameter)
    if value:
        queryset = queryset.filter(**{lookup: value})
```

SQL injection을 막는 문제와 **사용자가 어떤 field를 query할 수 있는지 제한하는 문제**는 별개입니다.

## Relation loading

relation에 접근할 때 관련 row를 언제 읽는지 이해하지 못하면 목록 하나를 출력하면서 많은 SQL이 실행될 수 있습니다.

예를 들어 다음 relation이 있다고 가정합니다.

```python
class Entry(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="entries",
    )
```

Entry 목록을 먼저 읽은 뒤 각 row의 `category`에 접근하면 관련 객체를 위한 query가 row마다 추가될 수 있습니다.

```python
entries = Entry.objects.all()

for entry in entries:
    print(entry.category.name)
```

Entry가 100개라면 개념적으로 다음과 같은 query 패턴이 될 수 있습니다.

```text
Entry 목록 조회           1 query
각 Entry의 Category 조회  100 queries
---------------------------------
총                        101 queries
```

이처럼 기본 query 뒤에 각 row 또는 relation마다 추가 query가 반복되는 문제를 **N+1 query**라고 부릅니다.

## `select_related()`

`ForeignKey`와 `OneToOneField`처럼 한 객체에서 하나의 관련 객체를 가리키는 relation은 `select_related()`로 함께 읽을 수 있습니다.

```python
entries = Entry.objects.select_related(
    "category",
    "created_by",
)
```

Django는 SQL `JOIN`을 사용해 Entry와 관련 row를 같은 query 결과에 포함합니다. 따라서 다음 relation 접근에서 추가 query가 발생하지 않습니다.

```python
for entry in entries:
    print(entry.category.name)
    print(entry.created_by.username)
```

관계를 연속해서 따라갈 수도 있습니다.

```python
Entry.objects.select_related("category__parent")
```

`select_related()`는 주로 다음 relation에 적합합니다.

- `ForeignKey`
- `OneToOneField`
- reverse `OneToOneField`

many-to-many나 reverse foreign key처럼 **한 객체에 여러 관련 row가 연결될 수 있는 relation**에는 일반적으로 사용할 수 없습니다. 이런 relation은 JOIN 결과에서 부모 row가 관련 row 수만큼 반복될 수 있기 때문에 `prefetch_related()`를 사용합니다.

## `prefetch_related()`

Many-to-many와 reverse foreign key처럼 여러 row가 연결되는 relation은 보통 `prefetch_related()`를 사용합니다.

```python
entries = Entry.objects.prefetch_related("tags")
```

`prefetch_related()`는 하나의 큰 JOIN query를 만드는 방식이 아닙니다. 개념적으로 다음처럼 동작합니다.

1. Entry를 조회합니다.
2. 조회된 Entry에 필요한 Tag를 별도 query로 가져옵니다.
3. Python에서 각 Entry와 Tag를 연결합니다.

따라서 다음 코드에서 Entry마다 tags query를 반복하는 일을 피할 수 있습니다.

```python
for entry in entries:
    for tag in entry.tags.all():
        print(tag.name)
```

reverse foreign key에도 사용할 수 있습니다.

```python
entries = Entry.objects.prefetch_related("reviews")
```

`prefetch_related()`는 many-valued relation에만 제한되는 것은 아니지만, foreign key나 one-to-one처럼 JOIN으로 자연스럽게 가져올 수 있는 relation은 보통 `select_related()`가 더 직접적인 선택입니다.

### 두 방법을 함께 사용하기

실제 화면에는 single-valued relation과 many-valued relation이 함께 필요한 경우가 많습니다.

```python
entries = (
    Entry.objects
    .filter(status=Entry.Status.PUBLISHED)
    .select_related("category", "created_by")
    .prefetch_related("tags", "reviews")
)
```

여기서는 category와 created_by를 JOIN으로 읽고, tags와 reviews는 별도 query로 미리 가져옵니다.

## 필요한 relation만 미리 읽습니다

모든 relation을 무조건 미리 읽는 것이 좋은 것은 아닙니다. query 수는 줄어도 다음 비용은 증가할 수 있습니다.

- database에서 읽는 row 수
- application으로 전송되는 데이터 양
- Python object 생성 비용
- application memory 사용량

따라서 template이나 serializer가 실제로 접근하는 relation을 기준으로 loading 전략을 정합니다.

예를 들어 template이 category만 사용한다면 다음으로 충분합니다.

```python
entries = Entry.objects.select_related("category")
```

또한 relation을 prefetch했더라도 **그 relation에 다른 filter를 다시 적용하면** prefetch 결과가 그대로 사용되지 않을 수 있습니다.

```python
entries = Entry.objects.prefetch_related("tags")

for entry in entries:
    entry.tags.filter(is_active=True)
```

`tags.all()`에 사용할 데이터를 미리 읽은 것이지 `tags.filter(is_active=True)` 결과까지 미리 계산한 것은 아니므로 추가 query가 발생할 수 있습니다. 필요한 filter가 정해져 있다면 `Prefetch` 객체로 지정합니다.

## `Prefetch`

`Prefetch`는 prefetch할 relation에 별도 `QuerySet`을 지정할 때 사용합니다.

예를 들어 공개 후기만 미리 읽고 싶다면 다음처럼 작성할 수 있습니다.

```python
from django.db.models import Prefetch

entries = Entry.objects.prefetch_related(
    Prefetch(
        "reviews",
        queryset=(
            Review.objects
            .filter(is_visible=True)
            .select_related("author")
        ),
        to_attr="visible_reviews",
    )
)
```

이 코드는 다음 의미를 가집니다.

- `reviews` relation을 미리 읽습니다.
- `is_visible=True`인 후기만 가져옵니다.
- 각 후기의 `author`도 함께 읽습니다.
- 결과를 `visible_reviews` attribute에 저장합니다.

사용할 때는 지정한 attribute를 읽습니다.

```python
for entry in entries:
    for review in entry.visible_reviews:
        print(review.author.username, review.body)
```

`to_attr`를 사용하면 결과가 해당 attribute에 일반 Python `list`로 저장됩니다. 따라서 template이나 view에서 다음처럼 원래 relation manager를 다시 조회하는 실수를 줄일 수 있습니다.

```python
# visible_reviews와 다른 접근
entry.reviews.all()
```

즉 `to_attr`는 **어떤 범위의 related row를 미리 읽었는지 이름으로 구분해 표현하는 데** 유용합니다.

## Ordering과 pagination

Pagination을 적용하기 전에 filter와 ordering을 먼저 확정합니다.

```python
queryset = (
    Entry.objects
    .filter(status=Entry.Status.PUBLISHED)
    .order_by("-published_at", "-pk")
)
```

그 다음 paginator에 전달합니다.

```python
from django.core.paginator import Paginator

paginator = Paginator(queryset, 20)
page = paginator.get_page(request.GET.get("page"))
```

### ordering은 전체 순서를 결정할 수 있어야 합니다

다음 ordering만 사용한다고 가정합니다.

```python
queryset.order_by("-published_at")
```

여러 row의 `published_at`이 같으면 그 row들 사이의 순서는 정의되지 않습니다. database가 항상 같은 상대적 순서를 반환한다고 보장할 수 없습니다.

따라서 마지막에 tie-breaker를 추가합니다.

```python
queryset.order_by("-published_at", "-pk")
```

`pk`가 고유하다면 같은 `published_at`을 가진 row 사이의 순서도 결정됩니다.

```text
published_at          pk
--------------------  --
2026-08-29 12:00:00    9
2026-08-29 12:00:00    7
2026-08-29 12:00:00    3
```

pagination에서는 이런 **안정적인 전체 순서(total ordering)** 가 필요합니다.

다만 안정적인 ordering이 있다고 해서 pagination 도중 데이터가 추가·삭제되는 영향까지 없어지는 것은 아닙니다. offset 기반 pagination에서는 앞쪽에 새 row가 삽입되면 뒤 page에서 일부 row가 중복되거나 밀릴 수 있습니다. 여기서 먼저 보장해야 할 것은 **동일한 데이터 상태에서 row의 순서를 명확히 결정할 수 있는 ordering**입니다.

## Query 확인

개발 중에는 ORM이 생성한 SQL 구조를 확인할 수 있습니다.

```python
print(queryset.query)
```

filter, JOIN, ordering 등이 예상한 형태로 만들어지는지 확인할 때 유용합니다.

database가 실제로 어떤 실행 계획을 선택하는지 보고 싶다면 `QuerySet.explain()`도 사용할 수 있습니다.

```python
print(queryset.explain())
```

실행 계획은 database 종류, schema, index, 통계에 따라 달라지므로 SQL 문자열이나 query 개수만으로 성능을 단정하지 않습니다.

## N+1 query를 test로 검증합니다

Django test에서는 `assertNumQueries()`로 특정 코드가 실행하는 query 수를 검증할 수 있습니다.

```python
from django.test import TestCase


class EntryListTest(TestCase):
    def test_entry_list_does_not_query_category_per_row(self):
        entries = (
            Entry.objects
            .select_related("category")
            .order_by("pk")
        )

        with self.assertNumQueries(1):
            for entry in entries:
                _ = entry.category.name
```

relation row 수를 늘렸을 때 query 수도 함께 증가한다면 N+1 가능성을 의심할 수 있습니다.

목표는 query 개수를 무조건 최소화하는 것이 아닙니다. 하나의 거대한 JOIN query가 여러 개의 단순한 query보다 항상 빠른 것도 아닙니다.

다음 요소를 함께 판단합니다.

- 한 화면에서 실제로 필요한 relation
- 조회되는 row 수와 column 수
- JOIN으로 인해 결과가 얼마나 커지는지
- database index와 실행 계획
- application memory 사용량
- 실제 응답 시간

먼저 N+1처럼 데이터 개수에 따라 query가 계속 늘어나는 구조를 제거하고, 이후 측정 결과를 기준으로 최적화합니다.

## 정리

`QuerySet`은 조건을 조합하는 동안에는 보통 SQL을 실행하지 않고 실제 결과가 필요한 순간 평가됩니다. 이를 이용해 filter와 ordering을 database query로 끝까지 유지합니다.

relation을 읽을 때는 관계의 형태에 따라 loading 전략을 구분합니다.

```text
ForeignKey / OneToOne
        │
        └─ select_related()
           SQL JOIN으로 함께 조회

ManyToMany / reverse ForeignKey
        │
        └─ prefetch_related()
           별도 query 후 Python에서 연결
```

목록 화면의 query는 다음 순서로 설계하면 각 단계의 책임을 확인하기 쉽습니다.

```text
공개 범위 제한
    ↓
검색·filter 적용
    ↓
필요한 relation loading
    ↓
안정적인 ordering 확정
    ↓
pagination
    ↓
query 수와 실행 결과 검증
```

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/db/queries/
- https://docs.djangoproject.com/en/5.2/ref/models/querysets/
- https://docs.djangoproject.com/en/5.2/topics/pagination/
