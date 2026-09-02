# 복잡도 클래스와 다항 시간 환원

이 문서는 필수 구현 경로가 아니라 이론을 정확히 표현하기 위한 참고 자료입니다.

## 학습 목표

- decision problem과 optimization problem을 구분합니다.
- P, NP, NP-hard, NP-complete의 관계를 정확히 설명합니다.
- certificate와 verifier의 크기·실행 시간을 입력의 bit 길이 기준으로 계산합니다.
- 다항 시간 many-one reduction의 방향과 그로부터 얻을 수 있는 난이도 주장을 확인합니다.
- 알려지지 않은 결과를 해결된 사실처럼 표현하지 않습니다.

## 선행지식

점근 시간, 입력의 bit 길이, yes/no 문제의 입력·출력 조건, 한 문제의 입력을 다른 문제의 입력으로 바꾸는 함수 개념을 알고 있어야 합니다.

특히 복잡도 이론에서는 `n`이 무엇을 뜻하는지 명확히 해야 합니다. 일반적으로 `n`은 입력에 포함된 숫자의 값이 아니라 **입력을 표현하는 데 필요한 bit의 수**, 즉 입력 길이를 뜻합니다.

예를 들어 정수 `C`를 binary로 표현하면 `C` 자체의 값은 매우 클 수 있지만 이를 표현하는 데 필요한 bit 수는 `Θ(log C)`입니다. 이 차이는 pseudo-polynomial 시간에서 중요합니다.

## 핵심 관점

복잡도 class는 특정 구현 한 번의 속도가 아니라 **입력 크기가 증가할 때 문제를 해결하는 데 필요한 계산 자원의 점근적 관계**를 다룹니다.

따라서 다음을 구분해야 합니다.

```text
특정 입력에서 실제로 얼마나 오래 걸렸는가?
vs.
입력 길이에 따라 실행 시간이 어떻게 증가하는가?
```

또한 `P`, `NP` 등의 정의는 기본적으로 decision problem을 기준으로 합니다. 최적값을 반환하는 문제를 바로 class에 넣기보다 적절한 decision version과의 관계를 먼저 정의합니다.

## 1. decision problem

**Decision problem**은 입력에 대해 `yes` 또는 `no` 중 하나를 답하는 문제입니다.

예:

```text
최단 경로 길이가 K 이하입니까?
무게 합이 C 이하이고 가치 합이 V 이상인 부분집합이 있습니까?
그래프에 크기 k인 clique가 있습니까?
```

반면 최솟값이나 최댓값 자체를 반환하는 문제는 일반적으로 **optimization problem**이라고 합니다.

예를 들어

```text
optimization:
그래프의 최소 vertex cover 크기를 구하십시오.

decision:
그래프에 크기 k 이하인 vertex cover가 있습니까?
```

처럼 대응시킬 수 있습니다.

복잡도 이론에서 optimization problem의 어려움을 논할 때는 이 decision version과의 관계를 명시해야 합니다. 두 문제를 이름만 보고 같은 문제라고 취급하면 안 됩니다.

## 2. P

`P`는 **결정적(deterministic) 알고리즘으로 입력 길이의 다항 시간 안에 풀 수 있는 decision problem의 집합**입니다.

즉 어떤 문제 `A`가 `P`에 속한다는 것은 어떤 상수 `c`에 대해

```text
T(n) = O(n^c)
```

인 결정적 알고리즘이 존재한다는 뜻입니다.

다항식의 차수가 크거나 상수 비용이 커도 이론적으로 `P`에 속할 수 있습니다. 따라서

```text
P에 속한다
```

와

```text
실무에서 항상 빠르다
```

는 같은 뜻이 아닙니다.

## 3. NP

`NP`는 **yes instance가 주어졌을 때, 다항 길이의 certificate를 다항 시간에 검증할 수 있는 decision problem의 집합**입니다.

