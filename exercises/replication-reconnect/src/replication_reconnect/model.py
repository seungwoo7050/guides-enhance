from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


# [Implementation 1]
# Replication message, replica, and queue records
# 서버 메시지와 클라이언트 복제 상태를 별도 Record로 정의합니다.
@dataclass(frozen=True)
class ReplicationConfig:
    match_id: str
    protocol_version: int
    schema_version: int
    max_pending_deltas: int
    max_gap: int
    max_snapshot_bytes: int
    max_send_queue_bytes: int


@dataclass(frozen=True)
class Message:
    message_id: str
    kind: Literal["SNAPSHOT", "DELTA"]
    match_id: str
    protocol_version: int
    schema_version: int
    version: int
    baseline_version: int | None = None
    state: dict[str, Any] | None = None
    operations: tuple[dict[str, Any], ...] = ()


@dataclass
class ClientReplica:
    client_id: str
    state_version: int
    state: dict[str, Any]
    connected: bool = True
    pending: dict[int, Message] = field(default_factory=dict)
    applied_message_ids: list[str] = field(default_factory=list)
    discarded_messages: list[dict[str, str]] = field(default_factory=list)
    resync_requested: bool = False
    outbound_messages: list[Message] = field(default_factory=list)
    outbound_bytes: int = 0
    max_outbound_bytes: int = 0
    reconnect_path: str | None = None
