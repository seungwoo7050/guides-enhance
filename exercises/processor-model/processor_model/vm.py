"""페이지 테이블과 LRU TLB를 이용해 가상 주소를 변환합니다."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class Mapping:
    pfn: int
    permissions: set[str]


@dataclass(frozen=True)
class Operation:
    kind: str
    values: tuple[str, ...]


def parse_operations(lines: Iterable[str]) -> list[Operation]:
    operations: list[Operation] = []
    for number, raw in enumerate(lines, 1):
        text = raw.split("#", 1)[0].strip()
        if not text:
            continue
        parts = text.split()
        kind = parts[0].upper()
        expected = {"R": 2, "W": 2, "X": 2, "MAP": 4, "UNMAP": 2}
        if kind not in expected or len(parts) != expected[kind]:
            raise ValueError(f"{number}행: 잘못된 VM 추적 명령입니다: {text}")
        operations.append(Operation(kind, tuple(parts[1:])))
    return operations


# [Implementation 7] 주소 변환 상태
# 페이지 테이블을 변환 정보의 원본으로 둡니다.
# TLB에는 페이지 테이블에서 얻은 변환과 권한만 저장합니다.
class VirtualMemorySimulator:
    def __init__(
        self,
        page_size: int,
        tlb_entries: int,
        mappings: dict[int, Mapping] | None = None,
    ) -> None:
        if page_size <= 0 or page_size & (page_size - 1):
            raise ValueError("페이지 크기는 2의 거듭제곱이어야 합니다")
        if tlb_entries < 0:
            raise ValueError("TLB 항목 수는 음수일 수 없습니다")
        self.page_size = page_size
        self.tlb_entries = tlb_entries
        self.page_table = dict(mappings or {})
        self.tlb: OrderedDict[int, Mapping] = OrderedDict()
        self.tlb_hits = 0
        self.tlb_misses = 0
        self.page_table_walks = 0
        self.page_faults = 0
        self.protection_faults = 0
        self.invalidations = 0
        self.events: list[dict[str, Any]] = []

    def _invalidate(self, vpn: int) -> None:
        if vpn in self.tlb:
            del self.tlb[vpn]
            self.invalidations += 1

    def _insert_tlb(self, vpn: int, mapping: Mapping) -> None:
        if self.tlb_entries == 0:
            return
        self.tlb[vpn] = mapping
        self.tlb.move_to_end(vpn)
        if len(self.tlb) > self.tlb_entries:
            self.tlb.popitem(last=False)

    # [Implementation 7-1] TLB 조회와 권한 검사
    # TLB 조회 또는 페이지 테이블 순회를 마치고 권한을 확인한 뒤
    # PFN과 페이지 오프셋으로 물리 주소를 만듭니다.
    def _translate(self, kind: str, address: int) -> None:
        if address < 0:
            raise ValueError("가상 주소는 음수일 수 없습니다")
        vpn, offset = divmod(address, self.page_size)
        tlb_hit = vpn in self.tlb
        if tlb_hit:
            self.tlb_hits += 1
            mapping = self.tlb[vpn]
            self.tlb.move_to_end(vpn)
        else:
            self.tlb_misses += 1
            self.page_table_walks += 1
            mapping = self.page_table.get(vpn)
            if mapping is not None:
                self._insert_tlb(vpn, mapping)

        fault: str | None = None
        physical: int | None = None
        required = kind.lower()
        if mapping is None:
            self.page_faults += 1
            fault = "page-fault"
        elif required not in mapping.permissions:
            self.protection_faults += 1
            fault = "protection-fault"
        else:
            physical = mapping.pfn * self.page_size + offset

        self.events.append(
            {
                "operation": kind,
                "virtual_address": address,
                "vpn": vpn,
                "offset": offset,
                "tlb_hit": tlb_hit,
                "pfn": None if mapping is None else mapping.pfn,
                "physical_address": physical,
                "fault": fault,
            }
        )

    # [Implementation 7-2] TLB 항목 무효화
    # MAP·UNMAP으로 페이지 테이블을 바꾼 직후 이전 TLB 항목을 제거합니다.
    def run(self, operations: list[Operation]) -> dict[str, Any]:
        for operation in operations:
            if operation.kind in {"R", "W", "X"}:
                self._translate(operation.kind, int(operation.values[0], 0))
            elif operation.kind == "MAP":
                vpn = int(operation.values[0], 0)
                pfn = int(operation.values[1], 0)
                permissions = set(operation.values[2].lower())
                if not permissions or permissions - {"r", "w", "x"}:
                    raise ValueError("권한은 r, w, x 가운데 하나 이상이어야 합니다")
                self.page_table[vpn] = Mapping(pfn, permissions)
                self._invalidate(vpn)
                self.events.append(
                    {
                        "operation": "MAP",
                        "vpn": vpn,
                        "pfn": pfn,
                        "permissions": "".join(sorted(permissions)),
                    }
                )
            elif operation.kind == "UNMAP":
                vpn = int(operation.values[0], 0)
                self.page_table.pop(vpn, None)
                self._invalidate(vpn)
                self.events.append({"operation": "UNMAP", "vpn": vpn})

        translations = sum(
            1 for event in self.events if event.get("operation") in {"R", "W", "X"}
        )
        return {
            "configuration": {
                "page_size": self.page_size,
                "tlb_entries": self.tlb_entries,
                "tlb_replacement": "LRU",
            },
            "translations": translations,
            "tlb_hits": self.tlb_hits,
            "tlb_misses": self.tlb_misses,
            "tlb_hit_rate": self.tlb_hits / translations if translations else 0.0,
            "page_table_walks": self.page_table_walks,
            "page_faults": self.page_faults,
            "protection_faults": self.protection_faults,
            "tlb_invalidations": self.invalidations,
            "events": self.events,
        }
