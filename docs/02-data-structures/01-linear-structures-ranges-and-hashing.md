# 선형 자료구조, 구간과 해시

## 학습 목표

- 배열, 연결 구조, stack, queue, deque를 필요한 연산으로 구분합니다.
- 반열린 구간과 누적 합으로 index 오류를 줄입니다.
- two pointers, sliding window, monotonic stack·deque를 적용할 수 있는 조건을 확인합니다.
- hash table의 기대 비용, 충돌, key 조건을 구분합니다.

## 선행지식

배열과 list의 index, [점근 분석](../01-foundations/02-asymptotic-analysis.md), 입력 조건을 정하는 방법을 먼저 이해해야 합니다.

## 핵심 관점

자료구조는 익숙한 이름이 아니라 실제로 필요한 연산에서 고릅니다.

```text
어떤 값을 자주 읽습니까?
어디에 삽입하고 어디에서 삭제합니까?
입력 순서를 보존해야 합니까?
최솟값, 최댓값, 가장 최근 값 중 무엇이 필요합니까?
key로 찾습니까, 위치로 찾습니까?
```

## 1. 선형 자료구조의 연산

| 자료구조 | 잘 지원하는 연산 | 주의할 연산 |
| --- | --- | --- |
| 동적 배열 | 임의 위치 읽기, 뒤쪽 `append` | 중간 삽입·삭제, 재할당 |
| 연결 구조 | node를 알고 있을 때 삽입·삭제 | 임의 위치 접근, cache locality |
| stack | 최근 원소의 `push`·`pop` | 중간 원소 접근 |
| queue | 먼저 들어온 원소 처리 | 뒤쪽 원소 제거 |
| deque | 양끝 삽입·삭제 | 일반적인 중간 삽입 |

동적 배열의 `append`는 한 번의 최악 비용이 항상 `O(1)`인 연산이 아닙니다. 공간이 부족하면 더 큰 배열을 할당하고 기존 원소를 옮깁니다. 여러 번의 `append`를 묶어 보면 상각 `O(1)`이 됩니다.

## 2. 반열린 구간

구간 `[left, right)`는 다음 성질을 가집니다.

- 길이는 `right - left`입니다.
- `left == right`이면 빈 구간입니다.
- `[a, b)`와 `[b, c)`는 겹치지 않습니다.
- 길이 `n`인 배열 전체는 `[0, n)`입니다.

누적 합도 같은 표현을 사용합니다.

```text
prefix[0] = 0
prefix[i+1] = prefix[i] + A[i]
sum(left, right) = prefix[right] - prefix[left]
```

전처리는 `O(n)`, 각 구간 합은 `O(1)`, 추가 공간은 `O(n)`입니다.

유지해야 할 조건은 다음과 같습니다.

```text
len(prefix) == n + 1
0 <= left <= right <= n
prefix[i] == sum(A[0:i])
```

## 3. 차분 배열

여러 구간에 같은 값을 더한 뒤 마지막 배열만 필요하다면 차분 배열을 사용할 수 있습니다.

```text
diff[left] += value
diff[right] -= value
```

모든 갱신이 끝난 뒤 누적 합을 한 번 계산하면 실제 값을 복원할 수 있습니다. 갱신 중간에 개별 원소나 구간 합을 계속 물어본다면 Fenwick tree나 segment tree처럼 갱신과 질의를 함께 지원하는 자료구조가 필요합니다.

## 4. two pointers와 sliding window

두 pointer가 안전하려면 한쪽 pointer를 움직여 버린 후보가 나중에 다시 필요하지 않아야 합니다.

예를 들어 모든 값이 음수가 아닌 배열에서 구간 합이 상한을 넘으면 왼쪽 pointer를 오른쪽으로 옮겨 합을 줄일 수 있습니다. 음수가 섞이면 오른쪽을 늘릴 때 합이 항상 증가하지 않으므로 같은 판단을 사용할 수 없습니다.

```text
현재 구간: [left, right)
저장값: 정확히 이 구간의 합이나 빈도
진행: right를 늘린 뒤 조건을 위반하는 동안 left를 늘립니다.
```

