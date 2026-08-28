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

    // [Implementation 4] 로그 위치와 조회 모델 적용 순서
    // Runner가 현재 로그 위치와 Projection 적용 사이의 실행 순서를 관리합니다.
    public static final class Runner {
        private final EventLog log;
        private final Projection projection;
        private long checkpoint;

        public Runner(EventLog log, Projection projection) {
            this.log = log;
            this.projection = projection;
        }

        // [Implementation 4-1] 적용 완료 후 체크포인트 전진
        // Projection 적용이 끝난 뒤에만 checkpoint를 늘려 처리하지 않은 이벤트를 건너뛰지 않습니다.
        public boolean processNext(
            boolean crashBeforeApply,
            boolean crashAfterApplyBeforeCheckpoint
        ) {
            if (checkpoint >= log.size()) {
                return false;
            }

            Event event = log.at(checkpoint);
            if (crashBeforeApply) {
                throw new SimulatedCrashException("before apply");
            }

            projection.apply(event);
            if (crashAfterApplyBeforeCheckpoint) {
                throw new SimulatedCrashException("after apply before checkpoint");
            }

            checkpoint++;
            return true;
        }

        // [Implementation 4-2] 전체 로그 재생
        // 온라인 처리와 같은 processNext 경로를 로그 끝까지 반복해 새 Projection을 만듭니다.
        public void replayAll() {
            while (processNext(false, false)) {
                // processNext가 현재 로그 끝에 도달하면 반복을 종료합니다.
            }
        }

        public long checkpoint() {
            return checkpoint;
        }
    }

    private ReadModelRebuild() {
    }
}
