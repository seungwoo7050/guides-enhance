# 문자열 검색과 전처리

## 학습 목표

- byte, Unicode code point, grapheme cluster 중 어떤 단위로 index를 계산하는지 정합니다.
- 단순 문자열 검색에서 같은 비교가 반복되는 이유를 설명합니다.
- KMP의 prefix function이 무엇을 저장하고, mismatch 뒤 어떤 상태로 fallback하는지 설명합니다.
- 첫 일치 검색과 모든 일치 검색의 상태 전이 차이를 구분합니다.
- rolling hash의 충돌 가능성과 정확성을 보장하는 검증 방법을 정합니다.

## 선행지식

[선형 구간](../02-data-structures/01-linear-structures-ranges-and-hashing.md), 반복 불변식, 문자열 index 범위를 알고 있어야 합니다.

이 문서에서 본문은 `T`, pattern은 `P`로 표기하고, 길이는 각각 `n`, `m`으로 표기합니다. 별도 설명이 없으면 index는 `0`부터 시작한다고 가정합니다.

## 핵심 관점

문자열 알고리즘을 선택하기 전에 **무엇을 한 글자로 취급하고 어떤 좌표계를 반환할지** 먼저 정해야 합니다.

```text
byte 위치를 반환합니까?
Unicode code point 위치를 반환합니까?
사용자가 보는 문자, 즉 grapheme cluster 위치를 반환합니까?
검색 전에 대소문자 변환이나 Unicode normalization을 적용합니까?
```

이 구분은 단순한 구현 세부사항이 아닙니다.

UTF-8에서는 한 Unicode code point가 여러 byte로 인코딩될 수 있습니다. 또한 사용자가 화면에서 한 글자로 인식하는 grapheme cluster는 여러 Unicode code point로 구성될 수 있습니다. 따라서 다음 값은 서로 다를 수 있습니다.

```text
byte index
code point index
grapheme cluster index
```

검색 전에 normalization이나 대소문자 변환을 수행하면 **전처리된 문자열의 index가 원본 문자열의 index와 항상 일치한다고 가정할 수 없습니다.** 원본 위치를 반환해야 한다면 전처리 과정에서 위치 대응 관계를 보존할지, 아니면 반환값이 전처리된 문자열 기준이라고 API에 명시할지 결정해야 합니다.

알고리즘 자체가 `O(n)`이어도 decoding, normalization, grapheme segmentation 같은 전처리 비용은 별도로 발생할 수 있습니다. 따라서 시간 복잡도를 말할 때는 알고리즘에 전달된 문자열 표현이 이미 준비되어 있는지도 구분합니다.

## 1. 단순 문자열 검색

가장 직접적인 방법은 본문 `T`의 가능한 각 시작 위치에서 pattern `P`를 앞부터 비교하는 것입니다.

```text
for start in 0 .. n-m:
    P와 T[start:start+m]을 앞에서부터 비교합니다.
    모두 같으면 start를 반환합니다.
```

예를 들어 다음 입력을 생각합니다.

```text
text    = "aaaaab"
pattern = "aaab"
```

시작 위치마다 pattern의 앞부분 `"aaa"`가 반복해서 일치한 뒤 뒤쪽에서 실패할 수 있습니다. 단순 검색은 이전 시작 위치에서 확인했던 사실을 다음 시작 위치에 이용하지 않기 때문에 같은 본문 문자를 여러 번 비교할 수 있습니다.

가능한 시작 위치는 `n-m+1`개이고 각 위치에서 최대 `m`개 문자를 비교하므로 최악 시간은 다음과 같습니다.

```text
O((n-m+1)m)
```

보통 상한을 단순화해 `O(nm)`이라고 표현합니다.

다만 다음과 같은 경우에는 단순 검색도 충분히 좋은 선택입니다.

- pattern이 매우 짧습니다.
- 입력 자체가 작습니다.
- 검색을 한 번만 수행합니다.
- 구현 단순성이 중요합니다.
- 더 복잡한 알고리즘을 검증하기 위한 기준 구현이 필요합니다.

복잡도가 더 낮은 알고리즘이 항상 실제 프로그램에서 더 빠르다는 뜻은 아닙니다. 입력 크기와 상수 비용도 함께 봅니다.

## 2. 이미 확인한 일치 정보를 상태로 남깁니다

