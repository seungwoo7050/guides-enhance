package dev.guides.distributed.outbox;

import dev.guides.distributed.testing.Checks;

public final class OutboxReconciliationTest {
    public static void main(String[] args) {
        stateAndOutboxAreCreatedTogether();
        System.out.println("outbox-reconciliation tests passed");
    }

    private static void stateAndOutboxAreCreatedTogether() {
        OutboxReconciliation.Database database = new OutboxReconciliation.Database();
        database.createOrder("order-1", "event-1");

        Checks.equals(1, database.orderCount(), "Order state must be committed");
        Checks.equals(1, database.outboxCount(), "The same commit must create an Outbox row");
        Checks.equals(1, database.pending().size(), "A new Outbox row must be pending");
    }

}
