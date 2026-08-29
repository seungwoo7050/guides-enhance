# 수정, 영향 제한과 회귀 검사

취약점 수정은 한 요청을 막는 patch에서 끝나지 않습니다. Actor가 이미 얻은 capability, 노출됐을 수 있는 credential과 data, 같은 원인을 가진 다른 실행 경로, 배포와 rollback까지 함께 다뤄야 합니다.

## 1. 수정 작업을 네 종류로 나누기

### 즉시 영향 제한

현재 악용과 확산을 줄이는 가역적인 조치입니다.

- 위험 endpoint 일시 제한
- token·session 폐기
- network·resource scope 축소
- feature flag와 traffic 차단

Monitoring 강화는 조치가 적용됐는지 관찰하지만 actor의 capability를 제거하지 않습니다. 실제 제한 작업과 detection 작업을 같은 완료 항목으로 세지 않습니다.

### 공통 원인 수정

약점을 만든 설계·구현·운영 방식을 바꿉니다.

- 모든 report read가 같은 authorization 함수를 호출함
- 문자열 조합 대신 parameter API 사용
- job-scoped credential 발급
- immutable artifact digest 검증
- 정본에서 원자적인 상태 변경

### 영향 범위 축소

같은 bug가 남더라도 영향을 줄이는 조치입니다.

- least privilege
- egress 제한
- read-only filesystem
- rate·resource limit
- 별도 audit·backup identity

### 재발 방지

같은 종류의 문제를 개발 과정에서 줄입니다.

- 안전한 helper와 기본 API
- linter·static rule
- test template
- review 항목
- coding standard
- 안전한 기본 설정

## 2. 증상 한 곳만 막지 않기

```text
증상 수정
/download route에 owner 조건문 한 줄 추가

공통 원인 수정
report를 읽는 API·export·worker가 모두 같은 authorization 함수를 호출하고,
subject·resource·action·tenant를 필수 입력으로 받도록 변경
```

공통 함수를 도입할 때 migration과 compatibility 위험도 확인합니다.

## 3. 최소 수정의 의미

최소 수정은 diff가 가장 작은 변경이 아닙니다. 정상 기능을 보존하면서 깨진 불변식을 모든 적용 경로에서 복원하는 데 필요한 가장 작은 change set입니다.

| 실행 경로 | 수정 전 결과 | 필요한 변경 | 수정 뒤 확인 |
|---|---|---|---|
| owner API read | 정상 허용 | owner context 유지 | allow + event |
| foreign API read | foreign data 노출 | 중앙 authorization 호출 | 내용 비노출 + deny event |
| export worker | 다른 owner 가능 | job·tenant scope 추가 | 현재 job 결과만 생성 |
| legacy cache | 적용 여부 미확인 | owner와 기한을 두고 조사 | 확인 전 close 금지 |

Route 하나만 막고 export·worker·cache가 같은 상태를 허용한다면 작은 diff여도 최소 수정이 아닙니다.

## 4. 유사한 실행 경로 찾기

Finding의 source, sink, authorization 함수와 identity 사용 형태를 기준으로 찾습니다.

- 같은 helper를 사용하지 않는 route
- batch·admin·export·mobile·legacy API
- background job과 retry
- cache·search index·report generator
- 같은 dependency·base image를 쓰는 artifact
- 같은 secret·service account를 쓰는 workload

같은 원인인지, 별도 finding과 owner가 필요한지 결정합니다.

## 5. Credential과 session 정리

Credential 노출 가능성이 있으면 patch만으로 충분하지 않습니다.

- 현재 유효한 credential과 session 목록
- 발급·사용 event
- 폐기·교체 순서
- 각 consumer의 새 credential 전환
- cache·agent·client에 남은 copy
- 이전 credential 사용 alert
- signing key라면 기존 artifact와 release 신뢰 영향

지금 invalid하다는 사실이 과거 유효 기간의 사용을 설명하지는 않습니다.

## 6. Data와 파생 상태

잘못된 write가 가능했다면 정본뿐 아니라 파생 상태를 확인합니다.

