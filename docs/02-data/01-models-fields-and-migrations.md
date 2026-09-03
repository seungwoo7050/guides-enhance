# Model, field와 migration

## 학습 목표

- Python class와 field 선언이 database table, column, constraint로 어떻게 연결되는지 이해합니다.
- `null`, `blank`, `default`, `unique`처럼 비슷해 보이는 옵션이 각각 어느 계층에 영향을 주는지 구분합니다.
- `ForeignKey`, `ManyToManyField`, `on_delete` 동작을 데이터 보존 기준으로 선택합니다.
- model 변경, migration file 생성, database schema 적용을 서로 다른 단계로 구분합니다.
- 첫 migration 전에 custom user model을 확정해야 하는 이유를 이해합니다.
- schema migration과 data migration의 역할을 구분합니다.

## Model은 저장할 데이터와 제약을 선언합니다

Django model은 보통 `models.Model`을 상속한 Python class로 선언합니다. 기본적인 경우 model class 하나는 database table 하나에 대응하고, model의 field는 table의 column 또는 relation을 표현합니다.

```python
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
```

위 선언은 단순히 Python 객체의 속성을 정의하는 것이 아닙니다. migration을 통해 database schema에 반영되면 `name`, `slug` column과 중복을 막는 제약 등이 생성됩니다.

다만 모든 field 옵션이 같은 계층에서 동작하는 것은 아닙니다. 특히 다음 옵션은 구분해서 이해해야 합니다.

- `max_length=80`: 허용할 문자열 길이의 상한을 선언합니다. `CharField`에서는 database column 정의와 Django validation에 사용됩니다.
- `null=True`: database column에 SQL `NULL` 저장을 허용합니다. 기본값은 `False`입니다.
- `blank=True`: Django form과 model validation에서 빈 입력을 허용합니다. database의 `NULL` 허용 여부와는 별개입니다.
- `default=...`: 새 model instance에서 값이 생략되었을 때 Django가 사용할 기본값입니다. 일반적으로 database 자체의 `DEFAULT` 제약을 의미하지 않습니다. database-level default가 필요하다면 Django 버전에 맞는 `db_default` 등의 기능을 별도로 검토해야 합니다.
- `unique=True`: 해당 column 값의 중복을 금지하는 unique constraint를 database에 만듭니다. application validation도 중복을 미리 검사할 수 있지만, 동시 요청 사이의 경쟁까지 최종적으로 막는 것은 database constraint입니다.

예를 들어 선택 입력을 저장하는 문자열 field를 다음과 같이 선언할 수 있습니다.

```python
summary = models.CharField(max_length=200, blank=True, default="")
```

이 경우 값이 없음을 빈 문자열 `""` 하나로 표현합니다. 문자열 field에서 `null=True`까지 함께 사용하면 값이 없는 상태가 `""`와 `NULL` 두 가지로 나뉠 수 있습니다.

```text
""    -> 문자열 값은 존재하지만 길이가 0
NULL  -> SQL 수준에서 값 자체가 없음
```

둘을 동시에 허용해야 할 명확한 이유가 없다면 문자열 field는 보통 `null=False`를 유지하고, 선택 입력에는 `blank=True`를 사용합니다. 상태 표현이 하나로 정리되어야 query, validation, serialization에서 `NULL`과 빈 문자열을 각각 처리할 필요가 줄어듭니다.

### `blank`와 `null`은 서로 대체하지 않습니다

다음 두 선언은 의미가 다릅니다.

```python
nickname = models.CharField(max_length=40, blank=True)
birthday = models.DateField(null=True, blank=True)
```

`nickname`은 form에서 비워 둘 수 있지만 database에는 보통 빈 문자열로 저장합니다. 반면 `DateField`는 빈 문자열을 날짜 값으로 저장할 수 없으므로 값이 없는 상태를 표현하려면 `NULL`이 필요하고, 사용자 입력도 선택 사항이라면 `null=True, blank=True`를 함께 사용하는 경우가 많습니다.

### `default`에 mutable 객체를 직접 두지 않습니다

field 기본값이 새 객체마다 독립적으로 생성되어야 한다면 callable을 사용합니다.

```python
metadata = models.JSONField(default=dict)
```

다음처럼 `default={}`를 사용하면 하나의 mutable 객체를 재사용하는 문제가 생길 수 있으므로 피합니다.

## Relation

관계형 database에서는 다른 table의 row를 참조하는 관계가 자주 필요합니다. Django는 `ForeignKey`, `OneToOneField`, `ManyToManyField` 등으로 이를 표현합니다.

```python
class Entry(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    tags = models.ManyToManyField(
        "Tag",
        related_name="entries",
        blank=True,
    )
```

