# 통계, 비용 모델과 EXPLAIN

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 합니다.

- 옵티마이저가 plan을 실제로 모두 실행하지 않고 비용을 추정하는 이유
- cardinality와 selectivity 오차가 상위 join과 sort 선택까지 커지는 방법
- histogram, most-common values와 distinct count가 제공하는 정보
- column correlation과 다중 column 의존성이 단일 column 추정을 틀리게 하는 이유
- plan의 cost가 실제 millisecond가 아닌 이유
- `EXPLAIN`과 `EXPLAIN ANALYZE`의 차이와 실행 부작용
- scan, join, sort와 aggregate plan에서 확인할 수치
- index 변경 전후를 같은 조건에서 비교하는 방법

## 옵티마이저는 후보 plan을 비교합니다

같은 SQL을 실행하는 방법은 여러 가지입니다.

```text
sequential scan / index scan / bitmap scan
nested-loop / hash join / merge join
A-B-C / B-C-A join 순서
hash aggregate / sort aggregate
전체 sort / top-N
단일 worker / parallel worker
```

모든 후보를 실제로 실행해서 가장 빠른 것을 고를 수는 없습니다. 옵티마이저는 table과 column 통계로 각 operator가 반환할 row 수를 추정하고, page I/O와 CPU 작업량을 상대 비용으로 계산합니다.

느린 plan을 분석할 때 다음 두 경우를 구분합니다.

```text
row 수 추정이 틀렸습니다.
→ 잘못된 join 순서나 알고리즘을 선택할 수 있습니다.

row 수는 비슷하지만 비용 설정이 실제 환경과 다릅니다.
→ random I/O, cache나 parallel 비용의 상대값이 맞지 않을 수 있습니다.
```

## Cardinality가 다음 operator 선택을 바꿉니다

다음 조건이 1,000,000 row 중 몇 row를 남기는지에 따라 적절한 scan이 달라집니다.

```sql
WHERE tenant_id = 42
  AND status = 'OPEN'
  AND created_at >= current_date - interval '7 days'
```

10 row만 남는다면 composite index가 유리할 수 있습니다. 700,000 row가 남는다면 sequential scan이 더 적은 page 접근으로 끝날 수 있습니다.

Join에서도 하위 추정이 중요합니다.

```text
outer filter 추정: 10 rows
실제 결과: 100,000 rows
→ inner index lookup을 10번 예상
→ 실제로는 100,000번 실행
```

하위 node의 오차는 상위 join, sort, aggregate의 memory 크기와 spill 여부까지 바꿉니다. Plan은 가장 아래 scan부터 읽어 첫 번째 큰 오차가 어디에서 시작하는지 찾습니다.

## 기본 column 통계

### Distinct count

서로 다른 값 수를 추정합니다. 값이 균등하게 분포한다고 가정하면 equality 조건의 selectivity를 대략 `1 / distinct_count`로 볼 수 있습니다.

Tenant별 row 수가 크게 다르면 이 가정은 맞지 않습니다.

### Most-common values

자주 나오는 값과 빈도를 별도로 저장합니다. `status='OPEN'`처럼 특정 값이 매우 흔할 때 전체 평균보다 나은 추정을 제공합니다.

### Histogram

값 범위를 여러 bucket으로 나누어 range 조건의 selectivity를 추정합니다. 최근 데이터가 급격히 늘어난 append-only table에서는 오래된 histogram이 최근 범위를 과소 추정할 수 있습니다.

### Null fraction과 평균 폭

`NULL` 비율은 `IS NULL`, join과 aggregate 결과 추정에 사용됩니다. 평균 column/row 폭은 page 수, hash table과 sort memory 계산에 영향을 줍니다.

## Column correlation과 다중 column 통계

두 조건이 독립이라고 가정하면 selectivity를 곱할 수 있습니다.

```text
P(tenant=42 AND status='OPEN')
≈ P(tenant=42) × P(status='OPEN')
```

하지만 tenant마다 status 분포가 다르면 틀립니다. 다음 조합도 자주 의존합니다.

```text
country와 city
zip_code와 state
tenant_id와 project_id
created_at과 순차 증가 id
```

단일 column 통계만 있으면 실제 조합 빈도를 놓칠 수 있습니다. PostgreSQL의 extended statistics처럼 다중 column 관계를 기록하거나, 실제 parameter별 row 수를 확인해야 합니다.

