# LedgerLab Policy

`LedgerLab Policy`는 합성 보고서와 작업자 객체에 대한 접근 가능 여부를 판정하는 Python 라이브러리입니다.

보고서를 읽을 때는 요청한 사용자와 보고서 소유자, tenant, 완료 상태를 함께 확인합니다. 작업자가 객체를 읽을 때는 service identity, credential 만료 시각과 폐기 여부, tenant, job, 객체 경로를 확인합니다. 모든 판정은 조사에 사용할 수 있는 authorization event를 반환합니다. `detect()`는 같은 `correlation_id`에 속한 범위 초과 거절을 하나의 alert로 묶습니다.

외부 네트워크, 실제 credential, cloud account와 관리자 권한은 사용하지 않습니다. 모든 결과는 `fixtures/state.json`에 저장된 합성 상태만으로 결정됩니다.

## 주요 기능

- 보고서 소유자, tenant와 완료 상태를 한 번의 판정에서 확인합니다.
- 작업자 credential의 service identity, 만료 시각, 폐기 여부, tenant와 job을 확인합니다.
- 객체 경로를 `/`로 나눈 segment 단위로 비교하여 `job-81`과 `job-81x`를 구분합니다.
- 절대 경로, backslash, 빈 segment, `.`와 `..`를 거절합니다.
- 판정에 필요한 상태나 현재 시각을 확인할 수 없으면 기본적으로 거절합니다.
- 입력 상태를 바꾸지 않고 `decision`, `reason_code`, `reason`과 audit event를 반환합니다.
- 같은 event가 중복되거나 순서가 바뀌어도 alert 수와 근거 event 목록이 달라지지 않습니다.
- alert에 actor, effective actor, credential, 거절 사유와 원본 event ID를 남깁니다.
- 실행 시 외부 패키지가 필요하지 않습니다.

## 프로젝트 구성

```text
ledgerlab-policy/
├── examples/demo.py
├── fixtures/state.json
├── src/ledgerlab_policy/
│   ├── __init__.py
│   ├── detection.py
│   └── policy.py
├── tests/
│   ├── _support.py
│   ├── test_detection.py
│   └── test_policy.py
├── pyproject.toml
└── README.md
```

- `policy.py`: 접근 가능 여부를 판정하고 audit event를 만듭니다.
- `detection.py`: 범위 초과 거절을 고르고 `correlation_id`별 alert를 만듭니다.
- `fixtures/state.json`: 정상·경계·거절 사례에서 공통으로 사용하는 합성 상태입니다.
- `tests/`: 정상 기능, 기본 거절, 입력 상태 불변성, event 필드와 중복 event 처리를 검사합니다.

## 요구 사항

- Python 3.10+
- 실행 시 표준 라이브러리 외 의존성 없음

## 실행

설치하지 않고 예제를 실행할 수 있습니다.

```sh
python3 examples/demo.py
```

`setuptools>=61`이 설치된 환경에서는 wheel을 만들 수 있습니다.

```sh
python3 -m pip wheel --no-deps --no-build-isolation . -w dist
python3 -m pip install dist/ledgerlab_policy-1.0.0-py3-none-any.whl
```

설치한 뒤 다음 함수를 불러올 수 있습니다.

```python
from ledgerlab_policy import authorize_object, authorize_report, detect
```

## 공개 API

```python
authorize_report(state, request) -> dict
authorize_object(state, request) -> dict
detect(events) -> list[dict]
```

두 authorization 함수는 다음 값을 반환합니다.

```json
{
  "decision": "allow|deny",
  "reason_code": "stable_machine_readable_code",
  "reason": "human-readable reason",
  "event": {
    "event_id": "EV-001",
    "event_type": "authorization.decision",
    "actor_id": "...",
    "effective_actor_id": "...",
    "credential_id": "...",
    "tenant_id": "...",
    "job_id": "...",
    "action": "...",
    "resource_id": "...",
    "decision": "allow|deny",
    "reason_code": "...",
    "reason": "...",
    "correlation_id": "...",
    "policy_version": "ledgerlab-v1"
  }
}
```

## 검사

프로젝트 루트에서 실행합니다.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

검사 범위는 다음과 같습니다.

