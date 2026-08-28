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
}
