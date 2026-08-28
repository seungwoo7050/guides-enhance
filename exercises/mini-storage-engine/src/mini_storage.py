from __future__ import annotations

import struct
from bisect import bisect_left
from dataclasses import dataclass
from typing import Literal

# [Implementation 1] page, slot, record의 binary layout을 정합니다.
# 메모리와 disk에서 같은 network byte order를 사용해 직렬화 결과를 일정하게 유지합니다.
PAGE_HEADER = struct.Struct("!4sQHH")
PAGE_SLOT = struct.Struct("!HH")
RECORD_HEADER = struct.Struct("!qI")
PAGE_MAGIC = b"MSTG"
MAX_PAGE_SIZE = 65535


class WALViolation(RuntimeError):
    """dirty page가 관련 WAL보다 먼저 disk에 기록될 때 발생합니다."""


class DuplicateKeyError(RuntimeError):
    """이미 존재하는 key를 다시 삽입할 때 발생합니다."""


class PageFull(RuntimeError):
    """인코딩한 record가 heap page에 들어가지 않을 때 발생합니다."""


def _validate_key(key: int) -> int:
    if isinstance(key, bool) or not isinstance(key, int):
        raise TypeError("key must be int")
    if not -(2**63) <= key < 2**63:
        raise ValueError("key exceeds signed 64-bit record format")
    return key


def _validate_value(value: bytes) -> bytes:
    if not isinstance(value, bytes):
        raise TypeError("value must be bytes")
    if not value:
        raise ValueError("value must be non-empty bytes")
    if len(value) >= 2**32:
        raise ValueError("value exceeds record length format")
    return value


