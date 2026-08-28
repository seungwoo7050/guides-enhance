package dev.guides.distributed.retry;
import dev.guides.distributed.testing.Checks;
import java.util.List;
public final class RetryBudgetTest {
public static void main(String[] args) {
var clock = new RetryBudget.VirtualClock();
clock.advance(5);
Checks.equals(5L, clock.nowMillis(), "Deterministic time");
Checks.throwsType(IllegalArgumentException.class, () -> clock.advance(-1), "No reverse time");
var dependency = new RetryBudget.ScriptedDependency().thenThrow(new RetryBudget.TransientFailure("temporary")).thenReturn("ok");
Checks.throwsType(RetryBudget.TransientFailure.class, () -> dependency.call("op"), "Failure classification");
Checks.equals("ok", dependency.call("op"), "Scripted response");
Checks.equals(List.of("op", "op"), dependency.receivedOperationIds(), "Operation identity");
System.out.println("stage tests passed");
}

}