KMP의 핵심은 mismatch가 발생했을 때 pattern을 무조건 처음부터 다시 비교하지 않는 것입니다.

본문의 어떤 위치까지 pattern의 앞 `k`글자가 일치했다고 가정합니다.

```text
P[0:k] == 지금까지 일치한 본문의 마지막 k글자
```

그 다음 문자에서 실패했을 때 필요한 질문은 다음과 같습니다.

> 지금까지 일치한 `P[0:k]`의 suffix 중에서, 동시에 `P`의 prefix인 가장 긴 문자열은 무엇인가?

그 길이를 알면 이미 확인한 문자 관계를 재사용하여 더 짧은 후보 상태에서 검색을 계속할 수 있습니다.

여기서 사용하는 값이 KMP의 **prefix function**입니다.

### proper prefix

문자열의 prefix는 문자열의 처음부터 시작하는 부분 문자열입니다.

예를 들어 `"abab"`의 prefix는 다음과 같습니다.

```text
""
"a"
"ab"
"aba"
"abab"
```

**proper prefix**는 문자열 전체 자신을 제외한 prefix입니다. 따라서 `"abab"`의 proper prefix에는 `"abab"` 자체가 포함되지 않습니다.

suffix는 문자열의 끝에서 끝나는 부분 문자열입니다.

KMP에서는 어떤 부분 문자열의 **proper prefix이면서 동시에 suffix인 가장 긴 문자열의 길이**를 저장합니다.

## 3. prefix function

`pi[i]`를 다음과 같이 정의합니다.

> `P[0:i+1]`의 proper prefix이면서 suffix인 문자열 중 가장 긴 것의 길이

즉 `pi[i] = k`라면 다음 관계가 성립합니다.

```text
P[0:k] == P[i-k+1:i+1]
```

그리고 `k < i+1`이므로 문자열 전체 자신은 후보에서 제외됩니다.

### 예시

pattern이 다음과 같다고 가정합니다.

```text
P = "ababaca"
```

prefix function은 다음과 같습니다.

```text
index  0 1 2 3 4 5 6
char   a b a b a c a
pi     0 0 1 2 3 0 1
```

몇 값을 직접 확인하면 다음과 같습니다.

```text
P[0:3] = "aba"
proper prefix이면서 suffix인 최장 문자열 = "a"
pi[2] = 1

P[0:5] = "ababa"
proper prefix이면서 suffix인 최장 문자열 = "aba"
pi[4] = 3

P[0:6] = "ababac"
공통인 non-empty proper prefix와 suffix가 없음
pi[5] = 0
```

### 계산 과정

```text
pi[0] = 0

for i in 1 .. m-1:
    j = pi[i-1]

    while j > 0 and P[i] != P[j]:
        j = pi[j-1]

    if P[i] == P[j]:
        j += 1

    pi[i] = j
```

반복 중 `j`는 **현재 검사 중인 prefix-suffix 후보의 길이**입니다.

처음에는 `pi[i-1]`을 사용합니다. `P[0:i]`에서 성립했던 가장 긴 prefix-suffix 관계를 가능한 최장 후보로 먼저 재사용하는 것입니다.

문자가 다르면 다음과 같이 이동합니다.

```text
j = pi[j-1]
```

이 대입은 단순히 `j`를 임의로 줄이는 것이 아닙니다. 현재 후보 `P[0:j]`가 실패했을 때, 그 후보 문자열 자체의 suffix이면서 pattern의 prefix인 다음으로 긴 길이가 `pi[j-1]`에 이미 계산되어 있기 때문에 그 상태로 바로 이동할 수 있습니다.

### fallback 뒤 같은 `P[i]`를 다시 비교하는 이유

다음 코드에서 `while`은 `i`를 증가시키지 않습니다.

```text
while j > 0 and P[i] != P[j]:
    j = pi[j-1]
```

즉 fallback한 뒤에는 **같은 현재 문자 `P[i]`를 더 짧은 prefix 후보 `P[j]`와 다시 비교**합니다.

이 동작을 빠뜨리고 mismatch가 발생할 때마다 다음 `i`로 넘어가면 유효한 prefix-suffix 관계를 놓칠 수 있습니다.

## 4. KMP 검색

