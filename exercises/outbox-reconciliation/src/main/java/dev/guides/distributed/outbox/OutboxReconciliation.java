package dev.guides.distributed.outbox;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class OutboxReconciliation {
    // [Implementation 1] 업무 이벤트 식별자
    // DomainEvent는 논리적 event ID와 대상 order ID를 함께 보관합니다.
    public record DomainEvent(String eventId, String orderId) {
    }

    public static final class SimulatedCrashException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public SimulatedCrashException() {
            super("crash after publish and before outbox acknowledgement");
        }
    }

    public static final class BrokerUnavailableException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public BrokerUnavailableException() {
            super("broker unavailable");
        }
    }

    // [Implementation 2] Outbox 행의 발행 상태
    // OutboxRow가 이벤트 하나의 발행 완료 여부와 시도 횟수를 보관합니다.
    public static final class OutboxRow {
        private final DomainEvent event;
        private boolean published;
        private int attempts;

        private OutboxRow(DomainEvent event) {
            this.event = event;
        }

        public DomainEvent event() {
            return event;
        }

        public boolean published() {
            return published;
        }

        public int attempts() {
            return attempts;
        }

        private void recordAttempt() {
            attempts++;
        }

        private void markPublished() {
            published = true;
        }
    }

    // [Implementation 3] 주문과 Outbox 함께 저장
    // Database가 주문 상태와 대응 이벤트, Outbox 행을 같은 synchronized 작업에서 생성합니다.
    public static final class Database {
        private final Map<String, String> orders = new HashMap<>();
        private final Map<String, String> eventByOrder = new HashMap<>();
        private final Map<String, DomainEvent> eventsById = new HashMap<>();
        private final List<OutboxRow> outbox = new ArrayList<>();

        // [Implementation 3-1] 주문·이벤트 ID 양방향 검증
        // 새 상태를 만들기 전에 order ID와 event ID가 서로 다른 대상을 가리키지 않는지 확인합니다.
        public synchronized void createOrder(String orderId, String eventId) {
            if (orderId == null || orderId.isBlank()
                || eventId == null || eventId.isBlank()) {
                throw new IllegalArgumentException("order and event IDs are required");
            }
            DomainEvent candidate = new DomainEvent(eventId, orderId);
            DomainEvent claimedEvent = eventsById.get(eventId);
            if (claimedEvent != null && !claimedEvent.equals(candidate)) {
                throw new IllegalArgumentException(
                    "event ID was reused by a different order"
                );
            }
            if (orders.containsKey(orderId)) {
                if (!eventId.equals(eventByOrder.get(orderId))) {
                    throw new IllegalArgumentException(
                        "order ID was reused with a different event ID"
                    );
                }
                return;
            }
            orders.put(orderId, "CREATED");
            eventByOrder.put(orderId, eventId);
            eventsById.put(eventId, candidate);
            outbox.add(new OutboxRow(candidate));
        }

        public synchronized List<OutboxRow> pending() {
            return outbox.stream().filter(row -> !row.published()).toList();
        }

        public synchronized int orderCount() {
            return orders.size();
        }

        public synchronized int outboxCount() {
            return outbox.size();
        }
    }
}
