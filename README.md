# 데이터베이스 시스템

관계형 데이터베이스의 논리적 의미부터 저장 방식, 동시성, 복구, 실행 계획과 안전한 변경까지 연결해서 학습하는 저장소입니다.

이 저장소는 SQL 문법 입문서가 아닙니다. 간단한 table을 만들고 `SELECT`, `INSERT`, `UPDATE`, `DELETE`를 작성해 본 개발자를 대상으로 합니다. 문서를 모두 읽은 뒤 한꺼번에 구현하지 않고, 필요한 개념을 익힌 즉시 해당 독립 프로젝트를 실행하고 다시 만들어 봅니다.

## 완료 후 갖춰야 할 능력

전체 필수 과정을 마치면 다음을 설명하고 재현할 수 있어야 합니다.

- relation, tuple, key와 SQL의 bag 의미를 구분하고 `NULL`, 외부 조인, 집계, 정렬 오류를 찾습니다.
- 업무 규칙을 candidate key, foreign key, `UNIQUE`, `CHECK`, `NOT NULL`로 표현합니다.
- tuple이 record와 page에 저장되고 `(page_id, slot_id)`로 참조되는 과정을 추적합니다.
- B+ tree의 탐색·분할·범위 조회와 composite·partial·covering index의 적용 조건을 설명합니다.
- buffer pool의 page table, pin, dirty, Clock 교체와 flush 순서를 추적합니다.
- lost update, write skew, deadlock과 재시도 조건을 실제 PostgreSQL 동시 실행으로 확인합니다.
- MVCC, WAL, LSN, `page_lsn`, REDO와 UNDO를 crash 시점별로 설명합니다.
- 논리 질의와 물리 실행 계획을 구분하고 join, sort, 통계와 `EXPLAIN ANALYZE`를 근거로 판단합니다.
- 새 필드 추가, 기존 데이터 채우기, 검증, 이전 형식 제거 순서로 데이터를 안전하게 변경합니다.

## 필수 학습 경로

세부 순서는 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 있습니다. 전체 경로는 다음과 같습니다.

```text
관계 모델과 SQL 의미
→ sql-semantics-views

스키마와 제약
→ ticketing-database의 schema 구간

페이지와 레코드
→ slotted-page

인덱스
→ bplus-tree

버퍼 풀
→ clock-buffer-pool

트랜잭션과 잠금
→ postgres-concurrency-guards

MVCC와 WAL 복구
→ wal-recovery-simulator

질의 실행
→ join-algorithms

통계와 실행 계획
→ postgres-workload-indexes

안전한 schema·index·migration 변경
→ ticketing-database 완성

시스템 종합 검토
→ 전체 필수 exercise 재검증
```

필수 exercise는 다음 9개입니다.

- [`sql-semantics-views`](exercises/sql-semantics-views/)
- [`ticketing-database`](exercises/ticketing-database/)
- [`slotted-page`](exercises/slotted-page/)
- [`bplus-tree`](exercises/bplus-tree/)
- [`clock-buffer-pool`](exercises/clock-buffer-pool/)
- [`postgres-concurrency-guards`](exercises/postgres-concurrency-guards/)
- [`wal-recovery-simulator`](exercises/wal-recovery-simulator/)
- [`join-algorithms`](exercises/join-algorithms/)
- [`postgres-workload-indexes`](exercises/postgres-workload-indexes/)

## 선택 자료

다음 문서는 필수 개념을 하나의 시나리오로 다시 묶는 참고 자료입니다.

- [`애플리케이션 데이터베이스 검토`](docs/05-capstones/01-application-database-review.md)
- [`미니 저장 엔진`](docs/05-capstones/02-mini-storage-engine.md)

[`mini-storage-engine`](exercises/mini-storage-engine/)은 page, buffer pool, WAL과 index를 한 프로그램으로 다시 연결하는 선택 통합 프로젝트입니다. 앞선 전용 exercise를 대체하지 않으며, 내부 저장 동작을 한 파일에서 끝까지 추적해 보고 싶을 때 수행합니다.

## 프로젝트 실행

각 프로젝트는 부모 저장소의 스크립트나 설정에 의존하지 않습니다.

Python 프로젝트:

```bash
cd exercises/<project>
make test
```

PostgreSQL 프로젝트:

```bash
cd exercises/<project>
make test
```

PostgreSQL 프로젝트는 Docker Engine과 Docker Compose v2가 필요합니다. 각 README에는 설치 조건, 실행 명령, 주요 설계 판단과 Implementation Order가 있습니다.

## 완료 기준

다음 조건을 모두 만족하면 이 저장소의 필수 과정을 완료한 것입니다.

- 필수 문서를 읽고 각 문서의 완료 질문에 답할 수 있습니다.
- 필수 프로젝트 9개의 테스트를 각 프로젝트 디렉터리에서 통과시킵니다.
- 결과가 맞는 이유뿐 아니라 잘못된 구현이 어떤 테스트에서 실패하는지 설명합니다.
- 하나의 ticket 생성 요청을 schema, transaction, page, index, buffer pool, WAL과 조회 plan까지 추적합니다.
- 느린 조회, deadlock, crash 뒤 복구, 대규모 backfill 상황에서 먼저 확인할 증거를 정합니다.
- 현재 프로젝트가 다루지 않는 범위를 구체적으로 말할 수 있습니다.

## 범위

이 저장소는 관계형 데이터베이스의 기초 원리와 축소 구현을 다룹니다. 특정 ORM 사용법, 운영 backup 자동화, replication과 sharding, 분산 transaction, 특정 DBMS source code 전체는 포함하지 않습니다. 이러한 주제는 실제 서비스나 운영 요구가 생겼을 때 별도로 학습해야 합니다.
