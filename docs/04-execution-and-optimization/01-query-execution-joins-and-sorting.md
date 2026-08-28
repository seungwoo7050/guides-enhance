# 질의 실행, join과 sort

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 합니다.

- 논리 질의와 physical execution plan의 차이
- iterator 실행 방식에서 `open`, `next`, `close`가 관리하는 자원 수명
- sequential scan과 index scan이 같은 논리 결과를 만드는 방법
- nested-loop, hash와 merge join의 적용 조건과 비용 차이
- 중복과 `NULL`이 join 구현에 미치는 영향
- sort와 hash aggregation이 memory를 넘을 때 disk를 사용하는 이유
- streaming operator와 blocking operator가 첫 결과 시간에 미치는 영향
- 정확한 결과 검증과 성능 측정을 분리해야 하는 이유

## 논리 연산과 실행 방법을 구분합니다

다음 SQL을 보겠습니다.

```sql
SELECT u.id, count(o.id)
FROM users AS u
LEFT JOIN orders AS o ON o.user_id = u.id
WHERE u.active
GROUP BY u.id;
```

논리적으로 필요한 작업은 다음과 같습니다.

```text
active user를 남깁니다.
→ users와 orders를 left join합니다.
→ user별로 묶습니다.
→ 주문 수를 계산합니다.
→ user ID와 count를 반환합니다.
```

같은 결과를 만드는 physical plan은 여러 가지입니다.

```text
users sequential scan + orders hash join
users index scan + orders index nested-loop
양쪽 입력 정렬 + merge join
hash aggregate
sort aggregate
```

SQL이 어떤 결과를 요구하는지와 DBMS가 그 결과를 어떤 연산자로 만드는지는 다른 문제입니다. 성능을 분석할 때 SQL 문자열만 보지 않고 각 논리 연산을 담당한 physical operator를 확인합니다.

## Iterator 실행 방식

축소한 pull 방식 실행기는 다음 메서드를 가질 수 있습니다.

```text
open()
next() -> tuple | EOF
close()
```

상위 operator가 `next()`를 호출하면 하위 operator에서 한 tuple을 요청합니다.

```text
Projection
  └─ Filter
       └─ SequentialScan
```

이 방식은 operator를 조합하기 쉽고, 필요한 만큼만 row를 가져올 수 있습니다. 대신 다음을 명확히 해야 합니다.

- `open()` 도중 실패하면 이미 연 file이나 buffer pin을 누가 정리하는지
- 정상적인 EOF와 중간 오류를 어떻게 구분하는지
- `close()`를 두 번 호출해도 안전한지
- 상위 operator가 `LIMIT` 때문에 일찍 끝나면 하위 자원을 어떻게 닫는지
- `next()`가 반환한 tuple의 memory가 언제까지 유효한지

실제 DBMS는 vectorized execution, push 방식이나 compiled query를 사용할 수 있습니다. 형식이 달라도 operator가 사용하는 자원의 수명과 오류 정리는 필요합니다.

## Scan operator

### Sequential scan

Heap page를 순서대로 읽고 각 tuple의 visibility와 filter를 확인합니다.

다음 조건에서는 합리적일 수 있습니다.

- table이 작습니다.
- 대부분의 row를 반환합니다.
- index를 따라가며 여러 heap page를 무작위로 읽는 비용이 더 큽니다.
- 큰 batch가 전체 table을 읽습니다.

### Index scan

Index에서 조건에 맞는 entry를 찾고 RID를 따라 heap record를 읽습니다.

비용에는 다음이 포함됩니다.

- root에서 leaf까지 index page 접근
- 조건 범위에 포함된 leaf page 읽기
- RID가 가리키는 heap page 읽기
- MVCC visibility 확인
- index에 없는 column 읽기

조건에 맞는 row가 적고 heap page 접근도 적다면 유리합니다. 많은 row를 반환하거나 RID가 넓게 흩어져 있으면 sequential scan보다 느릴 수 있습니다.

Index-only scan도 visibility 확인 때문에 heap을 읽을 수 있습니다. Plan에서 실제 `Heap Fetches`를 확인해야 합니다.

## Join 결과의 bag 의미

중복 key가 있는 equi-join에서는 모든 조합을 보존해야 합니다.

```text
left에 key=7인 row 2개
right에 key=7인 row 3개
→ 결과 6개
```

