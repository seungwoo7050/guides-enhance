package dev.guides.distributed.capstone;

import dev.guides.distributed.testing.Checks;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class ReservationFlowTest {
    public static void main(String[] args) {
        projectionOrderingSchemaAndTerminalRulesHold();
        conflictingIdentitiesAreRejectedBeforeMutation();
        System.out.println("reservation-flow tests passed");
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

}