# [Implementation 2] SlottedPage가 page_id, page_lsn, bytes와 slot 기반 RID를 관리합니다.
# record 위치가 바뀌어도 외부에서는 (page_id, slot_id)를 사용합니다.
class SlottedPage:
    def __init__(self, page_id: int, size: int) -> None:
        if isinstance(page_id, bool) or not isinstance(page_id, int):
            raise TypeError("page_id must be int")
        if page_id < 0:
            raise ValueError("page_id must be non-negative")
        if isinstance(size, bool) or not isinstance(size, int):
            raise TypeError("size must be int")
        minimum = PAGE_HEADER.size + PAGE_SLOT.size + RECORD_HEADER.size + 1
        if size < minimum:
            raise ValueError("page size is too small")
        if size > MAX_PAGE_SIZE:
            raise ValueError("page size exceeds on-page offset format")
        self.page_id = page_id
        self.size = size
        self.page_lsn = 0
        self._data = bytearray(size)
        self._slots: list[tuple[int, int]] = []
        self._free_end = size

    @property
    def free_space(self) -> int:
        return self._free_end - (PAGE_HEADER.size + len(self._slots) * PAGE_SLOT.size)

    # [Implementation 2-1] 입력과 남은 공간을 확인한 뒤 record를 삽입합니다.
    # 검증에 실패하면 record bytes와 slot 목록을 바꾸지 않습니다.
    def insert(self, key: int, value: bytes) -> int:
        key = _validate_key(key)
        value = _validate_value(value)
        record = RECORD_HEADER.pack(key, len(value)) + value
        if len(record) + PAGE_SLOT.size > self.free_space:
            raise PageFull("record does not fit")
        self._free_end -= len(record)
        self._data[self._free_end : self._free_end + len(record)] = record
        self._slots.append((self._free_end, len(record)))
        return len(self._slots) - 1

    def read(self, slot_id: int) -> tuple[int, bytes]:
        if isinstance(slot_id, bool) or not isinstance(slot_id, int) or slot_id < 0:
            raise KeyError(slot_id)
        try:
            offset, length = self._slots[slot_id]
        except IndexError as exc:
            raise KeyError(slot_id) from exc
        record = memoryview(self._data)[offset : offset + length]
        if len(record) < RECORD_HEADER.size:
            raise ValueError("corrupt record")
        key, value_length = RECORD_HEADER.unpack_from(record, 0)
        value = bytes(record[RECORD_HEADER.size :])
        if len(value) != value_length:
            raise ValueError("corrupt record length")
        return key, value

    def find_key(self, key: int) -> int | None:
        key = _validate_key(key)
        for slot_id in range(len(self._slots)):
            stored_key, _ = self.read(slot_id)
            if stored_key == key:
                return slot_id
        return None

    def records(self) -> list[tuple[int, int, bytes]]:
        return [(slot_id, *self.read(slot_id)) for slot_id in range(len(self._slots))]

    # [Implementation 2-2] page를 직렬화하고 외부 bytes를 검증합니다.
    # header와 slot 범위, record 길이, 연속 배치와 겹침을 확인한 뒤 SlottedPage를 만듭니다.
    def serialize(self) -> bytes:
        if self.page_lsn < 0 or self.page_lsn >= 2**64:
            raise ValueError("page_lsn exceeds header format")
        if len(self._slots) >= 2**16:
            raise ValueError("slot count exceeds header format")
        raw = bytearray(self._data)
        PAGE_HEADER.pack_into(
            raw,
            0,
            PAGE_MAGIC,
            self.page_lsn,
            len(self._slots),
            self._free_end,
        )
        for index, (offset, length) in enumerate(self._slots):
            PAGE_SLOT.pack_into(raw, PAGE_HEADER.size + index * PAGE_SLOT.size, offset, length)
        return bytes(raw)

    @classmethod
    def from_bytes(cls, page_id: int, raw: bytes) -> "SlottedPage":
        if not isinstance(raw, bytes):
            raise TypeError("raw page must be bytes")
        if len(raw) < PAGE_HEADER.size:
            raise ValueError("truncated page")
        if len(raw) > MAX_PAGE_SIZE:
            raise ValueError("page exceeds on-page offset format")

        magic, page_lsn, slot_count, free_end = PAGE_HEADER.unpack_from(raw, 0)
        if magic != PAGE_MAGIC:
            raise ValueError("invalid page magic")
        directory_end = PAGE_HEADER.size + slot_count * PAGE_SLOT.size
        if directory_end > free_end or free_end > len(raw):
            raise ValueError("corrupt page boundaries")

        slots: list[tuple[int, int]] = []
        ranges: list[tuple[int, int]] = []
        for index in range(slot_count):
            offset, length = PAGE_SLOT.unpack_from(raw, PAGE_HEADER.size + index * PAGE_SLOT.size)
            if length < RECORD_HEADER.size + 1:
                raise ValueError("corrupt slot length")
            if offset < free_end or offset + length > len(raw):
                raise ValueError("corrupt slot range")
            slots.append((offset, length))
            ranges.append((offset, offset + length))

        ranges.sort()
        if ranges:
            if ranges[0][0] != free_end or ranges[-1][1] != len(raw):
                raise ValueError("record region is not contiguous")
            if any(left_end != right_start for (_, left_end), (right_start, _) in zip(ranges, ranges[1:])):
                raise ValueError("record slots overlap or leave gaps")
        elif free_end != len(raw):
            raise ValueError("empty page has an invalid free boundary")

        page = cls(page_id, len(raw))
        page._data[:] = raw
        page.page_lsn = page_lsn
        page._free_end = free_end
        page._slots = slots
        for slot_id in range(slot_count):
            page.read(slot_id)
        return page


# [Implementation 3] page_id를 할당하고 직렬화된 page를 저장합니다.
# DiskManager가 고정 크기 page bytes와 다음 page_id를 보관합니다.
class DiskManager:
    def __init__(self, page_size: int = 256) -> None:
        if isinstance(page_size, bool) or not isinstance(page_size, int):
            raise TypeError("page_size must be int")
        if page_size < 96:
            raise ValueError("page_size must be at least 96")
        if page_size > MAX_PAGE_SIZE:
            raise ValueError("page_size exceeds on-page offset format")
        self.page_size = page_size
        self.pages: dict[int, bytes] = {}
        self._next_page_id = 0
        self.write_events: list[tuple[int, int]] = []

    def allocate(self) -> int:
        page_id = self._next_page_id
        self._next_page_id += 1
        self.pages[page_id] = SlottedPage(page_id, self.page_size).serialize()
        return page_id

    def read(self, page_id: int) -> SlottedPage:
        try:
            raw = self.pages[page_id]
        except KeyError as exc:
            raise KeyError(page_id) from exc
        return SlottedPage.from_bytes(page_id, raw)

    def write(self, page: SlottedPage) -> None:
        if page.page_id not in self.pages:
            raise KeyError(page.page_id)
        if page.size != self.page_size:
            raise ValueError("page size does not match disk manager")
        self.pages[page.page_id] = page.serialize()
        self.write_events.append((page.page_id, page.page_lsn))

    @property
    def page_ids(self) -> list[int]:
        return sorted(self.pages)


