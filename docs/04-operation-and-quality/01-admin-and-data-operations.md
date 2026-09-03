# Admin과 데이터 작업

## 학습 목표

- Django admin을 내부 운영 화면으로 사용합니다.
- 목록 column, filter, 검색 field를 실제 운영 작업에 맞게 구성합니다.
- 여러 row를 수정하는 admin action도 일반 요청과 같은 service function을 사용하도록 만듭니다.
- fixture와 management command의 용도와 한계를 구분합니다.

## Admin의 역할

Django admin은 `ModelAdmin`을 통해 model의 조회·생성·수정·삭제 화면을 빠르게 제공하는 **내부 운영 도구**입니다. 일반 사용자를 위한 제품 UI를 대신하기보다는 운영자나 관리자처럼 신뢰된 사용자가 데이터를 점검하고 수정하는 용도로 사용하는 것이 일반적입니다.

Model을 admin에 등록하면 기본 CRUD 화면을 사용할 수 있지만, 실제로 허용되는 작업은 해당 admin user의 Django permission과 `ModelAdmin`의 permission hook에 의해 제한됩니다. 따라서 "admin에 등록했다"는 것은 모든 admin user에게 모든 변경 권한을 준다는 뜻이 아닙니다.

## Admin 등록

```python
@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "published_at")
    list_filter = ("status", "category")
    search_fields = ("title", "summary")
```

각 설정의 역할은 다음과 같습니다.

- `list_display`: 목록 화면의 column을 지정합니다. 운영자가 상태를 판단할 때 자주 확인하는 값을 우선 배치합니다.
- `list_filter`: 목록 오른쪽에 filter를 제공해 특정 상태나 분류의 row만 빠르게 좁혀 볼 수 있게 합니다.
- `search_fields`: 목록의 검색창에서 검색할 model field를 지정합니다.

Admin은 model을 등록하는 것만으로도 기본 CRUD를 제공하지만, row가 많아지면 검색과 filter가 없이는 원하는 데이터를 찾는 비용이 급격히 커집니다. 따라서 화면에 "무엇을 보여 줄지"보다 운영자가 "어떤 조건으로 row를 찾고 판단하는지"를 기준으로 `list_display`, `list_filter`, `search_fields`를 구성하는 편이 좋습니다.

예를 들어 발행 대기 Entry를 주로 점검한다면 `status`와 `published_at`은 목록과 filter에서 모두 중요할 수 있습니다. 반대로 운영자가 거의 사용하지 않는 내부 식별자까지 목록에 많이 노출하면 한 화면에서 핵심 상태를 파악하기 어려워집니다.

## 입력 field 제한

Admin user에게도 모든 field를 무조건 수정하게 하지 않습니다. 시스템이 계산하거나 다른 workflow의 결과로 정해지는 값을 admin form에서 임의로 수정할 수 있게 하면 데이터의 의미가 깨질 수 있습니다.

예를 들어 작성자, 검수 시각, 승인 과정에서 생성된 `Entry` relation이 다른 로직에 의해 결정된다면 `readonly_fields`로 표시할 수 있습니다.

```python
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    readonly_fields = ("reviewed_by", "reviewed_at", "created_entry")
```

`readonly_fields`는 해당 값을 admin 변경 form에서 읽기 전용으로 보여 주는 설정입니다. **Database 자체를 불변으로 만드는 제약은 아닙니다.** 다른 application code, management command, shell 등에서는 여전히 값을 변경할 수 있으므로 반드시 지켜야 하는 invariant는 model constraint나 service logic 등 별도의 계층에서도 보장해야 합니다.

또한 단순히 화면에서 숨겨야 하는 field와 화면에 보여 주되 수정만 막아야 하는 field를 구분합니다. 운영자가 현재 값을 확인해야 하지만 직접 바꾸면 안 되는 값에는 `readonly_fields`가 적합합니다.

## Admin action

Admin action은 목록에서 여러 row를 선택한 뒤 같은 작업을 한 번에 실행하기 위한 기능입니다. 예를 들어 여러 제보(`Submission`)를 승인하거나 거절하는 작업에 사용할 수 있습니다.

문제는 action 안에서 곧바로 `QuerySet.update()`를 호출해 상태를 바꾸는 경우입니다.

```python
queryset.update(status=Submission.Status.APPROVED)
```

이 코드는 SQL `UPDATE`를 직접 수행하므로 빠르지만, application이 승인 작업에 대해 별도로 정의한 다음 규칙을 우회할 수 있습니다.

