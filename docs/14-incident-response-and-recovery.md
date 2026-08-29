# 사고 대응과 복구

Incident response는 침해가 확정된 뒤에만 시작하는 별도 절차가 아닙니다. 필요한 event, credential 폐기, 기능 제한과 신뢰할 수 있는 복구 원본은 사고 전에 준비해야 합니다.

## 1. Vulnerability, suspicious event와 incident

- vulnerability finding: 보안 상태를 깨뜨릴 수 있는 조건이 존재합니다.
- suspicious event: 정상 동작인지 설명이 필요한 신호입니다.
- incident: 실제 또는 임박한 보안 영향 때문에 대응이 필요합니다.

Confirmed vulnerability가 있어도 실제 악용 근거가 없을 수 있습니다. 반대로 알려진 취약점 없이 credential theft incident가 발생할 수도 있습니다.

## 2. 사고 전에 준비할 내용

- severity와 incident 선언 기준
- incident commander와 역할
- 연락 경로와 대체 channel
- asset·identity·data owner
- log·snapshot·backup 접근 권한
- credential·session 폐기와 교체 절차
- endpoint·feature·traffic·deployment 제한 방법
- 신뢰할 수 있는 source와 build 환경
- 사용자·고객·provider·법무 담당자 연락 기준
- restore와 기능 제한 훈련

Runbook 파일이 있어도 실제 credential과 권한이 작동하는지 정기적으로 확인합니다.

## 3. 사실·가설·결정 기록

Timeline의 항목을 다음처럼 구분합니다.

```text
FACT       직접 확인한 event·state
HYPOTHESIS 사실을 설명할 수 있지만 확인하지 않은 원인
DECISION   누가 어떤 근거로 선택한 조치
ACTION     실제로 수행한 변경
RESULT     변경 뒤 관찰한 상태
UNKNOWN    현재 확인하지 못한 범위
```

예:

```text
FACT 01:02 user-17의 foreign report read가 200을 반환함
HYPOTHESIS report owner 확인이 누락됐을 수 있음
DECISION 01:10 download를 owner-only mode로 제한하기로 함
ACTION 01:12 feature flag 변경
RESULT 01:14 합성 cross-owner 요청은 deny, owner 요청은 allow
```

## 4. 증거 보존

- 원본 log, artifact와 snapshot의 read-only copy를 만듭니다.
- source, timestamp, hash와 수집자를 기록합니다.
- 조사 대상 host에서 불필요한 cleanup을 먼저 하지 않습니다.
- timezone과 clock 차이를 기록합니다.
- memory·process처럼 사라질 수 있는 자료가 필요한지 판단합니다.
- secret과 개인정보 접근을 제한합니다.
- 원본과 분석용 note를 분리합니다.

Backup과 incident evidence는 목적이 다릅니다. Backup은 서비스를 복구하기 위한 copy이고, evidence는 사건을 다시 확인할 수 있도록 원본성·수집 방법·시간과 취급 이력을 보존합니다. Hash 일치는 copy가 바뀌지 않았다는 근거이지 원래 producer가 사실을 기록했다는 증명은 아닙니다.

## 5. Containment

추가 영향과 확산을 줄이는 조치입니다.

- token·session 폐기
- privileged identity 사용 중단
- endpoint·feature 제한
- egress·storage scope 축소
- 의심 artifact 배포 중단
- workload 격리
- write 요청을 read-only 또는 보류 상태로 변경

각 조치의 부작용도 기록합니다.

- log·snapshot 손실 가능성
- 사용자 가용성
- retry 증가와 자원 사용
- actor가 행동을 바꿀 가능성
- rollback과 복구 난이도

Logging과 alert를 강화하는 일은 containment 결과를 관찰하는 작업입니다. Actor의 credential이나 접근 경로를 제거하지 않으므로 containment 완료로 세지 않습니다.

## 6. Eradication

단순히 process를 종료하거나 file을 지우는 일이 아닙니다.

- initial access와 공통 원인 수정
- 손상된 identity·key·session 폐기
- persistence·scheduled job·변경된 permission 조사
- 악성 또는 출처를 확인하지 못한 artifact 제거
- 취약 dependency·configuration 교체
- 영향받은 data와 파생 상태 확인
- 같은 identity·build 경로를 쓰는 다른 환경 조사

