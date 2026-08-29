# Cloud security, observability와 incident

클라우드 보안은 firewall 규칙 몇 개와 `encryption enabled` 표시로 끝나지 않습니다. Account, control plane, workload identity, managed resource, tenant data와 audit 자료가 서로 다른 권한과 수명을 가지므로 누가 무엇을 바꿀 수 있고 실제 영향이 어디까지였는지를 복원할 수 있어야 합니다.

## 1. 공급자와 사용자의 보안 작업을 나눕니다

공급자는 물리 시설과 managed 기능 일부를 보호합니다. 사용자는 최소한 다음을 직접 관리합니다.

- organization, account와 project 구성
- 사람과 workload identity
- resource policy
- network 공개 범위
- application authorization
- data 분류
- key와 secret 사용
- logging과 alert 설정
- backup과 restore 확인
- 설정 변경 추적
- tenant isolation
- incident 대응

공급자가 안전한 서비스를 제공한다는 사실과 사용자가 안전하게 설정했다는 사실은 다릅니다.

## 2. Account와 project를 사고 범위로 사용합니다

Account, subscription과 project는 billing 단위이면서 policy와 관리자 권한이 적용되는 범위입니다.

분리 기준:

- production과 non-production
- 민감 데이터와 일반 데이터
- 팀별 담당
- 특정 고객 전용 환경
- security tooling
- log archive
- backup vault
- 실험 환경

모든 production을 한 account에 넣으면 하나의 잘못된 policy가 전체에 영향을 줄 수 있습니다. 반대로 지나치게 나누면 monitoring과 대응이 복잡해집니다.

## 3. Identity를 작업에 맞게 제한합니다

- 사람은 개인 계정과 MFA를 사용합니다.
- Privileged 작업은 필요할 때만 짧은 session으로 승격합니다.
- Workload는 장기 static key보다 runtime credential을 사용합니다.
- CI/CD는 repository, artifact와 environment 범위를 제한합니다.
- Support 접근에는 tenant, 사유, 만료 시각과 audit가 필요합니다.
- Break-glass 사용은 즉시 alert하고 사용 뒤 credential을 교체합니다.

Role 이름만 보지 말고 실제 `action`, `resource`, `condition`을 확인합니다.

## 4. 공개 경로를 모두 확인합니다

Public IP가 없다고 private한 것은 아닙니다.

- public endpoint
- peering과 transit network
- private endpoint
- VPN
- service-to-service network
- identity 기반 접근
- pre-signed URL
- support channel
- backup copy
- logging export

Network와 identity를 함께 검토합니다. Broad identity는 private network 안에서도 위험하고, 강한 identity가 public exploit을 없애 주지도 않습니다.

## 5. Key와 secret 수명

Cloud key service를 사용해도 다음 작업은 사용자에게 남습니다.

- key policy
- encrypt/decrypt principal
- region과 replication
- rotation
- disable과 delete delay
- backup dependency
- 사용 audit
- key loss 복구 방법

Data보다 key를 먼저 삭제하면 backup과 archive를 영구히 읽지 못할 수 있습니다. Data 보존 기간과 key 수명을 함께 정합니다.

Secret은 source, image와 log에 넣지 않습니다. Runtime identity로 읽고, version과 폐기 상태를 기록하며, rotation 중 이전과 새 credential을 언제 허용하는지 정합니다.

## 6. 배포 artifact를 추적합니다

Cloud workload는 다음 artifact를 신뢰합니다.

- base image
- package
- container image
- function bundle
- IaC module
- CI action
- provider extension
- policy template

확인할 항목:

- source와 build 위치
- 변경할 수 없는 artifact ID
- signature와 provenance
- dependency version
- scanner가 확인한 범위
- 누가 production에 배포할 수 있는지
- 되돌릴 artifact가 남아 있는지

## 7. 관측 자료를 네 종류로 나눕니다

### Control plane

- resource create, update와 delete
- policy와 identity 변경
- logging 비활성화
- key operation
- network 변경
- quota 변경

### Resource 상태

- instance health
- database replica와 connection
- queue depth
- function concurrency와 throttle
- storage request

### Application 결과

- request와 trace
- 업무 error
- tenant action
- entitlement 판정
- 외부에 반영된 결과

### 비용과 사용량

