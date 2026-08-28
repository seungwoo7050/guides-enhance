# Maven Wrapper와 빌드 수명 주기

소스가 같아도 JDK, Maven, 플러그인과 로컬 저장소 상태가 다르면 빌드 결과가 달라질 수 있습니다. Maven을 배우는 목적은 POM 문법을 외우는 것이 아니라 어떤 입력으로 소스를 컴파일하고 테스트하며 산출물을 만드는지 이해하는 데 있습니다.

## Maven과 Wrapper

시스템에 설치한 Maven은 `mvn`으로 실행합니다.

```sh
mvn -version
```

프로젝트에 Maven Wrapper가 포함되어 있다면 다음 명령을 사용합니다.

```sh
./mvnw -version
```

Wrapper는 프로젝트가 사용할 Maven 배포본을 고정합니다. JDK까지 설치하거나 고정하지는 않으므로 출력에서 Maven이 실제로 사용하는 Java 버전과 경로를 확인합니다.

이 저장소의 standalone exercise는 시스템 Maven을 사용합니다. 각 프로젝트 디렉터리에서 다음 명령으로 빌드합니다.

```sh
mvn clean test
```

## 실행 JDK와 컴파일 대상

Maven 자체를 실행하는 JDK와 컴파일할 Java release는 다를 수 있습니다.

```xml
<properties>
  <maven.compiler.release>17</maven.compiler.release>
</properties>
```

`maven.compiler.release`는 사용할 수 있는 표준 API와 생성할 클래스 파일 버전을 함께 제한합니다. JDK 21에서 Maven을 실행하면서 Java 17을 대상으로 컴파일할 수도 있습니다.

## POM과 산출물 좌표

Maven 산출물은 기본적으로 다음 세 값으로 식별합니다.

```text
groupId:artifactId:version
```

예를 들면 다음과 같습니다.

```text
dev.guides.java:number-report:1.0.0
```

`pom.xml`에는 프로젝트 좌표, Java release, 의존성, 플러그인과 빌드 설정을 작성합니다. 소스 디렉터리가 옆에 있다는 사실만으로 두 프로젝트가 연결되지는 않습니다. 소비 프로젝트의 POM이 정확한 산출물 좌표를 의존성으로 선언해야 합니다.

## 기본 디렉터리

Maven은 일반적으로 다음 경로를 사용합니다.

```text
src/main/java/       실행 코드
src/main/resources/  실행 시 필요한 파일
src/test/java/       테스트 코드
src/test/resources/  테스트용 파일
target/              컴파일 결과와 산출물
```

`target/`은 빌드할 때 다시 만들 수 있으므로 Git에 커밋하지 않습니다.

## 수명 주기 단계

| 단계 | 수행하는 작업 |
| --- | --- |
| `validate` | 프로젝트 설정과 필요한 정보를 확인합니다. |
| `compile` | `src/main/java`를 컴파일합니다. |
| `test` | 테스트 코드를 컴파일하고 단위 테스트를 실행합니다. |
| `package` | JAR 같은 산출물을 만듭니다. |
| `verify` | package 이후에 연결한 추가 검사를 실행합니다. |
| `install` | 산출물을 로컬 Maven 저장소에 설치합니다. |
| `deploy` | 산출물을 원격 저장소에 게시합니다. |

뒤 단계는 앞 단계를 포함합니다. 예를 들어 `mvn test`는 컴파일도 수행하고, `mvn package`는 테스트까지 수행합니다. 다만 POM에서 테스트를 건너뛰도록 설정했다면 실제 실행 내용은 달라질 수 있습니다.

`package` 성공만으로 정적 검사나 통합 테스트까지 통과했다고 말할 수는 없습니다. 어떤 검사가 어느 단계에 연결되어 있는지 POM을 확인합니다.

## 의존성 scope

| scope | 사용 범위 |
| --- | --- |
| `compile` | 실행 코드의 컴파일과 실행에 필요합니다. 기본값입니다. |
| `runtime` | 컴파일에는 필요 없지만 실행할 때 필요합니다. |
| `test` | 테스트 컴파일과 실행에만 필요합니다. |
| `provided` | 컴파일에는 필요하지만 실행 환경이 제공한다고 가정합니다. |

JUnit과 AssertJ는 보통 `test` scope로 선언합니다. 테스트 라이브러리가 실행 산출물에 불필요하게 포함되지 않게 하기 위해서입니다.

## dependency management와 실제 dependency

`dependencyManagement`는 사용할 버전을 모아 두지만 의존성을 자동으로 추가하지 않습니다. 실제로 사용할 모듈은 `<dependencies>`에 다시 선언해야 합니다.

```xml
<dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>org.junit</groupId>
      <artifactId>junit-bom</artifactId>
      <version>${junit.version}</version>
      <type>pom</type>
      <scope>import</scope>
    </dependency>
  </dependencies>
</dependencyManagement>
```

