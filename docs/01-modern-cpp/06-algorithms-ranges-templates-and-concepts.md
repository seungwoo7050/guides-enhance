# algorithm·range·template·concept

## 목표

컨테이너를 직접 반복하는 코드만 작성하지 않고, 표준 algorithm과 range를 사용해 **검색·선택·변환·정렬·집계의 의도**를 코드에 드러냅니다. 또한 iterator, view, reference 기반 결과처럼 원본을 소유하지 않는 값의 수명 조건을 추적하고, template이 실제로 요구하는 연산을 concept이나 문서로 명확하게 표현합니다.

이 문서에서 중요한 질문은 다음과 같습니다.

- 이 자료구조에서 가장 자주 수행하는 연산은 무엇입니까?
- 직접 loop보다 이름 있는 algorithm이 의도를 더 잘 표현합니까?
- iterator, reference, pointer, view는 원본 변경 뒤에도 유효합니까?
- 정렬 결과의 순서는 입력이나 구현에 관계없이 결정적입니까?
- template은 실제로 어떤 연산을 요구합니까?
- concept이 필요한 조건만 요구합니까, 아니면 지나치게 강합니까?
- 성능 문제는 이론적 복잡도 때문입니까, 할당·cache locality·반복 계산 때문입니까?

---

## 컨테이너부터 고르는 것이 아니라 필요한 연산부터 적습니다

자료구조 이름을 먼저 정하고 코드를 맞추기보다, 프로그램이 실제로 어떤 연산을 자주 수행하는지 먼저 적습니다.

예:

```text
요구사항
- 순서대로 저장
- index로 자주 접근
- 끝에 원소 추가
- 중간 삽입은 드묾
```

이 경우 `std::vector`가 자연스러운 후보가 됩니다.

반대로:

```text
요구사항
- key로 조회
- key 순서대로 순회
```

라면 `std::map`이 적합할 수 있습니다.

대표적인 선택 기준은 다음과 같습니다.

- 순서대로 저장하고 index 접근: `std::vector`
- key로 찾고 key 순서대로 순회: `std::map`
- 평균 상수 시간 key 조회, 순서 불필요: `std::unordered_map`
- 뒤에서 넣고 빼는 LIFO 동작: `std::stack` 같은 adapter
- 양끝 삽입·삭제: `std::deque`

다만 이것은 출발점일 뿐입니다.

---

## 복잡도만 보고 컨테이너를 고르지 않습니다

이론상 시간 복잡도가 더 좋아 보여도 실제 입력 크기와 메모리 접근 특성에 따라 결과는 달라질 수 있습니다.

예를 들어 원소 수가 작다면:

```text
std::vector
- 연속 메모리
- 적은 allocation
- cache locality가 좋음
```

이라는 특성이 tree 기반 container보다 실제로 더 빠를 수 있습니다.

반면 `std::map`은 각 노드가 따로 할당되는 경우가 많고 pointer를 따라 이동해야 하므로, 단순히 `O(log n)`이라는 표기만으로 실제 비용을 판단할 수 없습니다.

따라서 container 선택은 다음을 함께 봅니다.

```text
주요 연산
입력 크기
순서 보장 필요 여부
중복 허용 여부
iterator 안정성
메모리 배치
측정 결과
```

---

## `std::stack`은 container가 아니라 adapter입니다

`std::stack`은 독립적인 저장 구조라기보다 기존 sequence container를 감싼 **container adapter**입니다.

예:

```cpp
std::stack<int> values;
```

사용자는 내부 container를 직접 순회하지 않고 다음과 같은 stack 인터페이스만 사용합니다.

```cpp
values.push(1);
values.push(2);

int top = values.top();
values.pop();
```

즉 "뒤에서 넣고 빼기"만 필요한 경우에도 실제로 iterator 순회나 index 접근이 필요하다면 `std::vector` 자체가 더 적합할 수 있습니다.

---

## algorithm으로 의도를 적습니다

직접 loop를 작성할 수 있는 작업이라도 표준 algorithm에 이미 이름이 있다면 먼저 확인합니다.

예를 들어 ready 상태인 첫 task를 찾는 코드는 다음처럼 쓸 수 있습니다.

```cpp
const auto found = std::ranges::find_if(
    tasks,
    [](const Task& task) {
        return task.ready();
    }
);
```

이 코드에서 핵심 의도는 바로 드러납니다.

```text
tasks에서
조건을 만족하는
첫 원소를 찾는다
```

직접 loop로도 같은 코드를 작성할 수 있습니다.

```cpp
auto found = tasks.end();

for (auto it = tasks.begin(); it != tasks.end(); ++it) {
    if (it->ready()) {
        found = it;
        break;
    }
}
```

두 방식 모두 올바를 수 있지만, 작업 자체가 "조건에 맞는 원소 찾기"라면 `find_if`가 의도를 더 직접적으로 표현합니다.

---

