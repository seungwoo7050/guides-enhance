# 인덱스 구조: B+ tree, hash와 BRIN

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 합니다.

- index가 search key를 record 위치와 연결하는 별도 자료구조인 이유
- B+ tree가 equality, range와 정렬된 scan을 함께 지원하는 방법
- leaf node와 internal node의 split 규칙이 다른 이유
- composite index의 column 순서가 탐색 범위를 결정하는 방법
- hash index와 BRIN이 유리한 workload
- index가 읽기 I/O를 줄이는 대신 쓰기와 저장 공간을 늘리는 이유

## Index는 table의 복사본이 아닙니다

Index는 search key를 record나 RID와 연결합니다.

```text
search key
→ index entry
→ (page_id, slot_id)
→ heap record
```

Index를 추가하면 특정 조건에 맞는 record를 적은 page 접근으로 찾을 수 있습니다. 대신 다음 비용이 생깁니다.

- insert, update와 delete 때 index entry도 변경합니다.
- index page가 buffer pool 공간을 사용합니다.
- node split과 vacuum, rebuild 작업이 필요합니다.
- index가 커지면 backup, replica와 WAL 양도 늘어납니다.
- 많은 row를 찾을 때는 heap page를 무작위로 방문할 수 있습니다.

따라서 “조회하는 column에 index를 붙입니다”가 아니라 실제 filter, 정렬, 반환 행 수와 쓰기 빈도를 기준으로 선택해야 합니다.

## B+ tree의 기본 배치

B+ tree는 한 node에 많은 key와 pointer를 저장하는 균형 tree입니다.

```text
internal node: separator key + child pointer
leaf node: ordered key + RID 또는 value
leaf link: 다음 leaf
```

실제 record 위치는 leaf에만 저장합니다. Internal node는 key 범위를 나누고, 모든 leaf는 같은 깊이에 위치합니다. Node 하나가 page 하나에 대응하면 높은 fan-out 덕분에 수백만 entry도 몇 번의 page 접근으로 leaf까지 내려갈 수 있습니다.

## Separator 의미를 하나로 고정합니다

다음 internal node를 보겠습니다.

```text
[20 | 50]
child 0: key < 20
child 1: 20 <= key < 50
child 2: 50 <= key
```

Separator를 “왼쪽 child의 최대 key”로 둘 수도 있고 “오른쪽 subtree의 최소 key”로 둘 수도 있습니다. 어느 쪽이든 search, split과 validation에서 같은 정의를 사용해야 합니다.

[`bplus-tree`](../../exercises/bplus-tree/)는 separator를 오른쪽 subtree의 최소 key로 정의합니다. 따라서 key가 separator와 같으면 오른쪽 child로 내려갑니다.

## Leaf split

Leaf가 허용 key 수를 넘으면 key와 value를 두 leaf로 나눕니다.

```text
before: [10, 20, 30, 40]
after : [10, 20] → [30, 40]
parent에 추가할 separator: 30
```

Leaf split에서 지켜야 할 조건은 다음과 같습니다.

- 모든 key와 value가 두 leaf 중 하나에 남습니다.
- 오른쪽 leaf의 첫 key를 parent separator로 복사합니다.
- 기존 `next` 연결을 잃지 않습니다.
- 왼쪽 leaf가 새 오른쪽 leaf를 가리킵니다.
- parent가 넘치면 internal split을 계속 수행합니다.
- root가 split되면 새 root를 만듭니다.

## Internal split

Internal node는 child 수가 key 수보다 하나 많습니다.

```text
children = keys + 1
```

Internal node를 나눌 때는 가운데 separator를 parent로 올립니다.

```text
before keys: [20, 50, 80]
promote: 50
left keys: [20]
right keys: [80]
```

승격한 key는 두 child node에 남기지 않습니다. Leaf split과 같은 방식으로 처리하면 child 범위가 겹치거나 separator가 중복될 수 있습니다.

## Range scan은 leaf link를 사용합니다

범위 조회는 시작 key가 있는 leaf를 한 번 찾은 뒤 leaf link를 따라갑니다.

```text
seek(100)
→ leaf에서 100 이상인 첫 위치
→ 현재 leaf의 key 읽기
→ next leaf로 이동
→ upper bound를 넘으면 종료
```

각 key마다 root부터 다시 탐색하지 않습니다. 이 특징 때문에 B+ tree는 equality lookup뿐 아니라 범위 조건과 index 순서 scan에도 적합합니다.

## Duplicate key를 보존해야 합니다

Non-unique index는 같은 search key에 여러 RID를 연결해야 합니다.

가능한 표현은 다음과 같습니다.

- `(search_key, RID)`를 실제 정렬 key로 사용합니다.
- 하나의 key entry에 RID 목록을 둡니다.
- 같은 key entry를 연속해서 저장합니다.

업무 key가 유일하지 않은데 key마다 RID 하나만 저장하면 다른 row가 사라집니다. Index key의 유일성과 table row의 유일성을 혼동하면 안 됩니다.

## Composite index의 column 순서

다음 index를 보겠습니다.

```sql
CREATE INDEX ON events(tenant_id, created_at DESC, id DESC);
```

정렬 순서는 먼저 `tenant_id`, 그 안에서 `created_at`, 동률이면 `id`입니다.

다음 workload와 잘 맞습니다.

