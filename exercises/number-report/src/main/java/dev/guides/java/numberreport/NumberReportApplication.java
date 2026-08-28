package dev.guides.java.numberreport;

import java.io.PrintStream;

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

    output.println("count=" + arguments.length);
    output.println("min=" + minimum);
    output.println("max=" + maximum);
    output.println("sum=" + sum);
    return 0;
  }
}
