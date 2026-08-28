# Java 언어 기초

이 문서는 작은 Java 프로그램을 작성하는 데 필요한 언어 최소선을 다룹니다. 키워드를 나열하기보다 값이 어떻게 전달되고, 객체가 어떻게 바뀌며, 실패가 호출자에게 어떻게 전달되는지에 집중합니다.

## 기본형과 참조형

Java 변수에 들어가는 값은 크게 기본형과 참조형으로 나뉩니다.

| 종류 | 예 | 변수에 저장되는 값 |
| --- | --- | --- |
| 기본형 | `boolean`, `char`, `int`, `long`, `double` | 값 자체 |
| 참조형 | `String`, 배열, 클래스, 인터페이스 | 객체를 가리키는 참조 |

```java
int retryCount = 3;
long fileSize = 4_294_967_296L;
double ratio = 0.75;
boolean enabled = true;
```

지역 변수는 읽기 전에 직접 초기화해야 합니다. 필드는 자료형에 따른 기본값을 갖지만, 필요한 값을 생성자에서 명시하면 초기화 누락을 더 일찍 발견할 수 있습니다.

정수끼리 나누면 소수 부분이 버려집니다.

```java
int truncated = 5 / 2;        // 2
double precise = 5.0 / 2.0;  // 2.5
```

정수 연산은 범위를 벗어나도 기본적으로 예외가 발생하지 않습니다. 범위를 벗어난 결과를 허용할 수 없다면 `Math.addExact`, `Math.subtractExact`, `Math.multiplyExact`를 사용합니다.

## Java는 인자를 값으로 전달합니다

기본형 값뿐 아니라 객체 참조도 복사해서 전달합니다.

```java
static void replaceName(String name) {
  name = "Lee";
}

String name = "Kim";
replaceName(name);
System.out.println(name); // Kim
```

메서드 안에서 참조 변수에 다른 객체를 대입해도 호출자의 변수는 바뀌지 않습니다. 다만 두 참조가 같은 가변 객체를 가리키고 있다면 객체의 내용은 바뀔 수 있습니다.

```java
static void addItem(List<String> items) {
  items.add("note");
}
```

호출자가 넘긴 목록을 바꾸지 않아야 한다면 복사본을 만들어 반환합니다.

```java
static List<String> withItem(List<String> items, String item) {
  List<String> result = new ArrayList<>(items);
  result.add(item);
  return List.copyOf(result);
}
```

## `String`, `null`과 동등성

`String`은 참조형이지만 생성한 뒤 내용이 바뀌지 않는 불변 객체입니다.

```java
String first = "board";
String second = new String("board");

System.out.println(first == second);      // false
System.out.println(first.equals(second)); // true
```

- `==`는 두 참조가 같은 객체를 가리키는지 확인합니다.
- `equals`는 두 객체가 같은 값으로 취급되는지 확인합니다.

문자열과 값 객체는 보통 `equals`로 비교합니다.

`null`은 참조가 어떤 객체도 가리키지 않는 상태입니다. 반드시 필요한 값이라면 사용하는 곳까지 미루지 말고 입력을 받는 지점이나 생성자에서 즉시 거절합니다.

```java
static int titleLength(String title) {
  Objects.requireNonNull(title, "title");
  return title.length();
}
```

값이 없는 것이 정상 결과라면 빈 문자열이나 임의의 숫자로 대신하지 않습니다. 호출자가 값의 부재를 구분할 수 있는 반환 형식을 선택합니다. `Optional`은 반환값의 부재를 나타낼 때 유용하지만 필드와 인자에 습관적으로 사용하지 않습니다.

## 조건과 반복

조건문은 값을 분류하고, 반복문은 같은 처리를 여러 값에 적용합니다.

```java
static String accessLabel(boolean active, int roleLevel) {
  if (!active) {
    return "비활성";
  }
  return roleLevel >= 2 ? "편집 가능" : "읽기 전용";
}
```

가능한 값이 명확하면 `switch` 표현식으로 누락을 줄일 수 있습니다.

```java
static int retryLimit(String mode) {
  return switch (mode) {
    case "interactive" -> 1;
    case "batch" -> 3;
    default -> throw new IllegalArgumentException("알 수 없는 모드: " + mode);
  };
}
```

원소만 필요하면 향상된 `for`문을 사용합니다.

```java
for (String item : items) {
  System.out.println(item);
}
```

인덱스 자체가 필요한 경우에만 전통적인 `for`문을 사용하고, 마지막 인덱스를 넘지 않는지 확인합니다.

## 메서드로 작업 나누기

입력 해석, 계산, 상태 변경과 출력을 한 메서드에 모두 넣으면 실패 위치를 찾기 어렵고 테스트도 복잡해집니다.

```text
문자열 입력 해석
→ 유효한 값 생성
→ 계산
→ 결과 출력
```

계산 메서드는 가능한 한 값을 반환하게 하고, 파일이나 `stdout`에 쓰는 코드는 바깥쪽에 둡니다. 변환과 계산이 실패할 수 있다면 출력을 시작하기 전에 먼저 끝냅니다.

