# Java 학습 로드맵

이 로드맵은 Java 문법을 처음부터 끝까지 읽는 순서가 아닙니다. 작은 프로그램을 만들 수 있을 만큼 개념을 익힌 뒤 바로 구현하고, 다음 단계에서 필요한 내용을 추가하는 순서입니다.

## 대상 독자

다음 중 하나에 해당하면 첫 단계부터 진행합니다.

- Java를 첫 프로그래밍 언어로 선택했습니다.
- 다른 언어를 사용했지만 Java의 값·참조·예외·자원 관리 방식이 낯섭니다.
- Java 코드를 작성해 보았지만 Maven, 테스트와 동시성까지 한 과정으로 검증해 본 적은 없습니다.

조건문, 반복문, 함수, 배열과 클래스가 익숙하더라도 첫 두 문서의 완료 기준은 확인하는 편이 좋습니다. Java의 classpath, 참조 전달 방식과 종료 상태는 다른 언어의 경험만으로 정확히 추측하기 어렵습니다.

## 종료 능력

과정을 마치면 다음 작업을 스스로 수행할 수 있어야 합니다.

1. package가 있는 소스를 컴파일하고 JVM에서 실행합니다.
2. 값과 참조가 메서드에 전달되는 방식을 설명합니다.
3. 생성 시점부터 유효한 record와 클래스를 만듭니다.
4. 컬렉션의 순서·중복·키·소유 조건과 숫자 계산 방식을 코드에 명시합니다.
5. 입력 오류, 상태 거절과 실행 환경 실패를 구분합니다.
6. `Clock`과 명시적인 식별자로 반복 가능한 테스트를 작성합니다.
7. 손실 갱신을 결정적으로 재현하고 필요한 잠금 범위를 선택합니다.
8. 제한된 실행기의 포화, 작업 실패, 시간 초과, 취소와 종료를 처리합니다.
9. Maven과 JUnit으로 프로젝트를 빌드하고 실패 뒤 상태까지 검증합니다.
10. 위 내용을 하나의 동시 작업 원장에 결합합니다.

## 필수 문서

### 실행과 언어

- [JDK·JVM과 첫 프로그램](01-language-and-domain/01-jdk-jvm-and-first-program.md)
- [Java 언어 기초](01-language-and-domain/02-java-language-foundations.md)

### 타입, 데이터와 실패

- [도메인 타입, record와 sealed type](01-language-and-domain/03-domain-types-records-and-sealed-types.md)
- [컬렉션·Stream과 숫자 불변식](01-language-and-domain/04-collections-streams-and-numeric-invariants.md)
- [오류·검증·시간과 식별자](01-language-and-domain/05-errors-validation-time-and-identifiers.md)

### 동시성

- [동시성·잠금과 실행기](02-runtime-and-concurrency/01-concurrency-locking-and-executors.md)

### 빌드와 테스트

- [Maven Wrapper와 빌드 수명 주기](03-build-test-and-evidence/01-maven-wrapper-and-lifecycle.md)
- [JUnit·AssertJ와 테스트 대역](03-build-test-and-evidence/02-junit-assertj-and-test-doubles.md)

## 필수 프로젝트

- [Number Report](../exercises/number-report/README.md)
- [Counter Race](../exercises/counter-race/README.md)
- [Bounded Task Runner](../exercises/bounded-task-runner/README.md)
- [Concurrent Job Ledger](../exercises/concurrent-job-ledger/README.md)

## 권장 순서

### 1단계: Java 프로그램을 실행합니다

다음 두 문서를 읽습니다.

```text
JDK·JVM과 첫 프로그램
→ Java 언어 기초
```

이어서 `number-report`를 직접 다시 만들어 봅니다.

```sh
cd exercises/number-report
mvn clean test
```

이 단계에서는 다음을 확인합니다.

- 명령행 문자열을 `long`으로 변환합니다.
- 합계 오버플로를 감지합니다.
- 모든 입력이 유효한 경우에만 정상 결과를 출력합니다.
- `stdout`, `stderr`와 종료 상태를 따로 테스트합니다.

### 2단계: 빌드와 테스트 방법을 익힙니다

다음 문서를 읽습니다.

```text
Maven Wrapper와 빌드 수명 주기
→ JUnit·AssertJ와 테스트 대역
```

`number-report`의 `pom.xml`과 테스트를 다시 살펴보고 다음을 설명합니다.

- `compile`, `test`, `package`가 각각 무엇을 수행합니까?
- 테스트 의존성이 실행 산출물에 포함되지 않는 이유는 무엇입니까?
- 입력 실패 뒤 `stdout`이 비어 있는지 왜 별도로 확인합니까?

### 3단계: 유효한 타입과 실패 처리 방법을 익힙니다

다음 세 문서를 읽습니다.

