package dev.guides.java.numberreport;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;

class NumberReportApplicationTest {
  @Test
  void reportsCountRangeAndSum() {
    Invocation result = invoke("10", "-3", "8", "8", "42");

    assertThat(result.status()).isZero();
    assertThat(result.output())
        .isEqualTo(
            """
            count=5
            min=-3
            max=42
            sum=65
            """);
    assertThat(result.error()).isEmpty();
  }

  @Test
  void rejectsMissingArgumentsWithoutWritingStandardOutput() {
    Invocation result = invoke();

    assertThat(result.status()).isEqualTo(2);
    assertThat(result.output()).isEmpty();
    assertThat(result.error()).isEqualTo("error: at least one integer is required.\n");
  }

  @Test
  void rejectsMalformedIntegerWithoutPartialOutput() {
    Invocation result = invoke("10", "3x", "20");

    assertThat(result.status()).isEqualTo(2);
    assertThat(result.output()).isEmpty();
    assertThat(result.error()).isEqualTo("error: invalid integer: 3x\n");
  }

  @Test
  void rejectsOverflowWithoutPartialOutput() {
    Invocation result = invoke(Long.toString(Long.MAX_VALUE), "1");

    assertThat(result.status()).isEqualTo(2);
    assertThat(result.output()).isEmpty();
    assertThat(result.error()).isEqualTo("error: sum exceeds long range.\n");
  }

  private static Invocation invoke(String... arguments) {
    ByteArrayOutputStream outputBytes = new ByteArrayOutputStream();
    ByteArrayOutputStream errorBytes = new ByteArrayOutputStream();
    int status;
    try (PrintStream output = new PrintStream(outputBytes, true, StandardCharsets.UTF_8);
        PrintStream error = new PrintStream(errorBytes, true, StandardCharsets.UTF_8)) {
      status = NumberReportApplication.run(arguments, output, error);
    }
    return new Invocation(
        status,
        outputBytes.toString(StandardCharsets.UTF_8),
        errorBytes.toString(StandardCharsets.UTF_8));
  }

  private record Invocation(int status, String output, String error) {}

}