## 표준 algorithm을 먼저 확인할 만한 작업

다음처럼 이름이 명확한 작업은 표준 algorithm을 먼저 살펴볼 가치가 있습니다.

```text
찾기
    find, find_if

조건 만족 여부
    all_of, any_of, none_of

정렬
    sort, stable_sort

개수 세기
    count, count_if

복사
    copy, copy_if

변환
    transform

삭제 대상 이동
    remove, remove_if

최솟값/최댓값
    min_element, max_element
```

algorithm 이름 자체가 코드의 목적을 설명해 주므로 읽는 사람이 loop 내부의 제어 흐름을 직접 해석해야 하는 부담을 줄일 수 있습니다.

---

## 직접 loop가 더 명확한 경우도 있습니다

표준 algorithm을 사용하는 것이 항상 더 좋은 것은 아닙니다.

예를 들어 한 번의 순회 중 다음을 동시에 수행한다고 가정합니다.

```text
조건별 통계 갱신
여러 상태 변경
특정 조건에서 조기 종료
외부 자원과 상호작용
```

이를 여러 algorithm으로 잘게 나누면 오히려 코드 흐름이 더 복잡해질 수 있습니다.

예:

```cpp
for (const Task& task : tasks) {
    if (task.cancelled())
        continue;

    total += task.duration();

    if (task.failed()) {
        failed = true;
        break;
    }
}
```

이런 경우 직접 loop가 상태 변화와 종료 조건을 한눈에 보여 줄 수 있습니다.

핵심은 다음과 같습니다.

> algorithm을 사용하는 것이 목표가 아니라, 코드의 의도를 가장 명확하게 표현하는 방법을 선택하는 것이 목표입니다.

---

## iterator와 반열린 범위

많은 표준 algorithm은 `[first, last)` 형태의 범위를 사용합니다.

```text
[first, last)
```

의 의미는 다음과 같습니다.

- `first`는 첫 원소를 가리킵니다.
- `last`는 마지막 원소가 아니라 **마지막 원소 다음 위치**입니다.
- `last` 자체는 범위에 포함되지 않습니다.

예:

```cpp
std::sort(values.begin(), values.end());
```

`values.end()`는 마지막 원소를 가리키지 않습니다.

---

## 반열린 범위가 유용한 이유

반열린 범위를 사용하면 빈 범위를 자연스럽게 표현할 수 있습니다.

```cpp
values.begin() == values.end()
```

이면 원소가 하나도 없는 범위입니다.

또 길이 계산도 iterator 종류가 허용한다면 다음처럼 표현하기 쉽습니다.

```text
last - first
```

범위를 둘로 나눌 때도 경계가 겹치지 않습니다.

```text
[first, middle)
[middle, last)
```

---

## `end()` iterator를 역참조하면 안 됩니다

다음 코드는 잘못되었습니다.

```cpp
auto it = values.end();
std::cout << *it;
```

`end()`는 원소를 가리키는 iterator가 아니라 범위의 끝을 나타내는 sentinel 위치입니다.

검색 결과를 사용할 때도 먼저 끝인지 확인합니다.

```cpp
auto it = std::ranges::find(values, target);

if (it != values.end()) {
    use(*it);
}
```

즉 iterator를 역참조하기 전에는 그것이 실제 원소를 가리키는 상태인지 확인해야 합니다.

---

## iterator 종류마다 가능한 연산이 다릅니다

모든 iterator가 같은 연산을 지원하는 것은 아닙니다.

예를 들어 일부 iterator는 다음 정도만 지원합니다.

```cpp
++it
*it
it != end
```

반면 random-access iterator는 다음 같은 연산도 가능합니다.

```cpp
it + 5
it - 3
last - first
it[n]
```

`std::vector` iterator는 random-access iterator이지만, 모든 range의 iterator가 그렇다고 가정하면 안 됩니다.

template에서 iterator를 받을 때는 구현에서 실제로 필요한 iterator 능력만 요구해야 합니다.

---

## iterator의 유효 기간

iterator는 container 내부 원소를 가리키므로 container 변경에 따라 무효화될 수 있습니다.

예:

```cpp
std::vector<int> values{1, 2, 3};

auto it = values.begin();

values.push_back(4);
```

`push_back()` 때문에 vector의 capacity가 부족해 재할당이 일어나면 기존 storage의 원소가 새 storage로 이동합니다.

그 경우 이전의:

```text
iterator
pointer
reference
```

는 모두 무효화될 수 있습니다.

---

## vector 재할당

개념적으로 다음과 같습니다.

```text
변경 전

storage A
[1][2][3]

it ──> 첫 번째 원소


push_back으로 재할당

storage B
[1][2][3][4]

storage A 제거
```

이제 `it`는 이전 storage A의 주소를 가리키고 있으므로 사용할 수 없습니다.

