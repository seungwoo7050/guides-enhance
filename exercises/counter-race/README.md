# Counter Race

## 개요

이 프로젝트는 공유 카운터의 값을 읽고, 변경 가능 여부를 판단하고, 새 값을 쓰는 작업을 서로 분리했을 때 발생하는 손실 갱신을 반복해서 재현합니다. 같은 연산을 `ReentrantLock`으로 보호했을 때 값과 승인된 변경량의 관계가 유지되는지도 함께 확인합니다.

실행 순서를 `sleep`으로 추측하지 않습니다. `CyclicBarrier`를 사용해 두 작업이 같은 초기 값을 읽은 뒤 동시에 진행하도록 만듭니다.

## 주요 기능

- `RacyCounter`에서 두 작업이 같은 값을 읽도록 실행 순서를 고정합니다.
- 두 차감을 모두 승인했지만 실제 값에는 한 번만 반영되는 손실 갱신을 재현합니다.
- `LockedCounter`에서는 읽기·판단·쓰기를 하나의 잠금 범위에서 처리합니다.
- `Future.get`으로 작업 스레드에서 발생한 실패를 호출자에게 전달합니다.
- `CyclicBarrier`, Future와 실행기 종료 대기에 제한 시간을 둡니다.
- 실행 프로그램이 잠금 적용 전후의 결과를 나란히 출력합니다.

## 구성

- `RacyCounter`는 손실 갱신을 드러내기 위해 읽기·판단·쓰기를 의도적으로 분리합니다.
- `LockedCounter`는 같은 연산 전체를 `ReentrantLock`으로 보호합니다.
- `DeterministicRaceDemo`는 두 구현을 실행하고 결과를 모은 뒤 실행기를 종료합니다.
- `CounterConcurrencyTest`는 승인된 금액과 남은 값의 합이 초기 값과 일치하는지 확인합니다.

## 빌드

JDK 17 이상과 Maven 3.9 이상이 필요합니다.

```sh
mvn clean package
```

## 실행

```sh
java -cp target/classes \
  dev.guides.java.counterrace.DeterministicRaceDemo
```

예상 출력은 다음과 같습니다.

```text
racy accepted=160 value=20 invariant=false
locked accepted=80 value=20 invariant=true
```

## 테스트

```sh
mvn test
```

테스트는 최종 값만 확인하지 않습니다. 성공한 차감 금액의 합과 남은 값을 함께 검사해, 두 작업이 모두 성공했다고 반환하면서 실제 변경 한 건이 사라지는 구현을 검출합니다. 잠금을 적용한 구현에서는 두 차감 중 하나만 승인되고 다음 식이 유지되어야 합니다.

```text
승인된 차감액 + 남은 값 = 초기 값
```

## 설계상 선택

`volatile`은 다른 스레드가 최신 값을 볼 수 있게 하지만, 읽기·판단·쓰기를 한 번에 실행하지는 않습니다. 따라서 다음 연산 전체가 함께 보호되어야 합니다.

```text
현재 값 읽기 → 차감 가능 여부 판단 → 새 값 기록
```

경쟁을 재현할 때는 실행 속도에 기대지 않습니다. barrier에서 두 작업을 멈춘 뒤 같은 시점에 진행해 빠르거나 느린 환경에서도 같은 상태를 만듭니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | 읽기·판단·쓰기를 일부러 분리해 손실 갱신을 재현합니다. | `src/main/java/dev/guides/java/counterrace/RacyCounter.java` |
| 1-1 | 같은 값을 읽은 두 작업이 모두 도착할 때까지 CyclicBarrier에서 대기합니다. | `src/main/java/dev/guides/java/counterrace/RacyCounter.java` |
| 2 | 두 구현을 실행하고 결과 수집과 실행기 종료를 처리합니다. | `src/main/java/dev/guides/java/counterrace/DeterministicRaceDemo.java` |
| 3 | 읽기·판단·쓰기를 하나의 잠금 범위에서 수행합니다. | `src/main/java/dev/guides/java/counterrace/LockedCounter.java` |
| 3-1 | 값 조회도 같은 잠금을 사용해 갱신과 겹치지 않게 합니다. | `src/main/java/dev/guides/java/counterrace/LockedCounter.java` |

## 범위와 제한

- `RacyCounter`는 결함을 재현하기 위해 의도적으로 안전하지 않게 작성했습니다.
- 두 작업이 모두 차감 가능한 같은 초기 값을 읽는 상황을 대상으로 합니다.
- lock-free 알고리즘이나 Java Memory Model 전체를 다루지는 않습니다.