단조성이 없는 문제에 sliding window를 적용하지 않습니다.

## 5. monotonic stack과 deque

다음 큰 원소, 창의 최댓값처럼 현재 후보 중 일부가 앞으로 절대 답이 될 수 없는 문제에서는 후보를 단조 순서로 유지할 수 있습니다.

- 새 값보다 약한 뒤쪽 후보는 제거합니다.
- 창을 벗어난 index는 앞쪽에서 제거합니다.
- 각 원소는 최대 한 번 들어가고 한 번 나오므로 전체 비용은 `O(n)`입니다.

값만 저장하면 같은 값이 여러 번 있을 때 어느 원소가 창을 벗어났는지 알 수 없습니다. 만료 시점을 알아야 한다면 index를 저장합니다.

## 6. hash table

hash table은 key를 bucket으로 보내고 충돌을 처리합니다.

key에는 다음 조건이 필요합니다.

- 같은 key는 같은 hash를 가져야 합니다.
- 동등성 비교와 hash 계산이 같은 기준을 사용해야 합니다.
- 삽입한 뒤 값이 바뀌는 mutable object를 key로 사용하지 않습니다.
- 조회와 삽입은 보통 기대 `O(1)`이지만 최악 비용은 더 클 수 있습니다.

자주 저장하는 값은 다음과 같습니다.

- 등장 여부: `set`
- 빈도: `key -> count`
- 마지막 위치: `key -> index`
- 누적값이 처음 나온 위치: `prefix value -> earliest index`

## 7. 예제: 합이 `k`인 가장 긴 부분 배열

음수가 허용되면 sliding window를 사용할 수 없습니다. 누적 합 `S[i]`와 과거의 `S[j] = S[i] - k`를 찾습니다.

```text
map에는 각 누적값이 처음 나온 위치만 저장합니다.
현재 i에서 S[i] - k가 있으면 그 다음 위치부터 i까지의 합은 k입니다.
```

같은 누적값이 다시 나왔을 때 위치를 덮어쓰면 더 긴 구간을 잃을 수 있으므로 최초 위치를 보존해야 합니다.

## 8. 자료구조를 바꿀 때 확인할 비용

- 배열을 연결 list로 바꾸면 임의 index 접근이 느려집니다.
- queue를 Python `list.pop(0)`로 구현하면 원소 이동 때문에 `O(n)`이 듭니다.
- 전체 정렬이 필요하지 않은데 heap 대신 정렬을 반복하면 불필요한 비용이 생깁니다.
- hash key가 긴 문자열이나 tuple이면 hash 계산 자체의 비용도 고려합니다.

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 1]`에서 다음을 확인합니다.

- `prefix_sums`가 첫 값으로 `0`을 넣습니다.
- `range_sum`이 `[start, stop)`을 사용합니다.
- 빈 구간과 배열 전체를 같은 식으로 계산합니다.
- 잘못된 index 범위를 `ValueError`로 거부합니다.

exercise에는 sliding window와 monotonic deque가 포함되어 있지 않으므로, 창의 최댓값을 직접 구현하고 각 창을 순회한 결과와 비교합니다.

## 완료 기준

- `[start, stop)`의 길이와 빈 구간을 예제로 설명합니다.
- sliding window가 필요한 단조 조건과 음수 반례를 제시합니다.
- monotonic deque에 index를 저장해야 하는 이유를 설명합니다.
- hash table에서 기대 비용과 최악 비용을 구분합니다.
- 누적값의 최초 위치를 덮어쓸 때 실패하는 입력을 만듭니다.

## 실패 신호

- 구간 길이와 마지막 index를 섞어 사용합니다.
- sliding window의 단조 조건을 확인하지 않습니다.
- monotonic deque에 값만 저장해 만료 원소를 구분하지 못합니다.
- hash 조회를 무조건 최악 `O(1)`이라고 표현합니다.
- mutable key를 사용하거나 동등성 비교와 hash 계산 기준이 다릅니다.
