# 표준과 공식 자료 지도

이 문서는 필수 학습 문서가 아니라 확인 자료입니다. 본문은 공급자와 무관한 판단 기준을 다루고, 서비스별 timeout, quota, retry 기본값, 가격과 지원 version은 공식 문서에서 다시 확인합니다.

이 파일에 기록된 링크 확인 기준일은 **2026-08-09**입니다. 실제 설계에 사용할 때는 확인 날짜, region, account 유형과 CLI/SDK version을 새로 기록하십시오.

## 1. 클라우드 정의와 서비스 모델

### NIST SP 800-145 — The NIST Definition of Cloud Computing

- https://csrc.nist.gov/pubs/sp/800/145/final
- On-demand self-service, broad network access, resource pooling, rapid elasticity와 measured service를 정의합니다.
- IaaS, PaaS, SaaS와 public, private, community, hybrid deployment model을 구분하는 기준으로 사용합니다.

### NIST SP 500-322 — Evaluation of Cloud Computing Services Based on NIST SP 800-145

- https://www.nist.gov/publications/evaluation-cloud-computing-services-based-nist-sp-800-145
- 주어진 기능이 cloud service의 공통 특성을 실제로 제공하는지 평가할 때 참고합니다.

FaaS는 위 세 service model과 같은 분류 줄에 단순히 추가하지 않고, managed execution과 event 처리 방식으로 따로 검토합니다.

## 2. Cloud access control

### NIST SP 800-210 — General Access Control Guidance for Cloud Systems

- https://csrc.nist.gov/pubs/sp/800/210/final
- IaaS, PaaS와 SaaS에서 접근 대상과 공급자·사용자 작업이 어떻게 달라지는지 확인할 때 사용합니다.

## 3. Serverless와 event source

Event 전달 방식은 공급자뿐 아니라 source 종류에 따라서도 다릅니다. 다음 문서는 구체적인 확인 항목을 찾는 예입니다.

### AWS Lambda event source mapping API

- https://docs.aws.amazon.com/lambda/latest/api/API_CreateEventSourceMapping.html
- Batch, retry, record age, concurrency와 failure destination 설정을 확인합니다.

### AWS Lambda와 Amazon MQ

- https://docs.aws.amazon.com/lambda/latest/dg/with-mq.html
- At-least-once 처리, duplicate 가능성과 source별 concurrency 제한을 확인하는 예입니다.

### AWS Lambda Kafka retry configuration

- https://docs.aws.amazon.com/lambda/latest/dg/kafka-retry-configurations.html
- Retry 한도, failure destination와 batch 실패 동작을 확인합니다.

AWS 사용을 권장하거나 필수로 정하는 자료가 아닙니다. Generic 용어만으로는 ack, batch와 retry 결과를 확정할 수 없으므로 선택한 source의 공식 문서를 읽어야 한다는 예입니다.

## 4. Multitenancy

### Azure Architecture Center — Tenancy models

- https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/tenancy-models
- 모든 자원을 공유하는 방식과 tenant별로 분리하는 방식 사이의 선택지를 검토할 때 사용합니다.

### Azure Architecture Center — Multitenant solution architecture

- https://learn.microsoft.com/en-us/azure/architecture/guide/saas-multitenant-solution-architecture/
- SaaS 판매 방식과 실제 resource 공유 방식이 같지 않을 수 있음을 확인합니다.

특정 Azure service 구성을 그대로 정답으로 사용하지 말고, tenant isolation을 component별로 비교하는 참고 자료로 사용합니다.

## 5. FinOps

### FinOps Framework

- https://www.finops.org/framework/
- Engineering, finance와 product가 cloud 사용량과 업무 가치를 함께 관리하는 운영 방식을 확인합니다.

가격과 할인은 자주 바뀝니다. 고정 숫자를 가이드의 정답으로 두지 말고, provider calculator와 실제 billing export의 확인 날짜를 기록합니다.

## 6. 공급자 architecture framework

실제 provider를 선택했다면 다음 공식 framework에서 검토 질문과 관련 기능을 찾을 수 있습니다.

- AWS Well-Architected Framework: https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html
- Microsoft Azure Well-Architected Framework: https://learn.microsoft.com/azure/well-architected/
- Google Cloud Architecture Framework: https://cloud.google.com/architecture/framework

Framework는 질문 목록을 제공할 뿐입니다. Resource 상태, 담당 작업, failure injection, restore와 비용 자료를 직접 확인해야 합니다.

## 7. 바뀌기 쉬운 정보

다음 항목은 문서 작성 뒤 달라질 가능성이 큽니다.

- service 이름
- region 지원 여부
- runtime version
- timeout, payload와 concurrency limit
- retry 기본값
- SLA
- 가격과 free tier
- 지원 종료 일정
- API field

Provider별 조사 기록에는 다음 값을 남깁니다.

```text
provider
service
document_url
checked_at
region
account_type
cli_or_sdk_version
observed_behavior
```

본문의 일반 설명과 실제 공식 문서나 시험 결과가 다르면 실제 service contract와 관찰 결과를 우선하고 관련 문서를 갱신합니다.

## 8. 읽는 순서

```text
NIST 정의
→ 필요한 service model 분류
→ 선택한 provider의 architecture framework
→ 실제 service API, limit와 delivery 문서
→ 작은 시험 결과
→ responsibility, failure, cost와 exit 기록 갱신
```

링크가 열리는지만 확인해서는 내용의 정확성, region별 지원, 가격과 실제 동작을 증명할 수 없습니다.
