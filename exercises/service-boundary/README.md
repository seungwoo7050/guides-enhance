# 서비스 데이터 소유권 검사기

## 개요

데이터마다 쓰기를 수행할 서비스가 하나인지, 등록되지 않은 이름과 서비스 사이의 동기 호출 순환이 없는지 확인하는 Java 검사기입니다.

## 주요 기능

- DataSet별 owner와 writer를 확인합니다.
- 등록되지 않은 owner, writer와 dependency를 모두 보고합니다.
- 첫 오류에서 멈추지 않고 한 번의 검토에서 여러 문제를 수집합니다.
- 동기 호출 그래프의 순환을 찾습니다.

## 구성

`Architecture`는 Service와 DataSet 목록을 불변 값으로 보관합니다. `review`가 이름과 쓰기 권한을 검사하고, `findCycles`와 `visit`이 동기 의존 그래프를 순회합니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.boundary.ServiceBoundaryTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

읽기 복제본을 가진 서비스와 데이터를 직접 변경할 수 있는 서비스를 구분합니다. 순환 검사는 현재 재귀 경로와 이미 검토를 끝낸 서비스를 따로 보관해 실제 순환만 보고합니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 변경되지 않는 검토 입력 | `src/main/java/dev/guides/distributed/boundary/ServiceBoundary.java — DataSet, Service, Architecture` |
| 2 | 서비스·소유자·writer·의존 대상 검증 | `src/main/java/dev/guides/distributed/boundary/ServiceBoundary.java — review` |
| 3 | 의존 그래프 탐색 상태 | `src/main/java/dev/guides/distributed/boundary/ServiceBoundary.java — findCycles` |
| 3-1 | 동기 의존 순환 검출 | `src/main/java/dev/guides/distributed/boundary/ServiceBoundary.java — visit` |

## 범위와 제한

- 실행 중인 서비스 목록이나 배포 정보를 읽지 않습니다.
- 비동기 이벤트 의존은 순환 검사 대상이 아닙니다.
- 입력은 코드에서 직접 생성하는 메모리 모델입니다.
