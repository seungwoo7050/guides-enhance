package dev.guides.distributed.uncertain;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

public final class UncertainOutcome {
    // [Implementation 1] 처리 결과 상태
    // 서버가 확정한 결과와 클라이언트가 아직 알 수 없는 결과를 서로 다른 Status로 표현합니다.
    public enum Status {
        ACCEPTED,
        REJECTED,
        UNKNOWN
    }

    public record Result(String operationId, Status status, int units) {
    }

    public static final class ResponseLostException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public ResponseLostException() {
            super("response lost after commit");
        }
    }

    // [Implementation 2] operation 입력·결과·효과 횟수 저장
    // Gateway가 operation ID별 입력 지문, 결과와 업무 효과 횟수를 함께 보관합니다.
    public static final class Gateway {
        private final Map<String, Result> results = new HashMap<>();
        private final Map<String, Integer> fingerprints = new HashMap<>();
        private int effectCount;

        // [Implementation 2-1] 입력 지문 검증과 효과 한 번 적용
        // 같은 operation ID의 입력을 비교하고 처음 본 요청에서만 결과와 효과 횟수를 갱신합니다.
        public synchronized Result reserve(
            String operationId,
            int units,
            boolean loseResponseAfterCommit
        ) {
            requireInput(operationId, units);

            Result existing = results.get(operationId);
            if (existing != null) {
                if (fingerprints.get(operationId) != units) {
                    throw new IllegalArgumentException(
                        "operation id was reused with different input"
                    );
                }
                return existing;
            }

            Result created = new Result(operationId, Status.ACCEPTED, units);
            fingerprints.put(operationId, units);
            results.put(operationId, created);
            effectCount++;

            if (loseResponseAfterCommit) {
                throw new ResponseLostException();
            }
            return created;
        }

        // [Implementation 2-2] 저장된 결과 조회
        // 응답을 잃었을 때 전송 실패를 추측하지 않고 서버에 저장된 결과를 다시 읽습니다.
        public synchronized Optional<Result> query(String operationId) {
            return Optional.ofNullable(results.get(operationId));
        }

        public synchronized int effectCount() {
            return effectCount;
        }

        private static void requireInput(String operationId, int units) {
            if (operationId == null || operationId.isBlank()) {
                throw new IllegalArgumentException("operationId is required");
            }
            if (units <= 0) {
                throw new IllegalArgumentException("units must be positive");
            }
        }
    }

    // [Implementation 3] 응답 유실 후 결과 확인
    // Client는 처음 사용한 operation ID로 조회하고 결과가 없을 때만 UNKNOWN을 반환합니다.
    public static final class Client {
        private final Gateway gateway;

        public Client(Gateway gateway) {
            this.gateway = gateway;
        }

        public Result reserve(
            String operationId,
            int units,
            boolean loseFirstResponse
        ) {
            try {
                return gateway.reserve(operationId, units, loseFirstResponse);
            } catch (ResponseLostException lost) {
                return gateway.query(operationId)
                    .orElse(new Result(operationId, Status.UNKNOWN, 0));
            }
        }
    }

    private UncertainOutcome() {
    }
}
