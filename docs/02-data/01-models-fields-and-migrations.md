# Model, field와 migration

## 학습 목표

- Python class를 database table과 연결하는 방식을 이해합니다.
- field type, relation, `on_delete` 동작을 데이터 보존 기준으로 선택합니다.
- model 변경과 migration 적용을 구분합니다.
- 첫 migration 전에 custom user model을 확정합니다.

## Model은 저장할 데이터와 제약을 선언합니다

```python
class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
```

`max_length`, `unique`, `null`, `blank`, `default`는 서로 다른 의미를 가집니다.

- `null=True`: database에 `NULL` 저장 허용
- `blank=True`: form validation에서 빈 값 허용
- `default`: 새 row를 만들 때 사용할 값
- `unique=True`: database에서 중복 저장 방지

문자열 field는 보통 빈 문자열과 `NULL`을 동시에 허용하지 않습니다. 값이 없다는 상태를 두 가지로 표현하면 query와 validation이 복잡해집니다.

## Relation

```python
class Entry(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    tags = models.ManyToManyField(Tag, related_name="entries", blank=True)
```

`on_delete`는 parent row가 삭제될 때 무엇을 할지 정합니다.

- `CASCADE`: child도 함께 삭제
- `PROTECT`: child가 남아 있으면 parent 삭제 거부
- `SET_NULL`: relation을 끊고 child 유지

분류 항목을 실수로 삭제해 게시물이 함께 사라지면 안 되므로 `Category`에는 `PROTECT`가 적절합니다. 작성자가 탈퇴해도 게시물을 유지해야 한다면 user foreign key에는 `SET_NULL`을 사용할 수 있습니다.

## Model method

URL을 만드는 규칙은 model에 둘 수 있습니다.

```python
def get_absolute_url(self):
    return reverse("catalog:entry-detail", kwargs={"slug": self.slug})
```

반면 request user 권한 검사나 여러 model을 함께 수정하는 작업을 model `save()`에 숨기지 않습니다. 해당 입력을 가진 view나 service function에서 명시적으로 처리하는 편이 낫습니다.

## Migration

model class를 수정해도 database schema는 자동으로 바뀌지 않습니다.

```sh
python manage.py makemigrations
python manage.py migrate
```

- `makemigrations`: model 변경을 migration Python file로 기록
- `migrate`: 아직 적용하지 않은 migration을 database에 실행

Migration file은 source control에 포함합니다. 다른 개발 환경과 운영 database가 같은 schema 변경 순서를 실행하기 위해 필요합니다.

## Migration 검토

```sh
python manage.py makemigrations --check
python manage.py showmigrations
python manage.py sqlmigrate catalog 0001
```

생성된 migration이 의도한 column, index, constraint를 만드는지 확인합니다. field rename을 삭제와 추가로 잘못 인식하면 기존 데이터가 사라질 수 있으므로 migration 생성 질문을 그대로 넘기지 않습니다.

## Data migration

기존 row를 새 형식으로 바꿔야 한다면 `RunPython`을 사용한 data migration을 별도로 작성할 수 있습니다. 현재 model을 직접 import하지 않고 migration 시점의 model을 `apps.get_model()`로 가져와야 과거 migration도 재실행할 수 있습니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/topics/db/models/
- https://docs.djangoproject.com/en/5.2/topics/migrations/
- https://docs.djangoproject.com/en/5.2/ref/models/fields/
