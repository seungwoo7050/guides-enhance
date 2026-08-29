# Admin과 데이터 작업

## 학습 목표

- admin을 내부 운영 화면으로 사용합니다.
- 목록 column, filter, 검색 field를 실제 운영 작업에 맞게 구성합니다.
- 여러 row를 수정하는 admin action이 같은 service function을 사용하도록 만듭니다.
- fixture와 management command의 용도를 구분합니다.

## Admin 등록

```python
@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "published_at")
    list_filter = ("status", "category")
    search_fields = ("title", "summary")
```

Admin은 model을 등록하는 것만으로도 기본 CRUD를 제공하지만, row가 많아지면 검색과 filter가 없이는 실제 운영에 쓰기 어렵습니다.

## 입력 field 제한

Admin user에게도 모든 field를 무조건 수정하게 하지 않습니다. 자동으로 정해지는 작성자, 검수 시각, 생성된 Entry relation은 `readonly_fields`로 표시할 수 있습니다.

```python
readonly_fields = ("reviewed_by", "reviewed_at", "created_entry")
```

## Admin action

여러 제보를 승인하거나 거절할 때 action이 직접 row를 일괄 `update()`하면 service의 상태 검사와 transaction을 건너뛸 수 있습니다.

```python
for submission_id in queryset.values_list("pk", flat=True):
    approve_submission(
        submission_id=submission_id,
        reviewer=request.user,
    )
```

속도는 느릴 수 있지만 각 row의 현재 상태, staff 권한, transaction 규칙을 동일하게 적용합니다. 대량 처리가 실제 요구가 되면 batch 처리 규칙을 별도로 설계합니다.

## `save_model()` 남용 피하기

Admin hook에 중요한 변경 규칙을 숨기면 다른 view나 command가 같은 model을 저장할 때 동작이 달라집니다. Admin 전용 표시나 작성자 자동 설정은 hook으로 처리할 수 있지만, 여러 model을 수정하거나 상태 전이를 검사하는 작업은 service function으로 분리합니다.

## Fixture

작고 고정된 sample data는 fixture로 제공할 수 있습니다.

```sh
python manage.py loaddata catalog/sample_catalog
```

Fixture는 현재 schema와 field 이름에 강하게 의존합니다. 운영 데이터 migration이나 대량 seed 작업에는 management command 또는 별도 import program이 더 적합할 수 있습니다.

## Management command

반복해서 실행해야 하는 운영 작업은 `management/commands/` 아래 command로 만들 수 있습니다.

```text
catalog/
└── management/
    └── commands/
        └── import_entries.py
```

Command는 argument를 검증하고, 실패 시 0이 아닌 종료 상태를 반환하며, 필요한 transaction 범위를 명확히 해야 합니다.

현재 exercise는 sample fixture만 포함합니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/ref/contrib/admin/
- https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/
- https://docs.djangoproject.com/en/5.2/topics/serialization/
