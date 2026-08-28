package dev.guides.distributed.capstone;

import dev.guides.distributed.testing.Checks;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class ReservationFlowTest {
    public static void main(String[] args) {
        idempotentSubmissionAndAdmissionRemainBounded();
        brokerFailureAndCrashConvergeThroughRedelivery();
        projectionOrderingSchemaAndTerminalRulesHold();
        authoritativeReconciliationPreservesUnknownAndNextAction();
        endToEndConvergencePreservesIdentifiersAndEvidence();
        dispatcherBoundsQueueSlotsAndDeadlines();
        conflictingIdentitiesAreRejectedBeforeMutation();
        rejectionAndPendingStatesHaveDistinctConvergenceMeaning();
        System.out.println("reservation-flow tests passed");
    }

    private static void idempotentSubmissionAndAdmissionRemainBounded() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(2, 3);

        ReservationFlow.CommandResult first =
            system.submit("op-1", "corr-1", 1);
        ReservationFlow.CommandResult retry =
            system.submit("op-1", "corr-1", 1);

        Checks.equals(first, retry, "A retry must return the existing command result");
        Checks.equals(
            1,
            system.reservations().reservationCount(),
            "A retry must not create another reservation"
        );
        Checks.equals(
            1,
            system.reservations().outboxCount(),
            "A retry must not create another outbox event"
        );
        Checks.equals(
            first,
            system.reservations().findByOperation("op-1"),
            "The operation lookup must recover the authoritative result"
        );

        Checks.throwsType(
            IllegalArgumentException.class,
            () -> system.submit("op-1", "corr-1", 2),
            "The same operation ID must reject a different quantity"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> system.submit("op-1", "corr-other", 1),
            "The same operation ID must reject a different correlation ID"
        );
        Checks.equals(1, system.reservations().reservationCount(),
            "Conflicting input must not mutate reservation state");

        ReservationFlow.SystemUnderTest bounded =
            new ReservationFlow.SystemUnderTest(1, 3);
        bounded.submit("op-bounded-1", "corr-bounded-1", 1);
        Checks.throwsType(
            ReservationFlow.Overloaded.class,
            () -> bounded.submit("op-bounded-2", "corr-bounded-2", 1),
            "Pending admission must enforce its capacity"
        );
        Checks.equals(1, bounded.reservations().reservationCount(),
            "Overload rejection must happen before mutation");
        Checks.equals(1, bounded.reservations().outboxCount(),
            "Overload rejection must not append an outbox record");

        ReservationFlow.SystemUnderTest deadline =
            new ReservationFlow.SystemUnderTest(1, 1);
        Checks.throwsType(
            ReservationFlow.DeadlineExceeded.class,
            () -> deadline.submit("op-late", "corr-late", 1, 50, 50),
            "Expired ingress must be rejected"
        );
        Checks.equals(0, deadline.reservations().reservationCount(),
            "Expired ingress must not create state");
    }

    private static void brokerFailureAndCrashConvergeThroughRedelivery() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(2, 1);
        ReservationFlow.CommandResult command =
            system.submit("op-redelivery", "corr-redelivery", 1);

        system.broker().setAvailable(false);
        Checks.throwsType(
            ReservationFlow.BrokerUnavailable.class,
            () -> system.publishPending(false),
            "Broker failure must remain visible"
        );
        Checks.equals(1, system.reservations().pendingOutboxCount(),
            "Failed delivery must leave pending outbox work");

        system.broker().setAvailable(true);
        Checks.throwsType(
            ReservationFlow.SimulatedCrash.class,
            () -> system.publishPending(true),
            "A crash after send must be reproducible"
        );
        Checks.equals(1, system.reservations().pendingOutboxCount(),
            "A crash before publication acknowledgement must preserve pending work");

        system.publishPending(false);
        List<ReservationFlow.Event> sent = system.brokerMessages();
        Checks.equals(2, sent.size(), "The unacknowledged event must be redelivered");
        Checks.equals(sent.get(0).eventId(), sent.get(1).eventId(),
            "Redelivery must preserve event identity");

        system.consumeInventoryRequests();
        Checks.equals(1, system.inventory().allocationEffects(),
            "Duplicate delivery must allocate inventory once");
        Checks.equals(2, system.inventoryResults().size(),
            "Both delivery attempts must remain observable");

        system.applyInventoryResults();
        Checks.equals(
            ReservationFlow.Status.ACCEPTED,
            system.reservations().status(command.reservationId()),
            "The authoritative reservation must accept the inventory result"
        );
        Checks.equals(2, system.reservations().outboxCount(),
            "Duplicate inventory results must create one status event"
        );
    }

    private static void projectionOrderingSchemaAndTerminalRulesHold() {
        ReservationFlow.QueryService query = new ReservationFlow.QueryService();
        ReservationFlow.Event requested = new ReservationFlow.Event(
            "projection-requested",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "reservation-q",
            1,
            1,
            "corr-q",
            "op-q"
        );
        ReservationFlow.Event accepted = new ReservationFlow.Event(
            "projection-accepted",
            ReservationFlow.Kind.RESERVATION_ACCEPTED,
            "reservation-q",
            2,
            1,
            "corr-q",
            "inventory-q"
        );

        query.consume(accepted);
        Checks.equals(1, query.pendingCount("reservation-q"),
            "A sequence gap must buffer the terminal event");
        Checks.equals(null, query.status("reservation-q"),
            "A buffered terminal event must not mutate the projection");
        query.consume(requested);
        Checks.equals(ReservationFlow.Status.ACCEPTED, query.status("reservation-q"),
            "Closing the gap must apply the buffered event");
        Checks.equals(0, query.pendingCount("reservation-q"),
            "The contiguous buffer must drain completely");
        query.consume(accepted);
        Checks.equals(ReservationFlow.Status.ACCEPTED, query.status("reservation-q"),
            "Exact duplicate delivery must be idempotent");

        Checks.throwsType(
            IllegalArgumentException.class,
            () -> query.consume(new ReservationFlow.Event(
                "projection-rejected",
                ReservationFlow.Kind.RESERVATION_REJECTED,
                "reservation-q",
                2,
                1,
                "corr-q",
                "inventory-other"
            )),
            "A second event must not claim an applied sequence"
        );
        Checks.equals(ReservationFlow.Status.ACCEPTED, query.status("reservation-q"),
            "A sequence conflict must not change the terminal projection");

        ReservationFlow.Event future = new ReservationFlow.Event(
            "future-schema",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "reservation-future",
            1,
            1,
            "corr-future",
            "op-future"
        );
        query.consume(2, future);
        query.consume(2, future);
        Checks.equals(1, query.isolatedCount(),
            "An unsupported envelope must be isolated exactly once");
        Checks.equals(null, query.status("reservation-future"),
            "An isolated event must not enter the projection");
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> query.consume(3, future),
            "The same event ID must not change schema envelope identity"
        );

        ReservationFlow.Event invalidSequence = new ReservationFlow.Event(
            "invalid-sequence",
            ReservationFlow.Kind.RESERVATION_REJECTED,
            "reservation-invalid",
            3,
            1,
            "corr-invalid",
            "cause-invalid"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> query.consume(invalidSequence),
            "Invalid domain sequence must be rejected before buffering"
        );
        Checks.equals(0, query.pendingCount("reservation-invalid"),
            "Invalid sequence must not leave pending state");

        List<ReservationFlow.EventEnvelope> history = new ArrayList<>();
        history.add(new ReservationFlow.EventEnvelope(1, requested));
        history.add(new ReservationFlow.EventEnvelope(1, accepted));
        history.add(new ReservationFlow.EventEnvelope(2, future));
        Collections.reverse(history);
        ReservationFlow.QueryService rebuilt = new ReservationFlow.QueryService();
        rebuilt.rebuild(history);
        Checks.equals(ReservationFlow.Status.ACCEPTED, rebuilt.status("reservation-q"),
            "Rebuild must converge even when history arrives out of order");
        Checks.equals(1, rebuilt.isolatedCount(),
            "Rebuild must preserve unsupported-schema isolation");
    }

    private static void authoritativeReconciliationPreservesUnknownAndNextAction() {
        ReservationFlow.SystemUnderTest ageSystem =
            new ReservationFlow.SystemUnderTest(3, 2);
        ageSystem.submit("op-newer", "corr-newer", 1, 25, 100);
        ageSystem.submit("op-older", "corr-older", 1, 10, 100);
        Checks.equals(
            30L,
            ageSystem.reservations().oldestPendingOutboxAge(40).orElseThrow(),
            "Outbox age must expose the oldest pending responsibility"
        );
        ageSystem.publishPending(false);
        Checks.isTrue(
            ageSystem.reservations().oldestPendingOutboxAge(40).isEmpty(),
            "Published outbox records must disappear from pending-age evidence"
        );

        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(3, 2);
        ReservationFlow.CommandResult command =
            system.submit("op-authoritative", "corr-authoritative", 1, 10, 100);
        system.publishPending(false);
        system.consumeInventoryRequests();

        system.inventory().setLookupAvailable(false);
        List<ReservationFlow.ReconciliationRecord> unavailable =
            system.reconcilePending(50, 25);
        Checks.equals(
            ReservationFlow.ReconciliationOutcome.PENDING_SOURCE_UNAVAILABLE,
            unavailable.get(0).outcome(),
            "Unavailable authority must remain distinct from rejection"
        );
        Checks.equals(75L, unavailable.get(0).nextAttemptAtMillis(),
            "Unavailable authority must record a next action time");
        Checks.equals(
            ReservationFlow.Status.UNKNOWN,
            system.reservations().status(command.reservationId()),
            "An indeterminate authoritative result must be UNKNOWN"
        );

        system.inventory().setLookupAvailable(true);
        List<ReservationFlow.ReconciliationRecord> applied =
            system.reconcilePending(75, 25);
        Checks.equals(
            ReservationFlow.ReconciliationOutcome.APPLIED,
            applied.get(0).outcome(),
            "A later authoritative lookup must apply the stored result"
        );
        Checks.equals(
            List.of("op-authoritative", "op-authoritative"),
            system.inventory().lookupOperations(),
            "Reconciliation must preserve the original operation ID"
        );
        Checks.equals(ReservationFlow.Status.ACCEPTED,
            system.reservations().status(command.reservationId()),
            "Authoritative reconciliation must resolve UNKNOWN to ACCEPTED");

        ReservationFlow.SystemUnderTest absent =
            new ReservationFlow.SystemUnderTest(1, 1);
        ReservationFlow.CommandResult pending =
            absent.submit("op-absent", "corr-absent", 1, 5, 100);
        absent.inventory().setLookupAvailable(false);
        absent.reconcilePending(15, 5);
        absent.inventory().setLookupAvailable(true);
        List<ReservationFlow.ReconciliationRecord> notFound =
            absent.reconcilePending(20, 10);
        Checks.equals(
            ReservationFlow.ReconciliationOutcome.PENDING_NOT_FOUND,
            notFound.get(0).outcome(),
            "A missing authoritative result must remain pending"
        );
        Checks.equals(30L, notFound.get(0).nextAttemptAtMillis(),
            "A missing result must retain a next reconciliation time");
        Checks.equals(ReservationFlow.Status.PENDING,
            absent.reservations().status(pending.reservationId()),
            "A missing result must not become success or rejection");
    }

    private static void endToEndConvergencePreservesIdentifiersAndEvidence() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(2, 1);
        ReservationFlow.CommandResult command =
            system.submit("op-e2e", "corr-e2e", 1, 10, 100);
        system.reconcile();

        Checks.isTrue(system.converged(command.reservationId()),
            "Recovery must converge authority, outbox, and projection");
        Checks.equals(ReservationFlow.Status.ACCEPTED,
            system.reservations().status(command.reservationId()),
            "The authoritative result must be terminal");
        Checks.equals(ReservationFlow.Status.ACCEPTED,
            system.query().status(command.reservationId()),
            "The projection must match authority");
        Checks.equals(0, system.reservations().pendingOutboxCount(),
            "Convergence requires no pending outbox records");

        ReservationFlow.Event requested = system.brokerMessages().stream()
            .filter(event -> event.kind() == ReservationFlow.Kind.RESERVATION_REQUESTED)
            .findFirst()
            .orElseThrow();
        ReservationFlow.Event inventory = system.inventoryResults().get(0);
        ReservationFlow.Event status = system.brokerMessages().stream()
            .filter(event -> event.kind() == ReservationFlow.Kind.RESERVATION_ACCEPTED)
            .findFirst()
            .orElseThrow();
        Checks.equals("corr-e2e", requested.correlationId(),
            "The command correlation ID must reach the first event");
        Checks.equals("op-e2e", requested.causationId(),
            "The first event must identify the command operation");
        Checks.equals(requested.eventId(), inventory.causationId(),
            "The inventory result must identify its request event");
        Checks.equals(inventory.eventId(), status.causationId(),
            "The status event must identify its inventory result");
        Checks.equals("corr-e2e", status.correlationId(),
            "Correlation identity must survive every hop");
        Checks.isTrue(
            system.observations().stream()
                .anyMatch(observation -> "corr-e2e".equals(observation.correlationId())),
            "The flow must retain correlation evidence"
        );
    }

    private static void dispatcherBoundsQueueSlotsAndDeadlines() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(4, 2);
        ReservationFlow.Dispatcher dispatcher =
            new ReservationFlow.Dispatcher(system, 1, 1);
        ReservationFlow.DispatchTask first = new ReservationFlow.DispatchTask(
            "op-dispatch",
            "corr-dispatch",
            1,
            100
        );

        dispatcher.enqueue(first, 10);
        Checks.throwsType(
            ReservationFlow.Overloaded.class,
            () -> dispatcher.enqueue(
                new ReservationFlow.DispatchTask(
                    "op-overflow", "corr-overflow", 1, 100
                ),
                10
            ),
            "Queue capacity must reject excess work"
        );
        Checks.equals(0, system.reservations().reservationCount(),
            "Queue rejection must occur before system mutation");

        ReservationFlow.DispatchTask running = dispatcher.beginNext(20);
        dispatcher.enqueue(
            new ReservationFlow.DispatchTask(
                "op-expired", "corr-expired", 1, 50
            ),
            20
        );
        Checks.throwsType(
            ReservationFlow.Overloaded.class,
            () -> dispatcher.beginNext(20),
            "Running capacity must reject another acquisition"
        );
        Checks.equals(1, dispatcher.queuedCount(),
            "Running-capacity rejection must preserve queued work");

        ReservationFlow.CommandResult accepted = dispatcher.execute(running, 20);
        ReservationFlow.CommandResult retry = dispatcher.execute(running, 20);
        Checks.equals(accepted, retry,
            "Repeated execution must preserve operation identity and result");
        dispatcher.complete(running);
        Checks.throwsType(
            ReservationFlow.DeadlineExceeded.class,
            () -> dispatcher.beginNext(50),
            "An expired queued task must not start"
        );
        Checks.equals(0, dispatcher.runningCount(),
            "Expired work must not consume a running slot");
        Checks.equals(0, dispatcher.queuedCount(),
            "Expired work must be removed from the queue");

        ReservationFlow.Dispatcher duplicates =
            new ReservationFlow.Dispatcher(system, 2, 3);
        ReservationFlow.DispatchTask duplicate = new ReservationFlow.DispatchTask(
            "op-duplicate-running",
            "corr-duplicate-running",
            1,
            100
        );
        duplicates.enqueue(duplicate, 10);
        duplicates.enqueue(duplicate, 10);
        duplicates.enqueue(
            new ReservationFlow.DispatchTask("op-third", "corr-third", 1, 100),
            10
        );
        ReservationFlow.DispatchTask duplicateFirst = duplicates.beginNext(20);
        ReservationFlow.DispatchTask duplicateSecond = duplicates.beginNext(20);
        Checks.equals(2, duplicates.runningCount(),
            "Each duplicate task occurrence must consume a slot");
        Checks.throwsType(
            ReservationFlow.Overloaded.class,
            () -> duplicates.beginNext(20),
            "Duplicate operation identity must not bypass the running limit"
        );
        Checks.equals(1, duplicates.queuedCount(),
            "A running-limit rejection must retain the next task");
        duplicates.complete(duplicateFirst);
        ReservationFlow.DispatchTask third = duplicates.beginNext(20);
        Checks.equals("op-third", third.operationId(),
            "Releasing a slot must allow the retained next task");
        duplicates.complete(duplicateSecond);
        duplicates.complete(third);
        Checks.equals(0, duplicates.runningCount(),
            "Every acquired slot must be releasable exactly once");
    }

    private static void conflictingIdentitiesAreRejectedBeforeMutation() {
        ReservationFlow.InventoryService inventory =
            new ReservationFlow.InventoryService(5);
        ReservationFlow.Event request = new ReservationFlow.Event(
            "request-conflict",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "reservation-conflict",
            1,
            1,
            "corr-conflict",
            "op-conflict"
        );
        ReservationFlow.Event firstResult = inventory.handle(request);
        ReservationFlow.Event retryResult = inventory.handle(
            new ReservationFlow.Event(
                "request-retry",
                ReservationFlow.Kind.RESERVATION_REQUESTED,
                "reservation-conflict",
                1,
                1,
                "corr-conflict",
                "op-conflict"
            )
        );
        Checks.equals(firstResult, retryResult,
            "An operation retry with a new transport event ID must reuse its result");
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> inventory.handle(new ReservationFlow.Event(
                "request-retry",
                ReservationFlow.Kind.RESERVATION_REQUESTED,
                "reservation-conflict",
                1,
                1,
                "corr-conflict",
                "op-other"
            )),
            "An alias event ID must not be reused for another operation"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> inventory.handle(new ReservationFlow.Event(
                "request-other",
                ReservationFlow.Kind.RESERVATION_REQUESTED,
                "reservation-conflict",
                1,
                2,
                "corr-conflict",
                "op-conflict"
            )),
            "An operation ID must not hide different inventory input"
        );
        Checks.equals(4, inventory.available(),
            "Conflicting identities must not allocate more inventory");
        Checks.equals(1, inventory.allocationEffects(),
            "Conflicting identities must not add effects");

        ReservationFlow.ReservationService reservations =
            new ReservationFlow.ReservationService(1);
        ReservationFlow.CommandResult command =
            reservations.submit("op-terminal", "corr-terminal", 1);
        ReservationFlow.Event invalid = new ReservationFlow.Event(
            "inventory-invalid",
            ReservationFlow.Kind.INVENTORY_ACCEPTED,
            command.reservationId(),
            1,
            1,
            "wrong-correlation",
            "reservation-requested-" + command.reservationId()
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> reservations.applyInventoryResult(invalid),
            "Invalid causation input must be rejected before it is claimed"
        );

        ReservationFlow.Event accepted = new ReservationFlow.Event(
            "inventory-accepted",
            ReservationFlow.Kind.INVENTORY_ACCEPTED,
            command.reservationId(),
            1,
            1,
            "corr-terminal",
            "reservation-requested-" + command.reservationId()
        );
        reservations.applyInventoryResult(accepted);
        Checks.equals(ReservationFlow.Status.ACCEPTED,
            reservations.status(command.reservationId()),
            "A later valid result must still be applicable");

        ReservationFlow.Event rejected = new ReservationFlow.Event(
            "inventory-rejected",
            ReservationFlow.Kind.INVENTORY_REJECTED,
            command.reservationId(),
            1,
            1,
            "corr-terminal",
            "reservation-requested-" + command.reservationId()
        );
        Checks.throwsType(
            IllegalStateException.class,
            () -> reservations.applyInventoryResult(rejected),
            "A contradictory terminal transition must be rejected"
        );
        Checks.equals(ReservationFlow.Status.ACCEPTED,
            reservations.status(command.reservationId()),
            "A contradictory result must not alter authority");
    }

    private static void rejectionAndPendingStatesHaveDistinctConvergenceMeaning() {
        ReservationFlow.SystemUnderTest rejected =
            new ReservationFlow.SystemUnderTest(2, 0);
        ReservationFlow.CommandResult rejectedCommand =
            rejected.submit("op-rejected", "corr-rejected", 1);
        rejected.reconcile();
        Checks.equals(ReservationFlow.Status.REJECTED,
            rejected.reservations().status(rejectedCommand.reservationId()),
            "Insufficient inventory must become an authoritative rejection");
        Checks.equals(0, rejected.inventory().allocationEffects(),
            "Rejected inventory must not create an allocation effect");
        Checks.isTrue(rejected.converged(rejectedCommand.reservationId()),
            "Matching terminal rejection with an empty outbox is convergence");

        ReservationFlow.SystemUnderTest pending =
            new ReservationFlow.SystemUnderTest(2, 1);
        ReservationFlow.CommandResult pendingCommand =
            pending.submit("op-pending", "corr-pending", 1);
        pending.publishPending(false);
        pending.query().consume(pending.brokerMessages().get(0));
        Checks.equals(ReservationFlow.Status.PENDING,
            pending.reservations().status(pendingCommand.reservationId()),
            "Authority must remain pending before an inventory result");
        Checks.equals(ReservationFlow.Status.PENDING,
            pending.query().status(pendingCommand.reservationId()),
            "The creation projection must also be pending");
        Checks.equals(0, pending.reservations().pendingOutboxCount(),
            "The first event may already be published");
        Checks.isFalse(pending.converged(pendingCommand.reservationId()),
            "Matching PENDING states are not terminal convergence");
    }
}
