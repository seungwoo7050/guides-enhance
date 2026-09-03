# Constraint, transaction과 동시 수정

## 학습 목표

- form validation과 database constraint가 각각 막는 오류와 한계를 구분합니다.
- 함께 성공하거나 함께 실패해야 하는 변경을 `transaction.atomic()`으로 하나의 transaction에 묶습니다.
- 같은 row를 동시에 수정할 수 있는 작업에서 `select_for_update()`로 수정 순서를 직렬화합니다.
- constraint 위반과 transaction 실패를 `IntegrityError`와 rollback 관점에서 이해합니다.
- SQLite와 PostgreSQL의 lock 동작 차이를 인식하고 동시성 기능을 운영 database에서 검증합니다.

## Validation만으로는 충분하지 않습니다

후기 점수를 1~5로 제한하고, 한 사용자가 한 항목에 후기 하나만 작성하도록 form에서 검사할 수 있습니다.

예를 들어 form validation은 다음과 같은 문제를 사용자에게 저장 전에 알려 줄 수 있습니다.

```text
rating = 8
→ "점수는 1~5 사이여야 합니다."

같은 사용자의 기존 후기 존재
→ "이미 후기를 작성했습니다."
```

이 검사는 사용자 경험에는 유용하지만 **database의 최종 무결성을 보장하는 장치가 아닙니다.**

특히 동시 요청에서는 두 요청이 거의 같은 시점에 같은 상태를 읽을 수 있습니다.

```text
요청 A: 기존 후기 없음 확인
요청 B: 기존 후기 없음 확인

요청 A: validation 통과
요청 B: validation 통과

요청 A: INSERT
요청 B: INSERT
```

두 요청이 서로의 저장 전 상태를 보았기 때문에 application-level 검사만으로는 중복 저장을 막지 못할 수 있습니다.

따라서 database constraint를 함께 둡니다.

```python
class Review(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
            models.UniqueConstraint(
                fields=("entry", "author"),
                name="one_review_per_entry_author",
            ),
        ]
```

각 constraint의 의미는 다음과 같습니다.

```text
CheckConstraint
→ 저장된 row가 지정한 조건을 만족해야 함

UniqueConstraint
→ 지정한 column 조합이 다른 row와 중복될 수 없음
```

따라서 database는 어느 코드 경로에서 저장하더라도 다음 규칙을 최종적으로 검사합니다.

```text
1 <= rating <= 5

(entry, author) 조합은 유일
```

### Validation과 constraint의 역할은 다릅니다

두 계층은 서로 대체하지 않고 역할을 나눕니다.

```text
Form / serializer / service validation
        ↓
사용자가 이해할 수 있는 오류를 저장 전에 제공

Database constraint
        ↓
어떤 코드 경로에서든 잘못된 최종 상태의 저장을 거부
```

database constraint는 다음 경로도 보호합니다.

- 일반 view
- Django admin
- management command
- shell이나 script
- background worker
- 동시에 실행되는 여러 request

반대로 constraint 위반만 기다렸다가 database 오류를 그대로 사용자에게 보여 주는 것도 좋은 입력 처리 방식은 아닙니다. 예측 가능한 입력 오류는 application에서 먼저 검사해 이해하기 쉬운 메시지를 제공하고, database constraint는 마지막 안전장치로 유지합니다.

또한 `Model.save()`가 자동으로 모든 form/model validation을 실행해 주는 것은 아닙니다. 따라서 Python 쪽 validation이 존재한다는 이유만으로 database constraint를 생략해서는 안 됩니다.

## Constraint 위반은 저장 시점에 발생할 수 있습니다

동시 요청에서는 application validation을 모두 통과한 뒤 한쪽이 database constraint에서 거부될 수 있습니다.

예를 들어 `(entry, author)`에 unique constraint가 있다면 다음 상황이 가능합니다.

```text
요청 A ─ 기존 후기 없음 ─┐
                          ├─ 둘 다 validation 통과
요청 B ─ 기존 후기 없음 ─┘

요청 A ─ INSERT 성공
요청 B ─ INSERT 시 unique constraint 위반
```

