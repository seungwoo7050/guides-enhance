# 사이버보안 학습 로드맵

이 로드맵은 사이버보안 전 분야를 빠짐없이 나열하지 않습니다. 개발자가 기존 시스템의 보안 주장을 읽고, 허가된 범위에서 확인하고, 수정과 탐지·복구까지 연결하는 데 필요한 최소 순서를 정합니다.

목표는 문서를 많이 읽는 것이 아니라 다음 작업을 반복할 수 있는 상태입니다.

```text
지켜야 할 상태를 적습니다.
→ 그 상태를 바꿀 수 있는 주체와 조건을 찾습니다.
→ 허가된 합성 입력으로 결과를 확인합니다.
→ 요구사항과 테스트로 고정합니다.
→ 원인을 수정하고 같은 실패가 다시 생기지 않는지 검사합니다.
→ event와 alert로 시도를 관찰합니다.
→ 사고가 발생하면 신뢰할 수 있는 상태를 다시 만듭니다.
```

## 전체 경로

```text
Part 1. 보안 상태와 근거
        ↓
Part 2. 위협과 평가 허가
        ↓
Part 3. 애플리케이션·identity 실패
        ↓
Exercise A. 접근 판정
        ↓
Part 4. 위험·요구사항·telemetry
        ↓
Exercise B. detector
        ↓
Part 5. 검사·수정·복구
        ↓
Exercise C. 전체 검증
        ↓
완료
```

## Part 1. 보안 상태와 근거

### 문서

1. [`01-security-state-and-evidence.md`](01-security-state-and-evidence.md)
2. [`02-assets-trust-boundaries-and-threat-models.md`](02-assets-trust-boundaries-and-threat-models.md)

### 확인할 내용

- “안전하다”는 표현을 주체·자원·행동·허용 상태로 바꾸는 방법
- 기밀성·무결성·가용성을 실제 기능과 상태에 적용하는 방법
- 사실, 가설과 결론의 차이
- 설정, 테스트, event와 정본 데이터가 각각 보장하는 범위
- 자산 이름보다 보호할 상태와 그 상태를 바꾸는 사건을 적는 방법
- actor의 현재 capability와 attack path에서 새로 얻는 capability의 구분
- network 위치와 별도로, 상대가 주장한 identity·resource 정보를 다시 확인해야 하는 지점

### 완료 기준

다음 형식으로 최소 다섯 개의 보안 주장을 작성할 수 있어야 합니다.

```text
[주체]가 [전제]에서 [행동]을 시도하면
시스템은 [허용 또는 거절 결과]를 내야 하며
[서로 다른 실패 원인을 가진 근거]로 결과를 확인합니다.
```

## Part 2. 평가 허가와 최소 검증

### 문서

3. [`03-scope-authorization-and-rules-of-engagement.md`](03-scope-authorization-and-rules-of-engagement.md)
4. [`04-risk-vulnerability-and-prioritization.md`](04-risk-vulnerability-and-prioritization.md)

### 확인할 내용

- 자산이 공개돼 있다는 사실과 검증 권한의 차이
- 승인한 자산·identity·시간·행동·요청량을 고정하는 방법
- 범위 이탈, 실제 정보 노출과 예상하지 못한 상태 변경이 생겼을 때 멈추는 조건
- 합성 account와 marker로 영향을 최소화하는 방법
- weakness, exposure, vulnerability, attack path와 incident의 차이
- `confirmed`, `false-positive`, `not-reproducible`, `unknown`을 구분하는 근거
- 기술적 severity와 조직의 처리 priority를 구분하는 이유

### 완료 기준

평가를 시작하기 전에 다음 항목을 빠짐없이 적을 수 있어야 합니다.

```text
승인자와 유효 기간
in-scope / out-of-scope
평가 identity
허용·금지 행동
요청·시간·데이터 한도
중단과 연락 조건
증거 보존·폐기
정리와 복구 확인
```

## Part 3. 실제 실패 형태

### 문서

5. [`06-application-boundary-failures.md`](06-application-boundary-failures.md)
6. [`07-system-identity-and-secret-boundaries.md`](07-system-identity-and-secret-boundaries.md)

### 확인할 내용

- authentication과 object authorization의 차이
- 입력이 query, command, template, path와 URL로 해석되는 지점
- 업무 상태를 검사한 뒤 실제 변경까지 원자적으로 처리해야 하는 경우
- service identity와 사용자를 대신하는 권한의 차이
- credential의 발급, 사용, 만료, 폐기와 교체
- job·tenant·resource 단위로 권한을 제한하는 방법
- container, internal network와 broad service token을 자동 신뢰하면 안 되는 이유

### Exercise A — 접근 판정

이 시점에 [`ledgerlab-policy`](../exercises/ledgerlab-policy/README.md)의 다음 구현을 확인합니다.

```text
Implementation 0     Package API boundary
Implementation 1     Authorization decision event contract
Implementation 2     Shared fail-closed request context
Implementation 3     Report ownership authorization
Implementation 4     Worker credential lifecycle
Implementation 5     Job-scoped object authorization
```

직접 확인할 사례:

- 소유자가 완료된 자신의 보고서를 읽음
- 다른 소유자·tenant의 보고서를 요청함
- 작업자가 현재 job 객체를 읽음
- 다른 job, `job-81x`, `..`, 만료·폐기 credential을 사용함
- 판정에 필요한 상태나 현재 시각이 없음

## Part 4. 요구사항과 관측 가능한 결과

### 문서

7. [`10-security-requirements-and-design-invariants.md`](10-security-requirements-and-design-invariants.md)
8. [`13-telemetry-detection-and-investigation.md`](13-telemetry-detection-and-investigation.md)