# [Implementation 4] INSERT와 COMMIT WAL을 append-only로 기록합니다.
# LogManager가 LSN과 txid 이력을 보관하며 flushed_lsn은 뒤로 이동하지 않습니다.
@dataclass(frozen=True)
class LogRecord:
    lsn: int
    txid: int
    kind: Literal["INSERT", "COMMIT"]
    page_id: int | None = None
    key: int | None = None
    value: bytes | None = None


class LogManager:
    def __init__(self, records: list[LogRecord] | None = None, flushed_lsn: int = 0) -> None:
        self.records = list(records or [])
        self._validate_history(self.records)
        maximum_lsn = max((record.lsn for record in self.records), default=0)
        if isinstance(flushed_lsn, bool) or not isinstance(flushed_lsn, int):
            raise TypeError("flushed_lsn must be int")
        if flushed_lsn < 0 or flushed_lsn > maximum_lsn:
            raise ValueError("flushed_lsn is outside log history")
        self.next_lsn = maximum_lsn + 1
        self.flushed_lsn = flushed_lsn
        self.flush_events: list[int] = []

    @staticmethod
    def _validate_history(records: list[LogRecord]) -> None:
        previous_lsn = 0
        for record in records:
            if record.lsn <= previous_lsn:
                raise ValueError("log records must have increasing LSNs")
            if record.txid <= 0:
                raise ValueError("txid must be positive")
            if record.kind == "INSERT":
                if record.page_id is None or record.key is None or record.value is None:
                    raise ValueError("INSERT record is incomplete")
                if record.page_id < 0:
                    raise ValueError("page_id must be non-negative")
                _validate_key(record.key)
                _validate_value(record.value)
            elif record.kind == "COMMIT":
                if record.page_id is not None or record.key is not None or record.value is not None:
                    raise ValueError("COMMIT record contains insert fields")
            else:
                raise ValueError("unknown log record kind")
            previous_lsn = record.lsn

    @staticmethod
    def _validate_txid(txid: int) -> int:
        if isinstance(txid, bool) or not isinstance(txid, int):
            raise TypeError("txid must be int")
        if txid <= 0:
            raise ValueError("txid must be positive")
        return txid

    def _append(self, record: LogRecord) -> int:
        self.records.append(record)
        self.next_lsn += 1
        return record.lsn

    def insert(self, txid: int, page_id: int, key: int, value: bytes) -> int:
        txid = self._validate_txid(txid)
        if isinstance(page_id, bool) or not isinstance(page_id, int):
            raise TypeError("page_id must be int")
        if page_id < 0:
            raise ValueError("page_id must be non-negative")
        key = _validate_key(key)
        value = _validate_value(value)
        return self._append(LogRecord(self.next_lsn, txid, "INSERT", page_id, key, value))

    def commit(self, txid: int) -> int:
        txid = self._validate_txid(txid)
        return self._append(LogRecord(self.next_lsn, txid, "COMMIT"))

    def flush(self, lsn: int) -> None:
        if isinstance(lsn, bool) or not isinstance(lsn, int):
            raise TypeError("lsn must be int")
        if lsn < self.flushed_lsn or not any(record.lsn == lsn for record in self.records):
            raise ValueError("cannot flush unknown or older LSN")
        self.flushed_lsn = lsn
        self.flush_events.append(lsn)

    def durable_records(self) -> list[LogRecord]:
        return [record for record in self.records if record.lsn <= self.flushed_lsn]


# [Implementation 5] frame과 page table로 resident page를 관리합니다.
# 같은 page_id는 한 frame에만 올라가며 Clock hand가 다음 교체 후보를 가리킵니다.
@dataclass
class Frame:
    page: SlottedPage | None = None
    pin_count: int = 0
    dirty: bool = False
    referenced: bool = False