Physical order correlation도 중요합니다. Index key와 heap 배치 순서가 비슷하면 range scan이 연속 page를 읽기 쉽습니다. 상관관계가 낮으면 index에서 가까운 key가 서로 먼 heap page를 가리킬 수 있습니다.

## 통계는 데이터 변화 뒤 오래될 수 있습니다

다음 변화 뒤에는 기존 통계가 현재 분포를 반영하지 못할 수 있습니다.

- 대량 insert 또는 delete
- 특정 tenant의 급성장
- 새로운 status 값 추가
- 계절별 분포 변화
- migration backfill

`ANALYZE` 시점, sampling 크기와 column별 statistics target을 확인합니다. 모든 column의 target을 무조건 크게 올리면 분석 시간과 catalog 크기가 늘어납니다. 실제 추정 오차가 시작되는 column을 대상으로 조정해야 합니다.

## Cost는 상대값입니다

PostgreSQL plan의 `cost=a..b`는 일반적으로 startup cost와 total cost를 나타냅니다.

```text
startup cost .. total cost
```

이 값은 측정된 millisecond가 아닙니다. Sequential page, random page, tuple 처리와 operator 처리 비용을 설정값으로 계산한 상대 단위입니다.

Startup cost가 중요한 예:

- `LIMIT`으로 첫 row를 빨리 받고 싶습니다.
- interactive pagination입니다.
- `EXISTS`가 첫 match에서 끝날 수 있습니다.

Total cost가 중요한 예:

- 전체 export입니다.
- 전체 aggregation입니다.
- batch 작업입니다.

서로 다른 server나 설정의 cost 숫자를 직접 비교하지 않습니다.

## `EXPLAIN`과 `EXPLAIN ANALYZE`

### `EXPLAIN`

SQL을 실제로 실행하지 않고 추정 plan을 보여 줍니다. 실제 row 수, 실행 시간과 buffer 사용량은 없습니다.

### `EXPLAIN ANALYZE`

SQL을 실제로 실행하고 각 node의 실제 row와 시간을 기록합니다. `INSERT`, `UPDATE`, `DELETE`에 사용하면 실제 데이터가 바뀝니다. 검증용 database나 rollback 가능한 transaction에서 실행해야 합니다.

