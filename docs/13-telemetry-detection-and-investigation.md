# 보안 telemetry, 탐지와 조사

탐지는 공격 이름을 log에서 찾는 일이 아닙니다. 보호할 상태가 바뀌거나 판정 함수가 예상과 다른 결과를 냈을 때, 조사자가 actor·resource·시간과 결과를 다시 확인할 수 있도록 event를 설계하는 일입니다.

## 1. Security telemetry의 목적

- 중요한 allow·deny 판정을 다시 확인함
- identity·permission·configuration 변경을 추적함
- attack path의 시도와 성공을 구분함
- 영향받은 actor·asset·time 범위를 찾음
- containment와 recovery가 실제로 적용됐는지 확인함
- log 수집 지연·누락·parser 오류를 알아챔

Debug log를 많이 저장하는 것이 목적은 아닙니다.

## 2. Event schema

중요한 authorization event에는 다음 정보가 필요합니다.

```text
event_id
event_time과 timezone
ingest_time
producer service·instance·version
request·trace·job·correlation ID
actor와 effective actor
credential ID와 policy version
action
resource type·ID·tenant
allow·deny decision과 reason_code
처리 결과
release digest
```

Request body와 raw token을 그대로 기록하지 않습니다. 조사에 필요한 identity와 판정 결과를 구조화합니다.

### 서로 다른 시각

- `event_time`: producer가 행동이나 판정을 관찰한 시각입니다.
- `ingest_time`: 신뢰하는 collector가 event를 받은 시각입니다.
- `discovery_time`: analytic이나 조사자가 이상 상태를 처음 발견한 시각입니다.

세 시각을 서로 바꿔 쓸 수 없습니다. `ingest_time - event_time`에는 수집 지연과 clock 차이가 함께 포함될 수 있습니다. UTC offset, clock source와 timestamp precision을 보존하고, 순서가 바뀐 event를 무조건 버리지 않습니다.

### 개인정보 최소 수집

각 field마다 조사 목적, 접근 가능한 역할, 보존 기간과 삭제 규칙을 정합니다. Raw token, 불필요한 request body와 개인 정보는 수집 전에 제거합니다. Identifier를 hash했다고 자동으로 익명 정보가 되는 것은 아닙니다.

## 3. Allow와 deny event

거절만 기록하면 성공한 접근과 정상 사용을 비교하기 어렵습니다. 모든 read를 상세히 저장하면 비용과 개인정보 문제가 생깁니다.

위험에 따라 선택합니다.

- admin·privileged action은 allow·deny 모두 기록
- 민감한 export·download는 allow 기록
- 반복되는 낮은 위험 read는 sampling이나 집계 고려
- permission·credential·release 변경은 기록
- log 설정 변경과 삭제 시도는 별도 중요 event로 기록

## 4. Identity chain

여러 service를 거치는 요청에서는 다음을 구분합니다.

```text
human 또는 user actor
upstream service
현재 workload identity
delegated subject
token issuer·audience·scope
```

모든 행동을 service account 하나로 기록하면 원래 사용자와 resource context를 잃습니다.

## 5. Detection hypothesis

공격 이름보다 관찰 가능한 상태 변화로 작성합니다.

```text
Threat
일반 user session이 여러 owner의 report ID를 탐색할 수 있음

Hypothesis
짧은 시간에 한 actor가 여러 owner의 report에서 반복 deny를 만들거나,
예상하지 않은 tenant의 report read가 allow됨

필요한 data
actor, report owner, tenant, decision, reason_code, correlation_id

Analytic
서로 다른 owner에 대한 deny 증가 + cross-owner allow

Triage
정상 batch·support 작업, policy version과 release 변경 확인
```

## 6. Event sequence와 graph

단일 event는 정상처럼 보여도 여러 event를 연결하면 문제가 드러날 수 있습니다.

```text
새 session
→ 여러 resource 탐색
→ 반복된 deny
→ service credential 발급
→ 다른 storage prefix read
→ audit 설정 변경
```

Request, trace, job, actor, credential와 resource ID로 연결합니다. Clock 차이와 누락 event 가능성을 남깁니다.

