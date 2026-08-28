# Flyway와 스키마 연결

> 읽는 시점: 실제 프로젝트에 데이터베이스 스키마와 migration을 추가하거나 변경할 때

JPA entity는 Java 객체와 테이블의 매핑을 표현합니다. 운영 데이터베이스가 어떤 순서로 변경되었는지는 표현하지 않습니다. Flyway migration을 스키마 변경 기록으로 사용하고, Hibernate는 `ddl-auto=validate`로 entity와 실제 스키마가 맞는지 확인하게 합니다.

## 빈 데이터베이스에서 처음부터 재현합니다

운영에 적용된 migration 파일은 수정하지 않습니다. 변경이 필요하면 다음 version을 추가합니다.

```text
V1__create_project.sql
V2__add_project_status.sql
V3__backfill_project_status.sql
V4__require_project_status.sql
```

개발자 DB를 수동으로 고쳐서만 동작하는 상태는 재현할 수 없습니다. Testcontainers의 빈 PostgreSQL에서 첫 migration부터 모두 적용하고 애플리케이션 Context가 시작되는지 확인합니다.

## 호환 가능한 순서로 변경합니다

열 이름 변경이나 필수 제약 추가는 한 번의 배포에서 끝내기 어려울 수 있습니다.

```text
새 열 추가
→ 이전 코드와 새 코드가 함께 동작하는 버전 배포
→ 기존 데이터 채우기
→ 새 열 사용 확인
→ 이전 열 제거
```

migration과 application binary의 배포 순서를 정합니다. 이전 binary로 되돌렸을 때 새 스키마와 호환되는지도 확인합니다. 긴 table lock이나 대량 backfill이 필요한 경우에는 별도 작업으로 나눕니다.

## 데이터베이스 제약을 마지막 방어 수단으로 둡니다

Bean Validation은 사용자에게 빠른 오류를 주지만 동시에 들어온 요청의 경쟁을 막지는 못합니다.

```sql
constraint ck_inventory_available
  check (available >= 0),
constraint uq_request_actor_key
  unique (actor_id, idempotency_key),
constraint fk_project_owner
  foreign key (owner_id) references account(id)
```

제약 이름을 명시하면 어떤 규칙이 깨졌는지 애플리케이션 코드와 운영 로그에서 판단하기 쉽습니다. repository 테스트에서는 제약 위반이 의도한 애플리케이션 오류로 바뀌는지 확인합니다.

## migration을 실행하는 주체를 하나로 정합니다

애플리케이션 시작 때 Flyway를 실행할지, 배포 전에 별도 job이 실행할지 선택합니다. 두 방식을 섞으면 누가 언제 스키마를 바꾸는지 불분명해집니다.

애플리케이션이 migration을 실행한다면 다음을 확인합니다.

- migration 실패 시 readiness가 성공하지 않습니다.
- 여러 instance가 동시에 시작해도 Flyway lock이 정상 동작합니다.
- 큰 변경이 요청 처리용 connection pool을 오래 점유하지 않습니다.

별도 release job이 실행한다면 application은 schema version을 확인하고 맞지 않을 때 시작을 거부해야 합니다.

## 점검 항목

- 빈 DB에서 전체 migration이 성공합니까?
- 이미 적용된 migration의 checksum이 바뀌지 않았습니까?
- `ddl-auto=validate`가 entity와 스키마 차이를 시작 단계에서 찾습니까?
- unique, check, foreign key 제약 이름이 명시되어 있습니까?
- 이전 application version과 새 스키마의 호환성을 검토했습니까?
- migration을 실행하는 주체가 하나로 정해져 있습니까?

`inventory-reservation`은 Flyway와 JPA 잠금을 함께 검증하므로 프로젝트 완료 뒤 [`inventory-reservation`](../../exercises/inventory-reservation/)에서 두 내용을 한 번에 확인할 수 있습니다.
