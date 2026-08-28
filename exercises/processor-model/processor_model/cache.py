"""집합 연관 지연 쓰기 캐시와 3C 실패를 모의 실행합니다."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class Line:
    block: int
    dirty: bool = False


@dataclass(frozen=True)
class Access:
    kind: str
    address: int


def parse_trace(lines: Iterable[str]) -> list[Access]:
    result: list[Access] = []
    for number, raw in enumerate(lines, 1):
        text = raw.split("#", 1)[0].strip()
        if not text:
            continue
        parts = text.split()
        if len(parts) != 2 or parts[0].upper() not in {"R", "W"}:
            raise ValueError(f"{number}행: 'R 주소' 또는 'W 주소' 형식이어야 합니다")
        address = int(parts[1], 0)
        if address < 0:
            raise ValueError(f"{number}행: 주소는 음수일 수 없습니다")
        result.append(Access(parts[0].upper(), address))
    return result


# [Implementation 6] 캐시 상태 보관
# 실제 세트별 LRU와 3C 분류용 보조 캐시를 따로 유지합니다.
# 최초 접근 여부도 별도 집합에 기록합니다.
class CacheSimulator:
    def __init__(
        self,
        size_bytes: int,
        block_size: int,
        associativity: int,
        write_allocate: bool = True,
    ) -> None:
        if size_bytes <= 0 or block_size <= 0 or associativity <= 0:
            raise ValueError(
                "캐시 크기, 블록 크기와 연관도는 양수여야 합니다"
            )
        if block_size & (block_size - 1):
            raise ValueError("블록 크기는 2의 거듭제곱이어야 합니다")
        if size_bytes % (block_size * associativity):
            raise ValueError("캐시 크기는 블록 크기와 연관도를 곱한 값의 배수여야 합니다")
        self.size_bytes = size_bytes
        self.block_size = block_size
        self.associativity = associativity
        self.set_count = size_bytes // (block_size * associativity)
        self.line_count = size_bytes // block_size
        self.write_allocate = write_allocate
        self.sets: list[OrderedDict[int, Line]] = [
            OrderedDict() for _ in range(self.set_count)
        ]
        self.shadow: OrderedDict[int, None] = OrderedDict()
        self.seen: set[int] = set()
        self.hits = 0
        self.misses = 0
        self.reads = 0
        self.writes = 0
        self.compulsory = 0
        self.conflict = 0
        self.capacity = 0
        self.writebacks = 0
        self.memory_writes = 0
        self.events: list[dict[str, Any]] = []

    def _touch_shadow(self, block: int) -> bool:
        hit = block in self.shadow
        if hit:
            self.shadow.move_to_end(block)
        else:
            self.shadow[block] = None
            if len(self.shadow) > self.line_count:
                self.shadow.popitem(last=False)
        return hit

    # [Implementation 6-1] 캐시 적중·실패 전이
    # 주소를 블록·세트·태그로 나누고, 실패 종류와 수정된 라인의
    # 메모리 반영 여부를 한 번의 접근에서 확정합니다.
    def access(self, access: Access) -> None:
        block = access.address // self.block_size
        set_index = block % self.set_count
        tag = block // self.set_count
        cache_set = self.sets[set_index]
        actual_hit = tag in cache_set
        shadow_hit = self._touch_shadow(block)
        first = block not in self.seen
        self.seen.add(block)

        if access.kind == "R":
            self.reads += 1
        else:
            self.writes += 1

        evicted_block: int | None = None
        writeback = False
        miss_kind: str | None = None
        if actual_hit:
            self.hits += 1
            line = cache_set[tag]
            cache_set.move_to_end(tag)
            if access.kind == "W":
                line.dirty = True
        else:
            self.misses += 1
            if first:
                self.compulsory += 1
                miss_kind = "compulsory"
            elif shadow_hit:
                self.conflict += 1
                miss_kind = "conflict"
            else:
                self.capacity += 1
                miss_kind = "capacity"

            allocate = access.kind == "R" or self.write_allocate
            if allocate:
                if len(cache_set) >= self.associativity:
                    evicted_tag, evicted = cache_set.popitem(last=False)
                    evicted_block = evicted_tag * self.set_count + set_index
                    if evicted.dirty:
                        self.writebacks += 1
                        self.memory_writes += 1
                        writeback = True
                cache_set[tag] = Line(block=block, dirty=access.kind == "W")
            elif access.kind == "W":
                self.memory_writes += 1

        self.events.append(
            {
                "kind": access.kind,
                "address": access.address,
                "block": block,
                "set": set_index,
                "tag": tag,
                "hit": actual_hit,
                "miss_kind": miss_kind,
                "evicted_block": evicted_block,
                "writeback": writeback,
            }
        )

    def run(self, accesses: list[Access]) -> dict[str, Any]:
        for access in accesses:
            self.access(access)
        total = self.hits + self.misses
        return {
            "configuration": {
                "size_bytes": self.size_bytes,
                "block_size": self.block_size,
                "associativity": self.associativity,
                "sets": self.set_count,
                "lines": self.line_count,
                "write_allocate": self.write_allocate,
                "replacement": "LRU",
                "write_policy": "write-back",
            },
            "accesses": total,
            "reads": self.reads,
            "writes": self.writes,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total else 0.0,
            "miss_rate": self.misses / total if total else 0.0,
            "compulsory_misses": self.compulsory,
            "conflict_misses": self.conflict,
            "capacity_misses": self.capacity,
            "writebacks": self.writebacks,
            "memory_writes": self.memory_writes,
            "events": self.events,
        }
