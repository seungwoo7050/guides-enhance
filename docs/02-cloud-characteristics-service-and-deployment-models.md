# 클라우드 특성, 서비스 모델과 배포 방식

클라우드 용어는 서로 다른 분류 기준을 한 줄에 섞을 때 혼란이 생깁니다.

```text
IaaS·PaaS·SaaS        사용자가 어떤 기능을 서비스로 소비하는가
VM·container·FaaS     workload가 어떤 단위로 실행되는가
public·private·hybrid 어느 조직과 환경에 배치되는가
managed·serverless    어떤 운영 작업을 공급자가 대신 수행하는가
```

이 문서는 각 기준을 나눠 본 뒤 실제 서비스 선택에 다시 연결합니다.

## 1. 클라우드의 공통 특성

NIST SP 800-145는 클라우드 컴퓨팅을 다섯 가지 공통 특성으로 설명합니다.

### 1.1 On-demand self-service

사용자가 사람의 개별 승인을 기다리지 않고 API, portal이나 automation으로 resource를 만들고 지울 수 있습니다.

편리함과 함께 다음 관리 항목이 생깁니다.

- 누가 생성 권한을 가집니까?
- quota와 허용 규칙은 어디서 검사합니까?
- owner와 만료 시각을 어떻게 기록합니까?
- 잘못 만든 resource를 누가 찾아 지웁니까?

### 1.2 Broad network access

표준 network 방식으로 여러 client가 접근할 수 있다는 뜻입니다. 인터넷에 공개돼야 한다는 뜻은 아닙니다. Private endpoint, VPN과 service network도 포함될 수 있습니다.

### 1.3 Resource pooling

공급자가 공유 자원 풀에서 compute, storage와 network capacity를 할당합니다. 사용자는 정확한 물리 장비를 고르지 않는 대신 논리적 격리와 공급자 운영을 신뢰합니다.

이 특성은 noisy neighbor, 격리 오류, 지역 capacity 부족과 물리 위치 통제 문제를 만듭니다.

### 1.4 Rapid elasticity

수요에 따라 resource를 빠르게 늘리거나 줄일 수 있습니다. 즉시 무한대로 확장된다는 뜻은 아닙니다.

- quota
- provisioning 시간
- warm-up
- stateful bottleneck
- 지역 capacity
- 잘못된 scaling metric
- 비용 상한

이 제약은 항상 남습니다.

### 1.5 Measured service

사용량을 측정하고 보고합니다. 측정 단위는 request, 실행 시간, byte-month, I/O, provisioned capacity와 data transfer처럼 서비스마다 다릅니다.

사용량을 측정할 수 있어야 비용을 배분할 수 있지만, 잘못된 tag와 늦게 도착한 billing data도 함께 처리해야 합니다.

## 2. IaaS

IaaS에서는 사용자가 compute, network와 storage를 조합하고 그 위의 OS, runtime, application과 data를 비교적 많이 관리합니다.

사용자가 보통 관리하는 항목:

- image와 OS 설정
- network 분리와 route
- attached storage와 filesystem
- workload runtime
- application과 data
- patch 적용 시점과 host 수준 monitoring 일부

공급자가 보통 관리하는 항목:

- 물리 시설과 hardware
- hypervisor 또는 underlying host
- 핵심 control plane
- 물리 network와 storage fabric

IaaS는 제어 범위가 넓지만 patch, hardening, capacity와 recovery 작업도 많이 남습니다.

## 3. PaaS와 managed platform

PaaS는 application을 배포하고 실행하는 기능을 제공합니다. 사용자는 OS와 runtime 관리 일부를 공급자에게 맡기고 application과 data에 집중합니다.

제품 이름보다 다음 질문이 중요합니다.

- runtime version은 누가 선택하고 언제 지원을 끝냅니까?
- patch는 자동입니까, maintenance window를 고를 수 있습니까?
- 확장 단위는 instance, request, throughput 중 무엇입니까?
- network와 identity를 어디까지 설정할 수 있습니까?
- backup을 누가 만들고 restore 결과를 누가 확인합니까?
- extension, custom binary나 privileged operation을 쓸 수 있습니까?

Managed database, queue와 object service도 숨기는 작업과 남기는 작업이 서로 다릅니다.

## 4. SaaS

SaaS 사용자는 완성된 application 기능을 사용합니다. 공급자는 application, runtime, platform과 infrastructure 운영을 담당합니다.

그래도 고객에게 다음 작업은 남습니다.

- account와 identity 관리
- organization, role과 공유 설정
- data 분류와 입력 적법성
- export, 보존과 삭제 요청
- integration token과 API 사용
- audit와 compliance 설정
- client device 보안

SaaS를 만드는 개발자는 tenant lifecycle, data isolation, entitlement, usage, support, export와 deletion을 직접 구현해야 합니다.

## 5. FaaS는 실행 방식입니다