```text
도메인 타입, record와 sealed type
→ 컬렉션·Stream과 숫자 불변식
→ 오류·검증·시간과 식별자
```

이 시점부터 `concurrent-job-ledger`의 다음 부분을 먼저 작성할 수 있습니다.

```text
JobId
→ JobCommand
→ CreditJob / DebitJob
→ JobKind
→ JobReceipt
```

아직 실행기와 잠금 코드를 완성하지 않아도 됩니다. 생성 시점에 잘못된 값이 들어오지 않게 하고, 완료 시각을 외부에서 주입할 수 있는 타입부터 만듭니다.

### 4단계: 경쟁 상태와 잠금을 확인합니다

[동시성·잠금과 실행기](02-runtime-and-concurrency/01-concurrency-locking-and-executors.md)의 공유 상태와 잠금 부분을 읽은 뒤 `counter-race`를 실행합니다.

```sh
cd exercises/counter-race
mvn clean test
java -cp target/classes \
  dev.guides.java.counterrace.DeterministicRaceDemo
```

다음을 설명할 수 있어야 합니다.

- `volatile`만으로 읽기·판단·쓰기가 한 번에 실행되지 않는 이유
- barrier가 두 작업의 실행 순서를 어떻게 고정하는지
- 최종 값만 확인하면 손실 갱신을 놓칠 수 있는 이유

### 5단계: 제한된 실행기를 구현합니다

같은 동시성 문서의 실행기, `Future`, 인터럽트와 종료 부분을 읽고 `bounded-task-runner`를 확인합니다.

```sh
cd exercises/bounded-task-runner
mvn clean test
```

다음을 구현하고 테스트합니다.

- 고정된 작업자 수와 대기열 크기
- 포화 시 즉시 거절
- 작업 예외 전달
- 시간 초과 시 `cancel(true)`
- 정상 종료 후 필요할 때 강제 종료
- 시작하지 못한 `Future` 취소
- 종료 대기 인터럽트 상태 복원

### 6단계: 동시 작업 원장을 완성합니다

`concurrent-job-ledger`로 돌아가 나머지를 구현합니다.

```text
원장이 관리할 상태와 자원
→ 잔액과 적용 횟수의 원자적 변경
→ 중복 요청이 공유할 Future
→ 같은 ID의 중복·충돌 판정
→ 제한된 실행기에 제출
→ 정상·강제·인터럽트 종료
```

```sh
cd exercises/concurrent-job-ledger
mvn clean test
```

최종적으로 다음 상황을 모두 재현해야 합니다.

- 같은 명령을 여러 스레드에서 제출해도 한 번만 적용됩니다.
- 같은 ID에 다른 명령을 제출하면 즉시 실패합니다.
- 잔액 부족과 오버플로 뒤 상태가 그대로입니다.
- 작업자와 대기열이 모두 찼을 때 새 작업을 거절합니다.
- 강제 종료 뒤 시작하지 못한 Future가 취소됩니다.
- 종료 대기가 인터럽트되면 인터럽트 상태가 복원됩니다.

## 선택 자료

### 품질 검사와 프로파일링

[품질 검사·프로파일링과 검증 근거](03-build-test-and-evidence/03-quality-profiling-and-evidence.md)는 필수 경로를 마친 뒤 읽습니다. 정적 검사, debugger, thread dump와 JFR이 각각 확인하는 범위를 구분할 때 사용합니다.

### 여러 Maven 프로젝트 사이의 산출물

[Maven Artifact Boundary](../exercises/maven-artifact-boundary/README.md)는 서로 독립된 프로젝트를 로컬 Maven 저장소로 연결해야 할 때 수행합니다. 단일 프로젝트를 빌드하고 테스트하는 데 필요한 최소 과정은 아닙니다.

## 최종 확인

다음 질문에 코드 없이 답할 수 있어야 합니다.

- Java 소스, 바이트코드, JDK와 JVM은 각각 무엇입니까?
- 객체 참조를 메서드에 전달한 뒤 참조를 다시 대입하는 것과 객체를 변경하는 것은 어떻게 다릅니까?
- 어떤 검증을 생성자에 두고 어떤 검증을 현재 상태를 가진 메서드에 둡니까?
- `Math.addExact`와 `BigDecimal`은 각각 어떤 오류를 막습니까?
- `Clock`을 직접 호출하지 않고 주입하는 이유는 무엇입니까?
- visibility와 atomicity는 어떻게 다릅니까?
- 실행기의 대기열을 제한해야 하는 이유는 무엇입니까?
- 시간 초과 보고와 실제 작업 취소는 어떻게 다릅니까?
- 예외가 발생했을 때 어떤 상태가 그대로 남아야 합니까?
- Maven의 소스 디렉터리와 로컬 저장소의 산출물는 어떻게 다릅니까?

답하기 어려운 항목만 해당 문서와 프로젝트로 돌아가 다시 확인합니다.