- 사용량
- 일별 비용
- 이상 증가
- owner가 없는 resource
- commitment 사용률

`request_id`, `resource_id`, `deployment_version`과 `tenant_id`로 자료를 연결합니다.

## 8. Log에 남길 값

Secret, token과 민감한 payload를 기록하지 않습니다. 그렇다고 조사에 필요한 identity와 resource ID까지 없애면 안 됩니다.

```text
time
account_or_project
region
resource_id
action
actor_or_workload_identity
tenant_id_if_applicable
request_id
change_id
deployment_version
result
reason_code
source_context
```

Log storage는 workload의 삭제 권한과 분리하고, retention과 외부 export 방법을 정합니다.

## 9. Alert는 원인을 가정해야 합니다

`error > 0`보다 다음처럼 확인할 사건을 구체적으로 적습니다.

- production에서 사람이 직접 admin role을 사용했습니다.
- logging이나 backup policy가 꺼졌습니다.
- public access가 새로 허용됐습니다.
- key policy에 broad principal이 추가됐습니다.
- function concurrency가 평소보다 급증했습니다.
- 한 tenant의 대규모 export가 시작됐습니다.
- owner 없는 resource가 급증했습니다.
- break-glass 계정이 사용됐습니다.
- 사용하지 않던 region에 resource가 생겼습니다.

Alert마다 담당자, 심각도, 확인할 query와 첫 대응을 정합니다.

## 10. Incident 범위를 나눕니다

- identity 범위
- account 또는 project 범위
- resource 범위
- region 범위
- data 범위
- tenant 범위
- 시간 범위
- artifact와 deployment version

Credential 하나가 여러 account의 role을 사용할 수 있으면 실제 영향은 처음 발견한 resource보다 넓을 수 있습니다.

## 11. Containment

가능한 조치:

- session과 key 폐기
- role assumption 차단
- public route와 endpoint 제거
- function trigger 중지
- 문제 있는 image 배포 중단
- affected tenant suspend
- account network 격리
- snapshot과 log 보존

주의할 점:

- 조사 자료를 함께 지우지 않습니다.
- backup과 log 접근까지 막지 않습니다.
- 전체 production을 불필요하게 중단하지 않습니다.
- 공격자가 만든 automation과 scheduled job를 찾습니다.
- 같은 dependency를 다른 경로에서 호출하는지 확인합니다.

가능하면 되돌릴 수 있는 조치를 먼저 선택합니다.

## 12. Recovery

깨끗한 상태를 구체적으로 정의합니다.

- 신뢰할 수 있는 account와 identity
- 확인한 artifact
- 알려진 설정
- 교체한 secret과 key
- 복원한 data
- 다시 확인한 tenant isolation
- 동작 중인 monitoring
- 차단한 공격 지속 경로

침해된 resource를 그 자리에서 고치는 것보다 깨끗한 환경에 같은 artifact와 data를 다시 배포하는 편이 신뢰하기 쉬울 수 있습니다.

## 13. 보존할 조사 자료

- control plane audit export
- resource 설정 snapshot
- network flow 또는 access log
- 필요할 경우 disk snapshot
- function version과 bundle
- identity policy history
- key usage log
- 비용과 사용량 이상
- provider support case

자료에 개인정보와 tenant data가 포함될 수 있으므로 접근 권한과 보존 기간을 정합니다.

## 14. 검토 질문

1. Workload가 자신의 audit와 backup을 삭제할 수 있습니까?
2. 영향받은 tenant를 구분할 수 있습니까?
3. Control plane 변경과 application request를 같은 시간표에 놓을 수 있습니까?
4. Credential을 폐기한 뒤에도 asynchronous job가 실행됩니까?
5. 깨끗한 account에 같은 artifact를 다시 배포할 수 있습니까?
6. Incident 중 비용 증가를 감지하고 제한할 수 있습니까?

## 구현 실습과 연결

[`local-cloud-model`](../exercises/local-cloud-model/README.md)은 resource를 private로 표시하고 tenant별 상태를 분리하지만 실제 IAM, network와 encryption은 구현하지 않습니다. `evidence_snapshot()`은 조사에 필요한 식별자와 상태만 반환하고 문서 본문은 제외합니다. 실제 환경에서도 조사 자료에 필요한 값과 노출하면 안 되는 payload를 구분해야 합니다.
