# 도메인 타입, record와 sealed type

`long amount`, `String currency`, `String id`처럼 원시 값만 전달하면 단위와 허용 범위를 호출할 때마다 다시 확인해야 합니다. 타입을 만들 때는 이름을 붙이는 데 그치지 않고, 만들 수 있는 값과 허용할 연산을 코드로 제한해야 합니다.

## 값 객체와 식별자를 가진 객체

값 객체는 구성 값이 같으면 같은 값으로 취급합니다. 반면 사용자나 주문처럼 시간이 지나 상태가 바뀌어도 같은 대상을 나타내야 한다면 식별자를 기준으로 구분합니다.

값 객체 후보는 다음과 같습니다.

- 금액
- 기간
- 이메일 주소
- 작업 식별자

값 객체는 생성한 순간부터 유효해야 합니다.

```java
public record JobId(String value) {
  public JobId {
    if (value == null || value.isBlank()) {
      throw new IllegalArgumentException("작업 식별자가 필요합니다.");
    }
    value = value.trim();
  }
}
```

record가 접근자, `equals`, `hashCode`와 `toString`을 만들어 주더라도 입력 검증까지 대신하지는 않습니다.

## 가변 값을 record에 넣을 때

record의 필드 참조는 바뀌지 않지만, 참조가 가리키는 목록의 내용은 바뀔 수 있습니다. 호출자가 넘긴 목록을 그대로 보관하면 record 바깥에서 내용이 바뀔 수 있습니다.

```java
public record Batch(List<JobId> jobs) {
  public Batch {
    jobs = List.copyOf(Objects.requireNonNull(jobs, "jobs"));
  }
}
```

`List.copyOf`를 사용하면 생성 뒤 원본 목록이 바뀌어도 `Batch`의 내용은 달라지지 않습니다. 반환할 때 내부 가변 목록을 그대로 내보내지 않는 것도 같은 이유입니다.

## 생성자와 정적 팩터리

항상 참이어야 하는 조건은 생성자에서 확인합니다. 문자열 해석이나 여러 생성 방식을 이름으로 구분해야 한다면 정적 팩터리를 사용할 수 있습니다.

```java
public static Percentage parse(String raw) {
  BigDecimal value = new BigDecimal(raw);
  return new Percentage(value);
}
```

유효하지 않은 객체를 만든 뒤 setter로 고치는 방식은 피합니다. 객체가 호출자에게 전달되는 모든 경로에서 같은 조건을 만족해야 합니다.

현재 사용자 권한, 저장된 잔액이나 외부 설정에 따라 달라지는 조건은 값 객체 생성자에 넣지 않습니다.

- “금액은 음수가 아닙니다.”는 값 자체의 조건입니다.
- “현재 잔액보다 많이 출금할 수 없습니다.”는 현재 상태를 가진 원장이 판단해야 합니다.

## 클래스와 인터페이스를 선택하는 기준

클래스는 상태와 구현을 함께 가집니다. 인터페이스는 호출자가 기대하는 동작을 표현하며, 실제로 여러 구현을 바꿔 끼워야 하거나 외부 기능을 대신할 때 유용합니다.

```java
public interface ExchangeRateProvider {
  BigDecimal rate(Currency from, Currency to);
}
```

모든 클래스에 같은 이름의 인터페이스를 하나씩 만들 필요는 없습니다. 파일 수만 늘고 교체할 구현도 없다면 실제 사용법이 더 분명해지지 않습니다.

구현 재사용만을 위해 상속하기보다 필요한 객체를 필드로 받아 조합하는 방식을 먼저 검토합니다. 상속은 하위 타입이 상위 타입의 모든 공개 동작을 그대로 지킬 수 있을 때 사용합니다.

## 허용할 변형을 `sealed`로 제한하기

가능한 종류가 정해져 있고 종류마다 가진 값이 다르다면 sealed type이 알맞습니다.