검색 단계에서는 본문을 왼쪽에서 오른쪽으로 읽으면서 `matched`라는 상태를 유지합니다.

`matched = k`의 의미는 다음과 같습니다.

> 현재 본문 위치 바로 앞까지 처리했을 때, pattern의 앞 `k`글자가 본문의 마지막 `k`글자와 일치한다.

본문 위치를 `i`라고 하면 현재 문자 `T[i]`를 처리할 때 다음과 같이 진행합니다.

```text
for i in 0 .. n-1:
    while matched > 0 and T[i] != P[matched]:
        matched = pi[matched-1]

    if T[i] == P[matched]:
        matched += 1

    if matched == m:
        start = i - m + 1
        일치 처리
```

단, `m == 0`인 경우는 `P[0]`에 접근하기 전에 별도로 처리해야 합니다.

### mismatch 뒤 현재 본문 문자를 버리지 않습니다

KMP에서 중요한 점은 fallback할 때 본문 index `i`가 변하지 않는다는 것입니다.

```text
while matched > 0 and T[i] != P[matched]:
    matched = pi[matched-1]
```

`matched`만 더 짧은 후보로 바꾸고 **현재 문자 `T[i]`를 새 후보와 다시 비교**합니다.

본문 문자를 뒤로 되돌려 읽는 것도 아니고, mismatch가 났다고 현재 문자를 즉시 버리는 것도 아닙니다.

### 손으로 추적하는 예

```text
text    = "abababac"
pattern = "ababac"
pi      = [0, 0, 1, 2, 3, 0]
```

본문의 앞부분 `"ababa"`까지 일치하면 다음 상태입니다.

```text
matched = 5
```

다음 본문 문자는 `"b"`이고 비교 대상은 `pattern[5] == "c"`이므로 mismatch가 발생합니다.

```text
T[i] = "b"
P[5] = "c"
```

이때 처음부터 다시 시작하지 않고 다음과 같이 fallback합니다.

```text
matched = pi[4] = 3
```

그리고 **같은 본문 문자 `"b"`**를 다시 검사합니다.

```text
T[i] == P[3]
"b"  == "b"
```

그러므로 다음 상태가 됩니다.

```text
matched = 4
```

이후 `"a"`, `"c"`가 이어서 일치하여 pattern 전체를 찾습니다.

이 예시는 mismatch 뒤 `matched = 0`으로 무조건 초기화하면 이미 확인한 `"aba"`라는 관계를 버리게 된다는 것을 보여 줍니다.

## 5. 첫 일치와 모든 일치

검색 API가 무엇을 반환하는지 먼저 정해야 합니다.

### 첫 일치만 반환

첫 일치 위치만 필요하면 `matched == m`이 되는 즉시 시작 위치를 반환할 수 있습니다.

```text
if matched == m:
    return i - m + 1
```

일치가 없으면 예를 들어 `-1`을 반환하도록 계약을 정할 수 있습니다.

### 모든 일치를 반환

모든 일치를 계속 찾아야 한다면 pattern 전체가 일치한 뒤 상태를 그대로 둘 수 없습니다. `matched == m` 상태에서 다음 반복이 시작되면 `P[matched]`, 즉 `P[m]`에 접근하게 되어 범위를 벗어날 수 있습니다.

또한 상태를 무조건 `0`으로 만들면 겹치는 일치를 놓칠 수 있습니다.

따라서 일치를 기록한 뒤 다음과 같이 fallback합니다.

```text
if matched == m:
    결과에 i - m + 1 추가
    matched = pi[matched-1]
```

예를 들어 다음 입력을 생각합니다.

```text
text    = "aaaa"
pattern = "aa"
```

일치 시작 위치는 다음과 같습니다.

```text
0, 1, 2
```

첫 `"aa"`를 찾은 뒤 `matched = 0`으로 초기화하면 위치 `1`에서 시작하는 겹치는 일치를 놓칠 수 있습니다. 반대로 다음과 같이 이동하면

```text
matched = pi[1] = 1
```

이전 일치의 suffix `"a"`가 다음 일치의 prefix `"a"`로 재사용됩니다.

## 6. 빈 pattern과 경계 조건

빈 pattern의 의미는 알고리즘이 자동으로 정해 주는 것이 아니라 API 계약으로 정해야 합니다.

### 첫 일치 함수

