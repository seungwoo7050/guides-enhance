# Portability, lock-in과 exit

이 문서는 필수 경로가 아닌 심화 자료입니다. 실제 data export, 공급자 교체, 서비스 종료와 cutover를 준비할 때 읽으십시오.

특정 공급자 기능을 사용하는 것 자체가 잘못은 아닙니다. 문제는 얻는 이점과 교체 비용을 알지 못하거나, 실제로 나갈 절차를 시험하지 않은 상태입니다.

```text
lock-in
서비스를 바꾸는 데 비용과 작업이 필요한 상태

관리되지 않은 lock-in
교체 비용, 담당자, 절차와 시험 결과를 모르는 상태
```

목표는 모든 공급자 기능을 포기하는 것이 아니라 필요한 의존성을 의식적으로 선택하는 것입니다.

## 1. 의존성 종류

### API 의존성

Provider SDK, event format, identity API, monitoring query와 deployment 명령입니다.

### 동작 의미 의존성

Consistency, delivery, transaction, ordering, timeout와 retry 방식입니다. 이름이 비슷한 서비스로 바꿔도 결과가 달라질 수 있습니다.

### Data 의존성

Proprietary format, index, feature, data volume, export 속도와 egress입니다.

### 운영 의존성

Runbook, dashboard, alert, on-call, support와 팀 경험입니다.

### 상업 의존성

Commitment, 계약, license, minimum spend와 transfer 가격입니다.

### 조직 의존성

Security 승인, account 구성, compliance 자료와 vendor 관계입니다.

## 2. Portability를 여러 항목으로 나눕니다

| 항목 | 확인할 질문 |
|---|---|
| source | code와 설정을 다른 환경에서 build할 수 있습니까? |
| artifact | image, bundle과 schema를 다른 runtime에서 사용할 수 있습니까? |
| runtime | 필요한 OS, API와 limit를 대체 환경이 제공합니까? |
| data | full·incremental export와 import가 가능합니까? |
| identity | account, role, user와 tenant mapping을 다시 만들 수 있습니까? |
| operation | monitoring, backup과 incident 절차를 옮길 수 있습니까? |
| commercial | commitment, egress와 계약 종료 비용은 얼마입니까? |

Container image를 옮길 수 있어도 data, identity와 운영 절차가 그대로 이동하는 것은 아닙니다.

## 3. Provider-neutral wrapper도 비용이 있습니다

공통 wrapper를 만들면 일부 API 의존성을 줄일 수 있지만 다음 문제가 생깁니다.

- 공급자 고유 기능을 사용하지 못합니다.
- 공통 분모 기능만 지원하게 됩니다.
- 자체 변환 code와 bug가 생깁니다.
- provider metric과 error 정보가 줄어들 수 있습니다.
- 팀이 provider API와 wrapper를 모두 알아야 합니다.

실제로 교체할 가능성이 있고 API 변경이 자주 발생하는 지점에만 사용합니다. 모든 API를 미리 감싸는 것은 별도 platform을 만드는 일입니다.

## 4. Exit plan

`나중에 export합니다`만으로는 실행할 수 없습니다.

```text
exit trigger
owner
대상 resource와 data
write freeze 또는 dual-run 방법
full export
incremental catch-up
schema와 metadata
identity mapping
설정과 secret
새 환경 검증
traffic cutover
rollback window
원본 보존과 삭제
예상 비용과 시간
```

## 5. Data migration 방식

### Snapshot migration

Write를 중지하고 일관된 snapshot을 옮깁니다. 단순하지만 downtime이 필요합니다.

### Dual-write

새 시스템과 기존 시스템에 함께 씁니다. 두 결과가 달라졌을 때 어떤 값을 정본으로 볼지와 보정 방법이 필요합니다.

### Change capture

초기 snapshot 뒤 변경 event를 따라갑니다. Ordering, schema 변경, replay와 lag를 처리해야 합니다.

### Application-level export/import

업무 객체 단위로 옮기면 storage API 의존성을 줄일 수 있습니다. 대신 대용량 처리, 속도와 숨겨진 metadata 누락을 확인해야 합니다.

## 6. Serverless migration

Function code만 옮겨서는 같은 결과를 보장할 수 없습니다.

- trigger와 event schema
- retry, batch와 ordering
- workload identity
- timeout, memory와 concurrency
- network
- destination과 dead letter
- log와 trace
- deployment version

같은 handler가 실행돼도 source acknowledgment와 retry 방식이 다르면 중복 결과와 처리 순서가 달라질 수 있습니다.

## 7. 외부 SaaS 종료

외부 SaaS를 사용하는 조직도 종료 절차가 필요합니다.

- user, group과 role export
- 업무 data와 attachment
- audit 자료
- API rate와 export limit
- 계약 종료 뒤 data 보존 기간
- 고객 관리 key
- integration token 폐기
- legal hold
- 대체 업무 절차

SaaS를 만드는 공급자는 고객이 data를 export하고 삭제 결과를 확인할 수 있게 해야 합니다.

## 8. Multi-cloud을 목적 없이 선택하지 않습니다

여러 provider를 동시에 사용하면 일부 장애와 상업 의존성을 줄일 수 있지만 다음 작업이 늘어납니다.

- identity와 network 구성
- 중복 platform 운영
- data 동기화
- 필요한 기술 범위
- log와 trace 연결
- security rule 차이
- 정상 상태 비용

규제, 인수 합병, 고객 요구, 독립 backup처럼 구체적인 이유가 있어야 합니다. `lock-in 방지` 한 문장만으로는 비용을 정당화하기 어렵습니다.

## 9. Exit rehearsal

전체 migration을 자주 실행하기 어렵다면 대표 data로 작은 시험을 합니다.

- 실제와 비슷한 data export
- 깨끗한 환경 import
- checksum과 업무 불변식 확인
- identity remap
- application smoke test
- 측정한 처리량
- 전체 예상 시간
- egress 비용

시험 결과를 바탕으로 계획과 예상 시간을 갱신합니다.

## 10. 삭제 결과

서비스 종료 뒤 다음을 확인합니다.

- active resource 없음
- snapshot과 backup 보존 상태
- object version
- key 상태
- log와 audit의 법적 보존
- support copy
- 마지막 invoice와 과금 종료
- DNS, certificate와 token 폐기

공급자 내부 media 삭제는 사용자가 직접 증명하지 못할 수 있습니다. 사용자가 확인한 범위와 공급자 문서나 attest에 의존한 범위를 구분합니다.

## 11. Lock-in 목록

각 의존성을 다음 형식으로 기록합니다.

```text
dependency
얻는 이점
대안
migration 장애물
data volume
예상 작업량
exit trigger
owner
마지막 rehearsal
accepted_until
```

모든 의존성을 없애지 않습니다. 얻는 이점이 교체 비용보다 큰 동안 의식적으로 유지합니다.

## 필수 경로와의 관계

기본 과정에서는 [`06-paas-and-managed-service-contracts.md`](06-paas-and-managed-service-contracts.md)와 [`14-service-selection-and-architecture-review.md`](14-service-selection-and-architecture-review.md)에서 export 가능 여부와 종료 조건까지만 확인합니다. 이 문서는 실제 migration 방식, cutover와 삭제 증거가 필요할 때 그 판단을 실행 절차로 확장합니다.
