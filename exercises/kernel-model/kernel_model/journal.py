"""record를 append하고 commit된 transaction만 replay하는 journal입니다."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping


class JournalError(ValueError):
    """transaction 상태 또는 journal record 순서가 잘못됐을 때 발생합니다."""


# [Implementation 7] journal record 정의
@dataclass(frozen=True, slots=True)
class JournalRecord:
    txid: int
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Journal:
    records: list[JournalRecord] = field(default_factory=list)
    _next_txid: int = 1

    # [Implementation 7-1] transaction 시작과 txid 발급
    def begin(self) -> int:
        txid = self._next_txid
        self._next_txid += 1
        self.records.append(JournalRecord(txid, "begin"))
        return txid

    # [Implementation 7-2] 열린 transaction에 operation 추가
    def append(self, txid: int, operation: Mapping[str, Any]) -> None:
        state = self._state(txid)
        if state != "open":
            raise JournalError(f"Operations require an open transaction: txid={txid}")
        if "op" not in operation:
            raise JournalError("A journal operation requires an 'op' field")
        self.records.append(JournalRecord(txid, "operation", dict(operation)))

    def commit(self, txid: int) -> None:
        if self._state(txid) != "open":
            raise JournalError(f"Only an open transaction can commit: txid={txid}")
        self.records.append(JournalRecord(txid, "commit"))

    # [Implementation 7-3] commit된 transaction만 replay
    def recover(
        self,
        apply_operation: Callable[[Mapping[str, Any]], None],
        *,
        already_applied: set[int] | None = None,
    ) -> list[int]:
        """commit된 transaction을 각각 최대 한 번 replay합니다."""

        self.validate()
        applied = already_applied if already_applied is not None else set()
        operations: dict[int, list[dict[str, Any]]] = {}
        committed: set[int] = set()
        for record in self.records:
            if record.kind == "operation":
                operations.setdefault(record.txid, []).append(dict(record.payload))
            elif record.kind == "commit":
                committed.add(record.txid)

        recovered: list[int] = []
        for txid in sorted(committed):
            if txid in applied:
                continue
            for operation in operations.get(txid, []):
                apply_operation(operation)
            # 모든 operation이 끝난 뒤에만 적용 완료로 기록합니다.
            # 중간에 실패하면 같은 transaction을 다시 시도할 수 있어야 합니다.
            applied.add(txid)
            recovered.append(txid)
        return recovered

    # [Implementation 7-4] journal record 순서 검사
    def validate(self) -> None:
        states: dict[int, str] = {}
        for record in self.records:
            if record.txid <= 0:
                raise JournalError("Transaction identifiers must be positive")
            if record.kind == "begin":
                if record.txid in states:
                    raise JournalError(f"Duplicate begin record: txid={record.txid}")
                states[record.txid] = "open"
            elif record.kind == "operation":
                if states.get(record.txid) != "open":
                    raise JournalError(
                        f"Operation belongs to a transaction that is not open: txid={record.txid}"
                    )
                if "op" not in record.payload:
                    raise JournalError(f"Operation lacks an 'op' field: txid={record.txid}")
            elif record.kind == "commit":
                if states.get(record.txid) != "open":
                    raise JournalError(f"Commit record is out of order: txid={record.txid}")
                states[record.txid] = "committed"
            else:
                raise JournalError(f"Unknown journal record kind: {record.kind}")

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "txid": record.txid,
                "kind": record.kind,
                "payload": dict(record.payload),
            }
            for record in self.records
        ]

    @classmethod
    def from_snapshot(cls, records: Iterable[Mapping[str, Any]]) -> "Journal":
        journal = cls()
        journal.records = []
        maximum = 0
        for raw in records:
            record = JournalRecord(
                txid=int(raw["txid"]),
                kind=str(raw["kind"]),
                payload=dict(raw.get("payload", {})),
            )
            journal.records.append(record)
            maximum = max(maximum, record.txid)
        journal._next_txid = maximum + 1
        journal.validate()
        return journal

    def _state(self, txid: int) -> str | None:
        state: str | None = None
        for record in self.records:
            if record.txid != txid:
                continue
            if record.kind == "begin":
                state = "open"
            elif record.kind == "commit":
                state = "committed"
        return state
