# 보안 요구사항과 설계 불변식

위협 모델은 어떤 실패가 가능한지 설명합니다. 보안 요구사항은 시스템이 그 실패를 어떤 입력에서 거절하고, 무엇을 기록하며, 문제가 생긴 뒤 어떤 상태를 다시 만들어야 하는지 검사 가능한 문장으로 바꿉니다.

## 1. 검사 가능한 요구사항

다음 문장은 너무 넓습니다.

> API는 안전해야 합니다.

다음처럼 바꿉니다.

```text
REQ-AUTHZ-003
모든 report read는 authenticated subject, requested action,
report owner와 tenant를 판정 입력에 포함해야 합니다.
다른 owner 또는 tenant의 report는 내용을 반환하지 않고 거절하며,
subject·resource·decision·reason을 audit event에 기록해야 합니다.
```

좋은 요구사항에는 다음 정보가 있습니다.

- subject
- resource 또는 asset
- action
- 필요한 context와 사전 조건
- 허용·거절·격리 결과
- 실패할 때의 동작
- 확인할 test와 runtime evidence

## 2. Threat를 requirement로 바꾸기

```text
Threat
일반 사용자 session을 가진 actor가 다른 owner의 report ID를 사용해
report 내용을 읽을 수 있음

Invariant
모든 report read는 subject와 report owner를 비교함

Requirement
모든 read path가 같은 authorization 함수를 호출하고 foreign owner를 거절함

Test
owner·other owner·other tenant·revoked subject 사례

Detection
cross-owner deny event와 예상하지 못한 allow event

Recovery
영향 session 폐기, 접근 범위 조사, 잘못 생성된 결과물 정리
```

하나의 threat가 여러 요구사항을 만들 수 있고, 하나의 요구사항이 여러 threat를 줄일 수도 있습니다.

Threat 이름 하나만으로 적용 범위를 완료했다고 표시하지 않습니다. 같은 report read라도 API, export worker와 legacy batch가 서로 다른 코드를 사용할 수 있습니다. 각 경로에서 어느 함수가 금지된 상태를 거절하는지 확인합니다.

| 실행 경로 | 예방 | 탐지 | 복구 | 현재 근거 |
|---|---|---|---|---|
| direct report read | owner 판정 | cross-owner deny·unexpected allow | session 폐기·접근 범위 조사 | API 통합 테스트 |
| export worker | job-scoped credential | 다른 prefix 접근 event | credential 교체·잘못된 export 삭제 | worker fixture |
| legacy batch | 적용 여부 미확인 | legacy identity 사용 관찰 | 영향 output 검토 | owner와 확인 기한 필요 |

`N/A`는 구현하지 않았다는 뜻이 아닙니다. 해당 경로에서 요구사항의 전제가 성립할 수 없음을 source, configuration 또는 실행 결과로 확인했을 때만 사용합니다. 확인하지 않은 상태는 `unknown` 또는 `not-run`입니다.

## 3. 예방, 탐지와 복구 요구사항

세 종류는 서로 다른 결과를 만듭니다.

### 예방

- 허가되지 않은 상태 변경 거절
- identity·tenant·job·resource scope 제한
- untrusted data와 interpreter 분리
- artifact와 credential 검증
- 요청 수와 자원 사용량 제한

### 탐지

- 중요한 allow·deny 판정 기록
- role·credential·configuration·release 변경 기록
- 정상 순서에서 벗어난 상태 관찰
- event 손실·지연·parser 오류 확인

### 복구

- credential과 session 폐기·교체
- 신뢰할 수 있는 source와 builder로 artifact 재생성
- data restore와 무결성 확인
- cache·index·derived output 무효화 또는 재생성
- 영향 대상 연락과 재검토

Monitoring은 공격자의 capability를 제거하지 않습니다. Alert를 만들었다는 사실을 containment 또는 recovery 완료로 세면 안 됩니다.

## 4. 실패할 때의 기본 동작

다음 상황에서 어떤 결과를 낼지 미리 정합니다.

- authorization 함수가 응답하지 않으면 요청을 허용합니까?
- audit sink에 기록하지 못하면 업무 처리를 계속합니까?
- artifact signature를 확인할 수 없으면 배포합니까?
- dependency 정보가 없으면 release를 멈춥니까?
- detector가 실행되지 않으면 누가 알 수 있습니까?

