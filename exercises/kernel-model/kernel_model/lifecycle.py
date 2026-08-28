"""실행 주체의 상태 전이와 queue 위치를 함께 관리합니다."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Mapping


# [Implementation 1] 실행 상태와 위치 정의
class TaskState(str, Enum):
    """모델에서 사용하는 실행 상태입니다."""

    NEW = "new"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    TERMINATED = "terminated"


@dataclass(slots=True)
class Task:
    """실행 주체 하나에 속한 상태입니다."""

    tid: str
    state: TaskState = TaskState.NEW
    wait_channel: str | None = None
    block_reason: str | None = None
    transitions: list[str] = field(default_factory=list)

    def record(self, transition: str) -> None:
        self.transitions.append(transition)


class StateInvariantError(ValueError):
    """작업 상태와 실제 queue 위치가 다를 때 발생합니다."""


@dataclass
class KernelState:
    """CPU 하나와 ready queue 및 이름별 wait queue를 관리합니다."""

    tasks: dict[str, Task] = field(default_factory=dict)
    ready: Deque[str] = field(default_factory=deque)
    running: str | None = None
    wait_queues: dict[str, Deque[str]] = field(default_factory=dict)
    completed: list[str] = field(default_factory=list)

    # [Implementation 1-1] 생성·준비·실행 위치 이전
    def add(self, tid: str) -> Task:
        if not tid or tid in self.tasks:
            raise ValueError(f"Invalid new task identifier: {tid!r}")
        task = Task(tid=tid)
        self.tasks[tid] = task
        task.record("created")
        self.assert_invariants()
        return task

    def admit(self, tid: str) -> None:
        task = self._require(tid)
        if task.state is not TaskState.NEW:
            raise StateInvariantError(f"Only NEW tasks can be admitted: {tid}")
        task.state = TaskState.READY
        task.record("new->ready")
        self.ready.append(tid)
        self.assert_invariants()

    def dispatch(self) -> str | None:
        if self.running is not None:
            raise StateInvariantError("The CPU already owns a running task")
        if not self.ready:
            self.assert_invariants()
            return None
        tid = self.ready.popleft()
        task = self._require(tid)
        if task.state is not TaskState.READY:
            raise StateInvariantError(f"A ready-queue task is not READY: {tid}")
        task.state = TaskState.RUNNING
        task.record("ready->running")
        self.running = tid
        self.assert_invariants()
        return tid

    def preempt(self) -> str:
        task = self._running_task()
        self.running = None
        task.state = TaskState.READY
        task.record("running->ready:preempt")
        self.ready.append(task.tid)
        self.assert_invariants()
        return task.tid

    def yield_cpu(self) -> str:
        task = self._running_task()
        self.running = None
        task.state = TaskState.READY
        task.record("running->ready:yield")
        self.ready.append(task.tid)
        self.assert_invariants()
        return task.tid

    # [Implementation 1-2] 배타적인 실행 상태 전이
    def block(self, channel: str, reason: str) -> str:
        if not channel:
            raise ValueError("A wait channel cannot be empty")
        task = self._running_task()
        self.running = None
        task.state = TaskState.BLOCKED
        task.wait_channel = channel
        task.block_reason = reason
        task.record(f"running->blocked:{channel}")
        self.wait_queues.setdefault(channel, deque()).append(task.tid)
        self.assert_invariants()
        return task.tid

    def wake_one(self, channel: str) -> str | None:
        queue = self.wait_queues.get(channel)
        if not queue:
            self.assert_invariants()
            return None
        tid = queue.popleft()
        if not queue:
            self.wait_queues.pop(channel, None)
        task = self._require(tid)
        if task.state is not TaskState.BLOCKED or task.wait_channel != channel:
            raise StateInvariantError(f"Wait-queue ownership disagrees with task state: {tid}")
        task.state = TaskState.READY
        task.wait_channel = None
        task.block_reason = None
        task.record(f"blocked->ready:{channel}")
        self.ready.append(tid)
        self.assert_invariants()
        return tid

    def wake_all(self, channel: str) -> list[str]:
        awakened: list[str] = []
        while True:
            tid = self.wake_one(channel)
            if tid is None:
                break
            awakened.append(tid)
        return awakened

    def exit_running(self) -> str:
        task = self._running_task()
        self.running = None
        task.state = TaskState.TERMINATED
        task.wait_channel = None
        task.block_reason = None
        task.record("running->terminated")
        self.completed.append(task.tid)
        self.assert_invariants()
        return task.tid

    def snapshot(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "ready": list(self.ready),
            "wait_queues": {
                name: list(queue)
                for name, queue in sorted(self.wait_queues.items())
            },
            "completed": list(self.completed),
            "tasks": {
                tid: {
                    "state": task.state.value,
                    "wait_channel": task.wait_channel,
                    "block_reason": task.block_reason,
                    "transitions": list(task.transitions),
                }
                for tid, task in sorted(self.tasks.items())
            },
        }

    # [Implementation 1-3] 실행 상태 불변식 검사
    def assert_invariants(self) -> None:
        # state 값뿐 아니라 실제 container 위치도 맞아야 합니다.
        # 그렇지 않으면 scheduler가 작업을 잃거나 중복 실행할 수 있습니다.
        ready_items = list(self.ready)
        if len(set(ready_items)) != len(ready_items):
            raise StateInvariantError("A task appears more than once in the ready queue")
        if self.running is not None and self.running in ready_items:
            raise StateInvariantError("The running task also appears in the ready queue")

        blocked_locations: dict[str, str] = {}
        for channel, queue in self.wait_queues.items():
            if not channel:
                raise StateInvariantError("A wait queue has an empty name")
            for tid in queue:
                if tid in blocked_locations:
                    raise StateInvariantError(f"A task appears in multiple wait queues: {tid}")
                blocked_locations[tid] = channel

        completed_set = set(self.completed)
        if len(completed_set) != len(self.completed):
            raise StateInvariantError("A task appears more than once in the completion list")

        for tid, task in self.tasks.items():
            if task.tid != tid:
                raise StateInvariantError(
                    f"Task key and internal identifier disagree: key={tid} task={task.tid}"
                )
            in_ready = tid in ready_items
            is_running = tid == self.running
            wait_channel = blocked_locations.get(tid)
            in_completed = tid in completed_set

            if task.state is not TaskState.BLOCKED and (
                task.wait_channel is not None or task.block_reason is not None
            ):
                raise StateInvariantError(
                    f"A non-blocked task retains wait metadata: {tid}"
                )

            if task.state is TaskState.NEW:
                if in_ready or is_running or wait_channel is not None or in_completed:
                    raise StateInvariantError(f"A NEW task is exposed in execution structures: {tid}")
            elif task.state is TaskState.READY:
                if not in_ready or is_running or wait_channel is not None or in_completed:
                    raise StateInvariantError(f"A READY task has an invalid location: {tid}")
            elif task.state is TaskState.RUNNING:
                if not is_running or in_ready or wait_channel is not None or in_completed:
                    raise StateInvariantError(f"A RUNNING task has an invalid location: {tid}")
            elif task.state is TaskState.BLOCKED:
                if wait_channel is None or task.wait_channel != wait_channel:
                    raise StateInvariantError(
                        f"A BLOCKED task is not in its declared wait queue: {tid}"
                    )
                if not task.block_reason:
                    raise StateInvariantError(f"A BLOCKED task has no block reason: {tid}")
                if in_ready or is_running or in_completed:
                    raise StateInvariantError(
                        f"A BLOCKED task also appears in another execution location: {tid}"
                    )
            elif task.state is TaskState.TERMINATED:
                if not in_completed or in_ready or is_running or wait_channel is not None:
                    raise StateInvariantError(
                        f"A TERMINATED task has an invalid location: {tid}"
                    )

        if self.running is not None and self.running not in self.tasks:
            raise StateInvariantError("The CPU references a task that does not exist")
        for tid in ready_items + list(blocked_locations) + self.completed:
            if tid not in self.tasks:
                raise StateInvariantError(
                    f"An execution structure references a task that does not exist: {tid}"
                )

    @classmethod
    def validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        model = cls()
        task_data = snapshot.get("tasks")
        if not isinstance(task_data, Mapping):
            raise StateInvariantError("snapshot.tasks must be an object")
        for tid, raw in task_data.items():
            if not isinstance(tid, str) or not isinstance(raw, Mapping):
                raise StateInvariantError("A task entry has an invalid shape")
            state = TaskState(str(raw.get("state")))
            model.tasks[tid] = Task(
                tid=tid,
                state=state,
                wait_channel=raw.get("wait_channel"),
                block_reason=raw.get("block_reason"),
            )

        ready = snapshot.get("ready", [])
        completed = snapshot.get("completed", [])
        wait_queues = snapshot.get("wait_queues", {})
        if (
            not isinstance(ready, list)
            or not isinstance(completed, list)
            or not isinstance(wait_queues, Mapping)
        ):
            raise StateInvariantError("Snapshot queue fields have an invalid shape")

        model.ready = deque(str(item) for item in ready)
        running = snapshot.get("running")
        model.running = None if running is None else str(running)
        model.completed = [str(item) for item in completed]
        model.wait_queues = {
            str(channel): deque(str(item) for item in items)
            for channel, items in wait_queues.items()
            if isinstance(items, list)
        }
        if len(model.wait_queues) != len(wait_queues):
            raise StateInvariantError("Each wait queue must be an array")
        model.assert_invariants()

    def _require(self, tid: str) -> Task:
        try:
            return self.tasks[tid]
        except KeyError as exc:
            raise KeyError(f"Task not found: {tid}") from exc

    def _running_task(self) -> Task:
        if self.running is None:
            raise StateInvariantError("No task is currently running")
        task = self._require(self.running)
        if task.state is not TaskState.RUNNING:
            raise StateInvariantError("The running pointer disagrees with task state")
        return task
