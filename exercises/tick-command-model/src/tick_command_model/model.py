from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


# [Implementation 1]
# Simulation state, command, and result records
# 입력과 출력에서 공유할 값의 형태를 먼저 고정합니다.
@dataclass(frozen=True)
class SimulationConfig:
    match_id: str
    tick_rate_hz: int
    start_tick: int
    advance_to_tick: int
    max_commands_per_tick: int
    max_catch_up_ticks: int
    max_future_tick_distance: int
    max_move_delta: int = 100
    coordinate_limit: int = 1_000_000
    max_score_delta: int = 1_000_000
    score_limit: int = 2_147_483_647


@dataclass
class PlayerState:
    player_id: str
    session_epoch: int
    last_sequence: int
    x: int
    y: int
    score: int

    def to_dict(self) -> dict[str, int | str]:
        return {
            "player_id": self.player_id,
            "session_epoch": self.session_epoch,
            "last_sequence": self.last_sequence,
            "x": self.x,
            "y": self.y,
            "score": self.score,
        }


@dataclass(frozen=True)
class Command:
    command_id: str
    match_id: str
    player_id: str
    session_epoch: int
    sequence: int
    target_tick: int
    kind: str
    payload: dict[str, Any]
    received_order: int


@dataclass(frozen=True)
class Decision:
    command_id: str
    target_tick: int | None
    status: Literal["APPLIED", "REJECTED"]
    reason_code: str

    def to_dict(self) -> dict[str, int | str | None]:
        return {
            "command_id": self.command_id,
            "target_tick": self.target_tick,
            "status": self.status,
            "reason_code": self.reason_code,
        }
