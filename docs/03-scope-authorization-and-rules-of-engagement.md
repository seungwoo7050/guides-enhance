# 평가 범위, 허가와 실행 규칙

보안 평가의 첫 결과물은 scan 보고서가 아닙니다. 누가 어떤 자산을 어떤 identity와 방법으로 어느 기간 동안 확인하도록 승인했는지 적은 문서입니다. 이 내용이 없으면 기술적으로 가능한 행동도 안전한 평가가 아닙니다.

## 1. 허가가 먼저입니다

다음 중 하나가 명확해야 합니다.

- 자신이 소유하고 통제하는 local 환경
- 교육용으로 명시된 lab·CTF
- 조직이 문서로 승인한 test 환경
- 공개 vulnerability disclosure program이 허용한 자산과 행동

공개 인터넷에서 접근할 수 있다는 사실은 시험할 권한을 뜻하지 않습니다. 계정 하나를 가지고 있어도 다른 사용자, tenant와 provider의 자산을 확인할 권한은 생기지 않습니다.

## 2. 허가에는 상태와 유효 기간이 있음

허가 문서는 한 번 받은 서명으로 끝나지 않습니다.

```text
draft → approved → active → paused 또는 revised → expired 또는 revoked
```

- `draft`: 제안 단계이며 어떤 평가 행동도 허용하지 않습니다.
- `approved`: 권한자가 특정 version의 자산·identity·시간·행동을 승인했습니다.
- `active`: 현재 시각과 실행 환경이 승인 조건에 맞습니다.
- `paused`: 범위 이탈, incident 또는 중단 조건 때문에 새 행동을 멈춥니다.
- `revised`: 자산, identity, 시간, 행동이나 요청량을 바꾼 새 version입니다. 다시 승인받아야 합니다.
- `expired`: 승인 종료 시각을 지났습니다.
- `revoked`: 권한자가 종료 시각 전에 허가를 철회했습니다.

`expired`나 `revoked` 상태를 다시 `active`로 돌리지 않습니다. 계속해야 한다면 새 version을 `draft`에서 시작합니다. 평가자가 자신의 허가를 승인하거나 연장해서도 안 됩니다.

각 version에는 다음을 기록합니다.

```text
authorization ID와 version
이전 version
승인자·승인 시각
시작·종료 시각
정확한 자산과 환경
평가 identity와 role
허용·금지 행동
요청·시간·데이터 한도
중단과 연락 조건
증거 보관과 정리 방법
```

## 3. 평가 문서에 들어갈 내용

최소 항목은 다음과 같습니다.

```text
목적과 성공 조건
승인자와 긴급 연락처
평가자
시작·종료 시간
in-scope 자산과 version
out-of-scope 자산
허용 행동
금지 행동
요청·동시성·데이터 한도
중단 조건
증거 저장·전달·폐기
incident 연락 절차
종료 뒤 account·credential·fixture 정리
```

## 4. 자산을 정확히 식별하기

도메인 하나만 적으면 부족합니다.

- hostname, IP, repository와 application ID
- production, staging과 local 구분
- public endpoint와 admin endpoint
- test account와 role
- API, worker, queue와 storage 포함 여부
- third-party provider와 shared infrastructure
- 현재 release, commit 또는 image digest

동적으로 바뀌는 cloud 자산은 account, project, namespace와 tag 같은 식별 조건을 함께 적습니다.

## 5. 허용 행동과 금지 행동

### 허용 행동 예

- 제공된 test account로 정상 요청과 권한 거절 확인
- 합성 object 생성·조회·삭제
- 정한 rate 안에서 회귀 요청 실행
- local container에서 crash와 memory error 재현
- 승인된 source·binary 정적 분석
- 지정된 log와 event export 읽기

### 금지 행동 예

- 실제 사용자 계정 추측과 credential stuffing
- phishing, social engineering과 physical access 시도
- 서비스를 중단시킬 수 있는 자원 고갈
- persistence 설치, 보호 기능 비활성화와 log 삭제
- 범위 밖 host·tenant·bucket·repository 접근
- 실제 개인정보와 secret 다운로드
- 제3자 service로 공격 traffic 전달

승인되지 않은 행동을 “영향을 확인하려면 필요했다”는 이유로 나중에 정당화하지 않습니다.

