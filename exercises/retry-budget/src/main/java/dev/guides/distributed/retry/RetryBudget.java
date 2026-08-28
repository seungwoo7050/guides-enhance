package dev.guides.distributed.retry;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Queue;

public final class RetryBudget {
    // [Implementation 1] 실패 종류 구분
    // 업무 거절, 일시 장애, deadline 초과와 열린 Circuit Breaker를 서로 다른 예외로 표현합니다.
    public static final class TransientFailure extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public TransientFailure(String message) {
            super(message);
        }
    }

    public static final class BusinessRejection extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public BusinessRejection(String message) {
            super(message);
        }
    }

    public static final class DeadlineExceeded extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public DeadlineExceeded() {
            super("operation deadline exceeded");
        }
    }

    public static final class CircuitOpen extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public CircuitOpen() {
            super("circuit breaker is open");
        }
    }

    // [Implementation 2] 결정적 가상 시계
    // VirtualClock이 deadline과 backoff 계산에 사용할 시간을 직접 보관합니다.
    public static final class VirtualClock {
        private long nowMillis;

        public long nowMillis() {
            return nowMillis;
        }

        public void advance(long millis) {
            if (millis < 0) {
                throw new IllegalArgumentException("millis must not be negative");
            }
            nowMillis += millis;
        }
    }

    // [Implementation 3] 의존 서비스 호출
    // Dependency를 통해 operation ID가 재시도 사이에 유지되는지와 호출 결과를 관찰합니다.
    @FunctionalInterface
    public interface Dependency {
        String call(String operationId);
    }

    public static final class ScriptedDependency implements Dependency {
        private final Queue<Object> outcomes = new ArrayDeque<>();
        private final List<String> receivedOperationIds = new ArrayList<>();
        private int calls;

        public ScriptedDependency thenReturn(String value) {
            outcomes.add(value);
            return this;
        }

        public ScriptedDependency thenThrow(RuntimeException error) {
            outcomes.add(error);
            return this;
        }

        @Override
        public String call(String operationId) {
            calls++;
            receivedOperationIds.add(operationId);
            Object outcome = outcomes.remove();
            if (outcome instanceof RuntimeException error) {
                throw error;
            }
            return (String) outcome;
        }

        public int calls() {
            return calls;
        }

        public List<String> receivedOperationIds() {
            return List.copyOf(receivedOperationIds);
        }
    }

    // [Implementation 4] Circuit Breaker 상태
    // CircuitBreaker가 연속 일시 장애 수와 OPEN·HALF_OPEN probe 시각을 보관합니다.
    public static final class CircuitBreaker {
        public enum State {
            CLOSED,
            OPEN,
            HALF_OPEN
        }

        private final int failureThreshold;
        private final long openMillis;
        private final VirtualClock clock;
        private int consecutiveFailures;
        private long nextProbeAt;
        private State state = State.CLOSED;

        public CircuitBreaker(int failureThreshold) {
            this(failureThreshold, Long.MAX_VALUE, new VirtualClock());
        }

        public CircuitBreaker(int failureThreshold, long openMillis, VirtualClock clock) {
            if (failureThreshold <= 0) {
                throw new IllegalArgumentException("failureThreshold must be positive");
            }
            if (openMillis <= 0) {
                throw new IllegalArgumentException("openMillis must be positive");
            }
            this.failureThreshold = failureThreshold;
            this.openMillis = openMillis;
            this.clock = clock;
        }

        // [Implementation 4-1] OPEN 대기 시간과 HALF_OPEN probe
        // OPEN 시간이 끝난 경우에만 HALF_OPEN으로 바꾸고 probe 한 건을 허용합니다.
        public void beforeCall() {
            if (state == State.OPEN && clock.nowMillis() >= nextProbeAt) {
                state = State.HALF_OPEN;
            }
            if (state == State.OPEN) {
                throw new CircuitOpen();
            }
        }

        // [Implementation 4-2] 응답 후 실패 횟수 초기화
        // 업무 거절을 포함해 의존 서비스가 응답하면 일시 장애 횟수를 지우고 회로를 닫습니다.
        public void recordSuccess() {
            consecutiveFailures = 0;
            state = State.CLOSED;
        }

        // [Implementation 4-3] 일시 장애만 실패로 집계
        // TransientFailure만 횟수에 포함하고 실패한 probe에는 새 OPEN 시간을 설정합니다.
        public void recordTransientFailure() {
            consecutiveFailures++;
            if (state == State.HALF_OPEN || consecutiveFailures >= failureThreshold) {
                state = State.OPEN;
                nextProbeAt = clock.nowMillis() + openMillis;
            }
        }

        public boolean isOpen() {
            return state == State.OPEN;
        }

        public State state() {
            return state;
        }
    }

    // [Implementation 5] DLQ 재처리 입력
    // DeadLetter에 event ID, operation ID와 payload를 함께 보관합니다.
    public record DeadLetter(String eventId, String operationId, String payload) {
        public DeadLetter {
            if (eventId == null || eventId.isBlank()
                || operationId == null || operationId.isBlank()
                || payload == null || payload.isBlank()) {
                throw new IllegalArgumentException(
                    "dead letter event, operation, and payload are required"
                );
            }
        }
    }

    @FunctionalInterface
    public interface DeadLetterHandler {
        String replay(DeadLetter message);
    }

    // [Implementation 5-1] 재처리 성공 전까지 메시지 보존
    // DeadLetterQueue는 handler가 성공하기 전까지 원본 메시지를 제거하지 않습니다.
    public static final class DeadLetterQueue {
        private final Queue<DeadLetter> messages = new ArrayDeque<>();

        public void add(DeadLetter message) {
            messages.add(message);
        }

        // [Implementation 5-2] 재처리 성공 후 메시지 제거
        // handler가 값을 반환한 뒤에만 queue에서 메시지를 뺍니다.
        public String replayNext(DeadLetterHandler handler) {
            DeadLetter message = messages.element();
            String result = handler.replay(message);
            messages.remove();
            return result;
        }

        public int size() {
            return messages.size();
        }
    }

    // [Implementation 6] deadline 안에서 재시도 실행
    // Executor가 하나의 operation deadline 안에서 retry, backoff와 Circuit Breaker를 함께 적용합니다.
    public static final class Executor {
        private final VirtualClock clock;
        private final long backoffMillis;

        public Executor(VirtualClock clock, long backoffMillis) {
            if (backoffMillis <= 0) {
                throw new IllegalArgumentException("backoffMillis must be positive");
            }
            this.clock = clock;
            this.backoffMillis = backoffMillis;
        }

        // [Implementation 6-1] 같은 operation ID로 일시 장애만 재시도
        // 재시도할 때 operation ID를 바꾸지 않으며 TransientFailure 외의 결과는 반복하지 않습니다.
        public String execute(
            String operationId,
            long deadlineMillis,
            Dependency dependency,
            CircuitBreaker breaker
        ) {
            while (true) {
                if (clock.nowMillis() >= deadlineMillis) {
                    throw new DeadlineExceeded();
                }

                breaker.beforeCall();
                try {
                    String result = dependency.call(operationId);
                    breaker.recordSuccess();
                    return result;
                } catch (BusinessRejection rejection) {
                    breaker.recordSuccess();
                    throw rejection;
                } catch (TransientFailure transientFailure) {
                    breaker.recordTransientFailure();
                    if (breaker.isOpen()) {
                        throw new CircuitOpen();
                    }
                    if (clock.nowMillis() + backoffMillis >= deadlineMillis) {
                        throw new DeadlineExceeded();
                    }
                    clock.advance(backoffMillis);
                }
            }
        }
    }

    private RetryBudget() {
    }
}
