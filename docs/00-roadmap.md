# 데이터베이스 시스템 학습 로드맵

이 로드맵은 데이터베이스를 단순한 저장 API가 아니라 다음 요소가 함께 동작하는 하나의 시스템으로 이해하는 것을 목표로 합니다.

```text
논리적 데이터 의미
→ 스키마와 제약
→ 페이지와 인덱스
→ 버퍼 풀
→ 트랜잭션과 MVCC
→ WAL과 crash recovery
→ 질의 실행기와 옵티마이저
→ 안전한 스키마 변경
```

문서를 먼저 모두 읽지 않습니다. 의미 있는 구현을 시작할 만큼의 용어를 익히면 바로 연결된 프로젝트를 실행하고, 테스트가 검사하는 잘못된 상태를 확인한 뒤 다음 개념으로 이동합니다.

## 선행지식

다음 경험이 있으면 시작할 수 있습니다.

- 간단한 table 생성과 기본 CRUD SQL 작성
- primary key와 foreign key의 기본 의미
- 터미널에서 명령을 실행하고 오류를 읽는 능력
- Python의 함수, class, list와 dictionary 기본 사용
- PostgreSQL 프로젝트를 위한 Docker 실행 환경

SQL 문법 입문, ORM 연결법과 connection pool 사용법은 이 저장소의 필수 범위가 아닙니다.

## 종료 능력

필수 과정을 마치면 다음을 할 수 있어야 합니다.

1. SQL 결과의 행 단위, 중복, `NULL`, 정렬 조건을 명시합니다.
2. 업무상 허용하지 않는 상태를 스키마 제약과 트랜잭션으로 막습니다.
3. record가 page와 RID로 저장되고 index에서 다시 찾아지는 과정을 설명합니다.
4. page table, pin, dirty와 교체 상태를 추적합니다.
5. 동시 transaction에서 lost update와 write skew가 생기는 실행 순서를 재현합니다.
6. MVCC snapshot, WAL flush, REDO와 UNDO가 해결하는 실패를 구분합니다.
7. join 알고리즘과 실행 계획이 같은 SQL 결과를 만드는 이유를 설명합니다.
8. 통계와 실제 row 수를 비교해 index 변경을 검증합니다.
9. 기존 데이터와 이전 애플리케이션을 유지하면서 schema를 단계적으로 변경합니다.
10. 하나의 요청과 장애를 논리 의미부터 disk 상태까지 이어서 설명합니다.

## 필수 경로

### 1. 관계 모델과 SQL 의미

문서:

1. [`관계 모델과 관계 대수`](01-relational-semantics-and-design/01-relational-model-and-algebra.md)
2. [`SQL 의미와 질의 형태`](01-relational-semantics-and-design/02-sql-semantics-and-query-shape.md)

Exercise:

- [`sql-semantics-views`](../exercises/sql-semantics-views/)

이 구간에서는 `NULL`, anti-join, 외부 조인 집계와 완전한 정렬 조건을 실제 PostgreSQL 결과로 확인합니다.

### 2. 스키마와 업무 규칙

문서:

3. [`ER 모델, 정규화와 제약`](01-relational-semantics-and-design/03-er-normalization-and-constraints.md)

먼저 다음 파일까지 확인합니다.

```text
exercises/ticketing-database/schema.sql
exercises/ticketing-database/seed.sql
```

`ticketing-database`의 Implementation 1~3을 기준으로 조직 범위를 포함한 key, foreign key와 ticket 상태 조합을 설명합니다. 나머지 migration과 index는 뒤에서 이어서 봅니다.

### 3. 페이지와 안정적인 record identifier

문서:

4. [`페이지, 레코드와 파일`](02-storage-and-indexes/01-pages-records-and-files.md)

Exercise:

- [`slotted-page`](../exercises/slotted-page/)

Insert, delete, update와 compaction 뒤에도 slot ID가 유지되는지 확인합니다. 공간 부족이나 손상된 입력이 기존 page를 일부만 바꾸지 않는지도 검사합니다.

### 4. Index 탐색과 범위 조회

문서:

5. [`인덱스: B+ tree, hash와 BRIN`](02-storage-and-indexes/02-index-structures.md)

Exercise:

- [`bplus-tree`](../exercises/bplus-tree/)

Leaf와 internal node의 분할 규칙을 구분하고, separator와 leaf 연결이 point lookup과 range scan에서 일관되는지 확인합니다.

### 5. 버퍼 풀과 페이지 수명

문서:

6. [`Buffer pool과 page 교체`](02-storage-and-indexes/03-buffer-pool-and-replacement.md)

Exercise:

- [`clock-buffer-pool`](../exercises/clock-buffer-pool/)

Cache hit, pin, dirty, Clock second chance, flush와 eviction의 상태 변화를 추적합니다.

### 6. 트랜잭션과 실제 동시 실행

문서:

