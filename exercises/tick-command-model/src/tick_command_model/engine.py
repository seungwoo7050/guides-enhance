from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from typing import Any, Iterable

from .model import Command, Decision, PlayerState, SimulationConfig
from .serialization import digest_result


REASON_APPLIED = "APPLIED"
REASON_INVALID_INPUT = "INVALID_INPUT"
REASON_MATCH_MISMATCH = "MATCH_MISMATCH"
REASON_PLAYER_NOT_FOUND = "PLAYER_NOT_FOUND"
REASON_SESSION_EPOCH_MISMATCH = "SESSION_EPOCH_MISMATCH"
REASON_STALE_SEQUENCE = "STALE_SEQUENCE"
REASON_SEQUENCE_GAP = "SEQUENCE_GAP"
REASON_STALE_TICK = "STALE_TICK"
REASON_FUTURE_TICK_LIMIT = "FUTURE_TICK_LIMIT"
REASON_TICK_COMMAND_LIMIT = "TICK_COMMAND_LIMIT"
REASON_UNSUPPORTED_COMMAND = "UNSUPPORTED_COMMAND"
REASON_INVALID_PAYLOAD = "INVALID_PAYLOAD"
REASON_RANGE_VIOLATION = "RANGE_VIOLATION"
REASON_ARITHMETIC_OVERFLOW = "ARITHMETIC_OVERFLOW"


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


# [Implementation 2]
# Scenario input validation and normalization
# 상태를 만들기 전에 설정, 플레이어, 명령의 형식과 수치 범위를 확인합니다.
def _parse_config(raw: dict[str, Any]) -> SimulationConfig:
    required = (
        "match_id",
        "tick_rate_hz",
        "start_tick",
        "advance_to_tick",
        "max_commands_per_tick",
        "max_catch_up_ticks",
        "max_future_tick_distance",
    )
    if any(key not in raw for key in required):
        raise ValueError("missing required config field")
    numeric_keys = (
        "tick_rate_hz",
        "start_tick",
        "advance_to_tick",
        "max_commands_per_tick",
        "max_catch_up_ticks",
        "max_future_tick_distance",
        "max_move_delta",
        "coordinate_limit",
        "max_score_delta",
        "score_limit",
    )
    defaults = {
        "max_move_delta": 100,
        "coordinate_limit": 1_000_000,
        "max_score_delta": 1_000_000,
        "score_limit": 2_147_483_647,
    }
    numeric_values = {key: raw.get(key, defaults.get(key)) for key in numeric_keys}
    if any(not _is_int(value) for value in numeric_values.values()):
        raise ValueError("config numeric fields must be integers")
    if not isinstance(raw["match_id"], str) or not raw["match_id"]:
        raise ValueError("match_id must be a non-empty string")
    config = SimulationConfig(match_id=raw["match_id"], **numeric_values)
    if config.start_tick < 0 or config.advance_to_tick < config.start_tick:
        raise ValueError("tick range is invalid")
    if (
        config.tick_rate_hz <= 0
        or config.max_commands_per_tick <= 0
        or config.max_catch_up_ticks < 0
        or config.max_future_tick_distance < 0
        or config.max_move_delta < 0
        or config.coordinate_limit < 0
        or config.max_score_delta < 0
        or config.score_limit < 0
    ):
        raise ValueError("config limits must be non-negative")
    return config


def _parse_players(raw_players: Iterable[dict[str, Any]]) -> dict[str, PlayerState]:
    players: dict[str, PlayerState] = {}
    for raw in raw_players:
        if not isinstance(raw, dict):
            raise ValueError("each player must be an object")
        player_id = raw.get("player_id")
        if not isinstance(player_id, str) or not player_id or player_id in players:
            raise ValueError("player_id must be a unique non-empty string")
        values = {
            "session_epoch": raw.get("session_epoch"),
            "last_sequence": raw.get("last_sequence", 0),
            "x": raw.get("x", 0),
            "y": raw.get("y", 0),
            "score": raw.get("score", 0),
        }
        if any(not _is_int(value) for value in values.values()):
            raise ValueError("player numeric fields must be integers")
        if values["session_epoch"] < 0 or values["last_sequence"] < 0:
            raise ValueError("player epoch and sequence must be non-negative")
        players[player_id] = PlayerState(player_id=player_id, **values)
    return players


