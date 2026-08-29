# Control plane, data plane과 identity

클라우드에서는 “서비스에 접근할 수 있습니다”라는 한 문장만으로 권한을 설명할 수 없습니다. 자원의 존재와 설정을 바꾸는 작업, 운영 자료를 읽는 작업, 사용자 데이터를 처리하는 작업이 서로 다른 권한을 사용하기 때문입니다.

```text
control plane
resource의 생성, 삭제, 설정, policy와 배치를 바꿉니다.

management data plane
log, backup, secret와 artifact 같은 운영 자료를 다룹니다.

application data plane
사용자 request와 업무 데이터를 읽고 씁니다.
```

공급자마다 이름은 다를 수 있지만, 사고 범위와 audit 자료를 나누는 기준으로 유용합니다.

## 1. Control plane

대표 작업은 다음과 같습니다.

- VM, database와 function 생성·삭제
- network와 route 변경
- IAM role과 policy 연결
- backup 보존 기간 변경
- auto scaling limit 변경
- logging 비활성화
- key policy 변경
- replication topology 변경

Control plane 권한이 탈취되면 workload code를 직접 수정하지 않아도 network를 공개하거나 snapshot을 복사하고 audit를 끌 수 있습니다.

중요한 상태:

- 원하는 설정
- resource identity
- policy binding
- deployment version
- operation status
- audit event
- 변경 lock과 approval

필수 조건:

```text
production 변경은 승인된 identity만 수행합니다.
변경마다 actor, resource, change ID와 결과를 기록합니다.
workload identity는 audit, backup과 key를 삭제할 수 없습니다.
```

## 2. Data plane

Application data plane은 사용자 request, object read, database query와 queue publish처럼 실제 업무 데이터를 처리합니다.

Control plane 권한이 없어도 data token이 유출되면 정보가 노출될 수 있습니다. 반대로 업무 데이터 권한이 없어도 control plane 권한으로 network를 공개하거나 backup을 복제할 수 있습니다. 두 경로를 따로 위협 모델에 넣어야 합니다.

## 3. Identity 종류

### 사람 identity

개발자, 운영자, 지원 담당자와 감사자입니다. 개인별 계정, 강한 인증, 짧은 privileged session과 승인 기록이 필요합니다.

### Workload identity

VM, container, function, batch job와 service가 다른 resource에 접근할 때 사용합니다. 장기 access key를 파일에 저장하기보다 runtime이 짧은 credential을 발급하는 방식을 우선합니다.

### Automation identity

CI/CD, IaC runner, backup job와 scanner가 사용합니다. Workload identity와 비슷하지만 production 변경, 승인과 audit 요구가 더 강할 수 있습니다.

### Customer identity

SaaS 사용자와 tenant member입니다. Cloud IAM과 application authorization을 같은 것으로 취급하면 안 됩니다. Customer role은 업무 객체 접근을 제어하고, cloud IAM은 infrastructure resource 접근을 제어합니다.

### Provider identity

공급자 내부 service와 운영자가 자원을 관리할 때 사용합니다. 사용자가 직접 확인하지 못하는 작업은 service contract, audit 기능과 support 절차로 확인합니다.

## 4. 인증, 권한 검사와 위임

- **authentication**: 요청한 identity가 누구인지 확인합니다.
- **authorization**: 특정 action을 특정 resource에 허용할지 결정합니다.
- **delegation**: 한 identity의 권한 일부를 제한된 시간과 범위로 넘깁니다.
- **impersonation**: 지원이나 운영 목적으로 다른 사용자 관점에서 작업합니다.

Support impersonation에는 최소한 다음 정보가 필요합니다.

```text
operator
reason_or_ticket
tenant_id
allowed_actions
approved_by
starts_at
expires_at
result
audit_event
```

숨겨진 관리자 우회 경로로 만들면 안 됩니다.

## 5. 권한 규칙을 읽는 네 질문

1. Principal은 누구입니까?
2. 어떤 action을 허용합니까?
3. 어떤 resource에 적용합니까?
4. 어떤 condition에서만 허용합니까?

`admin` 같은 넓은 이름보다 실제 작업을 표현합니다.

```text
backup-restore-runner
- 지정한 backup artifact 읽기
- 격리된 restore 환경 생성
- production overwrite 금지
- 60분 뒤 credential 만료
```

