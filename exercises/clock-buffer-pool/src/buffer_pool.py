from __future__ import annotations

from dataclasses import dataclass, field


class BufferPoolFull(RuntimeError):
    """교체할 수 있는 unpinned frame이 없을 때 발생합니다."""


# [Implementation 1] 고정 크기 page를 저장하고 I/O 횟수를 기록합니다.
# DiskManager가 page_id를 발급하며 read와 write가 실제로 일어난 횟수를 셉니다.
class DiskManager:
    def __init__(self, page_size: int = 64) -> None:
        if isinstance(page_size, bool) or not isinstance(page_size, int):
            raise TypeError("page_size must be int")
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        self.page_size = page_size
        self.pages: dict[int, bytes] = {}
        self.read_count = 0
        self.write_count = 0
        self._next_page_id = 0

    def allocate(self, initial: bytes = b"") -> int:
        if not isinstance(initial, bytes):
            raise TypeError("initial page must be bytes")
        if len(initial) > self.page_size:
            raise ValueError("initial page is too large")
        page_id = self._next_page_id
        self._next_page_id += 1
        self.pages[page_id] = initial.ljust(self.page_size, b"\x00")
        return page_id

    def read(self, page_id: int) -> bytes:
        if page_id not in self.pages:
            raise KeyError(page_id)
        self.read_count += 1
        return self.pages[page_id]

    def write(self, page_id: int, data: bytes) -> None:
        if page_id not in self.pages:
            raise KeyError(page_id)
        if not isinstance(data, bytes):
            raise TypeError("page write must be bytes")
        if len(data) != self.page_size:
            raise ValueError("page write must match page_size")
        self.write_count += 1
        self.pages[page_id] = data


# [Implementation 2] frame과 page table로 resident mapping을 관리합니다.
# page_table의 frame index와 Frame.page_id가 항상 같은 page를 가리켜야 합니다.
@dataclass
class Frame:
    page_id: int | None = None
    data: bytearray = field(default_factory=bytearray)
    pin_count: int = 0
    dirty: bool = False
    referenced: bool = False


class BufferPool:
    def __init__(self, disk: DiskManager, capacity: int) -> None:
        if not isinstance(disk, DiskManager):
            raise TypeError("disk must be a DiskManager")
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be int")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.disk = disk
        self.frames = [Frame(data=bytearray(disk.page_size)) for _ in range(capacity)]
        self.page_table: dict[int, int] = {}
        self.hand = 0

    # [Implementation 3] cache hit를 재사용하고 miss 시 기존 mapping을 안전하게 교체합니다.
    # 없는 page는 victim 선택 전에 거부하며, dirty victim은 write가 끝난 뒤에만 다른 page로 바꿉니다.
    def fetch(self, page_id: int) -> bytearray:
        if page_id not in self.disk.pages:
            raise KeyError(page_id)

        resident = self.page_table.get(page_id)
        if resident is not None:
            frame = self.frames[resident]
            frame.pin_count += 1
            frame.referenced = True
            return frame.data

        frame_index = self._choose_victim()
        incoming = self.disk.read(page_id)
        frame = self.frames[frame_index]

        if frame.page_id is not None:
            if frame.dirty:
                self.disk.write(frame.page_id, bytes(frame.data))
            del self.page_table[frame.page_id]

        frame.page_id = page_id
        frame.data[:] = incoming
        frame.pin_count = 1
        frame.dirty = False
        frame.referenced = True
        self.page_table[page_id] = frame_index
        return frame.data

    # [Implementation 4] Clock 방식으로 교체할 frame을 고릅니다.
    # 빈 frame을 먼저 쓰고, referenced인 unpinned frame은 bit를 내린 뒤 한 번 더 기회를 줍니다.
    def _choose_victim(self) -> int:
        for index, frame in enumerate(self.frames):
            if frame.page_id is None:
                self.hand = (index + 1) % len(self.frames)
                return index

        inspected = 0
        limit = len(self.frames) * 2
        while inspected < limit:
            index = self.hand
            frame = self.frames[index]
            self.hand = (self.hand + 1) % len(self.frames)
            inspected += 1
            if frame.pin_count > 0:
                continue
            if frame.referenced:
                frame.referenced = False
                continue
            return index
        raise BufferPoolFull("all frames are pinned or recently referenced")

    # [Implementation 5] unpin으로 사용 중 표시를 반환하고 dirty 상태를 유지합니다.
    # 한 번 dirty가 되면 다른 호출자의 clean unpin으로 지우지 않으며, 성공한 flush 뒤에만 해제합니다.
    def unpin(self, page_id: int, *, dirty: bool = False) -> None:
        try:
            frame = self.frames[self.page_table[page_id]]
        except KeyError as exc:
            raise KeyError(page_id) from exc
        if frame.pin_count == 0:
            raise RuntimeError("page is already unpinned")
        frame.pin_count -= 1
        frame.dirty = frame.dirty or dirty

    # [Implementation 6] dirty page를 disk에 기록합니다.
    # write가 성공한 경우에만 dirty를 false로 바꿉니다.
    def flush(self, page_id: int) -> None:
        try:
            frame = self.frames[self.page_table[page_id]]
        except KeyError as exc:
            raise KeyError(page_id) from exc
        if frame.dirty:
            self.disk.write(page_id, bytes(frame.data))
            frame.dirty = False

    def flush_all(self) -> None:
        for page_id in list(self.page_table):
            self.flush(page_id)
