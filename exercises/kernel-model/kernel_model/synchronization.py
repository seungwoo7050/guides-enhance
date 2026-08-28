"""조건 대기, semaphore permit과 lost wakeup을 모델링합니다."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


class SynchronizationError(ValueError):
    """대기자 또는 permit 상태가 서로 맞지 않을 때 발생합니다."""


# [Implementation 2] 대기 generation 정의
@dataclass(frozen=True, slots=True)
class WaitToken:
    """predicate를 확인한 시점의 channel generation을 기록합니다."""

    channel: str
    generation: int


@dataclass
class ConditionChannel:
    """predicate 확인과 wait 등록 사이에 발생한 notify를 놓치지 않습니다."""

    name: str
    generation: int = 0
    waiters: dict[str, int] = field(default_factory=dict)

    def prepare_wait(self) -> WaitToken:
        return WaitToken(channel=self.name, generation=self.generation)

    # [Implementation 2-1] lost wakeup 방지
    def commit_wait(self, tid: str, token: WaitToken) -> bool:
        if token.channel != self.name:
            raise SynchronizationError("The wait token belongs to another condition channel")
        if tid in self.waiters:
            raise SynchronizationError(f"Task is already waiting: {tid}")
        # prepare 이후 notify가 있었다면 waiter로 등록하지 않고
        # predicate를 다시 확인하게 합니다.
        if token.generation != self.generation:
            return False
        self.waiters[tid] = token.generation
        return True

    def cancel_wait(self, tid: str) -> bool:
        return self.waiters.pop(tid, None) is not None

    def notify_one(self) -> str | None:
        self.generation += 1
        if not self.waiters:
            return None
        tid = next(iter(self.waiters))
        self.waiters.pop(tid)
        return tid

    def notify_all(self) -> list[str]:
        self.generation += 1
        awakened = list(self.waiters)
        self.waiters.clear()
        return awakened


# [Implementation 2-2] semaphore permit 직접 이전
@dataclass
class CountingSemaphore:
    """permit을 받은 작업과 FIFO waiter를 따로 관리합니다."""

    permits: int
    waiters: deque[str] = field(default_factory=deque)
    granted: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.permits < 0:
            raise ValueError("Semaphore permits cannot be negative")

    def acquire(self, tid: str) -> bool:
        if tid in self.granted or tid in self.waiters:
            raise SynchronizationError(f"Task requested a permit more than once: {tid}")
        if self.permits > 0:
            self.permits -= 1
            self.granted.add(tid)
            return True
        self.waiters.append(tid)
        return False

    def release(self, tid: str) -> str | None:
        if tid not in self.granted:
            raise SynchronizationError(f"Task does not own a permit: {tid}")
        self.granted.remove(tid)
        if self.waiters:
            # permit을 숫자로 되돌리는 순간을 만들지 않고
            # 다음 waiter에게 바로 넘깁니다.
            awakened = self.waiters.popleft()
            self.granted.add(awakened)
            return awakened
        self.permits += 1
        return None

    def assert_invariants(self) -> None:
        if self.permits < 0:
            raise SynchronizationError("Permit count is negative")
        if len(set(self.waiters)) != len(self.waiters):
            raise SynchronizationError("The semaphore wait queue contains duplicates")
        if self.granted.intersection(self.waiters):
            raise SynchronizationError("A task is both a permit owner and a waiter")