따라서 container 변경 뒤 기존 iterator를 계속 사용할 때는 해당 container와 연산의 **iterator invalidation 규칙**을 확인해야 합니다.

---

## 모든 container가 같은 무효화 규칙을 갖는 것은 아닙니다

`std::vector`, `std::deque`, `std::list`, `std::map`, `std::unordered_map`은 수정 연산 뒤 iterator/reference가 유지되는 조건이 서로 다릅니다.

따라서 다음처럼 일반화하면 안 됩니다.

```text
container에 원소를 추가해도 iterator는 항상 유효하다
```

또는:

```text
container를 수정하면 iterator는 항상 무효다
```

정확한 규칙은 container와 연산별로 확인해야 합니다.

---

## range는 begin/end 쌍을 더 직접적으로 표현합니다

기존 algorithm은 흔히 두 iterator를 받습니다.

```cpp
std::find_if(
    tasks.begin(),
    tasks.end(),
    predicate
);
```

ranges algorithm을 사용하면 range 자체를 전달할 수 있습니다.

```cpp
std::ranges::find_if(
    tasks,
    predicate
);
```

이 방식은 `begin()`과 `end()`를 반복해서 적는 코드를 줄이고, "tasks 전체를 대상으로 한다"는 의도를 직접 표현합니다.

---

## range와 view

C++20 ranges에서 view는 range를 변환하거나 필터링하는 가벼운 표현을 만드는 데 사용됩니다.

예:

```cpp
auto ready =
    tasks
    | std::views::filter([](const Task& task) {
          return task.ready();
      });
```

`ready`는 일반적으로 ready task를 복사해 새 `std::vector`를 만드는 것이 아닙니다.

원본 `tasks`를 필요할 때 순회하면서 filter 조건을 적용하는 view입니다.

---

## view는 보통 계산을 지연합니다

다음 코드에서:

```cpp
auto ready =
    tasks
    | std::views::filter([](const Task& task) {
          return task.ready();
      });
```

filter 조건이 view 생성 시 모든 원소에 즉시 적용되어 별도 결과 container가 만들어진다고 생각하면 안 됩니다.

실제 순회할 때 조건 검사가 수행되는 형태가 일반적입니다.

이를 **lazy evaluation**이라고 이해할 수 있습니다.

개념적으로:

```text
view 생성
    → 원본과 변환 규칙 보관

view 순회
    → 필요한 시점에 조건 계산
```

---

## lazy view는 같은 계산을 반복할 수 있습니다

view가 결과를 저장하는 container가 아니므로 다시 순회하면 predicate나 transform 계산이 다시 수행될 수 있습니다.

예:

```cpp
for (const Task& task : ready) {
    // 첫 번째 순회
}

for (const Task& task : ready) {
    // 두 번째 순회에서 filter 조건이 다시 평가될 수 있음
}
```

predicate가 비싸다면 중간 결과를 실제 container로 materialize하는 편이 더 나을 수도 있습니다.

따라서 view를 선택할 때는 allocation 감소뿐 아니라 반복 계산 비용도 고려합니다.

---

## view의 수명은 원본과 연결됩니다

view는 일반적으로 원본을 소유하지 않는 경우가 많습니다.

```cpp
auto ready =
    tasks
    | std::views::filter([](const Task& task) {
          return task.ready();
      });
```

이 경우 `ready`를 사용하는 동안 원본 `tasks`와 필요한 내부 storage가 유효해야 합니다.

개념적으로:

```text
ready
   │
   └── 원본 tasks를 참조
```

따라서 원본보다 view를 오래 저장하면 문제가 생길 수 있습니다.

---

## view뿐 아니라 view의 iterator도 수명을 확인합니다

다음처럼 view에서 iterator를 얻었다고 가정합니다.

```cpp
auto ready = tasks | std::views::filter(predicate);
auto it = ready.begin();
```

`it` 역시 결국 원본 `tasks`의 원소를 참조하게 됩니다.

원본 container 수정으로 storage가 무효화되면 view iterator도 더 이상 안전하지 않을 수 있습니다.

즉:

```text
view의 수명
iterator의 수명
원본 range의 수명
원본 storage의 안정성
```

을 함께 봐야 합니다.

---

## 임시 range와 view 수명에 주의합니다

비소유 view를 임시 객체에서 만들면 원본이 너무 빨리 사라질 수 있습니다.

예를 들어 일반적으로 다음과 같은 구조를 볼 때는 실제 view 종류와 range 규칙을 확인해야 합니다.

```cpp
auto view = make_tasks() | std::views::filter(predicate);
```

`make_tasks()`가 반환한 임시 container의 ownership이 view에 어떻게 처리되는지는 range/view 타입에 따라 달라질 수 있습니다.

따라서 "view는 항상 원본을 참조하므로 임시에서 만들면 무조건 dangling" 또는 "ranges가 알아서 항상 소유한다"라고 단정하지 말고, 사용 중인 view의 ownership과 `borrowed_range` 관련 규칙을 확인해야 합니다.

