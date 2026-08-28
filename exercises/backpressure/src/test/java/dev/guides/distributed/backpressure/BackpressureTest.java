package dev.guides.distributed.backpressure;
import dev.guides.distributed.testing.Checks;
public final class BackpressureTest {
public static void main(String[] args) {
var lane = new Backpressure.Lane(1, 1, Long.MAX_VALUE);
Checks.equals(Backpressure.Admission.STARTED, lane.submit("a", 0, 100), "First starts");
Checks.equals(Backpressure.Admission.QUEUED, lane.submit("b", 0, 100), "Second waits");
Checks.equals(Backpressure.Admission.REJECTED, lane.submit("c", 0, 100), "Bounded capacity");
Checks.throwsType(IllegalArgumentException.class, () -> lane.submit("a", 0, 100), "Duplicate ID");
Checks.equals(Backpressure.Admission.REJECTED, new Backpressure.Lane(1, 0, 100).submit("expired", 10, 10), "Deadline admission");
System.out.println("stage tests passed");
}

}
