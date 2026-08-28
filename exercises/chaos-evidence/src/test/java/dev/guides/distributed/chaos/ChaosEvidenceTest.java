package dev.guides.distributed.chaos;

import dev.guides.distributed.testing.Checks;
import java.util.EnumSet;

public final class ChaosEvidenceTest {
    public static void main(String[] args) {
        evidenceContainsAllPhases();
        recoveryUsesBusinessConvergence();
        multipleFailuresAreRejected();
        hypothesisBudgetAndCleanupEvidenceRemainSeparate();
        operationAndElapsedEvidenceStayConnected();
        lateConvergenceFailsThePrimaryResult();
        unsupportedFailureIsRejected();
        System.out.println("chaos-evidence tests passed");
    }

    private static void evidenceContainsAllPhases() {
        ChaosEvidence.Report report = new ChaosEvidence.Scenario()
            .run(ChaosEvidence.one(ChaosEvidence.Failure.BROKER_DOWN));

        ChaosEvidence.Snapshot before = report.at(ChaosEvidence.Phase.BEFORE);
        ChaosEvidence.Snapshot during = report.at(ChaosEvidence.Phase.DURING);
        ChaosEvidence.Snapshot after = report.at(ChaosEvidence.Phase.AFTER);

        Checks.equals(0, before.primaryRows(), "A baseline snapshot is required");
        Checks.equals(1, during.primaryRows(), "Primary mutation must remain visible during failure");
        Checks.equals(1, during.pendingOutbox(), "Pending Outbox evidence must be retained");
        Checks.equals(0, during.readModelRows(), "The read model must lag during broker failure");
        Checks.equals(0, after.pendingOutbox(), "The Outbox must drain after recovery");
        Checks.equals(1, after.readModelRows(), "The read model must converge after recovery");
        Checks.equals(1, during.pendingOutbox(), "Later mutation must not overwrite prior snapshots");
    }

    private static void recoveryUsesBusinessConvergence() {
        ChaosEvidence.Report report = new ChaosEvidence.Scenario()
            .run(ChaosEvidence.one(ChaosEvidence.Failure.BROKER_DOWN));

        Checks.isFalse(
            report.at(ChaosEvidence.Phase.DURING).converged(),
            "A running process is not sufficient evidence of business recovery"
        );
        Checks.isTrue(
            report.at(ChaosEvidence.Phase.AFTER).converged(),
            "Primary, Outbox, and read model must converge"
        );
    }

    private static void multipleFailuresAreRejected() {
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> new ChaosEvidence.Scenario().run(
                EnumSet.of(
                    ChaosEvidence.Failure.BROKER_DOWN,
                    ChaosEvidence.Failure.DATABASE_DOWN
                )
            ),
            "One scenario must inject exactly one failure"
        );
    }

    private static void hypothesisBudgetAndCleanupEvidenceRemainSeparate() {
        ChaosEvidence.Report report = new ChaosEvidence.Scenario().run(
            ChaosEvidence.one(ChaosEvidence.Failure.BROKER_DOWN),
            "Outbox replay converges within 250 ms",
            250,
            false
        );

        Checks.equals(
            "Outbox replay converges within 250 ms",
            report.hypothesis(),
            "The hypothesis must be fixed before execution"
        );
        Checks.equals(250L, report.timeBudgetMillis(), "The budget must remain in evidence");
        Checks.equals(
            ChaosEvidence.Result.PASS,
            report.primaryResult(),
            "Primary convergence must be evaluated independently"
        );
        Checks.equals(
            ChaosEvidence.Result.FAIL,
            report.cleanupResult(),
            "Cleanup failure must remain a separate verdict"
        );
    }

    private static void operationAndElapsedEvidenceStayConnected() {
        ChaosEvidence.Report report = new ChaosEvidence.Scenario().run(
            ChaosEvidence.one(ChaosEvidence.Failure.BROKER_DOWN),
            "op-chaos-7",
            "the projection converges within 100 ms",
            100,
            80,
            true
        );

        Checks.equals("op-chaos-7", report.operationId(), "The report must preserve operation identity");
        Checks.equals(80L, report.elapsedMillis(), "The report must preserve elapsed time");
        for (ChaosEvidence.Snapshot snapshot : report.snapshots()) {
            Checks.equals(
                "op-chaos-7",
                snapshot.operationId(),
                "All phases must belong to the same operation"
            );
        }
    }

    private static void lateConvergenceFailsThePrimaryResult() {
        ChaosEvidence.Report report = new ChaosEvidence.Scenario().run(
            ChaosEvidence.one(ChaosEvidence.Failure.BROKER_DOWN),
            "op-chaos-late",
            "the projection converges within 50 ms",
            50,
            51,
            true
        );

        Checks.isTrue(
            report.at(ChaosEvidence.Phase.AFTER).converged(),
            "Final state may converge after the budget"
        );
        Checks.equals(
            ChaosEvidence.Result.FAIL,
            report.primaryResult(),
            "Late convergence must fail the primary experiment verdict"
        );
    }

    private static void unsupportedFailureIsRejected() {
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> new ChaosEvidence.Scenario().run(
                ChaosEvidence.one(ChaosEvidence.Failure.DATABASE_DOWN)
            ),
            "Unsupported failure types must not produce success evidence"
        );
    }
}