학습 단계에서 가장 안전한 기본 습관은 **장기간 보관할 view라면 원본의 수명을 코드에서 명확하게 확인하는 것**입니다.

---

## 결과를 오래 보관해야 한다면 값을 소유하게 만들 수 있습니다

검색·filter 결과를 원본보다 오래 사용해야 한다면 새 container에 값을 복사하거나 이동할 수 있습니다.

예:

```cpp
std::vector<Task> ready_tasks;

for (const Task& task : tasks) {
    if (task.ready())
        ready_tasks.push_back(task);
}
```

이제 `ready_tasks`는 독립적인 값을 소유합니다.

```text
tasks
    → 원본

ready_tasks
    → 복사된 독립 Task 소유
```

원본 `tasks`가 파괴되어도 `ready_tasks`의 값은 남습니다.

대신 복사 비용이 발생합니다.

---

## 비소유 결과를 만들 수도 있습니다

복사 비용을 피하고 원본 객체를 그대로 참조하려면 비소유 결과 목록을 만들 수 있습니다.

```cpp
std::vector<std::reference_wrapper<const Task>> result;

for (const Task& task : tasks) {
    if (matches(task, query))
        result.emplace_back(std::cref(task));
}
```

이 결과는 `Task` 객체를 복사하지 않습니다.

개념적으로:

```text
result[0] ─┐
result[1] ─┼──> tasks 내부 Task
result[2] ─┘
```

하지만 수명 조건이 생깁니다.

```text
result의 마지막 사용 시점
<
tasks 및 해당 원소가 유효한 기간
```

---

## 비소유 결과는 반환 타입만 보고 완전한 수명을 알기 어렵습니다

다음 함수가 있다고 가정합니다.

```cpp
std::vector<std::reference_wrapper<const Task>>
find_matches(const std::vector<Task>& tasks);
```

반환 container 자체는 caller가 소유하지만 내부 `reference_wrapper`는 `tasks`의 원소를 소유하지 않습니다.

따라서 다음 같은 호출은 위험합니다.

```cpp
auto result = find_matches(make_tasks());
```

원본 temporary container가 너무 빨리 사라진다면 `result`의 참조가 dangling이 될 수 있습니다.

비소유 결과를 반환하는 API는 문서와 타입 설계에서 원본 수명 조건을 명확히 해야 합니다.

---

## 원본을 바꾸지 않는 조회

조회 결과만 특정 순서로 보여 주고 싶은데 원본 container를 직접 정렬하면 원본 상태까지 바뀝니다.

예:

```cpp
std::ranges::sort(tasks, compare_by_id);
```

이 연산은 `tasks` 자체의 순서를 변경합니다.

원본 순서가 다른 기능에 의미가 있다면 조회 하나 때문에 전체 상태가 바뀌는 것은 바람직하지 않을 수 있습니다.

---

## 비소유 참조 목록을 정렬할 수 있습니다

원본은 그대로 두고 참조 목록만 정렬할 수 있습니다.

```cpp
std::vector<std::reference_wrapper<const Task>> result;

for (const Task& task : tasks) {
    if (matches(task, query))
        result.emplace_back(std::cref(task));
}

std::ranges::sort(result, compare_by_id);
```

이 경우:

```text
tasks
    → 순서 유지

result
    → Task를 가리키는 참조의 순서만 변경
```

됩니다.

단, 앞서 본 것처럼 `result`는 원본보다 오래 사용할 수 없습니다.

---

## 값 복사와 비소유 참조 사이의 trade-off

두 방식에는 서로 다른 장단점이 있습니다.

### 값을 복사

```cpp
std::vector<Task>
```

장점:

- 원본 수명과 독립적
- 반환 후 사용이 단순함

비용:

- Task 복사 비용
- 추가 메모리

### 참조 보관

```cpp
std::vector<std::reference_wrapper<const Task>>
```

장점:

- Task 자체를 복사하지 않음
- 원본 객체를 직접 관찰

비용:

- 원본 수명에 의존
- 원본 수정에 따른 invalidation 고려 필요

따라서 "복사를 피하는 것이 항상 더 좋다"고 단정하지 않습니다.

---

## 결정적인 정렬 순서

정렬 결과가 출력, test, cache key 등에 사용된다면 동일한 입력에서 같은 순서가 나오도록 비교 기준을 충분히 정의하는 것이 좋습니다.

예:

```cpp
return std::tie(lhs.duration, lhs.id)
     < std::tie(rhs.duration, rhs.id);
```

정렬 기준은 다음과 같습니다.

```text
1차: duration
2차: duration이 같으면 id
```

`id`가 각 task를 유일하게 구분한다면 전체 순서를 결정할 수 있습니다.

---

## tie-breaker가 없다고 매번 순서가 달라지는 것은 아닙니다

다음 비교만 사용한다고 가정합니다.