def _parse_command(raw: Any, index: int) -> tuple[Command | None, Decision | None]:
    del index
    fallback_id = "invalid-command"
    if not isinstance(raw, dict):
        return None, Decision(fallback_id, None, "REJECTED", REASON_INVALID_INPUT)
    raw_command_id = raw.get("command_id", fallback_id)
    command_id = raw_command_id if isinstance(raw_command_id, str) else fallback_id
    required = (
        "match_id",
        "player_id",
        "session_epoch",
        "sequence",
        "target_tick",
        "kind",
        "payload",
        "received_order",
    )
    if any(key not in raw for key in required):
        return None, Decision(command_id, None, "REJECTED", REASON_INVALID_INPUT)
    if any(
        not isinstance(raw[key], str) or not raw[key]
        for key in ("match_id", "player_id", "kind")
    ) or not command_id:
        return None, Decision(command_id or fallback_id, None, "REJECTED", REASON_INVALID_INPUT)
    numeric = (
        raw["session_epoch"],
        raw["sequence"],
        raw["target_tick"],
        raw["received_order"],
    )
    if any(not _is_int(value) for value in numeric) or not isinstance(raw["payload"], dict):
        return None, Decision(command_id, None, "REJECTED", REASON_INVALID_INPUT)
    if raw["session_epoch"] < 0 or raw["sequence"] < 0 or raw["target_tick"] < 0:
        return None, Decision(command_id, raw["target_tick"], "REJECTED", REASON_INVALID_INPUT)
    return (
        Command(
            command_id=command_id,
            match_id=raw["match_id"],
            player_id=raw["player_id"],
            session_epoch=raw["session_epoch"],
            sequence=raw["sequence"],
            target_tick=raw["target_tick"],
            kind=raw["kind"],
            payload=raw["payload"],
            received_order=raw["received_order"],
        ),
        None,
    )


# [Implementation 3]
# Stable command ordering
# 입력 배열의 순서가 결과를 바꾸지 않도록 비교 기준을 한 곳에서 정의합니다.
def _command_order(command: Command) -> tuple[int, str, int, int, str]:
    return (
        command.received_order,
        command.player_id,
        command.session_epoch,
        command.sequence,
        command.command_id,
    )


# [Implementation 4]
# Payload range and arithmetic checks
# Python 정수가 커질 수 있더라도 설정한 좌표와 점수 한도는 넘지 못하게 합니다.
def _checked_add(left: int, right: int, lower: int, upper: int) -> int | None:
    result = left + right
    if result < lower or result > upper:
        return None
    return result


def _apply_payload(
    player: PlayerState,
    command: Command,
    config: SimulationConfig,
) -> str:
    if command.kind == "MOVE":
        dx = command.payload.get("dx")
        dy = command.payload.get("dy")
        if not _is_int(dx) or not _is_int(dy):
            return REASON_INVALID_PAYLOAD
        if abs(dx) > config.max_move_delta or abs(dy) > config.max_move_delta:
            return REASON_RANGE_VIOLATION
        next_x = _checked_add(
            player.x,
            dx,
            -config.coordinate_limit,
            config.coordinate_limit,
        )
        next_y = _checked_add(
            player.y,
            dy,
            -config.coordinate_limit,
            config.coordinate_limit,
        )
        if next_x is None or next_y is None:
            return REASON_ARITHMETIC_OVERFLOW
        player.x = next_x
        player.y = next_y
        return REASON_APPLIED

    if command.kind == "ADD_SCORE":
        delta = command.payload.get("delta")
        if not _is_int(delta):
            return REASON_INVALID_PAYLOAD
        if delta < 0 or delta > config.max_score_delta:
            return REASON_RANGE_VIOLATION
        next_score = _checked_add(player.score, delta, 0, config.score_limit)
        if next_score is None:
            return REASON_ARITHMETIC_OVERFLOW
        player.score = next_score
        return REASON_APPLIED

    return REASON_UNSUPPORTED_COMMAND


# [Implementation 5]
# Authoritative command validation
# 모든 검사를 통과하기 전에는 플레이어의 정본 상태를 확정하지 않습니다.
def _execute_command(
    command: Command,
    players: dict[str, PlayerState],
    config: SimulationConfig,
) -> Decision:
    if command.match_id != config.match_id:
        return Decision(command.command_id, command.target_tick, "REJECTED", REASON_MATCH_MISMATCH)
    player = players.get(command.player_id)
    if player is None:
        return Decision(
            command.command_id,
            command.target_tick,
            "REJECTED",
            REASON_PLAYER_NOT_FOUND,
        )

    # [Implementation 5-1]
    # Session epoch and sequence checks
    # 거절된 명령은 sequence를 소비하지 않아 다음 정상 명령을 막지 않습니다.
    if command.session_epoch != player.session_epoch:
        return Decision(
            command.command_id,
            command.target_tick,
            "REJECTED",
            REASON_SESSION_EPOCH_MISMATCH,
        )
    if command.sequence <= player.last_sequence:
        return Decision(command.command_id, command.target_tick, "REJECTED", REASON_STALE_SEQUENCE)
    if command.sequence != player.last_sequence + 1:
        return Decision(command.command_id, command.target_tick, "REJECTED", REASON_SEQUENCE_GAP)

    # 페이로드 처리 중 실패해도 원래 상태로 되돌릴 수 있도록 변경 전 값을 보관합니다.
    before = (player.x, player.y, player.score, player.last_sequence)
    reason = _apply_payload(player, command, config)
    if reason != REASON_APPLIED:
        player.x, player.y, player.score, player.last_sequence = before
        return Decision(command.command_id, command.target_tick, "REJECTED", reason)
    player.last_sequence = command.sequence
    return Decision(command.command_id, command.target_tick, "APPLIED", REASON_APPLIED)


