#!/usr/bin/env python3
"""TCP 송신 창과 RTO, Reno 상태를 결정적으로 계산합니다."""

from __future__ import annotations

from dataclasses import dataclass
import math


# [Implementation 1] Sender window state
# 한 객체가 순서 번호 위치, 두 윈도와 MSS를 함께 보관합니다.
@dataclass
class WindowSender:
    send_base: int
    next_sequence: int
    receive_window: int
    congestion_window: int
    maximum_segment_size: int

    def __post_init__(self) -> None:
        if self.next_sequence < self.send_base:
            raise ValueError("next_sequence는 send_base보다 작을 수 없습니다")
        if self.receive_window < 0:
            raise ValueError("receive_window는 음수일 수 없습니다")
        for name in ("congestion_window", "maximum_segment_size"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name}은 양수여야 합니다")

    # [Implementation 1-1] Derived send capacity
    # 저장값이 순서 번호와 어긋나지 않도록 전송 가능량은 매번 계산합니다.
    @property
    def in_flight(self) -> int:
        return self.next_sequence - self.send_base

    @property
    def effective_window(self) -> int:
        return min(self.receive_window, self.congestion_window)

    @property
    def available(self) -> int:
        return max(0, self.effective_window - self.in_flight)

    # [Implementation 1-2] Send and cumulative ACK sequence updates
    # 저장된 순서 번호 범위는 송신과 누적 ACK 처리에서만 바뀝니다.
    def send_one_segment(self) -> tuple[int, int] | None:
        size = min(self.maximum_segment_size, self.available)
        if size == 0:
            return None
        start = self.next_sequence
        self.next_sequence += size
        return start, self.next_sequence

    def acknowledge(self, next_expected: int) -> int:
        if next_expected < self.send_base:
            return 0
        if next_expected > self.next_sequence:
            raise ValueError("아직 보내지 않은 바이트를 ACK할 수 없습니다")
        newly_acked = next_expected - self.send_base
        self.send_base = next_expected
        return newly_acked


# [Implementation 2] RTT estimator and RTO backoff
# RTT 표본과 백오프는 같은 RTO 값을 정해진 범위 안에서 갱신합니다.
@dataclass
class RttEstimator:
    """RFC 6298의 기본 계산 순서로 재전송 제한 시간을 갱신합니다."""

    smoothed: float | None = None
    variation: float | None = None
    timeout: float = 1.0

    def sample(self, seconds: float) -> float:
        if (
            not isinstance(seconds, (int, float))
            or isinstance(seconds, bool)
            or not math.isfinite(seconds)
            or seconds <= 0
        ):
            raise ValueError("RTT 표본은 유한한 양수여야 합니다")
        if self.smoothed is None:
            self.smoothed = seconds
            self.variation = seconds / 2
        else:
            assert self.variation is not None
            self.variation = 0.75 * self.variation + 0.25 * abs(
                self.smoothed - seconds
            )
            self.smoothed = 0.875 * self.smoothed + 0.125 * seconds
        self.timeout = min(60.0, max(1.0, self.smoothed + 4 * self.variation))
        return self.timeout

    def backoff(self) -> float:
        self.timeout = min(60.0, self.timeout * 2)
        return self.timeout


# [Implementation 3] Reno congestion state
# 컨트롤러가 cwnd, ssthresh, 중복 ACK 횟수와 복구 상태를 함께 보관합니다.
@dataclass
class RenoController:
    """Reno의 느린 시작과 혼잡 회피를 바이트 단위로 계산합니다."""

    congestion_window: int
    slow_start_threshold: int
    maximum_segment_size: int
    duplicate_acknowledgments: int = 0
    fast_recovery: bool = False

    def __post_init__(self) -> None:
        if min(
            self.congestion_window,
            self.slow_start_threshold,
            self.maximum_segment_size,
        ) <= 0:
            raise ValueError("창, 임계값과 MSS는 모두 양수여야 합니다")

    # [Implementation 3-1] ACK-driven Reno transitions
    # 새 바이트를 확인한 ACK와 중복 ACK는 서로 다른 상태 전이를 적용합니다.
    def acknowledge(self, newly_acked: int) -> str:
        if newly_acked < 0:
            raise ValueError("ACK 바이트 수는 음수일 수 없습니다")
        if newly_acked == 0:
            self.duplicate_acknowledgments += 1
            if self.duplicate_acknowledgments == 3:
                self.slow_start_threshold = max(
                    2 * self.maximum_segment_size,
                    self.congestion_window // 2,
                )
                self.congestion_window = (
                    self.slow_start_threshold + 3 * self.maximum_segment_size
                )
                self.fast_recovery = True
                return "fast-retransmit"
            if self.duplicate_acknowledgments > 3 and self.fast_recovery:
                self.congestion_window += self.maximum_segment_size
            return "duplicate-ack"

        self.duplicate_acknowledgments = 0
        if self.fast_recovery:
            self.congestion_window = self.slow_start_threshold
            self.fast_recovery = False
            return "fast-recovery-complete"
        if self.congestion_window < self.slow_start_threshold:
            self.congestion_window += min(newly_acked, self.maximum_segment_size)
            return "slow-start"
        increment = max(
            1,
            self.maximum_segment_size * self.maximum_segment_size
            // self.congestion_window,
        )
        self.congestion_window += increment
        return "congestion-avoidance"

    # [Implementation 3-2] Timeout recovery
    # 제한 시간이 지나면 cwnd를 한 MSS로 줄이고 중복 ACK 복구 상태를 지웁니다.
    def timeout(self) -> None:
        self.slow_start_threshold = max(
            2 * self.maximum_segment_size,
            self.congestion_window // 2,
        )
        self.congestion_window = self.maximum_segment_size
        self.duplicate_acknowledgments = 0
        self.fast_recovery = False


# [Implementation 4] Deterministic demonstration
# 고정된 사건 순서를 사용해 각 상태 변화를 테스트에서 바로 비교합니다.
def demo() -> list[str]:
    sender = WindowSender(
        send_base=1000,
        next_sequence=1000,
        receive_window=4000,
        congestion_window=3000,
        maximum_segment_size=1000,
    )
    rows = [
        "event base next in_flight rwnd cwnd effective available",
        f"start {sender.send_base} {sender.next_sequence} {sender.in_flight} "
        f"{sender.receive_window} {sender.congestion_window} "
        f"{sender.effective_window} {sender.available}",
    ]
    for index in range(3):
        segment = sender.send_one_segment()
        assert segment is not None
        rows.append(
            f"send-{index + 1} {sender.send_base} {sender.next_sequence} "
            f"{sender.in_flight} {sender.receive_window} {sender.congestion_window} "
            f"{sender.effective_window} {sender.available}"
        )
    blocked = sender.send_one_segment()
    assert blocked is None
    rows.append(
        f"blocked {sender.send_base} {sender.next_sequence} {sender.in_flight} "
        f"{sender.receive_window} {sender.congestion_window} "
        f"{sender.effective_window} {sender.available}"
    )
    sender.acknowledge(2500)
    rows.append(
        f"ack-2500 {sender.send_base} {sender.next_sequence} {sender.in_flight} "
        f"{sender.receive_window} {sender.congestion_window} "
        f"{sender.effective_window} {sender.available}"
    )
    return rows


def main() -> int:
    print("\n".join(demo()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