```cpp
return lhs.duration < rhs.duration;
```

같은 `duration`을 가진 원소끼리는 comparator 관점에서 동등합니다.

이때 "실행할 때마다 반드시 순서가 달라진다"고 말할 수는 없습니다.

다만 `std::sort`는 동등한 원소의 기존 상대 순서를 보존한다고 보장하지 않습니다.

따라서 그 상대 순서에 의미가 있다면 다음 중 하나를 선택합니다.

- 추가 tie-breaker를 둡니다.
- 기존 상대 순서를 유지해야 한다면 `std::stable_sort` 같은 stable algorithm을 사용합니다.

---

## `sort`와 `stable_sort`

두 algorithm은 모두 정렬하지만 동등한 원소의 상대 순서 보장에서 차이가 있습니다.

### `std::sort`

```cpp
std::sort(first, last, comp);
```

comparator상 동등한 두 원소의 기존 상대 순서를 유지한다고 보장하지 않습니다.

### `std::stable_sort`

```cpp
std::stable_sort(first, last, comp);
```

comparator상 동등한 원소들의 기존 상대 순서를 유지합니다.

예를 들어 입력이 이미 `created_at` 순서이고 `priority`만 기준으로 정렬하면서 같은 priority에서는 기존 순서를 유지하고 싶다면 stable sort가 의미가 있을 수 있습니다.

---

## comparator는 strict weak ordering을 만족해야 합니다

정렬 comparator는 단순히 `bool`을 반환한다고 끝나는 것이 아닙니다.

표준 정렬 algorithm이 올바르게 동작하려면 comparator가 **strict weak ordering**을 만족해야 합니다.

대표적으로 다음 성질을 기대합니다.

### 자기 자신보다 작지 않음

```cpp
comp(x, x) == false
```

### 두 방향이 동시에 참일 수 없음

```cpp
comp(a, b) == true
```

이면:

```cpp
comp(b, a) == false
```

여야 합니다.

### 순서 관계가 일관됨

```text
a < b
b < c
```

라면:

```text
a < c
```

가 일관되게 성립해야 합니다.

---

## 잘못된 comparator 예시

다음은 흔한 실수입니다.

```cpp
return lhs.id <= rhs.id;
```

`lhs`와 `rhs`가 같은 객체라면:

```cpp
lhs.id <= rhs.id
```

가 `true`가 됩니다.

즉:

```cpp
comp(x, x) == true
```

가 되어 strict ordering 요구를 깨뜨립니다.

정렬 comparator에서는 보통 `<`처럼 strict comparison을 사용합니다.

---

## 여러 기준은 tuple이나 `std::tie`로 표현할 수 있습니다

다음처럼 직접 분기할 수도 있습니다.

```cpp
if (lhs.duration != rhs.duration)
    return lhs.duration < rhs.duration;

return lhs.id < rhs.id;
```

또는:

```cpp
return std::tie(lhs.duration, lhs.id)
     < std::tie(rhs.duration, rhs.id);
```

처럼 lexicographical comparison을 이용할 수 있습니다.

두 코드는 같은 정렬 의도를 더 간결하게 표현할 수 있습니다.

---

## ranges projection을 사용할 수도 있습니다

단순히 한 member를 기준으로 정렬한다면 ranges algorithm의 projection이 코드를 단순하게 만들 수 있습니다.

예:

```cpp
std::ranges::sort(tasks, {}, &Task::id);
```

의미는 개념적으로 다음과 같습니다.

```text
Task 자체를 비교하기 전에
Task::id를 꺼내어
기본 less로 비교
```

복잡한 tie-breaker가 필요한 경우에는 comparator가 더 명확할 수 있습니다.

---

## function template

template은 여러 타입에 대해 같은 구조의 코드를 재사용할 수 있게 합니다.

예:

```cpp
template <typename Iterator, typename Predicate>
Iterator find_match(
    Iterator first,
    Iterator last,
    Predicate predicate
) {
    for (; first != last; ++first) {
        if (predicate(*first))
            return first;
    }

    return last;
}
```

이 함수는 특정 container 타입을 직접 요구하지 않습니다.

대신 구현을 보면 필요한 연산을 추론할 수 있습니다.

---

## template의 실제 요구사항은 구현에 있습니다

위 `find_match`는 `Iterator`에 대해 최소한 다음 연산을 사용합니다.

```cpp
first != last
++first
*first
```

또 `Predicate`에 대해서는:

```cpp
predicate(*first)
```

가 가능한 것을 요구합니다.

즉 template parameter 이름만 보고는 요구사항이 드러나지 않을 수 있지만, 구현이 실제 요구하는 연산 집합이 존재합니다.

---

## unconstrained template의 문제

요구사항을 만족하지 않는 타입을 넘기면 compiler는 template 내부 깊은 위치에서 오류를 출력할 수 있습니다.

예를 들어 `++first`가 불가능한 타입을 넣으면:

