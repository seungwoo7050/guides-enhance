package dev.guides.distributed.duplicate;

import java.util.HashMap;
import java.util.Map;

public final class DuplicateDelivery {
    // [Implementation 1] 이벤트 식별자와 입력 값
    // event ID를 전체 업무 입력과 함께 비교해야 같은 ID에 다른 payload가 들어오는 충돌을 찾을 수 있습니다.
    public record Event(String eventId, String accountId, int amount) {
    }

    public static final class SimulatedCrashException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public SimulatedCrashException() {
            super("crash after commit and before acknowledgement");
        }
    }

    // [Implementation 2] 잔액·처리 결과·입력 지문 저장
    // EffectStore가 잔액 변경과 중복 판정 자료를 함께 보관해 둘 중 하나만 저장되는 상태를 막습니다.
    public static final class EffectStore {
        private final Map<String, Integer> balances = new HashMap<>();
        private final Map<String, Integer> appliedEvents = new HashMap<>();
        private final Map<String, Event> appliedInputs = new HashMap<>();

        // [Implementation 2-1] 이벤트 효과 한 번만 적용
        // 동일한 재전달에는 저장된 결과를 반환하고 처음 본 이벤트에서만 세 Map을 갱신합니다.
        public synchronized int applyOnce(Event event) {
            Integer previous = appliedEvents.get(event.eventId());
            if (previous != null) {
                if (!event.equals(appliedInputs.get(event.eventId()))) {
                    throw new IllegalArgumentException(
                        "event ID was reused with different payload"
                    );
                }
                return previous;
            }

            int updated = balances.getOrDefault(event.accountId(), 0) + event.amount();
            balances.put(event.accountId(), updated);
            appliedEvents.put(event.eventId(), updated);
            appliedInputs.put(event.eventId(), event);
            return updated;
        }

        public synchronized int balance(String accountId) {
            return balances.getOrDefault(accountId, 0);
        }

        public synchronized int appliedEventCount() {
            return appliedEvents.size();
        }
    }

    // [Implementation 3] 전달 시도와 저장 처리 연결
    // Handler는 전달 횟수와 EffectStore의 업무 효과 횟수가 다를 수 있음을 드러냅니다.
    public static final class Handler {
        private final EffectStore store;

        public Handler(EffectStore store) {
            this.store = store;
        }

        // [Implementation 3-1] 저장 후 ACK 유실 재현
        // 상태 저장 뒤 ACK 전에 중단되므로 재전달은 applyOnce에서 기존 결과로 수렴해야 합니다.
        public int handle(Event event, boolean crashAfterCommit) {
            int result = store.applyOnce(event);
            if (crashAfterCommit) {
                throw new SimulatedCrashException();
            }
            return result;
        }
    }

    private DuplicateDelivery() {
    }
}