```sql
WHERE tenant_id = $1
  AND created_at < $2
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

`tenant_id` equality로 좁은 범위를 찾은 뒤, 그 범위 안에서 시간 역순으로 읽을 수 있습니다.

반면 다음 질의는 첫 column을 제한하지 않습니다.

```sql
WHERE created_at >= now() - interval '1 day'
```

모든 tenant 범위를 확인해야 하므로 같은 index의 효율이 낮아질 수 있습니다. 단순히 “leftmost prefix”라는 말을 외우기보다 index entry가 어떤 순서로 정렬되는지 직접 그려 보는 편이 정확합니다.

## `INCLUDE`와 index-only scan

검색과 정렬에는 사용하지 않지만 결과에 필요한 column을 leaf에 포함할 수 있습니다.

```sql
CREATE INDEX events_tenant_created_id_idx
ON events(tenant_id, created_at DESC, id DESC)
INCLUDE (kind, payload);
```

필요한 column이 index에 모두 있으면 heap 접근을 줄일 수 있습니다. 다만 PostgreSQL의 index-only scan은 visibility map 상태에 따라 heap을 확인할 수 있습니다. `INCLUDE`를 많이 사용하면 index 크기와 write 비용이 늘어나므로 실제 heap fetch 수를 측정해야 합니다.

## Partial index

특정 조건을 만족하는 row만 index에 넣습니다.

```sql
CREATE INDEX jobs_pending_schedule_idx
ON jobs(scheduled_at, id)
WHERE status = 'PENDING';
```

완료된 job이 대부분이고 `PENDING`만 자주 조회한다면 index를 작게 유지할 수 있습니다. Planner가 사용하려면 query predicate가 partial index의 조건을 만족한다는 사실을 판단할 수 있어야 합니다.

상태 분포가 바뀌어 `PENDING`이 대부분이 되면 index가 작다는 장점은 사라집니다. Predicate와 데이터 분포를 함께 확인해야 합니다.

## Hash index

Hash index는 key의 hash 값을 bucket에 연결합니다.

장점:

- equality lookup에 직접적입니다.
- key 순서를 유지하지 않아도 됩니다.

제한:

- range와 정렬된 scan에 적합하지 않습니다.
- bucket overflow와 skew가 특정 bucket을 크게 만들 수 있습니다.
- resize와 hash function 변경을 처리해야 합니다.

다음과 같은 equality query에는 적합할 수 있습니다.

```sql
WHERE session_token = $1
```

반면 `BETWEEN`, prefix 순서와 `ORDER BY`를 제공하는 자료구조는 아닙니다.

## BRIN

BRIN은 table의 연속 page 범위마다 최소·최대값 같은 요약을 저장합니다. Row마다 entry 하나를 만들지 않습니다.

다음 조건에서 유리합니다.

- table이 매우 큽니다.
- column 값과 물리 page 순서의 상관관계가 높습니다.
- 시간 순 append처럼 비슷한 값이 가까운 page에 모입니다.
- 정확한 한 row 탐색보다 많은 page 범위를 건너뛰는 것이 목적입니다.

시간 순으로 쌓이는 event table이라면 `created_at` BRIN이 작은 크기로 오래된 page 범위를 제외할 수 있습니다. 값이 무작위 순서로 저장되면 각 page range의 최소·최대 범위가 넓어져 효과가 줄어듭니다.

## Physical order와 correlation

B+ tree에서 RID를 빠르게 찾더라도 RID가 서로 먼 heap page를 가리키면 random I/O가 많아집니다.

```text
root에서 leaf까지 탐색
+ 읽을 leaf page 수
+ 방문할 heap page 수
```

Index key 순서와 heap 배치 순서의 correlation이 높으면 range scan이 연속 page를 읽기 쉽습니다. 결과 row가 table의 큰 비율을 차지하면 sequential scan이 index scan보다 나을 수 있는 이유도 여기에 있습니다.

## Index 유지 비용

Index 하나를 추가하면 다음 작업량이 늘어납니다.

```text
INSERT: heap page + 각 index entry
UPDATE: 변경 column에 관련된 index 수정
DELETE: dead tuple과 index entry 정리
VACUUM: 재사용 가능한 tuple과 entry 확인
BACKUP / REPLICA: 더 많은 byte 전송과 보관
```

Prefix가 겹치는 index나 사용하지 않는 index는 write amplification을 만듭니다. 제거하기 전에는 unique constraint, 드문 batch query와 장애 대응 작업이 해당 index를 사용하는지도 확인해야 합니다.

## 연결 exercise

이 문서를 읽은 뒤 [`bplus-tree`](../../exercises/bplus-tree/)를 수행합니다.

Exercise에서는 다음을 구현합니다.

- leaf와 internal node의 서로 다른 split
- 오른쪽 subtree 최소 separator
- root 성장
- point lookup과 range scan
- duplicate key value 교체
- 동일 leaf depth와 leaf link 검증

실제 PostgreSQL index 설계는 뒤의 [`통계, 비용 모델과 EXPLAIN`](../04-execution-and-optimization/02-statistics-cost-model-and-explain.md)과 [`postgres-workload-indexes`](../../exercises/postgres-workload-indexes/)에서 이어집니다.

## 완료 기준

다음 질문에 답할 수 있어야 합니다.

1. Leaf와 internal node는 각각 어떤 값을 저장합니까?
2. Leaf split과 internal split에서 separator를 다르게 처리하는 이유는 무엇입니까?
3. Composite index의 column 순서를 equality, range와 정렬 요구로 설명할 수 있습니까?
4. Equality-only workload와 range workload에서 hash와 B+ tree를 어떻게 비교합니까?
5. BRIN이 작지만 정확한 row 위치를 바로 주지 않는 이유는 무엇입니까?
6. Index 추가 제안에 읽기 이득 외에 어떤 쓰기·공간 비용을 포함해야 합니까?
