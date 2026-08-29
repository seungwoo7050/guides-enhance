# Local Cloud Model

## 개요

`local-cloud-model`은 실제 cloud account나 provider SDK 없이 multi-tenant application의 핵심 상태 규칙을 실행하는 Python library입니다. Tenant 생성과 삭제, 문서 접근, active document quota, event 중복 처리, 재시도, dead letter와 점검용 snapshot을 하나의 in-memory model로 제공합니다.

같은 메서드를 같은 순서로 호출하면 같은 결과를 반환합니다. 실행 시 외부 패키지와 network가 필요하지 않으며, 이 디렉터리만 복사해도 설치하고 테스트할 수 있습니다.

## 확인하는 동작

- Tenant마다 private stateful resource 두 개를 만듭니다.
- 다른 tenant의 문서를 읽거나 덮어쓰지 못하게 합니다.
- `starter`와 `pro` plan별 active document 수를 제한합니다.
- 새 문서를 저장하기 전에 quota를 확인해 일부 상태가 남지 않게 합니다.
- Event를 `(tenant_id, event_id)`로 식별합니다.
- 같은 event를 여러 번 받아도 output과 usage를 한 번만 반영합니다.
- 실패 횟수를 event에 남기고 정해진 횟수에서 dead letter로 옮깁니다.
- Tenant를 삭제하면 문서, 결과, queue, dead letter와 resource를 함께 지웁니다.
- 문서 본문을 제외한 정렬된 snapshot을 새 객체로 반환합니다.

## 설치

Python 3.10 이상이 필요합니다.

```sh
python3 -m pip install . --no-deps --no-build-isolation
```

설치하지 않고 프로젝트 루트에서 바로 테스트할 수도 있습니다.

## 사용 예

```python
from local_cloud_model import CloudModel

model = CloudModel()
model.provision_tenant("tenant-a", plan="starter")
model.store_document("tenant-a", "doc-1", "payload")
model.enqueue_event("event-1", "tenant-a", "doc-1")

status = model.process_next()
snapshot = model.evidence_snapshot("tenant-a")

print(status)                       # processed
print(snapshot["usage_evidence"]) # 1
print(snapshot["active_outputs"])
```

## 공개 API

```text
provision_tenant(tenant_id, plan="starter")
store_document(tenant_id, document_id, content)
read_document(requester_tenant, document_id)
enqueue_event(event_id, tenant_id, document_id)
process_next(max_attempts=2)
drain_events(max_attempts=2, max_steps=100)
usage_for(tenant_id)
delete_tenant(tenant_id)
resource_inventory()
evidence_snapshot(tenant_id)
```

공개 예외:

- `CloudModelError`: 모델이 허용하지 않는 일반 작업
- `AccessDenied`: 다른 tenant의 문서 접근
- `QuotaExceeded`: active document capacity 초과
- `TenantInactive`: 존재하지 않거나 삭제한 tenant 사용
- `EventConflict`: 같은 tenant와 event ID를 다른 문서에 재사용

알 수 없는 plan과 0 이하의 `max_attempts`, `max_steps`에는 `ValueError`를 반환합니다.

## 상태별 동작

### Tenant

Tenant는 `ACTIVE`에서 `DELETED`로만 이동합니다. 삭제한 ID는 다시 사용할 수 없습니다. 존재하지 않는 tenant의 삭제와 이미 끝난 삭제를 다시 요청해도 상태는 바뀌지 않습니다.

Tenant를 만들 때 다음 private resource를 함께 등록합니다.

```text
db-partition:{tenant_id}
object-prefix:{tenant_id}
```

### Document와 quota

`starter`의 quota `2`는 누적 write 횟수가 아니라 동시에 보유할 수 있는 active document 수입니다. 기존 문서를 갱신해도 수는 늘지 않습니다.

새 문서가 capacity를 넘으면 저장하기 전에 `QuotaExceeded`를 반환합니다. 다른 tenant가 이미 사용 중인 `document_id`를 읽거나 덮어쓰려 하면 `AccessDenied`를 반환합니다.

### Event

Event identity는 `(tenant_id, event_id)`입니다. 같은 tenant에서 동일 ID를 같은 문서로 다시 보내는 것은 duplicate delivery로 처리합니다. 동일 ID를 다른 문서에 사용하면 `EventConflict`입니다. 다른 tenant는 같은 문자열 ID를 독립적으로 사용할 수 있습니다.

