"""상태 전이, policy, 자원 수명과 recovery를 단위별로 검증합니다."""
from __future__ import annotations
import unittest
from kernel_model.lifecycle import KernelState, TaskState

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
if __name__ == '__main__':
    unittest.main()
