package dev.guides.distributed.readmodel;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class ReadModelRebuild {
    // [Implementation 1] 재생 이벤트 식별자
    // Event는 중복 판정에 사용할 event ID와 aggregate별 변화량을 함께 보관합니다.
    public record Event(String eventId, String aggregateId, int delta) {
    }

    public static final class SimulatedCrashException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public SimulatedCrashException(String point) {
            super(point);
        }
    }

    // [Implementation 2] 입력 순서를 보존하는 이벤트 로그
    // EventLog가 온라인 처리와 전체 재구축에 사용할 입력 순서를 보관합니다.
    public static final class EventLog {
        private final List<Event> events = new ArrayList<>();

        public synchronized void append(Event event) {
            events.add(event);
        }

        public synchronized Event at(long position) {
            return events.get(Math.toIntExact(position));
        }

        public synchronized int size() {
            return events.size();
        }
    }

    // [Implementation 3] 집계 값과 적용 이벤트 기록
    // Projection이 aggregate별 합계와 이미 적용한 이벤트 지문을 함께 보관합니다.
    public static final class Projection {
        private final Map<String, Integer> totals = new HashMap<>();
        private final Map<String, Event> appliedEvents = new HashMap<>();

        // [Implementation 3-1] 이벤트 중복 적용 방지
        // 동일한 재전달은 무시하고 같은 ID의 다른 입력은 합계를 바꾸기 전에 거절합니다.
        public synchronized void apply(Event event) {
            Event previous = appliedEvents.get(event.eventId());
            if (previous != null) {
                if (!previous.equals(event)) {
                    throw new IllegalArgumentException(
                        "event ID was reused with different payload"
                    );
                }
                return;
            }
            appliedEvents.put(event.eventId(), event);
            totals.merge(event.aggregateId(), event.delta(), Integer::sum);
        }

        public synchronized int total(String aggregateId) {
            return totals.getOrDefault(aggregateId, 0);
        }

        public synchronized int appliedCount() {
            return appliedEvents.size();
        }
    }
}