class BufferPool:
    def __init__(self, disk: DiskManager, log: LogManager, capacity: int = 2) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be int")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.disk = disk
        self.log = log
        self.frames = [Frame() for _ in range(capacity)]
        self.page_table: dict[int, int] = {}
        self.hand = 0

    # [Implementation 5-1] 새 page를 검증한 뒤 Clock 방식으로 frame을 교체합니다.
    # 읽기나 직렬화가 실패하면 기존 mapping을 유지하고, dirty victim은 먼저 flush합니다.
    def fetch(self, page_id: int) -> SlottedPage:
        resident = self.page_table.get(page_id)
        if resident is not None:
            frame = self.frames[resident]
            frame.pin_count += 1
            frame.referenced = True
            assert frame.page is not None
            return frame.page

        incoming = self.disk.read(page_id)
        index = self._victim()
        frame = self.frames[index]
        if frame.page is not None:
            self._flush_frame(frame)
            del self.page_table[frame.page.page_id]
        frame.page = incoming
        frame.pin_count = 1
        frame.dirty = False
        frame.referenced = True
        self.page_table[page_id] = index
        return incoming

    def _victim(self) -> int:
        for index, frame in enumerate(self.frames):
            if frame.page is None:
                self.hand = (index + 1) % len(self.frames)
                return index
        for _ in range(len(self.frames) * 2):
            index = self.hand
            frame = self.frames[index]
            self.hand = (self.hand + 1) % len(self.frames)
            if frame.pin_count > 0:
                continue
            if frame.referenced:
                frame.referenced = False
                continue
            return index
        raise RuntimeError("all buffer frames are pinned or recently referenced")

    def unpin(self, page_id: int, *, dirty: bool = False) -> None:
        try:
            frame = self.frames[self.page_table[page_id]]
        except KeyError as exc:
            raise KeyError(page_id) from exc
        if frame.pin_count == 0:
            raise RuntimeError("page is already unpinned")
        frame.pin_count -= 1
        frame.dirty = frame.dirty or dirty

    # [Implementation 5-2] page_lsn까지 WAL이 durable한 dirty page만 flush합니다.
    # 전체 page write가 성공한 뒤에만 dirty를 false로 바꿉니다.
    def _flush_frame(self, frame: Frame) -> None:
        if frame.page is None or not frame.dirty:
            return
        if frame.page.page_lsn > self.log.flushed_lsn:
            raise WALViolation("data page reached disk before its WAL record")
        self.disk.write(frame.page)
        frame.dirty = False

    def flush(self, page_id: int) -> None:
        try:
            frame = self.frames[self.page_table[page_id]]
        except KeyError as exc:
            raise KeyError(page_id) from exc
        self._flush_frame(frame)

    def flush_all(self) -> None:
        for frame in self.frames:
            self._flush_frame(frame)


