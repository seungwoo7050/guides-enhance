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

    # [Implementation 3]
    # Connection creation and session ownership
    # 연결 식별자를 플레이어 식별자로 사용하지 않고 별도 자원으로 관리합니다.
    def _on_connect(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        connection_id = str(raw.get("connection_id", ""))
        if not connection_id:
            return self._decision(raw, REJECTED, "INVALID_CONNECTION_ID")
        if connection_id in self.connections:
            return self._decision(raw, REJECTED, "CONNECTION_ALREADY_EXISTS")
        self.connections[connection_id] = Connection(connection_id)
        created.append(f"connection:{connection_id}")
        return self._decision(raw, ACCEPTED, "CONNECTED")

    # [Implementation 3-1]
    # Authentication binding
    # 하나의 활성 세션은 한 연결과 한 플레이어만 가리키게 합니다.
    def _on_authenticate(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        connection_id = str(raw.get("connection_id", ""))
        session_id = str(raw.get("session_id", ""))
        player_id = str(raw.get("player_id", ""))
        epoch = raw.get("session_epoch")
        connection = self.connections.get(connection_id)
        if connection is None:
            return self._decision(raw, REJECTED, "CONNECTION_NOT_FOUND")
        if connection.state != "OPEN_UNAUTHENTICATED":
            return self._decision(raw, REJECTED, "CONNECTION_NOT_AUTHENTICATABLE")
        if (
            not session_id
            or not player_id
            or not isinstance(epoch, int)
            or isinstance(epoch, bool)
            or epoch < 1
        ):
            return self._decision(raw, REJECTED, "INVALID_AUTHENTICATION")
        existing = self.sessions.get(session_id)
        if existing is not None:
            if existing.player_id != player_id:
                return self._decision(raw, REJECTED, "SESSION_PLAYER_MISMATCH")
            if existing.state == "WAITING_RECONNECT":
                return self._decision(raw, REJECTED, "RECONNECT_REQUIRED")
            return self._decision(raw, REJECTED, "SESSION_ALREADY_EXISTS")
        if player_id in self.players:
            return self._decision(raw, REJECTED, "PLAYER_ALREADY_EXISTS")

        self.sessions[session_id] = Session(
            session_id=session_id,
            player_id=player_id,
            epoch=epoch,
            state="ACTIVE",
            connection_id=connection_id,
        )
        self.players[player_id] = Player(player_id=player_id, session_id=session_id)
        connection.state = "AUTHENTICATED"
        connection.session_id = session_id
        created.extend((f"session:{session_id}", f"player:{player_id}"))
        return self._decision(raw, ACCEPTED, "AUTHENTICATED")

    # [Implementation 3-2]
    # Disconnect grace and expiry
    # 연결이 끊겨도 grace가 끝나기 전에는 플레이어와 경기 참가 기록을 유지합니다.
    def _on_disconnect(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        connection_id = str(raw.get("connection_id", ""))
        connection = self.connections.get(connection_id)
        if connection is None:
            return self._decision(raw, REJECTED, "CONNECTION_NOT_FOUND")
        if connection.state == "DISCONNECTED":
            return self._decision(raw, IGNORED, "ALREADY_DISCONNECTED")
        connection.state = "DISCONNECTED"
        if connection.session_id is not None:
            session = self.sessions.get(connection.session_id)
            if session is not None and session.connection_id == connection_id:
                session.state = "WAITING_RECONNECT"
                session.connection_id = None
                session.grace_deadline = self.logical_time + self.reconnect_grace
        return self._decision(raw, ACCEPTED, "DISCONNECTED")

    def _expire_waiting_sessions(self, destroyed: list[str]) -> list[str]:
        expired: list[str] = []
        for session_id in sorted(self.sessions):
            session = self.sessions[session_id]
            if (
                session.state == "WAITING_RECONNECT"
                and session.grace_deadline is not None
                and self.logical_time > session.grace_deadline
            ):
                session.state = "EXPIRED"
                session.grace_deadline = None
                expired.append(session_id)
                player = self.players.get(session.player_id)
                if player is not None:
                    self._forfeit_or_detach(player, destroyed)
        return expired

    def _forfeit_or_detach(self, player: Player, destroyed: list[str]) -> None:
        if player.room_id is None:
            return
        room = self.rooms.get(player.room_id)
        if room is None:
            player.room_id = None
            return
        if room.match_id is not None:
            match = self.matches.get(room.match_id)
            if match is not None and match.state == "RUNNING":
                match.forfeited_player_ids.add(player.player_id)
                player.forfeited = True
                if room.owner_player_id == player.player_id:
                    successors = sorted(
                        participant_id
                        for participant_id in room.player_ids
                        if participant_id not in match.forfeited_player_ids
                    )
                    if successors:
                        room.owner_player_id = successors[0]
                    else:
                        self._dispose_abandoned_match(room, match, destroyed)
                return
        room.player_ids.discard(player.player_id)
        player.room_id = None
        player.ready = False
        if room.player_ids:
            if room.owner_player_id == player.player_id:
                room.owner_player_id = min(room.player_ids)
            room.state = (
                "READY"
                if all(self.players[item].ready for item in room.player_ids)
                else "OPEN"
            )
        else:
            self.rooms.pop(room.room_id, None)
            destroyed.append(f"room:{room.room_id}")

    def _dispose_abandoned_match(
        self,
        room: Room,
        match: Match,
        destroyed: list[str],
    ) -> None:
        match.state = "FINALIZED"
        match.result_revision = 1
        for player_id in sorted(room.player_ids):
            participant = self.players.get(player_id)
            if participant is not None:
                participant.room_id = None
                participant.ready = False
        self.matches.pop(match.match_id, None)
        self.rooms.pop(room.room_id, None)
        destroyed.extend((f"match:{match.match_id}", f"room:{room.room_id}"))

    # [Implementation 3-3]
    # Epoch-checked reconnect
    # 이전 연결의 늦은 요청이 현재 세션을 다시 차지하지 못하게 epoch를 증가시킵니다.
    def _on_reconnect(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        connection_id = str(raw.get("connection_id", ""))
        session_id = str(raw.get("session_id", ""))
        player_id = str(raw.get("player_id", ""))
        epoch = raw.get("session_epoch")
        connection = self.connections.get(connection_id)
        session = self.sessions.get(session_id)
        if connection is None:
            return self._decision(raw, REJECTED, "CONNECTION_NOT_FOUND")
        if connection.state != "OPEN_UNAUTHENTICATED":
            return self._decision(raw, REJECTED, "CONNECTION_NOT_RECONNECTABLE")
        if session is None or session.player_id != player_id:
            return self._decision(raw, REJECTED, "SESSION_NOT_FOUND")
        if session.state == "EXPIRED":
            return self._decision(raw, REJECTED, "RECONNECT_GRACE_EXPIRED")
        if session.state != "WAITING_RECONNECT":
            return self._decision(raw, REJECTED, "SESSION_NOT_WAITING")
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch != session.epoch + 1:
            return self._decision(raw, REJECTED, "SESSION_EPOCH_MISMATCH")
        if session.grace_deadline is None or self.logical_time > session.grace_deadline:
            return self._decision(raw, REJECTED, "RECONNECT_GRACE_EXPIRED")

        session.epoch = epoch
        session.state = "ACTIVE"
        session.connection_id = connection_id
        session.grace_deadline = None
        connection.state = "AUTHENTICATED"
        connection.session_id = session_id
        return self._decision(raw, ACCEPTED, "RECONNECTED")


def run_scenario(scenario):
    """Expose the package boundary while later lifecycle stages are unfinished."""
    raise NotImplementedError("scenario execution is introduced in a later implementation stage")
