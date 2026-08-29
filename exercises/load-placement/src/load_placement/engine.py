from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .model import MatchRequest, RequestDecision, Reservation, Server, ServerLimits


class PlacementEngine:
    def __init__(self, scenario: dict[str, Any]) -> None:
        policy = scenario.get("policy", {})
        self.stale_after = self._required_non_negative_int(policy, "stale_after")
        self.max_queue_size = self._required_non_negative_int(policy, "max_queue_size")
        self.soft_headroom = self._parse_headroom(policy.get("soft_headroom", {}))
        self.servers = self._parse_servers(scenario.get("servers", []))
        self.decisions: dict[str, RequestDecision] = {}
        self.requests: dict[str, MatchRequest] = {}
        self.reservations: dict[str, Reservation] = {}
        self.queue: list[str] = []
        self.processed_event_ids: set[str] = set()
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

    def _parse_headroom(self, raw: Any) -> dict[str, int]:
        if not isinstance(raw, dict):
            raise ValueError("soft_headroom must be an object")
        result = {
            "rooms": raw.get("rooms", 0),
            "players": raw.get("players", 0),
            "tick_cost": raw.get("tick_cost", 0),
            "outbound_bytes": raw.get("outbound_bytes", 0),
            "memory": raw.get("memory", 0),
        }
        if any(not self._is_int(value) or value < 0 for value in result.values()):
            raise ValueError("soft_headroom values must be non-negative integers")
        return result

    # [Implementation 2]
    # Scenario server and request validation
    # 서버 사용량과 요청 비용을 상태 변경 전에 검증합니다.
    def _parse_servers(self, raw_servers: Any) -> dict[str, Server]:
        if not isinstance(raw_servers, list):
            raise ValueError("servers must be an array")
        servers: dict[str, Server] = {}
        for raw in raw_servers:
            if not isinstance(raw, dict):
                raise ValueError("server must be an object")
            server_id = str(raw.get("server_id", ""))
            if not server_id or server_id in servers:
                raise ValueError("server_id must be unique and non-empty")
            state = str(raw.get("state", ""))
            if state not in ("ACTIVE", "DRAINING", "UNAVAILABLE"):
                raise ValueError("server state is invalid")
            protocols = raw.get("protocol_versions")
            limits_raw = raw.get("limits")
            release_id = raw.get("release_id")
            region = raw.get("region")
            if (
                not isinstance(protocols, list)
                or not protocols
                or any(not isinstance(item, str) or not item for item in protocols)
                or not isinstance(limits_raw, dict)
                or not isinstance(release_id, str)
                or not release_id
                or not isinstance(region, str)
                or not region
            ):
                raise ValueError("server identity, protocols, and limits are required")
            limits = ServerLimits(
                max_rooms=self._required_non_negative_int(limits_raw, "max_rooms"),
                max_players=self._required_non_negative_int(limits_raw, "max_players"),
                max_tick_cost=self._required_non_negative_int(limits_raw, "max_tick_cost"),
                max_outbound_bytes=self._required_non_negative_int(
                    limits_raw, "max_outbound_bytes"
                ),
                max_memory=self._required_non_negative_int(limits_raw, "max_memory"),
            )
            usage = {
                "room_count": raw.get("room_count"),
                "player_count": raw.get("player_count"),
                "tick_cost_used": raw.get("tick_cost_used"),
                "outbound_bytes_used": raw.get("outbound_bytes_used"),
                "memory_used": raw.get("memory_used"),
                "last_heartbeat": raw.get("last_heartbeat"),
            }
            if any(not self._is_int(value) or value < 0 for value in usage.values()):
                raise ValueError("server usage values must be non-negative integers")
            server = Server(
                server_id=server_id,
                release_id=release_id,
                protocol_versions=tuple(protocols),
                region=region,
                state=state,  # type: ignore[arg-type]
                limits=limits,
                **usage,
            )
            self._assert_server_within_hard_limits(server)
            servers[server_id] = server
        return servers

    def _parse_request(self, raw: Any) -> MatchRequest:
        if not isinstance(raw, dict):
            raise ValueError("request must be an object")
        request_id = raw.get("request_id")
        protocol_version = raw.get("required_protocol_version")
        preferences = raw.get("region_preferences", [])
        if (
            not isinstance(request_id, str)
            or not request_id
            or not isinstance(protocol_version, str)
            or not protocol_version
            or not isinstance(preferences, list)
            or any(not isinstance(item, str) or not item for item in preferences)
        ):
            raise ValueError("request identity, protocol, and region preferences are invalid")
        values = {
            "expected_players": raw.get("expected_players"),
            "estimated_tick_cost": raw.get("estimated_tick_cost"),
            "estimated_bandwidth": raw.get("estimated_bandwidth"),
            "estimated_memory": raw.get("estimated_memory", 0),
            "created_at": raw.get("created_at"),
            "deadline": raw.get("deadline"),
        }
        if any(not self._is_int(value) or value < 0 for value in values.values()):
            raise ValueError("request numeric fields must be non-negative integers")
        if values["expected_players"] <= 0 or values["deadline"] < values["created_at"]:
            raise ValueError("request players or deadline are invalid")
        return MatchRequest(
            request_id=request_id,
            required_protocol_version=protocol_version,
            region_preferences=tuple(preferences),
            **values,
        )

    def _assert_server_within_hard_limits(self, server: Server) -> None:
        if (
            server.room_count > server.limits.max_rooms
            or server.player_count > server.limits.max_players
            or server.tick_cost_used > server.limits.max_tick_cost
            or server.outbound_bytes_used > server.limits.max_outbound_bytes
            or server.memory_used > server.limits.max_memory
        ):
            raise ValueError(f"server {server.server_id} exceeds its hard limits")


def run_scenario(scenario):
    """Expose the package boundary while later lifecycle stages are unfinished."""
    raise NotImplementedError("scenario execution is introduced in a later implementation stage")
