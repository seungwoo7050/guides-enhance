package dev.guides.distributed.performance;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class PerformanceGate {
    // [Implementation 1] 판정 결과
    // Decision은 충분한 근거가 있는 PASS·FAIL과 근거가 부족한 UNVERIFIED를 구분합니다.
    public enum Decision {
        PASS,
        FAIL,
        UNVERIFIED
    }

    // [Implementation 2] 측정 결과와 목표
    // Run에는 측정값을, Goal에는 반복 수·정확한 효과 수·최대 시간을 보관합니다.
    public record Run(
        String environment,
        int attempted,
        int completedEffects,
        int duplicateEffects,
        int errors,
        long elapsedMillis
    ) {
    }

    public record Goal(
        int requiredRuns,
        int expectedEffectsPerRun,
        long maxElapsedMillis
    ) {
        // [Implementation 2-1] 목표 값 검증
        // 반복 수, 기대 효과 수와 최대 시간이 잘못되면 실행 결과를 평가하기 전에 거절합니다.
        public Goal {
            if (requiredRuns <= 0 || expectedEffectsPerRun < 0 || maxElapsedMillis < 0) {
                throw new IllegalArgumentException("invalid performance goal");
            }
        }
    }

    // [Implementation 3] 근거·정확성·시간 판정
    // 필수 실행 수, 동일 환경, 효과 수와 오류, 경과 시간을 차례로 확인합니다.
    public static Decision evaluate(Goal goal, List<Run> runs) {
        if (runs == null || runs.size() < goal.requiredRuns()) {
            return Decision.UNVERIFIED;
        }
        Set<String> environments = new HashSet<>();
        for (Run run : runs) {
            if (run == null || run.environment() == null || run.environment().isBlank()) {
                return Decision.UNVERIFIED;
            }
            environments.add(run.environment());
        }
        if (environments.size() != 1) {
            return Decision.UNVERIFIED;
        }

        for (Run run : runs) {
            boolean correct = run.attempted() == goal.expectedEffectsPerRun()
                && run.completedEffects() == goal.expectedEffectsPerRun()
                && run.duplicateEffects() == 0
                && run.errors() == 0;
            boolean withinTime = run.elapsedMillis() <= goal.maxElapsedMillis();
            if (!correct || !withinTime) {
                return Decision.FAIL;
            }
        }
        return Decision.PASS;
    }

    private PerformanceGate() {
    }
}
