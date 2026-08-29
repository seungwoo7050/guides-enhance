from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


# [Implementation 1]
# Server, request, reservation, and decision records
# 배치 전후에 사용하는 입력, 예약, 결정 값을 별도 Record로 정의합니다.
@dataclass(frozen=True)
class ServerLimits:
    max_rooms: int
    max_players: int
    max_tick_cost: int
    max_outbound_bytes: int
    max_memory: int


@dataclass
class Server:
    server_id: str
    release_id: str
    protocol_versions: tuple[str, ...]
    region: str
    state: Literal["ACTIVE", "DRAINING", "UNAVAILABLE"]
    room_count: int
    player_count: int
    tick_cost_used: int
    outbound_bytes_used: int
    memory_used: int
    last_heartbeat: int
    limits: ServerLimits


@dataclass(frozen=True)
class MatchRequest:
    request_id: str
    required_protocol_version: str
    region_preferences: tuple[str, ...]
    expected_players: int
    estimated_tick_cost: int
    estimated_bandwidth: int
    estimated_memory: int
    created_at: int
    deadline: int


@dataclass(frozen=True)
class Reservation:
    request_id: str
    server_id: str
    players: int
    tick_cost: int
    outbound_bytes: int
    memory: int


@dataclass
class RequestDecision:
    request_id: str
    status: Literal["PLACED", "QUEUED", "REJECTED", "COMPLETED"]
    reason_code: str
    server_id: str | None = None
    score: dict[str, object] | None = None