```text
primary record
→ cache
→ search index
→ report
→ event stream
→ analytics
→ backup
```

정본만 고쳐도 cache와 report가 오염된 채 남을 수 있습니다. Rebuild, replay, invalidate와 reconciliation 범위를 정합니다.

## 7. 배포와 rollback

보안 patch에도 일반 변경과 같은 운영 정보가 필요합니다.

- source revision과 exact artifact digest
- migration·configuration 변경
- 배포 전 검사
- 단계적 배포
- 정상 기능과 보안 회귀 검사
- runtime event
- rollback 조건
- rollback이 취약 version을 다시 활성화하는 위험

긴급 patch라도 검증·기록·review를 모두 생략하지 않습니다. 줄인 절차와 나중에 보완할 근거를 명시합니다.

Signature와 provenance가 유효해도 손상된 source·builder가 만든 artifact일 수 있습니다. Rollback artifact도 source, dependency, builder와 credential 신뢰를 다시 확인합니다.

## 8. 회귀 검사

최소 검사표:

- 원래 재현이 더 이상 성공하지 않음
- 정상 사용은 계속 성공함
- 다른 role·tenant·resource는 거절됨
- exact expiry, retry와 concurrent 요청에서도 유지됨
- background·export·cache도 같은 판정을 사용함
- audit event와 alert가 기대한 field를 가짐
- authorization dependency가 없을 때 정한 fallback이 동작함
- 이전 credential·artifact가 거절됨

각 경로를 `applicable-pass`, `applicable-fail`, `not-run`, `unknown`, 근거가 있는 `N/A`로 기록합니다.

## 9. Retest 독립성

가능하면 원래 구현자와 다른 사람이 finding과 requirement를 기준으로 다시 검사합니다. 같은 assumption을 반복할 가능성을 줄이기 위해서입니다.

Retest 자료:

```text
original finding
수정 요약
바뀐 source·configuration
새 requirement·test
deployed version·digest
credential·data 정리 결과
남은 예외
```

## 10. 임시 보완 통제

공통 원인 수정이 늦어질 때 임시 통제를 사용할 수 있습니다.

좋은 보완 통제는 다음 조건을 만족합니다.

- 실제 attack-path edge를 끊습니다.
- 적용 범위와 우회 조건이 명확합니다.
- runtime에서 적용됐음을 확인할 수 있습니다.
- owner와 만료일이 있습니다.
- 영구 수정 대신이 아님을 기록합니다.

Public reachability 제한은 외부 actor 경로를 줄일 수 있지만 내부 actor와 탈취한 service identity에는 효과가 없을 수 있습니다. Alert만 추가하는 조치는 첫 영향을 막지 못합니다.

## 11. 수정 신뢰도 확인

- 원인을 상태 변화로 설명할 수 있습니까?
- 같은 종류의 실행 경로를 찾았습니까?
- Known-bad 구현을 test가 거부합니까?
- 실제 배포된 digest에서 확인했습니까?
- credential·data·artifact 정리를 완료했습니까?
- detector와 incident 검토가 필요합니까?
- rollback이 취약 상태를 복원하지 않습니까?
- 남은 위험의 owner와 만료가 있습니까?

## 12. Finding 종료까지 연결하기

```text
owner 지정
→ 목표 시각
→ 수정과 review
→ 보안 회귀 검사
→ release artifact
→ runtime 확인
→ credential·data 정리
→ retest
→ close 또는 reopen
```

SLA 숫자만으로 품질을 판단하지 않습니다. 현재 노출, 영향, attack path와 수정 근거가 중요합니다.

## 완료 질문

- 원래 요청을 막는 것과 공통 원인을 수정하는 것은 어떻게 다릅니까?
- Credential 노출 가능성이 있으면 patch 외에 무엇을 해야 합니까?
- 파생 상태를 별도로 조사해야 하는 이유는 무엇입니까?
- Rollback이 취약 상태를 다시 만들 수 있는 경우는 언제입니까?
- Monitoring을 containment 완료로 세면 어떤 위험이 남습니까?
