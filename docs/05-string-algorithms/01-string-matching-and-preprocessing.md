# 문자열 검색과 전처리

## 학습 목표

- byte, Unicode code point, grapheme cluster 중 어떤 단위로 index를 계산하는지 정합니다.
- 단순 검색에서 반복되는 비교를 상태로 표현합니다.
- KMP의 prefix function과 mismatch 뒤 fallback 과정을 설명합니다.
- rolling hash의 충돌 가능성과 검증 방법을 정합니다.

## 선행지식

[선형 구간](../02-data-structures/01-linear-structures-ranges-and-hashing.md), 반복 불변식, 문자열 index 범위를 알고 있어야 합니다.

## 핵심 관점

문자열 알고리즘을 선택하기 전에 index 단위를 먼저 정합니다.

```text
byte 위치를 반환합니까?
Unicode code point 위치를 반환합니까?
사용자가 보는 문자 단위를 반환합니까?
대소문자와 Unicode normalization을 적용합니까?
```

알고리즘 자체가 선형이어도 decoding이나 normalization 비용은 별도로 들 수 있습니다.

## 1. 단순 문자열 검색

본문 `T`의 각 시작 위치에서 pattern `P`를 앞부터 비교합니다.

```text
for start in 0 .. n-m:
    P와 T[start:start+m]을 앞에서부터 비교합니다.
```

최악 시간은 `O((n-m+1)m)`, 보통 `O(nm)`으로 표현합니다. Pattern이 짧거나 입력이 작다면 구현이 단순한 기준 계산으로 적합합니다.

## 2. 이미 확인한 문자를 다시 비교하지 않습니다

긴 prefix가 일치한 뒤 한 문자에서 실패했다고 가정합니다. 처음부터 다시 비교하지 않으려면 현재까지 일치한 문자열 안에서 다음 값을 알아야 합니다.

```text
proper prefix이면서 suffix인 가장 긴 길이
```

이 값이 KMP의 prefix function입니다. Proper prefix는 문자열 전체 자신을 제외한 prefix입니다.

## 3. prefix function

`pi[i]`를 `P[0:i+1]`의 proper prefix이면서 suffix인 가장 긴 길이라고 정의합니다.

```text
j = pi[i-1]
while j > 0 and P[i] != P[j]:
    j = pi[j-1]
if P[i] == P[j]:
    j += 1
pi[i] = j
```

반복 중 `j`는 현재 prefix-suffix 후보 길이입니다. 문자가 다르면 `pi[j-1]`로 이동해 이미 검증된 더 짧은 후보를 시도합니다.

`j`가 줄어들 때마다 이전에 계산한 prefix 관계를 사용하므로 pattern을 처음부터 다시 비교하지 않습니다.

## 4. KMP 검색

본문을 왼쪽에서 오른쪽으로 한 번 읽으며 현재 일치 길이 `matched`를 유지합니다.

```text
for character in text:
    while matched > 0 and character != pattern[matched]:
        matched = pi[matched-1]
    if character == pattern[matched]:
        matched += 1
    if matched == len(pattern):
        일치 위치를 계산합니다.
```

첫 일치만 반환하는 함수인지 모든 일치 위치를 반환하는 함수인지 구분합니다.

모든 일치를 찾는 경우에는 한 번 일치한 뒤 `matched = pi[matched-1]`로 이동해야 겹치는 일치를 계속 찾을 수 있습니다. `"aaaa"`에서 `"aa"`를 찾을 때 위치 `0`, `1`, `2`가 모두 나와야 하는지가 함수 조건에 포함되어야 합니다.

## 5. 빈 pattern

빈 pattern의 결과를 명확히 정합니다.

일반적인 `find` 함수는 빈 pattern이 위치 `0`에서 일치한다고 봅니다. 모든 일치 위치를 반환하는 함수라면 `0..n` 전체를 반환할지, 빈 pattern을 거부할지 별도로 정해야 합니다.

빈 pattern을 일반 검색 loop에 그대로 넣으면 `pattern[0]` 접근에서 오류가 날 수 있으므로 먼저 처리합니다.

## 6. KMP 결함이 잘 드러나는 입력

