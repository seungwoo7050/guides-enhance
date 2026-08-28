"""주소 공간, page fault, COW와 page replacement를 모델링합니다."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping


# [Implementation 5] 가상 메모리 상태 정의
class FaultKind(str, Enum):
    NOT_MAPPED = "not-mapped"
    NOT_PRESENT = "not-present"
    PROTECTION = "protection"
    COPY_ON_WRITE = "copy-on-write"


class MemoryFault(RuntimeError):
    """memory access를 계속하려면 모델의 fault 처리가 필요할 때 발생합니다."""

    def __init__(self, kind: FaultKind, pid: str, vpn: int, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.pid = pid
        self.vpn = vpn


class MemoryInvariantError(ValueError):
    """PTE와 physical frame 참조 수가 맞지 않을 때 발생합니다."""


@dataclass
class PageTableEntry:
    frame: int | None = None
    present: bool = False
    readable: bool = True
    writable: bool = False
    cow: bool = False
    backing_value: int = 0

    def clone(self) -> "PageTableEntry":
        return PageTableEntry(
            frame=self.frame,
            present=self.present,
            readable=self.readable,
            writable=self.writable,
            cow=self.cow,
            backing_value=self.backing_value,
        )


@dataclass
class Frame:
    value: int
    refcount: int = 1
    dirty: bool = False
    referenced: bool = False


@dataclass
class AddressSpace:
    pid: str
    pages: dict[int, PageTableEntry] = field(default_factory=dict)


# [Implementation 5-1] mapping과 frame 수명 관리
@dataclass
class MemoryManager:
    """physical page 하나에 정수 값 하나를 저장합니다."""

    max_frames: int = 64
    spaces: dict[str, AddressSpace] = field(default_factory=dict)
    frames: dict[int, Frame] = field(default_factory=dict)
    _next_frame: int = 0

    def __post_init__(self) -> None:
        if self.max_frames <= 0:
            raise ValueError("Physical frame count must be positive")

    def create_process(self, pid: str) -> None:
        if not pid or pid in self.spaces:
            raise ValueError(f"Invalid process identifier: {pid!r}")
        self.spaces[pid] = AddressSpace(pid)

    def map_demand_zero(self, pid: str, vpn: int, *, writable: bool = True) -> None:
        space = self._space(pid)
        self._validate_vpn(vpn)
        if vpn in space.pages:
            raise MemoryInvariantError(f"Virtual page is already mapped: {pid}:{vpn}")
        space.pages[vpn] = PageTableEntry(
            present=False,
            readable=True,
            writable=writable,
            cow=False,
            backing_value=0,
        )
        self.assert_invariants()

    def map_value(self, pid: str, vpn: int, value: int, *, writable: bool = True) -> None:
        space = self._space(pid)
        self._validate_vpn(vpn)
        if vpn in space.pages:
            raise MemoryInvariantError(f"Virtual page is already mapped: {pid}:{vpn}")
        frame_id = self._allocate_frame(value)
        space.pages[vpn] = PageTableEntry(
            frame=frame_id,
            present=True,
            readable=True,
            writable=writable,
            cow=False,
            backing_value=value,
        )
        self.assert_invariants()

    # [Implementation 5-2] memory access fault 분류
    def read(self, pid: str, vpn: int) -> int:
        entry = self._entry(pid, vpn)
        if not entry.readable:
            raise MemoryFault(FaultKind.PROTECTION, pid, vpn, "Page is not readable")
        self._ensure_present(pid, vpn, entry)
        assert entry.frame is not None
        frame = self.frames[entry.frame]
        frame.referenced = True
        return frame.value

    def write(self, pid: str, vpn: int, value: int) -> FaultKind | None:
        entry = self._entry(pid, vpn)
        if not entry.writable and not entry.cow:
            raise MemoryFault(FaultKind.PROTECTION, pid, vpn, "Page is not writable")
        self._ensure_present(pid, vpn, entry)
        fault: FaultKind | None = None
        if entry.cow:
            self._resolve_cow(entry)
            fault = FaultKind.COPY_ON_WRITE
        assert entry.frame is not None
        frame = self.frames[entry.frame]
        frame.value = value
        frame.dirty = True
        frame.referenced = True
        entry.backing_value = value
        self.assert_invariants()
        return fault

    # [Implementation 5-3] COW 공유와 분리
    def fork(self, parent_pid: str, child_pid: str) -> None:
        if not child_pid or child_pid in self.spaces:
            raise ValueError(f"Invalid child process identifier: {child_pid!r}")
        parent = self._space(parent_pid)
        child = AddressSpace(child_pid)
        # 공유 frame을 writable로 남기지 않도록
        # 부모와 자식 PTE를 함께 COW로 바꿉니다.
        for vpn, parent_entry in parent.pages.items():
            child_entry = parent_entry.clone()
            if parent_entry.present:
                if parent_entry.frame is None:
                    raise MemoryInvariantError("A present page has no physical frame")
                self.frames[parent_entry.frame].refcount += 1
                if parent_entry.writable or parent_entry.cow:
                    parent_entry.writable = False
                    parent_entry.cow = True
                    child_entry.writable = False
                    child_entry.cow = True
            child.pages[vpn] = child_entry
        self.spaces[child_pid] = child
        self.assert_invariants()

    def unmap(self, pid: str, vpn: int) -> None:
        space = self._space(pid)
        try:
            entry = space.pages.pop(vpn)
        except KeyError as exc:
            raise MemoryFault(FaultKind.NOT_MAPPED, pid, vpn, "Page is not mapped") from exc
        if entry.present:
            assert entry.frame is not None
            self._decref(entry.frame)
        self.assert_invariants()

    def destroy_process(self, pid: str) -> None:
        space = self._space(pid)
        for entry in space.pages.values():
            if entry.present:
                assert entry.frame is not None
                self._decref(entry.frame)
        self.spaces.pop(pid)
        self.assert_invariants()

    def snapshot(self) -> dict[str, Any]:
        return {
            "frames": {
                str(frame_id): {
                    "value": frame.value,
                    "refcount": frame.refcount,
                    "dirty": frame.dirty,
                    "referenced": frame.referenced,
                }
                for frame_id, frame in sorted(self.frames.items())
            },
            "spaces": {
                pid: {
                    str(vpn): {
                        "frame": entry.frame,
                        "present": entry.present,
                        "readable": entry.readable,
                        "writable": entry.writable,
                        "cow": entry.cow,
                        "backing_value": entry.backing_value,
                    }
                    for vpn, entry in sorted(space.pages.items())
                }
                for pid, space in sorted(self.spaces.items())
            },
        }

    # [Implementation 5-4] PTE·frame 불변식 검사
    def assert_invariants(self) -> None:
        references: dict[int, list[PageTableEntry]] = {
            frame_id: [] for frame_id in self.frames
        }
        for pid, space in self.spaces.items():
            for vpn, entry in space.pages.items():
                self._validate_vpn(vpn)
                if entry.present:
                    if entry.frame is None or entry.frame not in self.frames:
                        raise MemoryInvariantError(
                            f"Mapping references a missing frame: {pid}:{vpn}"
                        )
                    references[entry.frame].append(entry)
                elif entry.frame is not None:
                    raise MemoryInvariantError(
                        f"A non-present page references a frame: {pid}:{vpn}"
                    )
                if entry.cow and entry.writable:
                    raise MemoryInvariantError(
                        f"A COW page is writable at the same time: {pid}:{vpn}"
                    )

        for frame_id, frame in self.frames.items():
            actual = len(references[frame_id])
            if actual != frame.refcount:
                raise MemoryInvariantError(
                    "Frame refcount mismatch: "
                    f"frame={frame_id} stored={frame.refcount} actual={actual}"
                )
            if actual == 0:
                raise MemoryInvariantError(f"An unreferenced frame remains allocated: {frame_id}")
            if actual > 1 and any(entry.writable for entry in references[frame_id]):
                raise MemoryInvariantError(f"A shared frame is exposed as writable: {frame_id}")

    @classmethod
    def validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        raw_frames = snapshot.get("frames")
        raw_spaces = snapshot.get("spaces")
        if not isinstance(raw_frames, Mapping) or not isinstance(raw_spaces, Mapping):
            raise MemoryInvariantError("Memory snapshot has an invalid shape")

        manager = cls(max_frames=max(1, len(raw_frames) + 1))
        manager.frames = {}
        for raw_id, raw in raw_frames.items():
            if not isinstance(raw, Mapping):
                raise MemoryInvariantError("A frame entry has an invalid shape")
            frame_id = int(raw_id)
            manager.frames[frame_id] = Frame(
                value=int(raw.get("value", 0)),
                refcount=int(raw.get("refcount", 0)),
                dirty=bool(raw.get("dirty", False)),
                referenced=bool(raw.get("referenced", False)),
            )

        manager.spaces = {}
        for pid, raw_pages in raw_spaces.items():
            if not isinstance(raw_pages, Mapping):
                raise MemoryInvariantError("An address-space entry has an invalid shape")
            space = AddressSpace(str(pid))
            for raw_vpn, raw in raw_pages.items():
                if not isinstance(raw, Mapping):
                    raise MemoryInvariantError("A PTE entry has an invalid shape")
                frame = raw.get("frame")
                space.pages[int(raw_vpn)] = PageTableEntry(
                    frame=None if frame is None else int(frame),
                    present=bool(raw.get("present", False)),
                    readable=bool(raw.get("readable", True)),
                    writable=bool(raw.get("writable", False)),
                    cow=bool(raw.get("cow", False)),
                    backing_value=int(raw.get("backing_value", 0)),
                )
            manager.spaces[space.pid] = space
        manager.assert_invariants()

    def _space(self, pid: str) -> AddressSpace:
        try:
            return self.spaces[pid]
        except KeyError as exc:
            raise KeyError(f"Address space not found: {pid}") from exc

    def _entry(self, pid: str, vpn: int) -> PageTableEntry:
        self._validate_vpn(vpn)
        space = self._space(pid)
        try:
            return space.pages[vpn]
        except KeyError as exc:
            raise MemoryFault(
                FaultKind.NOT_MAPPED,
                pid,
                vpn,
                "Virtual page is not mapped",
            ) from exc

    def _ensure_present(self, pid: str, vpn: int, entry: PageTableEntry) -> None:
        if entry.present:
            return
        try:
            frame_id = self._allocate_frame(entry.backing_value)
        except MemoryError as exc:
            raise MemoryFault(
                FaultKind.NOT_PRESENT,
                pid,
                vpn,
                "No physical frame is available",
            ) from exc
        entry.frame = frame_id
        entry.present = True
        self.assert_invariants()

    def _resolve_cow(self, entry: PageTableEntry) -> None:
        if not entry.present or entry.frame is None or not entry.cow:
            raise MemoryInvariantError("Entry is not a valid COW resolution target")
        old_id = entry.frame
        old_frame = self.frames[old_id]
        # 마지막 참조라면 copy 없이
        # 같은 frame의 write 권한만 복구할 수 있습니다.
        if old_frame.refcount == 1:
            entry.cow = False
            entry.writable = True
            return
        new_id = self._allocate_frame(old_frame.value)
        self._decref(old_id)
        entry.frame = new_id
        entry.cow = False
        entry.writable = True

    def _allocate_frame(self, value: int) -> int:
        if len(self.frames) >= self.max_frames:
            raise MemoryError("No physical frame is available")
        frame_id = self._next_frame
        self._next_frame += 1
        self.frames[frame_id] = Frame(value=value)
        return frame_id

    def _decref(self, frame_id: int) -> None:
        frame = self.frames[frame_id]
        frame.refcount -= 1
        if frame.refcount < 0:
            raise MemoryInvariantError(f"Frame refcount became negative: {frame_id}")
        if frame.refcount == 0:
            self.frames.pop(frame_id)

    @staticmethod
    def _validate_vpn(vpn: int) -> None:
        if not isinstance(vpn, int) or vpn < 0:
            raise ValueError(f"VPN must be a non-negative integer: {vpn!r}")


@dataclass(frozen=True)
class ReplacementResult:
    policy: str
    faults: int
    evictions: tuple[int, ...]
    frames: tuple[int, ...]


# [Implementation 5-5] page replacement 실행
def simulate_replacement(
    references: Iterable[int],
    capacity: int,
    policy: str,
) -> ReplacementResult:
    """FIFO, LRU 또는 Clock으로 page reference를 실행합니다."""

    pages = list(references)
    if capacity <= 0:
        raise ValueError("Frame capacity must be positive")
    if any(not isinstance(page, int) or page < 0 for page in pages):
        raise ValueError("Page references must be non-negative integers")
    normalized = policy.lower()
    if normalized not in {"fifo", "lru", "clock"}:
        raise ValueError(f"Unsupported replacement policy: {policy}")

    if normalized == "fifo":
        frames: list[int] = []
        queue: deque[int] = deque()
        faults = 0
        evictions: list[int] = []
        for page in pages:
            if page in frames:
                continue
            faults += 1
            if len(frames) == capacity:
                victim = queue.popleft()
                frames.remove(victim)
                evictions.append(victim)
            frames.append(page)
            queue.append(page)
        return ReplacementResult(normalized, faults, tuple(evictions), tuple(frames))

    if normalized == "lru":
        frames = []
        last_used: dict[int, int] = {}
        faults = 0
        evictions = []
        for tick, page in enumerate(pages):
            if page not in frames:
                faults += 1
                if len(frames) == capacity:
                    victim = min(frames, key=lambda item: (last_used[item], item))
                    frames.remove(victim)
                    last_used.pop(victim)
                    evictions.append(victim)
                frames.append(page)
            last_used[page] = tick
        return ReplacementResult(normalized, faults, tuple(evictions), tuple(frames))

    frames = []
    referenced: dict[int, bool] = {}
    hand = 0
    faults = 0
    evictions = []
    for page in pages:
        if page in frames:
            referenced[page] = True
            continue
        faults += 1
        if len(frames) < capacity:
            frames.append(page)
            referenced[page] = True
            continue
        while referenced[frames[hand]]:
            referenced[frames[hand]] = False
            hand = (hand + 1) % capacity
        victim = frames[hand]
        evictions.append(victim)
        referenced.pop(victim)
        frames[hand] = page
        referenced[page] = True
        hand = (hand + 1) % capacity
    return ReplacementResult(normalized, faults, tuple(evictions), tuple(frames))
