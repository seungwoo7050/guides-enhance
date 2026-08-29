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

    # [Implementation 3]
    # Health, drain, and protocol filtering
    # heartbeat가 오래됐거나 drain 중이거나 protocol이 다른 서버는 후보에서 제외합니다.
    def _healthy_servers(self, request: MatchRequest, now: int) -> tuple[list[Server], str]:
        active = []
        for server in self.servers.values():
            heartbeat_age = now - server.last_heartbeat
            if (
                server.state == "ACTIVE"
                and 0 <= heartbeat_age <= self.stale_after
            ):
                active.append(server)
        if not active:
            return [], "NO_HEALTHY_SERVER"
        compatible = [
            server
            for server in active
            if request.required_protocol_version in server.protocol_versions
        ]
        if not compatible:
            return [], "PROTOCOL_UNSUPPORTED"
        return compatible, "ELIGIBLE"

    def _post_usage(self, server: Server, request: MatchRequest) -> dict[str, int]:
        return {
            "rooms": server.room_count + 1,
            "players": server.player_count + request.expected_players,
            "tick_cost": server.tick_cost_used + request.estimated_tick_cost,
            "outbound_bytes": server.outbound_bytes_used + request.estimated_bandwidth,
            "memory": server.memory_used + request.estimated_memory,
        }

    # [Implementation 3-1]
    # Hard and soft capacity checks
    # 배치 뒤 사용량을 먼저 계산해 hard limit과 남겨야 할 headroom을 확인합니다.
    def _fits_hard_limits(self, server: Server, request: MatchRequest) -> bool:
        usage = self._post_usage(server, request)
        return (
            usage["rooms"] <= server.limits.max_rooms
            and usage["players"] <= server.limits.max_players
            and usage["tick_cost"] <= server.limits.max_tick_cost
            and usage["outbound_bytes"] <= server.limits.max_outbound_bytes
            and usage["memory"] <= server.limits.max_memory
        )

    def _preserves_soft_headroom(self, server: Server, request: MatchRequest) -> bool:
        usage = self._post_usage(server, request)
        return (
            server.limits.max_rooms - usage["rooms"] >= self.soft_headroom["rooms"]
            and server.limits.max_players - usage["players"]
            >= self.soft_headroom["players"]
            and server.limits.max_tick_cost - usage["tick_cost"]
            >= self.soft_headroom["tick_cost"]
            and server.limits.max_outbound_bytes - usage["outbound_bytes"]
            >= self.soft_headroom["outbound_bytes"]
            and server.limits.max_memory - usage["memory"]
            >= self.soft_headroom["memory"]
        )

    # [Implementation 3-2]
    # Headroom-aware stable scoring
    # 지역 선호와 배치 후 사용률이 같으면 server ID로 결과를 고정합니다.
    def _score(
        self,
        server: Server,
        request: MatchRequest,
    ) -> tuple[tuple[Any, ...], dict[str, object]]:
        usage = self._post_usage(server, request)
        limits = {
            "rooms": server.limits.max_rooms,
            "players": server.limits.max_players,
            "tick_cost": server.limits.max_tick_cost,
            "outbound_bytes": server.limits.max_outbound_bytes,
            "memory": server.limits.max_memory,
        }
        utilizations = {
            key: 0.0 if limits[key] == 0 else usage[key] / limits[key] for key in usage
        }
        try:
            region_rank = request.region_preferences.index(server.region)
        except ValueError:
            region_rank = len(request.region_preferences) + 1
        max_utilization = max(utilizations.values())
        average_utilization = sum(utilizations.values()) / len(utilizations)
        score_key = (
            region_rank,
            round(max_utilization, 12),
            round(average_utilization, 12),
            server.server_id,
        )
        score = {
            "region_rank": region_rank,
            "max_post_utilization": round(max_utilization, 6),
            "average_post_utilization": round(average_utilization, 6),
            "post_usage": usage,
        }
        return score_key, score

    # [Implementation 4]
    # Candidate server selection
    # 모든 필터를 통과한 서버만 점수로 비교합니다.
    def _select_server(
        self, request: MatchRequest, now: int
    ) -> tuple[Server | None, str, dict[str, object] | None]:
        eligible, reason = self._healthy_servers(request, now)
        if not eligible:
            return None, reason, None
        hard = [server for server in eligible if self._fits_hard_limits(server, request)]
        if not hard:
            return None, "HARD_CAPACITY_EXCEEDED", None
        soft = [server for server in hard if self._preserves_soft_headroom(server, request)]
        if not soft:
            return None, "SOFT_HEADROOM_REQUIRED", None
        ranked = [(self._score(server, request), server) for server in soft]
        ranked.sort(key=lambda item: item[0][0])
        (score_key, score), server = ranked[0]
        score["score_key"] = list(score_key[:-1])
        return server, "PLACEMENT_AVAILABLE", score

    # [Implementation 5]
    # Immediate reservation and duplicate request handling
    # 결정을 반환하기 전에 사용량을 반영해 같은 capacity를 두 요청이 함께 쓰지 못하게 합니다.
    def _reserve(
        self,
        request: MatchRequest,
        server: Server,
        score: dict[str, object],
    ) -> RequestDecision:
        server.room_count += 1
        server.player_count += request.expected_players
        server.tick_cost_used += request.estimated_tick_cost
        server.outbound_bytes_used += request.estimated_bandwidth
        server.memory_used += request.estimated_memory
        self._assert_server_within_hard_limits(server)
        self.reservations[request.request_id] = Reservation(
            request_id=request.request_id,
            server_id=server.server_id,
            players=request.expected_players,
            tick_cost=request.estimated_tick_cost,
            outbound_bytes=request.estimated_bandwidth,
            memory=request.estimated_memory,
        )
        decision = RequestDecision(
            request_id=request.request_id,
            status="PLACED",
            reason_code="PLACED",
            server_id=server.server_id,
            score=score,
        )
        self.decisions[request.request_id] = decision
        return decision

    def _admit(self, request: MatchRequest, now: int, allow_queue: bool) -> RequestDecision:
        existing = self.decisions.get(request.request_id)
        if existing is not None:
            return RequestDecision(
                request_id=request.request_id,
                status=existing.status,
                reason_code="DUPLICATE_REQUEST",
                server_id=existing.server_id,
                score=existing.score,
            )
        if now > request.deadline:
            decision = RequestDecision(request.request_id, "REJECTED", "DEADLINE_EXPIRED")
            self.decisions[request.request_id] = decision
            return decision
        server, reason, score = self._select_server(request, now)
        if server is not None and score is not None:
            return self._reserve(request, server, score)
        if allow_queue and now < request.deadline:
            return self._enqueue_request(request, reason)
        decision = RequestDecision(request.request_id, "REJECTED", reason)
        self.decisions[request.request_id] = decision
        return decision

    # [Implementation 6]
    # Bounded placement queue
    # 배치할 수 없는 요청은 정해진 개수까지만 보류합니다.
    def _enqueue_request(self, request: MatchRequest, placement_reason: str) -> RequestDecision:
        if len(self.queue) >= self.max_queue_size:
            decision = RequestDecision(request.request_id, "REJECTED", "QUEUE_FULL")
            self.decisions[request.request_id] = decision
            return decision
        self.queue.append(request.request_id)
        self.queue.sort(key=lambda item: (self.requests[item].created_at, item))
        decision = RequestDecision(
            request.request_id,
            "QUEUED",
            f"QUEUED_{placement_reason}",
        )
        self.decisions[request.request_id] = decision
        return decision

    # [Implementation 6-1]
    # Queue deadline expiry and retry
    # 요청 생성 시각과 deadline 순서를 유지하면서 다시 배치합니다.
    def _process_queue(self, now: int) -> list[dict[str, object]]:
        updates: list[dict[str, object]] = []
        remaining: list[str] = []
        for request_id in sorted(
            self.queue,
            key=lambda item: (self.requests[item].created_at, item),
        ):
            request = self.requests[request_id]
            if now > request.deadline:
                decision = RequestDecision(request_id, "REJECTED", "DEADLINE_EXPIRED")
                self.decisions[request_id] = decision
                updates.append(asdict(decision))
                continue
            server, reason, score = self._select_server(request, now)
            if server is None or score is None:
                remaining.append(request_id)
                self.decisions[request_id] = RequestDecision(
                    request_id,
                    "QUEUED",
                    f"QUEUED_{reason}",
                )
                continue
            decision = self._reserve(request, server, score)
            updates.append(asdict(decision))
        self.queue = remaining
        return updates

    # [Implementation 7]
    # Drain tracking and capacity release
    # 진행 중 경기의 예약을 반환한 뒤 남은 예약이 없을 때 drain 완료를 기록합니다.
    def _begin_drain(self, server_id: str) -> tuple[str, str]:
        server = self.servers.get(server_id)
        if server is None:
            return "REJECTED", "SERVER_NOT_FOUND"
        if server.state == "DRAINING":
            return "IGNORED", "ALREADY_DRAINING"
        if server.state == "UNAVAILABLE":
            return "REJECTED", "SERVER_UNAVAILABLE"
        server.state = "DRAINING"
        return "ACCEPTED", "DRAIN_STARTED"

    def _complete_match(self, request_id: str) -> tuple[str, str, str | None]:
        reservation = self.reservations.pop(request_id, None)
        if reservation is None:
            return "REJECTED", "RESERVATION_NOT_FOUND", None
        server = self.servers[reservation.server_id]
        server.room_count -= 1
        server.player_count -= reservation.players
        server.tick_cost_used -= reservation.tick_cost
        server.outbound_bytes_used -= reservation.outbound_bytes
        server.memory_used -= reservation.memory
        self.decisions[request_id] = RequestDecision(
            request_id,
            "COMPLETED",
            "MATCH_COMPLETED",
            server_id=server.server_id,
        )
        draining_reservations = any(
            item.server_id == server.server_id for item in self.reservations.values()
        )
        drain_result = (
            "DRAIN_COMPLETE"
            if server.state == "DRAINING" and not draining_reservations
            else None
        )
        return "ACCEPTED", "MATCH_COMPLETED", drain_result

    def apply_event(self, raw: dict[str, Any]) -> None:
        event_id = str(raw.get("event_id", ""))
        kind = str(raw.get("kind", ""))
        now = raw.get("logical_time")
        if not event_id or not kind or not self._is_int(now) or now < self.logical_time:
            raise ValueError("event_id, kind, and non-decreasing logical_time are required")
        self.logical_time = now
        queue_updates: list[dict[str, object]] = []
        details: dict[str, object] = {}
        if event_id in self.processed_event_ids:
            status, reason = "IGNORED", "DUPLICATE_EVENT"
        else:
            self.processed_event_ids.add(event_id)
            if kind == "REQUEST":
                try:
                    request = self._parse_request(raw.get("request"))
                except ValueError:
                    status, reason = "REJECTED", "INVALID_REQUEST"
                else:
                    if request.created_at > now:
                        decision = RequestDecision(
                            request.request_id,
                            "REJECTED",
                            "REQUEST_NOT_CREATED",
                        )
                        status, reason = decision.status, decision.reason_code
                        details["request_decision"] = asdict(decision)
                    else:
                        existing_request = self.requests.get(request.request_id)
                        if existing_request is not None and existing_request != request:
                            status, reason = "REJECTED", "REQUEST_ID_CONFLICT"
                        else:
                            self.requests.setdefault(request.request_id, request)
                            decision = self._admit(request, now, allow_queue=True)
                            status, reason = decision.status, decision.reason_code
                            details["request_decision"] = asdict(decision)
            elif kind == "ADVANCE_TIME":
                status, reason = "ACCEPTED", "TIME_ADVANCED"
                queue_updates = self._process_queue(now)
            elif kind == "BEGIN_DRAIN":
                status, reason = self._begin_drain(str(raw.get("server_id", "")))
            elif kind == "COMPLETE_MATCH":
                status, reason, drain_result = self._complete_match(
                    str(raw.get("request_id", ""))
                )
                if drain_result is not None:
                    details["drain_result"] = drain_result
                queue_updates = self._process_queue(now)
            elif kind == "HEARTBEAT":
                server = self.servers.get(str(raw.get("server_id", "")))
                if server is None:
                    status, reason = "REJECTED", "SERVER_NOT_FOUND"
                else:
                    state = raw.get("state")
                    if state is not None and state not in (
                        "ACTIVE",
                        "DRAINING",
                        "UNAVAILABLE",
                    ):
                        status, reason = "REJECTED", "INVALID_SERVER_STATE"
                    else:
                        server.last_heartbeat = now
                        if state is not None:
                            server.state = state
                        status, reason = "ACCEPTED", "HEARTBEAT_UPDATED"
                        queue_updates = self._process_queue(now)
            else:
                status, reason = "REJECTED", "UNKNOWN_EVENT"
        self.trace.append(
            {
                "event_id": event_id,
                "kind": kind,
                "logical_time": now,
                "status": status,
                "reason_code": reason,
                "queue_updates": queue_updates,
                **details,
                "queue": list(self.queue),
                "servers": self._server_list(),
            }
        )

    def _server_list(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for server_id in sorted(self.servers):
            server = self.servers[server_id]
            item = asdict(server)
            item["protocol_versions"] = list(server.protocol_versions)
            item["drain_complete"] = server.state == "DRAINING" and not any(
                reservation.server_id == server_id
                for reservation in self.reservations.values()
            )
            result.append(item)
        return result

    def result(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "trace": self.trace,
            "decisions": [asdict(self.decisions[item]) for item in sorted(self.decisions)],
            "active_reservations": [
                asdict(self.reservations[item]) for item in sorted(self.reservations)
            ],
            "queue": list(self.queue),
            "servers": self._server_list(),
        }
        result["digest"] = digest_value(result)
        return result


def run_scenario(scenario):
    """Expose the package boundary while later lifecycle stages are unfinished."""
    raise NotImplementedError("scenario execution is introduced in a later implementation stage")
