# 동기·비동기 요청 판정기

## 개요

즉시 결과를 확정하는 요청과 처리 책임만 먼저 받아들이는 요청을 구분하고, 원격 판정이 끝나기 전에는 예약 수량을 바꾸지 않는 Java 조정기입니다.

## 주요 기능

- 동기 요청은 Policy 결과를 즉시 `ACCEPTED` 또는 `REJECTED`로 확정합니다.
- 비동기 요청은 효과를 실행하지 않고 `PENDING` 상태와 대기열 항목만 만듭니다.
- Policy의 거절과 장애는 예약 수량을 바꾸지 않습니다.
- operation ID는 quantity와 Mode까지 같은 경우에만 이전 결과를 반환합니다.

## 구성

`CapacityLedger`가 예약된 수량을 저장하고 `Coordinator`가 요청 입력, 결과와 대기열을 관리합니다. `Policy`는 외부 서비스의 판정을 함수로 전달합니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.decision.RequestDecisionTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

비동기 접수는 업무가 끝났다는 뜻이 아니라 시스템이 후속 처리를 맡았다는 뜻으로 `PENDING`을 반환합니다. 재시도는 Policy를 다시 호출하기 전에 이전 입력과 완전히 같은지 확인합니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 요청 방식과 판정 결과 정의 | `src/main/java/dev/guides/distributed/decision/RequestDecision.java — Mode, PolicyResult, Status` |
| 2 | 예약 수량 변경 | `src/main/java/dev/guides/distributed/decision/RequestDecision.java — CapacityLedger` |
| 3 | 요청 입력·결과·대기열 저장 | `src/main/java/dev/guides/distributed/decision/RequestDecision.java — Coordinator` |
| 3-1 | 중복 요청 검증과 비동기 접수 | `src/main/java/dev/guides/distributed/decision/RequestDecision.java — Coordinator.submit` |
| 3-2 | 대기 요청 판정 완료 | `src/main/java/dev/guides/distributed/decision/RequestDecision.java — Coordinator.processNext` |
| 3-3 | ALLOW 이후에만 수량 변경 | `src/main/java/dev/guides/distributed/decision/RequestDecision.java — Coordinator.decideNow` |

## 범위와 제한

- 대기열과 결과를 영속화하지 않습니다.
- Policy 호출의 실제 timeout은 재현하지 않습니다.
- Coordinator 인스턴스 하나가 모든 요청을 처리한다고 가정합니다.
