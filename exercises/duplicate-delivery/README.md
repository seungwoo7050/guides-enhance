# 중복 전달 단일 효과 처리기

## 개요

상태 저장 뒤 ACK 전에 프로세스가 중단되어 같은 이벤트가 다시 들어와도 잔액 변경을 한 번만 적용하는 Java 처리기입니다.

## 주요 기능

- event ID와 전체 입력 값을 함께 기록합니다.
- 동일한 재전달에는 앞서 저장한 결과를 반환합니다.
- 같은 event ID에 다른 payload가 들어오면 상태를 바꾸지 않고 거절합니다.
- 상태 저장 뒤 ACK 유실과 재전달을 결정적으로 재현합니다.

## 구성

`EffectStore`가 계정별 잔액, 이벤트별 처리 결과와 입력 지문을 함께 보관합니다. `Handler`는 전달 시도를 `EffectStore.applyOnce`에 연결하고 저장 뒤 ACK가 사라지는 상황을 재현합니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.duplicate.DuplicateDeliveryTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

중복 처리 기록과 잔액 변경을 같은 synchronized 작업에서 수행합니다. 둘을 따로 저장하면 첫 번째 저장 뒤 중단되었을 때 재전달이 잔액을 다시 바꿀 수 있습니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 이벤트 식별자와 입력 값 | `src/main/java/dev/guides/distributed/duplicate/DuplicateDelivery.java — Event` |
| 2 | 잔액·처리 결과·입력 지문 저장 | `src/main/java/dev/guides/distributed/duplicate/DuplicateDelivery.java — EffectStore` |
| 2-1 | 이벤트 효과 한 번만 적용 | `src/main/java/dev/guides/distributed/duplicate/DuplicateDelivery.java — EffectStore.applyOnce` |
| 3 | 전달 시도와 저장 처리 연결 | `src/main/java/dev/guides/distributed/duplicate/DuplicateDelivery.java — Handler` |
| 3-1 | 저장 후 ACK 유실 재현 | `src/main/java/dev/guides/distributed/duplicate/DuplicateDelivery.java — Handler.handle` |

## 범위와 제한

- 저장소는 메모리로만 구현했습니다.
- 실제 broker protocol과 ACK 처리는 포함하지 않습니다.
- 정수 overflow 처리 방법은 정의하지 않습니다.
