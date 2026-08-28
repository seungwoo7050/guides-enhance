# Spring Kafka와 Avro 어댑터

> 읽는 시점: 실제 프로젝트에서 Kafka producer, consumer, Avro schema를 구현할 때

이 문서는 Kafka의 모든 전달 보장을 다시 설명하지 않습니다. Spring Kafka에서 producer, listener container, serializer, acknowledgement를 실제 broker와 연결하고 검증하는 방법에 집중합니다.

## 이벤트 이름과 schema를 한곳에서 관리합니다

생산자와 소비자가 이벤트 종류, 토픽, 키 규칙을 서로 다른 문자열로 관리하면 일부 값이 어긋나도 애플리케이션은 정상적으로 시작될 수 있습니다. 다음 값을 한곳에서 관리합니다.

```text
topic: publication-events
event type: publication.created.v1
key: publicationId
schema: schemas/publication-created-v1.avsc
```

Spring 설정, 테스트 fixture, 배포 설정이 같은 값을 사용하게 합니다. Context가 시작되었다는 사실만으로 listener가 올바른 topic을 구독했다고 판단하지 않습니다.

## key와 value 직렬화 방식을 양쪽에 고정합니다

producer와 consumer에서 key serializer와 value serializer를 명시합니다. Avro logical type, namespace, enum symbol이 서로 호환되는지도 확인합니다.

생성 class를 사용하든 `GenericRecord`를 사용하든 schema 원본을 여러 곳에 복사하지 않습니다. payload 전체를 오류 로그에 남기지 말고 다음 정보를 진단에 사용합니다.

- event ID
- event type
- key
- topic, partition, offset
- schema version

## 처리 성공 뒤에 offset을 확정합니다

수동 acknowledgement를 사용한다면 데이터를 정상적으로 처리한 뒤 offset을 전진시킵니다.

```text
record 수신
→ 역직렬화와 schema 검사
→ 업무 처리와 DB commit
→ acknowledgment
```

acknowledgement 전에 process가 종료되면 같은 record가 다시 전달될 수 있습니다. consumer는 중복 전달을 정상적인 입력으로 다뤄야 합니다. 반대로 먼저 acknowledge하면 뒤의 실패에서 record를 잃을 수 있습니다.

ack mode와 transaction manager 조합이 실제로 어떻게 동작하는지는 broker를 사용하는 통합 테스트로 확인합니다.

## 오류 종류에 따라 처리 방법을 나눕니다

다음 오류를 하나의 retry 규칙으로 처리하지 않습니다.

- Avro 역직렬화와 schema 호환성 오류
- 일시적인 데이터베이스나 외부 시스템 장애
- 재시도해도 결과가 바뀌지 않는 업무 거절
- 예상하지 못한 programming defect

재시도나 dead-letter topic을 사용한다면 원본 topic, partition, offset, event ID를 보존합니다. 수동 재처리 도구가 같은 업무 효과를 다시 만들지 않도록 consumer의 멱등 처리를 먼저 준비합니다.

## consumer 시작과 종료를 확인합니다

consumer가 partition assignment를 받았는지, 종료 중 새 record를 받는지, 처리 중인 작업을 얼마나 기다리는지 확인합니다.

운영에서 확인할 값은 다음과 같습니다.

- consumer lag
- 처리 성공과 실패 수
- retry와 dead-letter 수
- 처리 시간
- rebalance 횟수

고유 event ID나 aggregate ID를 metric tag로 넣지 않습니다. 이 값은 로그나 trace에 남깁니다.

## Rewind가 필요한 징후

- producer는 발행에 성공하지만 consumer가 record를 받지 못합니다.
- 같은 aggregate의 event 순서가 뒤섞입니다.
- 처리 실패 뒤에도 offset이 앞으로 이동합니다.
- malformed payload가 무한히 재시도됩니다.
- listener 종료 중 처리하던 작업이 설명 없이 사라집니다.

Kafka와 Avro 처리 능력을 별도로 확인하려면 전문 주제 프로젝트인 [`kafka-avro-contract`](../../exercises/kafka-avro-contract/)를 수행합니다.
