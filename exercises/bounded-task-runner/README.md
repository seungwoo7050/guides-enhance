# Bounded Task Runner

## 개요

`BoundedTaskRunner`는 작업자 수와 대기열 크기를 생성 시점에 고정하고, 작업 제출·시간 초과·취소·종료 결과를 호출자가 확인할 수 있게 만든 Java 실행기 유틸리티입니다.

무제한 대기열로 과부하를 숨기지 않습니다. 실행 중인 작업과 대기 중인 작업이 모두 찼을 때는 `RejectedExecutionException`을 즉시 반환합니다.

## 주요 기능

- 고정된 작업자 수와 `ArrayBlockingQueue`를 사용합니다.
- 대기열이 가득 차면 새 작업을 즉시 거절합니다.
- 작업의 반환값과 예외를 `Future`로 전달합니다.
- 제한 시간을 넘긴 작업에는 `cancel(true)`로 인터럽트를 요청합니다.
- 종료할 때는 이미 받은 작업의 완료를 먼저 기다립니다.
- 제한 시간 안에 끝나지 않으면 실행 중인 작업을 중단하고 대기 중인 작업을 취소합니다.
- 종료 대기가 인터럽트되면 현재 스레드의 인터럽트 상태를 복원합니다.

## 구성

- `BoundedTaskRunner`는 `ThreadPoolExecutor`, 작업자 스레드, 대기열과 종료 절차를 관리합니다.
- `ExecutorProbe`는 제한된 수의 작업을 제출하고 모든 `Future` 결과를 회수합니다.
- `BoundedTaskRunnerTest`는 latch를 사용해 포화 상태와 종료 순서를 반복해서 같은 방식으로 만듭니다.

## 빌드

JDK 17 이상과 Maven 3.9 이상이 필요합니다.

```sh
mvn clean package
```

## 사용

```java
try (BoundedTaskRunner runner =
    new BoundedTaskRunner(4, 32, Duration.ofSeconds(2))) {
  Future<String> result = runner.submit(() -> "done");
  System.out.println(result.get());
}
```

실행 가능한 확인 프로그램은 다음과 같이 실행합니다.

```sh
java -cp target/classes dev.guides.java.executor.ExecutorProbe
```

## 테스트

```sh
mvn test
```

테스트는 다음 결함을 검출합니다.

- 작업자와 대기열이 모두 찼는데도 새 작업을 계속 받는 경우
- 작업 예외가 `Future.get()`에서 사라지는 경우
- 시간 초과를 보고만 하고 실제 작업에 인터럽트를 보내지 않는 경우
- 정상 종료가 끝낼 수 있는 작업을 불필요하게 중단하는 경우
- 강제 종료 뒤 대기 중인 `Future`가 완료되지 않은 채 남는 경우
- 종료 대기가 인터럽트된 뒤 인터럽트 상태를 잃는 경우

## 설계상 선택

무제한 대기열은 거절을 없애는 대신 메모리 사용량과 대기 시간을 제한 없이 늘릴 수 있습니다. 이 프로젝트는 작업자 수와 대기열 크기를 고정하고 `AbortPolicy`를 사용해 더 받을 수 없는 작업을 즉시 알립니다.

시간 초과는 반환값만 바꾸는 것으로 끝내지 않습니다. 해당 `Future`에 `cancel(true)`를 호출해 실행 중인 스레드에 인터럽트를 전달합니다. 실제 중단 시점은 작업이 인터럽트에 협조하는지에 따라 달라집니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | 작업자 수와 대기열 크기를 고정한 실행기를 생성합니다. | `src/main/java/dev/guides/java/executor/BoundedTaskRunner.java` |
| 2 | 작업 제출 결과와 포화 거절을 호출자에게 그대로 반환합니다. | `src/main/java/dev/guides/java/executor/BoundedTaskRunner.java` |
| 3 | 제한 시간을 넘긴 Future에 인터럽트 취소를 요청합니다. | `src/main/java/dev/guides/java/executor/BoundedTaskRunner.java` |
| 4 | 정상 종료를 먼저 시도하고 필요하면 남은 작업을 강제로 중단합니다. | `src/main/java/dev/guides/java/executor/BoundedTaskRunner.java` |
| 4-1 | 시작하지 못한 대기 작업의 Future를 취소 상태로 바꿉니다. | `src/main/java/dev/guides/java/executor/BoundedTaskRunner.java` |
| 5 | 제한된 작업 묶음을 실행하고 모든 Future 결과를 회수합니다. | `src/main/java/dev/guides/java/executor/ExecutorProbe.java` |

## 범위와 제한

- `cancel(true)`는 작업이 인터럽트에 협조할 때만 빠른 중단을 보장합니다.
- 작업자 수와 대기열 크기는 생성한 뒤 변경할 수 없습니다.
- 예약 실행, 재시도, 우선순위, 지표 수집과 영구 대기열은 제공하지 않습니다.
