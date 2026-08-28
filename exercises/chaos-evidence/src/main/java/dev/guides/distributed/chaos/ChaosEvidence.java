package dev.guides.distributed.chaos;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Set;

public final class ChaosEvidence {
    // [Implementation 1] 실험 단계와 판정 값
    // Phase, Failure, Result로 이 모델이 지원하는 실험 입력과 결과를 제한합니다.
    public enum Phase {
        BEFORE,
        DURING,
        AFTER
    }

    public enum Failure {
        BROKER_DOWN,
        DATABASE_DOWN
    }

    public enum Result {
        PASS,
        FAIL
    }

    // [Implementation 2] 시점별 불변 스냅샷
    // Snapshot은 이후 상태가 바뀌어도 장애 전·중·후의 값을 그대로 보존합니다.
    public record Snapshot(
        Phase phase,
        String operationId,
        long elapsedMillis,
        int primaryRows,
        int pendingOutbox,
        int readModelRows,
        boolean processUp
    ) {
        public boolean converged() {
            return primaryRows == readModelRows && pendingOutbox == 0;
        }
    }

    // [Implementation 2-1] 실험 결과 보고서
    // Report는 가설, 시간 예산, 업무 복구 결과, 정리 결과와 모든 스냅샷을 함께 보관합니다.
    public record Report(
        String operationId,
        String hypothesis,
        long timeBudgetMillis,
        long elapsedMillis,
        Result primaryResult,
        Result cleanupResult,
        List<Snapshot> snapshots
    ) {
        public Report {
            snapshots = List.copyOf(snapshots);
        }

        public Snapshot at(Phase phase) {
            return snapshots.stream()
                .filter(snapshot -> snapshot.phase() == phase)
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("missing phase: " + phase));
        }
    }

    // [Implementation 3] 실험 상태 보관
    // Scenario만 원본 행, 미발행 Outbox, 조회 모델 행 수를 변경합니다.
    public static final class Scenario {
        private int primaryRows;
        private int pendingOutbox;
        private int readModelRows;
        private boolean processUp = true;

        public Report run(Set<Failure> failures) {
            return run(
                failures,
                "chaos-operation",
                "the system preserves evidence and converges after one failure",
                1_000,
                10,
                true
            );
        }

        public Report run(
            Set<Failure> failures,
            String hypothesis,
            long timeBudgetMillis,
            boolean cleanupSucceeds
        ) {
            return run(
                failures,
                "chaos-operation",
                hypothesis,
                timeBudgetMillis,
                Math.min(10, timeBudgetMillis),
                cleanupSucceeds
            );
        }

        // [Implementation 3-1] 장애 종류와 시간 예산 검증
        // 상태를 바꾸기 전에 지원하는 장애가 정확히 하나인지와 시간 입력이 유효한지 확인합니다.
        public Report run(
            Set<Failure> failures,
            String operationId,
            String hypothesis,
            long timeBudgetMillis,
            long elapsedMillis,
            boolean cleanupSucceeds
        ) {
            if (failures.size() != 1) {
                throw new IllegalArgumentException("inject exactly one failure");
            }
            if (operationId == null || operationId.isBlank()
                || hypothesis == null || hypothesis.isBlank()
                || timeBudgetMillis <= 0 || elapsedMillis < 0) {
                throw new IllegalArgumentException(
                    "operation, hypothesis, positive time budget and elapsed time are required"
                );
            }
            Failure failure = failures.iterator().next();
            if (failure != Failure.BROKER_DOWN) {
                throw new IllegalArgumentException("unsupported failure: " + failure);
            }

            List<Snapshot> evidence = new ArrayList<>();
            evidence.add(snapshot(Phase.BEFORE, operationId, 0));

            primaryRows++;
            pendingOutbox++;
            evidence.add(snapshot(Phase.DURING, operationId, elapsedMillis / 2));

            publishPending();
            evidence.add(snapshot(Phase.AFTER, operationId, elapsedMillis));
            return report(
                operationId,
                hypothesis,
                timeBudgetMillis,
                elapsedMillis,
                cleanupSucceeds,
                evidence
            );
        }

        // [Implementation 3-2] 업무 복구와 정리 결과 분리
        // 업무 상태의 수렴 여부와 cleanup 성공 여부를 따로 판정해 실패 원인을 보존합니다.
        private Report report(
            String operationId,
            String hypothesis,
            long timeBudgetMillis,
            long elapsedMillis,
            boolean cleanupSucceeds,
            List<Snapshot> evidence
        ) {
            boolean convergedInTime = evidence.get(evidence.size() - 1).converged()
                && elapsedMillis <= timeBudgetMillis;
            return new Report(
                operationId,
                hypothesis,
                timeBudgetMillis,
                elapsedMillis,
                convergedInTime ? Result.PASS : Result.FAIL,
                cleanupSucceeds ? Result.PASS : Result.FAIL,
                evidence
            );
        }

        // [Implementation 3-3] 장애 제거 후 상태 수렴
        // 브로커가 복구되면 미발행 건을 조회 모델에 반영하고 대기 건수를 0으로 만듭니다.
        private void publishPending() {
            readModelRows += pendingOutbox;
            pendingOutbox = 0;
        }

        private Snapshot snapshot(Phase phase, String operationId, long elapsedMillis) {
            return new Snapshot(
                phase,
                operationId,
                elapsedMillis,
                primaryRows,
                pendingOutbox,
                readModelRows,
                processUp
            );
        }
    }

    public static Set<Failure> one(Failure failure) {
        return EnumSet.of(failure);
    }

    private ChaosEvidence() {
    }
}
