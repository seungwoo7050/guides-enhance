"""순차 반영과 정밀한 예외를 재현하는 작은 재정렬 버퍼입니다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import MutableMapping


@dataclass
class Entry:
    tag: int
    destination: str | None
    ready: bool = False
    value: int | None = None
    fault: str | None = None


class PreciseException(RuntimeError):
    def __init__(self, tag: int, reason: str) -> None:
        super().__init__(f"명령 태그 {tag}에서 예외가 발생했습니다: {reason}")
        self.tag = tag
        self.reason = reason


# [Implementation 9] 재정렬 버퍼 상태
# 증가하는 태그와 제한된 항목 수로 아직 반영하지 않은 명령을 구분합니다.
# 발행·완료 시점과 레지스터 반영 시점을 나눕니다.
class ReorderBuffer:
    """완료 순서는 달라도 되지만 맨 앞 항목부터 레지스터에 반영합니다."""

    def __init__(self, capacity: int) -> None:
        if (
            not isinstance(capacity, int)
            or isinstance(capacity, bool)
            or capacity <= 0
        ):
            raise ValueError("버퍼 용량은 양의 정수여야 합니다")
        self.capacity = capacity
        self._next_tag = 0
        self._entries: list[Entry] = []

    def issue(self, destination: str | None) -> int:
        if destination is not None and (
            not isinstance(destination, str) or not destination
        ):
            raise ValueError(
                "목적지는 비어 있지 않은 문자열 또는 None이어야 합니다"
            )
        if len(self._entries) >= self.capacity:
            raise BufferError("재정렬 버퍼가 가득 찼습니다")
        tag = self._next_tag
        self._next_tag += 1
        self._entries.append(Entry(tag, destination))
        return tag

    def complete(
        self, tag: int, *, value: int | None = None, fault: str | None = None
    ) -> None:
        if fault is not None and (not isinstance(fault, str) or not fault):
            raise ValueError("예외 사유는 비어 있지 않은 문자열이어야 합니다")
        if fault is not None and value is not None:
            raise ValueError(
                "완료 결과에는 값과 예외를 함께 넣을 수 없습니다"
            )
        entry = next((item for item in self._entries if item.tag == tag), None)
        if entry is None:
            raise KeyError(f"대기 중인 항목이 아닌 태그입니다: {tag}")
        if entry.ready:
            raise ValueError(f"이미 완료한 태그입니다: {tag}")
        if entry.destination is not None and value is None and fault is None:
            raise ValueError("레지스터 쓰기 명령에는 완료 값이 필요합니다")
        entry.ready = True
        entry.value = value
        entry.fault = fault

    # [Implementation 9-1] 순차 반영과 정밀한 예외
    # 준비된 맨 앞 항목만 반영합니다. 예외를 만나면
    # 해당 항목과 그보다 뒤에 발행한 미반영 항목을 버립니다.
    def retire(
        self, registers: MutableMapping[str, int], limit: int | None = None
    ) -> list[int]:
        if limit is not None and (
            not isinstance(limit, int) or isinstance(limit, bool) or limit < 0
        ):
            raise ValueError("반영 개수 제한은 0 이상의 정수여야 합니다")
        retired: list[int] = []
        while self._entries and self._entries[0].ready:
            if limit is not None and len(retired) >= limit:
                break
            entry = self._entries.pop(0)
            if entry.fault is not None:
                self._entries.clear()
                raise PreciseException(entry.tag, entry.fault)
            if entry.destination is not None:
                assert entry.value is not None
                registers[entry.destination] = entry.value
            retired.append(entry.tag)
        return retired

    def pending_tags(self) -> list[int]:
        return [entry.tag for entry in self._entries]
