package dev.guides.java.numberreport;

import java.io.PrintStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Locale;

public final class NumberReportApplication {
  private static final int INVALID_INPUT = 2;

  private NumberReportApplication() {}

  // [Implementation 1] 입력·출력 스트림을 받아 실행 결과를 반환합니다.
  public static int run(String[] arguments, PrintStream output, PrintStream error) {
    if (arguments.length == 0) {
      error.println("error: at least one integer is required.");
      return INVALID_INPUT;
    }

    long minimum = Long.MAX_VALUE;
    long maximum = Long.MIN_VALUE;
    long sum = 0L;

    // [Implementation 1-1] 모든 인자를 검증하고 합계를 계산한 뒤에만 출력을 시작합니다.
    for (String argument : arguments) {
      long value;
      try {
        value = Long.parseLong(argument);
      } catch (NumberFormatException exception) {
        error.println("error: invalid integer: " + argument);
        return INVALID_INPUT;
      }

      try {
        sum = Math.addExact(sum, value);
      } catch (ArithmeticException exception) {
        error.println("error: sum exceeds long range.");
        return INVALID_INPUT;
      }
      minimum = Math.min(minimum, value);
      maximum = Math.max(maximum, value);
    }

    // [Implementation 1-2] 평균의 자릿수와 Locale을 고정해 같은 형식으로 출력합니다.
    BigDecimal average =
        BigDecimal.valueOf(sum)
            .divide(BigDecimal.valueOf(arguments.length), 2, RoundingMode.HALF_UP);

    output.println("count=" + arguments.length);
    output.println("min=" + minimum);
    output.println("max=" + maximum);
    output.println("sum=" + sum);
    output.printf(Locale.ROOT, "average=%.2f%n", average);
    return 0;
  }

  // [Implementation 2] run이 반환한 상태를 프로세스 종료 상태로 전달합니다.
  public static void main(String[] arguments) {
    int status = run(arguments, System.out, System.err);
    if (status != 0) {
      System.exit(status);
    }
  }
}
