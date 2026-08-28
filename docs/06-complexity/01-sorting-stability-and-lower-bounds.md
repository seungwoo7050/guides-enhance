# 정렬, 안정성과 비교 하한

## 학습 목표

- 정렬의 key, 방향, 동점 처리, 안정성, 입력 변경 여부를 정합니다.
- comparison sort와 key 표현을 직접 사용하는 정렬을 구분합니다.
- merge sort, quicksort, heapsort의 시간·공간 보장을 비교합니다.
- decision tree로 comparison sort의 `Ω(n log n)` 하한을 설명합니다.

## 선행지식

[점근 분석](../01-foundations/02-asymptotic-analysis.md), 비교 관계, 반복 불변식을 알고 있어야 합니다.

## 핵심 관점

“정렬합니다”라는 문장만으로는 결과가 정해지지 않습니다.

```text
오름차순입니까, 내림차순입니까?
어떤 필드를 key로 사용합니까?
같은 key의 기존 순서를 보존합니까?
입력 배열을 직접 바꿉니까?
추가 메모리를 얼마나 사용합니까?
최악 시간과 기대 시간 중 무엇을 보장합니까?
```

## 1. 안정 정렬

안정 정렬은 같은 key를 가진 원소의 원래 상대 순서를 보존합니다.

예를 들어 record를 먼저 이름으로 안정 정렬하고, 그다음 부서로 안정 정렬하면 최종 결과의 주 key는 부서이고 같은 부서 안에서는 이름 순서가 유지됩니다.

안정성이 필요하지 않다면 이를 위해 추가 메모리나 복잡한 구현을 사용할 이유는 없습니다. 반대로 여러 key를 순차 정렬할 때 안정성이 필요할 수 있습니다.

## 2. 대표 comparison sort

| 알고리즘 | 시간 | 추가 공간 | 안정성 | 주의점 |
| --- | --- | --- | --- | --- |
| merge sort | 최악 `O(n log n)` | 보통 `O(n)` | 안정 구현 가능 | 병합 buffer가 필요합니다. |
| quicksort | 기대 `O(n log n)`, 최악 `O(n²)` | 재귀 stack | 보통 불안정 | pivot과 partition 방식에 영향을 받습니다. |
| heapsort | 최악 `O(n log n)` | `O(1)` 구현 가능 | 불안정 | cache locality와 상수 비용을 확인합니다. |
| insertion sort | 최악 `O(n²)` | `O(1)` | 안정 구현 가능 | 작거나 거의 정렬된 입력에 유리할 수 있습니다. |

표준 library의 정렬은 여러 알고리즘을 조합할 수 있습니다. 실제로 필요한 안정성과 최악 시간 보장은 library 문서에서 확인합니다.

## 3. merge sort의 병합 불변식

정렬된 두 구간을 병합할 때 다음을 유지합니다.

```text
출력에 넣은 prefix는 두 입력에서 소비한 원소 전체를 정렬한 결과입니다.
각 pointer는 아직 소비하지 않은 첫 원소를 가리킵니다.
```

두 key가 같을 때 왼쪽 원소를 먼저 선택하면 원래 상대 순서를 보존할 수 있습니다.

병합이 매 단계 `Θ(n)`이고 재귀 깊이가 `Θ(log n)`이므로 전체 시간은 `Θ(n log n)`입니다.

## 4. quicksort partition

Partition 함수가 반환하는 값과 분할된 구간의 의미를 하나로 고정합니다.

예를 들면 다음과 같습니다.

```text
pivot 왼쪽의 값은 pivot 이하입니다.
pivot 오른쪽의 값은 pivot 이상입니다.
pivot은 최종 위치에 있습니다.
```

Hoare와 Lomuto partition은 pointer 이동과 반환 index의 의미가 다릅니다. 두 방식을 한 함수에서 섞지 않습니다.

같은 값이 많으면 3-way partition으로 `< pivot`, `== pivot`, `> pivot` 구간을 나누는 편이 불필요한 재귀를 줄일 수 있습니다.

## 5. comparison sort의 하한

서로 다른 `n`개 원소에는 `n!`개의 순열이 있습니다. 비교 기반 정렬은 각 비교 결과에 따라 두 갈래로 나뉘는 decision tree로 표현할 수 있습니다.

