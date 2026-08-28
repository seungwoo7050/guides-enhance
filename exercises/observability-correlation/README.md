# 분산 처리 식별자 연결 모델

## 개요

request, operation, trace, correlation, event와 causation ID를 여러 처리 단계에 이어 주고, 지표 태그의 cardinality를 제한하는 Java 모델입니다.

## 주요 기능

- 상위 시스템에서 받은 trace ID와 correlation ID를 그대로 전달합니다.
- 새 이벤트가 어떤 operation 때문에 만들어졌는지 causation ID로 남깁니다.
- 중복 전달 기록과 실제 업무 효과 횟수를 분리합니다.
- metric tag는 값의 종류가 제한된 `component`와 `outcome`만 허용합니다.
- 같은 event ID에 다른 식별자가 연결되면 잘못된 관찰값을 남기기 전에 거절합니다.

## 구성

`Command`, `Event`, `Observation`이 각 식별자의 사용 위치를 나타냅니다. `Flow`는 처리 단계별 관찰값, 이미 처리한 이벤트, 지표와 업무 효과 횟수를 함께 보관합니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.observability.ObservabilityCorrelationTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

operation ID나 event ID는 로그와 trace에는 필요하지만 metric tag로 사용하면 시계열 수가 계속 늘어납니다. 따라서 상세 식별자는 Observation에 남기고 지표는 제한된 값만 사용합니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 상관관계 식별자 정의 | `src/main/java/dev/guides/distributed/observability/ObservabilityCorrelation.java — Command, Event, Observation` |
| 2 | 관찰 기록·중복 기록·지표 집계 | `src/main/java/dev/guides/distributed/observability/ObservabilityCorrelation.java — Flow` |
| 2-1 | 외부에서 받은 식별자 보존 | `src/main/java/dev/guides/distributed/observability/ObservabilityCorrelation.java — Flow.receive` |
| 2-2 | 이벤트 원인 식별자 전파 | `src/main/java/dev/guides/distributed/observability/ObservabilityCorrelation.java — Flow.publish` |
| 2-3 | 중복 전달과 업무 효과 분리 | `src/main/java/dev/guides/distributed/observability/ObservabilityCorrelation.java — Flow.consume` |
| 2-4 | 제한된 지표 태그 | `src/main/java/dev/guides/distributed/observability/ObservabilityCorrelation.java — Flow.metricTagKeys` |
| 2-5 | 관찰 기록과 지표 동시 집계 | `src/main/java/dev/guides/distributed/observability/ObservabilityCorrelation.java — Flow.observe` |

## 범위와 제한

- 실제 tracing SDK와 metric backend를 사용하지 않습니다.
- sampling과 span 계층은 다루지 않습니다.
- 지표 값은 프로세스 내부 Map에 저장합니다.