# [Implementation 6] 정렬된 leaf 배열에서 key와 RID를 관리합니다.
# key는 유일하며 leaf가 가득 차면 나누고, 각 key는 하나의 (page_id, slot_id)를 가리킵니다.
class OrderedLeafIndex:
    def __init__(self, leaf_capacity: int = 4) -> None:
        if isinstance(leaf_capacity, bool) or not isinstance(leaf_capacity, int):
            raise TypeError("leaf_capacity must be int")
        if leaf_capacity < 2:
            raise ValueError("leaf_capacity must be at least 2")
        self.leaf_capacity = leaf_capacity
        self.leaves: list[list[tuple[int, tuple[int, int]]]] = [[]]

    def insert(self, key: int, rid: tuple[int, int]) -> None:
        key = _validate_key(key)
        if (
            not isinstance(rid, tuple)
            or len(rid) != 2
            or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in rid)
        ):
            raise TypeError("rid must be a pair of non-negative integers")
        leaf_index = self._leaf_index(key)
        leaf = self.leaves[leaf_index]
        position = bisect_left([item[0] for item in leaf], key)
        if position < len(leaf) and leaf[position][0] == key:
            raise DuplicateKeyError(key)
        leaf.insert(position, (key, rid))
        if len(leaf) > self.leaf_capacity:
            split = len(leaf) // 2
            self.leaves.insert(leaf_index + 1, leaf[split:])
            del leaf[split:]

    def _leaf_index(self, key: int) -> int:
        for index, leaf in enumerate(self.leaves):
            if not leaf or key <= leaf[-1][0]:
                return index
        return len(self.leaves) - 1

    def get(self, key: int) -> tuple[int, int]:
        key = _validate_key(key)
        leaf = self.leaves[self._leaf_index(key)]
        position = bisect_left([item[0] for item in leaf], key)
        if position == len(leaf) or leaf[position][0] != key:
            raise KeyError(key)
        return leaf[position][1]

    def range(self, start: int, end: int) -> list[tuple[int, tuple[int, int]]]:
        start = _validate_key(start)
        end = _validate_key(end)
        if start > end:
            return []
        return [item for leaf in self.leaves for item in leaf if start <= item[0] <= end]

    def validate(self) -> None:
        if not self.leaves:
            raise AssertionError("index must retain one leaf")
        flattened: list[int] = []
        for index, leaf in enumerate(self.leaves):
            if not leaf and len(self.leaves) > 1:
                raise AssertionError("non-singleton index contains an empty leaf")
            if len(leaf) > self.leaf_capacity:
                raise AssertionError("leaf exceeds capacity")
            keys = [key for key, _ in leaf]
            if any(left >= right for left, right in zip(keys, keys[1:])):
                raise AssertionError("leaf keys are not strictly increasing")
            flattened.extend(keys)
            if index and self.leaves[index - 1] and leaf:
                if self.leaves[index - 1][-1][0] >= leaf[0][0]:
                    raise AssertionError("leaf ranges overlap")
        if len(flattened) != len(set(flattened)):
            raise AssertionError("duplicate key in index")


