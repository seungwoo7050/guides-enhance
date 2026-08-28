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
var breaker = new RetryBudget.CircuitBreaker(1, 10, clock);
breaker.beforeCall(); breaker.recordTransientFailure();
Checks.equals(RetryBudget.CircuitBreaker.State.OPEN, breaker.state(), "Failure opens");
Checks.throwsType(RetryBudget.CircuitOpen.class, breaker::beforeCall, "Open rejection");
clock.advance(10); breaker.beforeCall();
Checks.equals(RetryBudget.CircuitBreaker.State.HALF_OPEN, breaker.state(), "Probe after window");
breaker.recordTransientFailure();
Checks.throwsType(RetryBudget.CircuitOpen.class, breaker::beforeCall, "Failed probe restarts window");
clock.advance(10); breaker.beforeCall(); breaker.recordSuccess();
Checks.equals(RetryBudget.CircuitBreaker.State.CLOSED, breaker.state(), "Successful probe closes");
System.out.println("stage tests passed");
}

}