```text
find_match 호출
↓
template 인스턴스화
↓
++first 컴파일 실패
↓
긴 오류 메시지
```

가 나올 수 있습니다.

규모가 큰 generic code에서는 caller가 무엇을 잘못했는지 파악하기 어려워질 수 있습니다.

---

## concept으로 요구사항을 표현합니다

C++20 concept을 사용하면 template이 허용할 타입의 요구사항을 이름으로 표현할 수 있습니다.

예:

```cpp
template <typename Range>
concept JobRange =
    std::ranges::input_range<Range> &&
    std::same_as<
        std::remove_cvref_t<
            std::ranges::range_reference_t<Range>
        >,
        Job
    >;
```

그리고:

```cpp
template <JobRange Range>
std::size_t count_failed(const Range& jobs);
```

처럼 사용할 수 있습니다.

---

## concept은 runtime 검사가 아닙니다

concept은 함수가 실행된 뒤 조건을 검사하는 기능이 아닙니다.

```text
호출 후보 결정
↓
template constraint 확인
↓
조건을 만족하는 타입만 사용 가능
```

즉 compile-time 제약입니다.

concept을 만족하지 않는 타입은 해당 template의 유효한 인스턴스가 될 수 없습니다.

---

## concept은 함수 내부 오류를 없애는 기능도 아닙니다

concept을 사용했다고 함수 구현이 자동으로 올바르게 되는 것은 아닙니다.

```cpp
template <JobRange Range>
std::size_t count_failed(const Range& jobs) {
    // 여전히 구현 버그를 작성할 수 있습니다.
}
```

concept이 해결하는 것은 주로 다음 문제입니다.

```text
이 template은 어떤 종류의 타입을 받는가?
```

를 호출 interface에 드러내는 것입니다.

---

## 필요한 것보다 강한 concept을 요구하지 않습니다

template 내부에서 한 번 순회만 하면 되는 함수라고 가정합니다.

그런데 다음처럼 요구하면:

```cpp
std::ranges::random_access_range
```

실제로 필요하지 않은 능력까지 요구할 수 있습니다.

함수가 실제로 필요한 것이 단순한 입력 순회라면:

```cpp
std::ranges::input_range
```

가 더 적절할 수 있습니다.

원칙은 다음과 같습니다.

> 구현에 필요한 최소한의 의미적·연산적 요구사항을 표현합니다.

---

## reference type 조건을 지나치게 엄격하게 만들 수 있습니다

다음 concept을 봅니다.

```cpp
template <typename Range>
concept JobRange =
    std::ranges::input_range<Range> &&
    std::same_as<
        std::remove_cvref_t<
            std::ranges::range_reference_t<Range>
        >,
        Job
    >;
```

이 조건은 range reference에서 cv/ref를 제거한 타입이 정확히 `Job`일 것을 요구합니다.

필요에 따라서는 이것이 맞지만, 함수가 실제로는 `Job`처럼 읽을 수 있는 proxy reference나 파생 타입도 처리할 수 있다면 너무 강한 제약일 수 있습니다.

따라서 concept은 "현재 예시가 통과하는가"보다 **함수 구현이 정말 정확히 어떤 타입 관계를 필요로 하는가**를 기준으로 작성해야 합니다.

---

## 표준 concept을 조합합니다

직접 모든 연산을 검사하는 concept을 만들기보다 이미 존재하는 표준 concept을 조합할 수 있습니다.

예:

```cpp
std::ranges::input_range<R>
std::ranges::forward_range<R>
std::ranges::random_access_range<R>

std::integral<T>
std::floating_point<T>

std::same_as<T, U>
std::convertible_to<T, U>
```

이름 자체가 요구하는 의미를 잘 표현하므로 generic code의 계약을 읽기 쉽게 만들 수 있습니다.

---

## template과 반환 결과의 수명

generic function에서도 반환 결과가 원본을 소유하는지 확인해야 합니다.

예를 들어 iterator를 반환하는 함수:

```cpp
template <std::ranges::range Range>
auto find_ready(Range& range) {
    return std::ranges::find_if(
        range,
        [](const auto& item) {
            return item.ready();
        }
    );
}
```

반환 iterator는 `range` 내부를 가리킵니다.

따라서 caller는 원본 range가 살아 있고 iterator가 무효화되지 않은 동안만 사용할 수 있습니다.

즉 template이라고 lifetime 문제가 사라지는 것이 아닙니다.

---

## 임시 range에서 iterator를 반환하는 문제

다음처럼 temporary container를 전달하고 그 내부 iterator를 저장하려는 코드는 위험할 수 있습니다.

```cpp
auto it = find_ready(make_tasks());
```

함수 signature가 lvalue reference만 받는다면 애초에 이런 호출을 막을 수 있습니다.

```cpp
template <std::ranges::range Range>
auto find_ready(Range& range);
```

