package dev.guides.distributed.uncertain;

import dev.guides.distributed.testing.Checks;

public final class UncertainOutcomeTest {
    public static void main(String[] args) {
        responseLossDoesNotEraseCommittedResult();
        sameOperationReturnsSameEffect();
        conflictingInputIsRejected();
        System.out.println("uncertain-outcome tests passed");
    }

    private static void responseLossDoesNotEraseCommittedResult() {
        UncertainOutcome.Gateway gateway = new UncertainOutcome.Gateway();
        UncertainOutcome.Client client = new UncertainOutcome.Client(gateway);

        UncertainOutcome.Result result = client.reserve("op-1", 3, true);

        Checks.equals(
            UncertainOutcome.Status.ACCEPTED,
            result.status(),
            "A committed result must be recovered after response loss"
        );
        Checks.equals(1, gateway.effectCount(), "The business effect must occur once");
    }

    private static void sameOperationReturnsSameEffect() {
        UncertainOutcome.Gateway gateway = new UncertainOutcome.Gateway();
        UncertainOutcome.Client client = new UncertainOutcome.Client(gateway);

        UncertainOutcome.Result first = client.reserve("op-2", 2, false);
        UncertainOutcome.Result second = client.reserve("op-2", 2, false);

        Checks.equals(first, second, "A retry must return the existing result");
        Checks.equals(1, gateway.effectCount(), "A retry must not add another effect");
    }

    private static void conflictingInputIsRejected() {
        UncertainOutcome.Gateway gateway = new UncertainOutcome.Gateway();
        gateway.reserve("op-3", 1, false);

        Checks.throwsType(
            IllegalArgumentException.class,
            () -> gateway.reserve("op-3", 2, false),
            "An operation ID must remain bound to its original input"
        );
        Checks.equals(1, gateway.effectCount(), "Conflicting input must not mutate state");
    }
}
