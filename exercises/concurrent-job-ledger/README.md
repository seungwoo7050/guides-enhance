# Concurrent Job Ledger

## 개요

`ConcurrentJobLedger`는 입금과 차감 작업을 제한된 실행기에서 처리하는 메모리 기반 원장입니다. 같은 `JobId`와 같은 명령이 여러 번 들어오면 하나의 `CompletableFuture`와 처리 결과를 공유합니다. 같은 `JobId`에 다른 명령이 들어오면 충돌로 거절합니다.

잔액과 적용 횟수는 다음 값을 모두 계산한 뒤 하나의 잠금 범위에서 함께 바꿉니다. 잔액 부족이나 정수 오버플로가 발생하면 기존 상태는 그대로 유지됩니다.

## 주요 기능

- `JobId`, `CreditJob`, `DebitJob`을 생성할 때 값을 검증합니다.
- `JobCommand`를 credit과 debit 두 종류로 제한합니다.
- 같은 `JobId`와 같은 명령은 하나의 `CompletableFuture`를 공유합니다.
- 같은 `JobId`에 금액이나 종류가 다른 명령이 들어오면 즉시 거절합니다.
- 잔액과 적용 횟수를 `ReentrantLock`으로 함께 보호합니다.
- 잔액 부족과 산술 오버플로가 발생해도 상태를 바꾸지 않습니다.
- 완료 시각은 생성자에서 받은 `Clock`으로 구합니다.
- 작업자 수와 대기열 크기를 고정해 포화 상태를 호출자에게 알립니다.
- 정상 종료, 강제 종료, 인터럽트된 종료와 대기 작업 취소를 처리합니다.

## 구성

- `JobId`, `JobCommand`, `CreditJob`, `DebitJob`은 원장이 받을 명령의 값과 생성 조건을 정의합니다.
- `JobKind`와 `JobReceipt`는 적용된 작업 종류, 금액, 잔액과 완료 시각을 기록합니다.
- `ConcurrentJobLedger`는 잔액, 적용 횟수, 작업별 완료 결과, 실행기와 종료 상태를 관리합니다.
- 내부 `JobSlot`은 원본 명령과 중복 요청이 공유할 `CompletableFuture`를 묶습니다.

## 빌드

JDK 17 이상과 Maven 3.9 이상이 필요합니다.

```sh
mvn clean package
```

## 사용

```java
Clock clock = Clock.systemUTC();
try (ConcurrentJobLedger ledger =
    new ConcurrentJobLedger(1_000, 2, 16, clock)) {
  JobReceipt credit =
      ledger.submit(new CreditJob(new JobId("credit-42"), 250)).get();
  JobReceipt debit =
      ledger.submit(new DebitJob(new JobId("debit-17"), 100)).get();

  assert credit.balance() == 1_250;
  assert debit.balance() == 1_150;
}
```

## 테스트

```sh
mvn test
```

테스트는 다음 내용을 확인합니다.

- 식별자와 명령 금액의 생성 조건
- 주입한 `Clock`에서 얻은 완료 시각
- 순차·동시 중복 요청이 같은 `CompletableFuture`를 공유하는지
- 같은 식별자로 다른 명령을 제출했을 때 즉시 실패하는지
- 잔액 부족과 오버플로 뒤 잔액과 적용 횟수가 그대로인지
- 작업자와 대기열이 찼을 때 새 작업을 거절하는지
- 강제 종료 뒤 시작하지 못한 작업이 취소되는지
- 종료 대기가 인터럽트되었을 때 인터럽트 상태를 복원하는지
- 종료한 원장이 새 작업을 받지 않는지

## 설계상 선택

### 중복 요청 등록 순서

작업을 실행기에 제출하기 전에 `JobId`별 슬롯을 먼저 등록합니다. 제출부터 하면 같은 ID를 가진 두 요청이 동시에 서로 다른 작업을 만들 수 있습니다. 슬롯을 먼저 등록하면 한 요청만 실제 작업을 제출하고 나머지는 같은 `CompletableFuture`를 받습니다.

