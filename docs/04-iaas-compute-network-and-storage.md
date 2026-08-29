# IaaS compute, network와 storage

IaaS는 물리 장비 대신 API로 compute, network와 storage를 조합하게 합니다. 자원을 빨리 만들고 교체할 수 있으므로 정본 데이터, 자원 수명, 연결, identity와 삭제 조건을 더 분명히 적어야 합니다.

## 1. Resource inventory부터 작성합니다

Diagram만으로 관리하면 실제 resource와 담당자가 쉽게 어긋납니다. 최소한 다음 값을 기록합니다.

```text
resource_id
resource_type
account_or_project
region
zone
owner
purpose
environment
data_classification
created_by
created_at
expires_at
dependencies
stateful
backup_policy
cost_center
```

사람이 붙인 resource name은 바뀌거나 재사용될 수 있습니다. 공급자가 발급한 ID와 업무에서 쓰는 이름을 구분합니다.

## 2. Compute instance

VM에는 다음 상태가 포함됩니다.

- base image
- boot disk
- instance 설정
- network interface
- workload identity
- startup script
- local ephemeral storage
- 실행 중 process와 cache

### 수동 변경을 오래 남기지 않습니다

Instance에 접속해 package와 설정을 계속 바꾸면 선언한 상태와 실제 상태가 달라집니다.

```text
새 image 또는 반복 실행 가능한 bootstrap 준비
→ 새 instance 생성
→ readiness 확인
→ traffic 전환
→ 이전 instance 종료
```

이 방식은 replacement와 scale-out을 쉽게 하지만 database migration, local state와 처리 중 request는 별도로 다뤄야 합니다.

### Image에 기록할 항목

- 변경할 수 없는 image ID 또는 digest
- build source
- OS와 package version
- vulnerability와 지원 종료 시점
- startup dependency
- secret이 포함되지 않았다는 검사
- boot 뒤 readiness 조건
- 이전 image로 되돌리는 방법

## 3. Network

IaaS network는 여러 객체를 조합해 만듭니다.

- address range와 subnet
- route table
- network interface
- public/private address
- firewall 또는 security rule
- NAT와 egress
- load balancer
- private endpoint
- DNS

`private-subnet`이라는 이름만으로 접근이 차단되지는 않습니다. Route, public address, peering, endpoint와 firewall을 함께 확인합니다.

### Ingress와 egress

Ingress만 제한하고 egress를 모두 허용하면 침해된 workload가 외부로 데이터를 보내거나 다른 service에 접근할 수 있습니다. 반대로 egress를 모두 막으면 identity, package, telemetry와 외부 API가 동작하지 않을 수 있습니다.

연결마다 다음을 적습니다.

```text
source identity 또는 network
destination service
protocol과 port
purpose
DNS dependency
proxy 또는 inspection
failure behavior
owner
```

### Load balancer

Healthy target만 고른다는 주장은 health check가 정확할 때만 성립합니다.

- process가 살아 있는지와 application이 준비됐는지를 구분합니다.
- 모든 dependency를 readiness에 묶어 전체 target이 동시에 빠지지 않게 합니다.
- drain timeout과 long-lived connection을 고려합니다.
- TLS 종료 위치와 request ID 전달을 확인합니다.
- target이 zone별로 실제 분산됐는지 확인합니다.

## 4. Storage 유형

### Block storage

Filesystem이나 database volume처럼 block device로 연결합니다.

- 어느 zone과 instance에 붙일 수 있는가
- single/multi attach가 무엇을 보장하는가
- snapshot이 어느 시점의 데이터를 포함하는가
- 어떤 key로 암호화하는가
- detach와 reattach 순서가 무엇인가
- filesystem 손상 시 어떻게 복구하는가
- 삭제 보호가 있는가

### Object storage

Object key와 metadata로 접근합니다. Filesystem의 rename, locking과 partial write 의미를 그대로 가정하면 안 됩니다.

- versioning과 overwrite 의미
- delete와 lifecycle rule
- retention과 legal hold
- 중단된 multipart upload 정리
- public access
- tenant별 key prefix와 authorization
- inventory와 checksum
- request, storage와 egress 비용