## 6. 최소 영향 순서

가능한 한 다음 순서로 확인합니다.

```text
source·configuration 검토
→ 상태를 바꾸지 않는 요청
→ 합성 자원에 제한된 상태 변경
→ 필요한 최소 결과 확인
→ 즉시 중단과 정리
```

다른 사용자의 데이터에 접근할 수 있는지 확인할 때 실제 내용을 수집하지 않습니다. 합성 account 두 개와 서로 다른 marker를 사용해 cross-owner read가 가능한지만 확인합니다.

## 7. 중단 조건

다음 상황에서는 즉시 새 행동을 멈추고 승인자에게 알립니다.

- 요청이 범위 밖 자산으로 전달됩니다.
- 실제 개인정보, secret 또는 production key가 보입니다.
- 예상하지 못한 데이터 변경이나 서비스 저하가 발생합니다.
- logging, monitoring 또는 backup 기능이 손상됩니다.
- 다른 사용자의 작업이나 shared 환경에 영향이 보입니다.
- 승인한 test account가 아닌 identity가 사용됩니다.
- 승인 문서와 실제 topology가 다릅니다.

중단할 때 무엇을 보존하고 무엇을 되돌릴지도 미리 정합니다. 무조건 process나 log를 삭제하면 중요한 근거를 잃을 수 있습니다.

## 8. 요청과 자원 한도

자동화된 도구는 예상보다 많은 작업을 수행할 수 있습니다.

- 최대 요청 수와 초당 요청 수
- 동시 connection·process·job 수
- 생성할 수 있는 데이터 크기
- CPU·memory·disk·network 사용량
- 전체 실행 시간과 비용
- retry 횟수
- 특정 오류나 alert가 발생했을 때 중단하는 조건

문서에 숫자를 적는 것으로 끝내지 않습니다. 가능한 경우 proxy, sandbox와 resource limit에서 실제로 강제합니다. 시작 전에 정상·경계·거절 probe를 소량 실행해 현재 version의 제한이 적용됐는지 확인합니다.

## 9. 평가 account와 데이터

- 평가자별 test identity를 사용합니다.
- role과 resource scope를 기록합니다.
- 실제 사용자 데이터를 복제하지 않습니다.
- synthetic marker로 소유권과 변경 여부를 확인합니다.
- test credential은 수명과 권한을 짧게 제한합니다.
- 종료 뒤 account, token과 object를 폐기합니다.

## 10. 증거 처리

보안 증거 자체가 민감할 수 있습니다.

```text
무엇을 수집합니까?
왜 필요합니까?
누가 읽을 수 있습니까?
어디에 저장합니까?
어떤 식별자를 가립니까?
언제 폐기합니까?
source·timestamp·hash를 어떻게 남깁니까?
```

원본과 분석용 복사본을 구분합니다. 원본을 직접 편집하지 않습니다.

## 11. 제3자와 shared 환경

SaaS, CDN, cloud, identity provider와 package registry를 사용한다면 다음을 구분합니다.

- 자신의 application과 configuration
- provider가 명시적으로 허용한 시험 범위
- provider 내부 구현
- 다른 tenant가 함께 사용하는 control plane

자신의 애플리케이션을 평가한다는 이유로 provider 자체를 scan하거나 우회하지 않습니다.

## 12. 즉시 알려야 할 발견

다음 항목은 최종 보고서까지 기다리지 않습니다.

- 실제 악용 징후
- 유효한 credential, signing key와 backup key 노출
- 범위 밖 데이터 접근
- production 데이터 변경
- 즉시 악용할 수 있는 public code execution 가능성
- 조사 중인 보호 기능의 비활성화

연락 대상, 답변을 기다릴 시간과 평가를 계속할지 중단할지를 미리 정합니다.

## 완료 질문

- public endpoint가 평가 허가를 의미하지 않는 이유는 무엇입니까?
- scope·identity·시간·행동이 바뀌면 왜 새 version을 승인해야 합니까?
- 영향 확인과 최소 영향 원칙을 어떻게 함께 지킬 수 있습니까?
- 승인 문서가 `active`여도 실제 제한이 적용됐는지 먼저 확인해야 하는 이유는 무엇입니까?
- 범위 밖 provider가 attack path에 포함되면 어떻게 기록해야 합니까?