Hash table에 key마다 row 하나만 저장하거나 merge join이 같은 key의 첫 row만 결합하면 잘못된 결과입니다.

또한 SQL의 일반 equi-join에서 `NULL = NULL`은 true가 아닙니다. Python의 `None == None`을 그대로 사용하면 SQL과 다른 결과를 만듭니다. [`join-algorithms`](../../exercises/join-algorithms/)는 중복과 `NULL`을 포함한 결과를 multiset으로 비교합니다.

## Nested-loop join

가장 단순한 형태는 왼쪽 row마다 오른쪽 입력을 모두 확인합니다.

```text
for each left row:
    for each right row:
        if keys match:
            emit pair
```

비교 횟수는 대략 `|L| × |R|`입니다. 하지만 다음 상황에서는 적합할 수 있습니다.

- 한쪽 입력이 매우 작습니다.
- outer input이 강하게 filter됩니다.
- inner key에 index가 있습니다.
- 첫 번째 결과를 빨리 반환해야 합니다.

Index nested-loop는 outer row마다 inner index lookup을 수행합니다. 예상 outer row가 10인데 실제로 100,000이라면 random lookup이 크게 늘어날 수 있습니다.

확인할 실패 사례는 다음과 같습니다.

- 빈 입력
- 중복 key
- `NULL` key
- outer join의 unmatched row
- 중간 오류와 조기 종료 시 inner cursor 정리

## Hash join

일반적으로 작은 입력으로 hash table을 만들고 큰 입력을 순회하며 같은 key bucket을 찾습니다.

```text
build: key → 같은 key의 row 목록
probe: bucket을 찾고 실제 key equality 확인
```

Equality join에 적합하며 평균적으로 입력 크기에 비례하는 처리를 기대할 수 있습니다. 다만 다음 조건을 확인해야 합니다.

- build input이 memory 안에 들어가는지
- 같은 key가 한 bucket에 몰리지 않는지
- hash collision 뒤 실제 key를 다시 비교하는지
- duplicate row 목록을 모두 보존하는지

Build input이 memory를 넘으면 key hash로 partition을 나누어 disk에 기록한 뒤 같은 partition끼리 처리할 수 있습니다. 특정 key에 row가 몰리면 한 partition만 계속 커질 수 있습니다.

Hash join은 출력 순서를 보장하지 않습니다. 결과에 순서가 필요하면 별도 sort가 필요합니다.

## Merge join

두 입력이 join key 순서로 정렬되어 있으면 양쪽을 함께 전진시킬 수 있습니다.

```text
left key < right key  → left를 전진합니다.
left key > right key  → right를 전진합니다.
left key = right key  → 양쪽의 같은 key 구간을 모두 결합합니다.
```

같은 key가 여러 번 나오면 양쪽 run의 곱집합을 만들어야 합니다. 한쪽 run의 첫 row만 사용하면 중복 수가 틀립니다.

비용은 입력이 이미 정렬되어 있는지에 크게 좌우됩니다.

- index 순서를 그대로 사용할 수 있는지
- 하위 operator가 정렬된 결과를 제공하는지
- 별도 sort가 필요한지
- 정렬 결과를 뒤의 `ORDER BY`에서도 사용할 수 있는지

Merge join이 정렬된 결과를 내더라도 SQL이 순서를 보장하려면 최종 질의에 `ORDER BY`가 있어야 합니다.

## Sort는 첫 결과를 늦출 수 있습니다

일반 sort는 입력 전체를 읽은 뒤에야 가장 작은 row나 가장 큰 row를 확정할 수 있습니다. 따라서 첫 결과를 반환하기 전까지 기다리는 blocking operator입니다.

Memory 안에 들어가면 in-memory sort를 사용할 수 있습니다. Memory를 넘으면 다음처럼 처리합니다.

```text
memory 크기만큼 row를 읽어 정렬된 run을 만듭니다.
→ 각 run을 임시 파일에 기록합니다.
→ 여러 run을 merge합니다.
```

비용은 row 수뿐 아니라 row 폭, memory 제한, 임시 파일 I/O와 merge 횟수에 따라 달라집니다.

`ORDER BY ... LIMIT N`은 전체 sort 대신 크기 N의 heap으로 상위 N개를 유지할 수 있습니다. 그러나 join이나 filter가 큰 중간 결과를 먼저 만들면 `LIMIT`만으로 앞 단계의 비용이 사라지지는 않습니다.

