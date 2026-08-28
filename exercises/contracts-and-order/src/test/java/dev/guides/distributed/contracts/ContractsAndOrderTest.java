package dev.guides.distributed.contracts;
import dev.guides.distributed.testing.Checks;
public final class ContractsAndOrderTest {
public static void main(String[] args) {
var projection = new ContractsAndOrder.Projection("orders", 2);
var event = new ContractsAndOrder.Event("orders", 2, "e1", "a1", 2, "pending");
Checks.equals(ContractsAndOrder.Outcome.BUFFERED, projection.onEvent(event), "Gap must be retained");
Checks.equals(ContractsAndOrder.Outcome.DUPLICATE, projection.onEvent(event), "Duplicate must not add work");
Checks.equals(1, projection.bufferedCount("a1"), "One pending event");
Checks.throwsType(ContractsAndOrder.ContractViolationException.class, () -> projection.onEvent(new ContractsAndOrder.Event("orders", 2, "e2", "a1", 2, "other")), "Sequence ownership");
Checks.throwsType(ContractsAndOrder.ContractViolationException.class, () -> projection.onEvent(new ContractsAndOrder.Event("wrong", 2, "e3", "a1", 3, "other")), "Channel contract");
Checks.equals(ContractsAndOrder.Outcome.ISOLATED, projection.onEvent(new ContractsAndOrder.Event("orders", 3, "e4", "a1", 4, "other")), "Future schema isolation");
System.out.println("stage tests passed");
}

}
