# 이벤트 계약과 순서 처리기

## 개요

channel, schema version, event ID와 aggregate sequence를 검사하고 순서가 뒤바뀐 이벤트를 aggregate별로 보류하는 Java 조회 모델입니다.

## 주요 기능

- 예상한 channel과 다른 이벤트를 거절합니다.
- 지원하지 않는 schema version은 상태에 적용하지 않고 격리합니다.
- aggregate별 sequence gap을 보류하고 앞선 이벤트가 오면 이어서 적용합니다.
- 같은 event ID의 재전달과 다른 payload 재사용을 구분합니다.
- 한 aggregate의 gap이 다른 aggregate의 진행을 막지 않습니다.

## 구성

`Projection`이 aggregate별 상태, 다음 sequence, 보류 이벤트, 이미 선점된 sequence와 격리 목록을 함께 보관합니다. 입력 검증은 조회 모델을 바꾸기 전에 끝냅니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.contracts.ContractsAndOrderTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

event ID 중복 기록과 aggregate sequence 선점 기록을 분리합니다. 같은 이벤트의 재전달과 서로 다른 이벤트가 같은 순서를 주장하는 충돌은 처리 방법이 다르기 때문입니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 이벤트 입력과 처리 결과 | `src/main/java/dev/guides/distributed/contracts/ContractsAndOrder.java — Outcome, Event` |
| 2 | 조회 모델 상태와 순서 기록 | `src/main/java/dev/guides/distributed/contracts/ContractsAndOrder.java — Projection` |
| 2-1 | 채널·식별자·스키마 검증 | `src/main/java/dev/guides/distributed/contracts/ContractsAndOrder.java — Projection.onEvent` |
| 2-2 | Aggregate별 sequence 선점 기록 | `src/main/java/dev/guides/distributed/contracts/ContractsAndOrder.java — Projection.onEvent` |
| 2-3 | 상태와 다음 sequence 함께 갱신 | `src/main/java/dev/guides/distributed/contracts/ContractsAndOrder.java — Projection.apply` |
| 2-4 | Aggregate별 보류 이벤트 적용 | `src/main/java/dev/guides/distributed/contracts/ContractsAndOrder.java — Projection.drain` |

## 범위와 제한

- schema 변환은 제공하지 않습니다.
- 보류 목록의 크기와 보존 시간은 제한하지 않습니다.
- 모든 상태는 메모리에만 저장합니다.
