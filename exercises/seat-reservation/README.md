# Seat Reservation

PostgreSQL과 Kysely로 구현한 좌석 예약 프로젝트입니다. 같은 행사와 좌석 번호의 예약을 데이터베이스 고유 제약으로 막고, 예약 행과 감사 행을 한 트랜잭션에서 저장합니다.

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

## 설치와 검증

```sh
npm install
npm run typecheck
npm run migrate
npm test
```

종료할 때 테스트 데이터베이스를 제거합니다.

```sh
docker compose down -v
```

## 테스트

테스트는 실제 PostgreSQL에서 다음 잘못된 구현을 검출합니다.

- 같은 좌석의 두 예약이 모두 성공함
- 예약은 저장됐지만 감사 기록은 실패한 상태가 남음
- 사용자 입력이 SQL 문장으로 결합됨
- 테스트 종료 뒤 연결 풀이 남음

감사 테이블에 삽입을 거부하는 임시 trigger를 설치해 두 번째 쓰기의 실패를 만들고, 예약 행도 롤백되었는지 확인합니다.

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

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Database-enforced reservation rules | `migrations/001_initial.sql` |
| 2 | Kysely table types and connection pool | `src/db.ts` |
| 3 | Migration runner cleanup | `src/migrate.ts` |
| 4 | Parameterized event insertion | `src/repository.ts` |
| 5 | Reservation transaction and conflict mapping | `src/repository.ts` |
| 6 | Reservation and audit atomic write | `src/repository.ts` |

## 범위와 제한

좌석 해제, 예약 만료, 결제, 사용자 인증과 행사 관리 API는 포함하지 않습니다. 데이터베이스의 경쟁 쓰기와 롤백을 좁게 검증합니다.
