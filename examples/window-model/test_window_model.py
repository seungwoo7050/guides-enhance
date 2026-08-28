from __future__ import annotations

import unittest

from window_model import RenoController, RttEstimator, WindowSender


class WindowSenderTests(unittest.TestCase):
    def test_effective_window_is_minimum_of_flow_and_congestion_windows(self) -> None:
        sender = WindowSender(100, 300, 1000, 600, 200)
        self.assertEqual(sender.in_flight, 200)
        self.assertEqual(sender.effective_window, 600)
        self.assertEqual(sender.available, 400)

    def test_sender_stops_at_the_effective_window(self) -> None:
        sender = WindowSender(0, 0, 5000, 2500, 1000)
        self.assertEqual(sender.send_one_segment(), (0, 1000))
        self.assertEqual(sender.send_one_segment(), (1000, 2000))
        self.assertEqual(sender.send_one_segment(), (2000, 2500))
        self.assertIsNone(sender.send_one_segment())

    def test_cumulative_ack_opens_the_window(self) -> None:
        sender = WindowSender(1000, 3000, 3000, 2000, 1000)
        self.assertEqual(sender.acknowledge(2000), 1000)
        self.assertEqual(sender.available, 1000)
        self.assertEqual(sender.send_one_segment(), (3000, 4000))

    def test_zero_receive_window_blocks_new_data(self) -> None:
        sender = WindowSender(0, 0, 0, 3000, 1000)
        self.assertEqual(sender.effective_window, 0)
        self.assertEqual(sender.available, 0)
        self.assertIsNone(sender.send_one_segment())

    def test_ack_cannot_cover_unsent_bytes(self) -> None:
        # 보내지 않은 바이트까지 ACK하면 send_base가 next_sequence를 넘어갑니다.
        sender = WindowSender(10, 20, 100, 100, 10)
        with self.assertRaises(ValueError):
            sender.acknowledge(21)


class RttEstimatorTests(unittest.TestCase):
    def test_first_sample_and_backoff_follow_bounds(self) -> None:
        estimator = RttEstimator()
        self.assertEqual(estimator.sample(0.2), 1.0)
        self.assertEqual(estimator.backoff(), 2.0)
        for _ in range(8):
            estimator.backoff()
        self.assertEqual(estimator.timeout, 60.0)

    def test_invalid_sample_is_rejected(self) -> None:
        for sample in (0, -0.1, float("inf"), float("nan"), True):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                RttEstimator().sample(sample)


class RenoControllerTests(unittest.TestCase):
    def test_slow_start_then_congestion_avoidance(self) -> None:
        controller = RenoController(1000, 2000, 1000)
        self.assertEqual(controller.acknowledge(1000), "slow-start")
        self.assertEqual(controller.congestion_window, 2000)
        self.assertEqual(
            controller.acknowledge(1000), "congestion-avoidance"
        )
        self.assertEqual(controller.congestion_window, 2500)

    def test_three_duplicate_acks_trigger_fast_retransmit(self) -> None:
        controller = RenoController(8000, 16000, 1000)
        self.assertEqual(controller.acknowledge(0), "duplicate-ack")
        self.assertEqual(controller.acknowledge(0), "duplicate-ack")
        self.assertEqual(controller.acknowledge(0), "fast-retransmit")
        self.assertEqual(controller.slow_start_threshold, 4000)
        self.assertEqual(controller.congestion_window, 7000)
        self.assertEqual(controller.acknowledge(0), "duplicate-ack")
        self.assertEqual(controller.congestion_window, 8000)
        self.assertEqual(controller.acknowledge(1000), "fast-recovery-complete")
        self.assertEqual(controller.congestion_window, 4000)

    def test_timeout_returns_to_one_segment(self) -> None:
        # 제한 시간 뒤 중복 ACK 상태가 남으면 다음 ACK가 잘못된 복구 전이를 택합니다.
        controller = RenoController(9000, 12000, 1000)
        controller.timeout()
        self.assertEqual(controller.congestion_window, 1000)
        self.assertEqual(controller.slow_start_threshold, 4500)


if __name__ == "__main__":
    unittest.main()
