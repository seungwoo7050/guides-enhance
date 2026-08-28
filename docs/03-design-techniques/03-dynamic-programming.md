# 동적 계획법

## 학습 목표

- 이후 결과를 결정하는 데 필요한 최소 정보로 상태를 정의합니다.
- 상태 정의, recurrence, base case, 계산 순서를 구분합니다.
- memoization과 tabulation을 같은 상태 의존 관계를 계산하는 두 방법으로 이해합니다.
- 필요할 때 최적값뿐 아니라 실제 선택 결과도 복원합니다.

## 선행지식

재귀적 문제 분해, [점화식](../01-foundations/03-recurrences-and-divide-and-conquer.md), 상태 불변식을 설명할 수 있어야 합니다.

## 핵심 관점

Dynamic programming은 다음 조건을 만족할 때 사용합니다.

```text
같은 하위 문제가 여러 경로에서 반복됩니다.
하위 문제의 결과로 현재 결과를 계산할 수 있습니다.
상태 사이 의존 관계를 cycle 없이 계산할 수 있습니다.
```

Table부터 만들지 말고 각 칸이 무엇을 뜻하는지 먼저 적습니다.

## 1. 상태를 완전한 문장으로 정의합니다

좋은 상태 정의에는 처리한 입력 범위와 반환값의 의미가 들어갑니다.

```text
dp[i] = 처음 i개 원소를 처리했을 때의 최적값
dp[i][c] = 처음 i개 물건과 capacity c로 얻는 최대 가치
dp[i][j] = A[:i]와 B[:j]의 LCS 길이
```

“현재까지의 최적값”처럼 어느 입력을 처리했는지 없는 정의로는 recurrence를 정확히 정할 수 없습니다.

## 2. 0/1 knapsack

각 물건 `(weight, value)`를 사용하지 않거나 한 번만 사용합니다.

```text
dp[i][c] = max(
    dp[i-1][c],
    dp[i-1][c-weight_i] + value_i  if weight_i <= c
)
```

두 선택은 다음을 뜻합니다.

- 현재 물건을 사용하지 않습니다.
- 현재 물건을 한 번 사용하고 남은 capacity의 이전 결과를 더합니다.

현재 행 `dp[i]`를 다시 읽으면 같은 물건을 여러 번 사용할 수 있어 문제 자체가 unbounded knapsack으로 바뀝니다.

### 1차원 배열로 줄일 때

capacity를 큰 값에서 작은 값으로 순회합니다.

```text
for each item:
    for c from capacity down to item.weight:
        best[c] = max(best[c], best[c-item.weight] + item.value)
```

오름차순으로 갱신하면 방금 바꾼 값을 같은 item에서 다시 읽어 물건을 여러 번 사용합니다.

## 3. LCS

두 문자열 prefix의 longest common subsequence 길이를 구합니다.

```text
if A[i-1] == B[j-1]:
    dp[i][j] = dp[i-1][j-1] + 1
else:
    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
```

substring과 달리 문자 사이에 다른 문자가 있어도 순서만 유지하면 됩니다.

길이만 반환한다면 동점에서 어느 방향을 골라도 됩니다. 실제 subsequence를 반환하거나 사전순 최소를 요구하면 predecessor와 동점 규칙을 추가해야 합니다.

## 4. 계산 순서

각 상태가 참조하는 값이 먼저 계산되도록 순서를 정합니다.

- prefix 상태: 작은 index에서 큰 index로 진행합니다.
- interval DP: 짧은 구간에서 긴 구간으로 진행합니다.
- DAG path DP: topological order로 진행합니다.
- 0/1 knapsack 1차원: capacity를 내림차순으로 갱신합니다.
- unbounded knapsack: capacity를 오름차순으로 갱신할 수 있습니다.

순서를 외우지 말고 현재 갱신이 같은 단계의 새 값을 읽는지 확인합니다.

## 5. memoization과 tabulation

### memoization

재귀 함수 결과를 key로 저장합니다.

