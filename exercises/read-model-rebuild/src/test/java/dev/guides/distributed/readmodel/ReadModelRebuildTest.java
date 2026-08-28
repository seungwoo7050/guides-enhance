package dev.guides.distributed.readmodel;

import dev.guides.distributed.testing.Checks;

public final class ReadModelRebuildTest {
    public static void main(String[] args) {
        reusedIdWithDifferentPayloadIsRejected();
        System.out.println("read-model-rebuild tests passed");
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