많은 `find` 계열 API는 빈 pattern이 시작 위치 `0`에서 일치한다고 정의합니다.

```text
text    = "abc"
pattern = ""

result = 0
```

이 문서의 연결 구현인 `kmp_find`도 이 규칙을 사용합니다.

### 모든 일치 함수

모든 일치 위치를 반환하는 함수라면 여러 선택이 가능합니다.

```text
빈 pattern은 모든 경계 0..n에서 일치한다고 정의
빈 pattern은 위치 0에서만 일치한다고 정의
빈 pattern 입력 자체를 거부
```

어떤 규칙을 선택하든 문서와 테스트에서 명시해야 합니다.

빈 pattern을 일반 KMP loop에 그대로 넣으면 다음과 같은 접근이 발생할 수 있습니다.

```text
pattern[0]
```

pattern 길이가 `0`이면 유효하지 않으므로 일반 검색을 시작하기 전에 처리합니다.

함께 확인할 경계 조건은 다음과 같습니다.

```text
text = "", pattern = ""
text = "", pattern = "a"
pattern이 text보다 긴 경우
pattern과 text의 길이가 같은 경우
```

첫 일치 함수의 계약이 다음과 같다면

```text
빈 pattern -> 0
일치 없음  -> -1
```

위 입력 각각의 반환값을 테스트로 고정합니다.

## 7. KMP 결함이 잘 드러나는 입력

다음 입력들은 구현 오류를 찾는 데 특히 유용합니다.

- 빈 본문과 빈 pattern
- 빈 본문과 non-empty pattern
- pattern이 본문보다 긴 경우
- 같은 문자가 많이 반복되는 경우
- 긴 prefix 뒤 마지막 문자만 다른 경우
- 겹치는 일치가 있는 경우
- fallback이 여러 번 연속 발생하는 경우
- 일치 직후 다시 겹치는 일치가 시작되는 경우

예시:

```text
text    = "abababac"
pattern = "ababac"
```

확인할 질문은 다음과 같습니다.

```text
mismatch 직전 matched는 얼마입니까?
matched = pi[matched-1] 뒤 어떤 prefix가 남습니까?
본문 index는 그대로입니까?
같은 현재 본문 문자를 새 pattern 위치와 다시 비교합니까?
```

단순히 최종 반환값만 확인하지 말고 이 상태 변화를 손으로 추적할 수 있어야 합니다.

## 8. Rabin–Karp와 rolling hash

Rabin–Karp는 길이 `m`인 본문 창(window)의 hash와 pattern의 hash를 비교합니다.

```text
T[0:m]
T[1:m+1]
T[2:m+2]
...
```

각 창의 hash를 처음부터 다시 계산하면 창 하나당 `O(m)`이 필요합니다. rolling hash는 이전 창의 hash에서 빠지는 문자와 새로 들어오는 문자의 기여분을 갱신하여 다음 창의 hash를 보통 `O(1)`에 계산하도록 설계합니다.

따라서 전체 창을 순회하는 hash 계산 자체는 선형 시간으로 만들 수 있습니다.

하지만 다음 명제는 성립하지 않습니다.

```text
hash(A) == hash(B)  =>  A == B
```

서로 다른 문자열이 같은 hash를 가질 수 있는데, 이를 **hash collision**이라고 합니다.

### 정확한 문자열 검색이 필요한 경우

가장 명확한 방법은 hash가 같을 때 실제 문자열을 다시 비교하는 것입니다.

```text
if window_hash == pattern_hash:
    if 실제 window와 pattern이 같음:
        일치
```

이 경우 hash는 **비교할 후보를 줄이는 필터**이고, 최종 정확성은 실제 문자열 비교가 보장합니다.

다른 선택으로는 다음이 있습니다.

- 서로 독립적으로 설계한 여러 hash를 사용하고 남은 충돌 확률을 문서화합니다.
- 충돌 가능성을 허용하는 확률적 API임을 명시합니다.

단순히 hash 값 하나가 같다는 이유만으로 즉시 성공을 반환하면 false positive, 즉 실제로는 다른 문자열을 일치로 반환할 수 있습니다.

### 복잡도 해석 주의

rolling hash의 갱신이 창마다 `O(1)`이어도, hash가 같은 후보마다 실제 길이 `m` 문자열 비교를 수행한다면 검증 비용이 추가됩니다.