Django에서는 이런 database 무결성 위반이 보통 `IntegrityError`로 나타납니다.

```python
from django.db import IntegrityError, transaction

try:
    with transaction.atomic():
        Review.objects.create(
            entry=entry,
            author=request.user,
            rating=rating,
        )
except IntegrityError:
    ...
```

중요한 점은 `IntegrityError`를 모든 경우에 같은 사용자 오류로 해석하지 않는 것입니다. 한 transaction 안에는 여러 constraint와 여러 SQL이 있을 수 있으므로, 어느 constraint가 실패했는지 구분할 필요가 있다면 입력 구조와 database 오류 처리를 신중하게 설계해야 합니다.

## Transaction은 여러 변경을 하나의 성공 단위로 만듭니다

제보 승인에는 두 변경이 필요하다고 가정합니다.

```text
Submission 상태를 approved로 변경
+
draft Entry 생성
```

두 작업 중 하나만 성공하면 데이터가 서로 어긋납니다.

예를 들어 Entry 생성 후 Submission 상태 변경에서 오류가 발생하면 다음과 같은 잘못된 상태가 남을 수 있습니다.

```text
Entry       = 생성됨
Submission  = pending
```

반대로 Submission만 먼저 approved가 되고 Entry 생성이 실패할 수도 있습니다.

이 두 변경이 하나의 논리적 작업이라면 transaction으로 묶습니다.

```python
from django.db import transaction


@transaction.atomic
def approve_submission(...):
    ...
```

또는 block 범위를 명시할 수 있습니다.

```python
with transaction.atomic():
    ...
```

`atomic()` block 안에서 수행한 database 변경은 정상적으로 끝나면 commit되고, 처리되지 않은 예외 때문에 block을 벗어나면 rollback됩니다.

개념적으로 다음과 같습니다.

```text
transaction 시작
    ↓
Submission 조회/검증
    ↓
Entry 생성
    ↓
Submission 수정
    ↓
모두 성공
    ↓
COMMIT
```

중간에 실패하면 다음과 같습니다.

```text
transaction 시작
    ↓
Entry 생성
    ↓
Submission 수정 중 예외
    ↓
ROLLBACK
```

rollback되면 같은 transaction 안에서 수행한 변경은 database에 최종 반영되지 않습니다.

## `atomic()`은 business rule 자체를 만들어 주지 않습니다

transaction을 사용한다고 잘못된 상태 전이가 자동으로 막히는 것은 아닙니다.

예를 들어 다음 코드는 두 변경을 atomic하게 만들지만, 이미 승인된 Submission을 다시 승인하는 문제까지 자동으로 해결하지는 않습니다.

```python
@transaction.atomic
def approve_submission(submission_id):
    submission = Submission.objects.get(pk=submission_id)

    Entry.objects.create(...)
    submission.status = Submission.Status.APPROVED
    submission.save(update_fields=["status"])
```

동시에 두 요청이 `pending` 상태를 읽으면 둘 다 Entry를 생성할 가능성이 있습니다.

따라서 동시 수정이 가능한 business rule에서는 다음 두 가지를 구분해야 합니다.

```text
transaction.atomic()
→ 여러 database 변경의 원자성 보장

select_for_update()
→ 같은 row를 기준으로 경쟁하는 transaction의 수정 순서 제어
```

둘은 목적이 다르며 함께 필요한 경우가 많습니다.

## `atomic()` 내부에서 database 오류를 숨기지 않습니다

transaction 안에서 database 오류가 발생하면 해당 transaction은 정상적으로 계속 사용할 수 없는 상태가 될 수 있습니다.

따라서 다음처럼 `IntegrityError`를 같은 `atomic()` block 내부에서 잡고 무시한 뒤 query를 계속하는 방식은 피합니다.

```python
# 권장하지 않는 구조
with transaction.atomic():
    try:
        Review.objects.create(...)
    except IntegrityError:
        pass

    Entry.objects.create(...)  # transaction 상태가 이미 깨졌을 수 있음
```

오류를 처리해야 한다면 exception handling의 경계를 `atomic()` 바깥에 두는 방식이 명확합니다.

