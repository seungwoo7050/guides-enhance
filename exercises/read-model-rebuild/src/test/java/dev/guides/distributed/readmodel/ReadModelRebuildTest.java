package dev.guides.distributed.readmodel;

import dev.guides.distributed.testing.Checks;

public final class ReadModelRebuildTest {
    public static void main(String[] args) {
        checkpointDoesNotAdvanceBeforeApply();
        replayAfterApplyBeforeCheckpointIsIdempotent();
        emptyProjectionCanBeRebuilt();
        reusedIdWithDifferentPayloadIsRejected();
        System.out.println("read-model-rebuild tests passed");
    }

    private static void checkpointDoesNotAdvanceBeforeApply() {
        ReadModelRebuild.EventLog log = new ReadModelRebuild.EventLog();
        log.append(new ReadModelRebuild.Event("e-1", "a-1", 1));
        log.append(new ReadModelRebuild.Event("e-2", "a-1", 2));

        ReadModelRebuild.Projection projection = new ReadModelRebuild.Projection();
        ReadModelRebuild.Runner runner = new ReadModelRebuild.Runner(log, projection);
        runner.processNext(false, false);

        Checks.throwsType(
            ReadModelRebuild.SimulatedCrashException.class,
            () -> runner.processNext(true, false),
            "A pre-apply crash must be reproducible"
        );
        Checks.equals(1L, runner.checkpoint(), "An unapplied event must not be skipped");
        Checks.equals(1, projection.total("a-1"), "The second event must remain unapplied");

        runner.processNext(false, false);
        Checks.equals(3, projection.total("a-1"), "Restart must process the missing event");
    }

    private static void replayAfterApplyBeforeCheckpointIsIdempotent() {
        ReadModelRebuild.EventLog log = new ReadModelRebuild.EventLog();
        log.append(new ReadModelRebuild.Event("e-3", "a-2", 5));

        ReadModelRebuild.Projection projection = new ReadModelRebuild.Projection();
        ReadModelRebuild.Runner runner = new ReadModelRebuild.Runner(log, projection);

        Checks.throwsType(
            ReadModelRebuild.SimulatedCrashException.class,
            () -> runner.processNext(false, true),
            "The apply-before-checkpoint crash window must be reproducible"
        );
        Checks.equals(0L, runner.checkpoint(), "The same position must be retried");
        Checks.equals(5, projection.total("a-2"), "The first apply remains committed");

        runner.processNext(false, false);
        Checks.equals(5, projection.total("a-2"), "Redelivery must not double the total");
        Checks.equals(1, projection.appliedCount(), "Only one event claim must exist");
    }

    private static void emptyProjectionCanBeRebuilt() {
        ReadModelRebuild.EventLog log = new ReadModelRebuild.EventLog();
        log.append(new ReadModelRebuild.Event("e-a", "a-3", 2));
        log.append(new ReadModelRebuild.Event("e-b", "a-3", 4));

        ReadModelRebuild.Projection rebuilt = new ReadModelRebuild.Projection();
        ReadModelRebuild.Runner runner = new ReadModelRebuild.Runner(log, rebuilt);
        runner.replayAll();

        Checks.equals(6, rebuilt.total("a-3"), "The full log must rebuild the projection");
        Checks.equals(2, rebuilt.appliedCount(), "All unique events must apply");
        Checks.equals(2L, runner.checkpoint(), "The checkpoint must reach the log end");
    }

    private static void reusedIdWithDifferentPayloadIsRejected() {
        ReadModelRebuild.Projection projection = new ReadModelRebuild.Projection();
        projection.apply(new ReadModelRebuild.Event("e-conflict", "a-4", 2));

        Checks.throwsType(
            IllegalArgumentException.class,
            () -> projection.apply(new ReadModelRebuild.Event("e-conflict", "a-4", 5)),
            "An event ID cannot hide a different payload"
        );
        Checks.equals(2, projection.total("a-4"), "A conflict must not change the projection");
        Checks.equals(1, projection.appliedCount(), "A conflict must not add an event claim");
    }
}
