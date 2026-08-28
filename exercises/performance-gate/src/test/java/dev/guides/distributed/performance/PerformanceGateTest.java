package dev.guides.distributed.performance;

import dev.guides.distributed.testing.Checks;
import java.util.List;

public final class PerformanceGateTest {
    public static void main(String[] args) {
        missingEvidenceIsUnverified();
        mixedEnvironmentIsUnverified();
        fastButIncorrectRunFails();
        completeCorrectRunsPass();
        System.out.println("performance-gate tests passed");
    }

    private static PerformanceGate.Goal goal() {
        return new PerformanceGate.Goal(3, 100, 50);
    }

    private static void missingEvidenceIsUnverified() {
        Checks.equals(
            PerformanceGate.Decision.UNVERIFIED,
            PerformanceGate.evaluate(
                goal(),
                List.of(
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 30),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 31)
                )
            ),
            "Missing required runs must remain unverified"
        );
    }

    private static void mixedEnvironmentIsUnverified() {
        Checks.equals(
            PerformanceGate.Decision.UNVERIFIED,
            PerformanceGate.evaluate(
                goal(),
                List.of(
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 30),
                    new PerformanceGate.Run("jdk21-macos-arm", 100, 100, 0, 0, 20),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 32)
                )
            ),
            "Runs from different environments cannot form one verdict"
        );
    }

    private static void fastButIncorrectRunFails() {
        Checks.equals(
            PerformanceGate.Decision.FAIL,
            PerformanceGate.evaluate(
                goal(),
                List.of(
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 20),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 101, 1, 0, 19),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 21)
                )
            ),
            "A fast run with duplicate effects must fail"
        );
    }

    private static void completeCorrectRunsPass() {
        Checks.equals(
            PerformanceGate.Decision.PASS,
            PerformanceGate.evaluate(
                goal(),
                List.of(
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 30),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 32),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 31)
                )
            ),
            "Complete correctness evidence within the budget must pass"
        );
    }
}
