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


def run_scenario(scenario):
    """Expose the package boundary while later lifecycle stages are unfinished."""
    raise NotImplementedError("scenario execution is introduced in a later implementation stage")