### 확인할 내용

- threat를 subject·resource·action·결과가 명확한 requirement로 바꾸는 방법
- prevention, detection과 recovery가 각각 담당하는 결과
- 정상 기능까지 확인해 `deny-all` 구현을 거르는 test oracle
- actor, effective actor, credential, resource, decision, reason과 correlation을 포함한 event
- event time과 ingest time의 차이
- 중복·지연·누락된 event가 분석 결과에 주는 영향
- alert에서 원본 event로 돌아갈 수 있게 근거 ID를 보존하는 방법

### Exercise B — detector

```text
Implementation 6     Correlated deny-event detection
Implementation 6-1   Duplicate-event suppression
Implementation 6-2   Correlation-preserving alert construction
```

직접 확인할 사례:

- 정상 접근과 단순 중복 event가 alert를 만들지 않음
- 같은 요청에서 발생한 cross-owner와 cross-job 거절이 하나의 alert가 됨
- `correlation_id`가 다른 요청은 별도 alert로 남음
- 같은 `event_id`의 내용이 충돌해도 거절 기록이 숨겨지지 않음

## Part 5. 검사, 수정과 복구

### 문서

9. [`11-security-testing-and-assurance.md`](11-security-testing-and-assurance.md)
10. [`12-remediation-hardening-and-regression.md`](12-remediation-hardening-and-regression.md)
11. [`14-incident-response-and-recovery.md`](14-incident-response-and-recovery.md)

### 확인할 내용

- unit, integration, end-to-end, 정적 분석과 수동 검토가 각각 확인하는 범위
- status code 하나가 충분한 판정 기준이 아닌 이유
- 정상·경계·대표 실패 사례와 known-bad 구현
- 증상 한 곳만 막는 수정과 공통 원인을 제거하는 수정의 차이
- 유사한 코드 경로, 기존 credential, 파생 데이터와 rollback을 함께 검토하는 방법
- finding, suspicious event와 incident의 차이
- containment, eradication과 recovery가 각각 완료해야 하는 상태
- source, builder, credential, configuration과 data의 신뢰를 다시 세우는 방법

### Exercise C — 전체 검증

```text
Implementation 7     Fixture-backed policy verification
Implementation 7-1   Detection behavior verification
```

프로젝트 루트에서 다음 명령을 실행합니다.

```sh
cd exercises/ledgerlab-policy
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 examples/demo.py
```

완료하려면 테스트가 통과하는 것에 더해 다음을 설명해야 합니다.

- 어떤 잘못된 구현을 각 경계 사례가 검출합니까?
- 판정 전후 입력 상태가 같은지 왜 확인합니까?
- `reason` 문장이 바뀌어도 detector가 동작해야 하는 이유는 무엇입니까?
- event가 누락됐다면 alert가 없다는 결과를 어떻게 해석해야 합니까?
- 실제 cloud IAM이나 production telemetry에 이 합성 결과를 그대로 일반화할 수 없는 이유는 무엇입니까?

## 선택 문서

필수 경로를 완료한 뒤 실제 문제에 맞춰 사용합니다.

| 문서 | 분류 | 사용할 때 |
|---|---|---|
| [`05-attack-surface-and-paths.md`](05-attack-surface-and-paths.md) | 보조 | 여러 서비스의 capability를 연결하고 공통 차단 지점을 찾을 때 |
| [`08-supply-chain-and-build-trust.md`](08-supply-chain-and-build-trust.md) | 심화 | dependency, CI, registry와 release artifact의 신뢰를 검토할 때 |
| [`09-vulnerability-validation-and-reporting.md`](09-vulnerability-validation-and-reporting.md) | 보조 | finding 보고서, 근거 독립성, retest와 공개 절차를 정리할 때 |
| [`15-security-review-and-release-decision.md`](15-security-review-and-release-decision.md) | 심화 | release 전 잔여 위험과 진행·중단 조건을 판단할 때 |
| [`90-standards-map.md`](90-standards-map.md) | 참고 | NIST, OWASP, CWE, ATT&CK, CVSS와 SLSA의 용도를 확인할 때 |

선택 문서는 필수 경로의 개념을 다른 업무에 적용하는 자료입니다. 이 문서들을 읽지 않았다는 이유만으로 필수 과정이 미완료가 되지는 않습니다.

## 최종 완료 기준

다음 결과를 모두 충족하면 이 저장소의 학습을 완료한 것으로 봅니다.

- 보안 주장을 주체·자원·행동·상태로 작성할 수 있습니다.
- 각 근거가 확인한 version·입력·시간과 보장하지 않는 범위를 말할 수 있습니다.
- 허가되지 않은 평가와 합성 환경의 최소 검증을 구분할 수 있습니다.
- object authorization과 job-scoped credential 검사를 코드로 설명할 수 있습니다.
- 정상 기능을 보존하면서 cross-owner·cross-job·유사 prefix·만료·폐기 사례를 거절할 수 있습니다.
- 판정 결과를 완전한 event로 남기고 요청별 alert로 묶을 수 있습니다.
- 수정 뒤 회귀 검사와 credential·data 정리를 함께 계획할 수 있습니다.
- 사고가 발생했을 때 사실·가설·결정·조치를 분리하고 신뢰할 수 있는 복구 기준을 제시할 수 있습니다.

외부 프로젝트는 필수 완료 조건이 아닙니다. 이후 공급망, 보안 검토, 취약점 보고처럼 좁은 업무가 필요해질 때 선택 문서를 다시 읽으면 됩니다.
