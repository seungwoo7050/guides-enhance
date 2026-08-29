# Failure domain, elasticity와 recovery

클라우드는 자원을 여러 위치에 배치하고 자동으로 늘리는 기능을 제공합니다. 그러나 설정을 켰다는 사실만으로 가용성과 복구가 완성되지는 않습니다. 어떤 자원이 같은 원인으로 함께 멈추는지, 남은 용량과 데이터로 실제 업무를 계속 처리할 수 있는지를 확인해야 합니다.

## 1. Failure domain을 찾습니다

Failure domain은 하나의 사건으로 함께 영향을 받을 수 있는 자원 집합입니다.

- process
- instance 또는 node
- rack, power와 network 장비
- availability zone
- region
- identity provider 또는 control plane
- DNS provider
- artifact registry
- 조직 전체 policy

Instance가 두 개여도 같은 zone, database, secret, deployment와 load balancer를 공유하면 일부 장애에는 독립적이지 않습니다.

## 2. Region과 zone

공급자마다 topology 정의가 다르지만 보통 region은 지리적 운영 범위, zone은 region 안의 상대적으로 독립된 장애 단위를 뜻합니다.

다음을 실제 resource 목록과 시험 결과로 확인합니다.

- compute와 stateful service가 몇 zone에 배치됐습니까?
- zone 사이 data replication은 synchronous입니까?
- load balancer, network와 control plane은 zonal입니까, regional입니까?
- zone 하나가 사라졌을 때 남은 capacity가 peak traffic을 처리합니까?
- failover를 누가 감지하고 얼마나 걸려 승격합니까?
- 기존 client connection과 DNS cache가 새 target으로 이동합니까?

`multi-AZ enabled`는 확인을 시작할 설정일 뿐 결론이 아닙니다.

## 3. Availability와 durability를 구분합니다

- **availability**: 지금 요청을 처리할 수 있는가
- **durability**: 저장한 데이터가 장기간 보존되는가

Object가 여러 장치에 복제돼도 identity나 network 장애 때문에 읽지 못할 수 있습니다. 반대로 application이 계속 응답해도 최근 데이터 일부가 유실될 수 있습니다.

목표를 따로 적습니다.

```text
availability target
RTO: 서비스를 다시 제공하기까지 허용하는 시간
RPO: 복구할 때 허용하는 데이터 손실 구간
```

## 4. Redundancy, backup과 rebuild는 서로 다릅니다

### Redundancy

동시에 여러 replica나 경로를 유지합니다. 빠른 장애 전환에 유리하지만 잘못된 변경, 삭제와 corruption도 함께 복제될 수 있습니다.

### Backup

특정 시점의 독립 artifact를 보존합니다. 잘못된 삭제나 논리 오류를 되돌리는 데 필요하지만 restore 시간이 걸립니다.

### Rebuild

Image, 설정, secret과 backup으로 새 환경을 만듭니다. Region이나 account 전체를 잃었을 때 유용하지만 반복해서 시험하지 않으면 실제 복구 시간을 알 수 없습니다.

세 방법은 서로 대체하지 않습니다.

## 5. Elasticity 방식

### Scale out

Instance 수를 늘립니다. Application이 stateless하거나 공유 상태를 외부에 둬야 효과가 있습니다.

### Scale up

Instance 크기나 provisioned capacity를 늘립니다. 단순하지만 상한, 재시작과 큰 비용 증가 구간이 있습니다.

### Scale to zero

사용하지 않을 때 compute를 제거합니다. 비용은 줄지만 cold start, 첫 요청 지연과 local state 손실을 받아들여야 합니다.

### Queue-based scaling

Backlog, 가장 오래된 message의 대기 시간, 처리 시간과 concurrency를 기준으로 확장합니다. 처리할 수 없는 poison message가 쌓이면 capacity와 비용만 계속 늘어날 수 있습니다.

## 6. Scaling은 제어 반복입니다

```text
metric 관찰
→ 목표와 비교
→ 필요한 capacity 계산
→ resource 추가 또는 제거
→ readiness 또는 drain 대기
→ 결과 재측정
```

