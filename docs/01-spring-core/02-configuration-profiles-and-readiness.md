# 설정, 프로필과 준비 상태

> 읽는 시점: 모든 Spring Boot 백엔드 프로젝트를 시작하기 전

운영 설정은 단순한 문자열 모음이 아니라 애플리케이션이 시작할 때 받는 입력입니다. 주소, 제한값, 시간 단위가 잘못되었다면 첫 요청이 들어올 때까지 기다리지 말고 `ApplicationContext`를 만드는 단계에서 실패해야 합니다.

## 관련 값을 하나의 타입으로 묶습니다

여러 `@Value`에 설정을 흩어 놓으면 이름, 단위, 기본값과 검증 규칙을 한눈에 확인하기 어렵습니다. 같은 기능에 쓰는 값은 `@ConfigurationProperties`로 묶습니다.

```java
@ConfigurationProperties("client.policy")
@Validated
public record PolicyClientProperties(
    @NotBlank String baseUrl,
    @NotNull Duration connectTimeout,
    @NotNull Duration readTimeout,
    @Positive int maxConnections) {

  public PolicyClientProperties {
    if (readTimeout != null && connectTimeout != null
        && readTimeout.compareTo(connectTimeout) < 0) {
      throw new IllegalArgumentException(
          "readTimeout은 connectTimeout보다 짧을 수 없습니다.");
    }
  }
}
```

- 시간과 용량은 `Duration`, `DataSize`처럼 단위가 드러나는 타입으로 받습니다.
- 한 값의 범위는 Bean Validation으로 검사합니다.
- 여러 값 사이의 관계는 compact constructor나 별도 validator에서 검사합니다.
- 설정 객체는 외부 요청이나 데이터 변경을 수행하지 않습니다.

`@ConfigurationPropertiesScan` 또는 `@EnableConfigurationProperties`로 설정 객체를 등록합니다. 테스트에서는 실제 Context를 띄워 파일이나 환경 변수의 값이 예상한 타입으로 변환되는지도 확인합니다.

## 기본값은 누락을 숨기지 않을 때만 사용합니다

개발 환경에서 편한 기본값이 운영 설정 누락까지 감출 수 있습니다.

- timeout, batch size처럼 안전한 범위가 분명한 값은 기본값을 둘 수 있습니다.
- credential, 공개 host, 암호화 key는 운영 환경에서 반드시 제공하게 합니다.
- 비밀값은 로그, 예외 메시지, Actuator 응답에 포함하지 않습니다.
- 환경 변수 이름을 바꾸면 배포 설정과 CI도 함께 바꿉니다.

설정 source의 우선순위를 이용해 임의로 덮어쓰기보다 어떤 값을 파일, 환경 변수, command line에서 받을지 문서화합니다. 최소한 기본 설정, 정상 운영 설정, 잘못된 설정의 시작 실패를 테스트합니다.

## profile은 실행 환경 차이를 표현합니다

profile은 local, test, production처럼 실행 환경에 따라 달라지는 값을 묶는 데 사용합니다.

```text
local       로컬 애플리케이션과 개발용 의존성
test        Testcontainers, 고정 Clock, 짧은 poll interval
production  외부 주소와 비밀값 필수, 진단 정보 공개 제한
```

세부 기능마다 profile을 추가하면 가능한 조합이 빠르게 늘어납니다. 기능을 켜고 끄는 값이 필요하다면 별도 설정으로 두고 기본값, 제거 시점, 활성 여부를 확인할 metric을 정합니다.

## 프로세스가 실행 중인 것과 요청 가능한 상태를 구분합니다

Spring Context가 만들어졌다고 해서 항상 새 요청을 받을 준비가 끝난 것은 아닙니다.

- **liveness**는 프로세스를 재시작해야만 회복할 수 있는 상태인지 나타냅니다.
- **readiness**는 지금 새 요청을 받아도 되는지 나타냅니다.

일시적인 Kafka 지연이나 외부 API 장애 때문에 liveness를 실패시키면 불필요한 재시작이 반복될 수 있습니다. 반대로 필수 migration이 실패했거나 로컬 자원 초기화가 끝나지 않았다면 readiness는 성공하면 안 됩니다.

health 확인마다 느린 외부 요청을 새로 보내지 않습니다. readiness는 짧게 평가하고, 자세한 원인은 로그와 metric으로 확인합니다.

## 종료 순서를 정합니다

정상 종료도 시작 설정만큼 중요합니다. 일반적인 종료 순서는 다음과 같습니다.

```text
readiness 해제
→ 새 요청과 새 background 작업 거부
→ 진행 중인 요청과 transaction 완료 대기
→ consumer, scheduler, executor 중지
→ connection과 ApplicationContext 종료
```

무한히 기다리게 하지 말고 종료 제한 시간을 둡니다. 진행 중 작업이 중간에 끊길 수 있다면 Outbox나 멱등 처리처럼 재시작 뒤 이어서 처리할 방법을 별도로 마련합니다.

## 확인 사항

- 관련 설정이 한 `@ConfigurationProperties` 타입에 모여 있습니까?
- 시간과 크기 값에 단위가 명시되어 있습니까?
- 잘못된 값이 첫 요청이 아니라 시작 단계에서 거부됩니까?
- 운영에서 반드시 필요한 값에 위험한 기본값을 두지 않았습니까?
- liveness와 readiness가 같은 의미로 사용되지 않습니까?
- background worker와 connection의 종료 순서가 정해져 있습니까?

다음 Stable Core 문서인 [`Spring MVC 검증과 ProblemDetail`](../02-web-and-security/01-mvc-validation-and-problem-detail.md)에서 요청 입력과 오류 응답을 처리하는 방법을 확인합니다.
