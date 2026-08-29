# 클라우드 자원의 상태, 담당 작업과 검증 근거

클라우드 서비스를 검토할 때 다음 표현만으로는 판단할 수 없습니다.

```text
managed이므로 운영할 일이 없습니다.
serverless이므로 server가 없습니다.
multi-AZ이므로 장애가 나지 않습니다.
auto scaling이므로 부하를 처리합니다.
암호화했으므로 안전합니다.
```

어떤 조건에서는 맞지만, 누가 무엇을 관리하고 실패 뒤 어떤 상태가 남는지 빠져 있습니다. 이 문서는 이런 표현을 실제로 확인할 수 있는 질문으로 바꾸는 방법을 다룹니다.

## 1. 클라우드 자원은 상태를 가집니다

VM 하나만 보더라도 대략 다음 상태를 거칩니다.

```text
ABSENT
→ PROVISIONING
→ STARTING
→ RUNNING
→ STOPPING
→ STOPPED
→ DELETING
→ DELETED
```

공급자는 더 많은 중간 상태와 실패 상태를 둘 수 있습니다. 중요한 점은 API 요청이 성공했다는 사실과 사용자가 기능을 쓸 수 있다는 사실이 같지 않다는 것입니다.

```text
create 요청이 수락됨
≠ resource 생성 완료
≠ workload 실행 준비 완료
≠ dependency 연결 완료
≠ 사용자 기능 정상 동작
```

변경 작업을 기록할 때는 최소한 다음 시점을 나눕니다.

- 요청을 공급자가 수락했는가
- control plane 작업이 끝났는가
- resource가 data plane 요청을 받는가
- network, identity와 storage가 연결됐는가
- 애플리케이션 readiness 검사가 통과했는가
- 실패했다면 어떤 resource와 설정이 남았는가

## 2. 다섯 종류의 상태

모든 상태를 단순히 “인프라 상태”라고 부르면 삭제, 복구와 비용 판단이 어려워집니다.

### 2.1 원하는 상태

사용자가 만들고 싶은 결과입니다.

```text
application instance 3개
private database
public HTTPS endpoint
object retention 30일
worker concurrency 최대 20
```

IaC, deployment manifest, 설정 파일이나 관리 API 요청이 이 상태를 표현합니다.

### 2.2 공급자가 관리하는 상태

공급자가 자원을 만들고 배치하기 위해 보관하는 값입니다.

- resource ID
- region과 zone
- lifecycle status
- policy attachment
- auto scaling target
- managed backup 설정

사용자는 일부 값을 API로 읽고 바꿀 수 있지만, 내부 scheduler와 hardware 상태를 직접 관리하지는 않습니다.

### 2.3 실행 중 상태

실행 중인 workload가 가진 상태입니다.

- process와 memory
- connection pool
- local cache
- temporary file
- 처리 중인 request
- function execution context

PaaS나 FaaS가 runtime의 생성과 폐기를 관리하더라도 application bug, memory leak과 잘못된 retry는 사용자에게 남습니다.

### 2.4 보존해야 할 업무 상태

사용자, tenant, 문서, 결제 정보와 처리 결과처럼 서비스가 보존해야 하는 데이터입니다. Managed database에 저장하더라도 의미, 보존 기간, export와 삭제 시점은 애플리케이션 운영자가 결정합니다.

### 2.5 검증 근거

변경과 장애를 나중에 설명하는 자료입니다.

- audit log
- resource event
- metric과 trace
- deployment record
- billing line item
- backup manifest와 restore report
- tenant export manifest

이 자료도 접근 권한, 보존 기간, 시간 기준과 삭제 규칙을 가집니다.

## 3. 담당 작업은 제품 이름이 아니라 작업 단위로 적습니다

“OS 아래는 공급자, 애플리케이션 위는 사용자”라는 그림만으로는 실제 작업을 나누기 어렵습니다. 같은 managed database라도 항목마다 담당자가 다릅니다.

| 작업 | 공급자가 제공할 수 있는 것 | 사용자가 계속 해야 하는 일 |
|---|---|---|
| hardware 교체 | 장치와 host 유지 | 서비스 영향과 복구 목표 확인 |
| engine patch | patch 배포 기능 | 적용 시점, 호환성, rollback 판단 |
| backup 생성 | schedule과 artifact 생성 | 성공 감시, 보존 기간, restore 검증 |
| encryption | 암호화 기능과 key service | key 권한, rotation, 평문 경로 차단 |
| availability | replica와 failover 기능 | topology 선택, client retry, readiness 확인 |
| monitoring | metric과 log 수집 기능 | 필요한 신호, alert 조건, 대응 담당자 지정 |
| scaling | capacity 조정 기능 | metric, 상한, downstream 병목, 비용 제한 설정 |

따라서 “database는 공급자가 관리합니다”보다 “누가 patch를 적용하고, 누가 restore를 실행해 결과를 확인하는가”라고 적는 편이 정확합니다.