문제의 입력을 `x`, certificate를 `y`라고 하면 다음 조건을 만족하는 verifier가 존재해야 합니다.

```text
x가 yes instance
iff
어떤 y가 존재하여 V(x, y) = accept
```

여기서 중요한 조건은 다음과 같습니다.

- certificate `y`의 길이가 입력 길이 `|x|`의 다항식으로 제한됩니다.
- verifier `V`가 `x`와 `y`를 받아 다항 시간에 종료합니다.
- yes instance에는 적어도 하나의 올바른 certificate가 존재합니다.
- no instance에는 verifier가 받아들이는 certificate가 하나도 없습니다.

예를 들어 Hamiltonian Cycle의 decision problem을 생각합시다.

```text
그래프 G에 모든 정점을 정확히 한 번 방문하고
출발점으로 돌아오는 cycle이 존재합니까?
```

certificate는 모든 정점을 방문하는 순서로 표현할 수 있습니다.

Verifier는 다음을 확인합니다.

1. certificate가 그래프의 정점 수에 맞는 길이를 가지는지 확인합니다.
2. 모든 정점이 정확히 한 번 등장하는지 확인합니다.
3. 연속한 정점 사이에 간선이 있는지 확인합니다.
4. 마지막 정점에서 첫 번째 정점으로 돌아가는 간선이 있는지 확인합니다.

정점 수가 `n`이라면 certificate에는 `O(n)`개의 정점 정보가 들어가므로 그 크기는 입력 길이에 대해 다항식으로 제한됩니다. 또한 정점 중복 검사와 간선 존재 검사를 적절한 자료구조로 수행하면 verifier 역시 입력 길이에 대해 다항 시간에 실행할 수 있습니다.

`NP`는 “non-polynomial”의 약자가 아닙니다. 또한 **no instance도 같은 방식으로 쉽게 검증된다는 뜻이 아닙니다.**

## 4. NP-hard와 NP-complete

두 개념의 핵심 차이는 `NP` membership입니다.

- **NP-hard**: `NP`의 모든 문제를 이 문제로 다항 시간에 환원할 수 있는 문제입니다.
- **NP-complete**: `NP-hard`이면서 동시에 `NP`에 속하는 decision problem입니다.

따라서

```text
NP-complete = NP ∩ NP-hard
```

라고 생각할 수 있습니다.

NP-hard 문제는 반드시 decision problem일 필요가 없으며 `NP` 밖에 있을 수도 있습니다. 따라서 다음 두 표현을 같은 뜻으로 사용하면 안 됩니다.

```text
NP-hard
NP-complete
```

어떤 문제를 NP-complete라고 보이려면 보통 다음 두 사실을 모두 보여야 합니다.

```text
1. B ∈ NP
2. B is NP-hard
```

## 5. 다항 시간 many-one reduction

`A <=p B`는 **문제 A의 입력 하나를 문제 B의 입력 하나로 다항 시간에 변환하고 yes/no 결과를 보존할 수 있다**는 뜻입니다.

정확히는 다항 시간에 계산되는 함수 `f`가 존재하여 모든 입력 `x`에 대해

```text
x가 A의 yes instance
iff
f(x)가 B의 yes instance
```

가 성립해야 합니다.

구조는 다음과 같습니다.

```text
A의 입력 x
    ↓
다항 시간 변환 f
    ↓
B의 입력 f(x)
    ↓
B를 푸는 알고리즘
    ↓
A의 답
```

따라서 B를 다항 시간에 풀 수 있다면 A도

```text
변환 시간 + B를 푸는 시간
```

으로 다항 시간에 풀 수 있습니다.

이 때문에 `A <=p B`는 **B가 A보다 적어도 어렵다는 결론을 뒷받침하는 방향**입니다. 이것은 두 문제의 실제 실행 시간이 모든 입력에서 직접 비교된다는 뜻은 아닙니다.

