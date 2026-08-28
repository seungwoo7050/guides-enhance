# JUnit·AssertJ와 테스트 대역

테스트는 코드가 예외 없이 끝났다는 사실보다 프로그램이 지켜야 할 결과를 확인해야 합니다. 반환값, 내부 상태, 외부 호출, 실패 뒤 상태와 자원 정리를 서로 구분해 관찰합니다.

## 한 테스트에서 드러낼 내용

테스트는 보통 다음 순서로 읽을 수 있어야 합니다.

```text
Given  반복 가능한 시작 상태를 만듭니다.
When   공개 메서드 하나를 실행합니다.
Then   반환값과 상태 변화를 확인합니다.
```

테스트 이름에는 조건과 예상 결과를 함께 넣습니다.

```java
@Test
void rejectsDebitWhenBalanceWouldBecomeNegative() {
  // ...
}
```

한 동작에서 여러 값이 함께 바뀐다면 한 테스트가 관련 결과를 함께 검사해도 됩니다. 예를 들어 차감 실패 뒤 예외 타입, 잔액과 적용 횟수를 한 번에 확인할 수 있습니다.

공통 준비 코드에는 반복되는 설정만 둡니다. 테스트의 판단에 필요한 핵심 값까지 여러 도우미와 상속 클래스 뒤에 숨기면 실패 원인을 읽기 어렵습니다.

## JUnit 수명 주기

JUnit Jupiter는 `@Test`, `@BeforeEach`, `@AfterEach`, parameterized test와 extension 기능을 제공합니다.

- 각 테스트는 다른 테스트 없이도 실행되어야 합니다.
- 테스트 실행 순서를 성공 조건으로 사용하지 않습니다.
- 변경 가능한 static 상태를 테스트 사이에 공유하지 않습니다.
- 파일과 실행기는 `try-with-resources`나 `@AfterEach`에서 정리합니다.
- 테스트가 실패해도 차단된 작업과 임시 파일이 남지 않아야 합니다.

여러 입력이 같은 규칙을 확인할 때 parameterized test가 유용합니다. 원인이 다른 실패를 한 표에 억지로 합치면 어떤 조건이 깨졌는지 읽기 어려울 수 있습니다.

## AssertJ로 결과를 분명하게 검사합니다

AssertJ는 여러 검사를 연결해 읽기 쉬운 실패 메시지를 만들 수 있습니다.

```java
assertThat(result.balance()).isEqualTo(900L);

assertThatThrownBy(() -> ledger.debit(amount))
    .isInstanceOf(IllegalStateException.class)
    .hasMessageContaining("잔액");
```

예외 타입만 확인하고 기존 상태를 놓치지 않습니다.

```java
long originalBalance = ledger.currentBalance();
long originalCount = ledger.appliedJobCount();

assertThatThrownBy(() -> result.get(2, TimeUnit.SECONDS))
    .isInstanceOf(ExecutionException.class)
    .hasCauseInstanceOf(IllegalStateException.class);

assertThat(ledger.currentBalance()).isEqualTo(originalBalance);
assertThat(ledger.appliedJobCount()).isEqualTo(originalCount);
```

객체 전체 비교가 편하더라도 현재 테스트에서 중요하지 않은 임의 ID, 생성 시각이나 순서가 불안정한 값까지 무조건 묶지 않습니다. 필요한 필드만 검사하거나 시간을 주입해 고정합니다.

## 상태와 외부 호출을 따로 확인합니다

메서드가 값을 반환했다는 사실만으로 작업이 한 번만 적용되었다고 말할 수는 없습니다.

중복 요청 처리에서는 다음 항목을 각각 확인합니다.

```text
모든 호출이 같은 완료 결과를 받습니다.
내부 상태는 한 번만 바뀝니다.
변경 기록은 한 건만 추가됩니다.
외부 호출도 한 번만 실행됩니다.
```

[Concurrent Job Ledger](../../exercises/concurrent-job-ledger/README.md)는 같은 명령을 순차·동시에 제출하고 다음을 함께 확인합니다.

- 같은 `CompletableFuture` 인스턴스를 반환합니다.
- 잔액은 한 번만 바뀝니다.
- 적용 횟수는 1입니다.

이렇게 여러 관찰값을 사용하면 모든 호출이 non-null을 반환한다는 약한 테스트가 놓치는 중복 처리를 찾을 수 있습니다.

## 테스트 대역을 선택합니다

| 종류 | 주로 하는 일 |
| --- | --- |
| fake | 실제 동작과 비슷하지만 단순한 메모리 구현을 제공합니다. |
| stub | 미리 정한 값을 반환합니다. |
| spy | 호출 인자와 횟수를 기록합니다. |
| mock | 예상한 호출이 발생했는지 검사합니다. |

구현 내부의 모든 메서드 호출을 mock으로 고정하면 동작은 그대로인데 코드만 정리해도 테스트가 깨집니다. 외부 시스템 호출 횟수나 호출 순서가 실제 요구 사항일 때 상호작용을 검사하고, 순수 계산과 메모리 상태 변경은 결과값을 우선 확인합니다.

