# Maven Artifact Boundary

## 개요

이 프로젝트는 생산 모듈과 소비 모듈의 소스 디렉터리가 나란히 있어도 Maven이 옆 디렉터리의 소스를 자동으로 사용하는 것은 아니라는 점을 재현합니다. 소비 모듈은 `groupId:artifactId:version`으로 지정한 산출물을 로컬 Maven 저장소에서 찾습니다.

두 모듈은 하나의 reactor로 묶지 않습니다. 격리한 로컬 저장소에서 생산 산출물 설치 전 실패와 설치 후 성공을 순서대로 확인합니다.

## 구성

```text
contract-library/   dev.guides:contract-library:1.0-SNAPSHOT을 만듭니다.
consumer-service/   위 좌표에 의존하고 공개 API 사용 결과를 테스트합니다.
verify.sh           격리한 로컬 저장소에서 설치 전후 결과를 확인합니다.
```

## 요구 사항

- JDK 17 이상
- Maven 3.9 이상
- 필요한 Maven 플러그인이나 테스트 의존성이 로컬에 없으면 첫 실행 시 Maven Central에 접근할 수 있는 환경

## 실행

```sh
./verify.sh
```

스크립트는 다음 순서로 실행합니다.

1. 임시 로컬 Maven 저장소를 만듭니다.
2. 기존 `contract-library` 산출물을 임시 저장소에서 제거합니다.
3. 생산 산출물을 설치하기 전 `consumer-service` 테스트가 의존성 해석 오류로 실패하는지 확인합니다.
4. `contract-library`를 같은 임시 저장소에 `install`합니다.
5. `consumer-service` 테스트가 성공하는지 확인합니다.
6. 임시 저장소, 로그와 빌드 결과를 제거합니다.

기본값은 `~/.m2/repository`를 임시 저장소의 초기 내용으로 복사합니다. 다른 저장소를 사용하려면 절대 경로를 지정합니다.

```sh
MAVEN_REPOSITORY_SEED=/path/to/repository ./verify.sh
```

Maven 실행 파일을 직접 지정할 수도 있습니다.

```sh
MAVEN=/path/to/mvn ./verify.sh
```

## 직접 빌드

```sh
mvn -f contract-library/pom.xml clean install
mvn -f consumer-service/pom.xml clean test
```

첫 번째 명령이 성공하면 현재 사용자의 기본 로컬 저장소에 생산 산출물이 설치됩니다. 설치 전 실패를 다시 확인하려면 `verify.sh`처럼 별도 저장소를 사용해야 합니다.

## 설계상 선택

루트 aggregator POM을 두지 않습니다. 두 모듈을 같은 reactor에 넣으면 Maven이 reactor 안의 생산 모듈을 직접 찾아 소비 모듈에 연결할 수 있으므로, 로컬 저장소에 설치되기 전과 후의 차이가 드러나지 않습니다.

검증할 때마다 별도 저장소를 사용합니다. 호스트의 기본 저장소에 과거 `SNAPSHOT`이 남아 있어도 설치 전 검사가 잘못 성공하지 않습니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | 생산 모듈의 산출물 좌표와 Java 빌드 설정을 정의합니다. | `contract-library/pom.xml` |
| 1-1 | 소비 모듈이 사용할 공개 버전 값을 제공합니다. | `contract-library/src/main/java/dev/guides/contract/ContractVersion.java` |
| 2 | 소비 모듈이 생산 모듈의 산출물 좌표에 의존하도록 설정합니다. | `consumer-service/pom.xml` |
| 2-1 | 설치된 contract-library 산출물의 공개 API를 사용합니다. | `consumer-service/src/main/java/dev/guides/consumer/ConsumerApplication.java` |
| 3 | 격리한 로컬 저장소에서 설치 전 실패와 설치 후 성공을 재현합니다. | `verify.sh` |

## 범위와 제한

- `SNAPSHOT` 산출물의 로컬 설치와 의존성 해석만 다룹니다.
- 원격 저장소 배포, 서명, release 승격과 버전 충돌 해결은 포함하지 않습니다.
- 필요한 Maven 플러그인과 테스트 의존성이 로컬에 없으면 최초 실행 시 네트워크가 필요할 수 있습니다.
