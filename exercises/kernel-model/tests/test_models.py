"""상태 전이, policy, 자원 수명과 recovery를 단위별로 검증합니다."""
from __future__ import annotations
import unittest
from kernel_model.deadlock import DeadlockInputError, detect_deadlocked, find_wait_cycle, safe_sequence
from kernel_model.lifecycle import KernelState, TaskState
from kernel_model.paging import FaultKind, MemoryFault, MemoryManager, simulate_replacement
from kernel_model.scheduler import JobSpec, Policy, simulate
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

class SchedulerTests(unittest.TestCase):

    def test_round_robin_and_metrics(self) -> None:
        jobs = [JobSpec('A', 0, (4,)), JobSpec('B', 1, (2,))]
        result = simulate(jobs, Policy.RR, quantum=2)
        self.assertEqual([tick.running for tick in result.timeline], ['A', 'A', 'B', 'B', 'A', 'A'])
        self.assertEqual(result.completion_order, ('B', 'A'))
        self.assertEqual(result.metrics['A'].response, 0)
        self.assertEqual(result.metrics['B'].response, 1)
        self.assertEqual(result.cpu_busy_ticks, 6)

    def test_io_wait_moves_job_out_of_ready_queue(self) -> None:
        jobs = [JobSpec('A', 0, (1, 1), (2,)), JobSpec('B', 0, (2,))]
        result = simulate(jobs, Policy.FCFS)
        self.assertEqual(result.completion_order, ('B', 'A'))
        self.assertTrue(any((tid == 'A' for tick in result.timeline for tid, _ in tick.blocked)))

    def test_sjf_uses_current_cpu_burst(self) -> None:
        result = simulate([JobSpec('long', 0, (5,)), JobSpec('short', 0, (1,))], Policy.SJF)
        self.assertEqual(result.timeline[0].running, 'short')

    def test_rejects_invalid_quantum_and_duplicate_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Quantum'):
            simulate([JobSpec('A', 0, (1,))], Policy.RR, quantum=0)
        with self.assertRaisesRegex(ValueError, 'Duplicate job identifier'):
            simulate([JobSpec('A', 0, (1,)), JobSpec('A', 1, (1,))], Policy.FCFS)

class DeadlockTests(unittest.TestCase):

    def test_cycle_and_multiple_instance_detection(self) -> None:
        cycle = find_wait_cycle({'A': ['B'], 'B': ['C'], 'C': ['A']})
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle[0], cycle[-1])
        self.assertEqual(detect_deadlocked([0, 0], {'A': [1, 0], 'B': [0, 1]}, {'A': [0, 1], 'B': [1, 0]}), {'A', 'B'})

    def test_safe_sequence(self) -> None:
        sequence = safe_sequence([1, 1], {'A': [1, 0], 'B': [0, 1]}, {'A': [1, 1], 'B': [1, 1]})
        self.assertIsNotNone(sequence)
        self.assertEqual(set(sequence or []), {'A', 'B'})

    def test_rejects_vector_shape_mismatch(self) -> None:
        with self.assertRaises(DeadlockInputError):
            detect_deadlocked([0], {'A': [1, 0]}, {'A': [0, 1]})

class PagingTests(unittest.TestCase):

    def test_demand_zero_and_copy_on_write(self) -> None:
        memory = MemoryManager(max_frames=8)
        memory.create_process('parent')
        memory.map_demand_zero('parent', 0)
        self.assertEqual(memory.read('parent', 0), 0)
        self.assertIsNone(memory.write('parent', 0, 7))
        memory.fork('parent', 'child')
        self.assertEqual(memory.read('child', 0), 7)
        self.assertEqual(memory.write('child', 0, 9), FaultKind.COPY_ON_WRITE)
        self.assertEqual(memory.read('parent', 0), 7)
        self.assertEqual(memory.read('child', 0), 9)
        self.assertEqual(len(memory.frames), 2)
        memory.assert_invariants()

    def test_write_protection_fault(self) -> None:
        memory = MemoryManager()
        memory.create_process('p')
        memory.map_value('p', 1, 5, writable=False)
        with self.assertRaises(MemoryFault) as context:
            memory.write('p', 1, 6)
        self.assertEqual(context.exception.kind, FaultKind.PROTECTION)

    def test_read_only_demand_zero_write_does_not_allocate(self) -> None:
        memory = MemoryManager()
        memory.create_process('p')
        memory.map_demand_zero('p', 2, writable=False)
        with self.assertRaises(MemoryFault) as context:
            memory.write('p', 2, 1)
        self.assertEqual(context.exception.kind, FaultKind.PROTECTION)
        self.assertEqual(memory.frames, {})
        self.assertFalse(memory.spaces['p'].pages[2].present)

    def test_replacement_policies_have_bounded_results(self) -> None:
        references = [1, 2, 3, 1, 4, 5]
        results = {policy: simulate_replacement(references, 3, policy) for policy in ('fifo', 'lru', 'clock')}
        self.assertEqual(results['fifo'].faults, 5)
        self.assertEqual(results['lru'].faults, 5)
        self.assertTrue(4 <= results['clock'].faults <= 6)
if __name__ == '__main__':
    unittest.main()
