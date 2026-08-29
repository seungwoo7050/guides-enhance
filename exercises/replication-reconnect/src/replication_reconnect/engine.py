from __future__ import annotations

import copy
from dataclasses import asdict
from typing import Any

from .model import ClientReplica, Message, ReplicationConfig


class ReplicationEngine:
    def __init__(self, scenario: dict[str, Any]) -> None:
        self.config = self._parse_config(scenario.get("config", {}))
        self.server_version, self.server_state, self.history = self._parse_server(
            scenario.get("server", {})
        )
        self.clients = self._parse_clients(scenario.get("clients", []))
        self.processed_event_ids: set[str] = set()
        self.trace: list[dict[str, Any]] = []
        self.resync_requests: list[dict[str, str]] = []

    @staticmethod
    def _is_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _parse_config(self, raw: dict[str, Any]) -> ReplicationConfig:
        if not isinstance(raw, dict):
            raise ValueError("config must be an object")
        required = (
            "match_id",
            "protocol_version",
            "schema_version",
            "max_pending_deltas",
            "max_gap",
            "max_snapshot_bytes",
            "max_send_queue_bytes",
        )
        if any(key not in raw for key in required):
            raise ValueError("missing required config field")
        if not isinstance(raw["match_id"], str) or not raw["match_id"]:
            raise ValueError("match_id must be a non-empty string")
        config = ReplicationConfig(
            match_id=raw["match_id"],
            protocol_version=raw["protocol_version"],
            schema_version=raw["schema_version"],
            max_pending_deltas=raw["max_pending_deltas"],
            max_gap=raw["max_gap"],
            max_snapshot_bytes=raw["max_snapshot_bytes"],
            max_send_queue_bytes=raw["max_send_queue_bytes"],
        )
        values = asdict(config)
        values.pop("match_id")
        if not config.match_id or any(not self._is_int(value) for value in values.values()):
            raise ValueError("config fields are invalid")
        if any(value < 0 for value in values.values()):
            raise ValueError("config limits must be non-negative")
        return config

    def _parse_server(
        self, raw: dict[str, Any]
    ) -> tuple[int, dict[str, Any], dict[int, Message]]:
        if not isinstance(raw, dict):
            raise ValueError("server must be an object")
        version = raw.get("current_version")
        state = raw.get("current_state")
        history_items = raw.get("history", [])
        if (
            not self._is_int(version)
            or version < 0
            or not isinstance(state, dict)
            or not isinstance(history_items, list)
        ):
            raise ValueError("server current state and history are invalid")
        try:
            canonical_size(state)
        except (TypeError, ValueError) as error:
            raise ValueError("server state must contain canonical JSON values") from error
        history: dict[int, Message] = {}
        message_ids: set[str] = set()
        for raw_message in history_items:
            message = self._parse_message(raw_message)
            if message.kind != "DELTA" or message.baseline_version is None:
                raise ValueError("server history must contain deltas")
            if self._identity_reason(message) is not None:
                raise ValueError("server history identity does not match config")
            if message.version > version:
                raise ValueError("server history cannot exceed current_version")
            if message.baseline_version in history:
                raise ValueError("server history contains a conflicting baseline")
            if message.message_id in message_ids:
                raise ValueError("server history message_id must be unique")
            message_ids.add(message.message_id)
            history[message.baseline_version] = message
        return version, copy.deepcopy(state), history

    def _parse_clients(self, raw_clients: Any) -> dict[str, ClientReplica]:
        if not isinstance(raw_clients, list):
            raise ValueError("clients must be an array")
        clients: dict[str, ClientReplica] = {}
        for raw in raw_clients:
            if not isinstance(raw, dict):
                raise ValueError("client must be an object")
            client_id = str(raw.get("client_id", ""))
            version = raw.get("state_version", 0)
            state = raw.get("state", {})
            connected = raw.get("connected", True)
            if (
                not client_id
                or client_id in clients
                or not self._is_int(version)
                or version < 0
                or version > self.server_version
                or not isinstance(state, dict)
                or not isinstance(connected, bool)
            ):
                raise ValueError("client fields are invalid")
            try:
                canonical_size(state)
            except (TypeError, ValueError) as error:
                raise ValueError("client state must contain canonical JSON values") from error
            clients[client_id] = ClientReplica(
                client_id=client_id,
                state_version=version,
                state=copy.deepcopy(state),
                connected=connected,
            )
        return clients

    # [Implementation 2]
    # Message envelope validation
    # payload를 해석하기 전에 match, protocol, schema, version 필드를 확인합니다.
    def _parse_message(self, raw: Any) -> Message:
        if not isinstance(raw, dict):
            raise ValueError("message must be an object")
        required = (
            "message_id",
            "kind",
            "match_id",
            "protocol_version",
            "schema_version",
            "version",
        )
        if any(key not in raw for key in required):
            raise ValueError("message envelope is incomplete")
        kind = raw["kind"]
        if not isinstance(kind, str) or kind not in ("SNAPSHOT", "DELTA"):
            raise ValueError("message kind is unsupported")
        if not isinstance(raw["match_id"], str) or not raw["match_id"]:
            raise ValueError("message match_id is invalid")
        numeric = (raw["protocol_version"], raw["schema_version"], raw["version"])
        if any(not self._is_int(value) or value < 0 for value in numeric):
            raise ValueError("message version fields are invalid")
        message_id = raw["message_id"]
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("message_id must be a non-empty string")

        if kind == "SNAPSHOT":
            # [Implementation 2-1]
            # Snapshot content and size validation
            # 복사 가능한 JSON 값인지 확인하고 외부 객체와의 aliasing을 끊습니다.
            state = raw.get("state")
            if not isinstance(state, dict):
                raise ValueError("snapshot state must be an object")
            try:
                canonical_size(state)
            except (TypeError, ValueError) as error:
                raise ValueError("snapshot state must contain canonical JSON values") from error
            return Message(
                message_id=message_id,
                kind="SNAPSHOT",
                match_id=raw["match_id"],
                protocol_version=raw["protocol_version"],
                schema_version=raw["schema_version"],
                version=raw["version"],
                state=copy.deepcopy(state),
            )

        baseline = raw.get("baseline_version")
        operations = raw.get("operations")
        if (
            not self._is_int(baseline)
            or baseline < 0
            or raw["version"] != baseline + 1
            or not isinstance(operations, list)
        ):
            raise ValueError("delta baseline or version is invalid")

        # [Implementation 2-2]
        # Delta operation validation
        # 지원하는 연산과 object path만 받아 잘못된 경로가 부분 변경을 남기지 않게 합니다.
        normalized_operations: list[dict[str, Any]] = []
        for operation in operations:
            if not isinstance(operation, dict):
                raise ValueError("delta operation must be an object")
            op = str(operation.get("op", ""))
            path = operation.get("path")
            if op not in ("SET", "DELETE", "INCREMENT"):
                raise ValueError("delta operation is unsupported")
            if (
                not isinstance(path, list)
                or not path
                or any(not isinstance(part, str) or not part for part in path)
            ):
                raise ValueError("delta path is invalid")
            normalized = {"op": op, "path": list(path)}
            if op in ("SET", "INCREMENT"):
                if "value" not in operation:
                    raise ValueError("delta operation value is missing")
                if op == "INCREMENT" and not self._is_int(operation["value"]):
                    raise ValueError("increment value must be an integer")
                try:
                    canonical_size(operation["value"])
                except (TypeError, ValueError) as error:
                    raise ValueError("delta value must be canonical JSON") from error
                normalized["value"] = copy.deepcopy(operation["value"])
            normalized_operations.append(normalized)
        return Message(
            message_id=message_id,
            kind="DELTA",
            match_id=raw["match_id"],
            protocol_version=raw["protocol_version"],
            schema_version=raw["schema_version"],
            version=raw["version"],
            baseline_version=baseline,
            operations=tuple(normalized_operations),
        )

    def _identity_reason(self, message: Message) -> str | None:
        if message.match_id != self.config.match_id:
            return "MATCH_MISMATCH"
        if message.protocol_version != self.config.protocol_version:
            return "PROTOCOL_VERSION_MISMATCH"
        if message.schema_version != self.config.schema_version:
            return "SCHEMA_VERSION_MISMATCH"
        return None

    def _message_dict(self, message: Message) -> dict[str, Any]:
        data = asdict(message)
        data["operations"] = list(message.operations)
        return data

    def _snapshot_message(self, message_id: str) -> Message:
        return Message(
            message_id=message_id,
            kind="SNAPSHOT",
            match_id=self.config.match_id,
            protocol_version=self.config.protocol_version,
            schema_version=self.config.schema_version,
            version=self.server_version,
            state=copy.deepcopy(self.server_state),
        )

    def _record_discard(self, client: ClientReplica, message: Message, reason: str) -> None:
        client.discarded_messages.append(
            {"message_id": message.message_id, "reason_code": reason}
        )

    def _request_resync(self, client: ClientReplica, reason: str) -> None:
        client.resync_requested = True
        item = {"client_id": client.client_id, "reason_code": reason}
        if item not in self.resync_requests:
            self.resync_requests.append(item)

    def _apply_operations(
        self, state: dict[str, Any], operations: tuple[dict[str, Any], ...]
    ) -> dict[str, Any]:
        candidate = copy.deepcopy(state)
        for operation in operations:
            parent: dict[str, Any] = candidate
            path = operation["path"]
            for part in path[:-1]:
                child = parent.get(part)
                if child is None:
                    if operation["op"] == "SET":
                        child = {}
                        parent[part] = child
                    else:
                        raise ValueError("delta path does not exist")
                if not isinstance(child, dict):
                    raise ValueError("delta path crosses a non-object value")
                parent = child
            key = path[-1]
            if operation["op"] == "SET":
                parent[key] = copy.deepcopy(operation["value"])
            elif operation["op"] == "DELETE":
                if key not in parent:
                    raise ValueError("delete target does not exist")
                del parent[key]
            else:
                current = parent.get(key)
                if not self._is_int(current):
                    raise ValueError("increment target is not an integer")
                value = operation["value"]
                result = current + value
                if result < -9_223_372_036_854_775_808 or result > 9_223_372_036_854_775_807:
                    raise ValueError("increment overflows signed 64-bit range")
                parent[key] = result
        return candidate

    def _apply_delta(self, client: ClientReplica, message: Message) -> tuple[str, str]:
        try:
            candidate = self._apply_operations(client.state, message.operations)
        except ValueError:
            self._record_discard(client, message, "INVALID_DELTA_OPERATION")
            client.pending.clear()
            self._request_resync(client, "INVALID_DELTA_OPERATION")
            return "REJECTED", "INVALID_DELTA_OPERATION"
        client.state = candidate
        client.state_version = message.version
        client.applied_message_ids.append(message.message_id)
        client.resync_requested = False
        return "APPLIED", "DELTA_APPLIED"

    # [Implementation 3]
    # Contiguous buffered-delta replay
    # 현재 version에서 바로 이어지는 delta만 순서대로 꺼내 적용합니다.
    def _drain_pending(self, client: ClientReplica) -> list[str]:
        applied: list[str] = []
        while client.state_version in client.pending:
            message = client.pending.pop(client.state_version)
            status, _ = self._apply_delta(client, message)
            if status != "APPLIED":
                break
            applied.append(message.message_id)
        return applied

    # [Implementation 4]
    # Version and baseline validation
    # 현재 replica가 요구한 baseline과 일치하지 않으면 상태를 바꾸지 않습니다.
    def deliver(self, client: ClientReplica, message: Message) -> tuple[str, str, list[str]]:
        identity_reason = self._identity_reason(message)
        if identity_reason is not None:
            self._record_discard(client, message, identity_reason)
            return "REJECTED", identity_reason, []
        if not client.connected:
            self._record_discard(client, message, "CLIENT_DISCONNECTED")
            return "REJECTED", "CLIENT_DISCONNECTED", []
        if message.version > self.server_version:
            self._record_discard(client, message, "SERVER_VERSION_EXCEEDED")
            self._request_resync(client, "SERVER_VERSION_EXCEEDED")
            return "REJECTED", "SERVER_VERSION_EXCEEDED", []

        if message.kind == "SNAPSHOT":
            return self._apply_snapshot(client, message)

        assert message.baseline_version is not None
        if message.version <= client.state_version:
            self._record_discard(client, message, "DUPLICATE_OR_STALE_DELTA")
            return "IGNORED", "DUPLICATE_OR_STALE_DELTA", []
        if message.baseline_version == client.state_version:
            status, reason = self._apply_delta(client, message)
            return status, reason, self._drain_pending(client) if status == "APPLIED" else []
        if message.baseline_version < client.state_version:
            self._record_discard(client, message, "BASELINE_MISMATCH")
            self._request_resync(client, "BASELINE_MISMATCH")
            return "REJECTED", "BASELINE_MISMATCH", []

        # [Implementation 4-1]
        # Bounded future-delta buffering
        # gap과 보류 개수를 모두 제한해 손실된 delta를 무기한 기다리지 않습니다.
        gap = message.baseline_version - client.state_version
        if gap > self.config.max_gap:
            self._record_discard(client, message, "GAP_LIMIT_EXCEEDED")
            client.pending.clear()
            self._request_resync(client, "GAP_LIMIT_EXCEEDED")
            return "RESYNC_REQUIRED", "GAP_LIMIT_EXCEEDED", []
        existing = client.pending.get(message.baseline_version)
        if existing is not None:
            reason = (
                "DUPLICATE_PENDING_DELTA"
                if existing.message_id == message.message_id
                else "CONFLICTING_PENDING_DELTA"
            )
            self._record_discard(client, message, reason)
            if reason == "CONFLICTING_PENDING_DELTA":
                client.pending.clear()
                self._request_resync(client, reason)
                return "RESYNC_REQUIRED", reason, []
            return "IGNORED", reason, []
        if len(client.pending) >= self.config.max_pending_deltas:
            self._record_discard(client, message, "PENDING_QUEUE_LIMIT")
            client.pending.clear()
            self._request_resync(client, "PENDING_QUEUE_LIMIT")
            return "RESYNC_REQUIRED", "PENDING_QUEUE_LIMIT", []
        client.pending[message.baseline_version] = message
        return "BUFFERED", "FUTURE_DELTA_BUFFERED", []


def run_scenario(scenario):
    """Expose the package boundary while later lifecycle stages are unfinished."""
    raise NotImplementedError("scenario execution is introduced in a later implementation stage")