7. [`트랜잭션, 격리와 잠금`](03-transactions-and-recovery/01-transactions-isolation-and-locks.md)

Exercise:

- [`postgres-concurrency-guards`](../exercises/postgres-concurrency-guards/)

조건부 `UPDATE`가 재고 차감을 어떻게 순서대로 처리하는지, 여러 행의 조건을 공용 guard row로 어떻게 보호하는지 두 PostgreSQL session으로 확인합니다.

### 7. MVCC, WAL과 복구

문서:

8. [`MVCC, WAL과 crash recovery`](03-transactions-and-recovery/02-mvcc-wal-and-recovery.md)

Exercise:

- [`wal-recovery-simulator`](../exercises/wal-recovery-simulator/)

WAL보다 data page를 먼저 쓰지 않는 조건, `page_lsn`, committed REDO, 미완료 UNDO와 반복 recovery를 구현합니다.

### 8. 질의 실행기

문서:

9. [`질의 실행, join과 sort`](04-execution-and-optimization/01-query-execution-joins-and-sorting.md)

Exercise:

- [`join-algorithms`](../exercises/join-algorithms/)

Nested-loop, hash, merge join이 중복과 `NULL`을 포함해 같은 bag 결과를 만드는지 비교합니다.

### 9. 통계와 실행 계획

문서:

10. [`통계, 비용 모델과 EXPLAIN`](04-execution-and-optimization/02-statistics-cost-model-and-explain.md)

Exercise:

- [`postgres-workload-indexes`](../exercises/postgres-workload-indexes/)

Composite, partial, covering index가 실제 catalog와 plan에 나타나는지 확인합니다. 결과 정렬이 맞는지와 별도 `Sort`가 생기는지도 함께 검사합니다.

### 10. 안전한 변경과 애플리케이션 데이터베이스 통합

문서:

11. [`Schema, index와 안전한 변경 절차`](04-execution-and-optimization/03-schema-index-and-tuning-loop.md)

Exercise:

- [`ticketing-database`](../exercises/ticketing-database/)

앞에서 확인한 schema에 다음 항목을 이어서 봅니다.

```text
migration.sql
queries.sql
indexes.sql
tests/verify.sql
scripts/test.sh
```

Migration의 재실행, 기존 행 검증, keyset pagination, partial index와 실제 plan을 하나의 database 안에서 확인합니다.

### 11. 최종 검증

문서:

12. [`Database Systems 종합 검토`](90-system-review.md)

필수 프로젝트 9개를 다시 실행하고 다음 설명을 작성합니다.

```text
업무 규칙
→ 스키마와 SQL 결과
→ 트랜잭션과 잠금
→ 페이지와 RID
→ 인덱스와 버퍼 풀
→ WAL과 commit
→ crash recovery
→ 조회 실행 계획
→ 안전한 migration
```

틀린 상태를 막는 주체와 실패 뒤 남는 상태를 각 단계에서 구체적으로 적습니다.

## 선택 자료

다음 두 문서는 새 필수 개념을 추가하지 않습니다. 여러 개념을 한 시나리오로 다시 정리할 때 사용합니다.

- [`애플리케이션 데이터베이스 검토`](05-capstones/01-application-database-review.md)
- [`미니 저장 엔진`](05-capstones/02-mini-storage-engine.md)

선택 프로젝트:

- [`mini-storage-engine`](../exercises/mini-storage-engine/)

이 프로젝트는 page, buffer pool, WAL과 index를 한 프로그램으로 다시 연결합니다. 전용 exercise에서 각 동작을 이미 검증했다면 필수 완료 조건은 아닙니다.

## 선택적 되돌아보기

모든 문서를 처음부터 다시 읽지 않습니다. 최종 설명이나 테스트에서 막힌 부분만 되돌아갑니다.

- SQL 결과가 틀리면 관계 모델과 SQL 의미를 다시 봅니다.
- 다른 조직의 행이 연결되면 schema key와 foreign key를 다시 봅니다.
- RID나 page bytes가 달라지면 slotted page를 다시 봅니다.
- dirty page가 사라지면 buffer pool과 WAL 순서를 함께 봅니다.
- 동시 실행 결과가 불안정하면 transaction과 잠금 구간을 다시 봅니다.
- 실행 계획을 설명할 수 없으면 join operator, 통계와 실제 row 수를 다시 봅니다.

## 최종 완료 기준

다음을 모두 만족해야 합니다.

- 필수 문서 12개의 완료 질문에 답합니다.
- 필수 프로젝트 9개의 테스트를 각 프로젝트 디렉터리에서 통과합니다.
- Implementation Order를 따라 각 프로젝트를 처음부터 다시 만들 수 있는 순서를 설명합니다.
- 하나의 요청 처리, 느린 질의, deadlock, crash와 migration 사례를 별도 도움 없이 분석합니다.
- 현재 모델이 다루지 않는 replication, backup 운영, 분산 transaction과 DBMS 내부 세부 구현을 과장하지 않습니다.
