package dev.guides.java.numberreport;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;

class NumberReportApplicationTest {
  @Test
  void reportsCountRangeSumAndRoundedAverage() {
    Invocation result = invoke("10", "-3", "8", "8", "42");

    assertThat(result.status()).isZero();
    assertThat(result.output())
        .isEqualTo(
            """
            count=5
            min=-3
            max=42
            sum=65
            average=13.00
            """);
    assertThat(result.error()).isEmpty();
  }

  @Test
  void roundsHalfUpAtTwoDecimalPlaces() {
    Invocation result = invoke("1", "2", "2");

    assertThat(result.output()).contains("average=1.67\n");
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

  @Test
  void commandLineProcessReturnsDocumentedExitStatus() throws Exception {
    ProcessResult result = runProcess("not-a-number");

    assertThat(result.status()).isEqualTo(2);
    assertThat(result.output()).isEmpty();
    assertThat(result.error()).contains("invalid integer");
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

  private static ProcessResult runProcess(String... arguments) throws Exception {
    String java = Path.of(System.getProperty("java.home"), "bin", "java").toString();
    String classes =
        Path.of(
                NumberReportApplication.class
                    .getProtectionDomain()
                    .getCodeSource()
                    .getLocation()
                    .toURI())
            .toString();
    String[] command = new String[4 + arguments.length];
    command[0] = java;
    command[1] = "-cp";
    command[2] = classes;
    command[3] = NumberReportApplication.class.getName();
    System.arraycopy(arguments, 0, command, 4, arguments.length);

    Process process = new ProcessBuilder(command).start();
    if (!process.waitFor(5, TimeUnit.SECONDS)) {
      process.destroyForcibly();
      throw new IllegalStateException("command-line process did not finish before the deadline");
    }
    int status = process.exitValue();
    String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
    String error = new String(process.getErrorStream().readAllBytes(), StandardCharsets.UTF_8);
    return new ProcessResult(status, output, error);
  }

  private record Invocation(int status, String output, String error) {}

  private record ProcessResult(int status, String output, String error) {}
}