### Ephemeral/local storage

Instance나 execution environment와 함께 사라질 수 있습니다. Cache와 scratch 용도로만 사용하고 정본 데이터를 두지 않습니다.

### Managed database

단순 storage가 아니라 관리형 service입니다. Engine version, transaction, backup, failover와 connection limit는 [`06-paas-and-managed-service-contracts.md`](06-paas-and-managed-service-contracts.md)에서 다룹니다.

## 5. 데이터 수명을 분류합니다

| 종류 | 예 | instance 교체 시 처리 |
|---|---|---|
| 다시 만들 수 있음 | image, deployment 설정 | source에서 다시 생성 |
| 보존해야 할 정본 | database, object | 외부 durable storage와 backup 사용 |
| 정본에서 파생됨 | search index, thumbnail | 다시 계산 |
| 일시적 | temp file, local cache | 손실 허용 |
| 검증 자료 | audit, metric, trace | workload 밖으로 전송해 보존 |

이 분류 없이 instance를 언제든 지울 수 있다고 판단하면 안 됩니다.

## 6. Bootstrap과 설정 적용

Startup script는 다음 실패를 고려해야 합니다.

- package repository 지연
- DNS 실패
- secret 발급 실패
- database migration 경쟁
- 같은 script 재실행
- 일부 단계만 성공한 뒤 중단
- log에 secret 출력

Bootstrap은 반복 실행해도 같은 결과가 나와야 하며, 실패 지점과 최종 상태를 남기고 readiness 전에 끝나야 합니다. 시간이 오래 걸리는 build는 startup보다 image build 단계에서 수행하는 편이 재현하기 쉽습니다.

## 7. 생성과 삭제 순서

일반적인 생성 순서는 다음과 같습니다.

```text
identity와 policy
→ network
→ storage·database
→ compute
→ load balancer·DNS
→ telemetry와 alert
```

삭제는 단순히 역순으로 실행하지 못할 수 있습니다.

- DNS TTL과 traffic drain을 기다려야 합니다.
- final backup이나 export가 필요할 수 있습니다.
- retention lock 때문에 바로 지울 수 없을 수 있습니다.
- log를 일정 기간 보존해야 합니다.
- key를 먼저 지우면 backup을 읽지 못할 수 있습니다.
- shared resource가 다른 workload에서 사용 중일 수 있습니다.
- API 삭제 뒤에도 과금 종료를 따로 확인해야 합니다.

Resource graph에 dependency와 삭제 조건을 함께 기록합니다.

## 8. 대표 실패를 확인합니다

### Instance loss

- load balancer가 target을 제거합니까?
- 같은 image와 설정으로 replacement를 만들 수 있습니까?
- local state 손실을 허용했습니까?
- 남은 capacity와 quota가 충분합니까?

### Network rule 오류

- 변경한 actor를 audit에서 찾을 수 있습니까?
- management access가 끊겼을 때 되돌릴 방법이 있습니까?
- 지나치게 넓은 규칙을 자동으로 찾습니까?

### Disk full 또는 volume loss

- application이 read-only나 fail-fast로 바뀝니까?
- snapshot consistency 수준을 알고 있습니까?
- restore 뒤 schema와 업무 불변식을 확인합니까?

### Orphan resource

- unattached volume, idle address, snapshot, load balancer, NAT와 log sink가 남았습니까?
- owner와 만료 시각이 있습니까?
- 삭제 뒤 inventory와 billing 자료를 다시 확인했습니까?

## 9. 남길 검증 자료

- resource inventory export
- image digest 또는 immutable ID
- network path test
- private resource negative access test
- replacement instance bootstrap log
- backup과 restore report
- instance 종료 뒤 사용자 기능 결과
- 삭제 전후 inventory와 비용 변화

## 다음 단계

IaaS 자원의 수명을 정리한 뒤 [`05-failure-domains-elasticity-and-recovery.md`](05-failure-domains-elasticity-and-recovery.md)에서 어떤 자원이 같은 원인으로 함께 멈추는지 확인하십시오.
