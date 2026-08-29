# 서비스 선택과 architecture review

서비스 선택은 가장 새롭거나 익숙한 제품을 고르는 일이 아닙니다. Workload가 보존해야 할 상태, 예상 부하, 장애 목표, 팀의 운영 능력과 비용을 비교하는 일입니다.

같은 workload를 IaaS, managed platform이나 FaaS에 둘 수 있지만 사용자가 직접 수행할 작업과 실패 결과가 달라집니다.

## 1. Workload를 먼저 설명합니다

제품을 보기 전에 다음 내용을 적습니다.

```text
사용자와 tenant
request 또는 event 발생 방식
보존할 data와 민감도
latency와 throughput
availability target
RTO와 RPO
consistency와 ordering
runtime과 dependency
변경 빈도
identity와 network 요구
예상 성장
budget과 비용 담당자
팀의 운영 능력
export와 종료 요구
```

요구를 적지 않으면 제품 기능을 나열한 뒤 그에 맞춰 문제를 바꾸게 됩니다.

## 2. IaaS가 맞을 수 있는 경우

- OS, runtime과 network를 세밀하게 제어해야 합니다.
- Custom binary, agent나 driver가 필요합니다.
- 사용량이 꾸준하고 예측 가능합니다.
- 기존 application을 큰 변경 없이 옮겨야 합니다.
- Managed service limit가 요구에 맞지 않습니다.
- 특수한 security 또는 compliance 설정이 필요합니다.

사용자가 맡을 작업:

- image와 patch
- host capacity
- scaling과 failover
- monitoring과 backup
- 설정 drift와 replacement

## 3. Managed platform이 맞을 수 있는 경우

- 표준 web/API runtime을 사용합니다.
- Host 운영보다 application 변경에 집중하려 합니다.
- 배포, scaling과 managed data 기능을 빠르게 사용하려 합니다.

확인할 항목:

- runtime과 지원 version
- extension와 network 제한
- maintenance 방식
- scale 단위와 준비 시간
- metric과 log
- 최소 비용
- export와 종료 방식

## 4. FaaS가 맞을 수 있는 경우

- Event-driven 작업입니다.
- 사용량이 불규칙하거나 burst가 큽니다.
- 작업 시간이 짧고 상한을 정할 수 있습니다.
- 각 작업을 독립적으로 처리할 수 있습니다.
- 사용하지 않을 때 compute를 없애는 가치가 큽니다.
- 업무 결과별 비용을 세밀하게 나누려 합니다.

확인할 항목:

- timeout과 deadline
- duplicate와 ordering
- downstream capacity
- cold start
- package 크기
- local state 필요 여부
- concurrency
- 꾸준한 고사용량일 때 비용

## 5. 외부 SaaS 구매와 직접 구현

- 해당 기능이 제품의 차별점입니까?
- Data 민감도와 보존 요구는 무엇입니까?
- 기존 identity와 어떻게 연결합니까?
- 필요한 custom 동작을 지원합니까?
- Audit, export와 deletion을 확인할 수 있습니까?
- 공급자가 중단되거나 계약을 끝낼 때 대안이 있습니까?
- License 비용과 내부 운영 비용을 함께 계산했습니까?

직접 구현하면 license 비용을 줄일 수 있지만 tenant isolation, support, migration과 incident 대응을 직접 맡게 됩니다.

## 6. Managed database 선택

다음 질문부터 확인합니다.

- Relational, key-value, document와 object 중 data 조건에 맞습니까?
- 필요한 transaction과 consistency를 제공합니까?
- Access pattern과 partition key가 정해졌습니까?
- Backup, restore와 tenant 단위 복구가 가능합니까?
- Connection, throughput와 item size limit가 맞습니까?
- Export와 다른 시스템 import가 가능합니까?
- 실제 workload에서 비용 곡선이 어떻게 변합니까?

유행하는 storage 유형보다 data가 지켜야 할 조건을 먼저 봅니다.

## 7. 실행 방식 비교

| 기준 | IaaS | Managed platform | FaaS |
|---|---|---|---|
| OS 제어 | 넓음 | 제한적 | 거의 없음 |
| 확장 단위 | instance | service instance 또는 capacity | invocation과 concurrency |
| idle 비용 | 보통 존재 | 서비스마다 다름 | scale-to-zero 가능 |
| 시작 시간 | instance boot | platform 배포 | cold start 가능 |
| local state | instance 수명에 묶임 | 제한되거나 일시적 | 일시적 |
| event 처리 | 사용자가 구성 | 서비스마다 다름 | trigger 동작 확인 필요 |
| patch | 사용자가 많이 수행 | 일부 공급자에게 이동 | runtime은 공급자, code는 사용자 |
| 이식성 | image와 network 의존 | platform API 의존 | trigger와 delivery 의미 의존 |
| 관측 | 직접 구성 항목이 많음 | 제공 metric과 application 자료 결합 | invocation과 최종 결과 연결 필요 |

