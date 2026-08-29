from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


ConnectionState = Literal["OPEN_UNAUTHENTICATED", "AUTHENTICATED", "DISCONNECTED"]
SessionState = Literal["ACTIVE", "WAITING_RECONNECT", "EXPIRED"]
RoomState = Literal["OPEN", "READY", "IN_MATCH", "CLOSING"]
MatchState = Literal["RUNNING", "FINALIZED"]
ServerState = Literal["ACTIVE", "DRAINING", "SHUTDOWN"]


# [Implementation 1]
# Connection, session, player, room, and match records
# 서로 다른 수명을 가진 값을 별도 Record로 정의합니다.
@dataclass
class Connection:
    connection_id: str
    state: ConnectionState = "OPEN_UNAUTHENTICATED"
    session_id: str | None = None


@dataclass
class Session:
    session_id: str
    player_id: str
    epoch: int
    state: SessionState
    connection_id: str | None
    grace_deadline: int | None = None


@dataclass
class Player:
    player_id: str
    session_id: str
    room_id: str | None = None
    ready: bool = False
    forfeited: bool = False


@dataclass
class Room:
    room_id: str
    owner_player_id: str
    state: RoomState = "OPEN"
    player_ids: set[str] = field(default_factory=set)
    match_id: str | None = None


@dataclass
class Match:
    match_id: str
    room_id: str
    state: MatchState = "RUNNING"
    participant_ids: set[str] = field(default_factory=set)
    forfeited_player_ids: set[str] = field(default_factory=set)
    result_revision: int = 0


@dataclass(frozen=True)
class EventDecision:
    event_id: str
    kind: str
    logical_time: int
    status: Literal["ACCEPTED", "REJECTED", "IGNORED"]
    reason_code: str
