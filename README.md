# Java 기초 개발 가이드

이 저장소는 Java 프로그램을 직접 만들고 검증하는 데 필요한 최소 기반을 다룹니다. 문법을 전부 외운 뒤 구현을 시작하는 방식이 아니라, 필요한 개념을 익힌 즉시 작은 프로그램으로 확인하고 마지막에 하나의 동시 처리 애플리케이션으로 결합합니다.

과정을 마친 뒤 별도의 입문 프로젝트를 다시 수행하지 않아도 Java 코드의 실행, 타입 설계, 정확한 계산, 실패 처리, 동시성, 빌드와 테스트를 스스로 판단할 수 있는 상태를 목표로 합니다.

## 완료 후 기대하는 능력

- package가 있는 Java 소스를 컴파일하고 JVM에서 실행합니다.
- 기본형과 참조형, `null`, 값 동등성과 객체 동일성을 구분합니다.
- record, enum과 sealed type으로 허용할 값을 제한하고 생성 시점에 잘못된 상태를 거절합니다.
- 컬렉션의 순서·중복·키·소유 조건에 맞는 구현을 선택합니다.
- 정수 오버플로, `BigDecimal`의 scale과 반올림 방식을 명시합니다.
- 입력 오류, 현재 상태에서의 거절과 실행 환경 실패를 구분합니다.
- `Clock`을 주입해 시간에 의존하는 테스트를 반복해서 같은 결과로 실행합니다.
- 경쟁 상태를 `sleep` 없이 재현하고, 함께 바뀌어야 하는 값을 하나의 잠금 범위에서 갱신합니다.
- 제한된 실행기의 작업자, 대기열, 거절, 취소, 인터럽트와 종료를 처리합니다.
- Maven으로 프로젝트를 빌드하고 JUnit·AssertJ로 반환값, 상태 변화, 실패 뒤 상태와 자원 정리를 검증합니다.

## 지원 환경

- Linux 또는 macOS
- JDK 17 이상
- Maven 3.9 이상
- Bash가 필요한 프로젝트는 `maven-artifact-boundary`뿐입니다.

각 exercise는 독립된 Maven 프로젝트입니다. 해당 디렉터리로 이동해 다음 명령을 실행합니다.

```sh
mvn clean test
```

## 필수 학습 범위

### 1. 실행과 언어 기초

- [JDK·JVM과 첫 프로그램](docs/01-language-and-domain/01-jdk-jvm-and-first-program.md)
- [Java 언어 기초](docs/01-language-and-domain/02-java-language-foundations.md)
- [Number Report](exercises/number-report/README.md)

문자열 인자를 읽고 계산한 뒤 `stdout`, `stderr`와 종료 상태를 구분하는 프로그램을 완성합니다.

### 2. 빌드와 테스트 기초

- [Maven Wrapper와 빌드 수명 주기](docs/03-build-test-and-evidence/01-maven-wrapper-and-lifecycle.md)
- [JUnit·AssertJ와 테스트 대역](docs/03-build-test-and-evidence/02-junit-assertj-and-test-doubles.md)

앞에서 만든 프로그램을 Maven으로 빌드하고 정상 결과뿐 아니라 실패 시 남는 상태까지 테스트합니다.

### 3. 타입, 데이터와 실패 처리

- [도메인 타입, record와 sealed type](docs/01-language-and-domain/03-domain-types-records-and-sealed-types.md)
- [컬렉션·Stream과 숫자 불변식](docs/01-language-and-domain/04-collections-streams-and-numeric-invariants.md)
- [오류·검증·시간과 식별자](docs/01-language-and-domain/05-errors-validation-time-and-identifiers.md)

이 단계까지 읽은 뒤 [Concurrent Job Ledger](exercises/concurrent-job-ledger/README.md)의 값 타입과 생성 검증부터 작성할 수 있습니다. 동시 처리 부분은 다음 단계에서 이어서 완성합니다.

### 4. 동시성과 실행기

- [동시성·잠금과 실행기](docs/02-runtime-and-concurrency/01-concurrency-locking-and-executors.md)
- [Counter Race](exercises/counter-race/README.md)
- [Bounded Task Runner](exercises/bounded-task-runner/README.md)

손실 갱신을 반복해서 재현하고, 잠금으로 값을 보호한 뒤 제한된 실행기의 포화와 종료를 검증합니다.

### 5. 최종 통합

- [Concurrent Job Ledger](exercises/concurrent-job-ledger/README.md)

값 타입, 정확한 정수 연산, 주입한 시간, 중복 요청 처리, 잠금, 제한된 실행기와 종료 절차를 하나의 애플리케이션에 결합합니다.

## 선택 자료

- [품질 검사·프로파일링과 검증 근거](docs/03-build-test-and-evidence/03-quality-profiling-and-evidence.md)
  - debugger, thread dump, 정적 검사와 JFR이 각각 무엇을 확인하는지 정리합니다.
- [Maven Artifact Boundary](exercises/maven-artifact-boundary/README.md)
  - 서로 독립된 Maven 프로젝트 사이에서 로컬 저장소의 산출물 설치 전후를 재현합니다.

두 자료는 유용하지만 필수 완료 조건에는 포함하지 않습니다.

## 학습 원칙

### 필요한 만큼 읽고 바로 구현합니다

문서를 모두 읽은 뒤 exercise를 몰아서 수행하지 않습니다. 현재 프로젝트를 시작할 수 있을 만큼만 읽고 구현하면서 부족한 개념을 다시 확인합니다.

### 정상 사례만 확인하지 않습니다

입력 오류, 경계값, 오버플로, 중복 요청, 작업 거절, 시간 초과와 종료 중 인터럽트를 함께 테스트합니다. 예외가 발생했다는 사실뿐 아니라 실패 뒤 기존 상태가 유지되는지도 확인합니다.

### 실행 속도로 동시성 테스트를 맞추지 않습니다

`Thread.sleep`으로 작업 순서를 추측하지 않습니다. latch, barrier와 제어 가능한 `Clock`으로 필요한 상태를 직접 만듭니다.

## 완료 기준

다음을 모두 만족하면 이 과정을 완료한 것으로 봅니다.

1. 필수 문서 8개를 이해하고 핵심 선택 이유를 설명합니다.
2. `number-report`, `counter-race`, `bounded-task-runner`, `concurrent-job-ledger`의 테스트를 통과합니다.
3. 각 프로젝트의 실패 사례가 기존 상태와 자원을 어떻게 남기는지 설명합니다.
4. `concurrent-job-ledger`에서 같은 작업의 중복 제출, 대기열 포화, 잔액 부족, 오버플로와 종료를 테스트로 재현합니다.
5. 모든 필수 프로젝트를 각각 독립된 디렉터리에서 빌드하고 실행합니다.

전체 순서는 [학습 로드맵](docs/00-roadmap.md)에서 확인할 수 있습니다.
