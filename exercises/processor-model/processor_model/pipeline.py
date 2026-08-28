"""5단계 순차 파이프라인의 데이터·제어 위험을 추적합니다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .isa import Instruction, sources_and_destination

STAGE_NAMES = ("IF", "ID", "EX", "MEM", "WB")


@dataclass
class Slot:
    index: int
    instruction: Instruction


@dataclass
class PipelineResult:
    cycles: int
    retired: int
    data_stalls: int
    control_stalls: int
    flushes: int
    timeline: list[dict[str, str]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "cycles": self.cycles,
            "retired": self.retired,
            "data_stalls": self.data_stalls,
            "control_stalls": self.control_stalls,
            "flushes": self.flushes,
            "cpi": self.cycles / self.retired if self.retired else 0.0,
            "timeline": self.timeline,
        }


# [Implementation 5] 데이터 위험 판정
# 일반 ALU 결과는 전달 경로로 해결하고, 적재 결과를 바로 읽는
# 명령만 한 사이클 정지시킵니다.
def _has_data_hazard(
    id_slot: Slot | None,
    ex_slot: Slot | None,
    mem_slot: Slot | None,
    forwarding: str,
) -> bool:
    if id_slot is None:
        return False
    sources, _, _ = sources_and_destination(id_slot.instruction)
    sources.discard(0)
    if not sources:
        return False

    if forwarding == "full":
        if ex_slot is None:
            return False
        _, destination, is_load = sources_and_destination(ex_slot.instruction)
        return is_load and destination not in {None, 0} and destination in sources

    if forwarding == "none":
        for producer in (ex_slot, mem_slot):
            if producer is None:
                continue
            _, destination, _ = sources_and_destination(producer.instruction)
            if destination not in {None, 0} and destination in sources:
                return True
        return False

    raise ValueError("전달 방식은 full 또는 none이어야 합니다")


# [Implementation 5-1] 5단계 상태 전이
# 각 사이클의 단계 위치를 먼저 기록합니다.
# 이후 완료 수 계산, 분기 비우기, 데이터 정지, 단계 이동과 명령 인출을 적용합니다.
def simulate(
    instructions: list[Instruction],
    forwarding: str = "full",
    branch_penalty: int = 2,
    max_cycles: int = 100_000,
) -> PipelineResult:
    """분기하지 않음으로 예측하는 5단계 추적 모델을 실행합니다."""

    if forwarding not in {"full", "none"}:
        raise ValueError("전달 방식은 full 또는 none이어야 합니다")
    if branch_penalty < 0:
        raise ValueError("분기 비용은 음수일 수 없습니다")

    stages: dict[str, Slot | None] = {name: None for name in STAGE_NAMES}
    pc = 0
    cycle = 0
    retired = 0
    data_stalls = 0
    control_stalls = 0
    flushes = 0
    fetch_blocked = 0
    timeline_by_instruction: dict[int, dict[int, str]] = {
        index: {} for index in range(len(instructions))
    }

    def empty() -> bool:
        return all(slot is None for slot in stages.values())

    while pc < len(instructions) or not empty():
        cycle += 1
        if cycle > max_cycles:
            raise RuntimeError(f"최대 사이클 수를 넘었습니다: {max_cycles}")

        for stage_name in STAGE_NAMES:
            slot = stages[stage_name]
            if slot is not None:
                previous = timeline_by_instruction[slot.index].get(cycle)
                label = stage_name if previous is None else f"{previous}/{stage_name}"
                timeline_by_instruction[slot.index][cycle] = label

        if stages["WB"] is not None:
            retired += 1

        branch_taken = bool(
            stages["EX"] is not None
            and stages["EX"].instruction.op in {"beq", "bne", "j"}
            and stages["EX"].instruction.taken
        )

        flushed: list[Slot] = []
        if branch_taken:
            for stage_name in ("ID", "IF"):
                slot = stages[stage_name]
                if slot is not None:
                    flushed.append(slot)
                    timeline_by_instruction[slot.index][cycle] = f"{stage_name}*"
            if stages["EX"] is None or stages["EX"].instruction.target_index is None:
                raise ValueError("실행된 분기에는 목적지 인덱스가 필요합니다")
            pc = stages["EX"].instruction.target_index
            flushes += len(flushed)
            stages["ID"] = None
            stages["IF"] = None
            fetch_blocked = max(fetch_blocked, branch_penalty)

        stall = _has_data_hazard(
            stages["ID"], stages["EX"], stages["MEM"], forwarding
        )
        if stall:
            data_stalls += 1

        old_if = stages["IF"]
        old_id = stages["ID"]
        old_ex = stages["EX"]
        old_mem = stages["MEM"]

        stages["WB"] = old_mem
        stages["MEM"] = old_ex
        if stall:
            stages["EX"] = None
            stages["ID"] = old_id
            stages["IF"] = old_if
        else:
            stages["EX"] = old_id
            stages["ID"] = old_if
            stages["IF"] = None

        if fetch_blocked > 0:
            fetch_blocked -= 1
            control_stalls += 1
        elif stages["IF"] is None and pc < len(instructions):
            stages["IF"] = Slot(pc, instructions[pc])
            pc += 1

    table: list[dict[str, str]] = []
    for index, instruction in enumerate(instructions):
        row: dict[str, str] = {
            "instruction": f"I{index}: {instruction.text}",
        }
        for number in range(1, cycle + 1):
            row[str(number)] = timeline_by_instruction[index].get(number, ".")
        table.append(row)

    return PipelineResult(
        cycles=cycle,
        retired=retired,
        data_stalls=data_stalls,
        control_stalls=control_stalls,
        flushes=flushes,
        timeline=table,
    )