```java
public sealed interface JobCommand permits CreditJob, DebitJob {
  JobId id();

  long amount();
}

public record CreditJob(JobId id, long amount) implements JobCommand {}

public record DebitJob(JobId id, long amount) implements JobCommand {}
```

새 명령을 추가하려면 `permits` 목록과 해당 명령을 처리하는 코드도 함께 검토해야 합니다. 반대로 외부 플러그인이 자유롭게 구현해야 하는 API에는 sealed type이 맞지 않습니다.

Java 17에서는 `instanceof` 패턴으로 타입 확인과 변환을 한 번에 처리할 수 있습니다.

```java
if (command instanceof CreditJob credit) {
  return applyCredit(credit);
}
```

각 명령은 `null`과 금액 범위처럼 자신만의 생성 조건을 확인하고, 잔액처럼 공유 상태를 바꾸는 코드는 원장이 처리합니다.

## `enum`을 사용할 때

가능한 이름이 고정되어 있고 각 값이 같은 형태를 가진다면 `enum`이 적합합니다.

```java
public enum JobStatus {
  ACCEPTED,
  REJECTED
}
```

외부 문자열을 `Enum.valueOf`에 바로 전달하지 않습니다. 대소문자, 공백과 알 수 없는 값의 처리 방식을 입력 해석 코드에서 정합니다.

종류마다 서로 다른 필드를 가져야 한다면 enum보다 sealed type이 더 분명할 수 있습니다.

## 제네릭과 읽기·쓰기 범위

제네릭은 cast를 줄이는 것뿐 아니라 어떤 타입을 읽고 쓸 수 있는지 표현합니다.

```java
static <T> void copy(List<? extends T> source, List<? super T> target) {
  target.addAll(source);
}
```

- 값을 읽어 오는 쪽은 `? extends T`를 사용할 수 있습니다.
- 값을 넣는 쪽은 `? super T`를 사용할 수 있습니다.

와일드카드를 무조건 공개 API에 넣으면 호출하기 어려워질 수 있습니다. 실제로 여러 하위 타입을 읽거나 상위 타입 목록에 써야 하는 경우에만 사용합니다.

원시 타입과 넓은 범위의 `@SuppressWarnings`는 컴파일러가 찾을 수 있는 오류를 실행 시점으로 미룹니다. 경고를 억제해야 한다면 가장 좁은 위치에서 사용하고 안전한 이유를 설명합니다.

## 값 객체의 연산

값 객체가 연산을 제공한다면 단위와 범위를 스스로 확인해야 합니다.

```java
public Money add(Money other) {
  requireSameCurrency(other);
  return new Money(Math.addExact(minor, other.minor), currency);
}
```

다른 통화를 조용히 더하거나 오버플로 값을 그대로 반환하지 않습니다. 연산이 실패해도 기존 객체는 바뀌지 않아야 합니다.

## 공개 타입 점검

타입을 공개하기 전에 다음을 확인합니다.

- 생성할 수 있는 모든 상태가 유효합니까?
- `null`, 빈 값과 최솟값·최댓값의 의미가 분명합니까?
- 외부에서 내부 컬렉션을 바꿀 수 있습니까?
- `equals`와 `hashCode`가 같은 기준을 사용합니까?
- 실패를 예외로 알릴지 정상 결과로 반환할지 구분했습니까?
- 인터페이스가 실제로 교체할 구현을 나타냅니까?
- sealed type에 종류를 추가할 때 확인할 코드가 분명합니까?

[Concurrent Job Ledger](../../exercises/concurrent-job-ledger/README.md)의 `JobId`, `JobCommand`, `CreditJob`, `DebitJob`, `JobKind`, `JobReceipt`에서 이 선택을 확인할 수 있습니다.

다음 문서는 [컬렉션·Stream과 숫자 불변식](04-collections-streams-and-numeric-invariants.md)입니다.