### `ForeignKey`

`ForeignKey`는 여러 `Entry`가 하나의 `Category`를 참조하는 many-to-one 관계를 표현합니다. database에는 일반적으로 `Entry` table 쪽에 `category_id` 같은 foreign key column이 생깁니다.

정방향 접근은 다음과 같습니다.

```python
entry.category
```

`related_name="entries"`를 지정했으므로 반대 방향에서는 다음처럼 접근할 수 있습니다.

```python
category.entries.all()
```

`related_name`은 단순한 별칭이 아니라 reverse relation의 public API가 되므로, model 간 의미가 드러나는 이름을 선택하는 편이 좋습니다.

### `ManyToManyField`

`ManyToManyField`는 한 `Entry`에 여러 `Tag`가 연결되고, 하나의 `Tag`도 여러 `Entry`에 연결될 수 있는 many-to-many 관계를 표현합니다.

이 관계는 보통 `Entry` table에 tag ID 목록을 저장하는 방식으로 구현되지 않습니다. Django가 두 model의 primary key를 연결하는 중간 table을 사용합니다.

```text
Entry 1 ----< entry_tags >---- Tag A
       ----<            >---- Tag B
Entry 2 ----<            >---- Tag A
```

`ManyToManyField(..., blank=True)`의 `blank=True`는 relation이 하나도 없는 상태를 form validation에서 허용한다는 뜻입니다. many-to-many 관계는 별도 중간 table의 row 존재 여부로 표현되므로 `null=True`로 관계 부재를 표현하지 않습니다.

관계 자체에 `added_at`, `role`, `position` 같은 추가 데이터가 필요하면 명시적인 중간 model을 만들고 `through`를 사용합니다.

## `on_delete`는 참조 대상이 삭제될 때의 정책입니다

`ForeignKey`가 가리키는 parent object를 삭제하려 할 때 child object를 어떻게 처리할지 `on_delete`로 지정합니다.

대표적인 정책은 다음과 같습니다.

- `CASCADE`: parent가 삭제되면 이를 참조하는 child도 함께 삭제합니다.
- `PROTECT`: child가 하나라도 참조하고 있으면 parent 삭제를 거부하고 `ProtectedError`를 발생시킵니다.
- `SET_NULL`: parent가 삭제되면 foreign key를 `NULL`로 바꾸고 child는 유지합니다. 이 경우 foreign key field에 반드시 `null=True`가 필요합니다.

예를 들어 게시물이 반드시 유효한 분류에 속해야 하고, 분류를 지우는 과정에서 게시물까지 실수로 삭제되어서는 안 된다면 다음처럼 `PROTECT`를 사용할 수 있습니다.

```python
category = models.ForeignKey(
    Category,
    on_delete=models.PROTECT,
    related_name="entries",
)
```

반대로 작성자 계정이 삭제된 뒤에도 게시물 기록을 유지해야 한다면 작성자 relation을 nullable로 만들고 `SET_NULL`을 선택할 수 있습니다.

```python
from django.conf import settings


class Entry(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
    )
```

이 선택은 기술적인 취향보다 **데이터의 생명주기와 보존 정책**에 따라 결정해야 합니다.

- parent와 child가 하나의 생명주기를 가지는가? → `CASCADE` 후보
- child를 보존하기 위해 parent 삭제를 막아야 하는가? → `PROTECT` 후보
- parent가 없어져도 child 자체는 의미가 남는가? → `SET_NULL` 후보

또한 Django의 `on_delete`는 Django ORM이 삭제를 수집하고 처리하는 정책입니다. 이를 database의 `ON DELETE` 동작과 완전히 같은 개념으로 가정해서는 안 됩니다. 삭제가 Django ORM 외부의 SQL이나 다른 system에서도 일어날 수 있다면 database constraint와 운영 경로까지 함께 검토해야 합니다.

## Model method

하나의 model instance 자체에서 자연스럽게 계산할 수 있는 동작은 model method로 둘 수 있습니다.

예를 들어 object의 canonical URL을 만드는 규칙은 model이 자신의 식별 정보를 알고 있으므로 다음처럼 둘 수 있습니다.

```python
from django.urls import reverse


class Entry(models.Model):
    slug = models.SlugField(unique=True)

    def get_absolute_url(self):
        return reverse(
            "catalog:entry-detail",
            kwargs={"slug": self.slug},
        )
```

이 메서드는 현재 `Entry`의 `slug`만으로 결과를 결정합니다. 따라서 model이 책임져도 자연스럽습니다.

반면 다음과 같은 작업을 model `save()`에 숨기는 것은 주의해야 합니다.

