package dev.guides.distributed.capstone;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.OptionalLong;

public final class ReservationFlow {
    // [Implementation 1] 서비스 간 공유 상태와 이벤트
    // 명령 결과, 예약 상태, 이벤트, 재조정 결과와 관찰값을 서비스 사이에서 같은 의미로 사용합니다.
    public enum Status {
        PENDING,
        UNKNOWN,
        ACCEPTED,
        REJECTED
    }

    public enum Kind {
        RESERVATION_REQUESTED,
        INVENTORY_ACCEPTED,
        INVENTORY_REJECTED,
        RESERVATION_ACCEPTED,
        RESERVATION_REJECTED
    }

    public static final class BrokerUnavailable extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public BrokerUnavailable() {
            super("broker unavailable");
        }
    }

    public static final class SimulatedCrash extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public SimulatedCrash() {
            super("crash after broker send");
        }
    }

    public static final class Overloaded extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public Overloaded() {
            super("too many pending reservations");
        }
    }

    public static final class DeadlineExceeded extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public DeadlineExceeded() {
            super("reservation deadline exceeded");
        }
    }

    public static final class InventoryQueryUnavailable extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public InventoryQueryUnavailable() {
            super("inventory operation lookup unavailable");
        }
    }

    public record CommandResult(String reservationId, Status status) {
    }

    public record Reservation(
        String reservationId,
        String operationId,
        int quantity,
        Status status,
        String correlationId
    ) {
    }

    public record Event(
        String eventId,
        Kind kind,
        String reservationId,
        int sequence,
        int quantity,
        String correlationId,
        String causationId
    ) {
    }

    public record EventEnvelope(int schemaVersion, Event event) {
    }

    public record Observation(
        String component,
        String action,
        String correlationId,
        String operationId,
        String eventId,
        String outcome
    ) {
    }

    public enum ReconciliationOutcome {
        APPLIED,
        PENDING_NOT_FOUND,
        PENDING_SOURCE_UNAVAILABLE
    }

    public record ReconciliationRecord(
        String operationId,
        String reservationId,
        ReconciliationOutcome outcome,
        long nextAttemptAtMillis
    ) {
    }

    public record DispatchTask(
        String operationId,
        String correlationId,
        int quantity,
        long deadlineMillis
    ) {
    }

    // [Implementation 2] Outbox 이벤트의 생성 시각과 발행 상태
    // OutboxRecord 하나가 이벤트와 생성 시각, 발행 완료 여부를 보관합니다.
    private static final class OutboxRecord {
        private final Event event;
        private final long createdAtMillis;
        private boolean published;

        private OutboxRecord(Event event, long createdAtMillis) {
            this.event = event;
            this.createdAtMillis = createdAtMillis;
        }
    }

    // [Implementation 3] 예약 상태와 Outbox 저장
    // ReservationService만 예약 상태와 해당 예약에서 만든 Outbox 행을 변경합니다.
    public static final class ReservationService {
        private final int maxPending;
        private final Map<String, Reservation> reservations = new LinkedHashMap<>();
        private final Map<String, String> reservationByOperation = new HashMap<>();
        private final Map<String, Integer> inputByOperation = new HashMap<>();
        private final Map<String, String> correlationByOperation = new HashMap<>();
        private final Map<String, OutboxRecord> outbox = new LinkedHashMap<>();
        private final Map<String, Event> consumedInventoryEvents = new HashMap<>();
        private int nextReservation = 1;

        public ReservationService(int maxPending) {
            if (maxPending <= 0) {
                throw new IllegalArgumentException("maxPending must be positive");
            }
            this.maxPending = maxPending;
        }

        public CommandResult submit(
            String operationId,
            String correlationId,
            int quantity
        ) {
            return submit(operationId, correlationId, quantity, 0L);
        }

        // [Implementation 3-1] 예약 요청 멱등 처리
        // operation ID를 먼저 선점한 뒤 예약과 첫 Outbox 이벤트를 함께 생성합니다.
        public CommandResult submit(
            String operationId,
            String correlationId,
            int quantity,
            long nowMillis
        ) {
            if (operationId == null || operationId.isBlank()
                || correlationId == null || correlationId.isBlank()) {
                throw new IllegalArgumentException("operation and correlation IDs are required");
            }
            if (quantity <= 0) {
                throw new IllegalArgumentException("quantity must be positive");
            }

            String existingId = reservationByOperation.get(operationId);
            if (existingId != null) {
                if (inputByOperation.get(operationId) != quantity
                    || !correlationId.equals(correlationByOperation.get(operationId))) {
                    throw new IllegalArgumentException(
                        "operation ID was reused with different input"
                    );
                }
                Reservation existing = reservations.get(existingId);
                return new CommandResult(existing.reservationId(), existing.status());
            }
            if (pendingCount() >= maxPending) {
                throw new Overloaded();
            }

            String reservationId = "reservation-" + nextReservation++;
            Reservation reservation = new Reservation(
                reservationId,
                operationId,
                quantity,
                Status.PENDING,
                correlationId
            );
            reservations.put(reservationId, reservation);
            reservationByOperation.put(operationId, reservationId);
            inputByOperation.put(operationId, quantity);
            correlationByOperation.put(operationId, correlationId);

            Event requested = new Event(
                "reservation-requested-" + reservationId,
                Kind.RESERVATION_REQUESTED,
                reservationId,
                1,
                quantity,
                correlationId,
                operationId
            );
            outbox.put(requested.eventId(), new OutboxRecord(requested, nowMillis));
            return new CommandResult(reservationId, Status.PENDING);
        }

        public CommandResult findByOperation(String operationId) {
            String reservationId = reservationByOperation.get(operationId);
            if (reservationId == null) {
                return null;
            }
            Reservation reservation = reservations.get(reservationId);
            return new CommandResult(reservationId, reservation.status());
        }

        public void applyInventoryResult(Event result) {
            applyInventoryResult(result, 0L);
        }

        // [Implementation 3-2] 재고 결과 검증과 최종 상태 전이
        // event ID, quantity, correlation과 causation을 확인한 뒤 예약 상태와 상태 이벤트를 갱신합니다.
        public void applyInventoryResult(Event result, long nowMillis) {
            if (result == null
                || (result.kind() != Kind.INVENTORY_ACCEPTED
                    && result.kind() != Kind.INVENTORY_REJECTED)) {
                throw new IllegalArgumentException("not an inventory result");
            }
            if (result.eventId() == null || result.eventId().isBlank()) {
                throw new IllegalArgumentException("inventory result event ID is required");
            }

            Event consumed = consumedInventoryEvents.get(result.eventId());
            if (consumed != null) {
                if (!consumed.equals(result)) {
                    throw new IllegalArgumentException(
                        "inventory result ID was reused with different payload"
                    );
                }
                return;
            }

            Reservation previous = requireReservation(result.reservationId());
            if (result.quantity() != previous.quantity()
                || !result.correlationId().equals(previous.correlationId())
                || !result.causationId().equals(
                    "reservation-requested-" + previous.reservationId()
                )) {
                throw new IllegalArgumentException(
                    "inventory result does not match reservation input"
                );
            }

            Status nextStatus = result.kind() == Kind.INVENTORY_ACCEPTED
                ? Status.ACCEPTED
                : Status.REJECTED;
            if (previous.status() != Status.PENDING
                && previous.status() != Status.UNKNOWN) {
                if (previous.status() != nextStatus) {
                    throw new IllegalStateException("contradictory terminal transition");
                }
                consumedInventoryEvents.put(result.eventId(), result);
                return;
            }

            consumedInventoryEvents.put(result.eventId(), result);
            Reservation updated = new Reservation(
                previous.reservationId(),
                previous.operationId(),
                previous.quantity(),
                nextStatus,
                previous.correlationId()
            );
            reservations.put(updated.reservationId(), updated);

            Kind statusKind = nextStatus == Status.ACCEPTED
                ? Kind.RESERVATION_ACCEPTED
                : Kind.RESERVATION_REJECTED;
            Event statusEvent = new Event(
                "reservation-status-" + updated.reservationId(),
                statusKind,
                updated.reservationId(),
                2,
                updated.quantity(),
                updated.correlationId(),
                result.eventId()
            );
            outbox.putIfAbsent(
                statusEvent.eventId(),
                new OutboxRecord(statusEvent, nowMillis)
            );
        }

        public void markUnknown(String reservationId) {
            Reservation previous = requireReservation(reservationId);
            if (previous.status() == Status.PENDING) {
                reservations.put(
                    reservationId,
                    new Reservation(
                        previous.reservationId(),
                        previous.operationId(),
                        previous.quantity(),
                        Status.UNKNOWN,
                        previous.correlationId()
                    )
                );
            }
        }

        public void markPending(String reservationId) {
            Reservation previous = requireReservation(reservationId);
            if (previous.status() == Status.UNKNOWN) {
                reservations.put(
                    reservationId,
                    new Reservation(
                        previous.reservationId(),
                        previous.operationId(),
                        previous.quantity(),
                        Status.PENDING,
                        previous.correlationId()
                    )
                );
            }
        }

        // [Implementation 3-3] 미발행 이벤트 스냅샷
        // 호출자에게 변경 가능한 OutboxRecord가 아니라 Event 값의 복사본만 반환합니다.
        public List<Event> pendingOutbox() {
            List<Event> pending = new ArrayList<>();
            for (OutboxRecord record : outbox.values()) {
                if (!record.published) {
                    pending.add(record.event);
                }
            }
            return List.copyOf(pending);
        }

        public void markPublished(String eventId) {
            OutboxRecord record = outbox.get(eventId);
            if (record == null) {
                throw new IllegalArgumentException("unknown outbox event: " + eventId);
            }
            record.published = true;
        }

        public int reservationCount() {
            return reservations.size();
        }

        public int pendingCount() {
            return (int) reservations.values().stream()
                .filter(reservation -> reservation.status() == Status.PENDING
                    || reservation.status() == Status.UNKNOWN)
                .count();
        }

        public int outboxCount() {
            return outbox.size();
        }

        public int pendingOutboxCount() {
            return pendingOutbox().size();
        }

        // [Implementation 3-4] 가장 오래된 미발행 이벤트 시간
        // 현재 시각에서 각 미발행 행의 생성 시각을 빼 가장 긴 대기 시간을 계산합니다.
        public OptionalLong oldestPendingOutboxAge(long nowMillis) {
            return outbox.values().stream()
                .filter(record -> !record.published)
                .mapToLong(record -> Math.max(0L, nowMillis - record.createdAtMillis))
                .max();
        }

        public List<Reservation> pendingReservations() {
            return reservations.values().stream()
                .filter(reservation -> reservation.status() == Status.PENDING
                    || reservation.status() == Status.UNKNOWN)
                .toList();
        }

        public Status status(String reservationId) {
            return requireReservation(reservationId).status();
        }

        private Reservation requireReservation(String reservationId) {
            Reservation reservation = reservations.get(reservationId);
            if (reservation == null) {
                throw new IllegalArgumentException("unknown reservation: " + reservationId);
            }
            return reservation;
        }
    }

    // [Implementation 4] 재고와 operation별 결과 저장
    // InventoryService만 재고를 차감하고 operation ID별 확정 결과를 보관합니다.
    public static final class InventoryService {
        private int available;
        private int allocationEffects;
        private final Map<String, Event> resultByRequestEvent = new HashMap<>();
        private final Map<String, Event> requestsByEventId = new HashMap<>();
        private final Map<String, Event> requestsByOperation = new HashMap<>();
        private final Map<String, Event> resultByOperation = new HashMap<>();
        private final List<String> lookupOperations = new ArrayList<>();
        private boolean lookupAvailable = true;

        public InventoryService(int available) {
            if (available < 0) {
                throw new IllegalArgumentException("available must not be negative");
            }
            this.available = available;
        }

        // [Implementation 4-1] 재고 차감 한 번만 적용
        // event ID와 operation ID를 모두 확인한 뒤 처음 본 요청에서만 재고를 줄입니다.
        public Event handle(Event request) {
            if (request == null || request.kind() != Kind.RESERVATION_REQUESTED) {
                throw new IllegalArgumentException("not a reservation request");
            }

            Event previous = resultByRequestEvent.get(request.eventId());
            if (previous != null) {
                if (!request.equals(requestsByEventId.get(request.eventId()))) {
                    throw new IllegalArgumentException(
                        "request event ID was reused with different payload"
                    );
                }
                return previous;
            }

            Event previousOperation = requestsByOperation.get(request.causationId());
            if (previousOperation != null) {
                if (!sameOperationInput(previousOperation, request)) {
                    throw new IllegalArgumentException(
                        "inventory operation ID was reused with different input"
                    );
                }
                Event operationResult = resultByOperation.get(request.causationId());
                requestsByEventId.put(request.eventId(), request);
                resultByRequestEvent.put(request.eventId(), operationResult);
                return operationResult;
            }

            boolean accepted = request.quantity() <= available;
            if (accepted) {
                available -= request.quantity();
                allocationEffects++;
            }
            Event result = new Event(
                "inventory-result-" + request.reservationId(),
                accepted ? Kind.INVENTORY_ACCEPTED : Kind.INVENTORY_REJECTED,
                request.reservationId(),
                1,
                request.quantity(),
                request.correlationId(),
                request.eventId()
            );
            resultByRequestEvent.put(request.eventId(), result);
            requestsByEventId.put(request.eventId(), request);
            requestsByOperation.put(request.causationId(), request);
            resultByOperation.put(request.causationId(), result);
            return result;
        }

        private static boolean sameOperationInput(Event left, Event right) {
            return left.kind() == right.kind()
                && left.reservationId().equals(right.reservationId())
                && left.sequence() == right.sequence()
                && left.quantity() == right.quantity()
                && left.correlationId().equals(right.correlationId())
                && left.causationId().equals(right.causationId());
        }

        // [Implementation 4-2] 원래 operation ID로 결과 조회
        // 재조정은 최초 operation ID로 InventoryService의 확정 결과를 조회합니다.
        public Event findResultByOperation(String operationId) {
            lookupOperations.add(operationId);
            if (!lookupAvailable) {
                throw new InventoryQueryUnavailable();
            }
            return resultByOperation.get(operationId);
        }

        public void setLookupAvailable(boolean lookupAvailable) {
            this.lookupAvailable = lookupAvailable;
        }

        public List<String> lookupOperations() {
            return List.copyOf(lookupOperations);
        }

        public int available() {
            return available;
        }

        public int allocationEffects() {
            return allocationEffects;
        }
    }
}