여기서 사용하는 reduction은 **polynomial-time many-one reduction**입니다. A의 한 입력을 B의 하나의 입력으로 바꾸고, B의 yes/no 답 하나를 사용합니다. 다른 종류의 reduction은 여러 질의 등을 허용할 수 있으므로 reduction의 종류를 명시해야 합니다.

## 6. 새 문제의 어려움을 보이는 방향

새 문제 `B`가 어렵다는 사실을 보이려면 이미 어렵다고 알려진 문제 `A`에서 출발하여

```text
A <=p B
```

를 보입니다.

직관적으로 이 관계가 주는 의미는

```text
B를 빠르게 풀 수 있다.
→ A도 빠르게 풀 수 있다.
```

입니다.

따라서 A가 이미 NP-hard라면 `A <=p B`를 통해 B도 NP-hard임을 보일 수 있습니다.

반대로

```text
B <=p A
```

만 보이면 B를 A의 알고리즘을 이용해 풀 수 있다는 사실을 얻을 뿐입니다. 이것만으로는 B가 A보다 어렵거나 NP-hard라고 결론 내릴 수 없습니다.

특히 NP-hardness를 증명할 때는 보통 **알려진 NP-hard 문제 A에서 새 문제 B로 환원**합니다.

## 7. NP-complete 증명 순서

새 decision problem `B`가 NP-complete임을 보이려면 일반적으로 다음 순서를 사용합니다.

### 1단계: `B ∈ NP`

- certificate를 정의합니다.
- certificate가 입력 길이의 다항식 크기임을 보입니다.
- verifier가 certificate의 유효성을 다항 시간에 검사함을 보입니다.
- yes instance에는 올바른 certificate가 존재하고 no instance에는 verifier가 받아들이는 certificate가 없음을 설명합니다.

### 2단계: 알려진 NP-complete 문제 `A` 선택

이미 NP-complete인 문제를 하나 고릅니다.

### 3단계: `A <=p B` 구성

A의 입력 `x`를 B의 입력 `f(x)`로 변환하는 방법을 정의합니다.

### 4단계: 정답 보존 증명

다음 양방향을 보입니다.

```text
x가 A의 yes instance
iff
f(x)가 B의 yes instance
```

`yes -> yes`만 보이는 것으로는 충분하지 않습니다. many-one reduction에서는 `no -> no`도 필요하며, 위의 `iff`가 이를 함께 표현합니다.

### 5단계: 다항 시간성 확인

변환 `f`를 계산하는 시간이 입력 길이에 대해 다항식인지 확인합니다.

또한 `f(x)`의 크기가 입력 길이에 대해 다항식으로 제한되는지도 확인합니다. 일반적인 문자열 입력 모델에서 다항 시간에 출력한 결과는 그 실행 시간만큼의 출력 기호를 넘을 수 없으므로 결과 크기도 다항식으로 제한됩니다.

이 과정을 통해

```text
B ∈ NP
+
A <=p B, A가 NP-complete
```

이면 B는 NP-hard이고 B ∈ NP이므로 B는 NP-complete입니다.

NP-hard만 보이려는 경우에는 첫 번째 membership 단계가 필요하지 않을 수 있습니다.

## 8. 예제: Independent Set과 Vertex Cover

그래프를

```text
G = (V, E)
```

라고 합시다.

**Independent Set**은 선택한 정점들 사이에 간선이 하나도 없는 정점 집합입니다.

**Vertex Cover**는 그래프의 모든 간선에 대해 적어도 한 끝점이 선택된 정점 집합입니다.

정점 집합 `S`에 대해 다음이 성립합니다.

```text
S가 independent set
iff
V-S가 vertex cover
```

왜냐하면 `S` 안에 간선 `(u, v)`가 존재하면 그 간선의 두 끝점 모두가 `S`에 있으므로 `V-S`에는 어느 끝점도 없습니다. 따라서 `V-S`는 그 간선을 cover하지 못합니다.

반대로 `S` 안에 간선이 하나도 없다면 모든 간선은 적어도 한 끝점을 `V-S`에 가지므로 `V-S`는 vertex cover입니다.

