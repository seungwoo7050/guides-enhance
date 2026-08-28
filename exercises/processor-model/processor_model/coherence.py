"""단순화한 스누핑 MESI 추적 입력을 모의 실행합니다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class Access:
    kind: str
    core: int
    address: int


def parse_trace(lines: Iterable[str]) -> list[Access]:
    result: list[Access] = []
    for number, raw in enumerate(lines, 1):
        text = raw.split("#", 1)[0].strip()
        if not text:
            continue
        parts = text.split()
        if len(parts) != 3 or parts[0].upper() not in {"R", "W"}:
            raise ValueError(
                f"{number}행: 'R 코어 주소' 또는 "
                "'W 코어 주소' 형식이어야 합니다"
            )
        core = int(parts[1], 0)
        address = int(parts[2], 0)
        if core < 0 or address < 0:
            raise ValueError(f"{number}행: 코어 번호와 주소는 음수일 수 없습니다")
        result.append(Access(parts[0].upper(), core, address))
    return result


# [Implementation 10] 안정 MESI 상태
# 캐시 블록마다 코어별 MESI 상태를 저장합니다.
# 과도 상태와 상호연결망의 전송 시간은 다루지 않습니다.
class MESISimulator:
    def __init__(self, cores: int, line_size: int) -> None:
        if cores < 2:
            raise ValueError("코어 수는 2 이상이어야 합니다")
        if line_size <= 0 or line_size & (line_size - 1):
            raise ValueError("캐시 라인 크기는 2의 거듭제곱이어야 합니다")
        self.cores = cores
        self.line_size = line_size
        self.states: dict[int, list[str]] = {}
        self.bus_reads = 0
        self.bus_read_exclusive = 0
        self.bus_upgrades = 0
        self.invalidations = 0
        self.writebacks = 0
        self.hits = 0
        self.misses = 0
        self.events: list[dict[str, Any]] = []

    def _line_states(self, block: int) -> list[str]:
        return self.states.setdefault(block, ["I"] * self.cores)

    # [Implementation 10-1] MESI 읽기·쓰기 전이
    # BusRd·BusRdX·BusUpgr, 무효화와 메모리 반영 전후의
    # 코어별 상태를 접근마다 기록합니다.
    def access(self, access: Access) -> None:
        if access.core >= self.cores:
            raise ValueError(f"존재하지 않는 코어입니다: {access.core}")
        block = access.address // self.line_size
        states = self._line_states(block)
        before = list(states)
        local = states[access.core]
        bus_event = "none"

        if access.kind == "R":
            if local != "I":
                self.hits += 1
            else:
                self.misses += 1
                self.bus_reads += 1
                bus_event = "BusRd"
                sharers = [index for index, state in enumerate(states) if state != "I"]
                if not sharers:
                    states[access.core] = "E"
                else:
                    for index in sharers:
                        if states[index] == "M":
                            self.writebacks += 1
                        states[index] = "S"
                    states[access.core] = "S"
        else:
            if local == "M":
                self.hits += 1
            elif local == "E":
                self.hits += 1
                states[access.core] = "M"
            elif local == "S":
                self.hits += 1
                self.bus_upgrades += 1
                bus_event = "BusUpgr"
                for index, state in enumerate(states):
                    if index != access.core and state != "I":
                        states[index] = "I"
                        self.invalidations += 1
                states[access.core] = "M"
            else:
                self.misses += 1
                self.bus_read_exclusive += 1
                bus_event = "BusRdX"
                for index, state in enumerate(states):
                    if index == access.core or state == "I":
                        continue
                    if state == "M":
                        self.writebacks += 1
                    states[index] = "I"
                    self.invalidations += 1
                states[access.core] = "M"

        self.events.append(
            {
                "kind": access.kind,
                "core": access.core,
                "address": access.address,
                "block": block,
                "word_offset": access.address % self.line_size,
                "local_hit": local != "I",
                "bus_event": bus_event,
                "before": before,
                "after": list(states),
            }
        )

    def run(self, accesses: list[Access]) -> dict[str, Any]:
        for access in accesses:
            self.access(access)
        total = self.hits + self.misses
        return {
            "configuration": {"cores": self.cores, "line_size": self.line_size},
            "accesses": total,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total else 0.0,
            "bus_reads": self.bus_reads,
            "bus_read_exclusive": self.bus_read_exclusive,
            "bus_upgrades": self.bus_upgrades,
            "invalidations": self.invalidations,
            "writebacks": self.writebacks,
            "final_states": {str(block): states for block, states in sorted(self.states.items())},
            "events": self.events,
        }
