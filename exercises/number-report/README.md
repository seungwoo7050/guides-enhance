# Number Report

## 개요

`NumberReportApplication`은 명령행 인자를 `long`으로 변환한 뒤 개수, 최솟값, 최댓값, 합계와 평균을 출력하는 작은 CLI 프로그램입니다. 모든 입력과 합계를 먼저 확인한 뒤 결과를 출력하므로, 잘못된 입력이 하나라도 있으면 정상 결과의 일부가 남지 않습니다.

## 주요 기능

- 하나 이상의 10진수 정수를 처리합니다.
- `Math.addExact`로 합계가 `long` 범위를 벗어나는지 확인합니다.
- 평균은 `BigDecimal`과 `RoundingMode.HALF_UP`을 사용해 소수 둘째 자리까지 계산합니다.
- 정상 결과는 `stdout`, 오류 메시지는 `stderr`에 기록합니다.
- 입력 오류가 있으면 종료 상태 `2`를 반환합니다.
- 메서드 직접 호출과 별도 JVM 프로세스 실행을 모두 테스트합니다.

## 구성

- `NumberReportApplication.run`은 인자를 검증하고 결과를 계산한 뒤 지정된 출력 스트림에 기록합니다.
- `NumberReportApplication.main`은 `run`의 반환값을 실제 프로세스 종료 상태로 전달합니다.
- `NumberReportApplicationTest`는 계산 결과, 실패 시 출력 상태와 프로세스 종료 상태를 확인합니다.

## 빌드

JDK 17 이상과 Maven 3.9 이상이 필요합니다.

```sh
mvn clean package
```

## 실행

```sh
java -cp target/classes \
  dev.guides.java.numberreport.NumberReportApplication \
  10 -3 8 8 42
```

출력은 다음과 같습니다.

```text
count=5
min=-3
max=42
sum=65
average=13.00
```

인자가 없거나 정수로 변환할 수 없는 값이 있거나 합계가 `long` 범위를 벗어나면 `stdout`에는 아무것도 기록하지 않습니다. 오류 메시지는 `stderr`에 기록하고 종료 상태 `2`를 반환합니다.

## 테스트

```sh
mvn test
```

테스트는 다음 결함을 검출합니다.

- 집계 결과의 개수, 범위, 합계 또는 평균이 잘못된 경우
- 평균을 `HALF_UP`이 아닌 다른 방식으로 반올림한 경우
- 실패 전에 정상 출력의 일부를 기록한 경우
- 합계 오버플로를 놓친 경우
- `main`이 실패 상태를 실제 프로세스 종료 상태로 전달하지 않은 경우

## 설계상 선택

입력을 읽는 동안 결과를 한 줄씩 출력하지 않습니다. 모든 문자열 변환과 합계 계산이 끝난 뒤에만 완성된 결과를 출력합니다. 따라서 중간 인자에서 실패하더라도 성공한 것처럼 보이는 부분 출력이 남지 않습니다.

평균 출력에는 `Locale.ROOT`를 사용합니다. 실행 환경의 Locale이 달라도 소수점 기호와 출력 형식이 바뀌지 않습니다.

## Implementation Order

| 순서 | 구현 내용 | 주요 위치 |
| ---: | --- | --- |
| 1 | 입력·출력 스트림을 받아 실행 결과를 반환합니다. | `src/main/java/dev/guides/java/numberreport/NumberReportApplication.java` |
| 1-1 | 모든 인자를 검증하고 합계를 계산한 뒤에만 출력을 시작합니다. | `src/main/java/dev/guides/java/numberreport/NumberReportApplication.java` |
| 1-2 | 평균의 자릿수와 Locale을 고정해 같은 형식으로 출력합니다. | `src/main/java/dev/guides/java/numberreport/NumberReportApplication.java` |
| 2 | run이 반환한 상태를 프로세스 종료 상태로 전달합니다. | `src/main/java/dev/guides/java/numberreport/NumberReportApplication.java` |

## 범위와 제한

- 입력은 Java `long` 범위의 10진수 정수만 지원합니다.
- 합계가 `long` 범위를 벗어나면 전체 실행이 실패합니다.
- 출력은 줄 단위 텍스트로 고정되어 있으며 JSON 출력은 제공하지 않습니다.
