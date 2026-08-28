package dev.guides.distributed.contracts;

import dev.guides.distributed.testing.Checks;

public final class ContractsAndOrderTest {
    private static final String CHANNEL = "reservation.events";

    public static void main(String[] args) {
        mismatchedChannelIsRejected();
        unsupportedVersionIsIsolated();
        sequenceGapIsBufferedAndDrained();
        duplicateEventIsIgnored();
        reusedIdAndCompetingSequenceAreRejected();
        aggregateGapsRemainIndependent();
        nonPositiveSchemaVersionsAreRejected();
        System.out.println("contracts-and-order tests passed");
    }

    private static ContractsAndOrder.Event event(
        String id,
        String aggregate,
        long sequence,
        String state
    ) {
        return new ContractsAndOrder.Event(CHANNEL, 1, id, aggregate, sequence, state);
    }

    private static void mismatchedChannelIsRejected() {
        ContractsAndOrder.Projection projection = new ContractsAndOrder.Projection(CHANNEL, 2);
        Checks.throwsType(
            ContractsAndOrder.ContractViolationException.class,
            () -> projection.onEvent(
                new ContractsAndOrder.Event(
                    "reservation.event", 1, "event-wrong", "r-1", 1, "CREATED"
                )
            ),
            "Channel drift must be rejected"
        );
    }

    private static void unsupportedVersionIsIsolated() {
        ContractsAndOrder.Projection projection = new ContractsAndOrder.Projection(CHANNEL, 2);
        ContractsAndOrder.Outcome outcome = projection.onEvent(
            new ContractsAndOrder.Event(CHANNEL, 3, "event-v3", "r-2", 1, "CREATED")
        );
        Checks.equals(ContractsAndOrder.Outcome.ISOLATED, outcome, "Future schema must isolate");
        Checks.equals(1, projection.isolatedCount(), "Isolation evidence must be retained");
        Checks.equals(null, projection.state("r-2"), "Isolated data must not mutate state");
    }

    private static void sequenceGapIsBufferedAndDrained() {
        ContractsAndOrder.Projection projection = new ContractsAndOrder.Projection(CHANNEL, 2);
        Checks.equals(
            ContractsAndOrder.Outcome.BUFFERED,
            projection.onEvent(event("event-2", "r-3", 2, "ACCEPTED")),
            "A sequence gap must buffer"
        );
        Checks.equals(1, projection.bufferedCount("r-3"), "The gap must be retained");
        Checks.equals(null, projection.state("r-3"), "Later state must not apply early");

        projection.onEvent(event("event-1", "r-3", 1, "CREATED"));
        Checks.equals("ACCEPTED", projection.state("r-3"), "The buffer must drain in order");
        Checks.equals(0, projection.bufferedCount("r-3"), "The closed gap must be empty");
    }

    private static void duplicateEventIsIgnored() {
        ContractsAndOrder.Projection projection = new ContractsAndOrder.Projection(CHANNEL, 2);
        ContractsAndOrder.Event event = event("event-d", "r-4", 1, "CREATED");
        projection.onEvent(event);
        Checks.equals(
            ContractsAndOrder.Outcome.DUPLICATE,
            projection.onEvent(event),
            "The same event must classify as duplicate"
        );
        Checks.equals("CREATED", projection.state("r-4"), "Duplicate delivery must not regress state");
    }

    private static void reusedIdAndCompetingSequenceAreRejected() {
        ContractsAndOrder.Projection projection = new ContractsAndOrder.Projection(CHANNEL, 2);
        projection.onEvent(event("event-gap", "r-5", 2, "ACCEPTED"));

        Checks.throwsType(
            ContractsAndOrder.ContractViolationException.class,
            () -> projection.onEvent(event("event-other", "r-5", 2, "REJECTED")),
            "Two events cannot claim the same aggregate sequence"
        );
        Checks.throwsType(
            ContractsAndOrder.ContractViolationException.class,
            () -> projection.onEvent(event("event-gap", "r-6", 2, "REJECTED")),
            "An event ID cannot hide a different payload"
        );
        Checks.equals(1, projection.bufferedCount("r-5"), "Conflicts must preserve prior buffer state");
    }

    private static void aggregateGapsRemainIndependent() {
        ContractsAndOrder.Projection projection = new ContractsAndOrder.Projection(CHANNEL, 2);
        projection.onEvent(event("event-a2", "aggregate-a", 2, "A2"));

        Checks.equals(
            ContractsAndOrder.Outcome.APPLIED,
            projection.onEvent(event("event-b1", "aggregate-b", 1, "B1")),
            "One aggregate gap must not block another aggregate"
        );
        Checks.equals("B1", projection.state("aggregate-b"), "The other aggregate must advance");
        Checks.equals(1, projection.bufferedCount("aggregate-a"), "The first gap must remain");

        projection.onEvent(event("event-a1", "aggregate-a", 1, "A1"));
        Checks.equals("A2", projection.state("aggregate-a"), "The first aggregate must drain");
        Checks.equals("B1", projection.state("aggregate-b"), "Other state must remain unchanged");
    }

    private static void nonPositiveSchemaVersionsAreRejected() {
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> new ContractsAndOrder.Projection(CHANNEL, 0),
            "Supported schema version must be positive"
        );
        ContractsAndOrder.Projection projection = new ContractsAndOrder.Projection(CHANNEL, 2);
        Checks.throwsType(
            ContractsAndOrder.ContractViolationException.class,
            () -> projection.onEvent(
                new ContractsAndOrder.Event(CHANNEL, 0, "event-v0", "r-v0", 1, "CREATED")
            ),
            "Event schema version must be positive"
        );
        Checks.equals(0, projection.isolatedCount(), "Invalid versions are not compatibility isolation");
    }
}