[Number Report](../../exercises/number-report/README.md)는 다음 작업을 분리합니다.

- 인자 개수 확인
- 문자열을 `long`으로 변환
- 합계·최솟값·최댓값·평균 계산
- 정상 출력과 오류 출력 분리
- 실패 종료 상태 반환

## 배열과 컬렉션

배열은 길이가 고정되어 있고 인덱스로 접근합니다.

```java
String[] roles = {"viewer", "editor", "owner"};
System.out.println(roles[1]);
```

원소 수가 바뀌는 목록은 `List`, 중복을 허용하지 않는 값은 `Set`, 키로 값을 찾을 때는 `Map`을 먼저 검토합니다.

```java
List<String> names = new ArrayList<>();
names.add("Kim");

Set<String> permissions = new HashSet<>();
permissions.add("board:read");

Map<String, Integer> versions = new HashMap<>();
versions.put("board-a", 3);
```

변수와 인자는 보통 `ArrayList` 같은 구현 클래스보다 `List`, `Set`, `Map` 같은 인터페이스 타입으로 선언합니다. 호출자가 실제로 필요한 연산을 더 잘 드러내고 구현을 바꿀 여지도 남길 수 있습니다.

## 클래스, 생성자와 상태 변경

클래스는 상태와 그 상태를 바꾸는 메서드를 함께 둘 수 있습니다.

```java
public final class Counter {
  private final int minimum;
  private int value;

  public Counter(int minimum, int initialValue) {
    if (initialValue < minimum) {
      throw new IllegalArgumentException("initialValue가 minimum보다 작습니다.");
    }
    this.minimum = minimum;
    this.value = initialValue;
  }

  public int value() {
    return value;
  }

  public void decrease() {
    if (value == minimum) {
      throw new IllegalStateException("최솟값보다 줄일 수 없습니다.");
    }
    value -= 1;
  }
}
```

필드는 기본적으로 `private`로 두고 필요한 조회와 변경 메서드만 공개합니다. 모든 필드에 setter를 만들기보다 `decrease`, `approve`, `close`처럼 실제 동작을 이름으로 표현하고 거절 조건을 해당 메서드에서 확인합니다.

`final` 필드는 생성한 뒤 다른 값이나 참조로 다시 대입할 수 없습니다. 참조가 `final`이어도 그 참조가 가리키는 가변 객체의 내용은 바뀔 수 있습니다.

`static` 멤버는 특정 객체가 아니라 클래스에 속합니다. `main`이나 상태 없는 유틸리티에는 알맞지만, 변경 가능한 전역 상태를 두면 테스트 사이에 값이 섞이고 동시 실행이 어려워집니다.

## package와 접근 범위

package는 이름 충돌을 피하고 어느 코드에서 접근할 수 있는지 정하는 데 사용합니다.

```java
package dev.guides.foundations;

import java.util.List;
```

접근 범위는 `public`, `protected`, 같은 package에서만 보이는 생략 표기, 같은 클래스 안에서만 보이는 `private`로 나뉩니다. 다른 package가 실제로 사용해야 하는 타입과 메서드만 `public`으로 공개합니다.

## 예외와 자원 정리

잘못된 인자는 `IllegalArgumentException`, 현재 객체 상태에서 실행할 수 없는 동작은 `IllegalStateException`처럼 실패 이유를 드러내는 예외를 사용할 수 있습니다.

저수준 예외를 다른 의미로 바꿀 때는 원인을 보존합니다.

```java
try {
  return Files.readString(path);
} catch (IOException error) {
  throw new IllegalStateException("설정 파일을 읽지 못했습니다: " + path, error);
}
```

파일, socket, stream과 실행기처럼 닫아야 하는 자원은 수명을 명시합니다. `AutoCloseable` 자원은 `try-with-resources`로 관리할 수 있습니다.

```java
static List<String> readLines(Path path) throws IOException {
  try (BufferedReader reader = Files.newBufferedReader(path)) {
    return reader.lines().toList();
  }
}
```

정상 완료, 예외와 조기 반환 모두에서 같은 정리 코드가 실행되어야 합니다.

## 완료 기준

- 기본형 값과 객체 참조가 복사되어 전달되는 방식을 구분합니다.
- 문자열의 `==`와 `equals` 차이를 설명합니다.
- 입력 해석, 계산과 출력을 별도 메서드로 나눕니다.
- 배열, `List`, `Set`, `Map`의 기본 용도를 구분합니다.
- 생성자가 유효한 객체만 만들게 하고 상태 변경 메서드에서 거절 조건을 확인합니다.
- 예외 원인을 보존하고 닫아야 하는 자원을 정리합니다.

이제 [Number Report](../../exercises/number-report/README.md)를 구현한 뒤 [Maven Wrapper와 빌드 수명 주기](../03-build-test-and-evidence/01-maven-wrapper-and-lifecycle.md)로 진행합니다.