실행기가 새 작업을 거절하면 방금 등록한 슬롯을 제거하고 공유 `CompletableFuture`를 예외로 완료합니다. 이 처리가 없으면 실행되지 않은 작업이 작업 목록에 남아 이후 같은 요청도 끝나지 않은 결과를 받게 됩니다.

### 상태 반영 순서

잔액과 적용 횟수는 새 값을 먼저 모두 계산합니다. 계산과 검증이 성공한 뒤 두 필드를 함께 바꿉니다. 따라서 잔액 부족이나 오버플로가 발생해도 한 필드만 바뀐 상태가 남지 않습니다.

### 종료 순서

먼저 새 작업 수락을 막고 이미 받은 작업이 끝나기를 기다립니다. 제한 시간을 넘기면 실행 중인 작업에 인터럽트를 보내고, 아직 시작하지 못한 작업의 `CompletableFuture`는 취소 상태로 바꿉니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | 빈 값이 아닌 작업 식별자만 생성합니다. | `src/main/java/dev/guides/java/jobledger/JobId.java` |
| 2 | 원장이 처리할 명령을 CreditJob과 DebitJob으로 제한합니다. | `src/main/java/dev/guides/java/jobledger/JobCommand.java` |
| 2-1 | 양수 금액을 가진 CreditJob만 생성합니다. | `src/main/java/dev/guides/java/jobledger/CreditJob.java` |
| 2-2 | 양수 금액을 가진 DebitJob만 생성합니다. | `src/main/java/dev/guides/java/jobledger/DebitJob.java` |
| 3 | 영수증에 기록할 작업 종류를 고정합니다. | `src/main/java/dev/guides/java/jobledger/JobKind.java` |
| 3-1 | 적용 결과와 완료 시각을 바뀌지 않는 영수증으로 묶습니다. | `src/main/java/dev/guides/java/jobledger/JobReceipt.java` |
| 4 | 잔액, 작업 기록, 실행기와 종료 상태의 수명을 원장이 관리합니다. | `src/main/java/dev/guides/java/jobledger/ConcurrentJobLedger.java` |
| 5 | 다음 잔액과 적용 횟수를 모두 계산한 뒤 함께 반영합니다. | `src/main/java/dev/guides/java/jobledger/ConcurrentJobLedger.java` |
| 5-1 | 잔액 조회가 갱신 중간 상태를 읽지 않도록 같은 잠금을 사용합니다. | `src/main/java/dev/guides/java/jobledger/ConcurrentJobLedger.java` |
| 5-2 | 적용 횟수 조회도 잔액과 같은 잠금을 사용합니다. | `src/main/java/dev/guides/java/jobledger/ConcurrentJobLedger.java` |
| 6 | 명령과 모든 중복 요청이 공유할 Future를 한 슬롯에 묶습니다. | `src/main/java/dev/guides/java/jobledger/ConcurrentJobLedger.java` |
| 6-1 | 작업 성공과 실패를 공유 Future의 완료 결과로 전달합니다. | `src/main/java/dev/guides/java/jobledger/ConcurrentJobLedger.java` |
| 7 | 같은 ID의 중복·충돌을 판정한 뒤 제한된 실행기에 한 번만 제출합니다. | `src/main/java/dev/guides/java/jobledger/ConcurrentJobLedger.java` |
| 8 | 새 작업을 막고 정상 종료를 시도한 뒤 필요하면 남은 작업을 중단합니다. | `src/main/java/dev/guides/java/jobledger/ConcurrentJobLedger.java` |
| 8-1 | 시작하지 못한 작업의 Future를 취소 상태로 바꿉니다. | `src/main/java/dev/guides/java/jobledger/ConcurrentJobLedger.java` |

## 범위와 제한

- 원장, 작업 목록과 영수증은 프로세스 메모리에만 저장합니다.
- 프로세스 재시작 뒤 복구, 데이터베이스 트랜잭션과 여러 서버 사이의 중복 제거는 제공하지 않습니다.
- 실행 중인 작업은 호출하는 코드와 주입한 객체가 인터럽트에 협조할 때만 빠르게 중단됩니다.
- 작업자 수와 대기열 크기는 생성한 뒤 변경할 수 없습니다.
