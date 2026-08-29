"""합성 LedgerLab 상태를 읽어 접근 가능 여부를 기본 거절 방식으로 판정합니다."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

Decision = Literal["allow", "deny"]
POLICY_VERSION = "ledgerlab-v1"

POLICY_UNAVAILABLE = "policy_context_unavailable"
ACTION_INVALID = "action_context_invalid"
ACTOR_INVALID = "actor_context_invalid"
ACTOR_OR_REPORT_NOT_FOUND = "actor_or_report_not_found"
ACTOR_TENANT_MISMATCH = "actor_tenant_mismatch"
REPORT_SCOPE_MISMATCH = "report_scope_mismatch"
REPORT_NOT_COMPLETED = "report_not_completed"
CREDENTIAL_NOT_FOUND = "credential_not_found"
CREDENTIAL_SCOPE_INCOMPLETE = "credential_scope_incomplete"
CREDENTIAL_REVOKED = "credential_revoked"
CREDENTIAL_SERVICE_MISMATCH = "credential_service_mismatch"
TIME_CONTEXT_INVALID = "time_context_invalid"
CREDENTIAL_EXPIRED = "credential_expired"
TENANT_SCOPE_MISMATCH = "tenant_scope_mismatch"
JOB_SCOPE_MISMATCH = "job_scope_mismatch"
OBJECT_PREFIX_MISMATCH = "object_prefix_mismatch"
REPORT_SCOPE_SATISFIED = "report_scope_satisfied"
CREDENTIAL_SCOPE_SATISFIED = "credential_scope_satisfied"

REASONS = {
    POLICY_UNAVAILABLE: "policy context unavailable",
    ACTION_INVALID: "action context missing or invalid",
    ACTOR_INVALID: "actor context missing or delegated",
    ACTOR_OR_REPORT_NOT_FOUND: "actor or report not found",
    ACTOR_TENANT_MISMATCH: "actor tenant mismatch",
    REPORT_SCOPE_MISMATCH: "report scope mismatch",
    REPORT_NOT_COMPLETED: "report is not completed",
    CREDENTIAL_NOT_FOUND: "credential not found",
    CREDENTIAL_SCOPE_INCOMPLETE: "credential scope incomplete",
    CREDENTIAL_REVOKED: "credential revoked",
    CREDENTIAL_SERVICE_MISMATCH: "credential service identity mismatch",
    TIME_CONTEXT_INVALID: "time context missing or invalid",
    CREDENTIAL_EXPIRED: "credential expired",
    TENANT_SCOPE_MISMATCH: "tenant scope mismatch",
    JOB_SCOPE_MISMATCH: "job scope mismatch",
    OBJECT_PREFIX_MISMATCH: "object prefix mismatch",
    REPORT_SCOPE_SATISFIED: "owner and tenant policy satisfied",
    CREDENTIAL_SCOPE_SATISFIED: "credential scope satisfied",
}


# [Implementation 1] Authorization decision event contract
class AuthorizationEvent(TypedDict):
    event_id: object
    event_type: str
    actor_id: object
    effective_actor_id: object
    credential_id: object
    tenant_id: object
    job_id: object
    action: object
    resource_id: object
    decision: Decision
    reason_code: str
    reason: str
    correlation_id: object
    policy_version: str


class AuthorizationResult(TypedDict):
    decision: Decision
    reason_code: str
    reason: str
    event: AuthorizationEvent


def _request_value(request: Mapping[str, Any] | object, key: str) -> object:
    if isinstance(request, Mapping):
        return request.get(key)
    return None


def _event(
    request: Mapping[str, Any] | object,
    decision: Decision,
    reason_code: str,
) -> AuthorizationEvent:
    return {
        "event_id": _request_value(request, "event_id"),
        "event_type": "authorization.decision",
        "actor_id": _request_value(request, "actor_id"),
        "effective_actor_id": _request_value(request, "effective_actor_id"),
        "credential_id": _request_value(request, "credential_id"),
        "tenant_id": _request_value(request, "tenant_id"),
        "job_id": _request_value(request, "job_id"),
        "action": _request_value(request, "action"),
        "resource_id": _request_value(request, "resource_id"),
        "decision": decision,
        "reason_code": reason_code,
        "reason": REASONS[reason_code],
        "correlation_id": _request_value(request, "correlation_id"),
        "policy_version": POLICY_VERSION,
    }


def _result(
    request: Mapping[str, Any] | object,
    decision: Decision,
    reason_code: str,
) -> AuthorizationResult:
    event = _event(request, decision, reason_code)
    return {
        "decision": decision,
        "reason_code": reason_code,
        "reason": event["reason"],
        "event": event,
    }


def _deny(
    request: Mapping[str, Any] | object,
    reason_code: str,
) -> AuthorizationResult:
    return _result(request, "deny", reason_code)


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


# [Implementation 2] Shared fail-closed request context

def _common_denial(
    state: Mapping[str, Any] | object,
    request: Mapping[str, Any] | object,
    expected_action: str,
) -> str | None:
    if not isinstance(state, Mapping) or state.get("policy_available") is not True:
        return POLICY_UNAVAILABLE
    if not isinstance(request, Mapping) or request.get("action") != expected_action:
        return ACTION_INVALID
    actor_id = request.get("actor_id")
    effective_actor_id = request.get("effective_actor_id")
    if not _non_empty_string(actor_id) or effective_actor_id != actor_id:
        return ACTOR_INVALID
    return None


def _parse_time(value: object) -> datetime | None:
    if not _non_empty_string(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Fixture의 offset 없는 시각은 UTC로 고정해 실행 환경의 local timezone 영향을 없앱니다.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# [Implementation 3] Report ownership authorization

def authorize_report(
    state: Mapping[str, Any] | object,
    request: Mapping[str, Any] | object,
) -> AuthorizationResult:
    denial = _common_denial(state, request, "report.read")
    if denial is not None:
        return _deny(request, denial)

    if not isinstance(state, Mapping) or not isinstance(request, Mapping):
        return _deny(request, POLICY_UNAVAILABLE)

    tenant_id = request.get("tenant_id")
    if not _non_empty_string(tenant_id):
        return _deny(request, ACTOR_TENANT_MISMATCH)

    actors = _mapping(state.get("actors"))
    reports = _mapping(state.get("reports"))
    actor = _mapping(actors.get(request.get("actor_id"))) if actors else None
    report = _mapping(reports.get(request.get("resource_id"))) if reports else None
    if actor is None or report is None:
        return _deny(request, ACTOR_OR_REPORT_NOT_FOUND)
    if actor.get("tenant_id") != tenant_id:
        return _deny(request, ACTOR_TENANT_MISMATCH)
    if (
        report.get("tenant_id") != tenant_id
        or report.get("owner_id") != request.get("actor_id")
    ):
        return _deny(request, REPORT_SCOPE_MISMATCH)
    if report.get("status") != "completed":
        return _deny(request, REPORT_NOT_COMPLETED)
    return _result(request, "allow", REPORT_SCOPE_SATISFIED)
