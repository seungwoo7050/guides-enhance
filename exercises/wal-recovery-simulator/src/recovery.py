from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal


class WALViolation(RuntimeError):
    """관련 WAL보다 data page가 먼저 disk에 기록될 때 발생합니다."""


# [Implementation 1] page 상태와 변경 이력을 별도로 표현합니다.
# Page는 현재 값과 page_lsn을 갖고, LogRecord는 before/after image를 바꾸지 않은 채 보관합니다.
@dataclass
class Page:
    value: int = 0
    page_lsn: int = 0


@dataclass(frozen=True)
class LogRecord:
    lsn: int
    txid: int
    kind: Literal["UPDATE", "COMMIT"]
    page_id: int | None = None
    before: int | None = None
    after: int | None = None


# [Implementation 2] 증가하는 LSN을 발급하고 durable 범위를 기록합니다.
# flush된 LSN은 뒤로 이동할 수 없으며, 존재하지 않는 LSN까지 flush할 수 없습니다.
class LogManager:
    def __init__(self) -> None:
        self.records: list[LogRecord] = []
        self.next_lsn = 1
        self.flushed_lsn = 0

    @staticmethod
    def _positive_identifier(value: int, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be int")
        if value <= 0:
            raise ValueError(f"{name} must be positive")
        return value

    @staticmethod
    def _page_identifier(value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("page_id must be int")
        if value < 0:
            raise ValueError("page_id must be non-negative")
        return value

    def _append(self, record: LogRecord) -> int:
        self.records.append(record)
        self.next_lsn += 1
        return record.lsn

    def update(self, txid: int, page_id: int, before: int, after: int) -> int:
        txid = self._positive_identifier(txid, "txid")
        page_id = self._page_identifier(page_id)
        if isinstance(before, bool) or not isinstance(before, int):
            raise TypeError("before must be int")
        if isinstance(after, bool) or not isinstance(after, int):
            raise TypeError("after must be int")
        return self._append(
            LogRecord(self.next_lsn, txid, "UPDATE", page_id, before, after)
        )

    def commit(self, txid: int) -> int:
        txid = self._positive_identifier(txid, "txid")
        return self._append(LogRecord(self.next_lsn, txid, "COMMIT"))

    def flush(self, lsn: int) -> None:
        if isinstance(lsn, bool) or not isinstance(lsn, int):
            raise TypeError("lsn must be int")
        if lsn < self.flushed_lsn or lsn >= self.next_lsn:
            raise ValueError("cannot flush unknown or older LSN")
        self.flushed_lsn = lsn


# [Implementation 3] WAL이 먼저 durable한 page만 저장합니다.
# page_lsn이 flushed_lsn보다 크면 write를 거부하고, 성공할 때는 Page의 복사본을 보관합니다.
class Disk:
    def __init__(self) -> None:
        self.pages: dict[int, Page] = {}
        self.write_events: list[tuple[int, int]] = []

    def read(self, page_id: int) -> Page:
        return replace(self.pages.get(page_id, Page()))

    def write(self, page_id: int, page: Page, log: LogManager) -> None:
        if page.page_lsn > log.flushed_lsn:
            raise WALViolation("log must be flushed before the data page")
        self.pages[page_id] = replace(page)
        self.write_events.append((page_id, page.page_lsn))


class RecoveryManager:
    @staticmethod
    def _validate(records: list[LogRecord]) -> None:
        previous_lsn = 0
        seen: set[int] = set()
        for record in records:
            if record.lsn <= previous_lsn or record.lsn in seen:
                raise ValueError("log records must have unique increasing LSNs")
            seen.add(record.lsn)
            previous_lsn = record.lsn
            if record.kind == "UPDATE":
                if record.page_id is None or record.before is None or record.after is None:
                    raise ValueError("UPDATE record is incomplete")
            elif record.kind == "COMMIT":
                if record.page_id is not None or record.before is not None or record.after is not None:
                    raise ValueError("COMMIT record contains update fields")
            else:
                raise ValueError("unknown log record kind")

    # [Implementation 4] page_lsn보다 새로운 UPDATE를 REDO합니다.
    # committed 여부와 관계없이 crash 직전의 update 순서를 먼저 재현한 뒤 UNDO 대상을 처리합니다.
    def recover(self, disk: Disk, records: list[LogRecord]) -> None:
        self._validate(records)
        committed = {record.txid for record in records if record.kind == "COMMIT"}
        updates = [record for record in records if record.kind == "UPDATE"]

        for record in updates:
            assert record.page_id is not None and record.after is not None
            page = disk.pages.setdefault(record.page_id, Page())
            if page.page_lsn < record.lsn:
                page.value = record.after
                page.page_lsn = record.lsn

        # [Implementation 5] 미완료 transaction을 역순으로 UNDO합니다.
        # 현재 값이 해당 UPDATE의 after image일 때만 되돌려 뒤에 적용된 committed 값을 보존합니다.
        losers = {record.txid for record in updates} - committed
        for record in reversed(updates):
            if record.txid not in losers:
                continue
            assert record.page_id is not None
            assert record.before is not None and record.after is not None
            page = disk.pages.setdefault(record.page_id, Page())

            # 이 모델은 각 UPDATE의 before/after 값이 실제 변경 순서와 이어진다고 가정합니다.
            # 현재 값이 달라졌다면 뒤의 UPDATE가 이미 적용된 것이므로 이 record는 값을 바꾸지 않습니다.
            if page.value == record.after:
                page.value = record.before
            page.page_lsn = max(page.page_lsn, record.lsn)
