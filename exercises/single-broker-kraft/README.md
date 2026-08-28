# 단일 브로커 KRaft 실행 환경

## 개요

Docker Compose로 Kafka KRaft 브로커 하나를 실행하고, Broker API와 직접 partition 소비, consumer group 소비가 모두 동작하는지 확인하는 환경입니다.

## 주요 기능

- Kafka broker와 controller 역할을 한 프로세스에서 실행합니다.
- client와 controller listener를 분리합니다.
- Kafka image를 tag와 digest로 함께 고정합니다.
- healthcheck는 프로세스 존재가 아니라 Kafka API 응답을 확인합니다.
- smoke test는 고유한 Compose project name을 사용하고 자신이 만든 자원만 정리합니다.

## 구성

`compose.yaml`은 image, KRaft 역할, listener와 내부 토픽 복제 수를 정의합니다. `smoke-test.sh`는 브로커를 시작하고 메시지 생산·소비 경로를 검사한 뒤 container, network와 volume을 제거합니다.

## 실행 및 검증

Docker Engine, Docker Compose v2, Bash와 Python 3이 필요합니다.

Docker를 시작하지 않고 구성 값과 shell 문법만 확인할 수 있습니다.

```sh
bash -n smoke-test.sh
./smoke-test.sh --static
```

Docker Compose를 사용할 수 있으면 `--static`이 `docker compose config`도 실행합니다. 실제 메시지 경로는 다음 명령으로 검사합니다.

```sh
./smoke-test.sh
```

검사는 Broker API 응답을 기다린 뒤 topic을 만들고 메시지 한 건을 보냅니다. 이어서 partition과 offset을 지정한 consumer와 별도 group ID를 가진 consumer가 같은 메시지를 읽는지 확인하고, 이 실행이 만든 Docker 자원만 삭제합니다. 중단 뒤 정리만 다시 실행하려면 `./smoke-test.sh --cleanup`을 사용합니다.

## 주요 설계 결정

브로커가 하나이므로 consumer group이 사용하는 내부 토픽의 replication factor와 minimum ISR을 1로 설정합니다. 먼저 직접 partition 소비를 확인한 뒤 group 소비를 검사해 일반 데이터 경로와 내부 group metadata 문제를 구분합니다.

## 구현 순서

아래 순서는 파일 배치나 과거 Git 이력이 아니라, 이 프로젝트를 처음부터 구현할 때 필요한 순서입니다. 소스의 `[Implementation N]` 주석과 번호 및 설명이 같습니다.

| 순서 | 구현 내용 | 위치 |
| ---: | --- | --- |
| 1 | 고정된 Kafka 이미지와 실행 식별자 | `compose.yaml — kafka service image and run label` |
| 2 | 단일 프로세스 KRaft 역할 | `compose.yaml — KRaft roles, quorum, and listeners` |
| 2-1 | 내부 토픽 복제 수 | `compose.yaml — offsets and transaction topic settings` |
| 3 | Kafka API 응답 기반 준비 상태 | `compose.yaml — healthcheck` |
| 4 | 독립된 Compose 실행과 정리 | `smoke-test.sh — run_integration` |

## 범위와 제한

- 브로커나 controller 장애 허용을 제공하지 않습니다.
- PLAINTEXT만 사용하며 인증, 권한 검사와 TLS를 구성하지 않습니다.
- replication factor 1은 로컬 단일 노드용 값이며 운영 권장값이 아닙니다.
- 운영용 저장소, upgrade, backup과 처리량 조정은 다루지 않습니다.