메모리 fake는 빠르지만 실제 데이터베이스의 transaction, constraint와 query 결과까지 대신하지는 못합니다. 단위 테스트와 실제 기술을 사용한 통합 테스트가 서로 다른 오류를 찾는다는 점을 구분합니다.

## 시간을 제어합니다

테스트 대상에서 `Instant.now()`를 직접 호출하면 예상 결과를 고정하기 어렵습니다. `Clock`을 생성자에 전달하고 테스트에서는 `Clock.fixed`를 사용합니다.

```java
private static final Instant COMPLETED_AT =
    Instant.parse("2026-01-02T03:04:05Z");

private static final Clock FIXED_CLOCK =
    Clock.fixed(COMPLETED_AT, ZoneOffset.UTC);
```

시간이 작업 순서를 제어해야 한다면 `sleep` 대신 latch를 가진 테스트 대역을 만들 수 있습니다. `ConcurrentJobLedgerTest`의 대기형 `Clock`은 작업이 `clock.instant()`에 들어온 시점을 알리고, 테스트가 해제할 때까지 작업 스레드를 멈춥니다. 이 방식으로 실행 중인 작업 하나와 대기 중인 작업 하나를 안정적으로 만들 수 있습니다.

## 실패와 경계값을 먼저 추가합니다

정상 사례 다음에는 해당 코드가 실제로 틀리기 쉬운 값을 확인합니다.

- 빈 문자열과 `null`
- 0, 최솟값과 최댓값
- 서로 맞지 않는 값의 조합
- 정수 오버플로
- 중간 계산 실패
- 같은 요청 반복
- 같은 식별자와 다른 내용
- 시간 경계
- 대기열 포화
- 시간 초과와 인터럽트
- 종료 뒤 메서드 호출

모든 예외를 넓은 상위 타입 하나로 검사하지 않습니다. 서로 다른 실패가 같은 테스트를 통과하면 잘못된 원인으로 실패해도 발견하지 못할 수 있습니다.

## 동시성 테스트를 반복 가능하게 만듭니다

동시성 테스트는 컴퓨터 속도를 합격 조건으로 사용하지 않습니다.

- latch나 barrier로 작업이 멈출 지점을 정합니다.
- 모든 대기에 제한 시간을 둡니다.
- 모든 `Future`를 읽어 작업 스레드의 예외를 테스트 스레드로 전달합니다.
- 성공 횟수, 합계, 최종 상태와 기록 수를 함께 검사합니다.
- `finally`나 `try-with-resources`에서 실행기를 종료합니다.
- 테스트가 실패해도 기다리는 작업을 해제합니다.

`assertTimeout`은 테스트 스레드의 대기 시간을 제한하지만, 실행 중인 작업과 실행기가 자동으로 정리된다는 뜻은 아닙니다. 테스트 코드가 직접 취소와 종료를 처리해야 합니다.

[Counter Race](../../exercises/counter-race/README.md)는 barrier로 같은 값을 읽은 상태를 만들고, [Bounded Task Runner](../../exercises/bounded-task-runner/README.md)는 latch로 실행 중인 작업과 대기 중인 작업을 구분합니다.

## 프로세스 수준 동작도 필요한 만큼 검사합니다

메서드를 직접 호출하는 테스트는 빠르고 오류 위치를 찾기 쉽습니다. 하지만 `main`이 종료 상태를 올바르게 전달하는지는 별도 프로세스에서만 정확히 확인할 수 있습니다.

[Number Report](../../exercises/number-report/README.md)는 두 방식을 함께 사용합니다.

- `run`을 직접 호출해 `stdout`, `stderr`와 반환 상태를 검사합니다.
- 별도 JVM을 실행해 실제 프로세스 종료 상태를 검사합니다.

프로세스 테스트에는 종료 제한 시간을 두고, 시간을 넘기면 프로세스를 강제로 끝냅니다.

## 테스트가 찾지 못하는 범위를 기록합니다

단위 테스트 통과가 다음 내용을 자동으로 보장하지는 않습니다.

- 실제 데이터베이스의 transaction과 constraint
- 네트워크 단절과 지연
- 운영 환경의 메모리와 CPU 제한
- 여러 프로세스 사이의 경쟁
- 배포 설정과 권한

테스트 결과를 기록할 때 실행한 범위와 실행하지 못한 범위를 구분합니다.

## 완료 기준

- 테스트 이름에 조건과 예상 결과를 나타냅니다.
- 반환값, 상태 변화, 외부 호출과 실패 뒤 상태를 구분해 검사합니다.
- fake, stub, spy와 mock을 필요한 위치에서만 사용합니다.
- `Clock`으로 시간에 의존하는 결과를 고정합니다.
- 동시성 테스트에서 `sleep`에 의존하지 않습니다.
- 테스트가 실패해도 자원과 차단된 작업을 정리합니다.
- 메서드 테스트와 프로세스 테스트가 확인하는 범위를 구분합니다.

다음 단계에서는 [도메인 타입, record와 sealed type](../01-language-and-domain/03-domain-types-records-and-sealed-types.md)부터 읽고 [Concurrent Job Ledger](../../exercises/concurrent-job-ledger/README.md)의 값 타입을 구현합니다.