- 현재 상태에서 승인이 가능한지 검사하는 규칙
- 승인자에게 필요한 업무 권한 검사
- 승인 시각이나 관련 object를 함께 변경하는 규칙
- 여러 변경을 하나의 transaction으로 묶는 규칙
- service function 안에 정의한 logging이나 후속 처리

따라서 일반 view에서 이미 `approve_submission()`과 같은 service function을 통해 상태 전이를 수행한다면 admin action도 같은 함수를 호출하는 편이 일관성이 높습니다.

```python
for submission_id in queryset.values_list("pk", flat=True):
    approve_submission(
        submission_id=submission_id,
        reviewer=request.user,
    )
```

이 구조의 핵심은 **admin만의 별도 승인 규칙을 만드는 것이 아니라 동일한 업무 동작을 다른 진입점에서 재사용한다는 것**입니다. Web view, admin, management command 중 어디에서 호출하더라도 같은 상태 검사와 변경 규칙이 적용됩니다.

다만 위 코드는 선택된 row마다 service를 한 번씩 호출하므로 대량 처리에서는 느릴 수 있습니다. 또한 service가 각 호출마다 별도 transaction을 연다면 앞의 일부 row는 성공하고 뒤의 row는 실패하는 부분 성공(partial success)이 발생할 수 있습니다. 전체 batch가 반드시 모두 성공하거나 모두 실패해야 하는 요구가 있다면 그 요구 자체를 명시하고 batch 전용 transaction과 locking 전략을 설계해야 합니다.

즉, 성능 때문에 처음부터 `update()`로 업무 규칙을 생략하지 말고, 실제로 대량 처리가 요구될 때 **어떤 invariant를 유지하면서 batch화할지**를 별도로 결정합니다.

## `save_model()` 남용 피하기

`ModelAdmin.save_model()`은 admin에서 model을 저장할 때 개입할 수 있는 hook입니다.

예를 들어 admin을 통해 새 object를 만들 때 현재 사용자를 작성자로 기록하는 정도의 admin 전용 처리는 자연스럽습니다.

```python
def save_model(self, request, obj, form, change):
    if not change:
        obj.created_by = request.user
    super().save_model(request, obj, form, change)
```

하지만 중요한 업무 규칙을 `save_model()` 안에만 숨기면 문제가 생깁니다. 같은 model을 일반 view, API, management command, test fixture setup 등 다른 경로에서 저장하면 그 hook은 실행되지 않기 때문입니다. 결과적으로 "같은 상태 변경"처럼 보여도 진입점에 따라 동작이 달라질 수 있습니다.

따라서 다음과 같이 구분합니다.

- admin에서만 필요한 작성자 자동 설정이나 admin 표시와 밀접한 처리는 admin hook에서 처리할 수 있습니다.
- 여러 model을 함께 수정하는 작업, 상태 전이 가능 여부 검사, transaction 경계처럼 **진입점과 무관하게 항상 적용되어야 하는 업무 규칙**은 service function으로 분리합니다.

`save_model()`은 service layer를 대체하는 위치가 아니라 admin 저장 과정에 필요한 얇은 adapter로 보는 편이 안전합니다.

## Fixture

Fixture는 미리 직렬화해 둔 데이터를 `loaddata`로 database에 적재하는 기능입니다. 작고 고정된 sample data나 개발·학습 환경에서 반복해서 필요한 초기 데이터를 제공할 때 유용합니다.

```sh
python manage.py loaddata catalog/sample_catalog
```

예를 들어 category 몇 개나 실습에서 사용하는 고정 sample Entry처럼 내용이 작고 변경 빈도가 낮은 데이터에는 fixture가 간단한 선택입니다.

Fixture는 다음 특성이 있습니다.

- 저장된 field 이름과 model 구조가 현재 schema와 맞아야 합니다.
- foreign key 등 relation이 있다면 참조 대상도 올바르게 존재하거나 함께 로드되어야 합니다.
- 복잡한 입력 검증, 외부 파일 parsing, 조건부 갱신 같은 절차를 표현하기에는 적합하지 않습니다.

따라서 fixture를 "모든 초기 데이터 작업을 위한 범용 script"로 사용하면 schema 변화에 취약해지고 작업 절차를 코드로 표현하기 어려워집니다.

운영 데이터 migration, 외부 시스템에서 받은 대량 데이터 import, 여러 번 안전하게 재실행해야 하는 seed 작업에는 management command나 별도 import program이 더 적합할 수 있습니다.

