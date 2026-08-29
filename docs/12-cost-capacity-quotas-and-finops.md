# Cost, capacity, quota와 FinOps

클라우드 비용은 나중에 청구서를 확인하는 회계 작업만이 아닙니다. Resource를 만들고, 늘리고, 보존하고, 전송하는 설계가 실제 사용량과 비용을 만듭니다.

```text
workload demand
→ resource allocation
→ measured usage
→ price rule
→ bill
```

비용을 줄이기 전에 어떤 resource가 어떤 업무 결과를 만들었는지 연결해야 합니다.

## 1. 비용 단위를 먼저 찾습니다

대표적인 단위:

- VM 또는 node 실행 시간
- provisioned CPU와 memory
- request 수
- function 실행 시간과 memory
- storage byte-month
- I/O operation
- database capacity unit
- snapshot과 backup
- internet egress
- cross-zone·cross-region transfer
- log 수집, 보존과 query
- public address, NAT와 load balancer
- support plan

`serverless는 사용한 만큼만 냅니다`라는 표현도 request 외의 log, warm capacity, storage와 egress를 포함해 확인해야 합니다.

## 2. 고정, 사용량 연동과 단계 비용

### 고정 또는 idle 비용

Traffic이 없어도 발생합니다.

- 항상 켜 둔 instance
- managed database의 최소 capacity
- load balancer
- NAT
- reserved capacity
- tenant 전용 resource

### 사용량 연동 비용

사용량과 함께 증가합니다.

- request
- function execution
- object operation
- egress
- log ingestion

### 단계 비용

특정 threshold를 넘을 때 replica나 service tier 하나가 추가됩니다. 작은 증가가 큰 월 비용 증가로 이어질 수 있습니다.

비용 곡선을 알아야 낮은 사용량과 꾸준한 고사용량에 맞는 실행 방식을 비교할 수 있습니다.

## 3. 업무 결과당 비용을 계산합니다

총 bill만으로는 효율을 판단하기 어렵습니다.

```text
active tenant 1곳당 비용
문서 1,000건 처리 비용
성공한 job 1건당 비용
보존 데이터 1GB당 비용
정상 API request 1,000건당 비용
```

분모는 실제 업무 결과와 연결해야 합니다. 실패, retry와 dead letter도 비용에 포함합니다.

## 4. 비용을 담당자에게 연결합니다

Resource 비용을 team, service, environment와 tenant에 배분합니다.

- account 또는 project
- tag와 label
- resource group
- usage event
- shared cost 배분 규칙

Owner가 없는 resource를 허용하면 비용과 cleanup 실패가 계속 쌓입니다.

Shared database와 network 비용은 정확히 한 tenant에 나누기 어려울 수 있습니다. 일관된 배분 기준과 적용 version을 기록합니다.

## 5. Budget alert와 강제 제한을 구분합니다

Budget이 초과됐다고 resource 생성이 자동으로 멈추는 것은 아닐 수 있습니다.

가능한 통제는 다음처럼 강도가 다릅니다.

- forecast
- alert
- 추가 승인
- quota
- policy deny
- automation kill switch
- 기능 축소

어떤 조치가 자동으로 실행되고 누가 예외를 승인할 수 있는지 적습니다.

## 6. 비용 이상 증가

대표 원인:

- retry loop
- log 폭증
- 상한 없는 auto scaling
- 예상하지 못한 egress
- orphan resource
- 오래 남은 snapshot
- 탈취된 credential
- tenant abuse
- 가격이나 discount 변경

Anomaly alert에는 기준 사용량, threshold, billing data 지연, 담당자와 containment 방법이 필요합니다.

## 7. Capacity와 quota

공급자에게 큰 resource pool이 있어도 account quota와 지역 capacity는 제한됩니다.

- instance 수
- public address 수
- storage 용량
- management API rate
- function concurrency
- database connection
- throughput
- account별 resource 수

Peak 전에 현재 quota와 증가 요청에 걸리는 시간을 확인합니다. Quota를 크게 높이면 장애와 침해 시 비용 범위도 커질 수 있습니다.

## 8. Rightsizing

작은 instance로 바꾸는 것만이 rightsizing은 아닙니다.

- CPU, memory와 I/O 사용률
- tail latency
- traffic burst
- zone 하나를 잃었을 때의 여유 capacity
- scaling 준비 시간
- license 비용
- 운영 복잡성

평균 사용률만 보고 줄이면 peak와 장애 전환 시 capacity가 부족해질 수 있습니다.

## 9. Commitment

Reserved capacity와 committed-use 할인은 가격 할인과 장기 의존성을 교환합니다.

확인할 항목:

- 실제로 꾸준히 사용하는 baseline
- 계약 기간
- instance나 service 변경 가능 범위
- region 의존성
- 성장과 축소 예상
- migration 계획
- 쓰지 못하고 남을 commitment

할인율만 보지 말고 workload 변화와 exit 시점을 함께 봅니다.

## 10. Storage 수명과 비용

- hot, cool과 archive tier
- retrieval latency와 비용
- 최소 보존 기간
- object versioning
- 중복 backup
- legal hold
- 중단된 multipart upload
- snapshot dependency

Lifecycle rule로 데이터를 옮기거나 지우기 전에 업무 보존 규칙과 restore 결과를 확인합니다.

## 11. Network egress

Architecture diagram의 화살표는 비용을 만들 수 있습니다.

- internet egress
- cross-zone transfer
- cross-region replication
- provider 사이 transfer
- backup copy
- analytics export
- 고객 download

Data가 클수록 provider 이전과 disaster recovery 비용도 커집니다.

## 12. FinOps 운영 반복

```text
inform
resource, usage와 비용을 담당자가 볼 수 있게 합니다.

optimize
사용하지 않는 resource와 비효율적인 설계를 줄입니다.

operate
budget, quota, forecast와 ownership을 평상시 변경 절차에 넣습니다.
```

FinOps는 비용 절감 담당자만의 일이 아닙니다. Engineering, finance, product와 업무 담당자가 성능, 안정성과 비용의 trade-off를 함께 결정해야 합니다.

## 13. Cleanup 결과를 확인합니다

실험과 임시 환경에는 종료 조건이 필요합니다.

```text
resource prefix
tag owner
expires_at
dependency list
destroy command
final inventory
billing delay note
log와 evidence 보존 기간
```

Delete command가 성공했다고 정리가 끝난 것은 아닙니다. Inventory가 비었는지, snapshot과 network resource가 남지 않았는지, 과금이 언제 끝났는지 확인합니다.

## 14. 검토 질문

1. 가장 큰 세 비용 단위는 무엇입니까?
2. Traffic이 없어도 남는 비용은 무엇입니까?
3. Retry와 실패가 비용을 얼마나 늘립니까?
4. 한 tenant가 전체 비용을 급격히 늘릴 수 있습니까?
5. Zone 장애 뒤에도 필요한 capacity를 남겨 두었습니까?
6. Egress와 log 비용을 estimate에 포함했습니까?
7. 모든 resource에 담당자와 만료 시각이 있습니까?
8. Commitment가 migration이나 규모 축소를 막습니까?

## 구현 실습과 연결

[`local-cloud-model`](../exercises/local-cloud-model/README.md)은 provider 가격을 계산하지 않습니다. 대신 tenant별 usage와 active document quota를 따로 보관합니다. 실제 비용 모델을 붙일 때는 duplicate event가 usage와 비용을 중복으로 늘리지 않는지, tenant 삭제 뒤 유료 resource가 남지 않는지를 같은 기준으로 확인해야 합니다.
