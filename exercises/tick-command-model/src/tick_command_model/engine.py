from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from typing import Any, Iterable

from .model import Command, Decision, PlayerState, SimulationConfig


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


def run_scenario(scenario):
    """Expose the package boundary while later lifecycle stages are unfinished."""
    raise NotImplementedError("scenario execution is introduced in a later implementation stage")
