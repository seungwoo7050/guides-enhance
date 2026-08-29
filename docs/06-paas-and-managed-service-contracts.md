# PaaS와 managed service의 사용 조건

Managed service는 운영을 없애지 않습니다. Host와 engine 관리 같은 일부 작업을 공급자에게 맡기고, 사용자는 설정, 데이터, 호환성, 비용과 종료 준비를 계속 관리합니다.

“누가 patch합니까?”만 묻지 말고 서비스가 제공하는 기능, 제한, 실패 결과와 확인 방법을 함께 적어야 합니다.

## 1. Managed라는 말을 작업별로 나눕니다

Managed database를 예로 들면 공급자는 다음 작업을 수행할 수 있습니다.

- host와 storage 장비 유지
- engine 설치
- 일부 patch 적용
- replica 배치와 failover
- 기본 metric 제공
- 자동 backup artifact 생성

사용자에게 남는 작업:

- schema와 query 설계
- transaction에서 지켜야 할 조건
- connection pool 설정
- data와 resource 접근 권한
- backup 보존 기간과 restore 시험
- maintenance window 선택
- driver, extension과 version 호환성
- capacity와 quota 관리
- data 분류
- export, migration과 삭제 확인

제품 소개 문구보다 실제 작업과 결과를 기준으로 나눕니다.

## 2. 서비스 검토표

새 managed service를 선택할 때 최소한 다음 항목을 기록합니다.

```text
제공 기능
사용자가 바꿀 수 있는 설정
데이터 모델
identity와 network 접근 방식
availability가 적용되는 범위
consistency 또는 delivery 의미
limit와 quota
maintenance와 version 지원 기간
backup과 restore 방법
metric, log와 audit
export와 deletion
과금 단위
support와 incident 문의 방법
```

공식 문서에 없는 항목은 임의로 추정하지 않고 `unknown`으로 남깁니다. 필요하면 작은 시험이나 support 문의로 확인합니다.

## 3. 숨겨진 내부 상태가 있습니다

Managed service가 node와 process를 숨겨도 내부 상태가 사라지는 것은 아닙니다.

- replica lag
- storage compaction
- queue partition
- runtime pool
- background maintenance
- index build
- cache warming
- connection proxy
- failover 진행 상태
- quota accounting

사용자는 내부 구조를 직접 보지 못할 수 있으므로 client latency, error, queue age와 service metric으로 이상을 찾아야 합니다.

## 4. Version과 maintenance

다음 질문에 답해야 합니다.

- runtime 또는 engine version을 누가 선택합니까?
- 자동 upgrade와 사용자가 승인하는 upgrade가 어떻게 다릅니까?
- 지원 종료 일정은 언제 어떻게 통지됩니까?
- maintenance 중 connection과 request는 어떻게 처리됩니까?
- extension, driver와 protocol 호환성을 누가 시험합니까?
- 문제가 생겼을 때 이전 version으로 돌아갈 수 있습니까?
- data migration이 되돌릴 수 없는 작업입니까?

Managed service는 patch 작업을 줄이는 대신 강제 upgrade와 지원 종료라는 새 사건을 만듭니다.

## 5. Availability 주장을 분해합니다

SLA는 보상 조건일 수 있으며 application recovery를 대신하지 않습니다.

- multi-zone 기능이 어떤 resource와 operation에 적용됩니까?
- control plane이 멈춘 동안 data plane은 계속 동작합니까?
- failover 때 DNS, connection과 transaction은 어떻게 됩니까?
- client가 retry할 때 중복 write가 생길 수 있습니까?
- maintenance와 잘못된 설정은 SLA에서 제외됩니까?

공급자 기능과 application의 실제 복구 결과를 따로 확인합니다.

## 6. Backup과 restore

`automated backup enabled`만 확인하면 부족합니다.

- snapshot 주기
- point-in-time recovery 범위
- 보존 기간
- 다른 account 또는 region으로 복사할 수 있는지
- encryption key dependency
- logical corruption을 되돌릴 수 있는지
- 서비스를 삭제한 뒤 backup이 얼마나 남는지
- restore 대상의 network와 identity
- restore 뒤 schema, row 수와 업무 불변식 결과

