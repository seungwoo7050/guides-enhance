package dev.guides.distributed.capstone;
import dev.guides.distributed.testing.Checks;
public final class ReservationFlowTest {
public static void main(String[] args) {
var service = new ReservationFlow.ReservationService(2);
var result = service.submit("op", "correlation", 1);
Checks.equals(result, service.submit("op", "correlation", 1), "Idempotent request");
Checks.equals(1, service.reservationCount(), "One reservation");
Checks.equals(1, service.pendingOutboxCount(), "Atomic outbox creation");
Checks.throwsType(IllegalArgumentException.class, () -> service.submit("op", "correlation", 2), "Conflicting input");
var inventory = new ReservationFlow.InventoryService(5);
var request = service.pendingOutbox().get(0);
var outcome = inventory.handle(request);
Checks.equals(outcome, inventory.handle(request), "Inventory deduplication");
Checks.equals(4, inventory.available(), "One allocation");
System.out.println("stage tests passed");
}

}
