package dev.guides.distributed.decision;

import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;
import java.util.Queue;

public final class RequestDecision {
    // [Implementation 1] 요청 방식과 판정 결과 정의
    // Mode, PolicyResult, Status로 즉시 판정과 비동기 접수 결과를 구분합니다.
    public enum Mode {
        SYNCHRONOUS,
        ASYNCHRONOUS
    }

    public enum PolicyResult {
        ALLOW,
        DENY,
        UNAVAILABLE
    }

    public enum Status {
        ACCEPTED,
        REJECTED,
        PENDING
    }

    public record Request(String operationId, int units) {
    }

    public record Decision(Status status, String reason) {
    }

    private record Submission(Request request, Mode mode) {
    }

    @FunctionalInterface
    public interface Policy {
        PolicyResult evaluate(Request request);
    }

    // [Implementation 2] 예약 수량 변경
    // CapacityLedger만 예약 수량을 변경할 수 있습니다.
    public static final class CapacityLedger {
        private int reserved;

        public synchronized void reserve(int units) {
            if (units <= 0) {
                throw new IllegalArgumentException("units must be positive");
            }
            reserved += units;
        }

        public synchronized int reserved() {
            return reserved;
        }
    }

    // [Implementation 3] 요청 입력·결과·대기열 저장
    // Coordinator가 operation별 입력과 결과, 아직 처리하지 않은 요청을 함께 보관합니다.
    public static final class Coordinator {
        private final CapacityLedger ledger;
        private final Queue<Request> pending = new ArrayDeque<>();
        private final Map<String, Decision> results = new HashMap<>();
        private final Map<String, Submission> submissions = new HashMap<>();

        public Coordinator(CapacityLedger ledger) {
            this.ledger = ledger;
        }

        // [Implementation 3-1] 중복 요청 검증과 비동기 접수
        // 기존 operation은 전체 입력을 비교하고 비동기 신규 요청은 효과를 실행하지 않은 채 PENDING으로 저장합니다.
        public synchronized Decision submit(Request request, Mode mode, Policy policy) {
            if (request == null || request.operationId() == null
                || request.operationId().isBlank() || request.units() <= 0
                || mode == null || policy == null) {
                throw new IllegalArgumentException("valid request, mode, and policy are required");
            }
            Submission input = new Submission(request, mode);
            Submission previousInput = submissions.get(request.operationId());
            Decision existing = results.get(request.operationId());
            if (previousInput != null) {
                if (!previousInput.equals(input)) {
                    throw new IllegalArgumentException(
                        "operation ID was reused with a different decision input"
                    );
                }
                return existing;
            }

            if (mode == Mode.ASYNCHRONOUS) {
                Decision result = new Decision(Status.PENDING, "queued");
                submissions.put(request.operationId(), input);
                pending.add(request);
                results.put(request.operationId(), result);
                return result;
            }

            Decision result = decideNow(request, policy);
            submissions.put(request.operationId(), input);
            return result;
        }

        // [Implementation 3-2] 대기 요청 판정 완료
        // 대기열에서 꺼낸 요청의 판정과 결과 저장을 같은 synchronized 작업에서 끝냅니다.
        public synchronized Decision processNext(Policy policy) {
            Request request = pending.remove();
            Decision result = decideNow(request, policy);
            results.put(request.operationId(), result);
            return result;
        }

        public synchronized int pendingCount() {
            return pending.size();
        }

        // [Implementation 3-3] ALLOW 이후에만 수량 변경
        // 원격 Policy가 명시적으로 ALLOW를 반환한 경우에만 예약 수량을 늘립니다.
        private Decision decideNow(Request request, Policy policy) {
            PolicyResult policyResult = policy.evaluate(request);
            Decision result;

            if (policyResult == PolicyResult.ALLOW) {
                ledger.reserve(request.units());
                result = new Decision(Status.ACCEPTED, "policy allowed");
            } else if (policyResult == PolicyResult.DENY) {
                result = new Decision(Status.REJECTED, "policy denied");
            } else {
                result = new Decision(Status.REJECTED, "policy unavailable");
            }

            results.put(request.operationId(), result);
            return result;
        }
    }

    private RequestDecision() {
    }
}