```python
try:
    with transaction.atomic():
        Review.objects.create(...)
except IntegrityError:
    # 여기서는 atomic block이 이미 종료되어 rollback 처리가 끝난 상태
    ...
```

더 작은 부분만 별도 rollback 대상으로 만들고 싶다면 nested `atomic()`을 사용할 수도 있습니다.

```python
with transaction.atomic():
    do_first_work()

    try:
        with transaction.atomic():
            do_risky_work()
    except IntegrityError:
        recover()

    do_later_work()
```

안쪽 `atomic()`은 savepoint를 사용할 수 있으며, 안쪽 작업만 rollback한 뒤 바깥 transaction을 계속 진행할 수 있습니다. 다만 복구 후에도 전체 business invariant가 올바른지 확실할 때만 이런 구조를 사용합니다.

## Row lock이 필요한 이유

두 staff가 같은 Submission을 동시에 승인한다고 가정합니다.

lock 없이 다음 순서로 실행될 수 있습니다.

```text
Staff A                     Staff B
-------                     -------
pending 읽음
                            pending 읽음
Entry 생성
                            Entry 생성
approved 저장
                            approved 저장
```

최종 Submission 상태는 하나의 `approved`이지만 draft Entry는 두 개 생길 수 있습니다.

이 문제는 단순히 transaction으로 둘러싼다고 없어지지 않습니다. 두 transaction 모두 상대 transaction의 commit 전 상태를 읽고 작업을 진행할 수 있기 때문입니다.

같은 Submission을 기준으로 승인 작업을 하나씩 처리해야 한다면 row lock을 사용합니다.

```python
submission = (
    Submission.objects
    .select_for_update()
    .get(pk=submission_id)
)
```

`select_for_update()`는 지원하는 database에서 선택한 row에 lock을 걸도록 요청합니다. 다른 transaction이 같은 row에 충돌하는 lock이나 update를 시도하면 일반적으로 현재 transaction의 lock이 풀릴 때까지 기다리게 됩니다.

lock은 transaction 종료 시점에 해제됩니다.

따라서 `select_for_update()`는 `transaction.atomic()` 안에서 사용해야 합니다.

```python
@transaction.atomic
def approve_submission(submission_id, reviewer):
    submission = (
        Submission.objects
        .select_for_update()
        .get(pk=submission_id)
    )

    ...
```

PostgreSQL처럼 `SELECT ... FOR UPDATE`를 지원하는 backend에서 autocommit 상태로 해당 queryset을 평가하면 Django는 transaction 없이 lock을 유지할 수 없기 때문에 `TransactionManagementError`를 발생시킵니다.

## Lock을 얻은 뒤 상태를 다시 확인합니다

row lock의 목적은 row를 읽는 것 자체가 아니라 **lock을 획득한 시점의 현재 상태를 기준으로 의사결정하는 것**입니다.

승인 작업은 다음 순서가 되어야 합니다.

```text
transaction 시작
    ↓
row lock 획득
    ↓
현재 상태 다시 확인
    ↓
business rule 검사
    ↓
Entry 생성
    ↓
Submission 상태 변경
    ↓
commit
    ↓
lock 해제
```

예를 들면 다음과 같습니다.

```python
from django.db import transaction


@transaction.atomic
def approve_submission(*, submission_id, reviewer):
    submission = (
        Submission.objects
        .select_for_update()
        .get(pk=submission_id)
    )

    if submission.status != Submission.Status.PENDING:
        raise ValueError("Only pending submissions can be approved.")

    entry = Entry.objects.create(
        title=submission.title,
        # 필요한 field 복사
    )

    submission.status = Submission.Status.APPROVED
    submission.reviewed_by = reviewer
    submission.save(
        update_fields=[
            "status",
            "reviewed_by",
        ]
    )

    return entry
```

두 요청이 동시에 들어오면 개념적으로 다음처럼 됩니다.

```text
요청 A                    요청 B
------                    ------
row lock 획득
pending 확인
                          같은 row lock 대기
Entry 생성
approved 저장
commit / lock 해제
                          lock 획득
                          approved 상태 확인
                          승인 거부
```