## 4. 한 자원에도 여러 담당자가 있습니다

- **업무 담당자**: 자원이 필요한 이유와 종료 조건을 결정합니다.
- **설정 담당자**: 원하는 설정과 변경 승인을 관리합니다.
- **운영 담당자**: 정상 동작을 감시하고 장애에 대응합니다.
- **데이터 담당자**: 분류, 보존, export와 삭제를 결정합니다.
- **비용 담당자**: 예산, 비용 배분, 이상 증가와 정리를 확인합니다.

`owner=platform-team` 한 필드만으로는 변경 승인과 데이터 삭제의 담당자를 구분할 수 없습니다.

## 5. 주장을 검증 가능한 자료로 바꿉니다

### “두 zone에 배치했습니다”

다음을 확인합니다.

- 실제 resource가 배치된 zone
- traffic이 각 zone으로 분배되는지
- zone 하나를 제외했을 때 사용자 오류와 복구 시간
- database와 queue 같은 stateful dependency의 배치
- 남은 zone이 peak traffic을 처리할 수 있는지

### “자동으로 확장합니다”

다음 값과 결과가 필요합니다.

- 측정 metric과 threshold
- 측정 구간
- 최소·최대 capacity
- 새 instance가 준비되기까지 걸린 시간
- scale-in 전에 처리 중 작업을 비우는 방법
- load test 중 latency, error, queue와 비용 변화

### “백업됩니다”

backup 생성 사실만으로는 충분하지 않습니다.

- 최근 성공한 backup ID와 checksum
- 포함하거나 제외한 데이터
- 다른 환경에 복원한 결과
- 측정한 RPO와 RTO
- key, secret과 설정을 다시 준비하는 방법

### “tenant가 격리됩니다”

- request마다 tenant를 확정하는 방법
- cross-tenant negative test
- cache, queue, background job과 export의 tenant 식별자
- support/admin 접근 기록
- backup, analytics와 log에서 tenant를 구분하는 방법

## 6. 변경 작업에 남길 최소 정보

```text
change_id
actor_identity
requested_at
resource_scope
before_state
requested_state
authorization_result
provider_operation_id
observed_final_state
verification_evidence
cost_effect
rollback_or_compensation
```

모든 시스템이 이 필드 이름을 그대로 쓸 필요는 없습니다. 다만 누가 어떤 자원을 왜 바꿨고, 공급자가 실제로 어떤 상태를 만들었는지는 복원할 수 있어야 합니다.

## 7. 비동기 control plane에서 자주 생기는 문제

- client는 timeout을 받았지만 공급자 작업은 계속 진행됩니다.
- 일부 resource만 만들어진 뒤 dependency 생성이 실패합니다.
- 삭제 요청은 성공했지만 실제 삭제와 과금 종료는 늦게 반영됩니다.
- rollback 도중 다른 오류가 발생합니다.
- 같은 create 요청을 다시 보내 중복 resource가 생깁니다.
- console과 audit export가 서로 다른 시점의 상태를 보여 줍니다.

변경 코드는 client request ID, provider operation ID와 resource tag를 함께 기록하고, 재시도 전에 이미 만들어진 자원을 조회해야 합니다.

## 8. 검증 근거가 보장하지 않는 것

- control plane audit는 application data 접근을 모두 기록하지 않을 수 있습니다.
- 평균 metric은 짧은 오류 증가를 숨길 수 있습니다.
- `backup completed`는 restore 가능성을 증명하지 않습니다.
- provider status page의 범위와 특정 tenant의 장애 범위는 다를 수 있습니다.
- 비용 estimate는 실제 egress와 retry를 놓칠 수 있습니다.
- local model은 실제 IAM 전파 지연, network와 공급자 quota를 재현하지 못합니다.

자료를 제시할 때는 확인한 항목과 확인하지 못한 항목을 함께 적습니다.

## 9. 검토 질문

1. 이 resource를 지운 뒤 같은 설정으로 다시 만들 수 있습니까?
2. 다시 만들 수 없다면 정본 데이터는 어디에 있습니까?
3. create, update와 delete가 중간에 실패하면 무엇이 남습니까?
4. 설정 변경 권한과 업무 데이터 접근 권한이 같은 identity에 묶여 있습니까?
5. 공급자가 대신 수행한다는 작업을 사용자는 어떤 자료로 확인합니까?
6. 사용하지 않는 동안에도 비용이 발생합니까?
7. 종료할 때 data, log, key와 설정을 회수하고 삭제할 수 있습니까?

## 구현 실습과 연결

[`local-cloud-model`](../exercises/local-cloud-model/README.md)은 tenant, document, event, usage와 resource를 서로 다른 상태로 보관합니다. `evidence_snapshot()`이 어떤 값을 보여 주고 무엇을 숨기는지 확인하면 이 문서의 상태 구분을 코드로 검토할 수 있습니다.