- 빈 본문과 빈 pattern
- pattern이 본문보다 긴 경우
- 같은 문자가 반복되는 경우
- 긴 prefix 뒤 마지막 문자만 다른 경우
- 겹치는 일치가 있는 경우
- fallback이 여러 번 연속 발생하는 경우

예시:

```text
text    = "abababac"
pattern = "ababac"
```

Mismatch 뒤 `matched`가 한 번에 0으로 돌아가지 않고 여러 prefix 후보를 거치는지 추적합니다.

## 7. Rabin–Karp와 rolling hash

길이 `m`인 창의 hash를 이동하며 pattern hash와 비교합니다. 각 이동에서 이전 문자를 빼고 새 문자를 더하면 `O(1)`에 hash를 갱신할 수 있습니다.

하지만 hash가 같다고 문자열이 반드시 같은 것은 아닙니다.

정확성이 필요한 함수에서는 다음 중 하나를 사용합니다.

- hash가 같으면 실제 문자열을 다시 비교합니다.
- 서로 독립적인 여러 hash를 사용하고 남은 충돌 확률을 문서에 적습니다.
- 충돌을 허용하는 확률적 결과라는 점을 반환 조건에 포함합니다.

Hash 값만 비교하고 즉시 성공을 반환하면 잘못된 일치를 만들 수 있습니다.

## 8. Z-function과 선택 기준

Z-function은 각 위치에서 전체 문자열의 prefix와 얼마나 길게 일치하는지 저장합니다. `pattern + separator + text` 형태로 문자열 검색에 사용할 수 있습니다.

- KMP: pattern 상태를 유지하며 streaming 입력을 처리하기 좋습니다.
- Z-function: 각 위치의 prefix 일치 길이가 직접 필요한 문제에 적합합니다.
- rolling hash: substring equality 질의가 많을 때 유용하지만 충돌 처리가 필요합니다.
- suffix array·automaton: 많은 질의와 더 넓은 문자열 문제를 위한 심화 주제입니다.

문제 이름보다 필요한 반환값과 질의 수로 선택합니다.

## 9. 시간과 공간

KMP의 prefix table 계산은 `O(m)`, 검색은 `O(n)`, 추가 공간은 `O(m)`입니다.

Mismatch가 여러 번 발생해도 `matched`의 전체 증가·감소 횟수는 선형으로 제한됩니다. 각 본문 문자를 처음부터 다시 읽지 않습니다.

## 연결 구현

[`verified-algorithms`](../../exercises/verified-algorithms/)의 `[Implementation 12]`에서 `kmp_find`를 확인합니다.

- 빈 pattern은 `0`을 반환합니다.
- prefix table에 proper prefix 길이를 저장합니다.
- mismatch 뒤 더 짧은 prefix로 이동합니다.
- 첫 일치 위치를 반환하고, 일치가 없으면 `-1`을 반환합니다.
- 테스트는 Python `str.find`와 고정 seed 문자열을 사용합니다.

현재 API는 첫 일치만 반환합니다. 모든 겹치는 일치와 streaming KMP는 [`80-extended-practice.md`](../80-extended-practice.md)의 선택 문제로 다룹니다.

## 완료 기준

- prefix function 각 값이 무엇을 뜻하는지 proper prefix와 suffix로 설명합니다.
- mismatch 뒤 현재 문자를 다시 처리하는 과정을 손으로 추적합니다.
- 빈 pattern의 반환값을 함수 조건에 포함합니다.
- Unicode 문자열에서 반환하는 index 단위를 정합니다.
- rolling hash 충돌을 실제 문자 비교나 명시적인 확률로 처리합니다.

## 실패 신호

- byte index와 사용자가 보는 문자 위치를 같은 값으로 생각합니다.
- prefix function에 문자열 전체 길이를 저장합니다.
- fallback 뒤 현재 문자를 다시 비교하지 않습니다.
- 모든 일치를 찾으면서 match 뒤 상태를 0으로 만들어 겹치는 일치를 놓칩니다.
- rolling hash 충돌이 불가능하다고 가정합니다.
- 빈 pattern의 처리 방법이 없습니다.