따라서 정확한 최악 시간과 기대 시간을 구분해야 할 수 있습니다. 특히 충돌이 많이 발생하는 hash 설계나 입력에서는 hash 비교만으로 전체 비용을 설명하면 안 됩니다.

## 9. Z-function과 선택 기준

Z-function에서 `Z[i]`는 다음 값을 저장합니다.

> 문자열의 위치 `i`에서 시작하는 suffix와 문자열 전체의 prefix가 앞에서부터 몇 글자까지 일치하는가

문자열 검색에서는 개념적으로 다음과 같은 결합 문자열을 만들 수 있습니다.

```text
pattern + separator + text
```

그리고 text 영역의 어떤 위치에서 Z 값이 `len(pattern)` 이상이면 그 위치에서 pattern이 일치합니다.

이때 `separator`는 pattern이나 text 내부의 문자와 검색 의미상 충돌하지 않는 구분자여야 합니다. 임의의 일반 문자를 separator로 선택하고 그 문자가 입력에도 나타날 수 있다면 경계가 흐려질 수 있습니다. 실제 구현에서는 입력에 나타나지 않는 sentinel을 보장하거나, 문자열 경계를 구조적으로 구분하는 방법을 사용합니다.

알고리즘은 이름이 아니라 필요한 연산과 반환값으로 선택합니다.

- **KMP**: pattern의 prefix 상태를 유지하면서 왼쪽에서 오른쪽으로 검색하기 좋습니다. 이미 계산한 pattern 상태를 이용하므로 streaming 입력에도 적용하기 좋습니다.
- **Z-function**: 각 위치에서 전체 prefix와 얼마나 일치하는지 그 길이 자체가 필요한 문제에 적합합니다.
- **rolling hash**: substring equality 질의가 많거나 여러 창을 빠르게 비교할 때 유용하지만 충돌 처리 규칙이 필요합니다.
- **suffix array·suffix automaton**: 하나의 검색보다 많은 질의나 더 넓은 substring 문제를 다루는 심화 자료구조입니다.

pattern 하나를 본문에서 한 번 찾는 문제라면 더 복잡한 자료구조가 자동으로 더 좋은 선택이 되는 것은 아닙니다.

## 10. KMP의 시간과 공간 복잡도

pattern 길이를 `m`, 본문 길이를 `n`이라고 합니다.

### prefix table

prefix function 계산은 다음 시간이 걸립니다.

```text
O(m)
```

`pi` 배열에는 다음 공간을 사용합니다.

```text
O(m)
```

코드 안에 중첩 `while`이 있기 때문에 겉보기에는 `O(m^2)`처럼 보일 수 있습니다. 그러나 `j`가 증가하려면 문자 일치가 있어야 하고, fallback에서 감소하는 과정은 이전에 만들어진 상태를 되돌리는 과정입니다. 전체 계산 동안 상태의 증가와 감소 횟수를 합치면 `m`에 선형으로 제한됩니다.

### 검색

검색은 다음 시간입니다.

```text
O(n)
```

본문 index `i`는 왼쪽에서 오른쪽으로만 증가합니다. mismatch 때에는 `i`를 뒤로 돌리지 않고 `matched`만 prefix table을 따라 감소시킵니다.

`matched`가 증가하는 횟수와 fallback으로 감소하는 전체 횟수를 함께 세면 전체 상태 전이 수도 `n`에 선형으로 제한됩니다. 따라서 어떤 한 본문 문자에서 fallback이 여러 번 일어나더라도 전체 검색이 `O(nm)`으로 증가하지 않습니다.

### 전체

prefix table 계산까지 포함한 KMP의 전체 비용은 다음과 같습니다.

```text
시간: O(n + m)
추가 공간: O(m)
```

여기에는 문자열 decoding, normalization, grapheme segmentation 같은 별도 전처리 비용은 포함하지 않은 것으로 봅니다.

## 11. 문자열 표현과 index 계약

KMP, Z-function, rolling hash 모두 결국 어떤 **원소의 연속열** 위에서 동작합니다. 그 원소가 무엇인지는 구현이 결정합니다.

예를 들어 다음 세 구현은 서로 다른 검색 문제가 될 수 있습니다.

```text
UTF-8 byte 배열 위에서 검색
Unicode code point 배열 위에서 검색
grapheme cluster 배열 위에서 검색
```

