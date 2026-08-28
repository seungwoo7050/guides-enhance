# 장애 실험 근거 기록 모델

## 개요

장애 전·중·복구 후의 상태, 사전에 정한 가설과 시간 예산, 업무 복구 결과와 cleanup 결과를 따로 기록하는 Java 모델입니다.

## 주요 기능

- 한 번의 실험에는 지원하는 장애 하나만 허용합니다.
- `BEFORE`, `DURING`, `AFTER`의 값을 불변 Snapshot으로 남깁니다.
- 업무 상태의 수렴 여부와 cleanup 성공 여부를 따로 판정합니다.
- 최종 상태가 맞더라도 시간 예산을 넘기면 업무 복구 결과를 실패로 판정합니다.

## 구성

`Scenario`가 원본 행 수, 미발행 Outbox 수와 조회 모델 행 수를 변경합니다. `Snapshot`은 한 시점의 값을 고정하고, `Report`는 가설·시간·판정 결과와 모든 Snapshot을 묶어 반환합니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.chaos.ChaosEvidenceTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

프로세스가 실행 중인지가 아니라 원본 상태, Outbox와 조회 모델이 정해진 시간 안에 같은 결과로 수렴했는지를 확인합니다. cleanup 실패는 별도 결과로 남겨 원래 실험의 성공·실패를 바꾸지 않습니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 실험 단계와 판정 값 | `src/main/java/dev/guides/distributed/chaos/ChaosEvidence.java — Phase, Failure, Result` |
| 2 | 시점별 불변 스냅샷 | `src/main/java/dev/guides/distributed/chaos/ChaosEvidence.java — Snapshot` |
| 2-1 | 실험 결과 보고서 | `src/main/java/dev/guides/distributed/chaos/ChaosEvidence.java — Report` |
| 3 | 실험 상태 보관 | `src/main/java/dev/guides/distributed/chaos/ChaosEvidence.java — Scenario` |
| 3-1 | 장애 종류와 시간 예산 검증 | `src/main/java/dev/guides/distributed/chaos/ChaosEvidence.java — Scenario.run` |
| 3-2 | 업무 복구와 정리 결과 분리 | `src/main/java/dev/guides/distributed/chaos/ChaosEvidence.java — Scenario.report` |
| 3-3 | 장애 제거 후 상태 수렴 | `src/main/java/dev/guides/distributed/chaos/ChaosEvidence.java — Scenario.publishPending` |

## 범위와 제한

- 실제 시나리오는 `BROKER_DOWN`만 지원합니다.
- 경과 시간은 호출자가 전달하는 값입니다.
- 실제 프로세스나 네트워크에 장애를 주입하지 않습니다.
