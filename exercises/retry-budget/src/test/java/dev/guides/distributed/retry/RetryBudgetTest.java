package dev.guides.distributed.retry;

import dev.guides.distributed.testing.Checks;
import java.util.ArrayList;
import java.util.List;

public final class RetryBudgetTest {
    public static void main(String[] args) {
        transientFailureUsesSameOperationId();
        businessRejectionIsNotRetried();
        nextBackoffCannotCrossDeadline();
        circuitBreakerStopsNewCalls();
        halfOpenProbeAndDlqReplayPreserveContracts();
        failedHalfOpenProbeStartsANewOpenWindow();
        nonPositiveBackoffIsRejected();
        halfOpenBusinessRejectionClosesBreaker();
        System.out.println("retry-budget tests passed");
    }

    private static void transientFailureUsesSameOperationId() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("temporary"))
            .thenReturn("accepted");
        RetryBudget.CircuitBreaker breaker = new RetryBudget.CircuitBreaker(3);

        String result = new RetryBudget.Executor(clock, 10)
            .execute("op-1", 100, dependency, breaker);

        Checks.equals("accepted", result, "A transient retry must return the eventual result");
        Checks.equals(
            List.of("op-1", "op-1"),
            dependency.receivedOperationIds(),
            "Retries must preserve operation identity"
        );
        Checks.equals(10L, clock.nowMillis(), "Only the configured backoff may elapse");
    }

    private static void businessRejectionIsNotRetried() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.BusinessRejection("insufficient capacity"))
            .thenReturn("should-not-run");
        RetryBudget.CircuitBreaker breaker = new RetryBudget.CircuitBreaker(3);

        Checks.throwsType(
            RetryBudget.BusinessRejection.class,
            () -> new RetryBudget.Executor(clock, 10)
                .execute("op-2", 100, dependency, breaker),
            "Business rejection must return immediately"
        );
        Checks.equals(1, dependency.calls(), "Business rejection must not retry");
        Checks.isFalse(breaker.isOpen(), "Business rejection is not a breaker failure sample");
    }

    private static void nextBackoffCannotCrossDeadline() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("slow"))
            .thenReturn("too-late");
        RetryBudget.CircuitBreaker breaker = new RetryBudget.CircuitBreaker(3);

        Checks.throwsType(
            RetryBudget.DeadlineExceeded.class,
            () -> new RetryBudget.Executor(clock, 20)
                .execute("op-3", 15, dependency, breaker),
            "A backoff that reaches the deadline must stop the operation"
        );
        Checks.equals(1, dependency.calls(), "No call may start outside the deadline");
        Checks.equals(0L, clock.nowMillis(), "Unused backoff must not advance time");
    }

    private static void circuitBreakerStopsNewCalls() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("down-1"))
            .thenThrow(new RetryBudget.TransientFailure("down-2"))
            .thenReturn("must-not-run");
        RetryBudget.CircuitBreaker breaker = new RetryBudget.CircuitBreaker(2);
        RetryBudget.Executor executor = new RetryBudget.Executor(clock, 1);

        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-4", 100, dependency, breaker),
            "The breaker must open after the failure threshold"
        );
        int callsBefore = dependency.calls();
        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-5", 100, dependency, breaker),
            "An open breaker must reject new calls"
        );
        Checks.equals(callsBefore, dependency.calls(), "Open admission must not call the dependency");
    }

    private static void halfOpenProbeAndDlqReplayPreserveContracts() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.CircuitBreaker breaker = new RetryBudget.CircuitBreaker(1, 20, clock);
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("down"))
            .thenReturn("recovered");
        RetryBudget.Executor executor = new RetryBudget.Executor(clock, 1);

        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-probe", 100, dependency, breaker),
            "The initial failure must open the breaker"
        );
        clock.advance(20);
        Checks.equals(
            "recovered",
            executor.execute("op-probe", 100, dependency, breaker),
            "An expired open window must allow a recovery probe"
        );
        Checks.equals(
            RetryBudget.CircuitBreaker.State.CLOSED,
            breaker.state(),
            "A successful probe must close the breaker"
        );

        RetryBudget.DeadLetterQueue dlq = new RetryBudget.DeadLetterQueue();
        RetryBudget.DeadLetter message =
            new RetryBudget.DeadLetter("event-dlq", "op-dlq", "reservation");
        dlq.add(message);
        Checks.throwsType(
            RetryBudget.TransientFailure.class,
            () -> dlq.replayNext(ignored -> {
                throw new RetryBudget.TransientFailure("still unavailable");
            }),
            "Failed replay must retain the original message"
        );
        Checks.equals(1, dlq.size(), "Failed replay must not remove the message");

        List<RetryBudget.DeadLetter> replayed = new ArrayList<>();
        Checks.equals(
            "replayed",
            dlq.replayNext(replayedMessage -> {
                replayed.add(replayedMessage);
                return "replayed";
            }),
            "The message must replay successfully"
        );
        Checks.equals(List.of(message), replayed, "Replay must preserve the full identity tuple");
        Checks.equals(0, dlq.size(), "Successful replay must remove the message");
    }

    private static void failedHalfOpenProbeStartsANewOpenWindow() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.CircuitBreaker breaker = new RetryBudget.CircuitBreaker(1, 20, clock);
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("initial outage"))
            .thenThrow(new RetryBudget.TransientFailure("probe still failing"))
            .thenReturn("recovered later");
        RetryBudget.Executor executor = new RetryBudget.Executor(clock, 1);

        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-window", 100, dependency, breaker),
            "The first failure must open the breaker"
        );
        clock.advance(20);
        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-window", 100, dependency, breaker),
            "A failed half-open probe must reopen the breaker"
        );
        clock.advance(19);
        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-window", 100, dependency, breaker),
            "The new open window must be enforced"
        );
        Checks.equals(2, dependency.calls(), "No dependency call may occur inside the new window");
        clock.advance(1);
        Checks.equals(
            "recovered later",
            executor.execute("op-window", 100, dependency, breaker),
            "A later probe must be admitted"
        );
    }

    private static void nonPositiveBackoffIsRejected() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> new RetryBudget.Executor(clock, 0),
            "Backoff must be positive"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> new RetryBudget.Executor(clock, -1),
            "Negative backoff must be rejected"
        );
    }

    private static void halfOpenBusinessRejectionClosesBreaker() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.CircuitBreaker breaker = new RetryBudget.CircuitBreaker(1, 20, clock);
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("initial outage"))
            .thenThrow(new RetryBudget.BusinessRejection("capacity unavailable"));
        RetryBudget.Executor executor = new RetryBudget.Executor(clock, 1);

        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-business-probe", 100, dependency, breaker),
            "The transient failure must open the breaker"
        );
        clock.advance(20);
        Checks.throwsType(
            RetryBudget.BusinessRejection.class,
            () -> executor.execute("op-business-probe", 100, dependency, breaker),
            "A business response must propagate to the caller"
        );
        Checks.equals(
            RetryBudget.CircuitBreaker.State.CLOSED,
            breaker.state(),
            "A business response proves dependency availability and closes the breaker"
        );
    }
}