반면 forwarding reference나 값 parameter를 사용한다면 반환 iterator의 lifetime을 별도로 검토해야 합니다.

generic API에서는 반환 타입뿐 아니라 **반환값이 어느 객체를 참조하는가**를 명확히 해야 합니다.

---

## ranges의 `dangling`이 존재하는 이유

일부 ranges algorithm은 temporary range에서 iterator를 반환하면 실제 iterator 대신 `std::ranges::dangling`을 반환할 수 있습니다.

이것은 caller가 이미 파괴된 temporary range의 iterator를 실수로 사용하는 것을 줄이기 위한 장치입니다.

이 동작은 range가 `borrowed_range`인지 여부와 관련됩니다.

학습 단계에서는 다음을 기억하면 충분합니다.

```text
ranges algorithm이 iterator를 반환한다고 해서
항상 모든 temporary range에서 유효한 iterator를 얻는 것은 아니다.
```

---

## `borrowed_range`의 핵심 의미

어떤 range는 range 객체 자체가 파괴된 뒤에도 그 iterator가 가리키는 대상이 별도로 살아 있을 수 있습니다.

그런 range는 borrowed range로 취급될 수 있습니다.

반대로 일반 owning container의 temporary는 파괴되면 내부 storage도 함께 사라지므로 iterator를 유지할 수 없습니다.

이 개념은 view와 iterator를 generic하게 반환하는 코드를 작성할 때 중요합니다.

---

## 복잡도와 할당

algorithm 이름만 보고 실제 성능을 판단하지 않습니다.

예를 들어:

- `vector::push_back`은 amortized constant time이지만 재할당 시 기존 원소 이동이 필요합니다.
- `map::find`는 logarithmic time이지만 node allocation과 pointer chasing 비용이 있습니다.
- view는 중간 container allocation을 줄일 수 있지만 계산을 반복할 수 있습니다.
- `reserve()`는 예상 크기를 안다면 재할당 횟수를 줄일 수 있습니다.
- 값을 복사하는 결과 container는 수명을 단순하게 만들지만 복사 비용이 생깁니다.

성능은 복잡도뿐 아니라 실제 데이터와 메모리 사용 방식에 영향을 받습니다.

---

## amortized constant time

`std::vector::push_back`을 평균 상수 시간이라고 설명할 때는 **amortized constant time**이라는 의미입니다.

대부분의 `push_back()`은 남은 capacity에 새 원소 하나만 생성하면 됩니다.

```text
capacity 남음
↓
끝에 원소 생성
```

하지만 capacity가 부족하면:

```text
더 큰 storage 할당
↓
기존 원소 이동/복사
↓
새 원소 추가
↓
기존 storage 해제
```

가 필요합니다.

개별 호출 하나는 선형 비용이 들 수 있지만 여러 `push_back()` 전체 비용을 평균하면 상수 시간으로 볼 수 있다는 의미입니다.

---

## `reserve()`는 size를 늘리지 않습니다

예상 원소 수를 알고 있다면:

```cpp
std::vector<Task> tasks;
tasks.reserve(1000);
```

처럼 미리 capacity를 확보할 수 있습니다.

`reserve(1000)`은 1000개의 실제 `Task`를 만드는 것이 아닙니다.

```text
size     → 실제 원소 수
capacity → 재할당 없이 저장 가능한 공간
```

따라서 호출 직후에는 여전히:

```cpp
tasks.size() == 0
```

일 수 있습니다.

---

## 성능 측정에서는 측정 대상을 분리합니다

정렬 성능을 측정하고 싶은데 다음을 모두 포함하면 결과를 해석하기 어렵습니다.

```text
파일 읽기
문자열 parsing
정렬
출력
```

정렬 자체가 병목인지 확인하려면 가능한 한 측정 범위를 분리합니다.

또 최소한 다음 정보를 함께 기록합니다.

```text
입력 크기
compiler
optimization level
Debug/Release 여부
측정 반복 횟수
환경
```

특히 Debug build와 Release build의 성능 차이는 매우 클 수 있습니다.

---

## 성능 최적화 전에 의미를 보존합니다

더 빠른 container나 algorithm으로 바꾸더라도 다음이 바뀌면 안 될 수 있습니다.

```text
출력 순서
중복 처리 규칙
iterator/reference 안정성
오류 처리
수명 보장
```

예를 들어 `std::map`을 `std::unordered_map`으로 바꾸면 조회 성능 특성뿐 아니라 iteration order 보장도 달라집니다.

따라서 성능 최적화는 단순한 타입 교체가 아니라 프로그램의 observable behavior까지 함께 검토해야 합니다.

---

## 자주 놓치는 문제

### 정렬 결과만 필요한데 원본을 직접 정렬합니다

조회 하나가 원본 상태를 변경해 다른 코드의 의미까지 바꿀 수 있습니다.

원본을 유지해야 한다면 값 복사나 비소유 참조 목록을 검토합니다.