- 현재 request user의 권한 검사
- 외부 API 호출
- 서로 다른 여러 model의 변경을 하나의 업무 흐름으로 조정
- 특정 화면에서만 필요한 side effect 실행

`save()`는 admin, management command, test, background job 등 여러 경로에서 호출될 수 있습니다. request 문맥에만 존재하는 규칙을 `save()` 안에 넣으면 호출 위치에 따라 예상하지 못한 side effect가 생기기 쉽습니다.

이런 작업은 해당 입력과 transaction 경계를 명시적으로 가진 view, form, service function 등에서 처리하는 편이 추적하기 쉽습니다.

## Migration

model class를 수정해도 database schema는 자동으로 바뀌지 않습니다. Django는 **현재 model 정의**와 **migration에 기록된 이전 model 상태**를 비교해 schema 변경 작업을 migration file로 만듭니다.

일반적인 흐름은 다음 두 단계입니다.

```sh
python manage.py makemigrations
python manage.py migrate
```

### `makemigrations`

`makemigrations`는 model 변경을 migration Python file로 기록합니다.

예를 들어 새 field를 추가하면 다음과 비슷한 operation이 생성될 수 있습니다.

```python
migrations.AddField(
    model_name="entry",
    name="published_at",
    field=models.DateTimeField(null=True, blank=True),
)
```

중요한 점은 `makemigrations`가 **현재 database schema를 기준으로 diff를 계산하는 명령이 아니라는 것**입니다. Django는 migration file에 기록된 model state와 현재 model code를 비교합니다.

### `migrate`

`migrate`는 아직 적용하지 않은 migration operation을 실제 database에 실행합니다.

Django는 적용된 migration을 database의 migration 기록 table에 저장하므로, 어떤 migration까지 적용되었는지 추적할 수 있습니다.

따라서 다음 세 상태를 구분해야 합니다.

```text
model code 변경
    ↓ makemigrations
migration file 생성
    ↓ migrate
실제 database schema 변경
```

model code만 변경하고 `makemigrations`를 하지 않았다면 변경 이력이 없습니다. migration file만 생성하고 `migrate`하지 않았다면 code repository에는 변경 계획이 있지만 현재 database schema에는 아직 적용되지 않은 상태입니다.

## Migration file은 source control에 포함합니다

migration file은 단순한 local cache가 아니라 schema 변경의 순서와 의도를 기록하는 source code입니다. 따라서 일반적으로 Git 같은 source control에 함께 commit합니다.

여러 개발 환경과 운영 database가 같은 migration graph를 공유해야 다음과 같은 순서를 재현할 수 있습니다.

```text
0001_initial
    ↓
0002_entry_published_at
    ↓
0003_category_slug_index
```

개발자마다 migration file을 무시하고 각자 `makemigrations`를 실행하면 파일 이름만 다른 문제가 아니라 operation의 dependency와 schema 변경 순서가 달라질 수 있습니다.

## Migration 검토

migration은 자동 생성되더라도 그대로 적용하기 전에 의도와 일치하는지 확인해야 합니다.

```sh
python manage.py makemigrations --check
python manage.py showmigrations
python manage.py migrate --plan
python manage.py sqlmigrate catalog 0001
```

각 명령의 목적은 다릅니다.

- `makemigrations --check`: 현재 model 변경 중 migration으로 기록되지 않은 것이 있는지 검사합니다. CI에서 migration 누락을 탐지할 때 유용합니다.
- `showmigrations`: migration 목록과 현재 database에서의 적용 여부를 보여 줍니다.
- `migrate --plan`: 앞으로 실행될 migration operation의 순서를 확인합니다.
- `sqlmigrate catalog 0001`: 특정 migration이 현재 database backend에서 어떤 SQL로 변환되는지 확인합니다.

`makemigrations --check`가 성공했다고 해서 database가 최신 schema라는 뜻은 아닙니다. 이 명령은 **model 변경이 migration file에 반영되었는지**를 검사하고, 실제 적용 여부는 `showmigrations`나 `migrate`로 확인합니다.

### rename은 특히 주의합니다

예를 들어 다음처럼 field 이름만 바꾸려는 상황을 생각해 봅니다.

```text
name  →  display_name
```

Django가 이를 `RenameField`로 인식하면 기존 column의 데이터를 유지하면서 이름을 바꿀 수 있습니다. 하지만 상황에 따라 삭제 후 새 field 추가로 판단되면 기존 column의 데이터가 사라질 수 있습니다.

따라서 `makemigrations`가 rename 여부를 묻거나 예상하지 못한 `RemoveField`와 `AddField`가 생성되었다면 migration file을 직접 확인해야 합니다.

