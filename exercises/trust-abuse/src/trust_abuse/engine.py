from __future__ import annotations

import copy
import math
from dataclasses import asdict
from typing import Any

from .model import (
    CommandDecision,
    Entity,
    Match,
    Player,
    RateLimitPolicy,
    Room,
    Session,
    TokenBucket,
)


class TrustEngine:
    def __init__(self, scenario: dict[str, Any]) -> None:
        config = scenario.get("config", {})
        self.release_id = str(config.get("release_id", ""))
        self.max_payload_bytes = self._required_non_negative_int(
            config, "max_payload_bytes"
        )
        self.max_move_delta = self._required_non_negative_int(config, "max_move_delta")
        self.coordinate_limit = self._required_non_negative_int(
            config, "coordinate_limit"
        )
        self.alert_threshold = self._required_non_negative_int(
            config, "alert_threshold"
        )
        if not self.release_id or self.alert_threshold == 0:
            raise ValueError("release_id and a positive alert_threshold are required")
        self.default_rate_limit = self._parse_policy(
            config.get("default_rate_limit", {}), "default_rate_limit"
        )
        self.rate_limits = self._parse_rate_limits(config.get("rate_limits", {}))
        initial = scenario.get("initial_state", {})
        if not isinstance(initial, dict):
            raise ValueError("initial_state must be an object")
        self.sessions = self._parse_sessions(initial.get("sessions", []))
        self.players = self._parse_players(initial.get("players", []))
        self.rooms = self._parse_rooms(initial.get("rooms", []))
        self.matches = self._parse_matches(initial.get("matches", []))
        self.entities = self._parse_entities(initial.get("entities", []))
        self._assert_identity_graph()
        self.buckets: dict[tuple[str, str, str], TokenBucket] = {}
        self.command_cache: dict[str, tuple[str, CommandDecision]] = {}
        self.command_conflicts: set[tuple[str, str]] = set()
        self.processed_event_ids: set[str] = set()
        self.audit_events: list[dict[str, Any]] = []
        self.denial_groups: dict[tuple[str, str, str], set[str]] = {}
        self.trace: list[dict[str, Any]] = []
        self.logical_time = 0

    @staticmethod
    def _is_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _required_non_negative_int(self, raw: dict[str, Any], key: str) -> int:
        value = raw.get(key)
        if not self._is_int(value) or value < 0:
            raise ValueError(f"{key} must be a non-negative integer")
        return value

    def _parse_policy(self, raw: Any, name: str) -> RateLimitPolicy:
        if not isinstance(raw, dict):
            raise ValueError(f"{name} must be an object")
        capacity = raw.get("capacity")
        refill = raw.get("refill_per_tick")
        if (
            not self._is_int(capacity)
            or capacity <= 0
            or not self._is_int(refill)
            or refill < 0
        ):
            raise ValueError(f"{name} is invalid")
        return RateLimitPolicy(capacity=capacity, refill_per_tick=refill)

    def _parse_rate_limits(self, raw: Any) -> dict[str, RateLimitPolicy]:
        if not isinstance(raw, dict):
            raise ValueError("rate_limits must be an object")
        return {str(kind): self._parse_policy(value, str(kind)) for kind, value in raw.items()}

    def _parse_sessions(self, raw_items: Any) -> dict[str, Session]:
        if not isinstance(raw_items, list):
            raise ValueError("sessions must be an array")
        result: dict[str, Session] = {}
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise ValueError("session must be an object")
            session_id = str(raw.get("session_id", ""))
            epoch = raw.get("session_epoch")
            active = raw.get("active", True)
            if (
                not session_id
                or session_id in result
                or not self._is_int(epoch)
                or epoch < 1
                or not isinstance(active, bool)
            ):
                raise ValueError("session fields are invalid")
            result[session_id] = Session(
                session_id=session_id,
                actor_id=str(raw.get("actor_id", "")),
                player_id=str(raw.get("player_id", "")),
                connection_id=str(raw.get("connection_id", "")),
                epoch=epoch,
                active=active,
            )
        return result

    def _parse_players(self, raw_items: Any) -> dict[str, Player]:
        if not isinstance(raw_items, list):
            raise ValueError("players must be an array")
        result: dict[str, Player] = {}
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise ValueError("player must be an object")
            player_id = str(raw.get("player_id", ""))
            numeric = {
                "x": raw.get("x", 0),
                "y": raw.get("y", 0),
                "score": raw.get("score", 0),
                "last_sequence": raw.get("last_sequence", 0),
            }
            if (
                not player_id
                or player_id in result
                or any(not self._is_int(value) for value in numeric.values())
                or numeric["last_sequence"] < 0
            ):
                raise ValueError("player fields are invalid")
            result[player_id] = Player(
                player_id=player_id,
                session_id=str(raw.get("session_id", "")),
                room_id=str(raw.get("room_id", "")),
                match_id=str(raw.get("match_id", "")),
                **numeric,
            )
        return result

    def _parse_rooms(self, raw_items: Any) -> dict[str, Room]:
        if not isinstance(raw_items, list):
            raise ValueError("rooms must be an array")
        result: dict[str, Room] = {}
        for raw in raw_items:
            if not isinstance(raw, dict) or not isinstance(raw.get("player_ids"), list):
                raise ValueError("room fields are invalid")
            room_id = str(raw.get("room_id", ""))
            if not room_id or room_id in result:
                raise ValueError("room_id must be unique and non-empty")
            result[room_id] = Room(
                room_id=room_id,
                player_ids=frozenset(str(item) for item in raw["player_ids"]),
            )
        return result

    def _parse_matches(self, raw_items: Any) -> dict[str, Match]:
        if not isinstance(raw_items, list):
            raise ValueError("matches must be an array")
        result: dict[str, Match] = {}
        for raw in raw_items:
            if not isinstance(raw, dict) or not isinstance(raw.get("player_ids"), list):
                raise ValueError("match fields are invalid")
            match_id = str(raw.get("match_id", ""))
            if not match_id or match_id in result:
                raise ValueError("match_id must be unique and non-empty")
            result[match_id] = Match(
                match_id=match_id,
                room_id=str(raw.get("room_id", "")),
                state=str(raw.get("state", "")),
                player_ids=frozenset(str(item) for item in raw["player_ids"]),
            )
        return result

    def _parse_entities(self, raw_items: Any) -> dict[str, Entity]:
        if not isinstance(raw_items, list):
            raise ValueError("entities must be an array")
        result: dict[str, Entity] = {}
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise ValueError("entity must be an object")
            entity_id = str(raw.get("entity_id", ""))
            use_count = raw.get("use_count", 0)
            if (
                not entity_id
                or entity_id in result
                or not self._is_int(use_count)
                or use_count < 0
            ):
                raise ValueError("entity fields are invalid")
            result[entity_id] = Entity(
                entity_id=entity_id,
                room_id=str(raw.get("room_id", "")),
                match_id=str(raw.get("match_id", "")),
                owner_player_id=str(raw.get("owner_player_id", "")),
                use_count=use_count,
            )
        return result

    # [Implementation 2]
    # Initial identity and membership consistency
    # 세션, 플레이어, 방, 경기, entity가 서로 같은 식별자를 가리키는지 시작 시 확인합니다.
    def _assert_identity_graph(self) -> None:
        for session in self.sessions.values():
            if (
                not session.actor_id
                or not session.connection_id
                or session.player_id not in self.players
                or self.players[session.player_id].session_id != session.session_id
            ):
                raise ValueError("session and player identity graph is inconsistent")
        for player in self.players.values():
            session = self.sessions.get(player.session_id)
            room = self.rooms.get(player.room_id)
            match = self.matches.get(player.match_id)
            if (
                session is None
                or session.player_id != player.player_id
                or room is None
                or match is None
                or player.player_id not in room.player_ids
                or player.player_id not in match.player_ids
                or match.room_id != room.room_id
            ):
                raise ValueError("player identity or membership is inconsistent")
        for room in self.rooms.values():
            if any(
                player_id not in self.players
                or self.players[player_id].room_id != room.room_id
                for player_id in room.player_ids
            ):
                raise ValueError("room membership is inconsistent")
        for match in self.matches.values():
            if match.room_id not in self.rooms or any(
                player_id not in self.players
                or self.players[player_id].match_id != match.match_id
                for player_id in match.player_ids
            ):
                raise ValueError("match membership is inconsistent")
        for entity in self.entities.values():
            owner = self.players.get(entity.owner_player_id)
            if (
                owner is None
                or entity.room_id != owner.room_id
                or entity.match_id != owner.match_id
            ):
                raise ValueError("entity ownership is inconsistent")

    # [Implementation 3]
    # Payload size and finite-number checks
    # NaN과 infinity를 JSON digest에 그대로 넣지 않고 안전한 표기로 바꿉니다.
    def _contains_non_finite(self, value: Any) -> bool:
        if isinstance(value, float):
            return not math.isfinite(value)
        if isinstance(value, dict):
            return any(self._contains_non_finite(item) for item in value.values())
        if isinstance(value, list):
            return any(self._contains_non_finite(item) for item in value)
        return False

    def _safe_value(self, value: Any) -> Any:
        if isinstance(value, float) and not math.isfinite(value):
            if math.isnan(value):
                return {"non_finite": "NaN"}
            return {"non_finite": "Infinity" if value > 0 else "-Infinity"}
        if isinstance(value, dict):
            return {str(key): self._safe_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._safe_value(item) for item in value]
        return value

    # [Implementation 4]
    # Command envelope normalization
    # 필수 식별자와 수치 형식을 확인하고 audit에 남길 payload 요약을 만듭니다.
    def _normalize_command(self, raw: Any) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(raw, dict):
            return None, "INVALID_COMMAND"
        required = (
            "command_id",
            "actor_id",
            "session_id",
            "connection_id",
            "session_epoch",
            "player_id",
            "room_id",
            "match_id",
            "sequence",
            "kind",
            "payload",
        )
        if any(key not in raw for key in required):
            return None, "INVALID_COMMAND"
        numeric = (raw["session_epoch"], raw["sequence"])
        if any(not self._is_int(value) or value < 0 for value in numeric):
            return None, "INVALID_NUMERIC_VALUE"

        payload = raw["payload"]
        payload_error: str | None = None
        if not isinstance(payload, dict):
            payload = {}
            payload_error = "INVALID_PAYLOAD"
        safe_payload = self._safe_value(payload)
        payload_size = canonical_size(safe_payload)
        if payload_error is None and self._contains_non_finite(payload):
            payload_error = "INVALID_NUMERIC_VALUE"
        if payload_error is None and payload_size > self.max_payload_bytes:
            payload_error = "PAYLOAD_TOO_LARGE"

        command = {
            "command_id": str(raw["command_id"]),
            "actor_id": str(raw["actor_id"]),
            "session_id": str(raw["session_id"]),
            "connection_id": str(raw["connection_id"]),
            "session_epoch": raw["session_epoch"],
            "player_id": str(raw["player_id"]),
            "room_id": str(raw["room_id"]),
            "match_id": str(raw["match_id"]),
            "sequence": raw["sequence"],
            "kind": str(raw["kind"]),
            "payload": copy.deepcopy(payload),
            "safe_payload": safe_payload,
            "payload_size": payload_size,
        }
        if any(
            not command[key]
            for key in required
            if key not in ("payload", "session_epoch", "sequence")
        ):
            return None, "INVALID_COMMAND"
        return command, payload_error

    # [Implementation 5]
    # Session epoch and connection validation
    # 인증된 세션의 actor, player, connection, epoch와 요청 값을 모두 비교합니다.
    def _validate_session(self, command: dict[str, Any]) -> tuple[Session | None, str | None]:
        session = self.sessions.get(command["session_id"])
        if session is None or not session.active:
            return None, "SESSION_NOT_ACTIVE"
        if session.actor_id != command["actor_id"]:
            return session, "ACTOR_SESSION_MISMATCH"
        if session.player_id != command["player_id"]:
            return session, "PLAYER_SESSION_MISMATCH"
        if session.connection_id != command["connection_id"]:
            return session, "CONNECTION_MISMATCH"
        if session.epoch != command["session_epoch"]:
            return session, "SESSION_EPOCH_MISMATCH"
        return session, None

    # [Implementation 5-1]
    # Room, match, and ownership validation
    # 현재 방과 경기 참가자에게 허용된 entity만 사용할 수 있게 합니다.
    def _validate_membership(
        self, command: dict[str, Any]
    ) -> tuple[Player | None, str | None]:
        player = self.players.get(command["player_id"])
        if player is None:
            return None, "PLAYER_NOT_FOUND"
        if player.room_id != command["room_id"]:
            return None, "ROOM_MISMATCH"
        if player.match_id != command["match_id"]:
            return None, "MATCH_MISMATCH"
        room = self.rooms.get(command["room_id"])
        match = self.matches.get(command["match_id"])
        if room is None or player.player_id not in room.player_ids:
            return None, "ROOM_MEMBERSHIP_MISMATCH"
        if (
            match is None
            or match.state != "RUNNING"
            or match.room_id != room.room_id
            or player.player_id not in match.player_ids
        ):
            return None, "MATCH_NOT_ACTIVE"
        return player, None

    def _policy_for(self, kind: str) -> RateLimitPolicy:
        return self.rate_limits.get(kind, self.default_rate_limit)

    # [Implementation 6]
    # Logical-time token bucket
    # 실제 시각 대신 이벤트의 logical time으로 token을 보충합니다.
    def _consume_rate_limit(
        self,
        session: Session,
        player: Player,
        kind: str,
        logical_time: int,
    ) -> tuple[bool, TokenBucket]:
        policy = self._policy_for(kind)
        # [Implementation 6-1]
        # Reconnect-stable rate-limit keys
        # connection ID를 key에서 빼 reconnect로 기존 제한을 우회하지 못하게 합니다.
        key = (session.session_id, player.player_id, kind)
        bucket = self.buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(tokens=policy.capacity, last_tick=logical_time)
            self.buckets[key] = bucket
        elapsed = max(0, logical_time - bucket.last_tick)
        bucket.tokens = min(
            policy.capacity,
            bucket.tokens + elapsed * policy.refill_per_tick,
        )
        bucket.last_tick = logical_time
        if bucket.tokens <= 0:
            return False, bucket
        bucket.tokens -= 1
        return True, bucket

    # [Implementation 7]
    # Validate and prepare authoritative changes
    # 정본 상태를 직접 바꾸지 않고 적용할 다음 값을 먼저 계산합니다.
    def _validate_and_prepare_change(
        self,
        player: Player,
        command: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str | None]:
        kind = command["kind"]
        payload = command["payload"]
        if kind in ("SET_POSITION", "SET_SCORE", "CLAIM_OWNERSHIP"):
            return None, "CLIENT_AUTHORITY_VIOLATION"
        if kind == "MOVE":
            dx = payload.get("dx")
            dy = payload.get("dy")
            if not self._is_int(dx) or not self._is_int(dy):
                return None, "INVALID_PAYLOAD"
            if abs(dx) > self.max_move_delta or abs(dy) > self.max_move_delta:
                return None, "MOVE_LIMIT_EXCEEDED"
            next_x = player.x + dx
            next_y = player.y + dy
            if (
                next_x < -self.coordinate_limit
                or next_x > self.coordinate_limit
                or next_y < -self.coordinate_limit
                or next_y > self.coordinate_limit
            ):
                return None, "COORDINATE_LIMIT_EXCEEDED"
            return {"kind": "MOVE", "x": next_x, "y": next_y}, None
        if kind == "USE_OWNED_ENTITY":
            entity_id = payload.get("entity_id")
            if not isinstance(entity_id, str) or not entity_id:
                return None, "INVALID_PAYLOAD"
            entity = self.entities.get(entity_id)
            if entity is None:
                return None, "ENTITY_NOT_FOUND"
            if entity.room_id != player.room_id or entity.match_id != player.match_id:
                return None, "ENTITY_SCOPE_MISMATCH"
            if entity.owner_player_id != player.player_id:
                return None, "ENTITY_OWNERSHIP_MISMATCH"
            if entity.use_count >= 2_147_483_647:
                return None, "ARITHMETIC_OVERFLOW"
            return {
                "kind": "USE_OWNED_ENTITY",
                "entity_id": entity_id,
                "use_count": entity.use_count + 1,
            }, None
        return None, "UNSUPPORTED_COMMAND"

    # [Implementation 7-1]
    # Commit sequence after state change
    # 상태 변경이 끝난 뒤에만 sequence를 갱신합니다.
    def _commit_change(
        self,
        player: Player,
        command: dict[str, Any],
        change: dict[str, Any],
    ) -> dict[str, Any]:
        if change["kind"] == "MOVE":
            player.x = change["x"]
            player.y = change["y"]
            applied = {"player_id": player.player_id, "x": player.x, "y": player.y}
        else:
            entity = self.entities[change["entity_id"]]
            entity.use_count = change["use_count"]
            applied = {"entity_id": entity.entity_id, "use_count": entity.use_count}
        player.last_sequence = command["sequence"]
        applied["last_sequence"] = player.last_sequence
        return applied

    def _command_fingerprint(self, command: dict[str, Any]) -> str:
        return digest_value(
            {
                key: value
                for key, value in command.items()
                if key not in ("payload_size", "payload")
            }
        )

    def _redacted_audit(
        self,
        command: dict[str, Any],
        decision: CommandDecision,
    ) -> dict[str, Any]:
        actor_id = command.get("authenticated_actor_id", command["actor_id"])
        return {
            "audit_id": digest_value(
                {
                    "command_id": command["command_id"],
                    "command_fingerprint": self._command_fingerprint(command),
                    "decision": decision.status,
                    "reason_code": decision.reason_code,
                    "release_id": self.release_id,
                }
            ),
            "actor_id": actor_id,
            "claimed_actor_id": command["actor_id"],
            "session_id": command["session_id"],
            "player_id": command["player_id"],
            "room_id": command["room_id"],
            "match_id": command["match_id"],
            "command_id": command["command_id"],
            "command_kind": command["kind"],
            "decision": decision.status,
            "reason_code": decision.reason_code,
            "release_id": self.release_id,
            "payload_size": command["payload_size"],
            "payload_digest": digest_value(command["safe_payload"]),
        }

    # [Implementation 8]
    # Redacted audit records
    # 원문 payload와 인증 token 대신 크기, digest, 판정 사유만 기록합니다.
    def _record_audit(
        self,
        command: dict[str, Any],
        decision: CommandDecision,
    ) -> None:
        self.audit_events.append(self._redacted_audit(command, decision))
        if decision.status == "DENY":
            key = (
                command.get("authenticated_actor_id", command["actor_id"]),
                command["match_id"],
                decision.reason_code,
            )
            self.denial_groups.setdefault(key, set()).add(command["command_id"])

    def _deny(
        self,
        command: dict[str, Any],
        reason: str,
        fingerprint: str,
        *,
        cache: bool = True,
    ) -> CommandDecision:
        decision = CommandDecision(command["command_id"], "DENY", reason)
        if cache:
            self.command_cache[command["command_id"]] = (fingerprint, decision)
        self._record_audit(command, decision)
        return decision

    def handle_command(self, raw: Any, logical_time: int) -> CommandDecision:
        command, error = self._normalize_command(raw)
        if command is None:
            command_id = (
                str(raw.get("command_id", "invalid-command"))
                if isinstance(raw, dict)
                else "invalid-command"
            )
            return CommandDecision(command_id, "DENY", error or "INVALID_COMMAND")
        fingerprint = self._command_fingerprint(command)
        known_session = self.sessions.get(command["session_id"])
        if known_session is not None:
            command["authenticated_actor_id"] = known_session.actor_id

        # [Implementation 9]
        # Duplicate command decision reuse
        # 같은 command ID는 최초 판정을 재사용하고 충돌 요청이 audit 수를 계속 늘리지 못하게 합니다.
        cached = self.command_cache.get(command["command_id"])
        if cached is not None:
            cached_fingerprint, cached_decision = cached
            if cached_fingerprint == fingerprint:
                return CommandDecision(
                    command["command_id"],
                    "IGNORED",
                    "DUPLICATE_COMMAND",
                    cached_decision.applied_changes,
                )
            conflict = (command["command_id"], fingerprint)
            if conflict in self.command_conflicts:
                return CommandDecision(
                    command["command_id"],
                    "IGNORED",
                    "DUPLICATE_COMMAND_ID_CONFLICT",
                )
            self.command_conflicts.add(conflict)
            return self._deny(
                command,
                "COMMAND_ID_CONFLICT",
                fingerprint,
                cache=False,
            )

        session, reason = self._validate_session(command)
        if reason is not None or session is None:
            return self._deny(command, reason or "SESSION_NOT_ACTIVE", fingerprint)
        player, reason = self._validate_membership(command)
        if reason is not None or player is None:
            return self._deny(command, reason or "PLAYER_NOT_FOUND", fingerprint)

        allowed, _bucket = self._consume_rate_limit(
            session,
            player,
            command["kind"],
            logical_time,
        )
        if not allowed:
            return self._deny(command, "RATE_LIMITED", fingerprint)

        if error is not None:
            return self._deny(command, error, fingerprint)

        if command["sequence"] <= player.last_sequence:
            return self._deny(command, "STALE_SEQUENCE", fingerprint)
        if command["sequence"] != player.last_sequence + 1:
            return self._deny(command, "SEQUENCE_GAP", fingerprint)

        change, reason = self._validate_and_prepare_change(player, command)
        if reason is not None or change is None:
            return self._deny(command, reason or "INVALID_COMMAND", fingerprint)
        applied = self._commit_change(player, command, change)
        decision = CommandDecision(command["command_id"], "ALLOW", "ALLOWED", applied)
        self.command_cache[command["command_id"]] = (fingerprint, decision)
        self._record_audit(command, decision)
        return decision

    def reconnect(self, raw: dict[str, Any]) -> tuple[str, str]:
        session_id = str(raw.get("session_id", ""))
        connection_id = str(raw.get("new_connection_id", ""))
        epoch = raw.get("session_epoch")
        session = self.sessions.get(session_id)
        if session is None:
            return "REJECTED", "SESSION_NOT_FOUND"
        if (
            not connection_id
            or not self._is_int(epoch)
            or epoch != session.epoch + 1
        ):
            return "REJECTED", "SESSION_EPOCH_MISMATCH"
        if any(
            other.session_id != session_id
            and other.active
            and other.connection_id == connection_id
            for other in self.sessions.values()
        ):
            return "REJECTED", "CONNECTION_ALREADY_BOUND"
        session.connection_id = connection_id
        session.epoch = epoch
        session.active = True
        return "ACCEPTED", "RECONNECTED"

    def apply_event(self, raw: dict[str, Any]) -> None:
        event_id = str(raw.get("event_id", ""))
        kind = str(raw.get("kind", ""))
        logical_time = raw.get("logical_time")
        if (
            not event_id
            or not kind
            or not self._is_int(logical_time)
            or logical_time < self.logical_time
        ):
            raise ValueError("event_id, kind, and non-decreasing logical_time are required")
        self.logical_time = logical_time
        details: dict[str, Any] = {}
        if event_id in self.processed_event_ids:
            status, reason = "IGNORED", "DUPLICATE_EVENT"
        else:
            self.processed_event_ids.add(event_id)
            if kind == "COMMAND":
                decision = self.handle_command(raw.get("command"), logical_time)
                status, reason = decision.status, decision.reason_code
                details["decision"] = asdict(decision)
            elif kind == "RECONNECT":
                status, reason = self.reconnect(raw)
            else:
                status, reason = "REJECTED", "UNKNOWN_EVENT"
        self.trace.append(
            {
                "event_id": event_id,
                "kind": kind,
                "logical_time": logical_time,
                "status": status,
                "reason_code": reason,
                **details,
                "state_digest": digest_value(self._state_dict()),
            }
        )


def run_scenario(scenario):
    """Expose the package boundary while later lifecycle stages are unfinished."""
    raise NotImplementedError("scenario execution is introduced in a later implementation stage")