따라서 decision problem의 parameter를 대응시키면

```text
G에 크기 k인 independent set이 있습니다.
iff
G에 크기 |V|-k인 vertex cover가 있습니다.
```

가 됩니다.

이 변환은 graph 자체를 바꾸지 않고 parameter만 `k`에서 `|V|-k`로 바꾸므로 다항 시간에 계산할 수 있습니다.

이 관계 자체와 NP-hardness 증명의 방향은 구분해야 합니다. 두 문제가 서로 변환된다는 사실만으로 어느 한 문제가 NP-hard라는 결론이 자동으로 나오지는 않습니다. 어떤 방향의 reduction인지와 출발 문제의 복잡도 class를 함께 확인해야 합니다.

## 9. pseudo-polynomial 시간

0/1 knapsack의 대표적인 DP에서 시간 복잡도가

```text
O(nC)
```

라고 합시다. 여기서 `n`은 item 수이고 `C`는 capacity의 **숫자 값**입니다.

문제는 `C`가 binary로 표현될 때 발생합니다.

예를 들어

```text
C = 1,000,000
```

이라는 숫자를 표현하는 데 필요한 bit 수는 `C` 자체의 값보다 훨씬 작으며 `Θ(log C)`입니다.

따라서 `O(nC)`는 `n`과 `C`라는 숫자 값에 대해서는 다항식이지만, 입력의 전체 bit 길이

```text
L = Θ(n + log C + ...)
```

에 대해서는 일반적으로 다항식이 아닙니다.

이처럼 입력에 등장하는 숫자의 **값 자체**에 다항식인 실행 시간을 **pseudo-polynomial time**이라고 합니다.

따라서 다음을 항상 구분해야 합니다.

```text
숫자의 값 C
vs.
그 숫자를 표현하는 데 필요한 bit 수 Θ(log C)
```

이 구분이 없으면 `O(nC)` 알고리즘을 일반적인 의미의 polynomial-time 알고리즘으로 잘못 분류할 수 있습니다.

## 10. verifier는 최적해를 다시 계산하지 않습니다

Certificate verifier의 역할은 **주어진 certificate가 해당 decision problem의 yes 조건을 만족하는지 검사하는 것**입니다.

예를 들어 Vertex Cover decision problem이

```text
그래프 G에 크기 k 이하의 vertex cover가 있습니까?
```

라면 certificate로 선택된 정점 집합 `S`를 받을 수 있습니다.

Verifier는 다음을 확인합니다.

```text
|S| <= k
모든 간선 (u, v)에 대해
u ∈ S 또는 v ∈ S
```

이 검사는 주어진 `S`가 조건을 만족하는지를 확인하는 것이지, 최소 vertex cover 자체를 처음부터 계산하는 것이 아닙니다.

왜 이것으로 충분한지도 decision problem의 정의와 연결해서 봐야 합니다.

```text
yes instance
→ 조건을 만족하는 적절한 S가 하나 존재
→ 그 S를 certificate로 제시
→ verifier가 다항 시간에 확인
```

반면 “이 vertex cover가 **최소**인가?”처럼 최적성 자체를 검증하는 문제는 단순히 feasible solution 하나를 제시하는 것만으로 충분하지 않을 수 있습니다. 최적성에 대한 추가 증명이나 다른 형태의 certificate가 필요할 수 있으므로, **feasibility 검증과 optimality 검증을 구분**해야 합니다.

## 11. P와 NP에 관한 표현

복잡도 이론에서는 아직 증명되지 않은 명제를 이미 해결된 사실처럼 표현하지 않도록 주의합니다.

다음과 같은 단정을 피합니다.

