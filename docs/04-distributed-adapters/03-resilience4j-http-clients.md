# Resilience4j HTTP 클라이언트

> 읽는 시점: 실제 프로젝트에서 외부 HTTP API를 호출하고 timeout, 재시도, Circuit Breaker를 적용할 때

외부 HTTP 호출에서 중요한 것은 모든 비정상 응답을 같은 실패로 처리하지 않는 것입니다. 업무상 정상적인 거절과 연결 장애, timeout, 잘못된 응답은 서로 다른 결과이며 재시도와 Circuit Breaker 기록 방식도 달라야 합니다.

## client 설정을 타입으로 받습니다

base URL, connect timeout, read timeout, 최대 연결 수, 재시도 횟수를 `@ConfigurationProperties`로 묶고 시작 단계에서 검증합니다.

- URL은 허용한 scheme의 절대 주소인지 확인합니다.
- timeout은 양수인지 확인합니다.
- 재시도 횟수에는 작은 상한을 둡니다.
- 테스트에서는 같은 property에 WireMock 주소를 주입합니다.

blocking MVC 애플리케이션에서 특별한 이유 없이 reactive client를 사용한 뒤 `.block()`으로 되돌리지 않습니다. 실행 방식에 맞는 `RestClient`나 `WebClient`를 선택합니다.

## 외부 응답을 application 의미로 바꿉니다

상대 시스템의 status와 예외를 Controller까지 전달하지 않습니다. client adapter에서 다음처럼 나눕니다.

```text
409 업무 거절           → PolicyRejectedException
429 요청 제한           → 정해진 Retry-After 처리
5xx·연결 실패·timeout   → DependencyUnavailableException
잘못된 JSON·필드 누락   → DependencyContractException
```

업무 거절은 상대 시스템이 정상적으로 판단한 결과일 수 있습니다. 반면 timeout이나 5xx는 요청 결과가 확실하지 않거나 상대 시스템을 사용할 수 없는 상태입니다.

## Circuit Breaker에는 의존성 장애만 기록합니다

업무 거절까지 실패로 기록하면 상대 시스템이 정상이어도 Circuit Breaker가 열립니다. `recordExceptions`와 `ignoreExceptions`를 실제 예외 타입에 맞춥니다.

annotation은 Spring proxy를 거쳐야 적용됩니다. 다음 경우를 주의합니다.

- 같은 객체 안에서 annotation method를 직접 호출합니다.
- 테스트에서 client 객체를 `new`로 만듭니다.
- mock만 사용하고 실제 Circuit Breaker state를 확인하지 않습니다.

WireMock을 사용하는 통합 테스트에서 연속 실패 뒤 open 상태와 open 상태에서 외부 호출을 생략하는지 확인합니다.

## 재시도 횟수와 전체 시간을 제한합니다

쓰기 요청의 timeout은 server가 아무것도 처리하지 않았다는 뜻이 아닙니다. 응답만 받지 못했을 수 있습니다. 자동 재시도 전에 다음 조건이 필요합니다.

- server가 인식하는 안정적인 idempotency key
- 전체 요청 deadline 안의 제한된 시도 횟수
- 재시도 가능한 오류의 좁은 분류
- backoff와 jitter
- 실제 외부 호출 횟수를 확인하는 테스트

같은 논리 요청을 재시도할 때 request ID를 바꾸지 않습니다. request ID가 단순 추적용인지 server가 중복 방지에 사용하는 key인지도 분명히 합니다.

## fallback이 정상 결과처럼 보이지 않게 합니다

fallback을 허용할 수 있는 기능과 허용하면 안 되는 기능을 구분합니다. fallback 응답을 반환한다면 degraded 상태를 외부 응답이나 metric에서 확인할 수 있게 합니다.

잘못된 허용이 큰 손실로 이어진다면 임의의 기본값을 반환하기보다 503으로 빠르게 실패하는 편이 낫습니다.

## WireMock으로 실패를 재현합니다

최소한 다음 상황을 테스트합니다.

- 정상 응답
- 업무 4xx
- 재시도 가능한 5xx
- 연결 지연과 read timeout
- 연결 강제 종료
- 잘못된 JSON
- Circuit Breaker open 뒤 외부 호출 횟수

테스트 시간만 재지 말고 exception type, 호출 횟수, request ID, Circuit Breaker metric, 최종 HTTP 응답을 함께 확인합니다.

## Rewind가 필요한 징후

- 409 업무 거절이 반복되자 Circuit Breaker가 열립니다.
- timeout 한 번에 무제한 재시도가 시작됩니다.
- 재시도마다 request ID가 바뀝니다.
- 잘못된 JSON이 정상 응답이나 `null`로 처리됩니다.
- fallback을 사용했지만 운영 metric에서 알 수 없습니다.

프로젝트 완료 뒤 이 능력을 확인하려면 [`policy-decision-client`](../../exercises/policy-decision-client/)를 Guide 없이 구현합니다.
