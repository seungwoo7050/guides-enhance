package dev.guides.distributed.outbox;

import dev.guides.distributed.testing.Checks;

public final class OutboxReconciliationTest {
    public static void main(String[] args) {
        stateAndOutboxAreCreatedTogether();
        brokerFailureLeavesPendingWork();
        crashAfterPublishCanBeReconciledWithoutDuplicateEffect();
        conflictingIdentifiersAreRejected();
        System.out.println("outbox-reconciliation tests passed");
    }

    private static void stateAndOutboxAreCreatedTogether() {
        OutboxReconciliation.Database database = new OutboxReconciliation.Database();
        database.createOrder("order-1", "event-1");

        Checks.equals(1, database.orderCount(), "Order state must be committed");
        Checks.equals(1, database.outboxCount(), "The same commit must create an Outbox row");
        Checks.equals(1, database.pending().size(), "A new Outbox row must be pending");
    }

    private static void brokerFailureLeavesPendingWork() {
        OutboxReconciliation.Database database = new OutboxReconciliation.Database();
        OutboxReconciliation.Consumer consumer = new OutboxReconciliation.Consumer();
        OutboxReconciliation.Broker broker = new OutboxReconciliation.Broker(consumer);
        OutboxReconciliation.Publisher publisher =
            new OutboxReconciliation.Publisher(database, broker);

        database.createOrder("order-2", "event-2");
        broker.setAvailable(false);

        Checks.throwsType(
            OutboxReconciliation.BrokerUnavailableException.class,
            () -> publisher.publishNext(false),
            "Broker failure must remain visible"
        );
        Checks.equals(1, database.pending().size(), "A failed send must remain pending");
        Checks.equals(0, consumer.effectCount(), "An undelivered event must not create an effect");
    }

    private static void crashAfterPublishCanBeReconciledWithoutDuplicateEffect() {
        OutboxReconciliation.Database database = new OutboxReconciliation.Database();
        OutboxReconciliation.Consumer consumer = new OutboxReconciliation.Consumer();
        OutboxReconciliation.Broker broker = new OutboxReconciliation.Broker(consumer);
        OutboxReconciliation.Publisher publisher =
            new OutboxReconciliation.Publisher(database, broker);

        database.createOrder("order-3", "event-3");

        Checks.throwsType(
            OutboxReconciliation.SimulatedCrashException.class,
            () -> publisher.publishNext(true),
            "The send-before-ack crash window must be reproducible"
        );
        Checks.equals(1, database.pending().size(), "An unacknowledged row must be retried");
        Checks.equals(1, consumer.effectCount(), "The first delivery effect must remain committed");

        publisher.reconcile();

        Checks.equals(0, database.pending().size(), "Reconciliation must finish the row");
        Checks.equals(2, broker.deliveryCount(), "The logical event must be redelivered");
        Checks.equals(1, consumer.effectCount(), "Redelivery must preserve one business effect");
    }

    private static void conflictingIdentifiersAreRejected() {
        OutboxReconciliation.Database database = new OutboxReconciliation.Database();
        database.createOrder("order-conflict", "event-original");
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> database.createOrder("order-conflict", "event-other"),
            "An order cannot be rebound to another event"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> database.createOrder("order-other", "event-original"),
            "An event cannot be rebound to another order"
        );
        Checks.equals(1, database.orderCount(), "Identifier conflicts must not create orders");
        Checks.equals(1, database.outboxCount(), "Identifier conflicts must not create rows");

        OutboxReconciliation.Consumer consumer = new OutboxReconciliation.Consumer();
        consumer.onEvent(new OutboxReconciliation.DomainEvent("event-c", "order-a"));
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> consumer.onEvent(new OutboxReconciliation.DomainEvent("event-c", "order-b")),
            "A duplicate ID cannot hide a conflicting payload"
        );
        Checks.equals(1, consumer.effectCount(), "A conflict must not add an effect");
    }
}