공급자가 backup artifact를 만들어도 restore를 실행하고 결과를 확인하는 일은 사용자에게 남습니다.

## 7. Network와 identity

Managed endpoint가 public인지 private인지, private endpoint가 DNS와 route에 무엇을 요구하는지 확인합니다.

구분할 identity:

- application workload
- service resource policy
- database 또는 application role
- administrator
- provider maintenance service
- support operator
- encryption key 사용자

Cloud IAM에서 resource 접근을 허용했다고 해서 database row나 tenant 문서 접근까지 허용되는 것은 아닙니다.

## 8. Limit와 quota

Managed service는 내부 운영을 숨기는 대신 사용 제한을 공개합니다.

- connection 수
- request rate
- payload 크기
- object 수
- partition throughput
- retention 기간
- execution time
- concurrent operation
- backup 수
- management API rate

초과할 때 어떤 결과가 나오는지 확인합니다.

```text
즉시 거부
속도 제한
queue에 대기
기능 축소
일부만 성공
추가 비용 발생
수동 quota 증가 필요
```

Limit는 architecture를 결정하는 입력입니다. 문서 끝에 붙은 참고사항이 아닙니다.

## 9. Observability

Provider metric만으로 업무 결과를 알 수 없습니다. 다음 자료를 연결합니다.

- provider service health
- resource metric
- client가 관찰한 latency와 error
- application trace
- 최종 업무 결과
- 비용과 사용량

Queue의 message 수가 줄어도 consumer가 데이터를 버렸을 수 있습니다. 처리 결과와 정본 상태를 함께 확인해야 합니다.

## 10. Data ownership와 종료 준비

서비스를 선택하기 전에 다음을 적습니다.

- export format
- full·incremental export 지원 여부
- 일관된 snapshot 시점
- schema, metadata와 ACL 포함 여부
- key와 secret 준비 방법
- transfer bandwidth와 egress cost
- destination import 방법
- write 중지, dual-write 또는 change capture 선택
- import 뒤 검증
- 원본 삭제와 backup 보존 기간

Export 기능이 있다는 사실과 정해진 시간 안에 실제 이전할 수 있다는 사실은 다릅니다. 작은 데이터라도 정기적으로 연습합니다.

## 11. 직접 운영과 managed service 비교

| 기준 | 직접 운영 | managed service |
|---|---|---|
| 설정 제어 | 넓음 | 제한될 수 있음 |
| host와 engine 운영 | 사용자가 수행 | 일부 공급자에게 이동 |
| 표준 기능 도입 | 직접 구성 | 빠르게 사용 가능 |
| custom extension | 자유로움 | 제한될 수 있음 |
| scaling | 직접 구현 | 기능 제공, limit 존재 |
| 내부 장애 자료 | 내부까지 관찰 가능 | 공개 metric과 service contract 중심 |
| 비용 | 인력과 resource 비용 | premium, usage와 egress 비용 |
| 종료 | artifact를 직접 보유할 수 있음 | API, format과 공급자 기능에 의존 |

팀의 운영 능력, workload 중요도, 변경 빈도와 전체 비용을 함께 비교합니다.

## 12. 검토 질문

1. 공급자가 실제로 대신 수행하는 작업은 무엇입니까?
2. 기능만 제공하고 실행과 확인은 사용자에게 남는 작업은 무엇입니까?
3. Version, maintenance와 quota가 application에 어떤 실패를 만듭니까?
4. 내부 장애를 어떤 client-side 자료로 감지합니까?
5. Restore와 export를 마지막으로 언제 실행했습니까?
6. 서비스가 사라져도 data와 설정을 다시 만들 수 있습니까?
7. 사용량과 비용을 workload나 tenant에 연결할 수 있습니까?

## 다음 단계

Managed service의 사용 조건을 정리한 뒤 [`07-serverless-and-faas-runtime.md`](07-serverless-and-faas-runtime.md)에서 invocation 단위로 실행되는 환경의 수명과 제한을 확인하십시오.
