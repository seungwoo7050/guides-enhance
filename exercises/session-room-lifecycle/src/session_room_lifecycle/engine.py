from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .model import Connection, EventDecision, Match, Player, Room, Session
from .serialization import digest_result


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

    # [Implementation 4]
    # Room creation and membership
    # 방의 정원 확인과 참가자 추가를 한 이벤트 처리 안에서 끝냅니다.
    def _on_create_room(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        if self.server_state != "ACTIVE":
            return self._decision(raw, REJECTED, "SERVER_DRAINING")
        player, error = self._authenticated_player(raw)
        if error:
            return self._decision(raw, REJECTED, error)
        assert player is not None
        room_id = str(raw.get("room_id", ""))
        if not room_id:
            return self._decision(raw, REJECTED, "INVALID_ROOM_ID")
        if room_id in self.rooms:
            return self._decision(raw, REJECTED, "ROOM_ALREADY_EXISTS")
        if player.room_id is not None:
            return self._decision(raw, REJECTED, "PLAYER_ALREADY_IN_ROOM")
        room = Room(room_id=room_id, owner_player_id=player.player_id)
        room.player_ids.add(player.player_id)
        self.rooms[room_id] = room
        player.room_id = room_id
        player.ready = False
        created.append(f"room:{room_id}")
        return self._decision(raw, ACCEPTED, "ROOM_CREATED")

    # [Implementation 4-1]
    # Duplicate-safe readiness updates
    # 같은 참가 또는 준비 이벤트가 다시 와도 인원수와 준비 상태를 두 번 바꾸지 않습니다.
    def _on_join_room(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        if self.server_state != "ACTIVE":
            return self._decision(raw, REJECTED, "SERVER_DRAINING")
        player, error = self._authenticated_player(raw)
        if error:
            return self._decision(raw, REJECTED, error)
        assert player is not None
        room_id = str(raw.get("room_id", ""))
        room = self.rooms.get(room_id)
        if room is None:
            return self._decision(raw, REJECTED, "ROOM_NOT_FOUND")
        if room.state not in ("OPEN", "READY"):
            return self._decision(raw, REJECTED, "ROOM_NOT_JOINABLE")
        if player.room_id == room_id:
            return self._decision(raw, IGNORED, "ALREADY_IN_ROOM")
        if player.room_id is not None:
            return self._decision(raw, REJECTED, "PLAYER_ALREADY_IN_ROOM")
        room.player_ids.add(player.player_id)
        room.state = "OPEN"
        player.room_id = room_id
        player.ready = False
        return self._decision(raw, ACCEPTED, "ROOM_JOINED")

    def _on_ready(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        player, error = self._authenticated_player(raw)
        if error:
            return self._decision(raw, REJECTED, error)
        assert player is not None
        room = self.rooms.get(str(raw.get("room_id", "")))
        if room is None or player.player_id not in room.player_ids:
            return self._decision(raw, REJECTED, "PLAYER_NOT_IN_ROOM")
        if room.state not in ("OPEN", "READY"):
            return self._decision(raw, REJECTED, "ROOM_NOT_READYABLE")
        if player.ready:
            return self._decision(raw, IGNORED, "ALREADY_READY")
        player.ready = True
        if room.player_ids and all(self.players[item].ready for item in room.player_ids):
            room.state = "READY"
        return self._decision(raw, ACCEPTED, "PLAYER_READY")

    def _on_leave_room(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        player, error = self._authenticated_player(raw)
        if error:
            return self._decision(raw, REJECTED, error)
        assert player is not None
        room = self.rooms.get(str(raw.get("room_id", "")))
        if room is None or player.player_id not in room.player_ids:
            return self._decision(raw, REJECTED, "PLAYER_NOT_IN_ROOM")
        if room.match_id is not None:
            match = self.matches.get(room.match_id)
            if match is not None and match.state == "RUNNING":
                return self._decision(raw, REJECTED, "MATCH_RUNNING")
        room.player_ids.remove(player.player_id)
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
            self.rooms.pop(room.room_id)
            destroyed.append(f"room:{room.room_id}")
        return self._decision(raw, ACCEPTED, "ROOM_LEFT")

    # [Implementation 5]
    # Match start and phase transitions
    # 참가자와 준비 상태를 확인한 뒤에만 경기를 시작합니다.
    def _on_start_match(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        if self.server_state != "ACTIVE":
            return self._decision(raw, REJECTED, "SERVER_DRAINING")
        player, error = self._authenticated_player(raw)
        if error:
            return self._decision(raw, REJECTED, error)
        assert player is not None
        room = self.rooms.get(str(raw.get("room_id", "")))
        match_id = str(raw.get("match_id", ""))
        if room is None:
            return self._decision(raw, REJECTED, "ROOM_NOT_FOUND")
        if player.player_id != room.owner_player_id:
            return self._decision(raw, REJECTED, "ROOM_OWNER_REQUIRED")
        if room.state != "READY":
            return self._decision(raw, REJECTED, "ROOM_NOT_READY")
        if not match_id or match_id in self.matches:
            return self._decision(raw, REJECTED, "MATCH_ALREADY_EXISTS")
        match = Match(match_id=match_id, room_id=room.room_id)
        match.participant_ids.update(room.player_ids)
        self.matches[match_id] = match
        room.match_id = match_id
        room.state = "IN_MATCH"
        created.append(f"match:{match_id}")
        return self._decision(raw, ACCEPTED, "MATCH_STARTED")

    # [Implementation 5-1]
    # Result finalization and expired-player cleanup
    # 경기 결과는 한 번만 확정하고, 만료된 플레이어는 경기 상태에 맞춰 정리합니다.
    def _on_end_match(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        player, error = self._authenticated_player(raw)
        if error:
            return self._decision(raw, REJECTED, error)
        assert player is not None
        match_id = str(raw.get("match_id", ""))
        match = self.matches.get(match_id)
        if match is None:
            return self._decision(raw, REJECTED, "MATCH_NOT_FOUND")
        room = self.rooms.get(match.room_id)
        if room is None or player.player_id != room.owner_player_id:
            return self._decision(raw, REJECTED, "ROOM_OWNER_REQUIRED")
        if match.state == "FINALIZED":
            return self._decision(raw, IGNORED, "MATCH_ALREADY_FINALIZED")
        match.state = "FINALIZED"
        match.result_revision = 1
        room.state = "CLOSING"
        for player_id in sorted(match.forfeited_player_ids):
            expired_player = self.players.get(player_id)
            if expired_player is not None:
                room.player_ids.discard(player_id)
                expired_player.room_id = None
                expired_player.ready = False
        if not room.player_ids:
            self.matches.pop(match.match_id, None)
            self.rooms.pop(room.room_id, None)
            destroyed.extend((f"match:{match.match_id}", f"room:{room.room_id}"))
        elif room.owner_player_id not in room.player_ids:
            room.owner_player_id = min(room.player_ids)
        return self._decision(raw, ACCEPTED, "MATCH_FINALIZED")

    def _on_close_room(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        player, error = self._authenticated_player(raw)
        if error:
            return self._decision(raw, REJECTED, error)
        assert player is not None
        room_id = str(raw.get("room_id", ""))
        room = self.rooms.get(room_id)
        if room is None:
            return self._decision(raw, REJECTED, "ROOM_NOT_FOUND")
        if player.player_id != room.owner_player_id:
            return self._decision(raw, REJECTED, "ROOM_OWNER_REQUIRED")
        if room.match_id is not None:
            match = self.matches.get(room.match_id)
            if match is not None and match.state == "RUNNING":
                return self._decision(raw, REJECTED, "MATCH_RUNNING")
            if match is not None:
                self.matches.pop(match.match_id)
                destroyed.append(f"match:{match.match_id}")
        for player_id in sorted(room.player_ids):
            member = self.players.get(player_id)
            if member is not None:
                member.room_id = None
                member.ready = False
        self.rooms.pop(room_id)
        destroyed.append(f"room:{room_id}")
        return self._decision(raw, ACCEPTED, "ROOM_CLOSED")

    # [Implementation 6]
    # Drain admission checks
    # drain을 시작하면 기존 경기는 유지하되 새 방, 참가, 경기 시작은 받지 않습니다.
    def _on_begin_drain(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        if self.server_state == "DRAINING":
            return self._decision(raw, IGNORED, "ALREADY_DRAINING")
        self.server_state = "DRAINING"
        return self._decision(raw, ACCEPTED, "DRAIN_STARTED")

    # [Implementation 7]
    # Shutdown cleanup
    # 종료 뒤 연결, 세션, 플레이어, 방, 경기 참조가 남지 않게 모두 제거합니다.
    def _on_shutdown(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        if self.server_state == "SHUTDOWN":
            return self._decision(raw, IGNORED, "ALREADY_SHUTDOWN")
        destroyed.extend(f"match:{item}" for item in sorted(self.matches))
        destroyed.extend(f"room:{item}" for item in sorted(self.rooms))
        destroyed.extend(f"player:{item}" for item in sorted(self.players))
        destroyed.extend(f"session:{item}" for item in sorted(self.sessions))
        destroyed.extend(f"connection:{item}" for item in sorted(self.connections))
        self.matches.clear()
        self.rooms.clear()
        self.players.clear()
        self.sessions.clear()
        self.connections.clear()
        self.server_state = "SHUTDOWN"
        return self._decision(raw, ACCEPTED, "SHUTDOWN_COMPLETE")

    def _on_advance_time(
        self,
        raw: dict[str, Any],
        created: list[str],
        destroyed: list[str],
    ) -> EventDecision:
        return self._decision(raw, ACCEPTED, "TIME_ADVANCED")

    def _assert_invariants(self) -> None:
        for connection in self.connections.values():
            if connection.state == "AUTHENTICATED":
                assert connection.session_id in self.sessions
        for session in self.sessions.values():
            assert session.player_id in self.players
            if session.state == "ACTIVE":
                assert session.connection_id in self.connections
                assert self.connections[session.connection_id].session_id == session.session_id
            else:
                assert session.connection_id is None
        for room in self.rooms.values():
            assert room.owner_player_id in room.player_ids
            for player_id in room.player_ids:
                assert self.players[player_id].room_id == room.room_id
            if room.match_id is not None:
                assert room.match_id in self.matches
        for match in self.matches.values():
            assert match.room_id in self.rooms

    def snapshot(self) -> dict[str, Any]:
        return {
            "logical_time": self.logical_time,
            "server_state": self.server_state,
            "connections": [
                asdict(self.connections[item]) for item in sorted(self.connections)
            ],
            "sessions": [asdict(self.sessions[item]) for item in sorted(self.sessions)],
            "players": [asdict(self.players[item]) for item in sorted(self.players)],
            "rooms": [
                {
                    **asdict(self.rooms[item]),
                    "player_ids": sorted(self.rooms[item].player_ids),
                }
                for item in sorted(self.rooms)
            ],
            "matches": [
                {
                    **asdict(self.matches[item]),
                    "participant_ids": sorted(self.matches[item].participant_ids),
                    "forfeited_player_ids": sorted(
                        self.matches[item].forfeited_player_ids
                    ),
                }
                for item in sorted(self.matches)
            ],
        }


def run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be an object")
    config = scenario.get("config", {})
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    reconnect_grace = config.get("reconnect_grace", 0)
    if not isinstance(reconnect_grace, int) or isinstance(reconnect_grace, bool):
        raise ValueError("reconnect_grace must be an integer")
    engine = LifecycleEngine(reconnect_grace)
    events = scenario.get("events", [])
    if not isinstance(events, list):
        raise ValueError("events must be an array")
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("each event must be an object")
        engine.apply_event(event)
    result: dict[str, Any] = {
        "trace": engine.trace,
        "final_state": engine.snapshot(),
    }
    result["digest"] = digest_result(result)
    return result
