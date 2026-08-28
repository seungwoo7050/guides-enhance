package dev.guides.distributed.observability;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class ObservabilityCorrelation {
    // [Implementation 1] 상관관계 식별자 정의
    // Command, Event, Observation에 각 식별자를 명시해 요청부터 이벤트 처리까지의 연결을 보존합니다.
    public record Command(
        String requestId,
        String operationId,
        String traceId,
        String correlationId,
        String aggregateId
    ) {
    }

    public record Event(
        String eventId,
        String causationId,
        String traceId,
        String correlationId,
        String operationId,
        String aggregateId
    ) {
    }

    public record Observation(
        String component,
        String action,
        String traceId,
        String correlationId,
        String operationId,
        String eventId,
        String outcome
    ) {
    }

    // [Implementation 2] 관찰 기록·중복 기록·지표 집계
    // Flow가 단계별 관찰값, 처리한 event ID, 제한된 지표와 업무 효과 횟수를 보관합니다.
    public static final class Flow {
        private final List<Observation> observations = new ArrayList<>();
        private final Map<String, Event> appliedEvents = new LinkedHashMap<>();
        private final Map<String, Integer> metrics = new LinkedHashMap<>();
        private int effects;

        // [Implementation 2-1] 외부에서 받은 식별자 보존
        // 상위 시스템이 준 trace ID와 correlation ID는 새 값으로 덮어쓰지 않습니다.
        public Command receive(
            String requestId,
            String operationId,
            String traceId,
            String correlationId,
            String aggregateId
        ) {
            Command command = new Command(
                requestId,
                operationId,
                traceId,
                correlationId,
                aggregateId
            );
            observe(
                "gateway",
                "command.received",
                command.traceId(),
                command.correlationId(),
                command.operationId(),
                null,
                "accepted"
            );
            return command;
        }

        public Command receive(String requestId, String operationId, String aggregateId) {
            return receive(
                requestId,
                operationId,
                "trace-" + requestId,
                requestId,
                aggregateId
            );
        }

        // [Implementation 2-2] 이벤트 원인 식별자 전파
        // 이벤트를 만들 때 operation, trace, correlation과 causation ID를 그대로 이어 줍니다.
        public Event publish(Command command) {
            Event event = new Event(
                "evt-" + command.operationId(),
                command.operationId(),
                command.traceId(),
                command.correlationId(),
                command.operationId(),
                command.aggregateId()
            );
            observe(
                "reservation",
                "event.published",
                event.traceId(),
                event.correlationId(),
                command.operationId(),
                event.eventId(),
                "success"
            );
            return event;
        }
        public List<Observation> observations() { return List.copyOf(observations); }
        private void observe(
            String component,
            String action,
            String traceId,
            String correlationId,
            String operationId,
            String eventId,
            String outcome
        ) {
            observations.add(new Observation(
                component,
                action,
                traceId,
                correlationId,
                operationId,
                eventId,
                outcome
            ));
        }
    }
}