확인하지 않은 영역을 clean이라고 선언하지 않습니다.

## 7. Recovery

신뢰할 수 있는 원본에서 상태를 다시 만듭니다.

```text
검토한 source revision
+ 신뢰할 수 있는 builder
+ 검증한 artifact digest
+ 새 credential
+ 확인한 configuration
+ 무결성을 확인한 data·backup
+ 정상 동작하는 telemetry
```

먼저 recovery trust anchor를 정합니다. 손상 가능성이 있는 영역 밖에서 독립적으로 확인할 수 있는 source copy, key, builder, configuration baseline과 사고 전 backup이 필요합니다.

확인할 질문:

- source repository나 CI가 영향 범위라면 어떤 독립 copy로 source를 확인합니까?
- signing key나 builder가 의심된다면 기존 signature를 왜 계속 신뢰할 수 있습니까?
- dependency, base image와 build parameter를 어떤 digest로 고정합니까?
- backup이 사고 전 상태라는 근거는 무엇입니까?
- 새 credential과 configuration이 이전 손상 경로를 재사용하지 않음을 어떻게 확인합니까?

복구 뒤 다음을 검사합니다.

- 정상 사용자 기능
- 원래 공격과 유사 경로의 거절
- 이전 credential·artifact 거절
- log·alert 수집 상태
- data reconciliation
- 성능과 자원 한도
- 일정 기간 monitoring과 종료 기준

정상 기능과 알려진 공격 거절이 통과해도 모든 persistence가 제거됐다는 사실을 증명하지는 않습니다. 확인하지 못한 identity·asset·time을 `UNKNOWN`으로 남깁니다.

## 8. 영향 범위

다음 축으로 조사합니다.

- 시간: last-known-good와 earliest-observed known-bad 사이, containment까지
- identity: user, service, CI, admin과 key
- asset: host, service, tenant, bucket과 repository
- data: read·write·delete 가능한 범위
- release: 영향받은 digest와 environment
- evidence: log·backup·audit 신뢰 상태

첫 event의 시각을 실제 최초 침해 시각으로 단정하지 않습니다. “한 endpoint에서 발견됨”과 “그 endpoint만 영향받음”도 같은 뜻이 아닙니다.

## 9. Communication

기술 timeline과 연락 timeline을 함께 관리합니다.

- 내부 의사결정자
- service owner와 support
- 사용자·고객
- provider·maintainer
- 법무·privacy·규제 담당자
- 외부 researcher

확인한 사실, 현재 영향, 수행한 조치와 다음 update 시각을 구분합니다. 가설을 사실처럼 전달하지 않습니다.

## 10. 사고 뒤 검토

개인을 비난하는 대신 시스템 조건을 봅니다.

- 어떤 가정이 틀렸습니까?
- 예방 조치는 왜 실패했습니까?
- event가 왜 늦거나 불완전했습니까?
- 대응에 필요한 권한·문서·근거가 준비돼 있었습니까?
- recovery source를 실제로 신뢰할 수 있었습니까?
- 같은 문제를 다른 service에서 어떻게 찾습니까?

후속 작업에는 owner, priority, 기한과 검증 방법을 둡니다.

## 11. 훈련 유형

### Tabletop

상태와 의사결정을 토론합니다. 실제 credential 폐기와 restore가 동작한다는 사실은 증명하지 않습니다.

### 기능 훈련

Credential 폐기, endpoint 제한, restore와 alert 전달 중 한 기능을 실제로 실행합니다.

### 전체 합성 훈련

격리된 환경에서 detection부터 recovery까지 연결합니다. 실제 사용자 데이터, production credential와 무단 traffic은 사용하지 않습니다.

## 완료 질문

- Vulnerability와 incident는 어떻게 다릅니까?
- Containment가 evidence와 가용성에 줄 수 있는 영향은 무엇입니까?
- Process를 종료했다고 eradication이 끝난 것이 아닌 이유는 무엇입니까?
- Builder가 손상됐다면 기존에 서명된 artifact를 복구 원본으로 사용할 수 없는 이유는 무엇입니까?
- Monitoring이 containment나 recovery를 대신하지 못하는 이유는 무엇입니까?