## Management command

반복해서 실행해야 하는 application 운영 작업은 Django custom management command로 만들 수 있습니다. Command module은 app의 `management/commands/` 아래에 둡니다.

```text
catalog/
└── management/
    └── commands/
        └── import_entries.py
```

이 파일에 `BaseCommand`를 상속한 `Command` class를 정의하면 다음처럼 실행할 수 있습니다.

```sh
python manage.py import_entries --path ./entries.csv
```

간단한 구조는 다음과 같습니다.

```python
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Import catalog entries from a file"

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True)

    def handle(self, *args, **options):
        path = options["path"]

        if not path:
            raise CommandError("--path is required")

        # 파일을 읽고 입력을 검증한 뒤 필요한 service를 호출합니다.
```

운영용 command에서는 최소한 다음 사항을 명확히 해야 합니다.

- **입력 계약**: 필요한 argument와 허용되는 값을 검증합니다.
- **실패 신호**: 실패를 성공처럼 끝내지 말고 `CommandError` 같은 방식으로 실패를 호출자에게 전달합니다. shell이나 scheduler는 종료 상태를 통해 성공 여부를 판단할 수 있습니다.
- **transaction 범위**: 전체 작업이 하나의 원자적 변경이어야 하는지, row 단위로 독립적으로 처리할지 결정합니다.
- **재실행 가능성**: 작업 도중 실패한 뒤 다시 실행했을 때 duplicate나 잘못된 상태 전이가 생기지 않는지 고려합니다.
- **업무 규칙 재사용**: 이미 service function으로 정의된 변경 규칙이 있다면 command가 model을 직접 우회해서 수정하지 않고 해당 service를 호출하는 방식을 우선 검토합니다.

예를 들어 10만 row를 import하는 작업 전체를 하나의 transaction으로 묶으면 rollback 의미는 단순해지지만 transaction이 오래 유지되어 lock과 resource 사용량이 커질 수 있습니다. 반대로 일정 크기의 batch마다 commit하면 처리 부담은 줄어들지만 중간 실패 시 일부 데이터만 반영될 수 있습니다. 따라서 transaction 범위는 단순한 구현 취향이 아니라 **실패 시 어떤 상태를 허용할 것인지**에 따라 정해야 합니다.

## Fixture와 management command 선택 기준

두 방식은 모두 데이터를 넣을 수 있지만 목적이 다릅니다.

| 상황 | 더 적합한 선택 | 이유 |
| --- | --- | --- |
| 작고 고정된 sample data | Fixture | 별도 처리 코드 없이 간단히 로드할 수 있음 |
| 실습용 초기 데이터 | Fixture | repository에 고정된 데이터를 함께 배포하기 쉬움 |
| 외부 CSV/JSON import | Management command | parsing과 validation 절차를 코드로 표현할 수 있음 |
| 대량 seed | Management command | batch, transaction, progress, 재실행 정책을 제어할 수 있음 |
| 반복 운영 작업 | Management command | argument, 실패 상태, logging 등 실행 계약을 명확히 할 수 있음 |
| 기존 데이터를 조건에 따라 변환 | Data migration 또는 목적에 맞는 command | 단순 fixture보다 변경 절차를 명시적으로 표현할 수 있음 |

현재 exercise는 sample fixture만 포함합니다. 따라서 이 단계에서는 `loaddata`로 고정 sample data를 적재하는 흐름에 집중하고, management command는 반복 가능하거나 절차가 필요한 운영 데이터 작업에 사용하는 도구로 구분하면 됩니다.

## 정리

- Django admin은 내부 운영을 위한 빠른 CRUD 진입점이며, 운영자가 데이터를 찾고 판단하는 방식에 맞춰 목록·filter·검색을 구성합니다.
- Admin form에서 임의 수정하면 안 되는 값은 `readonly_fields`로 제한할 수 있지만, 이는 database invariant를 대신하지 않습니다.
- Admin action이 중요한 상태 변경을 수행한다면 일반 application 경로와 같은 service function을 재사용해 업무 규칙을 일관되게 적용합니다.
- `save_model()`에는 admin에만 필요한 얇은 처리를 두고, 공통 업무 규칙을 숨기지 않습니다.
- 작고 고정된 데이터는 fixture가 간단하지만, validation·batch·transaction·재실행 정책이 필요한 작업은 management command가 더 적합합니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/ref/contrib/admin/
- https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/
- https://docs.djangoproject.com/en/5.2/topics/serialization/
