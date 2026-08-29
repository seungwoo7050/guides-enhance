# Constraint, transaction과 동시 수정

## 학습 목표

- form validation과 database constraint가 막는 오류를 구분합니다.
- 함께 성공하거나 함께 실패해야 하는 변경을 `transaction.atomic()`으로 묶습니다.
- 같은 row를 동시에 수정할 수 있는 작업에서 `select_for_update()`를 사용합니다.
- SQLite와 PostgreSQL의 lock 동작 차이를 인식합니다.

## Validation만으로는 충분하지 않습니다

후기 점수를 1~5로 제한하고, 한 사용자가 한 항목에 후기 하나만 작성하도록 form에서 검사할 수 있습니다. 그러나 동시에 들어온 두 요청은 서로의 저장 전 상태를 보고 모두 통과할 수 있습니다.

Database constraint를 함께 둡니다.

```python
models.CheckConstraint(
    condition=models.Q(rating__gte=1, rating__lte=5),
    name="review_rating_between_1_and_5",
)

models.UniqueConstraint(
    fields=("entry", "author"),
    name="one_review_per_entry_author",
)
```

Form validation은 사용자가 이해할 오류를 빠르게 보여 줍니다. Database constraint는 다른 view, admin, script, 동시 요청을 포함해 잘못된 row 저장을 최종적으로 막습니다.

## Transaction

제보 승인에는 두 변경이 필요합니다.

```text
Submission 상태를 approved로 변경
+ draft Entry 생성
```

한쪽만 저장되면 제보 상태와 실제 항목이 어긋납니다.

```python
@transaction.atomic
def approve_submission(...):
    ...
```

함수 안에서 예외가 발생하면 transaction이 rollback됩니다. 예외를 transaction 내부에서 잡아 무시하면 Django가 rollback해야 할 상황을 알지 못할 수 있으므로, 복구하지 못하는 오류는 atomic block 밖으로 전달합니다.

## Row lock

두 staff가 같은 제보를 동시에 승인할 수 있습니다.

```python
submission = (
    Submission.objects
    .select_for_update()
    .get(pk=submission_id)
)
```

`select_for_update()`는 transaction이 끝날 때까지 선택한 row를 다른 transaction이 수정하지 못하도록 database에 요청합니다. lock을 얻은 뒤 현재 상태가 `pending`인지 다시 확인해야 합니다.

```text
row lock 획득
→ 현재 상태 확인
→ draft Entry 생성
→ Submission 상태 변경
→ commit
```

## Database 차이

SQLite에서는 `select_for_update()`가 PostgreSQL과 같은 row-level lock을 제공하지 않습니다. 학습과 단일 process 개발에는 SQLite가 편리하지만, 동시 write가 중요한 운영 기능은 실제 운영 database에서도 test해야 합니다.

## Service function

Transaction이 필요한 작업을 admin action이나 view 안에 직접 길게 작성하지 않습니다.

```python
approve_submission(submission_id=..., reviewer=...)
```

이 함수가 상태 확인, row lock, Entry 생성, Submission 변경을 모두 수행하면 admin과 다른 호출자가 같은 규칙을 사용합니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/ref/models/constraints/
- https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update