- 소유자가 완료된 자신의 보고서를 읽는 요청 허용
- 현재 job credential로 해당 job 객체를 읽는 요청 허용
- 다른 소유자, 다른 tenant, 미완료·존재하지 않는 보고서 거절
- 다른 job, 유사한 prefix, `..`, 만료·폐기된 credential 거절
- 만료 시각과 현재 시각이 같을 때 거절
- 판정 상태나 현재 시각을 확인할 수 없을 때 거절
- 판정 전후 입력 상태의 SHA-256이 같은지 확인
- 모든 audit event 필드와 안정된 `reason_code` 확인
- 정상 event와 단순 중복 event가 alert를 만들지 않는지 확인
- 범위 초과 거절이 요청별로 분리되고 원본 event ID를 보존하는지 확인
- 내용이 충돌하는 중복 event가 범위 초과 거절을 숨기지 못하는지 확인

## 주요 설계 판단

### 확인할 수 없으면 거절

`policy_available`, 요청 action, direct actor, credential의 유효 시간 중 하나라도 확인할 수 없으면 거절합니다. 누락된 값을 정상 상태로 추정하지 않습니다.

### 입력 상태를 수정하지 않음

Authorization 함수는 전달받은 상태를 읽기만 합니다. 같은 상태로 판정을 다시 실행할 수 있도록 테스트에서 호출 전후 SHA-256을 비교합니다.

### 객체 경로를 segment 단위로 비교

문자열의 시작 부분만 비교하면 `job-81x`가 `job-81`의 하위 경로로 잘못 판정될 수 있습니다. 객체 경로와 credential prefix를 `/`로 나눈 뒤 segment가 정확히 일치하는지 확인합니다. 절대 경로, backslash, 빈 segment, `.`와 `..`도 허용하지 않습니다.

### 사람이 읽는 문장을 판정 기준으로 사용하지 않음

Detector는 변경될 수 있는 `reason` 문장 대신 `reason_code`를 사용합니다. 동일한 `event_id`가 여러 번 들어오면 한 건으로 처리합니다. 내용이 충돌하면 범위 초과 거절 event를 남겨, 입력 순서 때문에 alert가 사라지지 않도록 합니다.

### 서로 다른 요청을 합치지 않음

`correlation_id`가 다른 event는 별도 alert로 만듭니다. 각 alert에는 actor, effective actor, credential, `reason_code`와 원본 event ID가 포함됩니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
|---:|---|---|
| 0 | Package API boundary | `src/ledgerlab_policy/__init__.py` |
| 1 | Authorization decision event contract | `src/ledgerlab_policy/policy.py` |
| 2 | Shared fail-closed request context | `src/ledgerlab_policy/policy.py` |
| 3 | Report ownership authorization | `src/ledgerlab_policy/policy.py` |
| 4 | Worker credential lifecycle | `src/ledgerlab_policy/policy.py` |
| 5 | Job-scoped object authorization | `src/ledgerlab_policy/policy.py` |
| 6 | Correlated deny-event detection | `src/ledgerlab_policy/detection.py` |
| 6-1 | Duplicate-event suppression | `src/ledgerlab_policy/detection.py` |
| 6-2 | Correlation-preserving alert construction | `src/ledgerlab_policy/detection.py` |
| 7 | Fixture-backed policy verification | `tests/test_policy.py` |
| 7-1 | Detection behavior verification | `tests/test_detection.py` |

## 범위와 한계

- 합성 메모리 상태만 판정합니다. 실제 cloud IAM, 운영체제 격리, 네트워크 경로와 운영 telemetry는 검증하지 않습니다.
- `report.read`와 `object.read`만 지원합니다.
- `actor_id`와 `effective_actor_id`가 같은 요청만 허용합니다. 위임된 identity의 연쇄 검증은 포함하지 않습니다.
- 객체의 실제 존재 여부와 내용은 확인하지 않습니다. Credential에 기록된 정확한 prefix 안인지 판정합니다.
- `state["now"]`를 현재 시각으로 사용합니다. 외부 clock과 token signature는 확인하지 않습니다.
- Detector는 전달받은 event만 분석합니다. event가 없다는 사실만으로 행동이 없었다고 판단할 수 없습니다.
- Alert는 조사를 시작할 근거입니다. actor의 의도나 실제 침해를 확정하지 않습니다.
