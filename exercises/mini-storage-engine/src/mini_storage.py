from __future__ import annotations

import struct
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
