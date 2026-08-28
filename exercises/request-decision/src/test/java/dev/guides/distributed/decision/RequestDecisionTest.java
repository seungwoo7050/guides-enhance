package dev.guides.distributed.decision;

import dev.guides.distributed.testing.Checks;

public final class RequestDecisionTest {
    public static void main(String[] args) {
        synchronousDenialDoesNotChangeCapacity();
        unavailablePolicyDoesNotChangeCapacity();
        asynchronousAcceptanceOnlyPromisesOwnership();
        operationIdentityIsIdempotentAndPayloadBound();
        System.out.println("request-decision tests passed");
    }

    private static void synchronousDenialDoesNotChangeCapacity() {
        RequestDecision.CapacityLedger ledger = new RequestDecision.CapacityLedger();
        RequestDecision.Coordinator coordinator = new RequestDecision.Coordinator(ledger);

        RequestDecision.Decision decision = coordinator.submit(
            new RequestDecision.Request("deny-1", 4),
            RequestDecision.Mode.SYNCHRONOUS,
            ignored -> RequestDecision.PolicyResult.DENY
        );

        Checks.equals(RequestDecision.Status.REJECTED, decision.status(), "Denial must reject");
        Checks.equals(0, ledger.reserved(), "A denied request must not reserve capacity");
    }

    private static void unavailablePolicyDoesNotChangeCapacity() {
        RequestDecision.CapacityLedger ledger = new RequestDecision.CapacityLedger();
        RequestDecision.Coordinator coordinator = new RequestDecision.Coordinator(ledger);

        RequestDecision.Decision decision = coordinator.submit(
            new RequestDecision.Request("down-1", 2),
            RequestDecision.Mode.SYNCHRONOUS,
            ignored -> RequestDecision.PolicyResult.UNAVAILABLE
        );

        Checks.equals(
            RequestDecision.Status.REJECTED,
            decision.status(),
            "An unavailable policy must fail closed"
        );
        Checks.equals(0, ledger.reserved(), "Policy failure must not mutate capacity");
    }

    private static void asynchronousAcceptanceOnlyPromisesOwnership() {
        RequestDecision.CapacityLedger ledger = new RequestDecision.CapacityLedger();
        RequestDecision.Coordinator coordinator = new RequestDecision.Coordinator(ledger);
        RequestDecision.Request request = new RequestDecision.Request("async-1", 3);

        RequestDecision.Decision queued = coordinator.submit(
            request,
            RequestDecision.Mode.ASYNCHRONOUS,
            ignored -> RequestDecision.PolicyResult.ALLOW
        );

        Checks.equals(RequestDecision.Status.PENDING, queued.status(), "Admission must be pending");
        Checks.equals(0, ledger.reserved(), "Queue ownership alone must not reserve capacity");
        Checks.equals(1, coordinator.pendingCount(), "The queued request must remain owned");

        RequestDecision.Decision completed = coordinator.processNext(
            ignored -> RequestDecision.PolicyResult.ALLOW
        );
        Checks.equals(RequestDecision.Status.ACCEPTED, completed.status(), "Processing must finalize");
        Checks.equals(3, ledger.reserved(), "Only an allowed result may reserve capacity");
    }

    private static void operationIdentityIsIdempotentAndPayloadBound() {
        RequestDecision.CapacityLedger ledger = new RequestDecision.CapacityLedger();
        RequestDecision.Coordinator coordinator = new RequestDecision.Coordinator(ledger);
        RequestDecision.Request request = new RequestDecision.Request("same-operation", 2);
        int[] policyCalls = {0};
        RequestDecision.Policy allow = ignored -> {
            policyCalls[0]++;
            return RequestDecision.PolicyResult.ALLOW;
        };

        RequestDecision.Decision first = coordinator.submit(
            request,
            RequestDecision.Mode.SYNCHRONOUS,
            allow
        );
        RequestDecision.Decision retry = coordinator.submit(
            request,
            RequestDecision.Mode.SYNCHRONOUS,
            allow
        );
        Checks.equals(first, retry, "A matching retry must return the existing result");
        Checks.equals(1, policyCalls[0], "A matching retry must not re-run policy");
        Checks.equals(2, ledger.reserved(), "A matching retry must preserve one effect");

        Checks.throwsType(
            IllegalArgumentException.class,
            () -> coordinator.submit(
                new RequestDecision.Request("same-operation", 3),
                RequestDecision.Mode.SYNCHRONOUS,
                allow
            ),
            "An operation ID cannot be rebound to another quantity"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> coordinator.submit(request, RequestDecision.Mode.ASYNCHRONOUS, allow),
            "An operation ID cannot be rebound to another mode"
        );
        Checks.equals(1, policyCalls[0], "Conflicts must fail before policy execution");
        Checks.equals(2, ledger.reserved(), "Conflicts must not mutate capacity");
    }
}