---

### view나 `reference_wrapper`를 원본보다 오래 저장합니다

반환 container 자체가 살아 있다고 내부 참조 대상까지 살아 있는 것은 아닙니다.

---

### container 수정 뒤 iterator를 계속 사용합니다

특히 `std::vector` 재할당은 기존 pointer, reference, iterator를 모두 무효화할 수 있습니다.

---

### `end()`를 실제 원소처럼 사용합니다

검색 실패 후 `end()`를 역참조하면 안 됩니다.

---

### comparator가 strict weak ordering을 지키지 않습니다

예를 들어 `<=`를 사용해 `comp(x, x)`가 true가 되는 comparator는 정렬 요구사항을 위반합니다.

---

### 같은 key의 상대 순서를 암묵적으로 기대합니다

tie-breaker가 없거나 unstable sort를 사용한다면 동등 원소의 상대 순서를 보장할 수 없습니다.

---

### template 오류를 줄이려다 필요하지 않은 concept을 추가합니다

함수가 input iteration만 필요한데 random-access까지 요구하면 사용할 수 있는 타입을 불필요하게 제한합니다.

---

### concept이 있으면 lifetime 문제가 해결된다고 생각합니다

concept은 type constraint를 표현할 뿐, 반환 iterator/view/reference의 원본 수명을 자동으로 보장하지 않습니다.

---

### container를 습관으로 선택합니다

실제 주요 연산, 순서 요구, invalidation, 입력 크기를 먼저 확인합니다.

---

### view가 항상 더 빠르다고 생각합니다

중간 allocation을 줄일 수 있지만 반복 순회에서 predicate나 transform이 계속 다시 계산될 수 있습니다.

---

## 설계할 때의 판단 순서

새 algorithm이나 generic API를 작성할 때는 다음 순서로 확인할 수 있습니다.

```text
1. 주요 연산은 무엇인가?
   └─ 그 연산에 맞는 container 후보 선택

2. 작업에 이미 이름 있는 표준 algorithm이 있는가?
   └─ 있으면 직접 loop와 가독성 비교

3. 결과는 값을 소유해야 하는가?
   ├─ 예 → 새 container
   └─ 아니오 → iterator/view/reference 수명 명시

4. 원본 변경으로 결과가 무효화될 수 있는가?
   └─ container별 invalidation 규칙 확인

5. 정렬 결과가 외부에 보이는가?
   └─ tie-breaker 또는 stable ordering 필요 여부 확인

6. template이 실제로 요구하는 연산은 무엇인가?
   └─ 필요한 최소 concept 또는 문서로 표현

7. 성능이 중요한가?
   └─ Release build와 실제 입력으로 측정
```

---

## 완료 기준

이 문서를 학습한 뒤에는 다음을 설명하고 판단할 수 있어야 합니다.

- 필요한 주요 연산을 기준으로 container를 선택합니다.
- 이론적 복잡도뿐 아니라 allocation과 cache locality 같은 실제 비용을 함께 고려합니다.
- `std::stack` 같은 container adapter와 실제 저장 container의 차이를 설명합니다.
- 직접 loop와 표준 algorithm 중 의도가 더 명확한 표현을 선택합니다.
- `[first, last)` 반열린 범위와 `end()` iterator의 의미를 설명합니다.
- iterator category에 따라 가능한 연산이 다름을 설명합니다.
- container 변경 뒤 iterator, pointer, reference가 무효화될 수 있음을 확인합니다.
- range algorithm이 iterator 쌍 대신 range 자체를 받을 수 있는 이유를 설명합니다.
- view의 lazy evaluation과 원본 수명 조건을 설명합니다.
- view의 iterator도 원본 storage의 invalidation 영향을 받는다는 점을 설명합니다.
- 값을 복사하는 결과와 비소유 reference 결과의 trade-off를 설명합니다.
- 비소유 결과가 원본보다 오래 살아서는 안 된다는 계약을 명시합니다.
- tie-breaker와 `stable_sort`가 각각 어떤 순서 보장을 제공하는지 설명합니다.
- comparator가 strict weak ordering을 만족해야 하는 이유를 설명합니다.
- ranges projection을 단순 member 기준 정렬에 활용할 수 있습니다.
- function template의 실제 요구사항을 구현에서 추적합니다.
- concept을 compile-time 제약으로 이해하고 필요한 최소 조건만 요구합니다.
- template 반환 iterator나 view에서도 lifetime 문제가 그대로 존재함을 설명합니다.
- temporary range와 `std::ranges::dangling`, `borrowed_range`의 관계를 개념적으로 설명합니다.
- `vector::push_back`의 amortized constant time 의미를 설명합니다.
- `reserve()`가 size가 아니라 capacity를 늘린다는 점을 설명합니다.
- 성능 측정에서 parsing·I/O·정렬 시간을 분리하고 Release build와 입력 크기를 기록합니다.
