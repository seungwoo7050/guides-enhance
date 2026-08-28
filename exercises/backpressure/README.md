# 작업 종류별 Backpressure 제어기

## 개요

의존 서비스별로 실행 중인 작업 수와 대기열 크기를 제한하고, 처리할 수 없는 요청을 즉시 거절하는 Java 제어기입니다.

## 주요 기능

- Lane마다 동시에 실행할 수 있는 작업 수와 대기열 크기를 제한합니다.
- 한 Lane이 포화되어도 다른 Lane의 실행 자리는 사용할 수 있습니다.
- 작업 하나가 끝나면 아직 유효한 대기 작업 하나만 실행 상태로 옮깁니다.
- deadline과 최대 대기 시간을 넘긴 작업을 제거하고 만료 건수를 기록합니다.
- 가장 오래 기다린 시간을 대기열 길이와 별도로 확인할 수 있습니다.

## 구성

`Lane`은 작업 종류 하나의 실행 중·대기·완료·거절·만료 상태를 보관합니다. `AdmissionSystem`은 이름으로 Lane을 찾아 요청을 넣고 완료 처리와 상태 조회를 수행합니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.backpressure.BackpressureTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

중복 ID와 만료된 요청을 처리 용량보다 먼저 검사합니다. 이미 끝난 요청이나 실행할 수 없는 요청이 실행 자리와 대기열 크기에 영향을 주지 않게 하기 위해서입니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 처리 결과 정의 | `src/main/java/dev/guides/distributed/backpressure/Backpressure.java — Admission` |
| 2 | 작업 종류별 실행·대기 상태 | `src/main/java/dev/guides/distributed/backpressure/Backpressure.java — Lane` |
| 2-1 | 중복·만료 검사와 수용 여부 판단 | `src/main/java/dev/guides/distributed/backpressure/Backpressure.java — Lane.submit` |
| 2-2 | 실행 자리 하나의 승격 | `src/main/java/dev/guides/distributed/backpressure/Backpressure.java — Lane.completeOne` |
| 2-3 | 대기 작업 만료 | `src/main/java/dev/guides/distributed/backpressure/Backpressure.java — Lane.expire` |
| 2-4 | 최장 대기 시간 계산 | `src/main/java/dev/guides/distributed/backpressure/Backpressure.java — Lane.oldestAge` |
| 3 | 작업 종류별 격리 | `src/main/java/dev/guides/distributed/backpressure/Backpressure.java — AdmissionSystem` |

## 범위와 제한

- 실제 worker pool과 scheduler는 포함하지 않습니다.
- 대기 순서는 FIFO만 지원합니다.
- 현재 시각은 호출자가 전달해야 합니다.