FaaS는 function invocation을 실행 단위로 사용하는 serverless compute 형태입니다. 일반적으로 PaaS 계열의 managed execution 기능으로 볼 수 있지만, IaaS·PaaS·SaaS와 같은 분류 줄에 단순히 네 번째 항목으로 놓으면 기준이 섞입니다.

확인할 항목은 다음과 같습니다.

- invocation 단위
- 실행 환경 수명
- timeout과 memory limit
- concurrency와 scale 방식
- event source의 전달 방식
- retry와 duplicate
- cold start와 warm reuse
- local state 보존 여부
- 관측 자료와 과금 단위

## 6. VM, container와 CaaS

VM과 container는 실행과 격리 단위입니다. VM을 IaaS에서 직접 관리할 수도 있고, container를 managed platform에서 실행할 수도 있습니다.

CaaS라는 이름도 공급자마다 뜻이 다를 수 있으므로 다음을 확인합니다.

- cluster와 node를 누가 관리합니까?
- scheduler와 network rule을 누가 설정합니까?
- image와 runtime patch는 누가 적용합니까?
- workload identity와 secret을 어떻게 전달합니까?
- scaling과 node 교체를 어떤 controller가 수행합니까?

## 7. 배포 방식

### Public cloud

공급자가 여러 고객에게 cloud 기능을 제공합니다. Public network에 공개된다는 뜻과는 다릅니다. Public cloud에서도 private network와 private endpoint를 사용할 수 있습니다.

### Private cloud

한 조직을 위해 cloud 특성을 제공하는 환경입니다. 사내 virtualization cluster만 있다고 private cloud가 되는 것은 아닙니다. Self-service, pooling, elasticity와 measured service가 실제로 제공되는지 확인해야 합니다.

### Community cloud

공통 규제나 업무 요구를 가진 조직 집단을 위한 환경입니다. 사용 빈도는 낮지만 산업 공동 요구를 설명할 때 사용합니다.

### Hybrid cloud

서로 다른 cloud나 기존 환경을 연결합니다. 두 환경을 동시에 사용한다는 사실만으로 운영 가능한 hybrid architecture가 되지는 않습니다.

다음 항목을 정해야 합니다.

- identity federation
- network 연결
- data 정본과 동기화 방식
- 배포 순서
- 장애가 서로 독립적인지
- log와 trace를 연결하는 방법
- 한쪽 환경이 실패했을 때의 동작과 종료 절차

## 8. Cloud-native는 서비스 모델이 아닙니다

`cloud-native`는 보통 자동화, 변경 가능한 resource의 교체, 분산 실행, managed service와 observability를 활용하는 설계 방식을 뜻합니다. 정확한 제품 분류는 아닙니다.

다음처럼 구체적으로 물어야 합니다.

- 어떤 변경과 장애를 더 빠르게 처리합니까?
- 어떤 새 dependency와 운영 작업이 생깁니까?
- 비용과 공급자 의존성이 얼마나 늘어납니까?
- 현재 팀이 이를 검증하고 운영할 수 있습니까?

## 9. 서비스 분류 순서

새 서비스를 검토할 때 다음 순서로 적습니다.

1. 사용자가 실제로 얻는 기능을 적습니다.
2. 사용자가 직접 바꿀 수 있는 resource와 설정을 적습니다.
3. 공급자가 patch, scale과 recovery를 수행하는 범위를 적습니다.
4. data, identity, availability와 비용에 대해 사용자에게 남는 작업을 적습니다.
5. 실행 단위를 VM, container, function이나 완성 application으로 구분합니다.
6. public, private와 hybrid 배치 방식을 적습니다.
7. 가장 가까운 service model과 예외를 기록합니다.

## 10. 자주 틀리는 분류

| 표현 | 빠진 판단 | 다시 물을 질문 |
|---|---|---|
| VM이므로 cloud입니다 | virtualization과 cloud characteristic을 섞었습니다 | self-service, pooling, elasticity와 metering이 있습니까? |
| FaaS이므로 SaaS입니다 | 실행 방식과 완성 application을 섞었습니다 | 사용자가 function code를 소유합니까? |
| managed DB이므로 운영할 일이 없습니다 | engine 운영과 data 운영을 섞었습니다 | schema, query, access와 restore 결과는 누가 확인합니까? |
| SaaS이므로 multi-tenant입니다 | 판매 방식과 자원 공유 방식을 섞었습니다 | tenant를 무엇으로 정의하고 어떤 resource를 공유합니까? |
| serverless이므로 무한히 확장됩니다 | 관리 방식과 실제 limit를 섞었습니다 | concurrency, quota와 downstream capacity는 얼마입니까? |

## 다음 단계

서비스 분류를 마치면 [`03-control-plane-data-plane-and-identity.md`](03-control-plane-data-plane-and-identity.md)에서 누가 어떤 자원을 바꾸고 데이터를 읽을 수 있는지 확인하십시오.