또한 기존 row가 존재하는 table에 non-nullable field를 기본값 없이 추가하면 기존 row에 무엇을 저장할지 결정할 수 없습니다. 이 경우 다음과 같은 단계적 변경이 더 안전할 수 있습니다.

```text
1. nullable field 추가
2. 기존 row 값을 backfill하는 data migration 실행
3. null이 남아 있지 않은지 확인
4. field를 non-nullable로 변경
```

schema 변경의 안전성은 model code만 보고 판단할 수 없으며, 기존 데이터의 상태와 운영 database 규모도 함께 고려해야 합니다.

## 첫 migration 전에 custom user model을 확정합니다

새 Django project에서 기본 user model 대신 custom user model을 사용할 계획이라면 **첫 migration을 적용하기 전에** 결정하는 것이 중요합니다.

가장 단순한 출발점은 `AbstractUser`를 상속해 자신의 user model을 만드는 것입니다.

```python
# accounts/models.py
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass
```

그리고 settings에서 Django가 사용할 user model을 지정합니다.

```python
AUTH_USER_MODEL = "accounts.User"
```

다른 model에서 user를 참조할 때는 구체적인 `accounts.User` class를 직접 고정하기보다 `settings.AUTH_USER_MODEL`을 사용합니다.

```python
from django.conf import settings
from django.db import models


class Entry(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="entries",
    )
```

user model은 authentication 관련 table뿐 아니라 여러 app의 foreign key와 migration dependency에 연결되기 쉽습니다. 이미 migration을 적용하고 많은 relation이 만들어진 뒤 `AUTH_USER_MODEL`을 교체하려면 table, foreign key, migration dependency, 기존 데이터 이동을 함께 처리해야 하므로 훨씬 복잡해집니다.

따라서 custom user model을 사용할 가능성이 있다면 project 초기에 먼저 확정한 뒤 첫 migration을 만드는 편이 안전합니다.

## Data migration

schema를 바꾸는 것만으로 충분하지 않고 기존 row의 값을 새 형식으로 변환해야 할 때는 data migration이 필요합니다.

예를 들어 기존 `status` 값을 새 규칙으로 변환해야 한다면 `RunPython`을 사용할 수 있습니다.

```python
from django.db import migrations


def forwards(apps, schema_editor):
    Entry = apps.get_model("catalog", "Entry")
    Entry.objects.filter(status="drafted").update(status="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_entry_status"),
    ]

    operations = [
        migrations.RunPython(
            forwards,
            migrations.RunPython.noop,
        ),
    ]
```

migration code에서 다음처럼 현재 application의 model을 직접 import하지 않습니다.

```python
# 피해야 하는 방식
from catalog.models import Entry
```

migration은 생성된 당시의 schema 상태를 기준으로 나중에도 순서대로 재실행할 수 있어야 합니다. 현재 `catalog.models.Entry`는 시간이 지나 field가 추가되거나 이름이 바뀐 최신 model이므로 과거 migration의 schema와 맞지 않을 수 있습니다.

대신 다음처럼 migration 실행 시점의 historical model을 가져옵니다.

```python
Entry = apps.get_model("catalog", "Entry")
```

### schema migration과 data migration을 구분합니다

두 작업은 목적이 다릅니다.

```text
schema migration
- column 추가/삭제/변경
- index 생성
- constraint 변경
- table 관계 변경

Data migration
- 기존 row 값 변환
- 새 column backfill
- 오래된 값 정규화
- 새로운 참조 관계 구성
```

운영 데이터가 많은 경우 한 migration에서 거대한 table 전체를 한 번에 갱신하면 transaction 시간과 lock 시간이 길어질 수 있습니다. 따라서 변경량이 큰 data migration은 배포 방식, transaction 범위, batch 처리 필요성까지 검토해야 합니다.

## 전체 흐름

model 변경 작업은 다음 순서로 이해하면 됩니다.

```text
1. 저장할 데이터와 관계의 의미를 결정한다.
2. field type과 constraint를 model에 선언한다.
3. 삭제 시 데이터 보존 정책에 맞춰 on_delete를 선택한다.
4. makemigrations로 변경을 migration file에 기록한다.
5. 생성된 migration operation과 SQL을 검토한다.
6. 필요하면 historical model을 사용하는 data migration을 추가한다.
7. migrate로 database에 적용한다.
8. migration file을 application code와 함께 source control에 commit한다.
```

핵심은 **model은 원하는 상태를 선언하고, migration은 그 상태로 database를 이동시키는 변경 이력을 기록한다**는 점입니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/db/models/
- https://docs.djangoproject.com/en/5.2/topics/migrations/
- https://docs.djangoproject.com/en/5.2/ref/models/fields/
- https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#substituting-a-custom-user-model
