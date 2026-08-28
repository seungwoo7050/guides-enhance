# 복잡도 클래스와 다항 시간 환원

이 문서는 필수 구현 경로가 아니라 이론을 정확히 표현하기 위한 참고 자료입니다.

## 학습 목표

- decision problem과 optimization problem을 구분합니다.
- P, NP, NP-hard, NP-complete의 관계를 정확히 설명합니다.
- certificate와 verifier의 크기·실행 시간을 입력 길이로 계산합니다.
- 환원 방향으로 얻을 수 있는 난이도 주장을 확인합니다.
- 알려지지 않은 결과를 해결된 사실처럼 표현하지 않습니다.

## 선행지식

점근 시간, 입력의 bit 길이, yes/no 문제의 입력·출력 조건, 한 문제의 입력을 다른 문제의 입력으로 바꾸는 함수 개념을 알고 있어야 합니다.

## 핵심 관점

복잡도 class는 특정 구현 한 번의 속도가 아니라 입력 크기가 커지는 문제 전체에 필요한 계산 자원을 다룹니다.

## 1. decision problem

복잡도 이론에서는 주로 yes/no로 답하는 문제를 사용합니다.

예:

```text
최단 경로 길이가 K 이하입니까?
무게 합이 C 이하이고 가치 합이 V 이상인 부분집합이 있습니까?
그래프에 크기 k인 clique가 있습니까?
```

최솟값이나 최댓값을 반환하는 optimization problem을 사용하려면 먼저 대응하는 decision version과의 관계를 설명합니다.

## 2. P

P는 결정적 알고리즘으로 입력 길이의 다항 시간 안에 풀 수 있는 decision problem의 집합입니다.

다항식의 차수가 크거나 상수 비용이 커도 이론적으로 P에 속할 수 있습니다. P에 속한다는 말과 실무에서 빠르다는 말은 같은 뜻이 아닙니다.

## 3. NP

NP는 yes instance에 대해 다음 조건을 만족하는 certificate가 있는 decision problem의 집합입니다.

- certificate 길이가 입력 길이의 다항식으로 제한됩니다.
- certificate가 정답을 증명하는지 다항 시간에 검사할 수 있습니다.

예를 들어 Hamiltonian Cycle의 certificate는 모든 정점을 방문하는 순서입니다. Verifier는 다음을 확인합니다.

1. 정점 수와 certificate 길이가 맞습니다.
2. 모든 정점이 정확히 한 번 등장합니다.
3. 연속한 정점 사이에 간선이 있습니다.
4. 마지막 정점에서 첫 정점으로 돌아가는 간선이 있습니다.

NP는 “non-polynomial”의 약자가 아닙니다. 또한 no instance도 같은 방식으로 쉽게 검증된다는 뜻은 아닙니다.

## 4. NP-hard와 NP-complete

- NP-hard: NP의 모든 문제를 이 문제로 다항 시간에 환원할 수 있습니다.
- NP-complete: NP-hard이면서 NP에도 속합니다.

NP-hard 문제는 decision problem이 아닐 수도 있고 NP 밖에 있을 수도 있습니다. 따라서 NP-hard와 NP-complete를 같은 뜻으로 사용하지 않습니다.

## 5. 다항 시간 many-one reduction

`A <=p B`는 A의 입력 `x`를 다항 시간에 B의 입력 `f(x)`로 바꾸며 yes/no 결과를 보존한다는 뜻입니다.

```text
x가 A의 yes instance
iff
f(x)가 B의 yes instance
```

B를 빠르게 풀 수 있다면 변환과 B의 알고리즘을 이어서 A도 빠르게 풀 수 있습니다.

## 6. 새 문제의 어려움을 보이는 방향

새 문제 `B`가 어렵다는 사실을 보이려면 이미 어려운 것으로 알려진 문제 `A`에서 출발합니다.

```text
A <=p B
```

반대로 `B <=p A`만 보이면 B가 A보다 어렵다는 결론은 나오지 않습니다. B를 A를 이용해 풀 수 있다는 사실만 알 수 있습니다.

## 7. NP-complete 증명 순서

1. `B`가 NP에 속함을 보입니다.
   - certificate를 정의합니다.
   - verifier가 yes certificate를 정확히 받아들이는지 보입니다.
   - certificate 길이와 검증 시간이 다항식인지 계산합니다.
2. 알려진 NP-complete 문제 `A`를 고릅니다.
3. `A`의 입력을 `B`의 입력으로 다항 시간에 바꿉니다.
4. yes이면 yes이고, yes가 아니면 yes가 아닌 양방향을 증명합니다.
5. 만들어진 입력 크기가 원래 입력의 다항식으로 제한되는지 확인합니다.

