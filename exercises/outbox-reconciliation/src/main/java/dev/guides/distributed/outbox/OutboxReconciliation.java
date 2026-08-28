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

    // [Implementation 7] Saga 진행 상태
    // 정방향 처리, 보상 중, 완료와 취소를 구분해 아직 끝나지 않은 작업을 숨기지 않습니다.
    public enum SagaState {
        STARTED,
        INVENTORY_RESERVED,
        COMPENSATING,
        COMPLETED,
        CANCELLED
    }

    public static final class PaymentRejectedException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public PaymentRejectedException() {
            super("payment rejected");
        }
    }

    public static final class CompensationUnavailableException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public CompensationUnavailableException() {
            super("inventory compensation unavailable");
        }
    }

    // [Implementation 8] 재고 예약과 보상 상태
    // InventoryParticipant가 가용 재고와 주문별 예약·해제 여부를 변경합니다.
    public static final class InventoryParticipant {
        private int available;
        private final Set<String> reservedOrders = new HashSet<>();
        private final Set<String> releasedOrders = new HashSet<>();
        private boolean releaseAvailable = true;
        private int releaseEffects;

        public InventoryParticipant(int available) {
            this.available = available;
        }

        // [Implementation 8-1] 주문별 재고 예약 한 번만 적용
        // 재고 부족으로 실패한 예약은 ID 선점을 되돌려 이후의 정상 재시도를 막지 않습니다.
        public void reserve(String orderId) {
            if (!reservedOrders.add(orderId)) {
                return;
            }
            if (available <= 0) {
                reservedOrders.remove(orderId);
                throw new IllegalStateException("inventory unavailable");
            }
            available--;
        }

        public void setReleaseAvailable(boolean releaseAvailable) {
            this.releaseAvailable = releaseAvailable;
        }

        // [Implementation 8-2] 실패 후 다시 시도할 수 있는 보상
        // 재고 해제가 성공한 뒤에만 완료를 기록해 외부 장애 시 재조정 근거를 남깁니다.
        public void release(String orderId) {
            if (!reservedOrders.contains(orderId) || releasedOrders.contains(orderId)) {
                return;
            }
            if (!releaseAvailable) {
                throw new CompensationUnavailableException();
            }
            releasedOrders.add(orderId);
            available++;
            releaseEffects++;
        }

        public int available() {
            return available;
        }

        public int releaseEffects() {
            return releaseEffects;
        }
    }

    // [Implementation 9] 결제 승인·거절 재현
    // PaymentParticipant는 Saga가 호출하는 결제 승인 결과만 제공합니다.
    public static final class PaymentParticipant {
        private boolean accept;

        public PaymentParticipant(boolean accept) {
            this.accept = accept;
        }

        public void setAccept(boolean accept) {
            this.accept = accept;
        }

        public void charge(String orderId) {
            if (!accept) {
                throw new PaymentRejectedException();
            }
        }
    }

    // [Implementation 10] 주문 Saga 실행 상태
    // OrderSaga가 주문별 현재 상태와 재고·결제 호출 순서를 보관합니다.
    public static final class OrderSaga {
        private final String orderId;
        private final InventoryParticipant inventory;
        private final PaymentParticipant payment;
        private SagaState state = SagaState.STARTED;

        public OrderSaga(
            String orderId,
            InventoryParticipant inventory,
            PaymentParticipant payment
        ) {
            this.orderId = orderId;
            this.inventory = inventory;
            this.payment = payment;
        }

        // [Implementation 10-1] 정방향 처리와 보상 전환
        // 결제가 거절되면 먼저 COMPENSATING을 기록한 뒤 재고 해제를 시도합니다.
        public void execute() {
            if (state == SagaState.COMPLETED || state == SagaState.CANCELLED) {
                return;
            }
            inventory.reserve(orderId);
            state = SagaState.INVENTORY_RESERVED;
            try {
                payment.charge(orderId);
                state = SagaState.COMPLETED;
            } catch (PaymentRejectedException rejection) {
                state = SagaState.COMPENSATING;
                compensate();
            }
        }

        // [Implementation 10-2] 미완료 보상 재시도
        // COMPENSATING 상태에 남은 주문만 다시 보상합니다.
        public void reconcile() {
            if (state == SagaState.COMPENSATING) {
                compensate();
            }
        }

        // [Implementation 10-3] 보상 성공 후 취소 확정
        // 재고 해제가 성공한 경우에만 Saga를 CANCELLED로 바꿉니다.
        private void compensate() {
            inventory.release(orderId);
            state = SagaState.CANCELLED;
        }

        public SagaState state() {
            return state;
        }
    }

    private OutboxReconciliation() {
    }
}