대표적인 형식은 다음과 같습니다.

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT JSON)
SELECT ...;
```

- `ANALYZE`: 실제로 실행합니다.
- `BUFFERS`: shared/local/temp block hit와 read/write를 보여 줍니다.
- `VERBOSE`: 출력 column과 세부 조건을 표시합니다.
- `FORMAT JSON`: 자동 비교하기 쉬운 형식으로 반환합니다.

측정 overhead를 줄일 필요가 있으면 `TIMING OFF`를 검토합니다.

## Plan은 아래에서 위로 읽습니다

상위 node는 하위 결과를 입력으로 사용합니다. 가장 안쪽 scan부터 다음 값을 기록합니다.

```text
estimated rows
actual rows × loops
Rows Removed by Filter
startup / total time
shared hit / read
local / temp read-write
sort method와 memory/disk
join condition과 filter
index condition과 residual filter
```

Inner nested-loop node가 한 번에 3 row를 반환해도 `loops=100000`이면 총 처리량은 큽니다. `actual rows × loops`를 함께 봐야 합니다.

## Scan plan 읽기

### Sequential Scan

항상 나쁜 plan이 아닙니다.

확인할 내용:

- table 전체 중 반환하는 비율
- filter가 제거한 row 수
- table과 row 폭
- shared read와 hit
- parallel worker 사용 여부

### Index Scan

확인할 내용:

- `Index Cond`가 실제 탐색 범위를 줄이는지
- `Filter`가 많은 row를 다시 버리는지
- heap page read가 많은지
- index 순서가 `ORDER BY`를 제공하는지

Index에 첫 column만 맞고 나머지 조건이 filter로 처리되면 많은 entry를 읽고 버릴 수 있습니다.

### Bitmap Scan

중간 정도의 selectivity에서 heap page별로 RID를 묶어 방문할 수 있습니다. 여러 index 결과를 합칠 수도 있습니다. Bitmap이 lossy하면 heap에서 조건을 다시 검사합니다.

### Index Only Scan

필요한 column이 index에 있어도 visibility 확인을 위해 heap을 읽을 수 있습니다. `Heap Fetches`를 보고 vacuum과 visibility map 상태를 확인합니다.

## Join plan 읽기

### Nested Loop

- outer의 실제 row 수
- inner node의 loops
- inner lookup 한 번의 비용
- 예상보다 큰 outer input
- memoization 여부

### Hash Join

- build side
- bucket와 batch 수
- memory 사용량
- disk spill 여부
- skew
- hash condition 외 추가 filter

### Merge Join

- 양쪽 입력이 어떤 순서로 제공되는지
- 별도 sort가 있는지
- sort가 disk로 spill했는지
- 같은 key가 얼마나 반복되는지

Join 알고리즘만 보고 강제로 바꾸기보다, row 추정과 정렬 정보가 왜 그 선택을 만들었는지 먼저 확인합니다.

## Sort와 aggregate 읽기

Sort node에서는 다음을 확인합니다.

```text
Sort Key
Sort Method
Memory
Disk 사용량
입력 rows와 row width
```

Aggregate node에서는 다음을 확인합니다.

```text
HashAggregate / GroupAggregate
실제 group 수
batch 또는 partition 수
memory와 disk 사용량
입력 정렬 여부
```

`work_mem`을 크게 올리면 한 query의 spill은 줄일 수 있지만, 동시에 실행되는 query와 operator마다 memory를 사용할 수 있습니다. 전체 DB memory 사용량을 함께 계산해야 합니다.

## 변경 전후 비교 조건을 고정합니다

Index나 query를 변경하기 전후에는 다음을 같게 맞춥니다.

- schema와 data volume
- 통계 상태
- query parameter
- DB 설정
- cold/warm cache 여부와 기록 방식
- 동시 workload
- 충분한 반복 횟수

다음 표를 남기면 결과를 비교하기 쉽습니다.

| 항목 | 변경 전 | 변경 후 |
| --- | ---: | ---: |
| 실제 반환 row |  |  |
| 총 처리 row |  |  |
| shared read |  |  |
| shared hit |  |  |
| temp read/write |  |  |
| execution time |  |  |
| insert/update 영향 |  |  |
| index 크기 |  |  |

조회 하나가 빨라졌다고 변경이 끝난 것은 아닙니다. Write latency, vacuum, backup 크기와 migration 시간도 확인합니다.

## Parameter와 cached plan

Prepared statement는 여러 parameter 값에 같은 generic plan을 사용할 수 있습니다. 데이터가 치우쳐 있다면 작은 tenant와 전체 row의 절반을 가진 tenant에 적절한 plan이 다를 수 있습니다.

```text
tenant_id = 작은 tenant
 tenant_id = 매우 큰 tenant
```

Literal 한 값만 검사하면 production의 parameter-sensitive 문제를 놓칠 수 있습니다. 대표 분포를 여러 구간으로 나누어 custom/generic plan을 비교합니다.

## 성능 주장은 조건과 함께 기록합니다

다음 표현만으로는 근거가 부족합니다.

```text
index를 추가하니 빨라졌습니다.
hash join이 nested-loop보다 빠릅니다.
plan cost가 줄었습니다.
```

대신 다음 정보를 함께 기록합니다.

```text
DBMS와 version
hardware와 주요 설정
data volume과 분포
query parameter
cold/warm cache
동시 workload
반환 row 수
latency와 block read 변화
write와 저장 공간 변화
```

환경이나 workload가 달라지면 결론도 다시 측정해야 합니다.

## 연결 exercise

이 문서를 읽은 뒤 [`postgres-workload-indexes`](../../exercises/postgres-workload-indexes/)를 수행합니다.

Exercise는 실제 PostgreSQL에서 다음을 확인합니다.

- tenant별 최신 event query의 복합 정렬 index
- `PENDING` job만 포함하는 partial index
- `INCLUDE` column
- 별도 `Sort` 없이 index 순서를 사용하는 plan
- 실제 결과의 안정적인 순서
- catalog에 저장된 정확한 index 정의

## 완료 기준

다음 분석을 작성할 수 있어야 합니다.

1. 첫 번째 큰 추정 오차가 시작되는 plan node는 어디입니까?
2. 그 오차가 상위 join이나 sort 선택에 어떤 영향을 줍니까?
3. Sequential scan이 합리적인지 어떤 수치로 판단합니까?
4. Index scan이 많은 heap page를 읽는 이유는 무엇입니까?
5. `actual rows × loops`를 확인해야 하는 이유는 무엇입니까?
6. Sort나 hash가 disk를 사용한 증거는 어디에 있습니까?
7. 변경 전후를 비교할 때 어떤 조건을 고정해야 합니까?