두 번째 요청은 첫 번째 요청이 끝난 뒤 **변경된 최신 상태를 확인하고 작업을 중단**할 수 있습니다.

## `select_for_update()`가 모든 읽기를 막는 것은 아닙니다

"row가 lock되면 다른 transaction은 그 row를 전혀 읽을 수 없다"라고 이해하면 정확하지 않습니다.

PostgreSQL의 MVCC에서는 일반적인 non-locking `SELECT`가 다른 transaction이 잡은 row lock 때문에 항상 막히는 것은 아닙니다. 어떤 version의 row를 볼지는 transaction isolation과 snapshot 규칙에 따라 결정됩니다.

`select_for_update()`에서 중요한 보장은 다음과 같습니다.

```text
이 row를 수정하거나 충돌하는 lock을 얻어
같은 business operation을 진행하려는 transaction끼리
순서를 조정할 수 있다.
```

따라서 "누구도 읽을 수 없게 한다"가 아니라 **동시에 수정하려는 경쟁 transaction을 조정하는 도구**로 이해해야 합니다.

## Lock 범위는 가능한 한 짧게 유지합니다

row lock은 동시 실행을 일부 직렬화하므로 너무 오래 유지하면 다른 request의 대기 시간이 늘어납니다.

다음처럼 transaction 안에서 느린 외부 작업을 수행하면 좋지 않습니다.

```python
@transaction.atomic
def approve_submission(...):
    submission = (
        Submission.objects
        .select_for_update()
        .get(pk=...)
    )

    call_external_api()   # 오래 걸릴 수 있음

    ...
```

외부 HTTP 호출, 긴 계산, 사용자 입력 대기 같은 작업은 가능한 한 lock을 잡기 전이나 commit 후로 분리합니다.

좋은 기본 원칙은 다음과 같습니다.

```text
transaction 시작
→ 필요한 row lock
→ 짧은 상태 검사
→ 필요한 database 변경
→ commit
```

transaction과 lock의 범위를 business invariant를 지킬 수 있는 최소 범위로 유지합니다.

## Database constraint와 row lock은 해결하는 문제가 다릅니다

constraint와 lock은 경쟁 관계가 아니라 서로 다른 무결성 문제를 해결합니다.

### Constraint

최종 database 상태가 허용되는지 검사합니다.

```text
rating은 1~5
(entry, author)는 unique
```

동시 요청이 발생하더라도 잘못된 최종 row 저장을 막습니다.

### Row lock

현재 상태를 읽고 그 상태를 기준으로 여러 단계를 수행하는 작업의 순서를 제어합니다.

```text
pending인지 확인
→ 관련 row 생성
→ approved로 변경
```

이처럼 **읽은 상태를 근거로 다음 변경을 결정하는 read-modify-write 작업**에서 중요합니다.

실제 service에서는 둘을 함께 사용할 수 있습니다.

```text
database constraint
    +
transaction.atomic()
    +
필요한 row의 select_for_update()
```

각 장치가 서로 다른 실패 경로를 막습니다.

## SQLite와 PostgreSQL의 lock 차이

SQLite는 개발 환경에서 간단히 사용하기 좋지만 PostgreSQL과 동시성 제어 방식이 다릅니다.

Django에서 SQLite의 `select_for_update()`는 PostgreSQL과 같은 row-level `SELECT ... FOR UPDATE` lock을 제공하지 않습니다. SQLite backend에서는 `select_for_update()`가 실질적인 row lock 역할을 하지 않습니다.

따라서 다음 코드가 SQLite에서 문제없이 실행된다고 해서 PostgreSQL에서의 경쟁 상황까지 검증된 것은 아닙니다.

```python
Submission.objects.select_for_update().get(pk=...)
```

특히 다음 기능은 실제 운영 database에서도 test해야 합니다.

- 같은 row에 대한 동시 승인
- 재고 차감
- 잔액 변경
- 상태 전이
- worker가 동시에 claim하는 작업
- unique constraint와 동시 INSERT의 상호작용
- lock 대기와 deadlock 가능성이 있는 작업

