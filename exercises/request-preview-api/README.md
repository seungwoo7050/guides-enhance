# Request Preview API

Spring MVC가 요청 본문을 변환하고 검증한 뒤 업무 규칙을 적용하며, 실패 원인에 따라 서로 다른 `ProblemDetail` 응답을 반환하는 작은 Spring Boot API입니다. 설정값도 `ApplicationContext` 시작 단계에서 검증합니다.

## 주요 기능

- `@ConfigurationProperties`로 수량 범위와 허용 카테고리를 읽습니다.
- 최소 수량이 최대 수량보다 큰 설정은 애플리케이션 시작 중에 거부합니다.
- 요청 본문의 빈 값과 숫자 범위는 Bean Validation으로 검사합니다.
- 설정된 카테고리와 수량 범위를 벗어난 요청은 업무 거절로 처리합니다.
- 입력 오류와 업무 거절을 서로 다른 HTTP 상태와 `errorCode`로 반환합니다.
- MockMvc 테스트로 JSON 변환, 검증, 업무 규칙, 오류 응답을 함께 확인합니다.

## 구성

- `RequestPolicyProperties`는 `request.policy` 설정을 읽고 최소·최대 수량의 관계를 검사합니다.
- `PreviewRequest`는 HTTP 요청 본문에서 바로 확인할 수 있는 형식 조건을 선언합니다.
- `PreviewController`는 형식 검증을 통과한 요청에 카테고리와 수량 규칙을 적용합니다.
- `ProblemDetailsAdvice`는 입력 오류를 400으로, 업무 거절을 409로 변환합니다.

## 요구 사항

- JDK 21
- Maven 3.9 이상

## 빌드와 테스트

```sh
mvn clean test
mvn clean package
```

테스트는 다음 내용을 확인합니다.

- 허용 범위 안의 요청이 성공합니다.
- 0 이하 수량은 Controller의 업무 코드에 도달하기 전에 400으로 거부됩니다.
- 최대 수량을 초과한 요청은 409와 `QUANTITY_OUT_OF_RANGE`를 반환합니다.

## 실행

```sh
mvn spring-boot:run
```

정상 요청 예시:

```sh
curl -i \
  -H 'Content-Type: application/json' \
  -d '{"quantity":10,"category":"STANDARD"}' \
  http://localhost:8080/requests/preview
```

기본 설정은 수량 `1..100`과 카테고리 `STANDARD`를 허용합니다. 요청 본문 형식이 잘못되면 400을 반환하고, 형식은 맞지만 설정된 범위를 벗어나면 409를 반환합니다.

## 주요 설계 판단

- 설정 오류는 첫 요청에서 발견하지 않고 애플리케이션 시작 중에 거부합니다.
- Bean Validation은 현재 요청만으로 판단할 수 있는 형식 조건을 검사합니다.
- 운영 설정에 따라 달라지는 카테고리와 최대 수량은 Controller가 설정 객체와 비교합니다.
- 클라이언트가 입력 오류와 업무 거절을 구분할 수 있도록 status와 `errorCode`를 다르게 반환합니다.

## 구현 순서

| 순서 | 구현 내용 | 기준 파일 |
|---:|---|---|
| 0 | 독립 실행 가능한 Spring MVC 애플리케이션 구성 | `pom.xml` |
| 1 | 설정 바인딩과 수량 범위 검증 | `src/main/java/dev/guides/spring/boundaries/RequestPolicyProperties.java` |
| 2 | 요청 본문의 형식 검증 | `src/main/java/dev/guides/spring/boundaries/PreviewRequest.java` |
| 3 | 카테고리와 수량 업무 규칙 검사 | `src/main/java/dev/guides/spring/boundaries/PreviewController.java` |
| 4 | 검증 실패와 업무 거절을 ProblemDetail로 변환 | `src/main/java/dev/guides/spring/boundaries/ProblemDetailsAdvice.java` |

## 범위와 제한

- 데이터베이스와 인증 기능은 포함하지 않습니다.
- 카테고리는 설정값 하나와 정확히 일치하는지만 검사합니다.
- 오류 응답은 이 API에서 발생하는 입력 오류와 업무 거절만 정의합니다.
