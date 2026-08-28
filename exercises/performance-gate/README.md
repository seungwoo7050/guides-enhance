# 정확성을 먼저 확인하는 성능 판정기

## 개요

반복 횟수와 실행 환경 정보가 충분한 경우에만 처리 결과의 정확성과 경과 시간을 함께 판정하는 Java 도구입니다.

## 주요 기능

- 필요한 실행 횟수가 부족하면 `UNVERIFIED`를 반환합니다.
- 서로 다른 환경에서 얻은 결과가 섞여 있어도 `UNVERIFIED`로 처리합니다.
- 완료 효과 수, 중복 효과 수와 오류 수가 틀리면 실행 시간이 빨라도 `FAIL`입니다.
- 모든 실행이 정확성과 시간 조건을 만족해야 `PASS`입니다.

## 구성

`Run`은 한 번의 측정 결과를, `Goal`은 필요한 반복 수와 정확한 효과 수, 최대 시간을 나타냅니다. `evaluate`가 근거의 완전성부터 정확성과 시간까지 차례로 확인합니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.performance.PerformanceGateTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

측정 자료가 부족한 상태를 성능 실패로 단정하지 않습니다. 또한 빠른 결과만 보고 누락이나 중복 효과를 통과시키지 않도록 정확성 검사를 시간 검사보다 먼저 수행합니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 판정 결과 | `src/main/java/dev/guides/distributed/performance/PerformanceGate.java — Decision` |
| 2 | 측정 결과와 목표 | `src/main/java/dev/guides/distributed/performance/PerformanceGate.java — Run, Goal` |
| 2-1 | 목표 값 검증 | `src/main/java/dev/guides/distributed/performance/PerformanceGate.java — Goal` |
| 3 | 근거·정확성·시간 판정 | `src/main/java/dev/guides/distributed/performance/PerformanceGate.java — evaluate` |

## 범위와 제한

- percentile과 warm-up 분석은 포함하지 않습니다.
- 환경 문자열이 실제 환경을 정확히 나타내는지는 확인하지 않습니다.
- 측정 실행과 결과 수집은 호출자가 수행해야 합니다.
