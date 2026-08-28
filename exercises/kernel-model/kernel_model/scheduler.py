"""같은 workload에서 CPU scheduling 결과를 tick 단위로 재현합니다."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Policy(str, Enum):
    FCFS = "fcfs"
    SJF = "sjf"
    PRIORITY = "priority"
    RR = "rr"
    MLFQ = "mlfq"


# [Implementation 3] workload와 scheduling 결과 정의
@dataclass(frozen=True, slots=True)
class JobSpec:
    """CPU burst와 I/O wait를 번갈아 수행하는 작업입니다."""

    tid: str
    arrival: int
    cpu_bursts: tuple[int, ...]
    io_waits: tuple[int, ...] = ()
    priority: int = 0

    def validate(self) -> None:
        if not self.tid:
            raise ValueError("Job identifier cannot be empty")
        if self.arrival < 0:
            raise ValueError(f"Arrival time cannot be negative: {self.tid}")
        if not self.cpu_bursts or any(value <= 0 for value in self.cpu_bursts):
            raise ValueError(f"CPU bursts must be positive: {self.tid}")
        if len(self.io_waits) != len(self.cpu_bursts) - 1:
            raise ValueError(f"Each adjacent CPU burst requires one I/O wait: {self.tid}")
        if any(value <= 0 for value in self.io_waits):
            raise ValueError(f"I/O waits must be positive: {self.tid}")


@dataclass
class _RuntimeJob:
    spec: JobSpec
    burst_index: int = 0
    remaining: int = 0
    first_run: int | None = None
    completion: int | None = None
    wait_time: int = 0
    ready_order: int = 0
    queue_level: int = 0

    def __post_init__(self) -> None:
        self.remaining = self.spec.cpu_bursts[0]


@dataclass(frozen=True)
class Tick:
    time: int
    running: str | None
    ready: tuple[str, ...]
    blocked: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class JobMetrics:
    response: int
    waiting: int
    turnaround: int


@dataclass(frozen=True)
class ScheduleResult:
    policy: Policy
    timeline: tuple[Tick, ...]
    completion_order: tuple[str, ...]
    metrics: dict[str, JobMetrics]

    @property
    def makespan(self) -> int:
        return len(self.timeline)

    @property
    def cpu_busy_ticks(self) -> int:
        return sum(1 for tick in self.timeline if tick.running is not None)


# [Implementation 3-1] 실행 중 scheduling 상태
def simulate(
    jobs: Iterable[JobSpec],
    policy: Policy | str,
    *,
    quantum: int = 2,
    max_time: int = 100_000,
) -> ScheduleResult:
    """선택한 policy로 작업을 한 tick씩 실행합니다."""

    selected_policy = Policy(policy)
    if quantum <= 0:
        raise ValueError("Quantum must be positive")
    if max_time <= 0:
        raise ValueError("Maximum simulation time must be positive")

    specs = list(jobs)
    if not specs:
        return ScheduleResult(selected_policy, (), (), {})

    seen: set[str] = set()
    for spec in specs:
        spec.validate()
        if spec.tid in seen:
            raise ValueError(f"Duplicate job identifier: {spec.tid}")
        seen.add(spec.tid)

    runtimes = {spec.tid: _RuntimeJob(spec) for spec in specs}
    not_arrived = sorted(specs, key=lambda item: (item.arrival, item.tid))
    ready: list[str] = []
    blocked: dict[str, int] = {}
    running: str | None = None
    quantum_used = 0
    order_counter = 0
    time = 0
    timeline: list[Tick] = []
    completion_order: list[str] = []

    def enqueue(tid: str, *, promote: bool = False) -> None:
        nonlocal order_counter
        runtime = runtimes[tid]
        if promote:
            runtime.queue_level = max(0, runtime.queue_level - 1)
        runtime.ready_order = order_counter
        order_counter += 1
        ready.append(tid)

    # [Implementation 3-2] 재현 가능한 작업 선택
    def choose() -> str:
        if selected_policy in (Policy.FCFS, Policy.RR):
            index = min(range(len(ready)), key=lambda i: runtimes[ready[i]].ready_order)
        elif selected_policy is Policy.SJF:
            index = min(
                range(len(ready)),
                key=lambda i: (
                    runtimes[ready[i]].remaining,
                    runtimes[ready[i]].ready_order,
                    ready[i],
                ),
            )
        elif selected_policy is Policy.PRIORITY:
            index = min(
                range(len(ready)),
                key=lambda i: (
                    runtimes[ready[i]].spec.priority,
                    runtimes[ready[i]].ready_order,
                    ready[i],
                ),
            )
        else:
            index = min(
                range(len(ready)),
                key=lambda i: (
                    runtimes[ready[i]].queue_level,
                    runtimes[ready[i]].ready_order,
                    ready[i],
                ),
            )
        return ready.pop(index)

    # [Implementation 3-3] tick 사건 처리 순서
    # 같은 시각의 arrival와 wakeup 처리 순서를 고정해야
    # timeline과 metric을 반복 재현할 수 있습니다.
    while len(completion_order) < len(specs):
        if time >= max_time:
            raise RuntimeError("Scheduling simulation exceeded its maximum time")

        while not_arrived and not_arrived[0].arrival <= time:
            spec = not_arrived.pop(0)
            enqueue(spec.tid)

        for tid, wake_time in sorted(list(blocked.items())):
            if wake_time <= time:
                blocked.pop(tid)
                enqueue(tid, promote=selected_policy is Policy.MLFQ)

        if running is None and ready:
            running = choose()
            quantum_used = 0
            runtime = runtimes[running]
            if runtime.first_run is None:
                runtime.first_run = time

        timeline.append(
            Tick(
                time=time,
                running=running,
                ready=tuple(sorted(ready, key=lambda tid: runtimes[tid].ready_order)),
                blocked=tuple(sorted(blocked.items())),
            )
        )

        for tid in ready:
            runtimes[tid].wait_time += 1

        if running is not None:
            runtime = runtimes[running]
            runtime.remaining -= 1
            quantum_used += 1
            if runtime.remaining == 0:
                end_time = time + 1
                if runtime.burst_index + 1 == len(runtime.spec.cpu_bursts):
                    runtime.completion = end_time
                    completion_order.append(running)
                else:
                    io_wait = runtime.spec.io_waits[runtime.burst_index]
                    runtime.burst_index += 1
                    runtime.remaining = runtime.spec.cpu_bursts[runtime.burst_index]
                    blocked[running] = end_time + io_wait
                running = None
                quantum_used = 0
            else:
                expired = False
                if selected_policy is Policy.RR and quantum_used >= quantum:
                    expired = True
                elif selected_policy is Policy.MLFQ:
                    level_quantum = quantum * (2**runtime.queue_level)
                    expired = quantum_used >= level_quantum
                if expired:
                    tid = running
                    running = None
                    quantum_used = 0
                    if selected_policy is Policy.MLFQ:
                        runtime.queue_level = min(runtime.queue_level + 1, 3)
                    enqueue(tid)

        time += 1

    metrics: dict[str, JobMetrics] = {}
    for tid, runtime in runtimes.items():
        if runtime.first_run is None or runtime.completion is None:
            raise RuntimeError(f"Job did not complete: {tid}")
        metrics[tid] = JobMetrics(
            response=runtime.first_run - runtime.spec.arrival,
            waiting=runtime.wait_time,
            turnaround=runtime.completion - runtime.spec.arrival,
        )

    return ScheduleResult(
        policy=selected_policy,
        timeline=tuple(timeline),
        completion_order=tuple(completion_order),
        metrics=metrics,
    )