- 실제로 필요한 상태만 계산하기 쉽습니다.
- recurrence를 코드에 직접 표현하기 쉽습니다.
- recursion depth와 hash key 생성 비용을 고려해야 합니다.

### tabulation

작은 상태부터 배열이나 map을 채웁니다.

- 계산 순서와 memory layout을 직접 제어하기 쉽습니다.
- 실제로 필요하지 않은 상태까지 계산할 수 있습니다.

두 방법이 같은 상태 정의와 recurrence를 사용한다면 알고리즘의 핵심은 같습니다.

## 6. 공간을 줄일 때 확인할 점

현재 row가 직전 row만 참조한다면 두 row나 한 row로 줄일 수 있습니다. 하지만 먼저 다음을 확인합니다.

- 갱신 전 값과 갱신 후 값을 같은 배열에서 구분할 수 있습니까?
- 실제 해를 복원하려면 이전 선택 정보가 필요하지 않습니까?
- 계산 순서를 바꾸면서 recurrence 의미가 달라지지 않습니까?
- 공간을 줄인 코드가 오류 가능성을 지나치게 높이지 않습니까?

## 7. 실제 해 복원

최적값만 저장했다면 recurrence를 역으로 따라가며 선택을 복원할 수 있습니다. 또는 각 상태에 predecessor나 선택 종류를 저장합니다.

복원 결과는 다음을 만족해야 합니다.

- 계산한 최적값과 실제 결과의 값이 같습니다.
- 원본 제약을 모두 지킵니다.
- 같은 항목을 허용 횟수보다 많이 사용하지 않습니다.
- 동점 규칙을 지킵니다.
- 복원 비용이 전체 시간 상한을 바꾸지 않습니다.

## 8. DP를 사용하기 어려운 경우

- 이후 결과를 정하려면 과거 전체가 필요합니다.
- 같은 key처럼 보이는 상태가 실제로는 다른 이후 제약을 가집니다.
- 의존 관계에 cycle이 있고 fixed point의 의미가 정해지지 않았습니다.
- 상태 수와 전이 수가 입력 제한보다 큽니다.
- greedy 교환 논리로 더 단순하게 풀 수 있습니다.

## 9. 기준 계산과 비교합니다

작은 입력에서는 가능한 선택을 모두 검사합니다.

- knapsack: 모든 물건 부분집합
- LCS: 짧은 문자열의 모든 subsequence
- 작은 DAG DP: 가능한 경로 전체

기준 계산은 후보와 같은 table 갱신 코드를 사용하지 않습니다.

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)에서 다음을 확인합니다.

- `[Implementation 4]` `knapsack_01`이 capacity를 내림차순으로 갱신합니다.
- 음수 value가 있어도 아무것도 고르지 않은 값 `0`을 유지합니다.
- `[Implementation 6]` `lcs_length`가 짧은 문자열을 열로 두어 추가 공간을 줄입니다.
- 테스트가 부분집합과 subsequence 전수 계산으로 결과를 비교합니다.

## 완료 기준

- 각 상태가 어떤 입력 범위와 결과를 뜻하는지 한 문장으로 적습니다.
- recurrence의 모든 참조 상태가 먼저 계산되는 순서를 설명합니다.
- base case가 빈 입력의 반환 조건과 일치하는지 확인합니다.
- 공간 최적화 전후 결과가 같은지 독립 계산과 비교합니다.
- 실제 해가 필요할 때 복원 정보와 동점 규칙을 설계합니다.

## 실패 신호

- 상태 정의에 처리한 입력 범위가 없습니다.
- base case가 빈 입력의 함수 조건과 다릅니다.
- 0/1 knapsack을 capacity 오름차순으로 갱신합니다.
- memo key에서 이후 결과에 필요한 값을 빠뜨립니다.
- 공간을 줄인 뒤 실제 해를 복원할 수 없게 되었습니다.
- 최적 부분 문제를 설명하지 않고 table 크기부터 정합니다.