## 7. ATT&CK 사용

ATT&CK은 관찰 가능한 adversary behavior를 분류하는 vocabulary로 사용할 수 있습니다.

```text
technique
→ detection strategy
→ 환경별 analytic
→ 필요한 data component
```

Technique ID를 붙였다는 사실만으로 coverage가 생기지는 않습니다. 자신의 시스템에서 해당 행동이 가능한지, 필요한 event가 실제로 수집되는지, known-positive와 known-negative에서 analytic이 동작하는지 확인해야 합니다. 사용한 ATT&CK snapshot과 object version을 기록합니다.

## 8. Alert 품질

확인할 항목:

- precision과 label 기준
- recall을 계산할 수 있는 모집단이 있는지
- known-scenario detection rate
- detection latency
- event freshness와 completeness
- duplicate와 alert storm 처리
- owner와 on-call 전달
- triage에 필요한 정보
- detector와 수집 시스템 자체의 health

운영에서 놓친 공격 전체를 알 수 없다면 recall을 정확히 측정했다고 말할 수 없습니다. Known-positive fixture 통과율은 회귀 근거이며 실제 운영 recall과 다릅니다.

## 9. False positive와 false negative

### False positive 원인

- 정상 batch·support 작업
- shared account
- clock·identity mapping 오류
- migration과 release 변경
- 현재 사용량에 맞지 않는 threshold

### False negative 원인

- 필요한 event field 누락
- allow 판정 미수집
- actor가 다른 identity나 낮은 속도를 사용함
- 수집 지연·drop·parser 오류
- analytic이 한 실행 경로만 가정함
- privileged actor를 무조건 제외함

예외를 늘리기 전에 event schema와 identity 기록을 먼저 확인합니다.

## 10. Event 무결성과 수집 가능성

- application이 local log를 지울 수 있습니까?
- audit sink가 별도 identity와 storage를 사용합니까?
- event loss, backlog와 parser failure를 관찰합니까?
- source sequence와 clock 상태가 있습니까?
- retention이 incident 발견 지연보다 충분합니까?
- 접근·삭제 권한과 개인정보 보존 기준이 있습니까?

공격자가 log를 지우지 않아도 수집 장애로 근거가 사라질 수 있습니다.

## 11. Detection-as-code

Analytic과 검증 자료를 함께 관리합니다.

```text
rule ID
연결된 threat·requirement
필수 event field
query 또는 logic
threshold와 시간 구간
known benign 사례
known-positive·negative fixture
owner
rollout·rollback
마지막 검증 version과 시각
```

## 12. Triage 자료

Alert는 조사자에게 다음 정보를 제공해야 합니다.

- 왜 발생했습니까?
- 어떤 threat와 asset에 연결됩니까?
- actor, resource와 시간 범위는 무엇입니까?
- 원본 event는 어디에 있습니까?
- 즉시 중단할 조건이 있습니까?
- 정상 작업인지 확인할 owner는 누구입니까?
- 실제 제한 조치가 필요하면 어떤 절차를 사용합니까?

## 13. `ledgerlab-policy`에서 확인할 내용

`detect()`는 다음 성질을 검사합니다.

- 사람이 읽는 `reason`이 아니라 `reason_code`로 범위 초과 거절을 고릅니다.
- 동일 `event_id`의 단순 중복을 한 건으로 처리합니다.
- 중복 event의 내용이 충돌하면 범위 초과 거절 기록을 남깁니다.
- 같은 `correlation_id`의 event만 하나의 alert로 묶습니다.
- alert에 원본 `evidence_event_ids`를 보존합니다.

이 결과는 전달받은 event만 설명합니다. 누락된 event의 존재 여부와 실제 침해를 확정하지 않습니다.

## 완료 질문

- Debug log를 많이 남기는 것과 security telemetry는 어떻게 다릅니까?
- Service identity만 기록하면 어떤 정보가 사라집니까?
- Allow event가 필요한 경우는 언제입니까?
- Known-positive 통과율을 실제 운영 recall이라고 부를 수 없는 이유는 무엇입니까?
- Event time, ingest time과 discovery time을 분리해야 하는 이유는 무엇입니까?
