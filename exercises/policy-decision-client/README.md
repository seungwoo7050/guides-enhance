# Policy Decision Client

외부 판단 API의 업무 거절과 시스템 장애를 구분하고, 연결·읽기 timeout, 제한된 재시도, Resilience4j Circuit Breaker를 적용한 Spring Boot HTTP 클라이언트입니다.

## 주요 기능

- 외부 주소, timeout, 최대 시도 횟수를 설정 타입으로 받습니다.
- 잘못된 주소, 0 이하 timeout, 허용 범위를 벗어난 시도 횟수는 시작 단계에서 거부합니다.
- `Duration` 값을 실제 HTTP 요청의 연결·읽기 timeout에 적용합니다.
- 한 요청은 최대 두 번만 시도합니다.
- 재시도할 때 같은 `DecisionRequest`와 `requestId`를 사용합니다.
- 409 업무 거절은 재시도하지 않고 Circuit Breaker 실패에도 포함하지 않습니다.
- 5xx, 연결 종료, timeout, 잘못된 JSON은 의존성 장애로 처리합니다.
- WireMock 테스트로 호출 횟수, 요청 본문, Circuit Breaker 상태를 확인합니다.

## 구성

- `DecisionClientProperties`는 base URL, 연결·읽기 timeout, 최대 시도 횟수를 검증합니다.
- `DecisionClientConfiguration`은 검증된 timeout을 `SimpleClientHttpRequestFactory`에 적용합니다.
- `DecisionClient`는 정해진 횟수 안에서만 요청을 다시 보내고, 업무 거절과 의존성 장애를 다른 예외로 반환합니다.
- `application.yml`은 `DependencyUnavailableException`만 Circuit Breaker 실패로 기록합니다.

## 요구 사항

- JDK 21
- Maven 3.9 이상

## 빌드와 테스트

```sh
mvn clean test
mvn clean package
```

테스트는 process 내부에서 WireMock을 실행하므로 Docker가 필요하지 않습니다. 다음 내용을 확인합니다.

- 409 응답을 반복해도 Circuit Breaker가 열리지 않습니다.
- 500 응답이 정해진 횟수만큼 기록되면 Circuit Breaker가 열립니다.
- 읽기 timeout, 연결 강제 종료, 잘못된 JSON을 모두 의존성 장애로 반환합니다.
- 첫 요청이 실패한 뒤 두 번째 요청에서도 같은 `requestId`를 보냅니다.

## 실행

기본 외부 주소는 `http://localhost:18080/decision`입니다.

```sh
mvn spring-boot:run
```

이 프로젝트는 외부에서 호출할 Controller를 제공하지 않습니다. 다른 Spring component가 `DecisionClient.check`를 호출해 사용하는 어댑터입니다.

## 주요 설계 판단

- 409는 상대 시스템이 정상적으로 내린 업무 판단입니다. 이를 장애로 기록하면 정상적인 거절만으로 Circuit Breaker가 열릴 수 있습니다.
- 재시도는 framework 기본 설정에 맡기지 않고 짧은 loop와 최대 횟수로 제한합니다. 테스트에서 실제 호출 횟수를 직접 확인합니다.
- timeout은 상대 서버가 요청을 처리하지 않았다는 뜻이 아닙니다. 쓰기 API에 사용할 경우 `requestId`를 서버가 인식하는 멱등성 key와 연결해야 합니다.
- 잘못된 JSON은 상대 시스템의 응답 형식을 신뢰할 수 없는 상태이므로 성공으로 처리하지 않습니다.

## 구현 순서

| 순서 | 구현 내용 | 기준 파일 |
|---:|---|---|
| 0 | 독립 실행 가능한 HTTP 클라이언트·복원력 테스트 구성 | `pom.xml` |
| 1 | 주소·timeout·재시도 횟수 검증 | `src/main/java/dev/guides/spring/failclosed/DecisionClientProperties.java` |
| 2 | 연결·읽기 timeout을 실제 HTTP 요청에 적용 | `src/main/java/dev/guides/spring/failclosed/DecisionClientConfiguration.java` |
| 3 | 정해진 횟수만 재시도하고 실패 유형 구분 | `src/main/java/dev/guides/spring/failclosed/DecisionClient.java` |
| 4 | Circuit Breaker에 의존성 장애만 기록 | `src/main/resources/application.yml` |

## 범위와 제한

- 재시도 간격, jitter, backoff는 포함하지 않습니다.
- bulkhead, rate limiter, 분산 tracing 전달은 포함하지 않습니다.
- 요청 본문은 메모리에 보관된 record이므로 같은 값을 다시 보낼 수 있습니다.
- 외부 시스템이 `requestId`를 실제 멱등성 key로 처리하는지는 이 클라이언트가 보장하지 않습니다.
