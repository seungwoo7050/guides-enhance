# Application Context와 Bean 수명

> 읽는 시점: 모든 Spring Boot 백엔드 프로젝트를 시작하기 전

Spring Boot를 사용할 때 가장 먼저 이해해야 할 것은 어노테이션 목록이 아니라 `ApplicationContext`가 객체를 만들고 연결하며 종료까지 관리한다는 점입니다. 어떤 객체가 Spring에 의해 생성되는지, 요청마다 달라지는 값이 어디에 저장되는지, proxy를 거치는지 알지 못하면 트랜잭션이나 권한 검사가 우연히 동작하는 코드를 만들기 쉽습니다.

## 애플리케이션 진입점이 탐색 범위를 정합니다

`@SpringBootApplication`은 설정 클래스, 자동 설정, component scan을 묶습니다. 진입점은 애플리케이션에서 공통으로 사용하는 패키지보다 위에 둡니다.

```java
package dev.guides.catalog;

@SpringBootApplication
public class CatalogApplication {
  public static void main(String[] args) {
    SpringApplication.run(CatalogApplication.class, args);
  }
}
```

진입점의 하위 패키지에 없는 `@Service`나 `@Configuration`은 자동으로 등록되지 않습니다. 문제가 생길 때마다 `scanBasePackages`를 넓히기보다 패키지 위치를 바로잡거나 `@Import`로 어떤 설정을 포함할지 명시하는 편이 낫습니다.

## 객체는 필요한 의존성을 생성자로 받습니다

업무 객체가 repository나 client를 직접 만들지 않게 합니다.

```java
@Service
public final class CatalogService {
  private final ProjectRepository projects;
  private final Clock clock;

  public CatalogService(ProjectRepository projects, Clock clock) {
    this.projects = projects;
    this.clock = clock;
  }
}
```

생성자에는 객체가 정상적으로 동작하기 위해 반드시 필요한 협력자만 둡니다. 이렇게 하면 다음 내용을 코드에서 바로 확인할 수 있습니다.

- 객체를 만들 때 필요한 의존성
- 테스트에서 대체할 대상
- 생성 직후부터 유효해야 하는 상태

필드 주입은 객체가 완성되기 전 상태를 만들고 의존성을 숨기기 쉽습니다. 같은 타입의 Bean이 여러 개라면 무조건 `@Primary`를 붙이기보다 `@Qualifier`를 사용하거나 역할이 다른 타입으로 나누는 편이 의도가 분명합니다.

## singleton Bean에는 요청 상태를 저장하지 않습니다

기본 scope인 singleton은 JVM 전체에 하나라는 뜻이 아니라 `ApplicationContext`마다 하나라는 뜻입니다. 여러 요청이 같은 객체를 동시에 호출할 수 있으므로 다음 값은 singleton 필드에 두지 않습니다.

- 현재 사용자
- 현재 요청의 DTO
- 요청 처리 중 만든 임시 collection
- transaction마다 달라지는 entity

요청마다 달라지는 값은 method parameter로 전달하는 것이 기본입니다. 여러 요청이 공유해야 하는 상태라면 thread-safe한 자료구조를 사용하거나 데이터베이스처럼 동시 접근을 처리할 저장소에 맡깁니다. request scope는 꼭 필요한 경우에만 사용합니다. 업무 코드가 웹 요청 수명에 불필요하게 묶일 수 있기 때문입니다.

## 시작과 종료 때 수행할 일을 나눕니다

Bean은 대략 다음 순서로 사용됩니다.

```text
Bean 정의 확인
→ 객체 생성
→ 의존성 연결
→ 초기화
→ 요청 처리
→ 종료 처리
```

생성자와 `@PostConstruct`에는 빠르고 결과가 일정한 검증만 둡니다. 느린 외부 호출, 대량 데이터 보정, 메시지 발행을 넣으면 애플리케이션 시작 자체가 외부 시스템 상태에 과도하게 묶입니다.

executor, connection, background worker처럼 직접 만든 자원이 있다면 종료 방법도 함께 제공해야 합니다. 종료 신호를 받은 뒤 새 작업을 받지 않고, 진행 중인 작업을 정해진 시간 안에 마친 뒤 자원을 닫아야 합니다.

## proxy가 적용되는 호출인지 확인합니다

Spring의 `@Transactional`, method security, Resilience4j annotation은 보통 proxy가 method 호출을 가로챌 때 동작합니다.

```text
호출자
→ Spring proxy
→ 실제 Bean method
```

다음 경우에는 기대한 기능이 적용되지 않을 수 있습니다.

- 같은 객체가 자신의 annotation method를 직접 호출합니다.
- `new`로 만든 객체의 annotation method를 호출합니다.
- proxy가 가로챌 수 없는 method를 사용합니다.
- 단위 테스트에서 객체를 직접 생성하고 proxy 동작까지 검증했다고 판단합니다.

트랜잭션이나 권한 검사가 필요한 작업을 별도 Bean의 public method로 옮기면 실제 호출 경로가 분명해집니다. annotation이 붙어 있는지만 보지 말고 Spring Context를 띄운 테스트에서 commit, rollback, 권한 거절이 실제로 일어나는지 확인합니다.

## HTTP 요청이 지나가는 순서를 이해합니다

일반적인 Spring MVC 요청은 다음 순서로 처리됩니다.

```text
Filter / SecurityFilterChain
→ DispatcherServlet
→ JSON 변환과 argument binding
→ Bean Validation
→ Controller
→ application service
→ repository 또는 외부 client
→ 예외 변환과 응답 직렬화
```

각 구성 요소가 맡는 일은 다음처럼 구분하는 편이 좋습니다.

- Controller는 HTTP 입력을 검증 가능한 요청 객체로 받고 application service를 호출합니다.
- application service는 업무 처리 순서와 transaction 범위를 정합니다.
- repository는 영속 상태를 읽고 씁니다.
- 외부 client는 상대 시스템의 주소, timeout, 응답 변환을 처리합니다.
- exception advice는 공개하기로 한 실패를 HTTP 상태와 응답 본문으로 바꿉니다.

Controller가 JPA entity를 직접 요청과 응답에 사용하면 JSON 형식, 저장 형식, lazy loading이 서로 묶입니다. 요청·응답 DTO와 entity는 분리합니다.

## 확인 사항

프로젝트에 들어가기 전에 다음 질문에 답할 수 있어야 합니다.

- 어떤 객체를 Spring이 만들고 어떤 객체를 코드가 직접 만듭니까?
- 요청마다 달라지는 값이 singleton 필드에 남아 있지 않습니까?
- 외부 자원을 만든 Bean은 종료 때 해당 자원을 닫습니까?
- `@Transactional`이나 method security가 적용되는 호출은 실제로 proxy를 통과합니까?
- Controller, application service, repository, 외부 client가 각각 수행하는 일이 분명합니까?

다음 Stable Core 문서인 [`설정, 프로필과 준비 상태`](02-configuration-profiles-and-readiness.md)에서 애플리케이션이 어떤 설정으로 시작하고 언제 요청을 받을 수 있는지 확인합니다.