NP-hard만 보이려면 첫 membership 단계가 필요하지 않을 수 있지만, NP-complete 결론에는 `B ∈ NP`가 필요합니다.

## 8. 예제: Independent Set과 Vertex Cover

정점 집합 `S`가 independent set이면 `V-S`는 vertex cover입니다. 반대도 성립합니다.

```text
G에 크기 k인 independent set이 있습니다.
iff
G에 크기 |V|-k인 vertex cover가 있습니다.
```

같은 graph를 사용하고 parameter만 바꿉니다. 두 방향에서 간선의 양끝 중 적어도 하나가 cover에 포함되는지 확인해야 합니다.

## 9. pseudo-polynomial 시간

0/1 knapsack의 `O(nC)` DP에서 `C`는 capacity 값입니다. 입력에서 `C`가 binary로 표현되면 `C`를 적는 데 필요한 길이는 `log C`입니다.

따라서 `O(nC)`는 숫자 값에는 다항식이지만 입력 bit 길이에는 다항식이 아닐 수 있습니다. 이런 실행 시간을 pseudo-polynomial이라고 합니다.

값의 크기와 그 값을 표현하는 bit 수를 구분합니다.

## 10. verifier는 최적해를 다시 계산하지 않습니다

Certificate 검증은 주어진 답이 조건을 만족하는지 확인합니다. 예를 들어 Vertex Cover verifier는 다음을 확인합니다.

- 선택한 정점 수가 `k` 이하입니다.
- 모든 간선의 양끝 중 하나 이상이 선택되어 있습니다.

최소 vertex cover를 다시 계산할 필요는 없습니다. 최적성 자체를 증명하는 certificate가 필요한 문제라면 별도 upper·lower bound나 dual certificate가 필요할 수 있습니다.

## 11. P와 NP에 관한 표현

다음과 같은 단정을 피합니다.

- 다항 알고리즘을 찾지 못했다는 이유로 NP-hard라고 결론 내리지 않습니다.
- 지수 시간 알고리즘이 있다는 이유로 NP-hard라고 결론 내리지 않습니다.
- NP-complete 문제에 다항 알고리즘을 제시했다고 주장할 때는 정확성·시간 증명이 필요합니다.
- P와 NP의 관계를 이미 해결된 사실처럼 표현하지 않습니다.

## 환원 검토표

- 출발 문제와 도착 문제를 정확히 정의했습니까?
- 두 문제가 decision version입니까?
- parameter가 어떻게 바뀝니까?
- 변환 시간과 결과 크기가 다항식입니까?
- `yes -> yes`와 `no -> no`가 모두 성립합니까?
- 환원 방향으로 얻으려는 결론이 맞습니까?
- NP-complete라고 주장한다면 NP membership도 보였습니까?

## 연결 학습

필수 exercise에는 complexity-class 증명 API가 없습니다. 따라서 다음 내용을 코드 밖에서 작성하고 검토합니다.

- Hamiltonian Cycle certificate와 verifier
- 비교 정렬 하한에서 decision tree가 필요한 이유
- 0/1 knapsack `O(nC)`가 pseudo-polynomial인 이유
- 알려진 문제 `A`에서 새 문제 `B`로 가는 환원 방향

[`verified-algorithms`](../../exercises/verified-algorithms/)의 MST 간선 목록과 flow matrix는 certificate를 반환하고 별도 검증기로 확인한다는 점에서 이 문서와 연결됩니다. 다만 두 함수가 NP membership을 보이는 예제라는 뜻은 아닙니다.

## 완료 기준

- P, NP, NP-hard, NP-complete를 서로 다른 문장으로 정의합니다.
- Certificate 길이와 verifier 시간을 입력 bit 길이로 계산합니다.
- 새 문제의 어려움을 보일 때 알려진 어려운 문제에서 출발합니다.
- 변환 시간, 결과 크기, yes/no 양방향을 모두 설명합니다.
- pseudo-polynomial 시간과 입력 길이의 다항 시간을 구분합니다.

## 실패 신호

- NP를 다항 시간에 풀 수 없는 문제로 정의합니다.
- NP-hard와 NP-complete를 같은 뜻으로 사용합니다.
- 새 문제에서 알려진 문제로 환원한 뒤 새 문제가 어렵다고 결론 내립니다.
- Verifier가 최적해를 처음부터 다시 계산합니다.
- 숫자 값과 binary 표현 길이를 같은 크기로 봅니다.
- 실험에서 느렸다는 이유로 복잡도 하한을 주장합니다.
