"""LedgerLab 거절 event를 요청별로 묶어 조사용 alert를 만듭니다."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from .policy import (
    ACTOR_TENANT_MISMATCH,
    JOB_SCOPE_MISMATCH,
    OBJECT_PREFIX_MISMATCH,
    POLICY_UNAVAILABLE,
    REPORT_SCOPE_MISMATCH,
    TENANT_SCOPE_MISMATCH,
)

CROSS_SCOPE_REASON_CODES = frozenset(
    {
        ACTOR_TENANT_MISMATCH,
        JOB_SCOPE_MISMATCH,
        OBJECT_PREFIX_MISMATCH,
        POLICY_UNAVAILABLE,
        REPORT_SCOPE_MISMATCH,
        TENANT_SCOPE_MISMATCH,
    }
)


# [Implementation 6] Correlated deny-event detection

def detect(events: Sequence[Mapping[str, Any] | object]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for event in _deduplicate_events(events):
        if not _is_cross_scope_denial(event):
            continue
        correlation_id = event.get("correlation_id")
        if isinstance(correlation_id, str) and correlation_id:
            groups.setdefault(correlation_id, []).append(event)

    return [
        _build_alert(correlation_id, groups[correlation_id])
        for correlation_id in sorted(groups)
    ]


# [Implementation 6-1] Duplicate-event suppression

def _deduplicate_events(
    events: Sequence[Mapping[str, Any] | object],
) -> list[Mapping[str, Any]]:
    candidates: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        if not isinstance(event, Mapping):
            continue
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            continue
        candidates.setdefault(event_id, []).append(event)

    unique: list[Mapping[str, Any]] = []
    for event_id in sorted(candidates):
        # 같은 event_id의 내용이 충돌하면 범위 초과 거절 기록을 남깁니다.
        # 정상처럼 보이는 중복 기록이 alert를 숨기지 못하게 하기 위한 선택입니다.
        selected = min(candidates[event_id], key=_event_rank)
        unique.append(selected)
    return unique


def _event_rank(event: Mapping[str, Any]) -> tuple[int, str]:
    suspicious_rank = 0 if _is_cross_scope_denial(event) else 1
    canonical = json.dumps(event, sort_keys=True, default=str, separators=(",", ":"))
    return suspicious_rank, canonical


def _is_cross_scope_denial(event: Mapping[str, Any]) -> bool:
    return (
        event.get("event_type") == "authorization.decision"
        and event.get("decision") == "deny"
        and event.get("reason_code") in CROSS_SCOPE_REASON_CODES
    )


# [Implementation 6-2] Correlation-preserving alert construction

def _build_alert(
    correlation_id: str,
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(events, key=lambda event: str(event.get("event_id")))
    return {
        "alert_id": f"DET-CROSS-SCOPE:{correlation_id}",
        "correlation_id": correlation_id,
        "actor_ids": _values(ordered, "actor_id"),
        "effective_actor_ids": _values(ordered, "effective_actor_id"),
        "credential_ids": _values(ordered, "credential_id"),
        "reason_codes": _values(ordered, "reason_code"),
        "evidence_event_ids": [str(event["event_id"]) for event in ordered],
    }


def _values(events: Sequence[Mapping[str, Any]], field: str) -> list[str]:
    return sorted(
        {
            str(event[field])
            for event in events
            if event.get(field) is not None and str(event[field])
        }
    )
