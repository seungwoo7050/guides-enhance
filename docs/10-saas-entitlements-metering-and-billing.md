# Entitlement, metering와 billing

이 문서는 필수 경로가 아닌 SaaS 제품 심화 자료입니다. 상품, 사용 권한, quota, 사용량과 청구 상태를 구현할 때 읽으십시오.

다음 개념은 서로 다른 상태입니다.

```text
plan
판매하는 상품의 기능과 가격 정의

subscription
tenant가 선택한 계약과 결제 상태

entitlement
현재 tenant가 사용할 수 있는 기능

quota
허용한 수량, 속도 또는 동시 실행 수

metering
실제로 발생한 사용량 기록

billing
가격 규칙을 적용해 invoice와 결제 상태를 만드는 작업
```

이를 `is_paid` 하나로 합치면 trial, upgrade, downgrade, grace period, overage와 partial provisioning을 설명하기 어렵습니다.

## 1. Plan

Plan은 이름이 아니라 version이 있는 상품 정의입니다.

```text
plan_id
version
currency
billing_period
base_price
included_usage
feature_set
limits
overage_rule
effective_from
retired_at
```

Plan을 바꿀 때 기존 subscription에 새 규칙을 적용할지, 이전 version을 계속 유지할지 정합니다.

## 2. Subscription 상태

대표 상태:

```text
TRIAL
→ ACTIVE
→ PAST_DUE
→ GRACE
→ SUSPENDED
→ CANCELED
→ ENDED
```

외부 payment provider의 상태와 내부 서비스 상태가 항상 같지는 않습니다. Webhook이 늦거나 중복으로 오고, 순서가 바뀔 수 있기 때문입니다.

Subscription 변경은 여러 작업을 일으킵니다.

- entitlement 변경
- quota 변경
- invoice 또는 proration
- 필요한 resource provisioning
- 알림
- audit 기록

일부만 성공하면 현재 상태를 다시 읽고 누락된 작업을 보정하는 reconciliation이 필요합니다.

## 3. Entitlement

Entitlement는 특정 tenant가 지금 기능을 사용할 수 있는지 결정합니다.

입력 예:

- tenant
- plan version
- add-on
- 계약별 예외
- rollout flag
- region 또는 compliance 제한
- subscription 상태

판정은 server에서 수행합니다. UI에서 버튼을 숨기는 것은 authorization이 아닙니다.

판정 자료:

```text
tenant_id
feature
allowed
source_plan_or_override
version
evaluated_at
expires_at
```

## 4. Quota 종류

- storage bytes
- project 수
- 월간 처리 문서 수
- concurrent job 수
- API request rate
- user seat 수

### Hard quota

초과 요청을 거부합니다. 거부하기 전에 resource나 usage를 일부만 만들면 안 됩니다.

### Soft quota

초과를 허용하고 alert나 overage billing을 만듭니다.

### Burst quota

짧은 burst를 허용하고 더 긴 구간의 평균을 제한합니다.

### Concurrency quota

현재 실행 중인 작업 수를 제한합니다. 여러 process나 region에서 처리한다면 atomic counter, lease나 partitioned token이 필요합니다.

## 5. Quota 검사는 먼저 확정해야 합니다

다음 순서는 concurrent 요청에서 한도를 넘길 수 있습니다.

```text
usage 읽기
→ limit 비교
→ resource 생성
→ usage 증가
```

대신 다음 방법을 사용합니다.

- database constraint
- conditional update
- reservation
- token bucket
- transaction
- idempotent usage record

Resource 생성이 실패하면 reservation을 해제하거나 만료시켜야 합니다.

## 6. Metering event

사용량 event에는 다음 값이 필요합니다.

```text
event_id
tenant_id
metric
quantity
unit
occurred_at
source
resource_id
idempotency_key
schema_version
```

지켜야 할 조건:

- 같은 event를 여러 번 받아도 한 번만 집계합니다.
- 사용량이 정확히 한 tenant에 속한다는 근거가 있습니다.
- 늦게 도착한 event와 correction을 처리합니다.
- 감소 조정과 refund를 원본 event에 연결합니다.
- raw event와 aggregate의 보존 기간을 따로 정합니다.

## 7. 측정과 가격 적용을 분리합니다

```text
문서 1,000 page를 처리했습니다.
```

이는 measurement입니다.

```text
포함량 500 page
+ 초과량 500 × unit price
+ discount
+ tax
```

이는 billing입니다.

가격이 바뀌어도 과거 raw usage를 다시 계산할 수 있어야 합니다. Aggregate만 남기면 분쟁을 설명하기 어려울 수 있습니다.

## 8. 외부 billing provider

외부 서비스가 payment method, charge와 invoice 전달을 맡더라도 내부 entitlement의 정본이 되는 것은 아닐 수 있습니다.

대표 문제:

- webhook duplicate
- 순서가 바뀐 상태 event
- API timeout 뒤 charge 결과 불명확
- charge 성공 뒤 entitlement 변경 실패
- refund 뒤 내부 usage 상태 불일치
- provider customer와 tenant mapping 오류

필요한 상태:

- 외부 object ID
- 내부 tenant와 subscription ID
- 처리한 webhook ID
- reconciliation job
- 수동 수정 사유와 audit

## 9. Upgrade와 downgrade

### Upgrade

- 기능을 즉시 열지
- quota를 초기화하거나 유지할지
- 새 resource를 먼저 만들지
- proration을 어떻게 계산할지
- provisioning 실패 시 무엇을 되돌릴지

### Downgrade

현재 사용량이 새 limit를 넘을 수 있습니다.

가능한 처리:

- 새 생성만 막습니다.
- grace period를 둡니다.
- 오래된 데이터를 archive합니다.
- 사용자 데이터를 자동 삭제하지 않습니다.
- 다음 billing period부터 적용합니다.

## 10. Trial과 abuse

Trial은 상품 상태이면서 abuse 대상입니다.

- 중복 account
- resource mining
- invitation abuse
- payment verification
- trial 종료 뒤 data 보존
- export 권리

Trial이 만든 resource, quota 사용량과 삭제 시점을 명시해야 합니다.

## 11. Provider 비용과 SaaS usage는 다릅니다

Provider bill에는 shared database, function, storage, egress, support와 외부 API 비용이 섞입니다. Tenant별 원가를 계산하려면 이런 비용을 사용량 지표에 따라 배분해야 합니다.

완벽한 정확성보다 일관된 배분 규칙과 version을 남기는 편이 중요합니다.

## 12. 분쟁에 대비합니다

고객이 usage나 invoice에 이의를 제기하면 다음을 재구성할 수 있어야 합니다.

- 집계한 raw event
- 제거한 duplicate
- 적용한 plan과 가격 version
- 수동 adjustment
- 시간대와 billing period
- correction invoice와 원본 invoice의 관계

## 필수 경로와의 관계

[`local-cloud-model`](../exercises/local-cloud-model/README.md)은 active document capacity와 event별 usage만 다룹니다. Subscription, invoice, payment와 월간 usage는 구현하지 않습니다. 실제 SaaS 제품에서 이 문서의 상태를 추가하더라도 tenant isolation과 event idempotency는 그대로 유지해야 합니다.
