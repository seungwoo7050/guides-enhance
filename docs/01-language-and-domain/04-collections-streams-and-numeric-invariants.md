# 컬렉션·Stream과 숫자 불변식

컬렉션과 숫자 타입은 메서드가 많거나 익숙하다는 이유로 고르지 않습니다. 순서, 중복, 조회 방식, 값의 단위와 반올림처럼 실제로 지켜야 할 조건을 먼저 정한 뒤 구현을 선택합니다.

## 필요한 동작에 맞는 컬렉션

| 필요한 동작 | 기본 후보 |
| --- | --- |
| 입력 순서를 유지하고 중복을 허용합니다. | `List` |
| 중복을 허용하지 않고 포함 여부를 자주 확인합니다. | `Set` |
| 키마다 하나의 값을 저장하고 조회합니다. | `Map` |
| 앞이나 뒤에서 값을 넣고 뺍니다. | `Deque` |
| 키나 값을 정렬된 상태로 유지합니다. | `TreeMap`, `TreeSet` 또는 명시적으로 정렬한 결과 |

`HashMap`과 `HashSet`의 순회 순서를 출력이나 테스트 기준으로 사용하지 않습니다. 순서가 필요하면 직접 정렬하고, 첫 번째 기준이 같을 때 사용할 두 번째 기준도 정합니다.

```java
Comparator<JobReceipt> order =
    Comparator.comparing(JobReceipt::completedAt)
        .thenComparing(receipt -> receipt.id().value());
```

Map의 키로 사용할 객체는 저장한 뒤 `equals`와 `hashCode` 결과가 바뀌지 않아야 합니다. 변경 가능한 객체 전체보다 바뀌지 않는 식별자를 키로 쓰는 편이 안전합니다.

## 컬렉션의 소유와 복사

생성자에서 받은 목록을 그대로 필드에 저장하면 호출자가 나중에 원본 목록을 바꿀 수 있습니다.

```java
public final class QueuePlan {
  private final List<JobId> jobs;

  public QueuePlan(List<JobId> jobs) {
    this.jobs = List.copyOf(jobs);
  }

  public List<JobId> jobs() {
    return jobs;
  }
}
```

`Collections.unmodifiableList`는 원본을 감싼 읽기 전용 보기일 수 있습니다. 원본이 바뀌면 보기의 내용도 달라질 수 있습니다. 독립된 복사본이 필요하면 `List.copyOf`나 새 컬렉션을 사용합니다.

반복 중인 컬렉션을 직접 수정하면 `ConcurrentModificationException`이 발생하거나 일부 원소를 건너뛸 수 있습니다. 조건에 맞는 항목을 지울 때는 `removeIf`, 새 결과가 필요할 때는 별도 컬렉션을 사용합니다.

## Stream을 사용할 때

Stream은 부수 효과가 없는 짧은 변환을 읽기 좋게 표현합니다.

```java
List<String> enabledNames =
    entries.stream()
        .filter(Entry::enabled)
        .map(Entry::name)
        .sorted()
        .toList();
```

다음과 같은 경우에는 명시적인 반복문이 더 분명할 수 있습니다.

- 중간에 여러 이유로 반복을 끝냅니다.
- checked exception을 처리해야 합니다.
- 파일, 저장소나 네트워크에 값을 씁니다.
- 여러 누적 값을 함께 바꿉니다.
- 중간 상태를 단계별로 확인해야 합니다.

```java
items.stream().forEach(item -> repository.save(transform(item)));
```

위 코드는 어느 항목까지 저장되었는지, 중간 저장 실패 뒤 무엇이 남는지 알아보기 어렵습니다. 외부 상태를 바꾸는 작업이라면 순서와 실패 처리를 반복문에서 드러내는 편이 낫습니다.

`parallelStream()`은 기본적으로 공용 `ForkJoinPool`을 사용합니다. 요청 처리, 블로킹 I/O나 transaction과 섞으면 작업 수와 종료를 제어하기 어렵습니다. 병렬 실행이 필요하면 작업자 수, 대기열과 종료 방법을 직접 정한 실행기를 사용합니다.

## `Optional`의 사용 위치

`Optional<T>`는 결과가 없을 수 있다는 사실을 반환 타입에 나타냅니다.

```java
Optional<JobReceipt> find(JobId id)
```

다음 위치에는 보통 사용하지 않습니다.

- 필드
- 메서드 인자
- 컬렉션 원소
- 직렬화할 DTO의 모든 선택 항목

