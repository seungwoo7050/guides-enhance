from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, ClassVar


# [Implementation 1]
# Public errors and queued event value.
class CloudModelError(RuntimeError):
    """Base error for operations rejected by the model."""


class AccessDenied(CloudModelError):
    """Raised when a tenant attempts to access another tenant's state."""


class QuotaExceeded(CloudModelError):
    """Raised when a tenant exceeds its active document capacity."""


class TenantInactive(CloudModelError):
    """Raised when an operation targets an unknown or deleted tenant."""


class EventConflict(CloudModelError):
    """Raised when an existing event identity is reused with a new payload."""


@dataclass(slots=True)
class Event:
    event_id: str
    tenant_id: str
    document_id: str
    attempts: int = 0


class CloudModel:
    """Deterministic in-memory tenant, document, and event state model.

    Document quota is active document capacity rather than cumulative writes.
    Event identity is scoped to a tenant as ``(tenant_id, event_id)``.
    """

    PLAN_LIMITS: ClassVar[dict[str, int]] = {"starter": 2, "pro": 100}

    # [Implementation 2]
    # Mutable state stores.
    def __init__(self) -> None:
        self._tenants: dict[str, dict[str, str]] = {}
        self._documents: dict[str, dict[str, str]] = {}
        self._outputs: dict[str, dict[str, str]] = {}
        self._queue: deque[Event] = deque()
        self._dead_letters: list[Event] = []
        self._event_registry: dict[tuple[str, str], str] = {}
        self._processed_events: set[tuple[str, str]] = set()
        self._usage: dict[str, int] = {}
        self._resources: list[dict[str, Any]] = []

    # [Implementation 3]
    # Tenant provisioning and private resources.
    def provision_tenant(self, tenant_id: str, plan: str = "starter") -> None:
        if plan not in self.PLAN_LIMITS:
            raise ValueError(f"unknown plan: {plan}")

        existing = self._tenants.get(tenant_id)
        if existing is not None:
            if existing["state"] == "DELETED":
                raise TenantInactive(f"tenant id cannot be reused: {tenant_id}")
            raise CloudModelError(f"tenant already active: {tenant_id}")

        self._tenants[tenant_id] = {"state": "ACTIVE", "plan": plan}
        self._usage[tenant_id] = 0
        self._resources.extend(
            [
                {
                    "id": f"db-partition:{tenant_id}",
                    "tenant_id": tenant_id,
                    "type": "database",
                    "stateful": True,
                    "public": False,
                },
                {
                    "id": f"object-prefix:{tenant_id}",
                    "tenant_id": tenant_id,
                    "type": "object-prefix",
                    "stateful": True,
                    "public": False,
                },
            ]
        )

    # [Implementation 3-1]
    # Active-tenant validation.
    def _require_active(self, tenant_id: str) -> dict[str, str]:
        tenant = self._tenants.get(tenant_id)
        if tenant is None or tenant["state"] != "ACTIVE":
            raise TenantInactive(tenant_id)
        return tenant

    # [Implementation 4]
    # Document ownership and active-capacity quota.
    def store_document(self, tenant_id: str, document_id: str, content: str) -> None:
        tenant = self._require_active(tenant_id)
        existing = self._documents.get(document_id)

        if existing is not None and existing["tenant_id"] != tenant_id:
            raise AccessDenied(document_id)

        if existing is None:
            active_count = sum(
                1
                for document in self._documents.values()
                if document["tenant_id"] == tenant_id
            )
            capacity = self.PLAN_LIMITS[tenant["plan"]]
            # 새 문서만 active capacity를 사용합니다. 기존 문서 갱신은 수를 늘리지 않습니다.
            if active_count >= capacity:
                raise QuotaExceeded(f"{tenant_id}: {active_count}/{capacity}")

        self._documents[document_id] = {
            "tenant_id": tenant_id,
            "content": content,
        }

    def read_document(self, requester_tenant: str, document_id: str) -> str:
        self._require_active(requester_tenant)
        document = self._documents.get(document_id)
        if document is None or document["tenant_id"] != requester_tenant:
            raise AccessDenied(document_id)
        return document["content"]

    # [Implementation 5]
    # Tenant-scoped event registration.
    def enqueue_event(self, event_id: str, tenant_id: str, document_id: str) -> None:
        self._require_active(tenant_id)
        identity = (tenant_id, event_id)
        registered_document = self._event_registry.get(identity)

        # 같은 tenant에서 event ID를 다른 문서에 재사용하면 재전송이 아니라 충돌입니다.
        if registered_document is not None and registered_document != document_id:
            raise EventConflict(f"event payload changed: {tenant_id}/{event_id}")

        self._event_registry.setdefault(identity, document_id)
        self._queue.append(Event(event_id, tenant_id, document_id))

    def process_next(self, max_attempts: int = 2) -> str:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if not self._queue:
            return "empty"

        event = self._queue.popleft()
        identity = (event.tenant_id, event.event_id)

        # [Implementation 6]
        # Duplicate-safe output and usage updates.
        if identity in self._processed_events:
            return "duplicate"

        try:
            self._require_active(event.tenant_id)
            document = self._documents.get(event.document_id)
            if document is None or document["tenant_id"] != event.tenant_id:
                raise CloudModelError("missing or mismatched document")

            output_id = (
                f"result:{event.tenant_id}:{event.document_id}:{event.event_id}"
            )
            self._outputs[output_id] = {
                "tenant_id": event.tenant_id,
                "document_id": event.document_id,
                "source_event": event.event_id,
            }
            self._usage[event.tenant_id] = self._usage.get(event.tenant_id, 0) + 1
            # output과 usage를 반영한 뒤 완료로 표시해야 중복 판정 기준이 맞습니다.
            self._processed_events.add(identity)
            return "processed"

        # [Implementation 6-1]
        # Retry attempts and dead-letter transition.
        except CloudModelError:
            event.attempts += 1
            if event.attempts >= max_attempts:
                self._dead_letters.append(event)
                return "dead-lettered"
            self._queue.append(event)
            return "retry"

    # [Implementation 6-2]
    # Bounded queue draining.
    def drain_events(self, max_attempts: int = 2, max_steps: int = 100) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")

        steps = 0
        while self._queue and steps < max_steps:
            self.process_next(max_attempts=max_attempts)
            steps += 1

        if self._queue:
            raise CloudModelError("event drain exceeded max_steps")

    def usage_for(self, tenant_id: str) -> int:
        return self._usage.get(tenant_id, 0)