모든 경우에 무조건 fail closed가 정답은 아닙니다. 예를 들어 audit 저장소 장애 때 모든 의료 기능을 중단하면 다른 위험이 생길 수 있습니다. 선택한 동작, 영향과 보완 근거를 명시합니다.

## 5. 최소 권한을 차원별로 적기

“최소 권한을 적용합니다”를 다음처럼 구체화합니다.

```text
worker credential은 audience=object-store이며,
현재 job의 tenant와 report prefix에 대한 read·write만 허용합니다.
10분 뒤 만료되며 admin API와 backup storage에는 사용할 수 없습니다.
```

필수 검사:

- intended prefix 허용
- 다른 tenant·job·prefix 거절
- unrelated API 거절
- exact expiry와 만료 뒤 거절
- wrong audience 거절
- 폐기 뒤 거절

## 6. 안전한 기본값

사용자가 별도 hardening 문서를 읽어야만 안전해지는 제품보다 기본 설정에서 위험을 줄입니다.

- admin endpoint는 기본적으로 public에 노출하지 않습니다.
- debug와 상세 오류는 production에서 기본 비활성화합니다.
- 새 tenant와 object는 기본 private로 둡니다.
- release에는 artifact 검증을 기본 gate로 둡니다.
- broad permission은 명시적인 예외 승인을 요구합니다.
- 중요한 allow·deny와 변경은 기본적으로 event를 남깁니다.

안전한 기본값 때문에 정상 업무가 불가능하면 사용자가 우회할 수 있습니다. 필요한 정상 동작을 함께 검사합니다.

## 7. 담당자를 구체적으로 적기

| 요구사항 | 실제로 수행할 component 또는 담당자 |
|---|---|
| report owner 판정 | application authorization 함수와 해당 팀 |
| worker credential scope | credential issuer와 identity 운영팀 |
| storage prefix 판정 | object proxy 또는 storage policy |
| release artifact 검증 | build·release verifier |
| alert 생성 | detection service와 security operations |
| restore 무결성 확인 | data owner와 operations |

업무 영향 결정, 상태 정본 관리, 요청 판정 구현, event 보관과 공식 위험 수용은 서로 다른 권한일 수 있습니다. `owner` 한 칸에 모두 넣지 않습니다.

## 8. ID와 추적

```text
THR-REPORT-02
→ REQ-AUTHZ-003
→ TEST-AUTHZ-011..017
→ EVENT-POLICY-001
→ DET-AUTHZ-004
→ RUNBOOK-ACCESS-002
```

목적은 문서 번호를 늘리는 것이 아닙니다. Requirement가 바뀌었을 때 다시 실행할 test, 필요한 event와 대응 절차를 찾기 위한 것입니다.

## 9. 금지 요구사항

하지 말아야 할 동작도 검사 가능하게 적습니다.

- user input을 shell command 문자열에 붙이지 않습니다.
- production release를 mutable tag만으로 식별하지 않습니다.
- application process가 container runtime socket을 열지 못하게 합니다.
- audit event에 raw credential과 session token을 기록하지 않습니다.
- production write와 backup delete를 같은 identity에 주지 않습니다.

## 10. 예외와 남은 위험

요구사항을 바로 충족하지 못한다면 다음을 기록합니다.

```text
미충족 requirement
현재 노출 범위
즉시 수정하지 못하는 이유
실제로 적용한 보완 통제
업무·위험 owner와 공식 승인자
시작·만료 시각
monitoring과 response 시간
수정 milestone
다시 검토할 조건
```

예외가 영구적인 약한 기본값이 되지 않도록 만료와 재검토 조건을 둡니다.

## 11. 다시 검토할 때

- 자산 분류와 threat model 변경
- 새 role·tenant·service·provider 추가
- authorization·identity 방식 변경
- dependency·build·deployment 방식 변경
- incident와 새로운 공격 방식
- 담당자 변경
- test·event가 더 이상 현재 version을 설명하지 못함

## 완료 질문

- threat와 requirement는 어떻게 다릅니까?
- fail closed가 모든 상황의 정답은 아닌 이유는 무엇입니까?
- 최소 권한을 검사 가능하게 적으려면 어떤 차원이 필요합니까?
- monitoring과 containment를 구분해야 하는 이유는 무엇입니까?
- `N/A`, `unknown`과 `not-run`을 구분해야 하는 이유는 무엇입니까?