먼저 값이 없는 상태가 정상인지 오류인지 정합니다. 오류라면 의미 있는 예외나 별도 결과 타입이 필요합니다. 서로 다른 실패를 모두 빈 `Optional`로 바꾸면 호출자가 다음 행동을 결정하기 어렵습니다.

## 정수 단위와 오버플로

소수점이 필요 없는 값은 최소 단위를 정한 뒤 `long`으로 저장할 수 있습니다. 예를 들어 원 단위 금액이나 바이트 수입니다.

```java
long total = Math.addExact(first, second);
long remaining = Math.subtractExact(balance, amount);
long scaled = Math.multiplyExact(quantity, unitPrice);
```

일반 정수 연산은 범위를 벗어나도 자동으로 예외가 발생하지 않습니다. 범위 초과가 잘못된 상태라면 `Math.*Exact`를 사용합니다.

최종 값이 범위 안에 있더라도 중간 계산이 먼저 넘칠 수 있습니다. 연산 순서를 바꾸기 전에 수학적으로 같은 결과인지와 중간 값의 범위를 함께 확인합니다.

업무상 음수가 허용되지 않는다면 exact 연산만으로는 충분하지 않습니다. 계산 뒤 생성자나 상태 변경 메서드에서 음수 여부를 따로 검사합니다. 정수 범위 초과와 허용하지 않는 음수는 서로 다른 실패입니다.

## `BigDecimal`, scale과 반올림

십진 소수 계산이 필요하면 문자열이나 정수에서 `BigDecimal`을 만듭니다.

```java
BigDecimal amount = new BigDecimal("1250.00");
BigDecimal rate = new BigDecimal("0.075");
BigDecimal fee = amount.multiply(rate).setScale(2, RoundingMode.HALF_UP);
```

`new BigDecimal(0.1)`은 이진 부동소수점의 근삿값을 그대로 가져옵니다. 처음부터 십진 문자열이나 정수 최소 단위를 사용하는 편이 의도한 값을 분명히 나타냅니다.

나눗셈 결과가 끝나지 않는 소수가 될 수 있으므로 자릿수와 반올림 방식을 정합니다.

```java
BigDecimal average =
    total.divide(count, 2, RoundingMode.HALF_UP);
```

`scale`과 반올림 방식은 출력 장식이 아니라 계산 결과를 정하는 규칙입니다. 테스트에서도 같은 자릿수와 반올림 방식을 확인합니다.

값만 비교하려면 `compareTo`, scale까지 같아야 한다면 `equals`를 사용합니다.

```java
new BigDecimal("1.0").compareTo(new BigDecimal("1.00")) == 0  // true
new BigDecimal("1.0").equals(new BigDecimal("1.00"))        // false
```

## 결과 하나보다 관계를 확인합니다

상태가 바뀌는 코드에서는 최종 값 하나만 보지 말고 함께 유지되어야 하는 관계를 확인합니다.

```text
처리 전 합계 = 처리 후 합계 + 외부로 이동한 합계
```

[Counter Race](../../exercises/counter-race/README.md)는 승인된 차감액과 남은 값을 함께 검사해 손실 갱신을 찾습니다. [Concurrent Job Ledger](../../exercises/concurrent-job-ledger/README.md)는 잔액과 적용 횟수를 같은 잠금 아래에서 바꾸고 둘 다 테스트합니다.

## 테스트할 경계값

- 빈 컬렉션
- 원소 하나
- 중복 키
- 정렬 기준이 같은 값
- `Long.MAX_VALUE`와 `Long.MIN_VALUE` 근처
- 0과 음수
- 나누어떨어지지 않는 소수 계산
- 서로 다른 단위나 통화

## 완료 기준

- 필요한 순서, 중복과 조회 방식에 맞는 컬렉션을 고릅니다.
- 가변 컬렉션을 외부에 그대로 보관하거나 반환하지 않습니다.
- Stream과 반복문 중 실패와 상태 변경을 더 분명히 드러내는 쪽을 선택합니다.
- 정수 오버플로와 업무상 허용 범위를 따로 검사합니다.
- `BigDecimal`의 생성 방식, scale과 반올림 방식을 명시합니다.
- 최종 값뿐 아니라 보존되어야 하는 값의 관계를 테스트합니다.

다음 문서는 [오류·검증·시간과 식별자](05-errors-validation-time-and-identifiers.md)입니다.