모든 입력 순열을 구분하려면 leaf가 최소 `n!`개 필요합니다. 높이가 `h`인 이진 tree의 leaf는 최대 `2^h`개이므로 다음이 성립합니다.

```text
2^h >= n!
h >= log2(n!) = Ω(n log n)
```

따라서 일반적인 comparison sort는 최악의 경우 `Ω(n log n)`번 비교해야 합니다.

이 주장은 key를 비교해서만 정보를 얻는 정렬에 적용됩니다.

## 6. counting sort와 radix sort

### counting sort

Key가 작은 정수 범위 `0..K`에 있다면 빈도 배열을 사용할 수 있습니다.

- 시간: `O(n+K)`
- 추가 공간: `O(K)`

`K`가 `n`보다 매우 크면 비효율적입니다. 음수 key나 큰 범위를 어떻게 변환할지도 정해야 합니다.

### radix sort

고정 길이 digit를 여러 번 정렬합니다. 낮은 digit에서 높은 digit 순으로 처리하는 LSD radix sort에서는 각 pass가 안정적이어야 이전 digit의 순서가 보존됩니다.

시간은 원소 수뿐 아니라 digit 수와 base에 따라 달라집니다.

Comparison sort 하한을 피하는 이유는 key의 표현과 범위를 직접 사용하기 때문입니다.

## 7. 전체 정렬이 필요하지 않은 경우

- 최솟값 하나만 필요하면 한 번 순회합니다.
- 상위 `k`개만 필요하면 크기 `k` heap을 검토합니다.
- `k`번째 원소만 필요하면 selection 알고리즘을 검토합니다.
- 여러 membership 질의만 필요하면 hash set이 적합할 수 있습니다.

필요하지 않은 전체 순서를 만들지 않습니다.

## 8. 정렬 결과 검증

다음 항목을 따로 확인합니다.

- 반환 결과가 정한 순서를 만족합니까?
- 원본과 같은 multiset입니까?
- 안정성이 필요하다면 같은 key의 기존 순서를 보존합니까?
- comparator가 일관된 순서를 만듭니까?
- 빈 입력, 중복, 이미 정렬된 입력, 역순 입력을 처리합니까?
- 입력을 직접 변경하는지 문서와 일치합니까?

순서만 검사하면 원소 유실이나 중복 삽입을 놓칠 수 있습니다.

## 9. 정렬과 탐색의 연결

정렬 비용을 한 번 지불하면 여러 lower-bound 질의를 `O(log n)`에 처리할 수 있습니다. 질의가 한 번뿐이라면 선형 탐색이 더 단순할 수 있습니다.

정렬 뒤 원래 index가 필요하다면 `(value, original_index)`를 함께 저장합니다. 같은 값의 index 순서가 반환 조건에 영향을 주는지도 확인합니다.

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)은 정렬 알고리즘 자체를 공개 API로 제공하지 않습니다. 대신 다음 함수가 정렬 결과에 의존합니다.

- `lower_bound`: 입력이 오름차순이라는 호출자 전조건이 있습니다.
- `select_intervals`: `(end, start)` 순서로 정렬합니다.
- `kruskal_mst`: `(weight, source, target)` 순서로 정렬합니다.

따라서 merge sort나 stable multi-key sort를 별도 작은 구현으로 작성하고 다음을 확인합니다.

- 결과 순서
- 원본 multiset 보존
- 같은 key의 original id 순서
- comparison 횟수와 최악 입력

## 완료 기준

- 정렬의 key, 방향, 동점 처리, 안정성, 입력 변경 여부를 적습니다.
- 대표 정렬의 최악 시간과 추가 공간을 비교합니다.
- `n!`개 순열과 decision tree 높이에서 `Ω(n log n)`을 유도합니다.
- counting·radix sort가 comparison 하한과 모순되지 않는 이유를 설명합니다.
- 정렬 결과에서 순서와 multiset 보존을 따로 검사합니다.

## 실패 신호

- 안정성이 필요한데 key 값만 확인합니다.
- quicksort의 기대 시간을 최악 보장처럼 표현합니다.
- counting sort에서 key 범위 `K`의 비용을 빠뜨립니다.
- comparison 하한을 모든 정렬에 적용합니다.
- 결과가 정렬되었다는 이유로 원소 유실·중복을 확인하지 않습니다.
