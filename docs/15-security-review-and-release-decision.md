# 보안 검토와 release 결정

보안 검토는 취약점이 0개라고 선언하는 절차가 아닙니다. 현재 release가 어떤 자산과 변경을 포함하는지, 어떤 근거가 현재 version을 설명하는지, 남은 위험을 누가 어떤 조건으로 승인했는지 확인하는 과정입니다.

이 문서는 release 전 보안 검토를 맡을 때 사용하는 심화 자료입니다.

## 1. 검토 자료

최소 자료:

```text
release 범위와 exact artifact digest
system context와 데이터 분류
변경된 asset·identity·data flow
threat model
security requirement
open·closed finding
보안 test와 known-bad 결과
credential·network·storage permission
SBOM·provenance·dependency 상태
telemetry·alert·incident 절차
backup·restore·rollback 근거
예외와 남은 위험
```

문서 수보다 같은 release ID와 requirement로 서로 연결되는지가 중요합니다.

## 2. 변경된 부분 중심으로 보기

전체 시스템을 매번 처음부터 다시 검토하지는 않습니다. 다음 변경을 찾습니다.

- 새 component, endpoint, identity와 data flow
- permission, resource scope와 기본값 변경
- dependency, build, registry와 deployment 변경
- authorization 제거, fallback과 예외 추가
- 민감한 데이터와 retention 변경
- logging, backup과 recovery 영향
- 이전 finding과 attack path가 다시 열리는 조건

## 3. 근거의 현재성

각 근거에 다음을 기록합니다.

```text
source revision·artifact digest
실행 환경
실행 시각
검사 담당자
확인한 범위
알려진 한계
만료 또는 재실행 조건
```

오래된 penetration test나 다른 configuration의 scan을 현재 release 근거로 그대로 사용하지 않습니다.

## 4. Open finding 검토

각 finding에서 다음을 확인합니다.

- `validation_status`
- `treatment`
- `lifecycle_status`
- `duplicate_of`
- 현재 노출과 attack path 위치
- severity와 조직 priority
- 실제 적용된 보완 통제와 runtime 근거
- owner와 목표 기한
- release를 막는 조건
- monitoring과 incident 준비

`accepted risk`는 검증 상태가 아닙니다. `accept`는 `confirmed` finding에 대해 공식 권한자가 scope, 기한, 보완 통제, monitoring과 재검토 조건을 승인한 처리 결정입니다.

개별적으로 낮은 finding 여러 개가 하나의 높은 영향 경로를 만드는지도 봅니다.

## 5. 진행·조건부 진행·중단

### 진행

필수 requirement와 release gate가 충족되고, 남은 위험이 정한 범위 안에 있습니다.

### 조건부 진행

명확한 제한, owner, 만료와 확인 방법 아래 release합니다.

```text
admin endpoint를 public에 노출하지 않음
JIT identity로만 접근
7일 안에 공통 원인 수정 배포
특정 alert와 daily review 유지
공식 risk acceptance authority 승인
```

Monitoring만 추가해 취약 상태를 정상으로 취급하면 안 됩니다. 실제 attack path를 줄이는 조치, alert 뒤 response 시간, rollback·incident 조건과 만료 뒤 자동 재승인 금지가 필요합니다.

### 중단

다음과 같은 경우 release를 중단할 수 있습니다.

- 중요 자산에서 object authorization 실패를 제어하지 못함
- required artifact digest·signature·provenance를 확인할 수 없음
- 유효한 credential 노출과 폐기가 불가능함
- destructive migration에 rollback이 없음
- 필요한 audit·incident 근거가 없음
- 검사한 version과 release candidate가 다름

Signature가 유효하다는 이유만으로 source, builder와 review까지 안전하다고 결론 내리지 않습니다.

## 6. 역할과 권한

| 역할 | 맡는 일 | 자동으로 가지지 않는 권한 |
|---|---|---|
| security reviewer | scope·threat·test·한계를 검토하고 gate 충족 여부를 보고함 | 업무 위험 공식 수용 |
| risk owner | asset·service 영향과 처리 계획을 관리함 | 조직 절차 밖의 공식 승인 |
| risk acceptance authority | 정한 범위·기간의 남은 위험을 승인함 | 기술적 사실 변경 |
| release authority | 근거와 승인 상태를 바탕으로 배포 여부를 결정함 | 미승인 위험 임의 수용 |

한 사람이 여러 역할을 맡더라도 어떤 권한으로 결정했는지 기록합니다.

## 7. 예외 관리

예외에는 다음을 포함합니다.

```text
requirement·finding ID
적용 범위
허용 이유
보완 통제
owner와 승인자
시작·만료 시각
monitoring
수정 milestone
다시 검토할 조건
```

만료 뒤 자동으로 승인 상태를 유지하지 않습니다.

## 8. Release 뒤 확인

- 실제 runtime digest와 configuration
- 정상 기능과 authorization deny
- 새 event와 alert 수집 상태
- 이전 credential·artifact 거절
- migration과 data integrity
- external exposure
- 오류와 성능 회귀

Production 확인은 승인된 비파괴 요청으로 제한합니다. Synthetic identity·tenant·data와 전용 correlation ID를 사용하고 요청 수·시간·변경 범위와 정리 방법을 정합니다. Staging 결과나 실행 계획을 production 실행 근거라고 부르지 않습니다.

## 9. 다시 검토할 조건

- emergency patch와 rollback
- identity·permission·network 변경
- 새 exploit·advisory
- dependency·base image update
- 데이터 분류와 retention 변경
- incident·near miss
- 근거·예외 만료
- logging·backup·recovery 저하

## 10. 최종 결정 기록

```text
Decision
Release identifier
Scope
Evidence summary
Open risks
Required conditions
Risk owner and approver
Monitoring period
Rollback·incident trigger
Next review date
```

“보안 승인”이라는 한 줄 대신 조건과 한계를 남깁니다.

## 완료 질문

- Finding이 0개라는 사실이 안전을 증명하지 못하는 이유는 무엇입니까?
- 다른 version·환경의 근거를 현재 release에 사용하면 어떤 문제가 생깁니까?
- 조건부 진행에 필요한 제한과 만료는 무엇입니까?
- Security reviewer와 risk acceptance authority의 권한은 어떻게 다릅니까?
- Release 뒤 실제 runtime 확인이 필요한 이유는 무엇입니까?
