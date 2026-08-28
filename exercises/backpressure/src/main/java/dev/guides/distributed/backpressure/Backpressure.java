package dev.guides.distributed.backpressure;

import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.Map;
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
    private static final class Lane {
        private final int maxInFlight;
        private final int maxQueued;
        private final long maxQueueAge;
        private final Set<String> inFlight = new LinkedHashSet<>();
        private final Queue<Queued> queued = new ArrayDeque<>();
        private final Set<String> completed = new LinkedHashSet<>();
        private int rejected;
        private int expired;

        private Lane(int maxInFlight, int maxQueued, long maxQueueAge) {
            if (maxInFlight <= 0 || maxQueued < 0 || maxQueueAge < 0) {
                throw new IllegalArgumentException("invalid lane limits");
            }
            this.maxInFlight = maxInFlight;
            this.maxQueued = maxQueued;
            this.maxQueueAge = maxQueueAge;
        }

        // [Implementation 2-1] 중복·만료 검사와 수용 여부 판단
        // 중복 ID와 만료된 요청을 먼저 걸러낸 뒤 실행 자리와 대기열 여유를 확인합니다.
        private Admission submit(String requestId, long now, long deadline) {
            if (inFlight.contains(requestId)
                || queued.stream().anyMatch(entry -> entry.requestId().equals(requestId))
                || completed.contains(requestId)) {
                throw new IllegalArgumentException("duplicate request ID: " + requestId);
            }
            expire(now);
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

        // [Implementation 2-2] 실행 자리 하나의 승격
        // 작업 하나가 끝나면 아직 유효한 대기 작업을 최대 하나만 실행 상태로 옮깁니다.
        private String completeOne(long now) {
            if (inFlight.isEmpty()) {
                throw new IllegalStateException("no in-flight work");
            }
            String finished = inFlight.iterator().next();
            inFlight.remove(finished);
            completed.add(finished);

            expire(now);
            Queued next = queued.poll();
            if (next != null) {
                inFlight.add(next.requestId());
            }
            return next == null ? null : next.requestId();
        }

        // [Implementation 2-3] 대기 작업 만료
        // 대기열 앞에서부터 검사해야 FIFO 순서를 유지하면서 만료 건수를 정확히 셀 수 있습니다.
        private void expire(long now) {
            while (!queued.isEmpty()) {
                Queued head = queued.element();
                boolean tooOld = maxQueueAge != Long.MAX_VALUE
                    && now - head.enqueuedAt() >= maxQueueAge;
                if (now < head.deadline() && !tooOld) {
                    return;
                }
                queued.remove();
                expired++;
            }
        }

        // [Implementation 2-4] 최장 대기 시간 계산
        // 대기열 길이와 별도로 가장 오래 기다린 시간을 노출해 포화가 얼마나 지속됐는지 확인합니다.
        private long oldestAge(long now) {
            Queued head = queued.peek();
            return head == null ? 0 : Math.max(0, now - head.enqueuedAt());
        }
    }

    // [Implementation 3] 작업 종류별 격리
    // AdmissionSystem은 이름별 Lane을 따로 두어 한 작업의 포화가 다른 작업의 용량을 사용하지 못하게 합니다.
    public static final class AdmissionSystem {
        private final Map<String, Lane> lanes = new HashMap<>();

        public void register(String name, int maxInFlight, int maxQueued) {
            register(name, maxInFlight, maxQueued, Long.MAX_VALUE);
        }

        public void register(String name, int maxInFlight, int maxQueued, long maxQueueAge) {
            if (lanes.putIfAbsent(name, new Lane(maxInFlight, maxQueued, maxQueueAge)) != null) {
                throw new IllegalArgumentException("lane already registered: " + name);
            }
        }

        public Admission submit(String lane, String requestId) {
            return submit(lane, requestId, 0, Long.MAX_VALUE);
        }

        public Admission submit(String lane, String requestId, long now, long deadline) {
            return lane(lane).submit(requestId, now, deadline);
        }

        public String completeOne(String lane) {
            return completeOne(lane, 0);
        }

        public String completeOne(String lane, long now) {
            return lane(lane).completeOne(now);
        }

        public int inFlight(String lane) {
            return lane(lane).inFlight.size();
        }

        public int queued(String lane) {
            return lane(lane).queued.size();
        }

        public int rejected(String lane) {
            return lane(lane).rejected;
        }

        public int expire(String lane, long now) {
            Lane selected = lane(lane);
            int before = selected.expired;
            selected.expire(now);
            return selected.expired - before;
        }

        public int expired(String lane) {
            return lane(lane).expired;
        }

        public long oldestQueueAge(String lane, long now) {
            return lane(lane).oldestAge(now);
        }

        public boolean completed(String lane, String requestId) {
            return lane(lane).completed.contains(requestId);
        }

        private Lane lane(String name) {
            Lane lane = lanes.get(name);
            if (lane == null) {
                throw new IllegalArgumentException("unknown lane: " + name);
            }
            return lane;
        }
    }

    private Backpressure() {
    }
}
