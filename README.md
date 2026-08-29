# 클라우드 컴퓨팅 기초

이 저장소는 특정 공급자의 제품명이나 콘솔 사용법을 외우는 과정이 아닙니다. 클라우드 자원의 상태, 변경 권한, 장애 범위, 비용, 데이터 수명과 삭제 결과를 근거로 서비스를 판단하는 방법을 다룹니다.

문서와 `local-cloud-model`을 함께 완료하면 외부 프로젝트 없이도 이 학습 범위의 핵심 개념과 구현 확인을 끝낼 수 있습니다. 이후 공급자별 서비스, 대규모 SaaS 운영, 플랫폼 엔지니어링은 실제 업무가 필요할 때 이어서 학습합니다.

처음에는 [`docs/00-roadmap.md`](docs/00-roadmap.md)를 읽으십시오. 필수 문서, 구현 시점과 완료 기준을 한곳에서 확인할 수 있습니다.

## 선행 지식

다음 내용을 알고 있어야 합니다.

- Linux에서 프로세스가 실행되고 포트를 여는 과정을 설명할 수 있습니다.
- DNS, TLS, 애플리케이션, 데이터베이스, 로그와 백업의 역할을 구분할 수 있습니다.
- Git, Markdown, JSON과 Python 표준 라이브러리를 사용할 수 있습니다.
- 장애가 발생했을 때 마지막으로 성공한 작업과 처음 실패한 작업을 나눠 확인할 수 있습니다.

클라우드 계정, 신용카드, Kubernetes 경험은 필요하지 않습니다. 필수 실습은 외부 네트워크나 유료 자원을 사용하지 않습니다.

## 완료 후 남아야 할 능력

이 저장소를 마치면 다음 작업을 수행할 수 있어야 합니다.

- IaaS, PaaS, SaaS와 VM, container, FaaS를 서로 다른 분류 기준으로 설명합니다.
- 원하는 상태, 공급자가 관리하는 상태, 실행 중 상태, 보존해야 할 업무 데이터와 점검 근거를 구분합니다.
- 자원을 생성하거나 바꾸는 control plane 권한과 사용자 데이터를 처리하는 data plane 권한을 따로 검토합니다.
- compute, network, storage와 identity의 수명과 의존 관계를 inventory로 정리합니다.
- replica 수만 세지 않고 같은 원인으로 함께 실패하는 자원을 찾습니다.
- availability와 durability, RTO와 RPO, 복제와 백업, 자동 확장과 남은 처리 용량을 구분합니다.
- managed service가 대신 수행하는 작업과 사용자가 계속 확인해야 하는 작업을 구분합니다.
- FaaS 실행 환경의 수명, timeout, concurrency와 event 재전달을 고려합니다.
- 중복 event가 결과와 사용량을 한 번만 바꾸도록 만들고, 실패 횟수와 dead letter 상태를 보존합니다.
- tenant ID가 요청, 데이터, cache, job, export와 삭제 작업 전체에서 빠지지 않는지 확인합니다.
- cloud identity, 자원 공개 여부, 로그, 사고 범위와 복구 근거를 연결합니다.
- 고정 비용, 사용량 비용, 단계적으로 증가하는 비용, quota와 정리되지 않은 자원을 구분합니다.
- workload의 상태, 장애, 비용과 운영 능력을 기준으로 IaaS, managed platform과 FaaS를 비교합니다.

## 필수 문서

### 1. 판단 기준

1. [`01-cloud-state-responsibility-and-evidence.md`](docs/01-cloud-state-responsibility-and-evidence.md)
2. [`02-cloud-characteristics-service-and-deployment-models.md`](docs/02-cloud-characteristics-service-and-deployment-models.md)

클라우드라는 이름보다 실제 상태, 작업 담당자와 확인 가능한 근거를 먼저 적습니다. 서비스 모델, 실행 단위와 배포 방식을 섞지 않는 기준도 여기서 정리합니다.

### 2. 권한과 자원 수명

3. [`03-control-plane-data-plane-and-identity.md`](docs/03-control-plane-data-plane-and-identity.md)
4. [`04-iaas-compute-network-and-storage.md`](docs/04-iaas-compute-network-and-storage.md)
5. [`09-saas-tenancy-and-isolation.md`](docs/09-saas-tenancy-and-isolation.md)

자원을 바꾸는 권한과 데이터를 읽는 권한을 나눠 보고, compute·network·storage와 tenant 상태가 언제 만들어지고 없어지는지 확인합니다.

### 3. 장애와 관리형 실행