처리에 성공하면 다음 형식의 output ID를 만듭니다.

```text
result:{tenant_id}:{document_id}:{event_id}
```

Output과 usage를 반영한 뒤 event를 처리 완료로 표시합니다. 이후 같은 event를 처리하면 `duplicate`를 반환하고 상태를 더 바꾸지 않습니다.

### Retry와 dead letter

문서가 없거나 event의 tenant와 문서 소유자가 다르면 attempt를 증가시킵니다.

- attempt가 `max_attempts`보다 작으면 queue 뒤에 다시 넣고 `retry`를 반환합니다.
- attempt가 한도에 도달하면 dead letter로 옮기고 `dead-lettered`를 반환합니다.
- 처리할 event가 없으면 `empty`를 반환합니다.

`drain_events()`는 `max_steps`까지만 처리합니다. 그 뒤에도 queue가 남으면 `CloudModelError`를 반환하므로 미완료 작업을 성공처럼 숨기지 않습니다.

### Tenant 삭제

삭제할 때 다음 활성 상태를 제거합니다.

- document
- output
- pending event
- dead letter
- event 등록 정보
- 처리 완료 event ID
- stateful resource

`DELETED` 표시와 이미 발생한 누적 usage는 종료 사실을 확인하는 자료로 유지합니다.

### Snapshot

`evidence_snapshot()`은 다음 값을 반환합니다.

- tenant 상태와 plan
- active document ID
- output ID
- pending event와 attempt
- dead letter
- event 등록 정보
- resource inventory
- 누적 usage

문서 본문은 포함하지 않습니다. 내부 `dict`와 `list`를 그대로 돌려주지 않으므로 호출자가 반환값을 수정해도 모델 상태가 바뀌지 않습니다. 결과를 정렬하기 때문에 같은 상태에서는 같은 직렬화 결과를 얻을 수 있습니다.

## 파일별 역할

- `local_cloud_model/model.py`: tenant, document, event, usage와 resource 상태를 보관하고 공개 메서드를 구현합니다.
- `local_cloud_model/__init__.py`: 사용할 수 있는 class와 exception만 내보냅니다.
- `tests/test_model.py`: 공개 API만 사용해 격리, 원자적 거부, 중복 처리, 재시도 한도, 삭제와 snapshot을 검사합니다.

## 테스트

```sh
python3 -m unittest discover -s tests -v
```

문법 검사:

```sh
python3 -m compileall -q local_cloud_model tests
```

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 0 | Installable Python package | `pyproject.toml` |
| 1 | Public errors and queued event value | `local_cloud_model/model.py:CloudModelError` |
| 2 | Mutable state stores | `local_cloud_model/model.py:CloudModel.__init__` |
| 3 | Tenant provisioning and private resources | `local_cloud_model/model.py:CloudModel.provision_tenant` |
| 3-1 | Active-tenant validation | `local_cloud_model/model.py:CloudModel._require_active` |
| 4 | Document ownership and active-capacity quota | `local_cloud_model/model.py:CloudModel.store_document` |
| 5 | Tenant-scoped event registration | `local_cloud_model/model.py:CloudModel.enqueue_event` |
| 6 | Duplicate-safe output and usage updates | `local_cloud_model/model.py:CloudModel.process_next` |
| 6-1 | Retry attempts and dead-letter transition | `local_cloud_model/model.py:CloudModel.process_next` |
| 6-2 | Bounded queue draining | `local_cloud_model/model.py:CloudModel.drain_events` |
| 7 | Tenant deletion cleanup | `local_cloud_model/model.py:CloudModel.delete_tenant` |
| 8 | Content-free deterministic snapshots | `local_cloud_model/model.py:CloudModel.evidence_snapshot` |
| 9 | Public API behavior tests | `tests/test_model.py:CloudModelTest` |

## 범위와 한계

- 단일 process에서 동작하는 in-memory model이며 데이터를 파일이나 database에 저장하지 않습니다.
- Concurrent writer, distributed transaction, process crash와 infrastructure partial failure를 재현하지 않습니다.
- 실제 IAM, network rule, encryption, backup, billing, physical deletion과 provider control plane을 검사하지 않습니다.
- Tenant, document와 event ID 형식 및 document 크기를 제한하지 않습니다.
- Dead letter의 담당자, replay 조건, 보존 기간과 alert는 이 library 밖에서 정해야 합니다.
