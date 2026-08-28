# 선택 실습: 단일 브로커 KRaft 내부 토픽 설정

## 목표

Kafka Broker 프로세스와 일반 topic이 정상이어도 consumer group이 실패할 수 있는 설정 문제를 확인합니다. 단일 브로커에서 내부 토픽의 replication factor와 minimum ISR을 브로커 수에 맞춥니다.

이 내용은 분산 서비스의 필수 학습 경로가 아니라 Kafka 로컬 실행 환경에 한정된 선택 자료입니다.

## 일반 topic과 consumer group은 확인 대상이 다릅니다

Kafka Broker 하나를 실행하고 일반 topic을 만든 뒤 partition과 offset을 직접 지정해 소비하면 메시지를 읽을 수 있습니다. 하지만 consumer group은 `__consumer_offsets` 내부 토픽을 사용합니다.

브로커가 하나인데 내부 토픽의 replication factor를 3으로 두면 이 토픽을 만들 수 없습니다. 다음 상태가 동시에 나타날 수 있습니다.

```text
Broker process 실행 중
Kafka API 응답 성공
일반 topic produce/consume 성공
consumer group 실패
```

따라서 process health나 topic 목록 조회만으로 consumer group까지 정상이라고 판단하면 안 됩니다.

## 단일 브로커용 설정

로컬 브로커 하나에서는 다음 값을 1로 둡니다.

```text
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1
KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1
KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1
```

브로커가 하나이므로 복제 수나 minimum ISR이 1보다 크면 조건을 만족할 수 없습니다.

이 값은 운영 환경의 권장값이 아닙니다. 운영 클러스터에서는 브로커 수와 장애 허용 목표에 맞춰 다시 정해야 합니다.

## 검증 순서

1. Broker API가 응답할 때까지 기다립니다.
2. replication factor 1인 일반 topic을 만듭니다.
3. 메시지 한 건을 보냅니다.
4. partition과 offset을 지정한 consumer가 메시지를 읽는지 확인합니다.
5. 별도 group ID를 가진 consumer가 같은 메시지를 읽는지 확인합니다.
6. 이 실행이 만든 container, network와 volume만 삭제합니다.

직접 partition 소비를 먼저 확인해야 Broker의 일반 데이터 경로가 정상이라는 사실을 분리할 수 있습니다. 그다음 group 소비만 실패하면 내부 토픽 설정을 우선 확인할 수 있습니다.

## 관련 프로젝트

[`single-broker-kraft`](../../exercises/single-broker-kraft/)는 고정된 Kafka image, 단일 프로세스 KRaft 설정, API 기반 healthcheck와 독립된 smoke test를 제공합니다.

정적 검사:

```sh
cd exercises/single-broker-kraft
./smoke-test.sh --static
```

실제 Broker 검사:

```sh
./smoke-test.sh
```

## 범위와 제한

- 브로커 여러 대의 복제와 장애 조치는 다루지 않습니다.
- 인증, 권한 검사와 TLS는 구성하지 않습니다.
- 운영 저장소, upgrade와 backup은 포함하지 않습니다.

## 완료 기준

- process health와 consumer group 기능을 따로 검사할 수 있습니다.
- 단일 브로커에서 내부 토픽 복제 수를 1로 두는 이유를 설명할 수 있습니다.
- 로컬 설정을 운영 권장값으로 일반화하지 않습니다.
