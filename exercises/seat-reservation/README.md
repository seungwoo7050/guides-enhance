# Seat Reservation

PostgreSQL과 Kysely로 구현한 좌석 예약 프로젝트입니다. 같은 행사와 좌석 번호의 중복 예약을 **데이터베이스 고유 제약**으로 막고, 예약 행과 감사 행을 **하나의 트랜잭션**에서 저장합니다.

이 exercise의 핵심은 애플리케이션에서 먼저 조회한 결과를 믿는 것이 아니라, 실제 경쟁 상황에서도 데이터베이스가 최종 무결성을 보장하게 만드는 것입니다.

## 주요 기능

- 행사, 예약, 예약 감사 테이블
- 좌석 번호 양수 검사
- `(event_id, seat_no)` 고유 제약
- Kysely 테이블 타입
- SQL 마이그레이션 실행
- 예약과 감사 기록의 원자적 저장
- PostgreSQL `23505`를 `SeatTakenError`로 변환
- 실제 경쟁 요청과 롤백 테스트

## 데이터베이스 실행

```sh
export POSTGRES_PORT=55432
docker compose up -d --wait
export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:55432/reservation
```

포트를 바꾸면 `POSTGRES_PORT`와 `DATABASE_URL`을 함께 바꿉니다.

두 값이 서로 다른 포트를 가리키면 Docker의 PostgreSQL은 정상적으로 떠 있어도 애플리케이션은 다른 주소로 연결을 시도할 수 있습니다.

## 설치와 검증

```sh
npm install
npm run typecheck
npm run migrate
npm test
```

순서는 다음 의미를 가집니다.

```text
typecheck
→ Kysely 타입과 애플리케이션 타입 검사

migrate
→ 실제 PostgreSQL에 필요한 schema와 constraint 생성

test
→ 실제 DB에서 경쟁·rollback·parameter binding 검증
```

테스트가 끝나면 테스트 데이터베이스와 volume을 제거합니다.

```sh
docker compose down -v
```

`-v`는 이 compose 환경에서 사용하는 volume도 제거합니다. 보존해야 할 데이터가 있는 환경에서 같은 명령을 무심코 사용하지 않습니다.

## 데이터베이스가 보장하는 예약 규칙

같은 행사에서 같은 좌석 번호가 두 번 예약되지 않게 하는 최종 규칙은 다음 고유 제약입니다.

```text
(event_id, seat_no) UNIQUE
```

애플리케이션에서 다음처럼 먼저 조회하는 것만으로는 충분하지 않습니다.

```text
SELECT 예약 존재 여부
→ 없음
→ INSERT
```

두 요청이 동시에 실행되면 둘 다 "없음"을 볼 수 있기 때문입니다.

```text
request A → 없음 확인
request B → 없음 확인
request A → INSERT
request B → INSERT
```

따라서 실제 최종 판정은 PostgreSQL 고유 제약이 맡습니다.

```text
둘 중 첫 INSERT
→ 성공

다른 INSERT
→ unique violation
→ PostgreSQL SQLSTATE 23505
```

애플리케이션은 이 특정 오류만 `SeatTakenError`로 변환합니다.

## 오류 매핑

모든 PostgreSQL 오류를 `SeatTakenError`로 바꾸면 실제 장애를 좌석 충돌처럼 숨길 수 있습니다.

따라서 다음을 구분합니다.

```text
SQLSTATE 23505
→ 좌석 고유 제약 위반
→ SeatTakenError로 변환

연결 실패
trigger 실패
SQL 문법 오류
기타 DB 오류
→ 원인을 유지해 상위로 전달
```

정확히 어떤 고유 제약의 `23505`인지 구분해야 하는 구현이라면 constraint 이름까지 확인하는 방법도 있지만, 이 exercise의 범위에서는 제공된 예약 규칙에 집중합니다.

## 트랜잭션

좌석 예약과 감사 기록은 하나의 논리적 작업입니다.

원하는 결과:

```text
예약 성공 + 감사 성공
또는
예약 없음 + 감사 없음
```

다음 상태는 허용하지 않습니다.

```text
예약은 저장됨
감사 기록은 실패
```

따라서 같은 Kysely `trx` 객체 안에서 두 쓰기를 수행합니다.

개념적으로:

```text
BEGIN

reservation INSERT
audit INSERT

둘 다 성공
→ COMMIT

하나라도 실패
→ ROLLBACK
```

## 롤백 테스트

테스트는 감사 테이블 삽입을 의도적으로 실패시키는 임시 trigger를 설치합니다.

```text
reservation INSERT 성공
→ audit INSERT 시 trigger가 오류 발생
→ transaction 실패
→ reservation INSERT도 rollback
```

테스트는 함수가 예외를 던졌다는 사실만 보는 것이 아니라 실제 DB를 조회해 예약 행이 남지 않았는지 확인합니다.