따라서 함수 문서에는 최소한 다음을 명시합니다.

```text
입력 문자열의 논리적 원소 단위
반환 index의 단위
대소문자 구분 여부
Unicode normalization 적용 여부
전처리 뒤 index가 원본 기준인지 전처리 결과 기준인지
```

특히 `"사용자가 보는 문자 위치"`가 필요하다면 단순히 Unicode code point index를 반환하는 것으로 충분하다고 가정하면 안 됩니다. 한 grapheme cluster가 여러 code point로 구성될 수 있기 때문입니다.

반대로 파일 포맷이나 네트워크 프로토콜처럼 byte offset이 필요한 문제에서는 grapheme cluster 기준 검색이 오히려 잘못된 좌표계일 수 있습니다.

알고리즘을 구현하기 전에 API가 요구하는 좌표계를 먼저 결정합니다.

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 12]`에서 `kmp_find`를 확인합니다.

현재 구현의 계약은 다음과 같습니다.

- 빈 pattern은 `0`을 반환합니다.
- prefix table에는 각 위치까지의 proper prefix이면서 suffix인 최장 길이를 저장합니다.
- mismatch 뒤 `pi[matched-1]`을 사용해 더 짧은 prefix 상태로 이동합니다.
- fallback 중에는 현재 본문 문자를 버리지 않고 새 상태와 다시 비교합니다.
- 첫 일치 위치를 반환합니다.
- 일치가 없으면 `-1`을 반환합니다.
- 테스트는 Python `str.find`와 고정 seed 문자열을 사용합니다.

현재 API는 **첫 일치만 반환**합니다. 따라서 일치 직후의 상태를 복구하여 검색을 계속할 필요가 없습니다.

모든 겹치는 일치와 streaming KMP는 [`80-extended-practice.md`](../80-extended-practice.md)의 선택 문제로 다룹니다.

## 완료 기준

- byte, Unicode code point, grapheme cluster index가 서로 다른 좌표계임을 설명합니다.
- 검색 전 normalization이나 대소문자 변환이 반환 index 규약에 영향을 줄 수 있음을 설명합니다.
- `pi[i]`가 `P[0:i+1]`의 proper prefix이면서 suffix인 최장 길이라는 것을 설명합니다.
- prefix function 계산에서 fallback 뒤 같은 `P[i]`를 다시 비교하는 이유를 설명합니다.
- KMP 검색에서 `matched`가 나타내는 상태를 문장으로 설명합니다.
- mismatch 뒤 본문 index를 되돌리지 않고 같은 현재 문자를 더 짧은 prefix 후보와 다시 비교하는 과정을 손으로 추적합니다.
- 첫 일치 검색과 모든 일치 검색의 match 이후 상태 처리가 다름을 설명합니다.
- 빈 pattern의 반환값을 함수 계약에 포함합니다.
- rolling hash 충돌을 실제 문자 비교나 명시적인 확률적 계약으로 처리합니다.
- KMP의 전체 시간 `O(n+m)`이 중첩된 `while`에도 불구하고 선형인 이유를 설명합니다.

## 실패 신호

- byte index와 Unicode code point index, 사용자가 보는 문자 위치를 같은 값으로 생각합니다.
- normalization이나 대소문자 변환 뒤에도 원본 index가 자동으로 유지된다고 가정합니다.
- prefix function에 문자열 전체 길이를 proper prefix 길이로 저장합니다.
- `pi[i]`를 단순히 "앞에서 같은 글자 수" 정도로 설명하고 suffix 조건을 빠뜨립니다.
- fallback 뒤 현재 pattern 문자나 현재 본문 문자를 다시 비교하지 않습니다.
- mismatch가 발생할 때마다 `matched = 0`으로 초기화합니다.
- 모든 일치를 찾으면서 match 뒤 상태를 `0`으로 만들어 겹치는 일치를 놓칩니다.
- 모든 일치 검색에서 `matched == m`인 상태를 복구하지 않아 다음 반복에서 `pattern[m]`에 접근합니다.
- rolling hash 충돌이 불가능하다고 가정합니다.
- hash가 같다는 이유만으로 정확한 문자열 일치를 확정합니다.
- 빈 pattern의 처리 방법이 없습니다.
