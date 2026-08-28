# PostgreSQL Concurrency Guards

각각은 성공할 수 있지만 함께 실행하면 업무 규칙을 깨뜨리는 두 사례를 PostgreSQL 함수로 막는 프로젝트입니다. 재고 차감은 한 행의 조건부 `UPDATE`로 처리하고, 여러 의사 행에 걸친 당직 조건은 모든 변경 함수가 공유하는 guard row로 순서를 정합니다.

## 주요 기능

- 수량 확인과 차감을 한 문장으로 처리하는 `reserve_inventory`
- 최소 한 명의 당직자를 남기는 `take_off_call`
- write skew를 막기 위한 `shift_guard` 행 잠금
- 독립된 두 `psql` process를 사용하는 동시 실행 검사
- 제한 시간 안에 끝나지 않는 hang과 deadlock을 실패로 처리

## 파일 구성

- `setup.sql`: inventory, doctor와 공용 guard row를 만듭니다.
- `functions.sql`: 두 PL/pgSQL 함수를 정의합니다.
- `scripts/test.sh`: 두 session을 실제로 겹쳐 실행합니다.
- `compose.yaml`: PostgreSQL 16 실행 환경을 제공합니다.

## 실행

Docker Engine과 Docker Compose v2가 필요합니다.

```bash
make test
```

첫 검사는 재고가 10개일 때 7개 예약 두 건을 동시에 실행해 한 건만 성공하는지 확인합니다. 다음 검사는 당직 의사 두 명을 동시에 해제해 한 건만 성공하고 한 명이 남는지 확인합니다.

```sql
SELECT reserve_inventory('book', 2);
SELECT take_off_call(1);
```

두 함수는 변경이 허용되면 `true`, 현재 상태가 조건을 만족하지 않으면 `false`를 반환합니다. 0 이하의 예약 수량은 예외로 거부합니다.

## 설계에서 확인할 점

- `SELECT` 결과를 애플리케이션에서 판단한 뒤 `UPDATE`하지 않습니다. 재고 확인과 차감을 같은 `UPDATE`에 넣어 두 요청이 같은 재고 행에서 순서대로 처리되게 합니다.
- 의사별 행만 잠그면 두 transaction이 서로 다른 행을 변경하면서 당직자가 0명이 될 수 있습니다. 당직자를 줄이는 모든 함수가 `shift_guard(id=1)`을 먼저 잠가 같은 순서로 검사하게 합니다.
- 순차 호출만으로는 동시성 오류를 검출할 수 없습니다. 검사는 별도 `psql` process를 겹쳐 실행하고 성공 건수와 최종 행을 확인합니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | 동시 실행용 데이터와 공용 guard row | `setup.sql` |
| 2 | 조건부 UPDATE 재고 예약 | `functions.sql` · `reserve_inventory` |
| 3 | 여러 의사 행을 보호하는 공용 guard | `functions.sql` · `take_off_call` |
| 4 | 실제로 겹쳐 실행되는 두 session 검증 | `scripts/test.sh` |

## 범위와 제한

이 프로젝트는 두 업무 규칙과 PostgreSQL의 기본 transaction 동작만 다룹니다. 일반 lock manager, 분산 transaction, 자동 재시도, idempotency key, queue consumer와 외부 시스템 호출은 포함하지 않습니다.