이 차이가 중요합니다.

```text
예외 발생
≠
DB rollback이 실제로 완료됨
```

## 실제 경쟁 테스트

같은 좌석을 두 요청이 경쟁하도록 실행합니다.

```text
request A ─┐
           ├─ 같은 event_id + seat_no
request B ─┘
```

원하는 결과:

```text
정확히 하나 성공
정확히 하나 SeatTakenError
DB에는 예약 한 건
```

단순한 순차 호출:

```text
A 완료
→ B 시작
```

은 실제 경쟁 조건을 검증하지 못합니다.

테스트는 두 요청을 겹쳐 실행하고 PostgreSQL 고유 제약이 실제 경쟁 상황에서도 최종 무결성을 지키는지 확인합니다.

## 좌석 번호 제약

좌석 번호는 양수여야 합니다.

이런 도메인 제약을 데이터베이스에도 두면 애플리케이션의 특정 코드 경로를 거치지 않은 쓰기에도 무결성이 유지됩니다.

```text
seat_no > 0
```

애플리케이션 검증은 빠른 오류 메시지를 제공할 수 있고, DB 제약은 최종 방어선이 됩니다.

## 매개변수 바인딩

사용자 값을 SQL 문자열에 직접 이어 붙이지 않습니다.

잘못된 방향:

```text
"... values (" + userInput + ")"
```

Kysely의 `.values()`와 SQL 템플릿 매개변수를 사용해 값과 SQL 구조를 분리합니다.

```text
SQL 구조
+
별도 parameter 값
```

테스트는 사용자 입력이 SQL 코드 조각으로 실행되지 않는지 확인합니다.

## 연결 풀 정리

DB 연결을 만들었으면 테스트와 마이그레이션 종료 시 pool도 닫아야 합니다.

그렇지 않으면:

```text
테스트 assertion 완료
→ 열린 DB socket이 남음
→ Node.js 프로세스가 종료되지 않음
```

같은 문제가 생길 수 있습니다.

## 테스트

테스트는 실제 PostgreSQL에서 다음 잘못된 구현을 검출합니다.

- 같은 좌석의 두 예약이 모두 성공함
- 예약은 저장됐지만 감사 기록은 실패한 상태가 남음
- 사용자 입력이 SQL 문장으로 결합됨
- 테스트 종료 뒤 연결 풀이 남음

즉 메모리 repository mock으로는 확인할 수 없는 실제 DB 특성을 검사합니다.

## 코드 구성

- `migrations/001_initial.sql`: 테이블과 제약 조건
- `src/db.ts`: Kysely 타입과 PostgreSQL 연결 생성
- `src/migrate.ts`: SQL 파일 적용과 연결 종료
- `src/repository.ts`: 행사 생성과 좌석 예약
- `src/repository.test.ts`: 경쟁 요청, 롤백과 매개변수 바인딩 검사

## 주요 선택

- 좌석 중복의 최종 판정은 애플리케이션의 사전 조회가 아니라 PostgreSQL 고유 제약이 담당합니다.
- 예약과 감사 기록은 같은 `trx` 객체로 작성합니다. 두 번째 삽입이 실패하면 첫 번째 삽입도 남지 않습니다.
- 고유 제약 위반만 `SeatTakenError`로 바꾸고, 연결 오류나 trigger 실패는 원인을 유지해 상위로 전달합니다.
- 사용자 값은 Kysely의 `.values()`와 SQL 템플릿 매개변수로 전달합니다.
- 경쟁과 rollback은 실제 PostgreSQL에서 확인해야 하는 동작이므로 메모리 저장소로 대체하지 않습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Database-enforced reservation rules | `migrations/001_initial.sql` |
| 2 | Kysely table types and connection pool | `src/db.ts` |
| 3 | Migration runner cleanup | `src/migrate.ts` |
| 4 | Parameterized event insertion | `src/repository.ts` |
| 5 | Reservation transaction and conflict mapping | `src/repository.ts` |
| 6 | Reservation and audit atomic write | `src/repository.ts` |

데이터베이스가 지켜야 할 규칙을 먼저 정의한 뒤 애플리케이션이 그 제약을 사용하도록 구현합니다. 이 순서에서는 "코드가 맞으면 데이터도 맞다"가 아니라 "DB가 최종 무결성을 지킨다"는 구조가 분명해집니다.

## 범위와 제한

좌석 해제, 예약 만료, 결제, 사용자 인증과 행사 관리 API는 포함하지 않습니다. 데이터베이스의 경쟁 쓰기와 롤백을 좁게 검증합니다.

즉 이 프로젝트는 완성된 예약 서비스가 아니라 다음 세 가지를 집중적으로 확인하는 exercise입니다.

```text
unique constraint
transaction atomicity
real concurrency test
```