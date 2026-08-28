# 조회 모델 재구축 실행기

## 개요

이벤트 적용과 checkpoint 저장 사이에 중단되더라도 이벤트를 잃지 않고, 빈 조회 모델을 전체 로그에서 다시 만드는 Java 실행기입니다.

## 주요 기능

- 이벤트를 적용한 뒤에만 checkpoint를 전진시킵니다.
- 적용 뒤 checkpoint 저장 전에 중단되면 같은 이벤트를 다시 읽습니다.
- event ID를 기록해 재전달이 집계 값을 두 번 늘리지 않게 합니다.
- 전체 로그를 새 Projection에 재생할 수 있습니다.
- 같은 event ID의 다른 입력은 상태를 바꾸기 전에 거절합니다.

## 구성

`EventLog`가 이벤트 순서를 보관하고 `Projection`이 aggregate별 합계와 적용한 이벤트 지문을 저장합니다. `Runner`는 현재 로그 위치를 읽고 Projection 적용이 끝난 뒤 checkpoint를 전진시킵니다.

## 실행 및 검증

JDK 17 이상과 `make`가 필요합니다.

```sh
make build
make test
```

`make test`는 본 코드와 테스트 코드를 컴파일한 뒤 `dev.guides.distributed.readmodel.ReadModelRebuildTest`를 실행합니다. 생성 파일은 `build/`에만 저장되며 `make clean`으로 제거할 수 있습니다.

## 주요 설계 결정

checkpoint를 먼저 전진시키면 적용 전에 중단된 이벤트를 영구히 건너뜁니다. 반대로 적용 뒤 checkpoint 전에 중단되는 경우는 허용하고, 재전달을 멱등하게 처리합니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 재생 이벤트 식별자 | `src/main/java/dev/guides/distributed/readmodel/ReadModelRebuild.java — Event` |
| 2 | 입력 순서를 보존하는 이벤트 로그 | `src/main/java/dev/guides/distributed/readmodel/ReadModelRebuild.java — EventLog` |
| 3 | 집계 값과 적용 이벤트 기록 | `src/main/java/dev/guides/distributed/readmodel/ReadModelRebuild.java — Projection` |
| 3-1 | 이벤트 중복 적용 방지 | `src/main/java/dev/guides/distributed/readmodel/ReadModelRebuild.java — Projection.apply` |
| 4 | 로그 위치와 조회 모델 적용 순서 | `src/main/java/dev/guides/distributed/readmodel/ReadModelRebuild.java — Runner` |
| 4-1 | 적용 완료 후 체크포인트 전진 | `src/main/java/dev/guides/distributed/readmodel/ReadModelRebuild.java — Runner.processNext` |
| 4-2 | 전체 로그 재생 | `src/main/java/dev/guides/distributed/readmodel/ReadModelRebuild.java — Runner.replayAll` |

## 범위와 제한

- EventLog와 checkpoint를 파일이나 데이터베이스에 저장하지 않습니다.
- 한 번에 Runner 하나만 Projection을 갱신한다고 가정합니다.
- 이벤트 schema와 업무 순서 규칙은 검사하지 않습니다.
