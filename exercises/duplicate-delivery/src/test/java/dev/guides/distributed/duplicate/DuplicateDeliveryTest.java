package dev.guides.distributed.duplicate;

import dev.guides.distributed.testing.Checks;

public final class DuplicateDeliveryTest {
    public static void main(String[] args) {
        redeliveryAfterCrashKeepsOneEffect();
        differentEventsRemainIndependent();
        reusedIdWithDifferentPayloadIsRejected();
        System.out.println("duplicate-delivery tests passed");
    }

    private static void redeliveryAfterCrashKeepsOneEffect() {
        DuplicateDelivery.EffectStore store = new DuplicateDelivery.EffectStore();
        DuplicateDelivery.Handler handler = new DuplicateDelivery.Handler(store);
        DuplicateDelivery.Event event =
            new DuplicateDelivery.Event("event-1", "account-1", 7);

        Checks.throwsType(
            DuplicateDelivery.SimulatedCrashException.class,
            () -> handler.handle(event, true),
            "The first delivery must stop after commit"
        );
        int replayResult = handler.handle(event, false);

        Checks.equals(7, replayResult, "Redelivery must return the prior result");
        Checks.equals(7, store.balance("account-1"), "The balance effect must occur once");
        Checks.equals(1, store.appliedEventCount(), "Only one event claim must exist");
    }

    private static void differentEventsRemainIndependent() {
        DuplicateDelivery.EffectStore store = new DuplicateDelivery.EffectStore();
        DuplicateDelivery.Handler handler = new DuplicateDelivery.Handler(store);

        handler.handle(new DuplicateDelivery.Event("event-a", "account-2", 3), false);
        handler.handle(new DuplicateDelivery.Event("event-b", "account-2", 4), false);

        Checks.equals(7, store.balance("account-2"), "Distinct events must both apply");
        Checks.equals(2, store.appliedEventCount(), "Distinct event IDs must remain independent");
    }

    private static void reusedIdWithDifferentPayloadIsRejected() {
        DuplicateDelivery.EffectStore store = new DuplicateDelivery.EffectStore();
        DuplicateDelivery.Handler handler = new DuplicateDelivery.Handler(store);
        handler.handle(new DuplicateDelivery.Event("event-c", "account-3", 5), false);

        Checks.throwsType(
            IllegalArgumentException.class,
            () -> handler.handle(
                new DuplicateDelivery.Event("event-c", "account-3", 9),
                false
            ),
            "The same event ID cannot hide a different payload"
        );
        Checks.equals(5, store.balance("account-3"), "A conflict must not mutate the balance");
        Checks.equals(1, store.appliedEventCount(), "A conflict must not add a claim");
    }
}
