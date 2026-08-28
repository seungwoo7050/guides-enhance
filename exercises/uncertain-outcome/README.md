# 응답 유실 결과 복구 모델

## 개요

서버가 상태를 저장한 뒤 응답이 사라졌을 때 timeout을 업무 실패로 단정하지 않고, 같은 operation ID로 확정 결과를 다시 확인하는 Java 라이브러리입니다.

## 주요 기능

- 같은 operation ID와 같은 입력에는 이전 결과를 반환합니다.
- 같은 ID를 다른 입력에 사용하면 상태를 바꾸지 않고 거절합니다.
- 응답을 잃은 뒤 저장된 결과를 조회해 `ACCEPTED`와 `UNKNOWN`을 구분합니다.
- 재시도와 조회를 반복해도 업무 효과 횟수는 한 번으로 유지됩니다.

## 구성

`Gateway`가 operation ID별 입력 지문, 처리 결과와 효과 횟수를 보관합니다. `Client`는 응답 유실 예외를 받으면 처음 사용한 operation ID로 `Gateway.query`를 호출합니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.uncertain.UncertainOutcomeTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

operation ID는 단순한 중복 제거 문자열이 아니라 입력과 결합된 식별자입니다. 같은 ID에 다른 입력을 허용하면 과거 결과를 잘못 돌려줄 수 있으므로 충돌로 처리합니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 처리 결과 상태 | `src/main/java/dev/guides/distributed/uncertain/UncertainOutcome.java — Status, Result` |
| 2 | operation 입력·결과·효과 횟수 저장 | `src/main/java/dev/guides/distributed/uncertain/UncertainOutcome.java — Gateway` |
| 2-1 | 입력 지문 검증과 효과 한 번 적용 | `src/main/java/dev/guides/distributed/uncertain/UncertainOutcome.java — Gateway.reserve` |
| 2-2 | 저장된 결과 조회 | `src/main/java/dev/guides/distributed/uncertain/UncertainOutcome.java — Gateway.query` |
| 3 | 응답 유실 후 결과 확인 | `src/main/java/dev/guides/distributed/uncertain/UncertainOutcome.java — Client.reserve` |

## 범위와 제한

- 상태는 메모리에만 저장합니다.
- 실제 network timeout과 영속 저장소는 제공하지 않습니다.
- 한 프로세스 안에서 synchronized 메서드로 동시 접근을 제한합니다.
