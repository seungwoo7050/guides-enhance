"""상태 전이, policy, 자원 수명과 recovery를 단위별로 검증합니다."""
from __future__ import annotations
import unittest
from kernel_model.lifecycle import KernelState, TaskState
from kernel_model.synchronization import ConditionChannel, CountingSemaphore, SynchronizationError, WaitToken

class LifecycleTests(unittest.TestCase):

    def test_state_locations_remain_exclusive(self) -> None:
        model = KernelState()
        for tid in ('A', 'B'):
            model.add(tid)
            model.admit(tid)
        trace = [('dispatch-A', model.dispatch()), ('block-A', model.block('disk:0', 'read')), ('dispatch-B', model.dispatch()), ('preempt-B', model.preempt()), ('wake-A', model.wake_one('disk:0')), ('dispatch-B-again', model.dispatch()), ('exit-B', model.exit_running()), ('dispatch-A-again', model.dispatch()), ('exit-A', model.exit_running())]
        self.assertEqual(trace, [('dispatch-A', 'A'), ('block-A', 'A'), ('dispatch-B', 'B'), ('preempt-B', 'B'), ('wake-A', 'A'), ('dispatch-B-again', 'B'), ('exit-B', 'B'), ('dispatch-A-again', 'A'), ('exit-A', 'A')])
        model.assert_invariants()
        self.assertEqual(model.tasks['A'].state, TaskState.TERMINATED)
        self.assertEqual(model.completed, ['B', 'A'])

    def test_snapshot_rejects_duplicate_location(self) -> None:
        snapshot = {'running': 'A', 'ready': ['A'], 'wait_queues': {}, 'completed': [], 'tasks': {'A': {'state': 'running'}}}
        with self.assertRaisesRegex(ValueError, 'running task also appears'):
            KernelState.validate_snapshot(snapshot)

class SynchronizationTests(unittest.TestCase):

    def test_generation_closes_lost_wakeup_window(self) -> None:
        channel = ConditionChannel('items')
        token = channel.prepare_wait()
        self.assertIsNone(channel.notify_one())
        self.assertFalse(channel.commit_wait('consumer', token))
        self.assertNotIn('consumer', channel.waiters)
        fresh = channel.prepare_wait()
        self.assertTrue(channel.commit_wait('consumer', fresh))
        self.assertEqual(channel.notify_all(), ['consumer'])

    def test_semaphore_hands_permit_to_waiter(self) -> None:
        semaphore = CountingSemaphore(1)
        self.assertTrue(semaphore.acquire('A'))
        self.assertFalse(semaphore.acquire('B'))
        self.assertEqual(semaphore.release('A'), 'B')
        self.assertIn('B', semaphore.granted)
        self.assertIsNone(semaphore.release('B'))
        self.assertEqual(semaphore.permits, 1)
        semaphore.assert_invariants()

    def test_rejects_cross_channel_token_and_duplicate_owner(self) -> None:
        channel = ConditionChannel('items')
        with self.assertRaisesRegex(SynchronizationError, 'another condition channel'):
            channel.commit_wait('A', WaitToken('space', 0))
        semaphore = CountingSemaphore(1)
        self.assertTrue(semaphore.acquire('A'))
        with self.assertRaisesRegex(SynchronizationError, 'more than once'):
            semaphore.acquire('A')
if __name__ == '__main__':
    unittest.main()
