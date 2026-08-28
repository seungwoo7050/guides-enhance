package dev.guides.distributed.outbox;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

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

    // [Implementation 4] 소비자의 중복 처리 기록
    // Consumer는 전달 횟수와 별개로 처리한 이벤트 지문과 조회 모델 효과를 보관합니다.
    public static final class Consumer {
        private final Map<String, DomainEvent> processed = new HashMap<>();
        private final Set<String> projectedOrders = new HashSet<>();

        // [Implementation 4-1] 동일 재전달과 ID 충돌 구분
        // 동일 payload의 재전달은 무시하고 같은 ID의 다른 payload는 상태 변경 전에 거절합니다.
        public synchronized void onEvent(DomainEvent event) {
            DomainEvent previous = processed.get(event.eventId());
            if (previous != null) {
                if (!previous.equals(event)) {
                    throw new IllegalArgumentException(
                        "event ID was reused with different payload"
                    );
                }
                return;
            }
            processed.put(event.eventId(), event);
            projectedOrders.add(event.orderId());
        }

        public synchronized int effectCount() {
            return projectedOrders.size();
        }
    }

    // [Implementation 5] 브로커 가용성과 전달 횟수
    // Broker는 전송 가능 여부와 실제 전달 횟수만 기록하며 업무 효과 완료 여부는 판단하지 않습니다.
    public static final class Broker {
        private final Consumer consumer;
        private boolean available = true;
        private int deliveryCount;

        public Broker(Consumer consumer) {
            this.consumer = consumer;
        }

        public synchronized void setAvailable(boolean available) {
            this.available = available;
        }

        public synchronized void send(DomainEvent event) {
            if (!available) {
                throw new BrokerUnavailableException();
            }
            deliveryCount++;
            consumer.onEvent(event);
        }

        public synchronized int deliveryCount() {
            return deliveryCount;
        }
    }

    // [Implementation 6] 미발행 Outbox 처리
    // Publisher는 Database의 미발행 행을 Broker로 보내고 성공한 건만 완료로 표시합니다.
    public static final class Publisher {
        private final Database database;
        private final Broker broker;

        public Publisher(Database database, Broker broker) {
            this.database = database;
            this.broker = broker;
        }

        // [Implementation 6-1] 전송 후 완료 표시 전 중단
        // send를 먼저 호출해 전송 성공 뒤 프로세스가 멈추면 같은 이벤트가 다시 전달될 수 있게 합니다.
        public boolean publishNext(boolean crashAfterSend) {
            List<OutboxRow> pending = database.pending();
            if (pending.isEmpty()) {
                return false;
            }

            OutboxRow row = pending.get(0);
            row.recordAttempt();
            broker.send(row.event());

            if (crashAfterSend) {
                throw new SimulatedCrashException();
            }

            row.markPublished();
            return true;
        }

        // [Implementation 6-2] 미발행 행 재처리
        // 브로커 장애에서는 미발행 상태를 남기고 종료해 다음 실행이 같은 행부터 이어받습니다.
        public void reconcile() {
            while (true) {
                try {
                    if (!publishNext(false)) {
                        return;
                    }
                } catch (BrokerUnavailableException unavailable) {
                    return;
                }
            }
        }
    }
}