- 다항 알고리즘을 찾지 못했다는 이유만으로 NP-hard라고 결론 내리지 않습니다.
- 지수 시간 알고리즘이 있다는 이유만으로 NP-hard라고 결론 내리지 않습니다.
- NP-complete 문제에 다항 알고리즘을 제시했다고 주장할 때는 정확성·시간 증명이 필요합니다.
- `P = NP` 또는 `P ≠ NP`를 이미 해결된 사실처럼 표현하지 않습니다.

특히 **현재 알려진 알고리즘이 지수 시간이라는 사실**과 **다항 시간 알고리즘이 존재하지 않는다는 사실**은 다릅니다. 후자를 주장하려면 그에 맞는 이론적 증명이 필요합니다.

## 환원 검토표

- 출발 문제와 도착 문제를 정확히 정의했습니까?
- 두 문제가 같은 decision-problem 형식으로 정의되어 있습니까?
- 입력 parameter가 어떻게 바뀌는지 명확합니까?
- 변환이 다항 시간에 계산됩니까?
- 변환 결과의 크기가 입력 길이에 대해 다항식으로 제한됩니까?
- `yes -> yes`와 `no -> no`가 모두 성립합니까?
- reduction의 방향으로 얻으려는 결론이 맞습니까?
- 사용하는 reduction이 many-one reduction인지 명시했습니까?
- NP-complete라고 주장한다면 도착 문제의 NP membership도 보였습니까?
- 최적화 문제를 다룬다면 대응하는 decision version을 정의했습니까?

## 연결 학습

필수 exercise에는 complexity-class 증명 API가 없습니다. 따라서 다음 내용을 코드 밖에서 작성하고 검토합니다.

- Hamiltonian Cycle certificate와 verifier
- 비교 정렬 하한에서 decision tree가 필요한 이유
- 0/1 knapsack `O(nC)`가 pseudo-polynomial인 이유
- 알려진 문제 `A`에서 새 문제 `B`로 가는 환원 방향

[`verified-algorithms`](../../exercises/verified-algorithms/)의 MST 간선 목록과 flow matrix는 **결과를 별도 검증할 수 있는 입력·출력 구조**라는 점에서 이 문서와 연결됩니다. 다만 이것이 곧 NP membership의 certificate/verifier 예제라는 뜻은 아닙니다. 실제 NP membership을 주장하려면 해당 decision problem과 certificate 및 verifier를 별도로 정의해야 합니다.

## 완료 기준

- P, NP, NP-hard, NP-complete를 서로 다른 문장으로 정의합니다.
- certificate 길이와 verifier 시간을 입력 bit 길이 기준으로 계산합니다.
- 새 문제의 어려움을 보일 때 알려진 어려운 문제에서 새 문제로 환원합니다.
- 변환 시간, 결과 크기, yes/no 양방향을 모두 설명합니다.
- reduction의 방향에 따라 얻을 수 있는 결론이 달라짐을 설명합니다.
- pseudo-polynomial 시간과 입력 bit 길이에 대한 다항 시간을 구분합니다.
- NP-hard와 NP-complete를 구분하고 NP-complete 증명에서 NP membership이 필요한 이유를 설명할 수 있습니다.

## 실패 신호

- NP를 다항 시간에 풀 수 없는 문제로 정의합니다.
- NP-hard와 NP-complete를 같은 뜻으로 사용합니다.
- 새 문제에서 알려진 문제로 환원한 뒤 새 문제가 어렵다고 결론 내립니다.
- `A <=p B`의 의미를 “A와 B가 비슷한 난이도”라고 해석합니다.
- `yes -> yes`만 확인하고 many-one reduction이 완료되었다고 생각합니다.
- verifier가 최적해를 처음부터 다시 계산합니다.
- 숫자 값과 binary 표현 길이를 같은 크기로 봅니다.
- `O(nC)`를 무조건 polynomial time이라고 부릅니다.
- 실험에서 느렸다는 이유로 복잡도 하한이나 NP-hardness를 주장합니다.
- `P = NP` 또는 `P ≠ NP`를 증명되지 않은 상태에서 사실처럼 단정합니다.
