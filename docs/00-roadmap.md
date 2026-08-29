# 클라우드 컴퓨팅 학습 경로

## 과정의 목표

이 과정은 클라우드 제품 사용법이 아니라 다음 질문에 답하는 능력을 만듭니다.

- 어떤 상태를 사용자가 소유하고, 어떤 작업을 공급자가 수행합니까?
- 자원 생성 요청이 성공한 뒤 실제 서비스 준비 상태까지 무엇을 확인해야 합니까?
- 어떤 자원이 같은 원인으로 함께 실패합니까?
- 변경 권한과 업무 데이터 접근 권한은 어떻게 나뉩니까?
- 중복 event, timeout, quota 초과와 삭제 실패 뒤 무엇이 남습니까?
- 비용과 사용량을 어떤 업무 결과와 연결할 수 있습니까?
- 서비스를 바꾸거나 종료할 때 데이터와 설정을 실제로 회수할 수 있습니까?

필수 문서와 `local-cloud-model`만으로 완료할 수 있습니다. 외부 프로젝트나 유료 cloud account는 요구하지 않습니다.

## 대상 독자와 선행 지식

다음 조건을 만족하는 개발자를 대상으로 합니다.

- 작은 웹 또는 API 서비스를 실행해 본 경험이 있습니다.
- process, port, DNS, TLS, container, database, log와 backup을 구분할 수 있습니다.
- 장애가 발생했을 때 마지막 성공 지점과 첫 실패 지점을 찾아볼 수 있습니다.
- Git, Markdown, JSON과 Python 표준 라이브러리를 사용할 수 있습니다.

Kubernetes와 특정 공급자 경험은 필요하지 않습니다.

## 종료 역량

완료 후 다음을 설명하거나 재현할 수 있어야 합니다.

1. cloud characteristic, service model, execution model과 deployment model을 분리합니다.
2. desired state, provider control state, runtime state, durable business state와 evidence state를 구분합니다.
3. control plane, management data와 application data 접근 권한을 각각 검토합니다.
4. compute, network, storage, identity와 tenant의 생성·변경·삭제 순서를 정리합니다.
5. failure domain, 남은 처리 용량, RTO/RPO와 restore 결과를 판단합니다.
6. managed service의 version, maintenance, limit, backup과 export 책임을 확인합니다.
7. FaaS runtime 수명과 event ack, 외부 효과, retry와 dead letter를 연결합니다.
8. tenant context가 데이터, cache, queue, export와 삭제 작업에 계속 포함되는지 확인합니다.
9. account·identity·resource·tenant별 사고 범위와 점검 자료를 구분합니다.
10. 비용 단위, quota, headroom과 cleanup 결과를 판단합니다.
11. workload 요구를 바탕으로 IaaS, managed platform과 FaaS를 비교합니다.

## 필수 문서

### A. 판단 기준

- `01-cloud-state-responsibility-and-evidence.md`
- `02-cloud-characteristics-service-and-deployment-models.md`

먼저 상태, 작업 담당자와 확인 자료를 적는 습관을 만듭니다. IaaS/PaaS/SaaS, VM/container/FaaS, public/private/hybrid를 같은 축으로 나열하지 않는 것도 중요합니다.

### B. 권한과 상태 수명

- `03-control-plane-data-plane-and-identity.md`
- `04-iaas-compute-network-and-storage.md`
- `09-saas-tenancy-and-isolation.md`

자원을 바꾸는 권한, 애플리케이션 데이터를 읽는 권한과 tenant별 상태를 분리합니다. 이 세 문서를 읽으면 `local-cloud-model`의 tenant·document 부분을 이해할 수 있습니다.

### C. 장애와 managed execution

- `05-failure-domains-elasticity-and-recovery.md`
- `06-paas-and-managed-service-contracts.md`
- `07-serverless-and-faas-runtime.md`
- `08-event-delivery-concurrency-and-idempotency.md`

복제 수보다 함께 실패하는 원인을 찾고, 공급자가 숨긴 내부 상태를 외부 지표로 확인합니다. Event 처리에서는 effect와 ack가 서로 다른 시점이라는 점을 기준으로 retry를 설계합니다.

### D. 운영 판단과 최종 검토

- `11-cloud-security-observability-and-incidents.md`
- `12-cost-capacity-quotas-and-finops.md`
- `14-service-selection-and-architecture-review.md`

권한 변경, 장애, 비용과 복구 자료를 연결한 뒤 workload에 맞는 서비스를 선택합니다.

## 선택 문서

- `10-saas-entitlements-metering-and-billing.md`: SaaS 상품과 청구 상태를 구현할 때 읽습니다.
- `13-portability-lock-in-and-exit.md`: 실제 이전, cutover와 삭제 확인 절차가 필요할 때 읽습니다.
- `90-standards-map.md`: 공급자별 현재 제한, 가격과 API 동작을 확인할 때 사용합니다.

선택 문서를 읽지 않아도 필수 종료 역량은 충족할 수 있습니다.

## 구현 실습

### 프로젝트

`exercises/local-cloud-model/`