BOM은 관련 라이브러리의 버전을 맞출 수 있지만 Maven compiler, Surefire와 formatter 같은 플러그인 버전까지 정해 주지는 않습니다. 빌드 결과에 영향을 주는 주요 플러그인 버전도 명시합니다.

## parent와 reactor

여러 Maven module을 한 저장소에서 함께 빌드할 때는 루트 POM을 parent나 aggregator로 사용할 수 있습니다.

- parent POM은 공통 속성, dependency management와 plugin 설정을 상속시킵니다.
- aggregator POM은 `<modules>`에 적힌 프로젝트를 한 reactor에서 함께 빌드합니다.

두 역할을 한 POM이 같이 맡을 수도 있지만 같은 개념은 아닙니다.

reactor 안의 module을 선택할 때는 다음 옵션을 사용할 수 있습니다.

```sh
mvn -pl :module-artifact-id -am test
```

- `-pl`은 실행할 module을 선택합니다.
- `-am`은 선택한 module이 필요로 하는 reactor module도 함께 빌드합니다.

## 로컬 Maven 저장소

Maven의 로컬 저장소는 소스 체크아웃이 아니라 이미 만든 산출물과 메타데이터를 저장합니다. 기본 경로는 보통 `~/.m2/repository`입니다.

생산 프로젝트의 소스를 수정해도 다시 `install`하지 않으면 소비 프로젝트는 로컬 저장소에 남은 예전 산출물을 사용할 수 있습니다.

별도 저장소를 사용하면 숨은 상태를 찾을 수 있습니다.

```sh
repository=$(mktemp -d)
mvn -Dmaven.repo.local="$repository" clean test
```

[Maven Artifact Boundary](../../exercises/maven-artifact-boundary/README.md)는 다음 순서를 자동으로 확인합니다.

```text
생산 산출물 없음
→ 소비 프로젝트 의존성 해석 실패
→ 생산 프로젝트 install
→ 같은 저장소에서 소비 프로젝트 성공
```

이 프로젝트는 선택 자료입니다. 단일 Maven 프로젝트를 빌드하는 데 필수는 아니지만, 서로 독립된 저장소를 연결할 때 오래된 `SNAPSHOT` 때문에 생기는 잘못된 성공을 이해하는 데 도움이 됩니다.

## 실제 적용 결과 확인

POM에 적힌 값뿐 아니라 parent와 profile까지 적용한 최종 설정을 확인합니다.

```sh
mvn help:effective-pom
mvn dependency:tree
```

- `effective-pom`은 실제로 적용된 속성, dependency와 plugin 설정을 보여 줍니다.
- `dependency:tree`는 직접 의존성과 그 의존성이 가져온 라이브러리를 보여 줍니다.

버전 충돌이나 예상하지 못한 라이브러리가 들어온 경우 두 결과를 먼저 확인합니다.

## 다시 만들 수 있는 빌드에 필요한 정보

다음 값은 빌드 결과에 영향을 줍니다.

- JDK와 Maven 버전
- Java release
- dependency와 plugin 버전
- 소스 인코딩과 시간대
- 활성화한 Maven profile
- 환경 변수
- 생성한 소스와 리소스
- 운영체제에 따라 달라지는 명령

테스트가 기본 timezone이나 locale에 기대지 않게 하고, 필요한 값은 POM이나 테스트 코드에 명시합니다.

## 자주 쓰는 명령

| 목적 | 명령 |
| --- | --- |
| Maven과 JDK 확인 | `mvn -version` |
| 단위 테스트 | `mvn test` |
| JAR 생성 | `mvn package` |
| 추가 검사까지 실행 | `mvn verify` |
| 로컬 저장소에 설치 | `mvn install` |
| 한 테스트 클래스 실행 | `mvn -Dtest=ClassName test` |
| 의존성 확인 | `mvn dependency:tree` |
| 최종 POM 확인 | `mvn help:effective-pom` |
| 빌드 결과 삭제 | `mvn clean` |

`-DskipTests`는 테스트 실행을 건너뛰지만 테스트 소스는 컴파일할 수 있습니다. `-Dmaven.test.skip=true`는 테스트 컴파일도 생략합니다. 일반 검증에서는 사용하지 않습니다.

## 완료 기준

- Maven과 Wrapper의 역할을 구분합니다.
- Maven을 실행하는 JDK와 컴파일할 Java release를 구분합니다.
- `test`, `package`, `verify`, `install`이 확인하는 범위를 설명합니다.
- dependency scope와 `dependencyManagement`의 역할을 설명합니다.
- parent와 aggregator reactor의 차이를 설명합니다.
- 로컬 저장소의 산출물과 현재 소스가 서로 다른 상태일 수 있음을 이해합니다.
- `effective-pom`과 `dependency:tree`로 실제 빌드 설정을 확인합니다.

다음 문서는 [JUnit·AssertJ와 테스트 대역](02-junit-assertj-and-test-doubles.md)입니다.
