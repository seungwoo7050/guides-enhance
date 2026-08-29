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