실제 cloud를 흉내 내는 emulator가 아닙니다. Cloud application이 지켜야 할 다음 상태 규칙을 작은 Python 모델로 고정합니다.

- private stateful resource
- tenant별 document ownership
- active-capacity quota
- tenant별 event identity
- 중복 event의 단일 효과
- 제한된 retry와 dead letter
- tenant 삭제 전파
- content-free evidence

### 구현 순서와 학습 시점

#### 1단계: 기본 상태를 먼저 확인합니다

```text
01 → 02 → 03 → 04 → 09
```

그다음 프로젝트의 다음 단계를 읽고 실행합니다.

| Implementation | 확인할 내용 |
|---:|---|
| 0 | Python package가 독립적으로 설치되는 범위 |
| 1 | 공개 예외와 event 데이터 |
| 2 | tenant, document, output, queue와 usage 저장 위치 |
| 3 | tenant 생성과 삭제 ID 재사용 거부 |
| 3-1 | ACTIVE tenant만 허용하는 공통 검사 |
| 4 | 다른 tenant의 문서 접근 거부와 quota 선검사 |

이 시점에 다음 테스트를 집중해서 확인합니다.

- private resource와 고유 ID
- 잘못된 tenant 전이의 원자적 거부
- 기존 문서 update가 active capacity를 추가로 쓰지 않음
- cross-tenant read/write 거부
- quota 초과 뒤 partial document가 남지 않음

#### 2단계: event 처리를 이어서 확인합니다

```text
05 → 06 → 07 → 08
```

그다음 다음 구현 단계를 확인합니다.

| Implementation | 확인할 내용 |
|---:|---|
| 5 | `(tenant_id, event_id)`로 event를 식별하고 payload 변경을 거부함 |
| 6 | 동일 event가 output과 usage를 한 번만 바꿈 |
| 6-1 | 실패 횟수를 기록하고 한도에서 dead letter로 이동함 |
| 6-2 | 처리 횟수 상한을 넘으면 남은 queue를 숨기지 않고 실패함 |

다음 실패를 직접 재현합니다.

- 같은 event 두 번 전달
- 같은 tenant에서 event ID를 다른 document에 재사용
- 없는 document 처리
- 다른 tenant 문서를 가리키는 event
- `max_attempts`와 `max_steps`의 최소값 위반

#### 3단계: 삭제와 점검 결과를 확인합니다

```text
11 → 12
```

그다음 마지막 구현 단계를 확인합니다.

| Implementation | 확인할 내용 |
|---:|---|
| 7 | tenant 삭제가 document, output, queue, dead letter와 resource에 전파됨 |
| 8 | 문서 내용을 제외하고 정렬된 새 객체를 반환함 |
| 9 | 공개 API만 사용해 앞선 불변식을 검증함 |

삭제한 tenant ID는 다시 사용할 수 없어야 합니다. 삭제 전 발생한 누적 usage와 `DELETED` 표시는 남기되, 활성 문서와 event는 남기지 않습니다.

#### 4단계: 최종 검토를 수행합니다

```text
14 → 전체 테스트
```

`docs/14-service-selection-and-architecture-review.md`의 순서대로 `local-cloud-model`을 검토합니다.

- 어떤 상태가 정본입니까?
- 어떤 변경이 원자적으로 거부됩니까?
- 어떤 identity가 어떤 tenant를 대상으로 동작합니까?
- 어떤 failure를 이 모델이 재현합니까?
- 어떤 근거를 반환하며, 무엇은 확인하지 못합니까?
- 실제 provider에 옮기면 어떤 IAM, network, persistence와 concurrency 검사가 추가로 필요합니까?

## 실행 명령

```sh
cd exercises/local-cloud-model
python3 -m unittest discover -s tests -v
python3 -m compileall -q local_cloud_model tests
```

설치 상태도 확인하려면 다음 명령을 사용합니다.

```sh
python3 -m pip install . --no-deps --no-build-isolation
```

## 선택 자료를 읽는 시점

```text
SaaS plan·subscription·invoice 구현
→ 10

대규모 export·provider 교체·cutover
→ 13

공급자별 timeout·quota·price·API 확인
→ 90
```

## 완료 기준

다음을 모두 만족해야 합니다.

- 필수 문서의 핵심 질문에 제품명 대신 자원, 상태, 작업과 실패 결과로 답할 수 있습니다.
- `local-cloud-model`의 각 Implementation 단계가 어떤 잘못된 구현을 막는지 설명할 수 있습니다.
- 프로젝트 테스트가 모두 통과합니다.
- cross-tenant 접근, quota 초과, duplicate event, retry 한도와 tenant 삭제를 직접 재현합니다.
- 반환된 evidence가 문서 내용을 포함하지 않고, 호출자가 수정해도 내부 상태가 바뀌지 않는 이유를 설명합니다.
- 이 모델이 실제 IAM, network, database transaction, process crash와 concurrent writer를 검증하지 못한다는 점을 구분합니다.

이 기준을 충족하면 클라우드의 기본 판단 틀을 다시 처음부터 공부하지 않고, 실제 문제에 맞춰 공급자별 세부 기능을 추가로 학습할 수 있습니다.