6. [`05-failure-domains-elasticity-and-recovery.md`](docs/05-failure-domains-elasticity-and-recovery.md)
7. [`06-paas-and-managed-service-contracts.md`](docs/06-paas-and-managed-service-contracts.md)
8. [`07-serverless-and-faas-runtime.md`](docs/07-serverless-and-faas-runtime.md)
9. [`08-event-delivery-concurrency-and-idempotency.md`](docs/08-event-delivery-concurrency-and-idempotency.md)

한 자원이 사라졌을 때 함께 멈추는 대상을 찾고, managed service와 FaaS가 숨기는 작업과 남기는 실패 조건을 확인합니다.

### 4. 운영 판단

10. [`11-cloud-security-observability-and-incidents.md`](docs/11-cloud-security-observability-and-incidents.md)
11. [`12-cost-capacity-quotas-and-finops.md`](docs/12-cost-capacity-quotas-and-finops.md)
12. [`14-service-selection-and-architecture-review.md`](docs/14-service-selection-and-architecture-review.md)

권한 변경, 데이터 접근, 비용 증가와 장애 대응을 같은 자원 식별자와 시간 기준으로 연결한 뒤 서비스 선택을 검토합니다.

## 선택 자료

다음 문서는 필수 경로에서 제외합니다. 실제 업무에서 해당 문제가 생겼을 때 사용하십시오.

- [`10-saas-entitlements-metering-and-billing.md`](docs/10-saas-entitlements-metering-and-billing.md): plan, subscription, entitlement, usage와 billing을 구현하는 SaaS 제품 심화 자료입니다.
- [`13-portability-lock-in-and-exit.md`](docs/13-portability-lock-in-and-exit.md): 실제 export, import, cutover와 공급자 교체 연습이 필요할 때 사용합니다.
- [`90-standards-map.md`](docs/90-standards-map.md): 표준과 공급자별 최신 제한 사항을 공식 문서에서 다시 확인할 때 사용합니다.

## 구현 실습

필수 실습은 [`exercises/local-cloud-model`](exercises/local-cloud-model/README.md) 하나입니다.

이 프로젝트는 다음 동작을 코드와 테스트로 확인합니다.

- tenant별 문서와 상태 자원 분리
- active document 수를 기준으로 한 quota 검사
- 다른 tenant의 문서 읽기와 덮어쓰기 거부
- `(tenant_id, event_id)` 단위 event 식별
- 중복 event의 단일 결과와 단일 사용량 반영
- 제한된 재시도와 dead letter 이동
- 삭제한 tenant의 문서, 결과, queue와 자원 정리
- 문서 본문을 노출하지 않는 결정적 점검 결과

실습을 마지막에 한 번에 시작하지 않습니다. 자원과 tenant 상태를 읽은 뒤 기본 모델을 구현하고, event 문서를 읽은 뒤 처리 부분을 이어서 확인합니다. 자세한 순서는 roadmap에 있습니다.

## 권장 순서

```text
01~04, 09
→ local-cloud-model의 tenant·document 부분 확인
→ 05~08
→ local-cloud-model의 event 처리 부분 확인
→ 11~12
→ local-cloud-model의 삭제·evidence·test 확인
→ 14
→ 전체 테스트 실행
```

선택 문서 `10`, `13`, `90`은 필수 과정이 끝난 뒤 필요한 것만 읽습니다.

## 실행과 검증

```sh
cd exercises/local-cloud-model
python3 -m unittest discover -s tests -v
python3 -m compileall -q local_cloud_model tests
```

Python 3.10 이상이 필요합니다. 외부 runtime dependency는 없습니다.

## 완료 기준

다음을 모두 만족하면 이 저장소의 필수 과정을 완료한 것으로 봅니다.

- 필수 문서 12개의 검토 질문에 구체적인 자원, 상태와 실패 결과를 사용해 답할 수 있습니다.
- `local-cloud-model`의 Implementation Order를 따라 각 상태가 왜 필요한지 설명할 수 있습니다.
- 프로젝트 테스트가 모두 통과합니다.
- 다른 tenant의 문서 접근, quota 초과, 중복 event, 재시도 한도와 tenant 삭제를 직접 재현할 수 있습니다.
- `docs/14-service-selection-and-architecture-review.md`의 순서로 모델을 다시 검토하고, 이 구현이 실제 cloud provider에서 검증하지 못하는 항목을 구분할 수 있습니다.

완료는 특정 공급자의 전문가가 되었다는 뜻이 아닙니다. 처음 보는 cloud architecture에서 누가 무엇을 바꾸고, 무엇이 남으며, 어디까지 함께 실패하고, 어떤 근거로 확인해야 하는지를 스스로 정리할 수 있다는 뜻입니다.