## 6. Resource hierarchy와 사고 범위

공급자는 organization, account, subscription, project, folder와 resource group 같은 단위를 제공합니다. 이름은 달라도 다음 목적은 비슷합니다.

- 관리자와 변경 권한 분리
- policy 상속
- billing 배분
- quota 적용
- production과 실험 환경 분리
- audit 자료 보관

모든 환경을 한 account에 넣으면 잘못된 policy와 quota 변경의 영향이 커집니다. 반대로 지나치게 나누면 identity, network, inventory와 비용 관리가 복잡해집니다.

다음 기준으로 분리합니다.

- 신뢰 수준
- 데이터 민감도
- 자원 수명
- 비용 담당자
- 관리자
- 함께 실패해도 되는 범위
- 규제와 감사 요구

## 7. Metadata와 runtime credential

VM, container와 function runtime은 metadata endpoint를 통해 credential을 제공할 수 있습니다. 별도 secret 파일을 두지 않아도 되는 장점이 있지만 SSRF, 과도한 role과 결합하면 공격 경로가 됩니다.

확인할 항목:

- 어떤 process가 endpoint에 접근할 수 있습니까?
- credential 범위와 유효 시간은 얼마입니까?
- token audience와 resource condition이 있습니까?
- 애플리케이션이 임의 URL로 요청할 수 있습니까?
- credential 사용 기록을 남깁니까?

## 8. Secret와 일반 설정을 구분합니다

Secret도 설정의 일부지만 같은 방식으로 보관하면 안 됩니다.

- source repository와 image에 넣지 않습니다.
- workload identity로 필요한 시점에 읽습니다.
- version, rotation과 폐기 상태를 기록합니다.
- log와 error에 평문을 남기지 않습니다.
- `previous`, `candidate`, `current`, `revoked` 상태를 구분합니다.

Managed secret service를 사용해도 애플리케이션이 rotation을 견디는지, 이전 credential을 실제로 폐기했는지는 사용자가 확인해야 합니다.

## 9. Audit 자료

Control plane audit는 최소한 다음을 복원해야 합니다.

- actor identity와 session
- source context
- action과 resource
- 안전하게 기록한 request parameter
- 허용 또는 거부 결과
- provider operation ID
- 시간
- 최종 결과

Data plane audit는 양과 비용이 크므로 위험에 따라 선택합니다. Tenant export, admin read, key 사용과 backup restore처럼 민감한 작업은 별도 event로 남기는 편이 좋습니다.

Audit log도 보호해야 합니다.

- workload와 다른 storage에 저장합니다.
- workload identity의 삭제 권한을 막습니다.
- 필요한 기간 동안 보존합니다.
- 모든 시스템의 시간 기준을 맞춥니다.
- 사고 조사 시 다른 환경으로 export할 수 있어야 합니다.

## 10. Break-glass 접근

정상 identity provider나 automation이 실패했을 때 emergency access가 필요할 수 있습니다. 평소 사용하는 super-admin 계정과는 다릅니다.

- 계정 수를 제한합니다.
- credential을 별도로 보관합니다.
- 사용 조건과 승인자를 정합니다.
- 사용 즉시 alert를 보냅니다.
- session 시간을 짧게 둡니다.
- 사용 뒤 credential을 교체하고 사후 검토합니다.

## 11. 사고가 발생했을 때 확인할 순서

1. Control plane 설정이 바뀌었습니까?
2. Workload code나 image가 바뀌었습니까?
3. Data plane credential이 사용됐습니까?
4. 영향받은 account, resource와 tenant는 어디까지입니까?
5. 공격자가 log, backup과 key 설정을 바꿀 수 있었습니까?
6. Credential을 폐기한 뒤에도 cached session이나 job가 남아 있습니까?
7. 깨끗한 account나 project에서 같은 artifact를 다시 배포할 수 있습니까?

## 구현 실습과 연결

[`local-cloud-model`](../exercises/local-cloud-model/README.md)은 cloud IAM을 구현하지 않습니다. 대신 모든 공개 작업에 `tenant_id`를 전달하고, 다른 tenant의 문서 접근을 거부합니다. 실제 환경에서는 이 application 검사를 workload identity, resource policy와 network rule로 한 번 더 제한해야 합니다.
