from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


# [Implementation 1]
# Identity, authoritative state, rate-limit, and decision records
# 입력에서 주장한 값과 서버가 보유한 값을 분리해 저장합니다.
@dataclass
class Session:
    session_id: str
    actor_id: str
    player_id: str
    connection_id: str
    epoch: int
    active: bool = True


@dataclass
class Player:
    player_id: str
    session_id: str
    room_id: str
    match_id: str
    x: int
    y: int
    score: int
    last_sequence: int


@dataclass(frozen=True)
class Room:
    room_id: str
    player_ids: frozenset[str]


@dataclass(frozen=True)
class Match:
    match_id: str
    room_id: str
    state: str
    player_ids: frozenset[str]


@dataclass
class Entity:
    entity_id: str
    room_id: str
    match_id: str
    owner_player_id: str
    use_count: int = 0


@dataclass(frozen=True)
class RateLimitPolicy:
    capacity: int
    refill_per_tick: int


@dataclass
class TokenBucket:
    tokens: int
    last_tick: int


@dataclass(frozen=True)
class CommandDecision:
    command_id: str
    status: Literal["ALLOW", "DENY", "IGNORED"]
    reason_code: str
    applied_changes: dict[str, Any] = field(default_factory=dict)
