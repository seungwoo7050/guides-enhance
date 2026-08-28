from __future__ import annotations

import struct
from dataclasses import dataclass

# [Implementation 1] page header와 slot의 binary format을 정합니다.
# directory는 앞에서, record는 뒤에서 자라므로 두 영역이 만나는 지점을 계산할 수 있어야 합니다.
HEADER = struct.Struct("!4sHH")
SLOT = struct.Struct("!HHB3x")
MAGIC = b"SLPG"


class PageFullError(RuntimeError):
    """레코드를 넣으면 page layout을 유지할 수 없을 때 발생합니다."""


# [Implementation 2] SlottedPage가 page bytes와 slot 상태를 관리합니다.
# 외부에서는 slot_id를 유지하고, record의 byte 위치만 page 안에서 바뀝니다.
@dataclass
class Slot:
    offset: int
    length: int
    alive: bool = True


class SlottedPage:
    def __init__(self, page_size: int = 256) -> None:
        if page_size < HEADER.size + SLOT.size + 1:
            raise ValueError("page_size is too small")
        if page_size > 65535:
            raise ValueError("page_size exceeds on-page offset format")
        self.page_size = page_size
        self._data = bytearray(page_size)
        self._slots: list[Slot] = []
        self._free_end = page_size

    @property
    def free_space(self) -> int:
        return self._free_end - (HEADER.size + len(self._slots) * SLOT.size)

    # [Implementation 3] page를 바꾸기 전에 payload와 slot을 검증합니다.
    # 검증에 실패하면 header, slot, record bytes가 하나도 바뀌지 않습니다.
    def _validate_payload(self, payload: bytes) -> bytes:
        if not isinstance(payload, bytes):
            raise TypeError("payload must be bytes")
        if not payload:
            raise ValueError("empty records are not supported")
        if len(payload) > 65535:
            raise ValueError("record is too large")
        return payload

    def _slot(self, slot_id: int) -> Slot:
        if isinstance(slot_id, bool) or not isinstance(slot_id, int) or slot_id < 0:
            raise KeyError(slot_id)
        try:
            slot = self._slots[slot_id]
        except IndexError as exc:
            raise KeyError(slot_id) from exc
        if not slot.alive:
            raise KeyError(slot_id)
        return slot

    # [Implementation 4] 수용 가능성을 확인한 뒤 insert하고 tombstone slot을 재사용합니다.
    # 공간이 절대 부족하면 compaction도 하지 않으며, 다른 slot_id는 바꾸지 않습니다.
    def insert(self, payload: bytes) -> int:
        payload = self._validate_payload(payload)
        reusable = next((index for index, slot in enumerate(self._slots) if not slot.alive), None)
        directory_cost = 0 if reusable is not None else SLOT.size

        # 절대 들어갈 수 없는 레코드는 compaction도 하지 않습니다.
        # 실패 전후의 직렬화 결과가 같아야 기존 page를 그대로 다시 사용할 수 있습니다.
        live_bytes = sum(slot.length for slot in self._slots if slot.alive)
        required = HEADER.size + len(self._slots) * SLOT.size + directory_cost + live_bytes + len(payload)
        if required > self.page_size:
            raise PageFullError("record does not fit in page")
        if len(payload) + directory_cost > self.free_space:
            self.compact()

        self._free_end -= len(payload)
        self._data[self._free_end : self._free_end + len(payload)] = payload
        new_slot = Slot(self._free_end, len(payload), True)
        if reusable is None:
            self._slots.append(new_slot)
            return len(self._slots) - 1
        self._slots[reusable] = new_slot
        return reusable

    # [Implementation 5] read, update, delete, compaction 중에도 slot_id를 유지합니다.
    # 필요한 경우 record bytes의 위치만 다시 계산합니다.
    def read(self, slot_id: int) -> bytes:
        slot = self._slot(slot_id)
        return bytes(self._data[slot.offset : slot.offset + slot.length])

    def delete(self, slot_id: int) -> None:
        slot = self._slot(slot_id)
        slot.alive = False
        slot.length = 0
        slot.offset = 0

    def update(self, slot_id: int, payload: bytes) -> None:
        payload = self._validate_payload(payload)
        slot = self._slot(slot_id)
        if len(payload) <= slot.length:
            self._data[slot.offset : slot.offset + len(payload)] = payload
            slot.length = len(payload)
            return

        live_bytes = sum(item.length for item in self._slots if item.alive)
        required = HEADER.size + len(self._slots) * SLOT.size + live_bytes - slot.length + len(payload)
        if required > self.page_size:
            raise PageFullError("update would overflow page")

        records: list[bytes | None] = [
            self.read(index) if item.alive else None
            for index, item in enumerate(self._slots)
        ]
        records[slot_id] = payload
        self._rebuild(records)

    def compact(self) -> None:
        records: list[bytes | None] = [
            self.read(index) if item.alive else None
            for index, item in enumerate(self._slots)
        ]
        self._rebuild(records)

    def _rebuild(self, records: list[bytes | None]) -> None:
        self._data = bytearray(self.page_size)
        self._free_end = self.page_size
        rebuilt: list[Slot] = []
        for payload in records:
            if payload is None:
                rebuilt.append(Slot(0, 0, False))
                continue
            self._free_end -= len(payload)
            self._data[self._free_end : self._free_end + len(payload)] = payload
            rebuilt.append(Slot(self._free_end, len(payload), True))
        self._slots = rebuilt