다음 문제가 자주 생깁니다.

- metric이 늦게 도착합니다.
- capacity가 반복해서 늘고 줄어듭니다.
- 새 instance 준비가 traffic 증가보다 늦습니다.
- database나 외부 API가 먼저 포화됩니다.
- quota와 지역 capacity가 부족합니다.
- scale-in 과정에서 처리 중 작업을 잃습니다.
- 짧은 traffic burst가 측정 구간에 잡히지 않습니다.
- 비용 상한이 없습니다.

Minimum, maximum, cooldown, step size, readiness, drain과 budget 제한을 함께 설정합니다.

## 7. 무조건 확장하지 않습니다

Dependency가 병목일 때 application instance만 늘리면 connection 폭주와 비용 증가를 만들 수 있습니다.

필요한 통제:

- 새 요청 수락 제한
- tenant별 quota
- 길이가 제한된 queue
- end-to-end timeout
- retry 횟수와 시간 제한
- 기능 축소 모드
- 작업 우선순위
- circuit breaker
- 명확한 overload 응답

Auto scaling이 이 통제를 대신하지 않습니다.

## 8. 복구 절차

복구는 새 instance를 시작하는 것으로 끝나지 않습니다.

```text
장애 감지
→ 영향 범위 구분
→ 위험한 automation 중지
→ 조사 자료 보존
→ failover 또는 restore 선택
→ 깨끗한 capacity 준비
→ 데이터와 설정 복원
→ 업무 불변식 확인
→ traffic 전환
→ 상태 관찰
→ 이전 resource 정리
```

자동 failover는 빠르지만 잘못된 데이터와 설정을 퍼뜨릴 수 있습니다. 수동 승인은 느리지만 잘못된 승격을 막을 수 있습니다. RTO, 데이터 민감도와 운영 능력에 맞춰 결정합니다.

## 9. Failure injection을 안전하게 수행합니다

Production에서 범위를 정하지 않은 장애를 만들면 안 됩니다. 작은 환경에서 다음 항목을 시험할 수 있습니다.

- instance 종료
- 한 zone의 target 제외
- network deny
- dependency 지연
- quota 소진
- credential 만료
- 잘못된 deployment
- backup restore

시험 전에 다음을 적습니다.

```text
가설
대상 resource와 tenant
정상 상태 metric
주입할 실패
처음 울려야 할 alarm
예상되는 기능 축소
중단 조건
복구 방법
남길 자료
정리 방법
```

## 10. Common-mode failure를 찾습니다

Replica가 여러 개여도 다음 항목을 공유하면 동시에 실패할 수 있습니다.

- 같은 image bug
- 같은 deployment
- 같은 IAM policy
- 같은 key
- 같은 region control plane
- 같은 DNS
- 같은 provider
- 같은 운영자 실수

가용성 검토에서는 replica 개수보다 실패 원인이 실제로 분리됐는지 확인합니다.

## 11. 복구 비용도 기록합니다

Standby capacity, cross-zone transfer, backup 보존, cross-region replication과 restore test에는 비용이 듭니다. 반대로 모든 자원을 scale-to-zero로 만들면 첫 요청과 장애 복구가 느려집니다.

결정마다 다음을 적습니다.

- 보호하려는 업무 영향
- 예상 장애 빈도
- 정상 상태 비용
- failover 중 비용
- 정기 시험 비용
- 받아들이기로 한 잔여 위험

## 12. 남길 검증 자료

- zone과 dependency가 포함된 topology inventory
- failure domain별 남은 capacity
- load test와 scaling 시간표
- failover operation log
- 측정한 RTO와 RPO
- restore checksum과 업무 불변식 결과
- alarm 발생 시각
- traffic 전환 자료
- 정리 전후 resource와 비용 차이

## 다음 단계

장애와 복구 범위를 정리한 뒤 [`06-paas-and-managed-service-contracts.md`](06-paas-and-managed-service-contracts.md)에서 managed service가 어떤 작업을 대신 수행하고 어떤 확인은 사용자에게 남기는지 검토하십시오.