개념적으로 차이는 다음처럼 이해할 수 있습니다.

```text
SQLite
→ write concurrency가 제한적이고
  `select_for_update()`가 PostgreSQL식 row lock을 제공하지 않음

PostgreSQL
→ MVCC와 row-level lock을 제공하며
  `SELECT ... FOR UPDATE`로 특정 row의 경쟁 update를 조정할 수 있음
```

SQLite test는 application의 기본 동작을 확인하는 데는 유용하지만, **동시성 보장은 사용 중인 production database의 실제 semantics에 의존합니다.**

## 동시성 test에서는 transaction 경계도 확인합니다

동시성 코드를 test할 때는 단순히 service function을 한 번 호출해 성공 여부만 확인해서는 lock 동작을 검증할 수 없습니다.

다음 사항을 별도로 확인해야 합니다.

```text
두 transaction이 실제로 겹치는가?
첫 번째 transaction이 lock을 유지하고 있는가?
두 번째 transaction이 그 lock과 경쟁하는가?
첫 번째 commit 뒤 두 번째가 최신 상태를 다시 확인하는가?
```

또한 Django의 `TestCase`는 각 test를 transaction으로 감싸는 특성이 있으므로, transaction 자체의 동작을 검증해야 하는 test에서는 `TransactionTestCase`가 더 적절한 경우가 있습니다.

핵심은 test 환경이 실제로 검증하려는 transaction 경계를 재현하는지 확인하는 것입니다.

## Service function

transaction과 lock이 필요한 작업을 admin action이나 view 안에 길게 작성하면 같은 business rule이 여러 위치에 복제되기 쉽습니다.

view는 입력과 HTTP 처리를 담당하고, 승인 규칙은 service function에 모을 수 있습니다.

```python
approve_submission(
    submission_id=submission_id,
    reviewer=request.user,
)
```

service function이 다음 책임을 함께 가집니다.

```text
transaction 시작
→ Submission row lock
→ 현재 상태 검사
→ Entry 생성
→ Submission 상태 변경
→ 결과 반환
```

예를 들어 다음과 같이 구성할 수 있습니다.

```python
from django.db import transaction


@transaction.atomic
def approve_submission(*, submission_id, reviewer):
    submission = (
        Submission.objects
        .select_for_update()
        .get(pk=submission_id)
    )

    if submission.status != Submission.Status.PENDING:
        raise ValueError("Submission is not pending.")

    entry = Entry.objects.create(
        title=submission.title,
    )

    submission.status = Submission.Status.APPROVED
    submission.reviewed_by = reviewer
    submission.save(
        update_fields=[
            "status",
            "reviewed_by",
        ]
    )

    return entry
```

그러면 admin, 일반 view, management command 등 다른 호출자가 같은 승인 규칙을 재사용할 수 있습니다.

중요한 것은 "service function이라는 이름의 계층을 반드시 만들어야 한다"는 것이 아니라, **transaction 경계와 동시성 규칙을 여러 진입점에서 중복 구현하지 않도록 한곳에 명시적으로 모으는 것**입니다.

## 정리

데이터 무결성 문제는 한 가지 장치로 모두 해결하지 않습니다.

```text
사용자 입력 오류
    ↓
form / application validation

허용되지 않는 최종 database 상태
    ↓
CheckConstraint / UniqueConstraint 등

여러 변경의 부분 성공
    ↓
transaction.atomic()

같은 상태를 동시에 읽고 수정하는 경쟁
    ↓
select_for_update() + 상태 재확인
```

승인처럼 여러 row를 변경하는 동시성 작업은 다음 흐름으로 생각하면 됩니다.

```text
transaction 시작
    ↓
경쟁 기준 row lock
    ↓
현재 상태 확인
    ↓
business rule 검사
    ↓
관련 변경 수행
    ↓
database constraint 검증
    ↓
commit
    ↓
lock 해제
```

그리고 이 동작은 SQLite의 개발 환경만으로 판단하지 않고 실제 운영 database에서도 검증해야 합니다.

## 공식 문서

- https://docs.djangoproject.com/en/5.2/ref/models/constraints/
- https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update
