# Kafka Avro Contract

하나의 Avro schema로 event를 binary 형식으로 만들고, Kafka key와 topic을 유지해 발행한 뒤, consumer가 같은 값을 복원하고 처리 성공 후에만 offset을 확정하는 Spring Boot 프로젝트입니다.

## 주요 기능

- classpath의 `.avsc` 파일을 event schema의 기준으로 사용합니다.
- `GenericRecord`로 Avro binary 데이터를 인코딩하고 디코딩합니다.
- aggregate key를 Kafka record key로 유지합니다.
- producer에 `acks=all`과 idempotence를 적용합니다.
- 발행 결과를 최대 10초 안에 확인합니다.
- consumer는 디코딩과 처리 기록이 끝난 뒤에만 수동 acknowledgement를 수행합니다.
- digest가 고정된 Apache Kafka Testcontainer로 왕복 동작을 검증합니다.

## 구성

- `task-submitted.avsc`는 event namespace, 이름, 세 필드를 정의합니다.
- `AvroEventCodec`은 producer와 consumer가 같은 schema로 데이터를 변환하게 합니다.
- `EventPublisher`는 Kafka key와 binary payload를 함께 보내고 발행 완료를 제한 시간 안에 확인합니다.
- `EventConsumer`는 payload를 `TaskSubmitted`로 복원하고 `EventProbe`에 기록한 뒤 offset을 확정합니다.
- `EventProbe`는 통합 테스트에서 소비 결과를 확인하기 위한 메모리 내 저장소입니다.

## 요구 사항

- JDK 21
- Maven 3.9 이상
- Docker 호환 컨테이너 실행 환경
- 애플리케이션을 직접 실행할 때 Kafka broker

## 빌드와 테스트

```sh
mvn clean test
mvn clean package
```

통합 테스트는 실제 Kafka container를 시작한 뒤 다음 내용을 확인합니다.

- 발행한 record key가 소비 뒤에도 같습니다.
- `taskId`, `itemCount`, `category`가 Avro 왕복 변환 뒤에도 유지됩니다.
- 정해진 시간 안에 consumer 결과를 받지 못하면 테스트가 실패합니다.

## 실행

기본 broker 주소는 `localhost:9092`이며 topic은 `guide.task.submitted.v1`입니다.

```sh
mvn spring-boot:run
```

외부 HTTP API는 제공하지 않습니다. `EventPublisher.publish`가 발행 진입점이고 `EventConsumer`가 설정된 topic을 소비합니다.

## 주요 설계 판단

- Java record에서 schema를 암묵적으로 만들지 않고 `.avsc` 파일을 별도로 유지합니다.
- 같은 aggregate의 event가 같은 partition에 들어가도록 aggregate ID를 Kafka key로 사용합니다.
- auto commit을 끄고 디코딩과 처리 기록이 모두 성공한 뒤에만 offset을 확정합니다.
- schema registry와 생성 class는 사용하지 않습니다. 이 프로젝트는 schema, key, 수동 acknowledgement 순서만 작은 범위에서 검증합니다.

## 구현 순서

| 순서 | 구현 내용 | 기준 파일 |
|---:|---|---|
| 0 | 독립 실행 가능한 Kafka·Avro 통합 테스트 구성 | `pom.xml` |
| 1 | `TaskSubmitted` event schema 정의 | `src/main/resources/avro/task-submitted.avsc` |
| 2 | 하나의 Avro schema로 인코딩·디코딩 | `src/main/java/dev/guides/spring/kafkaavro/AvroEventCodec.java` |
| 3 | 직렬화 방식·topic·수동 acknowledgement 설정 | `src/main/resources/application.yml` |
| 4 | key를 보존하고 제한 시간 안에 발행 결과 확인 | `src/main/java/dev/guides/spring/kafkaavro/EventPublisher.java` |
| 5 | 디코딩과 처리 성공 후 offset 확정 | `src/main/java/dev/guides/spring/kafkaavro/EventConsumer.java` |

`task-submitted.avsc`는 JSON 형식이므로 주석을 넣을 수 없습니다. `[Implementation 1]`은 이 표에서만 표시합니다.

## 범위와 제한

- schema 변경 호환성과 schema registry 연동은 포함하지 않습니다.
- dead-letter topic, retry topic, consumer rebalance 처리는 포함하지 않습니다.
- `EventProbe`는 영속 저장소가 아니므로 process를 재시작하면 기록이 사라집니다.
- 발행 timeout 뒤 broker에 실제로 기록되었는지 다시 확인하는 기능은 없습니다.