## Aggregation

### Hash aggregate

Group key마다 accumulator를 hash table에 저장합니다. Group 수와 accumulator가 memory 안에 들어가면 효율적입니다. Group 수 추정이 틀리면 partition을 disk에 기록할 수 있습니다.

### Sort aggregate

Group key로 정렬한 뒤 같은 key가 이어지는 동안 값을 합칩니다. 입력이 이미 group key 순서이거나 hash table이 memory에 맞지 않을 때 선택될 수 있습니다.

Aggregation은 한 row가 뜻하는 대상을 바꿉니다. 다음을 확인해야 합니다.

- `count(*)`와 `count(column)`의 `NULL` 처리
- 빈 입력에서 aggregate 결과
- `sum`과 `avg`의 numeric 범위
- group key의 collation
- parallel partial aggregate를 합치는 연산이 결합법칙을 만족하는지

## Streaming과 materialization

Filter와 projection은 row 하나를 받으면 바로 다음 operator로 넘길 수 있습니다. 일부 nested-loop도 첫 row를 일찍 반환합니다. 반면 sort, hash build와 전체 aggregate는 입력을 모아야 합니다.

Materialization은 중간 결과를 memory나 disk에 저장합니다.

필요한 경우:

- 하위 결과를 여러 번 다시 읽습니다.
- 실행 중 값이 바뀔 수 있는 하위 결과를 한 번 계산해 고정합니다.
- 상위 operator가 rewind를 요구합니다.

대가:

- memory 또는 임시 disk 공간을 사용합니다.
- 첫 결과가 늦어질 수 있습니다.
- 중간 결과와 snapshot의 수명을 관리해야 합니다.

Plan에 `Materialize`가 보인다는 이유만으로 제거하면 안 됩니다. 어떤 반복 접근을 줄이기 위해 추가되었는지 확인합니다.

## Parallel execution

큰 scan, join과 aggregate를 여러 worker가 나누어 처리할 수 있습니다. 다음 비용이 추가됩니다.

- 작업 범위 분배
- worker 시작
- tuple 전달
- partial 결과 병합
- skew로 인한 worker 간 작업량 차이
- worker마다 사용하는 memory

작은 query는 worker 준비 비용이 더 클 수 있습니다. Worker 수를 늘리면 DB 전체의 CPU, memory와 I/O 경쟁도 증가합니다.

## 정확성과 성능을 따로 검증합니다

Join 구현을 처음 검사할 때는 결과가 맞는지 확인합니다.

```text
중복 key의 모든 조합이 있는가?
NULL이 서로 match하지 않는가?
빈 입력을 처리하는가?
입력 순서가 달라도 같은 multiset 결과인가?
```

그 뒤 실행 특성을 측정합니다.

```text
비교 횟수
hash build row 수
sort run 수
peak memory
임시 파일 byte
첫 row 시간
전체 시간
```

작은 입력에서 빠른 알고리즘이 실제 workload에서도 빠르다고 단정하면 안 됩니다. 데이터 분포, row 폭, cache, disk와 동시 실행을 함께 기록해야 합니다.

## 연결 exercise

이 문서를 읽은 뒤 [`join-algorithms`](../../exercises/join-algorithms/)를 수행합니다.

Exercise에서는 같은 inner equi-join을 다음 세 방식으로 구현합니다.

- nested-loop join
- hash join
- merge join

테스트는 `NULL`, 중복 key, 빈 입력, build side 변경과 무작위 입력에서 세 구현이 같은 multiset을 만드는지 확인합니다.

## 완료 기준

다음 질문에 작은 입력과 코드로 답할 수 있어야 합니다.

1. 논리 join 하나에 여러 physical join이 가능한 이유는 무엇입니까?
2. Hash join에서 key마다 row 목록을 저장해야 하는 이유는 무엇입니까?
3. Merge join이 같은 key의 양쪽 run 전체를 결합해야 하는 이유는 무엇입니까?
4. Index nested-loop가 유리한 조건과 불리한 조건은 무엇입니까?
5. Sort가 첫 결과를 늦추는 이유는 무엇입니까?
6. Hash와 sort가 memory를 넘으면 disk를 사용해야 하는 이유는 무엇입니까?
7. 결과 정확성 검사와 성능 측정을 분리해야 하는 이유는 무엇입니까?
