# Inventory Reservation

PostgreSQL의 비관적 쓰기 잠금으로 같은 재고 행에 대한 동시 차감을 순서대로 처리하는 Spring Data JPA 프로젝트입니다. 실제 PostgreSQL 컨테이너에서 20개 요청을 동시에 실행해 성공 수와 최종 재고를 검증합니다.

## 주요 기능

- Flyway migration으로 재고 테이블을 만듭니다.
- Java 객체와 데이터베이스 `CHECK` 제약에서 음수 재고를 모두 막습니다.
- `PESSIMISTIC_WRITE`로 같은 재고 행을 잠근 뒤 수량을 차감합니다.
- 잠금 조회부터 상태 변경과 commit까지 하나의 transaction에서 수행합니다.
- 두 개의 latch로 작업자 준비와 시작을 나누어 경쟁 구간을 재현합니다.
- 모든 대기와 `Future` 회수에 timeout을 둡니다.
- PostgreSQL Testcontainer 이미지를 digest로 고정합니다.

## 구성

- `V1__create_inventory_item.sql`은 테이블과 음수 방지 제약을 정의합니다.
- `InventoryItem`은 가용 수량을 보관하고 차감 뒤 음수가 되지 않게 합니다.
- `InventoryRepository.findByIdForUpdate`는 대상 행을 쓰기 잠금으로 조회합니다.
- `InventoryService.reserve`는 잠금 획득, 수량 변경, commit을 같은 transaction에서 수행합니다.
- `InventoryConcurrencyIntegrationTest`는 1,000개 재고에서 100개씩 요청한 20개 작업 중 정확히 10개만 성공하는지 확인합니다.

## 요구 사항

- JDK 21
- Maven 3.9 이상
- Docker 호환 컨테이너 실행 환경

## 빌드와 테스트

```sh
mvn clean test
mvn clean package
```

통합 테스트는 digest가 고정된 `postgres:18.4-alpine` 이미지를 사용합니다. 이미지를 받을 수 있는 네트워크와 실행 중인 Docker daemon이 필요합니다.

## 로컬 PostgreSQL로 실행

기본 연결 정보는 다음과 같습니다.

- URL: `jdbc:postgresql://localhost:5432/locking`
- 사용자 이름: `locking`
- 비밀번호: `locking`

데이터베이스를 준비한 뒤 실행합니다.

```sh
mvn spring-boot:run
```

이 프로젝트는 HTTP endpoint를 제공하지 않습니다. 재고 transaction과 동시성 검증을 작은 범위에서 재현하는 프로젝트입니다.

## 주요 설계 판단

- Java process 안의 lock이 아니라 PostgreSQL row lock을 사용하므로 여러 애플리케이션 instance가 같은 행을 수정해도 데이터베이스가 순서를 정합니다.
- 재고 변경은 잠금을 얻은 transaction 안에서만 수행합니다. 잠금 조회와 commit을 다른 transaction으로 나누면 보호가 사라집니다.
- 시작 latch는 요청을 겹치게 할 뿐 정확성을 보장하지 않습니다. 성공 수와 최종 재고는 DB lock과 constraint가 보장합니다.
- 대기 시간에 상한을 두어 deadlock이나 thread 누수가 무기한 테스트 정지로 이어지지 않게 합니다.

## 구현 순서

| 순서 | 구현 내용 | 기준 파일 |
|---:|---|---|
| 0 | 독립 실행 가능한 JPA·PostgreSQL 테스트 구성 | `pom.xml` |
| 1 | datasource·Flyway·스키마 검증 연결 | `src/main/resources/application.yml` |
| 2 | 재고 테이블과 음수 방지 제약 정의 | `src/main/resources/db/migration/V1__create_inventory_item.sql` |
| 3 | 가용 수량과 차감 불변식 유지 | `src/main/java/dev/guides/spring/locking/InventoryItem.java` |
| 4 | 재고 행을 쓰기 잠금으로 조회 | `src/main/java/dev/guides/spring/locking/InventoryRepository.java` |
| 5 | 잠금 획득부터 commit까지 한 transaction에서 수행 | `src/main/java/dev/guides/spring/locking/InventoryService.java` |

## 범위와 제한

- 하나의 재고 행에서 발생하는 예약 경쟁만 다룹니다.
- lock wait timeout, deadlock 재시도, 여러 행의 잠금 순서는 구현하지 않습니다.
- 외부 호출 endpoint는 없으며 통합 테스트가 주요 검증 진입점입니다.