# [Implementation 6]
# Bounded tick execution
# 늦어진 tick과 명령을 무제한 처리하지 않고 남은 작업을 결과에 명시합니다.
def run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be an object")
    raw_players = scenario.get("players", [])
    raw_commands = scenario.get("commands", [])
    if not isinstance(raw_players, list) or not isinstance(raw_commands, list):
        raise ValueError("players and commands must be arrays")
    config = _parse_config(scenario.get("config", {}))
    players = _parse_players(raw_players)
    for player in players.values():
        if (
            abs(player.x) > config.coordinate_limit
            or abs(player.y) > config.coordinate_limit
            or player.score < 0
            or player.score > config.score_limit
        ):
            raise ValueError("initial player state exceeds configured limits")
    buckets: dict[int, list[Command]] = defaultdict(list)
    decisions: list[Decision] = []

    for index, raw_command in enumerate(raw_commands):
        command, error = _parse_command(raw_command, index)
        if error is not None:
            decisions.append(error)
            continue
        assert command is not None
        if command.target_tick <= config.start_tick:
            decisions.append(
                Decision(command.command_id, command.target_tick, "REJECTED", REASON_STALE_TICK)
            )
            continue
        if command.target_tick > config.start_tick + config.max_future_tick_distance:
            decisions.append(
                Decision(
                    command.command_id,
                    command.target_tick,
                    "REJECTED",
                    REASON_FUTURE_TICK_LIMIT,
                )
            )
            continue
        buckets[command.target_tick].append(command)

    required_ticks = config.advance_to_tick - config.start_tick

    # [Implementation 6-1]
    # Catch-up limit and pending work
    # 따라잡지 못한 tick의 명령은 버리지 않고 pending 목록으로 반환합니다.
    executed_tick_count = min(required_ticks, config.max_catch_up_ticks)
    final_tick = config.start_tick + executed_tick_count
    catch_up_limited = required_ticks > config.max_catch_up_ticks
    tick_limit_exceeded = False
    tick_trace: list[dict[str, Any]] = []

    for tick in range(config.start_tick + 1, final_tick + 1):
        ordered = sorted(buckets.pop(tick, []), key=_command_order)

        # [Implementation 6-2]
        # Per-tick inspection limit
        # 거절된 명령도 검사 비용을 쓰므로 적용 성공 수가 아니라 검사 수를 제한합니다.
        processable = ordered[: config.max_commands_per_tick]
        rejected_by_budget = ordered[config.max_commands_per_tick :]
        if rejected_by_budget:
            tick_limit_exceeded = True
        tick_decisions = [_execute_command(command, players, config) for command in processable]
        tick_decisions.extend(
            Decision(
                command.command_id,
                command.target_tick,
                "REJECTED",
                REASON_TICK_COMMAND_LIMIT,
            )
            for command in rejected_by_budget
        )
        decisions.extend(tick_decisions)
        tick_trace.append(
            {
                "tick": tick,
                "applied_command_ids": [
                    decision.command_id
                    for decision in tick_decisions
                    if decision.status == "APPLIED"
                ],
                "rejected": [
                    {
                        "command_id": decision.command_id,
                        "reason_code": decision.reason_code,
                    }
                    for decision in tick_decisions
                    if decision.status == "REJECTED"
                ],
            }
        )

    pending_commands = [
        {
            "command_id": command.command_id,
            "target_tick": command.target_tick,
        }
        for tick in sorted(buckets)
        for command in sorted(buckets[tick], key=_command_order)
    ]
    overload_reasons = []
    if catch_up_limited:
        overload_reasons.append("CATCH_UP_LIMIT")
    if tick_limit_exceeded:
        overload_reasons.append("TICK_COMMAND_LIMIT")
    result: dict[str, Any] = {
        "match_id": config.match_id,
        "tick_rate_hz": config.tick_rate_hz,
        "start_tick": config.start_tick,
        "requested_final_tick": config.advance_to_tick,
        "final_tick": final_tick,
        "overloaded": bool(overload_reasons),
        "overload_reasons": overload_reasons,
        "tick_trace": tick_trace,
        "decisions": [
            decision.to_dict()
            for decision in sorted(
                decisions,
                key=lambda item: (
                    -1 if item.target_tick is None else item.target_tick,
                    item.command_id,
                    item.reason_code,
                ),
            )
        ],
        "players": [players[player_id].to_dict() for player_id in sorted(players)],
        "last_applied_sequence": {
            player_id: players[player_id].last_sequence for player_id in sorted(players)
        },
        "pending_commands": pending_commands,
    }
    result["digest"] = digest_result(result)
    return result