이 표는 일반적인 차이만 보여 줍니다. 실제 서비스의 공식 문서와 시험 결과를 우선합니다.

## 8. Architecture review 순서

### 1단계: 범위

- workload와 tenant
- production과 non-production
- region
- data 분류
- 외부 dependency

### 2단계: 상태

- 보존해야 할 정본
- 다시 계산할 수 있는 값
- 일시적 상태
- audit와 metric
- 상품과 사용량 상태가 필요한지

### 3단계: 담당자

- 업무 목적과 종료 결정
- 설정 변경
- runtime 운영
- data 보존과 삭제
- 비용과 cleanup

### 4단계: 접근 제어

- 사람, workload와 automation identity
- network 접근
- control plane과 data plane
- 변경 승인과 audit

### 5단계: 실패

- process, instance, zone과 region
- provider control plane
- dependency
- quota와 capacity
- duplicate와 timeout
- tenant isolation
- 비용 이상 증가

### 6단계: 검증 자료

- test
- metric
- trace
- audit
- restore 결과
- resource inventory
- 비용 자료

### 7단계: 종료

- export
- replacement
- cutover
- resource와 credential 삭제
- 계약 종료

## 9. 모호한 권장 사항을 시험 가능한 문장으로 바꿉니다

### Least privilege

```text
Function identity는 source object read와 result object create만 허용합니다.
다른 tenant prefix와 control plane action은 거부합니다.
Credential은 runtime이 발급하고 1시간 안에 만료됩니다.
허용과 거부 결과를 audit에서 확인합니다.
```

### Multi-AZ

```text
Application target은 zone A와 B에 나뉘어 있습니다.
Zone A target을 제외한 뒤 5분 안에 error rate가 목표 범위로 돌아옵니다.
Zone B의 남은 capacity가 peak traffic을 처리합니다.
Database failover 시간과 client reconnect를 측정합니다.
```

### Backup

```text
매일 backup을 만들고 30일 보존합니다.
매월 빈 환경에 restore합니다.
Checksum과 업무 불변식 다섯 개를 검사합니다.
측정한 RPO와 RTO를 기록합니다.
```

## 10. Decision record

선택마다 다음을 남깁니다.

```text
context
options
selected_option
reason
assumptions
evidence
cost_model
known_limits
security_and_tenant_impact
exit_cost
review_date
reversal_trigger
```

서비스와 workload는 바뀝니다. 결정도 영구 정답으로 취급하지 않고 정해진 조건에서 다시 검토합니다.

## 11. 선택을 보류할 조건

다음 항목이 없으면 production 선택을 보류할 수 있습니다.

- data 담당자
- identity와 network 접근 범위
- backup restore 결과
- 비용 담당자와 budget
- limit와 quota 확인
- provider 장애 대응 방법
- tenant negative test
- resource cleanup 방법
- version 지원 기간
- export와 종료 계획

## 12. Review 결과

```text
APPROVE
필요한 근거가 있고 잔여 위험을 수용합니다.

APPROVE_WITH_CONDITIONS
traffic, tenant, 기간이나 기능을 제한해 허용합니다.

DEFER
결정에 필요한 자료가 부족합니다.

REJECT
workload 요구와 서비스 동작이 맞지 않습니다.
```

조건에는 담당자, 기한, 확인 방법과 rollback 조건을 포함합니다.

## 최종 실습

[`local-cloud-model`](../exercises/local-cloud-model/README.md)을 이 순서로 다시 검토하십시오.

- 어떤 상태를 model이 보관합니까?
- 어떤 요청을 상태 변경 전에 거부합니까?
- 어떤 event가 한 번만 결과를 만듭니까?
- 삭제 뒤 무엇을 지우고 무엇을 남깁니까?
- `evidence_snapshot()`은 무엇을 확인하고 무엇은 확인하지 못합니까?
- 실제 provider에 옮길 때 IAM, network, persistence와 concurrency 중 무엇을 추가로 시험해야 합니까?

프로젝트 테스트가 모두 통과하고 위 질문에 구체적으로 답할 수 있으면 필수 과정을 완료한 것입니다.
