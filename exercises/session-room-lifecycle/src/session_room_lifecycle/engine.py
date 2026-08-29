from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .model import Connection, EventDecision, Match, Player, Room, Session


ACCEPTED = "ACCEPTED"
REJECTED = "REJECTED"
IGNORED = "IGNORED"


class LifecycleEngine:
    def __init__(self, reconnect_grace: int) -> None:
        if reconnect_grace < 0:
            raise ValueError("reconnect_grace must be non-negative")
        self.reconnect_grace = reconnect_grace
        self.logical_time = 0
        self.server_state = "ACTIVE"
        self.connections: dict[str, Connection] = {}
        self.sessions: dict[str, Session] = {}
        self.players: dict[str, Player] = {}
        self.rooms: dict[str, Room] = {}
        self.matches: dict[str, Match] = {}
        self.processed_events: dict[str, str] = {}
        self.trace: list[dict[str, Any]] = []

    # [Implementation 2]
    # Logical time and event deduplication
    # 같은 event ID의 재전달과 충돌을 먼저 판정한 뒤에만 시각과 상태를 바꿉니다.
    def apply_event(self, raw: dict[str, Any]) -> None:
        event_id = raw.get("event_id")
        kind = raw.get("kind")
        logical_time = raw.get("logical_time")
        if (
            not isinstance(event_id, str)
            or not event_id
            or not isinstance(kind, str)
            or not kind
            or not isinstance(logical_time, int)
            or isinstance(logical_time, bool)
        ):
            raise ValueError("event_id, kind, and integer logical_time are required")

        fingerprint = digest_result(raw)
        created: list[str] = []
        destroyed: list[str] = []
        expired: list[str] = []
        previous = self.processed_events.get(event_id)
        if previous is not None:
            reason = "DUPLICATE_EVENT" if previous == fingerprint else "EVENT_ID_CONFLICT"
            status = IGNORED if previous == fingerprint else REJECTED
            decision = EventDecision(event_id, kind, logical_time, status, reason)
        else:
            if logical_time < self.logical_time:
                raise ValueError("logical_time must be non-decreasing")
            self.logical_time = logical_time
            expired = self._expire_waiting_sessions(destroyed)
            self.processed_events[event_id] = fingerprint
            if self.server_state == "SHUTDOWN" and kind != "SHUTDOWN":
                decision = EventDecision(
                    event_id,
                    kind,
                    logical_time,
                    REJECTED,
                    "SERVER_SHUTDOWN",
                )
            else:
                handler = getattr(self, f"_on_{kind.lower()}", None)
                if handler is None:
                    decision = EventDecision(
                        event_id,
                        kind,
                        logical_time,
                        REJECTED,
                        "UNKNOWN_EVENT",
                    )
                else:
                    decision = handler(raw, created, destroyed)

        self._assert_invariants()
        self.trace.append(
            {
                **asdict(decision),
                "created_resources": created,
                "destroyed_resources": destroyed,
                "expired_sessions": expired,
                "state": self.snapshot(),
            }
        )

    def _decision(self, raw: dict[str, Any], status: str, reason: str) -> EventDecision:
        return EventDecision(
            event_id=str(raw["event_id"]),
            kind=str(raw["kind"]),
            logical_time=int(raw["logical_time"]),
            status=status,  # type: ignore[arg-type]
            reason_code=reason,
        )

    def _authenticated_player(self, raw: dict[str, Any]) -> tuple[Player | None, str | None]:
        connection_id = str(raw.get("connection_id", ""))
        connection = self.connections.get(connection_id)
        if connection is None:
            return None, "CONNECTION_NOT_FOUND"
        if connection.state != "AUTHENTICATED" or connection.session_id is None:
            return None, "CONNECTION_NOT_AUTHENTICATED"
        session = self.sessions.get(connection.session_id)
        if (
            session is None
            or session.state != "ACTIVE"
            or session.connection_id != connection_id
        ):
            return None, "SESSION_NOT_ACTIVE"
        player = self.players.get(session.player_id)
        if player is None:
            return None, "PLAYER_NOT_FOUND"
        return player, None


def run_scenario(scenario):
    """Expose the package boundary while later lifecycle stages are unfinished."""
    raise NotImplementedError("scenario execution is introduced in a later implementation stage")
