package dev.guides.distributed.backpressure;

import java.util.ArrayDeque;
import java.util.LinkedHashSet;
import java.util.Queue;
import java.util.Set;

public final class Backpressure {
    // [Implementation 1] 처리 결과 정의
    // 즉시 실행, 제한된 대기, 거절을 서로 다른 결과로 반환합니다.
    public enum Admission {
        STARTED,
        QUEUED,
        REJECTED
    }

    private record Queued(String requestId, long enqueuedAt, long deadline) {
    }

    // [Implementation 2] 작업 종류별 실행·대기 상태
    // Lane 하나가 해당 작업의 실행 중·대기·완료·거절·만료 상태를 보관합니다.
    public static final class Lane {
        private final int maxInFlight;
        private final int maxQueued;
        private final long maxQueueAge;
        private final Set<String> inFlight = new LinkedHashSet<>();
        private final Queue<Queued> queued = new ArrayDeque<>();
        private final Set<String> completed = new LinkedHashSet<>();
        private int rejected;
        private int expired;

        public Lane(int maxInFlight, int maxQueued, long maxQueueAge) {
            if (maxInFlight <= 0 || maxQueued < 0 || maxQueueAge < 0) {
                throw new IllegalArgumentException("invalid lane limits");
            }
            this.maxInFlight = maxInFlight;
            this.maxQueued = maxQueued;
            this.maxQueueAge = maxQueueAge;
        }

        // [Implementation 2-1] 중복·만료 검사와 수용 여부 판단
        // 중복 ID와 만료된 요청을 먼저 걸러낸 뒤 실행 자리와 대기열 여유를 확인합니다.
        public Admission submit(String requestId, long now, long deadline) {
            if (inFlight.contains(requestId)
                || queued.stream().anyMatch(entry -> entry.requestId().equals(requestId))
                || completed.contains(requestId)) {
                throw new IllegalArgumentException("duplicate request ID: " + requestId);
            }
            if (now >= deadline) {
                expired++;
                return Admission.REJECTED;
            }
            if (inFlight.size() < maxInFlight) {
                inFlight.add(requestId);
                return Admission.STARTED;
            }
            if (queued.size() < maxQueued) {
                queued.add(new Queued(requestId, now, deadline));
                return Admission.QUEUED;
            }
            rejected++;
            return Admission.REJECTED;
        }
}
}
