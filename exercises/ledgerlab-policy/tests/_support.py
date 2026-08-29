from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

FIXTURE = PROJECT_ROOT / "fixtures/state.json"


def load_state() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def clone_state(state: dict) -> dict:
    return copy.deepcopy(state)


def state_hash(state: dict) -> str:
    payload = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def request(**values: object) -> dict:
    base = {
        "event_id": "EV-LAB-000",
        "actor_id": None,
        "effective_actor_id": None,
        "credential_id": None,
        "tenant_id": "tenant-42",
        "job_id": None,
        "action": None,
        "resource_id": None,
        "correlation_id": "CORR-LAB-1",
    }
    base.update(values)
    return base
