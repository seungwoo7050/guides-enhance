package dev.guides.distributed.contracts;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public final class ContractsAndOrder {
    // [Implementation 1] 이벤트 입력과 처리 결과
    // Outcome과 Event가 소비자가 받아들이는 입력과 반환할 처리 결과를 정의합니다.
    public enum Outcome {
        APPLIED,
        BUFFERED,
        DUPLICATE,
        STALE,
        ISOLATED
    }

    public record Event(
        String channel,
        int schemaVersion,
        String eventId,
        String aggregateId,
        long sequence,
        String state
    ) {
    }

    public static final class ContractViolationException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public ContractViolationException(String message) {
            super(message);
        }
    }

    // [Implementation 2] 조회 모델 상태와 순서 기록
    // Projection은 적용 결과, 다음 sequence, 보류 이벤트, sequence 선점과 격리 목록을 함께 보관합니다.
    public static final class Projection {
        private final String expectedChannel;
        private final int supportedSchemaVersion;
        private final Map<String, String> states = new HashMap<>();
        private final Map<String, Long> nextSequence = new HashMap<>();
        private final Map<String, TreeMap<Long, Event>> buffers = new HashMap<>();
        private final Map<String, TreeMap<Long, Event>> claimedSequences = new HashMap<>();
        private final Map<String, Event> knownEvents = new HashMap<>();
        private final List<Event> isolated = new ArrayList<>();

        public Projection(String expectedChannel, int supportedSchemaVersion) {
            if (supportedSchemaVersion <= 0) {
                throw new IllegalArgumentException("supportedSchemaVersion must be positive");
            }
            this.expectedChannel = expectedChannel;
            this.supportedSchemaVersion = supportedSchemaVersion;
        }

        // [Implementation 2-1] 채널·식별자·스키마 검증
        // 조회 모델을 바꾸기 전에 channel, ID, sequence와 schema version을 검사합니다.
        public synchronized Outcome onEvent(Event event) {
            if (!expectedChannel.equals(event.channel())) {
                throw new ContractViolationException(
                    "unexpected channel: " + event.channel()
                );
            }
            if (event.eventId() == null || event.eventId().isBlank()
                || event.aggregateId() == null || event.aggregateId().isBlank()
                || event.sequence() <= 0) {
                throw new ContractViolationException("invalid event identity or sequence");
            }
            if (event.schemaVersion() <= 0) {
                throw new ContractViolationException("schema version must be positive");
            }
            Event known = knownEvents.get(event.eventId());
            if (known != null) {
                if (!known.equals(event)) {
                    throw new ContractViolationException(
                        "event ID was reused with different payload: " + event.eventId()
                    );
                }
                return Outcome.DUPLICATE;
            }
            if (event.schemaVersion() > supportedSchemaVersion) {
                knownEvents.put(event.eventId(), event);
                isolated.add(event);
                return Outcome.ISOLATED;
            }

            // [Implementation 2-2] Aggregate별 sequence 선점 기록
            // 같은 aggregate와 sequence를 먼저 차지한 이벤트를 기록해 gap, 오래된 전달과 충돌을 구분합니다.
            long expected = nextSequence.getOrDefault(event.aggregateId(), 1L);
            TreeMap<Long, Event> claims = claimedSequences.get(event.aggregateId());
            Event claimed = claims == null ? null : claims.get(event.sequence());
            if (claimed != null && !claimed.equals(event)) {
                throw new ContractViolationException(
                    "different events claim aggregate sequence " + event.sequence()
                );
            }
            if (event.sequence() < expected) {
                if (claimed == null) {
                    throw new ContractViolationException(
                        "late event claims an already applied aggregate sequence "
                            + event.sequence()
                    );
                }
                knownEvents.put(event.eventId(), event);
                return Outcome.STALE;
            }
            if (event.sequence() > expected) {
                TreeMap<Long, Event> buffer = buffers.computeIfAbsent(
                    event.aggregateId(), ignored -> new TreeMap<>()
                );
                Event competing = buffer.get(event.sequence());
                if (competing != null && !competing.equals(event)) {
                    throw new ContractViolationException(
                        "different events claim aggregate sequence " + event.sequence()
                    );
                }
                knownEvents.put(event.eventId(), event);
                if (claims == null) {
                    claims = new TreeMap<>();
                    claimedSequences.put(event.aggregateId(), claims);
                }
                claims.put(event.sequence(), event);
                buffer.put(event.sequence(), event);
                return Outcome.BUFFERED;
            }

            knownEvents.put(event.eventId(), event);
            if (claims == null) {
                claims = new TreeMap<>();
                claimedSequences.put(event.aggregateId(), claims);
            }
            claims.put(event.sequence(), event);
            apply(event);
            drain(event.aggregateId());
            return Outcome.APPLIED;
        }

        public synchronized String state(String aggregateId) {
            return states.get(aggregateId);
        }

        public synchronized int bufferedCount(String aggregateId) {
            return buffers.getOrDefault(aggregateId, new TreeMap<>()).size();
        }

        public synchronized int isolatedCount() {
            return isolated.size();
        }

        // [Implementation 2-3] 상태와 다음 sequence 함께 갱신
        // 상태를 적용하고 다음 sequence를 전진시키는 작업을 같은 synchronized 블록에서 끝냅니다.
        private void apply(Event event) {
            states.put(event.aggregateId(), event.state());
            nextSequence.put(event.aggregateId(), event.sequence() + 1);
        }

        // [Implementation 2-4] Aggregate별 보류 이벤트 적용
        // 빠진 sequence가 도착한 aggregate만 연속해서 적용하고 다른 aggregate는 건드리지 않습니다.
        private void drain(String aggregateId) {
            TreeMap<Long, Event> buffer = buffers.get(aggregateId);
            if (buffer == null) {
                return;
            }
            while (true) {
                long expected = nextSequence.getOrDefault(aggregateId, 1L);
                Event next = buffer.remove(expected);
                if (next == null) {
                    return;
                }
                apply(next);
            }
        }
    }

    private ContractsAndOrder() {
    }
}