# [Implementation 7] disk, WAL, buffer, index를 조합하고 다음 txid를 관리합니다.
# MiniStorageEngine이 한 insert를 구성 요소별 호출 순서로 묶습니다.
class MiniStorageEngine:
    def __init__(
        self,
        disk: DiskManager | None = None,
        log: LogManager | None = None,
        *,
        buffer_capacity: int = 2,
    ) -> None:
        self.disk = disk or DiskManager()
        self.log = log or LogManager()
        self.buffer = BufferPool(self.disk, self.log, buffer_capacity)
        self.index = OrderedLeafIndex()
        self._next_txid = max((record.txid for record in self.log.records), default=0) + 1
        if not self.disk.page_ids:
            self.disk.allocate()
        self._rebuild_index()

    # [Implementation 7-1] durable heap의 live record를 읽어 index를 다시 만듭니다.
    # index 자체는 저장하지 않으며, 복구 뒤 page의 실제 RID를 기준으로 재생성합니다.
    def _rebuild_index(self) -> None:
        rebuilt = OrderedLeafIndex()
        for page_id in self.disk.page_ids:
            page = self.disk.read(page_id)
            for slot_id, key, _ in page.records():
                rebuilt.insert(key, (page_id, slot_id))
        rebuilt.validate()
        self.index = rebuilt

    # [Implementation 7-2] page를 하나씩 확인하고 반드시 unpin한 뒤 삽입 대상을 정합니다.
    # 기존 page에 공간이 없을 때만 새 page_id를 할당합니다.
    def _choose_page(self, value: bytes) -> int:
        needed = RECORD_HEADER.size + len(value) + PAGE_SLOT.size
        empty_capacity = self.disk.page_size - PAGE_HEADER.size
        if needed > empty_capacity:
            raise PageFull("record does not fit in an empty page")
        for page_id in self.disk.page_ids:
            page = self.buffer.fetch(page_id)
            try:
                fits = page.free_space >= needed
            finally:
                self.buffer.unpin(page_id)
            if fits:
                return page_id
        return self.disk.allocate()

    # [Implementation 8] WAL을 먼저 기록하는 auto-commit insert를 수행합니다.
    # INSERT WAL 뒤 page를 바꾸고, COMMIT WAL을 flush한 다음에만 RID를 index에 공개합니다.
    def insert(self, key: int, value: bytes) -> None:
        key = _validate_key(key)
        value = _validate_value(value)
        try:
            self.index.get(key)
        except KeyError:
            pass
        else:
            raise DuplicateKeyError(key)

        page_id = self._choose_page(value)
        txid = self._next_txid
        self._next_txid += 1
        insert_lsn = self.log.insert(txid, page_id, key, value)
        page = self.buffer.fetch(page_id)
        dirty = False
        try:
            slot_id = page.insert(key, value)
            page.page_lsn = insert_lsn
            dirty = True
        finally:
            self.buffer.unpin(page_id, dirty=dirty)
        commit_lsn = self.log.commit(txid)
        self.log.flush(commit_lsn)
        self.index.insert(key, (page_id, slot_id))
        self.index.validate()

    # [Implementation 9] index를 이용해 읽고 checkpoint에서 dirty page를 flush합니다.
    # point와 range 조회는 fetch마다 unpin하며, checkpoint는 WAL 조건을 만족한 frame만 기록합니다.
    def get(self, key: int) -> bytes:
        page_id, slot_id = self.index.get(key)
        page = self.buffer.fetch(page_id)
        try:
            stored_key, value = page.read(slot_id)
            if stored_key != key:
                raise RuntimeError("index points to a different key")
            return value
        finally:
            self.buffer.unpin(page_id)

    def range(self, start: int, end: int) -> list[tuple[int, bytes]]:
        return [(key, self.get(key)) for key, _ in self.index.range(start, end)]

    def checkpoint(self) -> None:
        self.buffer.flush_all()

    @staticmethod
    def _committed_transactions(records: list[LogRecord]) -> set[int]:
        state: dict[int, str] = {}
        committed: set[int] = set()
        for record in records:
            current = state.get(record.txid)
            if record.kind == "INSERT":
                if current is not None:
                    raise ValueError("transaction contains duplicate or post-commit INSERT")
                state[record.txid] = "INSERTED"
            else:
                if current != "INSERTED":
                    raise ValueError("COMMIT does not follow exactly one INSERT")
                state[record.txid] = "COMMITTED"
                committed.add(record.txid)
        return committed

    # [Implementation 10] durable COMMIT이 있는 INSERT만 다시 적용합니다.
    # heap을 처음부터 만들며 미완료 record를 제거하고 다음 txid를 durable log의 최댓값 뒤로 옮깁니다.
    @classmethod
    def recover(
        cls,
        disk: DiskManager,
        durable_records: list[LogRecord],
        *,
        buffer_capacity: int = 2,
    ) -> "MiniStorageEngine":
        durable_lsn = max((record.lsn for record in durable_records), default=0)
        log = LogManager(durable_records, durable_lsn)
        committed = cls._committed_transactions(durable_records)

        # 이 구현은 WAL 전체를 보존하고, 복구할 때 heap page를 처음부터 다시 만듭니다.
        # 미완료 record가 disk에 기록됐더라도 COMMIT이 없는 INSERT는 재적용하지 않습니다.
        page_ids = set(disk.page_ids)
        page_ids.update(
            record.page_id
            for record in durable_records
            if record.kind == "INSERT" and record.page_id is not None
        )
        if not page_ids:
            page_ids.add(0)
        disk.pages = {
            page_id: SlottedPage(page_id, disk.page_size).serialize()
            for page_id in sorted(page_ids)
        }
        disk._next_page_id = max(page_ids) + 1

        engine = cls(disk, log, buffer_capacity=buffer_capacity)
        engine._next_txid = max((record.txid for record in durable_records), default=0) + 1
        replayed_keys: set[int] = set()

        for record in durable_records:
            if record.kind != "INSERT" or record.txid not in committed:
                continue
            assert record.page_id is not None and record.key is not None and record.value is not None
            if record.key in replayed_keys:
                raise ValueError("durable committed history contains a duplicate key")
            page = engine.buffer.fetch(record.page_id)
            dirty = False
            try:
                page.insert(record.key, record.value)
                page.page_lsn = max(page.page_lsn, record.lsn)
                dirty = True
            finally:
                engine.buffer.unpin(record.page_id, dirty=dirty)
            replayed_keys.add(record.key)

        engine.buffer.flush_all()
        engine._rebuild_index()
        return engine
